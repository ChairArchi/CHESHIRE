import importlib.util
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from task32_validation import segment_triangle_hit,manifold_links,embedding
from cheshire.reference_subdivision import cube
from cheshire.task32_patches import sweep_disk


def test_transverse_contact_detects_crossing_and_excludes_coplanarity():
    triangle=np.array([[0,0,0],[1,0,0],[0,1,0]],float)
    assert segment_triangle_hit(np.array([.2,.2,-1]),np.array([.2,.2,1]),triangle)
    assert not segment_triangle_hit(np.array([2,2,-1]),np.array([2,2,1]),triangle)
    assert not segment_triangle_hit(np.array([.1,.1,0]),np.array([.3,.3,0]),triangle)


def test_all_vertex_links_and_finite_embedding_on_constructive_surgery():
    out,_,_=sweep_disk(cube(),[1,2],dict(heights=[.2,.8],scales=[.8,.5]))
    links=manifold_links(out)
    assert links['checked_vertices']==len(out.xyz)
    assert links['invalid_vertex_links']==[] and links['orphan_vertices']==0
    summary=embedding(out)
    assert summary['Euler']==2 and summary['connected_components']==1
    assert summary['min_triangle_area']>0
