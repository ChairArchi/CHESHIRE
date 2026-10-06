from copy import deepcopy
from math import cos,pi,sin
from pathlib import Path
import json
import sys

import pytest
from compas.datastructures import Mesh

from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.validation import validate_lineage_coverage
from cheshire.weighted_doosabin import (weighted_corner,weighted_doosabin_once,STANDARD,
    FACE_DERIVED,EDGE_DERIVED,VERTEX_DERIVED,_cycle)

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"rhino"))
from carrier_study import coarse_gate
from subdivision_capability import BUDGET,schedules,refinements,run_capability,validate_schedule


def test_quad_and_triangle_formulas_independently_at_every_corner():
    quad=[[2,1,-3],[6,-2,4],[-1,7,5],[3,9,-2]]
    tri=quad[:3]; a,b=.6,-.35; normal=[0,0,1]
    for points in (quad,tri):
        for i in range(len(points)):
            if len(points)==4:
                coefficients=[(2.25+2*a)/4,(.75-a)/4,.25/4,(.75-a)/4]
            else:
                coefficients=[(2+a)/3,(1-a)/6,(1-a)/6]
            expected=[sum(points[(i+j)%len(points)][axis]*weight for j,weight in enumerate(coefficients)) for axis in range(3)]
            expected[2]+=b
            assert weighted_corner(points,i,normal,w1=a,w10=b)==pytest.approx(expected,abs=1e-13)
            assert sum(coefficients)==pytest.approx(1)
    with pytest.raises(ValueError,match="only triangles/quads"):
        weighted_corner(quad+[[0,0,0]],0,normal,w1=0,w10=0)


def test_zero_weights_match_public_compas_on_quad_and_triangle_fixtures(box_mesh):
    for source in (box_mesh,Mesh.from_polyhedron(4)):
        old=deepcopy(source.__data__); mesh=source; families=None
        for generation in range(3):
            expected=mesh.subdivided(scheme="doosabin",k=1)
            a=weighted_doosabin_once(mesh,face_families=families,current_generation=generation)
            b=weighted_doosabin_once(mesh,face_families=families,current_generation=generation)
            assert a.mesh.__data__==b.mesh.__data__
            assert a.face_families==b.face_families
            assert (a.mesh.number_of_vertices(),a.mesh.number_of_edges(),a.mesh.number_of_faces())==(expected.number_of_vertices(),expected.number_of_edges(),expected.number_of_faces())
            for v in expected.vertices():
                assert a.mesh.vertex_coordinates(v)==pytest.approx(expected.vertex_coordinates(v),abs=1e-12)
            assert {_cycle(a.mesh.face_vertices(f)) for f in a.mesh.faces()}=={_cycle(expected.face_vertices(f)) for f in expected.faces()}
            for f in mesh.faces():
                p=mesh.face_coordinates(f)
                if len(p) in (3,4):
                    for i,v in enumerate(expected.face_vertices(f)):
                        assert weighted_corner(p,i,mesh.face_normal(f),w1=0,w10=0)==pytest.approx(expected.vertex_coordinates(v),abs=1e-12)
            mesh,families=a.mesh,a.face_families
        assert source.__data__==old


def test_topological_families_lineage_and_source_immutability(box_mesh):
    old=deepcopy(box_mesh.__data__)
    first=weighted_doosabin_once(box_mesh,{"w1_face":.3,"w10_face":.2})
    assert first.metadata["family_counts"]=={FACE_DERIVED:6,EDGE_DERIVED:12,VERTEX_DERIVED:8}
    assert validate_lineage_coverage(box_mesh,first.mesh,first.lineage)==[]
    for f,origin in first.face_families.items():
        assert first.mesh.face_attribute(f,"origin_class")==origin["class"]
        assert origin["generation"]==1
        assert len(first.lineage.face_parents[f])=={FACE_DERIVED:1,EDGE_DERIVED:2,VERTEX_DERIVED:3}[origin["class"]]
    weights={**STANDARD,"w1_edge":.6,"w10_vertex":.25}
    second=weighted_doosabin_once(first.mesh,weights,face_families=first.face_families,current_generation=1)
    assert all(p["requested"]["w1"]==weights["w1_"+p["input_family"].split("_")[0].lower()] for p in second.metadata["points"])
    assert box_mesh.__data__==old
    with pytest.raises(ValueError,match="immediate-generation"):
        weighted_doosabin_once(first.mesh,face_families=first.face_families,current_generation=0)


def test_unsupported_pentagons_keep_actual_standard_placement():
    vertices=[[cos(2*pi*i/5),sin(2*pi*i/5),0] for i in range(5)]+[[0,0,1],[0,0,-1]]
    source=Mesh.from_vertices_and_faces(vertices,[[i,(i+1)%5,5] for i in range(5)]+[[(i+1)%5,i,6] for i in range(5)])
    first=weighted_doosabin_once(source)
    expected=first.mesh.subdivided(scheme="doosabin",k=1)
    weights={key:.3 for key in STANDARD}
    second=weighted_doosabin_once(first.mesh,weights,face_families=first.face_families,current_generation=1)
    assert second.metadata["fallback_groups"]==[dict(valence=5,family=VERTEX_DERIVED,count=2)]
    assert second.metadata["fallback_faces"]==2
    for p in second.metadata["points"]:
        if not p["weighted_supported"]:
            assert second.mesh.vertex_coordinates(p["id"])==expected.vertex_coordinates(p["id"])
            assert p["effective"]==dict(w1=0.,w10=0.)
    assert sum(len(second.mesh.face_vertices(f))==5 for f in second.mesh.faces())==2


def test_monitor_records_drift_without_intervention_and_has_no_gate_score():
    source=coarse_gate([0,0,0]); before=deepcopy(source.__data__)
    monitor=GateIntegrityMonitor(source); warped=source.copy()
    for v in warped.vertices():
        x,y,z=warped.vertex_coordinates(v); warped.vertex_attributes(v,"xyz",[x*2,y*3,z-1000])
    data=monitor.evaluate(warped,{v:v for v in source.vertices()},generation=4)
    assert data["opening_normalized"]["width"]==2
    assert data["dimensions_drift_percent"]["width"]==100
    assert data["support_base_displacement"]["mean"]==-1000
    assert data["topology"]==dict(components=1,boundary_edges=0,is_manifold=True,is_closed=True)
    assert data["missing_source_anchor_ids"]==[]
    assert source.__data__==before
    assert warped.vertex_coordinates(0)[2]==source.vertex_coordinates(0)[2]-1000
    assert not any(key in data for key in ("score","status","budget","admissible"))


def test_explicit_schedules_local_budget_and_deterministic_checkpoints():
    cases=schedules(); assert len(cases)==12
    assert len(refinements())==4
    for recipe in {**cases,**refinements()}.values():
        validate_schedule(json.loads(json.dumps(recipe["schedule"])))
    with pytest.raises(ValueError,match="Six explicit"):
        validate_schedule([STANDARD]*5)
    source=coarse_gate([0,0,0]); events=[]
    a=run_capability(source,cases["F10_edge_frame_vertex_peaks"]["schedule"],generations=2,
        publish=lambda mesh,stage:events.append((deepcopy(mesh.__data__),stage["monitor"])))
    other=[]
    b=run_capability(source,cases["F10_edge_frame_vertex_peaks"]["schedule"],generations=2,
        publish=lambda mesh,stage:other.append((deepcopy(mesh.__data__),stage["monitor"])))
    assert a["status"]==b["status"]=="SUCCESS" and events==other
    assert BUDGET.max_faces==BUDGET.max_vertices==120000 and BUDGET.max_generation==6
    first=weighted_doosabin_once(source)
    with pytest.raises(ValueError,match="blocked"):
        weighted_doosabin_once(first.mesh,budget=ExecutionBudget(100,100))
    assert weighted_doosabin_once(first.mesh,budget=BUDGET).mesh.number_of_faces()==354


def test_handoff_prefix_preserves_exact_c11_and_ds_reseeds_faces():
    from generational_study import run_choreography,choreographies,BEST_SCHEDULE
    from cheshire_worker import mesh_to_data
    source=coarse_gate([0,0,0]); events=[]
    legacy=run_choreography(source,choreographies()[BEST_SCHEDULE]["schedule"],generations=2)
    result=run_capability(source,schedules()["F10_edge_frame_vertex_peaks"]["schedule"],generations=3,cc_prefix=2,
        publish=lambda mesh,stage:events.append((mesh_to_data(mesh),stage)))
    assert result["status"]=="SUCCESS"
    assert [data for data,_ in events[:2]]==[s["mesh"] for s in legacy["stages"]]
    assert events[2][1]["metadata"]["input_family_counts"]=={"SOURCE_FACE":352}
    assert events[2][1]["monitor"]["missing_source_anchor_ids"]==[]
    assert events[2][1]["monitor"]["tracked_vertex_count"]<events[2][1]["monitor"]["total_vertex_count"]
