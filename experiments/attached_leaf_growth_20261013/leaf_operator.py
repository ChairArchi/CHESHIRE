"""Attached multi-face leaf/child sweeps on selected actual G7 disks.

Only small temporary closed shells are passed to the frozen Task32 operator.
Their back/collar faces never enter the output. Original G7 face slots receive
their replacement caps; generated walls are appended. Actual source IDs carry
X/Y reflection, without rebuilding or averaging the rest of the column.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import importlib.util
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh, unit, topology
from cheshire.task32_patches import disk_boundary, sweep_disk

_spec = importlib.util.spec_from_file_location('attached_leaf_existing_patch_geometry',
    HERE.parent/'connected_fold_growth_20261012/patch_growth.py')
growth = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = growth
_spec.loader.exec_module(growth)

RECIPE = dict(
    schema='CHESHIRE_ATTACHED_LOCAL_DISK_LEAVES_V1', source_generation=7, output_generation=7,
    seed_t=[.16, .25, .35, .44, .54, .64, .74, .85],
    seed_theta=[.40, .97, .38, .93, .42, .95, .40, .97],
    address_halfwidth_t=.030, address_halfwidth_theta=.14,
    address_score='(dt/.030)^2+(dtheta/.14)^2+4*((abs(wrapped_face_parent_phase)-1.55)/.65)^2',
    address_scope='One deterministic minimum in each fixed canonical support==0 window; no replacement location search.',
    patch_halfwidth_t=.0125, patch_halfwidth_theta=.045,
    minimum_patch_faces=2, minimum_canonical_roots=6, pca_gap_tolerance=1e-8,
    seam_tolerance=1e-11,
    root_heights=[.12, .28, .48, .70, .91, 1.10, 1.25, 1.35],
    root_scales=[1., 1.10, 1.18, 1.14, 1.02, .86, .72, .60], root_bend=.60,
    child_heights=[.12, .28, .46, .65, .84, 1.],
    child_scales=[1., 1.10, 1.15, 1.03, .82, .60], child_bend=.70,
    child_positions_major=[-.25, .25], child_halfwidth_major=.17, child_halfwidth_minor=.35,
    twist=0., projection_guard=False,
    temporary_shell_back_offset_root_radius=.10,
    added_CC_passes=0, added_mandelbulb_evaluations=0, normal_field_passes=0,
    source_geometry_averaged=False,
    topology_scope='Actual attached Task32 multi-face root plus up to two actual cap-owned child sweeps; G remains 7.',
    symmetry_scope='Existing source X/Y vertex and face IDs; reflect only edited disks and appended geometry, no global quarter reconstruction.',
    preservation_scope='All original source vertex IDs retained. Source controls outside selected disks, their classes/rest/chart, and face slots outside selected faces remain exact.',
    shell_scope='Small closed front/back/collar context satisfies frozen Task32 topology requirements. Only swept front walls/caps survive global splicing.',
    selection_failure='Explicit failed seed/child records; no retuning, alternate positions, or candidate matrix.',
    geometry_limitation='Monotonically increasing Task32 normal heights and scaled/bent rings do not guarantee a hook returning toward the source. No intersection or collision repair.',
    interpretation='One authored constructive leaf/descendant sequence, not emergent fractal growth or established visual success.',
)


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def code_hashes():
    paths = (Path(__file__).resolve(), HERE.parent/'connected_fold_growth_20261012/patch_growth.py',
             REPO/'src/cheshire/task32_patches.py', REPO/'src/cheshire/reference_subdivision.py')
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _pairs(pairs, nv, nf):
    result = {}
    for key, count in (('X', nv), ('Y', nv), ('face_X', nf), ('face_Y', nf)):
        value = np.asarray(pairs[key])
        if (value.shape != (count,) or value.dtype.kind not in 'iu' or
                value.min() < 0 or value.max() >= count or
                not np.array_equal(value[value], np.arange(count))):
            raise ValueError('Actual source involution required: '+key)
        result[key] = value
    for prefix in ('', 'face_'):
        x, y = result[prefix+'X'], result[prefix+'Y']
        if not np.array_equal(x[y], y[x]):
            raise ValueError('Actual source X/Y involutions must commute: '+prefix)
    return result


def _map_ids(ids, pairs, quarter, kind='vertex'):
    value = np.asarray(ids)
    prefix = '' if kind == 'vertex' else 'face_'
    if quarter & 1:
        value = pairs[prefix+'X'][value]
    if quarter & 2:
        value = pairs[prefix+'Y'][value]
    return value


def _face_coordinates(mesh, chart, phase, support, start, stop):
    q = mesh.faces[start:stop]
    c = chart[q].mean(1)
    theta = np.arctan2(c[:, 2], c[:, 1])
    eligible = np.all(chart[q, 1:] > RECIPE['seam_tolerance'], axis=(1, 2))
    eligible &= np.all(support[q] == 0., axis=1)
    p = phase[q]
    wrapped = np.arctan2(np.sin(p).mean(1), np.cos(p).mean(1))
    return c[:, 0], theta, wrapped, eligible


def _select_disks(mesh, chart, phase, support, chunk=131072):
    addresses = [None]*8
    best = np.full(8, np.inf)
    for start in range(0, len(mesh.faces), chunk):
        stop = min(start+chunk, len(mesh.faces))
        t, theta, wrapped, eligible = _face_coordinates(mesh, chart, phase, support, start, stop)
        for index, (target_t, target_theta) in enumerate(zip(RECIPE['seed_t'], RECIPE['seed_theta'])):
            dt, da = t-target_t, theta-target_theta
            inside = eligible & (np.abs(dt) < .030) & (np.abs(da) < .14)
            ids = np.flatnonzero(inside)
            if not len(ids):
                continue
            score = (dt[ids]/.030)**2+(da[ids]/.14)**2+4*((np.abs(wrapped[ids])-1.55)/.65)**2
            slot = int(np.argmin(score))
            if score[slot] < best[index]:
                f = int(ids[slot])
                best[index] = float(score[slot])
                addresses[index] = dict(face_id=start+f, t=float(t[f]), theta=float(theta[f]),
                    parent_phase=float(wrapped[f]), score=best[index])
    selections = [[] for _ in addresses]
    for start in range(0, len(mesh.faces), chunk):
        stop = min(start+chunk, len(mesh.faces))
        t, theta, _, eligible = _face_coordinates(mesh, chart, phase, support, start, stop)
        for index, address in enumerate(addresses):
            if address is None:
                continue
            score = ((t-address['t'])/.0125)**2+((theta-address['theta'])/.045)**2
            ids = np.flatnonzero(eligible & (score < 1.))
            selections[index].append(ids+start)
    return addresses, [np.concatenate(parts) if parts else np.empty(0, np.int64) for parts in selections]


def _front_geometry(xyz, faces):
    points = xyz[faces]
    relative = points-points.mean(1)[:, None]
    crosses = np.cross(relative, np.roll(relative, -1, axis=1))
    # Exact frozen fields() face-normal and quad area recipe; no edge graph.
    normals = unit(crosses.sum(1))
    area = np.linalg.norm(crosses, axis=2).sum(1)/2
    normal = unit(np.sum(normals*area[:, None], axis=0)[None])[0]
    if np.linalg.norm(normal) < .99 or area.sum() <= 0:
        raise ValueError('Selected actual front has cancelling normals or no positive area.')
    return normal, float(np.sqrt(area.sum()/np.pi))


def _closed_local_shell(mesh, chart, selection):
    source_ids, source_ring, _ = disk_boundary(mesh, selection)
    local_faces = np.searchsorted(source_ids, mesh.faces[selection])
    nv, nf = len(source_ids), len(selection)
    front_xyz = mesh.xyz[source_ids]
    normal, radius = _front_geometry(front_xyz, local_faces)
    local_front = ArrayMesh(front_xyz, local_faces, mesh.classes[source_ids], mesh.rest[source_ids],
                            mesh.anchors[selection], 7)
    _, ring, owners = disk_boundary(local_front, np.arange(nf))
    back_xyz = front_xyz-radius*.10*normal
    collar = np.column_stack([np.roll(ring, -1), ring, ring+nv, np.roll(ring, -1)+nv])
    faces = np.concatenate([local_faces, local_faces[:, ::-1]+nv, collar])
    source_parent = np.r_[selection, selection, selection[owners]]
    local = ArrayMesh(np.concatenate([front_xyz, back_xyz]), faces,
        np.r_[mesh.classes[source_ids], mesh.classes[source_ids]],
        np.concatenate([mesh.rest[source_ids], mesh.rest[source_ids]]),
        mesh.anchors[source_parent].copy(), 7)
    local.surface = 'mean'
    topology(local)  # Small context only; never the incoming full G7.
    data = dict(mesh=local, chart=np.concatenate([chart[source_ids], chart[source_ids]]),
        source_ids=source_ids, source_selection=np.asarray(selection), source_ring=source_ring,
        front_count=nv, original_context_count=2*nv,
        vertex_origin=np.r_[source_ids, source_ids], vertex_birth=np.zeros(2*nv, np.int32),
        face_source=source_parent, face_slot=np.r_[selection, np.full(nf+len(ring), -1, np.int64)],
        face_scope=np.zeros(len(faces), np.int32), face_role=np.zeros(len(faces), np.int8),
        face_parent_event=np.zeros(len(faces), np.int32), face_token=np.arange(len(faces)),
        next_token=len(faces), radius=radius)
    return data


def _apply_local(data, selected, spec, event_id, parent_id, level):
    before = data['mesh']
    vertices, ring, _ = disk_boundary(before, selected)
    old_nv = len(before.xyz)
    out, geometry, step = sweep_disk(before, selected, spec, data['face_scope'], event_id)
    parents, caps = step['parent_face'], step['cap_faces']
    fresh = step['face_scope'] == event_id
    origins = np.tile(ring, len(spec['heights']))
    if len(out.xyz) != old_nv+len(origins):
        raise ValueError('Frozen Task32 ring birth ordering differs.')
    updated = dict(data, mesh=out,
        chart=np.concatenate([data['chart'], data['chart'][origins]]),
        vertex_origin=np.r_[data['vertex_origin'], data['vertex_origin'][origins]],
        vertex_birth=np.r_[data['vertex_birth'], np.full(len(origins), event_id, np.int32)],
        face_source=data['face_source'][parents].copy(), face_slot=data['face_slot'][parents].copy(),
        face_role=data['face_role'][parents].copy(), face_scope=step['face_scope'].astype(np.int32),
        face_parent_event=data['face_parent_event'][parents].copy(),
        face_token=data['face_token'][parents].copy())
    updated['face_slot'][fresh] = -1
    updated['face_slot'][caps] = data['face_slot'][parents[caps]]
    updated['face_role'][fresh] = 1
    updated['face_role'][caps] = 2
    updated['face_parent_event'][fresh] = data['face_scope'][parents[fresh]]
    updated['face_token'][fresh] = np.arange(data['next_token'], data['next_token']+int(fresh.sum()))
    updated['next_token'] = data['next_token']+int(fresh.sum())
    updated['vertex_birth'][np.setdiff1d(vertices, ring)] = event_id
    record = dict(event_id=event_id, parent_event_id=parent_id, level=level, status='accepted',
                  actual_patch_faces=len(selected), boundary_vertices=len(ring),
                  geometry=geometry, local_cap_faces=caps.tolist(),
                  original_source_parent_faces=np.unique(data['face_source'][selected]).tolist())
    return updated, caps, record


def _child_plans(data, caps, root_id):
    frame = growth._pca(data['mesh'], caps, RECIPE)
    centres = data['mesh'].xyz[data['mesh'].faces[caps]].mean(1)
    coordinates = (centres-frame['origin'])@np.column_stack([frame['major'], frame['minor']])
    middle = (frame['lower']+frame['upper'])/2
    plans, used = [], set()
    for index, position in enumerate(RECIPE['child_positions_major']):
        target = middle+np.array([position, 0.])*frame['extent']
        radii = frame['extent']*np.array([.17, .35])
        selected = caps[np.sum(((coordinates-target)/radii)**2, axis=1) < 1.]
        plan = dict(index=index, event_id=root_id+index+1, status='rejected')
        try:
            if len(selected) < 2:
                raise ValueError('Insufficient actual multi-face child cap support.')
            vertices, _, _ = disk_boundary(data['mesh'], selected)
            if used.intersection(map(int, vertices)):
                raise ValueError('Frozen child selections share vertices.')
            child_frame = growth._pca(data['mesh'], selected, RECIPE)
            direction = child_frame['major'].copy()
            if np.dot(direction, frame['major']) < 0:
                direction *= -1
            direction *= -1 if position < 0 else 1
            plan.update(status='planned', tokens=data['face_token'][selected].copy(),
                        direction=direction, selected_count=len(selected))
            used.update(map(int, vertices))
        except ValueError as exc:
            plan['reason'] = str(exc)
        plans.append(plan)
    return plans


def _local_leaf(mesh, chart, selected, root_id):
    data = _closed_local_shell(mesh, chart, selected)
    frame = growth._pca(data['mesh'], np.arange(len(selected)), RECIPE)
    root_spec = dict(heights=RECIPE['root_heights'], scales=RECIPE['root_scales'],
                     bend=.60, direction=frame['major'].tolist(), twist=0., projection_guard=False)
    data, caps, record = _apply_local(data, np.arange(len(selected)), root_spec, root_id, 0, 0)
    records = [record]
    try:
        plans = _child_plans(data, caps, root_id)
    except ValueError as exc:
        plans = [dict(index=i, event_id=root_id+i+1, status='rejected', reason=str(exc)) for i in range(2)]
    for plan in plans:
        if plan['status'] == 'rejected':
            records.append(dict(event_id=plan['event_id'], parent_event_id=root_id, level=1,
                                status='rejected', reason=plan['reason']))
            continue
        selected_child = np.flatnonzero(np.isin(data['face_token'], plan['tokens']))
        try:
            if (len(selected_child) != plan['selected_count'] or
                    np.any(data['face_scope'][selected_child] != root_id) or
                    np.any(data['face_role'][selected_child] != 2)):
                raise ValueError('Frozen child tokens escaped their actual root cap.')
            spec = dict(heights=RECIPE['child_heights'], scales=RECIPE['child_scales'],
                        bend=.70, direction=plan['direction'].tolist(), twist=0., projection_guard=False)
            data, _, child = _apply_local(data, selected_child, spec, plan['event_id'], root_id, 1)
            records.append(child)
        except ValueError as exc:
            records.append(dict(event_id=plan['event_id'], parent_event_id=root_id, level=1,
                                status='rejected', reason=str(exc)))
    active = data['face_scope'] > 0
    used = np.unique(data['mesh'].faces[active])
    if np.any((used >= data['front_count']) & (used < data['original_context_count'])):
        raise ValueError('Temporary shell back/collar escaped into global output.')
    slots = data['face_slot'][active]
    caps_at_source = slots[slots >= 0]
    if not np.array_equal(np.sort(caps_at_source), np.sort(selected)):
        raise ValueError('Replacement caps do not bind one-to-one to original source face slots.')
    local_ring = np.searchsorted(data['source_ids'], data['source_ring'])
    if not np.array_equal(data['mesh'].xyz[local_ring], mesh.xyz[data['source_ring']]):
        raise ValueError('Original shared attachment boundary moved.')
    data['records'] = records
    return data


def _exact_outside(source, out, selected_vertices, selected_faces, chunk=131072):
    nv, nf = len(source.xyz), len(source.faces)
    allowed_v = np.zeros(nv, bool); allowed_v[selected_vertices] = True
    allowed_f = np.zeros(nf, bool); allowed_f[selected_faces] = True
    moved = 0
    for start in range(0, nv, chunk):
        stop = min(start+chunk, nv)
        outside = ~allowed_v[start:stop]
        if (not np.array_equal(out.xyz[start:stop][outside], source.xyz[start:stop][outside]) or
                not np.array_equal(out.classes[start:stop][outside], source.classes[start:stop][outside])):
            raise ValueError('Source controls outside selected disks changed.')
        if not np.array_equal(out.rest[start:stop], source.rest[start:stop]):
            raise ValueError('Original source rest association changed.')
        moved += int(np.count_nonzero(np.any(out.xyz[start:stop] != source.xyz[start:stop], axis=1)))
    for start in range(0, nf, chunk):
        stop = min(start+chunk, nf)
        outside = ~allowed_f[start:stop]
        if not np.array_equal(out.faces[start:stop][outside], source.faces[start:stop][outside]):
            raise ValueError('Source face slots outside selected disks changed.')
        if not np.array_equal(out.anchors[start:stop], source.anchors[start:stop]):
            raise ValueError('Original source anchor association changed.')
    return dict(source_outside_selected_controls_exact=True, source_outside_selected_face_slots_exact=True,
                source_rest_prefix_exact=True, source_anchor_prefix_exact=True,
                moved_original_control_count=moved, selected_original_control_count=len(selected_vertices),
                retained_original_vertex_ids=True, retained_original_face_slots=True)


def build(mesh, chart, pairs, phase, z, support, height):
    """Return (G7 output mesh, chart, metadata, array evidence), no file writes."""
    nv, nf = len(mesh.xyz), len(mesh.faces)
    if (mesh.generation != 7 or getattr(mesh, 'surface', None) != 'mean' or
            mesh.xyz.shape != (nv, 3) or mesh.faces.shape != (nf, 4) or
            np.asarray(chart).shape != (nv, 3) or not np.isfinite(mesh.xyz).all()):
        raise ValueError('Actual saved mean-native all-quad G7 source and chart required.')
    for value, name in ((phase, 'phase'), (z, 'z'), (support, 'support')):
        if np.asarray(value).shape != (nv,) or not np.isfinite(value).all():
            raise ValueError('Finite actual inherited vertex coordinate required: '+name)
    if np.any(np.asarray(support) < 0) or np.any(np.asarray(support) > 1):
        raise ValueError('Inherited support outside [0,1].')
    height = float(height)
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive inherited full-column height required.')
    pairs = _pairs(pairs, nv, nf)
    addresses, selections = _select_disks(mesh, np.asarray(chart), np.asarray(phase), np.asarray(support))
    leaves, records, used = [], [], set()
    for index, (address, selected) in enumerate(zip(addresses, selections)):
        root_id = 3*index+1
        try:
            if address is None or len(selected) < 2:
                raise ValueError('Fixed source address/window has insufficient actual faces.')
            vertices, _, _ = disk_boundary(mesh, selected)
            reflected_vertices = [_map_ids(vertices, pairs, q) for q in range(4)]
            reflected_faces = [_map_ids(selected, pairs, q, 'face') for q in range(4)]
            union_v = np.concatenate(reflected_vertices)
            if len(np.unique(union_v)) != len(union_v) or used.intersection(map(int, union_v)):
                raise ValueError('Source disks touch a mirror seam or an earlier selected disk.')
            if len(np.unique(np.concatenate(reflected_faces))) != 4*len(selected):
                raise ValueError('Mirrored source face selections overlap.')
            data = _local_leaf(mesh, np.asarray(chart), selected, root_id)
            data.update(seed_index=index, address=address, reflected_vertices=reflected_vertices,
                        reflected_faces=reflected_faces)
            leaves.append(data)
            used.update(map(int, union_v))
            for event in data['records']:
                event.update(seed_index=index, address=address)
            records.extend(data['records'])
        except ValueError as exc:
            records.append(dict(event_id=root_id, parent_event_id=0, level=0, seed_index=index,
                                address=address, status='rejected', reason=str(exc)))
    if len(leaves) < 6:
        failure = ValueError('Fewer than six unchanged fixed root windows were accepted; no retuning.')
        failure.events = records
        raise failure

    xyz_prefix, class_prefix = mesh.xyz.copy(), mesh.classes.copy()
    faces_prefix = mesh.faces.copy()
    source_face_event = np.zeros(nf, np.int32)
    source_face_role = np.zeros(nf, np.int8)
    source_face_parent_event = np.zeros(nf, np.int32)
    vertex_birth_prefix = np.zeros(nv, np.int32)
    additions = {key: [] for key in ('xyz', 'classes', 'rest', 'chart', 'faces', 'anchors',
        'vertex_origin', 'vertex_birth', 'face_source', 'face_event', 'face_role', 'face_parent_event',
        'pair_x_v', 'pair_y_v', 'pair_x_f', 'pair_y_f')}
    source_selected_v, source_selected_f = [], []
    next_vertex, next_face = nv, nf
    evidence = {}
    for data in leaves:
        local = data['mesh']
        active_faces = np.flatnonzero(data['face_scope'] > 0)
        cap_faces = active_faces[data['face_slot'][active_faces] >= 0]
        extra_faces = active_faces[data['face_slot'][active_faces] < 0]
        new_vertices = np.unique(local.faces[active_faces])
        new_vertices = new_vertices[new_vertices >= data['original_context_count']]
        nnew, nextra = len(new_vertices), len(extra_faces)
        vertex_start, face_start = next_vertex, next_face
        for quarter in range(4):
            signs = np.array([-1 if quarter & 1 else 1, -1 if quarter & 2 else 1, 1])
            source_ids = data['reflected_vertices'][quarter]
            source_faces = data['reflected_faces'][quarter]
            source_selected_v.append(source_ids); source_selected_f.append(source_faces)
            canonical_delta = local.xyz[:data['front_count']]-mesh.xyz[data['source_ids']]
            xyz_prefix[source_ids] = mesh.xyz[source_ids]+canonical_delta*signs
            class_prefix[source_ids] = local.classes[:data['front_count']]
            vertex_birth_prefix[source_ids] = data['vertex_birth'][:data['front_count']]
            local_to_global = np.full(len(local.xyz), -1, np.int64)
            local_to_global[:data['front_count']] = source_ids
            local_to_global[new_vertices] = np.arange(next_vertex, next_vertex+nnew)
            mapped_caps = local_to_global[local.faces[cap_faces]]
            mapped_extra = local_to_global[local.faces[extra_faces]]
            if quarter in (1, 2):
                mapped_caps = mapped_caps[:, ::-1]
                mapped_extra = mapped_extra[:, ::-1]
            slots = _map_ids(data['face_slot'][cap_faces], pairs, quarter, 'face')
            faces_prefix[slots] = mapped_caps
            source_face_event[slots] = data['face_scope'][cap_faces]
            source_face_role[slots] = data['face_role'][cap_faces]
            source_face_parent_event[slots] = data['face_parent_event'][cap_faces]
            additions['xyz'].append(local.xyz[new_vertices]*signs)
            additions['classes'].append(local.classes[new_vertices])
            original_vertices = _map_ids(data['vertex_origin'][new_vertices], pairs, quarter)
            additions['rest'].append(mesh.rest[original_vertices])
            additions['chart'].append(np.asarray(chart)[original_vertices])
            additions['faces'].append(mapped_extra)
            parents = _map_ids(data['face_source'][extra_faces], pairs, quarter, 'face')
            additions['anchors'].append(mesh.anchors[parents])
            additions['vertex_origin'].append(original_vertices)
            additions['vertex_birth'].append(data['vertex_birth'][new_vertices])
            additions['face_source'].append(parents)
            for key in ('face_event', 'face_role', 'face_parent_event'):
                source_key = {'face_event': 'face_scope', 'face_role': 'face_role',
                              'face_parent_event': 'face_parent_event'}[key]
                additions[key].append(data[source_key][extra_faces])
            additions['pair_x_v'].append(vertex_start+(quarter ^ 1)*nnew+np.arange(nnew))
            additions['pair_y_v'].append(vertex_start+(quarter ^ 2)*nnew+np.arange(nnew))
            additions['pair_x_f'].append(face_start+(quarter ^ 1)*nextra+np.arange(nextra))
            additions['pair_y_f'].append(face_start+(quarter ^ 2)*nextra+np.arange(nextra))
            next_vertex += nnew; next_face += nextra
        prefix = f'seed_{data["seed_index"]:02d}_'
        evidence[prefix+'source_faces'] = data['source_selection']
        evidence[prefix+'source_boundary_vertices'] = data['source_ring']
        evidence[prefix+'canonical_new_vertex_ids'] = np.arange(vertex_start, vertex_start+nnew)
        evidence[prefix+'canonical_appended_face_ids'] = np.arange(face_start, face_start+nextra)

    cat = lambda key: np.concatenate(additions[key])
    out = ArrayMesh(np.concatenate([xyz_prefix, cat('xyz')]),
        np.concatenate([faces_prefix, cat('faces')]), np.r_[class_prefix, cat('classes')],
        np.concatenate([mesh.rest, cat('rest')]), np.concatenate([mesh.anchors, cat('anchors')]), 7)
    out.surface = 'mean'
    outchart = np.concatenate([chart, cat('chart')])
    selected_vertices = np.unique(np.concatenate(source_selected_v))
    selected_faces = np.unique(np.concatenate(source_selected_f))
    preservation = _exact_outside(mesh, out, selected_vertices, selected_faces)
    if not np.array_equal(outchart[:nv], chart):
        raise ValueError('Original source chart prefix changed.')
    state = dict(evidence, mirror_x_vertex_pairs=np.r_[pairs['X'], cat('pair_x_v')],
        mirror_y_vertex_pairs=np.r_[pairs['Y'], cat('pair_y_v')],
        mirror_x_face_pairs=np.r_[pairs['face_X'], cat('pair_x_f')],
        mirror_y_face_pairs=np.r_[pairs['face_Y'], cat('pair_y_f')],
        selected_source_vertex_ids=selected_vertices, selected_source_face_ids=selected_faces,
        vertex_parent_source_ids=np.r_[np.arange(nv), cat('vertex_origin')],
        vertex_birth_event_ids=np.r_[vertex_birth_prefix, cat('vertex_birth')],
        face_parent_source_ids=np.r_[np.arange(nf), cat('face_source')],
        face_event_ids=np.r_[source_face_event, cat('face_event')],
        face_roles=np.r_[source_face_role, cat('face_role')],
        face_parent_event_ids=np.r_[source_face_parent_event, cat('face_parent_event')])
    accepted_roots = len(leaves)
    accepted_children = sum(event['status'] == 'accepted' and event['level'] == 1 for event in records)
    accepted = accepted_roots+accepted_children
    metadata = dict(experiment='ATTACHED_LEAF_GROWTH_20261013', recipe=deepcopy(RECIPE),
        source_generation=7, output_generation=7, added_CC_passes=0,
        added_mandelbulb_evaluations=0, normal_field_passes=0, source_geometry_averaged=False,
        added_topology_events=4*accepted, accepted_canonical_root_events=accepted_roots,
        accepted_canonical_child_events=accepted_children, accepted_canonical_events=accepted,
        reflected_root_events=4*accepted_roots, reflected_child_events=4*accepted_children,
        rejected_canonical_roots=8-accepted_roots,
        rejected_canonical_children=sum(event['status'] == 'rejected' and event['level'] == 1 for event in records),
        topology_event_count_scope='Actual reflected instances; canonical accepted events recorded separately.',
        events=records, input_xyz_sha256=_hash(mesh.xyz), output_xyz_sha256=_hash(out.xyz),
        source_control_count=nv, source_face_count=nf, added_control_count=len(out.xyz)-nv,
        added_quad_count=len(out.faces)-nf, source_chart_prefix_exact=True,
        global_topology_built_by_operator=False, local_closed_shells_only=True,
        temporary_shell_geometry_discarded=True, mean_native_surface_preserved=True,
        inherited_height=height, source_outside_control_exact=True,
        preservation=preservation, geometry_code_sha256=code_hashes(),
        source_pair_hashes={key: _hash(value) for key, value in pairs.items()},
        face_event_scope='New operator events only; zero means preexisting source G7, not absent historical ancestry.',
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED',
        interpretation=RECIPE['interpretation'], visual_status='PENDING_MATCHED_RENDER')
    return out, outchart, metadata, state
