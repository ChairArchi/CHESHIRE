import numpy as np
import pytest
from scipy.spatial import cKDTree
from cheshire.task36_growth import carrier,step,native
from cheshire.reference_subdivision import topology


def test_neutral_closed_square_without_hidden_silhouette():
    m=carrier();assert np.array_equal(np.ptp(m.xyz,axis=0),[1000,1000,4000])
    for z in np.unique(m.xyz[:,2]):assert np.array_equal(np.sort(m.xyz[m.xyz[:,2]==z,:2],axis=0),np.array([[-500,-500],[-500,-500],[500,500],[500,500]]))
    t=topology(m);assert len(m.xyz)-len(t['edges'])+len(m.faces)==2


@pytest.mark.parametrize('mode',['interpolating','coupled'])
def test_reflection_quarter_turn_and_closed_oriented_growth(mode):
    m=carrier()
    for _ in range(3):m,_=step(m,mode=mode,vertex_gain=.3,vertex_memory=.4)
    t=topology(native(m));assert len(native(m).xyz)-len(t['edges'])+len(native(m).faces)==2
    for transform in [np.diag([-1,1,1]),np.diag([1,-1,1]),np.array([[0,-1,0],[1,0,0],[0,0,1]])]:
        distance,index=cKDTree(m.xyz).query(m.xyz@transform.T)
        assert distance.max()<1e-9
        assert len(np.unique(index))==len(m.xyz)


def test_interpolating_parent_positions_and_actual_corner_ancestry():
    m=carrier();child,op=step(m)
    assert np.array_equal(child.xyz[:len(m.xyz)],m.xyz)
    assert np.array_equal(child.faces[:,1],op['parent_corner'])
    assert np.array_equal(op['parent_face_vertices'][op['parent_face']],m.faces.repeat(4,axis=0))
    grandchild,nextop=step(child)
    assert (nextop['incoming_point_classes']==1).sum()==len(op['input_edges'])
    assert (nextop['incoming_point_classes']==2).sum()==len(m.faces)
    assert np.count_nonzero(np.linalg.norm(nextop['face_vector'],axis=1))>np.count_nonzero(np.linalg.norm(op['face_vector'],axis=1))


def test_sampling_control_adds_no_fold_and_same_topology():
    m=carrier();sampling,_=step(m,active=False);folded,_=step(m)
    assert np.array_equal(sampling.faces,folded.faces)
    assert np.max(np.abs(sampling.xyz-folded.xyz))>50
    assert np.array_equal(np.ptp(sampling.xyz,axis=0),[1000,1000,4000])


@pytest.mark.parametrize('mode',['interpolating','coupled'])
def test_closed_cap_and_end_plane_stay_exact(mode):
    m=carrier()
    for _ in range(3):m,_=step(m,mode=mode,vertex_gain=.3,vertex_memory=.3)
    fixed=(m.rest[:,2]==0)|(m.rest[:,2]==4000)
    np.testing.assert_array_equal(m.xyz[fixed],m.rest[fixed])


def test_current_geometry_feedback_changes_same_input_operation():
    m=carrier()
    for _ in range(3):m,_=step(m)
    a,oa=step(m,source='current');b,ob=step(m,source='rest')
    assert np.array_equal(a.faces,b.faces)
    assert np.max(np.abs(oa['support_radius']-ob['support_radius']))>1
    assert np.max(np.abs(a.xyz-b.xyz))>1


@pytest.mark.parametrize('parameter',[{'face_gain':float('nan')},{'edge_gain':2},{'vertex_memory':-1},{'diagonal_tension':3},{'direction':'unknown'}])
def test_invalid_request_rejected_without_fallback(parameter):
    with pytest.raises(ValueError):step(carrier(),**parameter)


def test_deterministic_native_geometry():
    a=carrier();b=carrier()
    for _ in range(3):a,_=step(a);b,_=step(b)
    np.testing.assert_array_equal(native(a).xyz,native(b).xyz)
    np.testing.assert_array_equal(native(a).faces,native(b).faces)


def test_exact_component_reconstruction_and_separate_averaging():
    m=carrier();m,_=step(m)
    common=dict(mode='coupled',vertex_memory=.2,vertex_gain=.3,diagonal_tension=1.6)
    a,_=step(m,**common);b,op=step(m,**common,decompose=True)
    np.testing.assert_allclose(a.xyz,b.xyz,rtol=0,atol=1e-12)
    pre,_=step(m,active=False)
    np.testing.assert_allclose(b.xyz-pre.xyz,sum(op[k] for k in ['averaging_component','stencil_component','normal_component']),rtol=0,atol=1e-12)
    no_average,_=step(m,**common,averaging_gain=0,decompose=True)
    np.testing.assert_allclose(b.xyz-no_average.xyz,op['averaging_component'],rtol=0,atol=1e-12)


def test_free_cap_preserves_plane_without_freezing_xy():
    m=carrier();m,_=step(m,mode='coupled',cap_mode='plane_only',vertex_gain=.3,vertex_memory=.2)
    fixed=(m.rest[:,2]==0)|(m.rest[:,2]==4000)
    np.testing.assert_array_equal(m.xyz[fixed,2],m.rest[fixed,2])
    assert np.max(abs(m.xyz[fixed,:2]-m.rest[fixed,:2]))>1


def test_vf_split_preserves_actual_nonplanar_parent_triangle_surface():
    import trimesh
    m,_=step(carrier());before=native(m)
    child,_=step(m,active=False,surface='vf');after=native(child)
    parent_model=trimesh.Trimesh(vertices=before.xyz,faces=before.faces[:,:3],process=False)
    samples=np.concatenate([after.xyz,after.xyz[after.faces[:,:3]].mean(1)])
    _,distance,_=trimesh.proximity.closest_point_naive(parent_model,samples)
    assert distance.max()<1e-9
    child_model=trimesh.Trimesh(vertices=after.xyz,faces=after.faces[:,:3],process=False)
    assert abs(child_model.area-parent_model.area)<1e-7
    grandchild,_=step(child,active=False,surface='vf')
    grand_model=trimesh.Trimesh(vertices=native(grandchild).xyz,faces=native(grandchild).faces[:,:3],process=False)
    assert abs(grand_model.area-child_model.area)<1e-7
