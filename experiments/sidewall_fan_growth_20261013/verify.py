"""Actual sidewall-child edits and two CC passes from a frozen ROOT_ONLY G3.

Reuse the connected pilot's native geometry checks, without rerunning its 18
old meshes. Its PASS receipt is bound to actual parent files and metadata;
the new six stages require independent replay and actual native symmetry.
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
MODE = 'SIDEWALL_FAN'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = load_module('sidewall_reused_connected_verifier', HERE.parent/'connected_fold_growth_20261012/verify.py')
require, digest, read_json = H.require, H.digest, H.read_json


def parent_stage_receipt(receipt, case):
    """Require the complete original PASS; return its ROOT_ONLY G3 proof."""
    require(receipt['status'] == 'PASS' and receipt['expected_cases'] == list(CASES) and
        receipt['expected_modes'] == list(H.MODES) and set(receipt['cases']) == set(CASES),
        'Complete preserved two-input/three-mode parent verification PASS required.')
    for input_case in CASES:
        parent_case = receipt['cases'][input_case]
        require(parent_case['passed'] is True and set(parent_case['states']) == set(H.MODES),
            'Incomplete preserved parent case verification.')
        for state in parent_case['states'].values():
            require(state['passed'] is True and len(state['stages']) == 3,
                'Incomplete preserved parent stage verification.')
            for generation, stage in zip((3, 4, 5), state['stages']):
                require(stage['passed'] is True and stage['semantics']['actual_generation'] == generation and
                    stage['semantics']['added_CC_passes'] == generation-3 and
                    stage['exact_control_native_and_evidence_replay'] is True and
                    stage['actual_native_topology']['passed'] is True and
                    set(stage['actual_native_symmetry']) == {'X', 'Y'} and
                    all(axis['passed'] is True for axis in stage['actual_native_symmetry'].values()),
                    'Preserved parent proof must contain all 18 actual replay/topology/symmetry stages.')
    return receipt['cases'][case]['states']['ROOT_ONLY']['stages'][0]


def sidewall_ownership(events, evidence, parent_evidence):
    """Trace edits from actual inherited face roles, rather than a fresh cube."""
    keys = ('face_event_ids', 'face_roles', 'face_parent_event_ids', 'face_source_ids')
    owners, roles, parents, origins = [np.asarray(parent_evidence[key]).copy() for key in keys]
    require(owners.ndim == 1 and len(owners) > 0 and all(a.shape == owners.shape for a in (roles, parents, origins)) and
        all(a.dtype.kind in 'iu' for a in (owners, roles, parents, origins)), 'Invalid inherited actual face ancestry.')
    for key in keys:
        require(H.array_bits_equal(evidence['initial_parent_'+key], parent_evidence[key]),
            'Initial sidewall ancestry differs from frozen actual parent: '+key)
    immediate = np.arange(len(owners))
    accepted, rejected, seen, proofs = 0, 0, {1}, []
    for event in events:
        event_id = event['event_id']
        require(type(event_id) is int and event_id >= 2 and event_id not in seen and
            event['level'] == 1 and event['parent_event_id'] == 1 and event['parent_role'] == 1 and
            event['status'] in ('accepted', 'rejected'), 'New events must be unique level-1 children of inherited root 1.')
        seen.add(event_id)
        if event['status'] == 'rejected':
            rejected += 1
            continue
        require(event['source_generation'] == 3, 'Sidewall topology event must preserve subdivision G3.')
        key = f'event_{event_id:03d}_'
        selected, mapping, caps = [np.asarray(evidence[key+suffix]) for suffix in
            ('selected_input_faces', 'parent_face', 'generated_cap_faces')]
        require(selected.ndim == 1 and selected.dtype.kind in 'iu' and len(selected) >= 2 and
            len(np.unique(selected)) == len(selected) and selected.min() >= 0 and selected.max() < len(owners),
            'Actual distinct multi-face sidewall support required.')
        require(np.all(owners[selected] == 1) and np.all(roles[selected] == 1),
            'New child must replace inherited root-1 sidewall faces; cap/source/sibling support is forbidden.')
        require(np.array_equal(selected, event['selected_input_faces']) and
            np.array_equal(caps, event['generated_cap_faces']) and
            np.array_equal(evidence[key+'selected_parent_event_ids'], owners[selected]) and
            np.array_equal(evidence[key+'selected_parent_roles'], roles[selected]) and
            np.array_equal(evidence[key+'selected_parent_source_face_ids'], immediate[selected]),
            'Sidewall selection/declared parent evidence differs from immediate face ownership.')
        retained = np.setdiff1d(np.arange(len(owners)), selected)
        require(mapping.ndim == 1 and mapping.dtype.kind in 'iu' and len(mapping) > len(owners) and
            mapping.min() >= 0 and mapping.max() < len(owners) and
            np.array_equal(mapping[:len(retained)], retained), 'Actual sidewall disk parent mapping differs.')
        generated = np.arange(len(mapping)) >= len(retained)
        require(caps.ndim == 1 and caps.dtype.kind in 'iu' and
            np.all(np.isin(mapping[generated], selected)) and
            np.array_equal(caps, np.arange(len(mapping)-len(selected), len(mapping))) and
            np.array_equal(mapping[caps], selected), 'Actual generated child wall/cap support differs.')
        next_parents = parents[mapping].copy()
        next_parents[generated] = owners[mapping[generated]]
        owners, roles, origins, immediate = (owners[mapping].copy(), roles[mapping].copy(),
            origins[mapping], immediate[mapping])
        owners[generated] = event_id; roles[generated] = 1; roles[caps] = 2
        parents = next_parents; accepted += 1
        proofs.append(dict(event_id=event_id, passed=True, input_root_sidewall_faces=len(selected),
            generated_cap_faces=len(caps), generated_wall_faces=int(generated.sum()-len(caps))))
    mirror = np.asarray(evidence['mirror_source_face_ids'])
    require(mirror.ndim == 1 and mirror.dtype.kind in 'iu' and len(mirror) > 0 and
        mirror.min() >= 0 and mirror.max() < len(owners), 'Invalid final canonical mirror ancestry.')
    for key, values in zip(keys, (owners, roles, parents, origins)):
        require(np.array_equal(evidence[key], values[mirror]), 'Final actual sidewall face ancestry differs: '+key)
    signs = np.asarray(evidence['mirror_face_signs'])
    require(signs.shape == (len(mirror), 2) and np.all(np.isin(signs, (-1, 1))), 'Actual face mirror signs required.')
    physical_parent = immediate[mirror].copy()
    for column, axis in enumerate(('x', 'y')):
        pair = H.involution(parent_evidence['mirror_'+axis+'_face_pairs'], len(parent_evidence['face_event_ids']),
            'Inherited '+axis+' parent face mirror')
        selected = signs[:, column] == -1
        physical_parent[selected] = pair[physical_parent[selected]]
    require(np.array_equal(evidence['face_parent_source_ids'], physical_parent),
        'Final actual reflected parent-source face correspondence differs.')
    if 'temporary_parent_face_source_ids' in evidence:
        require(np.array_equal(evidence['temporary_parent_face_source_ids'], immediate),
            'Temporary parent face correspondence differs from actual disk edits.')
    levels = [1, accepted, 0]
    require(np.array_equal(evidence['accepted_event_counts_by_level'], levels) and
        int(evidence['rejected_event_count']) == rejected and int(evidence['inherited_event_count']) == 1 and
        int(evidence['new_accepted_event_count']) == accepted, 'Inherited/new accepted or rejected event counts differ.')
    return dict(passed=True, accepted_canonical_events=1+accepted, inherited_canonical_events=1,
        new_canonical_events=accepted, rejected_canonical_events=rejected,
        attempted_new_canonical_events=len(events), accepted_by_level=levels,
        reflected_constructive_event_instances=4*(1+accepted), new_event_proofs=proofs,
        scope='Inherited actual root sidewall ownership, ordered new disk replacements and final canonical mirror ancestry; no aesthetic success inferred.')


def inventory(root):
    files = [root/name for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json')]
    for case in CASES:
        for folder in ('G03_events', 'G04', 'G05'):
            files.extend(root/MODE/case/folder/name for name in
                ('control_quad.npz', 'geometry.npz', 'generation.json', 'evidence.npz'))
        files.append(root/MODE/case/'G03_events/events.json')
    require(all(path.is_file() for path in files), 'Both complete SPAN/COUNTER sidewall G3/G4/G5 lineages required.')


def preserved_parent_binding(source, case, runner):
    verification = Path(source['parent_verification'])
    require(digest(verification) == source['parent_verification_sha256'] and
        digest(source['parent_recipe']) == source['parent_recipe_sha256'], 'Preserved parent PASS/recipe file hash differs.')
    receipt = read_json(verification)
    stage = parent_stage_receipt(receipt, case)
    parent_root = Path(receipt['root'])
    require(Path(source['path']).resolve() == (parent_root/'ROOT_ONLY'/case/'G03_events').resolve() and
        Path(source['parent_recipe']).resolve() == (parent_root/'RECIPE.json').resolve() and
        receipt['verifier_module_sha256'] == digest(HERE.parent/'connected_fold_growth_20261012/verify.py') and
        receipt['source_index_sha256'] == digest(parent_root/'source_index.json'), 'Frozen actual parent verification linkage differs.')
    recipe = read_json(source['parent_recipe'])
    require(recipe == receipt['recipe'], 'Preserved parent recipe differs from original actual PASS.')
    for relative, checksum in recipe['geometry_code_sha256'].items():
        require(digest(REPO/relative) == checksum, 'Frozen connected geometry code differs: '+relative)
    for input_case in CASES:
        for mode in H.MODES:
            for proof in receipt['cases'][input_case]['states'][mode]['stages']:
                generation = proof['semantics']['actual_generation']
                folder = parent_root/mode/input_case/('G03_events' if generation == 3 else f'G{generation:02d}')
                info = read_json(folder/'generation.json')
                require(digest(folder/'generation.json') == proof['generation_json_sha256'] and
                    info['geometry_code_sha256'] == recipe['geometry_code_sha256'] and
                    all(info['checks'][key] == value for key, value in proof['hashes'].items()),
                    'An original 18-stage metadata/hash link differs from preserved parent PASS.')
    folder = Path(source['path']); info = read_json(folder/'generation.json')
    require(info['candidate'] == 'ROOT_ONLY' and info['input_case'] == case and
        info['subdivision_generation'] == 3 and info['accepted_canonical_events_by_level'] == [1, 0, 0] and
        info['source'] == source['original_wall_source'] and
        info['source_control_sha256'] == source['original_wall_control_sha256'] and
        stage['generation_json_sha256'] == source['generation_sha256'], 'Inherited actual root identity differs.')
    for filename, source_key, metadata_key in (
            ('control_quad.npz', 'control_sha256', 'control_file_sha256'),
            ('geometry.npz', 'geometry_sha256', 'geometry_file_sha256'),
            ('evidence.npz', 'evidence_sha256', 'evidence_file_sha256'),
            ('events.json', 'events_sha256', 'events_file_sha256'),
            ('generation.json', 'generation_sha256', None)):
        require(digest(folder/filename) == source[source_key] and
            (metadata_key is None or info[metadata_key] == source[source_key]), 'Actual frozen parent file differs: '+filename)
    mesh, chart, evidence, events = runner.load_parent(source)
    require(mesh.surface == 'mean' and len(events) == 1 and events[0]['status'] == 'accepted' and
        events[0]['event_id'] == 1 and events[0]['level'] == 0, 'Exactly one inherited mean-native root event required.')
    xyz, triangles = runner.core.native(mesh)
    H.exact_evidence(folder/'geometry.npz', dict(xyz=xyz, faces=triangles))
    for key, array in (('control_xyz_sha256', mesh.xyz), ('control_faces_sha256', mesh.faces),
            ('chart_sha256', chart), ('native_xyz_sha256', xyz), ('native_faces_sha256', triangles)):
        require(runner.core.array_hash(array) == stage['hashes'][key], 'Actual parent arrays differ from preserved proof: '+key)
    pairs = {axis: evidence['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
    faces = {axis: evidence['mirror_'+axis.lower()+'_face_pairs'] for axis in ('X', 'Y')}
    symmetry = H.actual_native_symmetry(xyz, triangles, mesh.faces, pairs, faces)
    topology = H.actual_topology(xyz, triangles)
    del xyz, triangles; gc.collect()
    proof = dict(passed=True, original_18_stage_metadata_links=True, original_18_meshes_rerun=False,
        actual_parent_native_exact=True, actual_parent_topology=topology, actual_parent_symmetry=symmetry,
        verification_sha256=source['parent_verification_sha256'], actual_parent_generation_sha256=source['generation_sha256'])
    return mesh, chart, evidence, events, proof


def verify_stage(folder, mesh, chart, source, case, cc_passes, counts, pairs, runner, evidence):
    info = read_json(folder/'generation.json')
    expected = dict(input_case=case, candidate=MODE, source=source['path'], source_control_sha256=source['control_sha256'],
        source_generation=3, source_surface='mean', preserved_parent=source, geometry_code_sha256=runner.geometry_code_hashes(),
        event_recipe=runner.patch.RECIPE, constructive_event_count=counts['accepted_canonical_events'],
        inherited_canonical_root_events=1, new_canonical_sidewall_events=counts['new_canonical_events'],
        reflected_constructive_event_instances=counts['reflected_constructive_event_instances'],
        reflected_new_sidewall_event_instances=4*counts['new_canonical_events'],
        attempted_canonical_events=1+counts['attempted_new_canonical_events'], rejected_canonical_events=counts['rejected_canonical_events'],
        accepted_canonical_events_by_level=counts['accepted_by_level'], added_field_passes=0, added_mandelbulb_evaluations=0,
        event_count_scope='One inherited canonical root plus new root-sidewall events; events.json contains only new events. Four reflected instances per accepted event.')
    require(all(info[key] == value for key, value in expected.items()) and info['checks']['passed'] is True,
        'Actual sidewall generation/source/count/frozen-code metadata differs.')
    H.verify_surface_labels(info, 'mean')
    semantics = H.generation_semantics(info['subdivision_generation'], info['constructive_event_count'], cc_passes)
    require(mesh.generation == 3+cc_passes, 'Actual CC generation differs.')
    for name, key in (('control_quad.npz', 'control_file_sha256'), ('geometry.npz', 'geometry_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')):
        require(digest(folder/name) == info[key], 'Actual new file hash differs: '+name)
    H.exact_evidence(folder/'control_quad.npz', dict(xyz=mesh.xyz, faces=mesh.faces, chart=chart, classes=mesh.classes,
        rest=mesh.rest, anchors=mesh.anchors, generation=np.array(mesh.generation), surface=np.array('mean')))
    H.exact_evidence(folder/'evidence.npz', evidence)
    xyz, triangles = runner.core.native(mesh)
    H.exact_evidence(folder/'geometry.npz', dict(xyz=xyz, faces=triangles))
    hashes = {key: runner.core.array_hash(array) for key, array in (
        ('control_xyz_sha256', mesh.xyz), ('control_faces_sha256', mesh.faces), ('chart_sha256', chart),
        ('native_xyz_sha256', xyz), ('native_faces_sha256', triangles))}
    require(all(info['checks'][key] == value for key, value in hashes.items()), 'Actual replayed new array hashes differ.')
    topology, symmetry = H.actual_topology(xyz, triangles), H.actual_native_symmetry(xyz, triangles, mesh.faces, pairs)
    require(abs(topology['minimum_actual_triangle_area']-info['checks']['minimum_native_triangle_area']) <= 3e-12 and
        all(info[key] == count for key, count in [('control_vertices', len(mesh.xyz)), ('control_quads', len(mesh.faces)),
            ('native_vertices', len(xyz)), ('native_triangles', len(triangles))]), 'Actual native area or generation sizes differ.')
    if cc_passes:
        parent = folder.parent/('G03_events' if cc_passes == 1 else 'G04')
        require(info['neutral_CC_passes_added'] == cc_passes and Path(info['parent']).resolve() == parent.resolve() and
            info['parent_generation_sha256'] == digest(parent/'generation.json'), 'Actual new CC parent linkage differs.')
    else:
        require(info['events_file_sha256'] == digest(folder/'events.json'), 'New event record hash differs.')
    del xyz, triangles; gc.collect()
    return dict(passed=True, semantics=semantics, exact_control_native_and_evidence_replay=True, hashes=hashes,
        actual_native_topology=topology, actual_native_symmetry=symmetry, generation_json_sha256=digest(folder/'generation.json'))


def verify_case(root, source, case, runner):
    runner.core.memory_guard()
    mesh, chart, parent_evidence, parent_events, parent_proof = preserved_parent_binding(source, case, runner)
    mesh, chart, events, evidence = runner.patch.build(mesh, chart, parent_evidence, parent_events)
    counts = sidewall_ownership(events, evidence, parent_evidence)
    for key, value in parent_evidence.items():
        if key.startswith('event_001_') or key.startswith('root_pca_'):
            inherited_key = 'inherited_'+key
            require(inherited_key in evidence and H.array_bits_equal(evidence[inherited_key], value),
                'Inherited root event evidence differs: '+key)
    inherited_root = parent_events[0]
    require(str(evidence['inherited_root_event_json']) == json.dumps(inherited_root, sort_keys=True) and
        float(evidence['inherited_root_radius']) == inherited_root['geometry']['area_radius'],
        'Inherited actual root event/radius provenance differs.')
    for event in events:
        if event['status'] == 'accepted':
            heights = np.asarray(runner.patch.RECIPE['heights_root_radius'])*inherited_root['geometry']['area_radius']
            require(event['root_radius'] == inherited_root['geometry']['area_radius'] and
                np.allclose(event['geometry']['actual_heights'], heights, rtol=0., atol=3e-12),
                'Actual child sweep heights are not bound to inherited root radius.')
    pairs = {axis: evidence['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
    for axis in ('X', 'Y'):
        H.face_involution(mesh.faces, pairs[axis], evidence['mirror_'+axis.lower()+'_face_pairs'], axis+' actual event mirror faces')
    folder = root/MODE/case/'G03_events'
    require(read_json(folder/'events.json') == json.loads(json.dumps(events, allow_nan=False)), 'Saved new-only event records do not replay exactly.')
    stages = [verify_stage(folder, mesh, chart, source, case, 0, counts, pairs, runner, evidence)]
    del evidence, events, parent_evidence, parent_events; gc.collect()
    for passes in (1, 2):
        previous_faces = mesh.faces
        mesh, chart, refinement = runner.core.refine(mesh, chart)
        pairs = {axis: H.refine_mirror_pairs(previous_faces, refinement['input_edges'], pair) for axis, pair in pairs.items()}
        stages.append(verify_stage(root/MODE/case/f'G{3+passes:02d}', mesh, chart, source, case, passes, counts, pairs, runner, refinement))
    del mesh, chart, previous_faces, refinement, pairs; gc.collect()
    for filename, key in (('control_quad.npz', 'control_sha256'), ('geometry.npz', 'geometry_sha256'),
            ('evidence.npz', 'evidence_sha256'), ('events.json', 'events_sha256'), ('generation.json', 'generation_sha256')):
        require(digest(Path(source['path'])/filename) == source[key], 'Read-only parent changed during new replay.')
    return dict(passed=True, input_case=case, parent=parent_proof, ownership=counts, stages=stages,
        visual_success='NOT_ASSESSED; source-sidewall normals/angles and accepted event counts are not aesthetic certification.')


def run(root):
    root = Path(root).resolve(); inventory(root)
    runner = load_module('sidewall_verified_actual_runner', HERE/'study.py')
    recipe, sources, summary = [read_json(root/name) for name in ('RECIPE.json', 'source_index.json', 'SUMMARY.json')]
    require(set(sources) == set(CASES) and sources == runner.source_index() and recipe['cases'] == list(CASES) and
        recipe['candidate'] == MODE and recipe['source_generation'] == 3 and recipe['final_generation'] == 5 and
        recipe['neutral_CC_passes'] == 2 and recipe['patch_growth'] == runner.patch.RECIPE and
        recipe['geometry_code_sha256'] == runner.geometry_code_hashes() and summary['all_two_complete'] is True and
        summary['quick_integrity_passed'] is True and len(summary['states']) == 2 and
        {state['input_case'] for state in summary['states']} == set(CASES), 'Both inputs require one complete frozen sidewall recipe/source lineage.')
    for state in summary['states']:
        require(state == read_json(root/MODE/state['input_case']/'G05/generation.json'), 'Summary differs from actual saved G5 metadata.')
    cases = {case: verify_case(root, sources[case], case, runner) for case in CASES}
    return dict(status='PASS', root=str(root), expected_cases=list(CASES), expected_modes=[MODE], recipe=recipe,
        source_index_sha256=digest(root/'source_index.json'), cases=cases, verifier_module_sha256=digest(Path(__file__)),
        scope='Preserved original 18-stage PASS metadata links, actual mean-native G3 parents, ordered new root-sidewall edits and ownership, two actual neutral CC passes, exact six-stage control/native/evidence replay and actual native topology/XYZ/oriented-triangle symmetry.',
        excluded=['Original 18 parent meshes rerun', 'Aesthetic/reference fidelity certification', 'Automatic feature detection',
            'Injective material chart', 'Self-intersections', 'Fabrication', 'Structural performance'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-receipt', type=Path,
        help='Fresh receipt path; relative names are placed under --root. Existing receipts are preserved.')
    args = parser.parse_args()
    output = H.receipt_destination(args.root, args.output_receipt)
    if output.exists():
        raise FileExistsError('Existing sidewall verification receipt preserved: '+str(output))
    try:
        receipt = run(args.root)
    except Exception as error:
        receipt = dict(status='FAIL', root=str(args.root.resolve()), error_type=type(error).__name__, error=str(error))
        with output.open('x', encoding='utf8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
        raise
    with output.open('x', encoding='utf8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    print('SIDEWALL_FAN_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
