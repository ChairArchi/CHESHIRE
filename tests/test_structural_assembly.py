import numpy as np
import pytest
from cheshire.structural_assembly import assemble_triangle_replacements


def _tetrahedron():
    x = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    t = np.array([[0,2,1],[0,1,3],[1,2,3],[2,0,3]],np.int64)
    return x,t


def _closed_edge_pairs(faces):
    edges = np.stack((faces,np.roll(faces,-1,axis=1)),axis=-1).reshape(-1,2)
    keys = np.sort(edges,axis=1)
    order = np.lexsort((keys[:,1],keys[:,0]))
    pairs = edges[order].reshape(-1,2,2)
    assert np.array_equal(pairs[:,0],pairs[:,1,::-1])


def test_native_triangle_disk_rebuild_preserves_closed_surface(tmp_path):
    x,t = _tetrahedron()
    patch = dict(vertices=np.vstack((x[t[0]],[[1/3,1/3,-.2]])),
        triangles=np.array([[0,1,3],[1,2,3],[2,0,3]],np.int64),
        host_vertex_ids=np.r_[t[0],-1],removed_host_face_ids=np.array([0]),
        tri_class_ids=np.array([1,2,3],np.int8))
    result = assemble_triangle_replacements(x,t,[patch],tmp_path/'surface')
    final_x = np.load(result['arrays']['XYZ']['path'])
    final_t = np.load(result['arrays']['TRIANGLES']['path'])
    assert result['counts']['vertices'] == 5
    assert result['counts']['triangles'] == 6
    assert final_t.max() == 4
    assert np.array_equal(final_x[:4],x)
    assert np.array_equal(final_t[:3],t[1:])
    assert np.array_equal(np.load(result['arrays']['TRIANGLE_CLASSES']['path']),
                          np.array([0,0,0,1,2,3]))
    _closed_edge_pairs(final_t)


def test_native_interior_vertex_is_actually_removed(tmp_path):
    x,t = _tetrahedron()
    x = np.vstack((x,[[1/3,1/3,0.]]))
    subdivided = np.array([[0,2,4],[2,1,4],[1,0,4]],np.int64)
    base = np.vstack((t[1:],subdivided))
    patch = dict(vertices=x[t[0]],triangles=np.array([[0,1,2]],np.int64),
        host_vertex_ids=t[0].copy(),removed_host_face_ids=np.arange(3,6))
    result = assemble_triangle_replacements(x,base,[patch],tmp_path/'surface')
    final_x = np.load(result['arrays']['XYZ']['path'])
    final_t = np.load(result['arrays']['TRIANGLES']['path'])
    remap = np.load(result['arrays']['OLD_TO_NEW']['path'])
    assert len(final_x) == 4 and remap[4] == -1
    assert final_t.max() == 3
    assert result['counts']['discarded_unreferenced_vertices'] == 1
    _closed_edge_pairs(final_t)


def test_reversed_native_seam_is_rejected(tmp_path):
    x,t = _tetrahedron()
    patch = dict(vertices=x[t[0]],triangles=np.array([[0,2,1]],np.int64),
        host_vertex_ids=t[0].copy(),removed_host_face_ids=np.array([0]))
    with pytest.raises(ValueError,match='directed original boundary'):
        assemble_triangle_replacements(x,t,[patch],tmp_path/'bad')
