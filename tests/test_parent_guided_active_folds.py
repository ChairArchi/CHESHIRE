"""Small field/guard/symmetry counterexamples; no saved G6 body is generated."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_active_folds',
    ROOT/'experiments/parent_guided_detail_20261012/active_folds.py')
active = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(active)


@pytest.fixture
def parent():
    parameter = np.linspace(.2, .8, 9)
    fraction = np.linspace(0., 1., 129)
    cross = np.broadcast_to(.20+.60*fraction, (len(parameter), len(fraction)))
    uv = np.stack([np.broadcast_to(parameter[:, None], cross.shape), cross], axis=2)
    return dict(parameter=parameter, parent_shoulder_uv=uv,
        parent_shoulder_arc=np.broadcast_to(.30*fraction, cross.shape),
        parent_shoulder_width=np.full(len(parameter), .20),
        parent_tangent=np.tile([0., 0., 1.], (len(parameter), 1)))


def chart(q, u):
    q, u = np.broadcast_arrays(q, u)
    theta = .20+.60*u.ravel()
    return np.column_stack([.50+.30*q.ravel(), np.cos(theta), np.sin(theta)])


def test_branches_join_the_trunk_continuously_and_split_at_different_stations():
    for index, start in enumerate(active.RECIPE['branch_starts'], 1):
        q = np.array([start-1e-5, start, start+1e-5])
        curves, gates = active.curves(q)
        assert np.allclose(curves[index], curves[0], atol=1e-12, rtol=0)
        assert gates[index, 1] == 0.
    curves, _ = active.curves(np.array([.90]))
    assert curves[1, 0]-curves[0, 0] > .20
    assert curves[2, 0]-curves[0, 0] < -.17
    assert active.RECIPE['branch_starts'][0] != active.RECIPE['branch_starts'][1]


def test_active_signed_bands_use_actual_normals_and_reflect_equivariantly(parent):
    material = chart(np.linspace(-.90, .90, 41)[:, None], np.linspace(.26, .99, 97)[None, :])
    normal = np.tile([1., 0., 0.], (len(material), 1))
    delta, fields = active.normal_delta(material, normal, parent, [parent], 4)
    assert fields['height'].max() > .10
    assert fields['height'].min() < -.02
    assert np.array_equal(delta[:, 0], fields['height'])
    assert np.array_equal(delta[:, 1:], np.zeros_like(delta[:, 1:]))
    for signs in ([1., -1., 1.], [1., 1., -1.], [1., -1., -1.]):
        other_chart = material*np.asarray(signs)
        world_sign = np.array([signs[1], signs[2], 1.])
        other, _ = active.normal_delta(other_chart, normal*world_sign, parent, [parent], 4)
        assert np.array_equal(other, delta*world_sign)
    small, _ = active.normal_delta(material, normal, parent, [parent], 5)
    assert 0. < np.linalg.norm(small, axis=1).max() < np.linalg.norm(delta, axis=1).max()
    with pytest.raises(ValueError, match='degenerate frame'):
        active.normal_delta(material, np.tile([0., 0., 1.], (len(material), 1)), parent, [parent], 4)
    bounded = active._bound(np.array([[0., 0., 0.], [0., .60, .80]]), .45)
    assert np.array_equal(bounded[0], [0., 0., 0.])
    assert np.isclose(np.linalg.norm(bounded[1]), .45)


def test_all_parent_cores_and_endpoints_exclude_new_active_changes(parent):
    other = {key: np.array(value, copy=True) for key, value in parent.items()}
    other['parent_shoulder_uv'][:, :, 1] += .33
    material = chart(np.array([0., 0., -2., 2.]), np.array([.55, .0, .55, .55]))
    alone = active.ownership(material, parent, [parent])
    together = active.ownership(material, parent, [parent, other])
    assert alone['weight'][0] > 0.
    assert together['weight'][0] == 0.
    assert together['protected'][0]
    assert np.array_equal(together['weight'][1:], [0., 0., 0.])
    assert together['ends'][-2:].all()


def test_outside_native_fan_guard_restores_every_incident_control(parent):
    material = chart(np.zeros(4), [0., 0., 0., .60])
    mesh = SimpleNamespace(faces=np.array([[0, 1, 2, 3]]), surface='mean')
    assert active.ownership(material, parent, [parent])['weight'][-1] > 0.
    weight, _, fan = active._restore_guarded_weights(mesh, material, parent, [parent], active.RECIPE)
    assert fan['weight'][0] == 0.
    assert np.array_equal(weight, np.zeros(4))


def test_actual_xy_native_symmetry_rejects_positions_and_winding_corruption():
    xyz = np.array([[-1., -1., 0.], [1., -1., 0.], [1., 1., 0.], [-1., 1., 0.]])
    material = np.column_stack([np.full(4, .5), xyz[:, :2]])
    mesh = SimpleNamespace(xyz=xyz, faces=np.array([[0, 1, 2, 3]]), surface='mean')
    native = SimpleNamespace(xyz=np.vstack([xyz, [0., 0., 0.]]),
        faces=np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]))
    for axis in (0, 1):
        assert active._native_axis_symmetry(mesh, material, native, axis)['passed']
    changed = native.xyz.copy(); changed[0, 1] += .01
    assert not active._native_axis_symmetry(mesh, material, SimpleNamespace(xyz=changed, faces=native.faces), 1)['passed']
    # Right and left side triangles are distinct partners under X reflection.
    winding = native.faces.copy(); winding[1] = winding[1, ::-1]
    check = active._native_axis_symmetry(mesh, material, SimpleNamespace(xyz=native.xyz, faces=winding), 0)
    assert not check['passed']
    assert not check['reflected_oriented_native_triangles_identical']
