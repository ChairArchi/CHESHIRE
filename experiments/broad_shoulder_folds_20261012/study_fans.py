"""One G6 surface-field pass of smaller folds attached to the broad ridge.

No new subdivision, field volume, separate components or modification of the
preserved broad parent is performed. Every generated candidate has its own E
directory and retains the actual incoming G6 frame and displacement evidence.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json
import shutil
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import folds
import rooted_fans
_spec = importlib.util.spec_from_file_location('rooted_fans_broad_runner', HERE/'study.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)

finish, t, bulb = folds.finish, folds.t, folds.bulb
MODE = 'ROOTED_FANS'


def displacement(chart, patch, frame, guarded_weight, recipe):
    if int(frame['incoming_generation']) != 6:
        raise ValueError('Actual incoming broad G6 frame required.')
    height, fields = rooted_fans.height(chart, patch, recipe)
    height = height.copy()
    height[guarded_weight == 0.] = 0.
    parameter = np.clip(chart[:, 0], frame['parameter'][0], frame['parameter'][-1])
    normal = bulb.unit(PchipInterpolator(frame['parameter'], frame['pooled_normals'], axis=0)(parameter))
    normal[:, :2] *= np.where(chart[:, 1:] < 0., -1., 1.)
    raw = height[:, None]*normal
    fields.update(applied_height=height, applied_pooled_normals=normal, guarded_weight=guarded_weight)
    return raw, fields


def run_case(parent_root, output, case):
    finish.memory_guard()
    source = parent_root/'BROAD_ACTIVE'/case/'G06'
    final = output/MODE/case/'G06'
    evidence = output/case
    if final.exists() or evidence.exists():
        raise FileExistsError('Preserved fine-fold output already exists.')
    parent_verification = json.loads((parent_root/'VERIFICATION.json').read_text(encoding='utf8'))
    if parent_verification['status'] != 'PASS':
        raise ValueError('The actual broad parent must pass before fine-fold evaluation.')
    parent_state = parent_verification['cases'][case]['states']['BROAD_ACTIVE']
    mesh, chart, tags = t.load(source)
    if mesh.generation != 6 or finish.array_hash(mesh.xyz) != parent_state['final_control_xyz_sha256']:
        raise ValueError('Actual incoming parent differs from the verified broad G6.')
    baseline = mesh.xyz.copy()
    patch = bulb.read_arrays(parent_root/case/'actual_patch.npz')
    weight, controls, fans = folds.guarded_weight(mesh, chart, patch)
    frame = folds.incoming_frame(mesh, chart, patch)
    evidence.mkdir(parents=True)
    frame_path = evidence/'G06_incoming_frame.npz'
    np.savez_compressed(frame_path, **frame)
    curves = rooted_fans.curve_evidence(patch)
    incoming_native = t.growth.native(mesh)
    incoming_chart = np.concatenate([chart, t.face_values(mesh, chart)])
    sampler = bulb.study.NativeChartSampler(incoming_native.xyz, incoming_native.faces[:, :3], incoming_chart)
    curve_xyz, curve_ids, curve_bary = sampler.sample(curves['surface_uv'], records=True)
    curves.update(source_uv=curves['surface_uv'], source_xyz=curve_xyz,
        source_triangle_ids=curve_ids, source_barycentric=curve_bary,
        incoming_generation=np.array(6), incoming_control_xyz_sha256=np.array(finish.array_hash(baseline)))
    curve_path = evidence/'G06_incoming_curves.npz'
    np.savez_compressed(curve_path, **curves)
    del sampler, incoming_native, incoming_chart, curves, curve_xyz, curve_ids, curve_bary
    gc.collect()
    raw, fields = displacement(chart, patch, frame, weight, rooted_fans.RECIPE)
    raw_hash = finish.array_hash(raw)
    requested = folds.previous.reflect(raw, chart)
    mesh.xyz = baseline+requested
    actual_delta = mesh.xyz-baseline
    native = t.growth.native(mesh)
    baseline_native = np.concatenate([baseline, t.face_values(mesh, baseline)])
    outside = np.r_[controls['weight'] == 0., fans['weight'] == 0.]
    ends = np.r_[controls['ends'], fans['ends']]
    pairs, pair_receipts = study.checks_module.reflection_pairs(mesh, chart)
    symmetry = study.checks_module.coordinate_symmetry(native.xyz, pairs, pair_receipts)
    faces_hash = finish.array_hash(native.faces[:, :3])
    area = finish.minimum_area(native.xyz, native.faces[:, :3])
    checked = dict(finite=bool(np.isfinite(native.xyz).all()), minimum_triangle_area=area,
        actual_native_xy_symmetry=symmetry, native_faces_sha256=faces_hash,
        inherited_native_faces_identical_to_parent=faces_hash == parent_state['native_faces_sha256'],
        control_xyz_sha256=finish.array_hash(mesh.xyz), native_xyz_sha256=finish.array_hash(native.xyz),
        maximum_actual_added_shift=float(np.linalg.norm(actual_delta, axis=1).max()),
        actual_native_outside_parent_exact=bool(np.array_equal(native.xyz[outside], baseline_native[outside])),
        actual_native_ends_parent_exact=bool(np.array_equal(native.xyz[ends], baseline_native[ends])),
        actual_changed_native_vertices=int(np.count_nonzero(np.linalg.norm(native.xyz-baseline_native, axis=1) > 1e-12)))
    checked['passed'] = bool(checked['finite'] and area > 1e-14 and
        checked['inherited_native_faces_identical_to_parent'] and
        checked['actual_native_outside_parent_exact'] and checked['actual_native_ends_parent_exact'])
    final.mkdir(parents=True)
    np.savez_compressed(final/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors, generation=np.array(6),
        surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(final/'geometry.npz', xyz=native.xyz, faces=native.faces[:, :3])
    np.savez_compressed(final/'operation_fields.npz', requested_delta=requested,
        actual_delta=actual_delta, **fields)
    metadata = dict(input_case=case, candidate=MODE, recipe=rooted_fans.RECIPE,
        source=str(source), source_control_sha256=bulb.digest(source/'control_quad.npz'),
        source_control_xyz_sha256=finish.array_hash(baseline),
        source_generation_sha256=bulb.digest(source/'generation.json'),
        parent_verification_sha256=bulb.digest(parent_root/'VERIFICATION.json'),
        patch_source=str(parent_root/case/'actual_patch.npz'), patch_sha256=bulb.digest(parent_root/case/'actual_patch.npz'),
        frame_path=str(frame_path.relative_to(output)), frame_sha256=bulb.digest(frame_path),
        curve_path=str(curve_path.relative_to(output)), curve_sha256=bulb.digest(curve_path),
        raw_delta_sha256=raw_hash, applied_delta_sha256=finish.array_hash(requested),
        output_generation=6, added_subdivision_passes=0, added_surface_field_passes=1,
        added_mandelbulb_evaluations=0,
        lineage='Actual verified BROAD_ACTIVE G6 → one rooted fan signed-height pass along actual incoming pooled native normal → constructive material reflection',
        scope='Authored sparse two-scale rooted curves, not automatic branching or a restored Hansmeyer/IAAC algorithm; parent broad geometry stays read-only',
        self_intersection='NOT_CHECKED_EXPLORATORY', visual_success='NOT_ASSESSED', checks=checked)
    study.write(final/'generation.json', metadata)
    for filename in ('study_fans.py', 'rooted_fans.py'):
        shutil.copy2(HERE/filename, evidence/filename)
    print('ROOTED_FANS_SAVED', case, checked['passed'], checked['maximum_actual_added_shift'], flush=True)
    del mesh, frame, fields, raw, requested, native, baseline_native, baseline, actual_delta, pairs
    gc.collect()
    if not checked['passed']:
        raise ValueError('Failed candidate preserved: '+str(final))
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=study.CASES, default=list(study.CASES))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Fresh output root required.')
    args.output.mkdir(parents=True)
    study.write(args.output/'RECIPE.json', rooted_fans.RECIPE)
    states = [run_case(args.parent_root.resolve(), args.output.resolve(), case) for case in args.case]
    study.write(args.output/'SUMMARY.json', dict(cases=args.case,
        both_inputs_complete=set(args.case) == set(study.CASES) and len(args.case) == 2,
        geometry_checks_passed=all(state['checks']['passed'] for state in states), states=states,
        visual_success='NOT_ASSESSED'))
