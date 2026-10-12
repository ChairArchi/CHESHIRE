"""Actual-parent lineage, exclusion, provenance and scale for one descendant."""
from pathlib import Path
import importlib.util
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'experiments/fold_visible_gate_20261012'))
from wall_fold import measure_rails, apply_wall
from child_fold import measure_child


@pytest.fixture(scope='module')
def source():
    spec = importlib.util.spec_from_file_location('child_test_old_study',
        ROOT/'experiments/fold_region_growth_20261012/study.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    from region_fold import NativeChartSampler, measure_longitudinal
    mesh, chart, tags = old.anchor.t.load(old.SOURCES['SPAN'])
    native_g2 = old.anchor.t.growth.native(mesh)
    pchart_g2 = np.concatenate([chart, old.anchor.t.face_values(mesh, chart)])
    sampler_g2 = NativeChartSampler(native_g2.xyz, native_g2.faces[:, :3], pchart_g2)
    guides = [measure_longitudinal(sampler_g2, parent, frame_mode='region')
        for parent in old.anchor.t.overlap.EVENTS]
    parents = [measure_rails(sampler_g2, guide) for guide in guides]
    out, outchart, _, _ = old.anchor.t.memory.refine(mesh, chart, tags)
    delta, _ = apply_wall(out.xyz, outchart, parents, 'WALL')
    out.xyz += delta
    native = old.anchor.t.growth.native(out)
    pchart = np.concatenate([outchart, old.anchor.t.face_values(out, outchart)])
    sampler = NativeChartSampler(native.xyz, native.faces[:, :3], pchart)
    children = [measure_child(sampler, parent) for parent in parents]
    return dict(native=native, pchart=pchart, sampler=sampler, parents=parents,
        children=children, native_g2=native_g2, pchart_g2=pchart_g2, guides=guides)


def test_parent_valley_is_outside_child_support_and_depth_is_smaller(source):
    for child in source['children']:
        assert np.all(child['lower_cross'] > child['parent_valley_cross'])
        assert np.allclose(child['child_owned_arc_fraction'], [.35, .55, .75], atol=1e-13)
        assert np.all(child['depth'] <= .4*child['parent_depth'])
        assert np.all(child['depth'] > 0)
        uv = np.column_stack([child['parameter'], child['parent_valley_cross']])
        xyz = source['sampler'].sample(uv)
        chart = np.column_stack([uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])])
        delta, fields = apply_wall(xyz, chart, child, 'WALL')
        assert np.array_equal(delta, np.zeros_like(delta))
        assert np.array_equal(fields['weights'], np.zeros_like(fields['weights']))


def test_parent_and_child_records_are_actual_native_triangle_samples(source):
    native = source['native']
    for child in source['children']:
        for prefix in ('source_sample', 'parent_search', 'parent_shoulder'):
            ids_key = 'source_triangle_ids' if prefix == 'source_sample' else prefix+'_triangle_ids'
            bary_key = 'source_barycentric' if prefix == 'source_sample' else prefix+'_barycentric'
            xyz_key = 'source_sample_xyz' if prefix == 'source_sample' else prefix+'_xyz'
            bary, ids = child[bary_key], child[ids_key]
            actual = np.einsum('nki,nkij->nkj', bary, native.xyz[native.faces[ids, :3]])
            assert np.allclose(actual, child[xyz_key], rtol=0, atol=1e-13)


def test_detection_is_majority_and_only_bracketed_holes_can_interpolate(source):
    for child in source['children']:
        valid = child['parent_search_valid']
        central = child['parent_search_central']
        assert (valid & central).sum() > central.sum()/2
        owned = child['parent_valley_measured_mask']
        assert owned[0] and owned[-1]
        assert child['interpolated_ray_count'] == (~owned).sum()
        search_width = child['parent_search_upper_cross']-child['parent_search_lower_cross']
        assert np.all(search_width > 0)
        indices = child['parent_search_trough_indices'][valid]
        assert np.all((indices > 0) & (indices < 256))
        assert np.all(child['parent_search_prominence'][valid] > 0)


def test_physical_scale_equivariance_uses_the_same_owned_rule(source):
    from region_fold import NativeChartSampler
    native_g2, native = source['native_g2'], source['native']
    twice_g2 = NativeChartSampler(2*native_g2.xyz, native_g2.faces[:, :3], source['pchart_g2'])
    twice = NativeChartSampler(2*native.xyz, native.faces[:, :3], source['pchart'])
    for guide, child in zip(source['guides'], source['children']):
        scaled_parent = measure_rails(twice_g2, guide)
        scaled = measure_child(twice, scaled_parent)
        for key in ('parameter', 'lower_cross', 'guide_cross', 'upper_cross'):
            assert np.allclose(scaled[key], child[key], rtol=0, atol=2e-12)
        for key in ('centre_fit', 'lower_fit', 'upper_fit', 'depth', 'parent_depth'):
            assert np.allclose(scaled[key], 2*child[key], rtol=0, atol=2e-11)
        assert np.array_equal(scaled['parent_search_valid'], child['parent_search_valid'])


def test_no_actual_parent_trough_fails_instead_of_using_an_old_band(source):
    class MonotoneSampler:
        def sample(self, uv, records=False):
            uv = np.asarray(uv)
            xyz = np.stack([uv[..., 1], np.zeros(uv.shape[:-1]), uv[..., 0]], axis=-1)
            if records:
                return xyz, np.zeros(uv.shape[:-1], dtype=int), np.broadcast_to(
                    [1., 0., 0.], (*uv.shape[:-1], 3)).copy()
            return xyz
    with pytest.raises(ValueError, match='Actual parent trough absent on majority'):
        measure_child(MonotoneSampler(), source['parents'][0])
