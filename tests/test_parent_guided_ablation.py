"""Small ablation failure-mode checks; no full geometry/atlas evaluation."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location('tested_parent_guided_ablation',
    Path(__file__).resolve().parents[1]/'experiments/parent_guided_detail_20261012/ablation.py')
ablation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ablation)


def test_ablation_retains_middle_fold_and_only_tapers_existing_priority():
    priority = np.array([[.2, .0, .0], [.2, .0, .0], [.2, .0, .0]])
    middle = np.array([[0., 0., 0.], [0., -.1, 0.], [0., -.1, 0.]])
    result = ablation.compose_raw(priority, middle, np.array([0., 1., .25]))
    np.testing.assert_array_equal(result[0], priority[0])
    np.testing.assert_array_equal(result[1], middle[1])
    np.testing.assert_allclose(result[2], [.15, -.1, 0.], rtol=0, atol=1e-16)
    # A malformed patch cannot silently extrapolate and invert priority.
    with pytest.raises(ValueError, match='envelope'):
        ablation.compose_raw(priority, middle, np.array([0., 1.01, .25]))


def test_cap_diagnostics_require_uncapped_vectors_not_capped_saved_delta():
    # Every coordinate is below .30, but one actual vector needs limiting.
    raw = np.array([[.29, .29, 0.], [0., -.14, 0.]])
    before = ablation.cap_diagnostics(raw)
    capped = ablation.study.bound_delta(raw)
    after = ablation.cap_diagnostics(capped)
    assert before['cap_active_beyond_1e_12_count'] == 1
    assert before['uncapped_maximum'] > .4
    assert after['cap_active_beyond_1e_12_count'] == 0
    np.testing.assert_allclose(np.linalg.norm(capped[0]), .30, rtol=0, atol=1e-16)
    # Two distinct pre-cap operations can have identical saved capped vectors.
    other = raw.copy(); other[0] *= 2
    np.testing.assert_allclose(ablation.study.bound_delta(other), capped, rtol=0, atol=1e-16)
    assert ablation.cap_diagnostics(other)['uncapped_maximum'] > before['uncapped_maximum']


def test_flow_diagnostics_must_reconnect_to_actual_saved_controls():
    reference = np.array([[1., 2., 3.]])
    expected = reference+np.array([[.02, -.01, .03]])
    assert ablation.flow_replay_check(expected, expected.copy())['passed']
    with pytest.raises(ValueError, match='saved FLOW'):
        ablation.flow_replay_check(expected, expected+np.array([[0., .001, 0.]]))


def test_recapping_saved_actual_delta_cannot_move_unchanged_baseline_by_one_ulp():
    reference = np.tile([.1, .1, 0.], (3, 1))
    baseline = np.tile([.28, .34, 0.], (3, 1))
    chart = np.array([[.5, 1., 0.], [.05, 1., 0.], [.5, 1., 0.]])
    changed = np.array([0, 1, 1], dtype=np.uint8)
    saved_actual_delta = baseline-reference
    assert np.linalg.norm(saved_actual_delta[0]) > .30
    capped = ablation.study.bound_delta(saved_actual_delta)
    recapped_xyz = reference+capped
    assert not np.array_equal(recapped_xyz[0], baseline[0])
    with pytest.raises(ValueError, match='outside its declared'):
        ablation.verified.check_actual_delta(recapped_xyz, reference,
            dict(delta=recapped_xyz-reference, changed_region=changed), baseline, chart)
    result, synchronized_delta, receipt = ablation.preserve_unchanged_baseline(
        reference, capped, baseline, chart, changed)
    np.testing.assert_array_equal(result[:2], baseline[:2])
    np.testing.assert_array_equal(result[2], recapped_xyz[2])
    np.testing.assert_array_equal(synchronized_delta, result-reference)
    assert receipt['roundoff_changed_control_count'] == 2
    assert ablation.verified.check_actual_delta(result, reference,
        dict(delta=synchronized_delta, changed_region=changed), baseline, chart)['operation_delta_exact']
    bad = capped.copy(); bad[0, 0] += .001
    with pytest.raises(ValueError, match='Non-roundoff displacement'):
        ablation.preserve_unchanged_baseline(reference, bad, baseline, chart, changed)
