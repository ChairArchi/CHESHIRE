import copy
import numpy as np
import pytest
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import cube, topology
from cheshire.task36_growth import native, carrier
from cheshire.astra_curvature_response import step


def test_zero_displacement_is_exact_surface_sampling():
    m = native(carrier()); out, _, state = step(m, amplitude=0)
    assert np.array_equal(out.xyz[:len(m.xyz)], m.xyz)
    assert np.array_equal(out.xyz[len(m.xyz):], m.xyz[state['input_edges']].mean(1))
    assert np.array_equal(out.xyz, state['base_xyz'])
    assert np.all(state['resolved_displacement'] == 0)
    assert len(out.faces) == 4 * len(m.faces)
    p = out.xyz[out.faces[:, :3]]
    area = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1) / 2
    original = m.xyz[m.faces[:, :3]]
    cross = np.cross(original[:, 1]-original[:, 0], original[:, 2]-original[:, 0])
    expected = np.linalg.norm(cross, axis=1) / 2
    np.testing.assert_allclose(area.reshape(-1, 4).sum(1), expected)
    parent = state['parent_faces']
    np.testing.assert_allclose(np.einsum('ijk,ik->ij', p-original[parent, 0, None], cross[parent]), 0, atol=1e-5)
    assert len(out.xyz)-len(topology(out)['edges'])+len(out.faces) == 2
    assert np.array_equal(out.anchors, m.anchors[parent])
    assert np.array_equal(state['new_vertex_parent_faces'], topology(m)['ef'])


def test_physical_scale_equivariance():
    m = native(carrier()); scaled = copy.deepcopy(m)
    scaled.xyz *= 3; scaled.rest *= 3
    a, _, sa = step(m, amplitude=15, radius=100, reference_length=100)
    b, _, sb = step(scaled, amplitude=45, radius=300, reference_length=300)
    np.testing.assert_allclose(b.xyz, 3*a.xyz, atol=1e-10)
    np.testing.assert_allclose(sa['transferred_q'], sb['transferred_q'], atol=1e-12)
    np.testing.assert_allclose(sb['diffusion_local_rms_distance'], 3*sa['diffusion_local_rms_distance'], atol=1e-10)
    assert np.array_equal(a.faces, b.faces)


@pytest.mark.parametrize('response', ['monotonic', 'nonmonotonic'])
def test_xy_reflection(response):
    m = native(carrier())
    for _ in range(2):
        m, _, _ = step(m, response=response)
        tree = cKDTree(m.xyz)
        for axis in (0, 1):
            reflected = m.xyz.copy(); reflected[:, axis] *= -1
            distance, ids = tree.query(reflected)
            assert distance.max() < 1e-9
            assert len(np.unique(ids)) == len(ids)
            expected = {tuple(sorted(f)) for f in m.faces[:, :3]}
            assert expected == {tuple(sorted(f)) for f in ids[m.faces[:, :3]]}


def test_both_old_new_vertices_receive_field_and_no_xyz_diffusion():
    m = native(cube()); out, _, state = step(m, response='monotonic', radius=0)
    n = len(m.xyz)
    assert np.any(np.linalg.norm(state['resolved_displacement'][:n], axis=1) > 0)
    assert np.any(np.linalg.norm(state['resolved_displacement'][n:], axis=1) > 0)
    assert np.array_equal(state['raw_dimensionless_q'], state['diffused_q'])
    np.testing.assert_allclose(out.xyz, state['base_xyz'] + state['resolved_displacement'])
    _, _, other = step(m, response='monotonic', iterations=0)
    assert np.array_equal(other['diffused_q'], state['diffused_q'])


def test_current_vs_evolving_rest_feature_difference():
    m, _, _ = step(native(carrier()), amplitude=20, response='monotonic')
    _, _, a = step(m, source='current'); _, _, b = step(m, source='rest')
    assert np.max(abs(a['raw_dimensionless_q']-b['raw_dimensionless_q'])) > 1e-4


def test_guards():
    m = native(cube())
    for kw in ({'amplitude':np.nan}, {'radius':-1}, {'reference_length':0}, {'iterations':33}, {'iterations':1.5}):
        with pytest.raises(ValueError):step(m, **kw)
    m.xyz[0] = m.xyz[1]
    with pytest.raises(ValueError, match='Degenerate'):step(m)
