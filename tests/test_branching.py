"""Focused data/routing/path contracts; no per-recipe design assertions."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest
from cheshire.branching import (BranchRule,BranchTable,BranchingRecipe,BranchRouter,
    BranchSignatures,content_hash,run_branching)
from cheshire.ornament import OrnamentStage,source_history
from cheshire.lineage import ParentRef
from cheshire.execution import ExecutionBudget
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.weighted_doosabin import weighted_doosabin_once

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples"))
sys.path.insert(0,str(ROOT/"tools"))
from ornament_study import verified_resume,write,file_hash,digest


def test_process_identity_excludes_stale_parent_pid_and_its_descendants():
    from branching_process import born_descendants
    parents={10:1,11:10,12:11,20:10,21:20,30:10}
    births={10:100,11:110,12:120,20:90,21:130,30:None}
    assert born_descendants(10,parents,births)=={10,11,12}


def table():
    return BranchTable("split",(
        BranchRule("up",dict(role="FRAME_SIDE",event_stage="frame",depth=1,normal_axis="z",normal_min=.5),"TaperedExtrusion",dict(height_ratio=.1,fraction=.3)),
        BranchRule("rest",dict(role="FRAME_SIDE",event_stage="frame",depth=1),"quiet",{})))


def recipe():
    base=dict(id="fixture",family="test",mechanism="A box frame.",stages=[dict(id="frame",operator="InsetFrame",parameters=dict(width_ratio=.08),selector={})])
    return BranchingRecipe("fixture_branch","test","Role-aware fixture.",base,1,(table(),))


def test_branch_table_serialization_hash_and_quiet_fallback():
    a=table(); assert BranchTable.from_data(json.loads(json.dumps(a.to_data())))==a
    assert content_hash(a.to_data())==content_hash(BranchTable.from_data(a.to_data()).to_data())
    with pytest.raises(ValueError): BranchTable("bad",a.rules,"random")
    with pytest.raises(ValueError): BranchRule("bad",dict(role="INNER_CAP",event_stage="frame",face_ids=[2]),"quiet",{})


def test_role_depth_orientation_parent_operator_and_snapshot_routing(box_mesh):
    history=source_history(box_mesh)
    for row in history.values(): row.update(roles=(("frame","FRAME_SIDE"),),depth=1)
    router=BranchRouter(recipe()); stage=recipe().compile().stages[1]
    chosen=router.select(box_mesh,history,stage,box_mesh,None,[dict(stage="frame",operator="InsetFrame")])
    assert len(chosen["selected_ids"])==1
    assert box_mesh.face_normal(chosen["selected_ids"][0])[2]>.5
    assert chosen==router.select(box_mesh,history,stage,box_mesh,None,[])
    router=BranchRouter(recipe())
    for row in history.values(): row["depth"]=2
    assert router.select(box_mesh,history,stage,box_mesh,None,[])["selected_ids"]==[]
    history=source_history(box_mesh)
    for row in history.values(): row.update(roles=(("frame","INNER_CAP"),),depth=1)
    assert BranchRouter(recipe()).select(box_mesh,history,stage,box_mesh,None,[])["selected_ids"]==[]
    r=BranchRule("parent",dict(role="INNER_CAP",event_stage="frame",depth=1,parent_operator="TaperedExtrusion"),"InsetFrame",dict(width_ratio=.08))
    other=BranchingRecipe("parent","test","Parent operator check.",recipe().backbone,1,(BranchTable("other",(r,)),))
    assert BranchRouter(other).select(box_mesh,history,other.compile().stages[1],box_mesh,None,[dict(stage="frame",operator="InsetFrame")])["selected_ids"]==[]


def test_finish_none_serializes_no_automatic_finish():
    a=recipe(); restored=BranchingRecipe.from_data(json.loads(json.dumps(a.to_data())))
    assert restored==a and len(restored.compile().stages)==2 and restored.finish is None
    with pytest.raises(ValueError): BranchingRecipe("bad","t","Bad.",a.backbone,1,a.steps,"FINISH_NONE",OrnamentStage("cc","CC",dict(ratios={})))
    changed=a.to_data(); changed["backbone"]["stages"][0]["parameters"]["width_ratio"]*=2
    with pytest.raises(ValueError): BranchingRecipe.from_data(changed)


def test_signatures_append_constructive_child_roles_and_do_not_append_subdivision(box_mesh):
    tracker=BranchSignatures(box_mesh); f=next(box_mesh.faces())
    event=dict(id="e",operator="InsetFrame",parent_face=f,children=[dict(id=100,role="FRAME_SIDE"),dict(id=101,role="INNER_CAP")])
    tracker.advance({100:[ParentRef(f,1)],101:[ParentRef(f,1)]},dict(events=[event]))
    assert tracker.faces[100]=={("InsetFrame:FRAME_SIDE",):1}
    tracker.advance({200:[ParentRef(100,.25),ParentRef(101,.75)]},{})
    assert tracker.faces[200]=={("InsetFrame:FRAME_SIDE",):.25,("InsetFrame:INNER_CAP",):.75}


def test_real_cc_ds_preserve_positive_mixed_signature_paths(box_mesh):
    tracker=BranchSignatures(box_mesh); first=next(box_mesh.faces())
    tracker.faces[first]={("InsetFrame:INNER_CAP",):1}
    cc=generational_subdivide_once(box_mesh,{k:0 for k in ("wf","w1","we","w2","wp","w3","w4")},budget=ExecutionBudget(500,500))
    parents={r["id"]:[ParentRef(r["source_face"],1)] for r in cc.metadata["face_sources"]}
    tracker.advance(parents,{})
    assert sum(bool(next(iter(row))) for row in tracker.faces.values())==4
    ds=weighted_doosabin_once(cc.mesh,{},budget=ExecutionBudget(500,500))
    tracker.advance(ds.lineage.face_parents,{})
    assert any(len(row)>1 for row in tracker.faces.values())
    assert all(abs(sum(row.values())-1)<1e-12 for row in tracker.faces.values())
    assert {p for row in tracker.faces.values() for p in row}=={(),("InsetFrame:INNER_CAP",)}


def test_resume_invalidates_changed_branch_rule_or_artifact(tmp_path):
    request=dict(recipe=recipe().to_data()); write(tmp_path/"terminal.json",dict(mesh=[]))
    write(tmp_path/"summary.json",dict(status="SUCCESS",request_sha256=digest(request),artifacts={"terminal.json":file_hash(tmp_path/"terminal.json")}))
    assert verified_resume(tmp_path,request)
    other=deepcopy(request); other["recipe"]["steps"][0]["rules"][0]["when"]["normal_min"]=.8
    assert not verified_resume(tmp_path,other)
    write(tmp_path/"terminal.json",dict(mesh=[1])); assert not verified_resume(tmp_path,request)


@pytest.mark.skipif(not os.environ.get("CHESHIRE_MOLA_DLL"),reason="Explicit real HDMola DLL required")
def test_real_branching_quiet_no_finish_and_exact_repeat(box_mesh):
    a=run_branching(box_mesh,recipe(),dll_path=os.environ["CHESHIRE_MOLA_DLL"],budget=ExecutionBudget(1000,1000))
    b=run_branching(box_mesh,recipe(),dll_path=os.environ["CHESHIRE_MOLA_DLL"],budget=ExecutionBudget(1000,1000))
    assert a["status"]=="SUCCESS" and a["source_immutable"]
    assert a["mesh"].__data__==b["mesh"].__data__ and a["events"]==b["events"]
    assert a["signatures"].to_data()==b["signatures"].to_data()
    assert a["stages"][-1]["stage"]["operator"]=="TaperedExtrusion"
    assert not a["stages"][-1].get("quiet",False)
