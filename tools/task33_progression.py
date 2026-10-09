"""Matched actual native checkpoints, before/after each important operation."""
import argparse,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import ROOT,write_new,sha
from task29_search import load_mesh
from task33_evidence import state_at
from task33_measure import cut
from cheshire.task33_folds import evaluate


def progression(candidate,tag):
    job=ROOT/'candidates'/candidate;request=json.loads((job/'request.json').read_text())
    params=request['parameters'];dest=ROOT/'analysis'/tag;dest.mkdir(parents=True,exist_ok=False)
    arrays={};records=[]
    for g in range(request.get('macro_generation',3),request.get('final_generation',5)+1):
        for kind in ['PRE','FOLD']:
            stage=job/f'G{g}_{kind}';m=load_mesh(stage);state=state_at(stage)
            reference,_=evaluate(m,state,params,0)
            for s in [.06531,.15031,.24531]:
                u,d,xyz,_=cut(m,state,s,reference,params)
                arrays[f'G{g}_{kind}_s{s}']=np.column_stack([u,d,xyz])
            records.append(dict(stage=str(stage),mesh_sha256=sha(stage/'mesh.npz'),vertices=len(m.xyz),faces=len(m.faces)))
    np.savez_compressed(dest/'native_progression.npz',**arrays)
    write_new(dest/'native_progression.json',dict(candidate=candidate,records=records,
        data_sha256=sha(dest/'native_progression.npz'),parameters=params,
        method='Actual native checkpoints, not matched-resolution counterfactuals. Same material cuts and world units at every stage; PRE includes the recorded subdivision interpolation immediately before field reconstruction.'))
    print(candidate,'native stages',len(records))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    if not all(v.replace('_','').isalnum() for v in (a.candidate,a.tag)):raise ValueError('Safe names required.')
    progression(a.candidate,a.tag)
