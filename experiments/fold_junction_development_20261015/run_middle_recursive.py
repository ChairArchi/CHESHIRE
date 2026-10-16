"""Continue actual G6 MIDDLE ribbon families through measured 3D formation.

Starts from actual replay G06_MIDDLE. The exact saved neutral G07_SURFACE is
the paired control. Neither input is a mature-G7 old-ID sampling preview.
The existing G6 phase identifies its ribbon ownership once. Actual radial
episodes bound the parent domains; all child geometry uses fresh measured
shoulders and RETURN. Old G3 WALL rails are not the new MIDDLE parent list.
"""
from pathlib import Path
import argparse
import gc
import hashlib
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

STATES = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
ACCEPTED = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')


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


def arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key:data[key] for key in data.files}


def save_tree(root, name, value):
    """Save nested recurrence state losslessly without object arrays/pickle."""
    payload = {}
    def encode(item):
        if isinstance(item, np.ndarray):
            key = f'A{len(payload):06}'
            payload[key] = item
            return dict(npz_key=key, shape=list(item.shape), dtype=str(item.dtype), sha256=ah(item))
        if isinstance(item, np.generic):
            return item.item()
        if isinstance(item, dict):
            return {str(key):encode(child) for key,child in item.items()}
        if isinstance(item, (list, tuple)):
            return [encode(child) for child in item]
        if item is None or isinstance(item, (str, int, float, bool)):
            return item
        raise TypeError('Unsupported saved recurrence state: '+type(item).__name__)
    description = encode(value)
    path = root/(name+'.npz')
    np.savez_compressed(path, **payload)
    write(root/(name+'.json'), dict(array_file=str(path), array_file_sha256=digest(path), tree=description))
    return dict(array_file=str(path), array_file_sha256=digest(path), description=str(root/(name+'.json')))


def bound_stage(stage, sources):
    folder = STATES/stage
    meta_path = folder/'generation.json'
    meta = json.loads(meta_path.read_text(encoding='utf8'))
    if not meta['checks']['passed']:
        raise ValueError('Actual source checks failed: '+stage)
    for filename, key in (('control_quad.npz', 'control_file_sha256'),
                          ('evidence.npz', 'evidence_file_sha256')):
        path = folder/filename
        if digest(path) != meta[key]:
            raise ValueError('Actual immutable state differs: '+str(path))
        sources[str(path)] = meta[key]
    sources[str(meta_path)] = digest(meta_path)
    return folder, meta


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    if root.exists():
        raise FileExistsError('Earlier output preserved; choose a fresh root.')
    started = time.perf_counter()
    helper = module('recursive_run_receipt_helpers', HERE/'run_final.py')
    operator = module('actual_recursive_middle_formation', HERE/'recursive_parent_folds_v3.py')
    initializer = module('actual_middle_parent_ownership', HERE/'middle_parent_state.py')
    sources = {}
    incoming_folder, incoming_meta = bound_stage('G06_MIDDLE', sources)
    neutral_folder, neutral_meta = bound_stage('G07_SURFACE', sources)
    owners_folder, owners_meta = bound_stage('G03_SIDEWALL', sources)
    accepted_receipt = ACCEPTED/'RECEIPT.json'
    if digest(accepted_receipt) != helper.BASE_RECEIPT_SHA:
        raise ValueError('Accepted reference receipt changed.')
    sources[str(accepted_receipt)] = helper.BASE_RECEIPT_SHA
    print('LOAD actual G6 MIDDLE ribbon coordinates, phase, and SOURCE ownership', flush=True)
    control = arrays(incoming_folder/'control_quad.npz')
    mesh = ArrayMesh(control['xyz'], control['faces'], control['classes'], control['rest'],
                     control['anchors'], int(control['generation']))
    mesh.surface = str(control['surface'])
    if mesh.generation != 6:
        raise ValueError('Actual G6 source required.')
    chart = control['chart']
    with np.load(owners_folder/'evidence.npz', allow_pickle=False) as saved:
        owners = saved['face_event_ids']
    with np.load(owners_folder/'control_quad.npz', allow_pickle=False) as saved:
        q3 = saved['faces']
    ancestor = mesh.faces
    for _ in range(3):
        ancestor = ancestor.reshape(-1, 4, 4)[:, :, 1]
    if not np.array_equal(ancestor, q3) or len(owners) != len(q3):
        raise ValueError('Actual G6 -> G3 ownership ancestry differs.')
    body_mask = np.repeat(owners == 0, 4**3)
    with np.load(incoming_folder/'evidence.npz', allow_pickle=False) as saved:
        pairs = {axis:saved['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
        phase = saved['directional_phase']
    root.mkdir(parents=True)
    snapshots = {}
    paths = [Path(__file__).resolve(), HERE/'recursive_parent_folds_v3.py', HERE/'run_final.py',
             HERE/'middle_parent_state.py']
    paths.extend(operator.helper_paths())
    paths.extend(initializer.helper_paths())
    for path in dict.fromkeys(Path(item).resolve() for item in paths):
        relative = path.relative_to(REPO)
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots[relative.as_posix()] = dict(source=str(path), snapshot=str(target), sha256=digest(path))
    print('REGISTER actual G6 MIDDLE parent ribbons and measured radial episodes', flush=True)
    recorded, sampler_info = operator.core.native_body_sampler(mesh, chart, body_mask)
    sampler = operator.CoverageSampler(recorded)
    fold_state, initialization, init_evidence = initializer.initialize_middle(
        mesh, chart, phase, body_mask, sampler)
    write(root/'MIDDLE_INITIALIZATION.json', initialization)
    init_record = save_tree(root, 'MIDDLE_INITIALIZATION_EVIDENCE', init_evidence)
    del recorded, sampler, init_evidence, phase
    gc.collect()
    if not fold_state.get('parents'):
        write(root/'STOP.json', dict(reason='No valid actual G6 parent ribbon; no decorative substitute.',
                                    initialization=initialization))
        print('MIDDLE_PARENT_INITIALIZATION_STOP', flush=True)
        return
    print('FORM actual G6 MIDDLE descendants in one genuine G6 -> G7 step', flush=True)
    out, outchart, next_state, metadata, evidence = operator.step(
        mesh, chart, fold_state, body_mask, pairs, subdivide=True)
    write(root/'FORMATION.json', metadata)
    if out.generation != 7 or metadata.get('status') == 'NO_ACTIVE_PARENT_BASIN':
        write(root/'STOP.json', dict(reason='No valid actual parent basin; no decorative substitute.', metadata=metadata))
        print('RECURSIVE_FORMATION_STOP', flush=True)
        return
    print('VERIFY paired neutral topology and preserve measured next-generation state', flush=True)
    neutral = arrays(neutral_folder/'control_quad.npz')
    if not np.array_equal(out.faces, neutral['faces']):
        raise ValueError('Actual new G7 topology differs from paired neutral source.')
    if not np.array_equal(outchart, neutral['chart']):
        raise ValueError('Actual new chart differs from paired neutral source.')
    native_delta = out.xyz-neutral['xyz']
    norms = np.linalg.norm(native_delta, axis=1)
    symmetry = 0.
    # Reflected ID maps are saved in the exact paired neutral G7 state.
    with np.load(neutral_folder/'evidence.npz', allow_pickle=False) as saved:
        outpairs = {axis:saved['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
    for start in range(0, len(out.xyz), helper.CHUNK):
        ids = np.arange(start, min(start+helper.CHUNK, len(out.xyz)))
        for axis, key in enumerate(('X', 'Y')):
            partner = out.xyz[outpairs[key][ids]].copy()
            partner[:, axis] *= -1.
            symmetry = max(symmetry, float(np.max(np.abs(out.xyz[ids]-partner))))
    if not np.isfinite(out.xyz).all() or symmetry > 2e-12 or norms.max() <= 1e-10:
        raise ValueError('Actual formation finite/symmetry/visible-motion prerequisite failed.')
    evidence_record = save_tree(root, 'FORMATION_EVIDENCE', evidence)
    next_state_record = save_tree(root, 'NEXT_FOLD_STATE', next_state)
    validation = dict(formation=metadata, generation=7, source_generation=6,
        added_subdivision_passes=1, output_XY_position_symmetry_error=symmetry,
        displacement_maximum=float(norms.max()), moved_controls=int(np.count_nonzero(norms > 1e-12)),
        finite=True, self_intersection_checked=False, visual_success='Pending matched actual render.')
    del mesh, chart, control, fold_state, evidence, pairs, native_delta, norms, body_mask
    gc.collect()
    print('SAVE genuine new G7 native and paired original neutral G7', flush=True)
    variants = {'RECURSIVE':helper.save(root, 'RECURSIVE', out.xyz, out.faces, validation)}
    cp = root/'RECURSIVE/control_quad.npz'
    np.savez_compressed(cp, xyz=out.xyz, faces=out.faces, chart=outchart, classes=out.classes,
        rest=out.rest, anchors=out.anchors, generation=np.array(7), surface=np.array('mean'))
    variants['RECURSIVE'].update(control_quad=str(cp), control_quad_sha256=digest(cp))
    del out, outchart, next_state
    gc.collect()
    variants['REFERENCE_G7'] = helper.save(root, 'REFERENCE_G7', neutral['xyz'], neutral['faces'],
        dict(source=str(neutral_folder/'control_quad.npz'), source_generation=7,
             source_sha256=neutral_meta['control_file_sha256'], actual_saved_neutral_counterfactual=True))
    for record in snapshots.values():
        if digest(record['source']) != record['sha256'] or digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed source changed during actual generation.')
    for path, checksum in sources.items():
        if digest(path) != checksum:
            raise ValueError('Actual immutable source changed during generation.')
    write(root/'RECEIPT.json', dict(kind='ACTUAL_G6_MIDDLE_OWNED_RECURSIVE_FORMATION', date='2026-10-15',
        comparison_source_native_path=str(ACCEPTED/'NESTED/geometry.npz'),
        comparison_source_native_geometry_sha256=helper.BASE_NATIVE_SHA,
        source_control=str(incoming_folder/'control_quad.npz'),
        source_control_sha256=incoming_meta['control_file_sha256'], source_generation=6,
        counterfactual_neutral=str(neutral_folder/'control_quad.npz'),
        counterfactual_neutral_sha256=neutral_meta['control_file_sha256'],
        source_snapshots=snapshots, sources=sources, variants=variants,
        middle_initialization=initialization, middle_initialization_evidence=init_record,
        formation_evidence=evidence_record, next_fold_state=next_state_record,
        formation=metadata, generation=7, new_G8=False, added_subdivision_passes=1,
        elapsed_seconds=time.perf_counter()-started,
        scope='Actual G6 MIDDLE ribbons -> actual G7 geometric formation with reusable owned next state. '
              'Existing G6 phase seeds ownership only once; actual radial episodes bound each family. '
              'New child geometry comes from actual measured shoulders and 3D RETURN, not phase harmonics. '
              'Paired control is the exact saved neutral G7 SURFACE. '
              'Accepted NESTED02 is an additional design reference and is not identical to that control. '
              'No authored image-space guide, phase harmonics, late decorative normal field, or mature-G7 prefix resampling. '
              'Visual success requires actual matched renders.'))
    print('RECURSIVE_FORMATION_COMPLETE', time.perf_counter()-started, flush=True)


if __name__ == '__main__':
    main()
