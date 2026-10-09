"""Finite local-geometry column formation/refolding; no gate region copying.

X/Y section reflections only, Z is vertical. Original project units are
unresolved. Closed centre-fan native triangles and refinement stencils reuse
Task34 unchanged. Geometry is never averaged to enforce symmetry.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
from .task34_refolding import native,refine as refine_both,read_features,axial_features

HEIGHT=4000.
REFERENCE_RADIUS=np.sqrt(450.*250.)


class RejectedFormation(ValueError):
    """Rejected geometry retained for diagnostics; never silently repaired."""
    def __init__(self,message,state,controls,features):
        super().__init__(message);self.state=state;self.controls=controls;self.features=features


def carrier(kind='uniform',variant='standard'):
    if kind not in ('uniform','varied'):raise ValueError('Unknown column section configuration.')
    z=np.array([0,240,600,1800,2000,2240,2500,3400,4000.])
    w=np.full(9,450.);d=np.full(9,250.)
    if kind=='varied':
        w=np.array([450,450,560,560,200,200,650,450,450.])
        d=np.array([250,250,350,350,160,160,420,250,250.])
    if variant=='mild' and kind=='varied':w=450+.65*(w-450);d=250+.65*(d-250)
    elif variant!='standard':raise ValueError('Unknown coarse variant.')
    theta=np.arange(8)*np.pi/4;g=np.zeros((9,8,3))
    g[:,:,0]=w[:,None]*np.cos(theta);g[:,:,1]=d[:,None]*np.sin(theta);g[:,:,2]=z[:,None]
    return dict(grid=g,rest=g.copy(),s=z/HEIGHT,theta=theta,centres=np.column_stack([np.zeros(9),np.zeros(9),z]),
                knots=z/HEIGHT,axes=np.tile([1.,0.],(9,1)),roots=np.arange(64).reshape(8,8),classes=np.zeros((9,8),np.int8))


def refine(state,mode='both'):
    out,op=refine_both(state)
    if mode=='both':return out,op
    if mode!='angular':raise ValueError('Explicit both/angular sampling mode required.')
    nr,nt=state['grid'].shape[:2]
    for name in ['grid','rest','classes','s']:out[name]=out[name][::2].copy()
    out['roots']=out['roots'][::2].copy()
    parent_quad=np.repeat(np.arange((nr-1)*nt).reshape(nr-1,nt),2,axis=1)
    sides=np.tile([[0,2,3],[0,1,2]],(nr-1,nt,1))
    return out,dict(grid_parent_vertices=op['grid_parent_vertices'][::2],grid_parent_weights=op['grid_parent_weights'][::2],
        parent_quad=parent_quad,parent_native_triangle_contributors=parent_quad[:,:,None]*4+sides)


def end_window(state):
    s=state['s'];v=np.minimum((s-.06)/.04,(.94-s)/.04);v=np.clip(v,0,1)
    return v*v*(3-2*v)


def pair_scalar(state,a):
    n=len(state['theta']);j=np.arange(n)
    canonical=np.minimum(j,(-j)%n);canonical=np.minimum(canonical,(n//2-canonical)%n)
    a[:]=a[:,canonical]


def pair_vector(state,a):
    n=len(state['theta']);j=np.arange(n)
    canonical=np.minimum(j,(-j)%n);canonical=np.minimum(canonical,(n//2-canonical)%n)
    a[:]=a[:,canonical]
    a[:,:,0]*=np.where(np.cos(state['theta'])< -1e-12,-1,1)[None,:]
    a[:,:,1]*=np.where(np.sin(state['theta'])< -1e-12,-1,1)[None,:]
    a[:,[n//4,3*n//4],0]=0;a[:,[0,n//2],1]=0


def geometry_features(state):
    g=state['grid'];z=g[:,:,2].mean(1)
    if np.any(np.diff(z)<=0):raise ValueError('Nonmonotone mean section heights.')
    width=np.ptp(g[:,:,0],axis=1)/2;depth=np.ptp(g[:,:,1],axis=1)/2
    radius=np.sqrt(width*depth);dense_z=np.linspace(z[0],z[-1],1025)
    smooth=gaussian_filter1d(np.interp(dense_z,z,radius),80/(dense_z[1]-dense_z[0]),mode='nearest')
    slope=np.interp(z,dense_z,np.gradient(smooth,dense_z))
    curvature=np.interp(z,dense_z,np.gradient(np.gradient(smooth,dense_z),dense_z))
    b=np.clip((radius/REFERENCE_RADIUS-.65)/.85,0,1);b=b*b*(3-2*b)
    return dict(z=z,half_width=width,half_depth=depth,radius=radius,broadness=b,slope=slope,
                axial_curvature=curvature,aspect=np.log(np.maximum(width/depth,1e-12)/(450/250)))


def form(state,mode,params):
    if set(params)-{'amplitude'}:raise ValueError('Unknown initial column formation parameter.')
    amp=float(params.get('amplitude',500));window=end_window(state)
    if not np.isfinite(amp) or not 0<=amp<=800:raise ValueError('Finite amplitude0..800 required.')
    out=dict(state,grid=state['grid'].copy());f=geometry_features(state)
    if mode=='common':
        # Task34 N04 scalar formation recipe, evaluated at actual material Z.
        # Its gate-specific row-reflection is deliberately not called here.
        q=np.minimum(state['s'],1-state['s'])[:,None];theta=state['theta'][None,:]
        neck=np.maximum(np.exp(-((q-.15)/.045)**2),np.exp(-((q-.43)/.035)**2))
        bulge=np.maximum.reduce([np.exp(-((q-c)/.055)**2) for c in [.065,.285,.365,.495]])
        envelope=(.22+.78*bulge)*(1-.70*neck)
        foot=np.clip(q/.055,0,1);foot=foot*foot*(3-2*foot)
        phase=theta-.18*neck*np.sin(2*theta)
        requested=amp*envelope*foot*(.5+.5*np.cos(6*phase))**1.1*window[:,None]
        radial=state['grid'][:,:,:2]/np.maximum(np.linalg.norm(state['grid'][:,:,:2],axis=-1)[:,:,None],1e-12)
        delta=np.zeros_like(state['grid']);delta[:,:,:2]=requested[:,:,None]*radial;branch=np.zeros_like(requested)
    elif mode=='regional':
        b=f['broadness'][:,None];theta=state['theta'][None,:]
        fan=.28*np.tanh(1.5*f['slope'])+.10*np.tanh(f['aspect'])
        phase=theta-fan[:,None]*np.sin(2*theta)
        parent=(1-b)*(.5+.5*np.cos(4*phase))+b*(.5+.5*np.cos(8*phase))
        requested=amp*(.35+.65*b)*window[:,None]*parent**1.1
        radial=state['grid'][:,:,:2]/np.maximum(np.linalg.norm(state['grid'][:,:,:2],axis=-1)[:,:,None],1e-12)
        delta=np.zeros_like(state['grid']);delta[:,:,:2]=requested[:,:,None]*radial;branch=b+np.zeros_like(requested)
    else:raise ValueError('Explicit common/regional controller required.')
    pair_scalar(state,requested);pair_vector(state,delta);out['grid']+=delta
    return out,dict(requested_signed_distance=requested,applied_displacement=delta,total_applied_distance=np.linalg.norm(delta,axis=-1),
                    end_window=window,phase=phase,branch_mix=branch,**{'read_'+k:v for k,v in f.items()})


def periodic_interp(at,arc,values,perimeter):
    return np.interp(at%perimeter,np.r_[arc,perimeter],np.r_[values,values[0]])


def refold(state,source,mode,params):
    allowed={'fraction','chord_gain','branch_gain','direction_gain','axial_gain','width_scale','cut_width','amplitude_only','common_longitudinal_mix','common_axial_mix','signal_sigma','axial_wave_gain','axial_wavelength','fan_gain','axial_notch_gain'}
    if set(params)-allowed:raise ValueError('Unknown column folding parameters.')
    bounds={'branch_gain':(0,1),'direction_gain':(0,.4),'common_longitudinal_mix':(0,.4),'common_axial_mix':(0,1),'signal_sigma':(0,.2)}
    for key,(low,high) in bounds.items():
        if key in params and (not np.isfinite(params[key]) or not low<=params[key]<=high):raise ValueError('Declared bounds exceeded: '+key)
    if params.get('signal_sigma',.035)==0:raise ValueError('signal_sigma must be positive; it filters only feature scalars.')
    if state['grid'].shape!=source['grid'].shape:raise ValueError('Source/target sampling must match.')
    fraction=float(params.get('fraction',.45));chord_gain=float(params.get('chord_gain',1.))
    if not 0<=fraction<=.9 or not 0<=chord_gain<=1.5:raise ValueError('Declared fold strength bounds exceeded.')
    samples=512
    records,signal,geometries=read_features(source,samples=samples,sigma_angle=params.get('signal_sigma',.035),prominence=15.)
    f=geometry_features(source);nr,nt=state['grid'].shape[:2];depth=np.zeros((nr,nt));owner=np.full((nr,nt),-1,np.int64)
    chord_field=np.zeros_like(depth);window=end_window(state);theta=state['theta'];rows=[]
    axial,axial_owner,axial_table,actual_arc=axial_features(source,signal)
    axial_prominence=np.zeros(nr)
    for feature in axial_table:
        peak=int(np.rint(feature[1]/actual_arc[-1]*1024));axial_prominence[axial_owner==peak]=feature[3]
    axial_notch_gain=float(params.get('axial_notch_gain',0))
    if not 0<=axial_notch_gain<=1:raise ValueError('Measured axial notch gain outside0..1.')
    rmax=signal.max(1);longitudinal=np.gradient(rmax,actual_arc)
    # Actual current section scale and its gradient control fan/branch/transport.
    branch=f['broadness']*(1-.5*np.abs(np.tanh(f['slope'])))
    # A finite, physical aspect-ratio phase, read anew on the actual incoming
    # column. No generation index, random offset or recursively scaled rule.
    wave_gain=float(params.get('axial_wave_gain',0));wavelength=float(params.get('axial_wavelength',4.))
    fan_gain=float(params.get('fan_gain',0))
    if not 0<=wave_gain<=.8 or not 2<=wavelength<=8 or not 0<=fan_gain<=.8:raise ValueError('Measured-span controls outside declared bounds.')
    phase_rate=1/(wavelength*f['radius'])
    phase_arc=np.r_[0.,np.cumsum((phase_rate[:-1]+phase_rate[1:])/2*np.diff(f['z']))]*2*np.pi
    # Anchor to the common bottom fixed-buffer boundary, not an ornament label.
    phase_arc-=np.interp(240.,f['z'],phase_arc)
    wave=np.cos(phase_arc)
    amplitude_only=bool(params.get('amplitude_only',False))
    for row,(features,(xy,arc,perimeter)) in enumerate(zip(records,geometries)):
        sampled_arc=np.interp(theta,np.arange(samples)*2*np.pi/samples,arc)
        raw_radius=np.linalg.norm(xy,axis=1)
        for feature in features:
            at=arc[feature['peak']];distance=(sampled_arc-at+perimeter/2)%perimeter-perimeter/2
            width=np.where(distance<0,feature['half_width_left'],feature['half_width_right'])
            if mode=='common' or amplitude_only:
                t=distance/(width*.60);weight=np.maximum(0,1-t*t)**3
                profile=weight*(.9-2*np.exp(-(t/.28)**2))
                mix=params.get('common_axial_mix',.50)
                profile=(1-mix)*profile+mix*weight*axial[row]
                gain=1+.15*np.tanh(max(0,feature['projected_curvature'])*np.mean(width))
                requested=fraction*feature['prominence']*gain*profile
                if amplitude_only:requested*=.35+.65*f['broadness'][row]
                chord=0.
            elif mode=='regional':
                width_scale=params.get('width_scale',.85);cut_width=params.get('cut_width',.45)
                if not .3<=width_scale<=1.2 or not .2<=cut_width<=.8:raise ValueError('Declared crest support bounds exceeded.')
                t=distance/(width*width_scale);b=branch[row]*params.get('branch_gain',1.)
                if not 0<=b<=1:raise ValueError('Branch blend must stay within0..1.')
                candidates=[];chords=[]
                opening=1-fan_gain*(.5+.5*wave[row])
                for centre in [0.,-.38*opening,.38*opening]:
                    side=feature['half_width_left'] if centre<0 else feature['half_width_right']
                    middle=at+centre*side*width_scale;span=cut_width*min(feature['half_width_left'],feature['half_width_right'])*width_scale
                    rc=periodic_interp(middle,arc,raw_radius,perimeter)
                    chord=max(0.,rc-(periodic_interp(middle-span,arc,raw_radius,perimeter)+periodic_interp(middle+span,arc,raw_radius,perimeter))/2)
                    offset=(sampled_arc-middle+perimeter/2)%perimeter-perimeter/2
                    support=np.maximum(0,1-(offset/span)**2)**3
                    candidates.append(-(fraction*feature['prominence']+chord_gain*chord)*support)
                    chords.append(chord)
                requested=(1-b)*candidates[0]+b*np.minimum(candidates[1],candidates[2]);chord=max(chords)
                # Whole crest shoulder bends along a radius-relative span;
                # narrow parent-tip incisions alone cannot bend a long panel.
                shoulder=np.maximum(0,1-t*t)**2
                requested+=wave_gain*feature['prominence']*f['broadness'][row]*wave[row]*shoulder
                requested+=axial_notch_gain*axial_prominence[row]*axial[row]*shoulder
            else:raise ValueError('Unknown controller.')
            requested*=window[row];take=np.abs(requested)>np.abs(depth[row]);depth[row,take]=requested[take]
            owner[row,take]=row*samples+feature['peak'];chord_field[row,take]=chord
            rows.append(dict(**feature,branch_mix=float(branch[row]) if mode=='regional' and not amplitude_only else 0.,
                             chord_drop=float(chord),axial_phase=float(phase_arc[row]),axial_wave=float(wave[row]),
                             requested_min=float(requested.min()),requested_max=float(requested.max())))
    pair_scalar(state,depth);pair_scalar(state,owner);pair_scalar(state,chord_field)
    source_xy=source['grid'][:,:,:2];radial=source_xy/np.maximum(np.linalg.norm(source_xy,axis=-1)[:,:,None],1e-12)
    delta=np.zeros_like(state['grid']);delta[:,:,:2]=depth[:,:,None]*radial
    angular=np.zeros_like(depth);axial_delta=np.zeros(nr)
    if mode=='regional' and not amplitude_only:
        angular=params.get('direction_gain',.10)*np.tanh(f['slope'])[:,None]*np.sin(2*theta)[None,:]*window[:,None]
        # Rotate actual XY positions, with vector reflection enforced before application.
        x=state['grid'][:,:,0]+delta[:,:,0];y=state['grid'][:,:,1]+delta[:,:,1]
        delta[:,:,0]=np.cos(angular)*x-np.sin(angular)*y-state['grid'][:,:,0]
        delta[:,:,1]=np.sin(angular)*x+np.cos(angular)*y-state['grid'][:,:,1]
        gain=params.get('axial_gain',.40)
        if not 0<=gain<=.8:raise ValueError('Axial redistribution gain outside0..0.8.')
        z=np.linspace(240,3760,1025);radius=np.interp(z,f['z'],f['radius'])
        density=np.exp(-gain*np.tanh(radius/REFERENCE_RADIUS-1))
        integral=np.r_[0.,np.cumsum((density[1:]+density[:-1])/2*np.diff(z))]
        mapped=240+3520*integral/integral[-1]
        target=np.interp(f['z'],z,mapped);inside=(f['z']>240)&(f['z']<3760)
        axial_delta[inside]=target[inside]-f['z'][inside]
        delta[:,:,2]=axial_delta[:,None]
    else:
        delta[:,:,2]=-params.get('common_longitudinal_mix',.20)*depth*longitudinal[:,None]/np.sqrt(1+longitudinal[:,None]**2)
    pair_vector(state,delta);out=dict(state,grid=state['grid']+delta)
    controls=dict(requested_signed_distance=depth,applied_displacement=delta,total_applied_distance=np.linalg.norm(delta,axis=-1),
        feature_owner=owner,chord_drop=chord_field,angular_displacement=angular,axial_redistribution=axial_delta,
        end_window=window,source_signal=signal,axial_feature_table=axial_table,axial_feature_owner=axial_owner,
        axial_feature_profile=axial,axial_feature_prominence=axial_prominence,
        measured_span_phase=phase_arc,measured_span_wave=wave,
        **{'read_'+k:v for k,v in f.items()})
    radius=np.linalg.norm(out['grid'][:,:,:2],axis=-1)
    if np.any(radius<.15*np.linalg.norm(state['rest'][:,:,:2],axis=-1)):raise RejectedFormation('Consumed column thickness; no clipping.',out,controls,rows)
    if not np.isfinite(out['grid']).all():raise RejectedFormation('Nonfinite displacement.',out,controls,rows)
    # Observed order is logged/validated, not silently repaired or excluded.
    return out,controls,rows


def symmetry(mesh,chart):
    records={}
    for name,axis,slot in [('LR',0,1),('FB',1,2)]:
        reflected=chart.copy();reflected[:,slot]*=-1;distance,pair=cKDTree(chart).query(reflected)
        if distance.max()>1e-10 or not np.array_equal(pair[pair],np.arange(len(pair))):raise ValueError('Section reflection is not an involution.')
        xyz=mesh.xyz.copy();xyz[:,axis]*=-1
        def canonical(t):
            j=(np.arange(3)[None,:]+np.argmin(t,axis=1)[:,None])%3;return np.take_along_axis(t,j,axis=1)
        a=canonical(mesh.faces[:,:3]);b=canonical(pair[mesh.faces[:,:3][:,::-1]])
        a=a[np.lexsort(a.T)];b=b[np.lexsort(b.T)]
        records[name]=dict(geometry_max=float(np.linalg.norm(xyz-mesh.xyz[pair],axis=1).max()),
            oriented_triangle_cycle_failures=int(np.any(a!=b,axis=1).sum()),chart_max=float(distance.max()))
    return records
