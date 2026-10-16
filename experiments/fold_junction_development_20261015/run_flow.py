"""Axial end reconnection and recursive coupled relief on NESTED02 ancestry.

The current mature G7 is the geometric reference at every scale. Only a
displacement is prolonged; the old surface's fine residuals are never averaged.
No new G8 or independent ornament mesh is introduced.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
ANCESTRY = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
BASE_RECEIPT_SHA = 'ab212bf9222980a25cb6d0c5ca31aa82ad0fe5f48b64864d9ed8e8d5fbb02524'
BASE_NATIVE_SHA = 'cde95d13f64d86739ac25e134e67024533d6be4fafec7a5d4c7a46896b65403e'
CHUNK = 65536


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def recover(parent, child):
    nv, ne = len(parent)+2, 2*len(parent)
    layout = child.reshape(-1, 4, 4)
    if not np.array_equal(layout[:, :, 1], parent):
        raise ValueError('Actual old-corner ancestry differs.')
    following = layout[:, :, 2]-nv
    if not (np.all(layout[:, :, 3] == (nv+ne+np.arange(len(parent)))[:, None])
            and np.array_equal(layout[:, :, 0]-nv, np.roll(following, 1, axis=1))):
        raise ValueError('Actual V/E/F birth correspondence differs.')
    a, b = parent, np.roll(parent, -1, axis=1)
    endpoints = np.stack([np.minimum(a, b), np.maximum(a, b)], axis=-1)
    edges = np.full((ne, 2), -1, np.int64)
    edges[following.ravel()] = endpoints.reshape(-1, 2)
    if (np.any(edges < 0) or not np.all(np.bincount(following.ravel(), minlength=ne) == 2)
            or not np.array_equal(edges[following], endpoints)):
        raise ValueError('Actual shared edge correspondence differs.')
    degree = np.bincount(edges.ravel(), minlength=nv)
    return edges, following, degree


def carry(value, edges, faces):
    return np.concatenate([value, value[edges].mean(axis=1), value[faces].mean(axis=1)])


def neutral_delta(value, faces, edges, following, degree):
    """Completed-face CC stencil on displacement only, using actual birth IDs."""
    nv, ne = len(value), len(edges)
    face = value[faces].mean(axis=1)
    edge_sum = np.column_stack([np.bincount(following.ravel(),
        weights=np.repeat(face[:, k], 4), minlength=ne) for k in range(3)])
    edge = (edge_sum+value[edges[:, 0]]+value[edges[:, 1]])/4.
    fbar = np.column_stack([np.bincount(faces.ravel(),
        weights=np.repeat(face[:, k], 4), minlength=nv) for k in range(3)])/degree[:, None]
    midpoint = value[edges].mean(axis=1)
    rbar = np.column_stack([np.bincount(edges.ravel(),
        weights=np.repeat(midpoint[:, k], 2), minlength=nv) for k in range(3)])/degree[:, None]
    vertex = (fbar+2*rbar+(degree[:, None]-3)*value)/degree[:, None]
    return np.concatenate([vertex, edge, face])


def reflect_delta(delta, px, py):
    ids = np.arange(len(delta))
    both = px[py]
    rep = np.minimum(np.minimum(ids, px), np.minimum(py, both))
    result = delta[rep].copy()
    result[(ids == px[rep]) | (ids == both[rep]), 0] *= -1
    result[(ids == py[rep]) | (ids == both[rep]), 1] *= -1
    result[px == ids, 0] = 0.
    result[py == ids, 1] = 0.
    return result


def fan(xyz, q):
    nv, nf = len(xyz), len(q)
    vertices = np.empty((nv+nf, 3), xyz.dtype)
    vertices[:nv] = xyz
    triangles = np.empty((4*nf, 3), np.int64)
    minimum = float('inf')
    for start in range(0, nf, CHUNK):
        stop = min(start+CHUNK, nf)
        block = q[start:stop]
        vertices[nv+start:nv+stop] = xyz[block].mean(axis=1)
        f = triangles[4*start:4*stop].reshape(-1, 4, 3)
        f[:, :, 0], f[:, :, 1] = block, np.roll(block, -1, axis=1)
        f[:, :, 2] = (nv+np.arange(start, stop))[:, None]
        p = vertices[f.reshape(-1, 3)]
        area = .5*np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)
        if not np.isfinite(area).all() or np.any(area <= 0):
            raise ValueError('Nonfinite or degenerate native triangles.')
        minimum = min(minimum, float(area.min()))
    return vertices, triangles, dict(finite=True, degenerate_triangles=0, minimum_triangle_area=minimum)


def save(root, label, xyz, quads, validation):
    folder = root/label
    folder.mkdir()
    vertices, triangles, area = fan(xyz, quads)
    path = folder/'geometry.npz'
    np.savez_compressed(path, xyz=vertices, faces=triangles)
    record = dict(geometry=str(path), geometry_sha256=digest(path), xyz_sha256=ah(vertices),
        faces_sha256=ah(triangles), vertices=len(vertices), triangles=len(triangles),
        validation=dict(validation, native_area=area))
    write(folder/'VALIDATION.json', record['validation'])
    del vertices, triangles
    gc.collect()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--level', type=int, choices=(4, 5, 6, 7), default=7)
    parser.add_argument('--strength', type=float, default=1.)
    parser.add_argument('--detail-gain', type=float, default=1.)
    parser.add_argument('--reference', action='store_true', help='Save same ancestry-sampled baseline for preview.')
    args = parser.parse_args()
    root = args.root.resolve()
    if root.exists():
        raise FileExistsError('Earlier trial remains immutable; select a new root.')
    started = time.perf_counter()
    receipt_path = BASE/'RECEIPT.json'
    if digest(receipt_path) != BASE_RECEIPT_SHA:
        raise ValueError('Immutable NESTED02 source receipt changed.')
    base_receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    source = Path(base_receipt['variants']['NESTED']['control_quad'])
    if digest(source) != base_receipt['variants']['NESTED']['control_quad_sha256']:
        raise ValueError('Immutable NESTED02 controls changed.')
    print('LOAD mature NESTED02 coordinates and actual G3-G7 ancestry', flush=True)
    with np.load(source, allow_pickle=False) as data:
        baseline, q7 = data['xyz'], data['faces']
    topology = {7:q7}
    for g in (6, 5, 4, 3):
        topology[g] = topology[g+1].reshape(-1, 4, 4)[:, :, 1].copy()
    with np.load(ANCESTRY/'G04_NEUTRAL/control_quad.npz', allow_pickle=False) as data:
        chart4, actual_q4 = data['chart'], data['faces']
    if not np.array_equal(topology[4], actual_q4):
        raise ValueError('Mature G7 ancestry does not match actual G4 source.')
    del actual_q4
    with np.load(ANCESTRY/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as data:
        body_faces4 = np.repeat(data['face_event_ids'] == 0, 4)
    with np.load(ANCESTRY/'G07_SURFACE/evidence.npz', allow_pickle=False) as data:
        px, py = data['mirror_x_vertex_pairs'], data['mirror_y_vertex_pairs']
    root.mkdir(parents=True)
    snapshots = {}
    code = [Path(__file__).resolve(), HERE/'axial_reconnect_v2.py', HERE/'axial_reconnect.py',
            HERE/'coupled_flow_detail.py']
    for path in code:
        target = root/'source_snapshot_run'/path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[path.name] = dict(source=str(path), snapshot=str(target), sha256=digest(path))
    reconnect = module('new_axial_end_reconnect', HERE/'axial_reconnect_v2.py')
    relief = module('new_recursive_coupled_detail', HERE/'coupled_flow_detail.py')
    q4, nv4 = topology[4], len(topology[4])+2
    height = float(np.ptp(baseline[:, 2]))
    print('RECONNECT actual inverted SOURCE-body ends; preserve every radial X/Y coordinate', flush=True)
    delta, axial_meta = reconnect.build(baseline[:nv4], q4, chart4,
        body_faces4, {'X':px[:nv4], 'Y':py[:nv4]}, strength=args.strength)
    np.savez_compressed(root/'AXIAL_STATE.npz', displacement=delta)
    # True incoming normals and local edges at every level drive coupled detail.
    degree4 = np.bincount(q4.ravel(), minlength=nv4)
    support = np.bincount(q4.ravel(), weights=np.repeat(body_faces4.astype(float), 4),
        minlength=nv4)/degree4
    with np.load(ANCESTRY/'G06_MIDDLE/evidence.npz', allow_pickle=False) as data:
        phase = data['directional_phase'][:nv4].copy()
    details = []
    for generation in range(4, args.level):
        parent, child = topology[generation], topology[generation+1]
        nv = len(parent)+2
        print('COUPLED RELIEF ancestry G'+str(generation)+' -> G'+str(generation+1), flush=True)
        edges, following, degree = recover(parent, child)
        prolonged = neutral_delta(delta, parent, edges, following, degree)
        if args.detail_gain:
            addition, metadata = relief.split_detail(baseline[:nv]+delta, parent, child,
                edges, degree, phase, support, height,
                mirror_pairs={'X':px[:len(prolonged)], 'Y':py[:len(prolonged)]},
                gain=args.detail_gain, phase_multiplier=2.**(generation-3))
            if addition.shape != prolonged.shape:
                raise ValueError('Recursive coupling birth count differs.')
            prolonged += addition
            details.append(metadata)
            del addition
        delta = reflect_delta(prolonged, px[:len(prolonged)], py[:len(prolonged)])
        phase, support = carry(phase, edges, parent), carry(support, edges, parent)
        del edges, following, degree, prolonged
        gc.collect()
    n = len(topology[args.level])+2
    output = baseline[:n]+delta
    symmetry = 0.
    for start in range(0, n, CHUNK):
        ids = np.arange(start, min(start+CHUNK, n))
        for axis, pairs in ((0, px), (1, py)):
            partner = output[pairs[ids]].copy()
            partner[:, axis] *= -1
            symmetry = max(symmetry, float(np.max(np.abs(output[ids]-partner))))
    if not np.isfinite(output).all() or symmetry > 2e-12:
        raise ValueError('Output finite/symmetry failed: '+str(symmetry))
    validation = dict(axial_reconnection=axial_meta, coupled_detail=details,
        output_XY_position_symmetry_error=symmetry, displacement_max=float(np.linalg.norm(delta,axis=1).max()),
        unchanged_native_topology=True, self_intersection_checked=False,
        visual_success='Pending matched render; not inferred from validity.',
        source_residuals_retained=True, source_XYZ_averaged=False,
        generation=args.level, is_ancestry_sampling_preview=args.level<7)
    variants = {'DEVELOPED':save(root, 'DEVELOPED', output, topology[args.level], validation)}
    if args.level == 7:
        print('SAVE complete G7 control with all original associations', flush=True)
        with np.load(source, allow_pickle=False) as data:
            control = {key:data[key] for key in data.files if key != 'xyz'}
        control['xyz'] = output
        cp = root/'DEVELOPED/control_quad.npz'
        np.savez_compressed(cp, **control)
        variants['DEVELOPED'].update(control_quad=str(cp), control_quad_sha256=digest(cp))
        del control
    if args.reference:
        variants['REFERENCE'] = save(root, 'REFERENCE', baseline[:n], topology[args.level],
            dict(source='Exact mature NESTED02 old-ID ancestry sampling, no redesign.',
                 generation=args.level, is_ancestry_sampling_preview=args.level<7))
    for record in snapshots.values():
        if digest(record['source']) != record['sha256'] or digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed code changed during trial.')
    if digest(source) != base_receipt['variants']['NESTED']['control_quad_sha256']:
        raise ValueError('Immutable source controls changed during trial.')
    receipt = dict(kind='AXIAL_END_RECONNECTION_AND_RECURSIVE_COUPLED_RELIEF', date='2026-10-15',
        source_native_path=str(BASE/'NESTED/geometry.npz'), source_native_geometry_sha256=BASE_NATIVE_SHA,
        comparison_source_native_path=str(BASE/'NESTED/geometry.npz'), comparison_source_native_geometry_sha256=BASE_NATIVE_SHA,
        source_control=str(source), source_control_sha256=digest(source), source_receipt=str(receipt_path),
        source_receipt_sha256=BASE_RECEIPT_SHA, source_snapshots=snapshots,
        variants=variants, generation=args.level, new_G8=False, added_subdivision_passes=0,
        strength=args.strength, detail_gain=args.detail_gain, axial_reconnection=axial_meta,
        coupled_detail=details, elapsed_seconds=time.perf_counter()-started,
        scope='Mature accepted G7 geometry retained with its original fine residuals. A localized material-meridian Z redistribution repairs inherited inverted ends without changing radial coordinates. The new offset detail is recursively completed-face coupled over existing G4-G7 birth IDs. No full G0-G7 replay, no added topology, no blanket source smoothing, no exact reconstruction of unpublished reference systems.')
    write(root/'RECEIPT.json', receipt)
    print('DEVELOPMENT_COMPLETE', receipt['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
