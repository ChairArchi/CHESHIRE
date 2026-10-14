"""One native-center accent of existing fine directional G7 facets."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import shutil
import time
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/experiments/diagonal_facet_finish_20261014/trial01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED')
ORIGINAL = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
EXPECTED = {'geometry.npz':'952386874740ca35a26dcb0a5a42cda4fb91eaa8f814f7668550d839a2b688ce',
            'control_quad.npz':'0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27'}

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''): h.update(block)
    return h.hexdigest()

def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')

def units(value):
    return value/np.maximum(np.linalg.norm(value, axis=-1, keepdims=True), 1e-30)

def correspondence(count):
    ids = np.arange(count, dtype=np.int64)
    with np.load(ORIGINAL/'evidence.npz', allow_pickle=False) as saved:
        px, py = saved['mirror_x_face_pairs'], saved['mirror_y_face_pairs']
    for pair in (px, py):
        if pair.shape != ids.shape or not np.array_equal(pair[pair], ids):
            raise ValueError('Actual face mirror involutions required.')
    if not np.array_equal(px[py], py[px]): raise ValueError('Noncommuting face pairs.')
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, px[py]))
    return ids, px, py, representative

def transport(value, ids, px, py, representative):
    value[px == ids, 0] = 0.
    value[py == ids, 1] = 0.
    result = value[representative].copy()
    result[(ids == px[representative]) | (ids == px[py[representative]]), 0] *= -1
    result[(ids == py[representative]) | (ids == px[py[representative]]), 1] *= -1
    result[px == ids, 0] = 0.
    result[py == ids, 1] = 0.
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(); root = args.root.resolve()
    if (root/'ACCENT').exists() or (root/'RECEIPT.json').exists():
        raise FileExistsError('One existing candidate preserved; no overwrite.')
    started = time.perf_counter()
    executed_sha = digest(__file__)
    snapshot = root/'source_snapshot/experiments/diagonal_facet_finish_20261014/run.py'
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists(): raise FileExistsError('Earlier generator snapshot preserved.')
    shutil.copyfile(__file__, snapshot)
    for name, expected in EXPECTED.items():
        if digest(SOURCE/name) != expected: raise ValueError('Actual selected study source changed.')
    measurement = json.loads((root/'MEASUREMENT.json').read_text(encoding='utf8'))
    with np.load(root/'MASK.npz', allow_pickle=False) as mask:
        weight, flat = mask['quad_weight'], mask['flat_quads']
    if not np.isfinite(weight).all() or weight.min() < 0 or weight.max() > 1:
        raise ValueError('Finite source weights in [0,1] required.')
    if (measurement['source_native_geometry_sha256'] != EXPECTED['geometry.npz'] or
            measurement['source_control_sha256'] != EXPECTED['control_quad.npz']):
        raise ValueError('Measured mask belongs to a different source.')
    with np.load(SOURCE/'control_quad.npz', allow_pickle=False) as saved:
        corner, quad, chart = saved['xyz'], saved['faces'], saved['chart']
    nq, nc = len(quad), len(corner)
    if weight.shape != (nq,) or flat.shape != (nq,) or flat.dtype != np.bool_:
        raise ValueError('Fixed source-based fine mask required.')
    ids, px, py, representative = correspondence(nq)
    if not np.array_equal(flat, flat[px]) or not np.array_equal(flat, flat[py]):
        raise ValueError('Actual flat mask must be symmetric.')
    if not np.array_equal(weight, weight[px]) or not np.array_equal(weight, weight[py]):
        raise ValueError('Actual scalar weight must be symmetric.')
    chosen = np.flatnonzero(flat & (weight > 0))
    if not len(chosen): raise ValueError('No source fine pattern selected.')
    delta = np.zeros((nq, 3), dtype=np.float64)
    rejected = np.zeros(nq, dtype=bool)
    minarea, mincos, maxangle = float('inf'), 1., 0.
    for start in range(0, len(chosen), 32768):
        qid = chosen[start:start+32768]
        p = corner[quad[qid]]
        center = p.mean(axis=1)
        edge = np.roll(p, -1, axis=1)-p
        length = np.linalg.norm(edge, axis=2)
        normals = np.cross(edge, center[:, None, :]-p)
        normal = units(normals.sum(axis=1))
        signed = np.einsum('nki,ni->nk', normals, normal)
        altitude = (signed/np.maximum(length, 1e-30)).min(axis=1)
        longpair = (length[:, 1]+length[:, 3] > length[:, 0]+length[:, 2]).astype(np.int64)
        row = np.arange(len(qid))
        # Choose one of the two long edges by inherited material angular
        # direction (axial material coordinate resolves exact angular ties).
        material = chart[quad[qid]]
        material_edges = (material+np.roll(material, -1, axis=1))*.5
        a, b = material_edges[row, longpair], material_edges[row, longpair+2]
        theta_a = np.arctan2(np.abs(a[:, 2]), np.abs(a[:, 1]))
        theta_b = np.arctan2(np.abs(b[:, 2]), np.abs(b[:, 1]))
        select_b = (theta_b > theta_a) | ((theta_b == theta_a) & (b[:, 0] > a[:, 0]))
        edge_id = longpair+2*select_b
        middle = (p+np.roll(p, -1, axis=1))*.5
        tangent = middle[row, edge_id]-center
        tangent -= np.einsum('ni,ni->n', tangent, normal)[:, None]*normal
        tangent = units(tangent)
        scale = length.min(axis=1)*weight[qid]
        move = scale[:, None]*(.07*normal+.10*tangent)
        norm = np.linalg.norm(move, axis=1)
        move *= np.minimum(1., .20*altitude/np.maximum(norm, 1e-30))[:, None]
        safe = (signed > 0).all(axis=1) & (altitude > 0) & np.isfinite(move).all(axis=1)
        rejected[qid[~safe]] = True
        move[~safe] = 0
        delta[qid] = move
    # Transport one canonical displacement per source correspondence orbit.
    delta = transport(delta, ids, px, py, representative)
    rejected = rejected[representative] | rejected[px[representative]] | rejected[py[representative]] | rejected[px[py[representative]]]
    delta[rejected] = 0
    # One deterministic safety rejection per orbit, never a parameter retry.
    bad = np.zeros(nq, dtype=bool)
    for start in range(0, len(chosen), 32768):
        qid = chosen[start:start+32768]
        p = corner[quad[qid]]; center = p.mean(axis=1)
        edge = np.roll(p, -1, axis=1)-p
        before = np.cross(edge, center[:, None, :]-p)
        after = np.cross(edge, (center+delta[qid])[:, None, :]-p)
        base = units(before.sum(axis=1))
        signed = np.einsum('nki,ni->nk', after, base)
        cosine = np.sum(before*after, axis=2)/np.maximum(np.linalg.norm(before, axis=2)*np.linalg.norm(after, axis=2), 1e-30)
        bad[qid] = (signed <= 0).any(axis=1) | (cosine <= 0).any(axis=1) | ~np.isfinite(after).all(axis=(1, 2))
    bad = bad[representative] | bad[px[representative]] | bad[py[representative]] | bad[px[py[representative]]]
    delta[bad] = 0
    changed = np.flatnonzero(np.any(delta != 0, axis=1))
    if not len(changed): raise ValueError('Safe accent is empty.')
    for start in range(0, len(changed), 32768):
        qid = changed[start:start+32768]; p = corner[quad[qid]]; center = p.mean(axis=1)
        edge = np.roll(p, -1, axis=1)-p
        before = np.cross(edge, center[:, None, :]-p)
        after = np.cross(edge, (center+delta[qid])[:, None, :]-p)
        areas = np.linalg.norm(after, axis=2)*.5
        cosine = np.sum(before*after, axis=2)/np.maximum(np.linalg.norm(before, axis=2)*np.linalg.norm(after, axis=2), 1e-30)
        minarea = min(minarea, float(areas.min())); mincos = min(mincos, float(cosine.min()))
        maxangle = max(maxangle, float(np.rad2deg(np.arccos(np.clip(cosine, -1, 1))).max()))
        if minarea <= 0 or mincos <= 0: raise ValueError('Changed native fan failed.')
    symmetry = {}
    for label, axis, pair in (('x', 0, px), ('y', 1, py)):
        reflected = delta[pair].copy(); reflected[:, axis] *= -1
        symmetry[label] = float(np.linalg.norm(delta-reflected, axis=1).max())
        if symmetry[label] > 1e-12: raise ValueError('Accent reflection failed.')
    folder = root/'ACCENT'; folder.mkdir()
    np.savez_compressed(folder/'native_center_delta.npz', quad_ids=changed, delta=delta[changed])
    with np.load(SOURCE/'geometry.npz', allow_pickle=False) as saved:
        native, faces = saved['xyz'], saved['faces']
    if not np.array_equal(native[:nc], corner) or len(native) != nc+nq:
        raise ValueError('Actual source native/control association differs.')
    for start in range(0, nq, 65536):
        end = min(nq, start+65536)
        if not np.array_equal(native[nc+start:nc+end], corner[quad[start:end]].mean(axis=1)):
            raise ValueError('Source is not the recorded arithmetic fan.')
    corner_hash = ah(native[:nc])
    native[nc:] += delta
    if ah(native[:nc]) != corner_hash or not np.isfinite(native).all():
        raise ValueError('Control corners changed or nonfinite native finish.')
    xyz_hash, face_hash = ah(native), ah(faces)
    geometry = folder/'geometry.npz'; np.savez_compressed(geometry, xyz=native, faces=faces)
    stats = dict(selected_flat_quads=int(flat.sum()), changed_centers=len(changed),
        unchanged_control_corners=nc, changed_control_corners=0, added_vertices=0, added_triangles=0,
        safety_rejected_quads=int(np.count_nonzero((rejected | bad) & flat)),
        maximum_delta=float(np.linalg.norm(delta[changed], axis=1).max()),
        rms_changed_delta=float(np.sqrt(np.mean(np.sum(delta[changed]**2, axis=1)))),
        minimum_changed_triangle_area=minarea, minimum_old_new_normal_cosine=mincos,
        maximum_old_new_normal_angle_degrees=maxangle, displacement_reflection_residual=symmetry)
    recipe = dict(stage='EXPLICIT_NATIVE_FINISH_NOT_CONTROL_SUBDIVISION', source_growth_generation=7,
        added_G8=False, input='User-selected REVISED saved native body; original design baseline retained separately.',
        selection='One measured source-based fine anisotropic warped-cell mask; identical selective shading before/after.',
        displacement='weight*min_edge*(.07*source_fan_normal+.10*short_tangent_toward_selected_long_edge)',
        cap='Combined displacement <= .20 minimum positive source fan altitude.',
        direction='Choose long-edge side by increasing inherited material theta; exact ties increasing material t. Canonical face-orbit transport.',
        safety='One orbit-wide rejection for nonpositive baseline/projected fan area or nonpositive old/new triangle normal dot. No retuning.',
        control='Source control_quad.npz unchanged, referenced not copied. Finished native centers are no longer arithmetic quad centers.',
        topology='Exact source native triangle indices; inherited connectivity. No new components, ornaments, remesh or Boolean.',
        limits='No global self-intersection/fabrication certificate; local fine-cell native finish is not automatically carried by a future control subdivision.')
    after_hashes = {name:digest(SOURCE/name) for name in EXPECTED}
    if after_hashes != EXPECTED: raise ValueError('Study source changed.')
    if digest(__file__) != executed_sha or digest(snapshot) != executed_sha:
        raise ValueError('Executing generator source bytes changed.')
    receipt = dict(date='2026-10-14', timezone='Asia/Seoul', source_native_path=str(SOURCE/'geometry.npz'),
        source_native_geometry_sha256=EXPECTED['geometry.npz'], source_control_path=str(SOURCE/'control_quad.npz'),
        source_control_sha256=EXPECTED['control_quad.npz'], source_hashes_after=after_hashes,
        mask_path=str(root/'MASK.npz'), mask_sha256=digest(root/'MASK.npz'),
        measurement_path=str(root/'MEASUREMENT.json'), measurement_sha256=digest(root/'MEASUREMENT.json'),
        geometry_code_sha256={'experiments/diagonal_facet_finish_20261014/run.py':executed_sha},
        variants={'ACCENT':dict(geometry=str(geometry), geometry_sha256=digest(geometry),
            xyz_sha256=xyz_hash, faces_sha256=face_hash, vertices=len(native), triangles=len(faces),
            native_center_delta=str(folder/'native_center_delta.npz'),
            native_center_delta_sha256=digest(folder/'native_center_delta.npz'))},
        statistics=stats, recipe=recipe, seconds=time.perf_counter()-started, visual_success='PENDING_MATCHED_RENDER')
    write(root/'RECEIPT.json', receipt)
    print(json.dumps(stats), flush=True)

if __name__ == '__main__': main()
