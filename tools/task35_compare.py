"""Causal, physical-scale and sampling diagnostics for the fixed Task35 cases."""
import json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'tools'))
from task33_preserve import sha,write_new
ROOT=Path('E:/CHESHIRE_DATA/task35')


def load(tag,stage,file='formation_state.npz'):
    return dict(np.load(ROOT/'candidates'/tag/stage/file))


def pair(current,frozen):
    a=ROOT/'candidates'/current;b=ROOT/'candidates'/frozen;matched={}
    for name in ['G0_CARRIER','G3_FORM','G4_PRE','G4_FOLD','G7_PRE']:
        matched[name]=dict(mesh_sha_equal=sha(a/name/'mesh.npz')==sha(b/name/'mesh.npz'),
            xyz_max=float(abs(load(current,name)['grid']-load(frozen,name)['grid']).max()))
    ac=load(current,'G7_FOLD','control_state.npz');bc=load(frozen,'G7_FOLD','control_state.npz')
    delta=load(current,'G7_FOLD')['grid']-load(frozen,'G7_FOLD')['grid']
    fields={k:dict(max=float(abs(ac[k]-bc[k]).max()),rms=float(np.sqrt(np.mean((ac[k]-bc[k])**2)))) for k in ['requested_signed_distance','read_broadness','read_slope','angular_displacement','axial_redistribution','measured_span_phase'] if k in ac and k in bc}
    return dict(current=current,frozen=frozen,pre_fold_matches=matched,control_differences=fields,
        final_xyz_max=float(np.linalg.norm(delta,axis=-1).max()),final_xyz_rms=float(np.sqrt(np.mean(delta**2))),
        producer_core_sha_equal=json.loads((a/'source_identity.json').read_text())['src/cheshire/task35_columns.py']==json.loads((b/'source_identity.json').read_text())['src/cheshire/task35_columns.py'])


def fan(q,u,v):
    c=q.mean(axis=1)
    if v<=u and v<=1-u:return (1-u-v)*q[:,0]+(u-v)*q[:,1]+2*v*c
    if u>=v and u>=1-v:return (u-v)*q[:,1]+(u+v-1)*q[:,2]+2*(1-u)*c
    if v>=u and v>=1-u:return (u+v-1)*q[:,2]+(v-u)*q[:,3]+2*(1-v)*c
    return (v-u)*q[:,3]+(1-u-v)*q[:,0]+2*u*c


def bilinear(q,u,v):return (1-u)*(1-v)*q[:,0]+u*(1-v)*q[:,1]+u*v*q[:,2]+(1-u)*v*q[:,3]


def sampling_difference(tag,before,mode):
    s=load(tag,before);g=s['grid'];q=np.stack([g[:-1],np.roll(g[:-1],-1,axis=1),np.roll(g[1:],-1,axis=1),g[1:]],axis=2).reshape(-1,4,3)
    errors=[]
    for u in [.125,.375,.625,.875]:
        for v in [.125,.375,.625,.875]:
            u0=.5*(u>=.5);u1=u0+.5
            v0=.5*(v>=.5) if mode=='both' else 0.;v1=v0+.5 if mode=='both' else 1.
            child=np.stack([bilinear(q,u0,v0),bilinear(q,u1,v0),bilinear(q,u1,v1),bilinear(q,u0,v1)],axis=1)
            errors.append(np.linalg.norm(fan(q,u,v)-fan(child,(u-u0)/(u1-u0),(v-v0)/(v1-v0)),axis=1))
    return dict(candidate=tag,before=before,mode=mode,per_cell_domain_samples=16,max_surface_difference=float(np.max(errors)),
        rms_surface_difference=float(np.sqrt(np.mean(np.asarray(errors)**2))),
        limits='Finite corresponding material-domain surface samples, not Hausdorff certification. Grid stencils retain old samples, but native centre-fan triangulation can change between samples; no XYZ smoothing operation is called.')


def main(tag):
    dest=ROOT/'measurements'/tag;dest.mkdir(parents=True,exist_ok=False)
    causal=[pair('A04_VARIED_REGIONAL','C06_FROZEN_FORM'),pair('E08_SUBCRITICAL_CURRENT','E09_SUBCRITICAL_FROZEN')]
    ablations=[]
    base=load('A04_VARIED_REGIONAL','G4_FOLD','control_state.npz')['requested_signed_distance']
    for other in ['C01_CHORD_OFF','C02_DIRECTION_OFF','C03_AXIAL_OFF','C04_BRANCH_OFF','C05_AMPLITUDE_ONLY']:
        current=load(other,'G4_FOLD','control_state.npz')['requested_signed_distance'];scale=np.sum(base*current,axis=1)/np.maximum(np.sum(current*current,axis=1),1e-30)
        residual=base-scale[:,None]*current;denom=np.maximum(np.linalg.norm(base,axis=1),1e-30)
        ablations.append(dict(other=other,first_formation_xyz_max=float(abs(load('A04_VARIED_REGIONAL','G3_FORM')['grid']-load(other,'G3_FORM')['grid']).max()),
            same_strength_profile_residual_max=float(abs(base-current).max()),max_best_amplitude_fit_relative_residual=float((np.linalg.norm(residual,axis=1)/denom).max()),
            limit='C05 changes Task34 profile family as well as orientation/branch policy; it is a comparator, not a pure ablation.'))
    dense=load('E02_COUPLED_FOLDS','G7_FOLD');coarse=load('F01_ANGULAR_G6','G6_FOLD')
    ca=load('E02_COUPLED_FOLDS','G7_FOLD','control_state.npz');cb=load('F01_ANGULAR_G6','G6_FOLD','control_state.npz')
    resolution=dict(fine_grid=list(dense['grid'].shape[:2]),coarse_grid=list(coarse['grid'].shape[:2]),
        common_grid_xyz_max=float(abs(dense['grid'][:,::2]-coarse['grid']).max()),
        common_requested_distance_max=float(abs(ca['requested_signed_distance'][:,::2]-cb['requested_signed_distance']).max()),
        note='Halving the angular cell size does not halve the physical displacement. Different native tessellation still requires independent contact/cut checks.')
    plate=[]
    for candidate in ['A04_VARIED_REGIONAL','D03_WAVE_AND_FAN','E02_COUPLED_FOLDS','G02_PARENT_SPLIT']:
        stages={};reference=load(candidate,'G3_FORM')['s'];body_s=reference[(reference*4000>=900-1e-8)&(reference*4000<=1500+1e-8)]
        for stage in ['G3_FORM','G4_FOLD','G7_FOLD']:
            s=load(candidate,stage);body=np.array([np.flatnonzero(np.isclose(s['s'],v,rtol=0,atol=1e-14))[0] for v in body_s]);xy=s['grid'][body,:,:2]
            stages[stage]=dict(body_XY_range_max=float(np.linalg.norm(np.ptp(xy,axis=0),axis=-1).max()),
                material_height_range=[float(s['s'][body].min()*4000),float(s['s'][body].max()*4000)])
        plate.append(dict(candidate=candidate,stages=stages,note='Actual native grid variation within the preregistered long body; this quantifies departure from extrusion, not aesthetic quality or a full surface-flatness metric.'))
    sampling=[sampling_difference('E02_COUPLED_FOLDS','G3_FORM','both'),sampling_difference('E02_COUPLED_FOLDS','G4_FOLD','angular'),sampling_difference('E02_COUPLED_FOLDS','G6_PRE','angular')]
    late=load('F02_FORM_LATER','G7_FOLD');formation_delta=load('E02_COUPLED_FOLDS','G3_FORM')['grid']-load('F02_FORM_LATER','G4_FORM')['grid'][::2,::2]
    later_form=dict(common_first_formation_xyz_max=float(abs(formation_delta).max()),final_xyz_max=float(np.linalg.norm(dense['grid']-late['grid'],axis=-1).max()),
        final_xyz_rms=float(np.sqrt(np.mean((dense['grid']-late['grid'])**2))),
        limits='Postponed first formation and first refolding together by one sampling stage; this separates formation sampling from final resolution, not every schedule effect independently.')
    write_new(dest/'result.json',dict(causal=causal,ablations=ablations,angular_resolution=resolution,long_body_extrusion=plate,sampling=sampling,later_formation=later_form,producer_sha256=sha(Path(__file__))))
    print(json.dumps(dict(causal=causal,angular_resolution=resolution,long_body_extrusion=plate,sampling=sampling),indent=2))


if __name__=='__main__':main(sys.argv[1])
