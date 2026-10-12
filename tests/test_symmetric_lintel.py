"""Portable geometric regressions for symmetric lintels and fixed columns."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_path = Path(__file__).resolve().parents[1]/'experiments/fold_visible_gate_20261012/symmetric_lintel.py'
_spec = importlib.util.spec_from_file_location('symmetric_lintel_test_module', _path)
lintel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lintel)


@pytest.fixture
def portable_column(tmp_path):
    # The public G2 native mesh is a real, nontrivial fixture. Tests do not
    # depend on an untracked current WALL render or any external field cache.
    source = lintel.study.previous.SOURCES['SPAN']
    mesh, _, _ = lintel.study.previous.anchor.t.load(source)
    native = lintel.study.previous.anchor.t.growth.native(mesh)
    path = tmp_path/'actual_column_fixture.npz'
    np.savez_compressed(path, xyz=native.xyz, faces=native.faces[:, :3])
    return path, source


def test_symmetric_plain_box_preserves_reflected_triangle_sets():
    xyz, faces = lintel.plain_box(.973, .747, 4.77)
    assert len(xyz) == 14 and len(faces) == 24
    assert lintel.geometry_checks(xyz, faces, components=1)['passed']
    for axis, plane in [(0, 0.), (1, 0.), (2, 4.77/2)]:
        assert lintel.reflection(xyz, faces, axis, plane)['passed']


def test_source_is_new_pair_symmetric_carrier_with_one_fixed_extent_transform(portable_column):
    column, source = portable_column
    source_hash = lintel.digest(source/'control_quad.npz')
    layout = lintel.fixed_layout(column)
    mesh, chart, _, metadata, construction = lintel.make_source(source, layout)
    assert lintel.digest(source/'control_quad.npz') == source_hash
    pairs = construction['source_axial_pair_ids']
    assert np.array_equal(pairs[pairs], np.arange(len(chart)))
    assert np.max(np.linalg.norm(construction['pair_average_xyz']-construction['original_xyz'], axis=1)) > .1
    assert np.allclose(np.ptp(mesh.xyz, axis=0), [layout['width'], layout['depth'], layout['length']], atol=1e-12)
    native = lintel.study.previous.anchor.t.growth.native(mesh)
    for axis, plane in [(0, 0.), (1, 0.), (2, layout['length']/2)]:
        assert lintel.reflection(native.xyz, native.faces[:, :3], axis, plane)['passed']
    assert metadata['added_field_passes'] == 0 and len(metadata['parent_region_seeds']) == 4


def test_full_generation_keeps_column_geometry_and_replays_new_lintel(tmp_path, portable_column):
    column, source = portable_column
    root = tmp_path/'fixed_gate'
    source_hash = lintel.digest(column)
    lintel.generate(root, column=column, source_g2=source)
    assert lintel.digest(column) == source_hash
    receipt = json.loads((root/'verification.json').read_text())
    assert receipt['passed'] and all(item['passed'] for item in receipt['replay'])
    assert all(item['final_delta_max_error'] == 0. for item in receipt['replay'])
    column_data = lintel.arrays(column)
    vertex_count, face_count = len(column_data['xyz']), len(column_data['faces'])
    for mode in ('PLAIN', 'CONTROL', 'WALL'):
        metadata = json.loads((root/mode/'assembly.json').read_text())
        geometry = lintel.arrays(root/mode/'geometry.npz')
        for name, start in [('LEFT', 0), ('RIGHT', vertex_count)]:
            expected = lintel.gate_layout.apply_transform(column_data['xyz'], np.array(metadata['column_transforms'][name]))
            assert np.array_equal(geometry['xyz'][start:start+vertex_count], expected)
        assert np.array_equal(geometry['faces'][:face_count], column_data['faces'])
        assert np.array_equal(geometry['faces'][face_count:2*face_count]-vertex_count, column_data['faces'])
        assert metadata['checks']['global_left_right']['reflected_oriented_triangle_sets_identical']
    wall = lintel.arrays(root/'lintel/WALL/G03/operation_fields.npz')
    assert np.linalg.norm(wall['delta'], axis=1).max() > .01
    control = lintel.arrays(root/'lintel/CONTROL/G03/geometry.npz')
    folded = lintel.arrays(root/'lintel/WALL/G03/geometry.npz')
    assert not np.array_equal(control['xyz'], folded['xyz'])
    original_copy = root/'lintel/ORIGINAL_G02/control_quad.npz'
    assert lintel.digest(original_copy) == lintel.digest(source/'control_quad.npz')
    before = lintel.digest(root/'WALL/geometry.npz')
    with pytest.raises(FileExistsError, match='preserved'):
        lintel.generate(root, column=column, source_g2=source)
    assert lintel.digest(root/'WALL/geometry.npz') == before
