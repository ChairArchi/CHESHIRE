"""Small counterexamples for spatial signals, roles and preserved baseline links."""
from pathlib import Path
import copy
import importlib.util

import numpy as np
import pytest

from cheshire import reference_subdivision as reference


BASE = Path(__file__).resolve().parents[1]/'experiments/coherent_fold_detail_20261013'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


verify = load('tested_coherent_fold_verifier', 'verify.py')
operator = load('tested_coherent_fold_operator_for_verifier', 'fold_operator.py')


def fixture(mode='ROLE_CURVATURE'):
    source = reference.cube(side=2.); source.generation = 3
    mesh, _, g4 = reference.subdivide(source, {'weights': {}})
    g3 = dict(face_event_ids=np.array([0, 1, 0, 2, 0, 0]),
        face_roles=np.array([0, 1, 0, 2, 0, 0]), mirror_face_signs=np.ones((6, 2), np.int64),
        inherited_root_pca_origin=np.zeros(3), inherited_root_pca_major=np.array([0., 0., 1.]),
        inherited_root_pca_minor=np.array([1., 0., 0.]), inherited_root_pca_normal=np.array([0., 1., 0.]),
        inherited_root_pca_extent=np.array([2., 1.4]), inherited_root_radius=np.array(.6))
    out, metadata, state = operator.build(mesh, g4, g3, mode)
    return mesh, g4, g3, out, metadata, state


@pytest.mark.parametrize('mode', verify.MODES)
def test_independent_spatial_controls_replay_actual_cc_without_operator_self_call(mode):
    mesh, g4, g3, out, metadata, state = fixture(mode)
    _, controls, fields = verify.verify_rule_evidence(mesh, g4, g3, mode, state, operator.RECIPE)
    actual, ref_metadata, _ = reference.subdivide(mesh, {'weights': {}}, resolved_controls=controls)
    for name in ('xyz', 'faces', 'classes', 'rest', 'anchors'):
        assert verify.H.array_bits_equal(getattr(out, name), getattr(actual, name))
    verify.verify_operator_metadata(metadata, ref_metadata, fields, mesh, g4, g3, mode, operator.RECIPE, reference)
    assert np.all(fields['face_scalar'][fields['input_face_support'] == 0.] == 0.)
    assert np.all(controls['w3'] == 0.) and np.all(controls['w4'] == 0.)


@pytest.mark.parametrize('key', ['face_phase', 'face_role_gain', 'face_planarity', 'input_point_classes', 'resolved_we'])
def test_forged_signals_or_classes_cannot_hide_behind_unchanged_geometry(key):
    mesh, g4, g3, _, _, state = fixture()
    changed = {name: value.copy() for name, value in state.items()}
    changed[key][0] += 1 if key == 'input_point_classes' else .001
    with pytest.raises(ValueError, match='actual spatial/class/control evidence.*'+key):
        verify.verify_rule_evidence(mesh, g4, g3, 'ROLE_CURVATURE', changed, operator.RECIPE)


def test_coherent_vertex_compensation_uses_actual_extraordinary_degree():
    mesh = reference.cube(side=2.)
    topology = reference.topology(mesh)
    controls = verify.controls_from_amplitude(np.full(6, .8), topology, len(mesh.xyz))
    assert np.all(topology['degree'] == 3)
    np.testing.assert_allclose(controls['wp'], .8*(1.-1./3.), rtol=0., atol=1e-15)
    np.testing.assert_array_equal(controls['we'], np.full(12, .4))
    assert not np.allclose(controls['wp'], .4)


def test_anatomical_role_is_not_an_eq4_previous_point_class():
    mesh, g4, g3, _, _, _ = fixture()
    g3['face_roles'][0] = 2  # Owner zero cannot silently become a CAP/F class.
    with pytest.raises(ValueError, match='SOURCE/WALL/CAP'):
        verify.independent_fields(mesh, g4, g3, 'ROLE_CURVATURE', operator.RECIPE)


def test_cyclic_planarity_and_reflected_root_phase_use_actual_geometry():
    mesh, g4, g3, _, _, _ = fixture()
    mesh.xyz[0, 2] += .12
    _, _, fields = verify.independent_fields(mesh, g4, g3, 'ROLE_CURVATURE', operator.RECIPE)
    cyclic = copy.deepcopy(mesh); cyclic.faces = np.roll(cyclic.faces, 1, axis=1)
    _, _, cycled = verify.independent_fields(cyclic, g4, g3, 'ROLE_CURVATURE', operator.RECIPE)
    reflected = copy.deepcopy(mesh); reflected.xyz[:, 0] *= -1.; reflected.faces = reflected.faces[:, ::-1]
    reflected_g3 = copy.deepcopy(g3); reflected_g3['mirror_face_signs'][:, 0] *= -1
    _, _, mirrored = verify.independent_fields(reflected, g4, reflected_g3, 'ROLE_CURVATURE', operator.RECIPE)
    assert np.max(fields['face_planarity']) > 0.
    for key in ('face_planarity', 'face_bending', 'face_phase', 'face_scalar'):
        np.testing.assert_allclose(cycled[key], fields[key], rtol=0., atol=1e-13)
        np.testing.assert_allclose(mirrored[key], fields[key], rtol=0., atol=1e-13)


def baseline_fixture():
    tmp_path = Path(__file__).resolve().parent/'__unwritten_coherent_baseline_fixture__'
    source = dict(path=str(tmp_path/'G04'), control_sha256='G4', generation_sha256='G4meta', parent_verification_sha256='parentPASS',
        baseline=dict(path=str(tmp_path/'COMBINED/G05'), generation_sha256='G5meta', control_sha256='G5', geometry_sha256='native'))
    hashes = dict(control_xyz_sha256='x', control_faces_sha256='f', chart_sha256='c', native_xyz_sha256='nx', native_faces_sha256='nf')
    proof = dict(passed=True, candidate='COMBINED', actual_generation=5, generation_json_sha256='G5meta',
        exact_control_native_and_evidence_replay=True, actual_native_topology=dict(passed=True),
        actual_native_symmetry={axis: dict(passed=True) for axis in ('X', 'Y')}, hashes=hashes,
        shared_control_array_hashes=dict(faces='f', classes='cl', rest='r', anchors='a', chart='c'))
    info = dict(candidate='COMBINED', input_case='SPAN', subdivision_generation=5, source_generation=4,
        preserved_parent=dict(control_sha256='G4'), source=source['path'], checks=hashes.copy())
    rendered = dict(input_case='SPAN', candidate='COMBINED', subdivision_generation=5, reused_reference=False,
        generation_sha256='G5meta', control_sha256='G5', geometry_sha256='native',
        geometry=str(tmp_path/'COMBINED/G05/geometry.npz'), native_arrays=dict(xyz_sha256='nx', faces_sha256='nf'),
        source_provenance=dict(parent_control_sha256='G4', parent_generation_sha256='G4meta', parent_verification_sha256='parentPASS'),
        independent_geometry_generation_sha256='G5meta')
    return source, info, proof, rendered


@pytest.mark.parametrize('corruption', ['different_G4', 'different_native_render'])
def test_preserved_baseline_rejects_nearly_related_parent_or_wrong_render_arrays(corruption):
    source, info, proof, rendered = baseline_fixture()
    assert verify.check_baseline_records(source, 'SPAN', info, proof, rendered)[1] == proof['hashes']
    if corruption == 'different_G4':
        info['preserved_parent']['control_sha256'] = 'some_other_G4'
    else:
        rendered['native_arrays']['faces_sha256'] = 'other_triangle_order'
    with pytest.raises(ValueError, match='Frozen COMBINED'):
        verify.check_baseline_records(source, 'SPAN', info, proof, rendered)


def test_missing_mode_or_counter_cannot_be_silently_skipped():
    missing = Path(__file__).resolve().parent/'__unwritten_coherent_inventory__'
    assert not missing.exists()
    with pytest.raises(ValueError, match='six coherent-rule'):
        verify.inventory(missing)


def test_verifier_preserves_existing_receipt_before_any_replay(monkeypatch):
    class PreservedReceipt:
        def exists(self):
            return True

        def open(self, *args, **kwargs):
            pytest.fail('An existing receipt must never be opened for writing.')

    receipt = PreservedReceipt()
    monkeypatch.setattr(verify.H, 'receipt_destination', lambda *args: receipt)
    monkeypatch.setattr('sys.argv', ['verify.py', '--root', 'unwritten_fixture'])
    with pytest.raises(FileExistsError, match='preserved'):
        verify.main()
