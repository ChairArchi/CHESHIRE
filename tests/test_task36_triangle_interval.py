"""Geometric counterexamples, independent of generated candidate selection."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from task33_contacts import batch_hits
from task36_triangle_interval import interval_hits


def test_edge_to_edge_endpoints_still_intersect_triangle_interiors():
    a=np.array([[[-1,-1,0],[1,-1,0],[0,1,0]]],float)
    b=np.array([[[-1,0,-1],[1,0,-1],[0,0,1]]],float)
    assert not batch_hits(a,b)[0]
    assert interval_hits(a,b)[0]
    assert interval_hits(b,a)[0]


def test_disjoint_intervals_parallel_planes_and_point_tangency_excluded():
    a=np.array([[[-1,-1,0],[1,-1,0],[0,1,0]]],float)
    b=np.array([[[-1,0,-1],[1,0,-1],[0,0,1]]],float)
    assert not interval_hits(a,b+[2,0,0])[0]  # No interval overlap.
    assert not interval_hits(a,a+[0,0,1])[0]  # Parallel separated planes.
    assert not interval_hits(a,b+[1,0,0])[0]  # Intervals share one endpoint.
    assert not interval_hits(a,a)[0]  # Coplanar remains a declared exclusion.


def test_real_T02_crossing_is_not_a_tangent_or_coplanar_pair():
    a=np.array([[[-741.96229493,746.40135671,999.55244788],[-765.69165790,760.86774975,998.51348406],[-728.28092920,723.27928262,1002.22018170]]])/4000
    b=np.array([[[-760.86774975,765.69165790,998.51348406],[-746.40135671,741.96229493,999.55244788],[-723.27928262,728.28092920,1002.22018170]]])/4000
    assert interval_hits(a,b)[0]


def test_shared_vertex_bvh_audit_checks_interior_overlap_but_excludes_hinges():
    from types import SimpleNamespace
    from task36_contacts import contacts
    xyz=np.array([[-1,-1,0],[1,-1,0],[0,1,0],[1,1,-1],[1,1,1]],float)
    mesh=SimpleNamespace(xyz=xyz,faces=np.array([[0,1,2,-1],[0,3,4,-1]]))
    assert contacts(mesh,interval=True)['transverse_contacts']==0
    assert contacts(mesh,interval=True,include_shared=True)['pairs']==[[0,1]]
    mesh.xyz=np.r_[xyz[:3],[[0,-2,1]]];mesh.faces=np.array([[0,1,2,-1],[1,0,3,-1]])
    assert contacts(mesh,interval=True,include_shared=True)['transverse_contacts']==0
