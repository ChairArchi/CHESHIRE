"""Finite 3D Mandelbulb response in a measured parent's (T,B,N) coordinates.

This is a restricted-ray, finite-iteration geometric response, not a signed
distance function or a globally nearest exterior point. Membership uses the
actual 3D spherical-power orbit. Candidate exterior brackets lie in the B/N
plane through each query, so the returned longitudinal T motion is zero.
"""
from pathlib import Path

import numpy as np


POWER=4
ITERATIONS=12
RAY_COUNT=16
BISECTION_STEPS=12
INITIAL_RADIUS=1e-4
RADIUS_GROWTH=1.75
MAX_RADIUS=4.25
FRACTION=.45
MOTION_CAP=.35
BOUNDARY_SOFTENING=.01
WEIGHT_POWER=6.
BLOCK=2048
FORMULA_SOURCE='https://www.skytopia.com/project/fractal/mandelbulb.html'


def helper_paths():
    return [Path(__file__).resolve()]


def membership(c,*,power=POWER,iterations=ITERATIONS):
    """Finite bounded-orbit membership; bailout radius 2, z0=(0,0,0).

    The input's component order is (T,B,N), used as the Mandelbulb Cartesian
    axes. A finite unescaped orbit is not a mathematical infinite-set proof.
    """
    c=np.asarray(c,dtype=float)
    if c.ndim!=2 or c.shape[1]!=3 or not np.isfinite(c).all():
        raise ValueError('Finite Nx3 normalized parent coordinates required.')
    if not np.isfinite(power) or power<2 or int(iterations)!=iterations or not 1<=iterations<=64:
        raise ValueError('Finite power>=2 and integer iterations in [1,64] required.')
    z=np.zeros_like(c)
    active=np.ones(len(c),dtype=bool)
    for _ in range(int(iterations)):
        ids=np.flatnonzero(active)
        if not len(ids):break
        current=z[ids]
        radius=np.linalg.norm(current,axis=1)
        escaped=radius>2.
        active[ids[escaped]]=False
        ids=ids[~escaped];current=current[~escaped];radius=radius[~escaped]
        if not len(ids):continue
        polar=np.arccos(np.divide(current[:,2],radius,out=np.ones_like(radius),where=radius>0.).clip(-1.,1.))
        azimuth=np.arctan2(current[:,1],current[:,0])
        radial=radius**power
        sine=np.sin(power*polar)
        powered=np.column_stack((radial*sine*np.cos(power*azimuth),
            radial*sine*np.sin(power*azimuth),radial*np.cos(power*polar)))
        z[ids]=powered+c[ids]
    active&=np.linalg.norm(z,axis=1)<=2.
    return active


def _rays():
    angles=2.*np.pi*np.arange(RAY_COUNT)/RAY_COUNT
    return np.column_stack((np.zeros(RAY_COUNT),np.cos(angles),np.sin(angles)))


def _respond_block(c,power,iterations):
    inside=membership(c,power=power,iterations=iterations)
    delta=np.zeros_like(c)
    selected=np.flatnonzero(inside)
    if not len(selected):
        return delta,inside,np.zeros(0),np.zeros(0),np.zeros(0),0
    origin=c[selected];directions=_rays()
    n=len(origin)
    lower=np.zeros((n,RAY_COUNT))
    upper=np.full((n,RAY_COUNT),INITIAL_RADIUS)
    bracketed=np.zeros((n,RAY_COUNT),bool)
    tests=0
    for _ in range(24):
        rows,cols=np.nonzero(~bracketed)
        if not len(rows):break
        points=origin[rows]+upper[rows,cols,None]*directions[cols]
        bounded=membership(points,power=power,iterations=iterations)
        tests+=len(points)
        escaped=~bounded
        bracketed[rows[escaped],cols[escaped]]=True
        still_rows,still_cols=rows[bounded],cols[bounded]
        lower[still_rows,still_cols]=upper[still_rows,still_cols]
        upper[still_rows,still_cols]=np.minimum(MAX_RADIUS,upper[still_rows,still_cols]*RADIUS_GROWTH)
    if not bracketed.all():
        # Every finite-inside origin has norm<=2. Moving >4 along any unit
        # ray gives norm>2 by the reverse triangle inequality, so this is a
        # numerical failure, never a synthesized exterior target.
        raise ValueError('Unable to certify all restricted exterior brackets.')
    rows=np.repeat(np.arange(n),RAY_COUNT)
    cols=np.tile(np.arange(RAY_COUNT),n)
    for _ in range(BISECTION_STEPS):
        middle=(lower+upper)*.5
        points=origin[rows]+middle.ravel()[:,None]*directions[cols]
        bounded=membership(points,power=power,iterations=iterations).reshape(n,RAY_COUNT)
        tests+=len(points)
        lower=np.where(bounded,middle,lower)
        upper=np.where(bounded,upper,middle)
    # Upper is a genuinely finite-escaped sample on each ray. It is only the
    # first sampled exterior bracket, not an exact first intersection: thin
    # intervening exterior intervals can be skipped by geometric bracketing.
    nearest=upper.min(axis=1)
    weights=((nearest[:,None]+1e-9)/(upper+1e-9))**WEIGHT_POWER
    average=np.einsum('nr,nr,rj->nj',weights,upper,directions)/weights.sum(axis=1)[:,None]
    # A near-boundary quadratic taper meets the zero exterior response. Soft
    # direction averaging avoids a discontinuous hard argmin ray selection.
    average*=FRACTION*(nearest/(nearest+BOUNDARY_SOFTENING))[:,None]
    norm=np.linalg.norm(average,axis=1)
    scale=np.divide(MOTION_CAP*np.tanh(norm/MOTION_CAP),norm,
        out=np.ones_like(norm),where=norm>1e-30)
    average*=scale[:,None]
    average[:,0]=0.
    delta[selected]=average
    return delta,inside,nearest,(upper-lower).max(axis=1),np.linalg.norm(average,axis=1),tests


def _quantiles(value):
    return np.quantile(value,[0.,.25,.5,.75,1.]).tolist() if len(value) else []


def respond(c,*,power=POWER,iterations=ITERATIONS):
    """Return ``(normalized_Nx3_delta, compact_JSON_safe_metadata)``.

    Caller supplies measured physical parent coordinates/frames, then maps B
    and N back with its physical width/depth budget. Do not treat these three
    normalized components as world-space displacement or as exact distances.
    Outside queries return zero. The finite inside response travels a capped
    fraction toward a smooth blend of restricted exterior candidates; neither
    this blend nor its fractional endpoint is certified to lie outside.
    """
    c=np.asarray(c,dtype=float)
    if c.ndim!=2 or c.shape[1]!=3 or not np.isfinite(c).all():
        raise ValueError('Finite Nx3 normalized parent coordinates required.')
    out=np.zeros_like(c);inside_count=0;tests=0
    distances=[];errors=[];motions=[]
    for start in range(0,len(c),BLOCK):
        block=c[start:start+BLOCK]
        delta,inside,distance,error,motion,count=_respond_block(block,power,iterations)
        out[start:start+len(block)]=delta
        inside_count+=int(inside.sum());tests+=int(count)
        distances.append(distance);errors.append(error);motions.append(motion)
    distances=np.concatenate(distances) if distances else np.zeros(0)
    errors=np.concatenate(errors) if errors else np.zeros(0)
    motions=np.concatenate(motions) if motions else np.zeros(0)
    metadata=dict(implementation='FINITE_3D_PARENT_LOCAL_MANDELBULB_RESTRICTED_RAY_RESPONSE_V1',
        formula_source=FORMULA_SOURCE,power=float(power),iterations=int(iterations),
        bailout_radius=2.,query_count=int(len(c)),finite_inside_queries=inside_count,
        finite_inside_fraction=inside_count/max(1,len(c)),ray_count=RAY_COUNT,
        initial_radius=INITIAL_RADIUS,radius_growth=RADIUS_GROWTH,maximum_radius=MAX_RADIUS,
        bisection_steps=BISECTION_STEPS,query_block_size=BLOCK,orbit_queries=tests,
        fractional_travel=FRACTION,normalized_motion_cap=MOTION_CAP,
        near_boundary_softening=BOUNDARY_SOFTENING,soft_direction_weight_power=WEIGHT_POWER,
        nearest_restricted_escape_distance_quantiles=_quantiles(distances),
        final_ray_bracket_width_quantiles=_quantiles(errors),
        inside_response_norm_quantiles=_quantiles(motions),
        inside_zero_or_cancelled_response_queries=int(np.count_nonzero(motions<1e-10)),
        maximum_normalized_displacement=float(np.linalg.norm(out,axis=1).max(initial=0.)),
        maximum_longitudinal_T_motion=float(np.abs(out[:,0]).max(initial=0.)),
        coordinate_order=['parent_longitudinal_T','parent_cross_B','parent_normal_N'],
        physical_scaling='Caller owns actual parent width/depth caps and orthonormal frame mapping.',
        response='Genuine finite 3D spherical-power membership drives a fractional soft blend of B/N-plane exterior-ray vectors; not scalar normal-only orbit height.',
        exact_global_nearest_outside=False,signed_distance_field=False,
        endpoint_outside_certified=False,all_candidate_upper_samples_finitely_escaped=True,
        limitation='Finite membership and fixed angular rays only. Geometric radial brackets can skip thin exterior intervals. Smooth direction weighting and boundary taper reduce switches; they do not prove global field smoothness across all fractal branches. No topology, collision, flow, or aesthetic certificate.')
    if not np.isfinite(out).all() or np.any(out[:,0]!=0.):
        raise ValueError('Nonfinite response or forbidden parent-longitudinal motion.')
    return out,metadata
