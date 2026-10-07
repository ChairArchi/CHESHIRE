"""Verify the experimental composition without changing reference-mask tests."""
from copy import deepcopy

import pytest
from compas.datastructures import Mesh
from compas.geometry import Box

from cheshire.creases import make_network,crease_subdivide_once
from cheshire.crease_folding import folded_crease_once,route_support


def test_zero_schedule_exact_reference_and_route_local_face_displacement_oracle():
    mesh=Mesh.from_shape(Box(2,2,2));original=deepcopy(mesh.__data__)
    net=make_network(mesh,'top',list(mesh.face_halfedges(0)),4,{})
    reference=crease_subdivide_once(mesh,(net,))
    zero=folded_crease_once(mesh,(net,),{'weights':{}})
    assert zero.mesh.__data__==reference.mesh.__data__ and zero.networks==reference.networks
    declaration={'band_hops':2,'weights':{'wf':.4},'u_map':{}}
    a=folded_crease_once(mesh,(net,),declaration)
    b=folded_crease_once(mesh,(net,),deepcopy(declaration))
    assert a.mesh.__data__==b.mesh.__data__ and a.networks==b.networks
    support=route_support(mesh,(net,),2)
    for r in a.metadata['combined_fold']['placement']:
        if r['point_class']=='face':
            f=r['source'];alpha=sum(support[v] for v in mesh.face_vertices(f))/len(mesh.face_vertices(f))
            expected=[p+alpha*.4*n for p,n in zip(reference.mesh.vertex_coordinates(r['point']),mesh.face_normal(f))]
            assert a.mesh.vertex_coordinates(r['point'])==pytest.approx(expected)
    assert any(a.mesh.vertex_coordinates(v)!=reference.mesh.vertex_coordinates(v) for v in a.mesh.vertices())
    assert mesh.__data__==original and a.mesh.is_closed() and a.mesh.is_manifold()
    following=crease_subdivide_once(a.mesh,a.networks,current_generation=1)
    assert all(e.sharpness==2 for e in following.networks[0].edges)
    assert all(e.root_edge in {r.vertices for r in net.edges} for e in following.networks[0].edges)
    with pytest.raises(ValueError):folded_crease_once(mesh,(net,),{'band_hops':2,'weights':{'w3':1}})


def test_large_taper_is_explicit_and_default_domain_is_preserved(monkeypatch):
    from cheshire import ornament
    from cheshire.ornament import OrnamentStage,source_history,topology_event
    from cheshire.execution import ExecutionBudget
    mesh=Mesh.from_vertices_and_faces([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],[[0,1,2,3]])
    stage=OrnamentStage('large','TaperedExtrusion',{'height_ratio':1.,'fraction':.2},{})
    calls=[]
    def backend(path):
        def execute(points,height,fraction):
            calls.append(height)
            center=[sum(p[a] for p in points)/len(points) for a in range(3)]
            upper=[[(1-fraction)*p[a]+fraction*center[a]+(height if a==2 else 0) for a in range(3)] for p in points]
            return [[points[i],points[(i+1)%4],upper[(i+1)%4],upper[i]] for i in range(4)]+[upper]
        return execute,{'test':'constructor oracle'}
    monkeypatch.setattr(ornament,'_load_backend',backend)
    kwargs=dict(selected_faces=[0],dll_path='explicit-test-backend',budget=ExecutionBudget(100,100))
    with pytest.raises(ValueError,match='Conservative'):topology_event(mesh,source_history(mesh),stage,**kwargs)
    assert not calls
    result=topology_event(mesh,source_history(mesh),stage,allow_large_taper=True,**kwargs)
    assert calls and result['mesh'].number_of_faces()==5 and result['mesh'].number_of_vertices()==8
    assert max(result['mesh'].vertex_coordinates(v)[2] for v in result['mesh'].vertices())==pytest.approx(1.)
