"""ONE receipt-bound spine-chain candidate on the unchanged accepted G7 cloth.

Foundation checks run before full export. No geometry-nearest inverse, no
unconstrained triangulation, no parameter sweep, no independent ornament mesh.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import time

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from native_strip_surface import NativeSurface
import native_strip_surface
import recursive_spine_operator as spine


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = REPO/'experiments/fold_junction_development_20261015'
GRAPH = REPO/'docs/hansmeyer_reconstruction_20261015/phase_curve_probe01/PHASE_CURVE_GRAPH.json'
ACCEPTED = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
STATES = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


helper = module('spine_native_export_helpers', OLD/'run_final.py')
receipt_helper = module('spine_receipt_helpers', OLD/'run_recursive.py')
sha, ah, write = helper.digest, helper.ah, helper.write


class SourceAtlas:
    """Exact membership inverse of the generating strip's existing triangles."""
    def __init__(self, chart, q, delta, logical, *, verify_global=True):
        triangles = np.concatenate((q[:, [0, 1, 2]], q[:, [0, 2, 3]]))
        values = chart[triangles]
        theta = np.arctan2(values[:, :, 2], values[:, :, 1])
        centre_angle = np.arctan2(values[:, :, 2].mean(axis=1), values[:, :, 1].mean(axis=1))
        theta = centre_angle[:, None]+np.arctan2(np.sin(theta-centre_angle[:, None]), np.cos(theta-centre_angle[:, None]))
        uv = np.stack((values[:, :, 0], theta), axis=-1)
        det = np.cross(uv[:, 1]-uv[:, 0], uv[:, 2]-uv[:, 0])
        if np.any(np.abs(det) <= 1e-15) or np.any(det*np.median(det) <= 0.):
            raise ValueError('Source strip chart has a degenerate/flipped local Jacobian.')
        copies = [(uv, np.arange(len(uv)))]
        for sign in (-1, 1):
            take = uv[:, :, 1].min(axis=1) < -np.pi if sign == 1 else uv[:, :, 1].max(axis=1) > np.pi
            shifted = uv[take].copy(); shifted[:, :, 1] += sign*2*np.pi
            copies.append((shifted, np.flatnonzero(take)))
        self.uv = np.concatenate([item[0] for item in copies])
        self.original = np.concatenate([item[1] for item in copies])
        self.triangles = triangles
        self.delta, self.logical = delta, logical
        self.centre = self.uv.mean(axis=1)
        self.radius = float(np.linalg.norm(self.uv-self.centre[:, None], axis=2).max())
        self.tree = cKDTree(self.centre)
        self.low, self.high = self.uv.min(axis=1), self.uv.max(axis=1)
        # A local positive Jacobian alone is not global injectivity. Check all
        # potentially overlapping triangle pairs by exact 2D separating axes.
        pairs = (self.tree.query_pairs(2*self.radius+1e-12, output_type='ndarray')
                 if verify_global else np.empty((0, 2), np.int64))
        overlaps = 0
        for start in range(0, len(pairs), 65536):
            pair = pairs[start:start+65536]
            a, b = pair[:, 0], pair[:, 1]
            possible = np.all(np.minimum(self.high[a], self.high[b])-np.maximum(self.low[a], self.low[b]) > 1e-12, axis=1)
            pair = pair[possible]
            if not len(pair):
                continue
            a, b = self.uv[pair[:, 0]], self.uv[pair[:, 1]]
            axes = np.concatenate((np.roll(a, -1, axis=1)-a, np.roll(b, -1, axis=1)-b), axis=1)
            axes = np.stack((-axes[:, :, 1], axes[:, :, 0]), axis=-1)
            axes /= np.linalg.norm(axes, axis=2)[:, :, None]
            pa = np.einsum('nki,nji->nkj', axes, a); pb = np.einsum('nki,nji->nkj', axes, b)
            gap = np.minimum(pa.max(axis=2), pb.max(axis=2))-np.maximum(pa.min(axis=2), pb.min(axis=2))
            overlaps += int(np.count_nonzero(np.all(gap > 1e-11, axis=1)))
        if overlaps:
            raise ValueError(f'Source strip chart has {overlaps} nonadjacent positive-area triangle overlaps.')
        self.metadata = dict(triangles=len(triangles), periodic_seam_copies=len(self.uv)-len(triangles),
            local_jacobian_minimum=float(np.abs(det).min()), nonadjacent_triangle_overlaps=overlaps,
            inverse='All possible containing triangles inside proven centroid radius; exact bbox and barycentric membership. No Delaunay or nearest-world projection.',
            completeness_radius=self.radius)

    def evaluate(self, chart):
        uv = np.column_stack((chart[:, 0], np.arctan2(chart[:, 2], chart[:, 1])))
        valid_box = np.all((uv >= self.low.min(axis=0)-1e-12)&(uv <= self.high.max(axis=0)+1e-12), axis=1)
        output = np.zeros((len(chart), 3)); logical = np.zeros_like(output); valid = np.zeros(len(chart), bool)
        query_ids = np.flatnonzero(valid_box)
        if not len(query_ids):
            return output, logical, valid
        lists = self.tree.query_ball_point(uv[query_ids], self.radius+1e-12)
        counts = np.fromiter(map(len, lists), dtype=np.int64, count=len(lists))
        if not counts.sum():
            return output, logical, valid
        qi = np.repeat(query_ids, counts); ti = np.concatenate(lists).astype(np.int64)
        box = np.all((uv[qi] >= self.low[ti]-1e-12)&(uv[qi] <= self.high[ti]+1e-12), axis=1)
        qi, ti = qi[box], ti[box]
        tri = self.uv[ti]; e1, e2 = tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
        v = uv[qi]-tri[:, 0]; det = np.cross(e1, e2)
        b1, b2 = np.cross(v, e2)/det, np.cross(e1, v)/det
        bary = np.column_stack((1-b1-b2, b1, b2))
        inside = np.all(bary >= -1e-9, axis=1)&np.all(bary <= 1+1e-9, axis=1)
        qi, ti, bary = qi[inside], ti[inside], bary[inside]
        if len(qi):
            # Shared-edge duplicate hits interpolate the same vertex data.
            _, first = np.unique(qi, return_index=True)
            qi, ti, bary = qi[first], ti[first], bary[first]
            ids = self.triangles[self.original[ti]]
            output[qi] = np.einsum('nj,nji->ni', bary, self.delta[ids])
            logical[qi] = np.einsum('nj,nji->ni', bary, self.logical[ids])
            valid[qi] = True
        return output, logical, valid


def canonical_candidates(report, graph, height):
    labels = graph['node_component']; seen = set(); candidates = []
    for component in report['components']:
        ci = component['component']
        if ci in seen:
            continue
        nodes = np.flatnonzero(labels == ci)
        orbit = {ci}
        for key in ('node_mirror_x', 'node_mirror_y'):
            mirror = graph[key][nodes]
            orbit.update(labels[mirror[mirror >= 0]].tolist())
        seen.update(orbit)
        if (component['level_index'] in (report['extraction']['level_indices'][0], report['extraction']['level_indices'][-1])
                or component['physical_arc_length'] < .5*height):
            continue
        canonical = min(orbit)
        c = report['components'][canonical]
        cn = np.flatnonzero(labels == canonical)
        t = graph['node_material_t'][cn]
        vertical_span = float(np.quantile(t, .95)-np.quantile(t, .05))
        # Height coverage prevents a very folded local loop winning merely by
        # accumulating arc in one small architectural band.
        score = c['physical_arc_length']*float(np.median(graph['node_middle_envelope'][cn]))*vertical_span**2
        candidates.append((score, canonical, sorted(orbit)))
    return sorted(candidates, reverse=True)


def mirror_origin(graph, component, length, periodic):
    nodes = np.flatnonzero(graph['node_component'] == component)
    order = nodes[np.argsort(graph['node_arc_s'][nodes])]
    s = graph['node_arc_s']; labels = graph['node_component']
    for key in ('node_mirror_x', 'node_mirror_y'):
        mapped = graph[key][order]
        if not np.all(labels[mapped] == component):
            continue
        step = float(s[mapped[1]]-s[mapped[0]])
        if periodic:
            step = (step+length/2)%length-length/2
        sign = 1 if step > 0 else -1
        if sign < 0:
            c = s[mapped]+s[order]
            if periodic:
                angle = np.angle(np.exp(2j*np.pi*c/length).mean())%(2*np.pi)
                return float(angle*length/(4*np.pi))
            return .5*float(np.median(c))
    return 0.


def prepare_parent(surface, graph, component, orbit, height):
    nodes = np.flatnonzero(graph['node_component'] == component['component'])
    order = nodes[np.argsort(graph['node_arc_s'][nodes])]
    periodic = component['status'] == 'CLOSED_REGULAR_LOOP'
    curve = surface.resample_curve(graph, order, 129, periodic=periodic)
    measured = surface.measure_strip(curve['triangle_ids'], curve['barycentric'], samples=33,
        max_half_width=.03*height, curve_s=curve['s'], periodic=periodic, tangents=curve['tangent'])
    w, d = measured['width'], measured['prominence']
    adequate = measured['confirmed']&measured['valid'].all(axis=1)&(d >= .20*w)&(w > .04)
    # A few missing numerical crest confirmations can be filled only in metric
    # estimates; native surface coverage is never bridged or invented.
    if adequate.mean() < .75 or not measured['valid'].all():
        raise ValueError(f'Component{component["component"]}: insufficient covered salient ridge ({adequate.sum()}/129).')
    valid = np.flatnonzero(adequate)
    mode = 'wrap' if periodic else 'nearest'
    raw_w = np.interp(curve['s'], curve['s'][valid], w[valid])
    raw_d = np.interp(curve['s'], curve['s'][valid], d[valid])
    sigma = max(.5, .5*np.median(1.5*.65*raw_w)/np.median(np.diff(curve['s'])))
    width = gaussian_filter1d(raw_w, sigma, mode=mode)
    depth = gaussian_filter1d(raw_d, sigma, mode=mode)
    predicted_h = np.minimum(.35*.65*width, .6*depth)
    if np.median(predicted_h) < .020:
        raise ValueError('Confirmed parent cannot support visible median0.020 node relief.')
    length = curve['total_length']
    integral = np.trapezoid(1./(1.5*.65*width), curve['s'])
    if periodic:
        integral += (length-curve['s'][-1])/(1.5*.65*(width[-1]+width[0])/2)
    count = max(4, 2*round(integral/2)) if periodic else max(4, round(integral))
    dense = surface.resample_curve(graph, order, 4*count if periodic else 4*count+1, periodic=periodic)
    s = dense['s']; dw = np.interp(s, curve['s'], width); dd = np.interp(s, curve['s'], depth)
    offset = np.zeros(len(curve['s']))
    for row in np.flatnonzero(measured['confirmed']):
        offset[row] = measured['across_distances'][row, measured['geometric_peak_index'][row]]
    offset = np.interp(curve['s'], curve['s'][valid], offset[valid])
    offset = gaussian_filter1d(offset, sigma, mode=mode)
    offset_dense = np.interp(s, curve['s'], offset)
    xyz_grid = np.empty((len(s), 9, 3)); chart_grid = np.empty_like(xyz_grid)
    tri_grid = np.empty((len(s), 9), np.int64); bary_grid = np.empty_like(xyz_grid)
    normals = np.empty((len(s), 3)); across = np.empty_like(normals); centres = np.empty_like(normals)
    tangents = np.empty_like(normals); ridge_tri = np.empty(len(s), np.int64); ridge_bary = np.empty_like(normals)
    for row in range(len(s)):
        original = surface.sample(dense['triangle_ids'][row], dense['barycentric'][row])
        tangent = dense['tangent'][row]; tangent -= original['normal']*(tangent@original['normal'])
        tangent /= np.linalg.norm(tangent)
        direction = np.cross(original['normal'], tangent)
        shifted = surface.trace_across(int(dense['triangle_ids'][row]), dense['barycentric'][row],
                                      direction, np.asarray([offset_dense[row]]))
        if not shifted['valid'].all():
            raise ValueError('Actual ridge recentering crossed a SOURCE boundary.')
        tid, bary = int(shifted['triangle_ids'][0]), shifted['barycentric'][0]
        centre = surface.sample(tid, bary)
        normals[row], centres[row] = centre['normal'], centre['xyz']
        tangent -= normals[row]*(tangent@normals[row]); tangent /= np.linalg.norm(tangent)
        tangents[row], ridge_tri[row], ridge_bary[row] = tangent, tid, bary
        across[row] = np.cross(normals[row], tangent)
    frame_sigma = .5*np.median(1.5*.65*dw)/np.median(np.diff(s))
    pooled_tangent = gaussian_filter1d(tangents, frame_sigma, axis=0, mode=mode)
    pooled_tangent /= np.linalg.norm(pooled_tangent, axis=1)[:, None]
    curvature = np.abs(np.einsum('ij,ij->i', np.gradient(pooled_tangent, s, axis=0), across))
    usable_base = np.minimum(.65*dw, np.divide(.90, curvature, out=np.full_like(curvature, np.inf), where=curvature > 1e-12))
    if np.median(np.minimum(.35*usable_base, .6*dd)) < .020:
        raise ValueError('Curvature-safe actual base cannot sustain visible node relief.')
    for row in range(len(s)):
        grid = surface.trace_across(int(ridge_tri[row]), ridge_bary[row], across[row], spine.U_KNOTS*(.5*usable_base[row]))
        if not grid['valid'].all():
            raise ValueError('Confirmed generating footprint crossed SOURCE coverage; no forced point.')
        xyz_grid[row], chart_grid[row], tri_grid[row], bary_grid[row] = grid['xyz'], grid['chart'], grid['triangle_ids'], grid['barycentric']
    origin = mirror_origin(graph, component['component'], length, periodic)
    strip = dict(xyz0=xyz_grid, chart0=chart_grid, normal=normals, across=across,
                 width=dw, prominence=dd, base_width=usable_base, guides_prepooled=True, s=s)
    info = dict(component=component['component'], mirror_component_orbit=orbit,
        phase_level=component['level_index'], periodic=periodic, total_length=length,
        preflight_samples=129, adequate_rows=int(adequate.sum()),
        adequate_fraction=float(adequate.mean()), physical_width_quantiles=np.quantile(dw, [0., .1, .5, .9, 1.]).tolist(),
        prominence_quantiles=np.quantile(dd, [0., .1, .5, .9, 1.]).tolist(),
        usable_base_width_quantiles=np.quantile(usable_base, [0., .1, .5, .9, 1.]).tolist(),
        usable_base_bound='Full base=min(.65 measured forming-scale parent width,.90/pooled path geodesic curvature); half-base is at most .45 local curvature radius.',
        predicted_node_height_median=float(np.median(predicted_h)), node_count=count,
        recenter='Actual same-sheet geodesic offset to measured peak, pooled on half node-pitch; source XYZ not globally filtered.',
        phase_origin=origin, phase_rule='Even integer node count on closed curves and canonical mirror reversal origin; final G7 source-ID reflection exact.')
    evidence = dict(measurement=measured, dense_curve=dense, source_grid_triangle_ids=tri_grid,
                    source_grid_barycentric=bary_grid, actual_recentered_xyz=centres,
                    actual_parent_width=dw, actual_parent_depth=dd, usable_base_width=usable_base,
                    requested_base_width=.65*dw, actual_ridge_triangle_ids=ridge_tri,
                    actual_ridge_barycentric=ridge_bary)
    return strip, info, evidence


def load_tree(description, sources):
    path = Path(description)
    record = json.loads(path.read_text(encoding='utf8'))
    payload = Path(record['array_file'])
    if sha(payload) != record['array_file_sha256']:
        raise ValueError('Prepared foundation array file differs.')
    sources[str(path)], sources[str(payload)] = sha(path), sha(payload)
    with np.load(payload, allow_pickle=False) as z:
        arrays = {key:z[key] for key in z.files}
    def decode(item):
        if isinstance(item, dict) and 'npz_key' in item:
            value = arrays[item['npz_key']]
            if ah(value) != item['sha256']:
                raise ValueError('Prepared foundation array differs.')
            return value
        if isinstance(item, dict):
            return {key:decode(value) for key, value in item.items()}
        if isinstance(item, list):
            return [decode(value) for value in item]
        return item
    return decode(record['tree'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--preflight-only', action='store_true')
    p.add_argument('--foundation', type=Path, help='Reuse the exact saved passing foundation; no repeat surface measurements.')
    args = p.parse_args(); root = args.root.resolve()
    if root.exists():
        raise FileExistsError('Select a fresh immutable candidate root.')
    started = time.perf_counter(); sources = {}
    graph_report = json.loads(GRAPH.read_text(encoding='utf8'))
    graph_path = Path(graph_report['evidence']['path'])
    if sha(graph_path) != graph_report['evidence']['sha256']:
        raise ValueError('Frozen graph evidence differs.')
    sources[str(GRAPH)], sources[str(graph_path)] = sha(GRAPH), sha(graph_path)
    with np.load(graph_path, allow_pickle=False) as z:
        graph = {key:z[key] for key in z.files}
    for path, value in graph_report['sources'].items():
        if sha(path) != value:
            raise ValueError('Graph immutable source differs: '+path)
        sources[path] = value
    with np.load(graph_report['source_control'], allow_pickle=False) as z:
        x6, q6, chart6 = z['xyz'], z['faces'], z['chart']
    with np.load(STATES/'G06_MIDDLE/evidence.npz', allow_pickle=False) as z:
        phase = z['directional_phase']
    with np.load(STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z:
        body6 = np.repeat(z['face_event_ids'] == 0, 64)
    surface = None if args.foundation else NativeSurface(x6, q6, phase, body6, chart6)
    height = float(np.ptp(x6[:, 2]))
    root.mkdir(parents=True)
    paths = [Path(__file__).resolve(), HERE/'recursive_spine_operator.py', HERE/'native_strip_surface.py',
             HERE/'trace_middle_phase_curves.py', OLD/'run_final.py', OLD/'run_recursive.py',
             REPO/'src/cheshire/reference_subdivision.py']
    snapshots = {}
    for path in paths:
        target = root/'source_snapshot_run'/path.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
        snapshots[path.relative_to(REPO).as_posix()] = dict(source=str(path), snapshot=str(target), sha256=sha(path))
    accepted_receipt = ACCEPTED/'RECEIPT.json'
    if sha(accepted_receipt) != helper.BASE_RECEIPT_SHA:
        raise ValueError('Accepted cloth receipt differs.')
    receipt = json.loads(accepted_receipt.read_text(encoding='utf8'))
    base = receipt['variants']['NESTED']; source = Path(base['control_quad'])
    if sha(source) != base['control_quad_sha256']:
        raise ValueError('Accepted cloth controls differ.')
    sources[str(accepted_receipt)], sources[str(source)] = sha(accepted_receipt), sha(source)
    prepared, preflight, rejected = [], [], []
    if args.foundation:
        foundation_root = args.foundation.resolve()
        foundation_path = foundation_root/'PREFLIGHT.json'
        foundation = json.loads(foundation_path.read_text(encoding='utf8'))
        if not foundation['passed'] or len(foundation['selected']) != 2:
            raise ValueError('Two passing prepared parent orbits required.')
        sources[str(foundation_path)] = sha(foundation_path)
        for path in paths:
            old_snapshot = foundation_root/'source_snapshot_run'/path.relative_to(REPO)
            if sha(old_snapshot) != sha(path):
                raise ValueError('Prepared/executed source changed: '+str(path))
        preflight, rejected = foundation['selected'], foundation['rejected']
        for info in preflight:
            state = load_tree(info['evidence']['description'], sources)['formation']
            atlas = SourceAtlas(state['source_chart_refined'], state['quads_refined'],
                                state['delta_refined'], state['logical_refined'], verify_global=False)
            prepared.append((atlas, info))
    used_levels = set()
    for score, ci, orbit in ([] if args.foundation else canonical_candidates(graph_report, graph, height)):
        component = graph_report['components'][ci]
        if component['level_index'] in used_levels:
            continue
        try:
            print('CONFIRM actual parent component', ci, flush=True)
            strip, info, evidence = prepare_parent(surface, graph, component, orbit, height)
            delta, q, chart, meta, formation = spine.form(strip, periodic=info['periodic'],
                cell_count=info['node_count'], phase_origin=info['phase_origin'], total_length=info['total_length'])
            atlas = SourceAtlas(chart, q, delta, formation['logical_refined'])
        except ValueError as error:
            rejected.append(dict(component=ci, reason=str(error)))
            print('FOUNDATION_REJECT', ci, str(error), flush=True)
            continue
        info.update(selection_score=score, atlas=atlas.metadata, formation=meta)
        record = receipt_helper.save_tree(root, f'PARENT_{len(prepared):02}', dict(foundation=evidence, formation=formation))
        info['evidence'] = record
        prepared.append((atlas, info)); preflight.append(info); used_levels.add(component['level_index'])
        if len(prepared) == 2:
            break
    write(root/'PREFLIGHT.json', dict(passed=len(prepared) == 2, selected=preflight, rejected=rejected,
        selection='Two distinct internal MIDDLE phase-family canonical mirror orbits, ranked intrinsically by length*median saved amplitude envelope; meaningful actual same-sheet crest and injective generating source chart required. No camera selection or amplitude variants.'))
    if len(prepared) != 2 or args.preflight_only:
        print('PREFLIGHT_ONLY' if len(prepared) == 2 else 'FOUNDATION_STOP', flush=True)
        return
    del surface, x6, q6, chart6, body6, phase, graph
    gc.collect()
    print('TRANSFER shared connected spine differential to exact accepted G7 cloth', flush=True)
    with np.load(source, allow_pickle=False) as z:
        control = {key:z[key] for key in z.files}
    carrier, q7, chart7 = control['xyz'], control['faces'], control['chart']
    pair_path = STATES/'G07_SURFACE/evidence.npz'
    generation = json.loads((pair_path.parent/'generation.json').read_text(encoding='utf8'))
    if sha(pair_path) != generation['evidence_file_sha256']:
        raise ValueError('Actual G7 mirror map differs.')
    sources[str(pair_path)] = sha(pair_path)
    with np.load(pair_path, allow_pickle=False) as z:
        px, py = z['mirror_x_vertex_pairs'], z['mirror_y_vertex_pairs']
    with np.load(STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z:
        body7 = np.repeat(z['face_event_ids'] == 0, 256)
    degree = np.bincount(q7.ravel(), minlength=len(carrier))
    source_degree = np.bincount(q7[body7].ravel(), minlength=len(carrier))
    eligible = source_degree == degree
    ids = np.arange(len(carrier)); representative = np.minimum.reduce((ids, px, py, px[py]))
    free = np.flatnonzero(eligible&(ids == representative))
    raw = np.zeros_like(carrier); confidence = np.zeros(len(carrier))
    for atlas, info in prepared:
        for sx, sy in ((1., 1.), (-1., 1.), (1., -1.), (-1., -1.)):
            for start in range(0, len(free), 65536):
                take = free[start:start+65536]
                query = chart7[take].copy(); query[:, 1] *= sx; query[:, 2] *= sy
                d, logical, valid = atlas.evaluate(query)
                taper = spine.quintic((1.-np.abs(logical[:, 2]))/.22)*valid
                if not info['periodic']:
                    t = logical[:, 0]*info['total_length']
                    pitch = np.asarray(info['formation']['node_pitch_quantiles'])[[0, -1]]
                    taper *= spine.quintic(t/(1.5*pitch[0]))*spine.quintic((info['total_length']-t)/(1.5*pitch[1]))
                active = taper > confidence[take]
                d[:, 0] *= sx; d[:, 1] *= sy
                raw[take[active]] = d[active]*taper[active, None]
                confidence[take[active]] = taper[active]
    delta = helper.reflect_delta(raw, px, py)
    delta[~eligible] = 0.
    norms = np.linalg.norm(delta, axis=1); moved = np.flatnonzero(norms > 1e-12)
    if not len(moved) or float(np.quantile(norms[moved], .9)) < .015:
        raise ValueError('Strong visible-differential prerequisite failed; no full export.')
    output = carrier+delta
    outside = confidence[representative] == 0.
    if np.any(output[outside] != carrier[outside]):
        raise ValueError('Exact untouched cloth prerequisite failed.')
    symmetry = 0.
    for axis, pair in enumerate((px, py)):
        for start in range(0, len(output), 65536):
            sl = slice(start, min(start+65536, len(output)))
            reflected = output[pair[sl]].copy(); reflected[:, axis] *= -1
            symmetry = max(symmetry, float(np.abs(output[sl]-reflected).max()))
    if not np.isfinite(output).all() or symmetry > 2e-12:
        raise ValueError('Actual output finite/reflection prerequisite failed.')
    validation = dict(generation=7, original_topology_unchanged=True, added_original_CC_passes=0,
        local_scaffold_CC_passes=2, moved_controls=len(moved),
        displacement_quantiles=np.quantile(norms[moved], [0., .1, .5, .9, .99, 1.]).tolist(),
        output_XY_symmetry_error=symmetry, exact_untouched_controls=int(outside.sum()),
        maximum_bounds_change=(np.ptp(output, axis=0)-np.ptp(carrier, axis=0)).tolist(),
        macro_preservation='Exact carrier outside compact strips; inside strips structural differential can change local silhouette. No global fairing or flat carrier.',
        self_intersection_checked=False, visual_success='Pending matched full-native close/body/front renders.')
    np.savez_compressed(root/'SPARSE_DELTA.npz', ids=moved, delta=delta[moved], carrier_xyz_sha256=np.array(ah(carrier)))
    del raw, delta, norms, body7, degree, source_degree, representative, ids, confidence
    gc.collect()
    print('EXPORT exact-topology full native SPINE', flush=True)
    record = helper.save(root, 'SPINE', output, q7, validation)
    control['xyz'] = output
    cp = root/'SPINE/control_quad.npz'; np.savez_compressed(cp, **control)
    record.update(control_quad=str(cp), control_quad_sha256=sha(cp))
    variants = dict(SPINE=record, REFERENCE_NESTED=base)
    for entry in snapshots.values():
        if sha(entry['source']) != entry['sha256'] or sha(entry['snapshot']) != entry['sha256']:
            raise ValueError('Executed source changed during production.')
    for path, checksum in sources.items():
        if sha(path) != checksum:
            raise ValueError('Immutable production input changed.')
    write(root/'RECEIPT.json', dict(kind='ACTUAL_MIDDLE_WRINKLE_CONNECTED_SPINE_CHAIN', date='2026-10-15',
        comparison_source_native_path=str(ACCEPTED/'NESTED/geometry.npz'),
        comparison_source_native_geometry_sha256=helper.BASE_NATIVE_SHA,
        source_snapshots=snapshots, sources=sources, variants=variants, foundation=preflight,
        validation=validation, elapsed_seconds=time.perf_counter()-started,
        scope='Two selected intrinsic MIDDLE ridge-path mirror orbits; actual same-sheet shoulder confirmation and source-atlas injectivity precede shared-base BN node-cage and two causal local CC generations. Differential transferred onto unchanged-topology accepted G7 cloth. No world nearest projection, separate ornament object, full-surface coat, amplitude sweep or claim of exact Hansmeyer reproduction.'))
    print('SPINE_RECONSTRUCTION_COMPLETE', time.perf_counter()-started, flush=True)


if __name__ == '__main__':
    main()
