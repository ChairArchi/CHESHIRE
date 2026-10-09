import copy
import numpy as np
import pytest
from compas.datastructures import Mesh
from compas.datastructures.mesh.subdivision import mesh_subdivide_doosabin
from cheshire.reference_subdivision import ArrayMesh,cube,subdivide,topology
from cheshire.dual_subdivision import doo_sabin as bounded_ds
from cheshire.polygon_dual_subdivision import doo_sabin,polygon_corners
from cheshire.regional_generation import birth,inherit,coarse_edit,regional_controls,advance


def prism(n):
    a=np.arange(n)*2*np.pi/n
    xyz=np.array([[np.cos(t),np.sin(t),z] for z in (-1,1) for t in a])
    fs=[list(range(n-1,-1,-1)),list(range(n,n*2))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
    q=np.full((len(fs),max(n,4)),-1,np.int64)
    for i,f in enumerate(fs):q[i,:len(f)]=f
    return ArrayMesh(xyz,q,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(fs),3),-1,np.int64))


@pytest.mark.parametrize('n',[3,4,5,8])
def test_polygon_neutral_matches_independent_compas(n):
    m=prism(n);out,_,meta,_=doo_sabin(m,dict(w1=0,wf=0))
    cm=Mesh.from_vertices_and_faces(m.xyz.tolist(),[f[f>=0].tolist() for f in m.faces])
    expected=mesh_subdivide_doosabin(cm)
    # COMPAS emits face corners first in input order, then its own F/V/E ordering.
    assert np.allclose(out.xyz,np.array(expected.vertices_attributes('xyz')),rtol=0,atol=1e-15)
    assert len(out.faces)==expected.number_of_faces()
    assert len(out.xyz)-len(topology(out)['edges'])+len(out.faces)==2
    assert meta['extended_polygon_count']==(2 if n>4 else 0)


def test_bounded_quad_exact_compatibility_and_control_validation():
    m=cube();a,ar,_,ast=bounded_ds(m,dict(w1=.6,wf=.03));b,br,_,bst=doo_sabin(m,dict(w1=.6,wf=.03))
    for k in ('xyz','faces','rest','classes','anchors'):assert np.array_equal(getattr(a,k),getattr(b,k))
    assert np.array_equal(ar,br);assert np.array_equal(ast['parent_faces'],bst['parent_faces'])
    row=dict(weights=dict(wf=.1,w1=.2,w2=-.3))
    x,_,_=subdivide(m,row);y,_,_=subdivide(m,row,resolved_controls=None)
    assert np.array_equal(x.xyz,y.xyz)
    with pytest.raises(ValueError):subdivide(m,row,resolved_controls=dict(wf=np.ones(5)))


@pytest.mark.parametrize('kind,levels',[('opening',1),('recess',1),('recess',2)])
def test_edit_closes_and_has_exact_euler_and_region_ancestry(kind,levels):
    m=cube()
    for _ in range(2):m,_,_=subdivide(m,dict(weights={}))
    members,_=birth(m);roles=np.full(len(m.faces),-1,np.int8)
    out,_,membership,meta,st=coarse_edit(m,roles,members,dict(kind=kind,levels=levels,ratio=.6,depth=.3))
    assert meta['Euler_after']==(0 if kind=='opening' else 2)
    assert np.allclose(membership.sum(1),1)
    assert (membership[st['channel_faces']]==[0,0,0,1]).all()
    out,_,_,_=doo_sabin(out,dict(w1=.6,wf=.03))
    out,_,_,_=doo_sabin(out,dict(w1=.6,wf=.03))
    out,_,_=subdivide(out,dict(weights=dict(wf=.02,w1=.1)))
    assert np.isfinite(out.xyz).all();assert (out.faces>=0).all()
    assert len(out.xyz)-len(topology(out)['edges'])+len(out.faces)==meta['Euler_after']


def test_membership_multisupport_and_permutation_geometry_descriptor():
    members=np.eye(4);parents=np.array([[0,1,-1],[1,2,3]])
    assert np.allclose(inherit(members,parents),[[.5,.5,0,0],[0,1/3,1/3,1/3]])
    m=prism(5);a,_=birth(m,'fold');order=np.arange(len(m.faces))[::-1]
    shuffled=copy.deepcopy(m);shuffled.faces=m.faces[order];shuffled.anchors=m.anchors[order]
    b,_=birth(shuffled,'fold');assert np.array_equal(a[order],b)


def test_regional_contrast_zero_matches_base_and_one_changes_actual_geometry():
    m=cube()
    for _ in range(2):m,_,_=subdivide(m,dict(weights={}))
    members,_=birth(m);roles=np.full(len(m.faces),-1,np.int8)
    spec=dict(scheme='REFERENCE_COUPLED',generation=3,row=dict(weights=dict(wf=.11,w1=-.7,w2=-.6,w3=-.6,w4=.35)),scale='LOCAL_INCIDENT_SCALE',intrinsic=None)
    a,_,_=subdivide(m,spec['row']);b,_,mb,_,_=advance(m,roles,members,spec,dict(contrast=0,memory='persistent',descriptor='axis'))
    assert np.array_equal(a.xyz,b.xyz)
    c,_,_,_,_=advance(m,roles,members,spec,dict(contrast=.8,memory='persistent',descriptor='axis'))
    assert not np.allclose(a.xyz,c.xyz);assert np.array_equal(mb,members[np.repeat(np.arange(len(m.faces)),4)])


def test_disconnected_vertex_fans_are_rejected_even_when_each_edge_has_two_faces():
    a=cube();b=cube();b.xyz+=1000
    # Two spheres share only one vertex: closed edges, but a nonmanifold vertex.
    xyz=np.concatenate([a.xyz,b.xyz[1:]])
    remap=np.r_[0,np.arange(8,15)]
    faces=np.concatenate([a.faces,remap[b.faces]])
    m=ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(faces),3),-1,np.int64))
    topology(m)
    with pytest.raises(ValueError,match='fan'):doo_sabin(m,dict(w1=.6,wf=.03))


def test_invalid_checkpoint_generation_and_empty_support_fail_explicitly():
    m=cube();roles=np.full(6,-1,np.int8)
    with pytest.raises(ValueError,match='generation'):
        advance(m,roles,None,dict(generation=2),dict(memory='persistent'))
    with pytest.raises(ValueError,match='Empty'):
        inherit(np.eye(4),np.array([[-1,-1]]))
