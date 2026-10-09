"""Geometric response by saved mixtures; metrics are not style fidelity scores."""
import argparse,gc
import numpy as np
from task31_study import ROOT,read,write,load
from cheshire.reference_subdivision import topology,fields
from cheshire.regional_generation import MODES
from hero_design_sprint import guarded


def measure(kind):
    names=['AX_P8','AX_R8','FOLD_P8','FOLD_OPEN_85','AXIS_DEPTH'] if kind=='cube' else [read(ROOT/'definitions/task31_lead_pipeline.json')['gate']['id']]
    rows=[]
    for name in names:
        m,roles,members=load(ROOT/'candidates'/kind/name/'G8');t=topology(m);f=fields(m,t);regional=[]
        for j,mode in enumerate(MODES):
            weights=members[:,j];edge=weights[t['ef']].mean(1)
            if weights.sum()==0:continue
            regional.append(dict(mode=mode,membership_mass=float(weights.sum()),
                mean_adjacent_normal_angle=float(np.average(f['angles'],weights=edge)),
                mean_face_scale=float(np.average(f['sf'],weights=weights)),
                weighted_centroid=np.average(f['c'],weights=weights,axis=0).tolist(),
                exclusive_faces=int((weights==1).sum()),mixed_faces=int(((weights>0)&(weights<1)).sum())))
        rows.append(dict(id=name,regions=regional,interpretation='Different geometric response, not proof of independent non-repeating motif hierarchy.'))
        del m,t,f,members;gc.collect()
    write(ROOT/'analysis'/('regional_response_'+kind+'.json'),rows)
    print('Saved',kind,'regional response metrics.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['cube','gate']);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:measure(a.kind)
    else:
        result=guarded([a.kind,'--worker'],ROOT/'logs'/('regional_metrics_'+a.kind),worker_script=__file__);print(result,flush=True);raise SystemExit(result['exit_code'])
