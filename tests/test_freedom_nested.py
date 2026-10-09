import numpy as np
from cheshire.reference_subdivision import cube,fields
from cheshire.freedom_nested import pocket,exact_split,physical,centres


def area_moment(mesh):
    p=physical(mesh);v=p.xyz[p.faces[:,:3]];a=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
    return a.sum(),np.sum(a[:,None]*v.mean(1),axis=0)


def test_exact_split_preserves_nonplanar_declared_native_fan():
    m=cube();m.xyz[0]+=[100,30,20];m.physical_centres=fields(m)['c']+np.array([2,3,4])
    before=area_moment(m);out,_,_,_=exact_split(m,np.ones(6))
    after=area_moment(out)
    np.testing.assert_allclose(before[0],after[0],rtol=2e-14)
    np.testing.assert_allclose(before[1],after[1],rtol=2e-14,atol=1e-5)


def test_pocket_depth_uses_parent_support_and_keeps_exact_ancestry():
    m=cube();parent=np.full(6,800.)
    out,_,state,child=pocket(m,parent_support=parent,memory=1,depth=.3,selection=0)
    np.testing.assert_array_equal(state['requested_normal_distance'],np.full(6,-240.))
    np.testing.assert_array_equal(child,parent[state['parent_face']])
    assert len(out.faces)==30


def test_unselected_faces_keep_their_physical_centres_after_vf_split():
    m=cube();m.xyz[:,2]*=2;m,_,_,support=pocket(m,selection=0)
    m,_,_,support=exact_split(m,support);before=centres(m).copy()
    out,_,state,_=pocket(m,parent_support=support,memory=.5,selection=.7)
    unselected=np.setdiff1d(np.arange(len(m.faces)),state['selected_input_faces'])
    assert len(unselected)>0
    np.testing.assert_array_equal(centres(out)[:len(unselected)],before[unselected])
