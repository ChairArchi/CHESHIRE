"""Actual selection, deterministic replay and oriented export verification."""
import argparse,shutil,sys,gc
from pathlib import Path
from time import perf_counter
import numpy as np
from task30_study import ROOT,PREVIOUS,REPO,experimental_step
from task29_search import load_mesh
from task29_evidence import obj_save_verify
from cheshire.reference_subdivision import cube,fields,topology
from cross_cell_crease_study import read,write,file_hash


def select(name):
    spec=next(d for d in read(ROOT/'definitions/task30_variant_definitions.json') if d['id']==name)
    manifest=[]
    for g in range(9):
        src=ROOT/f'candidates/{name}/G{g}';d=ROOT/f'lead/G{g}';shutil.copytree(src,d)
        s=read(d/'summary.json');s.update(parent=str(ROOT/f'lead/G{g-1}') if g else None)
        write(d/'summary.json',s)
        manifest.append(dict(generation=g,source=str(src),source_sha256=file_hash(src/'mesh.npz'),lead_sha256=file_hash(d/'mesh.npz')))
    write(ROOT/'lead/lineage_manifest.json',dict(stages=manifest,selection='Exact actual saved stages; no substituted prefix or alternative lineage.'))
    write(ROOT/'definitions/final_selected_pipeline.json',spec)
    write(ROOT/'definitions/render_progression.json',dict(resolution=1500,width=2600,cols=3,size=1000,pages=9,
        sheet_name='TASK30_FINAL_LEAD_PROGRESSION.png',items=[dict(label=f'G{g}',stage=str(ROOT/f'lead/G{g}')) for g in range(9)]))
    items=[]
    for angle,a in [('oblique',[28,22]),('front',[0,0]),('upper',[12,62])]:
        for name,root in [('Task29',ROOT/'controls/task29'),('Task30',ROOT/'lead')]:
            items.append(dict(label=f'{name} G8 / {angle}',stage=str(root/'G8'),angles=a))
    write(ROOT/'definitions/render_comparison.json',dict(resolution=1800,width=2600,cols=2,size=1400,pages=6,
        sheet_name='TASK29_vs_TASK30_lead.png',items=items))
    items=[dict(label=f'{name} G{g} / 700 units',stage=str(root/f'G{g}'),width=700,target=[0,-350,0],angles=[0,0]) for name,root in [('Task29',ROOT/'controls/task29'),('Task30',ROOT/'lead')] for g in (3,5,8)]
    write(ROOT/'definitions/render_detail.json',dict(resolution=1800,width=2600,cols=3,size=1300,pages=6,sheet_name='TASK30_detail_comparison.png',items=items))


def verify():
    spec=read(ROOT/'definitions/final_selected_pipeline.json');m=cube();roles=np.full(len(m.faces),-1,np.int8);records=[];start=perf_counter()
    for g in range(9):
        d=ROOT/f'lead/G{g}';saved=load_mesh(d)
        if g:
            m,roles,meta,state=experimental_step(m,roles,spec['steps'][g-1])
            with np.load(d/'operator_state.npz') as actual:
                # Prefix state is the original exact Task29 archive. Extended
                # structural ancestry for CC is derivable from its parent_face.
                for k in actual.files:
                    assert np.array_equal(state[k],actual[k]),f'G{g} state {k}'
            assert not meta.get('all_zero',False)
        for k in ('xyz','faces','classes','rest','anchors'):
            assert np.array_equal(getattr(m,k),getattr(saved,k)),f'G{g} {k}'
        with np.load(d/'face_roles.npz') as z:assert np.array_equal(roles,z['face_roles'])
        obj=obj_save_verify(saved,d/f'G{g}.obj')
        # Equal-length task stamp changes only the informational first line.
        path=d/f'G{g}.obj'
        with path.open('r+b') as stream:
            header=stream.readline();replacement=header.replace(b'Task29',b'Task30')
            assert len(header)==len(replacement);stream.seek(0);stream.write(replacement)
        obj['sha256']=file_hash(path)
        records.append(dict(generation=g,exact_geometry_state=True,exact_operator_state=True,exact_face_roles=True,OBJ=obj))
        print('Exact cube replay, state and oriented OBJ reread G'+str(g),'PASS',flush=True);del saved;gc.collect()
    prior=load_mesh(ROOT/'lead/G7')
    with np.load(ROOT/'lead/G7/face_roles.npz') as z:priorroles=z['face_roles'].copy()
    continued,r,meta,state=experimental_step(prior,priorroles,spec['steps'][-1])
    assert all(np.array_equal(getattr(m,k),getattr(continued,k)) for k in ('xyz','faces','classes','rest','anchors'))
    assert np.array_equal(roles,r)
    with np.load(ROOT/'lead/G8/operator_state.npz') as z:assert all(np.array_equal(state[k],z[k]) for k in z.files)
    (ROOT/'dcc').mkdir(exist_ok=True);shutil.copy2(ROOT/'lead/G8/G8.obj',ROOT/'dcc/TASK30_LEAD.obj')
    write(ROOT/'analysis/geometry_validation.json',dict(status='PASS',records=records,exact_G0_to_G8=True,actual_G7_reload_continuation=True,
        all_modified_nonzero=True,definition_sha256=file_hash(ROOT/'definitions/final_selected_pipeline.json'),seconds=perf_counter()-start))


def retention():
    result=[]
    for name,root in [('Task29',ROOT/'controls/task29'),('Task30',ROOT/'lead')]:
        stages={g:load_mesh(root/f'G{g}') for g in range(9)};cached={g:fields(m) for g,m in stages.items()};curves=[]
        for birth in (1,2,3):
            ref=stages[birth];rf=cached[birth];t=topology(ref)
            scores=1-np.linalg.norm(rf['nf'][t['ef']].mean(1),axis=1);fs=np.zeros(len(ref.faces))
            np.maximum.at(fs,t['ef'].ravel(),np.repeat(scores,2))
            for anchor in np.argsort(-fs,kind='stable')[:3]:
                support=np.arange(len(ref.faces))==anchor;samples=[]
                normal=rf['nf'][anchor];center=rf['c'][anchor]
                for g in range(birth,9):
                    m=stages[g]
                    if g>birth:
                        with np.load(root/f'G{g}/operator_state.npz') as z:
                            parents=z['parent_faces'] if 'parent_faces' in z else z['parent_face'][:,None]
                        valid=parents>=0;support=(support[np.maximum(parents,0)]&valid).any(1)
                    ids=np.unique(m.faces[support]);ids=ids[ids>=0];xyz=m.xyz[ids];depth=(xyz-center)@normal
                    samples.append(dict(generation=g,supported_descendant_faces=int(support.sum()),depth_range=float(np.ptp(depth)),
                        depth_RMS=float(np.sqrt((depth**2).mean())),normal_variation=float(1-np.linalg.norm(cached[g]['nf'][support].mean(0)))))
                curves.append(dict(birth=birth,ancestor_face=int(anchor),samples=samples))
        result.append(dict(name=name,curves=curves,macro_extent=[dict(generation=g,extent=np.ptp(m.xyz,axis=0).tolist()) for g,m in stages.items()]))
        print('Actual multi-parent supported retention',name,flush=True)
    write(ROOT/'analysis/retention_metrics.json',dict(results=result,
        definition='Three high-normal-disagreement actual patches per birth G1/G2/G3. DS descendants include any actual source support, not a fabricated exclusive parent. Overlapping support grows by one neighbourhood per dual step; depth/normal proxies are not proof of feature identity. Fixed birth normals/centres; whole progression decides retention.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--select');p.add_argument('--verify',action='store_true');p.add_argument('--retention',action='store_true');a=p.parse_args()
    if a.select:select(a.select)
    if a.verify:verify()
    if a.retention:retention()
