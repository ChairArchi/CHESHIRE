"""Transfer contracts on different hosts; no project column fixture required."""
import numpy as np
import pytest

from cheshire.adaptive_ornament import (
    MandelRadialProfile, OrnamentRecipe, apply_adaptive_ornament,
)


def column(kind=0, nr=25, nt=48):
    z = np.linspace(0, 3, nr)
    t = np.arange(nt) * 2 * np.pi / nt
    tt, zz = np.meshgrid(t, z)
    twist = .35 * kind * np.sin(zz * 1.5)
    radius = 1 + (.07 + .04 * kind) * np.cos(6 * (tt + twist))
    radius *= 1 + .08 * kind * np.sin(zz * 2)
    x = np.column_stack((radius.ravel() * np.cos((tt + twist).ravel()),
                         radius.ravel() * np.sin((tt + twist).ravel()), zz.ravel()))
    ids = np.arange(nr * nt).reshape(nr, nt)
    q = np.stack((ids[:-1], np.roll(ids[:-1], -1, 1),
                  np.roll(ids[1:], -1, 1), ids[1:]), axis=2).reshape(-1, 4)
    uv = np.column_stack((zz.ravel(), tt.ravel()))
    w = np.zeros((len(x), 5))
    w[:, 0] = .4 + .3 * np.sin(tt.ravel()) ** 2
    w[:, 2] = 1 - w[:, 0]
    return x, q, uv, w


@pytest.fixture(scope="module")
def profile():
    # Synthetic interpolation fixture; the E: transfer proof uses the real
    # cached finite Mandelbulb boundary, not this trigonometric test surface.
    theta = np.linspace(0, np.pi, 17)
    phi = np.arange(32) * 2 * np.pi / 32
    radius = 1 + .15 * np.sin(theta[:, None]) ** 2 * np.cos(8 * phi[None, :])
    return MandelRadialProfile(theta, phi, radius)


def apply(host, profile, **kwargs):
    x, q, uv, w = host
    return apply_adaptive_ornament(x, q, shape_weights=w,
                                   pattern_coordinates=uv, profile=profile, **kwargs)


@pytest.mark.parametrize("kind", (0, 1))
def test_different_column_hosts_preserve_constraints_and_native_orientation(kind, profile):
    host = column(kind)
    x, q, uv, w = host
    before = x.copy()
    protection = ((uv[:, 1] < .15) & (uv[:, 0] > .4)).astype(float)
    result = apply(host, profile, flow_protection=protection,
                   tissue_height=np.full(len(x), .65),
                   tissue_priority=.7 * (np.sin(uv[:, 1]) ** 2))
    assert np.array_equal(x, before)
    assert np.array_equal(result['xyz'][result['fixed_mask']], x[result['fixed_mask']])
    assert result['quality']['reversed_native_fan_faces'] == 0
    assert np.quantile(np.linalg.norm(result['xyz'] - x, axis=1), .9) > .001
    # Tangent displacement would lose the host-flow preservation contract.
    delta = result['xyz'] - x
    tangent = delta - np.einsum('ij,ij->i', delta, result['normals'])[:, None] * result['normals']
    assert np.max(np.linalg.norm(tangent, axis=1)) < 1e-14


def test_recipe_is_covariant_under_physical_scale_and_rotation(profile):
    host = column(1)
    result = apply(host, profile)
    x, q, uv, w = host
    angle = .63
    r = np.array([[np.cos(angle), 0, np.sin(angle)], [0, 1, 0],
                  [-np.sin(angle), 0, np.cos(angle)]])
    scale = 3.7
    transformed = (x @ r.T * scale, q, uv * scale, w)
    actual = apply(transformed, profile, recipe=OrnamentRecipe(length_scale=scale))
    assert np.allclose(actual['xyz'], result['xyz'] @ r.T * scale, atol=2e-13, rtol=0)


def test_arbitrary_vertex_ids_do_not_change_the_algorithm(profile):
    host = column(1)
    expected = apply(host, profile)
    x, q, uv, w = host
    order = np.random.default_rng(82).permutation(len(x))
    inverse = np.empty_like(order)
    inverse[order] = np.arange(len(order))
    actual = apply((x[order], inverse[q], uv[order], w[order]), profile)
    assert np.allclose(actual['xyz'][inverse], expected['xyz'], atol=2e-14, rtol=0)


def test_recovery_contracts_only_new_relief_and_does_not_accept_reversed_fans(profile):
    host = column(1, nr=19, nt=32)
    x, q, uv, w = host
    recipe = OrnamentRecipe(class_amplitudes=(10,) * 5, tissue_amplitude=10,
                            normal_safety_ratio=100, max_recovery_passes=48)
    result = apply(host, profile, recipe=recipe)
    assert result['recovery_bad_face_counts'][0] > 0
    assert result['recovery_bad_face_counts'][-1] == 0
    assert np.count_nonzero(result['local_gain'] < 1) > 0
    assert np.array_equal(result['xyz'][result['fixed_mask']], x[result['fixed_mask']])


def test_missing_tissue_data_and_invalid_weights_are_rejected(profile):
    host = column()
    with pytest.raises(ValueError, match='actual Tissue'):
        apply(host, profile, tissue_priority=np.ones(len(host[0])))
    x, q, uv, w = host
    with pytest.raises(ValueError, match='sum to one'):
        apply((x, q, uv, w * .9), profile)
    with pytest.raises(ValueError, match='face budget'):
        apply(host, profile, recipe=OrnamentRecipe(max_faces=5))
