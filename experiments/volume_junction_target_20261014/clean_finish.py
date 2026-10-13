"""Remove disconnected residue and explicitly reflect the saved finish quadrant.

No voxel or subdivision computation is repeated. The original and uncleaned
finish remain intact. New IDs and actual mirror involutions are recorded.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def array_hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    parent, output = root/'volume_finish_v2', root/'volume_finish_clean'
    if output.exists():
        raise FileExistsError('Earlier cleaned output preserved.')
    output.mkdir()
    started = time.perf_counter()
    info = json.loads((parent/'FINISH_RECEIPT.json').read_text(encoding='utf-8'))
    if digest(parent/'geometry.npz') != info['geometry_sha256']:
        raise ValueError('Actual parent geometry changed.')
    with np.load(parent/'geometry.npz', allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    nv = len(xyz)
    # Two triangle edges suffice to connect every incident triangle's vertices.
    a, b = np.concatenate([faces[:,0],faces[:,1]]), np.concatenate([faces[:,1],faces[:,2]])
    graph = coo_matrix((np.ones(len(a),np.int8),(a,b)),shape=(nv,nv)).tocsr()
    component_count, labels = connected_components(graph,directed=False)
    sizes = np.bincount(labels)
    primary = int(sizes.argmax())
    main = labels == primary
    del graph,a,b,labels
    tolerance = 3e-6
    canonical_xyz = xyz.copy()
    canonical_xyz[np.abs(canonical_xyz[:,0]) <= tolerance,0] = 0.
    canonical_xyz[np.abs(canonical_xyz[:,1]) <= tolerance,1] = 0.
    canonical = main & (canonical_xyz[:,0] <= 0.) & (canonical_xyz[:,1] >= 0.)
    keep_face = np.empty(len(faces),bool)
    for start in range(0,len(faces),262144):
        block = faces[start:start+262144]
        keep_face[start:start+len(block)] = np.all(canonical[block],axis=1)
    source_face_ids = np.flatnonzero(keep_face)
    source_vertex_ids = np.unique(faces[keep_face])
    if not len(source_face_ids):
        raise ValueError('No actual canonical main-component faces.')
    mapping = np.full(nv,-1,np.int32)
    mapping[source_vertex_ids] = np.arange(len(source_vertex_ids),dtype=np.int32)
    cf = mapping[faces[keep_face]]
    cx = canonical_xyz[source_vertex_ids]
    if np.any(np.all(cx[cf,0] == 0.,axis=1)) or np.any(np.all(cx[cf,1] == 0.,axis=1)):
        raise ValueError('Unexpected entire canonical face in mirror plane; no silent duplication.')
    non_x = np.flatnonzero(cx[:,0] != 0.)
    nc = len(cx)
    mx = np.arange(nc,dtype=np.int32)
    mx[non_x] = nc+np.arange(len(non_x),dtype=np.int32)
    reflected_x = cx[non_x]*np.array([-1.,1.,1.],np.float32)
    base_xyz = np.concatenate([cx,reflected_x])
    base_faces = np.concatenate([cf,mx[cf][:,::-1]])
    px_base = np.concatenate([mx,non_x.astype(np.int32)])
    nb = len(base_xyz)
    non_y = np.flatnonzero(base_xyz[:,1] != 0.)
    my = np.arange(nb,dtype=np.int32)
    my[non_y] = nb+np.arange(len(non_y),dtype=np.int32)
    final_xyz = np.concatenate([base_xyz,base_xyz[non_y]*np.array([1.,-1.,1.],np.float32)])
    final_faces = np.concatenate([base_faces,my[base_faces][:,::-1]])
    px = np.concatenate([px_base,my[px_base[non_y]]])
    py = np.concatenate([my,non_y.astype(np.int32)])
    ids = np.arange(len(final_xyz),dtype=np.int32)
    if not np.array_equal(px[px],ids) or not np.array_equal(py[py],ids) or not np.array_equal(px[py],py[px]):
        raise ValueError('Constructed actual mirror involutions failed.')
    if not np.array_equal(final_xyz[px],final_xyz*np.array([-1.,1.,1.],np.float32)) or not np.array_equal(final_xyz[py],final_xyz*np.array([1.,-1.,1.],np.float32)):
        raise ValueError('Actual exact coordinate symmetry failed.')
    geometry = output/'geometry.npz'
    np.savez(geometry,xyz=final_xyz,faces=final_faces)
    evidence = output/'cleanup_evidence.npz'
    np.savez_compressed(evidence,canonical_parent_vertex_ids=source_vertex_ids,
        canonical_parent_face_ids=source_face_ids,mirror_x_vertex_pairs=px,mirror_y_vertex_pairs=py)
    recipe = dict(info['recipe'], cleanup='Retain only largest actual connected component; snap only abs(X/Y)<=3e-6 to the mirror planes, extract canonical x<=0,y>=0 triangles, then explicitly reflect vertices and reverse winding across each axis. No voxel/CC rerun.',
        cleanup_axis_snap_tolerance=tolerance, cleanup_added_voxel_passes=0, cleanup_added_CC_passes=0)
    result = dict(info, candidate='G7_DERIVED_VOLUME_FINISH_CLEAN', recipe=recipe,
        parent_finish=str(parent), parent_finish_receipt_sha256=digest(parent/'FINISH_RECEIPT.json'),
        parent_geometry_sha256=info['geometry_sha256'], geometry=str(geometry),geometry_sha256=digest(geometry),
        xyz_sha256=array_hash(final_xyz),faces_sha256=array_hash(final_faces),
        vertices=len(final_xyz),triangles=len(final_faces),polygons=len(final_faces),
        parent_components=int(component_count),parent_main_component_vertices=int(sizes[primary]),
        removed_disconnected_parent_vertices=int(nv-sizes[primary]),
        canonical_parent_vertices=len(source_vertex_ids),canonical_parent_triangles=len(source_face_ids),
        actual_exact_XY_coordinate_symmetry=True, cleanup_evidence_sha256=digest(evidence),
        cleanup_code_sha256=digest(__file__),elapsed_cleanup_seconds=time.perf_counter()-started,
        visual_status='PENDING_CLEAN_RENDER', remaining_modifiers=0)
    (output/'FINISH_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    snapshots=output/'source_snapshot'
    snapshots.mkdir()
    shutil.copyfile(__file__,snapshots/Path(__file__).name)
    print('CLEAN_FINISH_SAVED',len(final_xyz),len(final_faces),'removed',nv-sizes[primary],flush=True)


if __name__ == '__main__':
    main()
