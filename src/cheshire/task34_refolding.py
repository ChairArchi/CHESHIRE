"""Finite, geometry-responsive refolding on a closed structured gate.

Three explicitly scheduled formation/folding stages, not a fractal model.
Features are measured on actual incoming ring polylines. Their projected
curvature is not a general triangle-mesh principal-curvature estimator.
All distances use the unresolved original project units, never cell lengths.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from scipy.spatial import cKDTree
from .reference_subdivision import ArrayMesh
from .progressive_gates import PLANE_X, PLANE_Y


def carrier(template, kind='uniform'):
    if kind not in ('uniform', 'jointed', 'splayed','curved_uniform','curved_jointed'):
        raise ValueError('Unknown coarse carrier.')
    centres=template.xyz[:72].reshape(9,8,3).mean(1)
    if kind.startswith('curved_'):
        centres[2,2]=2000;centres[6,2]=2000
        centres[3,[0,2]]=[PLANE_X-1250,2750]
        centres[5,[0,2]]=[PLANE_X+1250,2750]
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(centres,axis=0),axis=1))]
    s/=s[-1]
    axes=np.array([[1,0],[1,0],[1,0],[2**-.5,-2**-.5],[0,-1],[-2**-.5,-2**-.5],[-1,0],[-1,0],[-1,0]])
    width=np.ones(9);depth=np.ones(9)
    if kind not in ('uniform','curved_uniform'):
        width=np.array([1,.70,.85,1.25,1,1.25,.85,.70,1.])
        depth=np.array([.6,.70,.72,1,.85,1,.72,.70,.6])
    if kind=='splayed':
        axes[3]=[np.cos(np.pi/6),-np.sin(np.pi/6)]
        axes[5]=[-np.cos(np.pi/6),-np.sin(np.pi/6)]
        width[[3,5]]=1.15
    theta=np.arange(8)*2*np.pi/8
    grid=np.broadcast_to(centres[:,None,:],(9,8,3)).copy()
    grid[:,:,[0,2]]+=axes[:,None,:]*(450*width[:,None]*np.cos(theta)[None,:])[:,:,None]
    grid[:,:,1]+=250*depth[:,None]*np.sin(theta)[None,:]
    return dict(grid=grid,rest=grid.copy(),s=s,theta=theta,centres=centres,knots=s.copy(),axes=axes,
                roots=np.arange(64).reshape(8,8),classes=np.zeros((9,8),np.int8))


def frame(state):
    s=state['s'];c=np.column_stack([np.interp(s,state['knots'],state['centres'][:,k]) for k in range(3)])
    a=np.column_stack([np.interp(s,state['knots'],state['axes'][:,k]) for k in range(2)])
    a/=np.linalg.norm(a,axis=1)[:,None]
    # Increasing material arc tangent. Its orientation reverses under LR.
    tangent=np.column_stack([-a[:,1],a[:,0]])
    return c,a,tangent


def native(state,generation):
    g=state['grid'];rest=state['rest'];nr,nt=g.shape[:2];idx=np.arange(nr*nt).reshape(nr,nt)
    q=np.stack([idx[:-1],np.roll(idx[:-1],-1,1),np.roll(idx[1:],-1,1),idx[1:]],axis=-1).reshape(-1,4)
    centres=g.reshape(-1,3)[q].mean(1);rc=rest.reshape(-1,3)[q].mean(1)
    cap=np.stack([g[0].mean(0),g[-1].mean(0)]);rcap=np.stack([rest[0].mean(0),rest[-1].mean(0)])
    xyz=np.concatenate([g.reshape(-1,3),cap,centres]);rr=np.concatenate([rest.reshape(-1,3),rcap,rc])
    ci=nr*nt+2+np.arange(len(q))
    tri=np.stack([q,np.roll(q,-1,1),np.repeat(ci[:,None],4,1)],axis=-1).reshape(-1,3)
    caps=np.concatenate([np.column_stack([np.full(nt,nr*nt),np.roll(idx[0],-1),idx[0]]),
                         np.column_stack([np.full(nt,nr*nt+1),idx[-1],np.roll(idx[-1],-1)])])
    faces=np.column_stack([np.concatenate([tri,caps]),np.full(len(tri)+2*nt,-1,np.int64)])
    classes=np.r_[state['classes'].ravel(),np.zeros(2,np.int8),np.full(len(q),2,np.int8)]
    roots=np.r_[np.repeat(state['roots'].ravel(),4),64+np.arange(nt)*8//nt,72+np.arange(nt)*8//nt]
    anchors=np.column_stack([roots,np.full(len(faces),-1,np.int64),np.full(len(faces),-1,np.int64)])
    chart=np.stack(np.broadcast_arrays(state['s'][:,None],np.cos(state['theta'])[None,:],np.sin(state['theta'])[None,:]),axis=-1).reshape(-1,3)
    chart=np.concatenate([chart,[[0,0,0],[1,0,0]],chart[q].mean(1)])
    return ArrayMesh(xyz,faces,classes,rr,anchors,generation),chart,q


def refine(state):
    nr,nt=state['grid'].shape[:2]
    def linear(a):
        b=np.empty((2*nr-1,2*nt,3));b[::2,::2]=a
        b[::2,1::2]=(a+np.roll(a,-1,axis=1))/2
        b[1::2]=(b[:-2:2]+b[2::2])/2
        return b
    s=np.empty(2*nr-1);s[::2]=state['s'];s[1::2]=(s[:-2:2]+s[2::2])/2
    out=dict(state,grid=linear(state['grid']),rest=linear(state['rest']),s=s,theta=np.arange(2*nt)*np.pi/nt,
             roots=np.repeat(np.repeat(state['roots'],2,axis=0),2,axis=1),classes=np.ones((2*nr-1,2*nt),np.int8))
    out['classes'][::2,::2]=0;out['classes'][1::2,1::2]=0
    # Exact previous-native vertex stencils, including previous quad centres.
    old=np.arange(nr*nt).reshape(nr,nt);parents=np.full((2*nr-1,2*nt,2),-1,np.int64);weights=np.zeros_like(parents,dtype=float)
    parents[::2,::2,0]=old;weights[::2,::2,0]=1
    parents[::2,1::2,0]=old;parents[::2,1::2,1]=np.roll(old,-1,1);weights[::2,1::2]=.5
    parents[1::2,::2,0]=old[:-1];parents[1::2,::2,1]=old[1:];weights[1::2,::2]=.5
    parents[1::2,1::2,0]=nr*nt+2+np.arange((nr-1)*nt).reshape(nr-1,nt);weights[1::2,1::2,0]=1
    old_quad=np.arange((nr-1)*nt).reshape(nr-1,nt)
    parent_quad=np.repeat(np.repeat(old_quad,2,0),2,1)
    corner=np.tile(np.array([[0,1],[3,2]]),(nr-1,nt))
    # A new quadrant overlaps two old centre-fan triangles, not one face.
    contributors=np.stack([parent_quad*4+corner,parent_quad*4+(corner-1)%4],axis=-1)
    return out,dict(grid_parent_vertices=parents,grid_parent_weights=weights,parent_quad=parent_quad,
                    parent_native_triangle_contributors=contributors)


def pair_controls(state,arrays):
    nr,nt=state['grid'].shape[:2]
    # Copy scalar controls from canonical (left, front) sector BEFORE geometry.
    row=np.minimum(np.arange(nr),nr-1-np.arange(nr))
    col=np.minimum(np.arange(nt),(-np.arange(nt))%nt)
    for a in arrays:a[:]=a[row[:,None],col[None,:]]


def macro(state,params):
    allowed={'amplitude','lobes','neck_depth','angular_convergence','bulge_span','xz_gain'}
    if set(params)-allowed:raise ValueError('Unknown macro control.')
    amp=float(params.get('amplitude',500));lobes=params.get('lobes',6)
    if not 0<=amp<=800 or lobes not in (4,6,8):raise ValueError('Invalid macro controls.')
    q=np.minimum(state['s'],1-state['s'])[:,None];theta=state['theta'][None,:]
    neck=np.maximum(np.exp(-((q-.15)/.045)**2),np.exp(-((q-.43)/.035)**2))
    bulge=np.maximum.reduce([np.exp(-((q-c)/params.get('bulge_span',.055))**2) for c in [.065,.285,.365,.495]])
    envelope=(.22+.78*bulge)*(1-params.get('neck_depth',.70)*neck)
    foot=np.clip(q/.055,0,1);foot=foot*foot*(3-2*foot)
    phase=theta-params.get('angular_convergence',.18)*neck*np.sin(2*theta)
    if abs(params.get('angular_convergence',.18))>=.4:raise ValueError('Angular map requires positive orientation.')
    depth=amp*envelope*foot*(.5+.5*np.cos(lobes*phase))**1.1
    pair_controls(state,[depth])
    c,a,_=frame(state);off=state['grid']-c[:,None,:]
    p=np.stack([(off[:,:,[0,2]]*a[:,None,:]).sum(-1),off[:,:,1]],axis=-1)
    radius=np.linalg.norm(p,axis=-1);radial=p/np.maximum(radius[:,:,None],1e-12)
    out=dict(state,grid=state['grid'].copy())
    xz_gain=params.get('xz_gain',1.)
    if not 0<=xz_gain<=1:raise ValueError('Explicit XZ direction gain must be within 0..1.')
    out['grid'][:,:,[0,2]]+=a[:,None,:]*(xz_gain*depth*radial[:,:,0])[:,:,None]
    out['grid'][:,:,1]+=depth*radial[:,:,1]
    applied=depth*(xz_gain*radial[:,:,0]**2+radial[:,:,1]**2)
    return out,dict(requested_radial=depth,applied_radial=applied,applied_displacement=out['grid']-state['grid'],foot=foot+np.zeros_like(depth))


def read_features(state,*,samples=512,prominence=15.,sigma_angle=.035):
    """Measure source edge polylines at fixed angular sampling, never smooth XYZ."""
    c,a,tangent=frame(state);g=state['grid'];off=g-c[:,None,:];rest=state['rest']-c[:,None,:]
    xy=np.stack([(off[:,:,[0,2]]*a[:,None,:]).sum(-1),off[:,:,1]],axis=-1)
    base=np.stack([(rest[:,:,[0,2]]*a[:,None,:]).sum(-1),rest[:,:,1]],axis=-1)
    theta=np.arange(samples)*2*np.pi/samples;records=[];dense=[];geometries=[]
    for row,(p,b) in enumerate(zip(xy,base)):
        pp=np.column_stack([np.interp(theta,state['theta'],p[:,k],period=2*np.pi) for k in range(2)])
        bb=np.column_stack([np.interp(theta,state['theta'],b[:,k],period=2*np.pi) for k in range(2)])
        value=np.linalg.norm(pp,axis=1)-np.linalg.norm(bb,axis=1)
        signal=gaussian_filter1d(value,sigma_angle*samples/(2*np.pi),mode='wrap')
        peaks,properties=find_peaks(np.tile(signal,3),prominence=prominence)
        take=(peaks>=samples)&(peaks<2*samples);peaks=peaks[take]-samples
        smooth=gaussian_filter1d(pp,sigma_angle*samples/(2*np.pi),axis=0,mode='wrap')
        dp=(np.roll(smooth,-1,0)-np.roll(smooth,1,0))/2;dd=np.roll(smooth,-1,0)-2*smooth+np.roll(smooth,1,0)
        curvature=(dp[:,0]*dd[:,1]-dp[:,1]*dd[:,0])/np.maximum(np.linalg.norm(dp,axis=1)**3,1e-12)
        edges=np.linalg.norm(np.roll(pp,-1,0)-pp,axis=1);arc=np.r_[0,np.cumsum(edges[:-1])];perimeter=edges.sum()
        row_records=[]
        if len(peaks)>=2:
            for j,peak in enumerate(peaks):
                previous=int(peaks[j-1]);nxt=int(peaks[(j+1)%len(peaks)])
                left=np.arange(previous,peak+samples*(peak<=previous)+1)%samples
                right=np.arange(peak,nxt+samples*(nxt<=peak)+1)%samples
                lv=int(left[np.argmin(signal[left])]);rv=int(right[np.argmin(signal[right])])
                floor=max(signal[lv],signal[rv]);prom=float(signal[peak]-floor)
                if prom<prominence:continue
                threshold=floor+.45*prom;l=int(peak);rr=int(peak)
                for _ in range(samples//2):
                    if signal[(l-1)%samples]<threshold:break
                    l=(l-1)%samples
                for _ in range(samples//2):
                    if signal[(rr+1)%samples]<threshold:break
                    rr=(rr+1)%samples
                wl=float((arc[peak]-arc[l])%perimeter);wr=float((arc[rr]-arc[peak])%perimeter)
                if min(wl,wr)<1e-6:continue
                raw=int(np.floor(theta[peak]/(2*np.pi)*len(p)))%len(p)
                weight=float(theta[peak]/(2*np.pi)*len(p)-raw)
                xyz=(1-weight)*g[row,raw]+weight*g[row,(raw+1)%len(p)]
                row_records.append(dict(row=row,s=float(state['s'][row]),peak=int(peak),theta=float(theta[peak]),
                    prominence=prom,crest_value=float(signal[peak]),left_valley=lv,right_valley=rv,
                    half_width_left=wl,half_width_right=wr,projected_curvature=float(curvature[peak]),
                    xyz=xyz.tolist(),source_edge_vertices=[int(row*len(p)+raw),int(row*len(p)+(raw+1)%len(p))],
                    source_edge_weights=[1-weight,weight]))
        records.append(row_records);dense.append(signal);geometries.append((pp,arc,perimeter))
    return records,np.asarray(dense),geometries


def axial_features(source,signal):
    """Finite bulges measured along the ACTUAL section-centre polyline."""
    centres=source['grid'].mean(1)
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(centres,axis=0),axis=1))]
    if np.any(np.diff(arc)<=0):raise ValueError('Axial feature curve has a collapsed segment.')
    samples=np.linspace(0,arc[-1],1025)
    values=np.interp(samples,arc,signal.max(1))
    values=gaussian_filter1d(values,80/(samples[1]-samples[0]),mode='nearest')
    peaks,_=find_peaks(values,prominence=40.)
    profile=np.zeros(len(arc));owner=np.full(len(arc),-1,np.int64);rows=[]
    for j,peak in enumerate(peaks):
        previous=0 if j==0 else peaks[j-1];nxt=len(values)-1 if j+1==len(peaks) else peaks[j+1]
        left=previous+np.argmin(values[previous:peak+1]);right=peak+np.argmin(values[peak:nxt+1])
        floor=max(values[left],values[right]);prom=values[peak]-floor
        if prom<40:continue
        l=int(peak);r=int(peak);threshold=floor+.45*prom
        while l>left and values[l-1]>=threshold:l-=1
        while r<right and values[r+1]>=threshold:r+=1
        wl=samples[peak]-samples[l];wr=samples[r]-samples[peak]
        if min(wl,wr)<=0:continue
        delta=arc-samples[peak];t=delta/(np.where(delta<0,wl,wr)*.8)
        weight=np.maximum(0,1-t*t)**3
        response=weight*(.9-2*np.exp(-(t/.28)**2))
        take=np.abs(response)>np.abs(profile);profile[take]=response[take];owner[take]=peak
        rows.append([float(np.interp(samples[peak],arc,source['s'])),float(samples[peak]),float(values[peak]),float(prom),float(wl),float(wr)])
    return profile,owner,np.asarray(rows).reshape(-1,6),arc


def refold(state,source,params):
    allowed={'fraction','normal_mix','longitudinal_mix','curvature_gain','prominence','notch_width','operator','axial_mix','direction_mode','tangent_mode'}
    if set(params)-allowed:raise ValueError('Unknown refolding control.')
    fraction=params.get('fraction',.60);mix=params.get('normal_mix',.15);lmix=params.get('longitudinal_mix',.20)
    operation=params.get('operator','notch')
    if operation not in ('notch','split'):raise ValueError('Unknown measured-crest operation.')
    direction_mode=params.get('direction_mode','profile');tangent_mode=params.get('tangent_mode','guide')
    if direction_mode not in ('profile','surface') or tangent_mode not in ('guide','measured'):raise ValueError('Unknown geometric direction source.')
    if not 0<=fraction<=.9 or not 0<=mix<=.4 or not 0<=lmix<=.4:raise ValueError('Refolding controls outside declared bounds.')
    if source['grid'].shape!=state['grid'].shape:raise ValueError('Source and target sampling must match.')
    records,signal,geometries=read_features(source,prominence=params.get('prominence',15.))
    axial_mix=params.get('axial_mix',0)
    if not 0<=axial_mix<=1:raise ValueError('Axial feature mixture must be within 0..1.')
    axial_profile,axial_owner,axial_table,actual_arc=axial_features(source,signal)
    nr,nt=state['grid'].shape[:2];depth=np.zeros((nr,nt));owner=np.full((nr,nt),-1,np.int64)
    source_xy=np.zeros((nr,nt,2));normals=np.zeros_like(source_xy)
    probe=state['theta']*512/(2*np.pi);sample_theta=np.arange(512)*2*np.pi/512
    rmax=signal.max(1);physical=actual_arc
    longitudinal=np.gradient(rmax,physical)
    for row,(features,(xy,arc,perimeter)) in enumerate(zip(records,geometries)):
        xy_smooth=gaussian_filter1d(xy,.035*512/(2*np.pi),axis=0,mode='wrap')
        tangent=np.roll(xy_smooth,-1,0)-np.roll(xy_smooth,1,0)
        n=np.column_stack([tangent[:,1],-tangent[:,0]]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
        for k in range(2):
            source_xy[row,:,k]=np.interp(state['theta'],sample_theta,xy[:,k],period=2*np.pi)
            normals[row,:,k]=np.interp(state['theta'],sample_theta,n[:,k],period=2*np.pi)
        sampled_arc=np.interp(state['theta'],sample_theta,arc)
        for feature in features:
            at=arc[feature['peak']];d=(sampled_arc-at+perimeter/2)%perimeter-perimeter/2
            width=np.where(d<0,feature['half_width_left'],feature['half_width_right'])
            t=d/(width*params.get('notch_width',.60));weight=np.maximum(0,1-t*t)**3
            gain=1+params.get('curvature_gain',.15)*np.tanh(max(0,feature['projected_curvature'])*np.mean(width))
            profile=-weight if operation=='notch' else weight*(.9-2*np.exp(-(t/.28)**2))
            profile=(1-axial_mix)*profile+axial_mix*weight*axial_profile[row]
            requested=fraction*feature['prominence']*gain*profile
            selected=np.abs(requested)>np.abs(depth[row]);depth[row,selected]=requested[selected]
            owner[row,selected]=row*512+feature['peak']
    pair_controls(state,[depth,owner])
    c,a,tangent=frame(state);off=state['grid']-c[:,None,:]
    actual=np.stack([(off[:,:,[0,2]]*a[:,None,:]).sum(-1),off[:,:,1]],axis=-1)
    radial=source_xy/np.maximum(np.linalg.norm(source_xy,axis=-1)[:,:,None],1e-12)
    direction=(1-mix)*radial+mix*normals;direction/=np.maximum(np.linalg.norm(direction,axis=-1)[:,:,None],1e-12)
    # Enforce vector parity from canonical controls, no XYZ averaging.
    rx=np.minimum(np.arange(nr),nr-1-np.arange(nr));cx=np.minimum(np.arange(nt),(-np.arange(nt))%nt)
    direction=direction[rx[:,None],cx[None,:]].copy();direction[:,:,1]*=np.where(np.sin(state['theta'])< -1e-12,-1,1)[None,:]
    direction[:,[0,nt//2],1]=0
    dz=-lmix*depth*longitudinal[:,None]/np.sqrt(1+longitudinal[:,None]**2)
    dz[nr//2+1:]=-dz[rx[nr//2+1:]];dz[nr//2]=0
    out=dict(state,grid=state['grid'].copy())
    global_direction=np.zeros_like(state['grid']);global_direction[:,:,[0,2]]=a[:,None,:]*direction[:,:,0,None]
    global_direction[:,:,1]=direction[:,:,1]
    if direction_mode=='surface':
        mesh,_,_=native(source,0);tri=mesh.faces[:,:3];points=mesh.xyz[tri]
        face_normals=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]);vertex_normals=np.zeros_like(mesh.xyz)
        for slot in range(3):np.add.at(vertex_normals,tri[:,slot],face_normals)
        vertex_normals=vertex_normals[:nr*nt].reshape(nr,nt,3)
        vertex_normals/=np.maximum(np.linalg.norm(vertex_normals,axis=-1)[:,:,None],1e-12)
        raw=np.zeros_like(state['grid']);raw[:,:,[0,2]]=a[:,None,:]*radial[:,:,0,None];raw[:,:,1]=radial[:,:,1]
        global_direction=(1-mix)*raw+mix*vertex_normals
        global_direction/=np.maximum(np.linalg.norm(global_direction,axis=-1)[:,:,None],1e-12)
    tangent_global=np.zeros((nr,3));tangent_global[:,[0,2]]=tangent
    if tangent_mode=='measured':
        tangent_global=np.gradient(source['grid'].mean(1),source['s'],axis=0)
        tangent_global/=np.maximum(np.linalg.norm(tangent_global,axis=1)[:,None],1e-12)
    displacement=depth[:,:,None]*global_direction+dz[:,:,None]*tangent_global[:,None,:]
    displacement=displacement[rx[:,None],cx[None,:]].copy()
    displacement[nr//2+1:,:,0]*=-1
    displacement[:,np.sin(state['theta'])< -1e-12,1]*=-1
    displacement[nr//2,:,0]=0;displacement[:,[0,nt//2],1]=0
    out['grid']+=displacement
    newoff=out['grid']-c[:,None,:];newxy=np.stack([(newoff[:,:,[0,2]]*a[:,None,:]).sum(-1),newoff[:,:,1]],axis=-1)
    radius=np.linalg.norm(actual,axis=-1);newradius=np.linalg.norm(newxy,axis=-1)
    if np.any(newradius<.15*np.linalg.norm(state['rest']-c[:,None,:],axis=-1)):
        raise ValueError('Requested refolding consumes the carrier thickness; no clipping or hidden reduction.')
    if not np.isfinite(out['grid']).all():raise ValueError('Nonfinite refolding result.')
    return out,dict(requested_radial=depth,applied_radial=depth,feature_owner=owner,
                    requested_signed_fold_distance=depth,applied_signed_fold_distance=depth,
                    total_applied_distance=np.linalg.norm(displacement,axis=-1),
                    direction_local=direction,longitudinal_displacement=dz,source_signal=signal,
                    direction_global_read=global_direction,applied_displacement=displacement,
                    axial_profile=axial_profile,axial_owner=axial_owner,axial_feature_table=axial_table,actual_axis_arc=actual_arc),records


def symmetry(mesh,chart,check_faces=False):
    records={}
    for name,axis,centre in [('LR',0,PLANE_X),('FB',1,PLANE_Y)]:
        mirrored=chart.copy()
        if name=='LR':mirrored[:,0]=1-mirrored[:,0]
        else:mirrored[:,2]*=-1
        distance,pair=cKDTree(chart).query(mirrored)
        if distance.max()>1e-10 or not np.array_equal(pair[pair],np.arange(len(pair))):raise ValueError('Symmetry chart is not an involution.')
        xyz=mesh.xyz.copy();xyz[:,axis]=2*centre-xyz[:,axis]
        records[name]=dict(chart_max=float(distance.max()),geometry_max=float(np.linalg.norm(xyz-mesh.xyz[pair],axis=1).max()))
        if check_faces:
            if np.any(mesh.faces[:,3]!=-1):raise ValueError('Explicit native triangles required for cycle proof.')
            def canonical(t):
                slot=(np.arange(3)[None,:]+np.argmin(t,axis=1)[:,None])%3
                return np.take_along_axis(t,slot,axis=1)
            a=canonical(mesh.faces[:,:3]);b=canonical(pair[mesh.faces[:,:3][:,::-1]])
            a=a[np.lexsort(a.T)];b=b[np.lexsort(b.T)]
            records[name]['oriented_triangle_cycle_failures']=int(np.any(a!=b,axis=1).sum())
    return records
