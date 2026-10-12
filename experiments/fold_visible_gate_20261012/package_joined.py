"""Small joined-gate review with exact native replay and actual ray overlap.

Reuses the packaged fixed-gate lintel and unchanged actual column. No original
output directory is needed for verification; large before/after native and
assembly arrays are represented by their exact original per-array hashes.
"""
from pathlib import Path
import argparse
import json
import shutil

import numpy as np

import gate_junctions as joint

REPO = Path(__file__).resolve().parents[2]


def array_hashes(arrays):
    return {key: joint.array_sha(a) for key, a in arrays.items()}


def omitted_expectations(source):
    return {key: array_hashes(joint.read_arrays(source/path)) for key, path in (
        ('native', 'beam/JOINED/G03/geometry.npz'),
        ('before_assembly', 'CONTROL/geometry.npz'),
        ('after_assembly', 'JOINED/geometry.npz'))}


def verify(destination, expectations):
    if set(expectations) != {'native', 'before_assembly', 'after_assembly'}:
        raise ValueError('All three omitted-array receipts are required.')
    lintel = joint.lintel
    original_folder = destination.parent/'fixed_gate/lintel/WALL/G03'
    column_file = destination.parent/'WALL/SPAN/G03/geometry.npz'
    joined = destination/'beam/JOINED/G03'
    metadata = json.loads((destination/'JOINED/assembly.json').read_text(encoding='utf8'))
    saved = json.loads((destination/'verification.json').read_text(encoding='utf8'))
    original = joint.read_arrays(original_folder/'control_quad.npz')
    actual = joint.read_arrays(joined/'control_quad.npz')
    operation = joint.read_arrays(joined/'operation_fields.npz')
    reference = operation['reference_xyz']
    original_matches = bool(np.array_equal(reference, original['xyz']) and
        all(joint.array_sha(original[key]) == saved['source_control_arrays'][key] for key in original))
    centres = operation['seat_local_z']
    halfwidth = float(operation['support_halfwidth'])
    seat_weights = np.array([joint.plateau((reference[:, 2]-seat)/halfwidth, .45) for seat in centres])
    weights = seat_weights.max(axis=0)
    weights_identical = bool(np.array_equal(seat_weights, operation['seat_weights']) and
        np.array_equal(weights, operation['weights']))
    after_xyz = joint.deform(reference, weights, float(operation['section_factor']), float(operation['common_drop']))
    after_control = dict(original, xyz=after_xyz)
    control_identical = array_hashes(after_control) == array_hashes(actual)
    delta_error = float(np.max(np.abs(after_xyz-reference-operation['delta'])))
    axial_error = float(np.max(np.abs(after_xyz[:, 2]-reference[:, 2])))
    mesh, chart, _ = lintel.study.previous.anchor.t.load(joined)
    native = lintel.study.previous.anchor.t.growth.native(mesh)
    native_arrays = dict(xyz=native.xyz, faces=native.faces[:, :3])
    native_identical = array_hashes(native_arrays) == expectations['native']
    column = joint.read_arrays(column_file)
    column_identical = joint.sha(column_file) == metadata['source_column_sha256'] == saved['source_existing_column_sha256']
    transforms = {key: np.asarray(value) for key, value in metadata['column_transforms'].items()}
    beam_transform = np.asarray(metadata['lintel_transform'])
    transform_identical = bool(np.array_equal(beam_transform, operation['beam_transform']) and
        np.array_equal(transforms['LEFT'], operation['column_left_transform']) and
        np.array_equal(transforms['RIGHT'], operation['column_right_transform']))
    transformed = {name: lintel.gate_layout.apply_transform(column['xyz'], transform)
        for name, transform in transforms.items()}
    baseline = joint.read_arrays(original_folder/'geometry.npz')
    count = len(column['xyz'])
    assembled = {}
    for name, beam in (('before_assembly', baseline), ('after_assembly', native_arrays)):
        world = lintel.gate_layout.apply_transform(beam['xyz'], beam_transform)
        assembled[name] = dict(xyz=np.vstack([transformed['LEFT'], transformed['RIGHT'], world]),
            faces=np.vstack([column['faces'], column['faces']+count, beam['faces']+2*count]),
            face_member=np.r_[np.zeros(len(column['faces']), np.int8), np.ones(len(column['faces']), np.int8),
                np.full(len(beam['faces']), 2, np.int8)])
    assembly_identical = {name: array_hashes(arrays) == expectations[name] for name, arrays in assembled.items()}
    before = assembled['before_assembly']; after = assembled['after_assembly']
    column_error = float(np.max(np.abs(before['xyz'][:2*count]-after['xyz'][:2*count])))
    column_faces_identical = np.array_equal(before['faces'][:2*len(column['faces'])],
        after['faces'][:2*len(column['faces'])])
    width, depth = metadata['target_lintel_vertical_section'], metadata['target_lintel_depth']
    rays = []
    for name in ('LEFT', 'RIGHT'):
        centre = transforms[name][0, 3]
        for dx in (-.18*width, 0., .18*width):
            for y in (-.12*depth, 0., .12*depth):
                rays.append((name, [centre+dx, y], dx == 0 and y == 0))
    surfaces = {name: joint.VerticalTriangles(xyz, column['faces']) for name, xyz in transformed.items()}
    world_beam = lintel.gate_layout.apply_transform(native.xyz, beam_transform)
    contacts = joint.contact_records(world_beam, native_arrays['faces'], surfaces, rays, saved['required_overlap'])
    contacts_identical = contacts == saved['actual_contact_after']
    contact_passed = joint.contact_passes(contacts)
    actual_sections = np.array([joint.section_extent(native.xyz, native_arrays['faces'], s) for s in centres])
    sections_identical = bool(np.array_equal(actual_sections, saved['actual_seat_sections_after']))
    geometry = lintel.geometry_checks(after['xyz'], after['faces'], components=3)
    reflection = lintel.reflection(after['xyz'], after['faces'], axis=0)
    passed = (original_matches and weights_identical and control_identical and native_identical and
        delta_error == 0 and axial_error == 0 and column_identical and transform_identical and
        all(assembly_identical.values()) and column_error == 0 and column_faces_identical and
        contacts_identical and contact_passed and sections_identical and geometry['passed'] and reflection['passed'])
    result = dict(status='PASS' if passed else 'FAIL',
        original_packaged_lintel_controls_identical=original_matches,
        recomputed_weights_identical=weights_identical, joined_control_arrays_identical=control_identical,
        operation_delta_max_error=delta_error, beam_axial_station_max_error=axial_error,
        omitted_native_hashes_identical=native_identical, omitted_assembly_hashes_identical=assembly_identical,
        packaged_column_bytes_identical=column_identical, transforms_identical=transform_identical,
        unchanged_column_max_error=column_error, unchanged_column_faces_identical=bool(column_faces_identical),
        actual_contact_ray_records_identical=contacts_identical, actual_head_overlap_passed=bool(contact_passed),
        passing_rays={name: sum(r['passes'] for r in contacts if r['seat'] == name) for name in ('LEFT', 'RIGHT')},
        actual_joint_sections_identical=sections_identical, actual_section_factors=saved['actual_seat_section_factors'],
        geometry=geometry, global_left_right=reflection,
        scope='Exact reconstruction from packaged original lintel, new control operation and unchanged existing column. Actual finite native-triangle vertical parity intervals overlap; deliberate member overlap remains separate closed meshes.',
        excluded=['Boolean union', 'structural joint', 'self-intersection certification', 'fabrication'])
    if not passed:
        raise ValueError('Compact joined replay failed: '+json.dumps(result))
    return result


def package(source, destination):
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError('Existing joined review preserved: '+str(destination))
    if not destination.is_relative_to(REPO):
        raise ValueError('Review destination must remain inside worktree.')
    names = [Path('beam/JOINED/G03')/name for name in ('control_quad.npz', 'operation_fields.npz', 'generation.json')]
    names += [Path('JOINED/assembly.json'), Path('verification.json'), Path('SUMMARY.json'), Path('gate_junctions.py')]
    for name in names:
        if not (source/name).is_file():
            raise FileNotFoundError(source/name)
    expectations = omitted_expectations(source)
    destination.mkdir(parents=True)
    (destination/'.gitattributes').write_bytes(b'# Preserve copied checkpoint bytes and recorded hashes.\n* -text\n')
    copied = []
    for name in names:
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
        digest = joint.sha(source/name)
        if joint.sha(target) != digest:
            raise ValueError('Copied joined asset differs: '+str(name))
        copied.append(dict(path=name.as_posix(), bytes=target.stat().st_size,
            sha256=digest, source=(source/name).relative_to(REPO).as_posix()))
    replay = verify(destination, expectations)
    (destination/'compact_joined_replay.json').write_text(json.dumps(replay, indent=2)+'\n', encoding='utf8')
    receipt = dict(copied_assets=copied, copied_bytes=sum(row['bytes'] for row in copied),
        omitted_array_expectations=expectations,
        original_lintel='../fixed_gate/lintel/WALL/G03', existing_column='../WALL/SPAN/G03/geometry.npz',
        omission='No duplicate before/after native or assembly geometry. All omitted original arrays exactly recreated and hashed.',
        replay_command='python -B experiments/fold_visible_gate_20261012/package_joined.py --verify docs/fold_visible_gate_20261012/review/gate_joined')
    (destination/'COPY_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(destination=str(destination), copied_bytes=receipt['copied_bytes'],
        compact_joined_replay=replay['status']), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        receipt = json.loads((args.verify/'COPY_RECEIPT.json').read_text(encoding='utf8'))
        print(json.dumps(verify(args.verify, receipt['omitted_array_expectations']), indent=2))
    else:
        if args.source is None or args.destination is None:
            parser.error('--source and --destination required for creation')
        package(args.source, args.destination)
