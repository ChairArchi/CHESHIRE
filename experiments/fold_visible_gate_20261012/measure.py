"""Unfiltered native wall cuts and matched-render difference diagnostics.

Wall residual is distance from each cut side's best straight projected line;
it is a local planarity diagnostic, not an aesthetic score. Image differences
include lighting response and are never treated as geometry certification.
"""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image

import study


def cut(sampler,rail,parameter):
    interp=lambda values:np.interp(parameter,rail['parameter'],values)
    lo,mid,hi=[interp(rail[key]) for key in ('lower_cross','guide_cross','upper_cross')]
    v=np.linspace(-1,1,257)
    cross=np.where(v<0,mid+v*(mid-lo),mid+v*(hi-mid))
    uv=np.column_stack([np.full(len(v),parameter),cross])
    xyz=sampler.sample(uv)
    normal=np.array([interp(rail['normal'][:,i]) for i in range(3)])
    normal/=np.linalg.norm(normal)
    height=xyz@normal
    side_masks=[(v>=-.65)&(v<=-.20),(v>=.20)&(v<=.65)]
    residuals=[];directions=[]
    for mask in side_masks:
        coefficient=np.polyfit(v[mask],height[mask],1)
        residuals.extend((height[mask]-np.polyval(coefficient,v[mask])).tolist())
        direction=np.polyfit(v[mask],xyz[mask],1)[0]
        directions.append(direction/np.linalg.norm(direction))
    left,right=np.interp([-.65,.65],v,height)
    near=np.abs(v)<.2
    trough=np.flatnonzero(near)[np.argmin(height[near])]
    chord=left+(right-left)*(v[trough]+.65)/1.3
    metrics=dict(wall_line_residual_rms=float(np.sqrt(np.mean(np.square(residuals)))),
        near_guide_chord_relief=float(chord-height[trough]),
        profile_turn_degrees=float(np.degrees(np.arccos(np.clip(np.dot(*directions),-1,1)))),
        trough_transverse_fraction=float(v[trough]))
    return metrics,dict(xyz=xyz,material_uv=uv,normal=normal,transverse_fraction=v)


def render_difference(before,after):
    with Image.open(before) as a,Image.open(after) as b:
        x,y=np.asarray(a.convert('RGB'),dtype=float),np.asarray(b.convert('RGB'),dtype=float)
    if x.shape!=y.shape:
        raise ValueError('Matched image dimensions required.')
    foreground=(x.mean(axis=2)>100)|(y.mean(axis=2)>100)
    difference=np.abs(x-y).mean(axis=2)
    return dict(foreground_pixels=int(foreground.sum()),
        mean_absolute_rgb_difference=float(difference[foreground].mean()),
        fraction_foreground_over_12_rgb_difference=float((difference[foreground]>12).mean()),
        threshold=12,scope='Matched full images; lighting, antialiasing and denoising included. Not an aesthetic quality score.')


def run(root):
    records=[];image_records=[]
    for case in ('SPAN','COUNTER','GATE_COLUMN','GATE_LINTEL'):
        for mode in ('CONTROL','PREVIOUS','DEPTH','WALL'):
            folder=root/mode/case/'G03'
            mesh,chart,_=study.previous.anchor.t.load(folder)
            sampler=study.native_sampler(mesh,chart)
            profiles={};cuts=[]
            for index in (0,1):
                with np.load(folder/f'rails_{index}.npz') as data:
                    rail={key:data[key] for key in data.files}
                parameters=rail['parameter']
                for ray,fraction in enumerate(np.linspace(.25,.75,7)):
                    parameter=parameters[0]+fraction*np.ptp(parameters)
                    metrics,arrays=cut(sampler,rail,parameter)
                    cuts.append(dict(guide=index,ray=ray,parameter=float(parameter),**metrics))
                    profiles.update({f'g{index}_r{ray}_{key}':value for key,value in arrays.items()})
            result=dict(case=case,mode=mode,finite_cuts=len(cuts),cuts=cuts,
                median_wall_line_residual_rms=float(np.median([c['wall_line_residual_rms'] for c in cuts])),
                median_near_guide_chord_relief=float(np.median([c['near_guide_chord_relief'] for c in cuts])),
                median_profile_turn_degrees=float(np.median([c['profile_turn_degrees'] for c in cuts])),
                scope='Fourteen unfiltered finite material cuts; common pooled source normals. No full-surface quality, collision, fabrication or continuous-hierarchy certification.')
            np.savez_compressed(folder/'wall_profiles.npz',**profiles)
            (folder/'wall_measurements.json').write_text(json.dumps(result,indent=2),encoding='utf8')
            records.append({key:value for key,value in result.items() if key!='cuts'})
            if case in ('SPAN','COUNTER') and mode!='CONTROL':
                for view in ('front','oblique','side'):
                    a=root/'CONTROL'/case/'G03/views'/(view+'.png');b=folder/'views'/(view+'.png')
                    if a.exists() and b.exists():
                        image_records.append(dict(case=case,mode=mode,view=view,**render_difference(a,b)))
    for mode in ('PREVIOUS','DEPTH','WALL'):
        for view in ('front','oblique','side'):
            a=root/'assemblies/CONTROL/views'/(view+'.png');b=root/'assemblies'/mode/'views'/(view+'.png')
            if a.exists() and b.exists():
                image_records.append(dict(case='GATE',mode=mode,view=view,**render_difference(a,b)))
    (root/'wall_summary.json').write_text(json.dumps(dict(cuts=records,images=image_records),indent=2),encoding='utf8')
    print(json.dumps(records,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root.resolve())
