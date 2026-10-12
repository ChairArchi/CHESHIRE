"""Actual source/event/CC replay verification for connected fold growth.

Topology events keep G3; two subsequent neutral CC passes are G4 and G5.
Explicit mirror-ID involutions, rather than nearest matches of overlapping
material charts, bind actual XYZ and oriented native triangles to symmetry.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent
CASES = ('SPAN', 'COUNTER')
MODES = ('SMOOTH_CONTROL', 'ROOT_ONLY', 'BRANCHED')
TOLERANCE = 1e-9
_TOPOLOGY = None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def involution(pair, count, label):
    pair = np.asarray(pair)
    require(pair.shape == (count,) and pair.dtype.kind in 'iu' and
        (count == 0 or (pair.min() >= 0 and pair.max() < count)), label+': invalid mirror IDs.')
    require(np.array_equal(pair[pair], np.arange(count)), label+': mirror mapping is not an involution.')
    return pair


def canonical_cycles(faces):
    """Cyclic starting corner is irrelevant; reversed winding remains distinct."""
    q = np.asarray(faces)
    require(q.ndim == 2 and q.dtype.kind in 'iu' and q.shape[1] in (3, 4) and
        (q.size == 0 or q.min() >= 0), 'Unpadded triangle/quad cycles required.')
    first = np.argmin(q, axis=1)
    result = np.empty_like(q)
    for corner in range(q.shape[1]):
        selected = first == corner
        result[selected] = np.roll(q[selected], -corner, axis=1)
    return result


def row_match(original, requested, label):
    """Exact bijective row correspondence; duplicate cycles cannot hide holes."""
    original, requested = np.asarray(original), np.asarray(requested)
    require(original.ndim == 2 and original.shape == requested.shape and original.dtype.kind in 'iu' and
        requested.dtype.kind in 'iu', label+': invalid row arrays.')
    original, requested = original.astype(np.int64, copy=False), requested.astype(np.int64, copy=False)
    order = np.lexsort(tuple(original[:, k] for k in range(original.shape[1]-1, -1, -1)))
    ordered = np.ascontiguousarray(original[order])
    dtype = np.dtype([(str(k), np.int64) for k in range(original.shape[1])])
    keys = ordered.view(dtype).ravel()
    targets = np.ascontiguousarray(requested).view(dtype).ravel()
    require(len(keys) < 2 or not np.any(keys[1:] == keys[:-1]), label+': duplicate cycles.')
    positions = np.searchsorted(keys, targets)
    require(np.all(positions < len(keys)) and np.array_equal(keys[positions], targets),
        label+': reflected topology has no exact counterpart.')
    result = order[positions]
    require(len(np.unique(result)) == len(result), label+': correspondence is not bijective.')
    return result


def face_involution(faces, vertex_pair, saved_face_pair=None, label='Mirror faces'):
    q = np.asarray(faces)
    require(q.ndim == 2 and q.shape[1] == 4 and q.dtype.kind in 'iu' and q.min() >= 0,
        'Actual all-quad control faces required.')
    pair = involution(vertex_pair, len(vertex_pair), label+' vertices')
    require(q.max() < len(pair), 'Control face indices exceed mirror mapping.')
    reflected = canonical_cycles(pair[q[:, ::-1]])
    result = row_match(canonical_cycles(q), reflected, label)
    involution(result, len(q), label)
    if saved_face_pair is not None:
        require(np.array_equal(result, saved_face_pair), label+': saved face mapping differs from actual topology.')
    return result


def refine_mirror_pairs(faces, input_edges, vertex_pair):
    """Transport explicit correspondence through actual CC V/E/F ordering."""
    pair = involution(vertex_pair, len(vertex_pair), 'Incoming CC mirror')
    edges = np.asarray(input_edges)
    require(edges.ndim == 2 and edges.shape[1] == 2 and edges.dtype.kind in 'iu' and
        len(edges) > 0 and edges.min() >= 0 and edges.max() < len(pair), 'Actual CC input edges required.')
    edge_pair = row_match(np.sort(edges, axis=1), np.sort(pair[edges], axis=1), 'Actual CC mirror edges')
    face_pair = face_involution(faces, pair)
    result = np.r_[pair, len(pair)+edge_pair, len(pair)+len(edges)+face_pair]
    return involution(result, len(result), 'Refined CC mirror')


def actual_native_symmetry(xyz, triangles, control_faces, control_pairs, saved_face_pairs=None, tolerance=TOLERANCE):
    """Check real coordinates and oriented triangles with topological mirror IDs."""
    xyz, triangles, faces = map(np.asarray, (xyz, triangles, control_faces))
    control_count = len(control_pairs['X'])
    require(xyz.shape == (control_count+len(faces), 3) and np.isfinite(xyz).all() and
        triangles.ndim == 2 and triangles.shape[1] == 3 and triangles.dtype.kind in 'iu' and
        triangles.min() >= 0 and triangles.max() < len(xyz), 'Invalid actual mean-fan native geometry.')
    original = canonical_cycles(triangles)
    records = {}
    for axis, coordinate in [('X', 0), ('Y', 1)]:
        control_pair = involution(control_pairs[axis], control_count, axis+' control mirror')
        expected_faces = None if saved_face_pairs is None else saved_face_pairs[axis]
        face_pair = face_involution(faces, control_pair, expected_faces, axis+' actual mirror faces')
        pair = np.r_[control_pair, control_count+face_pair]
        involution(pair, len(xyz), axis+' native mirror')
        error = 0.
        for start in range(0, len(xyz), 120000):
            stop = min(start+120000, len(xyz))
            reflected_xyz = xyz[pair[start:stop]].copy()
            reflected_xyz[:, coordinate] *= -1.
            error = max(error, float(np.max(np.linalg.norm(xyz[start:stop]-reflected_xyz, axis=1), initial=0.)))
        require(np.isfinite(error) and error <= tolerance, axis+' actual native XYZ reflection failed.')
        reflected = canonical_cycles(pair[triangles[:, ::-1]])
        row_match(original, reflected, axis+' actual oriented native triangles')
        records[axis] = dict(passed=True, mirror_involution=True, actual_xyz_max_error=error,
            oriented_native_triangle_sets_identical=True, tolerance=tolerance,
            correspondence='Explicit control mirror IDs plus actual reflected quad-to-fan-centre correspondence; no nearest-point matching.')
    return records


def exact_geometry(actual, expected, label):
    actual, expected = np.asarray(actual), np.asarray(expected)
    require(actual.shape == expected.shape and actual.dtype == expected.dtype and
        np.isfinite(actual).all() and np.isfinite(expected).all() and array_bits_equal(actual, expected),
        label+': actual saved array did not replay exactly.')


def array_bits_equal(actual, expected):
    """Include dtype and signed-zero bytes, without allocating Python byte copies."""
    actual, expected = np.asarray(actual), np.asarray(expected)
    return actual.shape == expected.shape and actual.dtype == expected.dtype and (
        hashlib.sha256(np.ascontiguousarray(actual)).digest() ==
        hashlib.sha256(np.ascontiguousarray(expected)).digest())


def actual_topology(xyz, triangles, minimum_area=1e-14):
    """Reuse actual native incidence/connectivity, then check Euler and area."""
    global _TOPOLOGY
    if _TOPOLOGY is None:
        _TOPOLOGY = load_module('connected_growth_existing_native_topology',
            HERE.parent/'fold_visible_gate_20261012/compactpackage_finish_g6.py')
    receipt = _TOPOLOGY.native_topology(xyz, triangles)
    require(receipt['passed'] is True and receipt['closed_oriented_edge_incidence'] is True and
        receipt['components'] == 1 and receipt['euler_characteristic'] == 2,
        'Actual native surface is not one closed oriented Euler-2 body.')
    area = float('inf')
    for start in range(0, len(triangles), 120000):
        q = triangles[start:start+120000]
        a, b, c = xyz[q[:, 0]], xyz[q[:, 1]], xyz[q[:, 2]]
        area = min(area, float(np.min(np.linalg.norm(np.cross(b-a, c-a), axis=1)/2)))
    require(np.isfinite(area) and area > minimum_area, 'Actual native surface has degenerate/too-small triangles.')
    receipt.update(minimum_actual_triangle_area=area, configured_minimum_triangle_area=minimum_area,
        self_intersection='NOT_CHECKED_EXPLORATORY')
    return receipt


def event_parent_ownership(selected_faces, current_face_event_ids, current_face_roles, parent_event_id):
    """A child must replace actual cap faces belonging to its stated parent."""
    selected, owners, roles = map(np.asarray, (selected_faces, current_face_event_ids, current_face_roles))
    require(selected.ndim == 1 and selected.dtype.kind in 'iu' and len(selected) >= 2 and
        len(np.unique(selected)) == len(selected) and owners.ndim == 1 and roles.shape == owners.shape and
        selected.min() >= 0 and selected.max() < len(owners), 'Child requires a nonempty actual multi-face selection.')
    require(np.all(owners[selected] == parent_event_id) and np.all(roles[selected] == 2),
        'Child selected faces are not caps owned by its declared parent event.')
    return dict(passed=True, actual_selected_parent_cap_faces=int(len(selected)), parent_event_id=int(parent_event_id))


def generation_semantics(actual_generation, event_count, cc_passes):
    require(type(actual_generation) is int and type(event_count) is int and type(cc_passes) is int and
        event_count >= 0 and cc_passes in (0, 1, 2) and actual_generation == 3+cc_passes,
        'Topology event count must remain separate from G3 plus actual CC subdivision passes.')
    return dict(actual_generation=actual_generation, topology_event_count=event_count, added_CC_passes=cc_passes)


def source_chart_pairs(chart):
    """Only the original, unique source chart is used to discover mirror IDs."""
    from scipy.spatial import cKDTree
    chart = np.asarray(chart)
    require(chart.ndim == 2 and chart.shape[1] == 3 and np.isfinite(chart).all(), 'Finite source material chart required.')
    tree = cKDTree(chart)
    result = {}
    for axis, coordinate in [('X', 1), ('Y', 2)]:
        reflected = chart.copy(); reflected[:, coordinate] *= -1.
        distance, pair = tree.query(reflected)
        require(np.max(distance, initial=0.) <= 1e-11, 'Source material reflection correspondence is missing.')
        result[axis] = involution(pair, len(chart), axis+' original source chart mirror')
    return result


def read_arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        return {key: saved[key].copy() for key in saved.files}


def exact_evidence(path, expected):
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == set(expected), 'Actual evidence field inventory differs.')
        for key, value in expected.items():
            actual, value = saved[key], np.asarray(value)
            require(actual.dtype.kind != 'O' and array_bits_equal(actual, value),
                'Actual evidence did not replay exactly: '+key)
            if value.dtype.kind in 'bifuc':
                require(np.isfinite(actual).all(), 'Nonfinite actual evidence: '+key)


def event_ownership(events, evidence, source_face_count):
    """Independently trace selected caps and immediate face ownership edits."""
    owners = np.zeros(source_face_count, np.int64)
    roles = np.zeros(source_face_count, np.int8)
    parent_owners = np.zeros(source_face_count, np.int64)
    origins = np.arange(source_face_count)
    accepted, rejected, level_counts, proofs = {}, 0, [0, 0, 0], []
    seen = set()
    for event in events:
        event_id, level, parent_id = event['event_id'], event['level'], event['parent_event_id']
        require(type(event_id) is int and event_id > 0 and event_id not in seen and
            type(level) is int and level in (0, 1, 2) and event['status'] in ('accepted', 'rejected'),
            'Invalid unique topology event identity/status/level.')
        seen.add(event_id)
        if level:
            require(parent_id in accepted and accepted[parent_id] == level-1,
                'Child event has no accepted immediate parent at the preceding level.')
        else:
            require(parent_id == 0, 'Root event cannot have a constructed parent.')
        if event['status'] == 'rejected':
            rejected += 1
            continue
        accepted[event_id] = level; level_counts[level] += 1
        require(event['source_generation'] == 3, 'Constructive event incorrectly increments subdivision generation.')
        key = f'event_{event_id:03d}_'
        selected = np.asarray(evidence[key+'selected_input_faces'])
        parent = np.asarray(evidence[key+'parent_face'])
        caps = np.asarray(evidence[key+'generated_cap_faces'])
        require(selected.ndim == 1 and selected.dtype.kind in 'iu' and len(selected) >= 2 and
            len(np.unique(selected)) == len(selected) and selected.min() >= 0 and selected.max() < len(owners),
            'Event requires actual distinct multi-face input support.')
        require(np.array_equal(selected, event['selected_input_faces']) and np.array_equal(caps, event['generated_cap_faces']) and
            np.array_equal(evidence[key+'selected_parent_event_ids'], owners[selected]) and
            np.array_equal(evidence[key+'selected_parent_roles'], roles[selected]),
            'Event selection/declared parent evidence differs from immediate actual face ownership.')
        if level:
            proof = event_parent_ownership(selected, owners, roles, parent_id)
        else:
            require(np.all(owners[selected] == 0) and np.all(roles[selected] == 0),
                'Root event must replace original source faces.')
            proof = dict(passed=True, actual_selected_source_faces=int(len(selected)), parent_event_id=0)
        retained = np.setdiff1d(np.arange(len(owners)), selected)
        require(parent.ndim == 1 and parent.dtype.kind in 'iu' and len(parent) > len(owners) and
            parent.min() >= 0 and parent.max() < len(owners) and np.array_equal(parent[:len(retained)], retained),
            'Event retained-face ordering/parent map differs from disk replacement.')
        new_faces = np.arange(len(parent)) >= len(retained)
        require(np.all(np.isin(parent[new_faces], selected)) and
            np.array_equal(caps, np.arange(len(parent)-len(selected), len(parent))) and
            np.array_equal(parent[caps], selected), 'Actual generated wall/cap parent support differs.')
        next_parent = parent_owners[parent].copy()
        next_parent[new_faces] = owners[parent[new_faces]]
        owners, roles, origins = owners[parent].copy(), roles[parent].copy(), origins[parent]
        owners[new_faces] = event_id; roles[new_faces] = 1; roles[caps] = 2
        parent_owners = next_parent
        proofs.append(dict(event_id=event_id, level=level, ownership=proof,
            generated_cap_faces=int(len(caps)), generated_wall_faces=int(new_faces.sum()-len(caps))))
    require(level_counts[0] == 1, 'Exactly one accepted canonical root is required.')
    mirrored = np.asarray(evidence['mirror_source_face_ids'])
    require(mirrored.ndim == 1 and mirrored.dtype.kind in 'iu' and len(mirrored) > 0 and
        mirrored.min() >= 0 and mirrored.max() < len(owners), 'Invalid canonical-quarter face ancestry IDs.')
    for key, expected in [('face_event_ids', owners[mirrored]), ('face_roles', roles[mirrored]),
            ('face_parent_event_ids', parent_owners[mirrored]), ('face_source_ids', origins[mirrored])]:
        require(np.array_equal(evidence[key], expected), 'Final mirrored face ownership differs: '+key)
    require(np.array_equal(evidence['accepted_event_counts_by_level'], level_counts) and
        int(evidence['rejected_event_count']) == rejected, 'Accepted/rejected level-count evidence differs.')
    return dict(passed=True, accepted_canonical_events=sum(level_counts), rejected_canonical_events=rejected,
        accepted_by_level=level_counts, reflected_constructive_event_instances=4*sum(level_counts),
        event_proofs=proofs, scope='Actual selected input face IDs and immediate cap/sidewall ownership traced through ordered disk edits and explicit canonical mirror ancestry.')


def inventory(root):
    files = [root/'RECIPE.json', root/'source_index.json', root/'SUMMARY.json']
    for case in CASES:
        for mode in MODES:
            for folder in ('G03_events', 'G04', 'G05'):
                files.extend(root/mode/case/folder/name for name in
                    ('control_quad.npz', 'geometry.npz', 'generation.json', 'evidence.npz'))
            files.append(root/mode/case/'G03_events/events.json')
    missing = [str(path) for path in files if not path.is_file()]
    require(not missing, 'Both SPAN/COUNTER and all three complete G3-event/G4/G5 lineages required: '+', '.join(missing))


def verify_surface_labels(info, source_surface):
    """Generation JSON describes the fan; control NPZ stores the 'mean' enum."""
    require(info['source_surface'] == source_surface and
        info['native_surface'] == 'Explicit arithmetic quad-centre fans',
        'Recorded original source/output native surface labels differ from the saved runner contract.')


def verify_saved_stage(folder, mesh, chart, source, source_surface, case, mode, cc_passes, counts, pairs, runner, expected_evidence):
    info = read_json(folder/'generation.json')
    semantics = generation_semantics(info['subdivision_generation'], info['constructive_event_count'], cc_passes)
    verify_surface_labels(info, source_surface)
    require(mesh.generation == 3+cc_passes and info['input_case'] == case and info['candidate'] == mode and
        info['source_generation'] == 3 and Path(info['source']).resolve() == Path(source['path']).resolve() and
        info['source_control_sha256'] == source['control_sha256'] and info['event_recipe'] == runner.patch_growth.RECIPE and
        info['geometry_code_sha256'] == runner.geometry_code_hashes() and
        info['added_field_passes'] == info['added_mandelbulb_evaluations'] == 0 and
        info['constructive_event_count'] == counts['accepted_canonical_events'] and
        info['reflected_constructive_event_instances'] == counts['reflected_constructive_event_instances'] and
        info['rejected_canonical_events'] == counts['rejected_canonical_events'] and
        info['accepted_canonical_events_by_level'] == counts['accepted_by_level'] and
        info['attempted_canonical_events'] == counts['accepted_canonical_events']+counts['rejected_canonical_events'] and
        info['checks']['passed'] is True, 'Saved generation/source/event-count/recipe identity differs.')
    require(info['event_count_scope'] == 'Canonical-quarter accepted events; reflected event instances counted separately',
        'Canonical topology events and reflected instances must be distinguished.')
    require(digest(folder/'control_quad.npz') == info['control_file_sha256'] and
        digest(folder/'geometry.npz') == info['geometry_file_sha256'] and
        digest(folder/'evidence.npz') == info['evidence_file_sha256'], 'Saved control/native/evidence file hashes differ.')
    expected = dict(xyz=mesh.xyz, faces=mesh.faces, chart=chart, classes=mesh.classes, rest=mesh.rest,
        anchors=mesh.anchors, generation=np.array(mesh.generation), surface=np.array('mean'))
    exact_evidence(folder/'control_quad.npz', expected)
    exact_evidence(folder/'evidence.npz', expected_evidence)
    xyz, triangles = runner.native(mesh)
    exact_evidence(folder/'geometry.npz', dict(xyz=xyz, faces=triangles))
    expected_hashes = dict(control_xyz_sha256=runner.array_hash(mesh.xyz), control_faces_sha256=runner.array_hash(mesh.faces),
        chart_sha256=runner.array_hash(chart), native_xyz_sha256=runner.array_hash(xyz), native_faces_sha256=runner.array_hash(triangles))
    for key, value in expected_hashes.items():
        require(info['checks'][key] == value, 'Actual replayed array hash differs: '+key)
    topology = actual_topology(xyz, triangles)
    symmetry = actual_native_symmetry(xyz, triangles, mesh.faces, pairs)
    require(abs(topology['minimum_actual_triangle_area']-info['checks']['minimum_native_triangle_area']) <= 3e-12,
        'Actual native triangle-area receipt differs.')
    for key, expected_count in [('control_vertices', len(mesh.xyz)), ('control_quads', len(mesh.faces)),
            ('native_vertices', len(xyz)), ('native_triangles', len(triangles))]:
        require(info[key] == expected_count, 'Actual generation size differs: '+key)
    if cc_passes:
        parent = folder.parent/('G03_events' if cc_passes == 1 else 'G04')
        require(info['neutral_CC_passes_added'] == cc_passes and Path(info['parent']).resolve() == parent.resolve() and
            info['parent_generation_sha256'] == digest(parent/'generation.json'), 'Saved actual neutral-CC parent link differs.')
    else:
        require(info['events_file_sha256'] == digest(folder/'events.json'), 'Actual event JSON hash differs.')
    del xyz, triangles; gc.collect()
    return dict(passed=True, semantics=semantics, exact_control_native_and_evidence_replay=True,
        hashes=expected_hashes, actual_native_topology=topology, actual_native_symmetry=symmetry,
        generation_json_sha256=digest(folder/'generation.json'),
        native_surface_scope='Explicit arithmetic quad-centre fans. Original source VF interpretation is recorded separately; equal source control XYZ does not imply equal original VF native triangles.')


def verify_case(root, source, case, runner):
    runner.memory_guard()
    source_path = Path(source['path'])
    require(digest(source_path/'control_quad.npz') == source['control_sha256'] and
        digest(source['original_receipt']) == source['original_receipt_sha256'], 'Actual preserved WALL/source receipt hashes differ.')
    original = read_json(source['original_receipt'])
    require(original['input_case'] == case and original['source_control_sha256'] == source['control_sha256'] and
        Path(original['source']).resolve() == source_path.resolve(), 'Original BASELINE receipt does not identify this actual WALL G3 source.')
    states = {}
    source_surface = None
    for mode in MODES:
        mesh, chart = runner.load_source(source_path)
        source_surface = mesh.surface
        if mode == 'SMOOTH_CONTROL':
            pairs = source_chart_pairs(chart)
            events, evidence = [], {}
            counts = dict(passed=True, accepted_canonical_events=0, rejected_canonical_events=0,
                accepted_by_level=[0, 0, 0], reflected_constructive_event_instances=0)
        else:
            source_face_count = len(mesh.faces)
            mesh, chart, events, evidence = runner.patch_growth.build(mesh, chart, mode)
            counts = event_ownership(events, evidence, source_face_count)
            pairs = {axis: evidence['mirror_'+axis.lower()+'_vertex_pairs'] for axis in ('X', 'Y')}
            for axis in ('X', 'Y'):
                face_involution(mesh.faces, pairs[axis], evidence['mirror_'+axis.lower()+'_face_pairs'], axis+' saved event mirror faces')
        mesh.surface = 'mean'
        event_folder = root/mode/case/'G03_events'
        require(read_json(event_folder/'events.json') == json.loads(json.dumps(events, allow_nan=False)),
            'Saved accepted/rejected event records do not replay exactly from actual source.')
        stages = [verify_saved_stage(event_folder, mesh, chart, source, source_surface, case, mode, 0, counts, pairs, runner, evidence)]
        for cc_passes in (1, 2):
            previous_faces = mesh.faces
            out, outchart, refinement = runner.refine(mesh, chart)
            pairs = {axis: refine_mirror_pairs(previous_faces, refinement['input_edges'], pair) for axis, pair in pairs.items()}
            mesh, chart = out, outchart
            folder = root/mode/case/f'G{3+cc_passes:02d}'
            stages.append(verify_saved_stage(folder, mesh, chart, source, source_surface, case, mode, cc_passes, counts, pairs, runner, refinement))
        states[mode] = dict(passed=True, ownership=counts, stages=stages,
            source_surface=source_surface, output_surface='mean', original_source_control_hash_linked=True,
            source_physical_surface_preservation_claimed=False,
            visual_success='NOT_ASSESSED: accepted topology events, one body and valid symmetry do not establish visible branching hierarchy.')
        del mesh, chart, out, outchart, previous_faces, evidence, events, pairs, refinement; gc.collect()
    require(digest(source_path/'control_quad.npz') == source['control_sha256'], 'Read-only source changed during verification.')
    return dict(passed=True, input_case=case, source_control_sha256=source['control_sha256'], source_surface=source_surface, states=states)


def run(root):
    root = Path(root).resolve()
    inventory(root)
    runner = load_module('verified_connected_fold_growth_runner', HERE/'study.py')
    recipe, sources, summary = read_json(root/'RECIPE.json'), read_json(root/'source_index.json'), read_json(root/'SUMMARY.json')
    require(set(sources) == set(CASES) and recipe['cases'] == list(CASES) and recipe['modes'] == list(MODES) and
        recipe['source_generation'] == 3 and recipe['final_generation'] == 5 and recipe['neutral_CC_passes'] == 2 and
        recipe['patch_growth'] == runner.patch_growth.RECIPE and recipe['geometry_code_sha256'] == runner.geometry_code_hashes() and
        summary['all_six_complete'] is True and
        summary['quick_integrity_passed'] is True and len(summary['states']) == 6 and
        {(state['candidate'], state['input_case']) for state in summary['states']} == {(mode, case) for mode in MODES for case in CASES},
        'Both inputs and all three alternatives require one complete common frozen recipe.')
    for state in summary['states']:
        require(state == read_json(root/state['candidate']/state['input_case']/'G05/generation.json'),
            'Summary state differs from its saved actual G5 metadata.')
    cases = {case: verify_case(root, sources[case], case, runner) for case in CASES}
    return dict(status='PASS', root=str(root), expected_cases=list(CASES), expected_modes=list(MODES),
        recipe=recipe, source_index_sha256=digest(root/'source_index.json'), cases=cases,
        verifier_module_sha256=digest(Path(__file__)),
        scope='Actual preserved WALL G3 source hashes, ordered connected topology-event replay and parent-cap ownership, two actual neutral CC passes and chart transport, exact saved native geometry, actual edge/connectivity/Euler/area and propagated-ID XYZ/oriented-triangle symmetry.',
        generation_scope='G3 events preserve subdivision generation; G4 and G5 are two real CC passes. Canonical events and four reflected instances are counted separately.',
        excluded=['Aesthetic/reference fidelity certification', 'Original VF native surface preservation',
            'Injective material chart', 'Self-intersections', 'Fabrication', 'Structural performance'])


def receipt_destination(root, requested=None):
    """An explicit relative recheck name belongs to the same output root."""
    if requested is None:
        return Path(root)/'VERIFICATION.json'
    requested = Path(requested)
    return requested if requested.is_absolute() else Path(root)/requested


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-receipt', type=Path,
        help='Fresh receipt path; relative names are placed under --root. Existing receipts are never overwritten.')
    args = parser.parse_args()
    output = receipt_destination(args.root, args.output_receipt)
    if output.exists():
        raise FileExistsError('Existing connected-growth verification receipt preserved: '+str(output))
    try:
        receipt = run(args.root)
    except Exception as error:
        receipt = dict(status='FAIL', root=str(args.root.resolve()), error_type=type(error).__name__, error=str(error))
        with output.open('x', encoding='utf8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        raise
    with output.open('x', encoding='utf8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print('CONNECTED_FOLD_VERIFICATION PASS', output, flush=True)


if __name__ == '__main__':
    main()
