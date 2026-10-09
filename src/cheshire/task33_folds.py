"""Finite three-scale material folds, independent of subdivision cell size.

Original U carrier and closed topology retained. Bilinear refinement samples
the carrier; it does not smooth geometry. No claim of Hansmeyer's algorithm,
physical buckling, a fractal, or certified collision-free geometry.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, subdivide, topology, mean_incident
from .progressive_gates import PLANE_X, PLANE_Y


def initial_chart(mesh):
    if len(mesh.xyz) != 74 or len(mesh.faces) != 80:
        raise ValueError('Only the unchanged Task31 RECT carrier is supported.')
    centres = mesh.xyz[:72].reshape(9, 8, 3).mean(1)
    lengths = np.r_[0., np.cumsum(np.linalg.norm(np.diff(centres,axis=0),axis=1))]
    lengths /= lengths[-1]
    a = np.arange(8)*np.pi/4
    u, v = np.cos(a), np.sin(a)
    divisor = np.maximum(np.abs(u), np.abs(v))
    u, v = u/divisor, v/divisor
    chart = np.array([[s, x, y] for s in lengths for x,y in zip(u,v)])
    chart = np.vstack([chart, [0,0,0], [1,0,0]])
    return dict(carrier=mesh.xyz.copy(), chart=chart, centres=centres, knots=lengths)


def refine(mesh, state, *, carrier_smoothing=False, smooth_geometry=False):
    out, meta, op = subdivide(mesh, {'weights':{}}, scale_mode='LOCAL_INCIDENT_SCALE')
    t = topology(mesh)
    def linear(a):
        return np.concatenate([a, a[t['edges']].mean(1), mean_incident(a[t['a']],t['fi'],len(mesh.faces))])
    carrier=linear(state['carrier'])
    if carrier_smoothing:
        cage=ArrayMesh(state['carrier'],mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
        smooth,_,_=subdivide(cage,{'weights':{}},scale_mode='LOCAL_INCIDENT_SCALE')
        carrier=smooth.xyz
    new = dict(state, carrier=carrier, chart=linear(state['chart']))
    # Explicitly overwrite every CC position. No geometric CC averaging survives.
    if not smooth_geometry:out.xyz = linear(mesh.xyz)
    meta['geometry'] = 'Every CC position overwritten by unchanged V / endpoint midpoint / face centroid; bilinear refinement.'
    if smooth_geometry:meta['geometry']='Actual neutral CC coordinates retained; geometric smoothing ablation.'
    meta['carrier_smoothing']=carrier_smoothing
    return out, new, meta, op


def refine_section(mesh,state):
    """Split section edges only; caps receive full bilinear refinement.

    Shared-edge decisions use the continuous material arc coordinate, so both
    incident faces split identically. Side quads split into two quads; cap
    polygons split into corner quads. This is not Catmull--Clark geometry.
    """
    t=topology(mesh);edges=t['edges'];nv=len(mesh.xyz)
    selected=np.abs(state['chart'][edges[:,0],0]-state['chart'][edges[:,1],0])<1e-12
    edge_ids=np.flatnonzero(selected);mapping=np.full(len(edges),-1,np.int64)
    mapping[edge_ids]=nv+np.arange(len(edge_ids))
    caps=[];cycles=[];parents=[]
    for i,row in enumerate(mesh.faces):
        q=row[row>=0];eid=t['fe'][i,:len(q)];chosen=np.flatnonzero(selected[eid])
        if len(chosen)==len(q):
            centre=nv+len(edge_ids)+len(caps);caps.append(i)
            for j in range(len(q)):
                cycles.append([mapping[eid[j-1]],q[j],mapping[eid[j]],centre]);parents.append(i)
        elif len(q)==4 and len(chosen)==2 and (chosen[1]-chosen[0])==2:
            k=int(chosen[0]);q=np.roll(q,-k);eid=np.roll(eid,-k)
            a,b=mapping[eid[0]],mapping[eid[2]]
            cycles.extend([[q[0],a,b,q[3]],[a,q[1],q[2],b]]);parents.extend([i,i])
        else:raise ValueError('Section refinement requires opposite selected edges or complete caps.')
    caps=np.asarray(caps,np.int64);parents=np.asarray(parents,np.int64)
    def linear(a):
        centres=mean_incident(a[t['a']],t['fi'],len(mesh.faces))
        return np.concatenate([a,a[edges[edge_ids]].mean(1),centres[caps]])
    xyz=linear(mesh.xyz)
    out=ArrayMesh(xyz,np.asarray(cycles,np.int64),
                  np.r_[np.zeros(nv,np.int8),np.ones(len(edge_ids),np.int8),np.full(len(caps),2,np.int8)],
                  linear(mesh.rest),mesh.anchors[parents].copy(),mesh.generation+1)
    new=dict(state,carrier=linear(state['carrier']),chart=linear(state['chart']))
    if mesh.generation<3:out.anchors[:,mesh.generation]=np.arange(len(out.faces))
    topology(out) # Shared edges must remain closed, no repair.
    return (out,new,dict(geometry='Section-only bilinear refinement; previous positions unchanged.',
                        side_faces_split=2,cap_faces_split='one quad per corner',carrier_smoothing=False),
                        dict(input_edges=edges[edge_ids],parent_face=parents,cap_input_faces=caps))


def fold_values(chart, params, levels):
    if levels not in (0,1,2,3):
        raise ValueError('Finite levels 0..3 required.')
    allowed={'neck_location','neck_locations','neck_span','convergence','lobes','sweep',
             'coupling','amplitudes','waist','windowed','child_floor','child_frequency_variation',
             'parent_gate_power','micro_frequency','twist','twist_start','twist_end',
             'child_phase_shift','micro_phase_shift','micro_coupling','fine_mode',
             'micro_slope_scale','gradient_epsilon','macro_recess','paired_controls'}
    if set(params)-allowed:raise ValueError('Unknown fold parameters: '+str(sorted(set(params)-allowed)))
    for key,value in params.items():
        if key=='fine_mode':
            if value not in ('phase','meso_slope','meso_notch'):raise ValueError('Unknown fine mechanism.')
            continue
        if not np.isfinite(np.asarray(value,dtype=float)).all():raise ValueError('Nonfinite fold control: '+key)
    if not 0<=params.get('macro_recess',0)<200:raise ValueError('Recess must preserve positive carrier thickness.')
    if params.get('lobes',1.15)<=0 or params.get('micro_frequency',3)<=1:
        raise ValueError('Positive macro frequency and finer micro frequency required.')
    if not 0<=params.get('waist',.28)<1 or not 0<=params.get('convergence',.6)<1:
        raise ValueError('Waist and convergence must be within [0,1).')
    if params.get('parent_gate_power',1)<1 or params.get('child_frequency_variation',0)<0:
        raise ValueError('Positive parent gate power and nonnegative frequency variation required.')
    if params.get('child_frequency_variation',0) and (params.get('child_floor',.2)!=0 or params.get('parent_gate_power',1)<2):
        raise ValueError('Variable local child phase requires zero valley floor and a squared parent gate for continuity.')
    s,u,v = chart.T
    q = np.minimum(s,1-s)
    # Symmetric physical chart, two broad basins separated by narrow bindings.
    locations=params.get('neck_locations',[params.get('neck_location',.18)])
    if not 1<=len(locations)<=4 or params.get('neck_span',.065)<=0 or np.any((np.asarray(locations)<0)|(np.asarray(locations)>.5)):
        raise ValueError('One to four explicit finite binding locations and positive span required.')
    neck=np.max([np.exp(-((q-loc)/params.get('neck_span',.065))**2) for loc in locations],axis=0)
    upper = np.exp(-((q-.39)/.055)**2)
    fan = 1 - params.get('convergence',.6)*neck - .25*params.get('convergence',.6)*upper
    if np.any(fan<=.15):
        raise ValueError('Convergence leaves insufficient chart width.')
    foot = np.clip(q/.055,0,1)
    foot = foot*foot*(3-2*foot) # scalar envelope only, not geometric smoothing.
    theta = 2*np.pi*params.get('lobes',1.15)*u/fan + params.get('sweep',.65)*np.cos(2*np.pi*q/.32)
    parent = .5+.5*np.cos(theta)
    if params.get('windowed',False):
        envelope=np.exp(-.5*(u/fan/1.05)**8)
        parent*=envelope
    frequency=3+params.get('child_frequency_variation',0)*(.5+.5*np.cos(2*np.pi*q/.24))
    if params.get('child_frequency_variation',0):
        local_phase=np.arctan2(np.sin(theta),np.cos(theta))
        child_phase=frequency*local_phase+params.get('coupling',1.4)*np.sin(theta)
    else:child_phase = 3*theta+params.get('coupling',1.4)*np.sin(theta)
    child_phase+=params.get('child_phase_shift',0)
    child = .5+.5*np.cos(child_phase)
    micro = .5+.5*np.cos(params.get('micro_frequency',3)*child_phase+params.get('micro_coupling',1)*np.sin(theta)+params.get('micro_phase_shift',0))
    a = params.get('amplitudes',[390,100,28])
    amplitudes = np.array(a,dtype=float)
    if amplitudes.shape!=(3,) or not np.isfinite(amplitudes).all() or np.any(amplitudes<0):
        raise ValueError('Three finite nonnegative amplitudes required.')
    depth = np.zeros(len(chart))
    if levels>=1:depth += a[0]*parent
    floor=params.get('child_floor',.2)
    if not 0<=floor<=1:raise ValueError('Child floor must be in [0,1].')
    gate=floor+(1-floor)*parent**params.get('parent_gate_power',1)
    width = 1-params.get('waist',.28)*neck+.12*np.exp(-((q-.31)/.10)**2)
    slope=np.zeros(len(chart))
    fine_mode=params.get('fine_mode','phase')
    if fine_mode=='meso_notch' and a[2]>a[1]:
        raise ValueError('A notch may not remove more than the meso contribution.')
    if fine_mode in ('meso_slope','meso_notch'):
        if levels>=3:
            eps=params.get('gradient_epsilon',1e-5);scale=params.get('micro_slope_scale',12)
            if eps<=0 or scale<=0:raise ValueError('Positive derivative step and slope scale required.')
            plus=chart.copy();minus=chart.copy();plus[:,1]+=eps;minus[:,1]-=eps
            derivative=(fold_values(plus,params,2)['depth']-fold_values(minus,params,2)['depth'])/(2*eps)
            # Generated meso depth field response, not a general actual-mesh
            # curvature estimator. Fixed nominal physical section scale.
            slope=derivative/(450*width)
            micro=(np.sin(np.pi*np.tanh(np.abs(slope)/scale))**2 if fine_mode=='meso_slope'
                   else -np.exp(-(slope/scale)**2))
        else:micro=np.zeros(len(chart))
    if levels>=2:depth += a[1]*gate*child
    if levels>=3:depth += a[2]*gate*(floor+(1-floor)*child)*micro
    depth *= foot
    if levels:depth-=params.get('macro_recess',0)*foot
    return dict(depth=depth, width=width, fan=fan, parent_phase=theta,
                child_phase=child_phase, parent=parent, child=child, foot=foot,meso_depth_slope=slope)


def evaluate(mesh, state, params, levels):
    f = fold_values(state['chart'],params,levels)
    pair=None
    if params.get('paired_controls',False):
        from scipy.spatial import cKDTree
        reflected=state['chart'].copy();reflected[:,0]=1-reflected[:,0]
        distance,pair=cKDTree(state['chart']).query(reflected)
        if distance.max()>1e-10 or not np.array_equal(pair[pair],np.arange(len(pair))):
            raise ValueError('Control reflection correspondence is invalid.')
        right=state['chart'][:,0]>.5
        # Reflect scalar controls BEFORE deformation, never average XYZ.
        for value in f.values():value[right]=value[pair[right]]
    base = state['carrier']
    s = state['chart'][:,0]
    centre = np.column_stack([np.interp(s,state['knots'],state['centres'][:,k]) for k in range(3)])
    xyz = base.copy()
    xyz[:,[0,2]] = centre[:,[0,2]] + (base[:,[0,2]]-centre[:,[0,2]])*f['width'][:,None]
    xyz[:,1] = PLANE_Y+(base[:,1]-PLANE_Y)*(1+f['depth']/250)
    twist=params.get('twist',0)
    f['twist_angle']=np.zeros(len(base))
    if not np.isfinite(twist) or abs(twist)>.8:raise ValueError('Twist must be finite and within 0.8 radians.')
    if twist:
        directions=state.get('directions')
        if directions is None:
            # Original carrier section axes, transported through its fixed knots.
            path=np.array([[1,0],[1,0],[1,0],[2**-.5,-2**-.5],[0,-1],[-2**-.5,-2**-.5],[-1,0],[-1,0],[-1,0]])
            directions=np.column_stack([np.interp(s,state['knots'],path[:,k]) for k in range(2)])
            directions/=np.linalg.norm(directions,axis=1)[:,None]
        q=np.minimum(s,1-s)
        angle=twist*np.sin(2*np.pi*q/.31)*f['foot']
        if 'twist_end' in params:
            start=params.get('twist_start',.21);end=params['twist_end']
            if not 0<start<end<.5:raise ValueError('Ordered twist support bounds required.')
            envelope=np.clip((end-q)/(end-start),0,1)
            angle*=envelope*envelope*(3-2*envelope)
        if pair is not None:angle[right]=angle[pair[right]]
        f['twist_angle']=angle.copy()
        off=xyz[:,[0,2]]-centre[:,[0,2]]
        u=(off*directions).sum(1);v=xyz[:,1]-PLANE_Y
        xyz[:,[0,2]]+=directions*(u*(np.cos(angle)-1)-v*np.sin(angle))[:,None]
        xyz[:,1]=PLANE_Y+u*np.sin(angle)+v*np.cos(angle)
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite generated geometry rejected.')
    out = ArrayMesh(xyz,mesh.faces.copy(),mesh.classes.copy(),mesh.rest.copy(),mesh.anchors.copy(),mesh.generation)
    return out, f


def reflection_error(state, xyz):
    # Actual paired chart coordinates, not a nearest-point geometry approximation.
    from scipy.spatial import cKDTree
    chart=state['chart']; reflected=chart.copy(); reflected[:,0]=1-reflected[:,0]
    distance,pair=cKDTree(chart).query(reflected)
    if distance.max()>1e-10 or not np.array_equal(pair[pair],np.arange(len(pair))):
        raise ValueError('Chart reflection correspondence lost or ambiguous.')
    target=xyz.copy(); target[:,0]=2*PLANE_X-target[:,0]
    return float(np.linalg.norm(target-xyz[pair],axis=1).max())
