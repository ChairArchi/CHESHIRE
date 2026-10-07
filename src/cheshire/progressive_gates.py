"""Task26 matched cages, material-space regions and constructive reflection.

These helpers concern the full closed U carrier and actual CC used here only.
No reflected coordinate averaging or independently subdivided half meshes.
"""
from math import cos, sin, pi, hypot, dist, exp
from compas.datastructures import Mesh
from .ornament import source_history
from .branching import BranchSignatures

PLANE_X=-400.036865234375
PLANE_Y=-18.533447265625


def gate_input(section='RECT',profile=False):
    if section not in ('RECT','ROUND'):raise ValueError('Unknown matched section.')
    # Tangents follow the left-base -> lintel -> right-base swept U. Cross-
    # section u is Y-cross-tangent; v is Y (u cross v follows tangent).
    # Continuous shared rings join parts.
    path=[(-1550,0,1,0),(-1550,1300,1,0),(-1550,2600,1,0),
          (-1550,3050,2**-.5,-2**-.5),(0,3050,0,-1),
          (1550,3050,-2**-.5,-2**-.5),(1550,2600,-1,0),
          (1550,1300,-1,0),(1550,0,-1,0)]
    xyz={};faces={};parts={}
    for r,(x,z,ux,uz) in enumerate(path):
        scale=(.72 if z==1300 else 1.12 if z==2600 else 1.) if profile else 1.
        for j in range(8):
            c,s=cos(j*pi/4),sin(j*pi/4)
            if abs(c)<1e-14:c=0.
            if abs(s)<1e-14:s=0.
            if section=='RECT':
                divisor=max(abs(c),abs(s));c/=divisor;s/=divisor
            xyz[r*8+j]=[PLANE_X+x+ux*450*c*scale,PLANE_Y+250*s*scale,z+uz*450*c*scale]
    # With u x v following tangent, reverse side winding gives outward faces.
    labels=['SUPPORT_LOWER_L','SUPPORT_UPPER_L','SHOULDER_L','LINTEL_L',
            'LINTEL_R','SHOULDER_R','SUPPORT_UPPER_R','SUPPORT_LOWER_R']
    for r in range(8):
        for j in range(8):
            k=(j+1)%8;f=r*8+j
            faces[f]=[r*8+j,r*8+k,(r+1)*8+k,(r+1)*8+j];parts[f]=labels[r]
    xyz[72]=[PLANE_X-1550,PLANE_Y,0];xyz[73]=[PLANE_X+1550,PLANE_Y,0]
    for j in range(8):
        k=(j+1)%8
        faces[64+j]=[72,k,j];parts[64+j]='FOOT_L'
        faces[72+j]=[73,64+j,64+k];parts[72+j]='FOOT_R'
    mesh=Mesh.from_vertices_and_faces(xyz,faces)
    # Ring r reflects to 8-r. Its u direction is already reflected, Y stays.
    vp={r*8+j:(8-r)*8+j for r in range(9) for j in range(8)}
    vp.update({72:73,73:72})
    lookup={cycle_key(c):f for f,c in faces.items()}
    fp={f:lookup[cycle_key([vp[v] for v in reversed(c)])] for f,c in faces.items()}
    history=source_history(mesh)
    state=dict(history=history,events=[],source_cells={f:[parts[f]] for f in mesh.faces()},
        signatures=BranchSignatures(mesh).faces,anchors={},origins={},networks=[],seed=None,
        generation=dict(absolute_cc=0,continuation_depth=0),completed_step=None,next_step=None,
        input=dict(name='INPUT_'+section+('_PROFILE' if profile else ''),units='UNRESOLVED',
            new_identity=True,section=section,profile=profile,frame=dict(X=PLANE_X,Y=PLANE_Y,Z_up=True),
            nominal_dimensions=[4000,500,3500],support_footprint=[900,500],
            nominal_opening=[2200,2600],joint='Shared 8-sided swept rings; rotated shoulder section, not cylinder/box overlap.'),
        gate=dict(parts=parts,vertex_pair=vp,face_pair=fp,material=xyz,
            orientation='Outward cycles; reflection determinant -1 requires reverse cycles. Normal offsets are unsigned outward lengths; w1..w7 scalar coefficients unchanged.',
            selection_policy='PAIRED_FULL_GATE',routes=[]))
    return mesh,state


def cycle_key(c):
    i=c.index(min(c));return tuple(c[i:]+c[:i])


def restore_gate(state):
    for k in ('parts','vertex_pair','face_pair','material'):
        state['gate'][k]={int(i):v for i,v in state['gate'][k].items()}
    return state


def advance_gate(before,result,old_state,new_state):
    old=old_state['gate'];vp=old['vertex_pair'];fp=old['face_pair'];mat=old['material']
    edges={tuple(sorted(r['edge'])):r['point'] for r in result.metadata['edge_points']}
    new_vp={v:vp[v] for v in before.vertices()};new_mat={v:mat[v] for v in before.vertices()}
    for e,p in edges.items():
        new_vp[p]=edges[tuple(sorted(vp[v] for v in e))]
        new_mat[p]=[sum(mat[v][a] for v in e)/2 for a in range(3)]
    originals=set(before.vertices());edge_points=set(edges.values());face_points={};children={}
    parts={}
    for row in result.metadata['face_sources']:
        f,parent=row['id'],row['source_face'];cycle=result.mesh.face_vertices(f)
        corners=originals.intersection(cycle)
        if len(corners)!=1:raise ValueError('CC child must contain one actual parent corner.')
        corner=corners.pop();children[(parent,corner)]=f
        face_points[parent]=(set(cycle)-originals-edge_points).pop()
        parts[f]=old['parts'][parent]
    for f,p in face_points.items():
        new_vp[p]=face_points[fp[f]];vertices=before.face_vertices(f)
        new_mat[p]=[sum(mat[v][a] for v in vertices)/len(vertices) for a in range(3)]
    new_fp={f:children[(fp[parent],vp[corner])] for (parent,corner),f in children.items()}
    new_state['gate']={**old,'parts':parts,'vertex_pair':new_vp,'face_pair':new_fp,'material':new_mat}
    return new_state


def symmetry(mesh,state):
    gate=state['gate'];vp=gate['vertex_pair'];fp=gate['face_pair'];maximum=0.;square=0.;fail=0
    for v in mesh.vertices():
        p=mesh.vertex_coordinates(v);q=mesh.vertex_coordinates(vp[v])
        error=dist([2*PLANE_X-p[0],p[1],p[2]],q);maximum=max(maximum,error);square+=error*error
        if vp[vp[v]]!=v:raise ValueError('Vertex reflection is not an involution.')
    for f in mesh.faces():
        reflected=[vp[v] for v in reversed(mesh.face_vertices(f))]
        if fp[fp[f]]!=f or cycle_key(reflected)!=cycle_key(mesh.face_vertices(fp[f])):fail+=1
    return dict(plane_X=PLANE_X,plane_Y_not_enforced=PLANE_Y,
        max_coordinate_residual=maximum,rms_coordinate_residual=(square/mesh.number_of_vertices())**.5,
        residual_over_nominal_width=maximum/4000,vertex_correspondences=len(vp),
        face_correspondences=len(fp),oriented_face_failures=fail,
        policy=gate['selection_policy'],method='Constructive ring/CC-parent correspondence, reverse oriented face cycles; no nearest-point correspondence or averaging.')


def physical_support(mesh,state,rule):
    """Fixed input-material physical region, transported by bilinear CC origins.

    This is a region coordinate, not a second subdivided geometry or a graph-hop
    count. Its declared units/width do not shrink with tessellation depth.
    """
    mat=state['gate']['material'];kind=rule.get('kind','ALL')
    values={}
    for v,(x,y,z) in mat.items():
        x-=PLANE_X;y-=PLANE_Y
        if kind=='ALL':a=1.
        elif kind=='UPPER':a=min(1.,max(0.,(z-rule.get('quiet_below',1700))/rule.get('transition',600)))
        elif kind=='DISTRIBUTED':
            # Nonuniform repeated zones inside both large supports and mantle.
            # Absolute radius/locations stay fixed across generations.
            zones=rule['zones'];a=max(exp(-((abs(x)-cx)/rx)**2-((z-cz)/rz)**2) for cx,cz,rx,rz in zones)
        elif kind=='ROUTE_BAND':
            # Multi-source weighted graph distance in physical input material
            # coordinates. Active actual route edges/seed vertices supplied below.
            values=None;break
        else:raise ValueError('Unknown physical support rule.')
        if rule.get('front_only'):a*=max(0.,min(1.,(-y+40)/220))
        values[v]=a
    if values is not None:return values
    from heapq import heappush,heappop
    radius=rule['radius'];seeds={v for n in state['networks'] for e in n['edges'] for v in e['vertices']}
    if not seeds:raise ValueError('No actual route seeds.')
    distances={v:0. for v in seeds};queue=[(0.,v) for v in seeds]
    from heapq import heapify
    heapify(queue)
    while queue:
        d,v=heappop(queue)
        if d!=distances[v]:continue
        for u in mesh.vertex_neighbors(v):
            q=d+dist(mat[v],mat[u])
            if q<radius and q<distances.get(u,radius):distances[u]=q;heappush(queue,(q,u))
    return {v:max(0.,1-distances.get(v,radius)/radius) for v in mesh.vertices()}
