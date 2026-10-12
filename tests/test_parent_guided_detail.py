"""Small failure-mode fixtures for parent-owned, body-integral detail.

These checks do not generate a full column, evaluate a new fractal atlas, or
render. Native topology and two-input package replay are checked separately.
"""
from pathlib import Path
import importlib.util

import numpy as np
import pytest


MODULE = Path(__file__).resolve().parents[1]/'experiments/parent_guided_detail_20261012/study.py'
SPEC = importlib.util.spec_from_file_location('test_parent_guided_detail_study', MODULE)
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)

RECIPE = dict(maximum_height=.30, collar_positive_suppression_height=.08)


def test_zero_ownership_preserves_baseline_bytes_and_inputs():
    # Deliberately not the formula's recomputed values: an unowned point must
    # preserve the supplied baseline, including its last bit and signed zero.
    baseline = np.array([[np.nextafter(.13, 1.), -0., .02], [.02, .03, -.04]])
    positive = np.array([.2, .11])
    collar = np.array([.035, .017])
    normals = np.array([[1., 0., 0.], [0., 0., 1.]])
    core = np.zeros(2)
    inputs = [baseline, positive, collar, normals, core]
    before = [value.tobytes() for value in inputs]
    delta = study.priority_delta(baseline, positive, collar, normals, core, RECIPE)
    assert delta.tobytes() == baseline.tobytes()
    assert [value.tobytes() for value in inputs] == before


def test_owned_groove_rejects_outward_growth_without_erasing_inward_collar():
    baseline = np.array([[.2, 0., 0.], [.2, 0., 0.], [.13, -0., .02]])
    normals = np.tile([1., 0., 0.], (3, 1))
    delta = study.priority_delta(
        baseline, np.array([.2, .2, .2]), np.array([.035, .035, .035]),
        normals, np.array([1., .8, 0.]), RECIPE)
    # Fully owned core keeps a real inward fold even when the previous positive
    # lobe was large enough to have hidden that collar entirely.
    assert delta[0, 0] == pytest.approx(-.035)
    assert np.array_equal(delta[0, 1:], [0., 0.])
    # A soft shoulder still develops relief; protecting the groove must not
    # silently freeze the complete nearby body.
    assert 0. < delta[1, 0] < .04
    assert delta[2].tobytes() == baseline[2].tobytes()
    assert np.isfinite(delta).all()
    assert np.linalg.norm(delta, axis=1).max() <= RECIPE['maximum_height']


def test_bound_limits_real_vector_length_and_keeps_direction_and_small_values():
    delta = np.array([[.3, .3, .3], [-3., 4., 0.], [.02, -0., .01], [0., 0., 0.]])
    original = delta.copy()
    bounded = study.bound_delta(delta, maximum=.30)
    assert np.isfinite(bounded).all()
    assert np.linalg.norm(bounded, axis=1).max() <= .30+1e-15
    assert np.allclose(np.linalg.norm(bounded[:2], axis=1), .30, rtol=0., atol=1e-15)
    # Per-axis clipping would pass a coordinate check and fail these assertions.
    assert np.allclose(np.cross(bounded[:2], original[:2]), 0., rtol=0., atol=1e-15)
    assert np.all(np.sum(bounded[:2]*original[:2], axis=1) > 0.)
    assert bounded[2:].tobytes() == original[2:].tobytes()
    assert delta.tobytes() == original.tobytes()


def test_two_input_verification_rejects_missing_or_unexpected_cases():
    study.validate_cases(['SPAN', 'COUNTER'])
    study.validate_cases(['COUNTER', 'SPAN'])
    for invalid in ([], ['SPAN'], ['COUNTER'], ['SPAN', 'COUNTER', 'PRIMITIVE']):
        with pytest.raises(ValueError):
            study.validate_cases(invalid)


def measured_parent(valley=.25, upper=1.10, depth=.20):
    """A simple actual-arc record, independent of the fold placement formula."""
    parameter = np.linspace(.2, .8, 9)
    fraction = np.linspace(0., 1., 129)
    uv = np.empty((len(parameter), len(fraction), 2))
    uv[:, :, 0] = parameter[:, None]
    uv[:, :, 1] = valley+(upper-valley)*fraction[None, :]
    return dict(parameter=parameter, parent_valley_cross=np.full(len(parameter), valley),
        parent_upper_cross=np.full(len(parameter), upper), parent_shoulder_uv=uv,
        parent_shoulder_arc=np.broadcast_to(fraction, uv.shape[:2]).copy(),
        parent_depth=np.full(len(parameter), depth),
        parent_shoulder_width=np.full(len(parameter), .20),
        parent_normal=np.tile([1., 0., 0.], (len(parameter), 1)),
        parent_tangent=np.tile([0., 0., 1.], (len(parameter), 1)))


def query_chart():
    # Include a known neighbouring parent's centre exactly, as well as points
    # beyond both longitudinal ends of the measured patch.
    heights = np.array([.05, .2, .35, .5, .65, .8, .95])
    theta = np.unique(np.r_[np.linspace(.2, 1.35, 117), .74, .90])
    h, a = np.meshgrid(heights, theta, indexing='ij')
    return np.column_stack([h.ravel(), np.cos(a.ravel()), np.sin(a.ravel())]), a.ravel()


def test_signed_fold_is_real_inward_bounded_and_absent_outside_parent_extent():
    chart, _ = query_chart()
    parent = measured_parent()
    delta, fields = study.signed_folds(chart, parent)
    assert np.isfinite(delta).all()
    assert delta.shape == (len(chart), 3)
    assert np.min(delta[:, 0]) < -.05
    assert 0. < np.max(delta[:, 0]) < .5*abs(np.min(delta[:, 0]))
    assert np.linalg.norm(delta, axis=1).max() <= .14+1e-12
    assert np.array_equal(delta[:, 1:], np.zeros_like(delta[:, 1:]))
    inactive = (chart[:, 0] < .2) | (chart[:, 0] > .8)
    assert np.array_equal(delta[inactive], np.zeros_like(delta[inactive]))
    assert np.array_equal(fields['fold_height'][inactive], np.zeros(inactive.sum()))
    # The parent trough itself is protected; nearby inward growth must be an
    # additional shoulder groove rather than simply deepening the old centre.
    valley_chart = np.column_stack([parent['parameter'],
        np.cos(parent['parent_valley_cross']), np.sin(parent['parent_valley_cross'])])
    valley_delta, _ = study.signed_folds(valley_chart, parent)
    assert np.array_equal(valley_delta, np.zeros_like(valley_delta))
    # A zero chord-depth measurement is not an absent geometric shoulder.
    # Generated fold size follows the measured shoulder width, so zero depth
    # must not silently remove a valid fold; reducing width must reduce it.
    depth_zero = dict(parent, parent_depth=np.zeros_like(parent['parent_depth']))
    still_folded, _ = study.signed_folds(chart, depth_zero)
    assert np.array_equal(still_folded, delta)
    narrower = dict(depth_zero, parent_shoulder_width=.5*parent['parent_shoulder_width'])
    smaller, _ = study.signed_folds(chart, narrower)
    assert np.allclose(smaller, .5*delta, rtol=0., atol=1e-15)


def test_other_parent_core_blocks_a_new_fold_independent_of_parent_order():
    chart, theta = query_chart()
    parent = measured_parent()
    other_a = measured_parent(valley=.74, upper=1.15)
    other_b = measured_parent(valley=.90, upper=1.30)
    unprotected, _ = study.signed_folds(chart, parent)
    protected, fields = study.signed_folds(chart, parent, (other_a, other_b))
    reverse, reverse_fields = study.signed_folds(chart, parent, (other_b, other_a))
    assert np.array_equal(protected, reverse)
    for key in ('fold_height', 'core_union', 'patch_envelope'):
        assert np.array_equal(fields[key], reverse_fields[key])
    # This is a real conflicting request, not just an empty mask whose output
    # would have been zero even without another parent's ownership.
    witness = (chart[:, 0] == .5) & (theta == .74)
    assert witness.sum() == 1
    assert np.linalg.norm(unprotected[witness], axis=1)[0] > .05
    assert np.array_equal(protected[witness], np.zeros((1, 3)))
    assert np.any(np.linalg.norm(protected, axis=1) > .01)


def test_signed_fold_scalar_fields_use_material_reflection_not_xyz_signs():
    chart, _ = query_chart()
    parent = measured_parent()
    parent['parent_normal'][:] = [.6, .8, 0.]
    expected_delta, expected = study.signed_folds(chart, parent)
    assert np.any(expected['fold_height'] < -.05)
    for signs in ([1., -1.], [-1., 1.], [-1., -1.]):
        reflected = chart.copy()
        reflected[:, 1:] *= signs
        actual_delta, actual = study.signed_folds(reflected, parent)
        assert np.array_equal(actual_delta, expected_delta*np.r_[signs, 1.])
        for key in ('fold_height', 'core_union', 'patch_envelope'):
            assert np.array_equal(actual[key], expected[key])
