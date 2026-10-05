"""Focused real COMPAS, boundary, budget and unchanged-raw bridge checks."""

from copy import deepcopy
import importlib.util
from math import isfinite
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from compas.datastructures import Mesh

from cheshire import ExecutionBudget
from cheshire.surface import catmull_clark_once

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))
from exchange import MOLA_SURFACE_MODE, read_json, validate_response, write_json_atomic
from mola_surface_study import compare_raw_stages
from worker_process import worker_launch_options
from test_mola_field_study import real_backend, request, run_mola_field_study, vertical_mesh


def test_real_compas_counts_finite_geometry_only_copy_and_source_immutability(box_mesh):
    box_mesh.vertex_attribute(0, "driver", 0.8)
    box_mesh.face_attribute(0, "cap_role", "cap")
    box_mesh.edge_attribute(next(box_mesh.edges()), "crease", 100)
    before = deepcopy(box_mesh.__data__)
    result = catmull_clark_once(box_mesh)
    assert result.mesh.number_of_vertices() == 26 and result.mesh.number_of_faces() == 24
    assert all(isfinite(v) for k in result.mesh.vertices() for v in result.mesh.vertex_coordinates(k))
    assert result.mesh.is_valid() and result.mesh.is_manifold() and result.mesh.is_closed()
    assert result.metadata["retained_vertex_displacement"]["median"] > 0
    assert result.metadata["semantic_lineage"] == "NOT IMPLEMENTED"
    assert all(result.mesh.vertex_attribute(k, "driver") is None for k in result.mesh.vertices())
    assert all(result.mesh.face_attribute(k, "cap_role") is None for k in result.mesh.faces())
    assert not any(result.mesh.edge_attribute(e, "crease") for e in result.mesh.edges())
    assert box_mesh.__data__ == before


def test_open_nonplanar_control_fixes_boundary_and_only_creases_boundary(monkeypatch, grid_mesh):
    grid_mesh.vertex_attribute(12, "z", 1.0)  # Interior faces need not be planar.
    before = deepcopy(grid_mesh.__data__)
    boundary = [e for e in grid_mesh.edges() if grid_mesh.is_edge_on_boundary(e)]
    fixed = {k for e in boundary for k in e}
    native, calls = Mesh.subdivided, []
    def recorded(mesh, **options):
        calls.append(options)
        assert {e for e in mesh.edges() if mesh.edge_attribute(e, "crease") == 2} == set(boundary)
        return native(mesh, **options)
    monkeypatch.setattr(Mesh, "subdivided", recorded)
    result = catmull_clark_once(grid_mesh)
    assert calls == [{"scheme": "catmullclark", "k": 1, "fixed": sorted(fixed)}]
    assert all(result.mesh.vertex_coordinates(k) == grid_mesh.vertex_coordinates(k) for k in fixed)
    assert result.mesh.vertex_coordinates(12) != grid_mesh.vertex_coordinates(12)
    for u, v in boundary:
        midpoint = [(a + b) / 2 for a, b in zip(grid_mesh.vertex_coordinates(u), grid_mesh.vertex_coordinates(v))]
        candidates = set(result.mesh.vertex_neighbors(u)) & set(result.mesh.vertex_neighbors(v))
        assert len(candidates) == 1
        w = candidates.pop()
        assert result.mesh.vertex_coordinates(w) == midpoint
        assert result.mesh.is_edge_on_boundary((u, w)) and result.mesh.is_edge_on_boundary((w, v))
    assert result.metadata["boundary_preservation"]["status"] == "PASS"
    assert result.metadata["fixed_vertex_count"] == result.metadata["creased_edge_count"] == 16
    assert result.metadata["components_before"] == result.metadata["components_after"] == 1
    assert grid_mesh.__data__ == before


def test_over_budget_blocks_before_copy_or_backend(monkeypatch, box_mesh):
    import cheshire.surface as surface
    def forbidden(*args, **kwargs):
        pytest.fail("Over-budget execution reached copying/subdivision.")
    monkeypatch.setattr(surface, "Mesh", forbidden)
    monkeypatch.setattr(Mesh, "subdivided", forbidden)
    with pytest.raises(ValueError, match="blocked before copying/subdivision"):
        catmull_clark_once(box_mesh, budget=ExecutionBudget(23, 26))
    with pytest.raises(ValueError, match="blocked before copying/subdivision"):
        catmull_clark_once(box_mesh, budget=ExecutionBudget(24, 25))


@real_backend
def test_real_worker_keeps_raw_semantics_separate_and_independent_budget_stop(tmp_path, monkeypatch):
    import mola_surface_study as study
    payload = request(vertical_mesh())
    raw = run_mola_field_study(payload)
    before = deepcopy(raw)
    payload["mode"] = MOLA_SURFACE_MODE
    write_json_atomic(tmp_path / "request.json", payload)
    process = subprocess.run(**worker_launch_options(ROOT, tmp_path / "request.json", tmp_path / "response.json"),
                             capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    response = validate_response(read_json(tmp_path / "response.json"), payload)
    assert response["status"] == "SUCCESS"
    for old, new in zip(raw["stages"], response["stages"]):
        assert {k: v for k, v in old.items() if k != "elapsed_seconds"} == {k: v for k, v in new.items() if k != "elapsed_seconds"}
    assert response["recipe"] == raw["recipe"] and response["drivers"] == raw["drivers"]
    assert [row["source_generation"] for row in response["derivatives"]] == [1, 3]
    assert all(row["semantic_lineage"] == "NOT IMPLEMENTED" and "fields" not in row and "lineage" not in row for row in response["derivatives"])
    invalid = deepcopy(response)
    invalid["derivatives"][0]["fields"] = raw["stages"][0]["fields"]
    with pytest.raises(ValueError, match="cannot be reassigned"):
        validate_response(invalid, payload)
    native, copies = study.mesh_from_data, []
    def recorded(data):
        copies.append(data)
        return native(data)
    monkeypatch.setattr(study, "mesh_from_data", recorded)
    limited = compare_raw_stages(raw, payload, budget=ExecutionBudget(80, 100))
    validate_response(limited, payload)
    assert limited["status"] == "PARTIAL" and len(limited["stages"]) == 3
    assert [row["status"] for row in limited["derivatives"]] == ["SUCCESS", "BLOCKED"]
    assert copies == [raw["stages"][0]["mesh"]]  # G3 blocked before creating a COMPAS copy.
    assert "mesh" not in limited["derivatives"][1]
    assert limited["stages"] == raw["stages"] and raw == before
    # Exercise actual UI orchestration with host calls stubbed. This does not
    # claim a Rhino host run; it guards complete and budget-blocked insertion.
    output, inserted = [], []
    rhino = MagicMock()
    rhino.RhinoApp.WriteLine.side_effect = output.append
    rhino.DocObjects.ObjectAttributes.side_effect = lambda: SimpleNamespace(SetUserString=MagicMock())
    eto, forms, system, drawing = [ModuleType(name) for name in ("Eto", "Eto.Forms", "System", "System.Drawing")]
    eto.Forms, system.Guid, drawing.Color = forms, SimpleNamespace(Empty=uuid4()), MagicMock()
    for name, module in (("Rhino", rhino), ("Eto", eto), ("Eto.Forms", forms), ("System", system), ("System.Drawing", drawing)):
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("cheshire_surface_launcher", ROOT / "rhino/CHESHIRE_Run.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    offsets = []
    def display(data, offset, values):
        assert values is None
        offsets.append(offset)
        return SimpleNamespace(data=data)
    monkeypatch.setattr(launcher, "data_to_rhino_mesh", display)
    doc = MagicMock()
    doc.BeginUndoRecord.return_value, doc.Layers.Add.return_value = 1, 0
    doc.Objects.AddMesh.side_effect = lambda mesh, attrs: inserted.append((attrs.Name, mesh.data)) or uuid4()
    doc.Objects.AddTextDot.side_effect = lambda *args: uuid4()
    for result, expected in ((response, 5), (limited, 4)):
        output.clear()
        inserted.clear()
        offsets.clear()
        launcher.print_steps(result)
        launcher.insert_results(doc, payload, result)
        assert len(inserted) == expected and inserted[0] == ("ORIGINAL REFERENCE", payload["mesh"])
        assert inserted[1] == ("G1 RAW", raw["stages"][0]["mesh"])
        assert inserted[2][0] == "G1 + CATMULL-CLARK 1"
        assert inserted[3][1] == raw["stages"][2]["mesh"]
        assert offsets == [offsets[0] * k for k in range(1, expected + 1)]
        if result is limited:
            assert inserted[3][0] == "G3 RAW (CC1 BLOCKED)" and any("BLOCKED" in line for line in output)
    assert raw == before
