"""Concrete Task25 risk: save/reload must retain origins and generation flow."""
from copy import deepcopy
import gzip
import json

from compas.datastructures import Mesh
from compas.geometry import Box

from cheshire.creases import make_network
from cheshire.execution import ExecutionBudget
from cheshire.fold_continuation import fold_state,save_state,load_state
from cheshire.ornament import source_history,propagate_history
from cheshire.lineage import ParentRef
from cheshire.branching import BranchSignatures
import pytest
from cheshire.crease_folding import folded_crease_once


@pytest.mark.parametrize('execution',['REFERENCE_THREE_MESHES','POINTWISE_EXISTING_STENCILS'])
def test_uninterrupted_matches_saved_state_with_later_face_stencil(tmp_path,execution):
    mesh=Mesh.from_shape(Box(2,2,2));history=source_history(mesh);signature=BranchSignatures(mesh)
    net=make_network(mesh,'flow',list(mesh.face_halfedges(0)),4,{})
    state=dict(history=history,events=[],source_cells={f:[f] for f in mesh.faces()},
        signatures=signature.faces,anchors={0:mesh.vertex_coordinates(0)},origins={},networks=[net.to_data()],
        generation=dict(absolute_cc=5,continuation_depth=0),completed_step=None,next_step=None)
    before=deepcopy(state)
    a=dict(band_hops=3,weights=dict(wf=.2,we=-.1,wp=.1,w1=-.5,w2=-.7),u_map={},execution=execution)
    b=dict(band_hops=5,weights=dict(wf=.05,w3=-.8,w4=.5),u_map={},execution=execution)
    budget=ExecutionBudget(10000,10000,None)
    first,first_state=fold_state(mesh,state,a,budget=budget)
    parents={r['id']:[ParentRef(r['source_face'],1.)] for r in first.metadata['face_sources']}
    assert first_state['history']==propagate_history(history,parents)
    signature.advance(parents,{})
    assert first_state['signatures']==signature.faces
    continuous,continuous_state=fold_state(first.mesh,first_state,b,budget=budget)
    path=tmp_path/'state.json.gz';save_state(path,first_state)
    geometry=tmp_path/'geometry.json.gz'
    data=dict(vertices={v:first.mesh.vertex_coordinates(v) for v in first.mesh.vertices()},
        faces={f:first.mesh.face_vertices(f) for f in first.mesh.faces()})
    with gzip.open(geometry,'wt',encoding='utf-8') as stream:json.dump(data,stream)
    with gzip.open(geometry,'rt',encoding='utf-8') as stream:actual=json.load(stream)
    reloaded=Mesh.from_vertices_and_faces({int(v):p for v,p in actual['vertices'].items()},
        {int(f):cycle for f,cycle in actual['faces'].items()})
    resumed,resumed_state=fold_state(reloaded,load_state(path),b,budget=budget)
    assert continuous.mesh.to_vertices_and_faces()==resumed.mesh.to_vertices_and_faces()
    assert continuous_state==resumed_state
    assert state==before
    assert resumed_state['generation']==dict(absolute_cc=7,continuation_depth=2)
    assert all(r['generation']==7 for r in resumed_state['origins'].values())
    assert resumed.networks==continuous.networks
    assert any(e.sharpness==2 for e in resumed.networks[0].edges)
    combined=resumed.metadata['combined_fold']
    if execution=='REFERENCE_THREE_MESHES':
        verified=combined['verified_sharp_operator']['later_generation_face_stencil']
        assert verified['eligible_faces']==first.mesh.number_of_faces()
        assert verified['fallback_faces']==0
    else:
        assert combined['later_face_stencil']['eligible_active_faces']>0
        assert not combined['later_face_stencil']['fallback_active_counts']


@pytest.mark.parametrize('later',[False,True])
def test_pointwise_evaluates_existing_stencils_on_same_whole_mesh(later):
    mesh=Mesh.from_shape(Box(2,2,2))
    # A nonsymmetric closed tri/quad cage exercises actual neighborhoods and
    # correspondence, without assuming generated key offsets.
    cycle=mesh.face_vertices(0);mesh.delete_face(0)
    mesh.add_face(cycle[:3]);mesh.add_face([cycle[0],cycle[2],cycle[3]])
    mesh.vertex_attributes(0,'xyz',[.31,-.72,-1.19])
    net=make_network(mesh,'flow',[next(mesh.edges())],4,{})
    budget=ExecutionBudget(10000,10000,None)
    origins=None;generation=5
    if later:
        first=folded_crease_once(mesh,(net,),dict(band_hops=3,weights={}),budget=budget,current_generation=generation)
        from cheshire.fold_continuation import cc_origins
        origins=cc_origins(mesh,first,6);mesh=first.mesh;net=first.networks[0];generation=6
    declaration=dict(band_hops=4,weights=dict(wf=.17,we=-.09,wp=.12,w1=-.6,w2=-1.1,
        w3=-.8 if later else 0.,w4=.5 if later else 0.,w6=.24,w7=-.13),
        u_map={'(3,3)':2.,'(4,4)':-1.,'(5,5)':2.5},unknown_u=.5)
    original=deepcopy(mesh.__data__)
    reference=folded_crease_once(mesh,(net,),declaration,budget=budget,current_generation=generation,origin_lineage=origins)
    compact=folded_crease_once(mesh,(net,),{**declaration,'execution':'POINTWISE_EXISTING_STENCILS'},
        budget=budget,current_generation=generation,origin_lineage=origins)
    assert list(reference.mesh.faces())==list(compact.mesh.faces())
    assert all(reference.mesh.face_vertices(f)==compact.mesh.face_vertices(f) for f in reference.mesh.faces())
    for v in reference.mesh.vertices():
        assert reference.mesh.vertex_coordinates(v)==pytest.approx(compact.mesh.vertex_coordinates(v),abs=1e-13,rel=0.)
    for a,b in zip(reference.networks,compact.networks):
        assert a.edges==b.edges and a.generation==b.generation
        assert a.path_length==pytest.approx(b.path_length,abs=1e-13,rel=0.)
    assert reference.sampling_parents==compact.sampling_parents
    assert mesh.__data__==original


def test_peak_forecast_counts_loaded_worker_once_and_still_stops_unsafe_growth(tmp_path,monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
    import generational_folding as runner
    mesh=Mesh.from_shape(Box(2,2,2))
    monkeypatch.setattr(runner,'windows_memory',lambda:dict(available_bytes=100000,combined_resident_bytes=100000))
    budget,record=runner.budget_for(mesh,tmp_path,dict(resource_bytes_per_face=5700))
    assert record['predicted_additional_bytes']==record['predicted_working_bytes']-100000
    assert record['predicted_working_bytes']>record['available_bytes']*.55
    assert budget.max_faces==sum(len(mesh.face_vertices(f)) for f in mesh.faces())
    monkeypatch.setattr(runner,'windows_memory',lambda:dict(available_bytes=100000,combined_resident_bytes=30000))
    with pytest.raises(MemoryError,match='PREDICTION_STOP'):
        runner.budget_for(mesh,tmp_path,dict(resource_bytes_per_face=5700))
