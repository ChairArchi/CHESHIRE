import copy
import numpy as np
import pytest
from cheshire.reference_subdivision import cube,subdivide,LOCAL_INCIDENT_SCALE
from cheshire.subdivision_pipeline import SubdivisionState,step,save_checkpoint,load_checkpoint


def initial():
    m=cube();return SubdivisionState(m,np.full(len(m.faces),-1,np.int8))


def ds(g,grouped=False):
    return dict(generation=g,scheme='REFERENCE_DOO_SABIN',scale=LOCAL_INCIDENT_SCALE,weights=dict(w1=.6,wf=.03),
        groups=dict(FACE=dict(w1=.85,wf=.03),EDGE=dict(w1=-.1,wf=-.02),VERTEX=dict(w1=.5,wf=.065)) if grouped else {})


def cc(g):
    return dict(generation=g,scheme='REFERENCE_COUPLED',scale=LOCAL_INCIDENT_SCALE,row=dict(weights=dict(wf=.1,w1=-.3,w2=-.4,w3=-.6,w4=.35)))


@pytest.mark.parametrize('after',['DS','CC'])
def test_checkpoint_preserves_grouped_continuation_and_full_state(tmp_path,after):
    s,_,arrays=step(initial(),ds(1));save_checkpoint(tmp_path/'stage',s,arrays);actual=load_checkpoint(tmp_path/'stage')
    for k in ('xyz','faces','classes','rest','anchors'):assert np.array_equal(getattr(s.mesh,k),getattr(actual.mesh,k))
    assert np.array_equal(s.face_roles,actual.face_roles)
    spec=ds(2,True) if after=='DS' else cc(2)
    a,am,aa=step(s,spec);b,bm,ba=step(actual,spec)
    assert am==bm and np.array_equal(a.mesh.xyz,b.mesh.xyz) and np.array_equal(a.face_roles,b.face_roles)
    assert all(np.array_equal(aa[k],ba[k]) for k in aa)
    if after=='DS':
        uniform,_,_=step(actual,ds(2));assert not np.array_equal(uniform.mesh.xyz,b.mesh.xyz)
    else:
        assert bm['eq4_eligible']==0
        c,cm,ca=step(b,cc(3));assert cm['eq4_eligible']==len(b.mesh.faces)
        assert np.array_equal(c.face_roles,b.face_roles[ca['parent_face']])


def test_lock_lifetime_removes_only_lock_and_does_not_mutate_definition():
    spec=cc(1);spec.update(lock_end=0,intrinsic=dict(field='NORMAL_VARIATION',start=1,gain=3,lock_threshold=.12,controls=dict(wf=[-.1,.18])))
    original=copy.deepcopy(spec);s,meta,arrays=step(initial(),spec)
    unlocked=copy.deepcopy(spec['intrinsic']);unlocked.pop('lock_threshold')
    expected,em,ea=subdivide(initial().mesh,spec['row'],intrinsic=unlocked)
    assert spec==original and meta['locked_vertex_count']==0
    assert meta['intrinsic']['controls']==original['intrinsic']['controls']
    assert np.array_equal(s.mesh.xyz,expected.xyz) and np.array_equal(arrays['intrinsic_signal'],ea['intrinsic_signal'])
    locked=copy.deepcopy(spec);locked['lock_end']=1
    other,om,oa=step(initial(),locked)
    assert om['locked_vertex_count']==8 and not np.array_equal(s.mesh.xyz,other.mesh.xyz)


@pytest.mark.parametrize('invalid',[dict(generation=2),dict(scheme='SILENT_LEGACY')])
def test_undeclared_or_misaligned_step_rejected(invalid):
    spec=ds(1);spec.update(invalid)
    with pytest.raises(ValueError):step(initial(),spec)


def test_no_overwrite_and_no_fabricated_role_shape(tmp_path):
    save_checkpoint(tmp_path/'stage',initial())
    with pytest.raises(FileExistsError):save_checkpoint(tmp_path/'stage',initial())
    with pytest.raises(ValueError):SubdivisionState(cube(),np.zeros(1,np.int8))


@pytest.mark.parametrize('role',[256,1.5])
def test_role_values_are_not_silently_truncated_or_wrapped(role):
    from cheshire.dual_subdivision import doo_sabin
    m=cube();bad=np.full(len(m.faces),role)
    with pytest.raises(ValueError):SubdivisionState(m,bad)
    with pytest.raises(ValueError):doo_sabin(m,{},face_roles=bad)
