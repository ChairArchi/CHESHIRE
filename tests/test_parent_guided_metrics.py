"""Reproducible synthetic counterexamples; no saved body or G6 execution."""
from pathlib import Path
import importlib.util
import json

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_parent_metrics',
    ROOT/'experiments/parent_guided_detail_20261012/metrics.py')
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)


@pytest.fixture
def v_parent():
    parameter = np.linspace(.2, .8, 9)
    x = np.linspace(-1., 1., 257)
    theta = .7+.5*x
    uv = np.stack(np.broadcast_arrays(parameter[:, None], theta[None, :]), axis=2)
    reference = np.stack(np.broadcast_arrays(x[None, :], parameter[:, None],
        (-.2+.2*np.abs(x))[None, :]), axis=2).copy()
    right_arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(reference[0, 128:], axis=0), axis=1))]
    left_arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(reference[0, :129], axis=0), axis=1))]
    parent = dict(parameter=parameter, parent_surface_uv=uv, parent_shoulder_uv=uv[:, 128:],
        parent_surface_signed_arc=np.broadcast_to(np.r_[left_arc[:-1]-left_arc[-1], right_arc], (9, 257)),
        parent_shoulder_arc=np.broadcast_to(right_arc, (9, 129)),
        parent_normal=np.tile([0., 0., 1.], (9, 1)),
        parent_valley_measured_mask=np.ones(9, bool), parent_index=np.array(1))
    return reference, parent


def test_unchanged_v_has_two_sided_depth_and_no_middle_basin(v_parent):
    reference, parent = v_parent
    report, arrays = metrics.compare_parent(reference, reference.copy(), parent)
    assert np.allclose(arrays['reference_signed_valley_deficit'], .2)
    assert report['valley_displacement']['magnitude']['maximum'] == 0.
    assert report['sampled_core_displacement']['magnitude']['maximum'] == 0.
    assert report['two_sided_signed_valley_deficit']['change']['maximum'] == 0.
    assert not report['intermediate_basin_diagnostic']['result_found']
    # A valley→upper chord has zero deficit at its first endpoint. It cannot
    # replace this lower→upper depth measurement of the same synthetic body.
    assert arrays['reference_signed_valley_deficit'][0] > 0.
    json.dumps(report, allow_nan=False)


def test_result_does_not_rechoose_reference_chord_projection(v_parent):
    reference, parent = v_parent
    result = reference.copy()
    result[:, 128, 0] = .5
    result[:, -1, 2] = .1
    _, arrays = metrics.compare_parent(reference, result, parent)
    assert np.allclose(arrays['fixed_reference_chord_projection_fraction'], .5)
    assert np.allclose(arrays['result_signed_valley_deficit'], .25)
    assert np.allclose(arrays['result_signed_valley_deficit']-arrays['reference_signed_valley_deficit'], .05)
    # Reprojecting onto the changed result chord would silently measure a
    # different location and produce a different apparent result depth.
    chord = result[:, -1]-result[:, 0]
    changed_fraction = np.sum((result[:, 128]-result[:, 0])*chord, axis=1)/np.sum(chord*chord, axis=1)
    assert not np.allclose(changed_fraction, arrays['fixed_reference_chord_projection_fraction'])


def test_known_owned_inward_basin_is_detected_on_fixed_slices(v_parent):
    reference, parent = v_parent
    result = reference.copy()
    x = reference[0, :, 0]
    basin = .06*np.exp(-((np.maximum(x, 0.)-.55)/.10)**2)
    basin[x <= 0.] = 0.
    result[:, :, 2] -= basin
    report, _ = metrics.compare_parent(reference, result, parent)
    diagnostic = report['intermediate_basin_diagnostic']
    assert diagnostic['fixed_slice_count'] > 0
    assert diagnostic['reference_slices_with_minima'] == 0
    assert diagnostic['result_found']
    assert diagnostic['slices_with_unmatched_result_minima'] > 0
    assert report['sampled_core_displacement']['magnitude']['maximum'] < .001
    json.dumps(report, allow_nan=False)


def test_deeper_parent_alone_is_not_middle_basin_or_visual_success(v_parent):
    reference, parent = v_parent
    result = reference.copy()
    result[:, :, 2] *= 1.5
    report, arrays = metrics.compare_parent(reference, result, parent)
    assert np.allclose(arrays['result_signed_valley_deficit'], .3)
    assert report['two_sided_signed_valley_deficit']['increased_station_count'] == 9
    assert not report['intermediate_basin_diagnostic']['result_found']
    assert 'passed' not in report
    assert 'visual success' in report['scope']
