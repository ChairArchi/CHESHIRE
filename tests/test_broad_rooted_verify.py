"""Small rooted-pass corruption/rounding cases; no actual pilot replay."""
from pathlib import Path
import copy
import importlib.util

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location('tested_broad_rooted_verify',
    Path(__file__).resolve().parents[1]/'experiments/broad_shoulder_folds_20261012/verify_fans.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def test_source_receipt_pass_cannot_hide_changed_actual_positions():
    xyz = np.array([[1., 0., 0.], [1., .2, 1.]])
    digest = verify.finish.array_hash(xyz)
    generation = dict(checks=dict(passed=True, control_xyz_sha256=digest))
    parent = dict(passed=True, final_control_xyz_sha256=digest, generation_json_sha256='saved-generation')
    assert verify.source_identity(xyz, generation, parent, 'saved-generation') == digest
    changed = xyz.copy(); changed[1, 2] += .001
    with pytest.raises(ValueError, match='Actual incoming broad'):
        verify.source_identity(changed, generation, parent, 'saved-generation')
    with pytest.raises(ValueError, match='Actual incoming broad'):
        verify.source_identity(xyz, generation, parent, 'different-generation')


def test_one_g6_field_pass_cannot_be_reported_as_another_subdivision_generation():
    recipe = {'example': 'same on both inputs'}
    metadata = dict(input_case='SPAN', candidate='ROOTED_FANS', recipe=recipe,
        output_generation=6, added_subdivision_passes=0, added_surface_field_passes=1,
        added_mandelbulb_evaluations=0, checks=dict(passed=True))
    verify.field_pass_identity(metadata, 'SPAN', recipe)
    for key, value in [('output_generation', 7), ('added_subdivision_passes', 1),
            ('added_surface_field_passes', 2), ('added_mandelbulb_evaluations', 1)]:
        changed = copy.deepcopy(metadata); changed[key] = value
        with pytest.raises(ValueError, match='exactly one non-bulb'):
            verify.field_pass_identity(changed, 'SPAN', recipe)


def test_requested_and_rounded_actual_delta_are_distinct_and_both_replayed():
    source = np.ones((3, 3))
    requested = np.zeros_like(source); requested[1] = [.01, -.03, .02]
    final = source+requested
    actual = final-source
    assert not np.array_equal(requested, actual)
    weight, ends = np.array([0., 1., 0.]), np.array([True, False, True])
    receipt = verify.exact_surface_pass(source, requested, actual, final, weight, ends)
    assert receipt['passed'] and receipt['requested_minus_actual_maximum'] > 0.
    with pytest.raises(ValueError, match='Saved actual delta'):
        verify.exact_surface_pass(source, requested, requested, final, weight, ends)


def test_final_control_tamper_is_not_hidden_by_consistent_actual_delta():
    source = np.ones((3, 3))
    requested = np.zeros_like(source); requested[1, 0] = .02
    changed = source+requested; changed[1, 0] = np.nextafter(changed[1, 0], np.inf)
    with pytest.raises(ValueError, match='source plus requested'):
        verify.exact_surface_pass(source, requested, changed-source, changed,
            np.array([0., 1., 0.]), np.array([True, False, True]))


def test_guarded_region_remains_exact_without_inheriting_the_old_total_cap():
    source = np.zeros((3, 3))
    requested = np.zeros_like(source); requested[1, 0] = .70
    weight, ends = np.array([0., 1., 0.]), np.array([True, False, True])
    receipt = verify.exact_surface_pass(source, requested, requested, source+requested, weight, ends)
    assert receipt['maximum_actual_added_shift'] == .70 and receipt['total_cap_applied'] is False
    for vertex, expected in [(0, 'weight-zero'), (2, 'fixed-end')]:
        bad = requested.copy(); bad[vertex, 0] = np.nextafter(0., 1.)
        test_weight = weight.copy()
        if vertex == 2:
            test_weight[vertex] = 1.
        with pytest.raises(ValueError, match=expected):
            verify.exact_surface_pass(source, bad, bad, source+bad, test_weight, ends)
    bad = requested.copy(); bad[1, 0] = np.nan
    with pytest.raises(ValueError, match='finite rooted-pass'):
        verify.exact_surface_pass(source, bad, bad, source+bad, weight, ends)


def test_inventory_cannot_silently_accept_span_without_counter(monkeypatch):
    root, parent = Path('fixture-fans'), Path('fixture-broad')
    monkeypatch.setattr(Path, 'is_file', lambda path: 'COUNTER' not in path.parts)
    with pytest.raises(ValueError, match='COUNTER'):
        verify.inventory(root, parent)


def test_authored_root_match_does_not_replace_actual_curve_triangle_provenance():
    xyz = np.array([[1., 0., 0.], [1., 1., 0.], [1., 0., 1.]])
    faces = np.array([[0, 1, 2]])
    chart = np.array([[.2, 1., 0.], [.5, 1., 1.], [.8, 1., 0.]])
    bary = np.array([[[.2, .3, .5], [.3, .3, .4], [.4, .3, .3]]])
    uv = np.column_stack([chart[:, 0], np.arctan2(chart[:, 2], chart[:, 1])])
    expected = dict(surface_uv=bary@uv, root_u=np.array([.5]), inherited_root_u=np.array([.5]),
        root_attachment_max_error=np.array(0.))
    curves = dict(expected, source_uv=expected['surface_uv'], source_xyz=bary@xyz,
        source_triangle_ids=np.zeros((1, 3), dtype=int), source_barycentric=bary,
        incoming_generation=np.array(6), incoming_control_xyz_sha256=np.array('actual-source-hash'))
    assert verify.verify_curve_evidence(xyz, faces, chart, curves, expected, 'actual-source-hash')['passed']
    # Matching authored root coordinates do not rescue invented world geometry.
    changed = dict(curves, source_xyz=curves['source_xyz']+np.array([0., 0., .01]))
    with pytest.raises(ValueError, match='Native sample XYZ'):
        verify.verify_curve_evidence(xyz, faces, chart, changed, expected, 'actual-source-hash')
    changed = dict(curves, inherited_root_u=np.array([.51]))
    with pytest.raises(ValueError, match='rooted curve replay'):
        verify.verify_curve_evidence(xyz, faces, chart, changed, expected, 'actual-source-hash')
    with pytest.raises(ValueError, match='source G6 identity'):
        verify.verify_curve_evidence(xyz, faces, chart, curves, expected, 'another-source-hash')
