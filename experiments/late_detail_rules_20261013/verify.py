"""Verify four late G4-to-G5 causal rule variants on two frozen inputs.

Actual CC ancestry binds support and explicit mirror IDs. Saved geometry is
replayed, and NEUTRAL must equal the preceding sidewall G5 byte for byte.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASES = ('SPAN', 'COUNTER')
MODES = ('NEUTRAL', 'EQ4_ONLY', 'NORMAL_ONLY', 'COMBINED')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = load_module('late_reused_connected_verifier', HERE.parent/'connected_fold_growth_20261012/verify.py')
require, digest, read_json = H.require, H.digest, H.read_json


def ancestry_support(parent_face, g3_owners, face_count):
    parent_face, g3_owners = np.asarray(parent_face), np.asarray(g3_owners)
    require(parent_face.shape == (face_count,) and parent_face.dtype.kind in 'iu' and face_count > 0 and
        g3_owners.ndim == 1 and g3_owners.dtype.kind in 'iu' and len(g3_owners) > 0 and
        g3_owners.min() >= 0 and parent_face.min() >= 0 and parent_face.max() < len(g3_owners),
        'Actual G4-to-G3 face ancestry and nonnegative G3 event IDs required.')
    return (g3_owners[parent_face] > 0).astype(float)


def causal_controls(mode, face, edge, vertex, coefficients):
    require(mode in MODES, 'Unknown causal rule variant.')
    support = {'face': np.asarray(face), 'edge': np.asarray(edge), 'vertex': np.asarray(vertex)}
    require(all(a.ndim == 1 and np.isfinite(a).all() and np.all((a >= 0.) & (a <= 1.)) for a in support.values()),
        'Finite support fractions in [0,1] required.')
    active_eq4, active_normal = mode in ('EQ4_ONLY', 'COMBINED'), mode in ('NORMAL_ONLY', 'COMBINED')
    controls = {key: np.zeros(len(support[kind])) for key, kind in
        [('w1', 'edge'), ('w2', 'vertex'), ('w3', 'face'), ('w4', 'face'), ('w6', 'face'),
         ('w7', 'edge'), ('wf', 'face'), ('we', 'edge'), ('wp', 'vertex')]}
    for key, kind, active in [('w3', 'face', active_eq4), ('w4', 'face', active_eq4),
            ('wf', 'face', active_normal), ('we', 'edge', active_normal), ('wp', 'vertex', active_normal)]:
        if active:
            controls[key] = support[kind]*coefficients[key]
    return controls


def independent_support(mesh, parent_evidence, g3_evidence, reference):
    topology = reference.topology(mesh)
    face = ancestry_support(parent_evidence['parent_face'], g3_evidence['face_event_ids'], len(mesh.faces))
    edge = face[topology['ef']].mean(axis=1)
    counts = np.bincount(topology['a'], minlength=len(mesh.xyz))
    require(np.all(counts > 0), 'Actual incoming mesh has orphan vertices.')
    vertex = np.bincount(topology['a'], weights=face[topology['fi']], minlength=len(mesh.xyz))/counts
    classes = mesh.classes[mesh.faces]
    eligible = ((classes == 0).sum(axis=1) == 1) & ((classes == 1).sum(axis=1) == 2) & ((classes == 2).sum(axis=1) == 1)
    eligible &= (np.argmax(classes == 0, axis=1)+2) % 4 == np.argmax(classes == 2, axis=1)
    return topology, face, edge, vertex, eligible


def inventory(root):
    paths = [root/name for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json')]
    for case in CASES:
        for mode in MODES:
            paths.extend(root/mode/case/'G05'/name for name in
                ('control_quad.npz', 'geometry.npz', 'evidence.npz', 'generation.json'))
    require(all(path.is_file() for path in paths), 'All eight late-rule states for SPAN/COUNTER are required.')


def verify_rule_evidence(mesh, g4_evidence, g3_evidence, mode, state, recipe, reference):
    topology, face, edge, vertex, eligible = independent_support(mesh, g4_evidence, g3_evidence, reference)
    coefficients = dict(recipe['eq4'], **recipe['normal'])
    controls = causal_controls(mode, face, edge, vertex, coefficients)
    expected = dict(input_face_support=face, input_edge_support=edge, input_vertex_support=vertex,
        input_g4_to_g3_face_ids=g4_evidence['parent_face'], input_g3_face_event_ids=g3_evidence['face_event_ids'],
        input_point_classes=mesh.classes, eq4_eligible_mask=eligible)
    expected.update({'resolved_'+key: value for key, value in controls.items()})
    for key, value in expected.items():
        require(key in state and H.array_bits_equal(state[key], value), 'Actual causal support/class/control evidence differs: '+key)
    return topology, controls, eligible, face


def parent_receipt(receipt, case):
    require(receipt['status'] == 'PASS' and receipt['expected_cases'] == list(CASES) and
        receipt['expected_modes'] == ['SIDEWALL_FAN'] and set(receipt['cases']) == set(CASES),
        'Complete frozen two-input sidewall verification PASS required.')
    for value in receipt['cases'].values():
        require(value['passed'] is True and len(value['stages']) == 3, 'Complete frozen sidewall stage proofs required.')
        for generation, proof in zip((3, 4, 5), value['stages']):
            require(proof['passed'] is True and proof['semantics']['actual_generation'] == generation and
                proof['exact_control_native_and_evidence_replay'] is True and
                proof['actual_native_topology']['passed'] is True and set(proof['actual_native_symmetry']) == {'X', 'Y'} and
                all(axis['passed'] is True for axis in proof['actual_native_symmetry'].values()),
                'All six frozen sidewall replay/topology/symmetry proofs required.')
    return receipt['cases'][case]['stages']


def load_actual_parent(source, case, runner):
    require(digest(source['parent_verification']) == source['parent_verification_sha256'] and
        digest(source['parent_recipe']) == source['parent_recipe_sha256'], 'Frozen sidewall PASS/recipe hash differs.')
    receipt, recipe = read_json(source['parent_verification']), read_json(source['parent_recipe'])
    proofs = parent_receipt(receipt, case)
    require(recipe == receipt['recipe'] and digest(HERE.parent/'sidewall_fan_growth_20261013/verify.py') ==
        receipt['verifier_module_sha256'], 'Frozen sidewall code/recipe receipt linkage differs.')
    for relative, checksum in recipe['geometry_code_sha256'].items():
        require(digest(REPO/relative) == checksum, 'Frozen sidewall geometry code differs: '+relative)
    parent_root = Path(receipt['root'])
    for input_case in CASES:
        for proof in receipt['cases'][input_case]['stages']:
            g = proof['semantics']['actual_generation']
            folder = parent_root/'SIDEWALL_FAN'/input_case/('G03_events' if g == 3 else f'G{g:02d}')
            info = read_json(folder/'generation.json')
            require(digest(folder/'generation.json') == proof['generation_json_sha256'] and
                all(info['checks'][key] == value for key, value in proof['hashes'].items()),
                'Frozen sidewall generation/actual-array receipt link differs.')
    for g, name, stage in ((3, 'G03_events', source['g3']), (4, 'G04', source), (5, 'G05', source['neutral'])):
        require(Path(stage['path']).resolve() == (parent_root/'SIDEWALL_FAN'/case/name).resolve() and
            stage['generation_sha256'] == proofs[g-3]['generation_json_sha256'], 'Frozen source lineage folder differs.')
        runner.check_stage(stage)
    mesh, chart, g4_evidence, g3_evidence = runner.load_parent(source)
    g3, g3chart = runner.core.load_source(source['g3']['path'])
    g3pairs = {axis: g3_evidence['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
    for axis in ('X', 'Y'):
        H.face_involution(g3.faces, g3pairs[axis], g3_evidence['mirror_'+axis.lower()+'_face_pairs'])
    rebuilt, rebuilt_chart, actual_refinement = runner.core.refine(g3, g3chart)
    H.exact_evidence(Path(source['path'])/'control_quad.npz', dict(xyz=rebuilt.xyz, faces=rebuilt.faces,
        chart=rebuilt_chart, classes=rebuilt.classes, rest=rebuilt.rest, anchors=rebuilt.anchors,
        generation=np.array(4), surface=np.array('mean')))
    H.exact_evidence(Path(source['path'])/'evidence.npz', actual_refinement)
    pairs = {axis: H.refine_mirror_pairs(g3.faces, actual_refinement['input_edges'], pair) for axis, pair in g3pairs.items()}
    for current, stage, proof, current_chart in ((g3, source['g3'], proofs[0], g3chart), (rebuilt, source, proofs[1], rebuilt_chart)):
        xyz, triangles = runner.core.native(current)
        H.exact_evidence(Path(stage['path'])/'geometry.npz', dict(xyz=xyz, faces=triangles))
        for key, array in [('control_xyz_sha256', current.xyz), ('control_faces_sha256', current.faces),
                ('chart_sha256', current_chart), ('native_xyz_sha256', xyz), ('native_faces_sha256', triangles)]:
            require(runner.core.array_hash(array) == proof['hashes'][key], 'Actual parent geometry differs from frozen sidewall proof: '+key)
        del xyz, triangles
    del g3, g3chart, rebuilt, rebuilt_chart, actual_refinement; gc.collect()
    return mesh, chart, g4_evidence, g3_evidence, pairs, dict(passed=True,
        frozen_six_stage_metadata_links=True, original_six_meshes_rerun=False,
        actual_G3_to_G4_neutral_CC_and_evidence_exact=True, actual_G3_G4_native_matches_frozen_PASS=True,
        support_and_mirror_ancestry='Actual replayed G3-to-G4 parent_face/input_edges; overlapping chart nearest matching is not used.',
        parent_verification_sha256=source['parent_verification_sha256'])


def neutral_identity(folder, source, info):
    proof = {}
    for filename in ('control_quad.npz', 'geometry.npz'):
        previous = H.read_arrays(Path(source['neutral']['path'])/filename)
        H.exact_evidence(folder/filename, previous)
        proof[filename] = dict(array_keys=sorted(previous), exact_dtype_shape_bytes=True)
        del previous; gc.collect()
    recorded = info['neutral_identity']
    require(recorded['passed'] is True and recorded['reference'] == source['neutral'] and recorded['arrays'] == proof,
        'Recorded neutral identity differs from actual all-array byte equality.')
    return dict(passed=True, reference=source['neutral'], arrays=proof,
        scope='All control/native array inventories, dtypes, shapes and bytes; NPZ containers and new evidence/metadata are excluded.')


def factorial_sanity(positions):
    require(set(positions) == set(MODES), 'All four actual coordinate arrays required for factorial sanity.')
    baseline = np.asarray(positions['NEUTRAL'])
    require(baseline.ndim == 2 and baseline.shape[1] == 3 and len(baseline) > 0 and
        all(np.asarray(value).shape == baseline.shape and np.isfinite(value).all() for value in positions.values()),
        'Finite matching actual factorial XYZ required.')
    scale = max(1., float(np.max(np.abs(baseline))))
    tolerance = 1e-12*scale
    deltas = {mode: np.asarray(value)-baseline for mode, value in positions.items()}
    error = deltas['COMBINED']-(deltas['EQ4_ONLY']+deltas['NORMAL_ONLY'])
    maximum = float(np.max(np.linalg.norm(error, axis=1)))
    require(maximum <= tolerance, 'Actual coupled factorial interaction exceeds floating-point tolerance.')
    displacement = {mode: dict(maximum=float(np.max(np.linalg.norm(delta, axis=1))),
        rms=float(np.sqrt(np.mean(np.sum(delta*delta, axis=1))))) for mode, delta in deltas.items()}
    return dict(passed=True, combined_minus_neutral_equals_sum_of_single_factor_deltas_max_error=maximum,
        tolerance=tolerance, coordinate_scale=scale, displacement_from_neutral=displacement,
        scope='Actual saved G5 control XYZ; algebraic sanity only, no aesthetic success threshold.')


def verify_state(root, source, case, mode, mesh, chart, g4_evidence, g3_evidence, pairs, runner):
    folder = root/mode/case/'G05'; info = read_json(folder/'generation.json')
    out, outchart, metadata, evidence = runner.refine(mesh, chart, g4_evidence, g3_evidence, mode)
    topology, controls, eligible, face = verify_rule_evidence(mesh, g4_evidence, g3_evidence, mode, evidence, runner.late.RECIPE, runner.core)
    independent, reference_metadata, reference_state = runner.core.subdivide(mesh,
        {'weights': {key: 0. for key in controls}}, scale_mode=runner.late.RECIPE['scale_mode'], resolved_controls=controls)
    for key in ('xyz', 'faces', 'classes', 'rest', 'anchors'):
        require(H.array_bits_equal(getattr(out, key), getattr(independent, key)), 'Independent coupled CC output differs: '+key)
    for key, value in reference_state.items():
        require(key in evidence and H.array_bits_equal(evidence[key], value), 'Independent actual CC reference state differs: '+key)
    require(all(metadata[key] == value for key, value in reference_metadata.items()) and
        metadata['eq4_eligible'] == int(eligible.sum()) and metadata['supported_eq4_eligible_count'] == int((eligible & (face > 0)).sum()) and
        metadata['supported_eq4_fallback_count'] == int((~eligible & (face > 0)).sum()) and
        metadata['factors'] == dict(eq4=mode in ('EQ4_ONLY', 'COMBINED'), normal=mode in ('NORMAL_ONLY', 'COMBINED')),
        'Actual coupled-rule metadata/factor/eligibility differs.')
    face_chart = runner.core.mean_incident(chart[topology['a']], topology['fi'], len(mesh.faces))
    independent_chart = np.concatenate([chart, chart[topology['edges']].mean(1), face_chart])
    require(H.array_bits_equal(outchart, independent_chart), 'Actual linear CC chart transport differs.')
    expected = dict(input_case=case, candidate=mode, source=source['path'], source_control_sha256=source['control_sha256'],
        source_generation=4, source_surface='mean', preserved_parent=source, geometry_code_sha256=runner.geometry_code_hashes(),
        late_rules=runner.late.RECIPE, operator_metadata=metadata, added_CC_passes=1, added_topology_events=0,
        added_field_passes=0, added_mandelbulb_evaluations=0, subdivision_generation=5)
    require(out.generation == independent.generation == 5 and all(info[key] == value for key, value in expected.items()) and
        info['checks']['passed'] is True, 'Actual late-rule generation/source/frozen-code metadata differs.')
    H.verify_surface_labels(info, 'mean')
    for filename, key in [('control_quad.npz', 'control_file_sha256'), ('geometry.npz', 'geometry_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')]:
        require(digest(folder/filename) == info[key], 'Actual late-rule file hash differs: '+filename)
    H.exact_evidence(folder/'control_quad.npz', dict(xyz=out.xyz, faces=out.faces, chart=outchart, classes=out.classes,
        rest=out.rest, anchors=out.anchors, generation=np.array(5), surface=np.array('mean')))
    H.exact_evidence(folder/'evidence.npz', evidence)
    xyz, triangles = runner.core.native(out)
    H.exact_evidence(folder/'geometry.npz', dict(xyz=xyz, faces=triangles))
    hashes = {key: runner.core.array_hash(array) for key, array in [('control_xyz_sha256', out.xyz), ('control_faces_sha256', out.faces),
        ('chart_sha256', outchart), ('native_xyz_sha256', xyz), ('native_faces_sha256', triangles)]}
    require(all(info['checks'][key] == value for key, value in hashes.items()), 'Saved late-rule actual array hash differs.')
    final_pairs = {axis: H.refine_mirror_pairs(mesh.faces, reference_state['input_edges'], pair) for axis, pair in pairs.items()}
    native_topology, symmetry = H.actual_topology(xyz, triangles), H.actual_native_symmetry(xyz, triangles, out.faces, final_pairs)
    require(abs(native_topology['minimum_actual_triangle_area']-info['checks']['minimum_native_triangle_area']) <= 3e-12 and
        all(info[key] == count for key, count in [('control_vertices', len(out.xyz)), ('control_quads', len(out.faces)),
            ('native_vertices', len(xyz)), ('native_triangles', len(triangles))]), 'Actual late-rule sizes/area differ.')
    result = dict(passed=True, candidate=mode, actual_generation=5, added_CC_passes=1,
        actual_support_controls_and_independent_coupled_CC_replay=True, exact_control_native_and_evidence_replay=True,
        hashes=hashes, actual_native_topology=native_topology, actual_native_symmetry=symmetry,
        shared_control_array_hashes={key: runner.core.array_hash(array) for key, array in
            [('faces', out.faces), ('classes', out.classes), ('rest', out.rest), ('anchors', out.anchors), ('chart', outchart)]},
        generation_json_sha256=digest(folder/'generation.json'))
    if mode == 'NEUTRAL':
        result['neutral_identity'] = neutral_identity(folder, source, info)
    del out, independent, xyz, triangles, evidence, reference_state; gc.collect()
    return result


def verify_case(root, source, case, runner):
    runner.core.memory_guard()
    mesh, chart, g4_evidence, g3_evidence, pairs, parent = load_actual_parent(source, case, runner)
    states = {mode: verify_state(root, source, case, mode, mesh, chart, g4_evidence, g3_evidence, pairs, runner) for mode in MODES}
    for key in ('control_faces_sha256', 'native_faces_sha256', 'chart_sha256'):
        require(len({state['hashes'][key] for state in states.values()}) == 1, 'Factorial variants must share actual connectivity/chart: '+key)
    require(all(state['shared_control_array_hashes'] == states['NEUTRAL']['shared_control_array_hashes'] for state in states.values()),
        'All four variants must share ordered faces/classes/rest/anchors/chart.')
    positions = {}
    for mode in MODES:
        with np.load(root/mode/case/'G05/control_quad.npz', allow_pickle=False) as saved:
            positions[mode] = saved['xyz']
    factorial = factorial_sanity(positions)
    del positions; gc.collect()
    for stage in (source, source['g3'], source['neutral']):
        runner.check_stage(stage)
    del mesh, chart, g4_evidence, g3_evidence, pairs; gc.collect()
    return dict(passed=True, input_case=case, parent=parent, states=states, actual_factorial_sanity=factorial,
        visual_success='NOT_ASSESSED; nonzero rule effects and numerical validity do not certify fine folds or visual hierarchy.')


def run(root):
    root = Path(root).resolve(); inventory(root)
    runner = load_module('verified_late_detail_actual_runner', HERE/'study.py')
    recipe, sources, summary = [read_json(root/name) for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json')]
    require(recipe == runner.recipe() and sources == runner.source_index() and set(sources) == set(CASES) and
        tuple(runner.MODES) == MODES and summary['all_eight_complete'] is True and summary['quick_integrity_passed'] is True and
        len(summary['states']) == 8 and {(s['candidate'], s['input_case']) for s in summary['states']} ==
        {(mode, case) for mode in MODES for case in CASES}, 'All eight conditions require one complete frozen recipe and parent source index.')
    for state in summary['states']:
        require(state == read_json(root/state['candidate']/state['input_case']/'G05/generation.json'), 'Summary differs from actual late G5 state.')
    cases = {case: verify_case(root, sources[case], case, runner) for case in CASES}
    return dict(status='PASS', root=str(root), expected_cases=list(CASES), expected_modes=list(MODES), recipe=recipe,
        source_index_sha256=digest(root/'source_index.json'), cases=cases, verifier_module_sha256=digest(Path(__file__)),
        scope='Frozen six-stage sidewall metadata/hash linkage, actual G3-to-G4 CC support/mirror ancestry, independent causal control construction and coupled G4-to-G5 replay, exact eight saved states, actual native one-body topology/area/XYZ/oriented-triangle symmetry, and NEUTRAL identity to existing G5.',
        excluded=['Frozen six original meshes all rerun', 'Aesthetic/reference fidelity certification', 'Exact XYZ pinning outside direct support',
            'Self-intersections', 'Fabrication', 'Structural performance', 'Arbitrary input generality'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-receipt', type=Path,
        help='Fresh receipt path; relative names belong to --root. Existing receipts are preserved.')
    args = parser.parse_args()
    output = H.receipt_destination(args.root, args.output_receipt)
    if output.exists():
        raise FileExistsError('Existing late-rule verification receipt preserved: '+str(output))
    try:
        receipt = run(args.root)
    except Exception as error:
        receipt = dict(status='FAIL', root=str(args.root.resolve()), error_type=type(error).__name__, error=str(error))
        with output.open('x', encoding='utf8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
        raise
    with output.open('x', encoding='utf8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    print('LATE_DETAIL_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
