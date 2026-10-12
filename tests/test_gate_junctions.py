"""Actual vertical ray parity and axis-preserving junction deformation."""
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'experiments/fold_visible_gate_20261012'))
from gate_junctions import VerticalTriangles, intervals, deform
from symmetric_lintel import plain_box


def test_actual_triangle_rays_deduplicate_shared_edges_and_detect_true_interval_overlap():
    xyz, faces = plain_box(2., 2., 2.)
    column = VerticalTriangles(xyz, faces)
    # The central ray crosses several shared fan edges; each surface height is
    # still represented exactly once, preserving closed-surface parity.
    hits = column.hits([0., 0.])
    assert np.allclose(hits, [0., 2.], rtol=0, atol=1e-13)
    above = VerticalTriangles(xyz+[0., 0., 2.2], faces)
    overlapping = VerticalTriangles(xyz+[0., 0., 1.8], faces)
    head = intervals(hits)[-1]
    gap = intervals(above.hits([0., 0.]))[0]
    joined = intervals(overlapping.hits([0., 0.]))[0]
    assert min(head[1], gap[1])-max(head[0], gap[0]) < 0
    assert np.isclose(min(head[1], joined[1])-max(head[0], joined[0]), .2)
    assert len(column.hits([2., 0.])) == 0


def test_continuous_joint_mapping_preserves_axial_stations_and_untouched_regions():
    source = np.array([[-.2, .3, .1], [.4, -.1, .5], [0., .2, 1.]])
    weight = np.array([0., .5, 1.])
    result = deform(source, weight, 1.65, .16)
    assert np.array_equal(result[:, 2], source[:, 2])
    assert np.array_equal(result[0], source[0])
    assert np.allclose(result[:, 1], source[:, 1]*(1.+.65*weight))
    assert np.allclose(result[:, 0], source[:, 0]*(1.+.65*weight)-.16*weight)
    assert np.array_equal(deform(source, np.zeros(3), 1.65, .16), source)
