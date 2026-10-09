import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from task33_planar import inspect_segments


def test_closed_section_and_nonadjacent_crossing_are_distinguished():
    square=np.array([[[0,0],[1,0]],[[1,0],[1,1]],[[1,1],[0,1]],[[0,1],[0,0]]])
    good=inspect_segments(square)
    assert good['non_cycle_nodes']==0 and good['crossings_touches_overlaps']==[]
    crossed=np.array([[[0,0],[1,1]],[[1,1],[0,1]],[[0,1],[1,0]],[[1,0],[0,0]]])
    assert inspect_segments(crossed)['crossings_touches_overlaps']


def test_shared_vertex_does_not_hide_collinear_overlap():
    lines=np.array([[[0,0],[2,0]],[[2,0],[1,0]],[[1,0],[0,1]],[[0,1],[0,0]]])
    assert [0,1] in inspect_segments(lines)['crossings_touches_overlaps']
