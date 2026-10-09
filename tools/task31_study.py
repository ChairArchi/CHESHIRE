"""Bounded Task31 actual cube and basic-gate experiment, immutable controls."""
import argparse,copy,gc,hashlib,json,shutil,sys
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'src'),str(REPO/'examples'),str(REPO/'tools')]
from cross_cell_crease_study import read,write,file_hash
from task29_search import load_mesh,save_mesh
from cheshire.reference_subdivision import ArrayMesh,topology,metrics
from cheshire.regional_generation import birth,advance,coarse_edit,CC_MODES,DS_MODES
from cheshire.progressive_gates import gate_input,PLANE_X,PLANE_Y
from hero_design_sprint import guarded
ROOT=Path('E:/CHESHIRE_DATA/task31');PREVIOUS=Path('E:/CHESHIRE_DATA/task30')


def variants():
    def d(name,descriptor=None,memory='persistent',contrast=0,edit=None,born=2):
        return dict(id=name,descriptor=descriptor,memory=memory,contrast=contrast,edit=edit,born=born,onset=3)
    v=[d(f'AX_{memory[:1].upper()}{int(c*10)}','axis',memory,c) for memory in ('persistent','remeasured') for c in (.4,.8)]
    v += [d(f'FOLD_P{int(c*10)}','fold',contrast=c) for c in (.4,.8)]
    for levels,depth in ((1,.3),(2,.3),(2,.6)):
        v.append(d(f'DEPTH_{levels}_{int(depth*10)}',edit=dict(kind='recess',levels=levels,depth=depth,ratio=.6)))
    v += [d(f'OPEN_{int(r*100)}',edit=dict(kind='opening',ratio=r)) for r in (.35,.6,.85)]
    v += [d(f'{s.upper()}_OPEN_{int(r*100)}',s,contrast=.8,edit=dict(kind='opening',ratio=r)) for s in ('axis','fold') for r in (.6,.85)]
    v += [d('AXIS_DEPTH','axis',contrast=.8,edit=dict(kind='recess',levels=2,depth=.6,ratio=.6)),d('AXIS_BORN1','axis',contrast=.8,born=1)]
    assert len(v)==18
    return v


def roles_at(path,m):
    f=path/'face_roles.npz'
    if f.exists():
        with np.load(f) as z:return z['face_roles']
    with np.load(path/'mesh.npz') as z:
        return z['face_roles'] if 'face_roles' in z.files else np.full(len(m.faces),-1,np.int8)


def save(path,m,roles,members,meta,state,parent):
    started=perf_counter()
    summary=save_mesh(path,m,meta,state,parent)
    np.savez_compressed(path/'regional_state.npz',face_roles=roles,**({} if members is None else dict(members=members)))
    summary.update(state_sha256=file_hash(path/'regional_state.npz'),parent_mesh_sha256=file_hash(parent/'mesh.npz') if parent else None,
        saved_seconds=perf_counter()-started)
    write(path/'summary.json',summary)
    return summary


def load(path):
    m=load_mesh(path)
    with np.load(path/'regional_state.npz') as z:return m,z['face_roles'],z['members'] if 'members' in z.files else None


def generate(definition,kind):
    spec=read(PREVIOUS/'definitions/final_selected_pipeline.json');dest=ROOT/'candidates'/kind/definition['id'];times=[]
    if kind=='cube':
        members=None
        for g in range(3):
            path=dest/f'G{g}';shutil.copytree(PREVIOUS/f'lead/G{g}',path)
            m=load_mesh(path);roles=roles_at(path,m)
            if definition['descriptor'] and g==definition['born']:
                members,bmeta=birth(m,definition['descriptor']);write(path/'regional_birth.json',bmeta)
            elif members is not None:
                with np.load(path/'operator_state.npz') as z:members=members[z['parent_face']]
            np.savez_compressed(path/'regional_state.npz',face_roles=roles,**({} if members is None else dict(members=members)))
            summary=read(path/'summary.json');summary.update(source_checkpoint=str(PREVIOUS/f'lead/G{g}'),
                parent=str(dest/f'G{g-1}') if g else None,state_sha256=file_hash(path/'regional_state.npz'))
            write(path/'summary.json',summary)
        start=3
    else:
        m=basic_gate();roles=np.full(len(m.faces),-1,np.int8);members=None
        save(dest/'G0',m,roles,members,dict(input='Exact existing gate_input RECT False'),None,None);start=1
    for g in range(start,9):
        parent=dest/f'G{g-1}';st=perf_counter()
        if g==3 and definition.get('edit'):
            target=[PLANE_X,PLANE_Y,3050] if kind=='gate' else None
            m,roles,members,meta,state=coarse_edit(m,roles,members,definition['edit'],target)
            editpath=dest/'G2_post_edit';save(editpath,m,roles,members,meta,state,parent);parent=editpath
        m,roles,members,meta,state=advance(m,roles,members,spec['steps'][g-1],definition)
        if definition['descriptor'] and m.generation==definition['born']:
            members,bmeta=birth(m,definition['descriptor']);meta['birth']=bmeta
        summary=save(dest/f'G{g}',m,roles,members,meta,state,parent);del state;gc.collect()
        times.append(perf_counter()-st)
        print(kind,definition['id'],f'G{g}',len(m.faces),round(times[-1],2),'s',flush=True)
    record=dict(id=definition['id'],kind=kind,definition=definition,stage_seconds=times,final_summary=summary)
    write(ROOT/'analysis/runs'/kind/(definition['id']+'.json'),record)
    return record


def basic_gate():
    mesh,_=gate_input('RECT',False)
    xyz=np.array([mesh.vertex_coordinates(v) for v in mesh.vertices()]);faces=np.full((mesh.number_of_faces(),4),-1,np.int64)
    for f in mesh.faces():q=mesh.face_vertices(f);faces[f,:len(q)]=q
    return ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(faces),3),-1,np.int64))


def prepare():
    write(ROOT/'definitions/task31_variant_definitions.json',dict(StageA=variants(),CC_modes=CC_MODES,DS_modes=DS_MODES,
        control='Unchanged actual Task30 U_67_LOCK_END4',blend='(1-contrast)*resolved Task30 intrinsic control + contrast*membership-weighted mode',
        inheritance='CC exact parent; DS all actual incident parents equal mean; edited walls CHANNEL',
        polygon_extension='Exact Eq5/6 n3/4; standard cosine mask n>4, w1 inactive there; common to controls and gate transfers'))
    shutil.copytree(PREVIOUS/'lead',ROOT/'controls/cube')
    m=load_mesh(PREVIOUS/'lead/G0');roles=roles_at(PREVIOUS/'lead/G0',m);proof=[]
    definition=dict(id='TASK30_REPLAY',descriptor=None,memory='persistent',contrast=0)
    for spec in read(PREVIOUS/'definitions/final_selected_pipeline.json')['steps']:
        m,roles,_,_,_=advance(m,roles,None,spec,definition);g=m.generation;old=load_mesh(PREVIOUS/f'lead/G{g}')
        identical={k:bool(np.array_equal(getattr(m,k),getattr(old,k))) for k in ('xyz','faces','classes','rest','anchors')}
        assert all(identical.values()),(g,identical);proof.append(dict(generation=g,exact_arrays=identical));print('Exact Task30 replay G',g,flush=True)
    write(ROOT/'analysis/task30_exact_replay.json',proof)
    sources=read(ROOT/'analysis/reference_sources.json')
    sources['polygon_mask_source']=dict(url='https://github.com/compas-dev/compas/blob/main/src/compas/datastructures/mesh/subdivision.py',
        local_version='COMPAS2.15.1',local_sha256=file_hash(REPO/'.venv/Lib/site-packages/compas/datastructures/mesh/subdivision.py'),
        independent_comparison='neutral n3/4/5/8 prism coordinates checked against installed COMPAS; tests/test_task31_regional_generation.py')
    write(ROOT/'analysis/reference_sources.json',sources)
    matrix=ROOT/'analysis/reference_research_matrix.md'
    matrix.write_text(matrix.read_text(encoding='utf-8')+'\n\nPolygon compatibility: standard cosine DS stencil independently checked against COMPAS2.15.1 for closed n3/4/5/8 prisms. Hansmeyer Eq5/6 remain exact for n3/4. Modified w1 is deliberately inactive for n>4; local wf remains active. This enables actual basic-gate and tunnel valences, not a third design search direction. Source: https://github.com/compas-dev/compas/blob/main/src/compas/datastructures/mesh/subdivision.py\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','cube','gate']);p.add_argument('--id');p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.worker:
        v=read(ROOT/'definitions/task31_variant_definitions.json')['StageA'] if a.action=='cube' else read(ROOT/'definitions/gate_specimen_definition.json')['variants']
        generate(next(d for d in v if d['id']==a.id),a.action)
    else:
        v=read(ROOT/'definitions/task31_variant_definitions.json')['StageA'] if a.action=='cube' else read(ROOT/'definitions/gate_specimen_definition.json')['variants']
        for d in v:
            if a.id and d['id']!=a.id:continue
            result=guarded([a.action,'--id',d['id'],'--worker'],ROOT/'logs'/(a.action+'_'+d['id']),worker_script=Path(__file__))
            print(d['id'],result,flush=True)
            if result['exit_code']!=0:raise SystemExit(result['exit_code'])
