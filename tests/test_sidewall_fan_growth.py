"""Small actual Task32 parent/child fixtures; no WALL arrays or rendering."""
from pathlib import Path
import copy
import importlib.util

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_sidewall_fan',
    REPO/'experiments/sidewall_fan_growth_20261013/patch_sidewall.py')
fan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fan)
FIXTURE_SPEC = importlib.util.spec_from_file_location('sidewall_small_box_fixture',
    REPO/'tests/test_connected_fold_growth.py')
fixtures = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixtures)


@pytest.fixture(scope='module')
def built():
    source, chart = fixtures.box_grid(24, 96)
    parent = fan.growth.build(source, chart, 'ROOT_ONLY')
    out = fan.build(parent[0], parent[1], parent[3], parent[2])
    return parent, out


def test_actual_sidewall_sweeps_preserve_closed_one_body_and_exact_identity_reflection(built):
    parent, (mesh, chart, events, evidence) = built
    accepted = [e for e in events if e['status'] == 'accepted']
    assert len(accepted) == 3
    assert np.array_equal(evidence['accepted_event_counts_by_level'], [1, 3, 0])
    assert [e['event_id'] for e in events] == [2, 3, 4]
    assert mesh.generation == 3 and mesh.surface == 'mean'
    assert evidence['subdivision_passes_added'] == 0
    checks = fan.growth._final_checks(mesh, evidence)
    assert checks['components'] == 1 and checks['euler'] == 2
    fixtures.assert_vertex_link_cycles(mesh)
    assert len(np.unique(chart, axis=0)) < len(chart)
    for name, axis in (('x', 0), ('y', 1)):
        pair = evidence['mirror_'+name+'_vertex_pairs']
        sign = np.ones(3); sign[axis] = -1.
        assert np.array_equal(mesh.xyz, mesh.xyz[pair]*sign)
        fpair = evidence['mirror_'+name+'_face_pairs']
        assert np.array_equal(fan._oriented_rows(mesh.faces[fpair]),
            fan._oriented_rows(pair[mesh.faces[:, ::-1]]))


def test_real_parent_wall_ownership_rows_and_absolute_height_recipe(built):
    parent, (_, _, events, evidence) = built
    pe = parent[3]
    rows = evidence['parent_root_sidewall_row']
    for event in events:
        assert event['status'] == 'accepted'
        key = f'event_{event["event_id"]:03d}_'
        assert event['level'] == 1 and event['parent_event_id'] == 1 and event['parent_role'] == 1
        assert np.all(evidence[key+'selected_parent_roles'] == 1)
        assert np.all(evidence[key+'selected_parent_event_ids'] == 1)
        original = evidence[key+'selected_parent_source_face_ids']
        assert np.all(pe['face_roles'][original] == 1)
        assert np.all(pe['face_event_ids'][original] == 1)
        assert set(rows[original]) == {1, 2}
        assert np.allclose(event['geometry']['actual_heights'],
            np.asarray(fan.RECIPE['heights_root_radius'])*event['root_radius'], atol=1e-15, rtol=0.)
        radius = event['geometry']['area_radius']
        assert np.isclose(radius, event['child_radius'], atol=1e-15, rtol=0.)
        assert np.allclose(np.asarray(event['geometry']['spec']['heights'])*radius,
            event['geometry']['actual_heights'], atol=1e-15, rtol=0.)
        diagnostics = event['proposal']['normal_diagnostics']
        assert 0. < diagnostics['normal_coherence'] <= 1.+1e-12
        actual = fan._normal_diagnostics(parent[0], original, pe['root_pca_normal'])
        assert np.isclose(actual['normal_coherence'], diagnostics['normal_coherence'], atol=1e-15, rtol=0.)
        assert 0. <= diagnostics['normal_spread_max_degrees'] <= 180.
    assert evidence['child_pair_normal_angles_degrees'].shape == (3, 3)


def test_parent_cap_input_and_old_provenance_stay_exact(built):
    parent, (mesh, chart, events, evidence) = built
    source, source_chart, root_events, pe = parent
    parent_again = fan.growth.build(*fixtures.box_grid(24, 96), 'ROOT_ONLY')
    assert np.array_equal(source.xyz, parent_again[0].xyz)
    assert np.array_equal(source.faces, parent_again[0].faces)
    assert np.array_equal(source_chart, parent_again[1])
    assert root_events == parent_again[2]
    for key, value in pe.items():
        if key.startswith('event_001_') or key.startswith('root_pca_'):
            assert np.array_equal(value, evidence['inherited_'+key])
    cap = np.unique(mesh.faces[(evidence['face_event_ids'] == 1) & (evidence['face_roles'] == 2)])
    assert np.array_equal(mesh.xyz[cap], source.xyz[evidence['vertex_parent_source_ids'][cap]])
    sourcefaces = evidence['face_parent_source_ids']
    old = evidence['face_event_ids'] <= 1
    assert np.array_equal(evidence['face_event_ids'][old], pe['face_event_ids'][sourcefaces[old]])
    assert np.array_equal(evidence['face_roles'][old], pe['face_roles'][sourcefaces[old]])
    # Older source IDs remain canonical associations, distinct from actual opposite-quarter IDs.
    assert np.any(evidence['face_source_ids'] != evidence['face_parent_source_ids'])
    assert np.all(mesh.classes[evidence['vertex_birth_event_ids'] > 0] == -1)


def test_invalid_parent_pair_map_or_cap_ancestry_is_rejected(built):
    parent, _ = built
    source, chart, events, pe = parent
    broken = copy.deepcopy(pe)
    broken['mirror_x_vertex_pairs'][0] = broken['mirror_x_vertex_pairs'][1]
    with pytest.raises(ValueError, match='involution|reflection'):
        fan.build(source, chart, broken, events)
    broken = copy.deepcopy(pe)
    selected = np.flatnonzero((broken['face_event_ids'] == 1) & (broken['face_roles'] == 1))[0]
    broken['face_roles'][selected] = 2
    with pytest.raises(ValueError, match='exactly all rings'):
        fan.build(source, chart, broken, events)


def test_empty_sectors_reject_explicitly_without_fallback_or_parent_change(built, monkeypatch):
    parent, _ = built
    recipe = copy.deepcopy(fan.RECIPE)
    recipe['beta_halfwidth'] = 1e-12
    monkeypatch.setattr(fan, 'RECIPE', recipe)
    source, chart, events, pe = parent
    out, out_chart, newevents, evidence = fan.build(source, chart, pe, events)
    assert len(newevents) == 3 and all(e['status'] == 'rejected' and e['reason'] for e in newevents)
    assert np.array_equal(evidence['accepted_event_counts_by_level'], [1, 0, 0])
    assert np.array_equal(out.xyz, source.xyz)
    assert np.array_equal(out.faces, source.faces)
    assert np.array_equal(out_chart, chart)
