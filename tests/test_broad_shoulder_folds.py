"""Small broad-coordinate, frame and fold counterexamples; no G6 generation."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location('tested_broad_fold_operator',
    Path(__file__).resolve().parents[1]/'experiments/broad_shoulder_folds_20261012/folds.py')
folds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(folds)


@pytest.fixture
def patch():
    parameter = np.linspace(.70, .87, 9)
    cross = np.linspace(.90, 1.56, 129)
    uv = np.stack(np.meshgrid(parameter, cross, indexing='ij'), axis=-1)
    fraction = np.linspace(0., 1., 129)
    return dict(parameter=parameter, surface_uv=uv,
        transverse_arc=(.75+.12*np.sin(np.linspace(0., np.pi, 9)))[:, None]*fraction[None]**1.1,
        physical_width=np.full(9, .65), axial_plateau_fraction=np.array(.6),
        transverse_fade_fraction=np.array(.12))


def material(parameters, fraction, patch):
    uv = folds.measure.uv_at_fraction(parameters, fraction, patch)
    return np.column_stack([uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])])


def test_actual_arc_map_round_trips_and_scalar_ownership_reflects(patch):
    parameter = np.linspace(.70, .87, 31)[:, None]
    fraction = np.linspace(0., 1., 51)[None]
    chart = material(parameter, fraction, patch)
    coords = folds.measure.coordinates(chart, patch)
    assert np.max(np.abs(coords['u']-np.broadcast_to(fraction, (31, 51)).ravel())) < 1e-12
    for signs in ([1., -1., 1.], [1., 1., -1.], [1., -1., -1.]):
        other = folds.measure.coordinates(chart*np.array(signs), patch)
        assert np.array_equal(other['envelope'], coords['envelope'])
    with pytest.raises(ValueError, match='in-range'):
        folds.measure.uv_at_fraction(.90, .5, patch)


def test_broad_profile_has_primary_crest_two_grooves_and_smaller_second_scale(patch):
    chart = material(np.full(1001, .785), np.linspace(0., 1., 1001), patch)
    height, fields = folds.signed_height(chart, patch, 4)
    assert height.max() > .25
    assert height.min() < -.10
    centre = folds.centre(np.array([0.]))[0]
    for expected in (centre-.23, centre+.23):
        index = np.argmin(np.abs(fields['u']-expected))
        assert height[index] < -.10
    small, _ = folds.signed_height(chart, patch, 5)
    assert 0. < small.max() < .09
    assert np.array_equal(height[[0, -1]], [0., 0.])


def test_frame_pool_is_normalized_and_rejects_cancellation(patch):
    arc = patch['transverse_arc']
    normals = np.broadcast_to([0., 1., 0.], arc.shape+(3,)).copy()
    pooled, cross, axial, length = folds.pool_normals(patch['parameter'], arc, normals)
    assert np.allclose(pooled, [0., 1., 0.], atol=1e-15)
    assert np.allclose(cross.sum(axis=1), 1.) and np.allclose(axial.sum(axis=1), 1.)
    assert np.allclose(length, 1.)
    with pytest.raises(ValueError, match='cancel'):
        folds.pool_normals(patch['parameter'], arc, np.zeros_like(normals))


def test_actual_frame_direction_and_reflection_control_the_vector(patch):
    chart = material(np.full(501, .785), np.linspace(.01, .99, 501), patch)
    frame = dict(parameter=patch['parameter'], pooled_normals=np.tile([.6, .8, 0.], (9, 1)),
        incoming_generation=np.array(4))
    delta, fields = folds.normal_delta(chart, patch, frame, 4)
    assert np.allclose(delta[:, 0], fields['height']*.6)
    assert np.allclose(delta[:, 1], fields['height']*.8)
    for signs in ([1., -1., 1.], [1., 1., -1.], [1., -1., -1.]):
        other, _ = folds.normal_delta(chart*np.array(signs), patch, frame, 4)
        assert np.array_equal(other, delta*np.array([signs[1], signs[2], 1.]))
    with pytest.raises(ValueError, match='actual incoming'):
        folds.normal_delta(chart, patch, frame, 5)


def test_clear_and_active_compose_differ_inside_and_restore_outside_exact():
    reference = np.zeros((4, 3))
    baseline = np.full((4, 3), .03)
    weight = np.array([0., .5, 1., 0.])
    delta = np.tile([0., .20, 0.], (4, 1))
    clear = folds.final_positions(reference, baseline, np.zeros_like(delta), weight)
    active = folds.final_positions(reference, baseline, delta, weight)
    assert np.array_equal(clear[[0, 3]], baseline[[0, 3]])
    assert np.array_equal(active[[0, 3]], baseline[[0, 3]])
    assert np.array_equal(clear[2], reference[2])
    assert np.array_equal(active[2], delta[2])
    assert np.allclose(active-clear, weight[:, None]*delta)


def test_fine_runner_resolves_local_study_despite_legacy_module_names():
    path = Path(__file__).resolve().parents[1]/'experiments/broad_shoulder_folds_20261012/study_fans.py'
    spec = importlib.util.spec_from_file_location('tested_rooted_fine_runner', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert Path(runner.study.__file__).resolve() == path.with_name('study.py').resolve()
    assert set(runner.study.CASES) == {'SPAN', 'COUNTER'}
    assert runner.study.MODES == ('CLEAR_ONLY', 'BROAD_ACTIVE')
