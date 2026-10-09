import numpy as np
import pytest
from cheshire.reference_subdivision import cube, topology
from cheshire.task32_patches import sweep_disk, disk_boundary


def test_multiface_disk_sweep_preserves_closed_oriented_mesh_and_parent_scope():
    m=cube(); original=m.xyz.copy()
    out,meta,state=sweep_disk(m,[1,2],dict(heights=[.2,.6],scales=[.8,.5],bend=.2),new_scope=7)
    t=topology(out)
    assert len(out.xyz)-len(t['edges'])+len(out.faces)==2
    assert len(np.unique(out.faces[out.faces>=0]))==len(out.xyz)
    assert meta['patch_faces']==2 and meta['boundary_vertices']==6
    assert len(state['parent_face'])==len(out.faces)
    assert (state['face_scope'][state['cap_faces']]==7).all()
    np.testing.assert_array_equal(m.xyz,original)
    assert np.isfinite(out.xyz).all()


def test_disconnected_or_whole_closed_selection_is_rejected():
    m=cube()
    with pytest.raises(ValueError,match='disk Euler'):
        disk_boundary(m,[0,1])
    with pytest.raises(ValueError,match='disk Euler'):
        disk_boundary(m,np.arange(6))


def test_zero_height_ring_cannot_be_hidden_by_unsigned_area_check():
    with pytest.raises(ValueError,match='Increasing'):
        sweep_disk(cube(),[1],dict(heights=[.2,.2],scales=[.8,.5]))
