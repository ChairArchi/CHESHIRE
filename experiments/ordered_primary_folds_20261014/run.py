"""Replace the whole-body MIDDLE field, then generate subordinate folds."""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prior = module('ordered_frozen_neutral_cc', HERE.parent/'end_continuity_20261014/coherent_finish.py')
primary = module('ordered_actual_primary', HERE/'primary.py')
secondary = module('ordered_actual_secondary', HERE/'secondary.py')
prepare, lift, old = prior.prepare, prior.lift, prior.old
digest, ah, write = old.digest, old.ah, old.write
ROOT = Path('E:/CHESHIRE_DATA/experiments/ordered_primary_folds_20261014/trial01')
DEPTH = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states/G06_DEPTH08')
DEPTH_SHA = '35f5bdbc39568a33697c2f414ad8754aa9b0e072ffe8f3bf8dfb0a76abdc58d1'
BASE = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
BASE_SHA = 'cde95d13f64d86739ac25e134e67024533d6be4fafec7a5d4c7a46896b65403e'
BASE_RECEIPT_SHA = 'ab212bf9222980a25cb6d0c5ca31aa82ad0fe5f48b64864d9ed8e8d5fbb02524'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    if root.exists():
        raise FileExistsError('Earlier trial remains immutable.')
    started = time.perf_counter()
    prep_path = prior.FRAME_PREPARATION
    if digest(prep_path) != prior.EXPECTED[prep_path]:
        raise ValueError('Frozen actual ancestry preparation changed.')
    bindings = json.loads(prep_path.read_text(encoding='utf8'))['source_binding']
    if digest(BASE/'RECEIPT.json') != BASE_RECEIPT_SHA:
        raise ValueError('Actual latest comparison receipt changed.')
    baseline = json.loads((BASE/'RECEIPT.json').read_text(encoding='utf8'))['variants']['NESTED']
    if baseline['geometry_sha256'] != BASE_SHA or digest(baseline['geometry']) != BASE_SHA:
        raise ValueError('Latest comparison native geometry changed.')
    sources = {str(prep_path): digest(prep_path), str(BASE/'RECEIPT.json'): BASE_RECEIPT_SHA,
               baseline['geometry']: BASE_SHA}
    for label in ('replay_middle6', 'replay_surface'):
        folder, binding = prepare.PATHS[label], bindings[label]
        for filename, expected in (('control_quad.npz', binding['control_sha256']),
                ('generation.json', binding['generation_json_sha256']),
                ('evidence.npz', binding['metadata']['evidence_file_sha256'])):
            path = folder/filename
            if digest(path) != expected:
                raise ValueError('Frozen actual association source changed: '+str(path))
            sources[str(path)] = expected
    depth_info = json.loads((DEPTH/'generation.json').read_text(encoding='utf8'))
    if digest(DEPTH/'control_quad.npz') != DEPTH_SHA or depth_info['control_file_sha256'] != DEPTH_SHA:
        raise ValueError('Actual G6 DEPTH08 source changed.')
    if bindings['replay_middle6']['metadata']['source_control_sha256'] != DEPTH_SHA:
        raise ValueError('Actual original MIDDLE does not bind this DEPTH08.')
    sources[str(DEPTH/'control_quad.npz')] = DEPTH_SHA
    sources[str(DEPTH/'generation.json')] = digest(DEPTH/'generation.json')
    root.mkdir(parents=True)
    code = [HERE/'run.py', HERE/'primary.py', HERE/'secondary.py',
        HERE.parent/'end_continuity_20261014/coherent_finish.py', prior.OLD_CODE/'middle_lift.py',
        prior.OLD_CODE/'prepare.py', prior.OLD_CODE/'run.py', prior.OLD_CODE/'texture.py',
        prior.FLOW_CODE/'run_curved.py']+primary.helper_paths()+secondary.helper_paths()
    snapshots = {}
    for source in dict.fromkeys(code):
        relative = source.relative_to(REPO)
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[relative.as_posix()] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    print('LOAD actual G6 DEPTH08 and bound G6/G7 associations', flush=True)
    with np.load(DEPTH/'control_quad.npz', allow_pickle=False) as saved:
        control6 = {key: saved[key] for key in saved.files}
    x6, q6, chart6 = control6['xyz'], control6['faces'], control6['chart']
    if ah(x6) != depth_info['checks']['control_xyz_sha256']:
        raise ValueError('Actual incoming G6 XYZ differs.')
    with np.load(prepare.PATHS['replay_middle6']/'evidence.npz', allow_pickle=False) as saved:
        support = saved['feature_support']
        vx6, vy6 = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    with np.load(prepare.PATHS['replay_surface']/'control_quad.npz', allow_pickle=False) as saved:
        control7 = {key: saved[key] for key in saved.files}
    with np.load(prepare.PATHS['replay_surface']/'evidence.npz', allow_pickle=False) as saved:
        edges7 = saved['input_edges']
        vx7, vy7 = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    following, degree6, cc_proof = lift.actual_incidence(q6, edges7, control7['faces'], len(x6))
    with np.load(prepare.PATHS['replay_middle6']/'control_quad.npz', allow_pickle=False) as saved:
        previous6 = saved['xyz']
    print('VERIFY neutral CC against actual preserved SURFACE once', flush=True)
    reproduced = lift.neutral_cc(previous6, q6, edges7, following, degree6)
    cc_error = float(np.max(np.abs(reproduced-control7['xyz'])))
    if cc_error > 1e-13:
        raise ValueError('Actual neutral CC reproduction failed.')
    cc_proof['checked_saved_SURFACE_max_coordinate_error'] = cc_error
    del previous6, reproduced
    gc.collect()
    print('REPLACE whole-body MIDDLE with ordered material-coordinate PRIMARY', flush=True)
    new6, phase6, amplitude6, primary_meta, primary_state = primary.build(
        x6, q6, chart6, support, vx6, vy6, old.H)
    stage6 = root/'PRIMARY_G06'
    stage6.mkdir()
    control6['xyz'] = new6
    np.savez_compressed(stage6/'control_quad.npz', **control6)
    np.savez_compressed(stage6/'STATE.npz', **primary_state)
    write(stage6/'RECEIPT.json', dict(stage='PRIMARY_G06', generation=6,
        control_sha256=digest(stage6/'control_quad.npz'), state_sha256=digest(stage6/'STATE.npz'),
        source_control=str(DEPTH/'control_quad.npz'), source_control_sha256=DEPTH_SHA,
        metadata=primary_meta))
    del primary_state, control6, x6, chart6, support, vx6, vy6
    gc.collect()
    print('REFINE new actual PRIMARY by verified neutral CC to G7', flush=True)
    carrier7 = lift.neutral_cc(new6, q6, edges7, following, degree6)
    phase7 = prepare.lift_coordinate(phase6, edges7, q6)
    amplitude7 = lift.neutral_cc(np.repeat(amplitude6[:, None], 3, axis=1), q6, edges7, following, degree6)[:, 0].copy()
    del new6, phase6, amplitude6, q6, edges7, following, degree6
    gc.collect()
    np.savez_compressed(root/'PRIMARY_G07_STATE.npz', parent_phase_unwrapped=phase7,
                        parent_envelope=amplitude7)
    print('GENERATE nested secondary and tertiary on the new parents', flush=True)
    output, subordinate, state = secondary.build(carrier7, control7['faces'], phase7, amplitude7, vx7, vy7, old.H)
    np.savez_compressed(root/'SUBORDINATE_STATE.npz', **state)
    del state, carrier7, phase7, amplitude7
    gc.collect()
    symmetry = old.symmetry(output, vx7, vy7)
    if symmetry > 2e-12:
        raise ValueError('Actual ordered G7 position symmetry failed.')
    native, faces = old.native_fan(output, control7['faces'])
    validation = dict(mesh=old.area_report(native, faces),
        output_XY_position_symmetry_error=symmetry, actual_neutral_CC=cc_proof,
        primary=primary_meta, subordinate=subordinate,
        original_native_topology_sha256=old.FACES_SHA,
        self_intersection_checked=False, aesthetic_success='Pending actual matched render.')
    variant = old.save_variant(root, 'ORDERED', native, faces, validation)
    control7['xyz'] = output
    np.savez_compressed(root/'ORDERED/control_quad.npz', **control7)
    variant.update(control_quad=str(root/'ORDERED/control_quad.npz'),
                   control_quad_sha256=digest(root/'ORDERED/control_quad.npz'))
    for path, expected in sources.items():
        if digest(path) != expected:
            raise ValueError('Actual preserved source changed during generation.')
    for record in snapshots.values():
        if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Executed source/snapshot changed.')
    receipt = dict(kind='WHOLE_BODY_ORDERED_PRIMARY_REPLACEMENT', date='2026-10-14',
        comparison_source_native_path=baseline['geometry'], comparison_source_native_geometry_sha256=BASE_SHA,
        source_control_path=str(DEPTH/'control_quad.npz'), source_control_sha256=DEPTH_SHA,
        variants={'ORDERED': variant}, sources=sources, source_snapshots=snapshots,
        primary=primary_meta, subordinate=subordinate, actual_neutral_CC=cc_proof,
        stage6_receipt=str(stage6/'RECEIPT.json'), stage6_receipt_sha256=digest(stage6/'RECEIPT.json'),
        generation=7, new_G8=False, elapsed_seconds=time.perf_counter()-started,
        scope='Actual G6 DEPTH08 -> fresh material-coordinate PRIMARY -> verified neutral CC G7 -> fresh subordinate two levels. Original MIDDLE/LINKED/WIDE/FLOW fields and their deltas are not mixed into the new geometry. Earlier G0-G6 DEPTH08 geometry remains the bound source. Not a semantic ridge detector, new topology branch, collision certificate or reference-exact algorithm.')
    write(root/'RECEIPT.json', receipt)
    print('ORDERED_PRIMARY_COMPLETE', receipt['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
