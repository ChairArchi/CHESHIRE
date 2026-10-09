import numpy as np
import pytest
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import cube, topology
from cheshire.task36_growth import native, carrier
from cheshire.astra_rotating import step as uniform_step
from cheshire.astra_adaptive import step


def cycles(tri):
    tri = np.asarray(tri)
    start = tri.argmin(1)
    rolled = tri[np.arange(len(tri))[:, None], (start[:, None] + np.arange(3)) % 3]
    return rolled[np.lexsort(rolled[:, ::-1].T)]


def test_uniform_mean_is_exact_existing_rotation():
    for m in (native(cube()), native(carrier())):
        for _ in range(3):
            a, _, sa = uniform_step(m, fold=.35, relaxation=.04, polarity=1.)
            b, _, sb = step(m, selection='uniform', hinge='mean')
            for attr in ('xyz', 'faces', 'classes', 'rest', 'anchors'):
                assert np.array_equal(getattr(a, attr), getattr(b, attr)), attr
            for key in ('parent_faces', 'parent_corner', 'resolved_offset'):
                assert np.array_equal(sa[key], sb[key]), key
            m = a


def test_adaptive_closed_conforming_and_real_parent_map():
    m = native(carrier())
    for _ in range(3):
        out, _, state = step(m, hinge='dominant')
        t = topology(out)
        assert len(out.xyz) - len(t['edges']) + len(out.faces) == 2
        assert np.all(t['degree'] >= 3)
        selected = state['selected_faces']
        assert np.any(selected) and np.any(~selected)
        assert len(out.faces) == len(m.faces) + 2 * selected.sum()
        assert len(out.xyz) == len(m.xyz) + selected.sum()
        parent = state['parent_faces']; kinds = state['child_construction']
        assert np.all(selected[parent[kinds == 2]])
        assert np.all(parent[kinds != 2, 1] == -1)
        assert np.all(selected[parent[kinds == 1, 0]])
        assert np.all(~selected[parent[kinds == 0, 0]])
        for child, old_ids, ps in zip(out.faces[:, :3], state['parent_old_corners'], parent):
            assert set(old_ids[old_ids >= 0]) == set(child[child < len(m.xyz)])
            for p in ps[ps >= 0]:
                assert set(old_ids[old_ids >= 0]) & set(m.faces[p, :3])
        assert np.array_equal(state['flipped_edges'], selected[topology(m)['ef']].all(1))
        m = out


@pytest.mark.parametrize('hinge', ['mean', 'dominant'])
def test_adaptive_reflection_includes_connectivity(hinge):
    m = native(carrier())
    for _ in range(3):
        m, _, _ = step(m, hinge=hinge)
        tree = cKDTree(m.xyz)
        for axis in (0, 1):
            reflected = m.xyz.copy(); reflected[:, axis] *= -1
            dist, ids = tree.query(reflected)
            assert dist.max() < 1e-9
            assert len(np.unique(ids)) == len(ids)
            assert np.array_equal(cycles(m.faces[:, :3]), cycles(ids[m.faces[:, :3]][:, [0, 2, 1]]))


def test_multiparent_anchors_agree_or_unknown():
    m = native(carrier())
    m.anchors = np.repeat(np.arange(len(m.faces))[:, None], 3, axis=1)
    out, _, state = step(m)
    parents = state['parent_faces']; two = parents[:, 1] >= 0
    assert np.all(out.anchors[two] == -1)
    assert np.array_equal(out.anchors[~two], m.anchors[parents[~two, 0]])


def test_current_vs_evolving_rest_changes_features():
    m = native(carrier()); m, _, _ = step(m)
    _, _, current = step(m, source='current')
    _, _, rest = step(m, source='rest')
    assert np.max(abs(current['feature_area'] - rest['feature_area'])) > 1
    assert np.max(abs(current['requested_offset'] - rest['requested_offset'])) > 1e-3


def test_reject_nonfinite_and_degenerate():
    m = native(cube())
    with pytest.raises(ValueError, match='Nonfinite'):step(m, quantile=np.nan)
    m.xyz[0] = m.xyz[1]
    with pytest.raises(ValueError, match='Degenerate'):step(m)
