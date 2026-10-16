"""Replace only the saved G7 CHILD/SMALL support on its retained carrier.

Caller supplies exact neutral G7 + preserved primary_delta. No G6 contribution
is removed, no new source-role mask is imposed, and no old CHILD/SMALL is added.
Actual finite power8 boundary geometry is pulled back through inherited detail
coordinates and the actual carrier's intrinsic phase direction.
"""
from pathlib import Path
import importlib.util
import numpy as np

HERE=Path(__file__).resolve().parent
PROFILE_PATH=HERE/'mandelbulb_surface_replacement.py'
OLD_PATH=HERE.parent/'parent_nested_folds_20261014/parent_nested_readable.py'
def _module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
profiles=_module('g7_only_actual_mandel_boundary',PROFILE_PATH)
old=_module('g7_only_frozen_support_normals',OLD_PATH)
CHUNK=65536
NORMAL_LIMIT=.035
NORMAL_WIDTH_RATIO=.30
B_WIDTH_RATIO=.12


def helper_paths():
    return list(dict.fromkeys([Path(__file__).resolve(),PROFILE_PATH,OLD_PATH,
        *profiles.helper_paths(),*old.helper_paths()]))


def _phase_gradient(xyz,quads,phase,degree):
    total=np.zeros_like(xyz,dtype=float);invalid=0
    for first in range(0,len(quads),CHUNK):
        q=quads[first:first+CHUNK];p=xyz[q]
        e1=p[:,1]-p[:,3];e2=p[:,2]-p[:,0]
        a=np.einsum('ij,ij->i',e1,e1);b=np.einsum('ij,ij->i',e1,e2);c=np.einsum('ij,ij->i',e2,e2)
        det=a*c-b*b;valid=(a>0.)&(c>0.)&(det>1e-8*a*c)
        d1=phase[q[:,1]]-phase[q[:,3]];d2=phase[q[:,2]]-phase[q[:,0]]
        x=np.divide(c*d1-b*d2,det,out=np.zeros_like(det),where=valid)
        y=np.divide(a*d2-b*d1,det,out=np.zeros_like(det),where=valid)
        gradient=x[:,None]*e1+y[:,None]*e2
        invalid+=int((~valid).sum())
        for axis in range(3):total[:,axis]+=np.bincount(q.ravel(),weights=np.repeat(gradient[:,axis],4),minlength=len(xyz))
    total/=degree[:,None]
    return total,invalid


def build(carrier_xyz,quads,inherited_phase,parent_mask,child_budget,local_flank_width,
          vx,vy,H,*,longitudinal=None,profile=None):
    """Return ``(outputXYZ, metadata, flat_NPZ_state)``.

    ``parent_mask`` and physical width must be the exact saved NESTED02 arrays.
    The budget is retained as provenance, not multiplied a second time into the
    visible radius relief. If supplied, longitudinal is the inherited material
    coordinate, never a new world-space angle or artist-selected patch.
    """
    xyz=np.asarray(carrier_xyz);q=np.asarray(quads);phase=np.asarray(inherited_phase)
    mask=np.asarray(parent_mask);budget=np.asarray(child_budget);width=np.asarray(local_flank_width)
    nv=len(xyz)
    if xyz.shape!=(nv,3) or q.ndim!=2 or q.shape[1]!=4 or q.dtype.kind not in 'iu':
        raise ValueError('Actual G7 all-quad carrier required.')
    if any(v.shape!=(nv,) for v in (phase,mask,budget,width)) or not all(np.isfinite(v).all() for v in (xyz,phase,mask,budget,width)):
        raise ValueError('Exact finite saved G7 support/phase/budget/width arrays required.')
    if np.any(mask<0.) or np.any(mask>1.+1e-12) or np.any(width<0.) or np.any(budget<0.):
        raise ValueError('Nonnegative saved widths/budgets and unit compact support required.')
    if longitudinal is None:
        long=np.zeros(nv);long_source='Fixed meridian; no longitudinal coordinate supplied.'
    else:
        long=np.asarray(longitudinal)
        if long.shape!=(nv,) or not np.isfinite(long).all():raise ValueError('Finite inherited longitudinal coordinate required.')
        long_source='Caller-supplied inherited longitudinal material coordinate; two full angular periods.'
    ids,pairs=old.field._mirror_pairs({'X':vx,'Y':vy},nv)
    if profile is None:profile,profile_metadata,profile_evidence=profiles.build_profile(power=8,iterations=8)
    else:profile_metadata=profile.metadata;profile_evidence={}
    degree=np.bincount(q.ravel(),minlength=nv)
    if np.any(degree==0):raise ValueError('Orphan G7 controls are not repaired.')
    print('G7_DETAIL_MB: fresh retained-carrier normals and intrinsic phase direction',flush=True)
    normal=old.field._input_normals(xyz,q)
    gradient,invalid=_phase_gradient(xyz,q,phase,degree)
    gradient-=normal*np.einsum('ij,ij->i',gradient,normal)[:,None]
    gradient_norm=np.linalg.norm(gradient,axis=1)
    across=np.divide(gradient,gradient_norm[:,None],out=np.zeros_like(gradient),where=gradient_norm[:,None]>1e-14)
    wrapped=np.arctan2(np.sin(phase),np.cos(phase))
    across*=np.where(wrapped>=0.,1.,-1.)[:,None]
    del gradient
    coordinate=(np.abs(wrapped)-.55)/1.8
    active=np.flatnonzero(mask>0.)
    delta=np.zeros_like(xyz,dtype=float);normal_scalar=np.zeros(nv);across_scalar=np.zeros(nv)
    for first in range(0,len(active),131072):
        take=active[first:first+131072]
        # One primary polar formation across the authored G7 flank, with the
        # actual bulb's smaller boundary structures inside it. The azimuth is
        # inherited material flow, not a world-coordinate repeating coating.
        theta=np.pi/2.+.70*(coordinate[take]-.5)
        phi=np.mod(4.*np.pi*long[take],2.*np.pi)
        radius=profile._spline.ev(theta,phi)
        relief=np.clip((radius-profile.centre)/profile.scale,-1.,1.)
        polar_gradient=profile._spline.ev(theta,phi,dx=1,dy=0)/profile.scale
        normal_amplitude=np.minimum(NORMAL_LIMIT,NORMAL_WIDTH_RATIO*width[take])
        dn=normal_amplitude*relief*mask[take]
        db=-np.minimum(B_WIDTH_RATIO*width[take],.5*normal_amplitude)*np.tanh(polar_gradient/4.)*mask[take]
        move=dn[:,None]*normal[take]+db[:,None]*across[take]
        delta[take]=move;normal_scalar[take]=dn;across_scalar[take]=db
    delta=old.field._transport(delta,ids,pairs)[0]
    delta[mask==0.]=0.
    output=xyz+delta
    output[mask==0.]=xyz[mask==0.]
    if not np.isfinite(output).all() or not np.array_equal(output[mask==0.],xyz[mask==0.]):
        raise ValueError('Replacement moved protected retained-carrier geometry.')
    metadata=dict(implementation='EXACT_G7_NESTED_SUPPORT_MANDELBULB_BOUNDARY_REPLACEMENT_V1',
        source_generation=7,output_generation=7,added_subdivision_passes=0,
        support='Exact saved NESTED02 parent_mask; all original roles, no new SOURCE/attachment/body mask.',
        preserved='Caller exact neutralG7+primary_delta carrier. Original delta_child/delta_small are not inputs and are not added back.',
        outside_support_exact=True,protected_controls=int((mask==0.).sum()),
        supported_controls=len(active),moved_controls=int((np.linalg.norm(delta,axis=1)>1e-12).sum()),
        maximum_displacement=float(np.linalg.norm(delta,axis=1).max(initial=0.)),
        maximum_requested_normal_relief=float(np.abs(normal_scalar).max(initial=0.)),
        maximum_requested_B_relief=float(np.abs(across_scalar).max(initial=0.)),
        normal_limit=NORMAL_LIMIT,normal_width_ratio=NORMAL_WIDTH_RATIO,B_width_ratio=B_WIDTH_RATIO,
        normal_rule='min(.035,.30*saved local flank width)*normalized actual finite bulb radial deviation*saved parent_mask.',
        across_rule='-min(.12*saved local flank width,.5*normal amplitude)*tanh(actual normalized bulb polar-radius derivative/4)*saved parent_mask, along positive authored flank coordinate. Same boundary geometry, no separate noise.',
        polar_mapping='theta=pi/2+.70*((abs(wrapped inherited phase)-.55)/1.8-.5): approximately one power8 polar lobe across each original G7 support band.',
        azimuth_mapping='phi=4*pi*inherited longitudinal material coordinate, wrapped continuously at2pi.',
        longitudinal_source=long_source,
        actual_normal_evaluation=True,intrinsic_phase_invalid_quads=invalid,
        zero_intrinsic_direction_supported_vertices=int(((gradient_norm<=1e-14)&(mask>0.)).sum()),
        inherited_child_budget_quantiles=np.quantile(budget,[0.,.5,.9,.99,1.]).tolist(),
        budget_scope='Old child budget retained for source provenance; replacement uses its saved physical flank width and declared visible cap, not a second tiny multiplicative budget.',
        profile=profile_metadata,geometry='Finite3D Mandelbulb radial-boundary pullback with normal and same-boundary-derived B components; not full volumetric topology or a target projection.',
        source_geometry_faired=False,delta_blurred=False,world_angle_mapping=False,
        global_self_intersection_checked=False,aesthetic_success='Pending matched actual native render.')
    state=dict(delta_mandel=delta,normal_scalar=normal_scalar,across_scalar=across_scalar,
        inherited_parent_mask=mask,inherited_child_budget=budget,inherited_local_flank_width=width,
        inherited_flank_coordinate=coordinate,**{'profile_'+key:value for key,value in profile_evidence.items()})
    return output,metadata,state
