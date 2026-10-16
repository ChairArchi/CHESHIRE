"""Reapply macro return geometry in actual parent cross-sections on NESTED02.

The accepted G7 is the exact input and comparison. A dense mesh is already
available; this pass changes geometry with a parent-relative folding rule.
No original late fields are removed, no display preview is resampled, and
no image-space sculpture or new ornament mesh is used.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    if root.exists():
        raise FileExistsError('Earlier trial preserved; select a fresh root.')
    started = time.perf_counter()
    util = module('macro_receipt_utils', HERE/'run_recursive.py')
    native = module('macro_native_save', HERE/'run_final.py')
    operator = module('macro_geometric_formation', HERE/'recursive_fold_formation.py')
    bank = module('original_macro_fold_bank', HERE/'original_fold_events.py')
    base = util.ACCEPTED
    receipt_path = base/'RECEIPT.json'
    if util.digest(receipt_path) != native.BASE_RECEIPT_SHA:
        raise ValueError('Accepted NESTED02 receipt changed.')
    accepted = json.loads(receipt_path.read_text(encoding='utf8'))
    expected = accepted['variants']['NESTED']
    source = Path(expected['control_quad'])
    if util.digest(source) != expected['control_quad_sha256']:
        raise ValueError('Accepted NESTED02 control changed.')
    sources = {str(receipt_path):native.BASE_RECEIPT_SHA,
               str(source):expected['control_quad_sha256']}
    owners_folder, _ = util.bound_stage('G03_SIDEWALL', sources)
    surface_folder = util.STATES/'G07_SURFACE'
    surface_meta_path = surface_folder/'generation.json'
    surface_meta = json.loads(surface_meta_path.read_text(encoding='utf8'))
    pair_path = surface_folder/'evidence.npz'
    if not surface_meta['checks']['passed'] or util.digest(pair_path) != surface_meta['evidence_file_sha256']:
        raise ValueError('Actual G7 mirror-ID evidence changed.')
    sources[str(pair_path)] = surface_meta['evidence_file_sha256']
    sources[str(surface_meta_path)] = util.digest(surface_meta_path)
    print('LOAD accepted G7, exact SOURCE ancestry, and original macro fold family', flush=True)
    control = util.arrays(source)
    mesh = ArrayMesh(control['xyz'], control['faces'], control['classes'], control['rest'],
                     control['anchors'], int(control['generation']))
    mesh.surface = str(control['surface'])
    if mesh.generation != 7:
        raise ValueError('Accepted actual G7 required.')
    chart = control['chart']
    with np.load(owners_folder/'evidence.npz', allow_pickle=False) as saved:
        owners = saved['face_event_ids']
    with np.load(owners_folder/'control_quad.npz', allow_pickle=False) as saved:
        q3 = saved['faces']
    ancestor = mesh.faces
    for _ in range(4):
        ancestor = ancestor.reshape(-1, 4, 4)[:, :, 1]
    if not np.array_equal(ancestor, q3):
        raise ValueError('Actual accepted G7 -> G3 ancestry differs.')
    body_mask = np.repeat(owners == 0, 4**4)
    with np.load(pair_path, allow_pickle=False) as saved:
        pairs = {axis:saved['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
    events, bank_metadata = bank.load_events()
    state = operator.initialize_events(events)
    root.mkdir(parents=True)
    snapshots = {}
    code = [Path(__file__).resolve(), HERE/'run_recursive.py', HERE/'run_final.py',
            HERE/'recursive_fold_formation.py', HERE/'original_fold_events.py',
            HERE/'actual_seed_fold_events.json']
    code.extend(operator.helper_paths())
    code.extend(bank.helper_paths())
    for path in dict.fromkeys(Path(item).resolve() for item in code):
        relative = path.relative_to(REPO)
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[relative.as_posix()] = dict(source=str(path), snapshot=str(target), sha256=util.digest(path))
    util.write(root/'ORIGINAL_FOLD_BANK.json', dict(events=events, provenance=bank_metadata))
    print('FORM physical cross-section returns along the actual macro fold direction', flush=True)
    out, outchart, next_state, metadata, evidence = operator.step(
        mesh, chart, state, body_mask, pairs, subdivide=False)
    util.write(root/'FORMATION.json', metadata)
    if metadata.get('status') == 'NO_ACTIVE_PARENT_BASIN':
        util.write(root/'STOP.json', dict(reason='No actual macro parent basin; no decorative substitute.',
                                         formation=metadata))
        print('MACRO_FORMATION_STOP', flush=True)
        return
    if not np.array_equal(out.faces, mesh.faces) or not np.array_equal(outchart, chart) or out.generation != 7:
        raise ValueError('Same-topology forming pass changed accepted associations.')
    delta = out.xyz-mesh.xyz
    norm = np.linalg.norm(delta, axis=1)
    if not np.isfinite(out.xyz).all() or norm.max() <= 1e-10:
        raise ValueError('No finite new macro formation.')
    symmetry = 0.
    for start in range(0, len(out.xyz), native.CHUNK):
        ids = np.arange(start, min(start+native.CHUNK, len(out.xyz)))
        for axis, key in enumerate(('X', 'Y')):
            partner = out.xyz[pairs[key][ids]].copy()
            partner[:, axis] *= -1.
            symmetry = max(symmetry, float(np.max(np.abs(out.xyz[ids]-partner))))
    if symmetry > 2e-12:
        raise ValueError('Actual output lost source reflection symmetry.')
    evidence_record = util.save_tree(root, 'FORMATION_EVIDENCE', evidence)
    state_record = util.save_tree(root, 'NEXT_FOLD_STATE', next_state)
    validation = dict(formation=metadata, generation=7, added_subdivision_passes=0,
        output_XY_position_symmetry_error=symmetry, maximum_displacement=float(norm.max()),
        moved_controls=int(np.count_nonzero(norm > 1e-12)),
        faces_unchanged=True, source_outside_forming_regions_retained=True,
        self_intersection_checked=False, aesthetic_success='Pending actual matched render.')
    del delta, norm, pairs, state, next_state, evidence, body_mask
    gc.collect()
    print('SAVE full native G7: accepted source plus new geometric macro descendants', flush=True)
    variants = {'FOLDS':native.save(root, 'FOLDS', out.xyz, out.faces, validation)}
    control['xyz'] = out.xyz
    cp = root/'FOLDS/control_quad.npz'
    np.savez_compressed(cp, **control)
    variants['FOLDS'].update(control_quad=str(cp), control_quad_sha256=util.digest(cp))
    for record in snapshots.values():
        if util.digest(record['source']) != record['sha256'] or util.digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed forming code changed during trial.')
    for path, checksum in sources.items():
        if util.digest(path) != checksum:
            raise ValueError('Actual preserved input changed during forming.')
    util.write(root/'RECEIPT.json', dict(kind='PARENT_RELATIVE_MACRO_CROSS_SECTION_FOLDING', date='2026-10-15',
        source_control=str(source), source_control_sha256=expected['control_quad_sha256'],
        comparison_source_native_path=str(base/'NESTED/geometry.npz'),
        comparison_source_native_geometry_sha256=native.BASE_NATIVE_SHA,
        source_snapshots=snapshots, sources=sources, variants=variants,
        formation=metadata, original_fold_bank=bank_metadata,
        formation_evidence=evidence_record, next_fold_state=state_record,
        generation=7, added_subdivision_passes=0, new_G8=False,
        elapsed_seconds=time.perf_counter()-started,
        scope='Accepted NESTED02 is the exact unchanged input outside new forming supports. '
              'Macro fold ancestry seeds actual native transverse parent measurement. '
              'Same PCHIP radial/back-return family acts in current parent N/B cross-section frames. '
              'No old fields removed, image-space guides, new ornament mesh, or generation relabeling. '
              'Visual success requires actual matched close/body/front images.'))
    print('MACRO_FORMATION_COMPLETE', time.perf_counter()-started, flush=True)


if __name__ == '__main__':
    main()
