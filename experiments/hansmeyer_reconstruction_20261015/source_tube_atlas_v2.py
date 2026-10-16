"""Certified source-domain construction; fixed ornament design is not tuned.

Adaptive native-curve stationing resolves skipped intrinsic bends. Cross
widths are solved against source-chart convexity and global collisions.
The resulting convex coarse partition carries affine UV through refinement.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import run_spine_reconstruction_v3 as base
import native_curve_sampling as native_curve


def qgrid(rows, periodic):
    r, u = np.meshgrid(np.arange(rows if periodic else rows-1), np.arange(8), indexing='ij')
    nr = (r+1)%rows
    return np.stack((r*9+u, nr*9+u, nr*9+u+1, r*9+u+1), axis=-1).reshape(-1, 4)


def sat_pairs(tri, pairs):
    if not len(pairs):
        return np.zeros(0, bool)
    a, b = tri[pairs[:, 0]], tri[pairs[:, 1]]
    edge = np.concatenate((np.roll(a, -1, axis=1)-a, np.roll(b, -1, axis=1)-b), axis=1)
    axis = np.stack((-edge[:, :, 1], edge[:, :, 0]), axis=-1)
    axis /= np.maximum(np.linalg.norm(axis, axis=2)[:, :, None], 1e-30)
    pa, pb = np.einsum('nki,nji->nkj', axis, a), np.einsum('nki,nji->nkj', axis, b)
    gap = np.minimum(pa.max(axis=2), pb.max(axis=2))-np.maximum(pa.min(axis=2), pb.min(axis=2))
    return np.all(gap > 1e-11, axis=1)


def overlap_intervals(uv, q):
    triangles = np.concatenate((q[:, [0, 1, 2]], q[:, [0, 2, 3]]))
    tri = uv[triangles]; low, high = tri.min(axis=1), tri.max(axis=1)
    order = np.argsort(low[:, 0]); active = np.empty(0, np.int64); pairs = []
    # Exact AABB sweep avoids a global maximum-radius neighbourhood explosion.
    for i in order:
        active = active[high[active, 0] >= low[i, 0]-1e-12]
        hit = active[(high[active, 1] >= low[i, 1]-1e-12)&(low[active, 1] <= high[i, 1]+1e-12)]
        if len(hit):
            pairs.append(np.column_stack((np.full(len(hit), i, np.int64), hit)))
        active = np.r_[active, i]
    if not pairs:
        return np.empty((0, 2), np.int64), 0
    pairs = np.concatenate(pairs); hits = []
    for start in range(0, len(pairs), 65536):
        part = pairs[start:start+65536]
        hits.append(part[sat_pairs(tri, part)])
    collision = np.concatenate(hits)
    intervals = (collision % len(q))//8
    return np.unique(np.sort(intervals, axis=1), axis=0), len(collision)


def convex_intervals(uv_grid, periodic, orientation):
    q = qgrid(len(uv_grid), periodic)
    p = uv_grid.reshape(-1, 2)[q]
    f, b = np.roll(p, -1, axis=1)-p, np.roll(p, 1, axis=1)-p
    det = base.cross2(f, b)*orientation
    scale = np.linalg.norm(f, axis=2)*np.linalg.norm(b, axis=2)
    good = np.all(det > 128*np.finfo(float).eps*np.maximum(scale, 1e-30), axis=1)
    return good.reshape(-1, 8).all(axis=1)


def recover_order(surface, graph, info):
    nodes = np.flatnonzero(graph['node_component'] == info['component'])
    order = nodes[np.argsort(graph['node_arc_s'][nodes])]
    report = json.loads(base.GRAPH.read_text(encoding='utf8'))
    periodic = report['components'][info['component']]['status'] == 'CLOSED_REGULAR_LOOP'
    order, periodic = base.longest_domain_run(graph, order, periodic, surface.source_mask)
    if info.get('source_coverage_cut'):
        edge_map = {tuple(pair):i for i, pair in enumerate(np.sort(graph['edges'], axis=1))}
        pairs = np.sort(np.column_stack((order[:-1], order[1:])), axis=1)
        s = np.r_[0., np.cumsum([graph['edge_length'][edge_map[tuple(pair)]] for pair in pairs])]
        lo, hi = info['source_coverage_cut']['original_arc_interval']
        order = order[(s >= lo)&(s <= hi)]
    return order


class DomainResolutionError(ValueError):
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def refine_two_sided_stations(surface, graph, order, old_strip, periodic=False,
                              max_rounds=12, max_stations=1025):
    """Resolve actual two-sided tiny source quads as well as centre derivatives."""
    data = native_curve._data(graph, order, periodic)
    targets = np.asarray(old_strip['s'], float).copy()
    tolerance = 64*np.finfo(float).eps*max(data['total_length'], 1.)
    history = []; vertices = 0; midpoints = 0; expected = None
    stop = 'ROUND_BUDGET'
    if len(targets) > max_stations:
        raise ValueError('Initial native source station budget exceeded.')
    for iteration in range(max_rounds+1):
        curve = native_curve._sample(surface, data, targets)
        local = native_curve._cross(curve['tangent_uv'], curve['across_uv'])
        if expected is None:
            expected = float(np.sign(np.median(local)))
        if not np.isfinite(local).all() or expected == 0. or np.any(local*expected <= 0.):
            raise ValueError('Actual native BODY chart orientation is singular/inconsistent.')
        centre = native_curve._intervals(curve, expected)
        tiny_width = 1e-3*np.interp(targets, old_strip['s'], old_strip['base_width'])
        uv = np.empty((len(targets), 9, 2))
        for row in range(len(targets)):
            got = surface.trace_across(int(curve['triangle_ids'][row]), curve['barycentric'][row],
                curve['across'][row], base.spine.U_KNOTS*(.5*tiny_width[row]))
            if not got['valid'].all():
                raise DomainResolutionError('Actual tiny source cross section left its BODY fan.',
                    dict(round=iteration, row=row, arc=float(targets[row]), statuses=got['status'].tolist()))
            angle = np.arctan2(got['chart'][:, 2], got['chart'][:, 1])
            angle = curve['uv'][row, 1]+np.arctan2(np.sin(angle-curve['uv'][row, 1]), np.cos(angle-curve['uv'][row, 1]))
            uv[row] = np.column_stack((got['chart'][:, 0], angle))
        points = uv.reshape(-1, 2)[qgrid(len(targets), periodic)]
        f = np.roll(points, -1, axis=1)-points; b = np.roll(points, 1, axis=1)-points
        determinant = base.cross2(f, b)*expected
        scale = np.linalg.norm(f, axis=2)*np.linalg.norm(b, axis=2)
        finite_good = np.all(determinant > 128*np.finfo(float).eps*np.maximum(scale, 1e-30), axis=1).reshape(-1, 8).all(axis=1)
        bad = np.flatnonzero(centre['bad'] | ~finite_good)
        entry = dict(round=iteration, stations=len(targets), bad_intervals=bad.tolist(),
            centre_bad_intervals=np.flatnonzero(centre['bad']).tolist(),
            tiny_finite_bad_intervals=np.flatnonzero(~finite_good).tolist(),
            minimum_actual_two_sided_signed_J=float(determinant.min()),
            minimum_actual_two_sided_relative_J=float((determinant/np.maximum(scale, 1e-300)).min()),
            tiny_physical_width_range=[float(tiny_width.min()), float(tiny_width.max())],
            bad_arc_intervals=np.column_stack((centre['start'][bad], centre['stop'][bad])).tolist())
        history.append(entry)
        print('SOURCE_TUBE_TWO_SIDED_STATIONS', entry, flush=True)
        if not len(bad):
            stop = 'POSITIVE_CENTRE_AND_ACTUAL_TWO_SIDED_TINY_QUADS'; break
        if iteration == max_rounds:break
        proposed = []; nv = 0; nm = 0
        for interval in bad:
            a, b = centre['start'][interval], centre['stop'][interval]
            all_s, all_uv = data['cumulative'], data['vertex_uv']
            if periodic and b > data['total_length']:
                all_s = np.r_[all_s, data['cumulative']+data['total_length']]
                shifted = data['vertex_uv'].copy(); shifted[:, 1] += data['theta_winding']
                all_uv = np.vstack((all_uv, shifted))
            inside = (all_s > a+tolerance)&(all_s < b-tolerance)
            candidates = all_s[inside]
            chord = centre['stop_uv'][interval]-centre['start_uv'][interval]
            deviation = abs(native_curve._cross(all_uv[inside]-centre['start_uv'][interval], chord))
            if len(candidates) and deviation.max() > 1e-14*max(np.linalg.norm(chord), 1e-30):
                chosen = float(candidates[np.argmax(deviation)]); nv += 1
            else:
                chosen = .5*(a+b); nm += 1
            proposed.append(chosen % data['total_length'] if periodic else chosen)
        merged = np.sort(np.r_[targets, proposed]); merged = merged[np.r_[True, np.diff(merged) > tolerance]]
        if len(merged) > max_stations:
            stop = 'STATION_BUDGET'; break
        if len(merged) == len(targets):
            stop = 'NO_DISTINCT_INSERTION'; break
        vertices += nv; midpoints += nm; targets = merged
    meta = dict(kind='ACTUAL_TWO_SIDED_NATIVE_SOURCE_TUBE_STATION_REFINEMENT',
        passed=not len(bad), stop_reason=stop, expected_source_orientation_sign=expected,
        initial_stations=len(old_strip['s']), final_stations=len(curve['s']),
        max_rounds=max_rounds, max_stations=max_stations,
        inserted_native_graph_vertices=vertices, inserted_midpoints=midpoints,
        unresolved_interval_indices=bad.tolist(), history=history,
        unchanged='Node count, peak height/width/depth budgets, pitch, section and CC coefficients; only actual native source-guide resolution changes.',
        limitation='Numerical local two-sided source-chart check, not global injectivity or beauty. Genuine unresolved kinks stop explicitly.')
    if not meta['passed']:
        raise DomainResolutionError('Actual two-sided source tube remains unresolved within bounded native station refinement.', meta)
    return curve, meta


def construct(surface, graph, old_strip, info, evidence):
    order = recover_order(surface, graph, info)
    curve, station_meta = refine_two_sided_stations(surface, graph, order, old_strip,
                                                    periodic=info['periodic'], max_rounds=12, max_stations=1025)
    if not station_meta.get('passed', False):
        raise ValueError('Native curve centre Jacobian unresolved: '+str(station_meta))
    s = curve['s']; rows = len(s); periodic = info['periodic']
    normals = curve['normal']; tangent = curve['tangent'].copy()
    tangent -= normals*np.einsum('ij,ij->i', tangent, normals)[:, None]
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    across = np.cross(normals, tangent)
    width = np.interp(s, old_strip['s'], old_strip['width'])
    depth = np.interp(s, old_strip['s'], old_strip['prominence'])
    usable = np.interp(s, old_strip['s'], old_strip['base_width'])
    centre_uv = curve['uv']; orientation = float(station_meta['expected_source_orientation_sign'])
    cache = {}
    def row_sample(row, base_width):
        key = (int(row), float(base_width))
        if key not in cache:
            got = surface.trace_across(int(curve['triangle_ids'][row]), curve['barycentric'][row],
                across[row], base.spine.U_KNOTS*(.5*base_width))
            if not got['valid'].all():
                raise ValueError('SOURCE boundary encountered inside already clipped source tube.')
            a = np.arctan2(got['chart'][:, 2], got['chart'][:, 1])
            a = centre_uv[row, 1]+np.arctan2(np.sin(a-centre_uv[row, 1]), np.cos(a-centre_uv[row, 1]))
            got['uv'] = np.column_stack((got['chart'][:, 0], a))
            cache[key] = got
        return cache[key]
    def grid(values):
        samples = [row_sample(row, values[row]) for row in range(rows)]
        return {key:np.asarray([item[key] for item in samples]) for key in
                ('xyz', 'chart', 'uv', 'triangle_ids', 'barycentric')}
    def pair_convex(i, ratio, values):
        j = (i+1)%rows
        uv = np.stack((row_sample(i, values[i]*ratio)['uv'], row_sample(j, values[j]*ratio)['uv']))
        return bool(convex_intervals(uv, False, orientation)[0])
    def collision_free(i, j, ratio, values):
        rr = np.unique(np.asarray((i, (i+1)%rows, j, (j+1)%rows)))
        uv = {int(row):row_sample(int(row), values[row]*ratio)['uv'] for row in rr}
        def triangles(interval):
            p = np.stack((uv[interval], uv[(interval+1)%rows]))
            return p.reshape(-1, 2)[np.concatenate((qgrid(2, False)[:, [0, 1, 2]], qgrid(2, False)[:, [0, 2, 3]]))]
        a, b = triangles(i), triangles(j)
        tri = np.concatenate((a, b))
        aa, bb = np.meshgrid(np.arange(len(a)), len(a)+np.arange(len(b)), indexing='ij')
        pairs = np.column_stack((aa.ravel(), bb.ravel()))
        if i == j:
            pairs = pairs[pairs[:, 0] < pairs[:, 1]-len(a)]
        return not sat_pairs(tri, pairs).any()
    history = []
    for iteration in range(8):
        sampled = grid(usable)
        good = convex_intervals(sampled['uv'], periodic, orientation)
        q0 = qgrid(rows, periodic)
        collisions, collision_triangles = overlap_intervals(sampled['uv'].reshape(-1, 2), q0) if good.all() else (np.empty((0, 2), np.int64), -1)
        history.append(dict(iteration=iteration, nonconvex_intervals=int((~good).sum()),
            global_overlap_triangle_pairs=int(collision_triangles), global_overlap_interval_pairs=len(collisions),
            median_usable_base=float(np.median(usable)), minimum_usable_base=float(usable.min())))
        print('SOURCE_TUBE_DOMAIN', history[-1], flush=True)
        if good.all() and not len(collisions):
            break
        bounds = usable.copy()
        for i in np.flatnonzero(~good):
            if not pair_convex(int(i), 1e-3, usable):
                raise ValueError('Infinitesimal-positive corridor still fails at tiny finite width; along geometry resolution required.')
            lo, hi = 1e-3, 1.
            for _ in range(12):
                mid = (lo+hi)/2
                if pair_convex(int(i), mid, usable): lo = mid
                else: hi = mid
            for row in (int(i), (int(i)+1)%rows):
                bounds[row] = min(bounds[row], .9*lo*usable[row])
        for i, j in collisions:
            if not collision_free(int(i), int(j), 1e-3, usable):
                raise ValueError('Phase source centre curve has an unresolved global crossing.')
            lo, hi = 1e-3, 1.
            for _ in range(12):
                mid = (lo+hi)/2
                if collision_free(int(i), int(j), mid, usable): lo = mid
                else: hi = mid
            for row in (int(i), (int(i)+1)%rows, int(j), (int(j)+1)%rows):
                bounds[row] = min(bounds[row], .9*lo*usable[row])
        usable = bounds
    else:
        raise ValueError('Source tube reach solver did not converge; no forced inverse.')
    height = np.minimum(.35*usable, .6*depth)
    if np.median(height) < .020:
        raise ValueError('Certified corridor cannot sustain meaningful median node height.')
    strip = dict(xyz0=sampled['xyz'], chart0=sampled['chart'], normal=normals, across=across,
                 width=width, prominence=depth, base_width=usable, guides_prepooled=True, s=s)
    new_info = dict(info, source_tube=dict(stationing=station_meta, domain_history=history,
        requested_rows=len(old_strip['s']), certified_rows=rows,
        source_uv='Actual native-source t/theta; convex coarse quads with all-pair positive-area overlap exclusion. Affine UV birth-coordinate refinement partitions these quads.',
        guide='Original registered phase contour, cached actual shoulder/prominence budgets; no independent peak offsets.',
        node_height_median=float(np.median(height))))
    new_evidence = dict(evidence, source_grid_triangle_ids=sampled['triangle_ids'],
        source_grid_barycentric=sampled['barycentric'], source_uv0=sampled['uv'],
        source_curve=curve, source_usable_base_width=usable)
    return strip, new_info, new_evidence


def affine_uv_refinement(uv0, q0, expected):
    uv = uv0.reshape(-1, 2); q = q0
    for _ in range(2):
        t = base.spine.topology(q, len(uv)); nv, ne, nf = len(uv), len(t['edges']), len(q)
        uv = np.concatenate((uv, uv[t['edges']].mean(axis=1), uv[q].mean(axis=1)))
        following = t['fe']; previous = np.roll(following, 1, axis=1)
        q = np.stack((previous+nv, q, following+nv,
            np.broadcast_to((nv+ne+np.arange(nf))[:, None], q.shape)), axis=-1).reshape(-1, 4)
    if not np.array_equal(q, expected):
        raise ValueError('Affine source-coordinate and formed scaffold birth IDs differ.')
    return uv


def main():
    p = argparse.ArgumentParser(); p.add_argument('--parent', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise FileExistsError('Frozen source tube proof already exists.')
    state = base.load_tree(a.parent, {})
    report = json.loads(base.GRAPH.read_text(encoding='utf8'))
    with np.load(report['evidence']['path'], allow_pickle=False) as z: graph = {k:z[k] for k in z.files}
    with np.load(report['source_control'], allow_pickle=False) as z: xyz, q, chart = z['xyz'], z['faces'], z['chart']
    with np.load(base.STATES/'G06_MIDDLE/evidence.npz', allow_pickle=False) as z: phase = z['directional_phase']
    with np.load(base.STATES/'G03_SIDEWALL/control_quad.npz', allow_pickle=False) as z: q3, c3 = z['faces'], z['chart']
    with np.load(base.STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z: owner = z['face_event_ids']
    cap = np.all(c3[q3, 0] == 0., axis=1)|np.all(c3[q3, 0] == 1., axis=1)
    surface = base.NativeSurface(xyz, q, phase, np.repeat((owner == 0)&~cap, 64), chart)
    a.output.mkdir(parents=True)
    try:
        strip, info, evidence = construct(surface, graph, state['strip'], state['info'], state['evidence'])
        delta, qf, cf, meta, formation = base.spine.form(strip, periodic=info['periodic'],
            cell_count=info['node_count'], phase_origin=info['phase_origin'], total_length=info['total_length'])
        uv = affine_uv_refinement(evidence['source_uv0'], qgrid(len(strip['s']), info['periodic']), qf)
        encoded = np.column_stack((uv[:, 0], np.cos(uv[:, 1]), np.sin(uv[:, 1])))
        atlas = base.SourceAtlas(encoded, qf, delta, formation['logical_refined'], verify_global=False)
        formation['source_uv_refined'] = uv; formation['source_chart_transfer'] = encoded
        saved = base.receipt_helper.save_tree(a.output, 'CERTIFIED_PARENT', dict(strip=strip, info=info, evidence=evidence, formation=formation))
        result = dict(passed=True, info=info, formation=meta, atlas=atlas.metadata, evidence=saved,
            global_injectivity='Proved on convex coarse source quads by all-pair SAT; affine source-coordinate midpoint/face-centre refinement partitions the same quads.')
    except ValueError as error:
        result = dict(passed=False, reason=str(error))
    result['helper_sha256'] = base.sha(__file__)
    base.write(a.output/'SOURCE_TUBE_PROOF.json', result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__': main()
