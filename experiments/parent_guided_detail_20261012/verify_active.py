"""Independent saved-state verification of both ACTIVE_FOLDS inputs.

Replays actual G03 relaxation, G04/G05 incoming-native normal operations and
G06 refinement followed by patch replacement/capping/exact restoration.
Curve evidence refers to incoming active stages before the final G06 blend.
No rendering, atlas evaluation, aesthetic or self-intersection certification.
Only a new verification receipt is written; all checkpoints remain read-only.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


active = module('verified_active_fold_operator', HERE/'active_folds.py')
main_verify = module('verified_active_main_receipts', HERE/'verify.py')
finish, bulb, t = active.finish, active.bulb, active.t
CASES = ('SPAN', 'COUNTER')
TOLERANCE = 3e-12


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def close(actual, expected, label, tolerance=TOLERANCE):
    actual, expected = np.asarray(actual), np.asarray(expected)
    require(actual.shape == expected.shape and np.isfinite(actual).all() and np.isfinite(expected).all(),
        label+': shape/nonfinite failure.')
    error = float(np.max(np.abs(actual-expected), initial=0.))
    require(error <= tolerance, label+': actual coordinate/field error exceeds tolerance.')
    return error


def inventory(root, parent_root):
    files = [root/'RECIPE.json', root/'SUMMARY.json', parent_root/'VERIFICATION.json']
    for case in CASES:
        files.extend(root/'ACTIVE_FOLDS'/case/'G06'/name for name in
            ('generation.json', 'control_quad.npz', 'geometry.npz', 'operation_fields.npz'))
        files.extend(parent_root/'BASELINE'/case/'G06'/name for name in ('generation.json', 'control_quad.npz'))
        for generation in (4, 5):
            files.extend(root/case/f'G{generation:02d}_{suffix}.npz' for suffix in ('active_fields', 'incoming_curves'))
        for name in ('actual_parent_0.npz', 'actual_parent_1.npz', 'common_carrier_relaxation.npz'):
            files.extend((root/case/name, parent_root/case/name))
    missing = [str(path) for path in files if not path.is_file()]
    require(not missing, 'Both SPAN/COUNTER complete assets are required: '+', '.join(missing))


def curve_provenance(records, mesh, chart, native, parent, generation, recipe):
    """Recover actual incoming XYZ and chart UV directly from saved triangles."""
    require(int(np.asarray(records['incoming_generation']).item()) == generation and
        str(np.asarray(records['source_control_xyz_sha256']).item()) == finish.array_hash(mesh.xyz),
        'Curve evidence incoming generation/control hash differs.')
    ids, bary = np.asarray(records['source_triangle_ids']), np.asarray(records['source_barycentric'])
    require(ids.ndim == 2 and ids.dtype.kind in 'iu' and ids.size > 0 and
        ids.min() >= 0 and ids.max() < len(native.faces) and bary.shape == ids.shape+(3,) and
        np.isfinite(bary).all() and np.all(bary >= -1e-9) and np.all(bary <= 1.+1e-9) and
        np.allclose(bary.sum(axis=-1), 1., rtol=0., atol=TOLERANCE), 'Invalid incoming curve triangle/barycentric records.')
    triangles = native.faces[ids, :3]
    triangle_xyz = native.xyz[triangles]
    xyz = np.einsum('...i,...ij->...j', bary, triangle_xyz)
    xyz_error = close(records['source_xyz'], xyz, 'Curve source XYZ')
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    uv = np.column_stack([pchart[:, 0], np.arctan2(pchart[:, 2], pchart[:, 1])])
    recovered_uv = np.einsum('...i,...ij->...j', bary, uv[triangles])
    uv_error = close(records['source_uv'], recovered_uv, 'Curve triangle UV')
    normal = bulb.unit(np.cross(triangle_xyz[..., 1, :]-triangle_xyz[..., 0, :],
        triangle_xyz[..., 2, :]-triangle_xyz[..., 0, :]))
    normal_error = close(records['actual_triangle_normals'], normal, 'Curve actual triangle normal')
    q = np.linspace(-.90, .90, recipe['curve_sample_count'])
    require(np.array_equal(records['q'], q), 'Incoming curve stations differ from recipe.')
    parameter = parent['parameter'][0]+(q+1.)*.5*np.ptp(parent['parameter'])
    centre, gate = active.curves(q, recipe)
    labels = np.array(['TRUNK', 'BRANCH_UPPER', 'BRANCH_LOWER'])
    if generation == 5:
        centre = centre[1:]+np.array([recipe['secondary_offset_arc'], -recipe['secondary_offset_arc']])[:, None]
        gate = np.array([active.guidance._quintic((q-start-recipe['secondary_start_delay'])/
            recipe['branch_gate_span']) for start in recipe['branch_starts']])
        labels = np.array(['SIDE_UPPER', 'SIDE_LOWER'])
    require(np.array_equal(records['curve_labels'], labels) and
        np.array_equal(records['physical_arc_fraction'], centre) and np.array_equal(records['activation'], gate),
        'Authored incoming curve recipe/labels differ.')
    expected_uv = np.stack([active.guidance._uv_at_fraction(parameter, line, parent) for line in centre])
    recipe_uv_error = close(records['source_uv'], expected_uv, 'Authored curve material UV')
    tangent = np.gradient(xyz, parameter, axis=1)
    tangent = bulb.unit(tangent-normal*np.sum(tangent*normal, axis=2)[..., None])
    tangent_error = close(records['actual_curve_tangent'], tangent, 'Curve actual incoming tangent')
    return dict(passed=True, incoming_generation=generation, triangle_sample_count=int(ids.size),
        xyz_max_error=xyz_error, chart_uv_max_error=uv_error, authored_uv_max_error=recipe_uv_error,
        actual_triangle_normal_max_error=normal_error, actual_curve_tangent_max_error=tangent_error,
        tolerance=TOLERANCE, barycentric_containment_tolerance=1e-9,
        scope='Actual incoming native triangle/UV/XYZ/normal/tangent provenance before this active operation and before final G06 replacement/blend; authored curves are not detected final branches.')


def replay_stage(root, case, mesh, chart, tags, parent, parents, generation, stage, recipe):
    mesh, chart, tags, operator = t.memory.refine(mesh, chart, tags)
    require(mesh.generation == generation and stage['generation'] == generation and
        finish.array_hash(mesh.xyz) == stage['incoming_xyz_sha256'], 'Active incoming refinement generation/hash differs.')
    fields_path = root/case/f'G{generation:02d}_active_fields.npz'
    curve_path = root/case/f'G{generation:02d}_incoming_curves.npz'
    require(Path(stage['fields_path']) == fields_path.relative_to(root) and
        Path(stage['curve_path']) == curve_path.relative_to(root) and
        bulb.digest(fields_path) == stage['fields_sha256'] and bulb.digest(curve_path) == stage['curve_sha256'],
        'Saved active evidence paths/hashes differ.')
    fields, records = bulb.read_arrays(fields_path), bulb.read_arrays(curve_path)
    require(np.array_equal(fields['input_edges'], operator['input_edges']) and
        np.array_equal(fields['parent_face'], operator['parent_face']), 'Active stage refinement ancestry differs.')
    native = t.growth.native(mesh)
    actual_normals = bulb.unit(finish.stream_control_normals(native.xyz, native.faces[:, :3], len(mesh.xyz)))
    normal_error = close(fields['incoming_normals'], actual_normals, 'Stored versus independently recalculated incoming native normals')
    curve_receipt = curve_provenance(records, mesh, chart, native, parent, generation, recipe)
    del native, records, actual_normals; gc.collect()
    height, expected_fields = active.signed_height(chart, parent, parents, generation, recipe)
    for key, expected in expected_fields.items():
        require(np.array_equal(fields[key], expected), 'Active signed-band/ownership field differs: '+key)
    normals = fields['incoming_normals']
    tangent = active.guidance._interp(chart[:, 0], parent['parameter'], parent['parent_tangent'])
    tangent[:, :2] *= np.where(chart[:, 1:] < 0., -1., 1.)
    tangent = bulb.unit(tangent-normals*np.sum(tangent*normals, axis=1)[:, None])
    tangent_error = close(fields['projected_parent_tangent'], tangent, 'Actual-normal projected parent tangent')
    raw = height[:, None]*normals
    require(np.isfinite(raw).all() and finish.array_hash(raw) == stage['raw_delta_sha256'],
        'Raw active displacement hash does not match height times actual-linked stored normals.')
    applied = active.reflect(raw, chart)
    require(np.array_equal(applied, fields['delta']) and
        finish.array_hash(fields['delta']) == stage['applied_delta_sha256'], 'Saved active delta/reflection/hash differs.')
    mesh.xyz += fields['delta']
    require(np.isfinite(mesh.xyz).all() and finish.array_hash(mesh.xyz) == stage['resulting_xyz_sha256'],
        'Applied active delta does not replay the resulting stage hash.')
    receipt = dict(passed=True, generation=generation, incoming_xyz_sha256=stage['incoming_xyz_sha256'],
        resulting_xyz_sha256=stage['resulting_xyz_sha256'], actual_incoming_native_normals_max_error=normal_error,
        projected_parent_tangent_max_error=tangent_error, normal_tolerance=TOLERANCE,
        raw_delta_hash_exact=True, applied_delta_and_material_reflection_exact=True,
        actual_native_curve_provenance=curve_receipt)
    del fields, expected_fields, normals, tangent, height, raw, applied, operator; gc.collect()
    return mesh, chart, tags, receipt


def verify_case(root, parent_root, case, parent_verification, recipe):
    finish.memory_guard()
    folder, baseline_path = root/'ACTIVE_FOLDS'/case/'G06', parent_root/'BASELINE'/case/'G06'
    info, baseline_info = read_json(folder/'generation.json'), read_json(baseline_path/'generation.json')
    require(info['input_case'] == case and info['candidate'] == 'ACTIVE_FOLDS' and
        info['output_generation'] == 6 and info['recipe'] == recipe and info['checks']['passed'] is True,
        'Wrong/failing ACTIVE_FOLDS identity/recipe.')
    baseline_receipt = parent_verification['cases'][case]['states']['BASELINE']
    require(baseline_receipt['passed'] is True and
        bulb.digest(baseline_path/'generation.json') == baseline_receipt['generation_json_sha256'],
        'Main BASELINE generation receipt does not bind to the prior full verification.')
    baseline, baseline_chart, _ = t.load(baseline_path)
    baseline_hash = finish.array_hash(baseline.xyz)
    require(baseline_hash == baseline_info['checks']['control_xyz_sha256'] == baseline_receipt['control_xyz_sha256'] and
        bulb.digest(baseline_path/'control_quad.npz') == info['baseline_control_sha256'],
        'Actual BASELINE control XYZ/file identity differs from main generation/full-verification receipts.')
    source = active._source(parent_root, case, baseline_info)
    require(bulb.digest(source/'control_quad.npz') == info['source_control_sha256'] == baseline_info['source_control_sha256'] and
        info['relaxation_recipe'] == baseline_info['relaxation_recipe'] == finish.RELAXATION,
        'Actual G03 source or common relaxation identity differs.')
    mesh, chart, tags = t.load(source)
    require(mesh.generation == 3, 'Actual source must be G03.')
    relaxation = finish.relax_carrier(mesh, chart, info['relaxation_recipe'])
    for source_root in (root, parent_root):
        with np.load(source_root/case/'common_carrier_relaxation.npz', allow_pickle=False) as saved:
            require(np.array_equal(saved['delta'], relaxation), 'Saved carrier relaxation does not replay exactly.')
    parents = [bulb.read_arrays(parent_root/case/f'actual_parent_{i}.npz') for i in (0, 1)]
    for index, parent in enumerate(parents):
        require(bulb.digest(root/case/f'actual_parent_{index}.npz') ==
            bulb.digest(parent_root/case/f'actual_parent_{index}.npz') and
            str(parent['measured_carrier_xyz_sha256']) == finish.array_hash(mesh.xyz), 'Parent evidence/carrier identity differs.')
    parent = parents[recipe['parent_index']]
    common, common_chart, common_tags = copy.deepcopy(mesh), chart.copy(), tags.copy()
    for _ in range(3):
        common, common_chart, common_tags, _ = t.memory.refine(common, common_chart, common_tags)
    reference = common.xyz
    reference_hash = finish.array_hash(reference)
    require(reference_hash == info['common_reference_xyz_sha256'] == baseline_info['common_reference_xyz_sha256'] ==
        parent_verification['cases'][case]['common_reference_xyz_sha256'], 'Actual common reference hash differs.')
    require([stage['generation'] for stage in info['stages']] == [4, 5], 'Both ordered active stages are required.')
    stages = []
    for generation, stage in zip((4, 5), info['stages']):
        mesh, chart, tags, receipt = replay_stage(root, case, mesh, chart, tags, parent, parents, generation, stage, recipe)
        stages.append(receipt)
    mesh, chart, tags, _ = t.memory.refine(mesh, chart, tags)
    require(mesh.generation == 6 and np.array_equal(chart, common_chart) and np.array_equal(mesh.faces, common.faces) and
        np.array_equal(baseline_chart, chart) and np.array_equal(baseline.faces, mesh.faces) and
        np.array_equal(baseline.classes, mesh.classes) and baseline.surface == mesh.surface, 'Final inherited control/native correspondence differs.')
    # Exact original order: inactive split, cap active total, replacement blend,
    # cap total relative to reference, material reflect, exact BASELINE restore.
    active_delta = active.reflect(active._bound(mesh.xyz-reference, recipe['maximum_total_shift']), chart)
    weight, control, fan = active._restore_guarded_weights(mesh, chart, parent, parents, recipe)
    mesh.xyz = baseline.xyz+weight[:, None]*(reference+active_delta-baseline.xyz)
    total = active.reflect(active._bound(mesh.xyz-reference, recipe['maximum_total_shift']), chart)
    mesh.xyz = reference+total
    mesh.xyz[weight == 0.] = baseline.xyz[weight == 0.]
    expected_hash = finish.array_hash(mesh.xyz)
    saved_mesh, saved_chart, _ = t.load(folder)
    require(saved_mesh.generation == 6 and np.array_equal(saved_mesh.xyz, mesh.xyz) and
        np.array_equal(saved_chart, chart) and np.array_equal(saved_mesh.faces, mesh.faces) and
        np.array_equal(saved_mesh.classes, mesh.classes) and saved_mesh.surface == mesh.surface and
        expected_hash == info['checks']['control_xyz_sha256'], 'Final G06 blend/cap/restore/control replay is not exact.')
    fields = bulb.read_arrays(folder/'operation_fields.npz')
    actual = saved_mesh.xyz-reference
    require(np.array_equal(fields['reference_xyz'], reference) and np.array_equal(fields['delta'], actual) and
        np.array_equal(fields['replacement_weight'], weight) and np.array_equal(fields['protected_core'], control['protected']) and
        np.array_equal(fields['fixed_ends'], control['ends']), 'Final saved reference/delta/ownership fields differ from actual replay.')
    maximum = float(np.max(np.linalg.norm(actual, axis=1), initial=0.))
    require(np.isfinite(actual).all() and maximum <= recipe['maximum_total_shift']+TOLERANCE and
        np.array_equal(saved_mesh.xyz[weight == 0.], baseline.xyz[weight == 0.]), 'Final actual cap or exact unchanged BASELINE contract failed.')
    del fields, actual, mesh, common, common_chart, common_tags, active_delta, total, relaxation; gc.collect()
    native = t.growth.native(saved_mesh)
    with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
        require(np.array_equal(native.xyz, saved['xyz']) and np.array_equal(native.faces[:, :3], saved['faces']),
            'Actual native control/fan rebuild is not exactly the saved geometry.')
    xyz_hash, faces_hash = finish.array_hash(native.xyz), finish.array_hash(native.faces[:, :3])
    require(np.isfinite(native.xyz).all() and xyz_hash == info['checks']['native_xyz_sha256'] and
        faces_hash == info['checks']['native_faces_sha256'] == baseline_receipt['native_faces_sha256'],
        'Actual native geometry/hash does not bind final and main BASELINE connectivity receipts.')
    topology = parent_verification['cases'][case]['actual_native_topology']
    require(topology['passed'] and topology['components'] == 1, 'Main actual topology receipt is not one closed oriented body.')
    pairs, pair_receipts = main_verify.reflection_pairs(saved_mesh, chart)
    coordinate_symmetry = main_verify.coordinate_symmetry(native.xyz, pairs, pair_receipts)
    for axis in ('X', 'Y'):
        original = info['checks']['actual_native_xy_symmetry'][axis]
        require(original['passed'] and original['pair_involution'] and
            original['reflected_oriented_native_triangles_identical'], 'Generation oriented native reflection receipt failed.')
    baseline_native = np.concatenate([baseline.xyz, t.face_values(baseline, baseline.xyz)])
    guards = dict(outside=np.r_[control['weight'] == 0., fan['weight'] == 0.],
        ends=np.r_[control['ends'], fan['ends']], cores=np.r_[control['protected'], fan['protected']])
    for name, mask in guards.items():
        require(np.array_equal(native.xyz[mask], baseline_native[mask]), 'Actual native '+name+' is not exact BASELINE.')
    area = finish.minimum_area(native.xyz, native.faces[:, :3])
    require(np.isfinite(area) and area > 1e-14, 'Actual native triangle area failed.')
    result = dict(passed=True, input_case=case, baseline_control_xyz_sha256=baseline_hash,
        baseline_linked_to_main_generation_and_verification=True, common_reference_reconstructed_exact=True,
        common_reference_xyz_sha256=reference_hash, active_stages=stages, final_control_xyz_sha256=expected_hash,
        native_xyz_sha256=xyz_hash, native_faces_sha256=faces_hash, saved_native_rebuild_exact=True,
        actual_delta_exact=True, maximum_actual_total_shift=maximum, minimum_actual_native_triangle_area=area,
        actual_native_coordinate_symmetry=coordinate_symmetry,
        oriented_symmetry_scope='Generation X/Y oriented native reflection PASS linked to exactly replayed native XYZ/faces; independently recalculated actual coordinate reflections.',
        actual_native_baseline_guards_exact={name: int(mask.sum()) for name, mask in guards.items()},
        topology_scope='Same actual native faces as the main verification one-closed-oriented-component BASELINE; no appended connectivity.',
        final_G06_postprocessing='Inactive refine → cap accumulated active displacement → measured patch replacement/blend with BASELINE → total .45 cap/material reflection → exact weight-zero BASELINE restore.',
        curve_scope='G04/G05 curve/frame evidence belongs to actual incoming native states before active displacement and before final G06 blend; it is not final-G06 detected branch evidence.',
        generation_json_sha256=bulb.digest(folder/'generation.json'))
    del saved_mesh, baseline, native, baseline_native, pairs, reference; gc.collect()
    return result


def run(root, parent_root):
    root, parent_root = Path(root).resolve(), Path(parent_root).resolve()
    inventory(root, parent_root)
    recipe, summary, parent_verification = read_json(root/'RECIPE.json'), read_json(root/'SUMMARY.json'), read_json(parent_root/'VERIFICATION.json')
    require(recipe == active.RECIPE and summary['passed'] is True and summary['both_inputs_complete'] is True and
        len(summary['cases']) == 2 and set(summary['cases']) == set(CASES), 'Both ACTIVE_FOLDS cases with the same frozen recipe must have passed.')
    require(parent_verification['status'] == 'PASS' and set(parent_verification['cases']) == set(CASES),
        'A complete main SPAN/COUNTER VERIFICATION PASS is required.')
    cases = {case: verify_case(root, parent_root, case, parent_verification, recipe) for case in CASES}
    return dict(status='PASS', root=str(root), parent_root=str(parent_root), expected_cases=list(CASES), cases=cases,
        recipe=recipe, parent_verification_sha256=bulb.digest(parent_root/'VERIFICATION.json'),
        verifier_module_sha256=bulb.digest(Path(__file__)),
        scope='Actual incoming-native normals, signed displacement/reflection and triangle/barycentric curve provenance at ordered G04/G05; exact G06 patch blend/cap/restore and saved native reconstruction.',
        excluded=['Aesthetic/reference fidelity certification', 'Automatic branch discovery', 'Self-intersections', 'Fabrication', 'Structural performance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, required=True)
    args = parser.parse_args()
    output = args.root/'ACTIVE_VERIFICATION.json'
    if output.exists():
        raise FileExistsError('Existing independent verification receipt preserved: '+str(output))
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
    print('ACTIVE_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
