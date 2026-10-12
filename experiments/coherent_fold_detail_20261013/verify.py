"""Independent spatial-signal and coupled CC replay for six coherent G5 states.

The preceding sidewall verifier supplies actual G3-to-G4 ancestry and mirror
IDs. Frozen COMBINED renders remain a linked comparison, not a new replay.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASES = ('SPAN', 'COUNTER')
MODES = ('COHERENT', 'DIRECTIONAL', 'ROLE_CURVATURE')
if str(REPO/'src') not in sys.path:
    sys.path.insert(0, str(REPO/'src'))
from cheshire import reference_subdivision as R


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load_module('coherent_reused_late_verifier', HERE.parent/'late_detail_rules_20261013/verify.py')
H = P.H
require, digest, read_json = H.require, H.digest, H.read_json


def inventory(root):
    paths = [root/name for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json')]
    paths.extend(root/mode/case/'G05'/name for mode in MODES for case in CASES
        for name in ('control_quad.npz', 'geometry.npz', 'evidence.npz', 'generation.json'))
    require(all(path.is_file() for path in paths), 'All six coherent-rule states for SPAN/COUNTER are required.')


def controls_from_amplitude(amplitude, topology, vertex_count):
    """Direct controls approximating a shared normal offset, not exact curves."""
    amplitude = np.asarray(amplitude)
    require(amplitude.shape == (len(topology['n']),) and np.isfinite(amplitude).all(),
        'Finite actual per-face amplitude required.')
    degree = topology['degree']
    require(degree.shape == (vertex_count,) and np.all(degree > 0), 'Actual nonzero vertex degree required.')
    edge_mean = amplitude[topology['ef']].mean(axis=1)
    counts = np.bincount(topology['a'], minlength=vertex_count)
    vertex_mean = np.bincount(topology['a'], weights=amplitude[topology['fi']], minlength=vertex_count)/counts
    controls = {key: np.zeros(size) for key, size in (
        ('w1', len(edge_mean)), ('w2', vertex_count), ('w3', len(amplitude)), ('w4', len(amplitude)),
        ('w6', len(amplitude)), ('w7', len(edge_mean)))}
    controls.update(wf=amplitude, we=.5*edge_mean, wp=(1.-1./degree)*vertex_mean)
    return controls


def actual_geometry_signals(mesh, topology, reference):
    """Measure four actual adjacent faces and cyclically invariant warping."""
    nf = reference.fields(mesh, topology)['nf']
    require(np.all(np.linalg.norm(nf, axis=1) >= .99), 'Actual nondegenerate incoming face normals required.')
    incident = topology['ef'][topology['fe']]
    current = np.arange(len(mesh.faces))[:, None]
    neighbours = np.where(incident[:, :, 0] == current, incident[:, :, 1], incident[:, :, 0])
    dots = np.sum(nf[:, None, :]*nf[neighbours], axis=2)
    bending = np.mean(1.-np.clip(dots, -1., 1.), axis=1)
    points = mesh.xyz[mesh.faces]
    distances = []
    for corner in range(4):
        p = np.roll(points, -corner, axis=1)
        plane = np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
        norms = np.linalg.norm(plane, axis=1)
        perimeter = (np.linalg.norm(p[:, 1]-p[:, 0], axis=1)+
            np.linalg.norm(p[:, 2]-p[:, 1], axis=1)+np.linalg.norm(p[:, 0]-p[:, 2], axis=1))
        require(np.all(norms > 0.) and np.all(perimeter > 0.), 'Nondegenerate actual three-point planes required.')
        unit = plane/norms[:, None]
        distances.append(np.abs(np.sum((p[:, 3]-p[:, 0])*unit, axis=1))/perimeter)
    planarity = np.max(np.stack(distances), axis=0)
    require(np.isfinite(bending).all() and np.isfinite(planarity).all(), 'Finite actual geometry signals required.')
    return neighbours, bending, planarity


def independent_fields(mesh, g4_evidence, g3_evidence, mode, recipe, reference=R):
    require(mode in MODES and mesh.generation == 4, 'Declared coherent mode and actual G4 required.')
    require(recipe['normal']['edge_incident_mean_factor'] == .5 and
        recipe['normal']['vertex_incident_mean_factor'] == '1 - 1 / actual degree' and
        recipe['fixed_zero'] == ['w1', 'w2', 'w3', 'w4', 'w6', 'w7'],
        'Coherent normal-control approximation and zero Eq4 contract differ.')
    topology, support, edge_support, vertex_support, eligible = P.independent_support(mesh, g4_evidence, g3_evidence, reference)
    parent, owners = np.asarray(g4_evidence['parent_face']), np.asarray(g3_evidence['face_event_ids'])
    roles, signs = np.asarray(g3_evidence['face_roles']), np.asarray(g3_evidence['mirror_face_signs'])
    require(roles.shape == owners.shape and roles.dtype.kind in 'iu' and np.isin(roles, [0, 1, 2]).all() and
        np.array_equal(owners > 0, roles > 0), 'Actual SOURCE/WALL/CAP roles must follow event ownership, not V/E/F classes.')
    require(mesh.classes.shape == (len(mesh.xyz),) and mesh.classes.dtype.kind in 'iu' and
        np.isin(mesh.classes, [-1, 0, 1, 2]).all(), 'Actual previous-point V/E/F classes required independently of anatomical roles.')
    require(signs.shape == (len(owners), 2) and signs.dtype.kind in 'iu' and np.isin(signs, [-1, 1]).all(),
        'Actual inherited G3 mirror face signs required.')
    frame = {key: np.asarray(g3_evidence['inherited_root_pca_'+key], float)
        for key in ('origin', 'major', 'minor', 'normal', 'extent')}
    require(all(value.shape == ((2,) if key == 'extent' else (3,)) and np.isfinite(value).all()
        for key, value in frame.items()) and np.all(frame['extent'] > 0.), 'Finite actual inherited root PCA frame required.')
    basis = np.column_stack([frame[key] for key in ('major', 'minor', 'normal')])
    radius_array = np.asarray(g3_evidence['inherited_root_radius'], float)
    require(np.allclose(basis.T@basis, np.eye(3), atol=2e-10, rtol=0.) and
        radius_array.shape == () and np.isfinite(radius_array) and radius_array > 0., 'Orthonormal inherited frame and positive root radius required.')
    radius = float(radius_array)
    actual = reference.fields(mesh, topology)
    mirror = signs[parent]
    canonical = actual['c']*np.column_stack([mirror, np.ones(len(mesh.faces), int)])
    coordinates = (canonical-frame['origin'])@basis/radius
    band_recipe = recipe['band']; longitudinal = coordinates[:, 0]
    phase = 2*np.pi*(coordinates[:, 1]/band_recipe['period_root_radius']+
        band_recipe['major_linear']*longitudinal+band_recipe['major_warp_amplitude']*
        np.sin(band_recipe['major_warp_frequency']*longitudinal+band_recipe['major_warp_phase']))
    band = np.cos(phase)
    neighbours, bending, planarity = actual_geometry_signals(mesh, topology, reference)
    raw_role = np.asarray([recipe['role_weights'][key] for key in ('SOURCE', 'WALL', 'CAP')])[roles[parent]]
    pool = recipe['role_pool']
    role_gain = (pool['own_weight']*raw_role+pool['neighbor_mean_weight']*raw_role[neighbours].mean(axis=1))/pool['divisor']
    gain = recipe['geometry_gain']
    geometry_gain = gain['floor']+(1-gain['floor'])*np.exp(-bending/gain['bending_scale']-planarity/gain['planarity_scale'])
    applied = role_gain*geometry_gain if mode == 'ROLE_CURVATURE' else np.ones(len(mesh.faces))
    scalar = recipe['amplitude']*support*(np.ones(len(mesh.faces)) if mode == 'COHERENT' else band)*applied
    controls = controls_from_amplitude(scalar, topology, len(mesh.xyz))
    edge_scalar = scalar[topology['ef']].mean(axis=1)
    counts = np.bincount(topology['a'], minlength=len(mesh.xyz))
    vertex_scalar = np.bincount(topology['a'], weights=scalar[topology['fi']], minlength=len(mesh.xyz))/counts
    phase_delta = phase[topology['ef'][:, 1]]-phase[topology['ef'][:, 0]]
    supported_edges = np.all(support[topology['ef']] > 0., axis=1)
    seam_edges = np.any(mirror[topology['ef'][:, 0]] != mirror[topology['ef'][:, 1]], axis=1) & supported_edges
    fields = dict(input_g4_to_g3_face_ids=parent.copy(), input_g3_face_event_ids=owners.copy(),
        input_g3_face_roles=roles.copy(), input_g3_mirror_face_signs=signs.copy(),
        input_face_event_ids=owners[parent], input_face_roles=roles[parent], input_face_mirror_signs=mirror,
        input_point_classes=mesh.classes.copy(), input_face_support=support, input_edge_support=edge_support,
        input_vertex_support=vertex_support, input_face_neighbour_ids=neighbours, input_vertex_degree=topology['degree'],
        input_face_normals=actual['nf'], input_edge_normals=actual['ne'], input_vertex_normals=actual['nv'],
        face_centroids=actual['c'], canonical_face_centroids=canonical, root_coordinates=coordinates,
        face_phase=phase, face_band=band, face_bending=bending, face_planarity=planarity,
        face_role_weight_raw=raw_role, face_role_gain=role_gain, face_geometry_gain=geometry_gain,
        face_applied_gain=applied, face_scalar=scalar, edge_scalar=edge_scalar, vertex_scalar=vertex_scalar,
        phase_edge_delta=phase_delta, supported_phase_edge_mask=supported_edges,
        phase_edge_alias_mask=supported_edges & (np.abs(phase_delta) > np.pi),
        supported_phase_seam_edge_mask=seam_edges, eq4_eligible_mask=eligible,
        physical_wavelength=np.array(band_recipe['period_root_radius']*radius),
        root_minor_cycles=np.array(frame['extent'][1]/(band_recipe['period_root_radius']*radius)),
        inherited_root_radius=np.array(radius))
    fields.update({'inherited_root_pca_'+key: value.copy() for key, value in frame.items()})
    require(all(np.isfinite(value).all() for value in fields.values()), 'Finite independent spatial signals required.')
    return topology, controls, fields


def verify_rule_evidence(mesh, g4_evidence, g3_evidence, mode, state, recipe, reference=R):
    topology, controls, fields = independent_fields(mesh, g4_evidence, g3_evidence, mode, recipe, reference)
    for key, value in dict(fields, **{'resolved_'+key: value for key, value in controls.items()}).items():
        require(key in state and H.array_bits_equal(state[key], value), 'Independent actual spatial/class/control evidence differs: '+key)
    return topology, controls, fields


def phase_sampling(fields):
    phase_abs = np.abs(fields['phase_edge_delta'][fields['supported_phase_edge_mask']])
    return dict(physical_wavelength=float(fields['physical_wavelength']),
        cycles_across_inherited_root_minor_extent=float(fields['root_minor_cycles']),
        supported_adjacent_edge_count=int(fields['supported_phase_edge_mask'].sum()),
        supported_neighbor_unwrapped_phase_abs_quantiles=[] if not len(phase_abs) else np.quantile(phase_abs, [0, .5, .9, 1.]).tolist(),
        alias_fraction_over_pi=0. if not len(phase_abs) else float((phase_abs > np.pi).mean()),
        supported_mirror_seam_edge_count=int(fields['supported_phase_seam_edge_mask'].sum()),
        interpretation='Sampling diagnostic only; not an aesthetic PASS threshold. Phase is unwrapped.')


def verify_operator_metadata(metadata, reference_metadata, fields, mesh, g4_evidence, g3_evidence, mode, recipe, core):
    supported, eligible = fields['input_face_support'] > 0., fields['eq4_eligible_mask']
    controls = controls_from_amplitude(fields['face_scalar'], core.topology(mesh), len(mesh.xyz))
    source_hashes = {name: hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest() for name, array in (
        ('xyz', mesh.xyz), ('faces', mesh.faces), ('classes', mesh.classes),
        ('g4_parent_face', g4_evidence['parent_face']), ('g3_face_event_ids', g3_evidence['face_event_ids']),
        ('g3_face_roles', g3_evidence['face_roles']), ('g3_mirror_face_signs', g3_evidence['mirror_face_signs']))}
    expected = dict(experiment='COHERENT_FOLD_DETAIL_20261013', mode=mode, recipe=recipe,
        support_policy=recipe['support_policy'], source_generation=4, output_generation=5,
        subdivision_passes_added=1, added_topology_events=0, added_field_passes=0,
        actual_class_counts={str(c): int((mesh.classes == c).sum()) for c in (-1, 0, 1, 2)},
        supported_face_count=int(supported.sum()),
        resolved_control_ranges={name: [float(value.min()), float(value.max())] for name, value in controls.items()},
        supported_eq4_eligible_count=int((eligible & supported).sum()),
        supported_eq4_fallback_count=int((~eligible & supported).sum()),
        phase_diagnostics=phase_sampling(fields), source_array_hashes=source_hashes, coherence_scope=recipe['coherence_scope'])
    require(all(metadata[key] == value for key, value in dict(reference_metadata, **expected).items()),
        'Independent actual spatial/class/control metadata differs.')


def scalar_reflection(fields, mesh, pairs):
    result = {}
    for axis, vertex_pair in pairs.items():
        face_pair = H.face_involution(mesh.faces, vertex_pair, label='Incoming '+axis)
        errors = {}
        for key in ('input_face_support', 'face_phase', 'face_bending', 'face_planarity',
                'face_role_gain', 'face_geometry_gain', 'face_scalar'):
            value = fields[key]
            maximum = float(np.max(np.abs(value-value[face_pair])))
            tolerance = 1e-12*max(1., float(np.max(np.abs(value))))
            require(maximum <= tolerance, 'Actual incoming scalar reflection differs: '+axis+'/'+key)
            errors[key] = dict(maximum_error=maximum, tolerance=tolerance)
        result[axis] = dict(passed=True, errors=errors,
            scope='Actual incoming G4 face reflection IDs; final native XYZ and oriented triangles are checked separately.')
    return result


def check_baseline_records(source, case, info, proof, render_state):
    """Bind preserved baseline records without claiming to replay its meshes."""
    require(info['candidate'] == 'COMBINED' and info['input_case'] == case and
        info['subdivision_generation'] == 5 and info['source_generation'] == 4 and
        info['preserved_parent']['control_sha256'] == source['control_sha256'] and
        Path(info['source']).resolve() == Path(source['path']).resolve() and
        proof['passed'] is True and proof['candidate'] == 'COMBINED' and proof['actual_generation'] == 5 and
        proof['generation_json_sha256'] == source['baseline']['generation_sha256'] and
        proof['exact_control_native_and_evidence_replay'] is True and proof['actual_native_topology']['passed'] is True and
        set(proof['actual_native_symmetry']) == {'X', 'Y'} and
        all(axis['passed'] is True for axis in proof['actual_native_symmetry'].values()) and
        all(info['checks'][key] == value for key, value in proof['hashes'].items()),
        'Frozen COMBINED actual PASS must bind the same actual G4 and saved G5 arrays.')
    require(render_state['input_case'] == case and render_state['candidate'] == 'COMBINED' and
        render_state['subdivision_generation'] == 5 and render_state['reused_reference'] is False and
        render_state['generation_sha256'] == source['baseline']['generation_sha256'] and
        render_state['control_sha256'] == source['baseline']['control_sha256'] and
        render_state['geometry_sha256'] == source['baseline']['geometry_sha256'] and
        Path(render_state['geometry']).resolve() == (Path(source['baseline']['path'])/'geometry.npz').resolve() and
        render_state['native_arrays']['xyz_sha256'] == proof['hashes']['native_xyz_sha256'] and
        render_state['native_arrays']['faces_sha256'] == proof['hashes']['native_faces_sha256'] and
        render_state['source_provenance']['parent_control_sha256'] == source['control_sha256'] and
        render_state['source_provenance']['parent_generation_sha256'] == source['generation_sha256'] and
        render_state['source_provenance']['parent_verification_sha256'] == source['parent_verification_sha256'] and
        render_state['independent_geometry_generation_sha256'] == proof['generation_json_sha256'],
        'Frozen COMBINED render must bind the actual saved baseline and independent geometry PASS.')
    return proof['shared_control_array_hashes'], proof['hashes']


def baseline_binding(source, case, states, runner):
    runner.check_stage(source['baseline'])
    for name in ('baseline_verification', 'baseline_render_verification'):
        require(digest(source[name]) == source[name+'_sha256'], 'Frozen baseline receipt changed: '+name)
    verified, rendered = [read_json(source[name]) for name in ('baseline_verification', 'baseline_render_verification')]
    require(verified['status'] == 'PASS' and verified['expected_cases'] == list(CASES) and
        verified['expected_modes'] == list(P.MODES) and set(verified['cases']) == set(CASES) and
        digest(HERE.parent/'late_detail_rules_20261013/verify.py') == verified['verifier_module_sha256'],
        'Complete preserved late-rule independent PASS required.')
    for value in verified['cases'].values():
        require(value['passed'] is True and set(value['states']) == set(P.MODES) and
            all(state['passed'] is True for state in value['states'].values()), 'All eight preserved baseline state proofs required.')
    require(read_json(Path(verified['root'])/'RECIPE.json') == verified['recipe'] and
        digest(Path(verified['root'])/'source_index.json') == verified['source_index_sha256'],
        'Preserved baseline recipe/source-index receipt linkage differs.')
    for relative, checksum in verified['recipe']['geometry_code_sha256'].items():
        require(digest(REPO/relative) == checksum, 'Frozen baseline geometry code differs: '+relative)
    require(rendered['passed'] is True and rendered['expected_cases'] == list(CASES) and
        rendered['expected_modes'] == list(P.MODES) and rendered['actual_mesh_states'] == 8 and
        rendered['independent_geometry_verification_sha256'] == source['baseline_verification_sha256'] and
        Path(rendered['independent_geometry_verification']).resolve() == Path(source['baseline_verification']).resolve(),
        'Preserved render PASS must link the exact baseline independent PASS.')
    matches = [state for state in rendered['states'] if state['input_case'] == case and state['candidate'] == 'COMBINED']
    require(len(matches) == 1, 'Exactly one preserved COMBINED render state per input required.')
    proof = verified['cases'][case]['states']['COMBINED']
    shared, hashes = check_baseline_records(source, case,
        read_json(Path(source['baseline']['path'])/'generation.json'), proof, matches[0])
    for state in states.values():
        require(state['shared_control_array_hashes'] == shared and all(state['hashes'][key] == hashes[key]
            for key in ('control_faces_sha256', 'native_faces_sha256', 'chart_sha256')),
            'New conditions and frozen COMBINED must share ordered faces/classes/rest/anchors/chart and native faces.')
    return dict(passed=True, baseline=source['baseline'], common_actual_G4_control_sha256=source['control_sha256'],
        actual_verification_sha256=source['baseline_verification_sha256'],
        render_verification_sha256=source['baseline_render_verification_sha256'],
        shared_control_array_hashes=shared, common_native_faces_sha256=hashes['native_faces_sha256'],
        frozen_baseline_mesh_rerun=False, frozen_baseline_images_reused=True,
        scope='Frozen COMBINED file/metadata/actual-PASS/render-PASS linkage and common ordered arrays; no new baseline mesh or image.')


def verify_state(root, source, case, mode, mesh, chart, g4_evidence, g3_evidence, pairs, runner):
    folder = root/mode/case/'G05'; info = read_json(folder/'generation.json')
    out, outchart, metadata, evidence = runner.refine(mesh, chart, g4_evidence, g3_evidence, mode)
    topology, controls, fields = verify_rule_evidence(mesh, g4_evidence, g3_evidence, mode,
        evidence, runner.fold.RECIPE, R)
    independent, reference_metadata, reference_state = runner.core.subdivide(mesh,
        {'weights': {key: 0. for key in controls}}, scale_mode=runner.fold.RECIPE['scale_mode'], resolved_controls=controls)
    for key in ('xyz', 'faces', 'classes', 'rest', 'anchors'):
        require(H.array_bits_equal(getattr(out, key), getattr(independent, key)), 'Independent coupled CC output differs: '+key)
    for key, value in reference_state.items():
        require(key in evidence and H.array_bits_equal(evidence[key], value), 'Independent actual CC reference state differs: '+key)
    verify_operator_metadata(metadata, reference_metadata, fields, mesh, g4_evidence, g3_evidence,
        mode, runner.fold.RECIPE, runner.core)
    face_chart = runner.core.mean_incident(chart[topology['a']], topology['fi'], len(mesh.faces))
    independent_chart = np.concatenate([chart, chart[topology['edges']].mean(1), face_chart])
    require(H.array_bits_equal(outchart, independent_chart), 'Actual linear CC chart transport differs.')
    expected = dict(input_case=case, candidate=mode, source=source['path'], source_control_sha256=source['control_sha256'],
        source_generation=4, source_surface='mean', preserved_parent=source, geometry_code_sha256=runner.geometry_code_hashes(),
        coherent_rules=runner.fold.RECIPE, operator_metadata=metadata, added_CC_passes=1, added_topology_events=0,
        added_field_passes=0, added_mandelbulb_evaluations=0, subdivision_generation=5)
    require(out.generation == independent.generation == 5 and all(info[key] == value for key, value in expected.items()) and
        info['checks']['passed'] is True, 'Actual coherent-rule generation/source/frozen-code metadata differs.')
    H.verify_surface_labels(info, 'mean')
    for filename, key in [('control_quad.npz', 'control_file_sha256'), ('geometry.npz', 'geometry_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')]:
        require(digest(folder/filename) == info[key], 'Actual coherent-rule file hash differs: '+filename)
    H.exact_evidence(folder/'control_quad.npz', dict(xyz=out.xyz, faces=out.faces, chart=outchart, classes=out.classes,
        rest=out.rest, anchors=out.anchors, generation=np.array(5), surface=np.array('mean')))
    H.exact_evidence(folder/'evidence.npz', evidence)
    xyz, triangles = runner.core.native(out)
    H.exact_evidence(folder/'geometry.npz', dict(xyz=xyz, faces=triangles))
    hashes = {key: runner.core.array_hash(array) for key, array in [('control_xyz_sha256', out.xyz), ('control_faces_sha256', out.faces),
        ('chart_sha256', outchart), ('native_xyz_sha256', xyz), ('native_faces_sha256', triangles)]}
    require(all(info['checks'][key] == value for key, value in hashes.items()), 'Saved coherent-rule actual array hash differs.')
    final_pairs = {axis: H.refine_mirror_pairs(mesh.faces, reference_state['input_edges'], pair) for axis, pair in pairs.items()}
    native_topology, symmetry = H.actual_topology(xyz, triangles), H.actual_native_symmetry(xyz, triangles, out.faces, final_pairs)
    require(abs(native_topology['minimum_actual_triangle_area']-info['checks']['minimum_native_triangle_area']) <= 3e-12 and
        all(info[key] == count for key, count in [('control_vertices', len(out.xyz)), ('control_quads', len(out.faces)),
            ('native_vertices', len(xyz)), ('native_triangles', len(triangles))]), 'Actual coherent-rule sizes/area differ.')
    result = dict(passed=True, candidate=mode, actual_generation=5, added_CC_passes=1,
        actual_spatial_signals_controls_and_independent_coupled_CC_replay=True, exact_control_native_and_evidence_replay=True,
        hashes=hashes, actual_native_topology=native_topology, actual_native_symmetry=symmetry,
        incoming_scalar_reflection=scalar_reflection(fields, mesh, pairs),
        shared_control_array_hashes={key: runner.core.array_hash(array) for key, array in
            [('faces', out.faces), ('classes', out.classes), ('rest', out.rest), ('anchors', out.anchors), ('chart', outchart)]},
        phase_sampling=phase_sampling(fields), generation_json_sha256=digest(folder/'generation.json'))
    del out, independent, xyz, triangles, evidence, reference_state, fields; gc.collect()
    return result


def verify_case(root, source, case, runner):
    runner.core.memory_guard()
    mesh, chart, g4_evidence, g3_evidence, pairs, parent = P.load_actual_parent(source, case, runner)
    states = {mode: verify_state(root, source, case, mode, mesh, chart, g4_evidence, g3_evidence, pairs, runner) for mode in MODES}
    require(all(state['shared_control_array_hashes'] == states[MODES[0]]['shared_control_array_hashes'] for state in states.values()),
        'All three variants must share ordered faces/classes/rest/anchors/chart.')
    baseline = baseline_binding(source, case, states, runner)
    for stage in (source, source['g3'], source['neutral'], source['baseline']):
        runner.check_stage(stage)
    del mesh, chart, g4_evidence, g3_evidence, pairs; gc.collect()
    return dict(passed=True, input_case=case, parent=parent, states=states, prior_baseline_binding=baseline,
        visual_success='NOT_ASSESSED; coherent normal-control approximation and numerical validity do not certify actual curves, small folds or hierarchy.')


def run(root):
    root = Path(root).resolve(); inventory(root)
    runner = load_module('verified_coherent_detail_actual_runner', HERE/'study.py')
    recipe, sources, summary = [read_json(root/name) for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json')]
    require(recipe == runner.recipe() and sources == runner.source_index() and set(sources) == set(CASES) and
        tuple(runner.MODES) == MODES and summary['all_six_complete'] is True and summary['quick_integrity_passed'] is True and
        len(summary['states']) == 6 and {(s['candidate'], s['input_case']) for s in summary['states']} ==
        {(mode, case) for mode in MODES for case in CASES}, 'All six conditions require one complete frozen recipe and parent source index.')
    for state in summary['states']:
        require(state == read_json(root/state['candidate']/state['input_case']/'G05/generation.json'), 'Summary differs from actual coherent G5 state.')
    cases = {case: verify_case(root, sources[case], case, runner) for case in CASES}
    return dict(status='PASS', root=str(root), expected_cases=list(CASES), expected_modes=list(MODES), recipe=recipe,
        source_index_sha256=digest(root/'source_index.json'), cases=cases, verifier_module_sha256=digest(Path(__file__)),
        scope='Frozen sidewall metadata/hash linkage; actual G3-to-G4 CC ancestry; independently reconstructed spatial, role and actual-geometry signals and normal controls; direct coupled G4-to-G5 CC; exact six new saved control/native/evidence states; actual one-body native topology/area/XYZ/oriented-triangle symmetry; and frozen COMBINED comparison linkage.',
        excluded=['Original six sidewall meshes all rerun', 'Original eight late-rule meshes all rerun', 'New baseline mesh/image generation',
            'Factorial or exact-curve proof', 'Aesthetic/reference fidelity certification', 'Exact XYZ pinning outside direct support',
            'Self-intersections', 'Fabrication', 'Structural performance', 'Arbitrary input generality'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-receipt', type=Path,
        help='Fresh receipt path; relative names belong to --root. Existing receipts are preserved.')
    args = parser.parse_args()
    output = H.receipt_destination(args.root, args.output_receipt)
    if output.exists():
        raise FileExistsError('Existing coherent-rule verification receipt preserved: '+str(output))
    try:
        receipt = run(args.root)
    except Exception as error:
        receipt = dict(status='FAIL', root=str(args.root.resolve()), error_type=type(error).__name__, error=str(error))
        with output.open('x', encoding='utf8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
        raise
    with output.open('x', encoding='utf8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    print('COHERENT_FOLD_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
