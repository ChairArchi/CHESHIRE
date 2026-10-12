"""Read-only geometric/package verification of both parent-guided inputs.

Reconstructs the common relaxed G03 carrier and its three inactive splits.
It does not reassess aesthetic quality, regenerate the atlas, render, or
certify self-intersections, fabrication, or structural performance.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json

import numpy as np
from scipy.spatial import cKDTree


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('verified_parent_guided_study', HERE/'study.py')
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)
LEGACY_SPEC = importlib.util.spec_from_file_location('verified_parent_guided_topology',
    study.LEGACY/'compactpackage_finish_g6.py')
legacy = importlib.util.module_from_spec(LEGACY_SPEC)
LEGACY_SPEC.loader.exec_module(legacy)
finish, bulb, t = study.finish, study.bulb, study.t
CASES = ('SPAN', 'COUNTER')
MODES = study.MODES
TOLERANCE = 3e-12


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def inventory(root):
    """Require every expected input and mode before allocating a G06 mesh."""
    root = Path(root)
    expected = [root/'RECIPE.json']
    for case in CASES:
        expected.extend(root/case/name for name in ('SUMMARY.json', 'actual_parent_0.npz',
            'actual_parent_1.npz', 'common_carrier_relaxation.npz', 'guided_colonies.npz'))
        for mode in MODES:
            expected.extend(root/mode/case/'G06'/name for name in ('generation.json',
                'control_quad.npz', 'geometry.npz', 'operation_fields.npz'))
    missing = [str(path) for path in expected if not path.is_file()]
    require(not missing, 'Missing expected SPAN/COUNTER comparison assets: '+', '.join(missing))
    return expected


def metadata_identity(metadata, case, mode, recipe, atlas_hash):
    require(metadata.get('input_case') == case and metadata.get('candidate') == mode and
        metadata.get('output_generation') == 6, 'Wrong case, mode, or G06 generation identity.')
    require(metadata.get('recipe') == recipe == study.RECIPE, 'Parent-guided recipe differs across states or from the implemented recipe.')
    require(metadata.get('relief_recipe') == bulb.VARIANTS['INTEGRATED'] and
        metadata.get('relaxation_recipe') == finish.RELAXATION, 'Relief/relaxation recipe differs from the common accepted recipe.')
    require(metadata.get('atlas_sha256') == atlas_hash and metadata.get('field_internal_iterations') == 10,
        'Atlas identity or finite field iteration count differs.')
    require(bool(metadata.get('combined_operation')) == (mode == 'FLOW_CHAIN'),
        'Combined FLOW_CHAIN operation must be declared explicitly.')
    checks = metadata.get('checks', {})
    symmetry = checks.get('actual_native_left_right_symmetry', {})
    require(checks.get('passed') is True and checks.get('finite') is True and
        np.isfinite(checks.get('minimum_triangle_area', np.nan)) and
        checks.get('minimum_triangle_area', 0.) > 1e-14, 'Generation geometry checks did not pass.')
    require(symmetry.get('passed') is True and symmetry.get('pair_involution') is True and
        symmetry.get('reflected_oriented_native_triangle_sets_identical') is True and
        symmetry.get('actual_native_xyz_pair_max_error', np.inf) < 1e-9 and
        symmetry.get('material_pair_max_error', np.inf) < 1e-9,
        'Generation native LR coordinate/oriented-face receipt did not pass.')
    return checks


def check_actual_delta(control_xyz, reference, operation, baseline_xyz, chart, maximum=.30):
    control_xyz, reference = np.asarray(control_xyz), np.asarray(reference)
    require(control_xyz.shape == reference.shape and np.isfinite(control_xyz).all(),
        'Invalid actual control XYZ.')
    actual = control_xyz-reference
    require(np.array_equal(operation['delta'], actual), 'Saved operation delta differs from actual control minus common reference.')
    maximum_shift = float(np.max(np.linalg.norm(actual, axis=1), initial=0.))
    require(maximum_shift <= maximum+1e-10, 'Actual total detail displacement exceeds .30.')
    region = np.asarray(operation['changed_region'])
    require(region.shape == (len(reference),) and np.isin(region, [0, 1]).all(), 'Invalid changed-region mask.')
    outside = region == 0
    fixed = (chart[:, 0] <= .10) | (chart[:, 0] >= .90)
    require(np.array_equal(control_xyz[outside], baseline_xyz[outside]), 'New detail changed controls outside its declared active region.')
    require(np.array_equal(control_xyz[fixed], baseline_xyz[fixed]), 'New detail changed inactive ends relative to BASELINE.')
    return dict(maximum_actual_total_detail_shift=maximum_shift, operation_delta_exact=True,
        outside_active_region_equals_baseline=True, inactive_ends_equal_baseline=True,
        inactive_end_control_count=int(fixed.sum()),
        maximum_end_relief_from_common_reference=float(np.max(np.linalg.norm(actual[fixed], axis=1), initial=0.)),
        endpoint_scope='New variation versus BASELINE is fixed; inherited BASELINE relief versus common reference is measured only.')


def guided_source_provenance(colonies, native, carrier_xyz, tolerance=TOLERANCE):
    """The final centres belong to the meso carrier, not the unmodified carrier."""
    require(int(np.asarray(colonies['source_control_generation']).item()) == 6,
        'Guided final centres must refer to the actual G06 meso carrier.')
    require(int(np.asarray(colonies['frame_source_generation']).item()) == 3,
        'Guided coarse frame source must remain explicitly identified as G03.')
    recorded_hash = str(np.asarray(colonies['source_carrier_xyz_sha256']).item())
    require(recorded_hash == finish.array_hash(carrier_xyz), 'Guided meso carrier control hash differs.')
    ids = np.asarray(colonies['source_triangle_ids'])
    bary = np.asarray(colonies['source_barycentric'])
    centres = np.asarray(colonies['centres'])
    require(ids.ndim == 1 and len(ids) > 0 and ids.dtype.kind in 'iu' and
        ids.min() >= 0 and ids.max() < len(native.faces), 'Guided source triangle IDs are invalid.')
    require(bary.shape == (len(ids), 3) and centres.shape == (len(ids), 3) and
        np.isfinite(bary).all() and np.all(bary >= -tolerance) and np.all(bary <= 1.+tolerance) and
        np.allclose(bary.sum(axis=1), 1., rtol=0., atol=tolerance), 'Guided source barycentric coordinates are invalid.')
    reconstructed = np.einsum('ni,nij->nj', bary, native.xyz[native.faces[ids, :3]])
    source = np.asarray(colonies['source_xyz'])
    require(source.shape == centres.shape and np.isfinite(source).all() and np.isfinite(centres).all(),
        'Guided source/centre XYZ is invalid.')
    centre_error = float(np.max(np.abs(reconstructed-centres), initial=0.))
    source_error = float(np.max(np.abs(reconstructed-source), initial=0.))
    require(max(centre_error, source_error) <= tolerance, 'Guided centres do not reconstruct on the actual meso carrier triangles.')
    primary = np.asarray(colonies['levels']) == 0
    require(primary.shape == (len(ids),) and primary.any(), 'Guided primary colony lineage is absent.')
    require(np.array_equal(colonies['primary_source_triangle_ids'], ids[primary]) and
        np.array_equal(colonies['primary_source_barycentric'], bary[primary]) and
        np.array_equal(colonies['primary_source_xyz'], source[primary]), 'Guided primary provenance records disagree with all-centre records.')
    return dict(passed=True, final_source_control_generation=6, final_source_carrier_hash_exact=True,
        actual_meso_native_centres_max_error=centre_error, actual_meso_native_source_max_error=source_error,
        tolerance=tolerance, colony_count=len(ids),
        frame_source_generation=int(np.asarray(colonies['frame_source_generation']).item()),
        scope='All final G06 centres/source XYZ are reconstructed from meso native triangle IDs and barycentric weights; coarse frame source is retained separately.')


def reflection_pairs(mesh, chart):
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    tree = cKDTree(pchart)
    output, receipts = [], {}
    for index, axis in enumerate(('X', 'Y')):
        signs = np.ones(3); signs[index+1] = -1.
        distance, pairs = tree.query(pchart*signs)
        error = float(distance.max())
        involution = bool(np.array_equal(pairs[pairs], np.arange(len(pairs))))
        require(error < 1e-9 and involution, axis+' material reflection does not supply an involution.')
        output.append(pairs)
        receipts[axis] = dict(material_pair_max_error=error, pair_involution=involution)
    del tree, pchart; gc.collect()
    return output, receipts


def coordinate_symmetry(native_xyz, pairs, pair_receipts, chunk=120000):
    result = {}
    for axis, (ids, receipt) in enumerate(zip(pairs, pair_receipts.values())):
        signs = np.ones(3); signs[axis] = -1.
        maximum = 0.
        for start in range(0, len(ids), chunk):
            local = ids[start:start+chunk]
            maximum = max(maximum, float(np.max(np.linalg.norm(native_xyz[start:start+len(local)]-
                native_xyz[local]*signs, axis=1), initial=0.)))
        require(maximum < 1e-9, ('X', 'Y')[axis]+' actual native coordinates fail reflection.')
        result[('X', 'Y')[axis]] = dict(receipt, actual_native_xyz_pair_max_error=maximum, passed=True)
    return result


def verify_case(root, previous_root, case, metadata, atlas_hash):
    identity = metadata['BASELINE']
    source = Path(identity['source'])
    require(source.name == 'G03' and source.parent.name == case and source.parent.parent.name == 'WALL',
        'Actual WALL case G03 source required.')
    require(bulb.digest(source/'control_quad.npz') == identity['source_control_sha256'], 'WALL source file hash changed.')
    require(bulb.digest(Path(identity['atlas_source'])) == atlas_hash, 'Saved atlas source file hash changed.')
    require(bulb.digest(Path(identity['original_colonies_source'])) == identity['original_colonies_sha256'],
        'Original colony file hash changed.')
    mesh3, chart3, tags3 = t.load(source)
    require(mesh3.generation == 3, 'Common reference must start from actual G03.')
    fixed3 = (chart3[:, 0] <= .10) | (chart3[:, 0] >= .90)
    original_fixed3 = mesh3.xyz[fixed3].copy()
    relaxation = finish.relax_carrier(mesh3, chart3, identity['relaxation_recipe'])
    require(np.array_equal(mesh3.xyz[fixed3], original_fixed3), 'Common G03 relaxation moved a fixed endpoint.')
    relaxation_maximum = float(np.max(np.linalg.norm(relaxation, axis=1), initial=0.))
    require(relaxation_maximum <= .04+1e-12 and
        abs(relaxation_maximum-identity['carrier_relaxation_maximum']) < 1e-12,
        'Common G03 relaxation differs from the declared .04 bound or saved actual maximum.')
    saved_relaxation = bulb.read_arrays(root/case/'common_carrier_relaxation.npz')['delta']
    require(np.array_equal(relaxation, saved_relaxation), 'Common G03 carrier relaxation does not replay exactly.')
    common, chart, tags = study.refine(mesh3, chart3, tags3)
    require(common.generation == 6, 'Exactly three inactive refinements must produce G06.')
    reference = common.xyz
    reference_hash = finish.array_hash(reference)
    require(reference_hash == identity['common_reference_xyz_sha256'], 'Common reference reconstruction hash differs.')
    pairs, pair_receipts = reflection_pairs(common, chart)
    parents = [bulb.read_arrays(root/case/f'actual_parent_{i}.npz') for i in (0, 1)]
    selected = study.guidance.patch_coordinates(chart, parents[study.RECIPE['parent_index']])
    core = np.maximum.reduce([study.guidance.patch_coordinates(chart, p)['core_weight'] for p in parents])
    old_prefix = 'bulb_finish_g6_relaxed_g3'+('_counter' if case == 'COUNTER' else '')
    old_folder = previous_root/old_prefix/'RELAXED_G06'/case/'G06'
    require((old_folder/'control_quad.npz').is_file(), 'Accepted previous RELAXED_G06 control is missing.')
    with np.load(old_folder/'control_quad.npz', allow_pickle=False) as old:
        old_xyz_hash = finish.array_hash(old['xyz'])
    baseline_xyz = None
    results = {}
    shared_native_faces_hash = None
    for mode in MODES:
        print('VERIFY', case, mode, flush=True)
        folder = root/mode/case/'G06'
        info = metadata[mode]
        checks = metadata_identity(info, case, mode, read_json(root/'RECIPE.json'), atlas_hash)
        for key in ('source', 'source_control_sha256', 'original_colonies_source', 'original_colonies_sha256',
            'common_reference_xyz_sha256', 'common_incoming_normals_sha256', 'atlas_sha256'):
            require(info.get(key) == identity.get(key), 'Mode changed common identity field: '+key)
        mesh, saved_chart, _ = t.load(folder)
        require(mesh.generation == 6 and np.array_equal(saved_chart, chart) and np.array_equal(mesh.faces, common.faces),
            'Mode altered inherited generation, material chart, or control connectivity.')
        require(finish.array_hash(mesh.xyz) == checks['control_xyz_sha256'] and
            finish.array_hash(mesh.faces) == checks['control_topology_sha256'], 'Saved control arrays differ from generation checks.')
        if mode == 'BASELINE':
            baseline_xyz = mesh.xyz.copy()
            require(finish.array_hash(baseline_xyz) == old_xyz_hash, 'BASELINE differs from accepted previous RELAXED_G06 controls.')
        operation = bulb.read_arrays(folder/'operation_fields.npz')
        require(np.array_equal(operation['parent_core_weight'], core) and
            np.array_equal(operation['selected_patch_envelope'], selected['envelope']), 'Operation ownership/patch fields do not match the saved measured parents.')
        expected_region = core > 0
        if mode == 'FLOW_CHAIN':
            middle_delta = operation['middle_delta']
            require(middle_delta.shape == reference.shape and np.isfinite(middle_delta).all(), 'Invalid middle-carrier displacement.')
            expected_region = expected_region | ((selected['envelope']*(1.-core)) > 0) | (np.linalg.norm(middle_delta, axis=1) > 0)
        require(np.array_equal(operation['changed_region'], expected_region.astype(np.uint8)), 'Changed-region mask differs from the actual defined support.')
        delta_check = check_actual_delta(mesh.xyz, reference, operation, baseline_xyz, chart)
        require(abs(delta_check['maximum_actual_total_detail_shift']-checks['maximum_total_detail_shift']) < 1e-12,
            'Generation maximum detail shift differs from actual controls.')
        native = t.growth.native(mesh)
        native_faces = native.faces[:, :3]
        with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
            require(np.array_equal(native.xyz, saved['xyz']) and np.array_equal(native_faces, saved['faces']),
                'Saved actual native geometry differs from the control/fan reconstruction.')
        require(np.isfinite(native.xyz).all(), 'Native reconstruction contains nonfinite coordinates.')
        xyz_hash, face_hash = finish.array_hash(native.xyz), finish.array_hash(native_faces)
        require(xyz_hash == checks['native_xyz_sha256'] and face_hash == checks['native_faces_sha256'],
            'Native array hashes do not bind the generation symmetry receipt to the replayed geometry.')
        counts = dict(control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
            physical_vertices=len(native.xyz), physical_triangles=len(native_faces))
        require(counts == finish.COUNTS, 'Actual G06 counts differ from the unchanged inherited surface.')
        require(checks['actual_native_left_right_symmetry']['physical_vertices'] == len(native.xyz) and
            checks['actual_native_left_right_symmetry']['physical_triangles'] == len(native_faces), 'Symmetry receipt native counts differ.')
        if mode == 'BASELINE':
            shared_native_faces_hash = face_hash
            topology = legacy.native_topology(native.xyz, native_faces)
            require(topology['passed'] and topology['components'] == 1, 'Actual BASELINE native topology is not one closed oriented component.')
        else:
            require(face_hash == shared_native_faces_hash, 'Native faces differ between modes.')
        results[mode] = dict(passed=True, actual_delta=delta_check, counts=counts,
            control_xyz_sha256=checks['control_xyz_sha256'], native_xyz_sha256=xyz_hash,
            native_faces_sha256=face_hash, actual_native_coordinate_reflections=coordinate_symmetry(native.xyz, pairs, pair_receipts),
            left_right_oriented_native_faces='Generation receipt PASS bound to exactly replayed native XYZ/faces hashes',
            y_reflection_scope='Independent actual XYZ reflection and identical native connectivity; oriented Y triangle sets not rechecked',
            generation_json_sha256=bulb.digest(folder/'generation.json'))
        del native, native_faces, mesh; gc.collect()
        if mode == 'FLOW_CHAIN':
            meso = copy.copy(common)
            meso.xyz = reference+operation['middle_delta']
            meso_native = t.growth.native(meso)
            results[mode]['guided_colony_provenance'] = guided_source_provenance(
                bulb.read_arrays(root/case/'guided_colonies.npz'), meso_native, meso.xyz)
            del meso_native, meso; gc.collect()
        del operation; gc.collect()
    return dict(passed=True, source_control_sha256=identity['source_control_sha256'],
        common_reference_xyz_sha256=reference_hash, common_reference_exact=True,
        maximum_actual_carrier_relaxation=relaxation_maximum, carrier_endpoints_fixed=True,
        accepted_previous_baseline_control_xyz_sha256=old_xyz_hash, baseline_exact=True,
        normals_scope='Incoming normal-field hash identity retained across modes; normals/atlas relief are not reevaluated by this verifier',
        actual_native_topology=topology, topology_scope='Actual BASELINE edge incidence checked once; all three modes have identical native faces',
        states=results)


def run(root, previous_root):
    root, previous_root = Path(root).resolve(), Path(previous_root).resolve()
    inventory(root)
    recipe = read_json(root/'RECIPE.json')
    require(recipe == study.RECIPE, 'Root recipe differs from the implemented recipe.')
    metadata = {case: {mode: read_json(root/mode/case/'G06/generation.json') for mode in MODES} for case in CASES}
    atlas_hash = metadata['SPAN']['BASELINE']['atlas_sha256']
    accepted_atlas = previous_root/'bulb_integrated/atlas/power8.npz'
    require(accepted_atlas.is_file() and bulb.digest(accepted_atlas) == atlas_hash,
        'Shared atlas is not the accepted previous INTEGRATED atlas.')
    for case in CASES:
        summary = read_json(root/case/'SUMMARY.json')
        require(summary.get('input_case') == case and summary.get('passed') is True and
            len(summary.get('states', [])) == len(MODES) and
            {item['candidate'] for item in summary['states']} == set(MODES), 'Case summary does not contain all completed expected modes.')
        for mode in MODES:
            metadata_identity(metadata[case][mode], case, mode, recipe, atlas_hash)
    cases = {}
    for case in CASES:
        finish.memory_guard()
        cases[case] = verify_case(root, previous_root, case, metadata[case], atlas_hash)
        gc.collect()
    return dict(status='PASS', root=str(root), previous_root=str(previous_root), expected_cases=list(CASES),
        expected_modes=list(MODES), recipe=recipe, shared_atlas_sha256=atlas_hash, cases=cases,
        scope='Common carrier reconstruction, actual displacement/locality, accepted baseline identity, exact native replay, native topology/coordinate symmetry and meso-carrier colony provenance; no aesthetic certification',
        excluded=['New parent chord-depth diagnosis', 'Aesthetic/reference fidelity certification', 'Self-intersections', 'Fabrication', 'Structural performance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--previous-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.root/'VERIFICATION.json'
    if output.exists():
        raise FileExistsError('Existing verification receipt preserved: '+str(output))
    try:
        result = run(args.root, args.previous_root)
    except Exception as error:
        result = dict(status='FAIL', root=str(args.root.resolve()), error_type=type(error).__name__, error=str(error))
        with output.open('x', encoding='utf8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        raise
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print('VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
