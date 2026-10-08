import numpy as np
from dataclasses import replace
from cheshire.reference_subdivision import cube, subdivide
from cheshire.task32_morphology import spring_system, growth_energy, signed_volume_gradient, triangles
from cheshire.task32_spectral import cotan_system, spectral_field, transport_coordinates,curvature_limit


def test_volume_constraint_energy_gradient_and_translation_invariance():
    m=cube(); edges,lap,scale=spring_system(m);base=m.xyz/scale
    tri=triangles(m);target_volume,_=signed_volume_gradient(base,tri)
    shifted,_=signed_volume_gradient(base+[.7,-1.2,.4],tri)
    np.testing.assert_allclose(shifted,target_volume,atol=1e-12)
    x=base+np.arange(base.size).reshape(base.shape)*.007
    target=np.linalg.norm(base[edges[:,0]]-base[edges[:,1]],axis=1)*1.1
    anchors=np.full(len(base),.01)
    def energy(z):return growth_energy(z,base,edges,target,lap,.03,anchors,(tri,target_volume,12))
    _,gradient=energy(x);flat=x.ravel();numeric=[]
    for i in range(len(flat)):
        d=np.zeros_like(flat);d[i]=1e-6
        numeric.append((energy(flat+d)[0]-energy(flat-d)[0])/2e-6)
    np.testing.assert_allclose(gradient,numeric,rtol=2e-6,atol=2e-9)


def test_cotan_constant_nullspace_symmetry_and_rigid_motion_invariance():
    m,_ ,_=subdivide(cube(),{})
    lap,area=cotan_system(m)
    np.testing.assert_allclose(lap.toarray(),lap.toarray().T,atol=1e-14)
    np.testing.assert_allclose(lap@np.ones(len(area)),0,atol=1e-13)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]],float)
    rotated=replace(m,xyz=m.xyz@rotation+[700,-900,400])
    lap2,area2=cotan_system(rotated)
    np.testing.assert_allclose(lap2.toarray(),lap.toarray(),atol=1e-13)
    np.testing.assert_allclose(area2,area,atol=1e-13)


def test_spectral_residual_and_positive_cc_field_transport():
    m,_,_=subdivide(cube(),{})
    coordinates,meta,state=spectral_field(m,dict(modes=[2,4]))
    assert meta['nonconstant_relative_residual_max']<1e-7
    assert meta['mass_orthogonality_max']<1e-8
    out,_,operator=subdivide(m,{})
    transported=transport_coordinates(coordinates,operator,m)
    assert transported.shape==(len(out.xyz),2)
    assert transported.min()>=coordinates.min()-1e-14
    assert transported.max()<=coordinates.max()+1e-14
    np.testing.assert_array_equal(transported[:len(m.xyz)],coordinates)


def test_curvature_limit_has_physical_scale_covariance():
    m,_,_=subdivide(cube(),{})
    bound,curvature=curvature_limit(m,.3)
    # Remove the declared 1/1000 regularizer when comparing scaling; compare
    # the actual curvature estimate independently, not a mirrored clamp rule.
    doubled=replace(m,xyz=m.xyz*2)
    _,curvature2=curvature_limit(doubled,.3)
    np.testing.assert_allclose(curvature2,curvature/2,rtol=1e-10,atol=1e-12)
    assert (bound>0).all() and np.isfinite(bound).all()
