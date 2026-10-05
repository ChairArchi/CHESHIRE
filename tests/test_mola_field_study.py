"""Focused deterministic field, cap-chain, budget and local-preference checks."""

from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest
from compas.datastructures import Mesh
from cheshire import ExecutionBudget

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))
from cheshire_worker import mesh_from_data, mesh_to_data
from exchange import face_driver_display_data, read_json, validate_response, write_json_atomic
from local_settings import remembered_mola_path, remember_mola_path
from mola_field_study import original_face_fields, run_mola_field_study
from mola_field_study import MODE
from worker_process import worker_launch_options

DLL = os.environ.get("CHESHIRE_MOLA_DLL")
real_backend = pytest.mark.skipif(not DLL or not importlib.util.find_spec("pythonnet"), reason="Configure the optional real Mola backend.")


def vertical_mesh():
    return Mesh.from_vertices_and_faces([[x, 0, z] for z in range(4) for x in range(2)],
        [[2*z, 2*z+1, 2*z+3, 2*z+2] for z in range(3)])


def request(mesh):
    return {"protocol": 1, "mode": MODE, "run_id": str(uuid4()),
            "source": {"document_serial": 0, "object_id": "control"}, "mola_dll": DLL,
            "selected_faces": "ALL_ELIGIBLE_PLANAR", "mesh": mesh_to_data(mesh)}


def test_original_fields_deterministic_exact_mapping_and_flat_face_display(open_mesh):
    mesh = vertical_mesh()
    before = deepcopy(mesh.__data__)
    fields = original_face_fields(mesh, list(mesh.faces()))
    rows = fields["faces"]
    assert [row["height_driver"] for row in rows] == [0.0, 0.5, 1.0]
    assert [row["taper_driver"] for row in rows] == [1.0, 0.0, 1.0]
    assert [row["height_ratio"] for row in rows] == pytest.approx([0.05, 0.20, 0.35])
    assert [row["original_fraction"] for row in rows] == pytest.approx([0.75, 0.15, 0.75])
    assert fields == original_face_fields(mesh, list(mesh.faces())) and mesh.__data__ == before
    constant = original_face_fields(open_mesh, list(open_mesh.faces()))
    assert constant["faces"][0]["height_driver"] == constant["faces"][0]["taper_driver"] == 0.5
    assert len(constant["warnings"]) == 2
    data, values, ids = face_driver_display_data(mesh_to_data(mesh), rows, "height_driver")
    assert len(data["vertices"]) == 12  # Shared calculation corners duplicated only for display.
    assert [row["id"] for row in data["faces"]] == list(mesh.faces())
    for face in data["faces"]:
        assert all(values[k] == rows[face["id"]]["height_driver"] for k in face["vertices"])
        assert [ids[k] for k in face["vertices"]] == mesh.face_vertices(face["id"])


def test_ignored_preference_roundtrip_invalid_path_and_explicit_replacement(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    first, second = tmp_path / "official.dll", tmp_path / "replacement.dll"
    first.write_bytes(b"Preference fixture only; not loaded as an assembly.")
    second.write_bytes(b"Preference fixture only; not loaded as an assembly.")
    assert remembered_mola_path(root) is None
    assert remember_mola_path(root, str(first)) == str(first.resolve())
    assert remembered_mola_path(root) == str(first.resolve())
    remember_mola_path(root, str(second))
    assert remembered_mola_path(root) == str(second.resolve())
    second.unlink()
    assert remembered_mola_path(root) is None
    (root / "output/local_settings.json").write_text("malformed")
    assert remembered_mola_path(root) is None
    internal = root / "internal.dll"
    internal.write_bytes(b"invalid installation location")
    with pytest.raises(ValueError):
        remember_mola_path(root, str(internal))
    assert subprocess.check_output(["git", "check-ignore", "output/local_settings.json"], cwd=ROOT).strip() == b"output/local_settings.json"


@real_backend
def test_real_three_generations_cap_only_alignment_lineage_and_immutability():
    mesh = vertical_mesh()
    payload = request(mesh)
    before = deepcopy(payload)
    result = run_mola_field_study(payload)
    assert result["status"] == "SUCCESS", result["reason"]
    assert [(s["vertex_count"], s["face_count"]) for s in result["stages"]] == [(20, 15), (32, 27), (44, 39)]
    original_fields = {row["id"]: row for row in result["drivers"]["faces"]}
    previous = payload["mesh"]
    for index, stage in enumerate(result["stages"]):
        selected = [0, 1, 2] if index == 0 else result["stages"][index-1]["cap_faces"]
        assert stage["processed_faces"] == selected and len(stage["cap_faces"]) == 3
        assert stage["lineage_coverage"] == [] and stage["recompute_fields"] == ["face_area"]
        source = mesh_from_data(previous)
        for row in stage["parameters"]:
            root = original_fields[row["root_face"]]
            assert row["height_driver"] == root["height_driver"] and row["taper_driver"] == root["taper_driver"]
            assert row["height_ratio"] == pytest.approx(root["height_ratio"]*[1.0, 0.65, 0.40][index])
            assert row["height"] == pytest.approx(row["height_ratio"]*source.face_area(row["id"])**0.5)
            assert row["fraction"] == pytest.approx(root["original_fraction"]+[0, 0.1, -0.05][index])
        for entry in stage["lineage"]["faces"]:
            parent = entry["parents"][0]["id"]
            if entry["id"] not in {r["id"] for r in previous["faces"]}:
                assert parent in selected
        # Earlier side faces keep their keys/connectivity across later steps.
        final_faces = {row["id"]: row["vertices"] for row in stage["mesh"]["faces"]}
        for face in previous["faces"]:
            if face["id"] not in selected:
                assert final_faces[face["id"]] == face["vertices"]
        previous = stage["mesh"]
    assert payload == before and mesh_to_data(mesh) == before["mesh"]
    assert result["top_five_g1"][0]["root_face"] == 2
    constant = Mesh.from_vertices_and_faces([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], [[0, 1, 2, 3]])
    weak = run_mola_field_study(request(constant))
    assert weak["status"] == "SUCCESS" and "visually weak" in weak["variation_assessment"]
    # A disconnected valid concave face is excluded and stays unchanged,
    # including across recursive generations; unavailable drivers stay None.
    with_exclusion = vertical_mesh()
    for key, (x, y, z) in zip(range(100, 104), [(10, 0, 0), (12, 0, 0), (10.5, 0, 0.2), (10, 0, 1)]):
        with_exclusion.add_vertex(key=key, x=x, y=y, z=z)
    with_exclusion.add_face([100, 101, 102, 103], fkey=900)
    excluded = run_mola_field_study(request(with_exclusion))
    assert excluded["status"] == "SUCCESS" and excluded["excluded_faces"][0]["id"] == 900
    for stage in excluded["stages"]:
        assert 900 not in stage["processed_faces"]
        assert mesh_from_data(stage["mesh"]).face_vertices(900) == [100, 101, 102, 103]
        assert next(row["value"] for row in stage["fields"]["height_driver"] if row["id"] == 900) is None


@real_backend
def test_excessive_generation_stops_before_backend_and_keeps_valid_checkpoint(monkeypatch):
    import mola_field_study as study
    native, calls = study.extrude_tapered_once, []
    def recorded(*args, **kwargs):
        calls.append(kwargs["selected_faces"].copy())
        return native(*args, **kwargs)
    monkeypatch.setattr(study, "extrude_tapered_once", recorded)
    payload = request(vertical_mesh())
    result = study.run_mola_field_study(payload, budget=ExecutionBudget(28, 50, 3))
    assert result["status"] == "PARTIAL" and len(result["stages"]) == len(calls) == 2
    assert result["stages"][-1]["face_count"] == 27
    assert result["next_budget"]["generation"] == 3 and result["next_budget"]["status"] == "BLOCKED"
    assert "blocked before Mola" in result["reason"]
    validate_response(result, payload)


@real_backend
def test_real_isolated_external_worker_field_study(tmp_path):
    payload = request(vertical_mesh())
    write_json_atomic(tmp_path / "request.json", payload)
    process = subprocess.run(**worker_launch_options(ROOT, tmp_path / "request.json", tmp_path / "response.json"),
                             capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    result = validate_response(read_json(tmp_path / "response.json"), payload)
    assert result["status"] == "SUCCESS" and len(result["stages"]) == 3, result["reason"]
    assert result["stages"][0]["backend"]["runtime"].startswith("8.")
    assert "G1/G2/G3 cap recursion completed" in process.stdout


@real_backend
def test_partial_checkpoint_reporting_and_insertion_without_final_metadata(monkeypatch):
    payload = request(vertical_mesh())
    checkpoints = []
    complete = run_mola_field_study(payload, publish=lambda value: checkpoints.append(deepcopy(value)))
    assert complete["status"] == "SUCCESS", complete["reason"]

    # Exercise the actual launcher functions with native host calls stubbed;
    # geometry/checkpoints come from the real DLL. This is not a host UI test.
    output, inserted = [], []
    rhino = MagicMock()
    rhino.RhinoApp.WriteLine.side_effect = output.append
    rhino.DocObjects.ObjectAttributes.side_effect = lambda: SimpleNamespace(SetUserString=MagicMock())
    eto, forms, system, drawing = [ModuleType(name) for name in ("Eto", "Eto.Forms", "System", "System.Drawing")]
    eto.Forms = forms
    system.Guid = SimpleNamespace(Empty=uuid4())
    drawing.Color = MagicMock()
    for name, module in (("Rhino", rhino), ("Eto", eto), ("Eto.Forms", forms), ("System", system), ("System.Drawing", drawing)):
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("cheshire_checkpoint_launcher", ROOT / "rhino/CHESHIRE_Run.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    monkeypatch.setattr(launcher, "data_to_rhino_mesh", lambda data, *args: SimpleNamespace(data=data, SetUserString=MagicMock()))
    doc = MagicMock()
    doc.BeginUndoRecord.return_value = 1
    doc.Layers.Add.return_value = 0
    doc.Objects.AddMesh.side_effect = lambda mesh, attrs: inserted.append((attrs.Name, mesh.data)) or uuid4()
    doc.Objects.AddTextDot.side_effect = lambda *args: uuid4()

    for number in (1, 2):
        checkpoint = deepcopy(checkpoints[number-1])
        assert checkpoint["status"] == "PARTIAL" and len(checkpoint["stages"]) == number
        for name in ("variation_assessment", "rhino_host_status", "elapsed_seconds"):
            checkpoint.pop(name, None)
        if number == 2:
            checkpoint.pop("top_five_g1", None)
            checkpoint["drivers"].pop("warnings", None)
        # Cover both an absent stop description and an actual timeout reason.
        checkpoint["reason"] = None if number == 1 else "Worker TIMEOUT; retaining the validated G2 checkpoint."
        before = deepcopy(checkpoint)
        validate_response(checkpoint, payload)
        output.clear()
        inserted.clear()
        launcher.print_steps(checkpoint)
        launcher.insert_results(doc, payload, checkpoint)
        text = "\n".join(output)
        assert f"Last completed generation: G{number} (PARTIAL)" in text
        assert "G1/G2/G3 cap recursion completed" not in text
        if number == 2:
            assert checkpoint["reason"] in text
        assert [label for label, _ in inserted[:3]] == ["ORIGINAL REFERENCE", "HEIGHT DRIVER", "TAPER DRIVER"]
        assert len(inserted) == 3+number
        assert inserted[-1][0].startswith(f"G{number}") and "last valid; PARTIAL" in inserted[-1][0]
        assert inserted[-1][1] == checkpoint["stages"][-1]["mesh"]
        assert checkpoint == before

    # New checkpoints include the static ORIGINAL-driver summary immediately.
    assert all(value["variation_assessment"] == complete["variation_assessment"] and
               value["rhino_host_status"] == complete["rhino_host_status"] for value in checkpoints)
    output.clear()
    inserted.clear()
    validate_response(complete, payload)
    launcher.print_steps(complete)
    launcher.insert_results(doc, payload, complete)
    assert output[0] == "MOLA_FIELD_STUDY SUCCESS: G1/G2/G3 cap recursion completed."
    assert complete["variation_assessment"] in output
    assert len(inserted) == 6 and inserted[-1][0] == "G3 - cap recursion"
    assert inserted[-1][1] == complete["stages"][-1]["mesh"]
