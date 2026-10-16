"""Whole-carrier pullback of an actual finite 3D Mandelbulb boundary profile.

Caller first removes sub-cutoff detail to obtain a scale-separated carrier.
This module supplies its replacement geometry on every carrier vertex, without
UV/role masks, pasted meshes, finite outside-target grids or camera placement.
It is a spherical boundary-profile pullback, not full volumetric bulb topology.
"""
from pathlib import Path
import importlib.util

import numpy as np
from scipy.interpolate import RectBivariateSpline


HERE=Path(__file__).resolve().parent
MEMBERSHIP_PATH=HERE/'parent_local_mandelbulb.py'
_spec=importlib.util.spec_from_file_location('whole_carrier_true_bulb_membership',MEMBERSHIP_PATH)
bulb=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(bulb)
LATITUDE_SAMPLES=97
LONGITUDE_SAMPLES=192
RADIAL_SAMPLES=81
RADIAL_MAX=1.6
BISECTION_STEPS=12
TANGENT_RATIO=.15
TANGENT_CAP_RATIO=.20
AXIS_A=np.array([1.,2.,3.])/np.sqrt(14.)
AXIS_B=np.array([2.,-1.,0.])/np.sqrt(5.)


def helper_paths():
    return [Path(__file__).resolve(),MEMBERSHIP_PATH]


class BoundaryProfile:
    def __init__(self,theta,phi,radius,metadata):
        self.theta=theta;self.phi=phi;self.radius=radius
        self.metadata=metadata
        # Three complete periods put the evaluated central period far from
        # spline boundaries. No discontinuous longitude tiling edge is used.
        extended_phi=np.concatenate((phi-2.*np.pi,phi,phi+2.*np.pi))
        self._spline=RectBivariateSpline(theta,extended_phi,
            np.tile(radius,(1,3)),kx=3,ky=3,s=0.)
        self.centre=float((radius.min()+radius.max())*.5)
        self.scale=float((radius.max()-radius.min())*.5)
        if self.scale<=1e-10:raise ValueError('Finite Mandelbulb radial profile is constant.')

    def displace(self,carrier_xyz,carrier_normals,*,cutoff=.30,amplitude=.035,chunk=131072):
        return displace(carrier_xyz,carrier_normals,profile=self,
            cutoff=cutoff,amplitude=amplitude,chunk=chunk)


def build_profile(*,power=8,iterations=8):
    """Return (profile, JSON-safe metadata, complete small NPZ evidence).

    For each spherical direction, retain the largest finite-inside radius on
    an81-sample scan, then bisect its following outside bracket. Thin farther
    satellites may be missed; the radius is not an exact outermost-set proof.
    """
    if power<3 or iterations<3:raise ValueError('Power>=3 and iterations>=3 required.')
    theta=np.linspace(0.,np.pi,LATITUDE_SAMPLES)
    phi=2.*np.pi*np.arange(LONGITUDE_SAMPLES)/LONGITUDE_SAMPLES
    tt,pp=np.meshgrid(theta,phi,indexing='ij')
    directions=np.column_stack((np.sin(tt.ravel())*np.cos(pp.ravel()),
        np.sin(tt.ravel())*np.sin(pp.ravel()),np.cos(tt.ravel())))
    radii=np.linspace(0.,RADIAL_MAX,RADIAL_SAMPLES)
    last_inside=np.full(len(directions),-1,dtype=int)
    inside_counts=np.zeros(len(directions),dtype=int)
    for index,radius in enumerate(radii):
        inside=bulb.membership(radius*directions,power=power,iterations=iterations)
        last_inside[inside]=index;inside_counts+=inside
    if np.any(last_inside<0) or np.any(last_inside>=RADIAL_SAMPLES-1):
        raise ValueError('Finite radial scan lacks inside/outside endpoint brackets.')
    lower=radii[last_inside];upper=radii[last_inside+1]
    for _ in range(BISECTION_STEPS):
        mid=(lower+upper)*.5
        inside=bulb.membership(mid[:,None]*directions,power=power,iterations=iterations)
        lower=np.where(inside,mid,lower);upper=np.where(inside,upper,mid)
    upper_escaped=~bulb.membership(upper[:,None]*directions,power=power,iterations=iterations)
    if not upper_escaped.all():raise ValueError('Final radial exterior samples failed membership check.')
    radius=((lower+upper)*.5).reshape(tt.shape)
    # All longitudes represent the identical geometric direction at either
    # pole. Round-off must not manufacture a pole seam.
    radius[0]=radius[0].mean();radius[-1]=radius[-1].mean()
    metadata=dict(implementation='FINITE_3D_MANDELBULB_OUTERMOST_SAMPLED_RADIAL_PROFILE_V1',
        power=float(power),iterations=int(iterations),bailout_radius=2.,
        latitude_samples=LATITUDE_SAMPLES,longitude_samples=LONGITUDE_SAMPLES,
        radial_samples=RADIAL_SAMPLES,radial_max=RADIAL_MAX,bisection_steps=BISECTION_STEPS,
        angular_directions=int(len(directions)),
        radial_bracket_width_max=float((upper-lower).max()),
        radius_quantiles=np.quantile(radius,[0.,.1,.5,.9,1.]).tolist(),
        all_upper_brackets_finitely_escaped=True,exact_infinite_membership=False,
        exact_outermost_boundary=False,full_volumetric_topology=False,
        source_formula=bulb.FORMULA_SOURCE,
        meaning='Actual finite3D spherical-power orbit, largest sampled finite-inside radius per spherical direction, then local inside/outside bisection. Not a scalar orbit-height or noise field.',
        limitation='Radial sampling may miss thin farther finite-inside intervals and the radial profile cannot represent overhangs/disconnected pieces along one ray. Cubic angular interpolation is a sampled approximation.')
    profile=BoundaryProfile(theta,phi,radius,metadata)
    evidence=dict(theta=theta,phi=phi,directions=directions.reshape(*tt.shape,3),
        radius=radius,finite_inside_scan_counts=inside_counts.reshape(tt.shape),
        last_inside_radial_sample=last_inside.reshape(tt.shape),
        lower_radius_bracket=lower.reshape(tt.shape),upper_radius_bracket=upper.reshape(tt.shape))
    return profile,metadata,evidence


def displace(carrier_xyz,carrier_normals,*,profile,cutoff=.30,amplitude=.035,chunk=131072):
    """Return full Nx3 replacement relief delta and compact metadata.

    Continuous angular world pullback has period4*cutoff. At power8 its main
    azimuthal lobe spacing is nominally cutoff/2. Canonical absolute coordinates
    and reflected vectors preserve X/Y reflection symmetry when the carrier
    and normals already possess it. All vertices/closed-mesh roles participate.
    """
    xyz=np.asarray(carrier_xyz);normals=np.asarray(carrier_normals)
    if xyz.ndim!=2 or xyz.shape[1]!=3 or normals.shape!=xyz.shape:
        raise ValueError('Matching Nx3 carrier positions and vertex normals required.')
    if not np.isfinite([cutoff,amplitude]).all() or cutoff<=0. or amplitude<=0. or chunk<1:
        raise ValueError('Positive finite cutoff/amplitude and chunk size required.')
    period=4.*cutoff;k=2.*np.pi/period;epsilon=.01*cutoff
    delta=np.zeros(xyz.shape,dtype=float)
    hmin=np.inf;hmax=-np.inf;normal_peak=0.;tangent_peak=0.;bad_normals=0
    for first in range(0,len(xyz),int(chunk)):
        last=min(first+int(chunk),len(xyz));x=np.asarray(xyz[first:last],dtype=float)
        n=np.asarray(normals[first:last],dtype=float)
        if not np.isfinite(x).all() or not np.isfinite(n).all():
            raise ValueError('Finite carrier positions/normals required.')
        length=np.linalg.norm(n,axis=1)
        if np.any(length<1e-12):raise ValueError('Degenerate carrier normal.')
        n=n/length[:,None]
        signs=np.where(x<0.,-1.,1.);canonical_normal=n*signs
        canonical=np.sqrt(x*x+epsilon*epsilon)
        q0=k*(canonical@AXIS_A);q1=k*(canonical@AXIS_B)
        sin0=np.sin(q0)
        theta=np.arccos(np.clip(np.cos(q0),-1.,1.))
        phi=np.mod(q1+np.where(sin0<0.,np.pi,0.),2.*np.pi)
        radius=profile._spline.ev(theta,phi)
        raw=(radius-profile.centre)/profile.scale
        h=np.clip(raw,-1.,1.)
        dtheta=profile._spline.ev(theta,phi,dx=1,dy=0)/profile.scale
        dphi=profile._spline.ev(theta,phi,dx=0,dy=1)/profile.scale
        active=(raw>-1.)&(raw<1.)
        gradient=k*(dtheta[:,None]*np.where(sin0>=0.,1.,-1.)[:,None]*AXIS_A+
            dphi[:,None]*AXIS_B)
        gradient*=active[:,None]*(np.abs(x)/canonical)
        tangent=gradient-canonical_normal*np.einsum('ij,ij->i',gradient,canonical_normal)[:,None]
        tangent*=-TANGENT_RATIO*amplitude*amplitude
        tnorm=np.linalg.norm(tangent,axis=1);tcap=TANGENT_CAP_RATIO*amplitude
        tangent*=np.divide(tcap*np.tanh(tnorm/tcap),tnorm,
            out=np.ones_like(tnorm),where=tnorm>1e-30)[:,None]
        move=(amplitude*h[:,None]*canonical_normal+tangent)*signs
        # Reflection-plane tangent components are exactly zero, independent
        # of floating-point trigonometric/interpolation round-off.
        move[np.abs(x[:,0])<1e-12,0]=0.
        move[np.abs(x[:,1])<1e-12,1]=0.
        delta[first:last]=move
        hmin=min(hmin,float(h.min(initial=np.inf)));hmax=max(hmax,float(h.max(initial=-np.inf)))
        normal_peak=max(normal_peak,float(np.abs(amplitude*h).max(initial=0.)))
        tangent_peak=max(tangent_peak,float(np.linalg.norm(tangent,axis=1).max(initial=0.)))
    if not np.isfinite(delta).all():raise ValueError('Nonfinite whole-carrier replacement relief.')
    metadata=dict(implementation='WHOLE_CARRIER_FINITE_3D_MANDELBULB_BOUNDARY_PULLBACK_V1',
        vertices=int(len(xyz)),cutoff=float(cutoff),amplitude=float(amplitude),
        angular_world_period=float(period),nominal_power8_primary_lobe_spacing=float(period/8.),
        nonaxis_map_vectors=[AXIS_A.tolist(),AXIS_B.tolist()],
        canonical_coordinate_smoothing=epsilon,
        normalized_relief_min=None if not len(xyz) else hmin,
        normalized_relief_max=None if not len(xyz) else hmax,
        maximum_normal_relief=normal_peak,maximum_tangent_relief=tangent_peak,
        maximum_total_relief=float(np.linalg.norm(delta,axis=1).max(initial=0.)),
        tangent_response='Bounded downhill surface-tangent component of the same actual radius-profile gradient; no independent texture/noise.',
        source_roles_masked=False,UV_chart_used=False,hard_periodic_cells_used=False,
        world_coordinates_modified=False,caller_carrier_required=True,
        macro_preservation='Caller supplies and validates a scale-separated carrier and any low-frequency projection. The amplitude bound alone is not exact preservation of the original large folds.',
        geometry='Replacement relief is a smooth angular world pullback of the actual sampled finite3D Mandelbulb outer radial boundary onto every carrier vertex. It is not the bulb full volumetric topology.',
        symmetry='Canonical smooth absolute XYZ and reflected vectors; exact X/Y reflection-plane components forcedzero. Actual source symmetry remains a caller check.',
        profile=profile.metadata,global_self_intersection_checked=False,
        aesthetic_success='Unverified until matched full/native render.')
    return delta,metadata
