"""Small corruption fixtures for the compact G06 proof, without G06 allocation."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import numpy as np
import pytest

MODULE = Path(__file__).resolve().parents[1]/'experiments/fold_visible_gate_20261012/compactpackage_finish_g6.py'
SPEC = importlib.util.spec_from_file_location('test_selected_g06_package', MODULE)
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


def tetrahedron():
    xyz = np.array([[1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1]], float)
    faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], np.int64)
    return xyz, faces


def test_actual_topology_accepts_closed_oriented_connected_surface():
    xyz, faces = tetrahedron()
    result = proof.native_topology(xyz, faces, chunk=2)
    assert result['passed']
    assert result['components'] == 1
    assert result['unique_native_edges'] == 6
    assert result['euler_characteristic'] == 2


@pytest.mark.parametrize('corruption', ['open', 'reverse_face', 'disconnected', 'isolated_vertex', 'duplicate_face'])
def test_actual_topology_rejects_corruption(corruption):
    xyz, faces = tetrahedron()
    if corruption == 'open':
        faces = faces[:-1]
    elif corruption == 'reverse_face':
        faces[0] = faces[0, ::-1]
    elif corruption == 'disconnected':
        xyz, faces = np.vstack([xyz, xyz+5]), np.vstack([faces, faces+4])
    elif corruption == 'isolated_vertex':
        xyz = np.vstack([xyz, [[7, 7, 7]]])
    else:
        faces = np.vstack([faces, faces[0]])
    assert not proof.native_topology(xyz, faces, chunk=2)['passed']


def test_actual_topology_rejects_out_of_range_indices():
    xyz, faces = tetrahedron()
    faces[0, 0] = len(xyz)
    with pytest.raises(ValueError, match='indices are invalid'):
        proof.native_topology(xyz, faces)


def test_metadata_excludes_preliminary_g05_relaxation():
    metadata = dict(candidate='RELAXED_G06', input_case='SPAN', source_generation=3,
        output_generation=6, inactive_refinements=3, source_candidate='WALL',
        carrier_stage_generation=3, source_xyz_smoothing=True,
        relaxation_recipe=dict(carrier_stage_generation=3, maximum_carrier_shift=.04),
        relief_recipe=dict(maximum_height=.30))
    assert proof.metadata_identity(metadata, 'RELAXED_G06', 'SPAN') == 3
    metadata['carrier_stage_generation'] = 5
    with pytest.raises(ValueError, match='Preliminary G05'):
        proof.metadata_identity(metadata, 'RELAXED_G06', 'SPAN')


def test_missing_expected_counter_cannot_pass_asset_inventory(tmp_path):
    asset = tmp_path/'recipe.json'
    asset.write_bytes(b'{}')
    receipt = dict(copied_assets=[dict(path=asset.name, bytes=2, sha256=proof.sha(asset))],
        selected_mode='RELAXED_G06', expected_original_arrays={'SPAN': {}})
    with pytest.raises(ValueError, match='both SPAN/COUNTER'):
        proof.validate_assets(tmp_path.resolve(), receipt)


def test_actual_colony_source_provenance_detects_displaced_centre():
    xyz, faces = tetrahedron()
    bary = np.array([[.2, .3, .5]])
    primary = np.einsum('ni,nij->nj', bary, xyz[faces[[0]]])
    colonies = dict(primary_source_triangle_ids=np.array([0]), primary_source_barycentric=bary,
        primary_source_xyz=primary, levels=np.array([0, 1]), centres=np.vstack([primary, xyz[2]]),
        native_vertex_ids=np.array([-1, 2]))
    native = SimpleNamespace(xyz=xyz, faces=faces)
    assert proof.colony_source_provenance(colonies, native)['passed']
    colonies['centres'][0, 0] += .01
    assert not proof.colony_source_provenance(colonies, native)['passed']


def test_legacy_raw_carrier_aliases_are_explicit_and_forbidden_for_relaxed():
    saved = dict(carrier=dict(g5_delta_sha256='delta', maximum_g5_shift=0.,
        moved_g5_controls=0, g5_xyz_sha256='xyz', g5_chart_sha256='chart'))
    normalized, legacy = proof.normalize_operation(saved, 'INTEGRATED_G06')
    assert legacy
    assert normalized['carrier_stage_generation'] == 5
    assert normalized['carrier']['delta_sha256'] == 'delta'
    with pytest.raises(ValueError, match='pilot is excluded'):
        proof.normalize_operation(saved, 'RELAXED_G06')
