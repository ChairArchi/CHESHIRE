"""Sampled ridges in actual triangle sections, with explicit missing splits.

Finite material cuts are not exact differential ridge extraction or a global
connectivity proof. Parent labels follow the three inner reference phases;
every reported location and depth comes from triangle-interpolated XYZ.
"""
import json,sys
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import ROOT,sha,write_new
from task29_search import load_mesh
from task33_evidence import state_at
from task33_measure import cut,prepare_cuts
from cheshire.task33_folds import evaluate,fold_values


def tracks(candidate,tag):
    job=ROOT/'candidates'/candidate
    stage=Path(json.loads((job/'completed.json').read_text())['final_stage'])
    request=json.loads((job/'request.json').read_text());params=request['parameters']
    mesh=load_mesh(stage);state=state_at(stage);reference,_=evaluate(mesh,state,params,0)
    macro,_=evaluate(mesh,state,params,1);meso,_=evaluate(mesh,state,params,2)
    prepared=prepare_cuts(mesh,state);qs=np.linspace(.06031,.49031,65)
    records=[];arrays={};last=None
    for index,s in enumerate(qs):
        profiles=[]
        for m in [macro,meso,mesh]:
            u,d,xyz,tangent=cut(m,state,s,reference,params,prepared);profiles.append((d,xyz))
        md,macroxyz=profiles[0];mid,_=profiles[1];final,finalxyz=profiles[2]
        peaks,prop=find_peaks(md,prominence=50)
        phases=fold_values(np.column_stack([np.full(len(u),s),u,-np.ones(len(u))]),params,1)['parent_phase']
        chosen=np.array([peaks[np.argmin(np.abs(phases[peaks]-2*np.pi*k))] for k in [-1,0,1]])
        if len(set(chosen))!=3:raise ValueError('Three distinct inner parent ridges not resolved.')
        mp,mprop=find_peaks(mid,prominence=25);fp,fprop=find_peaks(final,prominence=15)
        minima,_=find_peaks(-mid)
        row=dict(s=float(s),parents=[])
        for label,p in zip([-1,0,1],chosen):
            left=p;right=p
            while left>0 and md[left-1]>.5*md[p]:left-=1
            while right<len(u)-1 and md[right+1]>.5*md[p]:right+=1
            children=mp[(mp>left)&(mp<right)]
            child_rows=[]
            for c in children:
                l=minima[minima<c];r=minima[minima>c]
                l=int(l[-1]) if len(l) else 0;r=int(r[0]) if len(r) else len(u)-1
                a=fp[(fp>l)&(fp<c)];b=fp[(fp>c)&(fp<r)]
                split=None
                if len(a) and len(b):
                    a=int(a[np.argmax(final[a])]);b=int(b[np.argmax(final[b])])
                    valley=int(a+np.argmin(final[a:b+1]))
                    split=dict(left_u=float(u[a]),right_u=float(u[b]),valley_u=float(u[valley]),
                        valley_depth=float(min(final[a],final[b])-final[valley]))
                child_rows.append(dict(u=float(u[c]),xyz=finalxyz[c].tolist(),fine_split=split))
            row['parents'].append(dict(label=label,u=float(u[p]),xyz=macroxyz[p].tolist(),
                xyz_on_final_surface=finalxyz[p].tolist(),children=child_rows))
        span=float((macroxyz[chosen[-1]]-macroxyz[chosen[0]])@tangent)
        row['three_inner_parent_span']=span
        row['largest_parent_u_step']=None if last is None else float(np.max(np.abs(u[chosen]-last)))
        last=u[chosen]
        records.append(row)
        arrays[f'cut_{index}']=np.column_stack([u,md,mid,final,finalxyz])
    dest=ROOT/'analysis'/tag;dest.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(dest/'actual_tracks.npz',q=qs,**arrays)
    split_depths=[c['fine_split']['valley_depth'] for r in records for p in r['parents'] for c in p['children'] if c['fine_split']]
    write_new(dest/'tracks.json',dict(candidate=candidate,mesh_sha256=sha(stage/'mesh.npz'),rows=records,
        cuts=len(records),three_inner_parent_span_range=[min(r['three_inner_parent_span'] for r in records),max(r['three_inner_parent_span'] for r in records)],
        maximum_sampled_parent_u_step=max(r['largest_parent_u_step'] or 0 for r in records),
        children_with_resolved_fine_split=len(split_depths),fine_split_depth_range=[min(split_depths),max(split_depths)] if split_depths else None,
        data_sha256=sha(dest/'actual_tracks.npz'),
        method='65 actual front-material triangle cuts. Three macro parents labelled by nearest inner reference phase (-1,0,1); meso maxima lie in each parent half-height basin; a fine split requires final maxima on both sides of the meso maximum in its own minimum-bounded basin.',
        limitations='Sampled correspondence, not exact differential ridges or proof of continuous connectivity between cuts. Missing fine splits are retained, prominence cutoffs are descriptive 50/25/15 in original units. Cuts may be nonplanar at shoulders.'))
    print(candidate,'tracked cuts',len(records),'resolved fine splits',len(split_depths),'depth',min(split_depths) if split_depths else None,max(split_depths) if split_depths else None,flush=True)
