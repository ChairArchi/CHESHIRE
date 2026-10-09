"""Isolated causal tests of Task31 controls; historical code/data are read-only."""
import argparse,json,sys,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh,save_mesh
from task33_preserve import ROOT,sha,write_new
from cheshire.reference_subdivision import fields
from cheshire.regional_generation import birth,advance
from cheshire.progressive_gates import PLANE_X


def cycle(q):
    q=list(q[q>=0]);k=q.index(min(q));return tuple(q[k:]+q[:k])


def propagate(vp,fp,op,nv,nf):
    edges=op['input_edges'];lookup={tuple(e):i for i,e in enumerate(edges)}
    ep=np.array([lookup[tuple(sorted(vp[e]))] for e in edges])
    newvp=np.r_[vp,nv+ep,nv+len(edges)+fp]
    lookup={(int(f),int(c)):i for i,(f,c) in enumerate(zip(op['parent_face'],op['parent_corner']))}
    newfp=np.array([lookup[(int(fp[f]),int(vp[c]))] for f,c in zip(op['parent_face'],op['parent_corner'])])
    return newvp,newfp


def diagnose(tag='control_causality'):
    if not tag.replace('_','').isalnum():raise ValueError('Safe immutable tag required.')
    source=Path('E:/CHESHIRE_DATA/task31/lead/gate');dest=ROOT/'analysis'/tag
    dest.mkdir(parents=True,exist_ok=False)
    shutil.copy2(Path(__file__),dest/'producer_source.py')
    m=load_mesh(source/'G0');target=m.xyz.copy();target[:,0]=2*PLANE_X-target[:,0]
    distance,vp=cKDTree(m.xyz).query(target)
    assert distance.max()<1e-9
    lookup={cycle(q):i for i,q in enumerate(m.faces)}
    fp=np.array([lookup[cycle(np.r_[vp[q[q>=0]][::-1]])] for q in m.faces])
    for g in [1,2]:
        with np.load(source/f'G{g}/operator_state.npz') as z:op={k:z[k] for k in z.files}
        vp,fp=propagate(vp,fp,op,len(m.xyz),len(m.faces));m=load_mesh(source/f'G{g}')
    assert np.array_equal(vp[vp],np.arange(len(vp))) and np.array_equal(fp[fp],np.arange(len(fp)))
    members,bmeta=birth(m,'fold');paired=members.copy();right=fields(m)['c'][:,0]>PLANE_X+1e-9
    paired[right]=paired[fp[right]]
    assert np.array_equal(paired,paired[fp])
    spec=json.loads(Path('E:/CHESHIRE_DATA/task30/definitions/final_selected_pipeline.json').read_text())['steps'][2]
    definition=json.loads((REPO/'studies/task31/definitions/task31_lead_pipeline.json').read_text())['cube']
    records=[]
    for name,control in [('unpaired_birth',members),('paired_birth',paired)]:
        out,roles,regional,meta,op=advance(m,np.full(len(m.faces),-1,np.int8),control,spec,definition)
        ovp,ofp=propagate(vp,fp,op,len(m.xyz),len(m.faces))
        target=out.xyz.copy();target[:,0]=2*PLANE_X-target[:,0]
        residual=float(np.linalg.norm(target-out.xyz[ovp],axis=1).max())
        stage=dest/name;save_mesh(stage,out,meta,op,source/'G2')
        np.savez_compressed(stage/'regional_state.npz',members=regional,face_roles=roles,vertex_reflection=ovp,face_reflection=ofp)
        records.append(dict(case=name,maximum_constructive_symmetry_residual=residual,stage=str(stage),mesh_sha256=sha(stage/'mesh.npz')))
    locked=[]
    for g in [3,4]:
        stage=source/f'G{g}';parent=Path(json.loads((stage/'summary.json').read_text())['parent'])
        with np.load(stage/'operator_state.npz') as z:
            mask=z['vertex_lock_mask'];requested=np.abs(z['resolved_wp'])*z['vertex_scale']
        before=load_mesh(parent);after=load_mesh(stage)
        movement=float(np.linalg.norm(after.xyz[:len(before.xyz)][mask]-before.xyz[mask],axis=1).max())
        if movement!=0:raise ValueError('Saved locked vertices differ from their input positions.')
        locked.append(dict(generation=g,input=str(parent),locked_previous_vertices=int(mask.sum()),previous_vertices=len(mask),
            locked_requested_normal_distance_median=float(np.median(requested[mask])),
            locked_requested_normal_distance_max=float(requested[mask].max()),actual_locked_displacement=movement,
            meaning='The final vp overwrite cancels ALL requested movement at locked previous vertices. New face/edge points still deform; requested wp is not the total coupled displacement.'))
    write_new(dest/'results.json',dict(source_tool_sha256=sha(Path(__file__)),birth=bmeta,
        changed_control_faces=int(np.any(members!=paired,axis=1).sum()),no_opening_edit=True,
        causal_cases=records,locks=locked,
        conclusion='Only birth control pairing changes. Original XYZ, operator order and coefficients are unchanged; this isolates threshold asymmetry from coarse-opening selection.'))
    print(records,locked,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',default='control_causality');a=p.parse_args();diagnose(a.tag)
