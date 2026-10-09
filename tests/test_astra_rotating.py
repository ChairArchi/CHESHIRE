import numpy as np
import pytest
from cheshire.reference_subdivision import cube,topology
from cheshire.task36_growth import native,carrier
from cheshire.astra_rotating import step
from scipy.spatial import cKDTree

def test_rotation_closed_and_actual_multiparents():
    m=native(cube());out,meta,state=step(m)
    assert len(out.faces)==3*len(m.faces)
    assert len(out.xyz)-len(topology(out)['edges'])+len(out.faces)==2
    assert np.all(state['parent_faces'][:,0]!=state['parent_faces'][:,1])
    for axis in [0,1,2]:
        reflected=out.xyz.copy();reflected[:,axis]*=-1
        assert cKDTree(out.xyz).query(reflected)[0].max()<1e-9

def test_inactive_no_flip_preserves_triangle_area():
    m=native(carrier());out,_,_=step(m,fold=0,relaxation=0,flip=False)
    def area(x):
        p=x.xyz[x.faces[:,:3]];return np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1).sum()/2
    assert np.isclose(area(m),area(out))
    assert np.array_equal(m.xyz,out.xyz[:len(m.xyz)])

def test_current_observation_changes_later_rule():
    m=native(carrier());m,_,_=step(m)
    a,_,sa=step(m,source='current');b,_,sb=step(m,source='rest')
    assert np.max(abs(sa['resolved_offset']-sb['resolved_offset']))>1
    assert np.array_equal(a.faces,b.faces)

def test_similarity_equivariance_and_no_bbox_clamp():
    m=native(cube());a,_,_=step(m,fold=.5,bias=-1)
    m.xyz=m.xyz*3;m.rest=m.rest*3;b,_,_=step(m,fold=.5,bias=-1)
    np.testing.assert_allclose(b.xyz,a.xyz*3,atol=1e-10)

def test_nonfinite_rejected():
    with pytest.raises(ValueError):step(native(cube()),fold=float('nan'))


def test_multiparent_anchor_never_arbitrarily_picks_first():
    m=native(cube());m.anchors=np.repeat(np.arange(len(m.faces))[:,None],3,axis=1)
    out,_,state=step(m)
    assert np.all(out.anchors==-1)
    assert np.all(state["parent_faces"]>=0)


def test_degenerate_input_rejected_before_normalization():
    m=native(cube());m.xyz[0]=m.xyz[1]
    with pytest.raises(ValueError,match="Degenerate"):step(m)
