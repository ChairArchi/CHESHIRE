"""Focused grammar/lineage checks, plus small real Mola fixtures when configured."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest
from compas.datastructures import Mesh
from cheshire.execution import ExecutionBudget
from cheshire.lineage import ParentRef
from cheshire.ornament import (OrnamentRecipe, OrnamentStage, source_history, propagate_history,
    topology_event, select_event_faces, depth_diagnostics, run_ornament)

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples")); sys.path.insert(0,str(ROOT/"tools"))
from ornament_study import digest, verified_resume, write, file_hash
from ornament_process import descendants

def test_recipe_serialization_and_no_manual_selection():
    stage=OrnamentStage("frame","InsetFrame",dict(width_ratio=.1),dict(z_min=.1))
    recipe=OrnamentRecipe("small","C","A nested test.",(stage,))
    assert OrnamentRecipe.from_data(json.loads(json.dumps(recipe.to_data())))==recipe
    for selector in ({"face_ids":[12]},{"random_seed":2}):
        with pytest.raises(ValueError): OrnamentStage("bad","InsetFrame",dict(width_ratio=.1),selector)
    with pytest.raises(ValueError): OrnamentStage("bad","InsetFrame",dict(selected_ids=[12]),{})

def test_mixed_parent_ancestry_does_not_invent_common_cap(box_mesh):
    history=source_history(box_mesh); keys=list(history)[:2]
    history[keys[0]].update(events=("first:1",),roles=(("first","INNER_CAP"),),depth=1)
    child=propagate_history(history,{99:[ParentRef(keys[0],.5),ParentRef(keys[1],.5)]})[99]
    assert child["depth"]==1 and child["roles"]==()
    assert child["events"]==("first:1",) and child["source"]=={keys[0]:.5,keys[1]:.5}
    next_child=propagate_history({99:child},{100:[ParentRef(99,1)]})[100]
    assert next_child["depth"]==1 and next_child["operator_depth"]==2

def test_selector_determinism_and_source_immutability(box_mesh):
    before=deepcopy(box_mesh.__data__); history=source_history(box_mesh)
    selector=dict(z_min=0,z_max=1,normal_y_min=.5)
    a=select_event_faces(box_mesh,history,selector,box_mesh)
    assert a==select_event_faces(box_mesh,history,selector,box_mesh)
    assert len(a["selected_ids"])==2 and box_mesh.__data__==before

def test_depth_is_event_ancestry_not_subdivision_count(box_mesh):
    history=source_history(box_mesh)
    for i in range(3): history=propagate_history(history,{f:[ParentRef(f,1)] for f in history})
    assert depth_diagnostics(history,[])["maximum"]==0
    from ornament_verify import nested_components
    graph=[dict(id="a",parent_event_ids=[]),dict(id="b",parent_event_ids=[]),
        dict(id="nested",parent_event_ids=["a","b"])]
    counts=nested_components(graph)
    assert counts["nested_root_count"]==2 and counts["independent_nested_event_components"]==1

def test_resume_requires_matching_request_and_all_artifact_hashes(tmp_path):
    request=dict(recipe="r",operator_version="v1"); write(tmp_path/"terminal.json",dict(mesh=[]))
    write(tmp_path/"summary.json",dict(status="SUCCESS",request_sha256=digest(request),artifacts={"terminal.json":file_hash(tmp_path/"terminal.json")}))
    assert verified_resume(tmp_path,request)
    assert not verified_resume(tmp_path,dict(recipe="r",operator_version="v2"))
    write(tmp_path/"terminal.json",dict(mesh=[1]))
    assert not verified_resume(tmp_path,request)

def test_process_guard_includes_venv_redirector_grandchild():
    assert descendants(10,{10:1,11:10,12:11,13:12,20:1})=={10,11,12,13}

@pytest.mark.skipif(not os.environ.get("CHESHIRE_MOLA_DLL"),reason="Optional explicit real HDMola DLL required")
def test_real_nonplanar_event_order_roles_depth_repeat_and_closed_source(box_mesh):
    dll=os.environ["CHESHIRE_MOLA_DLL"]
    mesh=Mesh.from_vertices_and_faces([[0,0,0],[1,0,.12],[1,1,0],[0,1,-.08]],[[0,1,2,3]])
    before=deepcopy(mesh.__data__)
    frame=OrnamentStage("first","InsetFrame",dict(width_ratio=.1),{})
    first=topology_event(mesh,source_history(mesh),frame,selected_faces=[0],dll_path=dll,budget=ExecutionBudget(200,200))
    repeat=topology_event(mesh,source_history(mesh),frame,selected_faces=[0],dll_path=dll,budget=ExecutionBudget(200,200))
    assert first["mesh"].__data__==repeat["mesh"].__data__ and mesh.__data__==before
    roles=[c["role"] for c in first["events"][0]["children"]]
    assert roles==["FRAME_SIDE"]*4+["INNER_CAP"]
    cap=first["events"][0]["children"][-1]["id"]
    taper=OrnamentStage("second","TaperedExtrusion",dict(height_ratio=.12,fraction=.3),dict(role="INNER_CAP",event_stage="first"))
    second=topology_event(first["mesh"],first["history"],taper,selected_faces=[cap],dll_path=dll,budget=ExecutionBudget(200,200),stage_index=2)
    info=depth_diagnostics(second["history"],first["events"]+second["events"])
    assert info["maximum"]==2 and info["independent_nested_trees"]==1 and info["source_regions_at_least"]["2"]==[0]
    recipe=OrnamentRecipe("fixture","C","Frame inside a closed box.",(frame,))
    a=run_ornament(box_mesh,recipe,dll_path=dll,budget=ExecutionBudget(200,200))
    b=run_ornament(box_mesh,recipe,dll_path=dll,budget=ExecutionBudget(200,200))
    assert a["status"]=="SUCCESS" and a["mesh"].is_closed() and a["mesh"].__data__==b["mesh"].__data__
