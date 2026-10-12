"""Copy a compact, byte-preserved two-input review and replay omitted G4 arrays.

The new review root must not exist. No original output is edited or removed.
Rejected primitive gate geometry is deliberately outside this package. Its
attempt receipts remain diagnostic evidence, never the accepted gate design.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASES = ('SPAN', 'COUNTER')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(array):
    a = np.ascontiguousarray(array)
    return dict(shape=list(a.shape), dtype=a.dtype.str,
        sha256=hashlib.sha256(a.tobytes()).hexdigest())


def read_arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def selected_assets(source):
    pairs = []
    for case in CASES:
        parent = Path('WALL')/case/'G03'
        for name in ('control_quad.npz', 'geometry.npz', 'operation_fields.npz',
            'guide_0.npz', 'guide_1.npz', 'rails_0.npz', 'rails_1.npz',
            'generation.json', 'wall_profiles.npz', 'wall_measurements.json',
            'study.py', 'wall_fold.py'):
            pairs.append((source/parent/name, parent/name))
        child = Path('CHILD')/case/'G04'
        # G4 actual geometry and full operation arrays are exactly regenerated
        # below. Their original per-array hashes are retained instead of saving
        # duplicate high-resolution data alongside the parent and child controls.
        for name in ('control_quad.npz', 'rails_0.npz', 'rails_1.npz', 'generation.json',
            'study.py', 'wall_fold.py', 'child_fold.py', 'descend.py'):
            pairs.append((source/child/name, child/name))
        for kind in ('whole', 'detail'):
            image = Path('images')/(case.lower()+'_'+kind+'.png')
            pairs.append((source/image, image))
        attempt = Path('child_attempts')/(case+'.json')
        pairs.append((source/attempt, Path('receipts')/attempt))
    for name in ('verification.json', 'wall_summary.json', 'child_two_input_verification.json'):
        pairs.append((source/name, Path('receipts')/name))
    # These raw receipts intentionally include the earlier rejected primitive
    # gate pilot. Explicit scope lives in COPY_RECEIPT.json, next to their hashes.
    pilot = Path('receipts/rejected_primitive_pilot')
    pairs.append((source/'child_verification.json', pilot/'child_verification.json'))
    for case in ('GATE_COLUMN', 'GATE_LINTEL'):
        pairs.append((source/'child_attempts'/(case+'.json'), pilot/'child_attempts'/(case+'.json')))
    return pairs


def omitted_array_expectations(source):
    expected = {}
    for case in CASES:
        folder = source/'CHILD'/case/'G04'
        expected[case] = {
            name: {key: array_sha(value) for key, value in read_arrays(folder/name).items()}
            for name in ('geometry.npz', 'operation_fields.npz')}
    return expected


def verify_compact_children(destination, expected):
    """Recreate omitted arrays from packaged parents/rails and current repo code.

    This is strict about both expected cases and all saved operation-array keys.
    An empty/missing package cannot produce a PASS. Full-repository legacy
    refinement code is required; this is a portable repo review, not a standalone
    library detached from its recorded source revision.
    """
    import study
    records = []
    if set(expected) != set(CASES):
        raise ValueError('Exactly SPAN and COUNTER omitted-array receipts required.')
    for case in CASES:
        parent = destination/'WALL'/case/'G03'
        child = destination/'CHILD'/case/'G04'
        mesh, chart, tags = study.previous.anchor.t.load(parent)
        if mesh.generation != 3:
            raise ValueError('Packaged actual WALL G3 parent required: '+case)
        out, outchart, outtags, operator = study.previous.anchor.t.memory.refine(mesh, chart, tags)
        reference = out.xyz.copy()
        rails = [read_arrays(child/f'rails_{i}.npz') for i in (0, 1)]
        delta, fields = study.wall_fold.apply_wall(reference, outchart, rails, mode='WALL')
        existing = study.previous.anchor.t.prior.helpers.existing
        existing.reflect(delta, outchart, existing.symmetry(outchart))
        out.xyz = reference+delta
        actual_child = read_arrays(child/'control_quad.npz')
        control_error = float(np.max(np.abs(out.xyz-actual_child['xyz'])))
        discrete_equal = all(np.array_equal(a, actual_child[key]) for key, a in
            (('faces', out.faces), ('classes', out.classes), ('anchors', out.anchors),
             ('chart', outchart), ('memory', outtags), ('rest', out.rest)))
        native = study.previous.anchor.t.growth.native(out)
        generated = dict(geometry=dict(xyz=native.xyz, faces=native.faces[:, :3]),
            operations=dict(reference_xyz=reference, delta=delta, chart=outchart,
                input_edges=operator['input_edges'], parent_face=operator['parent_face'], **fields))
        errors = []
        for filename, group in (('geometry.npz', 'geometry'), ('operation_fields.npz', 'operations')):
            wanted = expected[case][filename]
            actual = generated[group]
            if set(wanted) != set(actual):
                errors.append(filename+': array keys differ')
            for key in set(wanted) & set(actual):
                if array_sha(actual[key]) != wanted[key]:
                    errors.append(filename+': '+key+' differs')
        passed = control_error == 0 and discrete_equal and not errors
        records.append(dict(case=case, passed=bool(passed),
            control_max_error=control_error, other_control_arrays_identical=bool(discrete_equal),
            omitted_native_and_operation_array_hashes_identical=not errors,
            physical_vertices=len(native.xyz), physical_triangles=len(native.faces), errors=errors))
    result = dict(status='PASS' if all(r['passed'] for r in records) else 'FAIL',
        expected_cases=list(CASES), records=records,
        scope='Exact saved-array replay from packaged WALL G3 controls and child rails. Does not certify aesthetics, self-intersections, fabrication or general recurrence.')
    if result['status'] != 'PASS':
        raise ValueError('Compact child replay failed: '+json.dumps(result))
    return result


def package(source, destination, max_mb=17.5):
    source, destination = source.resolve(), destination.resolve()
    if destination.exists():
        raise FileExistsError('Existing review preserved: '+str(destination))
    if not destination.is_relative_to(REPO):
        raise ValueError('Review destination must remain inside this worktree.')
    pairs = selected_assets(source)
    missing = [str(path) for path, _ in pairs if not path.is_file()]
    if missing:
        raise FileNotFoundError('Required review assets absent: '+json.dumps(missing))
    total = sum(path.stat().st_size for path, _ in pairs)
    if total > max_mb*1_000_000:
        raise ValueError(f'Column package exceeds declared budget: {total} > {max_mb} MB')
    expected = omitted_array_expectations(source)
    destination.mkdir(parents=True)
    # Scoped byte preservation; existing root attributes are never edited.
    (destination/'.gitattributes').write_bytes(b'# Preserve copied artifact bytes and recorded hashes.\n* -text\n')
    assets = []
    for original, relative in pairs:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        digest = sha(original)
        if sha(target) != digest:
            raise ValueError('Copied asset differs: '+str(relative))
        assets.append(dict(path=relative.as_posix(), bytes=original.stat().st_size,
            sha256=digest, source=original.relative_to(REPO).as_posix()))
    replay = verify_compact_children(destination, expected)
    (destination/'compact_child_replay.json').write_text(json.dumps(replay, indent=2)+'\n', encoding='utf8')
    receipt = dict(source_revision='055c42f', source_output=source.relative_to(REPO).as_posix(),
        copied_bytes=total, copied_megabytes=total/1_000_000, copied_assets=assets,
        omitted_child_array_expectations=expected,
        omitted_files=['CHILD/*/G04/geometry.npz', 'CHILD/*/G04/operation_fields.npz', 'member.ply'],
        omission_reason='Native arrays and operations exactly replayed from packaged controls/rails; PLY is a duplicate export.',
        replay_command='python -B experiments/fold_visible_gate_20261012/package_review.py --verify docs/fold_visible_gate_20261012/review',
        scope={
            'main_geometry': 'WALL and one bounded CHILD generation on SPAN and COUNTER only.',
            'images': 'Unretouched saved matched-camera native-geometry boards. CHILD visibility remains subtle.',
            'verification.json': 'Raw historical full-run receipt also includes rejected primitive gate pilot; only SPAN/COUNTER records support the accepted column work.',
            'wall_summary.json': 'Raw finite-cut/image-difference diagnostics also include pilot records. Neither is an aesthetic score.',
            'child_two_input_verification.json': 'Main explicit expected-case child verification receipt.',
            'rejected_primitive_pilot': 'Diagnostic receipts only. Primitive gate design was rejected after user steering; no pilot geometry is included.',
            'source_snapshots': 'Original generated-folder filenames/bytes retained. Their source_revision is the base revision, not a claim that the new experiment existed in that commit.',
            'gate': 'Accepted fixed-existing-column gate assets are added separately by the gate study.'})
    (destination/'COPY_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(destination=str(destination), copied_assets=len(assets),
        copied_bytes=total, compact_child_replay=replay['status']), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--max-mb', type=float, default=17.5)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        receipt = json.loads((args.verify/'COPY_RECEIPT.json').read_text(encoding='utf8'))
        print(json.dumps(verify_compact_children(args.verify, receipt['omitted_child_array_expectations']), indent=2))
    else:
        if args.source is None or args.destination is None:
            parser.error('--source and --destination are required when creating a review')
        package(args.source, args.destination, args.max_mb)
