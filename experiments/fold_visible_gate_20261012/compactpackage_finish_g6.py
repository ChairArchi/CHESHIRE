"""Compact exact replay of one selected G06 finish on exactly two inputs.

This package is separate from the immutable G05 comparison. It retains atlas,
colony frames, recipes and operation receipts, while recording every omitted
control/native/carrier array hash. Verification uses the packaged WALL G03
parents only and explicitly checks actual native reflection and mesh topology.
Run heavy replay only when other G06 generation/render processes are idle.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASES = ('SPAN', 'COUNTER')
MODES = ('INTEGRATED_G06', 'RELAXED_G06')
FILES = ('control_quad.npz', 'geometry.npz', 'carrier_relaxation.npz')
COUNTS = dict(control_vertices=1638402, control_quads=1638400,
    physical_vertices=3276802, physical_triangles=6553600)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def array_hashes(data):
    return {key: dict(shape=list(value.shape), dtype=value.dtype.str,
        sha256=hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest())
        for key, value in data.items()}


def file_array_hashes(path):
    # Read/hash one member at a time; do not retain a second high-resolution mesh.
    with np.load(path, allow_pickle=False) as data:
        return {key: array_hashes({key: data[key]})[key] for key in data.files}


def load_finish():
    spec = importlib.util.spec_from_file_location('compact_selected_finish_g6', HERE/'detail_finish.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata_identity(metadata, mode, case):
    if (mode not in MODES or case not in CASES or metadata['candidate'] != mode or
        metadata['input_case'] != case or metadata['source_generation'] != 3 or
        metadata['output_generation'] != 6 or metadata['inactive_refinements'] != 3 or
        metadata['source_candidate'] != 'WALL'):
        raise ValueError('Exactly the selected mode/case and WALL G03 to G06 recipe are required.')
    relaxed = mode == 'RELAXED_G06'
    stage = metadata.get('carrier_stage_generation', 5 if not relaxed else None)
    if stage != (3 if relaxed else 5) or bool(metadata['source_xyz_smoothing']) != relaxed:
        raise ValueError('Preliminary G05 relaxation is excluded; selected relaxation must act on G03.')
    recipe = metadata['relaxation_recipe']
    if relaxed and (recipe is None or recipe.get('carrier_stage_generation') != 3):
        raise ValueError('Saved explicit G03 carrier relaxation recipe required.')
    if not relaxed and recipe is not None:
        raise ValueError('Unchanged carrier mode cannot contain a relaxation recipe.')
    if metadata['relief_recipe']['maximum_height'] > .30 or (relaxed and recipe['maximum_carrier_shift'] > .04):
        raise ValueError('Selected finish exceeds the declared .30 relief/.04 carrier bounds.')
    return stage


def normalize_operation(saved, mode):
    """Declare the historical raw-G06 carrier key spelling without changing data."""
    saved = dict(saved)
    carrier = dict(saved['carrier'])
    legacy = 'g5_delta_sha256' in carrier
    if legacy:
        if mode != 'INTEGRATED_G06':
            raise ValueError('Historical G05-relaxed pilot is excluded.')
        aliases = dict(g5_delta_sha256='delta_sha256', maximum_g5_shift='maximum_shift',
            moved_g5_controls='moved_controls', g5_xyz_sha256='xyz_sha256', g5_chart_sha256='chart_sha256')
        carrier = {aliases.get(key, key): value for key, value in carrier.items()}
        carrier['carrier_stage_generation'] = 5
        saved['carrier_stage_generation'] = 5
    saved['carrier'] = carrier
    return saved, legacy


def colony_source_provenance(colonies, source_native):
    ids, bary = colonies['primary_source_triangle_ids'], colonies['primary_source_barycentric']
    triangles = source_native.faces[:, :3]
    reconstructed = np.einsum('ni,nij->nj', bary, source_native.xyz[triangles[ids]])
    primary = colonies['levels'] == 0
    secondary = colonies['levels'] == 1
    errors = dict(primary_native_reconstruction_max_error=float(np.max(np.abs(
        reconstructed-colonies['primary_source_xyz']), initial=0.)),
        primary_centres_max_error=float(np.max(np.abs(colonies['centres'][primary]-
        colonies['primary_source_xyz']), initial=0.)), secondary_native_centres_max_error=float(np.max(np.abs(
        colonies['centres'][secondary]-source_native.xyz[colonies['native_vertex_ids'][secondary]]), initial=0.)))
    errors['passed'] = bool(primary.any() and secondary.any() and max(errors.values()) < 1e-12)
    return errors


def native_topology(xyz, triangles, chunk=120000):
    """Actual edge incidence, winding and connectivity, using bounded arrays.

    Each directed edge becomes a packed uint64 key. Sorted pairs must have
    opposite directions and exactly two incidences. Connectivity then uses the
    actual unique native edges, including isolated vertices in the graph size.
    Self-intersections are deliberately outside this combinatorial check.
    """
    xyz, triangles = np.asarray(xyz), np.asarray(triangles)
    count = len(xyz)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or triangles.ndim != 2 or
        triangles.shape[1] != 3 or not count or not len(triangles)):
        raise ValueError('Nonempty native XYZ and triangle arrays required.')
    if count >= 2**31 or 2*count*count >= 2**64:
        raise ValueError('Native mesh exceeds this declared packed-edge verifier capacity.')
    if triangles.dtype.kind not in 'iu' or triangles.min() < 0 or triangles.max() >= count:
        raise ValueError('Native triangle indices are invalid.')
    keys = np.empty(len(triangles)*3, np.uint64)
    degenerate_edge = False
    for start in range(0, len(triangles), chunk):
        q = triangles[start:start+chunk]
        for corner in range(3):
            left, right = q[:, corner], q[:, (corner+1) % 3]
            degenerate_edge |= bool(np.any(left == right))
            lo = np.minimum(left, right).astype(np.uint64)
            hi = np.maximum(left, right).astype(np.uint64)
            keys[3*start+corner:3*(start+len(q)):3] = 2*(lo*np.uint64(count)+hi)+(left > right)
    keys.sort()
    even = len(keys) % 2 == 0
    opposite_pairs = bool(even and np.array_equal(keys[1::2], keys[::2]+np.uint64(1)))
    if not opposite_pairs or degenerate_edge:
        del keys
        return dict(passed=False, closed_oriented_edge_incidence=False,
            degenerate_edges=degenerate_edge, components=None, physical_vertices=count,
            physical_triangles=len(triangles))
    undirected = keys[::2]//np.uint64(2)
    unique_pairs = bool(len(undirected) < 2 or np.all(undirected[1:] != undirected[:-1]))
    del keys
    rows = (undirected//np.uint64(count)).astype(np.int32)
    columns = (undirected % np.uint64(count)).astype(np.int32)
    edge_count = len(undirected)
    del undirected
    graph = coo_matrix((np.ones(edge_count, np.uint8), (rows, columns)), shape=(count, count)).tocsr()
    del rows, columns
    components = int(connected_components(graph, directed=False, return_labels=False))
    del graph
    finite = bool(np.isfinite(xyz).all())
    return dict(passed=bool(finite and unique_pairs and components == 1),
        finite=finite, closed_oriented_edge_incidence=bool(opposite_pairs and unique_pairs),
        degenerate_edges=degenerate_edge, components=components, unique_native_edges=edge_count,
        euler_characteristic=count-edge_count+len(triangles), physical_vertices=count,
        physical_triangles=len(triangles), scope='Actual native edge incidence, orientation and connectivity; self-intersections excluded')


def validate_assets(destination, receipt):
    copied = receipt['copied_assets']
    if not copied or len({item['path'] for item in copied}) != len(copied):
        raise ValueError('Nonempty unique copied-asset inventory required.')
    for item in copied:
        path = (destination/item['path']).resolve()
        if (not path.is_relative_to(destination) or not path.is_file() or
            path.stat().st_size != item['bytes'] or sha(path) != item['sha256']):
            raise ValueError('Missing or changed compact G06 asset: '+item['path'])
    mode = receipt['selected_mode']
    expected = receipt['expected_original_arrays']
    if mode not in MODES or set(expected) != set(CASES):
        raise ValueError('Exactly one selected G06 mode and both SPAN/COUNTER cases are required.')
    for case in CASES:
        if set(expected[case]) != set(FILES):
            raise ValueError('Complete control/native/carrier array hash inventory required: '+case)
    return mode, expected


def verify(destination, progress=False):
    destination = Path(destination).resolve()
    receipt = json.loads((destination/'COPY_RECEIPT.json').read_text(encoding='utf8'))
    mode, expected = validate_assets(destination, receipt)
    metadata_by_case = {case: json.loads((destination/mode/case/'G06/generation.json').read_text(encoding='utf8'))
        for case in CASES}
    for case, metadata in metadata_by_case.items():
        metadata_identity(metadata, mode, case)
    if any(metadata_by_case['SPAN'][key] != metadata_by_case['COUNTER'][key]
        for key in ('relief_recipe', 'relaxation_recipe')):
        raise ValueError('Both inputs must use identical saved relief and carrier recipes.')
    finish = load_finish()
    atlas = finish.bulb.read_arrays(destination/'atlas/power8.npz')
    records = []
    for case in CASES:
        guard = finish.memory_guard()
        folder = destination/mode/case/'G06'
        metadata = metadata_by_case[case]
        stage = metadata_identity(metadata, mode, case)
        source = destination.parent/'WALL'/case/'G03'
        if sha(source/'control_quad.npz') != metadata['source_control_sha256']:
            raise ValueError('Packaged actual WALL parent differs: '+case)
        if sha(destination/'atlas/power8.npz') != metadata['atlas_sha256'] or sha(folder/'colonies.npz') != metadata['colonies_sha256']:
            raise ValueError('Saved G06 atlas or colony frames differ: '+case)
        colonies = finish.bulb.read_arrays(folder/'colonies.npz')
        source_mesh, _, _ = finish.t.load(source)
        source_native = finish.t.growth.native(source_mesh)
        source_frames = colony_source_provenance(colonies, source_native)
        source_topology = native_topology(source_native.xyz, source_native.faces[:, :3])
        del source_mesh, source_native
        gc.collect()
        mesh, chart, tags, carrier_delta, operation = finish.build(source, mode, atlas, colonies,
            relief_recipe=metadata['relief_recipe'], relaxation_recipe=metadata['relaxation_recipe'])
        native = finish.t.growth.native(mesh)
        operation.update(native_xyz_sha256=finish.array_hash(native.xyz),
            native_faces_sha256=finish.array_hash(native.faces[:, :3]))
        saved = json.loads((folder/'operation_receipt.json').read_text(encoding='utf8'))
        normalized_saved, legacy = normalize_operation(saved, mode)
        operation_equal = operation == normalized_saved
        carrier_keys = list(expected[case]['carrier_relaxation.npz'])
        if len(carrier_keys) != 1 or carrier_keys[0] not in ('carrier_delta', 'g5_delta'):
            raise ValueError('Unexpected carrier array inventory: '+case)
        if carrier_keys[0] == 'g5_delta' and not legacy:
            raise ValueError('Historical carrier-array spelling lacks its explicit legacy receipt.')
        actual = {'control_quad.npz': dict(xyz=mesh.xyz, faces=mesh.faces, chart=chart,
            classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
            generation=np.array(mesh.generation), surface=np.array(mesh.surface), memory=tags),
            'geometry.npz': dict(xyz=native.xyz, faces=native.faces[:, :3]),
            'carrier_relaxation.npz': {carrier_keys[0]: carrier_delta}}
        exact = {name: array_hashes(data) == expected[case][name] for name, data in actual.items()}
        counts = dict(control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
            physical_vertices=len(native.xyz), physical_triangles=len(native.faces))
        symmetry = finish.native_lr_symmetry(mesh, chart, native)
        gc.collect()
        topology = native_topology(native.xyz, native.faces[:, :3])
        minimum_area = finish.minimum_area(native.xyz, native.faces[:, :3])
        relief_bound = float(metadata['relief_recipe']['maximum_height'])
        carrier_bound = float(metadata['relaxation_recipe']['maximum_carrier_shift']) if mode == 'RELAXED_G06' else 0.
        bounds = bool(operation['maximum_relief'] <= relief_bound+1e-12 and
            operation['carrier']['maximum_shift'] <= carrier_bound+1e-12)
        passed = bool(mesh.generation == 6 and counts == COUNTS and operation_equal and all(exact.values()) and
            source_frames['passed'] and source_topology['passed'] and
            symmetry['passed'] and topology['passed'] and minimum_area > 1e-14 and bounds)
        record = dict(case=case, selected_mode=mode, passed=passed, output_generation=int(mesh.generation),
            source_control_sha256_matches=True, atlas_and_colony_byte_hashes_match=True,
            actual_source_colony_provenance=source_frames, actual_source_native_topology=source_topology,
            carrier_stage_generation=stage, exact_saved_array_hashes=exact,
            complete_operation_receipt_equal=operation_equal, historical_raw_g06_key_aliases_declared=legacy,
            counts=counts, actual_native_lr_symmetry=symmetry, actual_native_topology=topology,
            minimum_triangle_area=minimum_area, declared_bounds_passed=bounds,
            maximum_carrier_shift=operation['carrier']['maximum_shift'], maximum_relief=operation['maximum_relief'],
            memory_available_before_replay=guard['available_physical'])
        records.append(record)
        if progress:
            print('COMPACT_FINISH_G06', mode, case, 'PASS' if passed else 'FAIL', exact, flush=True)
        del mesh, chart, tags, native, carrier_delta, operation, colonies, actual
        gc.collect()
    result = dict(status='PASS' if len(records) == 2 and all(item['passed'] for item in records) else 'FAIL',
        selected_mode=mode, expected_generation=6, expected_cases=list(CASES),
        verified_copied_asset_hashes=len(receipt['copied_assets']), records=records,
        scope='Exact selected G06 control/native/carrier arrays and complete operation receipt reconstructed from packaged WALL G03 parents and saved recipes/atlas/colonies. Actual native XYZ and oriented triangle reflection plus native edge topology checked.',
        excluded=['aesthetic judgment', 'self-intersection validity', 'fabrication', 'infinite Mandelbulb boundary'])
    if result['status'] != 'PASS':
        raise ValueError('Compact selected G06 replay failed: '+json.dumps(result))
    return result


def package(sources, mode, destination):
    if mode not in MODES or set(sources) != set(CASES):
        raise ValueError('One selected mode and exactly SPAN/COUNTER sources required.')
    sources = {case: Path(path).resolve() for case, path in sources.items()}
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Existing G06 review preserved: '+str(destination))
    if not destination.is_relative_to(REPO):
        raise ValueError('New G06 review must remain inside this worktree.')
    # No heavy replay yet: reject incomplete or preliminary sources first.
    atlas = [path/'atlas/power8.npz' for path in sources.values()]
    if len({sha(path) for path in atlas}) != 1:
        raise ValueError('Selected cases must use one byte-identical atlas.')
    pairs = [(sources['SPAN']/'atlas'/name, Path('atlas')/name) for name in ('power8.npz', 'recipe.json')]
    expected = {}
    common_recipes = None
    for case, source in sources.items():
        folder = source/mode/case/'G06'
        metadata = json.loads((folder/'generation.json').read_text(encoding='utf8'))
        metadata_identity(metadata, mode, case)
        recipes = {key: metadata[key] for key in ('relief_recipe', 'relaxation_recipe')}
        if common_recipes is not None and common_recipes != recipes:
            raise ValueError('Selected SPAN/COUNTER recipes differ.')
        common_recipes = recipes
        expected[case] = {name: file_array_hashes(folder/name) for name in FILES}
        for name in ('generation.json', 'operation_receipt.json', 'native_symmetry.json'):
            pairs.append((folder/name, Path(mode)/case/'G06'/name))
        pairs.append((source/'colonies.npz', Path(mode)/case/'G06/colonies.npz'))
        if (folder/'replay.json').is_file():
            pairs.append((folder/'replay.json', Path('receipts')/case/'original_replay.json'))
        pairs.append((source/'detail_finish.py', Path('source_snapshots')/case/'detail_finish.py'))
    missing = [str(source) for source, _ in pairs if not source.is_file()]
    if missing:
        raise FileNotFoundError('Selected G06 evidence incomplete: '+json.dumps(missing))
    destination.mkdir(parents=True)
    (destination/'.gitattributes').write_bytes(b'# Preserve copied G06 recipe bytes and hashes.\n* -text\n')
    copied = []
    for source, relative in pairs:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        digest = sha(source)
        if sha(target) != digest:
            raise ValueError('Copied G06 asset differs: '+relative.as_posix())
        copied.append(dict(path=relative.as_posix(), bytes=target.stat().st_size, sha256=digest,
            source=source.relative_to(REPO).as_posix()))
    receipt = dict(selected_mode=mode, expected_generation=6, expected_cases=list(CASES),
        common_recipes=common_recipes,
        expected_original_arrays=expected, copied_assets=copied, copied_bytes=sum(item['bytes'] for item in copied),
        source_parents='../WALL/{SPAN,COUNTER}/G03', previous_g05_package_unchanged=True,
        omission='All selected full-resolution controls, native arrays and carrier delta are regenerated from saved recipes on demand; no original output array dependency.',
        replay_command='python -B experiments/fold_visible_gate_20261012/compactpackage_finish_g6.py --verify docs/fold_visible_gate_20261012/review/finish_g6')
    (destination/'COPY_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
    replay = verify(destination, progress=True)
    (destination/'compact_finish_g6_replay.json').write_text(json.dumps(replay, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(destination=str(destination), copied_bytes=receipt['copied_bytes'],
        selected_mode=mode, compact_finish_g6_replay=replay['status']), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-span', type=Path)
    parser.add_argument('--source-counter', type=Path)
    parser.add_argument('--mode', choices=MODES)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--write-proof', action='store_true')
    args = parser.parse_args()
    if args.verify:
        replay = verify(args.verify, progress=True)
        if args.write_proof:
            with (args.verify/'compact_finish_g6_replay.json').open('x', encoding='utf8') as stream:
                stream.write(json.dumps(replay, indent=2)+'\n')
        print(json.dumps(replay, indent=2))
    else:
        if any(value is None for value in (args.source_span, args.source_counter, args.mode, args.destination)):
            parser.error('--source-span, --source-counter, --mode and --destination required for creation')
        package(dict(SPAN=args.source_span, COUNTER=args.source_counter), args.mode, args.destination)
