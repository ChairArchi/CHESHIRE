"""Matched broad-shoulder clearing and active-fold geometry on two saved inputs.

All large outputs go to a fresh E data directory. Earlier checkpoints remain
read-only. CLEAR_ONLY and BROAD_ACTIVE share the exact same source, relaxation,
actual measured patch and final replacement envelope. They are alternatives at
G6, not consecutive generations.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import folds
import measure

previous, finish, bulb, t = folds.previous, folds.finish, folds.bulb, folds.t
_spec = importlib.util.spec_from_file_location('broad_previous_verify',
    HERE.parent/'parent_guided_detail_20261012/verify.py')
checks_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checks_module)
CASES = ('SPAN', 'COUNTER')
MODES = ('CLEAR_ONLY', 'BROAD_ACTIVE')


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def compose(reference, baseline, active_delta, weight, chart, recipe):
    result = folds.final_positions(reference, baseline, active_delta, weight, recipe)
    total = previous.reflect(result-reference, chart)
    result = reference+total
    result[weight == 0.] = baseline[weight == 0.]
    return result


def area_support(native, changed, chunk=120000):
    """Actual reference areas, not vertex counts or visual-success scores."""
    total, affected, triangle_count = 0., 0., 0
    for start in range(0, len(native.faces), chunk):
        tri = native.faces[start:start+chunk, :3]
        xyz = native.xyz[tri]
        area = .5*np.linalg.norm(np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0]), axis=1)
        mask = np.any(changed[tri], axis=1)
        total += float(area.sum())
        affected += float(area[mask].sum())
        triangle_count += int(mask.sum())
    return dict(reference_total_native_area=total, reference_area_of_affected_triangles=affected,
        affected_reference_area_fraction=affected/total, affected_triangles=triangle_count,
        scope='Reference triangles incident to actually changed native XYZ; not projected visible area or a quality score')


def run_case(parent_root, output, case):
    finish.memory_guard()
    case_root = output/case
    if case_root.exists():
        raise FileExistsError('Preserved case already exists: '+str(case_root))
    base_path = parent_root/'BASELINE'/case/'G06'
    baseline_metadata = json.loads((base_path/'generation.json').read_text(encoding='utf8'))
    source = previous._source(parent_root, case, baseline_metadata)
    mesh, chart, tags = t.load(source)
    if mesh.generation != 3:
        raise ValueError('Actual WALL G3 source required.')
    carrier_delta = finish.relax_carrier(mesh, chart, baseline_metadata['relaxation_recipe'])
    patch = measure.measure_patch(mesh, chart)
    case_root.mkdir(parents=True)
    np.savez_compressed(case_root/'actual_patch.npz', **patch)
    np.savez_compressed(case_root/'common_carrier_relaxation.npz', delta=carrier_delta)
    common, common_chart, common_tags = copy.deepcopy(mesh), chart.copy(), tags.copy()
    for _ in range(3):
        common, common_chart, common_tags, _ = t.memory.refine(common, common_chart, common_tags)
    reference = common.xyz
    if finish.array_hash(reference) != baseline_metadata['common_reference_xyz_sha256']:
        raise ValueError('The preserved common G6 reference did not replay exactly.')
    stages = []
    for generation in (4, 5):
        mesh, chart, tags, ancestry = t.memory.refine(mesh, chart, tags)
        incoming_hash = finish.array_hash(mesh.xyz)
        frame = folds.incoming_frame(mesh, chart, patch)
        frame_path = case_root/f'G{generation:02d}_incoming_frame.npz'
        np.savez_compressed(frame_path, **frame)
        delta, fields = folds.normal_delta(chart, patch, frame, generation)
        raw_hash = finish.array_hash(delta)
        previous.reflect(delta, chart)
        mesh.xyz += delta
        fields_path = case_root/f'G{generation:02d}_active_fields.npz'
        np.savez_compressed(fields_path, delta=delta, input_edges=ancestry['input_edges'],
            parent_face=ancestry['parent_face'], **fields)
        stages.append(dict(generation=generation, incoming_xyz_sha256=incoming_hash,
            raw_delta_sha256=raw_hash, applied_delta_sha256=finish.array_hash(delta),
            resulting_xyz_sha256=finish.array_hash(mesh.xyz),
            fields_path=str(fields_path.relative_to(output)), fields_sha256=bulb.digest(fields_path),
            frame_path=str(frame_path.relative_to(output)), frame_sha256=bulb.digest(frame_path),
            maximum_active_shift=float(np.linalg.norm(delta, axis=1).max()),
            moved_controls=int(np.count_nonzero(np.linalg.norm(delta, axis=1) > 1e-12))))
        print('ACTIVE_STAGE', case, generation, stages[-1]['maximum_active_shift'], flush=True)
        del frame, delta, fields, ancestry
        gc.collect()
    mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    baseline, baseline_chart, _ = t.load(base_path)
    if not (np.array_equal(chart, common_chart) and np.array_equal(chart, baseline_chart) and
            np.array_equal(mesh.faces, common.faces) and np.array_equal(mesh.faces, baseline.faces)):
        raise ValueError('Final topology or material correspondence differs.')
    if finish.array_hash(baseline.xyz) != baseline_metadata['checks']['control_xyz_sha256']:
        raise ValueError('Preserved baseline control XYZ differs from its receipt.')
    active_delta = mesh.xyz-reference
    weight, control_ownership, fan_ownership = folds.guarded_weight(mesh, chart, patch)
    pairs, pair_receipts = checks_module.reflection_pairs(mesh, chart)
    baseline_native_xyz = np.concatenate([baseline.xyz, t.face_values(baseline, baseline.xyz)])
    outside = np.r_[control_ownership['weight'] == 0., fan_ownership['weight'] == 0.]
    ends = np.r_[control_ownership['ends'], fan_ownership['ends']]
    reference_native = t.growth.native(common)
    receipts = []
    for mode in MODES:
        current_active = active_delta if mode == 'BROAD_ACTIVE' else np.zeros_like(active_delta)
        result = compose(reference, baseline.xyz, current_active, weight, chart, folds.RECIPE)
        result_mesh = copy.copy(common)
        result_mesh.xyz = result
        native = t.growth.native(result_mesh)
        total = result-reference
        symmetry = checks_module.coordinate_symmetry(native.xyz, pairs, pair_receipts)
        faces_hash = finish.array_hash(native.faces[:, :3])
        minimum_area = finish.minimum_area(native.xyz, native.faces[:, :3])
        changed = np.linalg.norm(native.xyz-baseline_native_xyz, axis=1) > 1e-12
        support = area_support(reference_native, changed)
        checked = dict(finite=bool(np.isfinite(native.xyz).all()), minimum_triangle_area=minimum_area,
            actual_native_xy_symmetry=symmetry, native_faces_sha256=faces_hash,
            inherited_native_faces_identical_to_baseline=faces_hash == baseline_metadata['checks']['native_faces_sha256'],
            native_xyz_sha256=finish.array_hash(native.xyz), control_xyz_sha256=finish.array_hash(result),
            actual_native_outside_baseline_exact=bool(np.array_equal(native.xyz[outside], baseline_native_xyz[outside])),
            actual_native_ends_baseline_exact=bool(np.array_equal(native.xyz[ends], baseline_native_xyz[ends])),
            maximum_total_shift=float(np.linalg.norm(total, axis=1).max()),
            actual_changed_native_vertices=int(changed.sum()), control_patch_count=int(np.count_nonzero(weight)),
            outside_native_count=int(outside.sum()), support=support)
        checked['passed'] = bool(checked['finite'] and minimum_area > 1e-14 and
            checked['inherited_native_faces_identical_to_baseline'] and
            checked['actual_native_outside_baseline_exact'] and checked['actual_native_ends_baseline_exact'] and
            checked['maximum_total_shift'] <= folds.RECIPE['maximum_total_shift']+3e-12)
        folder = output/mode/case/'G06'
        folder.mkdir(parents=True)
        np.savez_compressed(folder/'control_quad.npz', xyz=result, faces=common.faces, chart=chart,
            classes=common.classes, rest=common.rest, anchors=common.anchors,
            generation=np.array(6), surface=np.array(common.surface), memory=common_tags)
        np.savez_compressed(folder/'geometry.npz', xyz=native.xyz, faces=native.faces[:, :3])
        np.savez_compressed(folder/'operation_fields.npz', reference_xyz=reference, delta=total,
            blend_weight=weight, active_delta=current_active)
        metadata = dict(input_case=case, candidate=mode, source=str(source),
            source_control_sha256=bulb.digest(source/'control_quad.npz'), baseline_source=str(base_path),
            baseline_control_sha256=bulb.digest(base_path/'control_quad.npz'),
            parent_verification_sha256=bulb.digest(parent_root/'VERIFICATION.json'),
            common_reference_xyz_sha256=finish.array_hash(reference),
            relaxation_recipe=baseline_metadata['relaxation_recipe'],
            selection_recipe=measure.SELECTION, recipe=folds.RECIPE,
            patch_path=str((case_root/'actual_patch.npz').relative_to(output)),
            patch_sha256=bulb.digest(case_root/'actual_patch.npz'),
            stages=stages if mode == 'BROAD_ACTIVE' else [], output_generation=6,
            field_iteration_count_added=0, new_bulb_evaluations=0,
            lineage='G3 relaxed source; G4/G5 active only for BROAD_ACTIVE; G6 refinement then broad patch replacement/blend/bound/reflection/exact outside restoration',
            comparison='Same broad replacement patch for CLEAR_ONLY/BROAD_ACTIVE, preserving existing BASELINE outside; these are alternatives at actual G6',
            topology_scope='Same actual native triangle IDs as verified closed oriented BASELINE; independent verifier links actual faces and saved baseline receipt',
            self_intersection='NOT_CHECKED_EXPLORATORY', visual_success='NOT_ASSESSED', checks=checked)
        write(folder/'generation.json', metadata)
        receipts.append(metadata)
        print('SAVED', mode, case, checked['passed'], checked['maximum_total_shift'],
            'area_fraction', support['affected_reference_area_fraction'], flush=True)
        del native, result_mesh, result, total, changed
        gc.collect()
        if not checked['passed']:
            raise ValueError('Failed result preserved: '+str(folder))
    for filename in ('folds.py', 'measure.py', 'study.py'):
        shutil.copy2(HERE/filename, case_root/filename)
    write(case_root/'SUMMARY.json', dict(input_case=case, states=receipts,
        geometry_checks_passed=all(item['checks']['passed'] for item in receipts),
        visual_success='NOT_ASSESSED'))
    del mesh, baseline, common, reference_native, baseline_native_xyz, pairs, active_delta
    gc.collect()
    return receipts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case):
        parser.error('Repeated cases are not allowed.')
    output = args.output.resolve()
    recipe = dict(selection=measure.SELECTION, folds=folds.RECIPE, cases=list(CASES), modes=list(MODES))
    output.mkdir(parents=True, exist_ok=True)
    recipe_path = output/'RECIPE.json'
    if recipe_path.exists():
        if json.loads(recipe_path.read_text(encoding='utf8')) != recipe:
            raise FileExistsError('Existing output recipe differs.')
    else:
        write(recipe_path, recipe)
    for case in args.case:
        run_case(args.parent_root.resolve(), output, case)
    summaries = [json.loads((output/case/'SUMMARY.json').read_text(encoding='utf8'))
        for case in CASES if (output/case/'SUMMARY.json').is_file()]
    write(output/'SUMMARY.json', dict(cases=[item['input_case'] for item in summaries],
        both_inputs_complete=len(summaries) == 2,
        geometry_checks_passed=all(item['geometry_checks_passed'] for item in summaries),
        visual_success='NOT_ASSESSED', states=[state for item in summaries for state in item['states']]))
