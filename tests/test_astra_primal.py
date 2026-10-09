import numpy as np
from cheshire.reference_subdivision import cube,ArrayMesh,subdivide
from cheshire.astra_primal import features,step


def test_zero_feedback_full_placement_equals_reference():
    mesh=cube()
    params=dict(wf=-.08,we=.06,wp=.08,w1=-.1,w2=-1.2,w3=-.35,w4=.9)
    expected,_,_=subdivide(mesh,params)
    actual,_,_=step(mesh,**params)
    np.testing.assert_allclose(actual.xyz,expected.xyz,rtol=0,atol=2e-13)
    np.testing.assert_array_equal(actual.faces,expected.faces)


def test_features_cyclic_invariant_and_scale_invariant():
    mesh=cube();mesh.xyz[6]+=[70,130,210]
    base=features(mesh)[2]
    changed=ArrayMesh(mesh.xyz*3.1,np.roll(mesh.faces,2,axis=1),mesh.classes,mesh.rest,mesh.anchors,0)
    result=features(changed)[2]
    for key in base:np.testing.assert_allclose(result[key],base[key],rtol=1e-12,atol=1e-12)


def test_current_features_differ_from_frozen_carrier():
    mesh=cube();mesh.xyz[6]+=[70,130,210]
    a,_,sa=step(mesh,intrinsic=1,source='current')
    b,_,sb=step(mesh,intrinsic=1,source='rest')
    assert np.max(abs(sa['combined_signal']-sb['combined_signal']))>.01
    assert np.max(abs(a.xyz-b.xyz))>1


def test_reflection_equivariance():
    mesh=cube();mesh,_,_=step(mesh,intrinsic=1,spatial=.8)
    reflection=np.array([-1,1,1])
    reflected=ArrayMesh(mesh.xyz*reflection,mesh.faces[:,::-1],mesh.classes,mesh.rest*reflection,mesh.anchors,mesh.generation)
    out,_,_=step(mesh,intrinsic=1,spatial=.8)
    mirrored,_,_=step(reflected,intrinsic=1,spatial=.8)
    from scipy.spatial import cKDTree
    assert cKDTree(out.xyz*reflection).query(mirrored.xyz)[0].max()<1e-9


def test_optional_support_scale_and_stencil_are_independent():
    from cheshire.task36_growth import carrier
    mesh=carrier(height=8000.)
    _,_,plain=step(mesh)
    _,_,scaled=step(mesh,support_normalization=True)
    _,_,signed=step(mesh,signed_stencil=True)
    assert np.any(signed['resolved_w4']<0) and np.any(signed['resolved_w4']>0)
    np.testing.assert_array_equal(plain['resolved_w4'],scaled['resolved_w4'])
    np.testing.assert_array_equal(plain['resolved_wf'],signed['resolved_wf'])
    assert np.all(abs(scaled['resolved_wf'])<=abs(plain['resolved_wf']))


def test_default_geometry_unchanged_by_explicit_false_options():
    mesh=cube();mesh,_,_=step(mesh)
    a,_,_=step(mesh,intrinsic=1)
    b,_,_=step(mesh,intrinsic=1,signed_stencil=False,support_normalization=False)
    np.testing.assert_array_equal(a.xyz,b.xyz)
    np.testing.assert_array_equal(a.faces,b.faces)
