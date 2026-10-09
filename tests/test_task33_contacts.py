import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from cheshire.reference_subdivision import cube,ArrayMesh
from task32_full_contacts import full_contacts
from task33_contacts import contacts,batch_hits
from task32_validation import segment_triangle_hit


def test_radius_bins_preserve_all_transverse_pairs():
    m=cube(1000)
    n=ArrayMesh(np.vstack([m.xyz,m.xyz+np.array([350,250,190])]),np.vstack([m.faces,m.faces+8]),
                np.tile(m.classes,2),np.vstack([m.rest,m.rest+np.array([350,250,190])]),np.tile(m.anchors,(2,1)))
    assert sorted(contacts(n)['pairs'])==sorted(full_contacts(n)['pairs'])
    assert contacts(n)['transverse_contacts']>0


def test_extreme_radius_ratio_does_not_remove_small_contact_pairs():
    m=cube(1000)
    small=cube(5)
    meshes=[m,small,small]
    offsets=[np.zeros(3),np.array([10,20,30]),np.array([11,21,31])]
    xyz=np.vstack([s.xyz+o for s,o in zip(meshes,offsets)])
    faces=np.vstack([s.faces+8*i for i,s in enumerate(meshes)])
    n=ArrayMesh(xyz,faces,np.full(24,-1,np.int8),xyz.copy(),np.full((18,3),-1,np.int64))
    assert sorted(contacts(n)['pairs'])==sorted(full_contacts(n)['pairs'])
    assert contacts(n)['radius_bins']>1


def test_batch_predicate_matches_scalar_for_random_and_degenerate_triangles():
    rng=np.random.default_rng(33)
    a=rng.normal(size=(3,3));b=rng.normal(size=(2000,3,3))
    b[:20,2]=b[:20,1]
    expected=[any(segment_triangle_hit(one[k],one[(k+1)%3],two)
                  for one,two in ((a,tri),(tri,a)) for k in range(3)) for tri in b]
    np.testing.assert_array_equal(batch_hits(a,b),expected)
