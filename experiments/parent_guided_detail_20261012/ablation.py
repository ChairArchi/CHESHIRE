"""Local MESO_ONLY_PATCH ablation of saved FLOW_CHAIN; no new atlas build.

The measured middle fold stays. Guided bulb relief is removed only inside the
same tapered shoulder patch; inherited BASELINE relief remains outside it.
This is not a wholly Mandelbulb-free column or an aesthetic certification.
Existing experiment outputs are read-only. Run cases sequentially in a fresh
output root; this module performs no rendering.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('meso_ablation_verifier', HERE/'verify.py')
verified = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verified)
study = verified.study
finish, bulb, t = study.finish, study.bulb, study.t
CASES = ('SPAN', 'COUNTER')
CANDIDATE = 'MESO_ONLY_PATCH'
SCOPE = ('Remove new guided bulb relief only in the same tapered measured shoulder patch; '
    'keep the saved middle fold and valley priority. Inherited BASELINE atlas relief '
    'remains outside the patch and partly in its transition. Not a wholly fractal-free shape.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def compose_raw(priority, middle, envelope, guided=None):
    """The same FLOW formula, with guided relief replaced by zero for ablation."""
    priority, middle, envelope = map(np.asarray, (priority, middle, envelope))
    require(priority.ndim == 2 and priority.shape[1] == 3 and middle.shape == priority.shape and
        envelope.shape == (len(priority),), 'Priority, middle and patch envelope shapes differ.')
    require(np.isfinite(priority).all() and np.isfinite(middle).all() and
        np.isfinite(envelope).all() and np.all((envelope >= 0.) & (envelope <= 1.)),
        'Finite displacements and patch envelope in [0,1] required.')
    if guided is None:
        return priority+middle+envelope[:, None]*(0.-priority)
    guided = np.asarray(guided)
    require(guided.shape == priority.shape and np.isfinite(guided).all(), 'Invalid guided displacement.')
    return priority+middle+envelope[:, None]*(guided-priority)


def cap_diagnostics(raw, maximum=.30):
    raw = np.asarray(raw)
    require(raw.ndim == 2 and raw.shape[1] == 3 and np.isfinite(raw).all() and
        np.isfinite(maximum) and maximum > 0., 'Finite XYZ vectors and positive cap required.')
    lengths = np.linalg.norm(raw, axis=1)
    return dict(control_count=len(raw), maximum_vector_cap=float(maximum),
        uncapped_maximum=float(np.max(lengths, initial=0.)),
        cap_active_control_count=int(np.count_nonzero(lengths > maximum)),
        cap_active_beyond_1e_12_count=int(np.count_nonzero(lengths > maximum+1e-12)),
        cap_boundary_within_1e_12_count=int(np.count_nonzero(np.abs(lengths-maximum) <= 1e-12)),
        maximum_removed_vector_length=float(np.max(np.maximum(lengths-maximum, 0.), initial=0.)),
        scope='Euclidean norms before the same total-vector cap and material reflection; boundary count exposes floating-point cap ambiguity.')


def flow_replay_check(expected_xyz, actual_xyz, tolerance=verified.TOLERANCE):
    expected_xyz, actual_xyz = np.asarray(expected_xyz), np.asarray(actual_xyz)
    require(expected_xyz.shape == actual_xyz.shape and np.isfinite(expected_xyz).all() and
        np.isfinite(actual_xyz).all(), 'Invalid FLOW replay controls.')
    error = float(np.max(np.abs(expected_xyz-actual_xyz), initial=0.))
    require(error <= tolerance, 'Reconstructed uncapped FLOW does not reconnect to saved FLOW controls.')
    return dict(passed=True, maximum_control_coordinate_error=error, tolerance=tolerance,
        scope='Saved actual priority delta is round-tripped through control-minus-reference; replay is tolerance-bound, not claimed byte-exact.')


def preserve_unchanged_baseline(reference, delta, baseline_xyz, chart, changed_region):
    """Restore mathematically inactive controls after floating-point recapping.

    A saved actual delta can round to just above .30 after XYZ subtraction.
    Its second cap may then move a baseline control by one ULP. The unchanged
    region/ends have an exact XYZ contract, so preserve those saved coordinates
    and synchronize the returned actual delta before saving either array.
    """
    reference, delta, baseline_xyz, chart, region = map(np.asarray,
        (reference, delta, baseline_xyz, chart, changed_region))
    require(reference.ndim == 2 and reference.shape[1] == 3 and
        delta.shape == baseline_xyz.shape == chart.shape == reference.shape and
        region.shape == (len(reference),) and np.isin(region, (0, 1)).all(),
        'Invalid unchanged-region preservation arrays.')
    require(all(np.isfinite(array).all() for array in (reference, delta, baseline_xyz, chart)),
        'Finite unchanged-region preservation arrays required.')
    result = reference+delta
    inactive = (region == 0) | (chart[:, 0] <= .10) | (chart[:, 0] >= .90)
    difference = result[inactive]-baseline_xyz[inactive]
    maximum_correction = float(np.max(np.abs(difference), initial=0.))
    require(maximum_correction <= verified.TOLERANCE,
        'Non-roundoff displacement in mathematically unchanged controls; preservation would hide an active-region error.')
    receipt = dict(outside_and_ends_restored_from_exact_saved_baseline=True,
        preserved_control_count=int(inactive.sum()),
        roundoff_changed_control_count=int(np.count_nonzero(np.any(difference != 0., axis=1))),
        maximum_coordinate_correction=maximum_correction, correction_tolerance=verified.TOLERANCE,
        scope='Only controls outside the declared active region or in fixed material ends; active interior retains the same vector cap/reflection.')
    result[inactive] = baseline_xyz[inactive]
    return result, result-reference, receipt


def inventory(root, cases):
    require(bool(cases) and len(cases) == len(set(cases)) and set(cases) <= set(CASES),
        'Request SPAN and/or COUNTER exactly once.')
    root = Path(root)
    expected = [root/'RECIPE.json']
    for case in cases:
        expected.extend(root/case/name for name in ('actual_parent_0.npz', 'actual_parent_1.npz',
            'common_carrier_relaxation.npz', 'guided_colonies.npz'))
        for mode in study.MODES:
            expected.extend(root/mode/case/'G06'/name for name in ('generation.json',
                'control_quad.npz', 'operation_fields.npz'))
        expected.append(root/'FLOW_CHAIN'/case/'G06/geometry.npz')
    missing = [str(path) for path in expected if not path.is_file()]
    require(not missing, 'Missing requested ablation source assets: '+', '.join(missing))
    return expected


def run_case(root, output, case):
    finish.memory_guard()
    folders = {mode: root/mode/case/'G06' for mode in study.MODES}
    metadata = {mode: read_json(folder/'generation.json') for mode, folder in folders.items()}
    identity = metadata['BASELINE']
    atlas_path = Path(identity['atlas_source'])
    atlas_hash = bulb.digest(atlas_path)
    for mode, info in metadata.items():
        verified.metadata_identity(info, case, mode, read_json(root/'RECIPE.json'), atlas_hash)
        for key in ('source', 'source_control_sha256', 'common_reference_xyz_sha256',
                'original_colonies_sha256', 'common_incoming_normals_sha256', 'atlas_sha256'):
            require(info.get(key) == identity.get(key), 'Saved modes changed common identity: '+key)
    require(identity['field_internal_iterations'] == 10, 'Expected inherited ten-iteration finite atlas.')
    source = Path(identity['source'])
    require(source.name == 'G03' and source.parent.name == case and source.parent.parent.name == 'WALL',
        'Actual same-input WALL G03 source required.')
    require(bulb.digest(source/'control_quad.npz') == identity['source_control_sha256'],
        'Actual WALL G03 source hash changed.')
    mesh3, chart3, tags3 = t.load(source)
    require(mesh3.generation == 3, 'Source is not G03.')
    relaxation = finish.relax_carrier(mesh3, chart3, identity['relaxation_recipe'])
    with np.load(root/case/'common_carrier_relaxation.npz', allow_pickle=False) as saved:
        require(np.array_equal(relaxation, saved['delta']), 'Saved common carrier relaxation did not replay exactly.')
    common, chart, tags = study.refine(mesh3, chart3, tags3)
    reference = common.xyz.copy()
    require(common.generation == 6 and finish.array_hash(reference) == identity['common_reference_xyz_sha256'],
        'Actual G03 → same relaxation → three inactive refinements common reference hash differs.')
    del mesh3, chart3, tags3, relaxation; gc.collect()

    parents = [bulb.read_arrays(root/case/f'actual_parent_{i}.npz') for i in (0, 1)]
    selected = study.guidance.patch_coordinates(chart, parents[study.RECIPE['parent_index']])
    core = np.maximum.reduce([study.guidance.patch_coordinates(chart, parent)['core_weight'] for parent in parents])
    envelope = selected['envelope']*(1.-core)
    with np.load(folders['BASELINE']/'control_quad.npz', allow_pickle=False) as saved:
        baseline_xyz = saved['xyz']
        require(np.array_equal(saved['chart'], chart) and np.array_equal(saved['faces'], common.faces),
            'BASELINE chart/control topology differs from common reference.')
        require(finish.array_hash(baseline_xyz) == metadata['BASELINE']['checks']['control_xyz_sha256'],
            'Saved BASELINE controls changed.')
    with np.load(folders['VALLEY_PRIORITY']/'control_quad.npz', allow_pickle=False) as saved:
        priority_xyz = saved['xyz']
        require(np.array_equal(saved['chart'], chart) and np.array_equal(saved['faces'], common.faces),
            'Priority chart/control topology differs from common reference.')
        require(finish.array_hash(priority_xyz) == metadata['VALLEY_PRIORITY']['checks']['control_xyz_sha256'],
            'Saved priority controls changed.')
    with np.load(folders['VALLEY_PRIORITY']/'operation_fields.npz', allow_pickle=False) as saved:
        priority = saved['delta']
        verified.check_actual_delta(priority_xyz, reference,
            dict(delta=priority, changed_region=saved['changed_region']), baseline_xyz, chart)
        require(np.array_equal(saved['parent_core_weight'], core) and
            np.array_equal(saved['selected_patch_envelope'], selected['envelope']), 'Priority ownership fields differ.')
    del priority_xyz; gc.collect()
    with np.load(folders['FLOW_CHAIN']/'operation_fields.npz', allow_pickle=False) as saved:
        middle = saved['middle_delta']
        require(middle.shape == reference.shape and np.isfinite(middle).all(), 'Invalid saved actual middle delta.')
        require(np.array_equal(saved['parent_core_weight'], core) and
            np.array_equal(saved['selected_patch_envelope'], selected['envelope']), 'FLOW ownership fields differ.')
        expected_region = ((core > 0) | (envelope > 0) | (np.linalg.norm(middle, axis=1) > 0)).astype(np.uint8)
        require(np.array_equal(saved['changed_region'], expected_region), 'Saved FLOW active-region mask differs.')
        flow_actual_delta = saved['delta']
    with np.load(folders['FLOW_CHAIN']/'control_quad.npz', allow_pickle=False) as saved:
        flow_xyz = saved['xyz']
        require(np.array_equal(saved['chart'], chart) and np.array_equal(saved['faces'], common.faces),
            'FLOW chart/control topology differs from common reference.')
        require(finish.array_hash(flow_xyz) == metadata['FLOW_CHAIN']['checks']['control_xyz_sha256'],
            'Saved FLOW controls changed.')
    verified.check_actual_delta(flow_xyz, reference,
        dict(delta=flow_actual_delta, changed_region=expected_region), baseline_xyz, chart)
    del flow_actual_delta; gc.collect()

    # FLOW's saved final delta is already capped: it cannot supply honest
    # pre-cap statistics. Resample the saved atlas once on the actual meso
    # carrier; do not generate an atlas or iterate a new fractal field.
    meso = copy.copy(common)
    meso.xyz = reference+middle
    native = t.growth.native(meso)
    colonies = bulb.read_arrays(root/case/'guided_colonies.npz')
    provenance = verified.guided_source_provenance(colonies, native, meso.xyz)
    normals = finish.stream_control_normals(native.xyz, native.faces[:, :3], len(meso.xyz))
    del native; gc.collect()
    guided, guided_fields = bulb.apply_colonies(meso.xyz, chart, normals, colonies,
        bulb.read_arrays(atlas_path), .30, identity['relief_recipe'])
    del meso, normals, colonies, guided_fields; gc.collect()
    flow_raw = compose_raw(priority, middle, envelope, guided)
    flow_cap = cap_diagnostics(flow_raw)
    flow_expected = reference+study.reflect(study.bound_delta(flow_raw), chart)
    flow_replay = flow_replay_check(flow_expected, flow_xyz)
    del flow_raw, flow_expected, flow_xyz, guided; gc.collect()
    raw = compose_raw(priority, middle, envelope)
    ablation_cap = cap_diagnostics(raw)
    delta = study.reflect(study.bound_delta(raw), chart)
    del raw, priority; gc.collect()
    changed = expected_region
    common.xyz, delta, unchanged_restoration = preserve_unchanged_baseline(
        reference, delta, baseline_xyz, chart, changed)
    operation_check = verified.check_actual_delta(common.xyz, reference,
        dict(delta=common.xyz-reference, changed_region=changed), baseline_xyz, chart)
    del baseline_xyz; gc.collect()
    with np.load(folders['FLOW_CHAIN']/'geometry.npz', allow_pickle=False) as saved:
        flow_faces_hash = finish.array_hash(saved['faces'])
    require(flow_faces_hash == metadata['FLOW_CHAIN']['checks']['native_faces_sha256'],
        'Saved actual FLOW native faces differ from their generation receipt.')
    fields = dict(changed_region=changed, parent_core_weight=core,
        selected_patch_envelope=selected['envelope'], replacement_envelope=envelope, middle_delta=middle)
    folder = output/CANDIDATE/case/'G06'
    info = dict(identity, candidate=CANDIDATE, combined_operation=True, ablation_scope=SCOPE,
        ablation_source_root=str(root), inherited_atlas_internal_iterations=10,
        new_atlas_evaluations=0, saved_atlas_relief_resamplings_for_flow_diagnostics=1,
        operation='priority + saved FLOW middle_delta + replacement_envelope*(0-priority) → same .30 vector cap → same material reflection',
        comparison='Same FLOW meso fold, measured patch, common relaxed carrier and topology; guided relief replaced locally by zero.',
        exact_unchanged_baseline_restoration=unchanged_restoration,
        cap_comparison=dict(FLOW_CHAIN=flow_cap, MESO_ONLY_PATCH=ablation_cap),
        source_flow_generation_sha256=bulb.digest(folders['FLOW_CHAIN']/'generation.json'),
        source_flow_fields_sha256=bulb.digest(folders['FLOW_CHAIN']/'operation_fields.npz'),
        source_priority_fields_sha256=bulb.digest(folders['VALLEY_PRIORITY']/'operation_fields.npz'))
    checks = study.save_state(folder, common, chart, tags, reference, delta, info, fields)
    require(checks['native_faces_sha256'] == flow_faces_hash, 'Ablation native faces differ from actual saved FLOW faces.')
    del delta, middle, fields; gc.collect()

    # Bind the verification to the files actually saved, including both native
    # coordinate reflections. Oriented native X reflection is measured by
    # save_state; Y here is a coordinate/connectivity check only.
    with np.load(folder/'control_quad.npz', allow_pickle=False) as saved:
        require(finish.array_hash(saved['xyz']) == checks['control_xyz_sha256'] and
            np.array_equal(saved['faces'], common.faces), 'Saved ablation controls/topology differ.')
    with np.load(folder/'operation_fields.npz', allow_pickle=False) as saved:
        require(np.array_equal(saved['delta'], common.xyz-reference), 'Saved ablation actual delta differs.')
    pairs, pair_receipts = verified.reflection_pairs(common, chart)
    with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
        xyz = saved['xyz']
        require(finish.array_hash(xyz) == checks['native_xyz_sha256'] and
            finish.array_hash(saved['faces']) == flow_faces_hash, 'Saved ablation native geometry hashes differ.')
        coordinate_reflections = verified.coordinate_symmetry(xyz, pairs, pair_receipts)
    del xyz, pairs, common, chart, tags, reference; gc.collect()
    return dict(passed=True, input_case=case, candidate=CANDIDATE, scope=SCOPE,
        source_common_reference_sha256=identity['common_reference_xyz_sha256'], common_reference_reconstructed_exact=True,
        actual_delta=operation_check, checks=checks, native_faces_identical_to_saved_FLOW_CHAIN=True,
        exact_unchanged_baseline_restoration=unchanged_restoration,
        actual_native_coordinate_reflections=coordinate_reflections,
        y_reflection_scope='Actual native XYZ reflection and identical connectivity; oriented Y triangle sets not independently rechecked.',
        saved_actual_delta_exact=True, source_FLOW_replay=flow_replay,
        saved_guided_source_provenance=provenance,
        cap_comparison=dict(FLOW_CHAIN=flow_cap, MESO_ONLY_PATCH=ablation_cap),
        inherited_atlas_internal_iterations=10, new_atlas_evaluations=0,
        saved_atlas_relief_resamplings_for_flow_diagnostics=1,
        generation_json_sha256=bulb.digest(folder/'generation.json'))


def run(root, output, cases=CASES):
    root, output = Path(root).resolve(), Path(output).resolve()
    inventory(root, cases)
    require(read_json(root/'RECIPE.json') == study.RECIPE, 'Input recipe differs from the implemented common recipe.')
    require(root not in output.parents, 'Ablation output must be separate from the preserved input root.')
    if output.exists():
        raise FileExistsError('Existing ablation output preserved: '+str(output))
    output.mkdir(parents=True)
    receipt = dict(passed=False, candidate=CANDIDATE, source_root=str(root), requested_cases=list(cases),
        same_rule_two_inputs_checked=False, scope=SCOPE, ablation_module_sha256=bulb.digest(Path(__file__)),
        aesthetic_quality='NOT_CERTIFIED', self_intersection='NOT_CHECKED_PER_EXPLORATION_SCOPE', states=[])
    try:
        study.write_json(output/'ABLATION_RECIPE.json', dict(parent_recipe=study.RECIPE,
            candidate=CANDIDATE, scope=SCOPE, maximum_total_vector_relief=.30,
            inherited_atlas_internal_iterations=10, new_atlas_evaluations=0))
        for case in cases:
            receipt['states'].append(run_case(root, output, case))
        receipt['passed'] = all(state['passed'] for state in receipt['states'])
        receipt['same_rule_two_inputs_checked'] = receipt['passed'] and set(cases) == set(CASES)
    except Exception as error:
        receipt['error'] = type(error).__name__+': '+str(error)
        study.write_json(output/'ABLATION_VERIFICATION.json', receipt)
        raise
    study.write_json(output/'ABLATION_VERIFICATION.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Existing complete parent-guided trial output.')
    parser.add_argument('--output', type=Path, required=True, help='Fresh output root; existing paths are refused.')
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    args = parser.parse_args()
    receipt = run(args.root, args.output, args.case)
    print('ABLATION_COMPLETE', receipt['passed'], ','.join(args.case), flush=True)


if __name__ == '__main__':
    main()
