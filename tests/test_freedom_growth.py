"""Independent geometric contracts for exploratory freedom growth.

Transverse intersections are intentionally not a rejection condition here.
Tests check actual placement, source separation, ancestry and numeric behavior.
"""
from dataclasses import replace
import numpy as np
import pytest
from cheshire.reference_subdivision import topology
from cheshire.task36_growth import carrier,native
from cheshire.freedom_growth import step,observe


def specimen():
    return native(carrier(side=1000.,height=4000.,divisions=2))


def triangle_cross(mesh):
    p=mesh.xyz[mesh.faces[:,:3]]
    return np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])


@pytest.mark.parametrize('frame',['current','coherent'])
def test_zero_response_refinement_preserves_each_actual_parent_triangle(frame):
    mesh=specimen();original=mesh.xyz.copy()
    out,meta,state,memory=step(mesh,response='zero',tangent=0.,radius=210.,frame=frame)
    nv=len(mesh.xyz);edges=state['input_edges'];parents=state['parent_faces']
    assert np.array_equal(mesh.xyz,original)
    assert np.array_equal(out.xyz[:nv],original)
    assert np.array_equal(out.xyz[nv:],original[edges].mean(1))
    assert np.array_equal(state['base_xyz'],out.xyz)
    assert np.array_equal(parents,np.repeat(np.arange(len(mesh.faces)),4))
    old_cross=triangle_cross(mesh);new_cross=triangle_cross(out)
    np.testing.assert_allclose(new_cross,old_cross[parents]/4,rtol=1e-12,atol=1e-9)
    # Every child point has explicit support on its claimed parent's corners.
    parent_sets=[set(f[:3]) for f in mesh.faces]
    for face,parent in zip(out.faces[:,:3],parents):
        for vertex in face:
            support={int(vertex)} if vertex<nv else set(edges[vertex-nv])
            assert support<=parent_sets[parent]
    assert len(out.xyz)-len(topology(out)['edges'])+len(out.faces)==2
    assert meta['geometry_smoothing'] is False
    assert np.array_equal(memory['seed_xyz'][:nv],original)


def test_heat_coordinates_are_features_not_hidden_surface_replacement():
    mesh=specimen()
    out,meta,state,_=step(mesh,gain=0.,radius=700.,tangent=2.,refine=False,frame='coherent')
    assert np.max(np.linalg.norm(state['heat_feature_xyz']-mesh.xyz,axis=1))>10
    assert np.array_equal(out.xyz,mesh.xyz)
    assert np.array_equal(out.faces,mesh.faces)
    assert np.count_nonzero(state['resolved_displacement'])==0
    assert meta['heat_solve_relative_residual']<1e-10


@pytest.mark.parametrize('frame',['current','coherent'])
@pytest.mark.parametrize('scale',['parent','local'])
def test_scaled_geometry_radius_and_inherited_length_are_equivariant(frame,scale):
    mesh=specimen();factor=3.7
    scaled=replace(mesh,xyz=mesh.xyz*factor,rest=mesh.rest*factor)
    memory={'seed_xyz':mesh.xyz.copy(),'ancestor_scale':83.}
    scaled_memory={'seed_xyz':mesh.xyz*factor,'ancestor_scale':83.*factor}
    kwargs=dict(radius=235.,gain=.7,q0=.9,tangent=.35,rotation=.4,frame=frame,scale=scale)
    a,ma,sa,_=step(mesh,memory=memory,**kwargs)
    b,mb,sb,_=step(scaled,memory=scaled_memory,**dict(kwargs,radius=kwargs['radius']*factor))
    assert np.array_equal(a.faces,b.faces)
    np.testing.assert_allclose(b.xyz,a.xyz*factor,rtol=1e-11,atol=1e-8)
    np.testing.assert_allclose(sb['transferred_scalar'],sa['transferred_scalar'],rtol=1e-10,atol=1e-11)
    np.testing.assert_allclose(sb['observed_detail'],sa['observed_detail']*factor,rtol=1e-10,atol=1e-9)
    assert mb['requested_amplitude']==pytest.approx(ma['requested_amplitude']*factor)


def test_seed_observation_changes_features_but_uses_current_placement():
    mesh=specimen();deformed=mesh.xyz.copy()
    deformed[:,0]*=1.3;deformed[:,1]*=.8
    deformed[:,2]+=70*np.sin(mesh.xyz[:,0]/500.)
    incoming=replace(mesh,xyz=deformed)
    memory={'seed_xyz':mesh.xyz.copy(),'ancestor_scale':80.}
    a,_,sa,ma=step(incoming,memory=memory,source='current',radius=220.,gain=.8)
    b,_,sb,mb=step(incoming,memory=memory,source='seed',radius=220.,gain=.8)
    expected=observe(mesh.xyz,mesh.faces[:,:3],220.)[0]
    assert np.array_equal(sb['observed_xyz'],mesh.xyz)
    assert np.array_equal(sa['observed_xyz'],incoming.xyz)
    np.testing.assert_allclose(sb['observed_detail'],expected,atol=1e-10)
    assert np.max(abs(sa['observed_detail']-sb['observed_detail']))>1.
    assert np.array_equal(sa['base_xyz'],sb['base_xyz'])
    assert np.array_equal(sa['base_xyz'][:len(mesh.xyz)],incoming.xyz)
    assert np.max(np.linalg.norm(a.xyz-b.xyz,axis=1))>1.
    assert np.array_equal(ma['seed_xyz'],mb['seed_xyz'])
    assert np.array_equal(memory['seed_xyz'],mesh.xyz)


def test_coherent_frame_transfers_heat_observation_normals_without_xyz_smoothing():
    mesh=specimen()
    out,meta,state,_=step(mesh,frame='coherent',radius=270.,gain=.8,tangent=0.)
    observed=state['observed_normals'];edges=state['input_edges']
    expected=np.r_[observed,observed[edges].mean(1)]
    expected/=np.linalg.norm(expected,axis=1)[:,None]
    np.testing.assert_allclose(state['current_normal'],expected,atol=1e-12)
    np.testing.assert_allclose(np.cross(state['resolved_displacement'],expected),0.,atol=1e-10)
    nv=len(mesh.xyz)
    assert np.array_equal(state['base_xyz'][:nv],mesh.xyz)
    assert meta['parameters']['frame']=='coherent'
    assert meta['applied_normal_frame']=='coherent'
    assert meta['applied_frame_min_norm']==pytest.approx(1.)
    assert meta['applied_frame_near_zero']==0
    assert np.max(np.linalg.norm(out.xyz-state['base_xyz'],axis=1))>1.


def test_zero_normal_response_does_not_disable_explicit_tangential_control():
    mesh=specimen()
    out,_,state,_=step(mesh,response='zero',tangent=1.,radius=210.,refine=False)
    assert np.max(np.linalg.norm(out.xyz-mesh.xyz,axis=1))>1.
    np.testing.assert_allclose(np.sum(state['resolved_displacement']*state['current_normal'],axis=1),0.,atol=1e-10)


@pytest.mark.parametrize('response',['split','amplify','zero','oscillate'])
def test_finite_response_and_solve_for_declared_controls(response):
    out,meta,state,_=step(specimen(),response=response,radius=310.,gain=2.,q0=.2,tangent=.3)
    assert np.isfinite(out.xyz).all()
    assert np.isfinite(state['transferred_scalar']).all()
    assert np.isfinite(state['resolved_displacement']).all()
    assert meta['heat_solve_relative_residual']<1e-10


def test_split_response_remains_finite_for_small_positive_q0():
    # q0 is declared positive with no lower bound; its finite-input domain
    # must not turn algebraically bounded response into inf/inf.
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        out,_,state,_=step(specimen(),radius=210.,gain=1.,q0=1e-200,response='split')
    assert np.isfinite(out.xyz).all()
    assert np.isfinite(state['resolved_displacement']).all()


def test_oscillate_explicitly_rejects_scale_outside_declared_domain():
    with pytest.raises(ValueError,match='Oscillation scale below'):
        step(specimen(),response='oscillate',q0=1e-7)
