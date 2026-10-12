"""Compact exact replay package for the accepted fixed-column symmetric lintel.

Only a fresh fixed_gate review root is written. Assembly native arrays are
omitted and verified by their original per-array hashes after reconstructing
them from the already packaged actual column, saved transforms, and lintels.
"""
from pathlib import Path
import argparse
import json
import shutil

import numpy as np

from package_review import REPO, sha, array_sha, read_arrays

MODES = ('PLAIN', 'CONTROL', 'WALL')


def selected_assets(source):
    pairs = []
    for relative in (Path('lintel/ORIGINAL_G02'), Path('lintel/SOURCE/G02'), Path('lintel/PLAIN')):
        for path in sorted((source/relative).iterdir()):
            if path.is_file() and path.suffix in ('.npz', '.json'):
                pairs.append((path, relative/path.name))
    for mode in ('CONTROL', 'WALL'):
        relative = Path('lintel')/mode/'G03'
        names = ['control_quad.npz', 'geometry.npz', 'operation_fields.npz', 'generation.json']
        if mode == 'WALL':
            names += [f'{prefix}_{i}.npz' for prefix in ('guide', 'rails') for i in range(4)]
        pairs.extend((source/relative/name, relative/name) for name in names)
    for mode in MODES:
        relative = Path(mode)/'assembly.json'
        pairs.append((source/relative, relative))
    pairs.extend((source/name, Path(name)) for name in ('SUMMARY.json', 'verification.json', 'symmetric_lintel.py'))
    return pairs


def original_expectations(source):
    return {mode: {key: array_sha(a) for key, a in read_arrays(source/mode/'geometry.npz').items()}
        for mode in MODES}


def identical_arrays(actual, expected):
    return set(actual) == set(expected) and all(array_sha(actual[k]) == array_sha(expected[k]) for k in actual)


def verify(destination, expectations):
    import symmetric_lintel as lintel
    column = destination.parent/'WALL/SPAN/G03/geometry.npz'
    if set(expectations) != set(MODES):
        raise ValueError('Exactly PLAIN, CONTROL and WALL assembly expectations required.')
    if not column.is_file():
        raise FileNotFoundError('Existing packaged actual SPAN WALL column is required.')
    layout = lintel.fixed_layout(column)
    original = destination/'lintel/ORIGINAL_G02'
    source = destination/'lintel/SOURCE/G02'
    source_metadata = json.loads((source/'generation.json').read_text(encoding='utf8'))
    preserved_hashes = (sha(original/'control_quad.npz') == source_metadata['source_control_sha256'] and
        sha(original/'generation.json') == source_metadata['source_generation_metadata_sha256'])
    rebuilt, chart, tags, provenance, construction = lintel.make_source(original, layout)
    saved_construction = read_arrays(source/'construction.npz')
    construction_identical = identical_arrays(construction, saved_construction)
    control = dict(xyz=rebuilt.xyz, faces=rebuilt.faces, chart=chart, classes=rebuilt.classes,
        rest=rebuilt.rest, anchors=rebuilt.anchors, generation=np.array(rebuilt.generation),
        surface=np.array(rebuilt.surface), memory=tags)
    source_control_identical = identical_arrays(control, read_arrays(source/'control_quad.npz'))
    native = lintel.study.previous.anchor.t.growth.native(rebuilt)
    source_native_identical = identical_arrays(dict(xyz=native.xyz, faces=native.faces[:, :3]),
        read_arrays(source/'geometry.npz'))
    source_transform_identical = bool(np.array_equal(construction['fixed_dimension_transform'],
        np.array(source_metadata['fixed_member_dimension_transform'])))
    pair_ids, pair_error = lintel.axial_pairs(chart)
    source_pairs_identical = np.array_equal(pair_ids, saved_construction['source_axial_pair_ids'])
    source_result = dict(passed=bool(preserved_hashes and construction_identical and source_control_identical and
        source_native_identical and source_transform_identical and source_pairs_identical),
        original_checkpoint_hashes_identical=bool(preserved_hashes),
        all_source_construction_arrays_identical=bool(construction_identical),
        source_control_arrays_identical=bool(source_control_identical),
        source_native_arrays_identical=bool(source_native_identical),
        source_dimension_transform_identical=source_transform_identical,
        source_material_pair_ids_identical=bool(source_pairs_identical), material_pair_max_error=pair_error)
    # CONTROL intentionally needs no saved rails: replay_member emits its raw
    # zero field. WALL reads the exact four packaged rail dictionaries.
    replay = [lintel.replay_member(destination/'lintel'/mode/'G03') for mode in ('CONTROL', 'WALL')]
    for item in replay:
        folder = destination/'lintel'/item['candidate']/'G03'
        operation = read_arrays(folder/'operation_fields.npz')
        ids, error = lintel.axial_pairs(operation['chart'])
        item['saved_axial_pair_ids_identical'] = bool(np.array_equal(ids, operation['axial_pair_ids']))
        item['material_pair_max_error'] = error
        item['passed'] &= item['saved_axial_pair_ids_identical']
    assemblies = []
    column_arrays = read_arrays(column)
    source_xyz, source_faces = column_arrays['xyz'], column_arrays['faces']
    for mode in MODES:
        metadata = json.loads((destination/mode/'assembly.json').read_text(encoding='utf8'))
        if metadata['candidate'] != mode:
            raise ValueError('Assembly mode metadata differs: '+mode)
        local = read_arrays(destination/'lintel'/(mode if mode == 'PLAIN' else mode+'/G03')/'geometry.npz')
        left = lintel.gate_layout.apply_transform(source_xyz, np.array(metadata['column_transforms']['LEFT']))
        right = lintel.gate_layout.apply_transform(source_xyz, np.array(metadata['column_transforms']['RIGHT']))
        beam = lintel.gate_layout.apply_transform(local['xyz'], np.array(metadata['lintel_transform']))
        count = len(source_xyz)
        xyz = np.vstack([left, right, beam])
        faces = np.vstack([source_faces, source_faces+count, local['faces']+2*count])
        labels = np.r_[np.zeros(len(source_faces), np.int8), np.ones(len(source_faces), np.int8),
            np.full(len(local['faces']), 2, np.int8)]
        arrays = dict(xyz=xyz, faces=faces, face_member=labels)
        actual_hashes = {key: array_sha(a) for key, a in arrays.items()}
        hashes_identical = actual_hashes == expectations[mode]
        transforms_identical = (np.array_equal(np.array(metadata['lintel_transform']), layout['beam_transform']) and
            all(np.array_equal(np.array(metadata['column_transforms'][key]), layout['column_transforms'][key])
                for key in ('LEFT', 'RIGHT')))
        column_bytes_identical = sha(column) == metadata['source_column_sha256']
        ranges_identical = metadata['part_vertex_ranges'] == dict(LEFT=[0, count], RIGHT=[count, 2*count],
            LINTEL=[2*count, len(xyz)])
        geometry = lintel.geometry_checks(xyz, faces, components=3)
        reflection = lintel.reflection(xyz, faces, axis=0)
        passed = (hashes_identical and transforms_identical and column_bytes_identical and
            ranges_identical and geometry['passed'] and reflection['passed'])
        assemblies.append(dict(candidate=mode, passed=bool(passed),
            omitted_assembly_array_hashes_identical=bool(hashes_identical),
            fixed_column_bytes_identical=bool(column_bytes_identical),
            fixed_saved_transforms_identical=bool(transforms_identical), part_ranges_identical=bool(ranges_identical),
            physical_vertices=len(xyz), physical_triangles=len(faces), geometry=geometry,
            global_left_right=reflection))
    result = dict(status='PASS' if source_result['passed'] and all(item['passed'] for item in replay+assemblies) else 'FAIL',
        expected_modes=list(MODES), source_reconstruction=source_result, lintel_replay=replay,
        assembly_reconstruction=assemblies,
        scope='Exact preserved SOURCE reconstruction, saved lintel operation replay and assembly array hashes. Requires full repository code and packaged actual column; no original output directory dependency.',
        excluded=['self-intersection', 'physical bearing/joints', 'fabrication', 'central seam C1 continuity', 'aesthetic success'])
    if result['status'] != 'PASS':
        raise ValueError('Compact gate replay failed: '+json.dumps(result))
    return result


def package(source, destination):
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError('Existing fixed gate review preserved: '+str(destination))
    if not destination.is_relative_to(REPO):
        raise ValueError('Destination must remain inside this worktree.')
    pairs = selected_assets(source)
    missing = [str(a) for a, _ in pairs if not a.is_file()]
    if missing:
        raise FileNotFoundError('Required fixed gate checkpoint absent: '+json.dumps(missing))
    duplicate_receipts = []
    for prefix in ('guide', 'rails'):
        for i in range(4):
            name = f'{prefix}_{i}.npz'
            control, wall = source/'lintel/CONTROL/G03'/name, source/'lintel/WALL/G03'/name
            if sha(control) != sha(wall):
                raise ValueError('Cannot omit nonidentical CONTROL guide/rail: '+name)
            duplicate_receipts.append(dict(omitted='lintel/CONTROL/G03/'+name,
                packaged_identical='lintel/WALL/G03/'+name, sha256=sha(wall)))
    expectations = original_expectations(source)
    destination.mkdir(parents=True)
    (destination/'.gitattributes').write_bytes(b'# Preserve copied checkpoint bytes and recorded hashes.\n* -text\n')
    records = []
    for original, relative in pairs:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        digest = sha(original)
        if sha(target) != digest:
            raise ValueError('Copied fixed gate asset differs: '+str(relative))
        records.append(dict(path=relative.as_posix(), bytes=original.stat().st_size,
            sha256=digest, source=original.relative_to(REPO).as_posix()))
    replay = verify(destination, expectations)
    (destination/'compact_gate_replay.json').write_text(json.dumps(replay, indent=2)+'\n', encoding='utf8')
    copied_bytes = sum(item['bytes'] for item in records)
    receipt = dict(copied_assets=records, copied_bytes=copied_bytes, copied_megabytes=copied_bytes/1_000_000,
        expected_modes=list(MODES), omitted_assembly_array_expectations=expectations,
        omitted_duplicate_control_records=duplicate_receipts,
        fixed_existing_column='../WALL/SPAN/G03/geometry.npz',
        replay_command='python -B experiments/fold_visible_gate_20261012/package_gate.py --verify docs/fold_visible_gate_20261012/review/fixed_gate',
        scope='Accepted fixed layout and unchanged actual WALL column twice. New symmetric lintel carrier, PLAIN/CONTROL/WALL checkpoints. No rejected primitive gate geometry.',
        source_snapshot='symmetric_lintel.py copied exactly from generated root; dependencies are the repository experiment and legacy refinement code.',
        omitted='All three assembly geometry.npz arrays exactly reconstructed from saved transforms and packaged lintel/column data. Duplicated CONTROL guides/rails are byte-identical to WALL.')
    (destination/'COPY_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(destination=str(destination), copied_assets=len(records), copied_bytes=copied_bytes,
        compact_gate_replay=replay['status']), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        receipt = json.loads((args.verify/'COPY_RECEIPT.json').read_text(encoding='utf8'))
        print(json.dumps(verify(args.verify, receipt['omitted_assembly_array_expectations']), indent=2))
    else:
        if args.source is None or args.destination is None:
            parser.error('--source and --destination required for creation')
        package(args.source, args.destination)
