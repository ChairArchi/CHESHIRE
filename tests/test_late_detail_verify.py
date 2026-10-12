"""Small counterexamples for causal controls, ancestry and factorial proof."""
from pathlib import Path
import copy
import importlib.util

import numpy as np
import pytest

from cheshire import reference_subdivision as reference


BASE = Path(__file__).resolve().parents[1]/'experiments/late_detail_rules_20261013'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


verify = load('tested_late_detail_verifier', 'verify.py')
operator = load('tested_late_detail_verification_operator', 'late_operator.py')


def fixture(mode='COMBINED'):
    source = reference.cube(side=2.); source.generation = 3
    mesh, _, g4 = reference.subdivide(source, {'weights': {}})
    g3 = dict(face_event_ids=np.array([0, 1, 0, 2, 0, 0]))
    _, _, state = operator.build(mesh, g4, g3, mode)
    return mesh, g4, g3, state


def test_actual_cc_parent_map_drives_binary_faces_and_fractional_incidence_support():
    mesh, g4, g3, state = fixture()
    _, controls, eligible, face = verify.verify_rule_evidence(mesh, g4, g3, 'COMBINED', state, operator.RECIPE, reference)
    assert face.sum() == 8
    assert eligible.all()
    assert np.any((state['input_edge_support'] > 0) & (state['input_edge_support'] < 1))
    assert np.any((state['input_vertex_support'] > 0) & (state['input_vertex_support'] < 1))
    assert np.all(controls['we'] <= 0)


@pytest.mark.parametrize('key', ['input_face_support', 'input_vertex_support', 'input_g4_to_g3_face_ids', 'eq4_eligible_mask'])
def test_forged_support_or_eligible_flags_cannot_hide_behind_correct_geometry(key):
    mesh, g4, g3, state = fixture()
    changed = {k: value.copy() for k, value in state.items()}
    changed[key][0] = not bool(changed[key][0]) if key == 'eq4_eligible_mask' else changed[key][0]+1
    with pytest.raises(ValueError, match='causal support/class/control evidence'):
        verify.verify_rule_evidence(mesh, g4, g3, 'COMBINED', changed, operator.RECIPE, reference)


def test_eq4_only_cannot_silently_include_a_normal_factor():
    mesh, g4, g3, state = fixture('EQ4_ONLY')
    verify.verify_rule_evidence(mesh, g4, g3, 'EQ4_ONLY', state, operator.RECIPE, reference)
    state['resolved_wf'][0] = .8
    with pytest.raises(ValueError, match='resolved_wf'):
        verify.verify_rule_evidence(mesh, g4, g3, 'EQ4_ONLY', state, operator.RECIPE, reference)


def test_ownership_requires_actual_bounded_integer_ancestry():
    with pytest.raises(ValueError, match='G4-to-G3'):
        verify.ancestry_support(np.array([0., 1.]), np.array([0, 1]), 2)
    with pytest.raises(ValueError, match='G4-to-G3'):
        verify.ancestry_support(np.array([0, 2]), np.array([0, 1]), 2)
    with pytest.raises(ValueError, match='G4-to-G3'):
        verify.ancestry_support(np.array([0, 1]), np.array([0, -1]), 2)


def test_factorial_actual_geometry_detects_unexplained_interaction():
    baseline = np.array([[1., 2., 3.], [2., 3., 4.]])
    eq4, normal = baseline+.125, baseline-.0625
    positions = dict(NEUTRAL=baseline, EQ4_ONLY=eq4, NORMAL_ONLY=normal, COMBINED=eq4+normal-baseline)
    result = verify.factorial_sanity(positions)
    assert result['passed'] and result['displacement_from_neutral']['COMBINED']['maximum'] > 0.
    positions['COMBINED'] = positions['COMBINED'].copy(); positions['COMBINED'][0, 0] += .01
    with pytest.raises(ValueError, match='interaction'):
        verify.factorial_sanity(positions)


def test_previous_pass_must_cover_both_actual_lineages_and_all_six_stage_proofs():
    stage = lambda g: dict(passed=True, semantics=dict(actual_generation=g), exact_control_native_and_evidence_replay=True,
        actual_native_topology=dict(passed=True), actual_native_symmetry={a: dict(passed=True) for a in ('X', 'Y')})
    receipt = dict(status='PASS', expected_cases=list(verify.CASES), expected_modes=['SIDEWALL_FAN'],
        cases={case: dict(passed=True, stages=[stage(g) for g in (3, 4, 5)]) for case in verify.CASES})
    assert len(verify.parent_receipt(receipt, 'SPAN')) == 3
    receipt['cases']['COUNTER']['stages'][-1]['actual_native_symmetry']['X']['passed'] = False
    with pytest.raises(ValueError, match='six frozen'):
        verify.parent_receipt(receipt, 'SPAN')


def test_missing_mode_or_counter_cannot_be_silently_skipped():
    missing = Path(__file__).parent/'__missing_late_detail_verify_inventory__'
    assert not missing.exists()
    with pytest.raises(ValueError, match='eight late-rule'):
        verify.inventory(missing)
