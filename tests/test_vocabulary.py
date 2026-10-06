"""Focused live construction and deterministic frame/patch contracts."""
from copy import deepcopy
import json
import os
import pytest
from compas.datastructures import Mesh
from cheshire.vocabulary import (VocabularyStage,VocabularyRule,VocabularyTable,VocabularyRecipe,
    local_frame,routing_patches,vocabulary_event,run_vocabulary,validate_morphology_library)
from cheshire.ornament import source_history
from cheshire.branching import content_hash
from cheshire.execution import ExecutionBudget
from cheshire.validation import validate_lineage_coverage

def test_local_frame_and_outward_sign_are_repeatable(box_mesh):
    for face in box_mesh.faces():
        a=local_frame(box_mesh,face,'outward',0)
        assert a==local_frame(box_mesh,face,'outward',0)
        assert sum(v*v for v in a['T1'])==pytest.approx(1)
        assert sum(a['N'][i]*a['T1'][i] for i in range(3))==pytest.approx(0,abs=1e-12)
        assert a['outward_sign']==(-1 if box_mesh.face_centroid(face)[0]<0 else 1)
    assert any(local_frame(box_mesh,f,'vertical')['edge_fallback'] for f in box_mesh.faces())

def test_routing_patch_connected_cohorts_and_source_separation():
    mesh=Mesh.from_vertices_and_faces([[0,0,0],[1,0,0],[2,0,0],[0,1,0],[1,1,0],[2,1,0]],[[0,1,4,3],[1,2,5,4]])
    history=source_history(mesh)
    for row in history.values(): row.update(source={0:1.},roles=(('frame','FRAME_SIDE'),),depth=1)
    rule=VocabularyRule('aligned',dict(role='FRAME_SIDE',event_stage='frame',patch_mode='connected'),'DirectionalExtrusion',dict(height_ratio=.2,direction_mode='horizontal'))
    a=routing_patches(mesh,list(mesh.faces()),history,rule,1)
    assert len(a)==1 and a[0]['face_count']==2 and a==routing_patches(mesh,list(reversed(list(mesh.faces()))),history,rule,1)
    history[1]={**history[1],'source':{1:1.}}
    assert len(routing_patches(mesh,list(mesh.faces()),history,rule,1))==2

def test_vocabulary_serialization_rejects_manual_ids_and_unaccepted_operators():
    base=dict(id='fixture',family='test',mechanism='Box frame',stages=[dict(id='frame',operator='InsetFrame',parameters=dict(width_ratio=.08),selector={})])
    rule=VocabularyRule('cap',dict(role='INNER_CAP',event_stage='frame',depth=1,patch_mode='connected'),'Roof',dict(height_ratio=.2,gable_inset=.2,direction_mode='vertical'))
    recipe=VocabularyRecipe('fixture','test','Ridge on inner cap',base,1,(VocabularyTable('ridge',(rule,)),))
    assert VocabularyRecipe.from_data(json.loads(json.dumps(recipe.to_data())))==recipe
    assert content_hash(recipe.to_data())==content_hash(VocabularyRecipe.from_data(recipe.to_data()).to_data())
    with pytest.raises(ValueError): VocabularyStage('bad','LinearSplitQuad',{}, {})
    with pytest.raises(ValueError): VocabularyRule('bad',dict(role='INNER_CAP',event_stage='frame',face_ids=[1]),'quiet',{})
    with pytest.raises(ValueError): VocabularyStage('flat','DirectionalExtrusion',dict(height_ratio=.2,normal_ratio=0),{})
    changed=deepcopy(recipe.to_data()); changed['backbone']['stages'][0]['parameters']['width_ratio']=.12
    with pytest.raises(ValueError): VocabularyRecipe.from_data(changed)

def test_morphology_library_serialization_requires_actual_construction_evidence():
    entry=dict(id='ridge',source_recipe='fixture',source_stage_ids=['ridge'],required_input=dict(role='INNER_CAP'),
        operator_sequence=[dict(id='ridge',operator='Roof',parameters=dict(height_ratio=.2,direction_mode='horizontal',gable_inset=.2),selector={})],
        known_failure_boundaries=['Only eligible quads'],visual_intent='Angular ridge',lineage_contract='Constructive end/slope order',successful_geometry_sha256='a'*64)
    data=dict(version=1,entries=[entry])
    assert validate_morphology_library(data)==validate_morphology_library(json.loads(json.dumps(data)))
    with pytest.raises(ValueError): validate_morphology_library(dict(version=1,entries=[entry,entry]))
    bad=deepcopy(data); bad['entries'][0]['successful_geometry_sha256']=''
    with pytest.raises(ValueError): validate_morphology_library(bad)

@pytest.mark.skipif(not os.environ.get('CHESHIRE_MOLA_DLL'),reason='Explicit real official DLL required')
def test_old_branch_fragment_keeps_constructor_order_and_exact_geometry(box_mesh):
    from cheshire.branching import BranchRule,BranchTable,BranchingRecipe,run_branching
    base=dict(id='fixture',family='test',mechanism='Box frame',stages=[dict(id='frame',operator='InsetFrame',parameters=dict(width_ratio=.08),selector={})])
    rule=BranchRule('side',dict(role='FRAME_SIDE',event_stage='frame',depth=1),'TaperedExtrusion',dict(height_ratio=.16,fraction=.3))
    old=BranchingRecipe('fixture','test','Frame sides',base,1,(BranchTable('split',(rule,)),))
    data=old.to_data(); data.pop('finish'); data['reference_id']='test'
    new=VocabularyRecipe.from_data(data)
    a=run_branching(box_mesh,old,dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(500,500))
    b=run_vocabulary(box_mesh,new,dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(500,500))
    assert a['status']==b['status']=='SUCCESS'
    assert a['mesh'].__data__==b['mesh'].__data__ and a['events']==b['events']
    assert a['history']==b['history'] and a['signatures'].to_data()==b['signatures'].to_data()

@pytest.mark.skipif(not os.environ.get('CHESHIRE_MOLA_DLL'),reason='Explicit real official DLL required')
def test_live_reflected_constructors_roles_boundaries_and_lineage(box_mesh):
    original=deepcopy(box_mesh.__data__); f=next(box_mesh.faces()); history=source_history(box_mesh)
    for operator,parameters in [('DirectionalExtrusion',dict(height_ratio=.2,direction_mode='horizontal',normal_ratio=.5)),('Roof',dict(height_ratio=.2,gable_inset=.2,direction_mode='vertical'))]:
        stage=VocabularyStage('fixture',operator,parameters,{})
        a=vocabulary_event(box_mesh,history,stage,selected_faces=[f],dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(100,100))
        b=vocabulary_event(box_mesh,history,stage,selected_faces=[f],dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(100,100))
        assert a['mesh'].__data__==b['mesh'].__data__ and a['events']==b['events']
        assert a['mesh'].is_valid() and a['mesh'].is_manifold() and a['mesh'].is_closed()
        assert not validate_lineage_coverage(box_mesh,a['mesh'],a['lineage']) and box_mesh.__data__==original
        assert [a['mesh'].vertex_coordinates(v) for v in box_mesh.vertices()]==[box_mesh.vertex_coordinates(v) for v in box_mesh.vertices()]
        children=a['events'][0]['children']
        expected=['DIRECTIONAL_EXTRUSION_SIDE']*4+['DIRECTIONAL_EXTRUSION_CAP'] if operator=='DirectionalExtrusion' else ['RIDGE_END','RIDGE_SIDE','RIDGE_END','RIDGE_SIDE']
        assert [c['role'] for c in children]==expected
        assert operator in a['backend']['vocabulary_signatures']

@pytest.mark.skipif(not os.environ.get('CHESHIRE_MOLA_DLL'),reason='Explicit real official DLL required')
def test_real_grammar_exact_repeat_new_signatures_and_no_finish(box_mesh):
    base=dict(id='fixture',family='test',mechanism='Box frame',stages=[dict(id='frame',operator='InsetFrame',parameters=dict(width_ratio=.08),selector={})])
    plate=VocabularyRule('cap',dict(role='INNER_CAP',event_stage='frame',depth=1,patch_mode='connected'),'DirectionalExtrusion',dict(height_ratio=.12,normal_ratio=.7,direction_mode='horizontal'))
    ridge=VocabularyRule('crest',dict(role='DIRECTIONAL_EXTRUSION_CAP',event_stage='plate__cap',depth=2,patch_mode='connected'),'Roof',dict(height_ratio=.1,gable_inset=.2,direction_mode='vertical'))
    recipe=VocabularyRecipe('fixture','test','Nested plate and ridge',base,1,(VocabularyTable('plate',(plate,)),VocabularyTable('ridge',(ridge,))))
    a=run_vocabulary(box_mesh,recipe,dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(500,500))
    b=run_vocabulary(box_mesh,recipe,dll_path=os.environ['CHESHIRE_MOLA_DLL'],budget=ExecutionBudget(500,500))
    assert a['status']=='SUCCESS' and a['source_immutable'] and a['mesh'].__data__==b['mesh'].__data__
    assert a['events']==b['events'] and a['branch_tables']==b['branch_tables'] and a['signatures'].to_data()==b['signatures'].to_data()
    assert a['history']==b['history'] and a['stages']==b['stages']
    assert a['stages'][-1]['stage']['operator']=='Roof'
    assert any(any(token=='Roof:RIDGE_SIDE' for token in path) for paths in a['signatures'].faces.values() for path in paths)

@pytest.mark.skipif(not os.environ.get('CHESHIRE_MOLA_DLL'),reason='Explicit real official DLL required')
def test_bounded_nonlinear_fixture_rejects_nonmanifold_alias_without_mutation():
    from examples.vocabulary_nonlinear import construct_fixture,alias_proposal
    source,step=construct_fixture(os.environ['CHESHIRE_MOLA_DLL']); mesh=step['mesh']; before=deepcopy(mesh.__data__)
    a=alias_proposal(mesh,list(source.vertices()),step['corner_parents'],1.)
    assert a==alias_proposal(mesh,list(source.vertices()),step['corner_parents'],1.)
    assert len(a['pairs'])==2 and not a['accepted'] and not a['applied'] and not a['passes_bounded_edge_guard']
    assert a['proposed_topology']['maximum_edge_face_incidence']==4 and a['rejected_nonmanifold_edges']
    assert mesh.__data__==before and mesh.is_valid() and mesh.is_manifold()
