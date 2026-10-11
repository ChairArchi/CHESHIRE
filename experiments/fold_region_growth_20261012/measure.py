"""Finite matched native material cuts for new basin evidence, without filters."""
from pathlib import Path
import argparse
import json

import numpy as np
from scipy.signal import find_peaks

import study
from region_fold import NativeChartSampler


def sampler(folder):
    mesh,chart,_=study.anchor.t.load(folder)
    native=study.anchor.t.growth.native(mesh)
    pchart=np.concatenate([chart,study.anchor.t.face_values(mesh,chart)])
    return NativeChartSampler(native.xyz,native.faces[:,:3],pchart)


def run(root):
    summary=[]
    for case in ('SPAN','COUNTER'):
        reference=sampler(root/'CONTROL'/case/'G03')
        for mode in ('GROOVE','RETURN'):
            folder=root/mode/case/'G03'
            actual=sampler(folder)
            profiles={};records=[]
            for index in (0,1):
                with np.load(folder/f'guide_{index}.npz') as data:
                    g={key:data[key] for key in data.files}
                for ray,fraction in enumerate(np.linspace(.2,.8,7)):
                    axis_values=g['parameter'] if 'parameter' in g else g['theta']
                    parameter=axis_values[0]+fraction*np.ptp(axis_values)
                    interp=lambda values:np.interp(parameter,axis_values,values)
                    cross_keys=(('lower_cross','upper_cross','guide_cross') if 'guide_cross' in g else
                        ('lower_s','upper_s','guide_s'))
                    lower,upper,middle=[interp(g[key]) for key in cross_keys]
                    normal=np.array([interp(g['normal'][:,i]) for i in range(3)])
                    normal/=np.linalg.norm(normal)
                    s=np.linspace(lower,upper,257)
                    axis=str(g.get('axis','theta'))
                    longitudinal=axis=='height'
                    uv=(np.column_stack([np.full(len(s),parameter),s]) if longitudinal else
                        np.column_stack([s,np.full(len(s),parameter)]))
                    before=reference.sample(uv);after=actual.sample(uv)
                    old=before@normal;new=after@normal
                    arc=interp(g['shoulder_length']);prominence=.04*arc
                    b_ids,b_info=find_peaks(-old,prominence=prominence)
                    n_ids,n_info=find_peaks(-new,prominence=prominence)
                    # A finite new basin must lie within 20% of the declared
                    # shoulder width of the new guide, and lack an old basin
                    # within 8% of that same width. Raw triangles, no filtering.
                    near=np.abs(s[n_ids]-middle)<.20*(upper-lower)
                    unmatched=np.array([not np.any(np.abs(s[b_ids]-s[p])<.08*(upper-lower)) for p in n_ids],dtype=bool)
                    new_ids=n_ids[near&unmatched]
                    records.append(dict(guide=index,ray=ray,parameter=float(parameter),parameter_axis=axis,
                        baseline_basins=int(len(b_ids)),output_basins=int(len(n_ids)),
                        new_near_guide_basins=int(len(new_ids)),
                        prominence_project_units=float(prominence),
                        maximum_inward_offset=float(np.max(old-new)),
                        new_basin_transverse_material_coordinates=s[new_ids].tolist(),
                        new_basin_prominences=n_info['prominences'][near&unmatched].tolist()))
                    key=f'g{index}_r{ray}'
                    profiles[key+'_xyz_before']=before;profiles[key+'_xyz_after']=after
                    profiles[key+'_material_uv']=uv;profiles[key+'_projection_normal']=normal
            np.savez_compressed(folder/'measured_profiles.npz',**profiles)
            result=dict(case=case,mode=mode,finite_cuts=len(records),
                cuts_with_new_near_guide_basin=sum(r['new_near_guide_basins']>0 for r in records),
                cuts=records,
                scope='14 finite material cuts per candidate, projection on measured source guide normal; not world-Z sections, global hierarchy certification or fold depth by shortest distance',
                detection='Unfiltered native triangle samples, prominence 4% of measured shoulder arc, new-basin location matching in transverse material coordinate')
            (folder/'basin_measurements.json').write_text(json.dumps(result,indent=2),encoding='utf8')
            summary.append({key:result[key] for key in ('case','mode','finite_cuts','cuts_with_new_near_guide_basin')})
    (root/'basin_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root.resolve())
