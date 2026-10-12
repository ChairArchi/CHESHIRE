"""Small connected-surface verification counterexamples; no real pilot load."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest

from cheshire.reference_subdivision import cube, subdivide


SPEC = importlib.util.spec_from_file_location('tested_connected_fold_verify',
    Path(__file__).resolve().parents[1]/'experiments/connected_fold_growth_20261012/verify.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def mean_native(mesh):
    q = mesh.faces
    xyz = np.vstack([mesh.xyz, mesh.xyz[q].mean(axis=1)])
    centres = np.arange(len(q))[:, None]+len(mesh.xyz)
    triangles = np.stack([q, np.roll(q, -1, axis=1), np.broadcast_to(centres, q.shape)], axis=-1).reshape(-1, 3)
    return xyz, triangles


def cube_pairs(mesh):
    pairs = {}
    for axis, coordinate in [('X', 0), ('Y', 1)]:
        mirrored = mesh.xyz.copy(); mirrored[:, coordinate] *= -1.
        pairs[axis] = np.array([np.flatnonzero(np.all(mesh.xyz == p, axis=1))[0] for p in mirrored])
    return pairs


def test_explicit_id_symmetry_accepts_repeated_material_coordinates_without_nearest_matching():
    mesh = cube(side=2.)
    xyz, triangles = mean_native(mesh)
    # Several later rings may share chart values; symmetry uses no chart/KDTree.
    pairs = cube_pairs(mesh)
    receipt = verify.actual_native_symmetry(xyz, triangles, mesh.faces, pairs)
    assert all(value['passed'] for value in receipt.values())
    changed = xyz.copy(); changed[0, 2] += .001
    with pytest.raises(ValueError, match='actual native XYZ'):
        verify.actual_native_symmetry(changed, triangles, mesh.faces, pairs)


def test_actual_oriented_triangle_corruption_is_not_hidden_by_symmetric_positions():
    mesh = cube(side=2.); xyz, triangles = mean_native(mesh)
    triangles = triangles.copy(); triangles[0] = triangles[0, ::-1]
    with pytest.raises(ValueError, match='oriented native triangles'):
        verify.actual_native_symmetry(xyz, triangles, mesh.faces, cube_pairs(mesh))


def test_cc_transports_actual_edge_face_ids_and_rejects_a_fabricated_face_map():
    mesh = cube(side=2.); pairs = cube_pairs(mesh)
    out, _, state = subdivide(mesh, {})
    propagated = {axis: verify.refine_mirror_pairs(mesh.faces, state['input_edges'], pair)
        for axis, pair in pairs.items()}
    xyz, triangles = mean_native(out)
    assert all(r['passed'] for r in verify.actual_native_symmetry(xyz, triangles, out.faces, propagated).values())
    wrong = verify.face_involution(mesh.faces, pairs['X']).copy(); wrong[[0, 1]] = wrong[[1, 0]]
    with pytest.raises(ValueError, match='saved face mapping'):
        verify.face_involution(mesh.faces, pairs['X'], wrong)
    wrong_vertex = pairs['X'].copy(); wrong_vertex[0] = 0
    with pytest.raises(ValueError, match='not an involution'):
        verify.refine_mirror_pairs(mesh.faces, state['input_edges'], wrong_vertex)


def test_closed_flags_cannot_hide_missing_or_reversed_actual_faces():
    mesh = cube(side=2.); xyz, triangles = mean_native(mesh)
    assert verify.actual_topology(xyz, triangles)['passed']
    with pytest.raises(ValueError, match='closed oriented'):
        verify.actual_topology(xyz, triangles[:-1])
    reversed_one = triangles.copy(); reversed_one[0] = reversed_one[0, ::-1]
    with pytest.raises(ValueError, match='closed oriented'):
        verify.actual_topology(xyz, reversed_one)


def test_child_cannot_steal_a_sibling_cap_or_use_a_single_face_as_multi_face_growth():
    owners, roles = np.array([3, 3, 4, 3]), np.array([2, 2, 2, 1])
    assert verify.event_parent_ownership(np.array([0, 1]), owners, roles, 3)['passed']
    for selected in [np.array([0, 2]), np.array([0, 3])]:
        with pytest.raises(ValueError, match='caps owned'):
            verify.event_parent_ownership(selected, owners, roles, 3)
    with pytest.raises(ValueError, match='multi-face'):
        verify.event_parent_ownership(np.array([0]), owners, roles, 3)


def test_topology_events_do_not_increment_subdivision_generation():
    assert verify.generation_semantics(3, 10, 0)['actual_generation'] == 3
    assert verify.generation_semantics(5, 10, 2)['added_CC_passes'] == 2
    with pytest.raises(ValueError, match='event count'):
        verify.generation_semantics(15, 10, 2)


def test_exact_replay_rejects_one_ulp_and_nonfinite_saved_geometry():
    expected = np.array([[1., 2., 3.]])
    verify.exact_geometry(expected.copy(), expected, 'Native geometry')
    changed = expected.copy(); changed[0, 0] = np.nextafter(changed[0, 0], np.inf)
    with pytest.raises(ValueError, match='replay exactly'):
        verify.exact_geometry(changed, expected, 'Native geometry')
    with pytest.raises(ValueError, match='replay exactly'):
        verify.exact_geometry(expected*np.nan, expected, 'Native geometry')
    with pytest.raises(ValueError, match='replay exactly'):
        verify.exact_geometry(np.array([-0.]), np.array([0.]), 'Native signed-zero bytes')


def ownership_fixture():
    # Only the face ancestry state machine is exercised here; actual geometry,
    # closedness and reflection are separately checked using the cube above.
    root_parent = np.array([0, 3, 4, 5, 1, 2, 1, 2])
    child_parent = np.array([0, 1, 2, 3, 4, 5, 6, 7, 6, 7, 6, 7])
    events = [
        dict(event_id=1, status='accepted', level=0, parent_event_id=0,
            source_generation=3, selected_input_faces=[1, 2], generated_cap_faces=[6, 7]),
        dict(event_id=2, status='rejected', level=1, parent_event_id=1, reason='Insufficient actual support'),
        dict(event_id=3, status='accepted', level=1, parent_event_id=1,
            source_generation=3, selected_input_faces=[6, 7], generated_cap_faces=[10, 11])]
    evidence = dict(mirror_source_face_ids=np.arange(12),
        face_event_ids=np.array([0, 0, 0, 0, 1, 1, 3, 3, 3, 3, 3, 3]),
        face_roles=np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2]),
        face_parent_event_ids=np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]),
        face_source_ids=root_parent[child_parent], accepted_event_counts_by_level=np.array([1, 1, 0]),
        rejected_event_count=np.array(1))
    for event, parent in [(events[0], root_parent), (events[2], child_parent)]:
        key = f"event_{event['event_id']:03d}_"
        evidence.update({key+'selected_input_faces': np.array(event['selected_input_faces']),
            key+'generated_cap_faces': np.array(event['generated_cap_faces']), key+'parent_face': parent,
            key+'selected_parent_event_ids': np.full(2, event['parent_event_id']),
            key+'selected_parent_roles': np.full(2, 0 if event['level'] == 0 else 2)})
    return events, evidence


def test_event_trace_keeps_rejected_attempt_out_of_counts_and_detects_stolen_ancestry():
    events, evidence = ownership_fixture()
    result = verify.event_ownership(events, evidence, 6)
    assert result['accepted_canonical_events'] == 2
    assert result['rejected_canonical_events'] == 1
    assert result['reflected_constructive_event_instances'] == 8
    assert result['accepted_by_level'] == [1, 1, 0]
    changed = {key: value.copy() for key, value in evidence.items()}
    changed['face_parent_event_ids'][-1] = 0
    with pytest.raises(ValueError, match='Final mirrored face ownership'):
        verify.event_ownership(events, changed, 6)
    changed = {key: value.copy() for key, value in evidence.items()}
    changed['accepted_event_counts_by_level'][1] += 1
    with pytest.raises(ValueError, match='level-count'):
        verify.event_ownership(events, changed, 6)


def test_incomplete_archive_cannot_silently_skip_counter_or_an_alternative():
    missing_root = Path(__file__).parent/'__missing_connected_archive_inventory__'
    assert not missing_root.exists()
    with pytest.raises(ValueError, match='Both SPAN/COUNTER and all three complete') as failure:
        verify.inventory(missing_root)
    assert 'COUNTER' in str(failure.value)
    assert 'BRANCHED' in str(failure.value)
    assert 'G05' in str(failure.value)


def test_native_json_description_does_not_confuse_the_control_npz_surface_enum():
    info = dict(source_surface='vf', native_surface='Explicit arithmetic quad-centre fans')
    verify.verify_surface_labels(info, 'vf')
    with pytest.raises(ValueError, match='surface labels'):
        verify.verify_surface_labels(dict(info, native_surface='mean'), 'vf')
    with pytest.raises(ValueError, match='surface labels'):
        verify.verify_surface_labels(info, 'mean')


def test_explicit_recheck_receipt_name_keeps_default_failure_receipt_separate():
    root = Path(__file__).parent/'preserved_pilot_root'
    original = verify.receipt_destination(root)
    assert original == root/'VERIFICATION.json'
    recheck = verify.receipt_destination(root, Path('VERIFICATION_RECHECK_01.json'))
    assert recheck == root/'VERIFICATION_RECHECK_01.json'
    assert recheck != original
    absolute = Path(__file__).resolve().parent/'absolute_recheck.json'
    assert verify.receipt_destination(root, absolute) == absolute
