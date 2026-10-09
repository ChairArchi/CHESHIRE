import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from astra_hierarchy import section_curve,sample_segments
from cheshire.task36_growth import carrier,native
from cheshire.reference_subdivision import ArrayMesh


def test_affine_actual_transfer_uses_native_triangle_barycentrics():
    m=native(carrier());a=np.array([[1.2,.1,.03],[0,.8,-.02],[.2,.1,1.1]]);shift=np.array([30.,-14.,22.])
    m.xyz=m.rest@a.T+shift
    arrays,info=section_curve(m,1000.12345,samples=128)
    assert info['valid'] and info['transfer_reconstruction_max']<1e-9
    np.testing.assert_allclose(arrays['sample_actual_xyz'],arrays['sample_rest_xyz']@a.T+shift,atol=1e-9)
    assert np.all(arrays['sample_weights']>=-1e-8)
    np.testing.assert_allclose(arrays['sample_weights'].sum(1),1.,atol=1e-12)
    assert np.all(arrays['sample_triangle_ids']>=0)


def test_multiple_reference_shells_reject_ambiguous_rays():
    a=native(carrier(side=1000));b=native(carrier(side=600));n=len(a.xyz)
    m=ArrayMesh(np.r_[a.xyz,b.xyz],np.r_[a.faces,np.where(b.faces<0,-1,b.faces+n)],np.r_[a.classes,b.classes],np.r_[a.rest,b.rest],np.r_[a.anchors,b.anchors],0)
    arrays,info=section_curve(m,1000.12345,samples=128)
    assert not info['valid'] and info['ambiguous_rays']==128
    assert np.isnan(arrays['radial_excess']).all()
    assert np.all(arrays['sample_triangle_ids']==-1)


def test_duplicate_same_endpoint_is_accepted_but_different_actual_sheet_is_not():
    m=native(carrier());arrays,info=section_curve(m,1000.12345,samples=128)
    rest=arrays['rest_segments'];actual=arrays['actual_segments'];w=arrays['segment_endpoint_weights'];ids=arrays['segment_triangle_ids'];tri=m.faces[:,:3]
    doubled,record=sample_segments(np.r_[rest,rest],np.r_[actual,actual],np.r_[w,w],np.r_[ids,ids],tri,128)
    assert record['valid'] and record['duplicate_agreeing_rays']==128
    shifted=actual.copy();shifted[:,:,2]+=1
    invalid,record=sample_segments(np.r_[rest,rest],np.r_[actual,shifted],np.r_[w,w],np.r_[ids,ids],tri,128)
    assert not record['valid'] and record['ambiguous_rays']==128
    assert np.isnan(invalid['sample_actual_xyz']).all()


def test_no_intersection_does_not_count_as_successful_empty_hierarchy():
    arrays,info=section_curve(native(carrier()),5000.,samples=64)
    assert not info['valid'] and info['missing_rays']==64


def test_ray_collinear_segment_invalidates_instead_of_silently_disappearing():
    m=native(carrier());arrays,_=section_curve(m,1000.12345,samples=128)
    theta=(9+.371)*2*np.pi/128;u=np.array([np.cos(theta),np.sin(theta)])
    line=np.array([[*(100*u),1000.12345],[*(300*u),1000.12345]])
    rest=np.concatenate([arrays['rest_segments'],line[None]])
    actual=np.concatenate([arrays['actual_segments'],line[None]])
    weights=np.concatenate([arrays['segment_endpoint_weights'],arrays['segment_endpoint_weights'][:1]])
    ids=np.r_[arrays['segment_triangle_ids'],arrays['segment_triangle_ids'][0]]
    samples,info=sample_segments(rest,actual,weights,ids,m.faces[:,:3],128)
    assert not info['valid'] and samples['ambiguous_rays'][9]
    assert np.isnan(samples['radial_excess'][9])
