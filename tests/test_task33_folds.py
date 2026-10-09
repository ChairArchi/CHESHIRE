import numpy as np
import pytest
from cheshire.reference_subdivision import ArrayMesh
from cheshire.progressive_gates import gate_input
from cheshire.task33_folds import initial_chart, refine, refine_section, evaluate, reflection_error, fold_values


def gate():
    m,_=gate_input('RECT',False)
    xyz=np.asarray(m.vertices_attributes('xyz'))
    faces=np.full((80,4),-1,dtype=np.int64)
    for i,f in enumerate(m.faces()):
        q=m.face_vertices(f);faces[i,:len(q)]=q
    return ArrayMesh(xyz,faces,np.full(74,-1,np.int8),xyz.copy(),np.full((80,3),-1,np.int64))


def test_refinement_does_not_move_old_vertices():
    m=gate();s=initial_chart(m)
    out,ss,_,_=refine(m,s)
    np.testing.assert_array_equal(out.xyz[:74],m.xyz)
    np.testing.assert_array_equal(ss['carrier'][:74],m.xyz)


def test_refined_control_and_geometry_are_mirror_paired():
    m=gate();s=initial_chart(m)
    for _ in range(3):m,s,_,_=refine(m,s)
    for level in range(4):
        out,_=evaluate(m,s,{},level)
        assert reflection_error(s,out.xyz)<1e-9


def test_macro_is_identical_at_inherited_vertices_and_new_child_cannot_erase_it():
    m=gate();s=initial_chart(m)
    m,s,_,_=refine(m,s)
    macro,ff=evaluate(m,s,{},1)
    refined,ss,_,_=refine(m,s)
    macro2,_=evaluate(refined,ss,{},1)
    np.testing.assert_allclose(macro.xyz,macro2.xyz[:len(m.xyz)],atol=1e-12)
    child,child_field=evaluate(m,s,{},2)
    assert np.all(child_field['depth']>=ff['depth'])
    np.testing.assert_allclose(child.xyz[:,[0,2]],macro.xyz[:,[0,2]])


def test_invalid_fold_amplitude_or_convergence_is_rejected():
    chart=initial_chart(gate())['chart']
    with pytest.raises(ValueError):fold_values(chart,{'amplitudes':[1,-1,2]},3)
    with pytest.raises(ValueError):fold_values(np.array([[.18,0,1]]),{'convergence':1},1)


def test_twisted_variable_frequency_folds_retain_constructive_symmetry():
    m=gate();s=initial_chart(m)
    for _ in range(3):m,s,_,_=refine(m,s,carrier_smoothing=m.generation<2)
    out,_=evaluate(m,s,{'twist':.35,'twist_start':.21,'twist_end':.27,'child_frequency_variation':2,'parent_gate_power':2,
                      'child_floor':0,'neck_locations':[.15,.43]},3)
    assert reflection_error(s,out.xyz)<1e-9


def test_section_refinement_keeps_closed_oriented_topology_and_parent_support():
    from cheshire.reference_subdivision import topology
    m=gate();s=initial_chart(m)
    for _ in range(3):
        before=m
        m,s,_,op=refine_section(m,s)
        t=topology(m)
        assert len(m.xyz)-len(t['edges'])+len(m.faces)==2
        np.testing.assert_array_equal(m.xyz[:len(before.xyz)],before.xyz)
        assert np.all(op['parent_face']<len(before.faces))
        out,_=evaluate(m,s,{'twist':.35},3)
        assert reflection_error(s,out.xyz)<1e-9


@pytest.mark.parametrize('params',[{'sweep':float('nan')},{'lobes':0},{'typo_amplitude':300},{'child_frequency_variation':2}])
def test_invalid_or_discontinuous_controls_fail_explicitly(params):
    with pytest.raises(ValueError):fold_values(initial_chart(gate())['chart'],params,3)


def test_child_phase_can_form_a_real_valley_inside_the_parent_crest():
    chart=np.array([[.1,-.08,-1],[.1,0,-1],[.1,.08,-1]])
    p=dict(convergence=0,sweep=0,lobes=1,amplitudes=[500,260,75],child_floor=0,parent_gate_power=2,
           child_phase_shift=np.pi)
    macro=fold_values(chart,p,1)['depth'];meso=fold_values(chart,p,2)['depth']
    assert macro[1]>macro[0] and macro[1]>macro[2]
    assert meso[0]-meso[1]>100 and meso[2]-meso[1]>100


def test_fine_phase_can_create_additional_valleys_instead_of_only_sharpening_meso():
    from scipy.signal import find_peaks
    u=np.linspace(-1,1,2001)
    chart=np.column_stack([np.full(len(u),.24531),u,-np.ones(len(u))])
    p=dict(convergence=.55,neck_locations=[.15,.43],windowed=True,lobes=1.6,
           child_floor=0,parent_gate_power=2,child_frequency_variation=2,
           child_phase_shift=np.pi,micro_phase_shift=np.pi,micro_coupling=0,amplitudes=[500,400,200])
    meso=fold_values(chart,p,2)['depth'];fine=fold_values(chart,p,3)['depth']
    assert len(find_peaks(fine,prominence=25)[0])>len(find_peaks(meso,prominence=25)[0])
    np.testing.assert_array_equal(fold_values(chart,p,1)['depth'],fold_values(chart,{**p,'amplitudes':[500,0,0]},3)['depth'])


def test_generated_meso_response_and_signed_recess_remain_finite_and_symmetric():
    m=gate();s=initial_chart(m)
    for _ in range(3):m,s,_,_=refine(m,s,carrier_smoothing=m.generation<2)
    p=dict(child_floor=0,parent_gate_power=2,child_frequency_variation=2,child_phase_shift=np.pi,
           fine_mode='meso_slope',macro_recess=120,paired_controls=True,twist=.35,amplitudes=[500,400,100])
    out,ff=evaluate(m,s,p,3)
    assert reflection_error(s,out.xyz)<1e-9
    assert ff['depth'].min()>=-120 and np.isfinite(out.xyz).all()


def test_generated_meso_response_derivative_step_is_converged():
    u=np.linspace(-1,1,1001);c=np.column_stack([np.full(len(u),.24531),u,-np.ones(len(u))])
    p=dict(child_floor=0,parent_gate_power=2,child_frequency_variation=2,fine_mode='meso_slope')
    a=fold_values(c,{**p,'gradient_epsilon':1e-5},3)['depth']
    b=fold_values(c,{**p,'gradient_epsilon':1e-6},3)['depth']
    assert np.abs(a-b).max()<.01


def test_meso_notch_splits_generated_crests_without_erasing_macro_component():
    from scipy.signal import find_peaks
    u=np.linspace(-1,1,257);chart=np.column_stack([np.full(len(u),.06531),u,-np.ones(len(u))])
    p=dict(windowed=True,child_floor=0,lobes=1.6,convergence=.55,neck_locations=[.15,.43],
           child_frequency_variation=2,parent_gate_power=2,child_phase_shift=np.pi,
           fine_mode='meso_notch',micro_slope_scale=12,amplitudes=[500,400,180])
    macro=fold_values(chart,p,1)['depth'];meso=fold_values(chart,p,2)['depth'];fine=fold_values(chart,p,3)['depth']
    assert len(find_peaks(fine,prominence=25)[0])==12
    assert len(find_peaks(meso,prominence=25)[0])==6
    assert np.all(fine>=macro-1e-10)
    with pytest.raises(ValueError):fold_values(chart,{**p,'amplitudes':[500,100,180]},3)
