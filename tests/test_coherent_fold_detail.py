"""Small actual CC fixtures, geometry invariants and coherent-offset counterexamples."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_coherent_fold_operator',
    REPO/'experiments/coherent_fold_detail_20261013/fold_operator.py')
fold = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fold)
FIXTURE_SPEC = importlib.util.spec_from_file_location('coherent_closed_box_fixture',
    REPO/'tests/test_connected_fold_growth.py')
fixtures = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixtures)
from cheshire.reference_subdivision import fields, subdivide, topology  # noqa: E402


def parent_inputs(all_supported=False):
    source, _ = fixtures.box_grid(6, 6)
    source.xyz[:, 2] *= .2
    source.rest = source.xyz.copy()
    c = source.xyz[source.faces].mean(axis=1)
    owner = np.ones(len(c), np.int64) if all_supported else ((c[:, 2] > .3) & (c[:, 2] < 1.7)).astype(np.int64)
    role = np.where(owner, np.where(c[:, 2] > 1., 2, 1), 0).astype(np.int8)
    signs = np.where(c[:, :2] < 0, -1, 1).astype(np.int8)
    g3 = dict(face_event_ids=owner, face_roles=role, mirror_face_signs=signs,
        inherited_root_pca_origin=np.array([.35, .45, 1.]),
        inherited_root_pca_major=np.array([0., 0., 1.]),
        inherited_root_pca_minor=np.array([1., 0., 0.]),
        inherited_root_pca_normal=np.array([0., 1., 0.]),
        inherited_root_pca_extent=np.array([2., 1.]), inherited_root_radius=np.array(.5))
    g4, _, evidence = subdivide(source, {'weights': {}})
    return g4, evidence, g3


def test_constant_scalar_matches_final_vef_offsets_on_actual_flat_regular_patch():
    mesh, e4, e3 = parent_inputs(all_supported=True)
    out, metadata, state = fold.build(mesh, e4, e3, 'COHERENT')
    neutral = subdivide(mesh, {'weights': {}})[0]
    t = topology(mesh); f = fields(mesh)
    # Interior of the front plane has unit +Y normals and equal incident scale.
    face = (np.linalg.norm(f['nf'] - [0., 1., 0.], axis=1) < 1e-12)
    interior_vertex = np.all(face[t['ef']], axis=1)
    flat_vertices = []
    for i in range(len(mesh.xyz)):
        incident = np.flatnonzero(np.any(mesh.faces == i, axis=1))
        if len(incident) == 4 and np.all(face[incident]) and np.ptp(f['sf'][incident]) < 1e-12:
            flat_vertices.append(i)
    assert flat_vertices
    edges = np.flatnonzero(interior_vertex & (np.abs(f['se'] - 1/6) < 1e-12))
    vertices = np.asarray(flat_vertices)
    nv, ne = len(mesh.xyz), len(t['edges'])
    face_ids = np.flatnonzero(face & (np.abs(f['sf'] - 1/6) < 1e-12))
    indices = np.concatenate([vertices, nv+edges, nv+ne+face_ids])
    # Constant scalar .8, same scale 1/6: completed-face coupling contributes
    # half the edge offset and 1/degree of the vertex offset.
    expected = np.tile([0., .8/6, 0.], (len(indices), 1))
    np.testing.assert_allclose(out.xyz[indices] - neutral.xyz[indices], expected, atol=8e-16, rtol=0.)
    assert metadata['coherence_scope'].startswith('flat regular-scale')
    assert np.all(state['resolved_w3'] == 0) and np.all(state['resolved_w4'] == 0)


def test_signed_pooling_has_no_direct_outside_activation_and_is_not_role_as_class():
    mesh, e4, e3 = parent_inputs()
    before = mesh.xyz.copy()
    controls, state = fold.resolved_fields(mesh, e4, e3, 'ROLE_CURVATURE')
    t = topology(mesh); scalar = state['face_scalar']
    assert np.any(scalar > 0) and np.any(scalar < 0)
    assert np.all(scalar[state['input_face_support'] == 0] == 0)
    assert np.array_equal(controls['we'], .5*scalar[t['ef']].mean(axis=1))
    independent_vertex = np.array([scalar[np.any(mesh.faces == i, axis=1)].mean() for i in range(len(mesh.xyz))])
    np.testing.assert_allclose(controls['wp'], (1-1/t['degree'])*independent_vertex, atol=2e-16, rtol=0.)
    changed_roles = deepcopy(e3)
    active = changed_roles['face_event_ids'] > 0
    changed_roles['face_roles'][active] = 3 - changed_roles['face_roles'][active]
    other, _ = fold.resolved_fields(mesh, e4, changed_roles, 'ROLE_CURVATURE')
    assert np.max(np.abs(other['wf'] - controls['wf'])) > .01
    # Anatomical roles affect one mode's gain, never the actual point classes.
    for mode in ('COHERENT', 'DIRECTIONAL'):
        a = fold.resolved_fields(mesh, e4, e3, mode)[0]
        b = fold.resolved_fields(mesh, e4, changed_roles, mode)[0]
        assert all(np.array_equal(a[k], b[k]) for k in fold.WEIGHTS)
    assert np.array_equal(mesh.xyz, before)


def test_scalar_geometry_signals_ignore_face_start_and_oriented_reflection():
    mesh, e4, e3 = parent_inputs()
    _, state = fold.resolved_fields(mesh, e4, e3, 'ROLE_CURVATURE')
    shifted = deepcopy(mesh); shifted.faces = np.roll(mesh.faces, 1, axis=1)
    _, other = fold.resolved_fields(shifted, e4, e3, 'ROLE_CURVATURE')
    for key in ['face_phase', 'face_band', 'face_bending', 'face_planarity', 'face_role_gain', 'face_scalar']:
        # Cyclic reduction order changes centroids by floating-point roundoff.
        np.testing.assert_allclose(other[key], state[key], atol=8e-15, rtol=0.)
    # Explicit point reflection plus winding reversal retains the scalar field.
    reflected = deepcopy(mesh); reflected.xyz[:, 0] *= -1.; reflected.faces = reflected.faces[:, ::-1]
    mirrored_source = deepcopy(e3); mirrored_source['mirror_face_signs'][:, 0] *= -1
    _, mirrored = fold.resolved_fields(reflected, e4, mirrored_source, 'ROLE_CURVATURE')
    for key in ['canonical_face_centroids', 'face_phase', 'face_band', 'face_bending', 'face_planarity', 'face_scalar']:
        np.testing.assert_allclose(mirrored[key], state[key], atol=8e-15, rtol=0.)


def test_quad_triangle_perimeter_max_is_invariant_and_not_quad_perimeter():
    points = np.array([[[0., 0., 0.], [2., 0., 0.], [2., 1., .3], [0., 1., 0.]]])
    ratios = []
    for k in range(4):
        p = np.roll(points[0], -k, axis=0)
        n = np.cross(p[1]-p[0], p[2]-p[0]); n /= np.linalg.norm(n)
        perimeter = np.linalg.norm(p[1]-p[0])+np.linalg.norm(p[2]-p[1])+np.linalg.norm(p[0]-p[2])
        ratios.append(abs((p[3]-p[0])@n)/perimeter)
    expected = max(ratios)
    assert np.isclose(fold.quad_planarity(points)[0], expected, rtol=0., atol=1e-16)
    for shift in range(4):
        assert np.array_equal(fold.quad_planarity(np.roll(points, shift, axis=1)), fold.quad_planarity(points))
    reflected = points[:, ::-1].copy(); reflected[:, :, 0] *= -1
    assert np.array_equal(fold.quad_planarity(reflected), fold.quad_planarity(points))
    with pytest.raises(ValueError): fold.quad_planarity(np.zeros((1, 4, 3)))


def test_native_step_reflection_and_topology_follow_actual_source_ids():
    from scipy.spatial import cKDTree
    mesh, e4, e3 = parent_inputs()
    before = [a.copy() for a in (mesh.xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors)]
    for mode in fold.MODES:
        out, metadata, state = fold.build(mesh, e4, e3, mode)
        assert out.generation == 5 and out.surface == 'mean'
        t = topology(out)
        assert len(out.xyz)-len(t['edges'])+len(out.faces) == 2
        assert np.isfinite(out.xyz).all() and len(np.unique(out.faces)) == len(out.xyz)
        for axis in (0, 1):
            sign = np.ones(3); sign[axis] = -1.
            distance, pair = cKDTree(out.rest).query(out.rest*sign)
            assert distance.max() < 1e-12
            np.testing.assert_allclose(out.xyz, out.xyz[pair]*sign, atol=2e-15, rtol=0.)
            assert np.array_equal(fixtures.growth._canonical_polygons(out.faces),
                fixtures.growth._canonical_polygons(pair[out.faces[:, ::-1]]))
        assert metadata['phase_diagnostics']['physical_wavelength'] == .35
        assert np.all(state['resolved_w1'] == 0) and np.all(state['resolved_w2'] == 0)
    for a, b in zip(before, (mesh.xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors)):
        assert np.array_equal(a, b)


@pytest.mark.parametrize('bad', ['frame', 'roles', 'signs', 'parent', 'generation'])
def test_missing_actual_inputs_are_rejected_without_synthetic_fallback(bad):
    mesh, e4, e3 = parent_inputs()
    if bad == 'frame': del e3['inherited_root_pca_major']
    elif bad == 'roles': e3['face_roles'][:] = 0
    elif bad == 'signs': e3['mirror_face_signs'][0, 0] = 0
    elif bad == 'parent': e4['parent_face'] = e4['parent_face'][:-1]
    elif bad == 'generation': mesh.generation = 5
    with pytest.raises(ValueError): fold.build(mesh, e4, e3, 'DIRECTIONAL')
