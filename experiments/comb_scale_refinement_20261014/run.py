"""Replace only oversized accepted G7 native roofs by four smaller roofs.

The original control corners and every unrefined native coordinate stay fixed.
Shared boundary midpoints split adjacent existing triangles without changing
their planar surface. This is one local native finish, not a G8 CC pass.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01')
ACCEPTED = Path('E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01')
SOURCE = ACCEPTED/'RELIEF/geometry.npz'
STATE = ACCEPTED/'RELIEF/ridge_state.npz'
CONTROL = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED/control_quad.npz')
MIRRORS = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07/evidence.npz')
EXPECTED = {
    str(SOURCE): 'e874da795215bcd28f31a153f052d774bb2313b828c58cc381989dc115ed3f9e',
    str(STATE): '8ee43315100ec89ff9048515ee636863442f2dceb5c12202e2e4954da10bc2d6',
    str(CONTROL): '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27',
    str(MIRRORS): '226c22ca83f9c71e69059d817e42140483d19a46228d66c6710170bc1ac17e21',
    str(ACCEPTED/'RECEIPT.json'): '2373a46b3fd1192966b0205bd96f174394fa97ba58cc8715a3a83de4daf4cdbc',
}
SELECTION_SHA = '525b00cf7a3249324d88ddf035862fcec5cdb0443e9f2c6ebe90d57694533d09'
MEASUREMENT_SHA = 'b2908e59f057fa37596b78da90033e4c009ec26db399838575b8204774667b6f'
PATTERN = np.array([[0, 1, 4], [1, 5, 4], [1, 2, 5],
                    [2, 3, 5], [3, 4, 5], [3, 0, 4]], np.int64)
# Grid positions: A B C D, M_AB M_BC M_CD M_DA, original parent O.
CHILDREN = np.array([[0, 4, 8, 7], [4, 1, 5, 8],
                     [8, 5, 2, 6], [7, 8, 6, 3]], np.int64)


def digest(path):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            value.update(block)
    return value.hexdigest()


def ah(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def unit(value):
    return value/np.maximum(np.linalg.norm(value, axis=-1, keepdims=True), 1e-30)


def edge_keys(a, b, nc):
    return np.minimum(a, b)*np.int64(nc)+np.maximum(a, b)


def lookup(keys, query):
    index = np.searchsorted(keys, query)
    if (index >= len(keys)).any() or not np.array_equal(keys[index], query):
        raise ValueError('Required shared edge midpoint is missing.')
    return index


def cyclic_equal(a, b):
    answer = np.zeros(len(a), bool)
    for shift in range(4):
        answer |= np.all(np.roll(a, shift, axis=1) == b, axis=1)
    return answer


def template_check():
    triangles = []
    for child, corners in enumerate(CHILDREN):
        ids = np.r_[corners, 9+2*child, 10+2*child]
        triangles.extend(ids[PATTERN])
    edges = {}
    for triangle in triangles:
        for a, b in zip(triangle, np.roll(triangle, -1)):
            key = tuple(sorted((int(a), int(b))))
            edges.setdefault(key, []).append((int(a), int(b)))
    boundary = []
    for incident in edges.values():
        if len(incident) == 1:
            boundary.extend(incident)
        elif len(incident) != 2 or incident[0] != incident[1][::-1]:
            raise ValueError('Four-child patch has invalid interior edge incidence.')
    expected = {(0, 4), (4, 1), (1, 5), (5, 2),
                (2, 6), (6, 3), (3, 7), (7, 0)}
    if set(boundary) != expected or len(edges) != 40:
        raise ValueError('Four-child patch changes the oriented parent boundary.')
    return dict(vertices=17, edges=40, triangles=24, Euler_disk=1,
                boundary=boundary, internal_edges_oppositely_paired=True)


def children(p, weight, parent_height):
    """Canonical actual source corners -> four roofs; no output mutation."""
    o = p.mean(axis=1)
    grid = np.concatenate([p, (p+np.roll(p, -1, axis=1))*.5, o[:, None, :]], axis=1)
    cp = grid[:, CHILDREN]
    center = cp.mean(axis=2)
    edge = np.roll(cp, -1, axis=2)-cp
    cross = np.cross(edge, center[:, :, None, :]-cp)
    normal = unit(cross.sum(axis=2))
    signed = np.einsum('ncki,nci->nck', cross, normal)
    altitude = (signed/np.maximum(np.linalg.norm(edge, axis=3), 1e-30)).min(axis=2)
    diagonal = (cp[:, :, 0]+cp[:, :, 2])*.5-center
    rotate = (np.einsum('nci,nci->nc', diagonal, normal) < 0).astype(np.int64)
    order = (np.arange(4)[None, None, :]+rotate[:, :, None]) % 4
    indices = np.take_along_axis(np.broadcast_to(CHILDREN, (len(p), 4, 4)), order, axis=2)
    cp = np.take_along_axis(cp, order[:, :, :, None], axis=2)
    height = np.minimum(.65*weight[:, None]*altitude, .5*parent_height[:, None])
    ridge = np.stack([.4*cp[:, :, 0]+.6*center+height[:, :, None]*normal,
                      .4*cp[:, :, 2]+.6*center+height[:, :, None]*normal], axis=2)
    points = np.concatenate([cp, ridge], axis=2)
    tri = points[:, :, PATTERN]
    roof_cross = np.cross(tri[:, :, :, 1]-tri[:, :, :, 0], tri[:, :, :, 2]-tri[:, :, :, 0])
    roof_signed = np.einsum('ncki,nci->nck', roof_cross, normal)
    safe = ((signed > 0).all(axis=(1, 2)) & (roof_signed > 0).all(axis=(1, 2)) &
            (altitude > 0).all(axis=1) & (height > 0).all(axis=1) &
            np.isfinite(roof_cross).all(axis=(1, 2, 3)))
    return grid, indices, ridge, height, safe


def old_slots(quad_ids, roof_rank, source_fourfan_count):
    return np.concatenate([4*quad_ids[:, None]+np.arange(4),
                           source_fourfan_count+2*roof_rank[:, None]+np.arange(2)], axis=1)


def exact_mirrored_points(points, px, py):
    """Canonical reflection, allowing the inherited source's tiny residual."""
    ids = np.arange(len(points), dtype=np.int64)
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, px[py]))
    points = points.copy()
    points[px == ids, 0] = 0.
    points[py == ids, 1] = 0.
    out = points[representative].copy()
    out[(ids == px[representative]) | (ids == px[py[representative]]), 0] *= -1
    out[(ids == py[representative]) | (ids == px[py[representative]]), 1] *= -1
    out[px == ids, 0] = 0.
    out[py == ids, 1] = 0.
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if (root/'REFINED').exists() or (root/'RECEIPT.json').exists():
        raise FileExistsError('A previous refinement is immutable; use a new output root.')
    started = time.perf_counter()
    code_sha = digest(__file__)
    snapshot = root/'source_snapshot/experiments/comb_scale_refinement_20261014/run.py'
    if snapshot.exists():
        raise FileExistsError('Earlier execution source snapshot preserved.')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, snapshot)
    selection_path, measurement_path = root/'COARSE_QUADS.npz', root/'MEASUREMENT.json'
    frozen = dict(EXPECTED)
    frozen[str(selection_path)] = SELECTION_SHA
    frozen[str(measurement_path)] = MEASUREMENT_SHA
    for path, checksum in frozen.items():
        if digest(path) != checksum:
            raise ValueError('Frozen input changed: '+path)
    measurement = json.loads(measurement_path.read_text(encoding='utf8'))
    if (measurement['source_native_geometry_sha256'] != EXPECTED[str(SOURCE)] or
            measurement['source_ridge_state_sha256'] != EXPECTED[str(STATE)] or
            measurement['source_control_sha256'] != EXPECTED[str(CONTROL)]):
        raise ValueError('Coarse measurement is not bound to the accepted input.')
    with np.load(CONTROL, allow_pickle=False) as saved:
        xyz, q = saved['xyz'], saved['faces']
    nc, nq = len(xyz), len(q)
    source_fourfan_count, source_base_vertices = 4*nq, nc+nq
    with np.load(STATE, allow_pickle=False) as saved:
        roof_ids, old_corners, old_odd = saved['quad_ids'], saved['oriented_corners'], saved['odd_reflection']
        old_r0, old_r1 = saved['ridge0'], saved['ridge1']
        parent_weight, parent_height = saved['weight'], saved['height']
    roof_rank = np.full(nq, -1, np.int64)
    roof_rank[roof_ids] = np.arange(len(roof_ids))
    with np.load(selection_path, allow_pickle=False) as saved:
        requested = saved['coarse_quad_ids']
    if (requested.dtype != np.int64 or not len(requested) or
            (np.diff(requested) <= 0).any() or requested.min() < 0 or requested.max() >= nq or
            (roof_rank[requested] < 0).any()):
        raise ValueError('Sorted actual accepted coarse roof IDs required.')
    with np.load(MIRRORS, allow_pickle=False) as saved:
        px, py = saved['mirror_x_face_pairs'], saved['mirror_y_face_pairs']
        vx, vy = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    for pair, count in ((px, nq), (py, nq), (vx, nc), (vy, nc)):
        if pair.shape != (count,) or not np.array_equal(pair[pair], np.arange(count)):
            raise ValueError('Actual mirror involutions required.')
    if not np.array_equal(px[py], py[px]) or not np.array_equal(vx[vy], vy[vx]):
        raise ValueError('Actual mirror actions must commute.')
    ids = np.arange(nq, dtype=np.int64)
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, px[py]))
    fixed = (px == ids) | (py == ids) | (px[py] == ids)
    coarse_mask = np.zeros(nq, bool)
    coarse_mask[requested] = True
    if (fixed[requested].any() or not np.array_equal(coarse_mask, coarse_mask[px]) or
            not np.array_equal(coarse_mask, coarse_mask[py])):
        raise ValueError('Coarse selection must comprise complete nonfixed four-face orbits.')
    canonical = requested[representative[requested] == requested]
    if len(requested) != 4*len(canonical):
        raise ValueError('Exactly four source faces per refinement orbit required.')
    bad = np.zeros(nq, bool)
    print('PREFLIGHT', len(requested), 'oversized roofs; one fixed local replacement', flush=True)
    for start in range(0, len(canonical), 8192):
        f = canonical[start:start+8192]
        rr = roof_rank[f]
        if old_odd[rr].any():
            raise ValueError('Canonical accepted parent ordering must be even.')
        _, _, _, _, safe = children(xyz[old_corners[rr]], parent_weight[rr], parent_height[rr])
        rejected = f[~safe]
        bad[rejected] = bad[px[rejected]] = bad[py[rejected]] = bad[px[py[rejected]]] = True
    selected = requested[~bad[requested]]
    if not len(selected):
        raise ValueError('No complete safe four-child patch survived.')
    canonical = selected[representative[selected] == selected]
    local_rank = np.full(nq, -1, np.int64)
    local_rank[selected] = np.arange(len(selected))
    selected_roof_rank = roof_rank[selected]
    with np.load(SOURCE, allow_pickle=False) as saved:
        oldxyz, oldfaces = saved['xyz'], saved['faces']
    nold, fold = len(oldxyz), len(oldfaces)
    if (nold != source_base_vertices+len(roof_ids) or
            fold != source_fourfan_count+2*len(roof_ids) or not np.array_equal(oldxyz[:nc], xyz)):
        raise ValueError('Accepted native source association differs from frozen recipe.')
    slots = old_slots(selected, selected_roof_rank, source_fourfan_count)
    for start in range(0, len(selected), 32768):
        end = min(len(selected), start+32768)
        f, rr = selected[start:end], selected_roof_rank[start:end]
        corners = old_corners[rr]
        boundary = corners.copy()
        boundary[old_odd[rr]] = boundary[old_odd[rr]][:, [0, 3, 2, 1]]
        if not cyclic_equal(boundary, q[f]).all():
            raise ValueError('Accepted parent oriented boundary association failed.')
        vertex_ids = np.column_stack([corners, nc+f, source_base_vertices+rr])
        expected_tri = vertex_ids[:, PATTERN]
        expected_tri[old_odd[rr]] = expected_tri[old_odd[rr]][:, :, [0, 2, 1]]
        if not np.array_equal(oldfaces[slots[start:end]], expected_tri):
            raise ValueError('Actual accepted six-roof triangle slots differ.')
        if (not np.array_equal(oldxyz[nc+f], old_r0[rr]) or
                not np.array_equal(oldxyz[source_base_vertices+rr], old_r1[rr])):
            raise ValueError('Actual accepted ridge coordinates differ.')
    edge_corner = q[selected]
    keys = np.unique(edge_keys(edge_corner, np.roll(edge_corner, -1, axis=1), nc))
    elo, ehi = keys//nc, keys % nc
    midpoint = (xyz[elo]+xyz[ehi])*.5
    mpx = lookup(keys, edge_keys(vx[elo], vx[ehi], nc))
    mpy = lookup(keys, edge_keys(vy[elo], vy[ehi], nc))
    mirrored_midpoint = exact_mirrored_points(midpoint, mpx, mpy)
    midpoint_source_error = float(np.linalg.norm(mirrored_midpoint-midpoint, axis=1).max())
    if midpoint_source_error > 1e-9:
        raise ValueError('Symmetric midpoint no longer lies on its original source edge.')
    midpoint = mirrored_midpoint
    ne, npatch = len(keys), len(selected)
    replaced = np.zeros(fold, bool)
    replaced[slots.ravel()] = True
    incidence = np.zeros(ne, np.int16)
    balance = np.zeros(ne, np.int16)
    split_rows, split_edges, split_mid = [], [], []
    print('CONFORM shared boundary midpoints; preserve unrefined triangle planes', flush=True)
    for start in range(0, fold, 262144):
        end = min(fold, start+262144)
        triangle = oldfaces[start:end]
        count = np.zeros(len(triangle), np.int8)
        for edge in range(3):
            a, b = triangle[:, edge], triangle[:, (edge+1) % 3]
            valid = (a < nc) & (b < nc)
            rows = np.flatnonzero(valid)
            query = edge_keys(a[rows], b[rows], nc)
            index = np.searchsorted(keys, query)
            hit = index < ne
            hit[hit] &= keys[index[hit]] == query[hit]
            rows, index = rows[hit], index[hit]
            count[rows] += 1
            np.add.at(incidence, index, 1)
            np.add.at(balance, index, np.where(a[rows] < b[rows], 1, -1))
            keep = ~replaced[start+rows]
            if keep.any():
                split_rows.append(start+rows[keep])
                split_edges.append(np.full(int(keep.sum()), edge, np.int8))
                split_mid.append(index[keep])
        if (count > 1).any():
            raise ValueError('A source triangle has multiple original quad-boundary edges; unsupported split.')
    if not np.all(incidence == 2) or not np.all(balance == 0):
        raise ValueError('Each refined original edge must have exactly two opposite old incidences.')
    split_rows = np.concatenate(split_rows) if split_rows else np.empty(0, np.int64)
    split_edges = np.concatenate(split_edges) if split_edges else np.empty(0, np.int8)
    split_mid = np.concatenate(split_mid) if split_mid else np.empty(0, np.int64)
    if len(np.unique(split_rows)) != len(split_rows):
        raise ValueError('An unrefined neighbor triangle would be split twice.')
    nsplit = len(split_rows)
    outxyz = np.empty((nold+ne+7*npatch, 3), oldxyz.dtype)
    outxyz[:nold] = oldxyz
    outxyz[nold:nold+ne] = midpoint
    child_corners = np.empty((npatch, 4, 4), np.int64)
    child_ridge_ids = np.empty((npatch, 4, 2), np.int64)
    child_heights = np.empty((npatch, 4), float)
    parity = np.empty(npatch, bool)
    parent_center_ids = nold+ne+7*np.arange(npatch)
    # Reuse the two private old vertices for child0; only seven per-parent new
    # vertices are needed: original O and the other three pairs of ridges.
    child_ridge_ids[:, 0, 0] = nc+selected
    child_ridge_ids[:, 0, 1] = source_base_vertices+selected_roof_rank
    child_ridge_ids[:, 1:] = (parent_center_ids[:, None]+np.arange(1, 7)).reshape(npatch, 3, 2)
    for start in range(0, len(canonical), 8192):
        f = canonical[start:start+8192]
        rr = roof_rank[f]
        parent_corners = old_corners[rr]
        grid, oriented, ridge, height, safe = children(xyz[parent_corners], parent_weight[rr], parent_height[rr])
        if not safe.all():
            raise ValueError('Preflight result changed during deterministic construction.')
        for mx, my in ((False, False), (True, False), (False, True), (True, True)):
            faces, corners, points, o = f.copy(), parent_corners.copy(), ridge.copy(), grid[:, 8].copy()
            if mx:
                faces, corners = px[faces], vx[corners]
                points[:, :, :, 0] *= -1
                o[:, 0] *= -1
            if my:
                faces, corners = py[faces], vy[corners]
                points[:, :, :, 1] *= -1
                o[:, 1] *= -1
            rank = local_rank[faces]
            if (rank < 0).any():
                raise ValueError('Incomplete surviving refinement orbit.')
            mids = nold+lookup(keys, edge_keys(corners, np.roll(corners, -1, axis=1), nc))
            grid_ids = np.column_stack([corners, mids, parent_center_ids[rank]])
            child_corners[rank] = np.take_along_axis(grid_ids[:, None, :].repeat(4, axis=1), oriented, axis=2)
            child_heights[rank], parity[rank] = height, mx != my
            outxyz[parent_center_ids[rank]] = o
            outxyz[child_ridge_ids[rank].reshape(-1)] = points.reshape(-1, 3)
    if not np.array_equal(parity, old_odd[selected_roof_rank]):
        raise ValueError('Refined child parity differs from accepted canonical parent association.')
    outfaces = np.empty((fold+18*npatch+nsplit, 3), oldfaces.dtype)
    outfaces[:fold] = oldfaces
    minimum_area, minimum_signed = float('inf'), float('inf')
    wing_pitch = []
    for start in range(0, npatch, 8192):
        end = min(npatch, start+8192)
        vertex_ids = np.concatenate([child_corners[start:end], child_ridge_ids[start:end]], axis=2)
        tri_ids = vertex_ids[:, :, PATTERN]
        tri_ids[parity[start:end]] = tri_ids[parity[start:end]][:, :, :, [0, 2, 1]]
        actual = outxyz[tri_ids]
        cross = np.cross(actual[:, :, :, 1]-actual[:, :, :, 0], actual[:, :, :, 2]-actual[:, :, :, 0])
        p = outxyz[child_corners[start:end]]
        center = p.mean(axis=2)
        normal = unit(np.cross(np.roll(p, -1, axis=2)-p, center[:, :, None]-p).sum(axis=2))
        normal[parity[start:end]] *= -1
        signed = np.einsum('ncki,nci->nck', cross, normal)
        area = np.linalg.norm(cross, axis=3)*.5
        if not np.isfinite(area).all() or (signed <= 0).any():
            raise ValueError('Actual reflected child roof has a nonpositive projected face.')
        minimum_area = min(minimum_area, float(area.min()))
        minimum_signed = min(minimum_signed, float(signed.min()))
        pitch = np.rad2deg(np.arccos(np.clip(np.einsum('ncki,nci->nck', unit(cross), normal), -1, 1)))
        wing_pitch.append(pitch[:, :, [1, 4]].ravel().astype(np.float32))
        outfaces[slots[start:end].ravel()] = tri_ids[:, 0].reshape(-1, 3)
        outfaces[fold+18*start:fold+18*end] = tri_ids[:, 1:].reshape(-1, 3)
    # Every neighbor split is an exact subdivision of its existing triangle.
    split_plane_error, split_area_error = 0., 0.
    for start in range(0, nsplit, 65536):
        end = min(nsplit, start+65536)
        row, edge, mid = split_rows[start:end], split_edges[start:end], nold+split_mid[start:end]
        triangle = oldfaces[row]
        ar = np.arange(len(row))
        a, b, c = triangle[ar, edge], triangle[ar, (edge+1) % 3], triangle[ar, (edge+2) % 3]
        first, second = np.column_stack([a, mid, c]), np.column_stack([mid, b, c])
        before = oldxyz[triangle]
        oldcross = np.cross(before[:, 1]-before[:, 0], before[:, 2]-before[:, 0])
        normal = unit(oldcross)
        plane_error = abs(np.einsum('ni,ni->n', outxyz[mid]-before[:, 0], normal))
        split_plane_error = max(split_plane_error, float(plane_error.max()))
        areas = []
        for part in (first, second):
            p = outxyz[part]
            cross = np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
            if not np.isfinite(cross).all() or (np.einsum('ni,ni->n', cross, normal) <= 0).any():
                raise ValueError('Conforming neighbor split changes its triangle orientation.')
            areas.append(np.linalg.norm(cross, axis=1))
        oldarea = np.linalg.norm(oldcross, axis=1)
        split_area_error = max(split_area_error, float(abs(areas[0]+areas[1]-oldarea).max()))
        outfaces[row] = first
        outfaces[fold+18*npatch+start:fold+18*npatch+end] = second
    if split_plane_error > 1e-9 or split_area_error > 1e-9:
        raise ValueError('Unrefined neighbor surface changed beyond inherited floating residual.')
    modified_old = np.zeros(nold, bool)
    modified_old[nc+selected] = True
    modified_old[source_base_vertices+selected_roof_rank] = True
    for start in range(0, nold, 262144):
        end = min(nold, start+262144)
        keep = ~modified_old[start:end]
        if not np.array_equal(outxyz[start:end][keep], oldxyz[start:end][keep]):
            raise ValueError('An unrefined accepted native coordinate changed.')
    changed_rows = replaced.copy()
    changed_rows[split_rows] = True
    for start in range(0, fold, 262144):
        end = min(fold, start+262144)
        keep = ~changed_rows[start:end]
        if not np.array_equal(outfaces[start:end][keep], oldfaces[start:end][keep]):
            raise ValueError('An unrelated accepted native triangle changed.')
    if not np.array_equal(outxyz[:nc], xyz) or not np.isfinite(outxyz).all():
        raise ValueError('Source control corners changed or output is nonfinite.')
    symmetry = {}
    for label, axis, pair in (('x', 0, px), ('y', 1, py)):
        reflected_rank = local_rank[pair[selected]]
        points = outxyz[child_ridge_ids]
        reflected = points[reflected_rank].copy()
        reflected[:, :, :, axis] *= -1
        if not np.array_equal(points, reflected):
            raise ValueError('Transported child ridge symmetry is not exact: '+label)
        centers = outxyz[parent_center_ids]
        reflected = centers[reflected_rank].copy()
        reflected[:, axis] *= -1
        if not np.array_equal(centers, reflected):
            raise ValueError('Transported parent center symmetry is not exact: '+label)
        symmetry[label] = 0.
    template = template_check()
    wing_pitch = np.concatenate(wing_pitch)
    folder = root/'REFINED'
    folder.mkdir()
    state_path = folder/'refinement_state.npz'
    np.savez_compressed(state_path, parent_quad_ids=selected, old_roof_rank=selected_roof_rank,
                        child_corner_ids=child_corners, child_ridge_ids=child_ridge_ids,
                        child_height=child_heights, parent_center_ids=parent_center_ids,
                        midpoint_edge_keys=keys, midpoint_vertex_ids=nold+np.arange(ne),
                        odd_reflection=parity, split_source_triangle_ids=split_rows,
                        split_source_edge_index=split_edges, split_midpoint_index=split_mid)
    geometry = folder/'geometry.npz'
    print('SAVE one conforming local scale refinement', len(outxyz), len(outfaces), flush=True)
    xhash, fhash = ah(outxyz), ah(outfaces)
    np.savez_compressed(geometry, xyz=outxyz, faces=outfaces)
    for path, checksum in frozen.items():
        if digest(path) != checksum:
            raise ValueError('Frozen input changed during execution: '+path)
    if digest(__file__) != code_sha or digest(snapshot) != code_sha:
        raise ValueError('Executing source or frozen snapshot changed.')
    stats = dict(requested_parent_roofs=len(requested), refined_parent_roofs=npatch,
        one_orbit_unsafe_parents_excluded=int(bad[requested].sum()),
        preserved_other_accepted_roofs=len(roof_ids)-npatch,
        child_roofs=4*npatch, net_added_roofs=3*npatch,
        unique_shared_midpoints=ne, neighbor_triangles_split=nsplit,
        changed_source_control_corners=0, unchanged_source_control_corners=nc,
        unchanged_old_native_coordinates=nold-int(modified_old.sum()),
        reused_old_private_ridge_vertices=int(modified_old.sum()),
        added_native_vertices=ne+7*npatch, added_native_triangles=18*npatch+nsplit,
        minimum_new_roof_triangle_area=minimum_area, minimum_new_roof_projected_double_area=minimum_signed,
        child_height_quantiles=np.quantile(child_heights, [.1, .5, .9, .99, 1.]).tolist(),
        child_wing_pitch_quantiles_degrees=np.quantile(wing_pitch, [.1, .5, .9, .99]).tolist(),
        child_height_never_exceeds_half_parent=bool(np.all(child_heights <= .5*parent_height[selected_roof_rank, None])),
        symmetric_midpoint_source_error=midpoint_source_error,
        unrefined_split_max_plane_error=split_plane_error,
        unrefined_split_max_double_area_sum_error=split_area_error,
        transported_child_ridge_XY_residual=symmetry)
    validation = dict(control_corners_byte_identical=True,
        all_unrefined_native_coordinates_byte_identical=True,
        unrelated_old_triangle_rows_byte_identical=True,
        accepted_parent_six_triangle_slots_and_ridge_coordinates_checked=True,
        accepted_oriented_parent_boundary_cycles_checked=True,
        all_new_child_roof_projected_signed_areas_positive=True,
        conforming_edge_old_incidence_exactly_two_and_oppositely_oriented=True,
        neighbor_splits_preserve_old_planar_surface=True,
        child_ridge_and_parent_center_reflection_exact=True,
        no_orphan_scope='Both private old parent ridge IDs are reused by child0. Every appended grid center, midpoint and child ridge ID is referenced by the four-child disks or conforming neighbor split.',
        local_template=template,
        topology_scope='Four-child disk has the original oriented boundary split at shared original-edge midpoints; the two old edge incidences conform to the same midpoint. Source closed one-component connectivity is inherited without global edge sorting.',
        limits='No global collision, self-intersection or fabrication certificate. This local native finish is not an additional global Catmull-Clark generation.')
    variant = dict(geometry=str(geometry), geometry_sha256=digest(geometry), xyz_sha256=xhash,
        faces_sha256=fhash, vertices=len(outxyz), triangles=len(outfaces),
        refinement_state=str(state_path), refinement_state_sha256=digest(state_path), validation=validation)
    write(root/'RECEIPT.json', dict(date='2026-10-14', timezone='Asia/Seoul',
        source_native_path=str(SOURCE), source_native_geometry_sha256=EXPECTED[str(SOURCE)],
        source_control_path=str(CONTROL), source_control_sha256=EXPECTED[str(CONTROL)],
        source_ridge_state=str(STATE), source_ridge_state_sha256=EXPECTED[str(STATE)],
        source_hashes_after=frozen, selection_path=str(selection_path), selection_sha256=SELECTION_SHA,
        measurement_path=str(measurement_path), measurement_sha256=MEASUREMENT_SHA,
        geometry_code_sha256={'experiments/comb_scale_refinement_20261014/run.py': code_sha},
        variants={'REFINED': variant}, statistics=stats,
        recipe=dict(stage='LOCAL_NATIVE_COMB_SCALE_REFINEMENT_G7', source_growth_generation=7, added_G8=False,
            selection='Only measured oversized accepted roofs; no new aspect or world-axis gate; one complete source-face-orbit safety exclusion.',
            base='Return selected large cells to unchanged SOURCE quad corners, edge midpoints and arithmetic parent center; replace rather than cumulatively subdivide the old raised ornament.',
            child='Four children each retain the accepted higher-diagonal six-triangle roof formula.',
            height='min(.65*inherited_parent_weight*child_projected_fan_altitude, .5*actual_accepted_parent_height)',
            conformity='One midpoint per original control edge, opposite old incidences checked; neighboring original triangle split into two coplanar triangles.',
            preservation='All original control corners and unrefined native coordinates unchanged. Unrefined neighbor face indices may split while preserving their old planar surface.',
            symmetry='Canonical parent construction, actual corner-ID reflection, exact transported child ridges/parent centers, odd-reflection winding reversal.',
            scope='One local native 2x2 scale replacement, no global refinement, new ornament language, Mandelbulb, Boolean or remesh.'),
        seconds=time.perf_counter()-started, visual_success='PENDING_MATCHED_ACTUAL_RENDERS'))
    print(json.dumps(stats), flush=True)


if __name__ == '__main__':
    main()
