"""One continuous parent-coordinate fine-fold replacement on preserved G7.

Keep late folds at 80-100 percent and strengthen selected primary MIDDLE
families. Move actual carrier controls with one signed continuous field;
recompute ordinary native fan centres. No per-cell roof or sparse warp mask.
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
OLD_CODE = HERE.parent/'fold_hierarchy_20261014'
sys.path.insert(0, str(OLD_CODE))
spec = importlib.util.spec_from_file_location('preserved_hierarchy_utilities', OLD_CODE/'run.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
sys.path.insert(0, str(HERE))
import flow_curved_operator as flow_operator

ROOT = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial02')
FRAME = Path('E:/CHESHIRE_DATA/experiments/fold_hierarchy_20261014/trial01')
CONTROL, MIRRORS, H = old.CONTROL, old.MIRRORS, old.H
DESIGN = Path('E:/CHESHIRE_DATA/experiments/comb_scale_refinement_20261014/trial01/REFINED/geometry.npz')
EXPECTED = {CONTROL: '0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27',
            MIRRORS: '226c22ca83f9c71e69059d817e42140483d19a46228d66c6710170bc1ac17e21',
            FRAME/'COMPONENTS.npz': '3d2f4c1e1b46ad1ae881bf0f2130ebf85d9587bc3c2506604bf6f0346176314c',
            FRAME/'MIDDLE_COMPONENT.npz': '4b856cb97b111e567e97ef6c93436b87532a5a5488eefe2c9bda6e07744e833f',
            DESIGN: '37549b71c997a65943fbb6416d008b748ecba4ab05898eadfea95bc994e3a710'}
digest, ah, write = old.digest, old.ah, old.write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if root.exists():
        raise FileExistsError('A previous trial is immutable; choose a new root.')
    started = time.perf_counter()
    for path, checksum in EXPECTED.items():
        if digest(path) != checksum:
            raise ValueError('Frozen source changed: '+str(path))
    root.mkdir(parents=True)
    code = [HERE/'run_curved.py', HERE/'flow_curved_operator.py', OLD_CODE/'run.py', OLD_CODE/'texture.py']
    code.extend(flow_operator.helper_paths())
    snapshots = {}
    for source in dict.fromkeys(code):
        relative = source.relative_to(HERE.parents[1])
        target = root/'source_snapshot_run'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[relative.as_posix()] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    with np.load(CONTROL, allow_pickle=False) as saved:
        control = {key: saved[key] for key in saved.files}
    xyz, q = control['xyz'], control['faces']
    with np.load(MIRRORS, allow_pickle=False) as saved:
        vx, vy = saved['mirror_x_vertex_pairs'], saved['mirror_y_vertex_pairs']
    with np.load(FRAME/'COMPONENTS.npz', allow_pickle=False) as saved:
        linked, wide = saved['delta_linked'], saved['delta_wide']
        phase, z = saved['parent_phase_unwrapped'], saved['normalized_z']
    with np.load(FRAME/'MIDDLE_COMPONENT.npz', allow_pickle=False) as saved:
        middle = saved['delta_middle']
    k = phase/(2*np.pi)
    p = 1-(1-np.exp(-((k-1)/.70)**4))*(1-np.exp(-((k-4)/.70)**4))
    gm, gl = .95+.35*p, .80+.20*p
    delta_h = (gm-1)[:, None]*middle+(gl-1)[:, None]*(linked+wide)
    delta_h = old.transport_vector(delta_h, vx, vy)
    carrier = xyz+delta_h
    hierarchy = dict(profile='Same saved unwrapped k phase; primary parents k1,k4, width .70, union of exp(-distance^4)',
        middle_gain='.95+.35*p', linked_and_wide_gain='.80+.20*p',
        method='Enhance selected primary saved MIDDLE contribution, retain 80-100% of actual late LINKED/WIDE contributions.',
        middle_gain_range=[float(gm.min()), float(gm.max())],
        late_gain_range=[float(gl.min()), float(gl.max())],
        delta_norm_quantiles=np.quantile(np.linalg.norm(delta_h, axis=1), [.1, .5, .9, .99, 1]).tolist(),
        carrier_xyz_sha256=ah(carrier), full_G1_G7_replay=False,
        scope='Saved contribution reweighting with verified neutral CC lift of MIDDLE; not a regenerated G1-G7 growth recipe.')
    np.savez_compressed(root/'HIERARCHY_STATE.npz', primary_weight=p, delta_hierarchy=delta_h)
    del middle, linked, wide, k, p, gm, gl, delta_h
    gc.collect()
    print('BUILD continuous inherited-flow fine folds on actual mild carrier', flush=True)
    output, fine, state = flow_operator.build(carrier, q, phase, z, vx, vy, H)
    source_symmetry, output_symmetry = old.symmetry(xyz, vx, vy), old.symmetry(output, vx, vy)
    if output_symmetry > max(2e-12, source_symmetry+1e-12):
        raise ValueError('Actual X/Y position symmetry lost.')
    np.savez_compressed(root/'FLOW_STATE.npz', **state)
    del state, carrier, phase, z
    gc.collect()
    print('RECOMPUTE ordinary native fan centres from moved G7 controls', flush=True)
    native, faces = old.native_fan(output, q)
    mesh = old.area_report(native, faces)
    validation = dict(hierarchy=hierarchy, fine=fine, mesh=mesh,
        original_native_topology_sha256=old.FACES_SHA,
        source_XY_position_symmetry_error=source_symmetry, output_XY_position_symmetry_error=output_symmetry,
        native_fan_centres='Arithmetic mean of actual moved carrier quad corners; no independent centre lift.',
        connectivity='Exact original G7 native fan indices; inherited topology, no G8, added vertices or orphan creation.',
        self_intersection_checked=False, aesthetic_success='Pending actual matched render comparison')
    variant = old.save_variant(root, 'FLOW', native, faces, validation)
    control['xyz'] = output
    np.savez_compressed(root/'FLOW/control_quad.npz', **control)
    variant.update(control_quad=str(root/'FLOW/control_quad.npz'),
                   control_quad_sha256=digest(root/'FLOW/control_quad.npz'))
    for path, checksum in EXPECTED.items():
        if digest(path) != checksum:
            raise ValueError('Original source changed during update.')
    for record in snapshots.values():
        if digest(record['source']) != record['sha256'] or digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed source/snapshot changed.')
    receipt = dict(kind='CONTINUOUS_PARENT_FLOW_FINE_FOLD_REPLACEMENT', date='2026-10-14',
        variants={'FLOW': variant}, source_control_path=str(CONTROL), source_control_sha256=EXPECTED[CONTROL],
        design_source_native_path=str(DESIGN), design_source_native_geometry_sha256=EXPECTED[DESIGN],
        sources={str(path): checksum for path, checksum in EXPECTED.items()}, source_snapshots=snapshots,
        hierarchy=hierarchy, fine=fine, elapsed_seconds=time.perf_counter()-started,
        generation=7, new_G8=False,
        scope='One fixed combined correction: mild primary reinforcement preserving late folds, then signed continuous flow field on actual carrier controls. Replaces roof finish; no old sparse warpage mask. Actual render and saved mesh retained separately from prior accepted design. No claim of reference-exact recursive algorithm or global collision repair.')
    write(root/'RECEIPT.json', receipt)
    print('FLOW_FOLD_COMPLETE', receipt['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
