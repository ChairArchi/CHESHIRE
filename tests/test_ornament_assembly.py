import numpy as np
import pytest
from cheshire.ornament_assembly import assemble_patches,validate_patch


def fixture():
    x=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    q=np.array([[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
    p=dict(vertices=np.vstack((x[[4,5,6,7]],[.5,.5,1.2])),
        triangles=np.array([[0,1,4],[1,2,4],[2,3,4],[3,0,4]]),
        host_vertex_ids=np.array([4,5,6,7,-1]),removed_host_face_ids=np.array([1]))
    return x,q,p


def test_exact_stitch_and_compaction(tmp_path):
    x,q,p=fixture();r=assemble_patches(x,q,[p],tmp_path/'surface',progress=lambda *a,**k:None)
    assert r['counts']==dict(vertices=9,quads=5,triangles=4,removed_quads=1,discarded_unreferenced_vertices=0)
    result=np.load(r['arrays']['XYZ']['path']);assert np.array_equal(result[:8],x)
    quads=np.load(r['arrays']['QUADS']['path']);triangles=np.load(r['arrays']['TRIANGLES']['path'])
    assert np.array_equal(quads,q[[0,2,3,4,5]])
    assert np.array_equal(triangles,np.array([[4,5,8],[5,6,8],[6,7,8],[7,4,8]]))
    assert min(quads.min(),triangles.min())==0 and max(quads.max(),triangles.max())<len(result)
    assert r['patch_audits'][0]['exact_directed_boundary_binding']


def test_reversed_boundary_rejected():
    x,q,p=fixture();p['triangles']=p['triangles'][:,::-1]
    with pytest.raises(ValueError,match='directed original boundary'):validate_patch(x,q,p)


def test_floating_component_rejected():
    x,q,p=fixture();p['vertices']=np.vstack((p['vertices'],[[0,0,2],[.2,0,2],[0,.2,2]]))
    p['triangles']=np.vstack((p['triangles'],[[5,6,7]]));p['host_vertex_ids']=np.r_[p['host_vertex_ids'],[-1,-1,-1]]
    with pytest.raises(ValueError,match='connected with exactly one boundary'):validate_patch(x,q,p)


def test_overlapping_replacements_rejected(tmp_path):
    x,q,p=fixture()
    with pytest.raises(ValueError,match='overlap'):assemble_patches(x,q,[p,p],tmp_path/'surface',progress=lambda *a,**k:None)
