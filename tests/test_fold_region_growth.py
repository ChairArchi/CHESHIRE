"""Native sampling, shape response and scale invariance of the region study."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tested_region_study',
    ROOT/'experiments/fold_region_growth_20261012/study.py')
study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)
from region_fold import NativeChartSampler, measure_parent, measure_longitudinal, proposal


@pytest.fixture(scope='module')
def source():
    mesh, chart, _ = study.anchor.t.load(study.SOURCES['SPAN'])
    parents = study.anchor.t.overlap.EVENTS
    native = study.anchor.t.growth.native(mesh)
    pchart = np.concatenate([chart, study.anchor.t.face_values(mesh, chart)])
    return mesh, chart, parents, native, pchart


def measured(source, scale=1.,orientation='theta'):
    mesh, chart, parents, native, pchart = source
    sampler = NativeChartSampler(native.xyz*scale, native.faces[:, :3], pchart)
    measure=measure_parent if orientation=='theta' else measure_longitudinal
    return [measure(sampler, p) for p in parents]


def test_native_samples_reconstruct_from_recorded_triangles(source):
    _, _, _, native, pchart = source
    sampler = NativeChartSampler(native.xyz, native.faces[:, :3], pchart)
    queries = sampler.p[::137].mean(axis=1)
    points, ids, bary = sampler.sample(queries, records=True)
    exact = np.einsum('ni,nij->nj', bary, native.xyz[native.faces[ids, :3]])
    assert np.allclose(points, exact, rtol=0, atol=1e-13)
    assert np.all(bary >= -1e-9)
    assert np.allclose(bary.sum(axis=1), 1)
    with pytest.raises(ValueError, match='outside native chart'):
        sampler.sample([[1.5, .4]])


@pytest.mark.parametrize('mode', ['GROOVE', 'RETURN'])
@pytest.mark.parametrize('orientation',['theta','height'])
def test_physical_scale_changes_without_case_specific_coefficients(source, mode,orientation):
    mesh, chart, _, _, _ = source
    guides, scaled = measured(source,orientation=orientation), measured(source, 2.,orientation)
    first, _ = proposal(mesh.xyz, chart, guides, mode=mode)
    second, _ = proposal(mesh.xyz*2, chart, scaled, mode=mode)
    assert np.linalg.norm(first,axis=1).max() > .1
    assert np.allclose(second, 2*first, rtol=0, atol=2e-10)
    assert np.array_equal(guides[0]['guide_cross'], scaled[0]['guide_cross'])


def test_zero_intervention_restores_inactive_reference(source):
    mesh, chart, _, _, _ = source
    guides = measured(source)
    delta, _ = proposal(mesh.xyz, chart, guides, mode='RETURN', depth_ratio=0, angle=0)
    assert np.allclose(delta, 0, rtol=0, atol=1e-13)


def test_actual_shape_changes_guides_with_material_chart_unchanged(source):
    mesh, chart, parents, native, pchart = source
    transformed = native.xyz.copy()
    # A smooth, reflection-compatible change to the source mass; no event edits.
    factor = 1+.16*np.sin(2*np.pi*pchart[:, 0])
    transformed[:, :2] *= factor[:, None]
    sampler = NativeChartSampler(transformed, native.faces[:, :3], pchart)
    changed = [measure_parent(sampler,p) for p in parents]
    original = measured(source)
    assert max(np.max(np.abs(a['guide_s']-b['guide_s']))
        for a,b in zip(original,changed)) > 1e-4
    moved,_=proposal(mesh.xyz,chart,original)
    other,_=proposal(mesh.xyz*np.column_stack([factor[:len(mesh.xyz)],factor[:len(mesh.xyz)],np.ones(len(mesh.xyz))]),chart,changed)
    assert np.max(np.abs(moved-other)) > 1e-3


def test_unfolded_cylinder_is_not_claimed_as_an_existing_parent_basin(source):
    _, _, parents, native, pchart = source
    theta=np.arctan2(pchart[:,2],pchart[:,1])
    cylinder=np.column_stack([np.cos(theta),np.sin(theta),10*pchart[:,0]])
    sampler=NativeChartSampler(cylinder,native.faces[:,:3],pchart)
    with pytest.raises(ValueError,match='No measured parent basin'):
        measure_parent(sampler,parents[0])


def test_region_frame_does_not_inherit_local_direction_reversals(source):
    _,_,parents,native,pchart=source
    sampler=NativeChartSampler(native.xyz,native.faces[:,:3],pchart)
    for parent in parents:
        guide=measure_longitudinal(sampler,parent,frame_mode='region')
        for field in ('normal','tangent'):
            vectors=guide[field]
            assert np.all(np.sum(vectors[:-1]*vectors[1:],axis=1)>0)
        assert np.allclose(np.sum(guide['normal']*guide['tangent'],axis=1),0,atol=1e-13)
