"""Adaptive source-UV sampling of an immutable native phase-curve graph.

No model is generated. Refinement responds only to signed source-chart
centre/across orientation, never to world-space tangent angles or an image.
"""
from pathlib import Path

import numpy as np


def helper_paths():
    return [Path(__file__).resolve()]


def _cross(a, b):
    return a[..., 0]*b[..., 1]-a[..., 1]*b[..., 0]


def _unit(value):
    length = np.linalg.norm(value)
    if not np.isfinite(length) or length <= 1e-15:
        raise ValueError('Undefined immutable native curve direction.')
    return value/length


def _data(graph, node_order, periodic):
    order = np.asarray(node_order, dtype=np.int64)
    if order.ndim != 1 or len(order) < 2 or len(np.unique(order)) != len(order):
        raise ValueError('A nonduplicated ordered connected graph path is required.')
    edges = np.asarray(graph['edges'])
    edge_map = {tuple(pair):i for i,pair in enumerate(np.sort(edges, axis=1))}
    pairs = np.column_stack((order[:-1], order[1:]))
    if periodic:
        pairs = np.vstack((pairs, (order[-1], order[0])))
    edge_ids = []
    for pair in np.sort(pairs, axis=1):
        if tuple(pair) not in edge_map:
            raise ValueError('Native curve order crosses a graph gap.')
        edge_ids.append(edge_map[tuple(pair)])
    edge_ids = np.asarray(edge_ids, dtype=np.int64)
    lengths = np.asarray(graph['edge_length'])[edge_ids]
    if not np.isfinite(lengths).all() or np.any(lengths <= 0.):
        raise ValueError('Actual positive native graph edge lengths required.')
    cumulative = np.r_[0., np.cumsum(lengths)]
    if 'node_chart' not in graph:
        raise ValueError('Actual native graph node_chart correspondence is required.')
    chart = np.asarray(graph['node_chart'])[order]
    theta = np.arctan2(chart[:, 2], chart[:, 1])
    if periodic:
        theta = np.unwrap(np.r_[theta, theta[0]])
        material_t = np.r_[chart[:, 0], chart[0, 0]]
    else:
        theta = np.unwrap(theta)
        material_t = chart[:, 0]
    uv_vertices = np.column_stack((material_t, theta))
    winding = (theta[-1]-theta[0]) if periodic else 0.
    return dict(order=order, pairs=pairs, edge_ids=edge_ids, lengths=lengths,
        cumulative=cumulative, total_length=float(cumulative[-1]),
        vertex_uv=uv_vertices, theta_winding=float(winding), graph=graph,
        periodic=bool(periodic))


def _sample(surface, data, targets):
    targets = np.asarray(targets, dtype=float)
    length = data['total_length']
    tolerance = 64*np.finfo(float).eps*max(length, 1.)
    if targets.ndim != 1 or not len(targets) or not np.isfinite(targets).all():
        raise ValueError('Finite one-dimensional source-arc targets required.')
    if np.any(np.diff(targets) <= 0.) or targets.min() < -tolerance or targets.max() > length+tolerance:
        raise ValueError('Targets must be strictly ordered inside the actual native path.')
    if data['periodic'] and targets[-1] >= length-tolerance:
        raise ValueError('Periodic target endpoint L duplicates the origin; use endpoint=False.')
    targets = np.clip(targets, 0., length)
    cumulative, lengths = data['cumulative'], data['lengths']
    segment = np.clip(np.searchsorted(cumulative, targets, side='right')-1, 0, len(lengths)-1)
    graph = data['graph']
    ids = np.asarray(graph['edge_triangle_id'])[data['edge_ids'][segment]].copy()
    bary = np.empty((len(targets), 3))
    tangents = np.empty_like(bary)
    across = np.empty_like(bary)
    across_uv = np.empty((len(targets), 2))
    tangent_uv = np.empty_like(across_uv)
    unwrapped_reference = np.empty(len(targets))
    for row, edge in enumerate(segment):
        triangle = surface._triangle(int(ids[row]))
        points, normal, gram = triangle
        a, b = np.asarray(graph['node_xyz'])[data['pairs'][edge]]
        fraction = (targets[row]-cumulative[edge])/lengths[edge]
        bary[row] = ((1-fraction)*surface._barycentric(a, triangle)+
                     fraction*surface._barycentric(b, triangle))
        tangent = _unit(b-a)
        if abs(tangent@normal) > 1e-7:
            raise ValueError('Registered native edge tangent left its exact fan plane.')
        tangents[row] = tangent
        across[row] = _unit(np.cross(normal, tangent))
        face, corner = divmod(int(ids[row]), 4)
        q = surface.quads[face]
        native_chart = np.stack((surface.chart[q[corner]], surface.chart[q[(corner+1) % 4]],
                                 surface.chart[q].mean(axis=0)))
        actual_chart = bary[row]@native_chart
        rho2 = actual_chart[1]**2+actual_chart[2]**2
        if rho2 <= 1e-20:
            raise ValueError('Polar chart axis is not a valid BODY source chart.')
        e1, e2, aa, bb, cc, determinant = gram
        for vector, destination in ((tangent, tangent_uv), (across[row], across_uv)):
            r1, r2 = vector@e1, vector@e2
            du, dv = (cc*r1-bb*r2)/determinant, (aa*r2-bb*r1)/determinant
            derivative = np.asarray((-du-dv, du, dv))@native_chart
            destination[row] = (derivative[0],
                (actual_chart[1]*derivative[2]-actual_chart[2]*derivative[1])/rho2)
        unwrapped_reference[row] = ((1-fraction)*data['vertex_uv'][edge, 1]+
                                   fraction*data['vertex_uv'][edge+1, 1])
    curve = surface.sample(ids, bary)
    if not curve['valid'].all():
        raise ValueError('An adaptive target left its registered SOURCE fan.')
    theta = np.arctan2(curve['chart'][:, 2], curve['chart'][:, 1])
    theta += 2*np.pi*np.round((unwrapped_reference-theta)/(2*np.pi))
    curve.update(tangent=tangents.copy(), across=across, uv=np.column_stack((curve['chart'][:, 0], theta)),
        across_uv=across_uv, tangent_uv=tangent_uv, s=targets.copy(),
        total_length=length, periodic=data['periodic'], theta_winding=data['theta_winding'],
        native_segment_index=segment.copy())
    return curve


def sample_targets(surface, graph, node_order, targets, periodic=False):
    """Exact native edge/bary samples at arbitrary increasing physical arcs."""
    return _sample(surface, _data(graph, node_order, periodic), targets)


def _intervals(curve, expected_sign):
    uv, across = curve['uv'], curve['across_uv']
    if curve['periodic']:
        following = np.roll(uv, -1, axis=0)
        following[-1, 1] += curve['theta_winding']
        next_across = np.roll(across, -1, axis=0)
        stop_s = np.r_[curve['s'][1:], curve['s'][0]+curve['total_length']]
        start_s = curve['s']
    else:
        following, uv = uv[1:], uv[:-1]
        next_across, across = across[1:], across[:-1]
        start_s, stop_s = curve['s'][:-1], curve['s'][1:]
    chord = following-uv
    first, second = expected_sign*_cross(chord, across), expected_sign*_cross(chord, next_across)
    epsilon = 256*np.finfo(float).eps*np.maximum(
        np.linalg.norm(chord, axis=1)*np.maximum(np.linalg.norm(across, axis=1),
                                               np.linalg.norm(next_across, axis=1)), 1e-300)
    bad = (~np.isfinite(first)) | (~np.isfinite(second)) | (first <= epsilon) | (second <= epsilon)
    return dict(bad=bad, first=first, second=second, start=start_s, stop=stop_s,
                start_uv=uv, stop_uv=following)


def refine_centre_stations(surface, graph, node_order, initial_s, periodic=False,
                           max_rounds=12, max_stations=1025):
    """Refine only nonpositive source-UV infinitesimal centre/across intervals.

    This checks centre-frame orientation. It does not certify a finite-width
    strip, global injectivity, a geometric ridge, or ornament quality.
    """
    data = _data(graph, node_order, periodic)
    targets = np.asarray(initial_s, dtype=float).copy()
    if len(targets) < 3 or len(targets) > max_stations or max_rounds < 0:
        raise ValueError('Initial stations/round budget invalid.')
    history = []
    vertex_insertions, midpoint_insertions = 0, 0
    stop_reason = 'ROUND_BUDGET'
    expected_sign = None
    for iteration in range(max_rounds+1):
        curve = _sample(surface, data, targets)
        local = _cross(curve['tangent_uv'], curve['across_uv'])
        if not np.isfinite(local).all() or np.any(abs(local) <= 1e-18):
            raise ValueError('Native BODY source frame has a singular local chart.')
        if expected_sign is None:
            expected_sign = float(np.sign(np.median(local)))
        if expected_sign == 0. or np.any(local*expected_sign <= 0.):
            raise ValueError('Native BODY source chart orientation changes along the path.')
        intervals = _intervals(curve, expected_sign)
        bad = np.flatnonzero(intervals['bad'])
        history.append(dict(round=iteration, stations=len(targets), bad_intervals=len(bad),
            minimum_start_signed_determinant=float(intervals['first'].min()),
            minimum_end_signed_determinant=float(intervals['second'].min())))
        if not len(bad):
            stop_reason = 'POSITIVE_CENTRE_ORIENTATION'
            break
        if iteration == max_rounds:
            break
        proposed = []
        proposed_vertices, proposed_midpoints = 0, 0
        tolerance = 64*np.finfo(float).eps*max(data['total_length'], 1.)
        for interval in bad:
            a, b = intervals['start'][interval], intervals['stop'][interval]
            all_s, all_uv = data['cumulative'], data['vertex_uv']
            if periodic and b > data['total_length']:
                all_s = np.r_[all_s, data['cumulative']+data['total_length']]
                shifted_uv = data['vertex_uv'].copy()
                shifted_uv[:, 1] += data['theta_winding']
                all_uv = np.vstack((all_uv, shifted_uv))
            inside = (all_s > a+tolerance) & (all_s < b-tolerance)
            candidates = all_s[inside]
            if len(candidates):
                vector = intervals['stop_uv'][interval]-intervals['start_uv'][interval]
                deviation = abs(_cross(all_uv[inside]-intervals['start_uv'][interval], vector))
                if deviation.max() > 1e-14*max(np.linalg.norm(vector), 1e-30):
                    # np.argmax chooses first immutable graph-order maximum.
                    chosen = float(candidates[np.argmax(deviation)])
                    proposed_vertices += 1
                else:
                    chosen = .5*(a+b)
                    proposed_midpoints += 1
            else:
                chosen = .5*(a+b)
                proposed_midpoints += 1
            if periodic:
                chosen %= data['total_length']
            proposed.append(chosen)
        merged = np.sort(np.r_[targets, proposed])
        merged = merged[np.r_[True, np.diff(merged) > tolerance]]
        if len(merged) > max_stations:
            stop_reason = 'STATION_BUDGET'
            break
        if len(merged) == len(targets):
            stop_reason = 'NO_DISTINCT_INSERTION'
            break
        vertex_insertions += proposed_vertices
        midpoint_insertions += proposed_midpoints
        targets = merged
    return curve, dict(kind='IMMUTABLE_NATIVE_CURVE_SOURCE_UV_REFINEMENT',
        periodic=bool(periodic), expected_source_orientation_sign=expected_sign,
        passed=not bool(np.any(intervals['bad'])), stop_reason=stop_reason,
        initial_stations=len(initial_s), final_stations=len(curve['s']),
        max_rounds=max_rounds, max_stations=max_stations,
        inserted_native_graph_vertices=vertex_insertions, inserted_midpoints=midpoint_insertions,
        unresolved_interval_indices=np.flatnonzero(intervals['bad']).tolist(),
        unresolved_arc_intervals=np.column_stack((intervals['start'][intervals['bad']],
                                                  intervals['stop'][intervals['bad']])).tolist(),
        history=history,
        differential='Exact fan Gram derivative of source chart, then dtheta=(cx*dcy-cy*dcx)/(cx^2+cy^2). B=N cross immutable native contour T.',
        criterion='Both signed det(nextCentreUV-centreUV, Buv endpoint) must exceed scale-relative floating-point tolerance.',
        refinement='Only failing intervals; immutable graph vertex with maximum UV chord deviation, physical midpoint if no useful interior vertex.',
        limitations='One-sided native tangent at an exact graph vertex can have a genuine kink; unresolved intervals stop explicitly. This is not finite-width or global atlas injectivity, a new ridge measurement, geometry generation, or a world-angle cut.')
