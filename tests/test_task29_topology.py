import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
from task29_topology import weld
from cheshire.reference_subdivision import cube,subdivide,topology


def test_adjacent_close_generated_points_change_valid_connectivity_and_resume():
    m=cube();m.classes[:]=1;m.xyz[1]=m.xyz[0]+[.1,0,0]
    rule=dict(threshold=.001,scope='ADJACENT',generation=0)
    out,log=weld(m,rule);again,replay=weld(m,rule)
    assert log['status']=='ACCEPTED_CHANGED';assert len(log['merged_pairs'])==1
    assert len(out.xyz)==7;assert len(out.faces)==6;assert log['compressed_cycles']
    assert log['after']['Euler']==2;assert log==replay
    np.testing.assert_array_equal(out.xyz,again.xyz)
    resumed,meta,_=subdivide(out,dict(wf=.03,w1=-.2,w2=-.3))
    assert len(resumed.faces)==22;assert np.isfinite(resumed.xyz).all();topology(resumed)


def test_nonadjacent_proximity_cannot_silently_pinchtwo_vertex_fans():
    m=cube();m.classes[:]=1;m.xyz[6]=m.xyz[0]+[.1,0,0]
    out,log=weld(m,dict(threshold=.001,scope='ALL_PROXIMATE',generation=0))
    assert out is None;assert log['status']=='REJECTED_INVALID'
    assert 'vertex links' in log['invalid_reason'];assert len(log['merged_pairs'])==1


def test_no_generated_points_preserves_original_path():
    m=cube();out,log=weld(m,dict(threshold=.2,scope='ALL_PROXIMATE',generation=0))
    assert log['status']=='ACCEPTED_NO_PROXIMATE_POINTS';assert not log['merged_pairs']
    np.testing.assert_array_equal(m.xyz,out.xyz);np.testing.assert_array_equal(m.faces,out.faces)


@pytest.mark.parametrize('value',[0,-1,1,2])
def test_threshold_is_bounded(value):
    with pytest.raises(ValueError):weld(cube(),dict(threshold=value,scope='ADJACENT'))
