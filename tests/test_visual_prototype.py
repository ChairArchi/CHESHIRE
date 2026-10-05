"""Small checks for the consolidated study, not a new operator test matrix."""

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))
from cheshire_worker import mesh_to_data
from exchange import VISUAL_MODE, read_json, validate_response, write_json_atomic
from visual_prototype import RECIPES, _initial_fields, run_visual_prototype
from worker_process import worker_launch_options
from test_mola_field_study import DLL, real_backend


def control():
    return Mesh.from_vertices_and_faces([[x, 0, z] for z in range(9) for x in range(9)],
        [[z * 9 + x, z * 9 + x + 1, (z + 1) * 9 + x + 1, (z + 1) * 9 + x] for z in range(8) for x in range(8)])


def payload(mesh):
    return {"protocol": 1, "mode": VISUAL_MODE, "run_id": str(uuid4()), "source": {"document_serial": 0, "object_id": "vertical-control"},
            "mola_dll": DLL or str(ROOT.parent / "Libraries/HDMola/1.0.0/HDMola.dll"),
            "mesh": mesh_to_data(mesh), "selected_faces": "ALL_ELIGIBLE_PLANAR"}


@pytest.fixture(scope="module")
def real_study(tmp_path_factory):
    if not DLL or not importlib.util.find_spec("pythonnet"):
        pytest.skip("Configure the optional real Mola backend.")
    directory = tmp_path_factory.mktemp("visual-prototype")
    request = payload(control())
    write_json_atomic(directory / "request.json", request)
    process = subprocess.run(**worker_launch_options(ROOT, directory / "request.json", directory / "response.json"),
                             capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    return request, validate_response(read_json(directory / "response.json"), request)


def test_fixed_spatial_regions_are_reproducible_distinct_and_leave_quiet_areas():
    mesh = control()
    before = deepcopy(mesh.__data__)
    selections = []
    for recipe in RECIPES:
        fields = _initial_fields(mesh, recipe)
        assert fields == _initial_fields(mesh, recipe)
        selections.append({key for key, value in fields["region"].items() if value != "quiet"})
    assert all(0 < len(keys) < mesh.number_of_faces() for keys in selections)
    assert len({frozenset(keys) for keys in selections}) == 3
    assert RECIPES[0]["order"] != RECIPES[1]["order"] != RECIPES[2]["order"]
    assert mesh.__data__ == before


def test_count_budget_stops_before_any_operator_and_preserves_original(monkeypatch):
    import visual_prototype as study
    def forbidden(*args, **kwargs):
        pytest.fail("An over-budget recipe reached geometry execution.")
    for name in ("subdivide_quad_once", "extrude_tapered_once", "displace_vertices_along_normals", "catmull_clark_once"):
        monkeypatch.setattr(study, name, forbidden)
    request = payload(control())
    before = deepcopy(request)
    response = run_visual_prototype(request, budget=ExecutionBudget(63, 80))
    assert response["status"] == "FAILED" and response["variants"] == []
    assert all("blocked before execution" in row["reason"] for row in response["attempts"])
    assert request == before


@real_backend
def test_real_worker_three_actual_alternatives_and_available_lineage(real_study):
    request, response = real_study
    assert response["status"] == "SUCCESS", response["reason"]
    assert [row["id"] for row in response["variants"]] == ["A", "B", "C"]
    assert [len(row["steps"]) for row in response["variants"]] == [4, 3, 4]
    assert len({str(row["mesh"]) for row in response["variants"]}) == 3
    for variant in response["variants"]:
        assert all(isfinite(v) for row in variant["mesh"]["vertices"] for v in row["xyz"])
        for step in variant["steps"]:
            if "terminal_derivative" not in step:
                assert step["lineage_coverage"] == []
                assert set(step["fields"]) >= {"root_face", "source_u", "source_v", "face_area"}
                assert all(entry["value"] is not None for rows in step["fields"].values() for entry in rows)
            assert len(step["parameters"].get("selected_faces", [])) <= 1000
    a, b, c = response["variants"]
    assert a["semantic_lineage"] == "NOT IMPLEMENTED"
    assert b["semantic_lineage"] == c["semantic_lineage"] == "AVAILABLE_IN_STEPS"
    # B grows onto only perimeter sides, rather than every tile's neighbors.
    root_selection = set(b["steps"][0]["parameters"]["selected_faces"])
    roles = {row["id"]: row["role"] for row in b["steps"][0]["face_roles"]}
    side_selection = [key for key in b["steps"][1]["parameters"]["selected_faces"] if roles[key] == "side"]
    assert side_selection
    from cheshire_worker import mesh_from_data
    original, first = mesh_from_data(request["mesh"]), mesh_from_data(b["steps"][0]["mesh"])
    parents = {row["id"]: row["parents"][0]["id"] for row in b["steps"][0]["lineage"]["faces"]}
    for key in side_selection:
        assert not any(neighbor is not None and neighbor != parents[key] and neighbor in root_selection
                       for neighbor in original.edge_faces(tuple(first.face_vertices(key)[:2])))
    invalid = deepcopy(response)
    invalid["variants"][0]["steps"][-1]["lineage"] = {"vertices": [], "faces": []}
    with pytest.raises(ValueError, match="invented semantic lineage"):
        validate_response(invalid, request)


@real_backend
def test_complete_and_interrupted_display_use_actual_checkpoints_without_changing_input(real_study, monkeypatch):
    request, complete = real_study
    output, inserted, offsets = [], [], []
    rhino = MagicMock()
    rhino.RhinoApp.WriteLine.side_effect = output.append
    rhino.DocObjects.ObjectAttributes.side_effect = lambda: SimpleNamespace(SetUserString=MagicMock())
    eto, forms, system, drawing = [ModuleType(name) for name in ("Eto", "Eto.Forms", "System", "System.Drawing")]
    eto.Forms, system.Guid, drawing.Color = forms, SimpleNamespace(Empty=uuid4()), MagicMock()
    for name, module in (("Rhino", rhino), ("Eto", eto), ("Eto.Forms", forms), ("System", system), ("System.Drawing", drawing)):
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("cheshire_visual_launcher", ROOT / "rhino/CHESHIRE_Run.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    def display(data, offset, values):
        assert values is None
        offsets.append(offset)
        return SimpleNamespace(data=data)
    monkeypatch.setattr(launcher, "data_to_rhino_mesh", display)
    doc = MagicMock()
    doc.BeginUndoRecord.return_value, doc.Layers.Add.return_value = 1, 0
    doc.Objects.AddMesh.side_effect = lambda mesh, attrs: inserted.append((attrs.Name, mesh.data)) or uuid4()
    doc.Objects.AddTextDot.side_effect = lambda *args: uuid4()
    partial = deepcopy(complete)
    partial.update(status="PARTIAL", reason="Worker TIMEOUT; last validated operations retained.", variants=[partial["variants"][0]], attempts=[])
    candidate = partial["variants"][0]
    candidate.update(status="PARTIAL", reason=partial["reason"], steps=candidate["steps"][:3], semantic_lineage="AVAILABLE_IN_STEPS")
    candidate["mesh"] = candidate["steps"][-1]["mesh"]
    candidate.update(vertex_count=len(candidate["mesh"]["vertices"]), face_count=len(candidate["mesh"]["faces"]))
    for response in (complete, partial):
        before = deepcopy((request, response))
        validate_response(response, request)
        output.clear(); inserted.clear(); offsets.clear()
        launcher.print_steps(response)
        launcher.insert_results(doc, request, response)
        assert len(inserted) == 1 + len(response["variants"])
        assert inserted[0] == ("ORIGINAL REFERENCE", request["mesh"])
        assert [data for _, data in inserted[1:]] == [row["mesh"] for row in response["variants"]]
        assert offsets == [offsets[0] * index for index in range(1, len(inserted) + 1)]
        if response is partial:
            assert "PARTIAL" in inserted[-1][0] and any("TIMEOUT" in line for line in output)
        assert (request, response) == before
