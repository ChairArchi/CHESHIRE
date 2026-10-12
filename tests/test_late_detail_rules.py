"""Small asymmetric CC fixtures; no frozen column geometry or rendering."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_late_detail_operator',
    REPO / 'experiments/late_detail_rules_20261013/late_operator.py')
late = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(late)
from cheshire.reference_subdivision import cube, fields, subdivide, topology  # noqa: E402


@pytest.fixture
def parent():
    source = cube(2.)
    source.xyz = source.xyz @ np.array([[1.2, .12, -.2], [.15, .85, .11], [.08, -.17, 1.4]])
    source.xyz[6] += [.29, -.13, .21]
    source.rest = source.xyz.copy()
    source.generation = 3
    g4, _, evidence = subdivide(source, {'weights': {}})
    owners = np.array([0, 0, 1, 2, 0, 0], np.int64)
    return g4, evidence, {'face_event_ids': owners}


def test_neutral_exact_and_sources_are_unchanged(parent):
    mesh, evidence, ownership = parent
    before = [a.copy() for a in (mesh.xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors)]
    expected, _, expected_state = subdivide(mesh, {'weights': {}})
    out, metadata, state = late.build(mesh, evidence, ownership, 'NEUTRAL')
    assert np.array_equal(out.xyz, expected.xyz)
    assert np.array_equal(out.faces, expected.faces)
    assert out.generation == 5 and out.surface == 'mean'
    assert metadata['eq4_eligible'] == len(mesh.faces)
    assert metadata['eq4_fallback'] == 0
    for key in expected_state:
        assert np.array_equal(state[key], expected_state[key])
    for key in late.WEIGHTS:
        assert np.count_nonzero(state['resolved_' + key]) == 0
    for actual, original in zip((mesh.xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors), before):
        assert np.array_equal(actual, original)


def test_actual_parent_support_has_incident_mean_halo_and_npz_input(parent, tmp_path):
    mesh, evidence, ownership = parent
    np.savez(tmp_path / 'g4.npz', parent_face=evidence['parent_face'])
    np.savez(tmp_path / 'g3.npz', **ownership)
    with np.load(tmp_path / 'g4.npz') as e4, np.load(tmp_path / 'g3.npz') as e3:
        _, metadata, state = late.build(mesh, e4, e3, 'COMBINED')
    f = (ownership['face_event_ids'][evidence['parent_face']] > 0).astype(float)
    t = topology(mesh)
    e = np.array([np.mean(f[incident]) for incident in t['ef']])
    v = np.array([np.mean(f[np.any(mesh.faces == i, axis=1)]) for i in range(len(mesh.xyz))])
    for name, expected in [('face', f), ('edge', e), ('vertex', v)]:
        assert np.array_equal(state['input_' + name + '_support'], expected)
    assert np.any((e > 0) & (e < 1)) and np.any((v > 0) & (v < 1))
    assert metadata['supported_face_count'] == 8
    for key, expected in {'w3': 1.8*f, 'w4': .6*f, 'wf': .8*f, 'we': -.2*e, 'wp': .4*v}.items():
        assert np.array_equal(state['resolved_' + key], expected)
    for key in ['w1', 'w2', 'w6', 'w7']:
        assert not np.any(state['resolved_' + key])


def test_eq4_uses_actual_classes_and_coupled_points_change(parent):
    mesh, evidence, ownership = parent
    neutral = late.build(mesh, evidence, ownership, 'NEUTRAL')[0]
    out, metadata, state = late.build(mesh, evidence, ownership, 'EQ4_ONLY')
    nv = len(mesh.xyz); ne = len(topology(mesh)['edges'])
    expected = mesh.xyz[mesh.faces].mean(axis=1)
    # Independent scalar face formula: the class IDs, not event IDs, select V/E/F.
    for i in np.flatnonzero(state['input_face_support']):
        indices = mesh.faces[i]; c = mesh.classes[indices]
        V, F = mesh.xyz[indices[c == 0]][0], mesh.xyz[indices[c == 2]][0]
        E = mesh.xyz[indices[c == 1]].sum(axis=0)
        expected[i] = ((V*2.8 + F*(-.8))*1.6 + E*.4)/4.
    np.testing.assert_allclose(out.xyz[nv+ne:], expected, rtol=0., atol=8e-16)
    assert np.max(np.linalg.norm(out.xyz[:nv+ne] - neutral.xyz[:nv+ne], axis=1)) > 1e-3
    assert metadata['factors'] == {'eq4': True, 'normal': False}
    for key in ['wf', 'we', 'wp']:
        assert not np.any(state['resolved_' + key])


def test_four_conditions_are_one_step_causal_factorial_on_same_input(parent):
    mesh, evidence, ownership = parent
    results = {mode: late.build(mesh, evidence, ownership, mode) for mode in late.MODES}
    xyz = {mode: result[0].xyz for mode, result in results.items()}
    np.testing.assert_allclose(xyz['COMBINED'] - xyz['NEUTRAL'],
        xyz['EQ4_ONLY'] - xyz['NEUTRAL'] + xyz['NORMAL_ONLY'] - xyz['NEUTRAL'],
        atol=2e-15, rtol=0.)
    assert np.max(np.abs(xyz['NORMAL_ONLY'] - xyz['NEUTRAL'])) > .01
    hashes = [result[1]['source_array_hashes'] for result in results.values()]
    assert all(h == hashes[0] for h in hashes)
    assert all(np.array_equal(result[0].faces, results['NEUTRAL'][0].faces) for result in results.values())
    # Actual unit face normal and current local mean-edge scale control new faces.
    f = fields(mesh); state = results['NORMAL_ONLY'][2]
    start = len(mesh.xyz) + len(topology(mesh)['edges'])
    expected_delta = f['nf'] * (.8*state['input_face_support']*f['sf'])[:, None]
    np.testing.assert_allclose(xyz['NORMAL_ONLY'][start:] - xyz['NEUTRAL'][start:],
        expected_delta, rtol=0., atol=3e-16)


def test_invalid_class_pattern_is_honest_eq1_fallback_not_invented_role(parent):
    mesh, evidence, ownership = parent
    mesh.classes = np.full(len(mesh.xyz), -1, np.int8)
    neutral = late.build(mesh, evidence, ownership, 'NEUTRAL')[0]
    out, metadata, state = late.build(mesh, evidence, ownership, 'EQ4_ONLY')
    assert np.array_equal(out.xyz, neutral.xyz)
    assert metadata['eq4_eligible'] == 0 and metadata['eq4_fallback'] == len(mesh.faces)
    assert metadata['supported_eq4_fallback_count'] == 8
    assert not np.any(state['eq4_eligible_mask'])


@pytest.mark.parametrize('bad', ['missing', 'float', 'length', 'range', 'generation'])
def test_stale_or_untraceable_parent_is_rejected(parent, bad):
    mesh, evidence, ownership = parent
    if bad == 'missing': evidence = {}
    elif bad == 'float': evidence = {'parent_face': evidence['parent_face'].astype(float)}
    elif bad == 'length': evidence = {'parent_face': evidence['parent_face'][:-1]}
    elif bad == 'range': evidence = {'parent_face': np.full(len(mesh.faces), 100, np.int64)}
    elif bad == 'generation': mesh.generation = 3
    with pytest.raises(ValueError):
        late.build(mesh, evidence, ownership, 'COMBINED')
