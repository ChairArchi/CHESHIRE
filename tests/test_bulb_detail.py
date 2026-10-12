"""Finite-set relief invariants without an untracked WALL checkpoint dependency."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_path = Path(__file__).resolve().parents[1]/'experiments/fold_visible_gate_20261012/bulb_detail.py'
_spec = importlib.util.spec_from_file_location('bulb_detail_test_module', _path)
bulb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bulb)


@pytest.fixture(scope='module')
def small_atlas():
    recipe = dict(bulb.ATLAS_RECIPE, xy_resolution=49, z_resolution=48, iterations=8)
    return bulb.build_atlas(recipe)


def test_atlas_is_reproducible_finite_occupied_envelope(small_atlas):
    recipe = dict(bulb.ATLAS_RECIPE, xy_resolution=49, z_resolution=48, iterations=8)
    second = bulb.build_atlas(recipe)
    for key in small_atlas:
        assert np.array_equal(small_atlas[key], second[key])
    occupied = small_atlas['finite_membership']
    assert occupied.any() and not occupied[:, :, -1].any()
    expected = np.max(np.where(occupied, small_atlas['z_axis'][None, None], 0.), axis=2)
    assert np.array_equal(expected, small_atlas['height_raw'])
    # A finite bulb upper boundary retains angular structure at equal radius;
    # a smooth radial dome could not satisfy this physical-shape check.
    angle = np.linspace(0., 2*np.pi, 161)
    profile = bulb.sample_atlas(small_atlas, .72*np.cos(angle), .72*np.sin(angle))
    assert np.ptp(profile) > .1
    assert np.array_equal(bulb.sample_atlas(small_atlas, [2., -2.], [0., 0.]), [0., 0.])


def test_planar_relief_has_compact_support_outward_motion_and_amplitude_bound(small_atlas):
    axis = np.linspace(-.6, .6, 71)
    y, z = np.meshgrid(axis, axis)
    reference = np.column_stack([np.full(y.size, 2.), y.ravel(), z.ravel()])
    chart = np.tile([.5, 1., 1.], (len(reference), 1))
    incoming = np.tile([1., 0., 0.], (len(reference), 1))
    colonies = dict(centres=np.array([[2., 0., 0.]]), normals=np.array([[1., 0., 0.]]),
        tangents=np.array([[0., 0., 1.]]), bitangents=np.array([[0., -1., 0.]]),
        radii=np.array([.3]), amplitudes=np.array([.3]))
    delta, fields = bulb.apply_colonies(reference, chart, incoming, colonies, small_atlas, .12)
    assert np.isfinite(delta).all()
    assert np.linalg.norm(delta, axis=1).max() == pytest.approx(.12)
    assert np.max(delta[:, 0]) > .08
    assert np.all(delta[:, 0] >= 0.) and np.array_equal(delta[:, 1:], np.zeros_like(delta[:, 1:]))
    outside = np.linalg.norm(reference[:, 1:], axis=1) >= .3
    assert np.array_equal(delta[outside], np.zeros_like(delta[outside]))
    assert np.all(np.sum(delta*incoming, axis=1) >= 0.)
    repeated, repeated_fields = bulb.apply_colonies(reference, chart, incoming, colonies, small_atlas, .12)
    assert np.array_equal(delta, repeated)
    assert np.array_equal(fields['height'], repeated_fields['height'])


def test_colonies_correspond_to_actual_native_surface_without_changing_source():
    t = bulb.study.previous.anchor.t
    mesh, chart, _ = t.load(bulb.study.previous.SOURCES['SPAN'])
    before = mesh.xyz.copy()
    variant = dict(bulb.VARIANTS['COARSE_CLUSTER'], primary_count=6)
    colonies = bulb.make_colonies(mesh, chart, variant)
    repeated = bulb.make_colonies(mesh, chart, variant)
    for key in colonies:
        assert np.array_equal(colonies[key], repeated[key])
    assert np.array_equal(mesh.xyz, before)
    native = t.growth.native(mesh)
    source_triangles = native.faces[colonies['primary_source_triangle_ids'], :3]
    reconstructed = np.einsum('ni,nij->nj', colonies['primary_source_barycentric'], native.xyz[source_triangles])
    assert np.allclose(reconstructed, colonies['primary_source_xyz'], atol=1e-12)
    secondary = colonies['levels'] == 1
    assert np.array_equal(colonies['centres'][secondary], native.xyz[colonies['native_vertex_ids'][secondary]])
    frames = np.stack([colonies['normals'], colonies['tangents'], colonies['bitangents']], axis=1)
    assert np.allclose(frames@frames.transpose(0, 2, 1), np.eye(3), atol=1e-12)
    assert (colonies['pooled_native_normal_counts'] > 0).all()


def test_integrated_relief_has_attached_positive_buds_and_shallow_compact_root_collars(small_atlas):
    axis = np.linspace(-.5, .5, 101)
    y, z = np.meshgrid(axis, axis)
    reference = np.column_stack([np.full(y.size, 2.), y.ravel(), z.ravel()])
    chart = np.tile([.5, 1., 1.], (len(reference), 1))
    incoming = np.tile([1., 0., 0.], (len(reference), 1))
    colonies = dict(centres=np.array([[2., 0., 0.]]), normals=np.array([[1., 0., 0.]]),
        tangents=np.array([[0., 0., 1.]]), bitangents=np.array([[0., -1., 0.]]),
        radii=np.array([.3]), amplitudes=np.array([.22]), levels=np.array([0]))
    recipe = bulb.VARIANTS['INTEGRATED']
    delta, fields = bulb.apply_colonies(reference, chart, incoming, colonies, small_atlas, .15, recipe)
    assert np.isfinite(delta).all() and delta.shape == reference.shape
    assert np.max(delta[:, 0]) == pytest.approx(.15)
    assert np.min(delta[:, 0]) < -.01
    assert np.min(delta[:, 0]) >= -recipe['root_collar_amplitude']-1e-12
    assert np.array_equal(delta[:, 1:], np.zeros_like(delta[:, 1:]))
    outside = np.linalg.norm(reference[:, 1:], axis=1) >= .3*recipe['root_collar_outer_radius']
    assert np.array_equal(delta[outside], np.zeros_like(delta[outside]))
    established_bud = fields['positive_height'] >= recipe['collar_positive_suppression_height']
    assert not fields['root_collar_height'][established_bud].any()


def test_generation_options_reject_bad_generation_without_creating_outputs(tmp_path):
    root = tmp_path/'invalid'
    with pytest.raises(ValueError, match='generations'):
        bulb.generate(root, tmp_path/'missing_parent', detail_generation=6)
    assert not root.exists()
