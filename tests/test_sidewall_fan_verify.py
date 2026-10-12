"""Small sidewall provenance corruption cases; no actual pilot/data load."""
from pathlib import Path
import copy
import importlib.util

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location('tested_sidewall_fan_verify',
    Path(__file__).resolve().parents[1]/'experiments/sidewall_fan_growth_20261013/verify.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def fixture():
    parent = dict(face_event_ids=np.array([0, 1, 1, 1, 1, 1]),
        face_roles=np.array([0, 1, 1, 2, 1, 1]), face_parent_event_ids=np.zeros(6, np.int64),
        face_source_ids=np.arange(6), mirror_x_face_pairs=np.array([0, 2, 1, 3, 5, 4]),
        mirror_y_face_pairs=np.arange(6))
    mapping = np.array([0, 3, 4, 5, 1, 2, 1, 2])
    signs = np.ones((8, 2), np.int64); signs[4:, 0] = -1
    physical_parent = mapping.copy(); physical_parent[4:] = parent['mirror_x_face_pairs'][physical_parent[4:]]
    events = [dict(event_id=2, status='accepted', level=1, parent_event_id=1, parent_role=1,
        source_generation=3, selected_input_faces=[1, 2], generated_cap_faces=[6, 7]),
        dict(event_id=3, status='rejected', level=1, parent_event_id=1, parent_role=1, reason='Pinched patch')]
    evidence = dict(mirror_source_face_ids=np.arange(8), mirror_face_signs=signs,
        face_event_ids=np.array([0, 1, 1, 1, 2, 2, 2, 2]), face_roles=np.array([0, 2, 1, 1, 1, 1, 2, 2]),
        face_parent_event_ids=np.array([0, 0, 0, 0, 1, 1, 1, 1]), face_source_ids=mapping.copy(),
        face_parent_source_ids=physical_parent, temporary_parent_face_source_ids=mapping.copy(),
        accepted_event_counts_by_level=np.array([1, 1, 0]), rejected_event_count=np.array(1),
        inherited_event_count=np.array(1), new_accepted_event_count=np.array(1),
        event_002_selected_input_faces=np.array([1, 2]), event_002_parent_face=mapping,
        event_002_generated_cap_faces=np.array([6, 7]), event_002_selected_parent_event_ids=np.array([1, 1]),
        event_002_selected_parent_roles=np.array([1, 1]), event_002_selected_parent_source_face_ids=np.array([1, 2]))
    evidence.update({'initial_parent_'+key: parent[key].copy() for key in
        ('face_event_ids', 'face_roles', 'face_parent_event_ids', 'face_source_ids')})
    return parent, events, evidence


def parent_receipt():
    stages = [dict(passed=True, semantics=dict(actual_generation=g, added_CC_passes=g-3),
        exact_control_native_and_evidence_replay=True, actual_native_topology=dict(passed=True),
        actual_native_symmetry={axis: dict(passed=True) for axis in ('X', 'Y')}) for g in (3, 4, 5)]
    return dict(status='PASS', expected_cases=list(verify.CASES), expected_modes=list(verify.H.MODES),
        cases={case: dict(passed=True, states={mode: dict(passed=True, stages=copy.deepcopy(stages))
            for mode in verify.H.MODES}) for case in verify.CASES})


def test_sidewall_trace_separates_inherited_root_new_children_and_rejected_attempts():
    parent, events, evidence = fixture()
    result = verify.sidewall_ownership(events, evidence, parent)
    assert result['accepted_by_level'] == [1, 1, 0]
    assert result['new_canonical_events'] == 1
    assert result['accepted_canonical_events'] == 2
    assert result['reflected_constructive_event_instances'] == 8
    assert result['attempted_new_canonical_events'] == 2
    assert result['rejected_canonical_events'] == 1


@pytest.mark.parametrize('role,owner', [(2, 1), (0, 0), (1, 4)])
def test_cap_source_or_sibling_faces_cannot_masquerade_as_inherited_root_sidewall(role, owner):
    parent, events, evidence = fixture()
    parent['face_roles'][1] = role; parent['face_event_ids'][1] = owner
    evidence['initial_parent_face_roles'] = parent['face_roles'].copy()
    evidence['initial_parent_face_event_ids'] = parent['face_event_ids'].copy()
    with pytest.raises(ValueError, match='root-1 sidewall'):
        verify.sidewall_ownership(events, evidence, parent)


def test_final_parent_correspondence_requires_reflected_physical_parent_ids():
    parent, events, evidence = fixture()
    evidence['face_parent_source_ids'] = evidence['temporary_parent_face_source_ids'].copy()
    with pytest.raises(ValueError, match='reflected parent-source'):
        verify.sidewall_ownership(events, evidence, parent)


def test_actual_initial_ancestry_and_new_count_cannot_be_relabelled():
    parent, events, evidence = fixture()
    evidence['initial_parent_face_source_ids'][1] = 99
    with pytest.raises(ValueError, match='Initial sidewall ancestry'):
        verify.sidewall_ownership(events, evidence, parent)
    parent, events, evidence = fixture()
    evidence['new_accepted_event_count'] = np.array(2)
    with pytest.raises(ValueError, match='event counts'):
        verify.sidewall_ownership(events, evidence, parent)


def test_preserved_parent_pass_requires_all_old_cases_modes_and_actual_stages():
    receipt = parent_receipt()
    assert verify.parent_stage_receipt(receipt, 'SPAN')['semantics']['actual_generation'] == 3
    receipt['cases']['COUNTER']['states']['BRANCHED']['stages'][-1]['actual_native_symmetry']['Y']['passed'] = False
    with pytest.raises(ValueError, match='18 actual'):
        verify.parent_stage_receipt(receipt, 'SPAN')
    receipt = parent_receipt(); receipt['status'] = 'FAIL'
    with pytest.raises(ValueError, match='parent verification PASS'):
        verify.parent_stage_receipt(receipt, 'SPAN')


def test_missing_counter_is_not_skipped_and_recheck_has_separate_destination():
    missing = Path(__file__).parent/'__missing_sidewall_verify_inventory__'
    assert not missing.exists()
    with pytest.raises(ValueError, match='complete SPAN/COUNTER'):
        verify.inventory(missing)
    assert verify.H.receipt_destination(missing, Path('VERIFICATION_RECHECK_01.json')) != verify.H.receipt_destination(missing)
