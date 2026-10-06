"""Focused batch contracts; existing geometry tests remain authoritative."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import morphology as batch
from test_visual_prototype import control, payload
from test_mola_field_study import real_backend, DLL


def test_enumeration_preserves_family_ids_defaults_and_real_controls():
    before = deepcopy(batch.RECIPES)
    rows = batch.initial_candidates()
    assert len(rows) == 27 and len({r["candidate_id"] for r in rows}) == 27
    assert rows == batch.initial_candidates() and batch.RECIPES == before
    for row in rows:
        batch.check_candidate(row)
        assert row["recipe"]["id"] == row["candidate_id"][0]
    wrong = deepcopy(rows[0]); wrong["recipe"]["id"] = "A017"
    with pytest.raises(ValueError): batch.check_candidate(wrong)
    inert = batch.candidate("A", 17, {"quad_levels": 2})
    with pytest.raises(ValueError, match="fixed behavior"): batch.check_candidate(inert)


def test_each_request_resets_source_and_volatile_comparison_keeps_geometry(tmp_path, monkeypatch):
    source = payload(control()); before = deepcopy(source)
    a = batch.source_request(source, source["mola_dll"])
    b = batch.source_request(source, source["mola_dll"])
    assert a["run_id"] != b["run_id"] and a["mesh"] == b["mesh"] == source["mesh"]
    a["mesh"]["vertices"][0]["xyz"][0] += 1
    assert source == before and b["mesh"] == before["mesh"]
    assert batch.digest(batch.deterministic(a)) != batch.digest(batch.deterministic(b))
    # Initialization must write all explicit candidate files before geometry.
    source_path = tmp_path / "source.json"; batch.write_json_atomic(source_path, source)
    monkeypatch.setattr(batch, "remembered_mola_path", lambda _: source["mola_dll"])
    monkeypatch.setattr(batch, "runtime_identity", lambda _: {"test": True})
    manifest = batch.initialize(tmp_path / "study", source_path, tmp_path / "baseline.json")
    assert len(list((tmp_path / "study/candidates").glob("*.json"))) == 27
    assert manifest["source_info"]["inspection"]["vertex_count"] == 81


def test_timeout_reaps_owned_process_and_retains_partial_status(tmp_path):
    from worker_process import worker_launch_options
    options = worker_launch_options(ROOT, tmp_path / "request.json", tmp_path / "response.json")
    options["args"] = options["args"][:3] + ["-c", "import time; time.sleep(4)"]
    outcome = batch.monitored_process(options, tmp_path, .6, tmp_path, 0,
        tmp_path / "stdout.txt", tmp_path / "stderr.txt")
    assert outcome["stop_reason"] == "timeout" and outcome["returncode"] != 0
    assert batch.classify_response(None, outcome) == "timeout"
    partial = {"status": "PARTIAL", "variants": [{"steps": [1]}]}
    assert batch.classify_response(partial, outcome) == "partial"
    blocked = {"status": "FAILED", "variants": [], "reason": "Operation blocked before execution: face budget"}
    assert batch.classify_response(blocked, {"stop_reason": None, "returncode": 1}) == "budget skip"


def test_resume_refuses_changed_source_code_runtime_or_recipe(tmp_path, monkeypatch):
    source = payload(control())
    path = tmp_path / "source.json"; batch.write_json_atomic(path, source)
    monkeypatch.setattr(batch, "code_identity", lambda: {"sha256": "code"})
    monkeypatch.setattr(batch, "runtime_identity", lambda _: {"runtime": "same"})
    manifest = {"source_path": str(path), "identities": {"source": batch.digest(source["mesh"]),
        "code": "code", "runtime": batch.digest({"runtime": "same"})}, "candidates": [batch.candidate("A", 0)]}
    batch.assert_identity(manifest, "unused")
    for identity in ("source", "code", "runtime"):
        changed = deepcopy(manifest); changed["identities"][identity] = "changed"
        with pytest.raises(ValueError, match="identity mismatch"): batch.assert_identity(changed, "unused")
    manifest["candidates"][0]["recipe"]["parameters"]["width"] = .1
    with pytest.raises(ValueError, match="Recipe identity changed"): batch.assert_identity(manifest, "unused")


@real_backend
def test_actual_baseline_and_cap_only_reproduce_with_identical_roots(tmp_path):
    from worker_process import worker_launch_options
    records = []
    for number, changes in ((0, {}), (8, {"study_cap_only": True}), (9, {"study_cap_only": True})):
        request = batch.source_request(payload(control()), DLL)
        row = batch.candidate("B", number, changes)
        directory = tmp_path / str(number); directory.mkdir()
        batch.write_json_atomic(directory / "request.json", request)
        batch.write_json_atomic(directory / "recipe.json", row)
        options = worker_launch_options(ROOT, directory / "request.json", directory / "response.json")
        options["args"][3] = str(ROOT / "tools/morphology_worker.py")
        options["args"].append(str(directory / "recipe.json"))
        result = subprocess.run(**options, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        response = batch.validate_response(batch.read_json(directory / "response.json"), request)
        records.append(response["variants"][0])
    baseline, ablation, repeat = records
    assert batch.deterministic(ablation) == batch.deterministic(repeat)
    assert batch.deterministic(baseline["steps"][0]) == batch.deterministic(ablation["steps"][0])
    roles = {r["id"]: r["role"] for r in ablation["steps"][0]["face_roles"]}
    assert all(roles[k] == "cap" for k in ablation["steps"][1]["parameters"]["selected_faces"])
    assert ablation["semantic_lineage"] == "AVAILABLE_IN_STEPS"
