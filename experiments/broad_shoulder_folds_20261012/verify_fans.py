"""Verify one rooted signed-height pass on each actual broad G6 surface.

This adapter reuses the broad incoming-native frame and coordinate checks. It
does not regenerate the earlier broad experiment or certify visual quality.
Requested displacement and the rounded actual XYZ difference are distinct
evidence. The parent experiment's total cap is not reapplied to this pass.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('rooted_fans_broad_verification', HERE/'verify.py')
broad = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(broad)
finish, t, bulb = broad.finish, broad.t, broad.bulb
require, read_json = broad.require, broad.read_json
CASES, MODE, TOLERANCE = broad.CASES, 'ROOTED_FANS', broad.TOLERANCE


def source_identity(actual_xyz, generation, parent_state, generation_sha256):
    """Bind actual source positions and its metadata to the broad PASS receipt."""
    xyz = np.asarray(actual_xyz)
    require(xyz.ndim == 2 and xyz.shape[1] == 3 and np.isfinite(xyz).all(),
        'Finite actual incoming BROAD_ACTIVE XYZ required.')
    actual_hash = finish.array_hash(xyz)
    require(parent_state.get('passed') is True and generation.get('checks', {}).get('passed') is True and
        actual_hash == generation['checks']['control_xyz_sha256'] == parent_state['final_control_xyz_sha256'] and
        generation_sha256 == parent_state['generation_json_sha256'],
        'Actual incoming broad source/generation differs from its verification receipt.')
    return actual_hash


def field_pass_identity(metadata, case, recipe):
    require(metadata['input_case'] == case and metadata['candidate'] == MODE and
        metadata['recipe'] == recipe and metadata['output_generation'] == 6 and
        metadata['added_subdivision_passes'] == 0 and metadata['added_surface_field_passes'] == 1 and
        metadata['added_mandelbulb_evaluations'] == 0 and metadata['checks']['passed'] is True,
        'Rooted candidate requires the same recipe, G6, zero splits and exactly one non-bulb field pass.')


def exact_surface_pass(source_xyz, requested_delta, actual_delta, final_xyz, weight, ends):
    """Check an uncapped single addition, preserving honest rounding evidence."""
    source, requested, actual, final, weight, ends = map(np.asarray,
        (source_xyz, requested_delta, actual_delta, final_xyz, weight, ends))
    require(source.ndim == 2 and source.shape[1] == 3 and
        source.shape == requested.shape == actual.shape == final.shape and
        weight.shape == ends.shape == (len(source),) and
        all(np.isfinite(value).all() for value in (source, requested, actual, final, weight)) and
        np.all((weight >= 0.) & (weight <= 1.)) and np.isin(ends, (0, 1)).all(),
        'Invalid finite rooted-pass arrays or guards.')
    require(np.array_equal(final, source+requested), 'Final XYZ does not replay exact source plus requested delta.')
    require(np.array_equal(actual, final-source), 'Saved actual delta is not exact final minus source.')
    outside, ends = weight == 0., ends.astype(bool)
    require(np.array_equal(requested[outside], np.zeros_like(requested[outside])) and
        np.array_equal(final[outside], source[outside]), 'Rooted weight-zero controls changed from the parent.')
    require(np.array_equal(requested[ends], np.zeros_like(requested[ends])) and
        np.array_equal(final[ends], source[ends]), 'Rooted fixed-end controls changed from the parent.')
    return dict(passed=True, exact_source_plus_requested=True, saved_actual_delta_exact=True,
        maximum_requested_added_shift=float(np.max(np.linalg.norm(requested, axis=1), initial=0.)),
        maximum_actual_added_shift=float(np.max(np.linalg.norm(actual, axis=1), initial=0.)),
        requested_minus_actual_maximum=float(np.max(np.abs(requested-actual), initial=0.)),
        outside_control_count=int(outside.sum()), fixed_end_control_count=int(ends.sum()),
        total_cap_applied=False,
        scope='One uncapped source-G6 addition; operator amplitudes belong to the saved recipe, not inherited total caps.')


def verify_curve_evidence(native_xyz, native_faces, native_chart, curves, expected, source_hash):
    """Link authored attached UV curves to their actual incoming G6 triangles."""
    extra = {'source_uv', 'source_xyz', 'source_triangle_ids', 'source_barycentric',
        'incoming_generation', 'incoming_control_xyz_sha256'}
    require(set(curves) == set(expected) | extra and
        int(np.asarray(curves['incoming_generation']).item()) == 6 and
        str(np.asarray(curves['incoming_control_xyz_sha256']).item()) == source_hash,
        'Incoming curve source G6 identity/field inventory differs.')
    for name, value in expected.items():
        require(np.array_equal(curves[name], value), 'Authored rooted curve replay differs: '+name)
    require(np.array_equal(curves['source_uv'], expected['surface_uv']) and
        np.array_equal(curves['root_u'], curves['inherited_root_u']) and
        float(np.asarray(curves['root_attachment_max_error']).item()) == 0.,
        'Authored branch/child curve roots do not exactly meet their declared parent curves.')
    provenance = broad.native_sample_provenance(native_xyz, native_faces, native_chart, curves)
    return dict(passed=True, incoming_generation=6, authored_curve_replay_exact=True,
        authored_root_attachment_exact=True, actual_native_curve_provenance=provenance,
        scope='Authored connected material-UV curve family resampled on actual incoming broad G6; not detected ridge maxima or a certificate of visually legible attachment.')


def inventory(root, parent_root):
    files = [root/'RECIPE.json', root/'SUMMARY.json', parent_root/'VERIFICATION.json']
    for case in CASES:
        files.extend(parent_root/'BROAD_ACTIVE'/case/'G06'/name for name in ('control_quad.npz', 'generation.json'))
        files.extend([parent_root/case/'actual_patch.npz', root/case/'G06_incoming_frame.npz',
            root/case/'G06_incoming_curves.npz'])
        files.extend(root/MODE/case/'G06'/name for name in
            ('control_quad.npz', 'geometry.npz', 'generation.json', 'operation_fields.npz'))
    missing = [str(path) for path in files if not path.is_file()]
    require(not missing, 'Both SPAN/COUNTER rooted candidates and their actual broad evidence are required: '+', '.join(missing))


def verify_case(root, parent_root, case, parent_verification, runner, recipe):
    finish.memory_guard()
    operators = runner.folds
    source, folder = parent_root/'BROAD_ACTIVE'/case/'G06', root/MODE/case/'G06'
    parent_case = parent_verification['cases'][case]
    parent_state = parent_case['states']['BROAD_ACTIVE']
    source_info, metadata = read_json(source/'generation.json'), read_json(folder/'generation.json')
    field_pass_identity(metadata, case, recipe)
    parent_hash, source_generation_hash = bulb.digest(parent_root/'VERIFICATION.json'), bulb.digest(source/'generation.json')
    source_mesh, chart, source_tags = t.load(source)
    source_hash = source_identity(source_mesh.xyz, source_info, parent_state, source_generation_hash)
    require(source_mesh.generation == 6 and Path(metadata['source']).resolve() == source.resolve() and
        metadata['source_control_sha256'] == bulb.digest(source/'control_quad.npz') and
        metadata['source_control_xyz_sha256'] == source_hash and
        metadata['source_generation_sha256'] == source_generation_hash and
        metadata['parent_verification_sha256'] == parent_hash,
        'Rooted source/control/generation/parent verification identity differs.')
    patch_path, frame_path = parent_root/case/'actual_patch.npz', root/case/'G06_incoming_frame.npz'
    curve_path = root/case/'G06_incoming_curves.npz'
    patch_hash = bulb.digest(patch_path)
    require(Path(metadata['patch_source']).resolve() == patch_path.resolve() and
        metadata['patch_sha256'] == patch_hash == source_info['patch_sha256'] and
        Path(metadata['frame_path']) == frame_path.relative_to(root) and
        metadata['frame_sha256'] == bulb.digest(frame_path) and
        Path(metadata['curve_path']) == curve_path.relative_to(root) and
        metadata['curve_sha256'] == bulb.digest(curve_path),
        'Actual inherited patch, incoming G6 frame or curve identity differs.')
    patch, frame = bulb.read_arrays(patch_path), bulb.read_arrays(frame_path)
    weight, controls, fans = operators.guarded_weight(source_mesh, chart, patch, operators.RECIPE)
    native = t.growth.native(source_mesh)
    source_native_hash, source_faces_hash = finish.array_hash(native.xyz), finish.array_hash(native.faces[:, :3])
    require(source_native_hash == source_info['checks']['native_xyz_sha256'] == parent_state['native_xyz_sha256'] and
        source_faces_hash == source_info['checks']['native_faces_sha256'] == parent_state['native_faces_sha256'],
        'Actual source native XYZ/faces are not the verified broad body.')
    actual_frame, frame_receipt = broad.verify_incoming_frame(source_mesh, chart, native, frame, patch, 6, operators, operators.RECIPE)
    curves = bulb.read_arrays(curve_path)
    pchart = np.concatenate([chart, t.face_values(source_mesh, chart)])
    curve_receipt = verify_curve_evidence(native.xyz, native.faces[:, :3], pchart, curves,
        runner.rooted_fans.curve_evidence(patch, recipe), source_hash)
    del curves, pchart
    source_native_xyz = native.xyz
    del native; gc.collect()
    actual_raw, actual_fields = runner.displacement(chart, patch, actual_frame, weight, recipe)
    fields = bulb.read_arrays(folder/'operation_fields.npz')
    actual_delta_error = broad.compare_finite(fields['requested_delta'], operators.previous.reflect(actual_raw, chart),
        'Actual incoming G6 pooled-frame/PCHIP rooted displacement')
    actual_normal_error = broad.compare_finite(fields['applied_pooled_normals'], actual_fields['applied_pooled_normals'],
        'Actual incoming G6 PCHIP rooted normals')
    raw, expected_fields = runner.displacement(chart, patch, frame, weight, recipe)
    require(np.isfinite(raw).all() and finish.array_hash(raw) == metadata['raw_delta_sha256'],
        'Actual-linked saved G6 frame does not replay the raw rooted displacement hash.')
    require(set(fields) == set(expected_fields) | {'requested_delta', 'actual_delta'},
        'Rooted operation field inventory differs.')
    for name, expected in expected_fields.items():
        require(np.array_equal(fields[name], expected), 'Stored rooted signed-height/PCHIP/guard field differs: '+name)
    require(np.isfinite(fields['applied_pooled_normals']).all() and
        np.allclose(np.linalg.norm(fields['applied_pooled_normals'], axis=1), 1., rtol=0., atol=TOLERANCE),
        'Applied rooted pooled normals are not finite unit vectors.')
    requested = operators.previous.reflect(raw, chart)
    require(np.array_equal(fields['requested_delta'], requested) and
        finish.array_hash(requested) == metadata['applied_delta_sha256'], 'Requested rooted reflection/delta hash differs.')
    saved_mesh, saved_chart, saved_tags = t.load(folder)
    require(saved_mesh.generation == 6 and np.array_equal(saved_chart, chart) and
        np.array_equal(saved_mesh.faces, source_mesh.faces) and np.array_equal(saved_mesh.classes, source_mesh.classes) and
        np.array_equal(saved_mesh.rest, source_mesh.rest) and np.array_equal(saved_mesh.anchors, source_mesh.anchors) and
        np.array_equal(saved_tags, source_tags) and saved_mesh.surface == source_mesh.surface,
        'Rooted pass changed source generation, connectivity, chart or native surface semantics.')
    pass_receipt = exact_surface_pass(source_mesh.xyz, requested, fields['actual_delta'], saved_mesh.xyz, weight, controls['ends'])
    final_hash = finish.array_hash(saved_mesh.xyz)
    require(final_hash == metadata['checks']['control_xyz_sha256'], 'Final actual rooted control hash differs.')
    pairs, pair_receipts = broad.previous.reflection_pairs(source_mesh, chart)
    del actual_frame, actual_raw, actual_fields, raw, expected_fields, frame, requested, source_mesh; gc.collect()
    final_native = t.growth.native(saved_mesh)
    with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
        require(np.array_equal(final_native.xyz, saved['xyz']) and np.array_equal(final_native.faces[:, :3], saved['faces']),
            'Saved rooted native geometry differs from actual control/fan reconstruction.')
    native_hash, faces_hash = finish.array_hash(final_native.xyz), finish.array_hash(final_native.faces[:, :3])
    require(np.isfinite(final_native.xyz).all() and native_hash == metadata['checks']['native_xyz_sha256'] and
        faces_hash == metadata['checks']['native_faces_sha256'] == source_faces_hash and
        metadata['checks']['inherited_native_faces_identical_to_parent'] is True,
        'Final actual native geometry/faces are not linked to the verified source body.')
    symmetry = broad.previous.coordinate_symmetry(final_native.xyz, pairs, pair_receipts)
    guards = dict(outside=np.r_[controls['weight'] == 0., fans['weight'] == 0.],
        ends=np.r_[controls['ends'], fans['ends']])
    native_guards = broad.actual_native_guards(final_native.xyz, source_native_xyz, guards)
    area = finish.minimum_area(final_native.xyz, final_native.faces[:, :3])
    require(np.isfinite(area) and area > 1e-14 and
        abs(area-metadata['checks']['minimum_triangle_area']) <= TOLERANCE,
        'Actual rooted native triangle area/receipt differs.')
    changed_count = int(np.count_nonzero(np.linalg.norm(final_native.xyz-source_native_xyz, axis=1) > 1e-12))
    require(changed_count == metadata['checks']['actual_changed_native_vertices'] and
        abs(pass_receipt['maximum_actual_added_shift']-metadata['checks']['maximum_actual_added_shift']) <= TOLERANCE and
        metadata['checks']['actual_native_outside_parent_exact'] is True and metadata['checks']['actual_native_ends_parent_exact'] is True,
        'Actual rooted displacement/count/locality receipts differ.')
    require(parent_case['passed'] is True and parent_state['native_control_rebuild_exact'] is True,
        'Verified inherited native body/rebuild proof required.')
    result = dict(passed=True, input_case=case, source_control_xyz_sha256=source_hash,
        source_native_xyz_sha256=source_native_hash, source_generation_json_sha256=source_generation_hash,
        parent_verification_sha256=parent_hash, actual_incoming_G06_frame=frame_receipt,
        actual_incoming_G06_curves=curve_receipt,
        actual_PCHIP_normal_max_error=actual_normal_error, actual_PCHIP_requested_delta_max_error=actual_delta_error,
        raw_requested_field_replay_exact=True, rooted_fields_exact=True, actual_surface_pass=pass_receipt,
        final_control_xyz_sha256=final_hash, native_xyz_sha256=native_hash, native_faces_sha256=faces_hash,
        generation_json_sha256=bulb.digest(folder/'generation.json'), native_control_rebuild_exact=True,
        actual_native_coordinate_symmetry=symmetry, actual_native_guards=native_guards,
        minimum_actual_native_triangle_area=area, actual_changed_native_vertices=changed_count,
        output_generation=6, added_subdivision_passes=0, added_surface_field_passes=1, added_mandelbulb_evaluations=0,
        lineage_scope='Actual verified BROAD_ACTIVE G6 plus one rooted signed-height field; no new subdivision generation.',
        normal_scope='Actual incoming source G6 triangle/arc/pool frame, before this added field; not a frame sampled from its own result.',
        topology_scope='Actual native face hash unchanged from verified broad one-body source; closed/oriented connectivity proof is inherited, not recomputed.',
        symmetry_scope='Actual X/Y native XYZ pair checks; oriented triangle reflection sets not recomputed here.',
        visual_success='NOT_ASSESSED: continuity of mesh and valid displacement do not certify visible root attachment or reference fidelity.')
    del saved_mesh, fields, final_native, source_native_xyz, pairs; gc.collect()
    return result


def run(root, parent_root):
    root, parent_root = Path(root).resolve(), Path(parent_root).resolve()
    inventory(root, parent_root)
    runner = broad.load_module('verified_rooted_fans_runner', HERE/'study_fans.py')
    recipe, summary = read_json(root/'RECIPE.json'), read_json(root/'SUMMARY.json')
    require(recipe == runner.rooted_fans.RECIPE and summary['both_inputs_complete'] is True and
        summary['geometry_checks_passed'] is True and len(summary['cases']) == 2 and set(summary['cases']) == set(CASES) and
        len(summary['states']) == 2 and {item['input_case'] for item in summary['states']} == set(CASES),
        'Two complete rooted input states and one common frozen recipe are required.')
    parent = read_json(parent_root/'VERIFICATION.json')
    require(parent['status'] == 'PASS' and set(parent['cases']) == set(CASES) and
        parent['recipe']['folds'] == runner.folds.RECIPE and
        parent['recipe']['selection'] == runner.study.measure.SELECTION,
        'Both actual broad parents must have matching frozen recipe and verification PASS.')
    for state in summary['states']:
        require(state == read_json(root/MODE/state['input_case']/'G06/generation.json'),
            'Rooted summary state differs from saved generation metadata.')
    cases = {case: verify_case(root, parent_root, case, parent, runner, recipe) for case in CASES}
    return dict(status='PASS', root=str(root), parent_root=str(parent_root), expected_cases=list(CASES),
        candidate=MODE, recipe=recipe, cases=cases,
        parent_verification_sha256=bulb.digest(parent_root/'VERIFICATION.json'),
        verifier_module_sha256=bulb.digest(Path(__file__)),
        scope='Source G6 receipt/hash identity, actual incoming native triangle/arc/pool frame and authored-curve provenance, signed-height/PCHIP/reflection replay, exact requested and rounded actual displacement, native mesh/locality/symmetry and inherited face topology.',
        excluded=['Aesthetic/reference fidelity certification', 'Automatic feature attachment or branching detection',
            'Self-intersections', 'Fabrication', 'Structural performance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, required=True)
    args = parser.parse_args()
    output = args.root/'VERIFICATION.json'
    if output.exists():
        raise FileExistsError('Existing rooted verification receipt preserved: '+str(output))
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
    print('ROOTED_FANS_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
