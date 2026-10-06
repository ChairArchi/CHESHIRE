from copy import deepcopy
from math import dist
from pathlib import Path
import sys

import pytest

from cheshire.generational_subdivision import (generational_subdivide_once, classify_child_quad,
    later_generation_face_stencil, VERTEX_DERIVED, EDGE_DERIVED, FACE_DERIVED)
from cheshire.weighted_subdivision import weighted_subdivide_once

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "rhino"))


def test_equation_four_independent_coefficients_and_unchanged_normal_extrusion():
    V,F,E1,E2=[2,3,1],[-1,5,2],[7,-2,4],[4,1,-3]
    w3,w4,wf=.6,-.3,.25
    coefficients=[(1+w3)*(1+w4)/4,(1-w3)*(1+w4)/4,(1-w4)/4,(1-w4)/4]
    expected=[sum(p[i]*weight for p,weight in zip((V,F,E1,E2),coefficients)) for i in range(3)]
    expected[2]+=wf
    actual=later_generation_face_stencil(V,F,E1,E2,[0,0,1],w3=w3,w4=w4,wf=wf)
    assert actual == pytest.approx(expected,abs=1e-14)
    assert sum(coefficients) == pytest.approx(1)


def test_origin_classes_are_immediate_generation_and_classifier_is_order_independent(box_mesh):
    first=generational_subdivide_once(box_mesh)
    assert set(row["class"] for row in first.origin_lineage.values()) == {VERTEX_DERIVED,EDGE_DERIVED,FACE_DERIVED}
    assert first.metadata["origin_classes"] == {FACE_DERIVED:6,EDGE_DERIVED:12,VERTEX_DERIVED:8}
    face=next(first.mesh.faces())
    expected,reason=classify_child_quad(first.mesh,face,first.origin_lineage,1)
    assert reason is None
    vertices=first.mesh.face_vertices(face)
    for cycle in (vertices[1:]+vertices[:1],list(reversed(vertices))):
        changed=first.mesh.copy(); changed.delete_face(face); changed.add_face(cycle,fkey=face)
        assert classify_child_quad(changed,face,first.origin_lineage,1) == (expected,None)
    second=generational_subdivide_once(first.mesh,origin_lineage=first.origin_lineage,current_generation=1)
    previous_face_id=next(v for v,row in first.origin_lineage.items() if row["class"] == FACE_DERIVED)
    assert second.origin_lineage[previous_face_id]["class"] == VERTEX_DERIVED
    assert all(row["generation"] == 2 for row in second.origin_lineage.values())
    assert all(second.mesh.vertex_attribute(v,"origin_class") == row["class"] for v,row in second.origin_lineage.items())


def test_zero_weights_exactly_preserve_legacy_geometry_over_three_generations(box_mesh):
    original=deepcopy(box_mesh.__data__)
    old,new=box_mesh,box_mesh; origins=None
    for generation in range(3):
        weights=dict(wf=.15,w1=-.8,we=-.04,w2=-.5,wp=.025)
        old=weighted_subdivide_once(old,weights,current_generation=generation).mesh
        result=generational_subdivide_once(new,{**weights,"w3":0,"w4":0},origin_lineage=origins,current_generation=generation)
        new,origins=result.mesh,result.origin_lineage
        assert {v:new.vertex_coordinates(v) for v in new.vertices()} == {v:old.vertex_coordinates(v) for v in old.vertices()}
        assert [new.face_vertices(f) for f in new.faces()] == [old.face_vertices(f) for f in old.faces()]
    assert box_mesh.__data__ == original


def test_nonzero_stencil_only_changes_face_points_and_keeps_sampling_separate(box_mesh):
    first=generational_subdivide_once(box_mesh)
    before=deepcopy(first.mesh.__data__)
    old=weighted_subdivide_once(first.mesh,dict(wf=.03,w1=-.5,we=-.02,w2=-.4,wp=.01))
    new=generational_subdivide_once(first.mesh,dict(wf=.03,w1=-.5,we=-.02,w2=-.4,wp=.01,w3=1.3,w4=.5),
        origin_lineage=first.origin_lineage,current_generation=1)
    face_points={p["id"] for p in old.metadata["points"] if p["point_class"] == "face"}
    assert any(dist(new.mesh.vertex_coordinates(v),old.mesh.vertex_coordinates(v)) > 1e-6 for v in face_points)
    assert all(new.mesh.vertex_coordinates(v) == old.mesh.vertex_coordinates(v) for v in new.mesh.vertices() if v not in face_points)
    assert new.sampling_parents == old.sampling_parents
    assert first.mesh.__data__ == before
    assert new.metadata["later_generation_face_stencil"]["eligible_faces"] == 24
    row=new.metadata["later_generation_face_stencil"]["applications"][0]
    c=row["canonical"]
    reference=later_generation_face_stencil(*(first.mesh.vertex_coordinates(c[k]) for k in ("V","F","E1","E2")),
        first.mesh.face_normal(row["face"]),w3=1.3,w4=.5,wf=.03)
    assert new.mesh.vertex_coordinates(row["point"]) == pytest.approx(reference,abs=1e-14)


def test_missing_stale_and_false_incidence_fall_back_without_guessing(box_mesh):
    first=generational_subdivide_once(box_mesh)
    legacy=weighted_subdivide_once(first.mesh).mesh
    result=generational_subdivide_once(first.mesh,dict(w3=.8,w4=.5),current_generation=1)
    diagnostic=result.metadata["later_generation_face_stencil"]
    assert diagnostic["fallback_counts"] == {"missing_origin":24}
    assert all(result.mesh.vertex_coordinates(v) == legacy.vertex_coordinates(v) for v in legacy.vertices())
    face=next(first.mesh.faces()); pattern,_=classify_child_quad(first.mesh,face,first.origin_lineage,1)
    stale=deepcopy(first.origin_lineage); stale[pattern["V"]]["generation"]=0
    assert classify_child_quad(first.mesh,face,stale,1)[1] == "origin_generation_mismatch"
    false=deepcopy(first.origin_lineage); false[pattern["E1"]]["source"]=[999,1000]
    assert classify_child_quad(first.mesh,face,false,1)[1] == "parent_edge_incidence_mismatch"
    malformed=deepcopy(first.origin_lineage); malformed[pattern["E1"]]["source"]=[[],1000]
    assert classify_child_quad(first.mesh,face,malformed,1)[1] == "parent_edge_incidence_missing"


def test_schedule_serialization_deterministic_run_and_source_immutability(box_mesh):
    import json
    from generational_study import direct_probes,run_choreography
    first=direct_probes(); second=direct_probes()
    assert json.loads(json.dumps(first)) == second
    schedule=first["P01_vertex_bias"]["schedule"]
    assert len(schedule)==5 and all(set(row)=={"wf","w1","we","w2","wp","w3","w4"} for row in schedule)
    before=deepcopy(box_mesh.__data__)
    a=run_choreography(box_mesh,schedule,generations=2)
    b=run_choreography(box_mesh,schedule,generations=2)
    assert [stage["mesh"] for stage in a["stages"]] == [stage["mesh"] for stage in b["stages"]]
    assert a["stages"][1]["ratios"] == schedule[1]
    assert box_mesh.__data__ == before


def test_rhino_generational_budget_checkpoint_keeps_immediate_origins_and_partial_display(monkeypatch):
    from uuid import uuid4
    from cheshire.execution import ExecutionBudget
    import generational_study as study
    from cheshire_worker import mesh_to_data
    from exchange import GENERATIONAL_MODE,validate_request,validate_response
    from generational_display import comparison_items
    source=study.coarse_gate()
    payload=dict(protocol=1,run_id=str(uuid4()),source=dict(document_serial=7,object_id="gate"),
        mode=GENERATIONAL_MODE,mesh=mesh_to_data(source))
    before=deepcopy(payload); saved=[]
    monkeypatch.setattr(study,"BUDGET",ExecutionBudget(50000,50000,2))
    result=study.run_generational_study(validate_request(payload),publish=lambda value:saved.append(deepcopy(value)))
    assert result["status"] == "PARTIAL" and len(result["variants"]) == 1
    assert [stage["generation"] for stage in result["variants"][0]["stages"]] == [1,2]
    assert result["first_grotesque_gate_candidate"] is None and result["design_status"] == "PARTIAL_SUCCESS"
    assert payload == before and result["carrier"]["mesh"] == payload["mesh"]
    for checkpoint in saved:
        validate_response(checkpoint,payload)
    items=comparison_items(result)
    assert [row[0] for row in items] == ["C0 SOURCE","L4 CONTROL G2 (last valid; PARTIAL)"]
    bad=deepcopy(result); bad["variants"][0]["stages"][1]["origin_lineage"][0]["generation"]=1
    with pytest.raises(ValueError,match="origin classes"):
        validate_response(bad,payload)
