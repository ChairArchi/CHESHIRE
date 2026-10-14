"""Amplify only the saved trial02 fine displacement, without new fields.

Exact construction: output = trial02 FLOW controls + 1.5*saved fine delta.
The hierarchy, parent phase, pitch, support, and filtering remain inherited.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json
import shutil
import time

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('frozen_curved_flow_run_utilities', HERE/'run_curved.py')
curved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curved)
old = curved.old
digest, ah, write = old.digest, old.ah, old.write
SOURCE = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial02')
ROOT = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial03')
SCALE = 2.5
EXPECTED = {
    SOURCE/'RECEIPT.json': '13b588ffcc699c21cd6a9029011b3c08d4daced7259eb41614250dbe9f29b38b',
    SOURCE/'FLOW_STATE.npz': '416ae18d2d898944886e7db56f3d765d653be32b0e3c96a3896a17a5a8796b2c',
    SOURCE/'FLOW/control_quad.npz': '5ef97f75ad6cc131e7e9e55f541f3b55d42b40bd77a52e5742e0278888ae7454',
    curved.CONTROL: '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27',
    curved.MIRRORS: '226c22ca83f9c71e69059d817e42140483d19a46228d66c6710170bc1ac17e21',
    curved.DESIGN: '37549b71c997a65943fbb6416d008b748ecba4ab05898eadfea95bc994e3a710',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    if root.exists():
        raise FileExistsError('Existing trial remains immutable.')
    started = time.perf_counter()
    for path, checksum in EXPECTED.items():
        if digest(path) != checksum:
            raise ValueError('Frozen actual source changed: '+str(path))
    receipt = json.loads((SOURCE/'RECEIPT.json').read_text(encoding='utf8'))
    variant = receipt['variants']['FLOW']
    if (receipt['kind'] != 'CONTINUOUS_PARENT_FLOW_FINE_FOLD_REPLACEMENT' or
            variant['control_quad_sha256'] != EXPECTED[SOURCE/'FLOW/control_quad.npz'] or
            Path(variant['control_quad']).resolve() != (SOURCE/'FLOW/control_quad.npz').resolve()):
        raise ValueError('Actual curved source receipt binding differs.')
    for record in receipt['source_snapshots'].values():
        if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Inherited executed source/snapshot differs.')
    root.mkdir(parents=True)
    code = [HERE/'run_bold.py', HERE/'run_curved.py', HERE/'flow_curved_operator.py',
            curved.OLD_CODE/'run.py', curved.OLD_CODE/'texture.py']
    code.extend(curved.flow_operator.helper_paths())
    snapshots = {}
    for source in dict.fromkeys(code):
        relative = source.relative_to(HERE.parents[1])
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[relative.as_posix()] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    with np.load(SOURCE/'FLOW/control_quad.npz', allow_pickle=False) as saved:
        control = {key: saved[key] for key in saved.files}
    xyz, q = control['xyz'], control['faces']
    with np.load(SOURCE/'FLOW_STATE.npz', allow_pickle=False) as saved:
        delta = saved['delta']
        sampling, endfade = saved['sampling_gain'], saved['endfade']
    if (xyz.shape != (7002114, 3) or q.shape != (7002112, 4) or delta.shape != xyz.shape or
            not np.isfinite(delta).all() or ah(delta) != receipt['fine']['delta_sha256']):
        raise ValueError('Actual saved fine delta/control association differs.')
    if ah(xyz) != receipt['fine']['output_xyz_sha256']:
        raise ValueError('Actual saved source control XYZ differs.')
    print('AMPLIFY same saved fine displacement 2.5x; no normal or field generation', flush=True)
    output = xyz+(SCALE-1.)*delta
    final_delta = SCALE*delta
    if not np.isfinite(output).all():
        raise ValueError('Nonfinite derived scaled output.')
    with np.load(curved.MIRRORS, allow_pickle=False) as saved:
        vx, vy = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    source_symmetry, result_symmetry = old.symmetry(xyz, vx, vy), old.symmetry(output, vx, vy)
    delta_symmetry = old.symmetry(final_delta, vx, vy)
    if result_symmetry > max(2e-12, source_symmetry+1e-12) or delta_symmetry > 1e-12:
        raise ValueError('Actual scaled output/delta symmetry differs.')
    fine = copy.deepcopy(receipt['fine'])
    norms = np.linalg.norm(final_delta, axis=1)
    carrier_reconstruction_error = 0.
    for start in range(0, len(xyz), 65536):
        stop = min(len(xyz), start+65536)
        reconstructed = (xyz[start:stop]-delta[start:stop])+final_delta[start:stop]
        carrier_reconstruction_error = max(carrier_reconstruction_error,
            float(np.max(np.abs(reconstructed-output[start:stop]))))
    if carrier_reconstruction_error > 2e-12:
        raise ValueError('Scaled source/delta reconstruction exceeds roundoff.')
    fine.update(implementation='INHERITED_PARENT_CONTINUOUS_FINE_FOLDS_V1_CURVED_SCALED',
        normal_field_passes=0, inherited_source_normal_field_passes=receipt['fine']['normal_field_passes'],
        signed_request=receipt['fine']['signed_request'].replace('H*.00025', 'H*.000625'),
        fixed_amplitude_bound=receipt['fine']['fixed_amplitude_bound']*SCALE,
        raw_delta_norm_quantiles=(np.asarray(receipt['fine']['raw_delta_norm_quantiles'])*SCALE).tolist(),
        filtered_delta_norm_quantiles=np.quantile(norms, [.1, .5, .9, .99, 1.]).tolist(),
        actual_changed_control_vertices=int(np.count_nonzero(np.any(output != xyz, axis=1))),
        final_nonzero_delta_vertices=int(np.count_nonzero(norms)),
        final_nonzero_delta_vertex_fraction=float(np.count_nonzero(norms)/len(norms)),
        output_xyz_sha256=ah(output), delta_sha256=ah(final_delta),
        maximum_delta_XY_symmetry_error=delta_symmetry,
        derived_scale=SCALE, source_trial02_control_sha256=EXPECTED[SOURCE/'FLOW/control_quad.npz'],
        source_saved_fine_delta_sha256=receipt['fine']['delta_sha256'],
        source_saved_fine_state_sha256=EXPECTED[SOURCE/'FLOW_STATE.npz'],
        exact_derived_construction='output=actual_trial02_FLOW_xyz+1.5*saved_trial02_fine_delta; final_delta=2.5*saved_trial02_fine_delta',
        carrier_plus_scaled_delta_roundoff_error=carrier_reconstruction_error,
        generation_scope='Derived linear amplitude scaling only. No new normal evaluation, phase, mask, averaging, or hierarchy generation.',
        limits='Same inherited field direction, pitch, sampling attenuation and endfade. Actual render decides visual quality; global self-intersections remain unchecked.')
    np.savez_compressed(root/'FLOW_STATE.npz', delta=final_delta, sampling_gain=sampling, endfade=endfade)
    del delta, final_delta, sampling, endfade, norms
    gc.collect()
    native, faces = old.native_fan(output, q)
    validation = dict(hierarchy=receipt['hierarchy'], fine=fine, mesh=old.area_report(native, faces),
        original_native_topology_sha256=old.FACES_SHA,
        source_XY_position_symmetry_error=source_symmetry, output_XY_position_symmetry_error=result_symmetry,
        native_fan_centres='Arithmetic mean of actual amplified carrier quad corners; no independent centre lift.',
        connectivity='Exact original G7 native fan indices; no added subdivision or topology.',
        self_intersection_checked=False, aesthetic_success='Pending actual matched render comparison')
    variant = old.save_variant(root, 'FLOW', native, faces, validation)
    control['xyz'] = output
    np.savez_compressed(root/'FLOW/control_quad.npz', **control)
    variant.update(control_quad=str(root/'FLOW/control_quad.npz'),
                   control_quad_sha256=digest(root/'FLOW/control_quad.npz'))
    for path, checksum in EXPECTED.items():
        if digest(path) != checksum:
            raise ValueError('Frozen source changed during derived update.')
    for record in snapshots.values():
        if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Executed source/snapshot changed.')
    result = dict(kind='CONTINUOUS_PARENT_FLOW_FINE_FOLD_REPLACEMENT', date='2026-10-14',
        variants={'FLOW': variant}, source_control_path=str(curved.CONTROL),
        source_control_sha256=EXPECTED[curved.CONTROL],
        design_source_native_path=str(curved.DESIGN), design_source_native_geometry_sha256=EXPECTED[curved.DESIGN],
        sources={str(path): checksum for path, checksum in EXPECTED.items()}, source_snapshots=snapshots,
        derived_source_receipt=str(SOURCE/'RECEIPT.json'), derived_source_receipt_sha256=EXPECTED[SOURCE/'RECEIPT.json'],
        hierarchy=receipt['hierarchy'], fine=fine, elapsed_seconds=time.perf_counter()-started,
        generation=7, new_G8=False,
        scope='One fixed visibility correction: same saved trial02 continuous fine displacement scaled2.5x. Primary hierarchy, direction, pitch, sampling support and filtering unchanged. Derived linear scaling, not a full replay or new normal-field pass. Original checkpoints immutable.')
    write(root/'RECEIPT.json', result)
    print('FLOW_BOLD_COMPLETE', result['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
