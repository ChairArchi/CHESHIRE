"""Repair the cached strip frame by exact geodesic parallel transport.

Uses the frozen native walker state direction. World-space chord angles are
never treated as intrinsic reversals. Caustic contractions change the usable
source domain, not the ornament height coefficients or the cloth geometry.
"""
from pathlib import Path
import argparse
import json
import numpy as np
from scipy.ndimage import gaussian_filter1d
import run_spine_reconstruction_v3 as base


def source_quads(rows, periodic):
    r, u = np.meshgrid(np.arange(rows if periodic else rows-1), np.arange(8), indexing='ij')
    following = (r+1)%rows
    return np.stack((r*9+u, following*9+u, following*9+u+1, r*9+u+1), axis=-1).reshape(-1, 4)


def determinant(chart, q):
    tri = np.concatenate((q[:, [0, 1, 2]], q[:, [0, 2, 3]]))
    p = chart[tri]
    theta = np.arctan2(p[:, :, 2], p[:, :, 1])
    centre = np.arctan2(p[:, :, 2].mean(axis=1), p[:, :, 1].mean(axis=1))
    theta = centre[:, None]+np.arctan2(np.sin(theta-centre[:, None]), np.cos(theta-centre[:, None]))
    uv = np.stack((p[:, :, 0], theta), axis=-1)
    return base.cross2(uv[:, 1]-uv[:, 0], uv[:, 2]-uv[:, 0])


def repair(surface, strip, info, evidence):
    strip = dict(strip); evidence = dict(evidence); info = dict(info)
    curve, measured = evidence['dense_curve'], evidence['measurement']
    # The executed v3 caller modified its tangent view after recentering.
    # Recover the true original contour tangent from its frozen native graph,
    # without repeating any crest/profile search or changing the source curve.
    graph_report = json.loads(base.GRAPH.read_text(encoding='utf8'))
    with np.load(graph_report['evidence']['path'], allow_pickle=False) as z:
        graph = {key:z[key] for key in z.files}
    nodes = np.flatnonzero(graph['node_component'] == info['component'])
    order = nodes[np.argsort(graph['node_arc_s'][nodes])]
    original_periodic = graph_report['components'][info['component']]['status'] == 'CLOSED_REGULAR_LOOP'
    order, _ = base.longest_domain_run(graph, order, original_periodic, surface.source_mask)
    if info.get('source_coverage_cut'):
        edge_map = {tuple(pair):i for i, pair in enumerate(np.sort(graph['edges'], axis=1))}
        pairs = np.sort(np.column_stack((order[:-1], order[1:])), axis=1)
        node_s = np.r_[0., np.cumsum([graph['edge_length'][edge_map[tuple(pair)]] for pair in pairs])]
        lo, hi = info['source_coverage_cut']['original_arc_interval']
        order = order[(node_s >= lo)&(node_s <= hi)]
    recovered = surface.resample_curve(graph, order, len(strip['s']), periodic=info['periodic'])
    if np.max(np.abs(recovered['s']-strip['s'])) > 1e-10:
        raise ValueError('Frozen native contour recovery changed its actual arc stations.')
    curve = recovered
    evidence['dense_curve'] = recovered
    ms = measured['s']; covered = measured['valid'].all(axis=1)
    adequate = measured['confirmed']&covered&(measured['width'] > .04)
    good = np.flatnonzero(adequate)
    raw_width = np.interp(ms, ms[good], measured['width'][good])
    sigma = max(.5, .5*np.median(1.5*.65*raw_width)/np.median(np.diff(ms)))
    offset = np.zeros(len(ms))
    for row in np.flatnonzero(measured['confirmed']):
        offset[row] = measured['across_distances'][row, measured['geometric_peak_index'][row]]
    offset = gaussian_filter1d(np.interp(ms, ms[good], offset[good]), sigma,
                               mode='wrap' if info['periodic'] else 'nearest')
    offsets = np.interp(strip['s'], ms, offset)
    measured_peak_offsets = offsets.copy()
    offsets[:] = 0.
    rows = len(offsets); normals = np.empty((rows, 3)); across = np.empty_like(normals)
    centres = np.empty_like(normals); tri = np.empty(rows, np.int64); bary = np.empty_like(normals)
    for row in range(rows):
        normal = curve['normal'][row]
        tangent = curve['tangent'][row].copy()
        tangent -= normal*(tangent@normal); tangent /= np.linalg.norm(tangent)
        direction = np.cross(normal, tangent)
        sign = 1. if offsets[row] >= 0. else -1.
        state = (int(curve['triangle_ids'][row]), curve['barycentric'][row].copy(), sign*direction, -1)
        state, travelled, status = surface._walk(state, abs(float(offsets[row])), 100000)
        if status != 'OK':
            raise ValueError('Cached recenter parallel transport failed: '+status)
        point = surface.sample(state[0], state[1])
        normals[row], centres[row] = point['normal'], point['xyz']
        across[row] = sign*state[2]
        across[row] -= normals[row]*(across[row]@normals[row]); across[row] /= np.linalg.norm(across[row])
        tri[row], bary[row] = state[0], state[1]
    identity_error = float(np.linalg.norm(centres-curve['xyz'], axis=1).max())
    if identity_error > 1e-10:
        raise ValueError('Frozen registered phase contour reconstruction differs.')
    q = source_quads(rows, info['periodic'])
    widths = np.asarray(strip['base_width']).copy()
    history = []
    for iteration in range(5):
        xyz = np.empty((rows, 9, 3)); chart = np.empty_like(xyz)
        ids = np.empty((rows, 9), np.int64); weights = np.empty_like(xyz)
        for row in range(rows):
            sample = surface.trace_across(int(tri[row]), bary[row], across[row], base.spine.U_KNOTS*(.5*widths[row]))
            if not sample['valid'].all():
                raise ValueError('Transported source footprint crossed an actual SOURCE-body boundary.')
            xyz[row], chart[row], ids[row], weights[row] = sample['xyz'], sample['chart'], sample['triangle_ids'], sample['barycentric']
        det = determinant(chart.reshape(-1, 3), q)
        bad = (det*np.median(det) <= 0.)|(abs(det) <= 1e-15)
        nf = len(q); face = np.tile(np.arange(nf), 2)
        rows_bad, columns_bad = face[bad]//8, face[bad]%8
        central = int(np.count_nonzero(np.isin(columns_bad, (3, 4))))
        history.append(dict(iteration=iteration, flipped_or_degenerate=int(bad.sum()),
                            central_cell_failures=central, minimum_base_width=float(widths.min()),
                            median_base_width=float(np.median(widths))))
        print('TRANSPORTED_ATLAS_DOMAIN', history[-1], flush=True)
        if not bad.any():
            break
        if central:
            raise ValueError('Transported centre corridor remains underresolved/non-injective; width contraction alone cannot repair it.')
        contraction = np.ones(rows)
        for row, column in zip(rows_bad, columns_bad):
            # First invalid cross-cell bounds the usable corridor. Contract
            # inside its nearer station with a conservative20% margin.
            fraction = .8*min(abs(base.spine.U_KNOTS[column]), abs(base.spine.U_KNOTS[column+1]))
            contraction[row] = min(contraction[row], fraction)
            contraction[(row+1)%rows] = min(contraction[(row+1)%rows], fraction)
        widths *= contraction
    else:
        raise ValueError('Source caustic domain solver did not obtain a positive local Jacobian.')
    if np.median(np.minimum(.35*widths, .6*strip['prominence'])) < .020:
        raise ValueError('Certified usable corridor no longer supports visible node height.')
    strip.update(xyz0=xyz, chart0=chart, normal=normals, across=across,
                 base_width=widths, guides_prepooled=True)
    evidence.update(source_grid_triangle_ids=ids, source_grid_barycentric=weights,
                    transported_across=across, transported_normal=normals,
                    requested_geometric_peak_offset=offsets, caustic_usable_base_width=widths)
    evidence['measured_peak_offset_not_forced'] = measured_peak_offsets
    info['coherence_repair'] = dict(method='Exact hinge-parallel-transported across direction from the frozen walker state; T=BcrossN. No coarse world-chord reversal assumption.',
        centre_reconstruction_error=identity_error, domain_iterations=history,
        parent_guide='Original registered MIDDLE phase contour retained. Cached actual positive crest/shoulder measurements supply budgets, but independent per-row geometric peak offsets are not forced.',
        source_geometry_changed=False, geometry_height_coefficients_changed=False)
    return strip, info, evidence


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parent', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError('Frozen cache repair output already exists.')
    state = base.load_tree(args.parent, {})
    report = json.loads(base.GRAPH.read_text(encoding='utf8'))
    with np.load(report['source_control'], allow_pickle=False) as z:
        xyz, q, chart = z['xyz'], z['faces'], z['chart']
    with np.load(base.STATES/'G06_MIDDLE/evidence.npz', allow_pickle=False) as z:
        phase = z['directional_phase']
    with np.load(base.STATES/'G03_SIDEWALL/control_quad.npz', allow_pickle=False) as z:
        q3, c3 = z['faces'], z['chart']
    with np.load(base.STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z:
        owners = z['face_event_ids']
    cap = np.all(c3[q3, 0] == 0., axis=1)|np.all(c3[q3, 0] == 1., axis=1)
    surface = base.NativeSurface(xyz, q, phase, np.repeat((owners == 0)&~cap, 64), chart)
    args.output.mkdir(parents=True)
    try:
        strip, info, evidence = repair(surface, state['strip'], state['info'], state['evidence'])
        delta, qf, cf, meta, formation = base.spine.form(strip, periodic=info['periodic'],
            cell_count=info['node_count'], phase_origin=info['phase_origin'], total_length=info['total_length'])
        raw_det = determinant(strip['chart0'].reshape(-1, 3), source_quads(len(strip['s']), info['periodic']))
        refined_det = determinant(cf, qf)
        saved = base.receipt_helper.save_tree(args.output, 'REPAIRED_PARENT', dict(strip=strip, info=info,
            evidence=evidence, formation=formation, raw_determinant=raw_det, refined_determinant=refined_det))
        atlas = base.SourceAtlas(cf, qf, delta, formation['logical_refined'])
        result = dict(passed=True, parent=info, atlas=atlas.metadata, formation=meta, evidence=saved)
    except ValueError as error:
        result = dict(passed=False, reason=str(error))
    result['helper_sha256'] = base.sha(__file__)
    base.write(args.output/'REPAIR.json', result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
