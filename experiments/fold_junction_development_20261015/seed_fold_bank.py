"""Exact authored SPAN fold-family descriptors and material-coordinate roots.

This exposes the existing G0/G2 construction bank. It does not generate a mesh
or select an individual ornament. W is evaluated forward and inverted by a
root solve; a separately fitted inverse PCHIP would not be equivalent.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'src'))

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

seed=module('seed_bank_original_mass',HERE.parent/'column_development_20261011/seed_mass.py')
overlap=module('seed_bank_original_overlap',HERE.parent/'directional_growth_20261012/overlap_probe.py')
smooth=seed.old
legacy=smooth.repair.legacy
WARP_X=np.asarray([0.,.15,.33,.50,.70,.85,1.])
WARP_Y=np.asarray([0.,.18,.34,.51,.72,.86,1.])
WARP=PchipInterpolator(WARP_X,WARP_Y)
G0=Path('E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()

def helper_paths():
    return [Path(seed.__file__),Path(seed.source.__file__),Path(smooth.__file__),
            Path(smooth.repair.__file__),Path(legacy.__file__),Path(overlap.__file__)]

def build_bank():
    recipe=json.loads((G0/'generation.json').read_text(encoding='utf8'))['recipe']
    events=[]
    for tier,bank in sorted(legacy.EVENTS.items()):
        for original in bank:
            event=copy.deepcopy(original)
            for key in ('expansion','reexpansion','constriction','return_depth'):
                event[key]*=(1.65 if key in ('expansion','reexpansion') else
                             1.35 if key=='constriction' else 1.50) if tier==1 else 1.25
            events.append(dict(bank_id='G0_LEGACY_TIER'+str(tier)+'_'+event['id'],
                actual_insertion_stage='G0_SEED',legacy_recipe_tier=int(tier),
                event=event,coordinate='SPAN_WARPED_MATERIAL_T',amplitude_multiplier=1.,
                retention='Full tier1. Tier2/3 multiplied by incoming initial-memory complement and final smooth_valley protection complement.'))
    events.append(dict(bank_id='G0_OVERRUNNING_'+recipe['events'][-1]['id'],
        actual_insertion_stage='G0_SEED',legacy_recipe_tier=None,
        event=copy.deepcopy(recipe['events'][-1]),coordinate='CURRENT_MATERIAL_T',
        amplitude_multiplier=.36,retention='Added outside legacy initial-memory/valley-complement composition.'))
    for original in overlap.EVENTS:
        events.append(dict(bank_id='G2_'+original['id'],actual_insertion_stage='BEFORE_G2_TASK36',
            legacy_recipe_tier=None,event=copy.deepcopy(original),coordinate='CURRENT_MATERIAL_T',
            amplitude_multiplier=1.,retention='Applied to actual G1 controls before G2 Task36/finite field; no initial-memory mask.'))
    for descriptor in events:
        e=descriptor['event'];rp=[0,.1*e['expansion'],.62*e['expansion'],e['expansion'],
            .3*e['expansion'],-e['constriction'],-.35*e['constriction'],e['reexpansion'],.4*e['reexpansion'],0]
        zp=e['return_depth']*np.asarray([0,0,.2,1,.6,-.6,-1,-.2,0,0])
        descriptor['profile']=dict(u_knots=smooth.KNOTS.tolist(),radial_values=rp,
            axial_values=zp.tolist(),radial_PCHIP_coefficients=PchipInterpolator(smooth.KNOTS,rp).c.tolist(),
            axial_PCHIP_coefficients=PchipInterpolator(smooth.KNOTS,zp).c.tolist(),
            principal_features_u=dict(radial_expansion_crest=-.35,radial_constriction=.15,radial_reexpansion_crest=.75,
                                      positive_axial_return=-.35,negative_axial_return=.35))
    paths=[Path(__file__),*helper_paths(),HERE.parent/'fold_band_growth_20261011/sparse_input.py',G0/'generation.json',G0/'control_quad.npz']
    return dict(schema='EXACT_ORIGINAL_SPAN_AUTHORED_FOLD_BANK_V1',date='2026-10-15',events=events,
        source_hashes={str(p):sha(p) for p in dict.fromkeys(paths)},
        warp=dict(current_material_knots=WARP_X.tolist(),source_material_values=WARP_Y.tolist(),
            forward_PCHIP_coefficients=WARP.c.tolist(),coefficient_convention='c[j,i]*(t-x[i])**(3-j)',
            inverse='Solve W(t)-s=0 on the corresponding monotone cubic interval. Do not fit PCHIP with swapped knots.'),
        equations=dict(s='W(current_t) for G0 legacy bank; current_t for bridge and G2 returns',
            centre='direction+sweep*sin(pi*(s-height)/.32); optional second centre pi-centre if mirror',
            distance='d=atan2(sin(theta-centre),cos(theta-centre))',
            local_height='height+.05*clip(abs(d)/overlap_width,0,1)**1.4',
            u='(s-local_height)/span',
            angular_wave='q=clip(abs(d)/width,0,1); r=(sqrt(q*q+.12**2)-.12)/(sqrt(1+.12**2)-.12); wave=1-1.5*r+.5*r**3',
            displacement='multiplier*window(s-.5,.40,.49)*sum_centres(wave*[PCHIP_radial(u)*cos(theta),PCHIP_radial(u)*sin(theta),PCHIP_axial(u)])',
            window='1-a*a*(3-2*a), a=clip((abs(x)-inner)/(outer-inner),0,1)'),
        G0_composition=dict(initial_memory='Within source.initial, tiers1/2/3 add their smooth_event sum times(1-memory). After each event memory=max(memory,line_memory(event)*(1-memory)).',
            valley='Final legacy result=birth_after_tier1+smooth_valley_offset+(all_tier_result-birth)*(1-protect). smooth_valley temporarily uses the scaled legacy bank.',
            legacy_core='source.initial(warped)-old_terminal_bottom(warped)-old_terminal_top(warped)-old_cylinder(warped) + current proportional cylinder + .36*current bridge + current end_returns.',
            terminal='New end_returns and sampled cap radius/depth are separate bounded closures, not members of the longitudinal fold bank.',
            generations='Legacy recipe tiers1/2/3 are all already composed into actual G0; they are not actual current mesh generations.'),
        intended_parent_frame='theta-longitudinal, material-t-cross. Event u features are material cross rails along each theta; the current actual mesh must supply XYZ/tangent/normal/depth before a reusable smaller RETURN.',
        limitation='Construction provenance identifies active source families, not exact additive causal attribution after Task36, finite-field movement, G3 WALL and later geometry-dependent operations.')

def event_coordinates(descriptor,current_t,theta):
    t,theta=np.broadcast_arrays(np.asarray(current_t,dtype=float),np.asarray(theta,dtype=float))
    s=WARP(t) if descriptor['coordinate']=='SPAN_WARPED_MATERIAL_T' else t
    e=descriptor['event'];centre=e['direction']+e['sweep']*np.sin(np.pi*(s-e['height'])/.32)
    centres=[centre,np.pi-centre] if e['mirror'] else [centre]
    result=[]
    for a in centres:
        d=np.arctan2(np.sin(theta-a),np.cos(theta-a))
        q=np.clip(abs(d)/e['overlap_width'],0,1)
        rounded=(np.sqrt(q*q+.12**2)-.12)/(np.sqrt(1+.12**2)-.12)
        wave=1-1.5*rounded+.5*rounded**3
        u=(s-(e['height']+.05*q**1.4))/e['span']
        result.append((u,wave))
    return s,result

def evaluate_event(descriptor,current_t,theta):
    s,coordinates=event_coordinates(descriptor,current_t,theta)
    profile=descriptor['profile'];radial=np.zeros_like(s);axial=np.zeros_like(s)
    pr=PchipInterpolator(profile['u_knots'],profile['radial_values'],extrapolate=False)
    pz=PchipInterpolator(profile['u_knots'],profile['axial_values'],extrapolate=False)
    for u,wave in coordinates:
        radial+=np.nan_to_num(pr(u))*wave;axial+=np.nan_to_num(pz(u))*wave
    window=legacy.window(s-.5,.40,.49)*descriptor['amplitude_multiplier']
    theta=np.broadcast_to(np.asarray(theta),s.shape)
    return np.stack((radial*np.cos(theta),radial*np.sin(theta),axial),axis=-1)*window[...,None]

def material_roots(descriptor,theta,u_level,*,samples=1025,centre_index=0):
    """All exact current-material roots for each supplied angular station.

    No local-linear span approximation. Multiple branches remain a root list
    for the caller to track/validate, not an arbitrary nearest-root choice.
    """
    grid=np.linspace(0.,1.,samples);output=[]
    for angle in np.atleast_1d(theta):
        values=event_coordinates(descriptor,grid,float(angle))[1][centre_index][0]-u_level
        roots=[]
        for i in np.flatnonzero(values[:-1]*values[1:]<=0):
            value=brentq(lambda t:float(event_coordinates(descriptor,t,float(angle))[1][centre_index][0]-u_level),
                         float(grid[i]),float(grid[i+1]),xtol=1e-13)
            if not roots or abs(value-roots[-1])>1e-9:roots.append(value)
        output.append(roots)
    return output

def main():
    target=HERE/'actual_seed_fold_events.json'
    if target.exists():raise FileExistsError(target)
    bank=build_bank()
    with target.open('x',encoding='utf8') as stream:
        json.dump(bank,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(output=str(target),events=[e['bank_id'] for e in bank['events']]),indent=2))

if __name__=='__main__':main()
