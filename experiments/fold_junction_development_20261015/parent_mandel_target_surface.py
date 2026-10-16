"""Literal finite Mandelbulb upper-contour loft on an actual curved shoulder.

The fixed target is constructed before projection. Its ordered B contour can
return/backtrack; it is not a scalar force, a ruled sheet or a world coating.
"""
from pathlib import Path
import importlib.util
import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.ndimage import gaussian_filter1d

HERE=Path(__file__).resolve().parent
GEOMETRY_PATH=HERE/'parent_attached_mandel_volume.py'
_spec=importlib.util.spec_from_file_location('literal_target_actual_parent_geometry',GEOMETRY_PATH)
volume=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(volume)
POWER=8
ITERATIONS=8
FLOW_COUNT=65
CROSS_COUNT=129
SLICE_COUNT=33
ANGLE_COUNT=257
RADIAL_COUNT=81
BISECTIONS=12


def helper_paths():
    return [Path(__file__).resolve(),GEOMETRY_PATH,*volume.helper_paths()]


def _gate(x):
    x=np.clip(x,0.,1.)
    return x*x*x*(10.-15.*x+6.*x*x)


def _material_cross(geometry,theta,fraction):
    theta,fraction=np.broadcast_arrays(theta,fraction)
    flat_t=theta.ravel();flat_f=fraction.ravel();p=geometry.parameter
    lower=np.clip(np.searchsorted(p,flat_t,side='right')-1,0,len(p)-2);upper=lower+1
    alpha=(flat_t-p[lower])/(p[upper]-p[lower]);result=np.zeros(len(flat_t))
    for row in range(len(p)):
        for indices,weight in ((lower,1.-alpha),(upper,alpha)):
            ids=np.flatnonzero(indices==row)
            if len(ids):
                query=geometry.arc[row,0]+flat_f[ids]*(geometry.arc[row,-1]-geometry.arc[row,0])
                result[ids]+=weight[ids]*np.interp(query,geometry.arc[row],geometry.cross[row])
    return result.reshape(theta.shape)


def _contours(bulb):
    qt=np.linspace(-.4,.4,SLICE_COUNT)
    angle=np.linspace(np.pi,0.,ANGLE_COUNT)
    tt,aa=np.meshgrid(qt,angle,indexing='ij')
    direction=np.column_stack((np.zeros(tt.size),np.cos(aa.ravel()),np.sin(aa.ravel())))
    origins=np.column_stack((tt.ravel(),np.zeros(tt.size),np.zeros(tt.size)))
    radii=np.linspace(0.,1.6,RADIAL_COUNT);last=np.full(tt.size,-1,int)
    for index,radius in enumerate(radii):
        inside=bulb.membership(origins+radius*direction,power=POWER,iterations=ITERATIONS)
        last[inside]=index
    if np.any(last<0) or np.any(last>=RADIAL_COUNT-1):
        raise ValueError('Literal Mandelbulb upper contour lacks finite radial brackets.')
    lo=radii[last];hi=radii[last+1]
    for _ in range(BISECTIONS):
        mid=(lo+hi)*.5
        inside=bulb.membership(origins+mid[:,None]*direction,power=POWER,iterations=ITERATIONS)
        lo=np.where(inside,mid,lo);hi=np.where(inside,hi,mid)
    radius=((lo+hi)*.5).reshape(tt.shape)
    bn=np.stack((radius*np.cos(aa),radius*np.sin(aa)),axis=-1)
    u=np.linspace(0.,1.,CROSS_COUNT);ordered=np.zeros((SLICE_COUNT,CROSS_COUNT,2))
    for row in range(SLICE_COUNT):
        arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(bn[row],axis=0),axis=1))]
        for axis in range(2):ordered[row,:,axis]=np.interp(u*arc[-1],arc,bn[row,:,axis])
    b=(ordered[:,:,0]-ordered[:,:1,0])/(ordered[:,-1:,0]-ordered[:,:1,0])
    normal=ordered[:,:,1]-((1.-u[None,:])*ordered[:,:1,1]+u[None,:]*ordered[:,-1:,1])
    normal/=max(float(normal.max()),1e-12)
    return qt,u,b,normal,dict(contour_T=qt,contour_angle=angle,contour_radius=radius,
        contour_BN=bn,ordered_contour_BN=ordered,ordered_contour_B=b,ordered_contour_N=normal,
        radial_lower=lo.reshape(tt.shape),radial_upper=hi.reshape(tt.shape))


class TargetSurface:
    def __init__(self,geometry,events,ownership,s,u,target,footprint,metadata):
        self.geometry=geometry;self.events=events;self.ownership=ownership
        self.s=s;self.u=u;self.target=target;self.footprint=footprint
        self.metadata=metadata;self.stage_statistics=metadata['stage_statistics'];self.eligibility=None
        self.splines=[RectBivariateSpline(s,u,target[:,:,k],kx=3,ky=3,s=0.) for k in range(3)]

    def _sample(self,s,u,derivative=0):
        return np.column_stack([f.ev(s,u,dx=0,dy=derivative) for f in self.splines])

    def project(self,xyz,chart,stage,eligible=None):
        xyz=np.asarray(xyz);chart=np.asarray(chart)
        if xyz.ndim!=2 or xyz.shape[1]!=3 or chart.shape!=xyz.shape:
            raise ValueError('Matching actual stage XYZ and chart required.')
        output=xyz.copy();g=self.geometry
        theta=np.arctan2(np.abs(chart[:,2]),np.abs(chart[:,1]));cross=chart[:,0]
        allowed=(theta>g.parameter[0])&(theta<g.parameter[-1])
        eligibility=self.eligibility if eligible is None else eligible
        if eligibility is not None:
            mask=eligibility(xyz,chart,stage) if callable(eligibility) else eligibility
            mask=np.asarray(mask)
            if mask.shape!=(len(xyz),) or mask.dtype.kind!='b':raise ValueError('Actual boolean stage eligibility required.')
            allowed&=mask
        allowed&=(cross>np.interp(theta,g.parameter,g.cross[:,0]))&(cross<np.interp(theta,g.parameter,g.cross[:,-1]))
        ids=np.flatnonzero(allowed)
        record=dict(stage=str(stage),queried_controls=len(xyz),envelope_controls=len(ids),moved_controls=0,
            caller_topology_eligibility_bound=eligibility is not None)
        if not len(ids):self.stage_statistics.append(record);return output
        _,_,_,_,_,_,flow,fraction=g.sample(theta[ids],cross[ids])
        footprint=np.interp(flow,self.s,self.footprint)
        seed=.5+(fraction-.5)/footprint
        inside=(seed>0.)&(seed<1.)
        ids=ids[inside];flow=flow[inside];seed=seed[inside]
        if not len(ids):self.stage_statistics.append(record);return output
        signs=np.ones((len(ids),3));signs[:,0]=np.where(chart[ids,1]<0.,-1.,1.);signs[:,1]=np.where(chart[ids,2]<0.,-1.,1.)
        current=xyz[ids]*signs
        # Fixed material correspondence trust interval protects the ordered
        # Mandelbulb arc from jumps to a neighbouring return or parent sheet.
        trust=1./(2.*POWER);lower=np.maximum(0.,seed-trust);upper=np.minimum(1.,seed+trust)
        parameter=seed.copy()
        for _ in range(9):
            point=self._sample(flow,parameter);du=self._sample(flow,parameter,1);ddu=self._sample(flow,parameter,2)
            residual=point-current
            first=np.einsum('ij,ij->i',residual,du)
            second=np.einsum('ij,ij->i',du,du)+np.einsum('ij,ij->i',residual,ddu)
            denom=np.maximum(second,.1*np.einsum('ij,ij->i',du,du)+1e-20)
            step=np.clip(first/denom,-trust/3.,trust/3.)
            candidate=np.clip(parameter-step,lower,upper)
            # Backtracking decreases the fixed-target squared distance.
            old_error=np.einsum('ij,ij->i',residual,residual)
            for _ in range(4):
                trial=self._sample(flow,candidate)-current
                worse=np.einsum('ij,ij->i',trial,trial)>old_error
                candidate=np.where(worse,(candidate+parameter)*.5,candidate)
            parameter=candidate
        result=self._sample(flow,parameter)*signs
        result[np.abs(chart[ids,1])<1e-12,0]=0.;result[np.abs(chart[ids,2])<1e-12,1]=0.
        if not np.isfinite(result).all():raise ValueError('Nonfinite literal Mandelbulb target projection.')
        output[ids]=result
        magnitude=np.linalg.norm(result-xyz[ids],axis=1)
        record.update(parent_supported_controls=len(ids),moved_controls=int((magnitude>1e-12).sum()),
            maximum_full_projection_residual=float(magnitude.max(initial=0.)),
            maximum_target_parameter_shift=float(np.abs(parameter-seed).max(initial=0.)))
        self.stage_statistics.append(record)
        return output

    def evaluate(self,xyz,chart,stage,eligible=None):
        return self.project(xyz,chart,stage,eligible)-xyz

    __call__=evaluate


def build(parent,events,bulb,ownership):
    geometry=volume._ParentGeometry(parent)
    qt,cu,b,n,contour_evidence=_contours(bulb)
    bs=RectBivariateSpline(qt,cu,b,kx=3,ky=3,s=0.)
    ns=RectBivariateSpline(qt,cu,n,kx=3,ky=3,s=0.)
    s=np.linspace(0.,1.,FLOW_COUNT);u=np.linspace(0.,1.,CROSS_COUNT)
    theta=np.interp(s*geometry.flow[-1],geometry.flow,geometry.parameter)
    width=np.interp(theta,geometry.parameter,gaussian_filter1d(geometry.width,3.,mode='nearest'))
    depth=np.interp(theta,geometry.parameter,gaussian_filter1d(geometry.depth,3.,mode='nearest'))
    child_width=np.minimum(.25*width,2.*depth)
    if float(child_width.max())<=1e-8:raise ValueError('No positive measured parent depth for literal target.')
    footprint=np.maximum(child_width/width,1e-8)
    height=.9*depth
    ss,uu=np.meshgrid(s,u,indexing='ij');tt=np.broadcast_to(theta[:,None],ss.shape)
    cb=bs.ev(.8*(ss.ravel()-.5),uu.ravel()).reshape(ss.shape)
    cn=ns.ev(.8*(ss.ravel()-.5),uu.ravel()).reshape(ss.shape)
    guard=_gate(ss/.15)*_gate((1.-ss)/.15)*_gate(uu/.15)*_gate((1.-uu)/.15)
    target_u=uu+guard*(cb-uu)
    source_fraction=.5+footprint[:,None]*(uu-.5)
    mapped_fraction=.5+footprint[:,None]*(target_u-.5)
    if np.any(mapped_fraction<0.) or np.any(mapped_fraction>1.):
        raise ValueError('Literal target return escapes the measured actual parent shoulder.')
    source_material=_material_cross(geometry,tt,source_fraction)
    target_material=_material_cross(geometry,tt,mapped_fraction)
    source=geometry.sample(tt.ravel(),source_material.ravel())[0].reshape(FLOW_COUNT,CROSS_COUNT,3)
    mapped,_,_,normal,_,_,_,_=geometry.sample(tt.ravel(),target_material.ravel())
    target=mapped.reshape(FLOW_COUNT,CROSS_COUNT,3)+normal.reshape(FLOW_COUNT,CROSS_COUNT,3)*(guard*height[:,None]*cn)[:,:,None]
    partitions=ownership.partition_weights(tt.ravel(),source_material.ravel(),events)
    target_return=np.diff(target_u,axis=1)<-1e-6
    metadata=dict(implementation='CURVED_PARENT_LITERAL_FINITE_MANDELBULB_TARGET_SURFACE_V1',
        family_id=geometry.family,power=POWER,iterations=ITERATIONS,
        grid_shape=[FLOW_COUNT,CROSS_COUNT],contour_slices=SLICE_COUNT,contour_angles=ANGLE_COUNT,
        radial_samples=RADIAL_COUNT,bisection_steps=BISECTIONS,
        child_width_quantiles=np.quantile(child_width,[0.,.5,1.]).tolist(),
        target_normal_height_quantiles=np.quantile(height,[0.,.5,1.]).tolist(),
        footprint_fraction_quantiles=np.quantile(footprint,[0.,.5,1.]).tolist(),
        actual_B_return_intervals=int(target_return.sum()),maximum_target_vs_source=float(np.linalg.norm(target-source,axis=2).max()),
        ancestry_partition_quantiles=np.quantile(partitions[geometry.family],[0.,.5,1.]).tolist(),
        ancestry_amplitude_multiplied=False,
        proportions='Child width=min(.25*measured parent width,2*measured parent depth); normal height=.9*measured parent depth. Only measured scale curves pooled sigma3 rays; literal contour is not residual-smoothed.',
        shape='Actual finite power8 Mandelbulb upper B/N radial-boundary arc over ordered T slices, resampled by contour arc; B reversals retained when present. Outermost sampled finite radial brackets, not full volumetric topology or exact component proof.',
        curved_carrier='Actual measured curved native source shoulder, evaluated at displaced cross-arc correspondence; no straight/ruled carrier replacement.',
        source_matching='Compact quintic C2 margins15percent in source flow/cross coordinates; target matches the measured curved-source spline at patch boundaries. Outside the owned footprint projection is identity.',
        projection='Full absolute target projection at fixed inherited flow label, Newton/backtracking within ordered material-u trust1/(2*power); no global nearest branch switch, fractional force, overlap attenuation or post-projection cap.',
        source_boundary_exact_scope='Exact outside-footprint identity; C2 matching is to the measured reference target spline, not a claim that the discrete incoming CC carrier equals that spline at every boundary sample.',
        stage_statistics=[],limitations='Local constrained projector may converge to a local nearest point. Target may self-intersect or reverse quads; no intersection/beauty/recursive continuation certificate. Finite radial sampling can miss thin farther intervals.')
    evidence=dict(target_flow=s,target_cross=u,target_XYZ=target,source_curved_XYZ=source,
        source_material_cross=source_material,target_material_cross=target_material,
        actual_theta=theta,actual_child_width=child_width,actual_normal_height=height,
        actual_footprint_fraction=footprint,C2_guard=guard,normalized_contour_B=cb,
        normalized_contour_N=cn,target_ordered_B_parameter=target_u,
        B_return_intervals=target_return,ancestry_partition=partitions[geometry.family].reshape(ss.shape),
        **contour_evidence)
    return TargetSurface(geometry,events,ownership,s,u,target,footprint,metadata),metadata,evidence
