"""Seams, explicit reconstruction, physical scale and bounded patch ownership."""
from pathlib import Path
import importlib.util
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'experiments/fold_visible_gate_20261012'))
from wall_fold import apply_wall, measure_rails


class SyntheticSampler:
    """Known geometric relief, independent of the wall construction formula."""
    def __init__(self, scale=1):
        self.scale = scale

    def sample(self, uv, records=False):
        uv = np.asarray(uv)
        height, theta = uv[..., 0], uv[..., 1]
        radius = 1.+.18*np.sin(12*np.pi*height)+.08*np.cos(9*theta)
        xyz = self.scale*np.stack([radius*np.cos(theta), radius*np.sin(theta), 8*height], axis=-1)
        if records:
            return xyz, np.zeros(height.shape, dtype=int), np.broadcast_to([1., 0., 0.], (*height.shape, 3)).copy()
        return xyz


@pytest.fixture(scope='module')
def fixture():
    parameter = np.linspace(.2, .8, 41)
    guide = dict(axis=np.array('height'), parameter=parameter,
        lower_cross=np.full(41, .2), guide_cross=np.full(41, .6), upper_cross=np.full(41, 1.2))
    return SyntheticSampler(), guide


def query(sampler, height, theta):
    h, t = np.broadcast_arrays(height, theta)
    uv = np.column_stack([h.ravel(), t.ravel()])
    xyz = sampler.sample(uv)
    chart = np.column_stack([uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])])
    return xyz, chart


def test_exact_patch_seams_and_zero_intervention(fixture):
    sampler, guide = fixture
    rail = measure_rails(sampler, guide)
    height = np.concatenate([guide['parameter'], guide['parameter'], [.2]*11, [.8]*11])
    theta = np.concatenate([guide['lower_cross'], guide['upper_cross'],
        np.linspace(.2, 1.2, 11), np.linspace(.2, 1.2, 11)])
    xyz, chart = query(sampler, height, theta)
    for mode in ('DEPTH', 'WALL'):
        delta, fields = apply_wall(xyz, chart, rail, mode)
        assert np.array_equal(delta, np.zeros_like(delta))
        assert np.array_equal(fields['weights'], np.zeros_like(fields['weights']))
        inside, ichart = query(sampler, .5, .6)
        delta, _ = apply_wall(inside, ichart, rail, mode, strength=0)
        assert np.array_equal(delta, np.zeros_like(delta))


@pytest.mark.parametrize('mode', ['DEPTH', 'WALL'])
def test_scale_equivariance_and_constructed_reflection(fixture, mode):
    sampler, guide = fixture
    rail = measure_rails(sampler, guide)
    scaled = measure_rails(SyntheticSampler(2), guide)
    xyz, chart = query(sampler, np.linspace(.25, .75, 17), np.linspace(.25, 1.1, 17))
    delta, _ = apply_wall(xyz, chart, rail, mode)
    twice, _ = apply_wall(2*xyz, chart, scaled, mode)
    assert np.allclose(twice, 2*delta, rtol=0, atol=2e-12)
    for signs in ([1., -1., 1.], [-1., 1., 1.], [-1., -1., 1.]):
        reflected_chart = chart.copy()
        reflected_chart[:, 1:] *= np.asarray(signs)[:2]
        other, _ = apply_wall(xyz*np.asarray(signs), reflected_chart, rail, mode)
        assert np.allclose(other, delta*np.asarray(signs), rtol=0, atol=1e-13)


def test_reconstruction_removes_inherited_rail_jitter_and_differs_from_depth_only(fixture):
    sampler, guide = fixture
    rail = measure_rails(sampler, guide)
    xyz, chart = query(sampler, np.linspace(.35, .65, 21), .6)
    wall, wf = apply_wall(xyz, chart, rail, 'WALL')
    depth, df = apply_wall(xyz, chart, rail, 'DEPTH')
    assert np.array_equal(wf['weights'], df['weights'])
    assert np.allclose(xyz+wall, wf['targets'][0], rtol=0, atol=1e-13)
    assert np.max(np.linalg.norm(wall-depth, axis=1)) > .1
    assert np.max(np.linalg.norm(np.diff(xyz+wall, n=2, axis=0), axis=1)) < .05*np.max(
        np.linalg.norm(np.diff(xyz+depth, n=2, axis=0), axis=1))


def test_overlapping_core_proposals_are_averaged_instead_of_summed(fixture):
    sampler, guide = fixture
    first = measure_rails(sampler, guide, angle_degrees=30)
    second = measure_rails(sampler, guide, angle_degrees=40)
    xyz, chart = query(sampler, [.4, .5, .6], [.5, .6, .7])
    for mode in ('DEPTH', 'WALL'):
        a, _ = apply_wall(xyz, chart, first, mode)
        b, _ = apply_wall(xyz, chart, second, mode)
        both, fields = apply_wall(xyz, chart, [first, second], mode)
        assert np.array_equal(fields['overlap_denominator'], np.full(3, 2.))
        assert np.allclose(both, .5*(a+b), rtol=0, atol=1e-13)
        assert np.all(np.linalg.norm(both, axis=1) <= np.maximum(
            np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1))+1e-13)


def test_actual_source_rail_records_reconstruct_native_triangles():
    spec = importlib.util.spec_from_file_location('wall_test_old_study',
        ROOT/'experiments/fold_region_growth_20261012/study.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    from region_fold import NativeChartSampler, measure_longitudinal
    mesh, chart, _ = old.anchor.t.load(old.SOURCES['SPAN'])
    native = old.anchor.t.growth.native(mesh)
    pchart = np.concatenate([chart, old.anchor.t.face_values(mesh, chart)])
    sampler = NativeChartSampler(native.xyz, native.faces[:, :3], pchart)
    guide = measure_longitudinal(sampler, old.anchor.t.overlap.EVENTS[0], frame_mode='region')
    rail = measure_rails(sampler, guide)
    ids, bary = rail['source_triangle_ids'], rail['source_barycentric']
    reconstructed = np.einsum('nki,nkij->nkj', bary, native.xyz[native.faces[ids, :3]])
    assert np.allclose(reconstructed, rail['source_sample_xyz'], rtol=0, atol=1e-13)
    assert np.all(rail['depth'] <= rail['depth_cap'])
    assert np.all(rail['depth'] > 0)
    assert np.allclose(np.sum(rail['normal']*rail['tangent'], axis=1), 0, atol=1e-13)


def test_unordered_or_transverse_guide_is_rejected(fixture):
    sampler, guide = fixture
    for bad in (dict(guide, axis=np.array('theta')),
        dict(guide, upper_cross=guide['guide_cross'].copy())):
        with pytest.raises(ValueError):
            measure_rails(sampler, bad)
