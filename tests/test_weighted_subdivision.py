from copy import deepcopy
from math import dist
from pathlib import Path
import sys

import pytest
from cheshire.execution import ExecutionBudget
from cheshire.surface import catmull_clark_once
from cheshire.weighted_subdivision import weighted_subdivide_once

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rhino"))
from weighted_study import generation_weights, run_candidate, SCHEDULES


def test_closed_standard_control_exact_public_compas(box_mesh):
    actual = weighted_subdivide_once(box_mesh).mesh
    expected = box_mesh.subdivided(scheme="catmullclark", k=1)
    assert list(actual.vertices()) == list(expected.vertices())
    assert list(actual.faces()) == list(expected.faces())
    assert all(actual.face_vertices(f) == expected.face_vertices(f) for f in actual.faces())
    assert max(dist(actual.vertex_coordinates(v), expected.vertex_coordinates(v)) for v in actual.vertices()) < 1e-12


def test_open_boundary_policy_matches_conservative_control(open_mesh):
    actual = weighted_subdivide_once(open_mesh, dict(w1=-2, we=5, w2=-2, wp=5)).mesh
    expected = catmull_clark_once(open_mesh).mesh
    assert actual.__data__["vertex"] == expected.__data__["vertex"]
    free = open_mesh.subdivided(scheme="catmullclark", k=1)
    assert any(dist(actual.vertex_coordinates(v), free.vertex_coordinates(v)) > 0 for v in open_mesh.vertices())
    assert all(actual.vertex_coordinates(v) == open_mesh.vertex_coordinates(v) for v in open_mesh.vertices())


def test_weighted_placements_reproducible_immutable_and_separate_associations(box_mesh):
    original = deepcopy(box_mesh.__data__)
    first = weighted_subdivide_once(box_mesh, dict(wf=.2, w1=-1.2, we=-.1, w2=-1.1, wp=.05))
    second = weighted_subdivide_once(box_mesh, dict(wf=.2, w1=-1.2, we=-.1, w2=-1.1, wp=.05))
    assert first.mesh.__data__ == second.mesh.__data__
    assert first.metadata["points"] == second.metadata["points"]
    assert box_mesh.__data__ == original
    assert {p["point_class"] for p in first.metadata["points"]} == {"face", "edge", "corner"}
    assert all(sum(w for _, w in refs) == pytest.approx(1) and all(w > 0 for _, w in refs) for refs in first.sampling_parents.values())
    assert first.metadata["semantic_lineage"] == "NOT IMPLEMENTED"


def test_budget_blocks_before_backend(box_mesh, monkeypatch):
    monkeypatch.setattr(type(box_mesh), "subdivided", lambda *a, **kw: pytest.fail("Backend called over budget"))
    with pytest.raises(ValueError, match="blocked"):
        weighted_subdivide_once(box_mesh, budget=ExecutionBudget(23, 26))
    with pytest.raises(ValueError, match="Generation budget"):
        weighted_subdivide_once(box_mesh, budget=ExecutionBudget(50, 50, 1), current_generation=1)


def test_real_multigeneration_schedule_and_source_field_reproduction(box_mesh):
    schedule = SCHEDULES["ribs"]
    assert generation_weights(schedule, 1) != generation_weights(schedule, 2)
    assert generation_weights(schedule, 3) == generation_weights(schedule, 6)
    first = run_candidate(box_mesh, study="F", schedule=schedule, generations=3)
    second = run_candidate(box_mesh, study="F", schedule=schedule, generations=3)
    assert first["status"] == second["status"] == "SUCCESS"
    assert [s["face_count"] for s in first["stages"]] == [24, 96, 384]
    assert [s["mesh"] for s in first["stages"]] == [s["mesh"] for s in second["stages"]]
    assert first["stages"][1]["drivers"] == second["stages"][1]["drivers"]
    assert first["stages"][1]["ratios"] == schedule[1]
    assert all(0 <= r["value"] <= 1 for s in first["stages"] for r in s["source_z"])


def test_real_isolated_worker_protocol_and_rejection(tmp_path, box_mesh):
    import subprocess
    from uuid import uuid4
    from cheshire_worker import mesh_to_data
    from exchange import WEIGHTED_MODE, read_json, write_json_atomic, validate_response
    from worker_process import worker_launch_options
    root = Path(__file__).resolve().parents[1]
    request = dict(protocol=1, run_id=str(uuid4()), mode=WEIGHTED_MODE,
        source=dict(document_serial=0, object_id="weighted-control"), mesh=mesh_to_data(box_mesh))
    write_json_atomic(tmp_path / "request.json", request)
    process = subprocess.run(**worker_launch_options(root,tmp_path / "request.json",tmp_path / "response.json"), capture_output=True,text=True,timeout=60)
    assert process.returncode == 0, process.stderr
    result = validate_response(read_json(tmp_path / "response.json"),request)
    assert result["status"] == "SUCCESS" and [v["id"] for v in result["variants"]] == list("SUF")
    assert all(v["stages"][-1]["face_count"] == 96 for v in result["variants"])
    broken = deepcopy(result)
    broken["variants"][0]["stages"][0]["sampling_parents"][0]["parents"][0]["weight"] = -1
    with pytest.raises(ValueError,match="positive"):
        validate_response(broken,request)


def test_partial_host_display_uses_actual_checkpoints(box_mesh, monkeypatch):
    """Mock insertion only; explicitly not an actual Rhino host check."""
    import importlib.util
    from types import ModuleType, SimpleNamespace
    from unittest.mock import MagicMock
    from uuid import uuid4
    from cheshire_worker import mesh_to_data
    from exchange import WEIGHTED_MODE, validate_response
    from weighted_study import run_weighted_study
    root=Path(__file__).resolve().parents[1]
    request=dict(protocol=1,run_id=str(uuid4()),mode=WEIGHTED_MODE,
        source=dict(document_serial=0,object_id="mock-control"),mesh=mesh_to_data(box_mesh))
    result=run_weighted_study(request)
    result["variants"]=result["variants"][:1]
    result["variants"][0]["stages"]=result["variants"][0]["stages"][:1]
    result["variants"][0]["status"]="PARTIAL"
    result["status"]="PARTIAL"
    result["reason"]="Worker TIMEOUT; completed checkpoint retained."
    validate_response(result,request)
    before=deepcopy((request,result))
    rhino=MagicMock()
    rhino.DocObjects.ObjectAttributes.side_effect=lambda: SimpleNamespace(SetUserString=MagicMock())
    eto,forms,system,drawing=[ModuleType(n) for n in ("Eto","Eto.Forms","System","System.Drawing")]
    eto.Forms= forms
    system.Guid=SimpleNamespace(Empty=uuid4())
    drawing.Color=MagicMock()
    for name,module in (("Rhino",rhino),("Eto",eto),("Eto.Forms",forms),("System",system),("System.Drawing",drawing)):
        monkeypatch.setitem(sys.modules,name,module)
    spec=importlib.util.spec_from_file_location("cheshire_weighted_launcher",root / "rhino/CHESHIRE_Run.py")
    launcher=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    monkeypatch.setattr(launcher,"data_to_rhino_mesh",lambda data,offset,values: SimpleNamespace(data=data))
    doc=MagicMock()
    doc.BeginUndoRecord.return_value,doc.Layers.Add.return_value=1,0
    inserted=[]
    doc.Objects.AddMesh.side_effect=lambda mesh,attrs: inserted.append((attrs.Name,mesh.data)) or uuid4()
    doc.Objects.AddTextDot.side_effect=lambda *args: uuid4()
    launcher.print_steps(result)
    launcher.insert_results(doc,request,result)
    assert len(inserted)==2 and inserted[0][1]==request["mesh"]
    assert "PARTIAL" in inserted[1][0] and inserted[1][1]==result["variants"][0]["stages"][0]["mesh"]
    assert before==(request,result)
