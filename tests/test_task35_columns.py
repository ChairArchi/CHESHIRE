import numpy as np
from cheshire.task35_columns import carrier,native,refine,form,refold,symmetry,geometry_features
from cheshire.reference_subdivision import topology


def formed(kind='varied',mode='regional'):
    state=carrier(kind)
    for _ in range(3):state,_=refine(state)
    return form(state,mode,{})[0]


def test_column_native_closed_both_vertical_reflections():
    for kind in ['uniform','varied']:
        s=carrier(kind);m,c,_=native(s,0);topology(m)
        p=symmetry(m,c)
        assert all(d['geometry_max']<1e-9 and d['oriented_triangle_cycle_failures']==0 for d in p.values())


def test_end_sections_and_fixed_buffers_match_between_inputs():
    a=carrier('uniform');b=carrier('varied')
    for _ in range(3):a,_=refine(a);b,_=refine(b)
    fixed=(a['s']<=.06)|(a['s']>=.94)
    np.testing.assert_array_equal(a['grid'][fixed],b['grid'][fixed])


def test_both_and_angular_refinement_reconstruct_actual_parent_grid():
    s=formed();m,_,_=native(s,3)
    for mode,count in [('both',2),('angular',3)]:
        new,op=refine(s,mode);p=op['grid_parent_vertices'];w=op['grid_parent_weights']
        np.testing.assert_allclose((m.xyz[np.maximum(p,0)]*w[:,:,:,None]).sum(2),new['grid'],rtol=0,atol=1e-12)
        assert op['parent_native_triangle_contributors'].shape[-1]==count


def test_height_regions_are_not_reflected_or_copied():
    s=formed();f=geometry_features(s)
    assert np.max(abs(f['radius']-f['radius'][::-1]))>100
    out,controls,_=refold(s,s,'regional',{})
    assert np.max(abs(controls['requested_signed_distance']-controls['requested_signed_distance'][::-1]))>10


def test_all_operations_fix_original_end_buffer_xyz():
    for mode in ['common','regional']:
        s=carrier('varied')
        for _ in range(3):s,_=refine(s)
        original=s['grid'].copy();fixed=(s['s']<=.06)|(s['s']>=.94)
        s,_=form(s,mode,{})
        s,controls,_=refold(s,s,mode,{})
        np.testing.assert_array_equal(s['grid'][fixed],original[fixed])
        assert np.max(abs(controls['applied_displacement'][fixed]))==0


def test_regional_branch_and_direction_depend_on_current_geometry():
    s=formed();out,_,_=refold(s,s,'regional',{})
    _,current,_=refold(out,out,'regional',{})
    _,frozen,_=refold(out,s,'regional',{})
    assert np.max(abs(current['requested_signed_distance']-frozen['requested_signed_distance']))>10
    assert np.max(abs(current['read_broadness']-frozen['read_broadness']))>1e-3


def test_regional_operations_preserve_section_symmetry_without_xyz_averaging():
    s=formed();out,f,_=refold(s,s,'regional',{})
    m,c,_=native(out,4);p=symmetry(m,c);topology(m)
    assert all(d['geometry_max']<1e-8 and d['oriented_triangle_cycle_failures']==0 for d in p.values())
    np.testing.assert_allclose(out['grid']-s['grid'],f['applied_displacement'],rtol=0,atol=1e-10)


def test_chord_term_changes_refolding_at_same_prominence_fraction():
    s=formed();_,a,_=refold(s,s,'regional',{'chord_gain':0})
    _,b,_=refold(s,s,'regional',{'chord_gain':1})
    assert np.max(b['chord_drop'])>5
    assert np.max(abs(a['requested_signed_distance']-b['requested_signed_distance']))>5


def test_axial_map_changes_section_spacing_with_fixed_height():
    s=formed();out,f,_=refold(s,s,'regional',{})
    assert np.max(abs(f['axial_redistribution']))>10
    assert np.all(np.diff(out['grid'][:,:,2].mean(1))>0)
    np.testing.assert_array_equal(out['grid'][[0,-1]],s['grid'][[0,-1]])


def test_uniform_geometry_cannot_invent_internal_region_differences():
    s=carrier('uniform')
    for _ in range(3):s,_=refine(s)
    out,f=form(s,'regional',{})
    body=(s['s']>.1)&(s['s']<.9)
    assert np.ptp(f['read_broadness'][body])<1e-12
    assert np.max(np.ptp(out['grid'][body,:,:2],axis=0))<1e-9


def test_common_recipe_uses_physical_height_not_gate_row_partner():
    s=carrier('uniform')
    for _ in range(3):s,_=refine(s)
    out,c=form(s,'common',{})
    q=np.minimum(s['s'],1-s['s']);neck=np.maximum(np.exp(-((q-.15)/.045)**2),np.exp(-((q-.43)/.035)**2))
    bulge=np.maximum.reduce([np.exp(-((q-v)/.055)**2) for v in [.065,.285,.365,.495]])
    foot=np.clip(q/.055,0,1);foot=foot*foot*(3-2*foot)
    from cheshire.task35_columns import end_window
    expected=500*(.22+.78*bulge)*(1-.70*neck)*foot*end_window(s)
    np.testing.assert_allclose(c['requested_signed_distance'][:,0],expected,atol=1e-12)
    assert np.max(abs(expected-expected[::-1]))>100


def test_measured_span_uses_actual_radius_and_changes_more_than_amplitude():
    s=formed();out,a,_=refold(s,s,'regional',{'axial_wave_gain':.5,'fan_gain':.5})
    _,b,_=refold(out,out,'regional',{'axial_wave_gain':.5,'fan_gain':.5})
    _,frozen,_=refold(out,s,'regional',{'axial_wave_gain':.5,'fan_gain':.5})
    assert np.ptp(a['measured_span_wave'])>1
    assert np.max(abs(b['measured_span_phase']-frozen['measured_span_phase']))>.01
    m,c,_=native(out,4)
    assert max(v['geometry_max'] for v in symmetry(m,c).values())<1e-8
    assert np.all(np.diff(out['grid'][:,:,2],axis=0)>0)


def test_actual_cut_rays_intersect_segments_instead_of_vertex_radius_blending():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('task35_analysis_test',Path(__file__).resolve().parents[1]/'tools/task35_analyze.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    xy=np.array([[2,1],[-2,1],[-2,-1],[2,-1]],float)
    lines=np.zeros((4,2,3));lines[:,0,:2]=xy;lines[:,1,:2]=np.roll(xy,-1,axis=0)
    r,valid=module.radial_cut(lines)
    expected=np.minimum(2/abs(np.cos(module.THETA)),1/abs(np.sin(module.THETA)))
    assert valid==dict(missing_rays=0,multiple_distinct_rays=0)
    np.testing.assert_allclose(r,expected,rtol=0,atol=1e-12)
    r,valid=module.radial_cut(np.concatenate([lines,2*lines]))
    assert valid['multiple_distinct_rays']==module.SAMPLES


def test_actual_axial_bulge_features_drive_later_cross_folds():
    s=formed();a,c,_=refold(s,s,'regional',{'axial_notch_gain':.65})
    b,_,_=refold(s,s,'regional',{'axial_notch_gain':0})
    assert np.max(c['axial_feature_prominence'])>100
    assert np.max(abs(a['grid']-b['grid']))>50
    m,chart,_=native(a,4)
    assert max(v['geometry_max'] for v in symmetry(m,chart).values())<1e-8


def test_failed_thickness_preserves_actual_requested_geometry_and_controls():
    from cheshire.task35_columns import RejectedFormation
    import pytest
    s=formed();current,_,_=refold(s,s,'regional',{'axial_notch_gain':.65,'axial_wave_gain':.5,'fan_gain':.5})
    with pytest.raises(RejectedFormation) as captured:
        refold(current,s,'regional',{'axial_notch_gain':.65,'axial_wave_gain':.5,'fan_gain':.5})
    e=captured.value
    assert e.controls['total_applied_distance'].max()>100
    np.testing.assert_allclose(e.state['grid']-current['grid'],e.controls['applied_displacement'],atol=1e-10)


def test_unknown_or_nonfinite_controls_are_not_silently_ignored():
    import pytest
    s=formed()
    with pytest.raises(ValueError,match='Unknown initial'):form(s,'regional',{'not_applied':1})
    for parameter in ['direction_gain','common_axial_mix','signal_sigma']:
        with pytest.raises(ValueError,match='bounds'):refold(s,s,'regional',{parameter:np.nan})
