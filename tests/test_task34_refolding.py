import numpy as np
from cheshire.reference_subdivision import ArrayMesh,topology
from cheshire.task34_refolding import carrier,native,refine,macro,refold,symmetry


def template():
    # Match only the declared ring centres; carrier() constructs its own section.
    centres=np.array([[-1550,0,0],[-1550,0,1300],[-1550,0,2600],[-1550,0,3050],[0,0,3050],[1550,0,3050],[1550,0,2600],[1550,0,1300],[1550,0,0]],float)
    from cheshire.progressive_gates import PLANE_X,PLANE_Y
    centres+=np.array([PLANE_X,PLANE_Y,0])
    xyz=np.repeat(centres,8,axis=0)
    return ArrayMesh(np.vstack([xyz,centres[[0,-1]]]),np.zeros((80,4),np.int64),np.zeros(74,np.int8),np.zeros((74,3)),np.zeros((80,3),np.int64),0)


def seed():
    s=carrier(template(),'jointed')
    for _ in range(3):s,_=refine(s)
    s,_=macro(s,{})
    return s


def test_native_closed_and_both_symmetry_planes():
    for kind in ['uniform','jointed','splayed']:
        s=carrier(template(),kind);m,c,_=native(s,0);topology(m)
        result=symmetry(m,c,check_faces=True)
        assert max(d['geometry_max'] for d in result.values())<1e-9
        assert all(d['oriented_triangle_cycle_failures']==0 for d in result.values())


def test_refinement_uses_actual_previous_native_vertices():
    s=seed();m,_,_=native(s,3);out,op=refine(s)
    p=op['grid_parent_vertices'];w=op['grid_parent_weights']
    reconstructed=(m.xyz[np.maximum(p,0)]*w[:,:,:,None]).sum(2)
    np.testing.assert_allclose(reconstructed,out['grid'],atol=1e-12,rtol=0)
    assert len(np.unique(p[w==1]))==len(m.xyz)-2


def test_generated_geometry_changes_the_next_control():
    s=seed();first,_,_=refold(s,s,{})
    out,adaptive,_=refold(first,first,{})
    frozen,controls,_=refold(first,s,{})
    assert np.max(np.abs(adaptive['requested_radial']-controls['requested_radial']))>20
    assert np.max(np.linalg.norm(out['grid']-frozen['grid'],axis=-1))>20


def test_repeated_rule_is_symmetric_and_applies_requested_distance():
    s=seed()
    for g in [4,5]:
        s,fields,_=refold(s,s,{})
        np.testing.assert_array_equal(fields['requested_radial'],fields['applied_radial'])
        m,c,_=native(s,g);topology(m)
        assert max(d['geometry_max'] for d in symmetry(m,c).values())<1e-8
        assert fields['requested_radial'].min()<-20


def test_frozen_source_removes_geometry_control_response():
    s=seed();target=dict(s,grid=s['grid'].copy());target['grid'][:,:,1]*=1.03
    _,a,_=refold(s,s,{})
    _,b,_=refold(target,s,{})
    np.testing.assert_array_equal(a['requested_radial'],b['requested_radial'])
    np.testing.assert_array_equal(a['direction_local'],b['direction_local'])


def test_surface_direction_and_measured_axis_preserve_both_reflections():
    s=seed();out,f,_=refold(s,s,dict(operator='split',fraction=.4,axial_mix=.5,direction_mode='surface',tangent_mode='measured'))
    m,c,_=native(out,4);proof=symmetry(m,c,check_faces=True)
    assert all(d['geometry_max']<1e-8 and d['oriented_triangle_cycle_failures']==0 for d in proof.values())
    np.testing.assert_allclose(np.linalg.norm(out['grid']-s['grid'],axis=-1),f['total_applied_distance'],atol=1e-10,rtol=0)


def test_axial_features_use_generated_length_and_change_next_rule():
    from cheshire.task34_refolding import read_features,axial_features
    s=seed();_,signal,_=read_features(s);_,_,_,arc=axial_features(s,signal)
    changed=dict(s,grid=s['grid'].copy());changed['grid'][:,:,2]*=1.15
    _,newsignal,_=read_features(changed);_,_,_,newarc=axial_features(changed,newsignal)
    assert newarc[-1]>arc[-1]*1.05
    out,_,_=refold(s,s,dict(operator='split',fraction=.4,axial_mix=.5))
    _,a,_=refold(out,out,dict(operator='split',fraction=.4,axial_mix=.5))
    _,b,_=refold(out,s,dict(operator='split',fraction=.4,axial_mix=.5))
    assert np.max(np.abs(a['requested_signed_fold_distance']-b['requested_signed_fold_distance']))>20
