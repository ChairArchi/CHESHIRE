"""Focused exchange/recipe checks; actual Rhino UI checks are manual."""

from copy import deepcopy
import importlib.util
import json
from math import isfinite
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from compas.datastructures import Mesh
from cheshire import (
    ExecutionBudget, Rule, analyze_vertex_attributes, build_scalar_field,
    displace_vertices_along_normals, evaluate_vertex_rule, subdivide_quad_once,
)


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cheshire_demo_worker", ROOT / "rhino/cheshire_worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
from exchange import read_json, validate_request, validate_response, write_json_atomic


def request(mesh, strength=0.01):
    return {"protocol": 1, "run_id": str(uuid4()), "source": {"document_serial": 7, "object_id": "control"},
            "strength": strength, "mesh": worker.mesh_to_data(mesh)}


def test_mesh_exchange_retains_sparse_ids_coincident_vertices_and_winding(open_mesh):
    mesh = Mesh()
    for keys, face in (([900, 10, -4, 77], 700), ([300, 400, 500, 600], 900)):
        for key, original in zip(keys, open_mesh.vertices()):
            x, y, z = open_mesh.vertex_coordinates(original)
            mesh.add_vertex(key=key, x=x, y=y, z=z)
        mesh.add_face(keys, fkey=face)
    data = worker.mesh_to_data(mesh)
    assert worker.mesh_to_data(worker.mesh_from_data(data)) == data
    assert worker.mesh_from_data(data).number_of_vertices() == 8


def test_worker_recipe_matches_direct_core_and_leaves_input_unchanged(box_mesh):
    payload = request(box_mesh)
    before = deepcopy(payload)
    result = worker.run_experiment(payload)
    assert result["status"] == "SUCCESS", result["reason"]
    mesh = box_mesh
    rule = Rule("positive", "driver", "vertex", "greater_than", 0.0)
    for index, stage in enumerate(result["stages"]):
        refined = subdivide_quad_once(mesh, budget=ExecutionBudget(50000, max_vertices=50000, max_generation=4),
                                     current_generation=index, nonplanar_policy="bilinear")
        field = build_scalar_field(analyze_vertex_attributes(refined.mesh), "approximate_curvature", mapping="power",
                                   exponent=2.0, lower_percentile=0.0, upper_percentile=100.0)
        selected = evaluate_vertex_rule(field["values"], rule)["selected_keys"]
        transformed = displace_vertices_along_normals(refined.mesh, field["values"], selected_vertices=selected,
                                                     strength=0.01 / 2 ** index)
        assert stage["mesh"] == worker.mesh_to_data(transformed.mesh)
        assert stage["moved_count"] == transformed.moved_count > 0
        assert stage["maximum_displacement"] == transformed.max_displacement
        assert stage["lineage_coverage"] == [] and stage["recompute_fields"] == ["driver"]
        assert stage["vertex_count"] == stage["estimated_vertex_count"]
        assert stage["face_count"] == stage["estimated_face_count"]
        assert all(isfinite(value) for row in stage["mesh"]["vertices"] for value in row["xyz"])
        mesh = transformed.mesh
    assert payload == before and worker.mesh_to_data(box_mesh) == before["mesh"]
    assert result["driver"]["mesh"] != result["stages"][0]["mesh"]
    assert result["driver"]["parameters"] == {"exponent": 2.0, "lower_percentile": 0.0, "upper_percentile": 100.0}


def test_flat_open_control_reports_unavailable_without_alternative_field(open_mesh):
    result = worker.run_experiment(request(open_mesh))
    assert result["status"] == "SUCCESS"
    assert all(stage["moved_count"] == 0 for stage in result["stages"])
    assert result["stages"][0]["unavailable_count"] > 0
    assert all(row["value"] in (None, 0.0) for row in result["driver"]["values"])
    assert all(stage["notice"] for stage in result["stages"])


def test_budget_partial_response_contains_only_completed_valid_stages(box_mesh, monkeypatch):
    monkeypatch.setattr(worker, "MAX_STAGE_COUNT", 128)  # G2 has 98 vertices / 96 faces.
    payload = request(box_mesh, strength=0)
    saved = []
    result = worker.run_experiment(payload, publish=lambda value: saved.append(deepcopy(value)))
    assert result["status"] == "PARTIAL" and "budget" in result["reason"]
    assert [stage["face_count"] for stage in result["stages"]] == [24, 96]
    assert all(stage["validated"] for value in saved for stage in value["stages"])
    validate_response(result, payload)


def test_later_geometry_failure_retains_previous_stage(box_mesh, monkeypatch):
    native = worker.subdivide_quad_once
    calls = []

    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise ValueError("Unsupported geometry control")
        return native(*args, **kwargs)

    monkeypatch.setattr(worker, "subdivide_quad_once", fail_second)
    result = worker.run_experiment(request(box_mesh))
    assert result["status"] == "PARTIAL" and len(result["stages"]) == 1
    assert "G2 stopped" in result["reason"] and "Unsupported geometry" in result["reason"]


def test_exchange_rejects_stale_nonfinite_and_malformed_data(box_mesh, tmp_path):
    payload = request(box_mesh)
    result = worker.run_experiment(payload)
    stale = deepcopy(result)
    stale["run_id"] = str(uuid4())
    with pytest.raises(ValueError, match="match"):
        validate_response(stale, payload)
    bad = deepcopy(payload)
    bad["mesh"]["vertices"][0]["xyz"][0] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        validate_request(bad)
    malformed = deepcopy(payload["mesh"])
    malformed["faces"][0]["vertices"][1] = malformed["faces"][0]["vertices"][0]
    with pytest.raises(ValueError, match="distinct"):
        worker.mesh_from_data(malformed)
    path = tmp_path / "response.json"
    write_json_atomic(path, result)
    with pytest.raises(ValueError):
        write_json_atomic(path, {"bad": float("inf")})
    assert read_json(path) == result and list(tmp_path.iterdir()) == [path]


def test_external_worker_uses_real_venv_request_response(box_mesh, tmp_path):
    payload = request(box_mesh)
    write_json_atomic(tmp_path / "request.json", payload)
    process = subprocess.run([sys.executable, str(ROOT / "rhino/cheshire_worker.py"),
                              str(tmp_path / "request.json"), str(tmp_path / "response.json")],
                             shell=False, capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    result = validate_response(read_json(tmp_path / "response.json"), payload)
    assert result["status"] == "SUCCESS" and result["stages"][-1]["face_count"] == 1536
    assert json.loads((tmp_path / "request.json").read_text()) == payload
