import numpy as np
from cheshire.reference_subdivision import cube, topology
from cheshire.task32_morphology import spring_system, growth_energy, metric_growth, displace_hierarchy


def test_variational_gradient_matches_finite_difference():
    m = cube(1000)
    edges, lap, scale = spring_system(m)
    base = m.xyz/scale
    x = base + np.linspace(-.07, .11, base.size).reshape(base.shape)
    target = np.linalg.norm(base[edges[:, 0]]-base[edges[:, 1]], axis=1)*1.12
    anchors = np.linspace(.01, .13, len(base))
    def energy(z):
        return growth_energy(z, base, edges, target, lap, .05, anchors)
    _, grad = energy(x)
    flat = x.ravel()
    numerical = []
    for i in range(len(flat)):
        delta = np.zeros_like(flat); delta[i] = 1e-6
        numerical.append((energy(flat+delta)[0]-energy(flat-delta)[0])/2e-6)
    np.testing.assert_allclose(grad, numerical, rtol=2e-7, atol=1e-9)


def test_zero_growth_preserves_source_and_closed_connectivity():
    m = cube(1000)
    original = m.xyz.copy()
    out, meta, state = metric_growth(m, dict(growth=0, seed=0))
    np.testing.assert_array_equal(out.xyz, original)
    np.testing.assert_array_equal(m.xyz, original)
    np.testing.assert_array_equal(out.faces, m.faces)
    assert meta['converged'] and meta['initial_energy'] == 0
    assert topology(out)['edges'].shape == (12, 2)


def test_field_changes_geometry_without_claiming_branch_topology():
    m = cube(1000)
    out, meta, state = displace_hierarchy(m, dict(amplitude=50, coupling=1), 1)
    assert not np.array_equal(out.xyz, m.xyz)
    np.testing.assert_array_equal(out.faces, m.faces)
    assert not meta['topology_changed']
    assert np.isfinite(out.xyz).all()
    assert state['field'].shape == (8,)
