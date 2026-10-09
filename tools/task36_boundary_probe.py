"""Newest V/E/F points versus prior physical XY bounds; no mesh mutation."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path('E:/CHESHIRE_DATA/task36')


def probe(candidate,tag):
    job=ROOT/'candidates'/candidate;dest=ROOT/'measurements'/tag;dest.mkdir(parents=True,exist_ok=False)
    last=len(json.loads((job/'completed.json').read_text())['history']);prior=np.load(job/'G0_CARRIER/quad_state.npz')['xyz'];rows=[]
    for g in range(1,last+1):
        stage=job/f'G{g}_FOLD';z=np.load(stage/'quad_state.npz');x=z['xyz'];op=np.load(stage/'operator_state.npz');nv=len(op['incoming_point_classes']);ne=len(op['input_edges'])
        lo=prior[:,:2].min(0);hi=prior[:,:2].max(0)
        groups={}
        for name,points in [('retained',x[:nv]),('new_edge',x[nv:nv+ne]),('new_face',x[nv+ne:])]:
            groups[name]=dict(count=len(points),xy_absolute_max=float(abs(points[:,:2]).max()),outside_prior_global_XY_bounds=int(((points[:,:2]<lo-1e-9)|(points[:,:2]>hi+1e-9)).any(1).sum()))
        magnitude=np.sqrt(np.maximum(0,1-op['edge_bend']/2))
        rows.append(dict(generation=g,prior_XY_bounds=[lo.tolist(),hi.tolist()],groups=groups,
            coupled_edge_normal_magnitude_quantiles=np.quantile(magnitude,[0,.05,.5,.95,1]).tolist(),edge_normals_below_point1=int((magnitude<.1).sum()),
            incoming_support_quantiles=np.quantile(op['support_radius'],[0,.05,.5,.95,1]).tolist()))
        prior=x;print(g,groups['new_edge']['outside_prior_global_XY_bounds'],groups['new_face']['outside_prior_global_XY_bounds'],flush=True)
    value=dict(candidate=candidate,rows=rows,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitation='Global axis-aligned XY bounds are only one envelope diagnostic, not local silhouette freedom or independent topology proof. Edge normal magnitude follows the arithmetic mean of two current unit face normals; full displacement also includes coupled placement.')
    (dest/'boundary.json').write_text(json.dumps(value,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args();probe(a.candidate,a.tag)
