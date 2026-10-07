"""Task27 connected ports, real feedback, frozen control and exact resume."""
from copy import deepcopy
import pytest
from cheshire.dynamic_sections import definition,gate,measure,map_rules,step,restore,current_face_area
from cheshire.progressive_gates import symmetry
from cheshire.fold_continuation import save_state,load_state
from cheshire.execution import ExecutionBudget
from cheshire.creases import crease_subdivide_once

CONFIG=dict(offset_ratio=.08,face_gain=1.,edge_gain=1.)
BUDGET=ExecutionBudget(20000,20000,None)


def test_profiles_are_actual_connected_ports_with_matched_topology():
    control,cs=gate(definition(False));profile,ps=gate(definition(True))
    assert control.is_closed() and profile.is_closed() and profile.is_connected() and profile.is_manifold()
    assert list(control.faces())==list(profile.faces())
    assert all(control.face_vertices(f)==profile.face_vertices(f) for f in control.faces())
    d=measure(profile,ps)['sections']['COLUMN_L']
    assert [r['width'] for r in d]==pytest.approx([900,1050,900,560,1040,340,1200,1200])
    for side in ('L','R'):
        for v in ps['section']['station_vertices'][side][-1]:
            assert {'COLUMN_'+side,'LINTEL'}<=set(ps['gate']['parts'][f] for f in profile.vertex_faces(v))
    assert symmetry(profile,ps)['oriented_face_failures']==0
    assert symmetry(profile,ps)['max_coordinate_residual']<1e-9


def test_control_is_existing_crease_inactive_standard_cc():
    mesh,state=gate(definition(True))
    expected=crease_subdivide_once(mesh,(),budget=BUDGET).mesh
    actual,*_=step(mesh,state,'PROFILE_CC',CONFIG,BUDGET)
    assert actual.mesh.to_vertices_and_faces()==expected.to_vertices_and_faces()


@pytest.mark.parametrize('config',[CONFIG,{**CONFIG,'face_gain':3.},{**CONFIG,'face_gain':3.,'curvature_gain':.65}])
def test_dynamic_rereads_changed_geometry_and_static_freezes_g0(config):
    mesh,state=gate(definition(True));first,s,d,r,_=step(mesh,state,'PROFILE_DYNAMIC',config,BUDGET)
    static,t,*_=step(mesh,state,'PROFILE_STATIC',config,BUDGET)
    assert first.mesh.to_vertices_and_faces()==static.mesh.to_vertices_and_faces()
    second,s2,d2,r2,_=step(first.mesh,s,'PROFILE_DYNAMIC',config,BUDGET)
    frozen,t2,dm,rm,_=step(static.mesh,t,'PROFILE_STATIC',config,BUDGET)
    assert dm is None and rm==t['section']['frozen_rules']
    assert d2['generation']==1 and d2['sections']['COLUMN_L'][5]['width']!=d['sections']['COLUMN_L'][5]['width']
    assert second.mesh.to_vertices_and_faces()!=frozen.mesh.to_vertices_and_faces()
    assert symmetry(second.mesh,s2)['oriented_face_failures']==0
    assert symmetry(second.mesh,s2)['max_coordinate_residual']<1e-8


def test_measuring_actual_altered_neck_changes_rules_without_label_changes():
    mesh,state=gate(definition(True));before=measure(mesh,state);original=map_rules(before,CONFIG)
    for side in ('L','R'):
        for v in state['section']['station_vertices'][side][5]:
            p=mesh.vertex_coordinates(v)
            # Alter actual depth rather than moving a label/station definition.
            p[1]=-18.533447265625+(p[1]+18.533447265625)*1.4;mesh.vertex_attributes(v,'xyz',p)
    after=measure(mesh,state);modified=map_rules(after,CONFIG)
    assert before['sections']['COLUMN_L'][5]['depth']!=after['sections']['COLUMN_L'][5]['depth']
    assert any(original[f]!=modified[f] for f in mesh.faces())


@pytest.mark.parametrize('config',[CONFIG,{**CONFIG,'face_gain':3.,'curvature_gain':.65}])
def test_saved_resume_preserves_measurement_rules_geometry_and_symmetry(tmp_path,config):
    mesh,state=gate(definition(True));r,s,*_=step(mesh,state,'PROFILE_DYNAMIC',config,BUDGET)
    save_state(tmp_path/'state.gz',s);actual=restore(load_state(tmp_path/'state.gz'))
    assert actual==s
    a,sa,da,wa,_=step(r.mesh,s,'PROFILE_DYNAMIC',config,BUDGET)
    b,sb,db,wb,_=step(r.mesh,actual,'PROFILE_DYNAMIC',config,BUDGET)
    assert a.mesh.to_vertices_and_faces()==b.mesh.to_vertices_and_faces()
    assert sa==sb and da==db and wa==wb


def test_descriptor_mapping_reflects_parts_and_normals():
    mesh,state=gate(definition(True));d=measure(mesh,state);rules=map_rules(d,CONFIG)
    for f,g in state['gate']['face_pair'].items():
        assert rules[f]==pytest.approx(rules[g],abs=1e-11)
        assert d['faces'][f]['centroid'][0]+d['faces'][g]['centroid'][0]==pytest.approx(2*-400.036865234375)
        assert d['faces'][f]['normal'][0]==pytest.approx(-d['faces'][g]['normal'][0],abs=1e-11)


def test_folded_face_area_is_cycle_and_reflection_invariant():
    # Opposing centroid-fan triangle normals expose signed-reference area.
    points=[[0,0,0],[2,0,1],[.2,.1,-.8],[0,2,.5]]
    expected=current_face_area(points)
    for k in range(4):
        cycle=points[k:]+points[:k]
        assert current_face_area(cycle)==pytest.approx(expected,abs=1e-12)
        reflected=[[-p[0],p[1],p[2]] for p in reversed(cycle)]
        assert current_face_area(reflected)==pytest.approx(expected,abs=1e-12)


def test_actual_folded_g3_geometry_and_g4_rules_preserve_symmetry():
    config={**CONFIG,'face_gain':3.,'curvature_gain':.65}
    mesh,state=gate(definition(True))
    for g in range(1,4):
        r,state,*_=step(mesh,state,'PROFILE_DYNAMIC',config,BUDGET);mesh=r.mesh
        diag=symmetry(mesh,state)
        assert diag['oriented_face_failures']==0
        assert diag['max_coordinate_residual']<1e-8
    descriptors=measure(mesh,state);rules=map_rules(descriptors,config)
    for f,pair in state['gate']['face_pair'].items():
        assert descriptors['faces'][f]['h']==pytest.approx(descriptors['faces'][pair]['h'],abs=1e-9)
        assert rules[f]==pytest.approx(rules[pair],abs=1e-9)
