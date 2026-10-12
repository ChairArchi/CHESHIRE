"""Connected multi-face roots and cap-owned descendants on actual WALL G03.

Task32 sweep_disk supplies every topology event. The shared root is selected by
an authored material search ellipse; descendants use only the actual generated
cap's PCA/extent. A canonical quarter is reflected using vertex identity at the
material seams, without coordinate welding. Constructive events do not increase
the subdivision generation, and the new native surface explicitly uses mean
quad fans. This is an authored prototype, not an emergent fractal grammar.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh, topology, fields, unit
from cheshire.task32_patches import disk_boundary, sweep_disk

MODES = ('ROOT_ONLY', 'BRANCHED')
RECIPE = dict(source_generation=3, output_generation=3,
    root_parameter_centre=.785, root_parameter_halfwidth=.075,
    root_cross_centre=1.27, root_cross_sweep=.06, root_cross_halfwidth=.23,
    root_heights=[.30, .80, 1.15], root_scales=[.90, .82, .70], root_bend=.20,
    child_positions_major=[-.30, 0., .30], child_positions_minor=[-.035, .035, -.035],
    child_halfwidth_major=.115, child_halfwidth_minor=.22,
    child_heights=[.30, .75, 1.10], child_scales=[.90, .78, .62], child_bend=.24,
    grandchild_positions_major=[-.24, .24], grandchild_positions_minor=[-.035, .035],
    grandchild_halfwidth_major=.16, grandchild_halfwidth_minor=.25,
    grandchild_heights=[.25, .65, 1.00], grandchild_scales=[.90, .78, .60], grandchild_bend=.18,
    minimum_patch_faces=2, seam_tolerance=1e-11, source_symmetry_tolerance=3e-10,
    pca_gap_tolerance=1e-8, twist=0., projection_guard=False,
    scope='One authored fixed upper-shoulder search window per canonical quarter, followed by actual-cap geometry selection',
    generation_scope='G03 remains 3; constructive topology events are counted separately from subdivision',
    lineage_scope='Original classes/rest/anchors remain canonical source associations; new or moved-interior births have class -1; event parentage is separate',
    surface_scope='All output quads use new mean-native fan convention, including retained quads; source VF native geometry is not claimed unchanged',
    symmetry_scope='Canonical-quarter ancestry reflected by vertex identity; material seam axis is exactly zero',
    collision_scope='Intersections are permitted; no projection/contact repair or collision certificate')


def array_hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _canonical_polygons(faces):
    faces = np.asarray(faces)
    first = np.argmin(faces, axis=1)
    rolled = np.take_along_axis(faces,
        (first[:, None]+np.arange(faces.shape[1])[None]) % faces.shape[1], axis=1)
    return rolled[np.lexsort(tuple(rolled[:, k] for k in range(faces.shape[1]-1, -1, -1)))]


def _input_checks(mesh, chart, recipe):
    if int(mesh.generation) != recipe['source_generation']:
        raise ValueError('Actual WALL G03 input generation required.')
    if mesh.faces.ndim != 2 or mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0):
        raise ValueError('Closed all-quad source required; no repair or triangulation.')
    if chart.shape != mesh.xyz.shape or not np.isfinite(chart).all() or not np.isfinite(mesh.xyz).all():
        raise ValueError('Finite control-aligned XYZ/material chart required.')
    t = topology(mesh)
    if len(np.unique(mesh.faces)) != len(mesh.xyz):
        raise ValueError('Source has orphan vertices.')
    if len(mesh.xyz)-len(t['edges'])+len(mesh.faces) != 2:
        raise ValueError('Source must have Euler 2.')
    tol = recipe['seam_tolerance']
    corners = chart[mesh.faces, 1:]
    if np.any((corners.min(axis=1) < -tol) & (corners.max(axis=1) > tol)):
        raise ValueError('Source face crosses a material symmetry seam; no clipping fallback.')
    tree = cKDTree(chart)
    original = _canonical_polygons(mesh.faces)
    errors = []
    for axis in (0, 1):
        signs = np.ones(3); signs[axis+1] = -1.
        distance, pairs = tree.query(chart*signs)
        if distance.max() > tol or not np.array_equal(pairs[pairs], np.arange(len(chart))):
            raise ValueError('Source material reflection has no unique involution.')
        xyzsign = np.ones(3); xyzsign[axis] = -1.
        error = float(np.linalg.norm(mesh.xyz-mesh.xyz[pairs]*xyzsign, axis=1).max())
        if error > recipe['source_symmetry_tolerance']:
            raise ValueError('Source actual XYZ lacks required symmetry; no averaging repair.')
        if not np.array_equal(original, _canonical_polygons(pairs[mesh.faces[:, ::-1]])):
            raise ValueError('Source reflected oriented polygons do not correspond.')
        errors.append(error)
    return errors


def _pca(mesh, selected, recipe):
    """Actual area-weighted cap normal and projected vertex PCA, no world frame."""
    selected = np.asarray(selected, np.int64)
    f = fields(mesh)
    normal = unit(np.sum(f['nf'][selected]*f['area'][selected, None], axis=0)[None])[0]
    if np.linalg.norm(normal) < .99:
        raise ValueError('Actual cap normals cancel; no synthetic frame.')
    vertices = np.unique(mesh.faces[selected])
    points = mesh.xyz[vertices]
    origin = points.mean(axis=0)
    relative = points-origin
    projected = relative-relative@normal[:, None]*normal[None]
    covariance = projected.T@projected/len(projected)
    values, vectors = np.linalg.eigh(covariance)
    major = vectors[:, -1]
    scale = max(float(values[-1]), 1e-30)
    if values[-2] <= 1e-20 or (values[-1]-values[-2])/scale <= recipe['pca_gap_tolerance']:
        raise ValueError('Actual cap has degenerate/tied PCA axes; no ID-based fallback.')
    major -= normal*np.dot(major, normal)
    major = unit(major[None])[0]
    if major[np.argmax(np.abs(major))] < 0.:
        major *= -1.
    minor = np.cross(normal, major)
    xy = relative@np.column_stack([major, minor])
    lower, upper = xy.min(axis=0), xy.max(axis=0)
    extent = upper-lower
    if np.any(extent <= 1e-10):
        raise ValueError('Actual cap PCA extent vanishes.')
    return dict(origin=origin, normal=normal, major=major, minor=minor,
        lower=lower, upper=upper, extent=extent, eigenvalues=values,
        area=float(f['area'][selected].sum()), vertices=vertices)


def _root_selection(mesh, chart, recipe):
    centre = chart[mesh.faces].mean(axis=1)
    theta = np.arctan2(centre[:, 2], centre[:, 1])
    q = (centre[:, 0]-recipe['root_parameter_centre'])/recipe['root_parameter_halfwidth']
    u = (theta-(recipe['root_cross_centre']+recipe['root_cross_sweep']*np.sin(np.pi*q)))/recipe['root_cross_halfwidth']
    canonical = np.all(chart[mesh.faces, 1:] > recipe['seam_tolerance'], axis=(1, 2))
    selected = np.flatnonzero(canonical & (q*q+u*u < 1.))
    if len(selected) < recipe['minimum_patch_faces']:
        raise ValueError('Root authored search ellipse has insufficient actual faces.')
    disk_boundary(mesh, selected)
    return selected


def _plans(mesh, cap_faces, level, parent_id, face_tokens, recipe):
    """Freeze geometry-based sibling proposals before any sibling topology edit."""
    frame = _pca(mesh, cap_faces, recipe)
    centres = fields(mesh)['c'][cap_faces]
    xy = (centres-frame['origin'])@np.column_stack([frame['major'], frame['minor']])
    middle = (frame['lower']+frame['upper'])/2.
    prefix = 'child' if level == 1 else 'grandchild'
    major_positions, minor_positions = recipe[prefix+'_positions_major'], recipe[prefix+'_positions_minor']
    plans, used = [], set()
    for index, (major, minor) in enumerate(zip(major_positions, minor_positions)):
        target = middle+np.array([major, minor])*frame['extent']
        radii = frame['extent']*np.array([recipe[prefix+'_halfwidth_major'], recipe[prefix+'_halfwidth_minor']])
        score = np.sum(((xy-target)/radii)**2, axis=1)
        selected = np.asarray(cap_faces)[score < 1.]
        record = dict(level=level, parent_event_id=parent_id, sibling_index=index,
            planned_input_faces=selected.tolist(), selected_tokens=face_tokens[selected].tolist(),
            pca_origin=frame['origin'].tolist(), pca_major=frame['major'].tolist(),
            pca_minor=frame['minor'].tolist(), pca_normal=frame['normal'].tolist(),
            pca_extent=frame['extent'].tolist(), ellipse_target=target.tolist(),
            ellipse_radii=radii.tolist(), selection_rule='Actual generated parent-cap face centres in its actual PCA extent ellipse')
        try:
            if len(selected) < recipe['minimum_patch_faces']:
                raise ValueError('Insufficient actual multi-face child support.')
            vertices, _, _ = disk_boundary(mesh, selected)
            if used.intersection(map(int, vertices)):
                raise ValueError('Sibling proposals share vertices; no implicit merge or retuning.')
            local = _pca(mesh, selected, recipe)
            direction = local['major']
            # Outward sibling bends use cap axes, not source IDs or world axes.
            if major < 0.:
                direction = -direction
            record.update(direction=direction.tolist(), proposal_status='accepted')
            used.update(map(int, vertices))
        except ValueError as exc:
            record.update(proposal_status='rejected', reason=str(exc))
        plans.append(record)
    return plans


def _quarter_mirror(mesh, chart, arrays, recipe):
    """Reflect complete canonical faces and share only their exact seam IDs."""
    tol = recipe['seam_tolerance']
    keep = np.all(chart[mesh.faces, 1:] >= -tol, axis=(1, 2))
    source_faces = np.flatnonzero(keep)
    canonical = mesh.faces[keep]
    vertices = np.unique(canonical)
    if not len(source_faces):
        raise ValueError('Empty canonical quarter.')
    if np.any(np.all(np.abs(chart[canonical, 1]) <= tol, axis=1)) or np.any(
            np.all(np.abs(chart[canonical, 2]) <= tol, axis=1)):
        raise ValueError('A whole face lies on a material seam; no duplicate-face fallback.')
    mapping, xyz, out_chart, rest, classes = {}, [], [], [], []
    source_vertices, signs, birth, origin = [], [], [], []
    out_faces, source_face, face_signs, anchors = [], [], [], []
    face_lookup = {}
    seam_projection = 0.
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        local = {}
        for v in vertices:
            key = (int(v), 1 if abs(chart[v, 1]) <= tol else sx,
                   1 if abs(chart[v, 2]) <= tol else sy)
            if key not in mapping:
                mapping[key] = len(xyz)
                point = mesh.xyz[v].copy()*np.array([sx, sy, 1.])
                material = chart[v].copy()*np.array([1., sx, sy])
                association = mesh.rest[v].copy()*np.array([sx, sy, 1.])
                for axis in (0, 1):
                    if abs(chart[v, axis+1]) <= tol:
                        seam_projection = max(seam_projection, abs(float(point[axis])))
                        point[axis] = 0.; material[axis+1] = 0.; association[axis] = 0.
                xyz.append(point); out_chart.append(material); rest.append(association)
                classes.append(mesh.classes[v]); source_vertices.append(int(v)); signs.append([key[1], key[2]])
                birth.append(arrays['vertex_birth'][v]); origin.append(arrays['vertex_origin'][v])
            local[int(v)] = mapping[key]
        for f, polygon in zip(source_faces, canonical):
            output = [local[int(v)] for v in polygon]
            if sx*sy < 0:
                output = output[::-1]
            face_lookup[(int(f), sx, sy)] = len(out_faces)
            out_faces.append(output); source_face.append(int(f)); face_signs.append([sx, sy])
            anchors.append(mesh.anchors[f])
    source_vertices, signs = np.asarray(source_vertices), np.asarray(signs, np.int8)
    source_face, face_signs = np.asarray(source_face), np.asarray(face_signs, np.int8)
    vertex_pairs, face_pairs = [], []
    for axis in (0, 1):
        pair = np.empty(len(xyz), np.int64)
        for i, (v, ss) in enumerate(zip(source_vertices, signs)):
            reflected = ss.copy()
            if abs(chart[v, axis+1]) > tol:
                reflected[axis] *= -1
            pair[i] = mapping[(int(v), int(reflected[0]), int(reflected[1]))]
        vertex_pairs.append(pair)
        face_pairs.append(np.array([face_lookup[(int(f), int(-ss[0] if axis == 0 else ss[0]),
            int(-ss[1] if axis == 1 else ss[1]))] for f, ss in zip(source_face, face_signs)], np.int64))
    out = ArrayMesh(np.asarray(xyz), np.asarray(out_faces, np.int64), np.asarray(classes, np.int8),
        np.asarray(rest), np.asarray(anchors, np.int64), int(mesh.generation))
    out.surface = 'mean'
    evidence = dict(mirror_source_vertex_ids=source_vertices, mirror_signs=signs,
        mirror_source_face_ids=source_face, mirror_face_signs=face_signs,
        mirror_x_vertex_pairs=vertex_pairs[0], mirror_y_vertex_pairs=vertex_pairs[1],
        mirror_x_face_pairs=face_pairs[0], mirror_y_face_pairs=face_pairs[1],
        canonical_quarter_face_ids=source_faces, canonical_quarter_vertex_ids=vertices,
        vertex_birth_event_ids=np.asarray(birth), vertex_source_ids=np.asarray(origin),
        face_event_ids=arrays['face_event'][source_face], face_roles=arrays['face_role'][source_face],
        face_parent_event_ids=arrays['face_parent_event'][source_face],
        face_source_ids=arrays['face_source'][source_face],
        seam_axis_projection_max=np.array(seam_projection))
    return out, np.asarray(out_chart), evidence


def _final_checks(mesh, evidence):
    t = topology(mesh)
    if len(mesh.xyz)-len(t['edges'])+len(mesh.faces) != 2:
        raise ValueError('Mirrored output Euler is not 2.')
    if len(np.unique(mesh.faces)) != len(mesh.xyz):
        raise ValueError('Mirrored output contains orphan vertices.')
    # Connectivity on the control edge graph, independent of coincident XYZ.
    visited = np.zeros(len(mesh.xyz), bool)
    adjacency = [[] for _ in mesh.xyz]
    for a, b in t['edges']:
        adjacency[a].append(b); adjacency[b].append(a)
    stack = [0]; visited[0] = True
    while stack:
        for v in adjacency[stack.pop()]:
            if not visited[v]:
                visited[v] = True; stack.append(v)
    if not visited.all():
        raise ValueError('Mirrored output has multiple bodies.')
    original = _canonical_polygons(mesh.faces)
    for axis, name in enumerate(('x', 'y')):
        pairs = evidence['mirror_'+name+'_vertex_pairs']
        if not np.array_equal(pairs[pairs], np.arange(len(pairs))):
            raise ValueError('Mirror vertex mapping is not an involution.')
        signs = np.ones(3); signs[axis] = -1.
        if not np.array_equal(mesh.xyz, mesh.xyz[pairs]*signs):
            raise ValueError('Actual output XYZ reflection differs.')
        if not np.array_equal(original, _canonical_polygons(pairs[mesh.faces[:, ::-1]])):
            raise ValueError('Actual mirrored oriented polygon correspondence failed.')
    return dict(finite=bool(np.isfinite(mesh.xyz).all()), closed_oriented_edges=True,
        components=1, euler=2, orphan_vertices=0, exact_control_xy_reflection=True,
        exact_reflected_oriented_quads=True)


def build(mesh, chart, mode):
    """Return new closed G03 controls/chart, explicit events and array evidence.

    ROOT_ONLY and BRANCHED perform the identical root operation. Rejected child
    proposals are retained; they never trigger alternate locations or repair.
    The caller owns actual native export/render and later subdivision lineage.
    """
    if mode not in MODES:
        raise ValueError('Mode must be ROOT_ONLY or BRANCHED.')
    recipe = copy.deepcopy(RECIPE)
    chart = np.asarray(chart, float).copy()
    source_errors = _input_checks(mesh, chart, recipe)
    source_surface = getattr(mesh, 'surface', 'mean')
    source_xyz_hash, source_face_hash = array_hash(mesh.xyz), array_hash(mesh.faces)
    mesh = copy.deepcopy(mesh)
    mesh.surface = 'mean'
    nv, nf = len(mesh.xyz), len(mesh.faces)
    arrays = dict(vertex_birth=np.zeros(nv, np.int64), vertex_origin=np.arange(nv),
        face_event=np.zeros(nf, np.int64), face_role=np.zeros(nf, np.int8),
        face_parent_event=np.zeros(nf, np.int64), face_source=np.arange(nf), face_token=np.arange(nf))
    next_token, next_event = nf, 1
    events, evidence = [], {}

    def apply(selected, level, parent_id, direction, proposal=None):
        nonlocal mesh, chart, arrays, next_token, next_event
        event_id = next_event; next_event += 1
        selected = np.asarray(selected, np.int64)
        if level and (np.any(arrays['face_event'][selected] != parent_id) or
                      np.any(arrays['face_role'][selected] != 2)):
            raise ValueError('A descendant selection escaped its generated parent cap role.')
        vertices, ring, _ = disk_boundary(mesh, selected)
        prefix = ('root', 'child', 'grandchild')[level]
        spec = dict(heights=recipe[prefix+'_heights'], scales=recipe[prefix+'_scales'],
            bend=recipe[prefix+'_bend'], direction=np.asarray(direction).tolist(),
            twist=recipe['twist'], projection_guard=recipe['projection_guard'])
        before_count = len(mesh.xyz)
        out, meta, state = sweep_disk(mesh, selected, spec, arrays['face_event'], event_id)
        parents, caps = state['parent_face'], state['cap_faces']
        new_face = state['face_scope'] == event_id
        ring_origin = np.tile(ring, len(spec['heights']))
        if len(out.xyz) != before_count+len(ring_origin):
            raise ValueError('Unexpected sweep ring vertex ordering; no chart fallback.')
        new_chart = np.r_[chart, chart[ring_origin]]
        updated = {key: arrays[key][parents].copy() for key in
            ('face_event', 'face_role', 'face_parent_event', 'face_source', 'face_token')}
        updated['face_parent_event'][new_face] = arrays['face_event'][parents[new_face]]
        updated['face_event'][new_face] = event_id
        updated['face_role'][new_face] = 1; updated['face_role'][caps] = 2
        updated['face_token'][new_face] = np.arange(next_token, next_token+new_face.sum())
        next_token += int(new_face.sum())
        updated['vertex_birth'] = np.r_[arrays['vertex_birth'], np.full(len(ring_origin), event_id)]
        interior = np.setdiff1d(vertices, ring)
        updated['vertex_birth'][interior] = event_id
        updated['vertex_origin'] = np.r_[arrays['vertex_origin'], arrays['vertex_origin'][ring_origin]]
        key = f'event_{event_id:03d}_'
        evidence.update({key+'selected_input_faces': selected.copy(), key+'parent_face': parents.copy(),
            key+'generated_cap_faces': caps.copy(), key+'input_vertices': vertices.copy(),
            key+'input_xyz': mesh.xyz[vertices].copy(), key+'input_chart': chart[vertices].copy(),
            key+'boundary_ring': ring.copy(), key+'ring_source_vertex_ids': ring_origin.copy(),
            key+'ring_generated_vertex_ids': np.arange(before_count, len(out.xyz)),
            key+'selected_parent_event_ids': arrays['face_event'][selected].copy(),
            key+'selected_parent_roles': arrays['face_role'][selected].copy(),
            key+'output_xyz_hash': np.array(array_hash(out.xyz)),
            key+'output_face_hash': np.array(array_hash(out.faces))})
        record = dict(event_id=event_id, status='accepted', level=level, parent_event_id=parent_id,
            selected_input_faces=selected.tolist(), generated_cap_faces=caps.tolist(),
            actual_patch_faces=len(selected), generated_cap_tokens=updated['face_token'][caps].tolist(),
            boundary_vertices=len(ring), source_generation=int(mesh.generation),
            geometry=meta, proposal=proposal,
            chart_rule='New ring copies its actual input boundary chart; retained/interior chart unchanged')
        events.append(record)
        mesh, chart, arrays = out, new_chart, updated
        mesh.surface = 'mean'
        return event_id

    selected = _root_selection(mesh, chart, recipe)
    root_frame = _pca(mesh, selected, recipe)
    root_id = apply(selected, 0, 0, root_frame['major'])
    evidence['root_pca_origin'] = root_frame['origin']
    evidence['root_pca_major'] = root_frame['major']
    evidence['root_pca_minor'] = root_frame['minor']
    evidence['root_pca_normal'] = root_frame['normal']
    evidence['root_pca_extent'] = root_frame['extent']

    def descendants(parent_id, level):
        nonlocal next_event
        caps = np.flatnonzero((arrays['face_event'] == parent_id) & (arrays['face_role'] == 2))
        try:
            plans = _plans(mesh, caps, level, parent_id, arrays['face_token'], recipe)
        except ValueError as exc:
            events.append(dict(event_id=next_event, status='rejected', level=level,
                parent_event_id=parent_id, reason=str(exc), stage='parent cap PCA'))
            next_event += 1
            return []
        accepted = []
        for proposal in plans:
            if proposal['proposal_status'] == 'rejected':
                events.append(dict(event_id=next_event, status='rejected', **proposal))
                next_event += 1; continue
            token_ids = np.asarray(proposal['selected_tokens'])
            current = np.flatnonzero(np.isin(arrays['face_token'], token_ids))
            if len(current) != len(token_ids):
                raise ValueError('Frozen sibling face-token mapping was consumed unexpectedly.')
            accepted.append(apply(current, level, parent_id, proposal['direction'], proposal))
        return accepted

    if mode == 'BRANCHED':
        child_ids = descendants(root_id, 1)
        for child_id in child_ids:
            descendants(child_id, 2)
    out, out_chart, reflected = _quarter_mirror(mesh, chart, arrays, recipe)
    evidence.update(reflected)
    checks = _final_checks(out, evidence)
    evidence.update(source_xyz_hash=np.array(source_xyz_hash), source_face_hash=np.array(source_face_hash),
        source_surface=np.array(source_surface), output_surface=np.array('mean'),
        source_reflection_max_errors=np.asarray(source_errors),
        output_generation=np.array(out.generation), subdivision_passes_added=np.array(0),
        accepted_event_counts_by_level=np.array([sum(e['status'] == 'accepted' and e['level'] == k for e in events) for k in range(3)]),
        rejected_event_count=np.array(sum(e['status'] == 'rejected' for e in events)),
        recipe_json=np.array(json.dumps(recipe, sort_keys=True)),
        checks_json=np.array(json.dumps(checks, sort_keys=True)),
        ancestry_scope=np.array('Mirror IDs refer to canonical-quarter ancestry, not original opposite-quarter vertex/face IDs; rest/anchors are source associations, event parentage is separate'))
    return out, out_chart, events, evidence
