from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box

from cheshire.artifact_root import ArtifactRoot
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.sharp_subdivision import (equation7,compile_schedule,equation10,equation11,
    topology_motifs,motif_values,validate_motif_map,sharp_subdivide_once,source_graph_distance,
    inherit_scalar,intrinsic_overrides,normal_variation_values)

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('a,b,q,expected',[(.3,.2,1,[.3,.5,.7]),(.1,-.05,2,[.1,.05,-.1]),(-1,.125,3,[-1,-.875,0.])])
def test_eq7_independent_first_three_values(a,b,q,expected):
    assert [equation7(i,a,b,q) for i in (1,2,3)]==pytest.approx(expected)


def test_schedule_exact_horizon_and_serialized_parameter_identity():
    spec=dict(w6=dict(mode='EQ7_TREND',a=.04,b=-.005,q=2),w7=dict(mode='DISCRETE',values=[0,.1,-.1]))
    data=compile_schedule(spec,3)
    assert json.loads(json.dumps(data))==data and data['rows'][2]['w6']==pytest.approx(.02)
    assert next(w for w in data['weights'] if w['name']=='w6')['a']==.04
    with pytest.raises(ValueError): compile_schedule(spec,4)
    with pytest.raises(ValueError): equation7(0,.1,.2,1)
    with pytest.raises(ValueError): equation7(1,.1,.2,0)
    with pytest.raises(ValueError): equation7(1,float('nan'),0,1)


def test_literal_eq10_sign_and_unnormalized_asymmetric_corner_oracle():
    corners=[[0,0,0],[4,0,0],[4,2,0],[0,2,0]]
    assert equation10([2,1,1],corners,[1,0,0,0],.25)==[1.5,.75,.75]
    assert equation10([2,1,1],corners,[-1,0,0,0],.25)==[2.5,1.25,1.25]
    # Two active corners double the vertical sum, rather than averaging u.
    assert equation10([2,1,1],corners,[1,1,0,0],.25)==[2,.5,.5]
    with pytest.raises(ValueError): equation10([2,1,1],corners,[1],.25)


def test_literal_eq11_independent_unequal_endpoint_oracle():
    assert equation11([1,.5,.25],[0,0,0],[2,0,0],.5,-1,.4)==pytest.approx([.4,.6,.3])
    assert equation11([1,.5,.25],[0,0,0],[2,0,0],0,0,.4)==[1,.5,.25]


def test_motifs_topology_only_unknown_zero_and_map_serialization(box_mesh,open_mesh):
    before=topology_motifs(box_mesh)
    assert {s.key() for s in before.values()}=={'(3,3)'}
    box_mesh.vertex_attributes(0,'xyz',[100,-400,900])
    assert topology_motifs(box_mesh)==before
    assert {s.key() for s in topology_motifs(open_mesh).values()}=={'(2,1)'}
    mapping={'(3,3)':-.4,'(4,4)':.2}
    assert validate_motif_map(json.loads(json.dumps(mapping)))==mapping
    assert set(motif_values(open_mesh,mapping).values())=={0.}
    with pytest.raises(ValueError): validate_motif_map({'3,3':.4})


@pytest.mark.parametrize('kind',['cube','column','C0'])
def test_disabled_extension_exact_existing_mesh_and_sampling_regression(kind):
    if kind=='C0':
        data=json.loads((ROOT/'studies/task19/C0.json').read_text())
        mesh=Mesh.from_vertices_and_faces({v['id']:v['xyz'] for v in data['vertices']},{f['id']:f['vertices'] for f in data['faces']})
    else: mesh=Mesh.from_shape(Box(2,2,2) if kind=='cube' else Box(1,1,6))
    source=mesh; before=deepcopy(source.__data__); old_origin=None; new_origin=None
    for generation in range(2):
        weights=dict(w1=-.6,w2=-.4,wf=.03,we=-.01,wp=.02,w3=-.7,w4=.4)
        old=generational_subdivide_once(mesh,weights,origin_lineage=old_origin,current_generation=generation)
        new=sharp_subdivide_once(mesh,{**weights,'w6':0.,'w7':0.},u_map={'(3,3)':1.},
            lock_groups={'disabled':dict(vertices=[next(mesh.vertices())],iterations=0)},
            origin_lineage=new_origin,current_generation=generation)
        assert old.mesh.__data__==new.mesh.__data__ and old.sampling_parents==new.sampling_parents
        assert old.origin_lineage==new.origin_lineage
        old_origin=old.origin_lineage; new_origin=new.origin_lineage; mesh=old.mesh
    # Source remained untouched; the second call used a fresh returned mesh.
    assert source.__data__==before


def test_active_motif_offset_uses_original_input_points_and_keeps_source_unchanged(box_mesh):
    before=deepcopy(box_mesh.__data__)
    first=sharp_subdivide_once(box_mesh)
    mesh=first.mesh
    result=sharp_subdivide_once(mesh,dict(w6=.12,w7=.07),u_map={'(3,3)':.8,'(4,4)':-.1},
        origin_lineage=first.origin_lineage,current_generation=1)
    row=next(r for r in result.metadata['motif_applications'] if r['kind']=='face' and r['result_xyz']!=r['base_xyz'])
    expected=equation10(row['base_xyz'],[mesh.vertex_coordinates(v) for v in row['input_vertices']],row['motif_u'],.12)
    assert row['result_xyz']==expected
    assert result.mesh.is_valid() and result.mesh.is_manifold() and result.mesh.is_closed()
    assert box_mesh.__data__==before


def test_literal_corner_lock_duration_and_no_hidden_edge_tagging(box_mesh):
    original=deepcopy(box_mesh.__data__); vertex=min(box_mesh.vertices()); fixed=box_mesh.vertex_coordinates(vertex)
    config={'one':dict(vertices=[vertex],iterations=2)}; meshes=[]
    for _ in range(2):
        mesh=box_mesh; origin=None; rows=[]
        for generation in range(3):
            result=sharp_subdivide_once(mesh,lock_groups=config,origin_lineage=origin,current_generation=generation)
            rows.append(deepcopy(result.mesh.__data__))
            if generation<2: assert result.mesh.vertex_coordinates(vertex)==fixed
            else: assert result.mesh.vertex_coordinates(vertex)!=fixed
            assert all(not r['locked'] for r in result.metadata['motif_applications'] if r['kind']!='corner')
            mesh=result.mesh; origin=result.origin_lineage
        meshes.append(rows)
    assert meshes[0]==meshes[1] and box_mesh.__data__==original


def test_source_graph_hops_ignore_geometry_and_inherit_positive_samples(box_mesh):
    seeds=list(next(box_mesh.edges())); a=source_graph_distance(box_mesh,seeds)
    box_mesh.vertex_attributes(next(box_mesh.vertices()),'xyz',[20000,4000,-900])
    assert source_graph_distance(box_mesh,seeds)==a
    result=generational_subdivide_once(box_mesh)
    inherited=inherit_scalar(a['normalized'],result.sampling_parents)
    assert all(0<=v<=1 for v in inherited.values())
    parent=next(p for p in result.metadata['points'] if p['point_class']=='edge')
    assert inherited[parent['id']]==pytest.approx(sum(a['normalized'][v] for v in parent['source'])/2)


def test_intrinsic_linear_interpolation_and_existing_normal_proxy(box_mesh):
    scalar={v:1. for v in box_mesh.vertices()}
    a,b,_=intrinsic_overrides(box_mesh,dict(mode='SOURCE_GRAPH_DISTANCE',controls={'w1':[-.2,.7],'w3':[.1,.3]}),scalar)
    assert all(r['w1']==pytest.approx(.7) for r in a['edge'].values())
    assert all(r['w3']==pytest.approx(.3) for r in b.values())
    assert all(0<=v<=1 for v in normal_variation_values(box_mesh).values())
    with pytest.raises(ValueError): intrinsic_overrides(box_mesh,dict(mode='NORMAL_VARIATION',controls={'w6':[0,1]}),scalar)


def test_source_support_mask_does_not_change_motif_classification_or_zero_regression(box_mesh):
    motifs=topology_motifs(box_mesh)
    base=generational_subdivide_once(box_mesh)
    zero={v:0. for v in box_mesh.vertices()}
    result=sharp_subdivide_once(box_mesh,dict(w6=.3,w7=.2),u_map={'(3,3)':1.},vertex_u_scale=zero)
    assert result.mesh.__data__==base.mesh.__data__ and topology_motifs(box_mesh)==motifs
    with pytest.raises(ValueError): sharp_subdivide_once(box_mesh,vertex_u_scale={})


def test_serialized_nonstationary_sharp_checkpoint_replay(box_mesh):
    schedule=compile_schedule(dict(w1=dict(mode='DISCRETE',values=[-.7,-.5,-.3]),
        w2=dict(mode='DISCRETE',values=[-2.8,-2.2,-1.8]),w6=dict(mode='EQ7_TREND',a=.12,b=.025,q=1),
        w7=dict(mode='EQ7_TREND',a=.2,b=.01,q=2)),3)
    recipe=json.loads(json.dumps(dict(schedule=schedule,u_map={'(3,3)':1.,'(4,4)':-.2},
        groups={'source-edge':dict(vertices=list(next(box_mesh.edges())),iterations=1)})))
    checkpoints=[]
    for _ in range(2):
        mesh=box_mesh; origins=None; rows=[]
        for i,row in enumerate(recipe['schedule']['rows']):
            step=sharp_subdivide_once(mesh,row,u_map=recipe['u_map'],lock_groups=recipe['groups'],
                origin_lineage=origins,current_generation=i)
            rows.append(deepcopy(step.mesh.__data__)); mesh=step.mesh; origins=step.origin_lineage
        checkpoints.append(rows)
    assert checkpoints[0]==checkpoints[1]


def test_external_root_relative_identity_and_resume_after_relocation(tmp_path):
    sys.path.insert(0,str(ROOT/'examples'))
    from ornament_study import digest,file_hash,verified_resume
    a=ArtifactRoot(tmp_path/'one'); b=ArtifactRoot(tmp_path/'two')
    case=a.resolve('study/fixture'); case.mkdir(parents=True)
    mesh=case/'terminal.json'; mesh.write_text('{"actual":"fixture"}')
    request=dict(id='fixture',input='inputs/fixture.json',equation_mode='LITERAL_EQ10_EQ11_UNNORMALIZED')
    (case/'summary.json').write_text(json.dumps(dict(status='SUCCESS',request_sha256=digest(request),artifacts={'terminal.json':file_hash(mesh)})))
    assert a.reference(mesh)=='study/fixture/terminal.json' and verified_resume(case,request)
    shutil.copytree(a.path,b.path)
    assert b.reference(b.resolve(a.reference(mesh)))==a.reference(mesh)
    assert verified_resume(b.resolve('study/fixture'),request)
    b.resolve('study/fixture/terminal.json').write_text('{"changed":true}')
    assert not verified_resume(b.resolve('study/fixture'),request)
    for path in ('../outside','E:/outside/file.obj'):
        with pytest.raises(ValueError): a.resolve(path)
    from beyond_smoothness_study import can_resume
    request['code']=dict(commit='before-commit',source_files={'kernel.py':'unchanged-bytes'})
    (case/'request.json').write_text(json.dumps(request))
    (case/'summary.json').write_text(json.dumps(dict(status='SUCCESS',request_sha256=digest(request),artifacts={'terminal.json':file_hash(mesh)})))
    committed=deepcopy(request); committed['code']['commit']='after-commit'
    assert can_resume(case,committed)
    committed['code']['source_files']['kernel.py']='changed-bytes'
    assert not can_resume(case,committed)
    (case/'summary.json').write_text('{"interrupted":')
    assert not can_resume(case,request)
