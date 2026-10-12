"""Actual geometric carrier changes and hard native LR symmetry checks."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import trimesh

_path = Path(__file__).resolve().parents[1]/'experiments/fold_visible_gate_20261012/detail_finish.py'
_spec = importlib.util.spec_from_file_location('detail_finish_test_module', _path)
finish = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(finish)


def actual_fixture(case='SPAN'):
    return finish.t.load(finish.bulb.study.previous.SOURCES[case])


@pytest.mark.parametrize('case', ['SPAN', 'COUNTER'])
def test_streamed_normals_match_actual_native_angle_weighted_normals(case):
    mesh, _, _ = actual_fixture(case)
    native = finish.t.growth.native(mesh)
    actual = finish.stream_control_normals(native.xyz, native.faces[:, :3], len(mesh.xyz), chunk=701)
    expected = trimesh.Trimesh(native.xyz, native.faces[:, :3], process=False).vertex_normals[:len(mesh.xyz)]
    assert np.allclose(actual, expected, atol=1e-12, rtol=0.)


@pytest.mark.parametrize('case', ['SPAN', 'COUNTER'])
def test_carrier_relaxation_changes_real_xyz_with_bounded_shift_fixed_ends_and_symmetry(case):
    mesh, chart, _ = actual_fixture(case)
    original, faces, original_chart = mesh.xyz.copy(), mesh.faces.copy(), chart.copy()
    delta = finish.relax_carrier(mesh, chart)
    assert np.linalg.norm(delta, axis=1).max() > .005
    assert np.linalg.norm(delta, axis=1).max() <= finish.RELAXATION['maximum_carrier_shift']+1e-12
    fixed = (chart[:, 0] <= .1) | (chart[:, 0] >= .9)
    assert np.array_equal(mesh.xyz[fixed], original[fixed])
    assert np.array_equal(mesh.faces, faces) and np.array_equal(chart, original_chart)
    assert np.array_equal(mesh.xyz, original+delta)
    assert finish.native_lr_symmetry(mesh, chart)['passed']


@pytest.mark.parametrize('case', ['SPAN', 'COUNTER'])
def test_actual_native_symmetry_rejects_position_and_oriented_triangle_corruption(case):
    mesh, chart, _ = actual_fixture(case)
    native = finish.t.growth.native(mesh)
    triangles = native.faces[:, :3].copy()
    assert finish.native_lr_symmetry(mesh, chart, SimpleNamespace(xyz=native.xyz, faces=triangles))['passed']
    wrong = native.xyz.copy(); wrong[7, 0] += .01
    assert not finish.native_lr_symmetry(mesh, chart, SimpleNamespace(xyz=wrong, faces=triangles))['passed']
    triangles[5] = triangles[5, ::-1]
    result = finish.native_lr_symmetry(mesh, chart, SimpleNamespace(xyz=native.xyz, faces=triangles))
    assert result['actual_native_xyz_pair_max_error'] < 1e-9
    assert not result['reflected_oriented_native_triangle_sets_identical'] and not result['passed']


def test_memory_guard_rejects_insufficient_free_physical_memory(monkeypatch):
    monkeypatch.setattr(finish, 'memory_state', lambda: dict(available_physical=7_000_000_000))
    with pytest.raises(MemoryError, match='8 GB'):
        finish.memory_guard()
