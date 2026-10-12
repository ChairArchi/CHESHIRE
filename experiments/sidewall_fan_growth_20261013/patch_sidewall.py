"""Three actual-sidewall disk sweeps from a frozen ROOT_ONLY G03 parent.

The beta sectors are one authored alternative, not learned branch placement or
user-required proportions. Existing root control-cap coordinates remain exact
before subsequent subdivision. Later CC can couple neighbouring cap geometry.
Material charts overlap at new rings; all reflection uses saved vertex identity.
"""
from pathlib import Path
import copy
import importlib.util
import json

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('sidewall_frozen_patch_growth',
    REPO/'experiments/connected_fold_growth_20261012/patch_growth.py')
growth = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(growth)

RECIPE = dict(source_generation=3, output_generation=3,
    parent_event_id=1, parent_role=1, parent_rows=[1, 2],
    beta_centres=[-1.85, 1.30, .05], beta_halfwidth=.35,
    heights_root_radius=[.12, .40, .70], scales=[1., .80, .45],
    bend=.30, twist=0., projection_guard=False, minimum_patch_faces=2,
    seam_tolerance=1e-11, source_symmetry_tolerance=0., pca_gap_tolerance=1e-8,
    selection_scope='Fixed beta sectors of actual inherited root boundary PCA; sidewall rows 1 and 2 only (zero based)',
    coefficient_scope='A single authored alternative recipe; coefficients are not user design constraints',
    generation_scope='G03 remains 3; inherited root and new topology events are counted separately from subdivision',
    symmetry_scope='Actual saved parent involutions checked; canonical complete faces reflected by vertex identity',
    collision_scope='Intersections allowed; no collision checks or repair',
    cap_scope='Inherited root control-cap XYZ exact before subsequent CC; no later CC cap-invariance claim',
    lineage_scope='Existing births and source associations inherited; new or moved interior birth uses event ID and class -1; mirrored source associations mean canonical ancestry')


def _json(value):
    return np.array(json.dumps(value, sort_keys=True))


def _oriented_rows(faces):
    faces = np.asarray(faces)
    first = np.argmin(faces, axis=1)
    return np.take_along_axis(faces,
        (first[:, None]+np.arange(4)[None]) % 4, axis=1)


def _parent_checks(mesh, chart, evidence, events):
    if int(mesh.generation) != 3 or getattr(mesh, 'surface', 'mean') != 'mean':
        raise ValueError('Frozen ROOT_ONLY mean-native G03 parent required.')
    if mesh.faces.ndim != 2 or mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0):
        raise ValueError('Closed all-quad parent required; no repair.')
    if chart.shape != mesh.xyz.shape or not np.isfinite(chart).all() or not np.isfinite(mesh.xyz).all():
        raise ValueError('Finite aligned parent XYZ/material chart required.')
    for key in ('vertex_birth_event_ids', 'vertex_source_ids', 'mirror_source_vertex_ids',
                'mirror_signs', 'mirror_x_vertex_pairs', 'mirror_y_vertex_pairs'):
        if len(evidence[key]) != len(mesh.xyz):
            raise ValueError('Parent vertex evidence length differs: '+key)
    for key in ('face_event_ids', 'face_roles', 'face_parent_event_ids', 'face_source_ids',
                'mirror_source_face_ids', 'mirror_face_signs', 'mirror_x_face_pairs', 'mirror_y_face_pairs'):
        if len(evidence[key]) != len(mesh.faces):
            raise ValueError('Parent face evidence length differs: '+key)
    if np.any(np.asarray(evidence['face_event_ids']) > 1) or np.any(np.asarray(evidence['vertex_birth_event_ids']) > 1):
        raise ValueError('Parent already contains descendants; frozen ROOT_ONLY required.')
    roots = [e for e in events if e['status'] == 'accepted']
    if len(roots) != 1 or roots[0]['event_id'] != 1 or roots[0]['level'] != 0:
        raise ValueError('Exactly inherited root event 1 required.')
    growth._final_checks(mesh, evidence)
    rows = _oriented_rows(mesh.faces)
    for axis, name in enumerate(('x', 'y')):
        pairs = np.asarray(evidence['mirror_'+name+'_vertex_pairs'])
        fpair = np.asarray(evidence['mirror_'+name+'_face_pairs'])
        if not np.array_equal(fpair[fpair], np.arange(len(mesh.faces))):
            raise ValueError('Parent face map is not an involution.')
        if not np.array_equal(rows[fpair], _oriented_rows(pairs[mesh.faces[:, ::-1]])):
            raise ValueError('Parent saved face map does not reflect oriented quads.')
        signs = np.ones(3); signs[axis+1] = -1.
        if not np.array_equal(chart, chart[pairs]*signs):
            raise ValueError('Parent material chart disagrees with actual identity reflection.')
    return roots[0]


def _root_layout(mesh, chart, evidence, root, recipe):
    """Recover rows directly from Task32 face order and frozen original ring."""
    boundary = np.asarray(evidence['event_001_boundary_ring'], np.int64)
    n = len(boundary)
    cap = np.asarray(evidence['event_001_generated_cap_faces'], np.int64)
    rings = len(root['geometry']['spec']['heights'])
    if n != root['boundary_vertices'] or rings != 3 or not len(cap):
        raise ValueError('Unexpected inherited root ring/cap structure.')
    cap_start = int(cap.min())
    wall_start = cap_start-rings*n
    if wall_start < 0 or not np.array_equal(cap, np.arange(cap_start, cap_start+len(cap))):
        raise ValueError('Unexpected Task32 contiguous root wall/cap ordering.')
    source_faces = np.asarray(evidence['mirror_source_face_ids'])
    canonical = np.all(np.asarray(evidence['mirror_face_signs']) == [1, 1], axis=1)
    walls = canonical & (np.asarray(evidence['face_event_ids']) == 1) & (np.asarray(evidence['face_roles']) == 1)
    canonical_walls = np.flatnonzero(walls)
    if not np.array_equal(np.sort(source_faces[walls]), np.arange(wall_start, cap_start)):
        raise ValueError('Inherited canonical root wall face IDs do not cover exactly all rings.')
    row = np.full(len(mesh.faces), -1, np.int64)
    column = row.copy()
    row[walls] = (source_faces[walls]-wall_start)//n
    column[walls] = (source_faces[walls]-wall_start) % n
    ids = np.asarray(evidence['event_001_input_vertices'], np.int64)
    input_xyz = np.asarray(evidence['event_001_input_xyz'])
    lookup = {int(v): i for i, v in enumerate(ids)}
    try:
        boundary_xyz = input_xyz[[lookup[int(v)] for v in boundary]]
    except KeyError as exc:
        raise ValueError('Inherited root boundary lacks actual input XYZ.') from exc
    # Verify frozen boundary coordinates through identity, without chart nearest search.
    vsource = np.asarray(evidence['mirror_source_vertex_ids'])
    vsigns = np.asarray(evidence['mirror_signs'])
    actual_boundary = []
    for v in boundary:
        match = np.flatnonzero((vsource == v) & np.all(vsigns == [1, 1], axis=1))
        if len(match) != 1:
            raise ValueError('Root boundary has no unique canonical identity.')
        actual_boundary.append(int(match[0]))
    if not np.array_equal(mesh.xyz[actual_boundary], boundary_xyz):
        raise ValueError('Actual parent root base differs from inherited input boundary.')
    frame = {k: np.asarray(evidence['root_pca_'+k], float) for k in ('origin', 'major', 'minor', 'normal', 'extent')}
    basis = np.column_stack([frame['major'], frame['minor'], frame['normal']])
    if not np.isfinite(basis).all() or not np.allclose(basis.T@basis, np.eye(3), atol=1e-12, rtol=0.):
        raise ValueError('Inherited actual root PCA basis is invalid.')
    if np.any(frame['extent'] <= 0.):
        raise ValueError('Inherited root PCA extent vanishes.')
    midpoint = (boundary_xyz+np.roll(boundary_xyz, -1, axis=0))/2.
    projected = (midpoint-frame['origin'])@basis[:, :2]/frame['extent']
    beta = np.arctan2(projected[:, 1], projected[:, 0])
    radius = float(root['geometry']['area_radius'])
    if not np.isfinite(radius) or radius <= 0.:
        raise ValueError('Inherited actual root area radius is invalid.')
    return dict(boundary=boundary, boundary_xyz=boundary_xyz,
        parent_boundary_vertex_ids=np.asarray(actual_boundary), edge_midpoint_xyz=midpoint,
        beta=beta, row=row, column=column, canonical_walls=canonical_walls,
        wall_start=wall_start, cap_start=cap_start, radius=radius, frame=frame)


def _normal_diagnostics(mesh, selected, root_normal):
    f = growth.fields(mesh)
    normals, area = f['nf'][selected], f['area'][selected]
    weighted = np.sum(normals*area[:, None], axis=0)
    norm = float(np.linalg.norm(weighted))
    total = float(area.sum())
    if norm <= 1e-15 or total <= 0.:
        raise ValueError('Actual selected wall normal cancels or area vanishes.')
    normal = weighted/norm
    angles = np.degrees(np.arccos(np.clip(normals@normal, -1., 1.)))
    root_angle = float(np.degrees(np.arccos(np.clip(normal@root_normal, -1., 1.))))
    return dict(actual_area=total, normal=normal.tolist(), normal_coherence=norm/total,
        normal_spread_max_degrees=float(angles.max()),
        normal_spread_rms_degrees=float(np.sqrt(np.average(angles**2, weights=area))),
        angle_to_root_normal_degrees=root_angle,
        scope='Actual area-weighted incoming normals; diagnostic only, no aesthetic success threshold')


def _plans(mesh, layout, recipe):
    plans, used = [], set()
    root_normal = layout['frame']['normal']
    for index, centre in enumerate(recipe['beta_centres']):
        difference = np.arctan2(np.sin(layout['beta']-centre), np.cos(layout['beta']-centre))
        columns = np.flatnonzero(np.abs(difference) < recipe['beta_halfwidth'])
        selected = np.flatnonzero(np.isin(layout['row'], recipe['parent_rows']) &
            np.isin(layout['column'], columns))
        record = dict(sibling_index=index, beta_centre=centre, beta_halfwidth=recipe['beta_halfwidth'],
            parent_rows=recipe['parent_rows'], boundary_columns=columns.tolist(),
            planned_input_faces=selected.tolist(), selected_tokens=selected.tolist(),
            selected_boundary_beta=layout['beta'][columns].tolist(),
            selection_rule=recipe['selection_scope'])
        try:
            if len(selected) < recipe['minimum_patch_faces']:
                raise ValueError('Insufficient actual sidewall multi-face support.')
            vertices, _, _ = growth.disk_boundary(mesh, selected)
            if used.intersection(map(int, vertices)):
                raise ValueError('Sibling sidewall strips share vertices; no retuning or implicit merge.')
            local = growth._pca(mesh, selected, recipe)
            diagnostics = _normal_diagnostics(mesh, selected, root_normal)
            direction = local['major'].copy()
            if np.dot(direction, layout['frame']['major']) < 0.:
                direction *= -1.
            record.update(proposal_status='accepted', direction=direction.tolist(),
                pca_origin=local['origin'].tolist(), pca_major=local['major'].tolist(),
                pca_minor=local['minor'].tolist(), pca_extent=local['extent'].tolist(),
                normal_diagnostics=diagnostics)
            used.update(map(int, vertices))
        except ValueError as exc:
            record.update(proposal_status='rejected', reason=str(exc))
        plans.append(record)
    return plans


def _reflect_parent_ids(ids, signs, parent_evidence, kind):
    ids = np.asarray(ids).copy()
    for axis, name in enumerate(('x', 'y')):
        mask = signs[:, axis] < 0
        ids[mask] = np.asarray(parent_evidence['mirror_'+name+'_'+kind+'_pairs'])[ids[mask]]
    return ids


def build(parent_mesh, parent_chart, parent_evidence, parent_events):
    """Return G03 mean controls, copied chart, NEW child events IDs2+, evidence.

    Input is the exact reflected frozen ROOT_ONLY G03 event output, not original
    WALL or old BRANCHED. No source/root recomputation, repair or fallback occurs.
    Evidence face_parent_source_ids/vertex_parent_source_ids refer to actual
    frozen parent IDs after reflection; face_source_ids retains older ancestry.
    """
    recipe = copy.deepcopy(RECIPE)
    parent_chart = np.asarray(parent_chart)
    root = _parent_checks(parent_mesh, parent_chart, parent_evidence, parent_events)
    layout = _root_layout(parent_mesh, parent_chart, parent_evidence, root, recipe)
    plans = _plans(parent_mesh, layout, recipe)
    mesh, chart = copy.deepcopy(parent_mesh), parent_chart.copy()
    nv, nf = len(mesh.xyz), len(mesh.faces)
    arrays = dict(vertex_birth=np.asarray(parent_evidence['vertex_birth_event_ids']).copy(),
        vertex_origin=np.asarray(parent_evidence['vertex_source_ids']).copy(),
        face_event=np.asarray(parent_evidence['face_event_ids']).copy(),
        face_role=np.asarray(parent_evidence['face_roles']).copy(),
        face_parent_event=np.asarray(parent_evidence['face_parent_event_ids']).copy(),
        face_source=np.asarray(parent_evidence['face_source_ids']).copy(),
        face_token=np.arange(nf), face_parent_source=np.arange(nf), vertex_parent_source=np.arange(nv))
    cap_vertices = np.unique(mesh.faces[(arrays['face_event'] == 1) & (arrays['face_role'] == 2)])
    evidence = {('inherited_'+k): np.asarray(v).copy() for k, v in parent_evidence.items()
        if k.startswith('event_001_') or k.startswith('root_pca_')}
    evidence.update(parent_xyz_hash=np.array(growth.array_hash(mesh.xyz)),
        parent_face_hash=np.array(growth.array_hash(mesh.faces)), parent_chart_hash=np.array(growth.array_hash(chart)),
        parent_root_cap_vertex_ids=cap_vertices, parent_root_cap_xyz=mesh.xyz[cap_vertices].copy(),
        root_boundary_source_vertex_ids=layout['boundary'], root_boundary_parent_vertex_ids=layout['parent_boundary_vertex_ids'],
        root_boundary_xyz=layout['boundary_xyz'], root_boundary_edge_midpoints=layout['edge_midpoint_xyz'],
        root_boundary_beta=layout['beta'], inherited_root_radius=np.array(layout['radius']),
        inherited_root_wall_start=np.array(layout['wall_start']), inherited_root_cap_start=np.array(layout['cap_start']),
        parent_root_sidewall_row=layout['row'], parent_root_sidewall_column=layout['column'])
    for name in ('face_event_ids', 'face_roles', 'face_parent_event_ids', 'face_source_ids',
                 'vertex_birth_event_ids', 'vertex_source_ids'):
        evidence['initial_parent_'+name] = np.asarray(parent_evidence[name]).copy()
    events, next_token = [], nf
    for index, proposal in enumerate(plans):
        event_id = index+2
        if proposal['proposal_status'] == 'rejected':
            events.append(dict(event_id=event_id, status='rejected', level=1, parent_event_id=1,
                parent_role=1, reason=proposal['reason'], proposal=proposal))
            continue
        selected = np.flatnonzero(np.isin(arrays['face_token'], proposal['selected_tokens']))
        if len(selected) != len(proposal['selected_tokens']):
            raise ValueError('Frozen sibling sidewall tokens were unexpectedly consumed.')
        if np.any(arrays['face_event'][selected] != 1) or np.any(arrays['face_role'][selected] != 1):
            raise ValueError('Sidewall child escaped inherited root event1 role1.')
        vertices, ring, _ = growth.disk_boundary(mesh, selected)
        local = growth._pca(mesh, selected, recipe)
        child_radius = float(np.sqrt(local['area']/np.pi))
        spec = dict(heights=(np.asarray(recipe['heights_root_radius'])*layout['radius']/child_radius).tolist(),
            scales=recipe['scales'], bend=recipe['bend'], direction=proposal['direction'],
            twist=recipe['twist'], projection_guard=recipe['projection_guard'])
        before_count = len(mesh.xyz)
        out, meta, state = growth.sweep_disk(mesh, selected, spec, arrays['face_event'], event_id)
        parents, caps = state['parent_face'], state['cap_faces']
        new_face = state['face_scope'] == event_id
        ring_origin = np.tile(ring, len(spec['heights']))
        if len(out.xyz) != before_count+len(ring_origin):
            raise ValueError('Unexpected Task32 new ring ordering; no chart fallback.')
        updated = {k: arrays[k][parents].copy() for k in ('face_event', 'face_role',
            'face_parent_event', 'face_source', 'face_token', 'face_parent_source')}
        updated['face_parent_event'][new_face] = arrays['face_event'][parents[new_face]]
        updated['face_event'][new_face] = event_id
        updated['face_role'][new_face] = 1
        updated['face_role'][caps] = 2
        updated['face_token'][new_face] = np.arange(next_token, next_token+new_face.sum())
        next_token += int(new_face.sum())
        updated['vertex_birth'] = np.r_[arrays['vertex_birth'], np.full(len(ring_origin), event_id)]
        updated['vertex_birth'][np.setdiff1d(vertices, ring)] = event_id
        for key in ('vertex_origin', 'vertex_parent_source'):
            updated[key] = np.r_[arrays[key], arrays[key][ring_origin]]
        key = f'event_{event_id:03d}_'
        evidence.update({key+'selected_input_faces': selected.copy(), key+'parent_face': parents.copy(),
            key+'generated_cap_faces': caps.copy(), key+'input_vertices': vertices.copy(),
            key+'input_xyz': mesh.xyz[vertices].copy(), key+'input_chart': chart[vertices].copy(),
            key+'boundary_ring': ring.copy(), key+'ring_source_vertex_ids': ring_origin.copy(),
            key+'ring_generated_vertex_ids': np.arange(before_count, len(out.xyz)),
            key+'selected_parent_event_ids': arrays['face_event'][selected].copy(),
            key+'selected_parent_roles': arrays['face_role'][selected].copy(),
            key+'selected_parent_source_face_ids': arrays['face_parent_source'][selected].copy(),
            key+'output_xyz_hash': np.array(growth.array_hash(out.xyz)),
            key+'output_face_hash': np.array(growth.array_hash(out.faces))})
        events.append(dict(event_id=event_id, status='accepted', level=1, parent_event_id=1, parent_role=1,
            selected_input_faces=selected.tolist(), generated_cap_faces=caps.tolist(),
            generated_cap_tokens=updated['face_token'][caps].tolist(), actual_patch_faces=len(selected),
            boundary_vertices=len(ring), source_generation=3, geometry=meta, proposal=proposal,
            root_radius=layout['radius'], child_radius=child_radius,
            height_scope='Absolute heights = authored coefficients times inherited root area radius; Task32 relative heights divided by actual child radius',
            chart_rule='New ring copies actual pre-event input boundary chart; old/interior chart unchanged'))
        mesh, chart, arrays = out, np.r_[chart, chart[ring_origin]], updated
        mesh.surface = 'mean'
    if not np.array_equal(mesh.xyz[cap_vertices], parent_mesh.xyz[cap_vertices]):
        raise ValueError('Inherited root control cap coordinates changed before subdivision.')
    evidence['temporary_parent_face_source_ids'] = arrays['face_parent_source']
    evidence['temporary_parent_vertex_source_ids'] = arrays['vertex_parent_source']
    out, out_chart, reflected = growth._quarter_mirror(mesh, chart, arrays, recipe)
    evidence.update(reflected)
    evidence['face_parent_source_ids'] = _reflect_parent_ids(
        arrays['face_parent_source'][reflected['mirror_source_face_ids']],
        reflected['mirror_face_signs'], parent_evidence, 'face')
    evidence['vertex_parent_source_ids'] = _reflect_parent_ids(
        arrays['vertex_parent_source'][reflected['mirror_source_vertex_ids']],
        reflected['mirror_signs'], parent_evidence, 'vertex')
    checks = growth._final_checks(out, evidence)
    inherited_cap = (evidence['face_event_ids'] == 1) & (evidence['face_roles'] == 2)
    final_cap_vertices = np.unique(out.faces[inherited_cap])
    cap_source = evidence['vertex_parent_source_ids'][final_cap_vertices]
    cap_exact = np.array_equal(out.xyz[final_cap_vertices], parent_mesh.xyz[cap_source])
    if not cap_exact:
        raise ValueError('Inherited root cap XYZ not exact after reflection.')
    normals = np.array([e['proposal']['normal_diagnostics']['normal'] for e in events if e['status'] == 'accepted'])
    angles = np.degrees(np.arccos(np.clip(normals@normals.T, -1., 1.))) if len(normals) else np.empty((0, 0))
    checks.update(inherited_root_control_cap_exact=True, cap_scope=recipe['cap_scope'])
    accepted = sum(e['status'] == 'accepted' for e in events)
    evidence.update(source_xyz_hash=evidence['parent_xyz_hash'], source_face_hash=evidence['parent_face_hash'],
        source_surface=np.array('mean'), output_surface=np.array('mean'),
        source_reflection_max_errors=np.zeros(2), output_generation=np.array(3), subdivision_passes_added=np.array(0),
        accepted_event_counts_by_level=np.array([1, accepted, 0]), inherited_event_count=np.array(1),
        new_accepted_event_count=np.array(accepted), rejected_event_count=np.array(len(events)-accepted),
        child_pair_normal_angles_degrees=angles, recipe_json=_json(recipe), checks_json=_json(checks),
        ancestry_scope=np.array(recipe['lineage_scope']),
        inherited_root_event_json=_json(root),
        parent_correspondence_scope=np.array('face/vertex_parent_source_ids are actual frozen parent indices with parent X/Y involutions; face_source_ids and vertex_source_ids retain older canonical source ancestry'))
    return out, out_chart, events, evidence
