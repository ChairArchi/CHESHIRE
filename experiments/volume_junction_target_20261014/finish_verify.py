"""Required saved-array geometry checks for the G7-derived volume finish."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import shutil
import time

import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    folder = args.root.resolve()/'volume_finish'
    path = folder/'VERIFICATION.json'
    if path.exists():
        raise FileExistsError('Earlier verification preserved.')
    started = time.perf_counter()
    receipt = json.loads((folder/'FINISH_RECEIPT.json').read_text(encoding='utf-8'))
    geometry = folder/'geometry.npz'
    if digest(geometry) != receipt['geometry_sha256']:
        raise ValueError('Actual saved geometry hash changed.')
    with np.load(geometry, allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    nv, nf = len(xyz), len(faces)
    finite = bool(np.isfinite(xyz).all())
    indexed = bool(faces.shape == (nf, 3) and faces.min() >= 0 and faces.max() < nv)
    minimum_area, area_sum = np.inf, 0.
    for start in range(0, nf, 262144):
        points = xyz[faces[start:start+262144]].astype(float)
        areas = np.linalg.norm(np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0]), axis=1)*.5
        minimum_area = min(minimum_area, float(areas.min()))
        area_sum += float(areas.sum())
    # Exact integer packed edge incidence; every saved triangle is counted.
    encoded = np.empty(3*nf, np.uint64)
    oriented = np.empty(3*nf, np.int8)
    for corner in range(3):
        a, b = faces[:, corner], faces[:, (corner+1)%3]
        low, high = np.minimum(a, b).astype(np.uint64), np.maximum(a, b).astype(np.uint64)
        encoded[corner*nf:(corner+1)*nf] = low*np.uint64(nv)+high
        oriented[corner*nf:(corner+1)*nf] = np.where(a < b, 1, -1)
        del low, high
    order = np.argsort(encoded, kind='quicksort')
    encoded, oriented = encoded[order], oriented[order]
    del order
    start = np.r_[0, np.flatnonzero(encoded[1:] != encoded[:-1])+1]
    counts = np.diff(np.r_[start, len(encoded)])
    signs = np.add.reduceat(oriented.astype(np.int32), start)
    packed = encoded[start]
    closed, oriented_ok = bool(np.all(counts == 2)), bool(np.all(signs == 0))
    edges = np.column_stack([packed//np.uint64(nv), packed%np.uint64(nv)]).astype(np.int32)
    ne = len(edges)
    del encoded, oriented, packed, counts, signs, start
    gc.collect()
    degree = np.bincount(edges.ravel(), minlength=nv)
    no_orphans = bool(np.all(degree > 0))
    graph = coo_matrix((np.ones(ne, np.int8), (edges[:, 0], edges[:, 1])), shape=(nv, nv)).tocsr()
    component_count, labels = connected_components(graph, directed=False)
    component_sizes = np.bincount(labels)
    del graph, edges, degree, labels
    gc.collect()
    # Full all-vertex actual geometric symmetry; this remesh has new IDs.
    tree = cKDTree(xyz)
    symmetry = {}
    for axis in [0, 1]:
        maximum, total_squared = 0., 0.
        for first in range(0, nv, 262144):
            query = xyz[first:first+262144].astype(float)
            query[:, axis] *= -1.
            distance = tree.query(query, workers=-1)[0]
            maximum = max(maximum, float(distance.max()))
            total_squared += float(distance@distance)
        symmetry['XY'[axis]] = dict(maximum_nearest_vertex_residual=maximum,
            rms_nearest_vertex_residual=(total_squared/nv)**.5, tested_vertices=nv)
    tolerance = 1e-7
    symmetric = all(item['maximum_nearest_vertex_residual'] <= tolerance for item in symmetry.values())
    del tree
    source_unchanged = digest(receipt['source']) == receipt['input_hashes']['source_native_sha256'] and digest(receipt['source_control']) == receipt['input_hashes']['source_control_sha256']
    checks = dict(finite=finite, indexed_triangles=indexed, positive_triangle_area=minimum_area > 1e-14,
        closed_two_face_edges=closed, consistently_oriented_edges=oriented_ok,
        no_orphans=no_orphans, connected_single_component=int(component_count) == 1,
        actual_XY_geometric_symmetry=symmetric, original_files_unchanged=source_unchanged)
    result = dict(date='2026-10-14', checks=checks, all_required_checks_pass=all(checks.values()),
        vertices=nv, triangles=nf, unique_edges=ne, Euler_characteristic=nv-ne+nf,
        connected_components=int(component_count), component_sizes_descending=np.sort(component_sizes)[::-1].tolist(),
        minimum_triangle_area=minimum_area, total_surface_area=area_sum,
        bounding_box_minimum=xyz.min(axis=0).tolist(), bounding_box_maximum=xyz.max(axis=0).tolist(),
        symmetry=symmetry, symmetry_tolerance=tolerance,
        geometry_sha256=receipt['geometry_sha256'], finish_receipt_sha256=digest(folder/'FINISH_RECEIPT.json'),
        verifier_code_sha256=digest(__file__), elapsed_seconds=time.perf_counter()-started,
        scope='Every saved vertex/triangle/edge; full geometric nearest-vertex reflection check. New topology has no original source-ID ancestry. This does not certify non-self-intersection, tangent continuity, volume preservation, fabrication or visual quality.')
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    shutil.copyfile(__file__, folder/'source_snapshot'/'finish_verify.py')
    print('VOLUME_FINISH_VERIFIED', checks, flush=True)


if __name__ == '__main__':
    main()
