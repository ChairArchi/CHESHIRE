"""Actual deterministic regeneration, checkpoint continuation and OBJ reread."""
import argparse,gc,shutil,sys
from time import perf_counter
import numpy as np
from task31_study import ROOT,PREVIOUS,read,write,file_hash,load,load_mesh,basic_gate
from cheshire.regional_generation import advance,birth,coarse_edit
from cheshire.progressive_gates import PLANE_X,PLANE_Y
from task29_evidence import obj_save_verify
from hero_design_sprint import guarded


def compare(path,m,roles,members,state=None):
    with np.load(path/'mesh.npz') as z:
        for k in ('xyz','faces','classes','rest','anchors'):assert np.array_equal(getattr(m,k),z[k]),(str(path),k)
    with np.load(path/'regional_state.npz') as z:
        assert np.array_equal(roles,z['face_roles'])
        if members is not None:assert np.array_equal(members,z['members'])
    if state is not None:
        with np.load(path/'operator_state.npz') as z:
            assert set(z.files)==set(state),(str(path),set(z.files),set(state))
            for k in z.files:assert np.array_equal(z[k],state[k]),(str(path),k)


def verify(kind,existing=False):
    started=perf_counter();definition=read(ROOT/'definitions/task31_lead_pipeline.json')[kind]
    src=ROOT/'candidates'/kind/definition['id'];dest=ROOT/'lead'/kind
    if existing:
        for path in src.rglob('*.npz'):assert file_hash(path)==file_hash(dest/path.relative_to(src))
    else:shutil.copytree(src,dest)
    verified_definition=ROOT/'definitions'/('verified_'+kind+'_pipeline.json')
    snapshot=dict(kind=kind,definition=definition,base_pipeline_sha256=file_hash(PREVIOUS/'definitions/final_selected_pipeline.json'))
    if verified_definition.exists():assert read(verified_definition)==snapshot
    else:write(verified_definition,snapshot)
    m=load_mesh(src/'G0') if kind=='cube' else basic_gate();roles=np.full(len(m.faces),-1,np.int8);members=None;records=[]
    compare(src/'G0',m,roles,members)
    specs=read(PREVIOUS/'definitions/final_selected_pipeline.json')['steps']
    for spec in specs:
        g=spec['generation']
        if g==3 and definition['edit']:
            m,roles,members,meta,st=coarse_edit(m,roles,members,definition['edit'],[PLANE_X,PLANE_Y,3050] if kind=='gate' else None)
            compare(src/'G2_post_edit',m,roles,members,st);del st
        m,roles,members,meta,st=advance(m,roles,members,spec,definition)
        if definition['descriptor'] and g==definition['born']:members,_=birth(m,definition['descriptor'])
        compare(src/f'G{g}',m,roles,members,st);del st;gc.collect()
        records.append(dict(generation=g,exact_geometry=True,exact_regions_origins_rest_ancestry=True,exact_operator_arrays=True))
        print('Exact',kind,'G'+str(g),'PASS',flush=True)
    # Actual reload of G7 includes the persistent mixtures, not a recomputed tag.
    xyz=m.xyz.copy();faces=m.faces.copy();expected_members=members.copy() if members is not None else None
    del m;gc.collect()
    prior,roles,members=load(src/'G7');continued,roles,members,_,st=advance(prior,roles,members,specs[-1],definition)
    assert np.array_equal(continued.xyz,xyz) and np.array_equal(continued.faces,faces)
    assert np.array_equal(members,expected_members);del xyz,faces,expected_members,prior,st;gc.collect()
    dcc=ROOT/'dcc';dcc.mkdir(exist_ok=True);obj=dcc/('TASK31_'+kind.upper()+'_LEAD.obj')
    evidence=obj_save_verify(continued,obj)
    with obj.open('r+b') as out:out.write(b'# Task31')
    evidence['sha256']=file_hash(obj)
    write(ROOT/'analysis'/('geometry_validation_'+kind+'.json'),dict(exact_G0_to_G8_regeneration=True,records=records,
        actual_G7_checkpoint_continuation=True,OBJ=evidence,seconds=perf_counter()-started,source=str(src),lead_copy=str(dest),
        definition_sha256=file_hash(verified_definition)))
    print('Actual',kind,'OBJ exact reread PASS',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['cube','gate']);p.add_argument('--worker',action='store_true');p.add_argument('--existing',action='store_true');a=p.parse_args()
    if a.worker:verify(a.kind,a.existing)
    else:
        result=guarded([a.kind,'--worker']+(['--existing'] if a.existing else []),ROOT/'logs'/('verify_'+a.kind+('_final' if a.existing else '')),worker_script=__file__);print(result,flush=True);sys.exit(result['exit_code'])
