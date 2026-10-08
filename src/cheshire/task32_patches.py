"""Connected disk-patch sweeps for Task32; an independent constructive experiment.

Uses the familiar extrusion principle, not a new subdivision formula. Compared
with Task23's per-face Mola events, the changed condition is a connected,
multi-face cap, a curved multi-ring neck and inherited patch scope. No boolean
union, welding, hidden repair or claim of emergent topology is made.
"""
from dataclasses import replace
import numpy as np
from .reference_subdivision import ArrayMesh, topology, fields, unit


def disk_boundary(mesh, selection):
    selection = np.asarray(selection, dtype=np.int64)
    if not len(selection) or len(np.unique(selection)) != len(selection):
        raise ValueError('Nonempty unique disk faces required.')
    if selection.min() < 0 or selection.max() >= len(mesh.faces):
        raise ValueError('Disk selection outside mesh.')
    directed = {}
    for f in selection:
        q = mesh.faces[f]; q = q[q >= 0]
        for a, b in zip(q, np.roll(q, -1)):
            directed.setdefault(tuple(sorted((int(a), int(b)))), []).append((int(a), int(b), int(f)))
    edges = [row[0] for row in directed.values() if len(row) == 1]
    if any(len(row) > 2 for row in directed.values()):
        raise ValueError('Nonmanifold selected patch.')
    vertices = np.unique(mesh.faces[selection][mesh.faces[selection] >= 0])
    if len(vertices)-len(directed)+len(selection) != 1:
        raise ValueError('Patch must have disk Euler 1, no holes or disconnected pieces.')
    outgoing = {}; incoming = {}
    for a,b,f in edges:
        if a in outgoing or b in incoming:
            raise ValueError('Pinched patch boundary.')
        outgoing[a] = (b, f); incoming[b] = a
    if set(outgoing) != set(incoming) or not edges:
        raise ValueError('Closed patch boundary required.')
    start = min(outgoing); ring = [start]; owners = []
    while True:
        b, f = outgoing[ring[-1]]; owners.append(f)
        if b == start:
            break
        if b in ring:
            raise ValueError('Multiple or broken boundary loops.')
        ring.append(b)
    if len(ring) != len(edges):
        raise ValueError('Multiple boundary components.')
    return vertices, np.asarray(ring), np.asarray(owners)


def sweep_disk(mesh, selection, spec, face_scope=None, new_scope=1):
    vertices, ring, owners = disk_boundary(mesh, selection)
    selection = np.asarray(selection, np.int64)
    t = topology(mesh); f = fields(mesh, t)
    centre = mesh.xyz[vertices].mean(0)
    normal = unit((f['nf'][selection]*f['area'][selection, None]).sum(0)[None])[0]
    if np.linalg.norm(normal) < .5:
        raise ValueError('Patch has cancelling normals.')
    direction = np.asarray(spec.get('direction', [0, 0, 1]), float)
    direction -= normal*np.dot(normal, direction)
    direction = unit(direction[None])[0]
    if np.linalg.norm(direction) < .5:
        direction = unit((mesh.xyz[ring[1]]-mesh.xyz[ring[0]])[None])[0]
    side = np.cross(normal, direction)
    relative = mesh.xyz[vertices]-centre
    radius = float(np.sqrt(f['area'][selection].sum()/np.pi))
    heights = np.asarray(spec.get('heights', [.2, .6, 1.0]), float)*radius
    scales = np.asarray(spec.get('scales', [.7, .65, .45]), float)
    if len(heights) != len(scales) or not len(scales) or np.any(scales <= 0) or np.any(heights <= 0) or np.any(np.diff(heights) <= 0):
        raise ValueError('Increasing finite heights and positive matching scales required.')
    if not np.isfinite(heights).all() or not np.isfinite(scales).all():
        raise ValueError('Finite ring parameters required.')
    xyz = mesh.xyz.tolist(); rest = mesh.rest.tolist(); classes = mesh.classes.tolist()
    interior = set(vertices)-set(ring)
    mapping = {int(v):int(v) for v in vertices}
    keep = np.ones(len(mesh.faces), bool); keep[selection] = False
    polys = [q[q >= 0].tolist() for q in mesh.faces[keep]]
    parents = np.flatnonzero(keep).tolist()
    scopes = (np.zeros(len(mesh.faces), np.int64) if face_scope is None else np.asarray(face_scope)).copy()
    out_scope = scopes[keep].tolist()
    boundary_map = {int(v):i for i,v in enumerate(vertices)}
    rings = []; previous = ring.tolist()
    for level,(height, scale) in enumerate(zip(heights, scales)):
        angle = float(spec.get('twist', 0))*height/max(heights[-1], 1e-9)
        u = relative@direction; v = relative@side; n = relative@normal
        rotated = (u*np.cos(angle)-v*np.sin(angle))[:,None]*direction + \
                  (u*np.sin(angle)+v*np.cos(angle))[:,None]*side + n[:,None]*normal
        shift = float(spec.get('bend', .3))*(height**2/max(heights[-1],1e-9))*direction
        positions = centre+scale*rotated+height*normal+shift
        current = []
        for vertex in ring:
            new = len(xyz); xyz.append(positions[boundary_map[int(vertex)]].tolist())
            rest.append(mesh.rest[vertex].tolist()); classes.append(-1)
            current.append(new); mapping[int(vertex)] = new
        for j in range(len(ring)):
            k = (j+1)%len(ring)
            polys.append([previous[j],previous[k],current[k],current[j]])
            parents.append(int(owners[j])); out_scope.append(new_scope)
        rings.append(current); previous = current
    # Original interior vertices are reused in the cap, avoiding orphan vertices.
    for vertex in interior:
        xyz[vertex] = positions[boundary_map[int(vertex)]].tolist(); classes[vertex] = -1
    caps = []
    for face in selection:
        caps.append(len(polys))
        polys.append([mapping[int(v)] for v in mesh.faces[face] if v >= 0])
        parents.append(int(face)); out_scope.append(new_scope)
    parent_array = np.asarray(parents,np.int64)
    q = np.full((len(polys),max(map(len,polys))),-1,np.int64)
    for j,poly in enumerate(polys):
        q[j,:len(poly)] = poly
    out = ArrayMesh(np.asarray(xyz),q,np.asarray(classes,np.int8),np.asarray(rest),
                    mesh.anchors[parent_array].copy(),mesh.generation)
    after = topology(out)
    if len(out.xyz)-len(after['edges'])+len(out.faces) != len(mesh.xyz)-len(t['edges'])+len(mesh.faces):
        raise ValueError('Unexpected sweep Euler change.')
    if len(np.unique(out.faces[out.faces>=0])) != len(out.xyz):
        raise ValueError('Sweep created orphan vertices.')
    meta = dict(mechanism='connected multi-face curved patch sweep', selection=selection.tolist(),
        patch_faces=len(selection), boundary_vertices=len(ring), centre=centre.tolist(), normal=normal.tolist(),
        direction=direction.tolist(), area_radius=radius, actual_heights=heights.tolist(), spec=spec,
        topology_changed=True, genus_changed=False, new_scope=int(new_scope),
        caveat='Designed constructive branches; not emergent branching, no intersection repair.')
    state = dict(parent_face=parent_array,face_scope=np.asarray(out_scope,np.int64),
                 selected_input_faces=selection,boundary_ring=ring,cap_faces=np.asarray(caps,np.int64),
                 final_ring=np.asarray(rings[-1]),input_classes=mesh.classes)
    return out,meta,state


def choose_front_disks(mesh, spec):
    """Geometry-defined disjoint disk scopes; rejected selections remain explicit."""
    from .task32_morphology import carrier_coordinates
    t = topology(mesh); f = fields(mesh,t)
    material = mesh.rest[np.maximum(mesh.faces,0)]
    centres = (material*t['mask'][:,:,None]).sum(1)/t['n'][:,None]
    arc,theta,total,tangents = carrier_coordinates(centres)
    selected = []; rejected = []; used = set()
    for k,fraction in enumerate(spec.get('locations',[.14,.3,.44,.56,.7,.86])):
        # The front-facing actual geometry prevents through-back nearest points.
        score = ((arc-total*fraction)/spec.get('radius_arc',340))**2 + \
                ((theta+np.pi/2)/spec.get('radius_angle',.9))**2
        faces = np.flatnonzero((score<1)&(f['nf'][:,1]<-.35))
        try:
            vertices,ring,_ = disk_boundary(mesh,faces)
            if used.intersection(vertices):
                raise ValueError('Patch scopes touch; no implicit merge.')
            used.update(vertices); selected.append(faces)
        except ValueError as exc:
            rejected.append(dict(location=float(fraction),faces=faces.tolist(),reason=str(exc)))
    return selected,rejected


def branch_patches(mesh, spec, previous=None):
    initial_faces=len(mesh.faces)
    if previous is None:
        scopes=np.zeros(initial_faces,np.int64)
        caps=np.zeros(initial_faces,bool)
        levels=np.full(initial_faces,-1,np.int64)
        groups,rejected=choose_front_disks(mesh,spec)
        groups=[(g,0) for g in groups]
    else:
        scopes=previous['face_scope'].copy(); caps=previous['cap_mask'].copy()
        levels=previous['scope_level'].copy(); groups=[]; rejected=[]
        f=fields(mesh); next_level=int(levels[caps].max())+1 if np.any(caps) else 0
        for scope in np.unique(scopes[caps&(levels==next_level-1)]):
            face_ids=np.flatnonzero(caps&(scopes==scope)&(levels==next_level-1))
            centres=f['c'][face_ids]; centre=centres.mean(0)
            _,_,axes=np.linalg.svd(centres-centre,full_matrices=False)
            direction=axes[0]; coordinates=(centres-centre)@direction
            # Sign chosen in world space, stable across deterministic replays.
            if direction[np.argmax(np.abs(direction))]<0: direction=-direction; coordinates=-coordinates
            extent=float(np.ptp(coordinates)); radius=extent*float(spec.get('child_radius',.24))
            used=set()
            for sign in (-1,1):
                target=centre+sign*extent*float(spec.get('child_offset',.27))*direction
                faces=face_ids[np.linalg.norm(centres-target,axis=1)<radius]
                try:
                    vertices,_,_=disk_boundary(mesh,faces)
                    if len(faces)<2: raise ValueError('Child not a multi-face patch at this resolution.')
                    if used.intersection(vertices): raise ValueError('Child patches touch.')
                    used.update(vertices); groups.append((faces,int(scope)))
                except ValueError as exc:
                    rejected.append(dict(parent_scope=int(scope),side=int(sign),reason=str(exc),faces=faces.tolist()))
    if not groups:
        raise ValueError('No valid connected multi-face patch; rejected: '+str(rejected))
    overall=np.arange(initial_faces); records=[]
    next_id=int(scopes.max())+1
    for original,parent_scope in groups:
        # Original selection indices are mapped through EACH preceding edit.
        current=np.flatnonzero(np.isin(overall,original)&(scopes==parent_scope))
        level=0 if previous is None else int(levels[current].max())+1
        step_spec=dict(spec)
        if parent_scope:
            # Child bends alternate by inherited parent position, not random IDs.
            centre=fields(mesh)['c'][current].mean(0)
            step_spec['direction']=[1 if centre[0] < -400.036865234375 else -1,0,1]
        mesh,meta,state=sweep_disk(mesh,current,step_spec,scopes,next_id)
        parents=state['parent_face']; overall=overall[parents]
        caps=caps[parents]; levels=levels[parents]; scopes=state['face_scope']
        fresh=scopes==next_id; caps[fresh]=False; levels[fresh]=level
        caps[state['cap_faces']]=True
        meta.update(parent_scope=parent_scope,scope_level=level,input_selection=original.tolist())
        records.append(meta); next_id+=1
    return mesh,dict(mechanism='connected multi-face parent/child constructive grammar',
        actual_events=records,rejected_patch_proposals=rejected,topology_changed=True,
        scope='Own geometry-defined disk selection and multi-ring extrusion; not novel subdivision math.'), \
        dict(parent_face=overall,face_scope=scopes,cap_mask=caps,scope_level=levels)
