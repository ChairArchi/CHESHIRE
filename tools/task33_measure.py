"""Mesh-interpolated material cuts plus actual world-plane sections.

Material cuts follow the same carrier location, and can be nonplanar. World
Z cuts are separately computed from actual triangles, never analytic curves.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import ROOT,sha,write_new
from task29_search import load_mesh,save_mesh
from cheshire.task33_folds import evaluate
from cheshire.task32_morphology import triangles
from task32_validation import section_segments


def prepare_cuts(mesh,state):
    tri=triangles(mesh)
    # Actual front-material patches; not a projected silhouette.
    tri=tri[np.all(np.abs(state['chart'][tri,2]+1)<1e-10,axis=1)]
    values=state['chart'][tri,0]
    return tri,values.min(1),values.max(1)


def cut(mesh,state,s,reference,params,prepared=None):
    tri,lower,upper=prepare_cuts(mesh,state) if prepared is None else prepared
    chart=state['chart'];tri=tri[(lower<s)&(upper>s)]
    result=[]
    for j in range(3):
        a,b=tri[:,j],tri[:,(j+1)%3]
        good=(chart[a,0]<s)!=(chart[b,0]<s)
        a,b=a[good],b[good]
        t=(s-chart[a,0])/(chart[b,0]-chart[a,0])
        u=chart[a,1]*(1-t)+chart[b,1]*t
        xyz=mesh.xyz[a]*(1-t[:,None])+mesh.xyz[b]*t[:,None]
        base=reference.xyz[a]*(1-t[:,None])+reference.xyz[b]*t[:,None]
        result.append(np.column_stack([u,xyz,base]))
    pts=np.concatenate(result)
    pts=pts[np.argsort(pts[:,0])]
    _,ids=np.unique(np.round(pts[:,0],12),return_index=True);pts=pts[ids]
    path=np.array([[1,0],[1,0],[1,0],[2**-.5,-2**-.5],[0,-1],[-2**-.5,-2**-.5],[-1,0],[-1,0],[-1,0]])
    direction=np.array([np.interp(s,state['knots'],path[:,k]) for k in range(2)])
    direction/=np.linalg.norm(direction)
    angle=params.get('twist',0)*np.sin(2*np.pi*s/.31)*min(s/.055,1)**2*(3-2*min(s/.055,1))
    if 'twist_end' in params:
        envelope=np.clip((params['twist_end']-s)/(params['twist_end']-params.get('twist_start',.21)),0,1)
        angle*=envelope*envelope*(3-2*envelope)
    normal=np.array([direction[0]*np.sin(angle),-np.cos(angle),direction[1]*np.sin(angle)])
    tangent=np.array([direction[0]*np.cos(angle),np.sin(angle),direction[1]*np.cos(angle)])
    depth=(pts[:,1:4]-pts[:,4:7])@normal
    grid=np.linspace(-.98,.98,401)
    depth=np.interp(grid,pts[:,0],depth)
    xyz=np.column_stack([np.interp(grid,pts[:,0],pts[:,k]) for k in range(1,4)])
    return grid,depth,xyz,tangent


def measure(name,tag):
    job=ROOT/'candidates'/name
    request=json.loads((job/'request.json').read_text())
    final=Path(json.loads((job/'completed.json').read_text())['final_stage'])
    mesh=load_mesh(final)
    with np.load(final/'material_state.npz') as z:state={k:z[k].copy() for k in z.files}
    params=request.get('parameters',{})
    dest=ROOT/'analysis'/tag;dest.mkdir(parents=True,exist_ok=False)
    reference,_=evaluate(mesh,state,params,0)
    macro,_=evaluate(mesh,state,params,1)
    meso,_=evaluate(mesh,state,params,2)
    for label,m in [('counterfactual_carrier',reference),('counterfactual_macro',macro),('counterfactual_meso',meso)]:
        save_mesh(dest/label,m,dict(note='Matched-final-resolution counterfactual, not a generation checkpoint.',parameters=params))
    data={};rows=[]
    for s in [.06531,.10531,.15031,.19531,.24531,.31531,.43031,.48531]:
        profiles=[]
        for label,m in [('macro',macro),('meso',meso),('final',mesh)]:
            u,depth,xyz,tangent=cut(m,state,s,reference,params)
            data[f's{s}_{label}']=np.column_stack([u,depth,xyz])
            profiles.append(depth)
        macro_d,meso_d,final_d=profiles
        # 0.06 material-coordinate sigma, fixed across mesh resolutions.
        smooth=[gaussian_filter1d(d,.06/(u[1]-u[0])) for d in profiles]
        peaks,_=find_peaks(smooth[0],prominence=50)
        actual_peaks,_=find_peaks(smooth[2],prominence=50)
        meso_peaks,meso_properties=find_peaks(meso_d,prominence=25)
        final_peaks,final_properties=find_peaks(final_d,prominence=15)
        split=[]
        for peak in peaks:
            # Half-height parent basin, bounded to this same broad ridge.
            left=peak
            while left>0 and macro_d[left-1]>.5*macro_d[peak]:left-=1
            right=peak
            while right<len(u)-1 and macro_d[right+1]>.5*macro_d[peak]:right+=1
            if left<peak<right:
                split.append(dict(parent_u=float(u[peak]),
                    meso_internal_valley_depth=float(min(meso_d[left:peak].max(),meso_d[peak+1:right+1].max())-meso_d[peak]),
                    final_internal_valley_depth=float(min(final_d[left:peak].max(),final_d[peak+1:right+1].max())-final_d[peak])))
        span=float((xyz[peaks[-1]]-xyz[peaks[0]])@tangent) if len(peaks)>1 else None
        rows.append(dict(s=s,macro_peak_to_valley=float(np.ptp(macro_d)),final_peak_to_valley=float(np.ptp(final_d)),
            child_difference_peak_to_valley=float(np.ptp(meso_d-macro_d)),micro_difference_peak_to_valley=float(np.ptp(final_d-meso_d)),
            macro_ridge_u=u[peaks].tolist(),final_lowpass_ridge_u=u[actual_peaks].tolist(),macro_ridge_span=span,
            meso_peaks=u[meso_peaks].tolist(),final_peaks=u[final_peaks].tolist(),
            meso_peak_prominences=meso_properties['prominences'].tolist(),final_peak_prominences=final_properties['prominences'].tolist(),
            parent_internal_valleys=split,
            lowpass_correlation=float(np.corrcoef(smooth[0],smooth[2])[0,1]),
            lowpass_peak_to_valley_ratio=float(np.ptp(smooth[2])/np.ptp(smooth[0]))))
    section_info,segments=section_segments(mesh)
    data.update({'world_'+k:v for k,v in segments.items()})
    np.savez_compressed(dest/'profiles_sections.npz',**data)
    write_new(dest/'measurements.json',dict(candidate=name,stage=str(final),mesh_sha256=sha(final/'mesh.npz'),parameters=params,
        rows=rows,world_plane_sections=section_info,data_sha256=sha(dest/'profiles_sections.npz'),
        method='Intersections of actual fan triangles with fixed material-arc values; actual XYZ interpolated, front chart v=-1. Depth is measured relative to matched carrier along the rotated section normal. World-plane sections are independent trimesh cuts.',
        limitations='Material cuts may be nonplanar at shoulders. Fixed material lowpass sigma 0.06 and peak prominences 50/25/15 are descriptive, not pass thresholds. Curves are piecewise linear and resolution dependent; endpoint/cap regions excluded. No shading enters measurements. Three scale counterfactuals separate contributions but are not proof of aesthetic quality.'))
    print(name,[(r['s'],round(r['macro_peak_to_valley']),len(r['macro_ridge_u']),len(r['meso_peaks']),len(r['final_peaks']),round(r['lowpass_correlation'],3)) for r in rows])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    if not all(v.replace('_','').isalnum() for v in (a.candidate,a.tag)):raise ValueError('Safe names required.')
    measure(a.candidate,a.tag)
