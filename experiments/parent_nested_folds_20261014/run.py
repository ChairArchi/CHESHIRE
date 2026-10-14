"""Rebuild two subordinate decoration levels on the actual coherent parent.

Keep the latest primary MIDDLE weighting. Replace the competing LINKED/WIDE
and global fine layers with fresh, locally budgeted CHILD then SMALL fields.
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prior = module('nested_frozen_coherent_loader', HERE.parent/'end_continuity_20261014/coherent_finish.py')
prepare, lift, old = prior.prepare, prior.lift, prior.old
digest, ah, write = old.digest, old.ah, old.write
operator = module('nested_parent_operator', HERE/'parent_nested.py')
ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial01')
BASE = Path('E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial02')
BASE_SHA = 'e7adee3cd77d4882143aba82623e8cf839193c693866ab21315b410fb05bd34c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    if root.exists():
        raise FileExistsError('Earlier trial is immutable; choose another root.')
    started = time.perf_counter()
    preparation_path = prior.FRAME_PREPARATION
    if digest(preparation_path) != prior.EXPECTED[preparation_path]:
        raise ValueError('Actual frozen ancestry preparation changed.')
    bindings = json.loads(preparation_path.read_text(encoding='utf8'))['source_binding']
    baseline_path = BASE/'RECEIPT.json'
    baseline = json.loads(baseline_path.read_text(encoding='utf8'))['variants']['COHERENT_FLOW']
    if baseline['geometry_sha256'] != BASE_SHA or digest(baseline['geometry']) != BASE_SHA:
        raise ValueError('Latest comparison model changed.')
    sources = {str(preparation_path): digest(preparation_path), str(baseline_path): digest(baseline_path),
               baseline['geometry']: BASE_SHA}
    for label in ('replay_middle6', 'replay_surface'):
        folder, binding = prepare.PATHS[label], bindings[label]
        for filename, key in (('control_quad.npz', 'control_sha256'), ('generation.json', 'generation_json_sha256')):
            path, expected = folder/filename, binding[key]
            if digest(path) != expected:
                raise ValueError('Actual parent binding changed: '+str(path))
            sources[str(path)] = expected
        evidence = folder/'evidence.npz'
        expected = binding['metadata']['evidence_file_sha256']
        if digest(evidence) != expected:
            raise ValueError('Actual parent evidence changed.')
        sources[str(evidence)] = expected
    root.mkdir(parents=True)
    code = [HERE/'run.py', HERE/'parent_nested.py', HERE.parent/'end_continuity_20261014/coherent_finish.py',
            prior.OLD_CODE/'middle_lift.py', prior.OLD_CODE/'prepare.py', prior.OLD_CODE/'run.py',
            prior.OLD_CODE/'texture.py', prior.FLOW_CODE/'run_curved.py', prior.FLOW_CODE/'flow_curved_operator.py']
    code.extend(operator.helper_paths())
    snapshots = {}
    for source in dict.fromkeys(code):
        relative = source.relative_to(REPO)
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[relative.as_posix()] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    print('LOAD actual coherent G7 SURFACE and verified MIDDLE contribution', flush=True)
    source = prepare.PATHS['replay_surface']/'control_quad.npz'
    with np.load(source, allow_pickle=False) as saved:
        control = {key: saved[key] for key in saved.files}
    xyz, quads = control['xyz'], control['faces']
    if ah(xyz) != bindings['replay_surface']['metadata']['checks']['control_xyz_sha256']:
        raise ValueError('Actual saved parent XYZ differs.')
    middle, middle_proof = lift.extract('replay', bindings)
    incoming = middle_proof['actual_incoming_G6_control']
    sources[incoming['path']] = incoming['sha256']
    phase, z, support, frame_proof = prepare.frame('replay', bindings)
    del z, support
    with np.load(prepare.PATHS['replay_middle6']/'evidence.npz', allow_pickle=False) as saved:
        envelope6, support6 = saved['envelope'], saved['feature_support']
    with np.load(prepare.PATHS['replay_middle6']/'control_quad.npz', allow_pickle=False) as saved:
        quads6 = saved['faces']
    with np.load(prepare.PATHS['replay_surface']/'evidence.npz', allow_pickle=False) as saved:
        edges = saved['input_edges']
        vx, vy = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    height = bindings['replay_middle6']['metadata']['operator_metadata']['physical_height']
    fraction = bindings['replay_middle6']['metadata']['operator_metadata']['recipe']['middle_amplitude_height_fraction']
    if fraction != .006 or abs(height-old.H) > 1e-12:
        raise ValueError('Actual MIDDLE amplitude or physical height differs.')
    parent_envelope = prepare.lift_coordinate(height*fraction*envelope6*(1-.55*support6), edges, quads6)
    del envelope6, support6, edges, quads6
    k = phase/(2*np.pi)
    primary = 1-(1-np.exp(-((k-1)/.70)**4))*(1-np.exp(-((k-4)/.70)**4))
    gain = .95+.35*primary
    primary_delta = old.transport_vector((gain-1)[:, None]*middle, vx, vy)
    carrier = xyz+primary_delta
    parent_envelope *= gain
    np.savez_compressed(root/'PARENT_STATE.npz', primary_weight=primary, primary_delta=primary_delta,
                        parent_envelope=parent_envelope)
    del middle, k, primary, gain, primary_delta
    gc.collect()
    print('BUILD two fresh parent-contained decoration levels', flush=True)
    output, nested, state = operator.build(carrier, quads, phase, parent_envelope, vx, vy, height)
    np.savez_compressed(root/'NESTED_STATE.npz', **state)
    del state, carrier, phase, parent_envelope
    gc.collect()
    symmetry = old.symmetry(output, vx, vy)
    if symmetry > max(2e-12, old.symmetry(xyz, vx, vy)+1e-12):
        raise ValueError('Actual result lost X/Y position symmetry.')
    native, faces = old.native_fan(output, quads)
    validation = dict(mesh=old.area_report(native, faces), nested=nested,
        output_XY_position_symmetry_error=symmetry, original_native_topology_sha256=old.FACES_SHA,
        native_fan_centres='Arithmetic means of moved G7 quad corners; no independent lift.',
        self_intersection_checked=False, aesthetic_success='Pending actual matched render.')
    variant = old.save_variant(root, 'NESTED', native, faces, validation)
    control['xyz'] = output
    np.savez_compressed(root/'NESTED/control_quad.npz', **control)
    variant.update(control_quad=str(root/'NESTED/control_quad.npz'),
                   control_quad_sha256=digest(root/'NESTED/control_quad.npz'))
    for path, expected in sources.items():
        if digest(path) != expected:
            raise ValueError('Immutable source changed during generation.')
    for record in snapshots.values():
        if any(digest(record[key]) != record['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Executed source snapshot changed.')
    receipt = dict(kind='PARENT_CONTAINED_TWO_LEVEL_DECORATION', date='2026-10-14',
        source_control_path=str(source), source_control_sha256=sources[str(source)],
        comparison_source_native_path=baseline['geometry'], comparison_source_native_geometry_sha256=BASE_SHA,
        variants={'NESTED': variant}, sources=sources, source_snapshots=snapshots,
        parent_frame_proof=frame_proof, actual_middle_lift_proof=middle_proof,
        primary_gain='.95+.35*p; same primary weighting as COHERENT_FLOW',
        parent_budget='Actual G6 MIDDLE .006H*saved_envelope*(1-.55*saved_support), actual V/E/F scalar transport, multiplied by primary gain; not pointwise absolute displacement.',
        nested=nested, generation=7, new_G8=False, elapsed_seconds=time.perf_counter()-started,
        scope='Rebuild two late fields on actual coherent SURFACE parent. Original LINKED/WIDE and global FLOW are omitted. Fresh actual normals at both stages. Not a full G0-G7 replay, semantic ridge detection, collision certificate, or reference-exact recursive algorithm.')
    write(root/'RECEIPT.json', receipt)
    print('PARENT_NESTED_COMPLETE', receipt['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
