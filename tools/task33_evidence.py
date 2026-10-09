"""Native checkpoint recovery and constructive symmetry evidence for Task33."""
import argparse,json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import ROOT,sha,write_new
from task29_search import load_mesh
from cheshire.task33_folds import refine,refine_section,evaluate
from cheshire.progressive_gates import PLANE_X


def state_at(stage):
    with np.load(stage/'material_state.npz') as z:return {k:z[k].copy() for k in z.files}


def canonical(q):
    return np.take_along_axis(q,(np.argmin(q,axis=1)[:,None]+np.arange(q.shape[1]))%q.shape[1],axis=1)


def evidence(candidate,tag):
    job=ROOT/'candidates'/candidate
    request=json.loads((job/'request.json').read_text())
    completed=json.loads((job/'completed.json').read_text())
    records=[]
    for stage in sorted(job.glob('*/identity.json')):
        d=json.loads(stage.read_text())
        for file,digest in d['files'].items():
            if sha(stage.parent/file)!=digest:raise ValueError('Checkpoint changed: '+str(stage.parent/file))
        summary=json.loads((stage.parent/'summary.json').read_text())
        parent=summary['parent']
        if parent and sha(Path(parent)/'mesh.npz')!=d['parent_mesh_sha256']:raise ValueError('Parent mismatch')
        records.append(str(stage.parent))
    for file,digest in json.loads((job/'source_identity.json').read_text()).items():
        if sha(job/'source'/file)!=digest:raise ValueError('Producer source overlay changed')
    stage=Path(completed['final_stage']);m=load_mesh(stage);state=state_at(stage)
    mirrored=state['chart'].copy();mirrored[:,0]=1-mirrored[:,0]
    distance,pair=cKDTree(state['chart']).query(mirrored)
    if distance.max()>1e-10 or not np.array_equal(pair[pair],np.arange(len(pair))):raise ValueError('Invalid constructive reflection')
    target=m.xyz.copy();target[:,0]=2*PLANE_X-target[:,0]
    if np.any(m.faces<0):raise ValueError('Final quads required for exact oriented cycle audit')
    actual=canonical(m.faces);reflected=canonical(pair[m.faces[:,::-1]])
    a=actual[np.lexsort(actual.T)];b=reflected[np.lexsort(reflected.T)]
    oriented_failures=int(np.any(a!=b,axis=1).sum())
    if oriented_failures:raise ValueError('Reflected native face cycles differ')
    control_errors={}
    with np.load(stage/'fold_state.npz') as z:
        for key in z.files:control_errors[key]=float(np.abs(z[key]-z[key][pair]).max())
    replay=[]
    # Restore the latest pre-final native state, including material domain,
    # then regenerate the final checkpoint's geometry and topology.
    g=m.generation;previous=job/f'G{g-1}_FOLD'
    before=load_mesh(previous);restored=state_at(previous)
    if g>=request.get('section_refine_start',999):new,restored,_,_=refine_section(before,restored)
    else:new,restored,_,_=refine(before,restored)
    level=min(request.get('levels',3),int(g>=request.get('macro_generation',3))+int(g>=request.get('child_generation',4))+int(g>=request.get('micro_generation',5)))
    new,_=evaluate(new,restored,request.get('parameters',{}),level)
    exact={key:bool(np.array_equal(getattr(new,key),getattr(m,key))) for key in ['xyz','faces','classes','rest','anchors']}
    if not all(exact.values()):raise ValueError('Native continuation replay mismatch')
    macro_first=job/f'G{request.get("macro_generation",3)}_FOLD'
    early=load_mesh(macro_first)
    early_macro,_=evaluate(early,state_at(macro_first),request.get('parameters',{}),1)
    final_macro,_=evaluate(m,state,request.get('parameters',{}),1)
    preservation=float(np.abs(early_macro.xyz-final_macro.xyz[:len(early.xyz)]).max())
    write_new(ROOT/'preservation'/(tag+'.json'),dict(candidate=candidate,verified_checkpoints=records,
        source_identity_sha256=sha(job/'source_identity.json'),restored_from=str(previous),replay_exact_arrays=exact,
        final_mesh_sha256=sha(stage/'mesh.npz'),symmetry=dict(method='Material-arc reflection involution, exact reversed oriented native quad cycles; no coordinate averaging.',
        maximum_vertex_residual=float(np.linalg.norm(target-m.xyz[pair],axis=1).max()),chart_max_residual=float(distance.max()),
        oriented_face_failures=oriented_failures,control_residuals=control_errors,
        caveat='Native polygon correspondence; diagnostic first-corner fan triangulations can differ on reflected nonplanar quads.'),
        inherited_macro_max_coordinate_difference=preservation,
        note='Exact inherited macro coordinates prove reconstruction persistence, not perceptual quality; lowpass and native sections are separately reported.'))
    print(candidate,'native replay',exact,'macro difference',preservation,'oriented reflection failures',oriented_failures)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    if not all(v.replace('_','').isalnum() for v in (a.candidate,a.tag)):raise ValueError('Safe names required.')
    evidence(a.candidate,a.tag)
