"""Small actual-parent/provenance checks; no G6 generation or rendering."""
from pathlib import Path
import importlib.util
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_parent_guidance',
    ROOT/'experiments/parent_guided_detail_20261012/guidance.py')
guidance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guidance)


@pytest.fixture
def curved_arc_parent():
    parameter = np.linspace(.2, .8, 7)
    fractions = np.linspace(0., 1., 129)
    valley = .25+.12*parameter
    cross = valley[:, None]+(.60+.08*parameter[:, None])*fractions
    uv = np.stack([np.broadcast_to(parameter[:, None], cross.shape), cross], axis=2)
    arc = (fractions[None, :]**2+.2*fractions[None, :])*(1.+parameter[:, None])
    return dict(parameter=parameter, parent_shoulder_uv=uv, parent_shoulder_arc=arc)


def material(uv):
    uv = np.asarray(uv)
    return np.column_stack([uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])])


def test_physical_arc_inverse_reflections_boundaries_and_core(curved_arc_parent):
    parent = curved_arc_parent
    p = np.array([.2, .311, .5, .697, .8])
    f = np.array([0., .35, .55, .75, 1.])
    uv = guidance._uv_at_fraction(p, f, parent)
    chart = material(uv)
    coords = guidance.patch_coordinates(chart, parent)
    assert np.allclose(coords['u'], f, atol=2e-14, rtol=0)
    assert np.allclose(coords['q'][[0, -1]], [-1., 1.], atol=2e-14, rtol=0)
    assert np.array_equal(coords['envelope'][[0, -1]], [0., 0.])
    for signs in ([1., -1., 1.], [1., 1., -1.], [1., -1., -1.]):
        reflected = guidance.patch_coordinates(chart*np.asarray(signs), parent)
        for key in coords:
            assert np.array_equal(reflected[key], coords[key])
    valley = guidance._uv_at_fraction(np.array([.5]), np.array([0.]), parent)
    centre = guidance.patch_coordinates(material(valley), parent)
    assert centre['core_weight'][0] == 1.
    assert centre['envelope'][0] == 0.


def test_negative_core_uses_measured_left_arc(curved_arc_parent):
    parent = curved_arc_parent
    p = parent['parameter']
    valley = parent['parent_shoulder_uv'][:, 0, 1]
    cross = valley[:, None]+np.array([-.20, -.10, 0.])[None, :]
    uv = np.stack([np.broadcast_to(p[:, None], cross.shape), cross], axis=2)
    right_length = parent['parent_shoulder_arc'][:, -1:]
    signed_arc = right_length*np.array([-.60, -.30, 0.])[None, :]
    parent['parent_surface_uv'] = np.concatenate([uv[:, :-1], parent['parent_shoulder_uv']], axis=1)
    parent['parent_surface_signed_arc'] = np.concatenate([signed_arc[:, :-1], parent['parent_shoulder_arc']], axis=1)
    v = np.interp(.5, p, valley)
    coords = guidance.patch_coordinates(material([[.5, v-.05], [.5, v-.10]]), parent)
    assert np.allclose(coords['u'], [-.15, -.30], atol=2e-14, rtol=0)
    assert coords['core_weight'][0] > 0.
    assert coords['core_weight'][1] == 0.
    assert np.array_equal(coords['envelope'], [0., 0.])


@pytest.fixture(scope='module', params=['SPAN', 'COUNTER'])
def actual_parent(request):
    source = ROOT/'docs/fold_visible_gate_20261012/review/WALL'/request.param/'G03'
    mesh, chart, _ = guidance.t.load(source)
    parent = guidance.measure_parent(source, 1, mesh=mesh, chart=chart)
    return mesh, chart, parent


def test_actual_parent_depth_frame_and_barycentric_provenance(actual_parent):
    mesh, chart, parent = actual_parent
    size = len(parent['parameter'])
    for key in ('parent_depth', 'parent_shoulder_width'):
        assert parent[key].shape == (size,)
        assert np.isfinite(parent[key]).all()
    assert np.any(parent['parent_depth'] > 0.)
    assert np.all(parent['parent_shoulder_width'] > 0.)
    assert parent['parent_observed_prominence'].shape == (size,)
    assert np.all(parent['parent_observed_prominence'] > 0.)
    measured = parent['parent_observed_prominence_measured_mask']
    assert measured[0] and measured[-1]
    assert np.allclose(parent['parent_observed_prominence'][measured],
                       parent['parent_observed_prominence_raw'][measured], atol=2e-13, rtol=0)
    assert np.array_equal(measured, parent['parent_valley_measured_mask'])
    assert not np.array_equal(parent['parent_depth'], parent['legacy_parent_target_depth'])
    assert np.allclose(np.sum(parent['parent_tangent']*parent['parent_normal'], axis=1), 0., atol=2e-13)
    native = guidance.t.growth.native(mesh)
    for prefix in ('parent_search', 'parent_shoulder', 'parent_lower_shoulder'):
        ids, bary = parent[prefix+'_triangle_ids'], parent[prefix+'_barycentric']
        rebuilt = np.einsum('...i,...ij->...j', bary, native.xyz[native.faces[ids, :3]])
        assert np.allclose(rebuilt, parent[prefix+'_xyz'], rtol=0, atol=2e-13)


def test_guided_colonies_are_actual_attached_owned_frames_and_deterministic(actual_parent):
    mesh, chart, parent = actual_parent
    # A changed incoming carrier must be sampled afresh, not read from the
    # parent's saved XYZ. This small test edits only its in-memory coordinates.
    changed = mesh.xyz.copy()
    mesh.xyz = changed*1.003
    recipe = dict(primary_radius=.30, secondary_radius=.14, primary_amplitude=.22,
                  secondary_amplitude=.07, guided_primary_count=3)
    try:
        colonies = guidance.make_guided_colonies(mesh, chart, parent, recipe)
        repeated = guidance.make_guided_colonies(mesh, chart, parent, recipe)
        native = guidance.t.growth.native(mesh)
    finally:
        mesh.xyz = changed
    for key in colonies:
        assert np.array_equal(colonies[key], repeated[key])
    assert len(colonies['centres']) == 9
    assert np.all((colonies['owned_arc_fraction'] >= .35-1e-12) & (colonies['owned_arc_fraction'] <= .75+1e-12))
    rebuilt = np.einsum('ni,nij->nj', colonies['source_barycentric'],
        native.xyz[native.faces[colonies['source_triangle_ids'], :3]])
    assert np.allclose(rebuilt, colonies['centres'], rtol=0, atol=2e-13)
    assert np.allclose(np.cross(colonies['tangents'], colonies['bitangents']), colonies['normals'], atol=2e-13)
    curve = colonies['trajectory_sample_xyz']
    uv = colonies['trajectory_sample_uv']
    for i in range(3):
        coefficients = np.polyfit(uv[i, :, 0]-colonies['sample_uv'][i, 0], curve[i], 2)
        direction = coefficients[1]
        normal = colonies['normals'][i]
        projected = guidance.bulb.unit(direction-normal*np.dot(direction, normal))
        assert abs(np.dot(projected, colonies['tangents'][i])) > 1.-1e-12
