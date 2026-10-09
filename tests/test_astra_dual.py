import numpy as np
import pytest
from cheshire.reference_subdivision import cube,topology
from cheshire.dual_subdivision import doo_sabin
from cheshire.task36_growth import carrier
from cheshire.astra_dual import step,native,refine_fan


@pytest.mark.parametrize('make',[cube,carrier])
def test_zero_geometry_feedback_reproduces_published_operator(make):
    mesh=make();a,roles,_,state=step(mesh,fold_gain=0,feedback=0)
    b,br,_,bs=doo_sabin(mesh,{'w1':.65})
    np.testing.assert_array_equal(a.xyz,b.xyz)
    np.testing.assert_array_equal(a.faces,b.faces)
    np.testing.assert_array_equal(roles,br)
    np.testing.assert_array_equal(state['parent_faces'],bs['parent_faces'])


def test_repeated_dual_has_exact_multiparent_connected_incidence():
    mesh=carrier();roles=None
    for _ in range(3):
        before=len(mesh.faces);mesh,roles,_,state=step(mesh,roles)
        assert state['parent_faces'].max()<before
        t=topology(mesh)
        assert len(mesh.xyz)-len(t['edges'])+len(mesh.faces)==2
        assert (t['degree']==4).all()
        nt=topology(native(mesh));assert len(native(mesh).xyz)-len(nt['edges'])+len(native(mesh).faces)==2


def test_current_geometry_changes_next_controls_and_rest_ablation_does_not():
    mesh,roles,_,_=step(carrier())
    a,_,_,sa=step(mesh,roles)
    frozen,_,_,sf=step(mesh,roles,source='rest')
    assert np.max(np.abs(a.xyz-frozen.xyz))>1
    altered=type(mesh)(mesh.xyz*np.array([1.3,.7,1.]),mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    _,_,_,changed=step(altered,roles)
    _,_,_,still=step(altered,roles,source='rest')
    assert np.max(abs(changed['resolved_w1']-sa['resolved_w1']))>.001
    np.testing.assert_array_equal(sf['resolved_w1'],still['resolved_w1'])


def test_rigid_transform_and_scale_covariance():
    mesh,roles,_,_=step(carrier())
    a,_,_,_=step(mesh,roles)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1.]])
    altered=type(mesh)(mesh.xyz@rotation.T*2+[13,27,91],mesh.faces,mesh.classes,
        mesh.rest@rotation.T*2+[13,27,91],mesh.anchors,mesh.generation)
    b,_,_,_=step(altered,roles)
    np.testing.assert_allclose(b.xyz,a.xyz@rotation.T*2+[13,27,91],atol=2e-10,rtol=1e-12)


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):step(carrier(),fold_gain=float('nan'))
    with pytest.raises(ValueError):step(carrier(),source='generation_number')


def test_actual_newborn_origin_roles_change_next_folding_direction():
    from cheshire.dual_subdivision import FACE,EDGE,VERTEX
    mesh,roles,_,_=step(carrier(),fold_gain=0,feedback=0)
    _,_,_,state=step(mesh,roles,fold_gain=0,feedback=0,role_gain=.2)
    support=state['feature_support'][state['input_corner_face']]
    corner_role=roles[state['input_corner_face']]
    offset=state['resolved_corner_offset']
    np.testing.assert_allclose(offset[corner_role==EDGE],-.2*support[corner_role==EDGE])
    np.testing.assert_allclose(offset[corner_role==VERTEX],.2*support[corner_role==VERTEX])
    assert np.all(offset[corner_role==FACE]==0)


def test_fan_split_preserves_nonplanar_native_area_and_centroid():
    mesh,_,_,_=step(carrier());mesh.xyz[2]+=[31,57,24]
    old=native(mesh);split,state=refine_fan(mesh);new=native(split)
    def moments(m):
        p=m.xyz[m.faces[:,:3]];area=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2
        return area.sum(),(area[:,None]*p.mean(1)).sum(0)
    a,b=moments(old),moments(new)
    np.testing.assert_allclose(a[0],b[0],rtol=1e-13)
    np.testing.assert_allclose(a[1],b[1],rtol=1e-13)
    assert len(split.faces)==sum((mesh.faces>=0).sum(1))
    assert len(state['parent_face'])==len(split.faces)
    with pytest.raises(ValueError,match='centroid-fan'):refine_fan(split)
