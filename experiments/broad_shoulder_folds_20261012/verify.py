"""Independent actual-geometry verification of both broad-shoulder inputs.

Replays actual broad measurement, G04/G05 incoming pooled frames, signed
displacements and final G06 clear/active replacement, capping and reflection.
Existing parent-guided geometry, normal, native, topology and symmetry kernels
are reused. Displacement limits and topology choices belong to the experiment
recipe; .30/.45 and fixed connectivity are not universal user requirements.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('broad_verified_previous_geometry',
    HERE.parent/'parent_guided_detail_20261012/verify.py')
previous = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previous)
finish, t, bulb, topology = previous.finish, previous.t, previous.bulb, previous.legacy
CASES = ('SPAN', 'COUNTER')
TOLERANCE = previous.TOLERANCE
require, read_json = previous.require, previous.read_json


def compare_finite(actual, expected, label, tolerance=TOLERANCE):
    actual, expected = np.asarray(actual), np.asarray(expected)
    require(actual.shape == expected.shape and np.isfinite(actual).all() and np.isfinite(expected).all(),
        label+': shape/nonfinite failure.')
    error = float(np.max(np.abs(actual-expected), initial=0.))
    require(error <= tolerance, label+': actual reconstruction exceeds tolerance.')
    return error


def baseline_identity(actual_xyz, generation, main_state):
    """A generation PASS flag alone cannot establish a saved baseline identity."""
    actual_xyz = np.asarray(actual_xyz)
    require(actual_xyz.ndim == 2 and actual_xyz.shape[1] == 3 and np.isfinite(actual_xyz).all(),
        'Finite actual BASELINE XYZ required.')
    actual_hash = finish.array_hash(actual_xyz)
    require(main_state.get('passed') is True and generation.get('checks', {}).get('passed') is True and
        actual_hash == generation['checks']['control_xyz_sha256'] == main_state['control_xyz_sha256'],
        'Actual BASELINE differs from generation/main verification control hashes.')
    return actual_hash


def native_sample_provenance(native_xyz, native_faces, native_chart, records, tolerance=TOLERANCE):
    """Recover actual sampled XYZ/UV from native triangle IDs and barycentrics.

    This geometry proof is independent of the authored curve layout, allowing
    a single broad ridge without the earlier operator's two-branch assumptions.
    UV follows the established affine height/atan2 native-triangle chart.
    """
    xyz, faces, chart = map(np.asarray, (native_xyz, native_faces, native_chart))
    require(xyz.ndim == 2 and xyz.shape[1] == 3 and chart.shape == xyz.shape and
        np.isfinite(xyz).all() and np.isfinite(chart).all() and faces.ndim == 2 and
        faces.shape[1] == 3 and faces.dtype.kind in 'iu' and len(faces) > 0 and
        faces.min() >= 0 and faces.max() < len(xyz), 'Invalid actual native geometry/chart.')
    ids, bary = np.asarray(records['source_triangle_ids']), np.asarray(records['source_barycentric'])
    require(ids.dtype.kind in 'iu' and ids.size > 0 and ids.min() >= 0 and ids.max() < len(faces) and
        bary.shape == ids.shape+(3,) and np.isfinite(bary).all() and
        np.all(bary >= -1e-9) and np.all(bary <= 1.+1e-9) and
        np.allclose(bary.sum(axis=-1), 1., rtol=0., atol=tolerance), 'Invalid native triangle/barycentric source records.')
    triangles = faces[ids]
    reconstructed = np.einsum('...i,...ij->...j', bary, xyz[triangles])
    xyz_error = compare_finite(records['source_xyz'], reconstructed, 'Native sample XYZ', tolerance)
    uv = np.column_stack([chart[:, 0], np.arctan2(chart[:, 2], chart[:, 1])])
    reconstructed_uv = np.einsum('...i,...ij->...j', bary, uv[triangles])
    uv_error = compare_finite(records['source_uv'], reconstructed_uv, 'Native sample material UV', tolerance)
    return dict(passed=True, sample_count=int(ids.size), actual_xyz_max_error=xyz_error,
        actual_material_uv_max_error=uv_error, tolerance=tolerance,
        barycentric_containment_tolerance=1e-9,
        scope='Actual saved source native triangle/barycentric XYZ and affine material UV; no nearest-point substitution or authored-curve quality claim.')


def actual_delta_locality(control_xyz, reference_xyz, saved_delta, baseline_xyz, weight, ends, maximum=None):
    """Exact saved-delta and unchanged-region proof; cap is recipe-specific."""
    control, reference, delta, baseline, weight, ends = map(np.asarray,
        (control_xyz, reference_xyz, saved_delta, baseline_xyz, weight, ends))
    require(control.ndim == 2 and control.shape[1] == 3 and
        reference.shape == delta.shape == baseline.shape == control.shape and
        weight.shape == ends.shape == (len(control),) and
        all(np.isfinite(value).all() for value in (control, reference, delta, baseline, weight)) and
        np.all((weight >= 0.) & (weight <= 1.)) and np.isin(ends, (0, 1)).all(),
        'Invalid actual delta/locality arrays.')
    actual = control-reference
    require(np.array_equal(delta, actual), 'Saved delta differs from actual control minus reference.')
    outside, ends = weight == 0., ends.astype(bool)
    require(np.array_equal(control[outside], baseline[outside]), 'Weight-zero controls differ from exact BASELINE.')
    require(np.array_equal(control[ends], baseline[ends]), 'Fixed-end controls differ from exact BASELINE.')
    measured_maximum = float(np.max(np.linalg.norm(actual, axis=1), initial=0.))
    if maximum is not None:
        require(np.isfinite(maximum) and maximum > 0. and measured_maximum <= maximum+TOLERANCE,
            'Actual total vector displacement exceeds the configured experiment cap.')
    return dict(passed=True, saved_actual_delta_exact=True, unchanged_baseline_controls_exact=True,
        fixed_end_baseline_controls_exact=True, maximum_actual_total_shift=measured_maximum,
        configured_experiment_cap=maximum, outside_control_count=int(outside.sum()),
        fixed_end_control_count=int(ends.sum()),
        scope='Exact locality is this pilot comparison condition; a cap is checked only when explicitly configured.')


def actual_native_guards(native_xyz, baseline_native_xyz, guards):
    native, baseline = np.asarray(native_xyz), np.asarray(baseline_native_xyz)
    require(native.shape == baseline.shape and native.ndim == 2 and native.shape[1] == 3 and
        np.isfinite(native).all() and np.isfinite(baseline).all(), 'Invalid actual native guard geometry.')
    counts = {}
    for label, mask in guards.items():
        mask = np.asarray(mask)
        require(mask.shape == (len(native),) and np.isin(mask, (0, 1)).all(), 'Invalid native '+label+' guard mask.')
        mask = mask.astype(bool)
        require(np.array_equal(native[mask], baseline[mask]), 'Actual native '+label+' differs from exact BASELINE.')
        counts[label] = int(mask.sum())
    return dict(passed=True, exact_native_guard_counts=counts)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def verify_incoming_frame(mesh, chart, native, frame, patch, generation, operators, recipe):
    """Reconstruct the pooled frame from the actual incoming triangle surface."""
    require(int(np.asarray(frame['incoming_generation']).item()) == generation == mesh.generation and
        str(np.asarray(frame['incoming_control_xyz_sha256']).item()) == finish.array_hash(mesh.xyz),
        'Incoming frame generation/control identity differs.')
    require(np.array_equal(frame['parameter'], patch['parameter']) and
        np.array_equal(frame['source_uv'], patch['surface_uv']), 'Frame does not sample the saved measured broad patch.')
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    provenance = native_sample_provenance(native.xyz, native.faces[:, :3], pchart, frame)
    triangles = native.xyz[native.faces[frame['source_triangle_ids'], :3]]
    xyz = np.einsum('...i,...ij->...j', frame['source_barycentric'], triangles)
    normals = bulb.unit(np.cross(triangles[..., 1, :]-triangles[..., 0, :],
        triangles[..., 2, :]-triangles[..., 0, :]))
    arc = np.c_[np.zeros(len(xyz)), np.cumsum(np.linalg.norm(np.diff(xyz, axis=1), axis=2), axis=1)]
    pooled, transverse, axial, lengths = operators.pool_normals(patch['parameter'], arc, normals, recipe)
    actual = dict(parameter=patch['parameter'], source_uv=patch['surface_uv'], source_xyz=xyz,
        source_triangle_ids=frame['source_triangle_ids'], source_barycentric=frame['source_barycentric'],
        actual_triangle_normals=normals, actual_transverse_arc=arc, transverse_weights=transverse,
        axial_weights=axial, pooled_normals=pooled, pooled_vector_lengths=lengths,
        incoming_generation=np.array(generation), incoming_control_xyz_sha256=np.array(finish.array_hash(mesh.xyz)))
    errors = {key: compare_finite(frame[key], actual[key], 'Actual incoming frame '+key)
        for key in ('actual_triangle_normals', 'actual_transverse_arc', 'transverse_weights',
            'axial_weights', 'pooled_normals', 'pooled_vector_lengths')}
    require(np.all(np.diff(arc, axis=1) >= 0.) and np.all(arc[:, -1] > 0.), 'Actual frame has no positive transverse arc.')
    return actual, dict(passed=True, incoming_generation=generation, actual_native_sample_provenance=provenance,
        actual_frame_reconstruction_errors=errors, tolerance=TOLERANCE,
        normal_rule='Actual native triangle normals → physical transverse-arc quadrature → axial pooling; no control local-normal substitution.',
        evidence_scope='Incoming actual stage before its displacement and before final G06 replacement/blend.')


def replay_stage(root, case, mesh, chart, tags, patch, generation, stage, operators, recipe):
    mesh, chart, tags, refinement = t.memory.refine(mesh, chart, tags)
    require(mesh.generation == generation and stage['generation'] == generation and
        finish.array_hash(mesh.xyz) == stage['incoming_xyz_sha256'], 'Actual incoming stage refinement/hash differs.')
    fields_path = root/case/f'G{generation:02d}_active_fields.npz'
    frame_path = root/case/f'G{generation:02d}_incoming_frame.npz'
    require(Path(stage['fields_path']) == fields_path.relative_to(root) and
        Path(stage['frame_path']) == frame_path.relative_to(root) and
        bulb.digest(fields_path) == stage['fields_sha256'] and bulb.digest(frame_path) == stage['frame_sha256'],
        'Stored stage evidence paths/hashes differ.')
    fields, frame = bulb.read_arrays(fields_path), bulb.read_arrays(frame_path)
    require(np.array_equal(fields['input_edges'], refinement['input_edges']) and
        np.array_equal(fields['parent_face'], refinement['parent_face']), 'Stage refinement ancestry differs.')
    native = t.growth.native(mesh)
    actual_frame, frame_receipt = verify_incoming_frame(mesh, chart, native, frame, patch, generation, operators, recipe)
    del native; gc.collect()
    actual_delta, actual_fields = operators.normal_delta(chart, patch, actual_frame, generation, recipe)
    actual_delta_error = compare_finite(fields['delta'], operators.previous.reflect(actual_delta, chart),
        'Actual incoming pooled-frame/PCHIP displacement')
    normal_error = compare_finite(fields['applied_pooled_normals'], actual_fields['applied_pooled_normals'],
        'Actual incoming frame PCHIP applied normals')
    # Exact reproduction uses saved frames already linked above to the actual
    # source surface within tolerance; this keeps floating-point replay honest.
    raw, expected_fields = operators.normal_delta(chart, patch, frame, generation, recipe)
    require(np.isfinite(raw).all() and finish.array_hash(raw) == stage['raw_delta_sha256'],
        'Saved actual-linked frame does not replay the raw delta hash.')
    for name, expected in expected_fields.items():
        require(np.array_equal(fields[name], expected), 'Stored signed/profile/PCHIP field differs: '+name)
    reflected = operators.previous.reflect(raw, chart)
    require(np.array_equal(fields['delta'], reflected) and
        finish.array_hash(fields['delta']) == stage['applied_delta_sha256'], 'Applied delta/reflection/hash differs.')
    mesh.xyz += fields['delta']
    require(np.isfinite(mesh.xyz).all() and finish.array_hash(mesh.xyz) == stage['resulting_xyz_sha256'],
        'Stored delta does not replay the resulting actual stage hash.')
    receipt = dict(passed=True, generation=generation, incoming_xyz_sha256=stage['incoming_xyz_sha256'],
        resulting_xyz_sha256=stage['resulting_xyz_sha256'], incoming_frame=frame_receipt,
        actual_PCHIP_normal_max_error=normal_error, actual_PCHIP_reflected_delta_max_error=actual_delta_error,
        raw_delta_hash_exact=True, stored_fields_reflection_delta_exact=True, resulting_control_hash_exact=True)
    del fields, frame, actual_frame, actual_fields, actual_delta, raw, reflected, expected_fields, refinement; gc.collect()
    return mesh, chart, tags, receipt


MODES = ('CLEAR_ONLY', 'BROAD_ACTIVE')


def inventory(root, parent_root):
    files = [root/'RECIPE.json', root/'SUMMARY.json', parent_root/'VERIFICATION.json']
    for case in CASES:
        files.extend(root/case/name for name in ('actual_patch.npz', 'common_carrier_relaxation.npz', 'SUMMARY.json'))
        files.extend(parent_root/'BASELINE'/case/'G06'/name for name in ('generation.json', 'control_quad.npz'))
        for generation in (4, 5):
            files.extend(root/case/f'G{generation:02d}_{suffix}.npz' for suffix in ('active_fields', 'incoming_frame'))
        for mode in MODES:
            files.extend(root/mode/case/'G06'/name for name in ('generation.json', 'control_quad.npz', 'geometry.npz', 'operation_fields.npz'))
    missing = [str(path) for path in files if not path.is_file()]
    require(not missing, 'Both SPAN/COUNTER and both clear/active states are required: '+', '.join(missing))


def verify_case(root, parent_root, case, parent_verification, runner):
    finish.memory_guard()
    operators, selection, recipe = runner.folds, runner.measure.SELECTION, runner.folds.RECIPE
    metadata = {mode: read_json(root/mode/case/'G06/generation.json') for mode in MODES}
    identity = metadata['BROAD_ACTIVE']
    baseline_path = parent_root/'BASELINE'/case/'G06'
    baseline_info = read_json(baseline_path/'generation.json')
    main_case = parent_verification['cases'][case]
    main_baseline = main_case['states']['BASELINE']
    require(bulb.digest(baseline_path/'generation.json') == main_baseline['generation_json_sha256'],
        'Main BASELINE generation JSON is not bound to the full verification receipt.')
    baseline, baseline_chart, _ = t.load(baseline_path)
    baseline_hash = baseline_identity(baseline.xyz, baseline_info, main_baseline)
    parent_receipt_hash = bulb.digest(parent_root/'VERIFICATION.json')
    case_summary = read_json(root/case/'SUMMARY.json')
    require(case_summary['input_case'] == case and case_summary['geometry_checks_passed'] is True and
        len(case_summary['states']) == 2 and {item['candidate'] for item in case_summary['states']} == set(MODES),
        'Case summary does not include both complete alternatives.')
    patch_path = root/case/'actual_patch.npz'
    patch_hash = bulb.digest(patch_path)
    for mode, info in metadata.items():
        require(info['input_case'] == case and info['candidate'] == mode and info['output_generation'] == 6 and
            info['recipe'] == recipe and info['selection_recipe'] == selection and info['checks']['passed'] is True and
            info['new_bulb_evaluations'] == 0 and info['field_iteration_count_added'] == 0,
            'Candidate case/generation/recipe/no-new-bulb identity differs.')
        require(info['baseline_control_sha256'] == bulb.digest(baseline_path/'control_quad.npz') and
            info['parent_verification_sha256'] == parent_receipt_hash and info['patch_sha256'] == patch_hash and
            Path(info['patch_path']) == patch_path.relative_to(root), 'Candidate baseline/main/patch identity differs.')
        for key in ('source_control_sha256', 'common_reference_xyz_sha256', 'relaxation_recipe'):
            require(info[key] == baseline_info[key], 'Candidate common source/reference/relaxation differs: '+key)
    require(metadata['CLEAR_ONLY']['stages'] == [] and
        [item['generation'] for item in identity['stages']] == [4, 5], 'Clear has no active lineage; active requires ordered G04/G05.')
    source = operators.previous._source(parent_root, case, baseline_info)
    require(bulb.digest(source/'control_quad.npz') == identity['source_control_sha256'], 'Actual G03 source hash differs.')
    mesh, chart, tags = t.load(source)
    require(mesh.generation == 3 and identity['relaxation_recipe'] == finish.RELAXATION, 'Wrong G03/common relaxation recipe.')
    relaxation = finish.relax_carrier(mesh, chart, identity['relaxation_recipe'])
    with np.load(root/case/'common_carrier_relaxation.npz', allow_pickle=False) as saved:
        require(np.array_equal(saved['delta'], relaxation), 'Actual common carrier relaxation did not replay exactly.')
    patch = bulb.read_arrays(patch_path)
    actual_patch = runner.measure.measure_patch(mesh, chart, selection)
    require(set(patch) == set(actual_patch), 'Actual broad measurement fields differ.')
    patch_errors = {}
    for name, expected in actual_patch.items():
        if np.asarray(expected).dtype.kind in 'bifuc':
            patch_errors[name] = compare_finite(patch[name], expected, 'Actual measured patch '+name)
        else:
            require(np.array_equal(patch[name], expected), 'Measured patch identity/definition differs: '+name)
    width = dict(minimum=float(np.min(actual_patch['physical_width'])),
        median=float(np.median(actual_patch['physical_width'])), maximum=float(np.max(actual_patch['physical_width'])))
    del actual_patch; gc.collect()
    common, common_chart, common_tags = copy.deepcopy(mesh), chart.copy(), tags.copy()
    for _ in range(3):
        common, common_chart, common_tags, _ = t.memory.refine(common, common_chart, common_tags)
    reference = common.xyz
    reference_hash = finish.array_hash(reference)
    require(reference_hash == identity['common_reference_xyz_sha256'] == main_case['common_reference_xyz_sha256'],
        'Actual G03 relaxation and three inactive splits do not rebuild the exact common G06 reference.')
    stages = []
    for generation, stage in zip((4, 5), identity['stages']):
        mesh, chart, tags, receipt = replay_stage(root, case, mesh, chart, tags, patch, generation, stage, operators, recipe)
        stages.append(receipt)
    mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    require(mesh.generation == 6 and np.array_equal(chart, common_chart) and np.array_equal(chart, baseline_chart) and
        np.array_equal(mesh.faces, common.faces) and np.array_equal(mesh.faces, baseline.faces) and
        np.array_equal(common.classes, baseline.classes) and common.surface == baseline.surface,
        'Final source/BASELINE control, chart or native fan correspondence differs.')
    active_delta = mesh.xyz-reference
    weight, controls, fans = operators.guarded_weight(mesh, chart, patch, recipe)
    require(np.isfinite(active_delta).all() and np.isfinite(weight).all(), 'Nonfinite actual accumulated active displacement/weight.')
    pairs, pair_receipts = previous.reflection_pairs(common, chart)
    baseline_native = np.concatenate([baseline.xyz, t.face_values(baseline, baseline.xyz)])
    guards = dict(outside=np.r_[controls['weight'] == 0., fans['weight'] == 0.],
        ends=np.r_[controls['ends'], fans['ends']])
    reference_native = t.growth.native(common)
    require(main_case['actual_native_topology']['passed'] and main_case['actual_native_topology']['components'] == 1,
        'Main BASELINE actual native topology is not one closed oriented body.')
    states = {}
    for mode in MODES:
        info, folder = metadata[mode], root/mode/case/'G06'
        current_active = active_delta if mode == 'BROAD_ACTIVE' else np.zeros_like(active_delta)
        expected_xyz = runner.compose(reference, baseline.xyz, current_active, weight, chart, recipe)
        saved_mesh, saved_chart, _ = t.load(folder)
        expected_hash = finish.array_hash(expected_xyz)
        require(saved_mesh.generation == 6 and np.array_equal(saved_mesh.xyz, expected_xyz) and
            np.array_equal(saved_chart, chart) and np.array_equal(saved_mesh.faces, common.faces) and
            np.array_equal(saved_mesh.classes, common.classes) and saved_mesh.surface == common.surface and
            expected_hash == info['checks']['control_xyz_sha256'], 'Final '+mode+' patch blend/cap/reflection/restoration replay is not exact.')
        fields = bulb.read_arrays(folder/'operation_fields.npz')
        require(np.array_equal(fields['reference_xyz'], reference) and np.array_equal(fields['blend_weight'], weight) and
            np.array_equal(fields['active_delta'], current_active), 'Final reference/shared patch/active displacement fields differ.')
        delta_receipt = actual_delta_locality(saved_mesh.xyz, reference, fields['delta'], baseline.xyz,
            weight, controls['ends'], maximum=recipe.get('maximum_total_shift'))
        native = t.growth.native(saved_mesh)
        with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
            require(np.array_equal(native.xyz, saved['xyz']) and np.array_equal(native.faces[:, :3], saved['faces']),
                'Saved native geometry differs from actual saved control/fan reconstruction.')
        xyz_hash, faces_hash = finish.array_hash(native.xyz), finish.array_hash(native.faces[:, :3])
        require(np.isfinite(native.xyz).all() and xyz_hash == info['checks']['native_xyz_sha256'] and
            faces_hash == info['checks']['native_faces_sha256'] == main_baseline['native_faces_sha256'],
            'Actual native geometry/face hash is not linked to the generation and verified closed BASELINE.')
        symmetry = previous.coordinate_symmetry(native.xyz, pairs, pair_receipts)
        guard_receipt = actual_native_guards(native.xyz, baseline_native, guards)
        area = finish.minimum_area(native.xyz, native.faces[:, :3])
        require(np.isfinite(area) and area > 1e-14, 'Actual native triangle area failed.')
        changed = np.linalg.norm(native.xyz-baseline_native, axis=1) > 1e-12
        support = runner.area_support(reference_native, changed)
        for name, measured in support.items():
            if isinstance(measured, (float, int)):
                require(abs(measured-info['checks']['support'][name]) <= TOLERANCE,
                    'Actual affected-reference-area/count receipt differs: '+name)
        require(int(changed.sum()) == info['checks']['actual_changed_native_vertices'], 'Actual changed-native count receipt differs.')
        states[mode] = dict(passed=True, actual_delta=delta_receipt, actual_native_guards=guard_receipt,
            final_control_xyz_sha256=expected_hash, native_xyz_sha256=xyz_hash, native_faces_sha256=faces_hash,
            native_control_rebuild_exact=True, actual_native_coordinate_symmetry=symmetry,
            minimum_actual_native_triangle_area=area, actual_changed_native_vertices=int(changed.sum()),
            affected_reference_area=support, generation_json_sha256=bulb.digest(folder/'generation.json'),
            topology_scope='Identical actual native faces to main independently verified closed oriented one-component BASELINE; no new connectivity.',
            symmetry_scope='Actual X/Y native XYZ pair checks with material-chart involutions; same inherited native faces, oriented triangle reflection not recomputed here.',
            final_G06_postprocessing='Inactive refinement → same measured broad patch replacement with BASELINE → configured total-vector bound → material reflection → exact weight-zero BASELINE restoration.')
        del native, saved_mesh, saved_chart, expected_xyz, fields, changed; gc.collect()
    return dict(passed=True, input_case=case, baseline_control_xyz_sha256=baseline_hash,
        baseline_generation_main_receipt_linked=True, actual_measured_patch_replayed=True,
        measurement_reconstruction_errors=patch_errors, actual_physical_width=width,
        common_reference_reconstructed_exact=True, common_reference_xyz_sha256=reference_hash,
        active_stages=stages, states=states,
        comparison_scope='CLEAR_ONLY and BROAD_ACTIVE share actual patch/weight/carrier/BASELINE; clearing does not run active stages. Residual old detail remains outside and in the taper.',
        clearing_scope='Only the saved BASELINE-minus-common-reference finish is replaced locally; inherited G03 geometry/history is retained. This is not whole-column fractal removal.',
        visual_success='NOT_ASSESSED: width, area, displacement and normal validity are not aesthetic success scores.')


def run(root, parent_root):
    root, parent_root = Path(root).resolve(), Path(parent_root).resolve()
    inventory(root, parent_root)
    runner = load_module('verified_broad_shoulder_runner', HERE/'study.py')
    recipe, summary = read_json(root/'RECIPE.json'), read_json(root/'SUMMARY.json')
    expected_recipe = dict(selection=runner.measure.SELECTION, folds=runner.folds.RECIPE, cases=list(CASES), modes=list(MODES))
    require(recipe == expected_recipe and summary['both_inputs_complete'] is True and
        summary['geometry_checks_passed'] is True and len(summary['cases']) == 2 and set(summary['cases']) == set(CASES) and
        len(summary['states']) == 4, 'Both cases and both modes with one common frozen recipe are required.')
    parent_verification = read_json(parent_root/'VERIFICATION.json')
    require(parent_verification['status'] == 'PASS' and set(parent_verification['cases']) == set(CASES),
        'Complete main SPAN/COUNTER verification PASS required.')
    cases = {case: verify_case(root, parent_root, case, parent_verification, runner) for case in CASES}
    return dict(status='PASS', root=str(root), parent_root=str(parent_root), expected_cases=list(CASES),
        expected_modes=list(MODES), recipe=recipe, cases=cases,
        parent_verification_sha256=bulb.digest(parent_root/'VERIFICATION.json'),
        verifier_module_sha256=bulb.digest(Path(__file__)),
        scope='Actual broad measurement and incoming-native triangle/arc/pool/PCHIP frame proof, ordered G04/G05 active replay, exact G06 clearing/active composition, saved native geometry, coordinate symmetry and baseline locality/topology linkage.',
        excluded=['Aesthetic/reference fidelity certification', 'Automatic semantic shoulder detection', 'Self-intersections', 'Fabrication', 'Structural performance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, required=True)
    args = parser.parse_args()
    output = args.root/'VERIFICATION.json'
    if output.exists():
        raise FileExistsError('Existing broad verification receipt preserved: '+str(output))
    try:
        receipt = run(args.root, args.parent_root)
    except Exception as error:
        receipt = dict(status='FAIL', root=str(args.root.resolve()), parent_root=str(args.parent_root.resolve()),
            error_type=type(error).__name__, error=str(error))
        with output.open('x', encoding='utf8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        raise
    with output.open('x', encoding='utf8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print('BROAD_SHOULDER_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
