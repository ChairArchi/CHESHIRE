"""Pure coordinate/curve counterexamples; no real G06 mesh is read/generated."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest


SPEC = importlib.util.spec_from_file_location('tested_broad_rooted_fans',
    Path(__file__).resolve().parents[1]/'experiments/broad_shoulder_folds_20261012/rooted_fans.py')
fans = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fans)


@pytest.fixture
def patch():
    parameter = np.linspace(.70, .87, 9)
    cross = np.linspace(.90, np.pi/2.-.005, 129)
    uv = np.stack(np.meshgrid(parameter, cross, indexing='ij'), axis=-1)
    fraction = np.linspace(0., 1., 129)
    return dict(parameter=parameter, surface_uv=uv,
        transverse_arc=(.76+.08*np.sin(np.linspace(0., np.pi, 9)))[:, None]*fraction[None]**1.1,
        physical_width=np.full(9, .65), axial_plateau_fraction=np.array(.6),
        transverse_fade_fraction=np.array(.12))


def material(q, u, patch):
    q, u = np.broadcast_arrays(np.asarray(q, float), np.asarray(u, float))
    parameter = patch['parameter'][0]+(q+1.)*.5*np.ptp(patch['parameter'])
    uv = fans.measure.uv_at_fraction(parameter, u, patch)
    return np.column_stack([uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])])


def test_nonuniform_primary_roots_and_child_roots_attach_to_their_parent(patch):
    bank = fans.definitions()
    evidence = fans.curve_evidence(patch)
    assert len(bank) == 12 and np.array_equal(evidence['levels'], [0]*6+[1]*6)
    assert np.array_equal(evidence['parent_ids'], [-1]*6+list(range(6)))
    assert evidence['root_attachment_max_error'] == 0.
    assert np.max(np.abs(evidence['root_u']-evidence['inherited_root_u'])) == 0.
    starts = np.array([item['start_q'] for item in bank[:6]])
    assert np.ptp(np.diff(starts)) > .05
    assert np.all(evidence['height_gate'][:, [0, -1]] == 0.)
    assert evidence['surface_uv'].shape == (12, 97, 2)
    for item in bank:
        assert item['start_q'] < item['end_q'] < 1.
        if item['level']:
            parent = bank[item['parent_id']]
            assert parent['start_q'] < item['start_q'] < parent['end_q']


def test_root_join_has_zero_additional_height_and_zero_transverse_turn_derivative():
    bank = fans.definitions()
    epsilon = 1e-6
    for item in bank:
        q = np.array([item['start_q'], item['start_q']+epsilon])
        centre, _, gate = fans.curve(q, item, bank=bank)
        inherited = (fans.root_centre(q) if item['level'] == 0 else
                     fans.curve(q, bank[item['parent_id']], bank=bank)[0])
        assert centre[0] == inherited[0] and gate[0] == 0.
        assert abs((centre[1]-inherited[1])/epsilon) < 1e-8
        assert gate[1]/epsilon < 1e-6


def test_actual_width_adapts_two_amplitude_scales_and_crossings_do_not_add(patch):
    chart = material(np.linspace(-.98, .98, 151)[:, None],
                     np.linspace(0., 1., 251)[None], patch)
    height, fields = fans.height(chart, patch)
    assert fields['primary_positive_height'].max() > .038
    assert 0.015 < fields['child_positive_height'].max() <= .016
    assert height.max() <= .040 and height.min() >= -.040*fans.RECIPE['groove_ratio']
    assert height.min() < -.005
    assert np.array_equal(fields['positive_height'],
                          np.maximum(fields['primary_positive_height'], fields['child_positive_height']))
    narrower = dict(patch, physical_width=np.full(9, .325))
    _, small = fans.height(chart, narrower)
    assert np.max(small['primary_positive_height']) <= .325*.060
    assert np.max(small['child_positive_height']) <= .325*.025
    assert np.all(small['primary_positive_height'] < fields['primary_positive_height']+1e-14)


def test_signed_grooves_do_not_cut_any_fully_active_ridge_or_the_trunk(patch):
    bank = fans.definitions()
    for item in bank:
        q = np.linspace(item['start_q']+.35*(item['end_q']-item['start_q']),
                        item['start_q']+.65*(item['end_q']-item['start_q']), 17)
        u, _, gate = fans.curve(q, item, bank=bank)
        assert np.all(gate == 1.)
        _, fields = fans.height(material(q, u, patch), patch)
        assert np.max(fields['negative_height']) < 1e-28
    q = np.linspace(-.98, .98, 101)
    _, fields = fans.height(material(q, fans.root_centre(q), patch), patch)
    assert np.array_equal(fields['negative_height'], np.zeros(len(q)))


def test_height_reflects_exactly_and_all_patch_boundaries_are_zero(patch):
    chart = material(np.linspace(-1., 1., 61)[:, None], np.linspace(0., 1., 101)[None], patch)
    height, fields = fans.height(chart, patch)
    for signs in ([1., -1., 1.], [1., 1., -1.], [1., -1., -1.]):
        other, other_fields = fans.height(chart*np.array(signs), patch)
        assert np.array_equal(other, height)
        assert np.array_equal(other_fields['patch_weight'], fields['patch_weight'])
    grid = height.reshape(61, 101)
    assert np.all(grid[[0, -1]] == 0.) and np.all(grid[:, [0, -1]] == 0.)
    outside = chart[:8].copy()
    outside[:, 0] = [.10, .30, .69, .70, .87, .88, .90, .95]
    outside_height, _ = fans.height(outside, patch)
    assert np.array_equal(outside_height, np.zeros(8))


def test_invalid_family_and_missing_actual_width_are_rejected(patch):
    with pytest.raises(ValueError, match='inside'):
        fans.definitions(dict(fans.RECIPE, primary_start_q=[-.74, -.51, -.22, .045, .31, .95]))
    with pytest.raises(ValueError, match='generation'):
        fans.height(material(0., .5, patch), patch, dict(fans.RECIPE, output_generation=7))
    with pytest.raises(ValueError, match='Actual measured'):
        fans.height(material(0., .5, patch), dict(patch, physical_width=np.zeros(9)))
