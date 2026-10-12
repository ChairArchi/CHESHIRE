"""Small structural checks for the actual separated-member pilot, not fabrication."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import trimesh
from scipy.spatial import cKDTree

_path = Path(__file__).resolve().parents[1]/'experiments/fold_visible_gate_20261012/gate_members.py'
_spec = importlib.util.spec_from_file_location('gate_member_test_module', _path)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


@pytest.fixture(scope='module')
def sources():
    return {kind: gate.build_source(kind) for kind in ('COLUMN', 'LINTEL')}


def test_real_g2_sources_have_independent_rectangular_carriers(sources):
    for kind, (mesh, chart, tags, metadata) in sources.items():
        carrier, g0chart = gate.build_carrier(kind)
        assert carrier.generation == 0 and mesh.generation == 2
        assert len(mesh.faces) == 16*len(carrier.faces)
        assert np.array_equal(mesh.rest[:len(carrier.xyz)], carrier.xyz)
        assert len(chart) == len(tags) == len(mesh.xyz)
        assert metadata['field_passes_total'] == metadata['field_passes_inherited'] == 0
        assert metadata['parent_region_seeds'] == gate.PARENTS
        length = gate.DIMENSIONS[kind]['length']
        for end in (0., 1.):
            cap = np.abs(chart[:, 0]-end) < 1e-12
            assert np.max(np.abs(mesh.xyz[cap, 2]-end*length)) < 1e-12
        native = gate.task36_growth.native(mesh)
        physical = trimesh.Trimesh(native.xyz, native.faces[:, :3], process=False)
        assert physical.is_watertight and physical.is_winding_consistent
        assert physical.volume > 0 and physical.area_faces.min() > 1e-12
        # Every corner exists in the actual G0 perimeter, not an ellipse or
        # a chamfered approximation caused by missing 45-degree samples.
        for x in (-.45, .45):
            for y in (-.25, .25):
                assert np.min(np.linalg.norm(carrier.xyz-[x, y, 0], axis=1)) < 1e-12


def test_lintel_half_copy_applies_to_source_and_later_delta(sources):
    mesh, chart, _, _ = sources['LINTEL']
    ids = gate.axial_correspondence(chart)
    assert np.max(np.abs(mesh.xyz-(mesh.xyz[ids]*[1, 1, -1]+[0, 0, 4.]))) < 1e-12
    delta = np.random.default_rng(17).normal(size=mesh.xyz.shape)
    original = delta.copy()
    gate.reflect_axial_delta(delta, chart)
    first_half = chart[:, 0] < .5-1e-12
    assert np.array_equal(delta[first_half], original[first_half])
    assert np.max(np.abs(delta-delta[ids]*[1, 1, -1])) < 1e-12


def test_assembly_has_three_closed_parts_proper_beam_rotation_and_gate_lr(sources):
    parts = {}
    for kind, (mesh, _, _, _) in sources.items():
        native = gate.task36_growth.native(mesh)
        parts[kind] = native.xyz, native.faces[:, :3]
    assembly = gate.assemble(parts)
    physical = trimesh.Trimesh(assembly['xyz'], assembly['faces'], process=False)
    assert physical.body_count == 3 and physical.is_watertight and physical.is_winding_consistent
    assert set(assembly['face_parts']) == {0, 1, 2}
    for transform in gate.member_transforms().values():
        assert np.linalg.det(transform[:3, :3]) == pytest.approx(1.)
    beam = gate.member_transforms()['LINTEL']
    assert np.allclose(beam @ [0, 0, 0, 1], [-2, 0, 3.09, 1])
    assert np.allclose(beam @ [0, 0, 4, 1], [2, 0, 3.09, 1])
    target = assembly['xyz']*[-1, 1, 1]
    distance, _ = cKDTree(assembly['xyz']).query(target)
    assert distance.max() < 1e-12
    assert assembly['metadata']['nominal_seat_gap'] == .04


def test_portable_export_retains_actual_g0_g1_g2_and_refuses_overwrite(tmp_path, sources):
    source = gate.write_source(tmp_path, 'COLUMN')
    assert source == tmp_path/'COLUMN/G02'
    for stage in range(3):
        folder = tmp_path/'COLUMN'/f'G{stage:02}'
        with np.load(folder/'control_quad.npz', allow_pickle=False) as data:
            assert int(data['generation']) == stage
        assert (folder/'geometry.npz').exists() and (folder/'generation.json').exists()
    with np.load(source/'control_quad.npz', allow_pickle=False) as data:
        assert np.array_equal(data['xyz'], sources['COLUMN'][0].xyz)
    with pytest.raises(FileExistsError, match='preserved'):
        gate.write_source(tmp_path, 'COLUMN')
