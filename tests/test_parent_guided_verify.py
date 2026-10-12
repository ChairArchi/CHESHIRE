"""Small corruption checks; no G06 generation, replay, atlas, or rendering."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location('tested_parent_guided_verify',
    Path(__file__).resolve().parents[1]/'experiments/parent_guided_detail_20261012/verify.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def test_missing_expected_counter_or_mode_cannot_pass_inventory(tmp_path):
    for case in verify.CASES:
        (tmp_path/case).mkdir()
        for name in ('SUMMARY.json', 'actual_parent_0.npz', 'actual_parent_1.npz',
                'common_carrier_relaxation.npz', 'guided_colonies.npz'):
            (tmp_path/case/name).write_bytes(b'placeholder')
        for mode in verify.MODES:
            folder = tmp_path/mode/case/'G06'
            folder.mkdir(parents=True)
            for name in ('generation.json', 'control_quad.npz', 'geometry.npz', 'operation_fields.npz'):
                (folder/name).write_bytes(b'placeholder')
    (tmp_path/'RECIPE.json').write_bytes(b'{}')
    verify.inventory(tmp_path)
    (tmp_path/'FLOW_CHAIN/COUNTER/G06/geometry.npz').unlink()
    with pytest.raises(ValueError, match='SPAN/COUNTER'):
        verify.inventory(tmp_path)


def test_delta_corruption_and_inactive_end_change_are_rejected():
    reference = np.array([[1., 0., 0.], [1., 0., 1.], [1., 0., 2.]])
    baseline = reference+np.array([[.02, 0., 0.], [.1, 0., 0.], [.03, 0., 0.]])
    chart = np.array([[0., 1., 0.], [.5, 1., 0.], [1., 1., 0.]])
    actual = baseline.copy(); actual[1, 0] += .05
    operation = dict(delta=actual-reference, changed_region=np.array([0, 1, 0]))
    assert verify.check_actual_delta(actual, reference, operation, baseline, chart)['operation_delta_exact']
    corrupted = dict(operation, delta=operation['delta'].copy())
    corrupted['delta'][1, 0] += .001
    with pytest.raises(ValueError, match='operation delta'):
        verify.check_actual_delta(actual, reference, corrupted, baseline, chart)
    bad_end = actual.copy(); bad_end[0, 0] += .001
    # Even falsely labelling every point active cannot override fixed ends.
    bad_operation = dict(delta=bad_end-reference, changed_region=np.ones(3, dtype=np.uint8))
    with pytest.raises(ValueError, match='inactive ends'):
        verify.check_actual_delta(bad_end, reference, bad_operation, baseline, chart)


def test_guided_centres_must_belong_to_meso_carrier_not_common_reference():
    common = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    meso = common+np.array([0., 0., .1])
    faces = np.array([[0, 1, 2]])
    bary = np.array([[.2, .3, .5]])
    centres = bary@meso
    colonies = dict(source_control_generation=np.array(6),
        source_carrier_xyz_sha256=np.array(verify.finish.array_hash(meso)),
        source_triangle_ids=np.array([0]), source_barycentric=bary,
        source_xyz=centres.copy(), centres=centres.copy(), levels=np.array([0]),
        primary_source_triangle_ids=np.array([0]), primary_source_barycentric=bary.copy(),
        primary_source_xyz=centres.copy(), frame_source_generation=np.array(3))
    assert verify.guided_source_provenance(colonies, SimpleNamespace(xyz=meso, faces=faces), meso)['passed']
    with pytest.raises(ValueError, match='meso carrier triangles'):
        verify.guided_source_provenance(colonies, SimpleNamespace(xyz=common, faces=faces), meso)
    wrong = dict(colonies, centres=centres+np.array([0., 0., .01]))
    with pytest.raises(ValueError, match='meso carrier triangles'):
        verify.guided_source_provenance(wrong, SimpleNamespace(xyz=meso, faces=faces), meso)
