"""One saved-field hierarchy update and one coarser integral G7 finish.

No source checkpoint is overwritten. The saved G6 MIDDLE displacement is
lifted by the verified neutral CC stencil, then reweighted with the two saved
G7 contributions. This is contribution reweighting, not a new G1-G7 replay.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import shutil
import time

import numpy as np
from texture import build

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/fold_hierarchy_20261014/trial01')
CONTROL = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED/control_quad.npz')
MIRRORS = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07/evidence.npz')
MASK = Path('E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01/MASK.npz')
H = 9.735842284057451
CHUNK = 65536
FACES_SHA = '67109d7c7378b6cdfe82a713c74a860c98cdd53adcdce311f8612b3e6565a9ee'


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def transport_vector(delta, px, py):
    ids = np.arange(len(delta))
    both = px[py]
    rep = np.minimum(np.minimum(ids, px), np.minimum(py, both))
    result = delta[rep].copy()
    result[(ids == px[rep]) | (ids == both[rep]), 0] *= -1
    result[(ids == py[rep]) | (ids == both[rep]), 1] *= -1
    result[px == ids, 0] = 0.
    result[py == ids, 1] = 0.
    return result


def symmetry(xyz, vx, vy):
    maximum = 0.
    for start in range(0, len(xyz), CHUNK):
        ids = np.arange(start, min(start+CHUNK, len(xyz)))
        for axis, pair in ((0, vx), (1, vy)):
            reflected = xyz[pair[ids]].copy()
            reflected[:, axis] *= -1
            maximum = max(maximum, float(np.max(np.abs(xyz[ids]-reflected))))
    return maximum


def native_fan(xyz, q):
    nc, nq = len(xyz), len(q)
    out = np.empty((nc+nq, 3), xyz.dtype)
    out[:nc] = xyz
    faces = np.empty((4*nq, 3), q.dtype)
    for start in range(0, nq, CHUNK):
        stop = min(start+CHUNK, nq)
        cq = q[start:stop]
        out[nc+start:nc+stop] = xyz[cq].mean(axis=1)
        fan = faces[4*start:4*stop].reshape(-1, 4, 3)
        fan[:, :, 0] = cq
        fan[:, :, 1] = np.roll(cq, -1, axis=1)
        fan[:, :, 2] = (nc+np.arange(start, stop))[:, None]
    if ah(faces) != FACES_SHA:
        raise ValueError('Actual original G7 native fan connectivity differs.')
    return out, faces


def area_report(xyz, faces):
    minimum = float('inf')
    zero = 0
    for start in range(0, len(faces), 262144):
        p = xyz[faces[start:start+262144]]
        area = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)*.5
        if not np.isfinite(area).all():
            raise ValueError('Nonfinite native triangle area.')
        zero += int(np.count_nonzero(area <= 0))
        minimum = min(minimum, float(area.min()))
    if zero:
        raise ValueError('Degenerate native triangles: '+str(zero))
    return dict(all_finite=True, positive_area_triangles=len(faces), degenerate_triangles=zero,
                minimum_triangle_area=minimum)


def save_variant(root, label, xyz, faces, validation):
    folder = root/label
    folder.mkdir()
    path = folder/'geometry.npz'
    np.savez_compressed(path, xyz=xyz, faces=faces)
    record = dict(geometry=str(path), geometry_sha256=digest(path), xyz_sha256=ah(xyz),
                  faces_sha256=ah(faces), vertices=len(xyz), triangles=len(faces), validation=validation)
    write(folder/'VALIDATION.json', validation)
    print('SAVED', label, len(xyz), len(faces), flush=True)
    return record


def parent_weights(q, px, py, root):
    with np.load(MASK, allow_pickle=False) as saved:
        child = saved['quad_weight']
    if child.shape != (len(q),):
        raise ValueError('Existing broad support does not match G7.')
    weight = child.reshape(-1, 4).mean(axis=1, dtype=np.float64)
    initial = weight.copy()
    del child
    groups = q.reshape(-1, 4, 4)
    # These are actual G6 edge-point IDs, shared by exactly two parents.
    edge = groups[:, :, 2]-1750530
    if edge.min() != 0 or edge.max() != 3501055:
        raise ValueError('Actual G6 following-edge point range differs.')
    count = np.bincount(edge.ravel(), minlength=3501056)
    if not np.all(count == 2):
        raise ValueError('Actual coarse parent adjacency is not closed two-sided.')
    total = np.bincount(edge.ravel(), weights=np.repeat(weight, 4), minlength=3501056)
    neighbor = (total[edge]-weight[:, None]).mean(axis=1)
    weight = .65*weight+.35*neighbor
    ppx, ppy = px.reshape(-1, 4)[:, 0]//4, py.reshape(-1, 4)[:, 0]//4
    ids = np.arange(len(weight))
    rep = np.minimum(np.minimum(ids, ppx), np.minimum(ppy, ppx[ppy]))
    weight = np.clip(weight[rep], 0., 1.)
    report = dict(source_mask=str(MASK), source_sha256=digest(MASK),
                  aggregation='Mean of four actual G7 child weights per G6 parent',
                  feather='One .65*self + .35*mean_of_four_actual_edge_neighbors pass',
                  exact_actual_parent_mirror_transport=True,
                  fine_child_support_count=None,
                  parent_support_before=int(np.count_nonzero(initial)),
                  parent_support_after=int(np.count_nonzero(weight)),
                  parent_count=len(weight),
                  note='No new coarse-cell size gate or world-axis gate; support inherits the accepted broad mask.')
    np.savez_compressed(root/'PARENT_SUPPORT.npz', parent_weight=weight, source_parent_weight=initial)
    return weight, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if any((root/key).exists() for key in ('HIERARCHY', 'FINISHED', 'RECEIPT.json', 'source_snapshot_run')):
        raise FileExistsError('Earlier output is immutable; use a new trial root.')
    started = time.perf_counter()
    expected = {CONTROL: '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27',
                MIRRORS: '226c22ca83f9c71e69059d817e42140483d19a46228d66c6710170bc1ac17e21',
                MASK: 'db4b3b8f0bebd4907f25e3316cdd3a918e987bf99d941811586c365fdbf8a88a',
                root/'COMPONENTS.npz': '3d2f4c1e1b46ad1ae881bf0f2130ebf85d9587bc3c2506604bf6f0346176314c',
                root/'MIDDLE_COMPONENT.npz': '4b856cb97b111e567e97ef6c93436b87532a5a5488eefe2c9bda6e07744e833f',
                HERE/'texture.py': 'eebc604bb6e6bb70d3c8e90331ae9a02c091fb4c6ea46008dcb519c4589e2d5a'}
    for path, checksum in expected.items():
        if digest(path) != checksum:
            raise ValueError('Frozen input changed: '+str(path))
    snapshots = {}
    for name in ('run.py', 'texture.py', 'prepare.py', 'middle_lift.py'):
        source = HERE/name
        target = root/'source_snapshot_run'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[name] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    with np.load(CONTROL, allow_pickle=False) as saved:
        control = {key: saved[key] for key in saved.files}
    xyz, q = control['xyz'], control['faces']
    with np.load(MIRRORS, allow_pickle=False) as saved:
        vx, vy = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
        px, py = saved['mirror_x_face_pairs'], saved['mirror_y_face_pairs']
    with np.load(root/'COMPONENTS.npz', allow_pickle=False) as saved:
        base, linked, wide = saved['base_xyz'], saved['delta_linked'], saved['delta_wide']
        phase = saved['parent_phase_unwrapped']
    error = float(np.max(np.abs(base+linked+wide-xyz)))
    if error > 1e-12:
        raise ValueError('Prepared components do not reconstruct actual accepted bare control.')
    del base
    with np.load(root/'MIDDLE_COMPONENT.npz', allow_pickle=False) as saved:
        middle = saved['delta_middle']
    k = phase/(2*np.pi)
    p1 = np.exp(-((k-1)/.70)**4)
    p4 = np.exp(-((k-4)/.70)**4)
    primary = 1-(1-p1)*(1-p4)
    gains = {'MIDDLE': .45+.55*primary, 'LINKED': .30+.70*primary, 'WIDE': .18+.82*primary}
    delta = ((gains['MIDDLE']-1)[:, None]*middle+
             (gains['LINKED']-1)[:, None]*linked+
             (gains['WIDE']-1)[:, None]*wide)
    delta = transport_vector(delta, vx, vy)
    newxyz = xyz+delta
    if not np.isfinite(newxyz).all():
        raise ValueError('Nonfinite hierarchy output.')
    source_symmetry, result_symmetry = symmetry(xyz, vx, vy), symmetry(newxyz, vx, vy)
    if result_symmetry > max(2e-12, source_symmetry+1e-12):
        raise ValueError('Hierarchy update lost actual X/Y reflection.')
    hierarchy = dict(implementation='SAVED_COMPONENT_PARENT_HIERARCHY_V1',
        generation=7, full_G1_G7_replay=False, new_G8=False,
        component_reconstruction_maximum_error=error,
        phase_cycles_range=[float(k.min()), float(k.max())], primary_cycles_per_quadrant=[1, 4],
        primary_profile='p=1-(1-exp(-((k-1)/.70)^4))*(1-exp(-((k-4)/.70)^4)); k=saved_unwrapped_phase/(2*pi)',
        gains={'MIDDLE': '.45+.55*p', 'LINKED': '.30+.70*p', 'WIDE': '.18+.82*p'},
        gain_quantiles={key: np.quantile(value, [0, .1, .5, .9, 1]).tolist() for key, value in gains.items()},
        changed_control_vertices=int(np.count_nonzero(np.any(delta != 0, axis=1))),
        displacement_norm_quantiles=np.quantile(np.linalg.norm(delta, axis=1), [.1, .5, .9, .99, 1]).tolist(),
        source_XY_position_symmetry_error=source_symmetry, finished_XY_position_symmetry_error=result_symmetry,
        method='Actual verified neutral-CC-lifted G6 MIDDLE and actual G7 LINKED/WIDE saved coordinate contributions reweighted. Canonical actual vertex mirror delta transported without source averaging.',
        limits='Saved field contribution reweighting; later field normals are not regenerated on the new carrier. Not a full replay or a new variation pipeline. Global intersections and end morphology remain unverified.')
    np.savez_compressed(root/'HIERARCHY_STATE.npz', primary_weight=primary, delta=delta,
                        gain_middle=gains['MIDDLE'], gain_linked=gains['LINKED'], gain_wide=gains['WIDE'])
    del middle, linked, wide, delta, phase, k, p1, p4, primary, gains
    control['xyz'] = newxyz
    native, faces = native_fan(newxyz, q)
    bare_validation = dict(hierarchy=hierarchy, mesh=area_report(native, faces),
                           original_native_topology_sha256=FACES_SHA,
                           connectivity='Exact original G7 native fan indices; original topology inherited.')
    variant_h = save_variant(root, 'HIERARCHY', native, faces, bare_validation)
    np.savez_compressed(root/'HIERARCHY/control_quad.npz', **control)
    variant_h['control_quad'] = str(root/'HIERARCHY/control_quad.npz')
    variant_h['control_quad_sha256'] = digest(root/'HIERARCHY/control_quad.npz')
    del native, faces, xyz
    gc.collect()
    weight, support = parent_weights(q, px, py, root)
    print('BUILD_PARENT_TEXTURE', support['parent_support_after'], flush=True)
    native, faces, texture, state = build(newxyz, q, weight, px, py, vx, vy, H)
    if ah(faces) != FACES_SHA:
        raise ValueError('Finished native connectivity changed.')
    finished_validation = dict(hierarchy=hierarchy, texture=texture, support=support,
                               mesh=area_report(native, faces), original_native_topology_sha256=FACES_SHA,
                               self_intersection_checked=False, aesthetic_success='Requires actual rendered comparison')
    variant_f = save_variant(root, 'FINISHED', native, faces, finished_validation)
    np.savez_compressed(root/'FINISHED/texture_state.npz', **state)
    for path, checksum in expected.items():
        if digest(path) != checksum:
            raise ValueError('Frozen source changed during update: '+str(path))
    for record in snapshots.values():
        if digest(record['source']) != record['sha256'] or digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed source/snapshot changed during update.')
    receipt = dict(kind='ONE_HIERARCHY_AND_PARENT_SCALE_G7_UPDATE', date='2026-10-14',
                   source_control_path=str(CONTROL), source_control_sha256=expected[CONTROL],
                   design_source_native_path='E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01/REFINED/geometry.npz',
                   design_source_native_geometry_sha256='37549b71c997a65943fbb6416d008b748ecba4ab05898eadfea95bc994e3a710',
                   variants={'HIERARCHY': variant_h, 'FINISHED': variant_f},
                   sources={str(path): checksum for path, checksum in expected.items()}, source_snapshots=snapshots,
                   preparation_receipts={name: dict(path=str(root/name), sha256=digest(root/name))
                     for name in ('PREPARATION.json', 'MIDDLE_PREPARATION.json')},
                   hierarchy=hierarchy, texture=texture, support=support,
                   elapsed_seconds=time.perf_counter()-started,
                   scope='One fixed recipe. Original research/checkpoints immutable. Bare hierarchy and combined finished result retained separately for matched-camera evidence. No new G8, broad parameter matrix, global remesh or ornament addition.')
    write(root/'RECEIPT.json', receipt)
    print('FOLD_HIERARCHY_COMPLETE', receipt['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
