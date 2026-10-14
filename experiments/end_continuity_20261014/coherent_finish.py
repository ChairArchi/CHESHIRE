"""One coherent saved-replay carrier with subordinate continuous fine folds.

Reuse actual complete replay G7, reweight saved MIDDLE/LINKED/WIDE coordinate
contributions, then evaluate one current curved-flow field on fresh normals.
This is not a new G0-G7 replay or a new recursive dependency-chain recipe.
"""
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
OLD_CODE = HERE.parent/'fold_hierarchy_20261014'
FLOW_CODE = HERE.parent/'flow_fold_finish_20261014'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


lift = module('coherent_frozen_middle_lift', OLD_CODE/'middle_lift.py')
prepare = lift.prepare
flow_run = module('coherent_frozen_curved_run', FLOW_CODE/'run_curved.py')
old, flow = flow_run.old, flow_run.flow_operator
digest, ah, write = old.digest, old.ah, old.write
ROOT = Path('E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial02')
FRAME_PREPARATION = Path('E:/CHESHIRE_DATA/experiments/fold_hierarchy_20261014/trial01/PREPARATION.json')
BASE = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial03')
BASE_NATIVE = BASE/'FLOW/geometry.npz'
FINE_SCALE = 1.4
EXPECTED = {
    FRAME_PREPARATION: '0c413ec2ba61d40b6f12be01f2acab32c42183552a7a087dbd8bd3d528dcc247',
    BASE/'RECEIPT.json': '8c16e50324097ba6612e7a5e7ceb671ceb217e65dc3fd1f97d3af3f2aa7eb57f',
    BASE_NATIVE: '5bbd72fca4e4789dd6df1bfa947f38db72ad014c6c4afaf47733cff05aea9c1e',
    prepare.SOURCE: prepare.SOURCE_SHA,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    if root.exists():
        raise FileExistsError('Earlier end-continuity trial remains immutable.')
    started = time.perf_counter()
    for path, checksum in EXPECTED.items():
        if digest(path) != checksum:
            raise ValueError('Frozen actual source changed: '+str(path))
    prep = json.loads(FRAME_PREPARATION.read_text(encoding='utf8'))
    bindings = prep['source_binding']
    association = prep['accepted_source']['association_npy_sha256']
    sources = {str(path): checksum for path, checksum in EXPECTED.items()}
    for label in ('replay_middle6', 'replay_surface', 'replay_linked', 'replay_final'):
        bound = bindings[label]
        folder = prepare.PATHS[label]
        if Path(bound['folder']).resolve() != folder.resolve():
            raise ValueError('Actual preserved replay path differs: '+label)
        if not label.endswith('middle6') and bound['association_npy_sha256'] != association:
            raise ValueError('Frozen replay G7 associations differ: '+label)
        for path, checksum in ((folder/'control_quad.npz', bound['control_sha256']),
                               (folder/'generation.json', bound['generation_json_sha256'])):
            if digest(path) != checksum:
                raise ValueError('Actual replay ancestry changed: '+str(path))
            sources[str(path)] = checksum
        evidence = folder/'evidence.npz'
        expected_evidence = bound['metadata']['evidence_file_sha256']
        if digest(evidence) != expected_evidence:
            raise ValueError('Actual replay evidence changed: '+label)
        sources[str(evidence)] = expected_evidence
    root.mkdir(parents=True)
    code = [HERE/'coherent_finish.py', OLD_CODE/'middle_lift.py', OLD_CODE/'prepare.py',
            OLD_CODE/'run.py', OLD_CODE/'texture.py', FLOW_CODE/'run_curved.py',
            FLOW_CODE/'flow_curved_operator.py']+flow.helper_paths()
    snapshots = {}
    for source in dict.fromkeys(code):
        relative = source.relative_to(REPO)
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[relative.as_posix()] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    print('LOAD complete saved replay G7 and its actual contribution differences', flush=True)
    final_folder = prepare.PATHS['replay_final']
    with np.load(final_folder/'control_quad.npz', allow_pickle=False) as saved:
        control = {key: saved[key] for key in saved.files}
    xyz, q = control['xyz'], control['faces']
    if xyz.shape != (7002114, 3) or q.shape != (7002112, 4):
        raise ValueError('Actual complete replay dimensions differ.')
    if ah(xyz) != bindings['replay_final']['metadata']['checks']['control_xyz_sha256']:
        raise ValueError('Actual complete replay XYZ differs.')
    surface = prepare.load_xyz('replay_surface', bindings)
    linked_xyz = prepare.load_xyz('replay_linked', bindings)
    linked = linked_xyz-surface
    wide = xyz-linked_xyz
    reconstruction_error = float(np.max(np.abs(surface+linked+wide-xyz)))
    if reconstruction_error > 1e-12:
        raise ValueError('Saved full-replay contribution reconstruction differs.')
    del surface, linked_xyz
    gc.collect()
    middle, middle_proof = lift.extract('replay', bindings)
    incoming_middle = middle_proof['actual_incoming_G6_control']
    sources[incoming_middle['path']] = incoming_middle['sha256']
    phase, z, support, frame_proof = prepare.frame('replay', bindings)
    del support
    with np.load(final_folder/'evidence.npz', allow_pickle=False) as saved:
        vx, vy = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    k = phase/(2*np.pi)
    primary = 1-(1-np.exp(-((k-1)/.70)**4))*(1-np.exp(-((k-4)/.70)**4))
    gm, gl = .95+.35*primary, .80+.20*primary
    delta_hierarchy = ((gm-1.)[:, None]*middle+(gl-1.)[:, None]*(linked+wide))
    delta_hierarchy = old.transport_vector(delta_hierarchy, vx, vy)
    carrier = xyz+delta_hierarchy
    hierarchy = dict(implementation='COMPLETE_REPLAY_SAVED_CONTRIBUTION_HIERARCHY_V1',
        full_replay_source=str(final_folder), original_screen_mask_used=False,
        middle_gain='.95+.35*p', linked_and_wide_gain='.80+.20*p',
        primary='p=1-(1-exp(-((k-1)/.70)^4))*(1-exp(-((k-4)/.70)^4)); k=actual replay unwrapped phase/(2*pi)',
        middle_gain_range=[float(gm.min()), float(gm.max())],
        late_gain_range=[float(gl.min()), float(gl.max())],
        contribution_reconstruction_maximum_error=reconstruction_error,
        delta_norm_quantiles=np.quantile(np.linalg.norm(delta_hierarchy, axis=1), [.1, .5, .9, .99, 1.]).tolist(),
        carrier_xyz_sha256=ah(carrier), middle_lift_proof=middle_proof, frame_proof=frame_proof,
        scope='Actual complete saved replay and its verified MIDDLE CC lift, not original/replay screen-mask splicing. Saved coordinate contributions are reweighted; their later normal dependencies are not regenerated.')
    np.savez_compressed(root/'HIERARCHY_STATE.npz', primary_weight=primary, delta_hierarchy=delta_hierarchy)
    del middle, linked, wide, k, primary, gm, gl, delta_hierarchy
    gc.collect()
    print('EVALUATE subordinate curved flow on fresh coherent-carrier normals', flush=True)
    small_output, fine, state = flow.build(carrier, q, phase, z, vx, vy, old.H)
    delta = FINE_SCALE*state['delta']
    output = carrier+delta
    fine.update(implementation='COHERENT_COMPLETE_REPLAY_SUBORDINATE_CURVED_FLOW_V1',
        signed_request=fine['signed_request'].replace('H*.00025', 'H*.00035'),
        fixed_amplitude_bound=fine['fixed_amplitude_bound']*FINE_SCALE,
        raw_delta_norm_quantiles=(np.asarray(fine['raw_delta_norm_quantiles'])*FINE_SCALE).tolist(),
        filtered_delta_norm_quantiles=np.quantile(np.linalg.norm(delta, axis=1), [.1, .5, .9, .99, 1.]).tolist(),
        actual_changed_control_vertices=int(np.count_nonzero(np.any(output != carrier, axis=1))),
        output_xyz_sha256=ah(output), delta_sha256=ah(delta), derived_linear_amplitude_scale=FINE_SCALE,
        effective_amplitude_height_fraction=.00035,
        scope='Exactly one fresh normal evaluation and one existing displacement filter on the complete replay carrier; final linear scale1.4 gives effective A=.00035H. Same psi125, direction, endfade and continuous sampling attenuation.')
    state['delta'] = delta
    np.savez_compressed(root/'FLOW_STATE.npz', **state)
    del state, small_output, carrier, phase, z, delta
    gc.collect()
    source_symmetry, result_symmetry = old.symmetry(xyz, vx, vy), old.symmetry(output, vx, vy)
    if not np.isfinite(output).all() or result_symmetry > max(2e-12, source_symmetry+1e-12):
        raise ValueError('Actual coherent result is nonfinite or lost X/Y symmetry.')
    native, faces = old.native_fan(output, q)
    validation = dict(hierarchy=hierarchy, fine=fine, mesh=old.area_report(native, faces),
        original_native_topology_sha256=old.FACES_SHA,
        source_XY_position_symmetry_error=source_symmetry, output_XY_position_symmetry_error=result_symmetry,
        native_fan_centres='Arithmetic mean of moved carrier corners; no independent centre lifting.',
        self_intersection_checked=False, aesthetic_success='Pending actual matched render comparison')
    variant = old.save_variant(root, 'COHERENT_FLOW', native, faces, validation)
    control['xyz'] = output
    np.savez_compressed(root/'COHERENT_FLOW/control_quad.npz', **control)
    variant.update(control_quad=str(root/'COHERENT_FLOW/control_quad.npz'),
        control_quad_sha256=digest(root/'COHERENT_FLOW/control_quad.npz'))
    for path, checksum in sources.items():
        if digest(path) != checksum:
            raise ValueError('Original source changed during coherent finish.')
    for record in snapshots.values():
        if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Executed source/snapshot changed during coherent finish.')
    source_native = final_folder/'geometry.npz'
    source_native_sha = bindings['replay_final']['metadata']['geometry_file_sha256']
    if digest(source_native) != source_native_sha:
        raise ValueError('Actual complete replay native source changed.')
    sources[str(source_native)] = source_native_sha
    receipt = dict(kind='COMPLETE_SAVED_REPLAY_COHERENT_FLOW_FINISH', date='2026-10-14',
        source_native_path=str(source_native), source_native_geometry_sha256=source_native_sha,
        comparison_source_native_path=str(BASE_NATIVE),
        comparison_source_native_geometry_sha256=EXPECTED[BASE_NATIVE],
        source_baseline_receipt=str(BASE/'RECEIPT.json'), source_baseline_receipt_sha256=EXPECTED[BASE/'RECEIPT.json'],
        coherent_carrier_source=str(final_folder), variants={'COHERENT_FLOW': variant},
        sources=sources, source_snapshots=snapshots, hierarchy=hierarchy, fine=fine,
        generation=7, new_G8=False, elapsed_seconds=time.perf_counter()-started,
        scope='One authored finish on actual complete saved replay. No new G0-G7 replay, screen-space blending, added ornaments or topology. MIDDLE/LINKED/WIDE contribution reweighting and a fresh continuous normal field do not constitute a newly regenerated dependency-chain recipe. Original checkpoints immutable.')
    write(root/'RECEIPT.json', receipt)
    print('COHERENT_FINISH_COMPLETE', receipt['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
