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
