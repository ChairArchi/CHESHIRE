"""New Task26 risks: connected matched joint, reflection and resume."""
from pathlib import Path
import pytest
from cheshire.progressive_gates import gate_input,symmetry,advance_gate,restore_gate,physical_support
from cheshire.fold_continuation import fold_state,save_state,load_state
from cheshire.execution import ExecutionBudget


def test_matched_section_has_one_closed_joint_and_new_part_identity():
    rect,a=gate_input('RECT');round_,b=gate_input('ROUND')
    assert list(rect.faces())==list(round_.faces())
    assert all(rect.face_vertices(f)==round_.face_vertices(f) for f in rect.faces())
    assert rect.is_connected() and rect.is_manifold() and rect.is_closed()
    assert round_.is_connected() and round_.is_manifold() and round_.is_closed()
    assert a['gate']['parts']==b['gate']['parts']
    assert len(set(a['gate']['parts'].values()))==10
    assert symmetry(rect,a)['max_coordinate_residual']<1e-10
    assert symmetry(round_,b)['oriented_face_failures']==0
    assert any(rect.vertex_coordinates(v)!=round_.vertex_coordinates(v) for v in rect.vertices())


def test_material_region_and_reflected_normals_survive_saved_continuation(tmp_path):
    mesh,state=gate_input('ROUND');budget=ExecutionBudget(10000,10000,None)
    d=dict(weights=dict(wf=24,we=-18,wp=12,w1=-1.3,w2=-2.1),execution='POINTWISE_EXISTING_STENCILS')
    support=physical_support(mesh,state,dict(kind='UPPER',quiet_below=400,transition=900))
    first,s=fold_state(mesh,state,d,budget=budget,point_support=support);s=advance_gate(mesh,first,state,s)
    assert symmetry(first.mesh,s)['max_coordinate_residual']<1e-9
    assert symmetry(first.mesh,s)['oriented_face_failures']==0
    save_state(tmp_path/'state.gz',s);actual=restore_gate(load_state(tmp_path/'state.gz'))
    assert actual==s
    later=dict(weights=dict(w3=-.9,w4=.5),execution='POINTWISE_EXISTING_STENCILS')
    rule=dict(kind='DISTRIBUTED',zones=[[1550,1400,450,600],[0,3050,1000,500]])
    a,sa=fold_state(first.mesh,s,later,budget=budget,point_support=physical_support(first.mesh,s,rule))
    b,sb=fold_state(first.mesh,actual,later,budget=budget,point_support=physical_support(first.mesh,actual,rule))
    sa=advance_gate(first.mesh,a,s,sa);sb=advance_gate(first.mesh,b,actual,sb)
    assert a.mesh.to_vertices_and_faces()==b.mesh.to_vertices_and_faces()
    assert sa==sb
    assert symmetry(a.mesh,sa)['max_coordinate_residual']<1e-9


def test_explicit_support_rejects_unknown_ids_and_out_of_range():
    mesh,s=gate_input();d=dict(weights=dict(wf=1),execution='POINTWISE_EXISTING_STENCILS')
    with pytest.raises(ValueError,match='Explicit point support'):
        fold_state(mesh,s,d,budget=ExecutionBudget(1000,1000,None),point_support={v:2 for v in mesh.vertices()})


def test_actual_paired_route_metadata_and_edges_reflect_after_reload(tmp_path):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
    from progressive_gates import add_routes,correct_early_route_metadata
    mesh,s=gate_input('ROUND');budget=ExecutionBudget(5000,5000,None)
    for _ in range(3):
        result,t=fold_state(mesh,s,dict(weights={}),budget=budget)
        t=advance_gate(mesh,result,s,t);mesh,s=result.mesh,t
    report=add_routes(mesh,s,'PAIRED');assert report['reflected_edge_symmetric_difference']==0
    left,right=s['networks'];vp=s['gate']['vertex_pair']
    assert right['seed_rule']['junction_xz'][0]==-left['seed_rule']['junction_xz'][0]
    assert right['routing']['semantic_seed_vertices']==[vp[v] for v in left['routing']['semantic_seed_vertices']]
    save_state(tmp_path/'routes.gz',s);actual=restore_gate(load_state(tmp_path/'routes.gz'))
    assert actual['networks']==s['networks']
    # Explicitly repair preserved early trial's aliased birth metadata; no edge
    # graph, coordinates or sharpness changes are allowed by this narrow repair.
    edges=right['edges'][:]
    right['seed_rule']['junction_xz']=left['seed_rule']['junction_xz'][:]
    right['seed_rule']['arm_targets']=left['seed_rule']['arm_targets'][:]
    right['routing']['semantic_seed_vertices']=left['routing']['semantic_seed_vertices'][:]
    correct_early_route_metadata(s)
    assert right['edges']==edges
    assert right['routing']['semantic_seed_vertices']==[vp[v] for v in left['routing']['semantic_seed_vertices']]


def test_measured_total_forecast_keeps_headroom_guard(tmp_path,monkeypatch):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
    import generational_folding as runner
    mesh,_=gate_input()
    monkeypatch.setattr(runner,'windows_memory',lambda:dict(available_bytes=10000,combined_resident_bytes=500))
    _,forecast=runner.budget_for(mesh,tmp_path,{},predicted_total_bytes=4000)
    assert forecast['predicted_additional_bytes']==3500
    with pytest.raises(MemoryError,match='PREDICTION_STOP'):
        runner.budget_for(mesh,tmp_path,{},predicted_total_bytes=7000)


def test_same_level_calibration_refuses_other_resolution_before_operator(tmp_path):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
    import progressive_gates as runner
    runner.initialize(tmp_path)
    original=runner.file_hash(tmp_path/'inputs/INPUT_RECT/geometry.json.gz')
    runner.write(tmp_path/'analysis/resource_calibration.json',dict(exact_output_faces=999,measurements=[]))
    recipe=runner.read(tmp_path/'recipes/RECT_EARLY_G1.json');recipe['use_task26_calibration']=True
    runner.write(tmp_path/'recipes/RECT_EARLY_G1.json',recipe)
    with pytest.raises(ValueError,match='Exact-level memory calibration'):
        runner.run_one(tmp_path,'RECT_EARLY_G1')
    assert runner.file_hash(tmp_path/'inputs/INPUT_RECT/geometry.json.gz')==original
