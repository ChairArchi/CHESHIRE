"""Surface and generation contracts of the connected-patch pilot."""
from pathlib import Path
import importlib.util

import numpy as np
import trimesh

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('connected_study_test',
    REPO/'experiments/connected_fold_growth_20261012/study.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)
from cheshire.reference_subdivision import cube


def fixture():
    mesh = cube(2.)
    mesh.generation = 3
    chart = mesh.xyz.copy()
    chart[:, 0] = (mesh.xyz[:, 2]+1.)/2.
    chart[:, 1:] = mesh.xyz[:, :2]
    return mesh, chart


def test_neutral_step_really_changes_geometry_and_increments_G():
    mesh, chart = fixture()
    out, outchart, _ = study.refine(mesh, chart)
    assert out.generation == 4
    assert len(out.faces) == 4*len(mesh.faces)
    assert not np.array_equal(out.xyz[:len(mesh.xyz)], mesh.xyz)
    assert np.array_equal(outchart[:len(mesh.xyz)], chart)
    assert out.surface == 'mean'


def test_chart_is_linear_even_when_geometry_is_averaged():
    mesh, chart = fixture()
    out, outchart, state = study.refine(mesh, chart)
    edges = state['input_edges']
    expected = np.concatenate([chart, chart[edges].mean(1), chart[mesh.faces].mean(1)])
    assert np.array_equal(outchart, expected)
    assert not np.array_equal(out.xyz, outchart)


def test_mean_native_is_closed_oriented_single_body_without_orphans():
    mesh, _ = fixture()
    xyz, faces = study.native(mesh)
    physical = trimesh.Trimesh(xyz, faces, process=False)
    assert physical.is_watertight and physical.is_winding_consistent
    assert physical.body_count == 1
    assert physical.area_faces.min() > 0.
    assert len(np.unique(faces)) == len(xyz)
    assert np.array_equal(xyz[len(mesh.xyz):], mesh.xyz[mesh.faces].mean(1))
