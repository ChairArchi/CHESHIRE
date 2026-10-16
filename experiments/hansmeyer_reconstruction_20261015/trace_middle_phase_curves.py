"""Read-only connectivity/arc-coordinate probe of saved MIDDLE phase levelsets.

The arithmetic quad-centre fan is reconstructed from actual saved controls.
It is not asserted to be an original stored native file or a measured ridge.
Every graph crossing is identified by its native edge/vertex IDs, never XYZ
proximity. No surface geometry, ornament, render or source file is produced.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


REPO = Path(__file__).resolve().parents[2]
STATES = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
EDGE_CORNERS = np.asarray(((0, 1), (1, 2), (2, 0)))
KEY_DTYPE = np.dtype([('level', '<i8'), ('a', '<i8'), ('b', '<i8')])


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024**2), b''):
            digest.update(chunk)
    return digest.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def quantiles(value):
    value = np.asarray(value)
    value = value[np.isfinite(value)]
    return None if not len(value) else np.quantile(value, [0., .01, .1, .5, .9, .99, 1.]).tolist()


def bind(stage, sources):
    folder = STATES/stage
    meta_path = folder/'generation.json'
    meta = json.loads(meta_path.read_text(encoding='utf8'))
    if not meta['checks']['passed']:
        raise ValueError('Saved source checks failed: '+stage)
    sources[str(meta_path)] = sha(meta_path)
    for name, key in (('control_quad.npz', 'control_file_sha256'),
                      ('evidence.npz', 'evidence_file_sha256')):
        path = folder/name
        if sha(path) != meta[key]:
            raise ValueError('Saved immutable source changed: '+str(path))
        sources[str(path)] = meta[key]
    return folder


def triangle_gradients(points, scalar):
    e1, e2 = points[:, 1]-points[:, 0], points[:, 2]-points[:, 0]
    a = np.einsum('ij,ij->i', e1, e1)
    b = np.einsum('ij,ij->i', e1, e2)
    c = np.einsum('ij,ij->i', e2, e2)
    cross = np.cross(e1, e2)
    det = np.einsum('ij,ij->i', cross, cross)
    relative = np.divide(det, a*c, out=np.zeros_like(det), where=a*c > 0.)
    d1, d2 = scalar[:, 1]-scalar[:, 0], scalar[:, 2]-scalar[:, 0]
    valid = det > 0.
    alpha = np.divide(c*d1-b*d2, det, out=np.zeros_like(det), where=valid)
    beta = np.divide(a*d2-b*d1, det, out=np.zeros_like(det), where=valid)
    gradient = alpha[:, None]*e1+beta[:, None]*e2
    norm = np.linalg.norm(gradient, axis=1)
    maximum_edge = np.sqrt(np.maximum(np.maximum(a, c), a+c-2*b))
    return norm, norm*maximum_edge, relative, valid


def extract(xyz, quads, phase, source_faces, chunk):
    nv = len(xyz)
    selected = np.flatnonzero(source_faces)
    values = phase[quads[selected]]
    lo = int(np.ceil(values.min()/(2*np.pi)-1e-13))
    hi = int(np.floor(values.max()/(2*np.pi)+1e-13))
    levels = np.arange(lo, hi+1, dtype=np.int64)
    del values
    keys, triangles, barycentrics, lengths, gradients = [], [], [], [], []
    gradient_samples, relative_samples, dimensionless_samples = [], [], []
    counts = dict(triangles=0, degenerate_geometry=0, ill_conditioned_geometry=0,
                  zero_dimensionless_gradient=0, plateau_triangles=0,
                  isolated_vertex_touches=0, on_level_edges=0,
                  near_level_vertex_triangle_events=0)
    examples = []
    for start in range(0, len(selected), chunk):
        face_ids = selected[start:start+chunk]
        q = quads[face_ids]
        qxyz, qphi = xyz[q], phase[q]
        centres, centre_phi = qxyz.mean(axis=1), qphi.mean(axis=1)
        ids = np.stack((q, np.roll(q, -1, axis=1),
                        np.broadcast_to((nv+face_ids)[:, None], q.shape)), axis=-1).reshape(-1, 3)
        points = np.stack((qxyz, np.roll(qxyz, -1, axis=1),
                           np.broadcast_to(centres[:, None], qxyz.shape)), axis=-2).reshape(-1, 3, 3)
        scalar = np.stack((qphi, np.roll(qphi, -1, axis=1),
                           np.broadcast_to(centre_phi[:, None], qphi.shape)), axis=-1).reshape(-1, 3)
        tri_ids = (4*face_ids[:, None]+np.arange(4)).ravel()
        g, dimensionless, relative, geometry_valid = triangle_gradients(points, scalar)
        counts['triangles'] += len(ids)
        counts['degenerate_geometry'] += int(np.count_nonzero(~geometry_valid))
        counts['ill_conditioned_geometry'] += int(np.count_nonzero(relative < 1e-10))
        threshold = 256*np.finfo(float).eps*np.maximum(1., np.max(np.abs(scalar), axis=1))
        counts['zero_dimensionless_gradient'] += int(np.count_nonzero(dimensionless <= threshold))
        # Deterministic every-16 native triangle sample; every triangle contributes counts.
        sample = (tri_ids % 16) == 0
        gradient_samples.append(g[sample]); relative_samples.append(relative[sample])
        dimensionless_samples.append(dimensionless[sample])
        for k in levels:
            level = 2*np.pi*int(k)
            tolerance = 64*np.finfo(float).eps*max(1., abs(level))
            eligible = ((scalar.min(axis=1) <= level+tolerance) &
                        (scalar.max(axis=1) >= level-tolerance))
            if not np.any(eligible):
                continue
            rows = np.flatnonzero(eligible)
            residual = scalar[rows]-level
            zero = np.abs(residual) <= tolerance
            sign = np.where(zero, 0, np.sign(residual)).astype(np.int8)
            crossing = sign[:, EDGE_CORNERS[:, 0]]*sign[:, EDGE_CORNERS[:, 1]] < 0
            nzero = zero.sum(axis=1)
            npoints = nzero+crossing.sum(axis=1)
            counts['plateau_triangles'] += int(np.count_nonzero(nzero == 3))
            counts['isolated_vertex_touches'] += int(np.count_nonzero((nzero == 1)&(npoints == 1)))
            counts['on_level_edges'] += int(np.count_nonzero(nzero == 2))
            counts['near_level_vertex_triangle_events'] += int(np.count_nonzero(zero))
            for row in np.flatnonzero(nzero == 3)[:max(0, 12-len(examples))]:
                examples.append(dict(kind='PLATEAU_TRIANGLE', level_index=int(k),
                                     triangle_id=int(tri_ids[rows[row]])))
            take = np.flatnonzero(npoints == 2)
            if not len(take):
                continue
            real = rows[take]
            flags = np.concatenate((zero[take], crossing[take]), axis=1)
            record, feature = np.nonzero(flags)
            slot = np.cumsum(flags, axis=1)[record, feature]-1
            key = np.empty((len(take), 2, 3), np.int64)
            key[:, :, 0] = int(k)
            bary = np.zeros((len(take), 2, 3), float)
            is_vertex = feature < 3
            vr, vs, vf = record[is_vertex], slot[is_vertex], feature[is_vertex]
            vertex_ids = ids[real[vr], vf]
            key[vr, vs, 1] = vertex_ids; key[vr, vs, 2] = vertex_ids
            bary[vr, vs, vf] = 1.
            er, es = record[~is_vertex], slot[~is_vertex]
            edge = EDGE_CORNERS[feature[~is_vertex]-3]
            a, b = edge[:, 0], edge[:, 1]
            fraction = (level-scalar[real[er], a])/(scalar[real[er], b]-scalar[real[er], a])
            ea, eb = ids[real[er], a], ids[real[er], b]
            key[er, es, 1] = np.minimum(ea, eb)
            key[er, es, 2] = np.maximum(ea, eb)
            bary[er, es, a] = 1.-fraction; bary[er, es, b] = fraction
            segment_points = np.einsum('nkj,nji->nki', bary, points[real])
            length = np.linalg.norm(segment_points[:, 1]-segment_points[:, 0], axis=1)
            if np.any(length <= 0.) or not np.isfinite(length).all():
                raise ValueError('Zero/nonfinite extracted segment; no proximity merge.')
            keys.append(key.reshape(-1, 3)); triangles.append(np.repeat(tri_ids[real], 2))
            barycentrics.append(bary.reshape(-1, 3)); lengths.append(length); gradients.append(g[real])
        print(f'TRACE source faces {min(start+chunk, len(selected))}/{len(selected)}', flush=True)
    if not keys:
        raise ValueError('No saved phase levelsets cross the actual SOURCE surface.')
    raw_keys = np.concatenate(keys)
    unique_keys, first, inverse = np.unique(raw_keys, axis=0, return_index=True, return_inverse=True)
    edge_nodes = np.sort(inverse.reshape(-1, 2), axis=1)
    edge_nodes, edge_first, edge_count = np.unique(edge_nodes, axis=0, return_index=True, return_counts=True)
    all_triangles, all_bary = np.concatenate(triangles), np.concatenate(barycentrics)
    node_triangle = all_triangles[first]
    node_bary = all_bary[first]
    parent = node_triangle//4; corner = node_triangle%4
    native_ids = np.column_stack((quads[parent, corner], quads[parent, (corner+1)%4], nv+parent))
    node_points = np.empty((len(first), 3), float)
    for offset in range(0, len(first), chunk):
        sl = slice(offset, min(offset+chunk, len(first)))
        p = np.stack((xyz[native_ids[sl, 0]], xyz[native_ids[sl, 1]],
                      xyz[quads[parent[sl]]].mean(axis=1)), axis=1)
        node_points[sl] = np.einsum('nj,nji->ni', node_bary[sl], p)
    segment_length = np.linalg.norm(node_points[edge_nodes[:, 1]]-node_points[edge_nodes[:, 0]], axis=1)
    raw_length = np.concatenate(lengths)[edge_first]
    if np.max(np.abs(segment_length-raw_length)) > 2e-12:
        raise ValueError('Native barycentric crossing identity mismatch.')
    evidence = dict(node_keys=unique_keys, node_xyz=node_points, node_triangle_id=node_triangle,
                    node_barycentric=node_bary, edges=edge_nodes,
                    edge_triangle_id=all_triangles.reshape(-1, 2)[edge_first, 0],
                    edge_length=segment_length, edge_duplicate_triangle_records=edge_count,
                    edge_triangle_gradient_norm=np.concatenate(gradients)[edge_first])
    info = dict(level_indices=levels.tolist(), counters=counts, plateau_examples=examples,
                raw_segment_records=len(raw_keys)//2, graph_nodes=len(unique_keys),
                graph_edges=len(edge_nodes), duplicate_on_level_edge_records=int(np.sum(edge_count-1)),
                maximum_barycentric_identity_error=float(np.max(np.abs(segment_length-raw_length))),
                all_source_triangle_gradient_sample=quantiles(np.concatenate(gradient_samples)),
                all_source_triangle_dimensionless_gradient_sample=quantiles(np.concatenate(dimensionless_samples)),
                all_source_triangle_relative_gram_sample=quantiles(np.concatenate(relative_samples)),
                gradient_quantile_sampling='Deterministic global native triangle ID modulo16=0; counters evaluate every SOURCE triangle.',
                crossing_triangle_gradient_quantiles=quantiles(evidence['edge_triangle_gradient_norm']),
                crossing_pi_over_gradient_width_proxy=quantiles(np.divide(np.pi,
                    evidence['edge_triangle_gradient_norm'], out=np.full(len(edge_nodes), np.nan),
                    where=evidence['edge_triangle_gradient_norm'] > 0.)),
                width_proxy_limitation='pi/|intrinsic gradient of registered phase| is first-order crest-to-groove phase spacing, not a measured shoulder width or geometric ridge proof.')
    return evidence, info


def boundary_nodes(keys, quads, mask, nv, chunk):
    source_degree = np.bincount(quads[mask].ravel(), minlength=nv)
    total_degree = np.bincount(quads.ravel(), minlength=nv)
    boundary = np.zeros(len(keys), bool)
    exact = (keys[:, 1] == keys[:, 2]) & (keys[:, 1] < nv)
    boundary[exact] = source_degree[keys[exact, 1]] < total_degree[keys[exact, 1]]
    candidate = np.flatnonzero((keys[:, 1] != keys[:, 2]) & (keys[:, 2] < nv))
    radix = 2*nv
    code = keys[candidate, 1]*radix+keys[candidate, 2]
    unique, inverse = np.unique(code, return_inverse=True)
    counts = np.zeros(len(unique), np.int64)
    selected = np.flatnonzero(mask)
    for start in range(0, len(selected), chunk):
        q = quads[selected[start:start+chunk]]
        b = np.roll(q, -1, axis=1)
        edge_code = (np.minimum(q, b)*radix+np.maximum(q, b)).ravel()
        position = np.searchsorted(unique, edge_code)
        valid = position < len(unique)
        matched = np.zeros(len(position), bool)
        matched[valid] = unique[position[valid]] == edge_code[valid]
        counts += np.bincount(position[matched], minlength=len(unique))
    boundary[candidate] = counts[inverse] == 1
    return boundary


def graph_coordinates(evidence, source_boundary):
    edges = evidence['edges']; n = len(evidence['node_xyz'])
    graph = coo_matrix((np.ones(2*len(edges), np.int8),
                       (edges.ravel(), edges[:, ::-1].ravel())), shape=(n, n)).tocsr()
    count, labels = connected_components(graph, directed=False)
    degree = np.diff(graph.indptr)
    evidence.update(node_component=labels, node_degree=degree, node_source_boundary=source_boundary)
    node_arc = np.full(n, np.nan)
    component_edges = labels[edges[:, 0]]
    component_lengths = np.bincount(component_edges, weights=evidence['edge_length'], minlength=count)
    reports = []
    node_order = np.argsort(labels, kind='stable')
    bounds = np.searchsorted(labels[node_order], np.arange(count+1))
    for ci in range(count):
        ids = node_order[bounds[ci]:bounds[ci+1]]
        ends = ids[degree[ids] == 1]; branches = ids[degree[ids] > 2]
        closed = bool(np.all(degree[ids] == 2))
        regular_open = bool(len(ends) == 2 and not len(branches))
        status = 'CLOSED_REGULAR_LOOP' if closed else 'REGULAR_OPEN_CURVE' if regular_open else 'BRANCHED_OR_DEGENERATE_GRAPH'
        if closed or regular_open:
            start = int(ids.min()) if closed else int(ends.min())
            current, previous, arc = start, -1, 0.
            visited = 0
            while True:
                node_arc[current] = arc; visited += 1
                neighbours = graph.indices[graph.indptr[current]:graph.indptr[current+1]]
                options = neighbours[neighbours != previous]
                if not len(options):
                    break
                following = int(options.min()) if previous < 0 else int(options[0])
                if following == start:
                    break
                arc += float(np.linalg.norm(evidence['node_xyz'][following]-evidence['node_xyz'][current]))
                previous, current = current, following
                if visited > len(ids):
                    raise ValueError('Regular graph traversal cycled before its registered closure.')
            if visited != len(ids):
                raise ValueError('Regular graph arc coordinate omitted connected nodes.')
        reports.append(dict(component=ci, level_index=int(evidence['node_keys'][ids[0], 0]),
                            nodes=len(ids), edges=int(np.sum(degree[ids])//2), status=status,
                            physical_arc_length=float(component_lengths[ci]), endpoints=len(ends),
                            source_boundary_endpoints=int(np.count_nonzero(source_boundary[ends])),
                            nonboundary_endpoints=int(np.count_nonzero(~source_boundary[ends])),
                            branch_nodes=len(branches), maximum_degree=int(degree[ids].max()),
                            bounds_min=evidence['node_xyz'][ids].min(axis=0).tolist(),
                            bounds_max=evidence['node_xyz'][ids].max(axis=0).tolist()))
    evidence['node_arc_s'] = node_arc
    return reports


def reflection_check(evidence, vertex_pairs, face_pairs, nv):
    keys = evidence['node_keys']
    structured = np.ascontiguousarray(keys).view(KEY_DTYPE).ravel()
    reports = {}
    for axis, label in enumerate(('X', 'Y')):
        mirror = np.concatenate((vertex_pairs[label], nv+face_pairs[label]))
        mapped = mirror[keys[:, 1:]]
        expected = np.column_stack((keys[:, 0], np.sort(mapped, axis=1)))
        query = np.ascontiguousarray(expected).view(KEY_DTYPE).ravel()
        location = np.searchsorted(structured, query)
        valid = location < len(keys)
        good = np.zeros(len(keys), bool)
        good[valid] = np.all(keys[location[valid]] == expected[valid], axis=1)
        pairs = np.where(good, location, -1)
        evidence['node_mirror_'+label.lower()] = pairs
        reflected = evidence['node_xyz'][location[good]].copy(); reflected[:, axis] *= -1
        error = np.abs(evidence['node_xyz'][good]-reflected)
        reports[label] = dict(unmatched_nodes=int(np.count_nonzero(~good)),
                             coordinate_error_maximum=float(error.max(initial=0.)))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--chunk', type=int, default=65536)
    args = parser.parse_args(); root = args.output.resolve()
    if root.exists():
        raise FileExistsError('Existing research evidence is immutable; choose a fresh output.')
    started = time.perf_counter(); sources = {}; own_hash = sha(__file__)
    folder = bind('G06_MIDDLE', sources); owner_folder = bind('G03_SIDEWALL', sources)
    with np.load(folder/'control_quad.npz', allow_pickle=False) as saved:
        xyz, q, chart = saved['xyz'], saved['faces'], saved['chart']
    with np.load(folder/'evidence.npz', allow_pickle=False) as saved:
        phase = saved['directional_phase']; envelope = saved['envelope']
        vp = {a:saved['mirror_'+a.lower()+'_vertex_pairs'] for a in ('X', 'Y')}
        fp = {a:saved['mirror_'+a.lower()+'_face_pairs'] for a in ('X', 'Y')}
    with np.load(owner_folder/'control_quad.npz', allow_pickle=False) as saved:
        q3 = saved['faces']
    with np.load(owner_folder/'evidence.npz', allow_pickle=False) as saved:
        owners = saved['face_event_ids']
    ancestor = q
    for _ in range(3):
        ancestor = ancestor.reshape(-1, 4, 4)[:, :, 1]
    if not np.array_equal(ancestor, q3) or phase.shape != (len(xyz),):
        raise ValueError('Actual G3 ownership or registered G6 phase correspondence differs.')
    mask = np.repeat(owners == 0, 4**3)
    print('EXTRACT registered MIDDLE phase candidate curves on reconstructed SOURCE fans', flush=True)
    evidence, extraction = extract(xyz, q, phase, mask, args.chunk)
    boundary = boundary_nodes(evidence['node_keys'], q, mask, len(xyz), args.chunk)
    components = graph_coordinates(evidence, boundary)
    symmetry = reflection_check(evidence, vp, fp, len(xyz))
    tri = evidence['node_triangle_id']; parent = tri//4; corner = tri%4
    node_material_t = (evidence['node_barycentric'][:, 0]*chart[q[parent, corner], 0]+
                       evidence['node_barycentric'][:, 1]*chart[q[parent, (corner+1)%4], 0]+
                       evidence['node_barycentric'][:, 2]*chart[q[parent], 0].mean(axis=1))
    node_envelope = (evidence['node_barycentric'][:, 0]*envelope[q[parent, corner]]+
                     evidence['node_barycentric'][:, 1]*envelope[q[parent, (corner+1)%4]]+
                     evidence['node_barycentric'][:, 2]*envelope[q[parent]].mean(axis=1))
    node_chart = (evidence['node_barycentric'][:, 0, None]*chart[q[parent, corner]]+
                  evidence['node_barycentric'][:, 1, None]*chart[q[parent, (corner+1)%4]]+
                  evidence['node_barycentric'][:, 2, None]*chart[q[parent]].mean(axis=1))
    evidence.update(node_material_t=node_material_t, node_middle_envelope=node_envelope,
                    node_chart=node_chart)
    close_associations = []
    ray_path = REPO/'experiments/fold_junction_development_20261015/diagnosis_visible_face_owners_results.json'
    if ray_path.exists():
        sources[str(ray_path)] = sha(ray_path)
        rays = json.loads(ray_path.read_text(encoding='utf8'))['rays']
        node_theta = np.arctan2(node_chart[:, 2], node_chart[:, 1])
        for ray in rays:
            face_id, ci = int(ray['G6_quad_id']), int(ray['native_fan_corner'])
            bary = np.asarray(ray['barycentric'])
            tri_chart = np.stack((chart[q[face_id, ci]], chart[q[face_id, (ci+1)%4]],
                                  chart[q[face_id]].mean(axis=0)))
            material = bary@tri_chart
            theta = float(np.arctan2(material[2], material[1]))
            triangle_phase = np.asarray((phase[q[face_id, ci]], phase[q[face_id, (ci+1)%4]],
                                         phase[q[face_id]].mean()))
            phase_here = float(bary@triangle_phase)
            k = int(np.rint(phase_here/(2*np.pi)))
            candidates = np.flatnonzero(evidence['node_keys'][:, 0] == k)
            if not len(candidates):
                continue
            tri_theta = np.arctan2(tri_chart[:, 2], tri_chart[:, 1])
            tri_theta = theta+np.arctan2(np.sin(tri_theta-theta), np.cos(tri_theta-theta))
            uv = np.column_stack((tri_chart[:, 0], tri_theta))
            tri_xyz = np.stack((xyz[q[face_id, ci]], xyz[q[face_id, (ci+1)%4]],
                                xyz[q[face_id]].mean(axis=0)))
            matrix = (uv[1:]-uv[0]).T
            if abs(np.linalg.det(matrix)) < 1e-18:
                continue
            jacobian = (tri_xyz[1:]-tri_xyz[0]).T@np.linalg.inv(matrix)
            difference = np.column_stack((node_material_t[candidates]-material[0],
                np.arctan2(np.sin(node_theta[candidates]-theta), np.cos(node_theta[candidates]-theta))))
            estimate = difference@jacobian.T
            distance = np.linalg.norm(estimate, axis=1)
            selected_node = int(candidates[np.argmin(distance)])
            component_id = int(evidence['node_component'][selected_node])
            close_associations.append(dict(normalized_image_xy=ray['normalized_image_xy'],
                original_ray_quad=face_id, registered_phase=phase_here,
                nearest_phase_level_index=k, candidate_component=component_id,
                candidate_node=selected_node,
                local_chart_metric_distance_estimate=float(distance.min()),
                component_status=components[component_id]['status'],
                component_physical_arc_length=components[component_id]['physical_arc_length']))
    statuses = {key:sum(c['status'] == key for c in components) for key in
                ('CLOSED_REGULAR_LOOP', 'REGULAR_OPEN_CURVE', 'BRANCHED_OR_DEGENERATE_GRAPH')}
    summary = dict(component_count=len(components), component_status_counts=statuses,
                   total_physical_arc_length=float(evidence['edge_length'].sum()),
                   branches=int(np.count_nonzero(evidence['node_degree'] > 2)),
                   endpoints=int(np.count_nonzero(evidence['node_degree'] == 1)),
                   source_boundary_endpoints=int(np.count_nonzero((evidence['node_degree'] == 1)&boundary)),
                   nonboundary_endpoints=int(np.count_nonzero((evidence['node_degree'] == 1)&~boundary)),
                   arc_coordinate_nodes=int(np.count_nonzero(np.isfinite(evidence['node_arc_s']))),
                   zero_middle_envelope_nodes=int(np.count_nonzero(node_envelope == 0.)),
                   node_material_t_quantiles=quantiles(node_material_t), reflection=symmetry)
    root.mkdir(parents=True)
    payload = root/'PHASE_CURVE_GRAPH.npz'
    np.savez_compressed(payload, **evidence)
    if sha(__file__) != own_hash:
        raise ValueError('Executed research helper changed during extraction.')
    report = dict(kind='REGISTERED_MIDDLE_PHASE_GUIDED_CANDIDATE_CURVE_GRAPH', date='2026-10-15',
                  source_control=str(folder/'control_quad.npz'), sources=sources,
                  helper=dict(path=str(Path(__file__).resolve()), sha256=own_hash),
                  control_xyz_sha256=ah(xyz), control_faces_sha256=ah(q), phase_sha256=ah(phase),
                  input_vertices=len(xyz), input_quads=len(q), source_quads=int(mask.sum()),
                  correspondence='Native fan triangleID=4*quadID+corner; vertex IDs [q[corner],q[next],nv+quadID]. Every graph node stores a native edge/vertex key, one actual triangleID and barycentrics.',
                  phase_origin='Exact saved directional_phase, evaluated before MIDDLE deformation and registered onto actual MIDDLE controls; not reevaluated from current XYZ.',
                  surface='Arithmetic quad-centre fan reconstructed from actual saved G06_MIDDLE controls; not an original stored native file.',
                  selection='All actual G3 SOURCE faces repeated through verified G6 ancestry. Attached WALL/CAP roles excluded to avoid assuming duplicated chart sheets are one parent. No artist coordinate or nearest-world merge.',
                  arc_coordinate='Each regular open component uses its minimum-ID endpoint as origin; each regular loop uses a source-ID-defined cut and periodic total length. No per-face reset. Branch/degenerate components retain NaN arc coordinates and require explicit junction treatment.',
                  limitations='Phase-guided candidate curves, NOT independently measured geometric ridges or proof of a globally integrable 2D atlas. Scalar cusps at reflection seams and plateau degeneracies are explicit. This performs no new geometry/ornament/model/render.',
                  summary=summary, extraction=extraction, components=components,
                  previous_close_ray_candidate_associations=close_associations,
                  close_association_limitation='Diagnostic only: nearest same-phase-level node under the old hit triangle material-chart metric. Uses registered face/barycentric evidence, not a new ray or world-nearest sheet/ridge detection; never selects production geometry.',
                  evidence=dict(path=str(payload), sha256=sha(payload), bytes=payload.stat().st_size),
                  elapsed_seconds=time.perf_counter()-started)
    (root/'PHASE_CURVE_GRAPH.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(summary, indent=2), flush=True)
    print('PHASE_CURVE_GRAPH_COMPLETE', report['elapsed_seconds'], flush=True)


if __name__ == '__main__':
    main()
