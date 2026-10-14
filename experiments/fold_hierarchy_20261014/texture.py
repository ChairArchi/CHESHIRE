"""One integral diagonal relief per actual G6 parent on unchanged G7 fans.

The eight curved boundary vertices remain fixed. The interior parent centre
and four native child-fan centres are displaced; saved controls are read only.
This operator performs no subdivision, topology replacement, or file writes.
"""
import hashlib

import numpy as np


CHUNK = 16384


def _unit(value):
    return value/np.maximum(np.linalg.norm(value, axis=-1, keepdims=True), 1e-30)


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _pair(value, count, label):
    value = np.asarray(value)
    if (value.shape != (count,) or value.dtype.kind not in 'iu' or
            value.min() < 0 or value.max() >= count or
            not np.array_equal(value[value], np.arange(count))):
        raise ValueError('Actual mirror involution required: '+label)
    return value


def _patch(xyz, groups, parents):
    """Actual curved eight-boundary patch and its unchanged native fans."""
    q = groups[parents]
    points = xyz[q]
    outer = points[:, :, 1]
    boundary = np.empty((len(parents), 8, 3), dtype=xyz.dtype)
    boundary[:, ::2] = outer
    boundary[:, 1::2] = points[:, :, 2]
    centre = points[:, 0, 3]
    edge = np.roll(boundary, -1, axis=1)-boundary
    cross = np.cross(edge, centre[:, None, :]-boundary)
    normal = _unit(cross.sum(axis=1))
    signed = np.einsum('nki,ni->nk', cross, normal)
    altitude = (signed/np.maximum(np.linalg.norm(edge, axis=2), 1e-30)).min(axis=1)
    diagonal_delta = (outer[:, 0]+outer[:, 2]-outer[:, 1]-outer[:, 3])*.5
    diagonal = (np.einsum('ni,ni->n', diagonal_delta, normal) < 0).astype(np.int8)
    fans = points.mean(axis=2)
    source_cross = np.cross(np.roll(points, -1, axis=2)-points,
                            fans[:, :, None, :]-points)
    return q, points, fans, normal, altitude, diagonal, source_cross


def _candidate_cross(points, fans, normal, heights, diagonal):
    control_delta = heights[:, None]*normal
    fan_gain = np.full((len(points), 4), .25)
    rows = np.arange(len(points))
    fan_gain[rows, diagonal] = 1.
    fan_gain[rows, diagonal+2] = 1.
    fan_delta = fan_gain[:, :, None]*control_delta[:, None, :]
    changed = points.copy()
    changed[:, :, 3] += control_delta[:, None, :]
    changed_fans = fans+fan_delta
    cross = np.cross(np.roll(changed, -1, axis=2)-changed,
                     changed_fans[:, :, None, :]-changed)
    return control_delta, fan_delta, cross


def build(control_xyz, control_quads, parent_weight, face_pair_x, face_pair_y,
          vertex_pair_x, vertex_pair_y, height):
    """Return native XYZ, original fan indices, JSON metadata, NPZ state.

    ``parent_weight`` is prepared by the caller from the existing broad mask
    and one parent-neighbour feather. No additional fine-cell size gate is
    introduced here. Native prefix centres may move; input controls never do.
    """
    xyz, q = np.asarray(control_xyz), np.asarray(control_quads)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.dtype.kind != 'f' or
            not np.isfinite(xyz).all() or q.ndim != 2 or q.shape[1] != 4 or
            q.dtype.kind not in 'iu' or not len(q) or len(q) % 4 or
            q.min() < 0 or q.max() >= len(xyz)):
        raise ValueError('Finite actual all-quad G7 carrier required.')
    if not np.isfinite(height) or height <= 0:
        raise ValueError('Positive physical reference height required.')
    nc, nq = len(xyz), len(q)
    groups = q.reshape(-1, 4, 4)
    npatch = len(groups)
    weight = np.asarray(parent_weight)
    if (weight.shape != (npatch,) or weight.dtype.kind != 'f' or
            not np.isfinite(weight).all() or weight.min() < 0 or weight.max() > 1):
        raise ValueError('One finite parent weight in [0,1] required.')
    px = _pair(face_pair_x, nq, 'X source faces')
    py = _pair(face_pair_y, nq, 'Y source faces')
    vx = _pair(vertex_pair_x, nc, 'X source vertices')
    vy = _pair(vertex_pair_y, nc, 'Y source vertices')
    if not np.array_equal(px[py], py[px]) or not np.array_equal(vx[vy], vy[vx]):
        raise ValueError('Actual X/Y mirror actions must commute.')
    for start in range(0, nq, 65536):
        ids = np.arange(start, min(nq, start+65536))
        for vp, fp in ((vx, px), (vy, py)):
            reflected = vp[q[ids]][:, [0, 3, 2, 1]]
            target = q[fp[ids]]
            matches = np.zeros(len(ids), bool)
            for shift in range(4):
                matches |= np.all(np.roll(reflected, shift, axis=1) == target, axis=1)
            if not matches.all():
                raise ValueError('Actual reflected oriented source quad cycles differ.')
    if (not np.all(groups[:, :, 3] == groups[:, :1, 3]) or
            not np.array_equal(groups[:, :, 0], np.roll(groups[:, :, 2], 1, axis=1))):
        raise ValueError('Actual four-child common-centre/boundary cycle differs.')
    centres = groups[:, 0, 3]
    if len(np.unique(centres)) != npatch:
        raise ValueError('Actual parents must have distinct interior centres.')
    # Parent centre IDs must not occur anywhere on any parent boundary.
    is_centre = np.zeros(nc, bool)
    is_centre[centres] = True
    for start in range(0, npatch, CHUNK):
        if is_centre[groups[start:start+CHUNK, :, :3]].any():
            raise ValueError('An interior parent centre appears on a patch boundary.')
    ppx_all, ppy_all = px.reshape(-1, 4)//4, py.reshape(-1, 4)//4
    if not np.all(ppx_all == ppx_all[:, :1]) or not np.all(ppy_all == ppy_all[:, :1]):
        raise ValueError('Actual face mirrors do not transport complete parent patches.')
    ppx, ppy = ppx_all[:, 0], ppy_all[:, 0]
    _pair(ppx, npatch, 'X actual parents')
    _pair(ppy, npatch, 'Y actual parents')
    if (not np.array_equal(vx[centres], centres[ppx]) or
            not np.array_equal(vy[centres], centres[ppy])):
        raise ValueError('Actual parent-centre vertex reflection differs.')
    if not np.array_equal(weight, weight[ppx]) or not np.array_equal(weight, weight[ppy]):
        raise ValueError('Prepared parent support must have exact actual mirror symmetry.')
    parent_ids = np.arange(npatch, dtype=np.int64)
    pxy = ppx[ppy]
    representative = np.minimum(np.minimum(parent_ids, ppx), np.minimum(ppy, pxy))
    fixed = (ppx == parent_ids) | (ppy == parent_ids) | (pxy == parent_ids)
    requested = (weight > 0) & ~fixed
    canonical = np.flatnonzero(requested & (representative == parent_ids))
    safe = np.zeros(npatch, bool)
    heights = np.zeros(npatch, float)
    diagonal_state = np.full(npatch, -1, np.int8)
    cap = float(height)*.0012
    cap_count = 0
    minimum_area = float('inf')
    minimum_cross_cosine = 1.
    # Native centres begin as the actual arithmetic fan of the supplied body.
    native_xyz = np.empty((nc+nq, 3), xyz.dtype)
    native_xyz[:nc] = xyz
    for start in range(0, nq, 65536):
        native_xyz[nc+start:nc+min(nq, start+65536)] = xyz[q[start:start+65536]].mean(axis=1)
    native_faces = np.empty((4*nq, 3), q.dtype)
    for start in range(0, nq, 65536):
        stop = min(nq, start+65536)
        cq = q[start:stop]
        dest = native_faces[4*start:4*stop].reshape(-1, 4, 3)
        dest[:, :, 0] = cq
        dest[:, :, 1] = np.roll(cq, -1, axis=1)
        dest[:, :, 2] = (nc+np.arange(start, stop))[:, None]
    for start in range(0, len(canonical), CHUNK):
        p = canonical[start:start+CHUNK]
        cq, points, fans, normal, altitude, diag, old_cross = _patch(xyz, groups, p)
        raw_height = .55*weight[p]*altitude
        h = np.minimum(raw_height, cap)
        dc, df, new_cross = _candidate_cross(points, fans, normal, h, diag)
        old_area2 = np.linalg.norm(old_cross, axis=3)
        new_area2 = np.linalg.norm(new_cross, axis=3)
        cross_dot = np.einsum('ncki,ncki->nck', old_cross, new_cross)
        valid = ((altitude > 0) & (h > 0) & np.isfinite(h) &
                 np.isfinite(new_cross).all(axis=(1, 2, 3)) &
                 (old_area2 > 0).all(axis=(1, 2)) &
                 (new_area2 > 0).all(axis=(1, 2)) &
                 (cross_dot > 0).all(axis=(1, 2)))
        # Validate actual reflected source coordinates, not only the canonical
        # idealisation; all four patches are accepted or excluded together.
        orbits = []
        for mx, my in ((False, False), (True, False), (False, True), (True, True)):
            parents, child_faces = p.copy(), (4*p[:, None]+np.arange(4)).copy()
            center_ids = centres[p].copy()
            cdelta, fdelta = dc.copy(), df.copy()
            if mx:
                parents, child_faces, center_ids = ppx[parents], px[child_faces], vx[center_ids]
                cdelta[:, 0] *= -1
                fdelta[:, :, 0] *= -1
            if my:
                parents, child_faces, center_ids = ppy[parents], py[child_faces], vy[center_ids]
                cdelta[:, 1] *= -1
                fdelta[:, :, 1] *= -1
            if not np.array_equal(center_ids, centres[parents]):
                raise ValueError('Mapped native prefix centre differs from actual parent.')
            qp = q[child_faces]
            source_points = xyz[qp]
            source_fans = source_points.mean(axis=2)
            changed = source_points.copy()
            changed[:, :, 3] += cdelta[:, None, :]
            changed_fans = source_fans+fdelta
            old = np.cross(np.roll(source_points, -1, axis=2)-source_points,
                           source_fans[:, :, None, :]-source_points)
            new = np.cross(np.roll(changed, -1, axis=2)-changed,
                           changed_fans[:, :, None, :]-changed)
            old_a, new_a = np.linalg.norm(old, axis=3), np.linalg.norm(new, axis=3)
            dot = np.einsum('ncki,ncki->nck', old, new)
            valid &= ((old_a > 0).all(axis=(1, 2)) & (new_a > 0).all(axis=(1, 2)) &
                      (dot > 0).all(axis=(1, 2)) & np.isfinite(new).all(axis=(1, 2, 3)))
            orbits.append((parents, child_faces, center_ids, cdelta, fdelta, new_a, dot, old_a))
        cap_count += 4*int(np.count_nonzero(valid & (raw_height >= cap)))
        for parents, child_faces, center_ids, cdelta, fdelta, new_a, dot, old_a in orbits:
            accepted = parents[valid]
            safe[accepted] = True
            heights[accepted] = h[valid]
            # Store the diagonal in each actual parent's own child order.
            chosen = child_faces[valid, diag[valid]] % 4
            diagonal_state[accepted] = chosen % 2
            native_xyz[center_ids[valid]] = xyz[center_ids[valid]]+cdelta[valid]
            fan_ids = nc+child_faces[valid]
            native_xyz[fan_ids] += fdelta[valid]
            if valid.any():
                minimum_area = min(minimum_area, float(new_a[valid].min())*.5)
                minimum_cross_cosine = min(minimum_cross_cosine,
                    float((dot[valid]/(old_a[valid]*new_a[valid])).min()))
    selected = np.flatnonzero(safe)
    if len(selected) != 4*np.count_nonzero(safe & (representative == parent_ids)):
        raise ValueError('Accepted patches lost complete four-parent mirror orbits.')
    if not np.array_equal(safe, safe[ppx]) or not np.array_equal(safe, safe[ppy]):
        raise ValueError('Accepted patch safety differs across actual mirrors.')
    if not len(selected):
        raise ValueError('No safe nonfixed coarse diagonal relief patch survived.')
    # Validate changed prefix set and source+delta reflection without ever
    # replacing the actual source XYZ by idealised reflected positions.
    changed_prefix = centres[selected]
    prefix_keep = np.ones(nc, bool)
    prefix_keep[changed_prefix] = False
    for start in range(0, nc, 65536):
        stop = min(nc, start+65536)
        keep = prefix_keep[start:stop]
        if not np.array_equal(native_xyz[start:stop][keep], xyz[start:stop][keep]):
            raise ValueError('An unselected prefix or source boundary moved.')
    maximum_delta_symmetry_error = 0.
    maximum_reconstruction_error = 0.
    actual_changed_prefix_count = 0
    actual_changed_fan_count = 0
    source_height_pitch, finished_height_pitch = [], []
    for start in range(0, len(selected), CHUNK):
        p = selected[start:start+CHUNK]
        child = 4*p[:, None]+np.arange(4)
        centre_ids = centres[p]
        dc = native_xyz[centre_ids]-xyz[centre_ids]
        source_fans = xyz[q[child]].mean(axis=2)
        df = native_xyz[nc+child]-source_fans
        actual_changed_prefix_count += int(np.count_nonzero(np.any(dc != 0, axis=1)))
        actual_changed_fan_count += int(np.count_nonzero(np.any(df != 0, axis=2)))
        maximum_reconstruction_error = max(maximum_reconstruction_error,
            float(np.max(np.abs(xyz[centre_ids]+dc-native_xyz[centre_ids]))),
            float(np.max(np.abs(source_fans+df-native_xyz[nc+child]))))
        for axis, vp, fp in ((0, vx, px), (1, vy, py)):
            rdc = native_xyz[vp[centre_ids]]-xyz[vp[centre_ids]]
            rdf = native_xyz[nc+fp[child]]-xyz[q[fp[child]]].mean(axis=2)
            rdc[:, axis] *= -1
            rdf[:, :, axis] *= -1
            maximum_delta_symmetry_error = max(maximum_delta_symmetry_error,
                float(np.max(np.abs(dc-rdc))), float(np.max(np.abs(df-rdf))))
        _, points, fans, normal, _, _, old_cross = _patch(xyz, groups, p)
        new_points = native_xyz[q[child]]
        new_fans = native_xyz[nc+child]
        new_cross = np.cross(np.roll(new_points, -1, axis=2)-new_points,
                             new_fans[:, :, None, :]-new_points)
        for cross, samples in ((old_cross, source_height_pitch), (new_cross, finished_height_pitch)):
            angle = np.rad2deg(np.arccos(np.clip(np.einsum('ncki,ni->nck',
                _unit(cross), normal), -1., 1.)))
            samples.append(angle[:, :, [1, 2]].ravel().astype(np.float32))
    if maximum_delta_symmetry_error > 2e-12 or maximum_reconstruction_error > 1e-12:
        raise ValueError('Native relief displacement reflection/reconstruction exceeds roundoff.')
    if not np.isfinite(native_xyz).all():
        raise ValueError('Nonfinite native output.')
    pitch_before = np.concatenate(source_height_pitch)
    pitch_after = np.concatenate(finished_height_pitch)
    metadata = dict(implementation='PARENT_COARSE_DIAGONAL_NATIVE_RELIEF_V1',
        source_control_vertices=nc, source_control_quads=nq,
        native_vertices=len(native_xyz), native_triangles=len(native_faces),
        actual_parent_patches=npatch, requested_parent_patches=int(requested.sum()),
        accepted_parent_patches=len(selected), unsafe_parent_patches_excluded=int(requested.sum()-safe.sum()),
        fixed_parent_patches_left_untouched=int(np.count_nonzero((weight > 0) & fixed)),
        changed_native_prefix_centres=actual_changed_prefix_count,
        changed_native_child_fan_centres=actual_changed_fan_count,
        unchanged_native_prefix_vertices=nc-actual_changed_prefix_count,
        hierarchy_and_texture_scope='One native diagonal repeat spans four actual G7 children of one G6 parent; approximately twice the corresponding linear material footprint. Existing curved G7 parent boundaries are retained; no G8 or additional subdivision.',
        profile='Parent centre +h*N; two higher-diagonal child fan centres +h*N; other child fan centres +.25h*N. Eight curved boundary points remain unchanged.',
        height='h=min(.55*prepared_parent_weight*minimum_positive_projected_8boundary_altitude,H*.0012)',
        physical_height_reference=float(height), height_cap=cap, height_cap_parent_count=cap_count,
        height_quantiles=np.quantile(heights[selected], [.1, .5, .9, .99]).tolist(),
        minimum_new_changed_triangle_area=minimum_area,
        minimum_changed_triangle_old_new_normal_cosine=minimum_cross_cosine,
        source_fan_pitch_quantiles_degrees=np.quantile(pitch_before, [.1, .5, .9, .99]).tolist(),
        finished_fan_pitch_quantiles_degrees=np.quantile(pitch_after, [.1, .5, .9, .99]).tolist(),
        maximum_delta_XY_symmetry_error=maximum_delta_symmetry_error,
        maximum_source_plus_delta_reconstruction_error=maximum_reconstruction_error,
        unchanged_source_boundary_and_other_prefix_vertices_checked=True,
        source_native_fan_topology_exact=True, zero_weight_native_geometry_effect=True,
        validation='All 16 actually changed triangles per parent have positive area and positive old/new cross product dot. Unsafe whole mirror orbits excluded once; no amplitude retry.',
        source_control_xyz_sha256=_hash(xyz), source_control_faces_sha256=_hash(q),
        native_xyz_sha256=_hash(native_xyz), native_faces_sha256=_hash(native_faces),
        limits='Native detail displaces existing G7 parent-centre prefix vertices. Saved control carrier is immutable and differs from that native prefix intentionally. No global self-intersection or fabrication certificate.')
    state = dict(parent_weight=weight.copy(), parent_height=heights,
        parent_diagonal=diagonal_state, safe_parent=safe,
        parent_centre_control_ids=centres.copy())
    return native_xyz, native_faces, metadata, state
