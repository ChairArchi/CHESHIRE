"""Forming-scale bandlimit of a genuine parent-local 3D vector response.

The source surface is never filtered or replaced here. The original finite
Mandelbulb response is sampled on an intrinsic physical-arc grid, and its
signed B/N components are filtered before C2 interpolation to native controls.
"""
from pathlib import Path

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.ndimage import gaussian_filter


FLOW_SAMPLES=65
CROSS_SAMPLES=129


def helper_paths():
    return [Path(__file__).resolve()]


class VectorController:
    """C2 tensor-product cubic interpolation in parent arc coordinates."""
    def __init__(self,s,u,vector):
        self.s=np.asarray(s,dtype=float)
        self.u=np.asarray(u,dtype=float)
        self._b=RectBivariateSpline(self.s,self.u,vector[:,:,1],kx=3,ky=3,s=0.)
        self._n=RectBivariateSpline(self.s,self.u,vector[:,:,2],kx=3,ky=3,s=0.)

    def evaluate(self,s,u):
        """Return flattened Nx3 normalized (T=0,B,N), without extrapolation.

        Exact ancestry/compact support and the physical displacement cap are
        applied by the caller after interpolation, as in the original trial.
        Cubic interpolation can overshoot a bounded sample; this function is
        not a replacement for the caller's existing physical norm cap.
        """
        s,u=np.broadcast_arrays(np.asarray(s,dtype=float),np.asarray(u,dtype=float))
        if not(np.isfinite(s).all() and np.isfinite(u).all()):
            raise ValueError('Finite parent flow/cross arc fractions required.')
        s=s.ravel();u=u.ravel()
        valid=(s>=0.)&(s<=1.)&(u>=0.)&(u<=1.)
        out=np.zeros((len(s),3),dtype=float)
        out[valid,1]=self._b.ev(s[valid],u[valid])
        out[valid,2]=self._n.ev(s[valid],u[valid])
        if not np.isfinite(out).all():
            raise ValueError('Nonfinite bandlimited parent vector interpolation.')
        return out


def _cross_at_fraction(parameter,fraction,parent):
    """Invert the saved native shoulder's actual physical cross-arc table."""
    p=np.asarray(parent['parameter'],dtype=float)
    material=np.asarray(parent['formation_shoulder_cross'],dtype=float)
    arc=np.asarray(parent['formation_shoulder_arc'],dtype=float)
    if material.shape!=arc.shape or material.shape[0]!=len(p):
        raise ValueError('Matching measured parent material/physical arc tables required.')
    rows=np.asarray([np.interp(fraction*arc[row,-1],arc[row],material[row])
        for row in range(len(p))])
    return np.column_stack([np.interp(parameter,p,rows[:,column])
        for column in range(len(fraction))])


def build(parent,bulb,formation_utils):
    """Return ``(controller, JSON_safe_metadata, full_grid_NPZ_evidence)``.

    The local mapping is exactly the prior per-native trial: .8 physical T
    fraction, 2.2 child B fraction, and .65 plus the existing pooled measured
    N-height divided by the same observed-depth scale. Only controller sampling,
    vector bandlimiting and interpolation change. No source XYZ is modified.
    """
    if str(parent['axis'])!='theta':
        raise ValueError('Actual theta-flow parent required.')
    p=np.asarray(parent['parameter'],dtype=float)
    if len(p)<5 or not np.all(np.diff(p)>0.):
        raise ValueError('Ordered measured parent parameters required.')
    curve,tangent,across,normal,flow=formation_utils.frames(parent)
    if not np.all(np.diff(flow)>0.):
        raise ValueError('Strictly increasing physical parent flow arc required.')
    s=np.linspace(0.,1.,FLOW_SAMPLES)
    u=np.linspace(0.,1.,CROSS_SAMPLES)
    parameter=np.interp(s*flow[-1],flow,p)
    full_shoulder_fraction=.25+.50*u
    material_cross=_cross_at_fraction(parameter,full_shoulder_fraction,parent)
    q=np.broadcast_to(parameter[:,None],material_cross.shape).ravel()
    cross=material_cross.ravel()
    measured_height=formation_utils.controller_height(q,cross,parent,curve,normal)
    width=np.interp(parameter,p,parent['parent_physical_width'])
    depth=np.interp(parameter,p,parent['parent_observed_chord_depth'])
    if np.any(width<=0.) or np.any(depth<0.):
        raise ValueError('Positive measured shoulder width and nonnegative depth required.')
    nscale=np.minimum(np.maximum(.65*depth,.02*width),.20*width)
    grid_s=np.broadcast_to(s[:,None],material_cross.shape)
    grid_u=np.broadcast_to(u[None,:],material_cross.shape)
    local=np.column_stack(((grid_s.ravel()-.5)*.8,(grid_u.ravel()-.5)*2.2,
        .65+measured_height/np.repeat(nscale,CROSS_SAMPLES)))
    raw,field_metadata=bulb.respond(local)
    raw=raw.reshape(FLOW_SAMPLES,CROSS_SAMPLES,3)
    if not np.isfinite(raw).all() or np.any(raw[:,:,0]!=0.):
        raise ValueError('Finite B/N-only actual bulb response required.')
    power=float(field_metadata['power'])
    median_child_width=float(np.median(.50*width))
    physical_sigma=median_child_width/(8.*power)
    flow_spacing=float(flow[-1]/(FLOW_SAMPLES-1))
    cross_spacing=float(median_child_width/(CROSS_SAMPLES-1))
    sigma_flow=max(1.,physical_sigma/flow_spacing)
    sigma_cross=max(1.,physical_sigma/cross_spacing)
    filtered=np.zeros_like(raw)
    # Actual zero exterior responses participate in the same signed filter.
    # No valid-mask normalization, hard rim or scalar normal height is added.
    for component in (1,2):
        filtered[:,:,component]=gaussian_filter(raw[:,:,component],
            sigma=(sigma_flow,sigma_cross),mode='nearest')
    controller=VectorController(s,u,filtered)
    family=int(parent.get('family_id',-1))
    metadata=dict(implementation='PARENT_PHYSICAL_ARC_VECTOR_BANDLIMIT_CONTROLLER_V1',
        family_id=family,grid_shape=[FLOW_SAMPLES,CROSS_SAMPLES],
        query_count=int(local.shape[0]),finite_inside_queries=int(field_metadata['finite_inside_queries']),
        finite_inside_fraction=float(field_metadata['finite_inside_fraction']),
        median_child_physical_width=median_child_width,physical_sigma=physical_sigma,
        physical_flow_length=float(flow[-1]),flow_sample_physical_spacing=flow_spacing,
        median_cross_sample_physical_spacing=cross_spacing,
        sigma_flow_samples=sigma_flow,sigma_cross_samples=sigma_cross,
        effective_flow_physical_sigma=sigma_flow*flow_spacing,
        median_effective_cross_physical_sigma=sigma_cross*cross_spacing,
        maximum_raw_normalized_response=float(np.linalg.norm(raw,axis=2).max(initial=0.)),
        maximum_filtered_grid_normalized_response=float(np.linalg.norm(filtered,axis=2).max(initial=0.)),
        maximum_longitudinal_T_response=0.,
        local_mapping='Same prior mapping: T=.8*(physical flow fraction-.5), B=2.2*(child cross fraction-.5), N=.65+existing pooled measured normal height / min(max(.65depth,.02width),.20width).',
        grid='Uniform physical flow arc and uniform child cross arc; child spans25 to75percent of saved actual native shoulder arc. Actual material positions invert the measured arc table, then interpolate only controller lookup coordinates between measured rows.',
        filter='Complete signed B/N vector arrays, including actual exterior zeros; Gaussian sigma=median(childwidth)/(8*power), minimum one sample in each grid direction. No mask-renormalization.',
        interpolation='RectBivariateSpline tensor-product interpolating cubic, C2 inside the grid; no extrapolation. Caller applies original compact support/ancestry and physical cap afterward.',
        source_XYZ_filtered=False,source_XYZ_replaced=False,scalar_normal_texture=False,
        field_algorithm=field_metadata,
        limitation='Finite measured profile/grid controller, not a world-space outside-target grid, SDF, or global nearest point. Cubic interpolation may overshoot sample extrema, so the existing caller physical cap remains mandatory. No collision or aesthetic certificate.')
    evidence=dict(grid_s=s,grid_u=u,grid_parameter=parameter,
        grid_material_cross=material_cross,grid_local_query=local.reshape(FLOW_SAMPLES,CROSS_SAMPLES,3),
        grid_raw_vector=raw,grid_filtered_vector=filtered,
        grid_controller_normal_height=measured_height.reshape(FLOW_SAMPLES,CROSS_SAMPLES),
        grid_parent_physical_width=width,grid_parent_observed_depth=depth,
        grid_normal_scale=nscale,original_parameter=p,original_flow_arc=flow)
    return controller,metadata,evidence
