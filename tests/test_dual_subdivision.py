"""Independent literal masks and incidence checks, not visual-success tests."""
import numpy as np
import pytest
from cheshire.reference_subdivision import cube,ArrayMesh,topology,subdivide,LOCAL_INCIDENT_SCALE,GLOBAL_SCALE
from cheshire.dual_subdivision import doo_sabin,FACE,EDGE,VERTEX


def tetrahedron():
    x=np.array([[1,1,1],[-1,-1,1],[-1,1,-1],[1,-1,-1]],float)*300
    q=np.array([[0,2,1,-1],[0,1,3,-1],[0,3,2,-1],[1,2,3,-1]])
    return ArrayMesh(x,q,np.full(4,-1,np.int8),x.copy(),np.full((4,3),-1,np.int64))


@pytest.mark.parametrize('make',[cube,tetrahedron])
@pytest.mark.parametrize('controls',[{},dict(w1=.6,wf=.03),dict(w1=-.3,wf=-.04)])
@pytest.mark.parametrize('scale_mode',[LOCAL_INCIDENT_SCALE,GLOBAL_SCALE])
def test_published_mask_independent_scalar_loops(make,controls,scale_mode):
    m=make();m.xyz=m.xyz@np.array([[1,.2,0],[0,.8,.17],[.12,0,1.1]])
    result,roles,_,state=doo_sabin(m,controls,scale_mode=scale_mode)
    expected=[];t=topology(m)
    glob=sum(np.linalg.norm(m.xyz[a]-m.xyz[b]) for a,b in t['edges'])/len(t['edges'])
    for face in m.faces:
        face=face[face>=0];p=m.xyz[face];k=len(p);c=sum(p)/k
        normal=sum(np.cross(p[i]-c,p[(i+1)%k]-c) for i in range(k));normal/=np.linalg.norm(normal)
        scale=glob if scale_mode==GLOBAL_SCALE else sum(np.linalg.norm(p[i]-p[(i+1)%k]) for i in range(k))/k
        w=controls.get('w1',0);amount=controls.get('wf',0)*scale
        for i in range(k):
            if k==4:point=((2.25+2*w)*p[i]+(.75-w)*(p[(i+1)%k]+p[(i-1)%k])+.25*p[(i+2)%k])/4
            else:point=(2/3)*(1+w/2)*p[i]+(1-w)*(p[(i+1)%k]+p[(i-1)%k])/6
            expected.append(point+normal*amount)
    np.testing.assert_allclose(result.xyz,expected,rtol=2e-13,atol=1e-10)
    rt=topology(result);assert np.all(rt['degree']==4)
    assert len(result.xyz)-len(rt['edges'])+len(result.faces)==2
    assert np.array_equal(np.bincount(roles),[len(m.faces),len(t['edges']),len(m.xyz)])
    assert state['parent_faces'].shape==(len(result.faces),4)


def test_structural_groups_produce_actual_different_masks_and_replay():
    m,roles,_,_=doo_sabin(cube(),{'w1':.6,'wf':.03})
    groups={'FACE':{'w1':.85,'wf':.03},'EDGE':{'w1':-.1,'wf':-.02},'VERTEX':{'w1':.5,'wf':.065}}
    a,newroles,_,state=doo_sabin(m,{'w1':.6,'wf':.03},face_roles=roles,groups=groups)
    b,_,_,other=doo_sabin(m,{'w1':.6,'wf':.03},face_roles=roles,groups=groups)
    np.testing.assert_array_equal(a.xyz,b.xyz)
    for role,value in [(FACE,.85),(EDGE,-.1),(VERTEX,.5)]:assert np.all(state['resolved_w1'][roles==role]==value)
    for key in state:np.testing.assert_array_equal(state[key],other[key])


def test_multi_parent_ancestry_never_invents_single_owner():
    m=cube();m.anchors[:,0]=np.arange(6)
    out,_,_,state=doo_sabin(m,{'w1':.6})
    np.testing.assert_array_equal(out.anchors[:6,0],np.arange(6))
    assert np.all(out.anchors[6:,0]==-1)
    assert np.all((state['parent_faces'][6:18]>=0).sum(1)==2)
    assert np.all((state['parent_faces'][18:]>=0).sum(1)==3)


def test_real_ds_to_cc_provenance_fallback_and_restored_next_step():
    ds,_,_,_=doo_sabin(cube(),{'w1':.6,'wf':.03})
    cc,meta,_=subdivide(ds,{'w1':-.2,'w3':-.8,'w4':.5})
    assert meta['eq4_eligible']==0 and meta['eq4_fallback']==len(ds.faces)
    _,next_meta,_=subdivide(cc,{'w3':-.8,'w4':.5})
    assert next_meta['eq4_eligible']==len(cc.faces)


def test_open_or_invalid_group_input_is_explicitly_rejected():
    m=cube();m.faces=m.faces[:-1]
    with pytest.raises(ValueError,match='Closed'):doo_sabin(m,{})
    with pytest.raises(ValueError,match='group'):doo_sabin(cube(),{},groups={'BODY':{}})
