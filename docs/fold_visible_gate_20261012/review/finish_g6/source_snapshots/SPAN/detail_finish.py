"""Two bounded G06 geometry finishes of the accepted integral bulb relief.

INTEGRATED_G06 resolves the same atlas on the unchanged carrier.
RELAXED_G06 first relaxes only the G03 carrier controls by bounded Taubin
steps, then takes three inactive splits and evaluates the same attached relief.
No shading change or separate geometry is part of either operation.
"""
from pathlib import Path
import argparse
import ctypes
import gc
import hashlib
import importlib.util
import json
import shutil
from types import SimpleNamespace

import numpy as np
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree
import trimesh

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('integral_finish_bulb', HERE/'bulb_detail.py')
bulb = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(bulb)
t = bulb.study.previous.anchor.t
RELAXATION = dict(positive=.50, negative=-.53, pairs=6, maximum_carrier_shift=.04,
    material_end_limits=[.10, .90], fade_width=.08,
    carrier_stage_generation=3, graph='Uniform undirected G03 quad-edge neighbours',
    symmetry='Constructive material X/Y copy of the carrier delta after bounded relaxation')
MODES = ('INTEGRATED_G06', 'RELAXED_G06')
COUNTS = dict(control_vertices=1638402, control_quads=1638400,
    physical_vertices=3276802, physical_triangles=6553600)


def memory_state():
    """Read-only Windows physical/commit memory; no process modification."""
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)]+[
            (name, ctypes.c_ulonglong) for name in ('total_physical', 'available_physical',
            'total_commit', 'available_commit', 'total_virtual', 'available_virtual', 'reserved')]
    state = Memory(); state.length = ctypes.sizeof(state)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        raise OSError('GlobalMemoryStatusEx failed.')
    return {name: int(getattr(state, name)) for name, _ in state._fields_}


def memory_guard(minimum_bytes=8_000_000_000):
    state = memory_state()
    if state['available_physical'] < minimum_bytes:
        raise MemoryError('G06 requires 8 GB free physical memory; current bytes: '+str(state['available_physical']))
    return dict(state, required_available_physical=minimum_bytes,
        declared_native_counts=COUNTS, execution='One case and one variant at a time; chunked normals/areas')


def array_hash(value):
    value = np.asarray(value)
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def stream_control_normals(xyz, triangles, control_count, chunk=120000):
    """Angle-weighted actual native normals, accumulating only control corners.

    Equivalent to the usual native vertex-normal rule, without a full-mesh
    face-normal/face-angle cache. Fan-only render centres need no saved normal.
    """
    normals = np.zeros((control_count, 3), float)
    for start in range(0, len(triangles), chunk):
        q = triangles[start:start+chunk]
        a, b, c = xyz[q[:, 0]], xyz[q[:, 1]], xyz[q[:, 2]]
        e01, e02, e12 = b-a, c-a, c-b
        face_normal = bulb.unit(np.cross(e01, e02))
        u01, u02, u12 = bulb.unit(e01), bulb.unit(e02), bulb.unit(e12)
        cosines = (np.sum(u01*u02, axis=1), -np.sum(u01*u12, axis=1), np.sum(u02*u12, axis=1))
        for corner in range(3):
            ids = q[:, corner]; keep = ids < control_count
            angle = np.arccos(np.clip(cosines[corner], -1., 1.))
            np.add.at(normals, ids[keep], (angle[:, None]*face_normal)[keep])
    return bulb.unit(normals)


def minimum_area(xyz, triangles, chunk=120000):
    value = float('inf')
    for start in range(0, len(triangles), chunk):
        q = triangles[start:start+chunk]
        a, b, c = xyz[q[:, 0]], xyz[q[:, 1]], xyz[q[:, 2]]
        value = min(value, float(np.linalg.norm(np.cross(b-a, c-a), axis=1).min()/2))
    return value


def oriented_canonical(triangles):
    """Canonical cyclic orientation; reverse winding remains distinguishable."""
    q = np.asarray(triangles)
    first = np.argmin(q, axis=1)
    out = np.empty_like(q)
    for corner, order in ((0, [0, 1, 2]), (1, [1, 2, 0]), (2, [2, 0, 1])):
        keep = first == corner
        out[keep] = q[keep][:, order]
    order = np.lexsort((out[:, 2], out[:, 1], out[:, 0]))
    return out[order]


def native_lr_symmetry(mesh, chart, native=None):
    """Check actual native XYZ and exact oriented reflected triangle sets.

    Material correspondence supplies vertex IDs only. Positions themselves
    must reflect exactly; triangle comparison reverses winding under reflection.
    No bounding-box or inherited-symmetry shortcut is used for this check.
    """
    if native is None:
        native = t.growth.native(mesh)
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    tree = cKDTree(pchart)
    distance, pairs = tree.query(pchart*np.array([1., -1., 1.]))
    material_error = float(distance.max())
    involution = bool(np.array_equal(pairs[pairs], np.arange(len(pairs))))
    del tree, pchart, distance; gc.collect()
    xyz_error = 0.
    for start in range(0, len(pairs), 120000):
        ids = pairs[start:start+120000]
        xyz_error = max(xyz_error, float(np.linalg.norm(native.xyz[start:start+len(ids)]-
            native.xyz[ids]*np.array([-1., 1., 1.]), axis=1).max()))
    triangles = native.faces[:, :3]
    original = oriented_canonical(triangles)
    reflected = oriented_canonical(pairs[triangles[:, ::-1]])
    oriented_equal = bool(np.array_equal(original, reflected))
    return dict(passed=bool(material_error < 1e-9 and involution and xyz_error < 1e-9 and oriented_equal),
        actual_native_xyz_pair_max_error=xyz_error, material_pair_max_error=material_error,
        pair_involution=involution, reflected_oriented_native_triangle_sets_identical=oriented_equal,
        physical_vertices=len(native.xyz), physical_triangles=len(triangles))


def verify_saved_symmetry(folder):
    folder = Path(folder)
    memory_guard()
    mesh, chart, _ = t.load(folder)
    arrays = bulb.read_arrays(folder/'geometry.npz')
    receipt = native_lr_symmetry(mesh, chart, SimpleNamespace(xyz=arrays['xyz'], faces=arrays['faces']))
    path = folder/'native_symmetry.json'
    if path.exists():
        raise FileExistsError('Existing native symmetry receipt preserved: '+str(path))
    path.write_text(json.dumps(receipt, indent=2), encoding='utf8')
    return receipt


def smoothstep(value):
    value = np.clip(value, 0., 1.)
    return value*value*(3.-2.*value)


def relax_carrier(mesh, chart, recipe=RELAXATION):
    """Bounded actual XYZ relaxation; existing topology/chart/tags stay fixed."""
    original = mesh.xyz.copy()
    q = mesh.faces
    edges = np.concatenate([q[:, [0, 1]], q[:, [1, 2]], q[:, [2, 3]], q[:, [3, 0]]])
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    rows = np.r_[edges[:, 0], edges[:, 1]]; columns = np.r_[edges[:, 1], edges[:, 0]]
    degree = np.bincount(rows, minlength=len(original))
    graph = coo_matrix((1./degree[rows], (rows, columns)), shape=(len(original), len(original))).tocsr()
    lower, upper = recipe['material_end_limits']
    envelope = smoothstep((chart[:, 0]-lower)/recipe['fade_width'])*smoothstep((upper-chart[:, 0])/recipe['fade_width'])
    points = original.copy()
    for _ in range(recipe['pairs']):
        for coefficient in (recipe['positive'], recipe['negative']):
            points += coefficient*envelope[:, None]*(graph@points-points)
    delta = points-original
    magnitude = np.linalg.norm(delta, axis=1)
    delta *= np.minimum(1., recipe['maximum_carrier_shift']/np.maximum(magnitude, 1e-30))[:, None]
    existing = t.prior.helpers.existing
    existing.reflect(delta, chart, existing.symmetry(chart))
    mesh.xyz = original+delta
    fixed = (chart[:, 0] <= lower) | (chart[:, 0] >= upper)
    if not np.array_equal(mesh.xyz[fixed], original[fixed]):
        raise ValueError('Carrier relaxation moved a fixed material endpoint region.')
    return delta


def source_to_g5(source):
    mesh, chart, tags = t.load(source)
    if mesh.generation != 3:
        raise ValueError('Actual current WALL G03 parent required.')
    for _ in range(2):
        mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    return mesh, chart, tags


def build(source, mode, atlas, colonies, relief_recipe=None, relaxation_recipe=None):
    """Deterministically reconstruct one finish from the actual parent."""
    if mode not in MODES:
        raise ValueError('Unknown G06 finish mode: '+str(mode))
    recipe = bulb.VARIANTS['INTEGRATED'] if relief_recipe is None else relief_recipe
    relaxation_recipe = RELAXATION if relaxation_recipe is None else relaxation_recipe
    if mode == 'RELAXED_G06':
        mesh, chart, tags = t.load(source)
        if mesh.generation != 3 or relaxation_recipe['carrier_stage_generation'] != 3:
            raise ValueError('Final relaxed comparison requires the actual G03 carrier.')
        carrier_delta = relax_carrier(mesh, chart, relaxation_recipe)
        remaining_splits = 3
    else:
        mesh, chart, tags = source_to_g5(source)
        carrier_delta = np.zeros_like(mesh.xyz)
        remaining_splits = 1
    carrier_receipt = dict(carrier_stage_generation=int(mesh.generation), delta_sha256=array_hash(carrier_delta),
        maximum_shift=float(np.linalg.norm(carrier_delta, axis=1).max()),
        moved_controls=int((np.linalg.norm(carrier_delta, axis=1) > 1e-12).sum()),
        xyz_sha256=array_hash(mesh.xyz), chart_sha256=array_hash(chart))
    for _ in range(remaining_splits):
        mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    reference = mesh.xyz.copy()
    native = t.growth.native(mesh)
    normals = stream_control_normals(native.xyz, native.faces[:, :3], len(mesh.xyz))
    del native; gc.collect()
    delta, fields = bulb.apply_colonies(reference, chart, normals, colonies, atlas, recipe['maximum_height'], recipe)
    raw_hash = array_hash(delta)
    existing = t.prior.helpers.existing; pairs = existing.symmetry(chart)
    existing.reflect(delta, chart, pairs)
    mesh.xyz = reference+delta
    errors = []
    for axis, ids in enumerate(pairs):
        sign = np.ones(3); sign[axis] = -1
        errors.append(float(np.linalg.norm(mesh.xyz-mesh.xyz[ids]*sign, axis=1).max()))
    operation = dict(carrier_stage_generation=carrier_receipt['carrier_stage_generation'],
        reference_xyz_sha256=array_hash(reference), raw_delta_sha256=raw_hash,
        final_delta_sha256=array_hash(delta), control_xyz_sha256=array_hash(mesh.xyz),
        control_chart_sha256=array_hash(chart), control_faces_sha256=array_hash(mesh.faces),
        incoming_normals_sha256=array_hash(normals), maximum_relief=float(np.linalg.norm(delta, axis=1).max()),
        minimum_signed_relief=float(fields['height'].min()), moved_controls=int((np.linalg.norm(delta, axis=1) > 1e-12).sum()),
        control_xy_reflection_errors=errors, carrier=carrier_receipt)
    del reference, normals, delta, fields, pairs; gc.collect()
    return mesh, chart, tags, carrier_delta, operation


def save(folder, mesh, chart, tags, carrier_delta, operation, metadata):
    folder.mkdir(parents=True)
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors, generation=np.array(mesh.generation),
        surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(folder/'carrier_relaxation.npz', carrier_delta=carrier_delta)
    native = t.growth.native(mesh); triangles = native.faces[:, :3]
    area = minimum_area(native.xyz, triangles)
    counts = dict(control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
        physical_vertices=len(native.xyz), physical_triangles=len(triangles))
    finite = bool(np.isfinite(native.xyz).all())
    inherited = metadata['source_topology']['watertight'] and metadata['source_topology']['components'] == 1
    actual_symmetry = native_lr_symmetry(mesh, chart, native)
    passed = bool(finite and inherited and metadata['source_topology']['winding_consistent'] and actual_symmetry['passed'] and
        counts == COUNTS and area > 1e-14 and max(operation['control_xy_reflection_errors']) < 1e-9 and
        operation['maximum_relief'] <= .30+1e-12 and operation['carrier']['maximum_shift'] <= .04+1e-12)
    checks = dict(passed=passed, finite=finite, counts=counts, minimum_triangle_area=area,
        components=1 if inherited else None, watertight=bool(inherited),
        winding_consistent=bool(metadata['source_topology']['winding_consistent']),
        topology_scope='Inherited closed connected oriented source under three native inactive splits; no topology edits or appended geometry',
        actual_native_left_right_symmetry=actual_symmetry,
        maximum_carrier_shift=operation['carrier']['maximum_shift'], maximum_relief=operation['maximum_relief'],
        self_intersection='IGNORED_EXPLORATION_PER_USER', fabrication='NOT_CHECKED')
    np.savez_compressed(folder/'geometry.npz', xyz=native.xyz, faces=triangles)
    operation.update(native_xyz_sha256=array_hash(native.xyz), native_faces_sha256=array_hash(triangles))
    (folder/'operation_receipt.json').write_text(json.dumps(operation, indent=2), encoding='utf8')
    (folder/'native_symmetry.json').write_text(json.dumps(actual_symmetry, indent=2), encoding='utf8')
    metadata = dict(metadata, checks=checks)
    (folder/'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    print('DETAIL_G06', metadata['input_case'], metadata['candidate'], 'PASS' if passed else 'FAILED_PRESERVED',
        'carrier', checks['maximum_carrier_shift'], 'relief', checks['maximum_relief'], flush=True)
    if not passed:
        raise ValueError('G06 geometry check failed; result preserved: '+str(folder))
    return metadata


def generate(root, parent_root, integrated_root, case='SPAN', modes=MODES):
    root, parent_root, integrated_root = map(lambda p: Path(p).resolve(), (root, parent_root, integrated_root))
    if root.exists():
        raise FileExistsError('Existing G06 finish preserved: '+str(root))
    initial_memory = memory_guard()
    root.mkdir(parents=True)
    shutil.copytree(integrated_root/'atlas', root/'atlas')
    atlas = bulb.read_arrays(root/'atlas/power8.npz')
    source = parent_root/'WALL'/case/'G03'
    source_mesh, _, _ = t.load(source)
    source_native = t.growth.native(source_mesh)
    physical = trimesh.Trimesh(source_native.xyz, source_native.faces[:, :3], process=False)
    topology = dict(components=int(physical.body_count), watertight=bool(physical.is_watertight),
        winding_consistent=bool(physical.is_winding_consistent))
    del source_mesh, source_native, physical; gc.collect()
    colony_source = integrated_root/'INTEGRATED'/case/'G05/colonies.npz'
    colonies = bulb.read_arrays(colony_source)
    shutil.copy2(colony_source, root/'colonies.npz')
    receipts = []
    for mode in modes:
        guard = memory_guard()
        mesh, chart, tags, carrier_delta, operation = build(source, mode, atlas, colonies)
        metadata = dict(input_case=case, candidate=mode, source=str(source),
            source_control_sha256=bulb.digest(source/'control_quad.npz'), source_topology=topology,
            source_candidate='WALL', source_generation=3, output_generation=6, inactive_refinements=3,
            carrier_stage_generation=3 if mode == 'RELAXED_G06' else 5,
            integrated_source=str(integrated_root), atlas_sha256=bulb.digest(root/'atlas/power8.npz'),
            colonies_sha256=bulb.digest(root/'colonies.npz'), relief_recipe=bulb.VARIANTS['INTEGRATED'],
            relaxation_recipe=RELAXATION if mode == 'RELAXED_G06' else None,
            source_xyz_smoothing=mode == 'RELAXED_G06', new_relief_passes=1,
            normal_rule='Streamed actual native angle-weighted vertex normals; same colony frames and finite atlas as accepted G05',
            memory_guard=guard, operation='Optional bounded G03 geometric Taubin relaxation → three inactive splits → same attached finite-bulb relief at G06',
            replay_scope='Saved source/atlas/colonies/recipe rebuild control/native arrays; hashes record all stages')
        receipts.append(save(root/mode/case/'G06', mesh, chart, tags, carrier_delta, operation, metadata))
        del mesh, chart, tags, carrier_delta, operation; gc.collect()
    (root/'SUMMARY.json').write_text(json.dumps(dict(input_case=case, initial_memory_guard=initial_memory,
        states=receipts, passed=all(item['checks']['passed'] for item in receipts)), indent=2), encoding='utf8')
    shutil.copy2(__file__, root/'detail_finish.py')
    print('DETAIL_G06_COMPLETE', case, len(receipts), flush=True)


def replay(root, case, mode):
    """Reconstruct actual source-to-native geometry and compare all stage hashes."""
    root = Path(root); folder = root/mode/case/'G06'
    metadata = json.loads((folder/'generation.json').read_text())
    saved = json.loads((folder/'operation_receipt.json').read_text())
    if bulb.digest(Path(metadata['source'])/'control_quad.npz') != metadata['source_control_sha256']:
        raise ValueError('Actual source checkpoint hash changed.')
    memory_guard()
    mesh, chart, tags, carrier_delta, operation = build(Path(metadata['source']), mode,
        bulb.read_arrays(root/'atlas/power8.npz'), bulb.read_arrays(root/'colonies.npz'),
        metadata['relief_recipe'], metadata['relaxation_recipe'])
    native = t.growth.native(mesh)
    operation.update(native_xyz_sha256=array_hash(native.xyz), native_faces_sha256=array_hash(native.faces[:, :3]))
    equal = {key: operation[key] == value for key, value in saved.items() if key.endswith('_sha256')}
    equal['carrier_stage_hashes'] = operation['carrier'] == saved['carrier']
    equal['stored_carrier_delta'] = array_hash(bulb.read_arrays(folder/'carrier_relaxation.npz')['carrier_delta']) == operation['carrier']['delta_sha256']
    equal['actual_native_left_right_symmetry'] = native_lr_symmetry(mesh, chart, native)['passed']
    receipt = dict(input_case=case, candidate=mode, passed=all(equal.values()), checks=equal,
        scope='Actual WALL G3 → optional bounded carrier relaxation → inactive G06 → identical atlas/colonies/collars → native arrays')
    (folder/'replay.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, default=HERE.parents[1]/'output/fold_visible_gate_20261012')
    parser.add_argument('--integrated-root', type=Path, default=HERE.parents[1]/'output/fold_visible_gate_20261012/bulb_integrated')
    parser.add_argument('--case', choices=('SPAN', 'COUNTER'), default='SPAN')
    parser.add_argument('--mode', choices=MODES, default=None)
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--verify-symmetry', action='store_true')
    args = parser.parse_args()
    modes = (args.mode,) if args.mode else MODES
    if args.verify_symmetry:
        for mode in modes:
            print(json.dumps(verify_saved_symmetry(args.root/mode/args.case/'G06')), flush=True)
    elif args.replay:
        for mode in modes:
            print(json.dumps(replay(args.root, args.case, mode)), flush=True)
    else:
        generate(args.root, args.parent_root, args.integrated_root, args.case, modes)
