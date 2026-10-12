"""Small actual-geometry corruption checks; no pilot generation or rendering."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location('tested_broad_shoulder_verify',
    Path(__file__).resolve().parents[1]/'experiments/broad_shoulder_folds_20261012/verify.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def test_baseline_pass_flag_does_not_hide_actual_xyz_corruption():
    xyz = np.array([[1., 0., 0.], [1., 0., 1.]])
    digest = verify.finish.array_hash(xyz)
    generation = dict(checks=dict(passed=True, control_xyz_sha256=digest))
    main = dict(passed=True, control_xyz_sha256=digest)
    assert verify.baseline_identity(xyz, generation, main) == digest
    changed = xyz.copy(); changed[1, 0] += .001
    with pytest.raises(ValueError, match='Actual BASELINE'):
        verify.baseline_identity(changed, generation, main)


def test_source_samples_must_belong_to_actual_native_triangles_and_uv():
    xyz = np.array([[1., 0., 0.], [1., 1., 0.], [1., 0., 1.]])
    faces = np.array([[0, 1, 2]])
    chart = np.array([[.2, 1., 0.], [.5, 1., 1.], [.8, 1., 0.]])
    bary = np.array([[.2, .3, .5]])
    uv = np.column_stack([chart[:, 0], np.arctan2(chart[:, 2], chart[:, 1])])
    records = dict(source_triangle_ids=np.array([0]), source_barycentric=bary,
        source_xyz=bary@xyz, source_uv=bary@uv)
    assert verify.native_sample_provenance(xyz, faces, chart, records)['passed']
    changed = dict(records, source_xyz=records['source_xyz']+np.array([0., 0., .01]))
    with pytest.raises(ValueError, match='Native sample XYZ'):
        verify.native_sample_provenance(xyz, faces, chart, changed)
    changed = dict(records, source_uv=records['source_uv']+np.array([.01, 0.]))
    with pytest.raises(ValueError, match='material UV'):
        verify.native_sample_provenance(xyz, faces, chart, changed)


def test_delta_checks_actual_vector_cap_and_exact_unchanged_controls():
    reference = np.zeros((3, 3))
    baseline = np.array([[.02, 0., 0.], [0., 0., 0.], [.03, 0., 0.]])
    control = baseline.copy(); control[1] = [.50, .50, 0.]
    weight, ends = np.array([0., 1., 0.]), np.array([1, 0, 1], dtype=bool)
    delta = control-reference
    # No inherited .30/.45 limit applies when this experiment has no cap.
    assert verify.actual_delta_locality(control, reference, delta, baseline, weight, ends)['passed']
    with pytest.raises(ValueError, match='configured experiment cap'):
        verify.actual_delta_locality(control, reference, delta, baseline, weight, ends, maximum=.65)
    changed = control.copy(); changed[0, 0] = np.nextafter(changed[0, 0], np.inf)
    with pytest.raises(ValueError, match='Weight-zero'):
        verify.actual_delta_locality(changed, reference, changed-reference, baseline, weight, ends)
    bad_delta = delta.copy(); bad_delta[1, 0] += .001
    with pytest.raises(ValueError, match='Saved delta'):
        verify.actual_delta_locality(control, reference, bad_delta, baseline, weight, ends)


def test_native_fan_guard_is_checked_as_actual_geometry():
    baseline = np.array([[1., 0., 0.], [0., 1., 0.], [.5, .5, 0.]])
    current = baseline.copy(); current[-1, 2] += .001
    guard = dict(outside=np.array([0, 0, 1], dtype=bool))
    with pytest.raises(ValueError, match='Actual native outside'):
        verify.actual_native_guards(current, baseline, guard)


def test_actual_xy_geometry_symmetry_cannot_be_replaced_by_unchanged_chart_receipts():
    xyz = np.array([[-1., -1., 0.], [1., -1., 0.], [1., 1., 0.], [-1., 1., 0.]])
    pairs = [np.array([1, 0, 3, 2]), np.array([3, 2, 1, 0])]
    receipts = {axis: dict(material_pair_max_error=0., pair_involution=True) for axis in ('X', 'Y')}
    assert all(r['passed'] for r in verify.previous.coordinate_symmetry(xyz, pairs, receipts).values())
    changed = xyz.copy(); changed[0, 2] += .001
    with pytest.raises(ValueError, match='actual native coordinates'):
        verify.previous.coordinate_symmetry(changed, pairs, receipts)


def test_incoming_frame_pool_cannot_self_justify_against_its_saved_normals():
    operators = verify.load_module('tested_broad_frame_pool',
        Path(__file__).resolve().parents[1]/'experiments/broad_shoulder_folds_20261012/folds.py')
    xyz = np.array([[1., 0., 0.], [1., 1., 0.], [1., 1., 1.], [1., 0., 1.]])
    chart = np.array([[.2, np.cos(.9), np.sin(.9)], [.2, np.cos(1.5), np.sin(1.5)],
        [.8, np.cos(1.5), np.sin(1.5)], [.8, np.cos(.9), np.sin(.9)]])
    mesh = SimpleNamespace(xyz=xyz, faces=np.array([[0, 1, 2, 3]]), surface='mean', generation=4)
    native = SimpleNamespace(xyz=np.vstack([xyz, xyz.mean(axis=0)]),
        faces=np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]))
    pchart = np.vstack([chart, chart.mean(axis=0)])
    uv = np.column_stack([pchart[:, 0], np.arctan2(pchart[:, 2], pchart[:, 1])])
    fraction = np.linspace(.05, .95, 5)
    fan = np.array([.2, .4, .6])[:, None]*np.ones((3, 5))
    bary = np.stack([(1.-fan)*(1.-fraction), (1.-fan)*fraction, fan], axis=-1)
    ids = np.zeros((3, 5), dtype=int)
    sampled = np.einsum('...i,...ij->...j', bary, native.xyz[native.faces[ids]])
    sample_uv = np.einsum('...i,...ij->...j', bary, uv[native.faces[ids]])
    parameter = sample_uv[:, 0, 0]
    patch = dict(parameter=parameter, surface_uv=sample_uv)
    normals = np.tile([1., 0., 0.], (3, 5, 1))
    arc = np.c_[np.zeros(3), np.cumsum(np.linalg.norm(np.diff(sampled, axis=1), axis=2), axis=1)]
    pooled, transverse, axial, lengths = operators.pool_normals(parameter, arc, normals)
    frame = dict(parameter=parameter, source_uv=sample_uv, source_xyz=sampled,
        source_triangle_ids=ids, source_barycentric=bary, actual_triangle_normals=normals,
        actual_transverse_arc=arc, transverse_weights=transverse, axial_weights=axial,
        pooled_normals=pooled, pooled_vector_lengths=lengths, incoming_generation=np.array(4),
        incoming_control_xyz_sha256=np.array(verify.finish.array_hash(xyz)))
    _, receipt = verify.verify_incoming_frame(mesh, chart, native, frame, patch, 4, operators, operators.RECIPE)
    assert receipt['passed']
    # A unit but incorrect saved pool is rejected against actual triangle normals.
    changed = dict(frame, pooled_normals=np.tile([0., 1., 0.], (3, 1)))
    with pytest.raises(ValueError, match='pooled_normals'):
        verify.verify_incoming_frame(mesh, chart, native, changed, patch, 4, operators, operators.RECIPE)
    changed = dict(frame, actual_transverse_arc=arc.copy())
    changed['actual_transverse_arc'][0, 2] += .01
    with pytest.raises(ValueError, match='actual_transverse_arc'):
        verify.verify_incoming_frame(mesh, chart, native, changed, patch, 4, operators, operators.RECIPE)
    changed = dict(frame, transverse_weights=np.full_like(transverse, np.nan))
    with pytest.raises(ValueError, match='nonfinite'):
        verify.verify_incoming_frame(mesh, chart, native, changed, patch, 4, operators, operators.RECIPE)
