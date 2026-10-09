import numpy as np
import pytest
from cheshire.reference_subdivision import cube,subdivide,fields
from cheshire.freedom_legacy import step,pocket


def test_zero_memory_recovers_current_scale_published_masks():
    m=cube();m.xyz[:,2]*=3
    weights=dict(wf=.1,we=-.08,wp=.03,w1=-.4,w2=-.7)
    a,_,_,_=step(m,weights,memory=0)
    b,_,_=subdivide(m,weights)
    np.testing.assert_allclose(a.xyz,b.xyz,atol=1e-11,rtol=1e-13)
    np.testing.assert_array_equal(a.faces,b.faces)


def test_ancestor_scale_persists_through_actual_children_and_restart():
    m=cube();weights=dict(wf=.1,w1=-.3)
    a,_,state,parent=step(m,weights,memory=1)
    np.testing.assert_array_equal(parent,np.repeat(fields(m)['sf'],4))
    b,_,s,_=step(a,weights,ancestor_scale=parent,memory=1)
    np.testing.assert_array_equal(s['effective_face_scale'],parent)
    c,_,_,_=step(a,weights,ancestor_scale=state['child_ancestor_scale'].copy(),memory=1)
    np.testing.assert_array_equal(b.xyz,c.xyz)


def test_invalid_ancestry_scale_is_rejected_without_geometry_repair():
    with pytest.raises(ValueError):step(cube(),{},ancestor_scale=np.zeros(6))


def test_pocket_retains_boundaries_connected_topology_and_real_parent_faces():
    from cheshire.reference_subdivision import topology
    m=cube();a,meta,state,scale=pocket(m,depth=.5)
    np.testing.assert_array_equal(a.xyz[:len(m.xyz)],m.xyz)
    assert len(a.faces)==30 and len(a.xyz)==32
    t=topology(a);assert len(a.xyz)-len(t['edges'])+len(a.faces)==2
    assert np.all(np.bincount(state['parent_face'])==5)
    _,nextmeta,_,_=step(a,{},ancestor_scale=scale)
    assert nextmeta['eq4_eligible']==0
