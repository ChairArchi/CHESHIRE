"""Task27: explicit port-connected profiles and measured local CC feedback.

No Task26 fold recipe, route field, crease network or original-ring refit.
Existing COMPAS crease-inactive CC and Extended CC / equation 4 are reused.
"""
from collections import defaultdict
from copy import deepcopy
from math import cos, sin, pi, sqrt, hypot, isfinite
import numpy as np
from compas.datastructures import Mesh
from .ornament import source_history
from .branching import BranchSignatures
from .fold_continuation import fold_state
from .generational_subdivision import generational_subdivide_once
from .progressive_gates import PLANE_X, PLANE_Y, advance_gate, cycle_key
from .validation import validate_mesh

STATIONS=[('base',0,900,500),('lower_body',420,1050,580),
          ('body',1050,900,500),('constriction',1600,560,380),
          ('expansion',2020,1040,600),('neck',2450,340,260),
          ('shoulder',2780,1200,640),('port',2900,1200,640)]


def definition(profile=True):
    stations=[dict(zone=n,z=z,width=w if profile else 900,
        depth=d if profile else (640 if z>=2780 else 500),
        longitudinal=z/2900,frame=dict(T=[0,0,1],U=[1,0,0],V=[0,1,0]),
        section='RECT8' if z>=2780 else 'ELLIPSE8') for n,z,w,d in STATIONS]
    return dict(schema='TASK27_PORT_GATE_V1',profile=profile,stations=stations,
        centers_X=[PLANE_X-1350,PLANE_X+1350],Y=PLANE_Y,Z_up=True,
        units='UNRESOLVED original coordinate units',beam=dict(length=4000,
        bottom=2900,top=3500,depth=640,frame=dict(T=[1,0,0],U=[0,0,1],V=[0,-1,0])),
        joint='Remove beam-bottom cells over two rectangular ports; reuse their eight perimeter vertices as column top ring. No overlapping closed objects.',
        samples=8,symmetry_X=PLANE_X,front_rear_symmetry='Also maintained by absolute normal-Y mapping; separately diagnosed.')


def gate(defn):
    xyz={};faces={};parts={};bands={};registry={};rings={}
    def vertex(p):
        key=tuple(round(x,10) for x in p)
        if key not in registry:
            v=len(xyz);registry[key]=v;xyz[v]=list(p)
        return registry[key]
    def face(vs,part,band):
        f=len(faces);faces[f]=vs;parts[f]=part;bands[f]=band
    for side,cx in zip(('L','R'),defn['centers_X']):
        rr=[]
        for station in defn['stations']:
            ring=[]
            for j in range(8):
                c,s=cos(j*pi/4),sin(j*pi/4)
                if abs(c)<1e-14:c=0.
                if abs(s)<1e-14:s=0.
                if station['section']=='RECT8':
                    scale=max(abs(c),abs(s));c/=scale;s/=scale
                ring.append(vertex([cx+station['width']/2*c,PLANE_Y+station['depth']/2*s,station['z']]))
            rr.append(ring)
        rings[side]=rr
        for i in range(len(rr)-1):
            for j in range(8):
                k=(j+1)%8
                face([rr[i][j],rr[i][k],rr[i+1][k],rr[i+1][j]],'COLUMN_'+side,i)
        cap=vertex([cx,PLANE_Y,0])
        for j in range(8):face([cap,rr[0][(j+1)%8],rr[0][j]],'BASE_'+side,-1)
    port=defn['stations'][-1]['width'];beam=defn['beam']
    xvalues=sorted({PLANE_X-beam['length']/2,PLANE_X+beam['length']/2,
        *(cx+d*port/2 for cx in defn['centers_X'] for d in (-1,0,1))})
    ys=[PLANE_Y-beam['depth']/2,PLANE_Y,PLANE_Y+beam['depth']/2]
    grid={(i,j,k):vertex([x,y,z]) for i,x in enumerate(xvalues) for j,y in enumerate(ys)
        for k,z in enumerate((beam['bottom'],beam['top']))}
    # At the ports, vertex() reuses the explicitly matching column perimeter.
    for i in range(len(xvalues)-1):
        mid=(xvalues[i]+xvalues[i+1])/2
        inside=any(abs(mid-cx)<port/2 for cx in defn['centers_X'])
        for j in range(2):
            face([grid[i,j,1],grid[i+1,j,1],grid[i+1,j+1,1],grid[i,j+1,1]],'LINTEL',i)
            if not inside:face([grid[i,j+1,0],grid[i+1,j+1,0],grid[i+1,j,0],grid[i,j,0]],'LINTEL',i)
        face([grid[i,0,0],grid[i+1,0,0],grid[i+1,0,1],grid[i,0,1]],'LINTEL',i)
        face([grid[i,2,1],grid[i+1,2,1],grid[i+1,2,0],grid[i,2,0]],'LINTEL',i)
    for i,reverse in [(0,False),(len(xvalues)-1,True)]:
        for j in range(2):
            vs=[grid[i,j,0],grid[i,j,1],grid[i,j+1,1],grid[i,j+1,0]]
            face(list(reversed(vs)) if reverse else vs,'LINTEL',i)
    used={v for cycle in faces.values() for v in cycle}
    xyz={v:p for v,p in xyz.items() if v in used}
    mesh=Mesh.from_vertices_and_faces(xyz,faces)
    if not mesh.is_connected() or not mesh.is_closed() or not mesh.is_manifold() or not mesh.is_valid():
        raise ValueError('Port joint is not one connected closed manifold.')
    # Declared station/perimeter/grid reflection, looked up in the exact input
    # registry; no nearest-point matching and no reliance on ID equality.
    vp={v:registry[tuple(round(x,10) for x in [2*PLANE_X-p[0],p[1],p[2]])] for v,p in xyz.items()}
    lookup={cycle_key(c):f for f,c in faces.items()}
    fp={f:lookup[cycle_key([vp[v] for v in reversed(c)])] for f,c in faces.items()}
    state=dict(history=source_history(mesh),source_cells={f:[parts[f]] for f in faces},
        signatures=BranchSignatures(mesh).faces,origins={},networks=[],anchors={},events=[],
        generation=dict(absolute_cc=0,continuation_depth=0),completed_step=None,next_step=None,
        input=dict(name='G0_PROFILE' if defn['profile'] else 'G0_CONTROL',definition=defn),
        gate=dict(parts=parts,vertex_pair=vp,face_pair=fp,material=xyz,selection_policy='PAIRED_FULL_GATE'),
        section=dict(bands=bands,station_vertices=rings,beam_x=xvalues,
            beam_station_vertices=[[grid[i,j,k] for j in range(3) for k in range(2) if grid[i,j,k] in used] for i in range(len(xvalues))],
            frozen_rules=None,completed=[],next='Measure actual current geometry and map next local rules'))
    return mesh,state


def restore(state):
    from .progressive_gates import restore_gate
    restore_gate(state)
    state['section']['bands']={int(k):v for k,v in state['section']['bands'].items()}
    if state['section']['frozen_rules'] is not None:
        state['section']['frozen_rules']={int(k):v for k,v in state['section']['frozen_rules'].items()}
    return state


def current_face_area(points):
    """Unsigned centroid-fan area, invariant to cycle start and reflection.

    Generated quads can be folded/nonplanar. COMPAS area_polygon chooses a
    reference triangle to sign other fan triangles; its result then depends
    on the cycle start. This measurement keeps every triangle's magnitude.
    It measures the saved polygon without changing its geometry/topology.
    """
    p=np.asarray(points,dtype=float);center=p.mean(axis=0)
    return float(.5*np.linalg.norm(np.cross(p-center,np.roll(p,-1,axis=0)-center),axis=1).sum())


def _slice_sizes(mesh,face_ids,centers,axis,width_axis):
    # A centroid fan makes the nonplanar-quad measurement invariant under
    # cycle rotation/reflection. It is a derivative, not a saved mesh edit.
    ids=list(mesh.vertices());lookup={v:i for i,v in enumerate(ids)}
    points=[mesh.vertex_coordinates(v) for v in ids];triangles=[]
    for f in face_ids:
        q=[lookup[v] for v in mesh.face_vertices(f)]
        if len(q)==3:triangles.append(q)
        else:
            center=len(points);points.append([sum(points[v][a] for v in q)/4 for a in range(3)])
            triangles.extend([q[j],q[(j+1)%4],center] for j in range(4))
    xyz=np.asarray(points,dtype=float);tri=xyz[np.asarray(triangles)]
    minimum=tri[:,:,axis].min(axis=1);maximum=tri[:,:,axis].max(axis=1);rows=[]
    for center in centers:
        plane=center[axis];candidate=tri[(minimum<=plane+1e-8)&(maximum>=plane-1e-8)]
        points=[]
        for a,b in ((0,1),(1,2),(2,0)):
            p=candidate[:,a];q=candidate[:,b];den=q[:,axis]-p[:,axis]
            crosses=(np.abs(den)>1e-10)&((p[:,axis]-plane)*(q[:,axis]-plane)<=1e-8)
            if crosses.any():
                pp=p[crosses];qq=q[crosses];t=(plane-pp[:,axis])/(qq[:,axis]-pp[:,axis])
                points.extend((pp+(qq-pp)*t[:,None]).tolist())
            points.extend(p[np.abs(p[:,axis]-plane)<1e-8].tolist())
        if not points:raise ValueError('Current actual section intersection is empty.')
        a=np.asarray(points);extent=np.ptp(a,axis=0)
        rows.append(dict(center=center,width=float(extent[width_axis]),depth=float(extent[1]),
            intersection_points=len(points),plane_axis=axis,plane_position=plane))
    return rows


def measure(mesh,state):
    parts=state['gate']['parts'];sections={};generation=state['generation']['absolute_cc']
    for side in ('L','R'):
        centers=[[sum(mesh.vertex_coordinates(v)[a] for v in ring)/len(ring) for a in range(3)]
            for ring in state['section']['station_vertices'][side]]
        fs=[f for f in mesh.faces() if parts[f]=='COLUMN_'+side]
        rows=_slice_sizes(mesh,fs,centers,2,0)
        # The base/port slice can lie outside the smoothed side-only surface.
        for i,r in enumerate(rows):r.update(zone=state['input']['definition']['stations'][i]['zone'])
        sections['COLUMN_'+side]=rows
    centers=[[sum(mesh.vertex_coordinates(v)[a] for v in ring)/len(ring) for a in range(3)]
        for ring in state['section']['beam_station_vertices']]
    sections['LINTEL']=_slice_sizes(mesh,[f for f in mesh.faces() if parts[f]=='LINTEL'],centers,0,2)
    cache={}
    for part,rs in sections.items():
        axis=0 if part=='LINTEL' else 2
        positions=np.asarray([r['center'][axis] for r in rs]);widths=[r['width'] for r in rs];depths=[r['depth'] for r in rs]
        if np.any(np.diff(positions)<=0):raise ValueError('Current section plane order is unusable.')
        cache[part]=(axis,positions,widths,depths,np.gradient(widths,positions))
    normals={f:list(mesh.face_normal(f)) for f in mesh.faces()}
    curvature={}
    for f,n in normals.items():
        neighbors=mesh.face_neighbors(f)
        curvature[f]=sum(max(0.,min(1.,(1-sum(a*b for a,b in zip(n,normals[g])))/2)) for g in neighbors)/len(neighbors) if neighbors else 0.
    descriptors={}
    for f in mesh.faces():
        part=parts[f];centroid=list(mesh.face_centroid(f));normal=normals[f];area=current_face_area(mesh.face_coordinates(f))
        if part.startswith('BASE_'):
            row=dict(part=part,coarse=list(state['history'][f]['source']),centroid=centroid,normal=normal,
                width=0.,depth=0.,constriction=0.,expansion=0.,slope=0.,longitudinal=0.,
                joint_distance=0.,T=[0,0,1],h=sqrt(area),sharpness=0.,generation=generation)
        else:
            rs=sections[part];axis,positions,widths,depths,slopes=cache[part]
            x=centroid[axis];width=float(np.interp(x,positions,widths));depth=float(np.interp(x,positions,depths))
            slope=float(np.interp(x,positions,slopes))
            if part=='LINTEL':body=float(np.median(widths));neck=body
            else:body=rs[2]['width'];neck=rs[5]['width']
            c=max(0.,min(1.,1-width/max(body,1e-8)))
            e=max(0.,min(1.,(width/max(neck,1e-8)-1)/3))
            longitudinal=(x-positions[0])/max(positions[-1]-positions[0],1e-8)
            index=int(np.clip(np.searchsorted(positions,x)-1,0,len(rs)-2))
            T=np.subtract(rs[index+1]['center'],rs[index]['center']);T=T/max(np.linalg.norm(T),1e-8)
            row=dict(part=part,coarse=list(state['history'][f]['source']),centroid=centroid,normal=normal,
                width=width,depth=depth,constriction=c,expansion=e,slope=max(-2.,min(2.,slope)),
                longitudinal=longitudinal,joint_distance=abs(x-(positions[-1] if part!='LINTEL' else positions[len(rs)//2])),
                T=T.tolist(),h=sqrt(area),sharpness=0.,generation=generation)
        if not all(isfinite(v) for v in row['centroid']+row['normal']+[row['width'],row['depth'],row['h']]):
            raise ValueError('Non-finite current geometry measurement.')
        row['normal_contrast']=curvature[f]
        row['sharpness']=max(mesh.edge_attribute(e,'crease') or 0. for e in mesh.face_halfedges(f))
        descriptors[f]=row
    return dict(generation=generation,sections=sections,faces=descriptors,
        method='Current original-ring-corner centroids place planes; extents come from actual current side-mesh centroid-fan triangle/plane intersections. Current face centroid/normal and unsigned centroid-fan area are reread; area is invariant to cyclic rotation and reflection even for folded quads. Authored rings are never refitted.')


def map_rules(descriptors,config):
    rules={}
    for f,d in descriptors['faces'].items():
        if d['part'].startswith('BASE_'):
            rules[f]=dict(wf=0.,w1=0.,we=0.,w2=0.,wp=0.,w3=0.,w4=0.);continue
        c,e,s=d['constriction'],d['expansion'],abs(d['slope'])
        side=max(0.,1-abs(sum(a*b for a,b in zip(d['normal'],d['T']))))
        azimuth=.5+.5*abs(d['normal'][1]);k=.35+.4*c+.25*e+.2*min(s,1.)
        beam=.65 if d['part']=='LINTEL' else 1.
        wf=config['offset_ratio']*d['h']*k*side*azimuth*beam
        damping=1-config.get('curvature_gain',0.)*min(1.,d.get('normal_contrast',0.)/.35)
        rules[f]=dict(wf=wf,w1=-config['edge_gain']*(.12+.25*c),we=-.35*wf,
            w2=-config['edge_gain']*(.12+.3*c),wp=.08*wf,
            w3=-config['face_gain']*(.45+1.25*c+.35*e)*side*damping,
            w4=(.35+.3*e)*side)
    return rules


def step(mesh,state,path,config,budget):
    measured=None
    if path.endswith('_CC'):
        result,next_state=fold_state(mesh,state,dict(weights={}),budget=budget)
        rules={};method='Existing COMPAS crease-inactive standard CC, no additional displacement.'
    else:
        if path=='PROFILE_STATIC' and state['section']['frozen_rules'] is not None:
            rules=deepcopy(state['section']['frozen_rules']);method='Inherited G0 parameter values; no current measurement used by mapping.'
        else:
            measured=measure(mesh,state);rules=map_rules(measured,config)
            method='G0 measurement frozen for descendants' if path=='PROFILE_STATIC' else 'Fresh actual immediately preceding geometry measurement'
        face={f:dict(wf=r['wf']) for f,r in rules.items()}
        edge={tuple(sorted(e)):{k:sum(rules[f][k] for f in mesh.edge_faces(e))/2 for k in ('w1','we')} for e in mesh.edges()}
        corner={v:{k:sum(rules[f][k] for f in mesh.vertex_faces(v))/len(mesh.vertex_faces(v)) for k in ('w2','wp')} for v in mesh.vertices()}
        result=generational_subdivide_once(mesh,{},origin_lineage=state['origins'],
            point_weights=dict(face=face,edge=edge,corner=corner),
            face_weights={f:{k:r[k] for k in ('w3','w4')} for f,r in rules.items()},
            budget=budget,current_generation=state['generation']['absolute_cc'])
        # Adapt only metadata shape to the existing constructive correspondence.
        result.metadata['edge_points']=[dict(point=r['id'],edge=r['source']) for r in result.metadata['points'] if r['point_class']=='edge']
        next_state={**state,'origins':result.origin_lineage,'generation':dict(absolute_cc=state['generation']['absolute_cc']+1,
            continuation_depth=state['generation']['continuation_depth']+1),'completed_step':config,'next_step':None}
        for field in ('history','source_cells','signatures'):
            next_state[field]={r['id']:state[field][r['source_face']] for r in result.metadata['face_sources']}
        next_state['history']={f:{**h,'operator_depth':state['generation']['absolute_cc']+1} for f,h in next_state['history'].items()}
    next_state=advance_gate(mesh,result,state,next_state)
    section={**state['section']}
    section['bands']={r['id']:state['section']['bands'][r['source_face']] for r in result.metadata['face_sources']}
    if path=='PROFILE_STATIC':section['frozen_rules']={r['id']:rules[r['source_face']] for r in result.metadata['face_sources']}
    section['completed']=state['section']['completed']+[dict(path=path,input_generation=state['generation']['absolute_cc'],config=config,method=method)]
    section['next']='Standard CC' if path.endswith('_CC') else 'Reuse frozen G0 rules' if path=='PROFILE_STATIC' else 'Reread current generated geometry, measure slices and map rules again'
    next_state['section']=section
    if validate_mesh(result.mesh) or not result.mesh.is_valid():raise ValueError('Generated geometry is not finite/topologically usable.')
    return result,next_state,measured,rules,method
