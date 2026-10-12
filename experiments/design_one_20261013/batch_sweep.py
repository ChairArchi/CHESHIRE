"""Batch adapter of Task32's connected disk sweep, without another CC pass.

Only selected patches are measured. Each authored canonical patch is reflected
through actual saved identity maps; the dense untouched parent is copied once.
Intersections are permitted. This is the existing constructive sweep formula,
not a new subdivision or emergent branching algorithm.
"""
import numpy as np

from cheshire.reference_subdivision import ArrayMesh, unit
from cheshire.task32_patches import disk_boundary, projected_disk_admission


def _mapped(ids, reflection, pairs):
    result = np.asarray(ids, np.int64)
    for bit, axis in ((1, 'X'), (2, 'Y')):
        if reflection & bit:
            result = np.asarray(pairs[axis])[result]
    return result


def _measure(mesh, selection, spec):
    vertices, ring, owners = disk_boundary(mesh, selection)
    p = mesh.xyz[mesh.faces[selection]]
    c = p.mean(axis=1)
    cross = np.cross(p-c[:, None], np.roll(p, -1, axis=1)-c[:, None])
    area = np.linalg.norm(cross, axis=2).sum(axis=1)/2.
    normal = unit((unit(cross.sum(axis=1))*area[:, None]).sum(axis=0)[None])[0]
    if np.linalg.norm(normal) < .5:
        raise ValueError('Patch has cancelling normals.')
    centre = mesh.xyz[vertices].mean(axis=0)
    direction = np.asarray(spec.get('direction', [0., 0., 1.]), float).copy()
    direction -= normal*np.dot(normal, direction)
    direction = unit(direction[None])[0]
    if np.linalg.norm(direction) < .5:
        direction = unit((mesh.xyz[ring[1]]-mesh.xyz[ring[0]])[None])[0]
    side = np.cross(normal, direction)
    radius = float(np.sqrt(area.sum()/np.pi))
    heights = np.asarray(spec.get('heights', [.2, .6, 1.]), float)*radius
    scales = np.asarray(spec.get('scales', [.7, .65, .45]), float)
    if (len(heights) != len(scales) or not len(scales) or np.any(scales <= 0.) or
            np.any(heights <= 0.) or np.any(np.diff(heights) <= 0.) or
            not np.isfinite(heights).all() or not np.isfinite(scales).all()):
        raise ValueError('Increasing finite heights and positive matching scales required.')
    admission = projected_disk_admission(mesh, selection, ring) if spec.get('projection_guard') else None
    relative = mesh.xyz[vertices]-centre
    u, v, n = relative@direction, relative@side, relative@normal
    levels = []
    for height, scale in zip(heights, scales):
        angle = float(spec.get('twist', 0.))*height/max(heights[-1], 1e-9)
        rotated = ((u*np.cos(angle)-v*np.sin(angle))[:, None]*direction +
                   (u*np.sin(angle)+v*np.cos(angle))[:, None]*side + n[:, None]*normal)
        shift = float(spec.get('bend', .3))*height**2/max(heights[-1], 1e-9)*direction
        levels.append(centre+scale*rotated+height*normal+shift)
    return vertices, ring, owners, np.asarray(levels), dict(
        centre=centre.tolist(), normal=normal.tolist(), direction=direction.tolist(),
        side=side.tolist(), area_radius=radius, actual_area=float(area.sum()),
        actual_heights=heights.tolist(), scales=scales.tolist(),
        projection_admission=admission, spec=dict(spec))


def batch_sweep(mesh, chart, canonical_plans, vertex_pairs, face_pairs, event_start=1):
    """Return ``out, outchart, metadata, state`` with the parent's actual G.

    Reflected patches must be vertex-disjoint and avoid reflection seams. Event
    IDs identify canonical authored groups, each comprising four exact copies.
    Kept faces have event/role 0, new walls role 1 and moved caps role 2.
    """
    chart = np.asarray(chart)
    nv, nf = len(mesh.xyz), len(mesh.faces)
    if mesh.faces.ndim != 2 or mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0):
        raise ValueError('All-quad parent required.')
    if chart.shape != mesh.xyz.shape or not np.isfinite(chart).all():
        raise ValueError('Aligned finite parent chart required.')
    for pairs, size in ((vertex_pairs, nv), (face_pairs, nf)):
        for axis in ('X', 'Y'):
            pair = np.asarray(pairs[axis])
            if (pair.shape != (size,) or pair.dtype.kind not in 'iu' or
                    pair.min() < 0 or pair.max() >= size or
                    not np.array_equal(pair[pair], np.arange(size))):
                raise ValueError('Actual identity involutions required.')
        if not np.array_equal(pairs['X'][pairs['Y']], pairs['Y'][pairs['X']]):
            raise ValueError('Reflection involutions must commute.')
    prepared, used = [], set()
    keep = np.ones(nf, bool)
    for index, plan in enumerate(canonical_plans):
        selection = np.asarray(plan['selection'], np.int64)
        vertices, ring, owners, levels, geometry = _measure(mesh, selection, plan['spec'])
        copies = []
        for reflection in range(4):
            v = _mapped(vertices, reflection, vertex_pairs)
            if used.intersection(map(int, v)):
                raise ValueError('Patches touch one another or a reflection seam.')
            used.update(map(int, v))
            s = _mapped(selection, reflection, face_pairs)
            mapped_faces = _mapped(mesh.faces[selection], reflection, vertex_pairs)
            if reflection in (1, 2):
                mapped_faces = mapped_faces[:, ::-1]
            actual = mesh.faces[s]
            cyclic = np.any(np.all(actual[:, None, :] == np.stack(
                [np.roll(mapped_faces, shift, axis=1) for shift in range(4)], axis=1), axis=2), axis=1)
            if not cyclic.all():
                raise ValueError('Actual reflected oriented patch faces differ.')
            keep[s] = False
            copies.append((v, s, _mapped(ring, reflection, vertex_pairs),
                           _mapped(owners, reflection, face_pairs)))
        prepared.append((index, plan, vertices, ring, levels, geometry, copies))
    if not prepared:
        raise ValueError('At least one authored patch required.')
    xyz, classes = mesh.xyz.copy(), mesh.classes.copy()
    kept = np.flatnonzero(keep)
    kept_map = np.full(nf, -1, np.int64); kept_map[kept] = np.arange(len(kept))
    face_parts, parents, roles, events = [mesh.faces[kept]], [kept], [np.zeros(len(kept), np.int8)], [np.zeros(len(kept), np.int64)]
    xyz_parts, rest_parts, chart_parts = [xyz], [mesh.rest], [chart]
    class_parts = [classes]
    vp = {axis: [np.asarray(vertex_pairs[axis])] for axis in ('X', 'Y')}
    fp = {axis: [kept_map[np.asarray(face_pairs[axis])[kept]]] for axis in ('X', 'Y')}
    records = []; vertex_cursor, face_cursor = nv, len(kept)
    for index, plan, vertices, ring, levels, geometry, copies in prepared:
        event_id = int(event_start)+index
        nl, nb = len(levels), len(ring)
        ring_local = np.searchsorted(vertices, ring)
        interior_local = np.flatnonzero(~np.isin(vertices, ring))
        ring_ids = np.arange(vertex_cursor, vertex_cursor+4*nl*nb).reshape(4, nl, nb)
        vertex_cursor += ring_ids.size
        per_copy_faces = nl*nb+len(plan['selection'])
        face_ids = np.arange(face_cursor, face_cursor+4*per_copy_faces).reshape(4, per_copy_faces)
        face_cursor += face_ids.size
        caps = []
        for reflection, (v, selected, reflected_ring, owners) in enumerate(copies):
            signs = np.array([-1. if reflection & 1 else 1., -1. if reflection & 2 else 1., 1.])
            xyz[v[interior_local]] = levels[-1, interior_local]*signs
            classes[v[interior_local]] = -1
            xyz_parts.append((levels[:, ring_local]*signs).reshape(-1, 3))
            rest_parts.append(np.tile(mesh.rest[reflected_ring], (nl, 1)))
            chart_parts.append(np.tile(chart[reflected_ring], (nl, 1)))
            class_parts.append(np.full(nl*nb, -1, mesh.classes.dtype))
            previous = np.concatenate([reflected_ring[None], ring_ids[reflection, :-1]], axis=0)
            current = ring_ids[reflection]
            walls = np.stack([previous, np.roll(previous, -1, axis=1),
                              np.roll(current, -1, axis=1), current], axis=2).reshape(-1, 4)
            if reflection in (1, 2):
                walls = walls[:, ::-1]
            cap = mesh.faces[selected].copy()
            # Only boundary vertices acquire new IDs; interior cap IDs are reused.
            order = np.argsort(reflected_ring)
            ordered_ring = reflected_ring[order]
            pos = np.searchsorted(ordered_ring, cap)
            match = (pos < nb) & (ordered_ring[np.minimum(pos, nb-1)] == cap)
            cap[match] = current[-1, order[np.minimum(pos[match], nb-1)]]
            face_parts.append(np.concatenate([walls, cap]))
            parents.append(np.r_[np.tile(owners, nl), selected])
            roles.append(np.r_[np.ones(nl*nb, np.int8), np.full(len(cap), 2, np.int8)])
            events.append(np.full(per_copy_faces, event_id, np.int64))
            caps.append(face_ids[reflection, nl*nb:])
        for bit, axis in ((1, 'X'), (2, 'Y')):
            vp[axis].append(ring_ids[np.arange(4)^bit].ravel())
            fp[axis].append(face_ids[np.arange(4)^bit].ravel())
        records.append(dict(event_id=event_id, name=str(plan.get('name', 'patch_'+str(index))),
            canonical_selection=np.asarray(plan['selection']).tolist(),
            canonical_cap_faces=caps[0].tolist(), cap_faces_by_reflection=[c.tolist() for c in caps],
            patch_faces=len(plan['selection']), boundary_vertices=nb,
            reflected_instances=4, geometry=geometry))
    parent_face = np.concatenate(parents)
    out = ArrayMesh(np.concatenate(xyz_parts), np.concatenate(face_parts),
        np.concatenate(class_parts), np.concatenate(rest_parts), mesh.anchors[parent_face].copy(), mesh.generation)
    out.surface = getattr(mesh, 'surface', 'mean')
    state = dict(parent_face=parent_face, face_event_ids=np.concatenate(events),
        face_roles=np.concatenate(roles))
    for axis, label in (('X', 'x'), ('Y', 'y')):
        state['mirror_'+label+'_vertex_pairs'] = np.concatenate(vp[axis])
        state['mirror_'+label+'_face_pairs'] = np.concatenate(fp[axis])
    metadata = dict(mechanism='Task32 connected disk sweep batch adapter', events=records,
        source_generation=int(mesh.generation), output_generation=int(out.generation),
        added_CC_passes=0, added_topology_events=len(records), reflected_instances=4*len(records),
        collision_scope='Intersections allowed; no collision repair.',
        formula_scope='Task32 sweep_disk positions and cap/interior reuse; exact identity reflection.')
    return out, np.concatenate(chart_parts), metadata, state
