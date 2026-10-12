"""Replay children and isolate their motion from affine-chart refinement drift."""
from pathlib import Path
import argparse
import copy
import json

import numpy as np
from scipy.signal import find_peaks

import study


CASES = ('SPAN','COUNTER','GATE_COLUMN','GATE_LINTEL')


def run(root,output,cases=('SPAN','COUNTER')):
    records=[]
    if not cases or any(case not in CASES for case in cases):
        raise ValueError('At least one declared child input case is required.')
    for case in cases:
        folder=root/'CHILD'/case/'G04'
        if not folder.exists():
            raise FileNotFoundError('Expected child output is absent: '+str(folder))
        mesh,chart,_=study.previous.anchor.t.load(folder)
        metadata=json.loads((folder/'generation.json').read_text(encoding='utf8'))
        with np.load(folder/'operation_fields.npz') as data:
            reference,actual_delta=data['reference_xyz'],data['delta']
        rails=[]
        for path in sorted(folder.glob('rails_*.npz')):
            with np.load(path) as data:
                rails.append({key:data[key] for key in data.files})
        delta,_=study.wall_fold.apply_wall(reference,chart,rails,mode='WALL')
        existing=study.previous.anchor.t.prior.helpers.existing
        existing.reflect(delta,chart,existing.symmetry(chart))
        if case=='GATE_LINTEL':
            import gate_members
            gate_members.reflect_axial_delta(delta,chart)
        error=float(np.abs(actual_delta-delta).max())
        assert error<1e-12 and np.max(np.abs(mesh.xyz-reference-delta))<1e-12
        inactive=copy.deepcopy(mesh);inactive.xyz=reference.copy()
        before=study.native_sampler(inactive,chart);after=study.native_sampler(mesh,chart)
        native=study.previous.anchor.t.growth.native(mesh)
        with np.load(folder/'geometry.npz') as data:
            assert np.array_equal(data['xyz'],native.xyz)
            assert np.array_equal(data['faces'],native.faces[:,:3])
        children=[]
        for rail in rails:
            assert np.all(rail['depth']<=.4*rail['parent_depth']+1e-12)
            assert np.all(rail['child_owned_arc_fraction'][:,0]>=.25)
            uv=np.column_stack([rail['parameter'],rail['parent_valley_cross']])
            motion=np.linalg.norm(after.sample(uv)-before.sample(uv),axis=1)
            detected=[]
            for i in np.flatnonzero(np.abs((rail['parameter']-rail['parameter'].mean())/np.ptp(rail['parameter']))<=.3):
                cross=np.linspace(rail['lower_cross'][i],rail['upper_cross'][i],129)
                uv_child=np.column_stack([np.full(len(cross),rail['parameter'][i]),cross])
                normal=rail['normal'][i]
                a,b=before.sample(uv_child)@normal,after.sample(uv_child)@normal
                old,_=find_peaks(-a,prominence=.04*rail['depth'][i])
                new,_=find_peaks(-b,prominence=.04*rail['depth'][i])
                width=np.ptp(cross)
                new_near=[p for p in new if abs(cross[p]-rail['guide_cross'][i])<.2*width
                    and not np.any(abs(cross[old]-cross[p])<.08*width)]
                detected.append(bool(new_near))
            children.append(dict(parent_guide=int(rail['parent_guide_index']),
                maximum_parent_valley_motion_matched_g4=float(motion.max()),
                median_parent_valley_motion_matched_g4=float(np.median(motion)),
                maximum_child_parent_depth_ratio=float((rail['depth']/rail['parent_depth']).max()),
                child_cuts_with_new_basin=sum(detected),child_finite_cuts=len(detected),
                interpolated_rays=int(rail['interpolated_ray_count'])))
        records.append(dict(case=case,replay_max_error=error,children=children))
    output.write_text(json.dumps(dict(status='PASS',expected_cases=list(cases),records=records,
        scope='Saved child operation and actual native replay; finite matched inactive-G4 cuts. New-basin counts are diagnostics, not aesthetic or continuous hierarchy certification.',
        retention_note='Original first-run generation.json compared G3 and G4 affine-chart samples. This receipt uses matched G4 reference and excludes that chart-sampling drift.'),indent=2),encoding='utf8')
    print(json.dumps(records,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',nargs='+',choices=CASES,default=['SPAN','COUNTER'])
    args=p.parse_args();run(args.root.resolve(),args.output.resolve(),args.cases)
