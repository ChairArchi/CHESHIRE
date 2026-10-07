"""Independent small closed-fixture equations, not visual fidelity assertions."""
import numpy as np
import pytest
from compas.datastructures import Mesh
from cheshire.reference_subdivision import cube,subdivide,topology,GLOBAL_SCALE,LOCAL_INCIDENT_SCALE
from cheshire.sharp_subdivision import sharp_subdivide_once


def scalar_oracle(m,w,um=None,unknown=0.,global_scale=False):
    # Direct loops over incidence and literal equations, independent of array reductions.
    x=m.xyz;q=m.faces;t=topology(m);edges=t['edges'];centres=[];normals=[];scale=[]
    for f in q:
        ids=[int(v) for v in f if v>=0];p=x[ids];c=sum(p)/len(p)
        n=sum(np.cross(p[j]-c,p[(j+1)%len(p)]-c) for j in range(len(p)))
        n=n/np.linalg.norm(n) if np.linalg.norm(n) else n
        centres.append(c);normals.append(n)
        scale.append(sum(np.linalg.norm(p[j]-p[(j+1)%len(p)]) for j in range(len(p)))/len(p))
    global_length=sum(np.linalg.norm(x[a]-x[b]) for a,b in edges)/len(edges)
    F=[];um=um or {};u=[um.get(f'({d},{d})',unknown) for d in t['degree']]
    for j,f in enumerate(q):
        ids=[int(v) for v in f if v>=0];p=centres[j]
        if m.generation:
            kinds=list(m.classes[ids])
            if kinds.count(0)==1 and kinds.count(1)==2 and kinds.count(2)==1:
                V=x[ids[kinds.index(0)]];B=x[ids[kinds.index(2)]];E=sum(x[v] for v in ids if m.classes[v]==1)
                p=((V*(1+w.get('w3',0))+B*(1-w.get('w3',0)))*(1+w.get('w4',0))+E*(1-w.get('w4',0)))/4
        p=p+normals[j]*w.get('wf',0)*(global_length if global_scale else scale[j])
        p=p+w.get('w6',0)*sum((x[v]-p)*u[v] for v in ids);F.append(p)
    E=[]
    for k,(a,b) in enumerate(edges):
        fs=[j for j,face in enumerate(q) if a in face and b in face]
        wa=w.get('w1',0);p=((F[fs[0]]+F[fs[1]])*(1+wa)+(x[a]+x[b])*(1-wa))/4
        p+=sum(normals[j] for j in fs)/2*w.get('we',0)*(global_length if global_scale else sum(scale[j] for j in fs)/2)
        p+=w.get('w7',0)*((x[a]-p)*u[a]+(x[b]-p)*u[b]);E.append(p)
    V=[]
    for v,p in enumerate(x):
        fs=[j for j,f in enumerate(q) if v in f];incident=[(a,b) for a,b in edges if v in (a,b)]
        n=len(incident);Fb=sum(F[j] for j in fs)/len(fs);R=sum((x[a]+x[b])/2 for a,b in incident)/n
        normal=sum(normals[j] for j in fs);normal=normal/np.linalg.norm(normal) if np.linalg.norm(normal) else normal
        wc=w.get('w2',0);out=(Fb*(1+wc)+R*(2-wc)+p*(n-3))/n
        out+=normal*w.get('wp',0)*(global_length if global_scale else sum(scale[j] for j in fs)/len(fs));V.append(out)
    return np.concatenate([V,E,F])


@pytest.mark.parametrize('mode',[GLOBAL_SCALE,LOCAL_INCIDENT_SCALE])
@pytest.mark.parametrize('row',[{},dict(wf=.13),dict(w1=-1.05,w2=-.9,we=-.05,wp=.045),
    dict(wf=-.28,w1=.8,we=.32,w2=-2.8,wp=.52,w3=-.9,w4=.5,w6=.25,w7=.65)])
def test_literal_independent_equations(mode,row):
    m=cube();m.xyz=m.xyz@np.array([[1,.2,0],[0,.7,.13],[.1,0,1.2]])
    for g in range(2):
        r,_,_=subdivide(m,dict(weights=row,u_map={'(3,3)':1.,'(4,4)':-.2}),scale_mode=mode)
        expected=scalar_oracle(m,row,{'(3,3)':1.,'(4,4)':-.2},global_scale=mode==GLOBAL_SCALE)
        np.testing.assert_allclose(r.xyz,expected,rtol=2e-13,atol=2e-10)
        assert np.isfinite(r.xyz).all();m=r


def test_wf_downstream_and_original_midpoint_dependency():
    m=cube();a,_,_=subdivide(m,{});b,_,_=subdivide(m,{'wf':.1})
    # cube scale 1000: all faces +100 n; edge +25(n1+n2), vertex +100 sum(n)/(3*3).
    np.testing.assert_allclose(b.xyz[:8]-a.xyz[:8],np.sign(m.xyz)*100/9)
    assert np.all(np.linalg.norm(b.xyz[8:20]-a.xyz[8:20],axis=1)>0)
    assert np.all(np.linalg.norm(b.xyz[20:]-a.xyz[20:],axis=1)>0)
    c,_,_=subdivide(m,{'we':.1})
    np.testing.assert_array_equal(c.xyz[:8],a.xyz[:8])
    d,_,_=subdivide(m,{'wf':.1,'w2':-1});e,_,_=subdivide(m,{'w2':-1})
    np.testing.assert_array_equal(d.xyz[:8],e.xyz[:8])


def test_neutral_standard_compas_and_legacy_unchanged():
    m=cube();a,_,_=subdivide(m,{})
    old=Mesh.from_vertices_and_faces(m.xyz.tolist(),m.faces.tolist());cc=old.subdivided(scheme='catmullclark',k=1)
    legacy=sharp_subdivide_once(old,{},current_generation=0)
    # Structural generated point correspondence, not nearest-point matching.
    for v in old.vertices():np.testing.assert_allclose(a.xyz[v],cc.vertex_coordinates(v),atol=1e-12)
    for j,(u,v) in enumerate(topology(m)['edges']):
        k=(set(cc.vertex_neighbors(int(u)))&set(cc.vertex_neighbors(int(v)))).pop()
        np.testing.assert_allclose(a.xyz[8+j],cc.vertex_coordinates(k),atol=1e-12)
    assert {tuple(p) for p in a.xyz}=={tuple(cc.vertex_coordinates(v)) for v in cc.vertices()}
    assert {tuple(legacy.mesh.vertex_coordinates(v)) for v in legacy.mesh.vertices()}=={tuple(cc.vertex_coordinates(v)) for v in cc.vertices()}


def test_intrinsic_is_deterministic_and_nonuniform():
    m,_,_=subdivide(cube(),{'wf':-.28,'w1':.8,'we':.32,'w2':-2.8,'wp':.52})
    rule=dict(field='ORIGINAL_EDGE_DISTANCE',start=2,controls={'wf':[-.12,.12],'w3':[-.5,.5]})
    a,meta,s=subdivide(m,{'w3':-.6,'w4':.35},intrinsic=rule)
    b,_,_=subdivide(m,{'w3':-.6,'w4':.35},intrinsic=rule)
    np.testing.assert_array_equal(a.xyz,b.xyz)
    assert np.ptp(s['intrinsic_signal'])>0;assert meta['eq4_eligible']==24


def test_invalid_open_mesh_rejected():
    m=cube();m.faces=m.faces[:-1]
    with pytest.raises(ValueError,match='Closed'):subdivide(m,{})


def test_geometric_fold_locks_retain_actual_input_positions_only_where_declared():
    m,_,_=subdivide(cube(),{'wf':-.28,'w1':.8,'we':.32,'w2':-2.8,'wp':.52})
    rule=dict(field='NORMAL_VARIATION',start=2,controls={},lock_threshold=.2)
    a,meta,state=subdivide(m,{'w3':-.6,'w4':.35},intrinsic=rule)
    b,_,_=subdivide(m,{'w3':-.6,'w4':.35})
    mask=state['vertex_lock_mask'];assert mask.any();assert meta['locked_vertex_count']==mask.sum()
    np.testing.assert_array_equal(a.xyz[:len(m.xyz)][mask],m.xyz[mask])
    np.testing.assert_array_equal(a.xyz[:len(m.xyz)][~mask],b.xyz[:len(m.xyz)][~mask])
    np.testing.assert_array_equal(a.xyz[len(m.xyz):],b.xyz[len(m.xyz):])
