"""Read-only concentration of relative native-fan normal turnover.

Uses saved control IDs/chart and already-certified parent atlas. No model,
measurement, raycast, collision certificate, image or geometry output.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import time

import numpy as np


REPO = Path(__file__).resolve().parents[2]
HERE = REPO/'experiments/hansmeyer_reconstruction_20261015'
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('readonly_spine_v4', HERE/'run_spine_reconstruction_v4.py')
v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)
CHUNK = 65536


def qstats(x):
    x = np.asarray(x)
    return dict(count=len(x), probabilities=[0, .1, .5, .9, .99, 1],
                values=np.quantile(x, [0, .1, .5, .9, .99, 1]).tolist()) if len(x) else dict(count=0)


def arrays(z, tree, names):
    return {name:z[tree[name]['npz_key']] for name in names}


def project(points):
    position = np.asarray([-18., 28., 12.])
    target = np.asarray([-.6, .72, 6.6])
    forward = target-position; forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    relative = points-target
    return np.column_stack((.5+relative@right/1.25, .5-relative@up/1.25))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('New-only audit output.')
    started = time.perf_counter()
    receipt = json.loads((args.root/'RECEIPT.json').read_text(encoding='utf8'))
    variants = receipt['variants']
    with np.load(variants['REFERENCE_NESTED']['control_quad'], allow_pickle=False) as z:
        x0, q, chart = z['xyz'], z['faces'], z['chart']
    with np.load(variants['SPINE']['control_quad'], allow_pickle=False) as z:
        x1 = z['xyz']
    changed = np.any(x0 != x1, axis=1)
    points, uvcharts, ids, corners, angles, areas0, areas1 = [], [], [], [], [], [], []
    changed_base_area = 0.
    min_changed0, min_changed1 = np.inf, np.inf
    for start in range(0, len(q), CHUNK):
        block = q[start:start+CHUNK]
        take = np.flatnonzero(changed[block].any(axis=1))
        if not len(take): continue
        gids = start+take; block = block[take]
        p0, p1, c = x0[block], x1[block], chart[block]
        n0 = np.cross(np.roll(p0, -1, axis=1)-p0, p0.mean(axis=1)[:, None]-p0)
        n1 = np.cross(np.roll(p1, -1, axis=1)-p1, p1.mean(axis=1)[:, None]-p1)
        a0, a1 = .5*np.linalg.norm(n0, axis=2), .5*np.linalg.norm(n1, axis=2)
        dot = np.einsum('nki,nki->nk', n0, n1)
        changed_base_area += float(a0.sum())
        min_changed0 = min(min_changed0, float(a0.min()))
        min_changed1 = min(min_changed1, float(a1.min()))
        ri, ci = np.nonzero(dot <= 0.)
        if not len(ri): continue
        ids.append(gids[ri]); corners.append(ci)
        points.append((p1[ri, ci]+p1[ri, (ci+1)%4]+p1.mean(axis=1)[ri])/3)
        uvcharts.append((c[ri, ci]+c[ri, (ci+1)%4]+c.mean(axis=1)[ri])/3)
        angles.append(np.degrees(np.arccos(np.clip(dot[ri, ci]/(4*a0[ri, ci]*a1[ri, ci]), -1, 1))))
        areas0.append(a0[ri, ci]); areas1.append(a1[ri, ci])
    points, uvcharts, ids, corners, angles, areas0, areas1 = (
        np.concatenate(x) for x in (points, uvcharts, ids, corners, angles, areas0, areas1))
    del x0, x1, chart, q, changed
    print('AUDIT mapped relative-turnover triangles', len(ids), flush=True)
    parent_owner = np.full(len(ids), -1, np.int8)
    confidence = np.zeros(len(ids))
    logical_out = np.zeros((len(ids), 3))
    parent_states = []
    for pi, info in enumerate(receipt['foundation']):
        saved = json.loads(Path(info['evidence']['description']).read_text(encoding='utf8'))
        with np.load(saved['array_file'], allow_pickle=False) as z:
            formed = arrays(z, saved['tree']['formation'], ('source_chart_transfer', 'quads_refined',
                'delta_refined', 'logical_refined', 'logical_s', 'logical_chi', 'usable_base_width'))
        atlas = v4.BucketAtlas(formed['source_chart_transfer'], formed['quads_refined'],
            formed['delta_refined'], formed['logical_refined'], verify_global=False)
        parent_states.append(formed)
        for sx, sy in ((1., 1.), (-1., 1.), (1., -1.), (-1., -1.)):
            query = uvcharts.copy(); query[:, 1] *= sx; query[:, 2] *= sy
            delta, logical, valid = atlas.evaluate(query)
            taper = v4.spine.quintic((1-np.abs(logical[:, 2]))/.22)*valid
            if not info['periodic']:
                s = logical[:, 0]*info['total_length']
                pitch = np.asarray(info['formation']['node_pitch_quantiles'])[[0, -1]]
                taper *= v4.spine.quintic(s/(1.5*pitch[0]))*v4.spine.quintic((info['total_length']-s)/(1.5*pitch[1]))
            active = taper > confidence
            parent_owner[active] = pi; confidence[active] = taper[active]
            logical_out[active] = logical[active]
    projected = project(points)
    inside = np.all((projected>=0)&(projected<=1), axis=1)
    groups = []
    for pi, info in enumerate(receipt['foundation']):
        take = parent_owner == pi
        state = parent_states[pi]
        s = logical_out[take, 0]*info['total_length']
        width = np.interp(s, state['logical_s'], state['usable_base_width'])
        chi = np.interp(s, state['logical_s'], state['logical_chi'])
        node = (.5+.5*np.cos(2*np.pi*chi))**2
        u = np.abs(logical_out[take, 2])
        median_base = float(np.median(state['usable_base_width']))
        groups.append(dict(parent_index=pi, component=info['component'], triangle_count=int(take.sum()),
            source_arc_fraction=qstats(logical_out[take, 0]), absolute_across_u=qstats(u),
            arc_decile_counts=np.histogram(logical_out[take, 0], np.linspace(0, 1, 11))[0].tolist(),
            across_counts=dict(stem_abs_u_lt_022=int((u<.22).sum()), crown_022_to_078=int(((u>=.22)&(u<.78)).sum()), outer_taper_ge_078=int((u>=.78).sum())),
            node_envelope_counts=dict(crown_ge_05=int((node>=.5).sum()), neck_le_01=int((node<=.1).sum()), transition=int(((node>.1)&(node<.5)).sum())),
            local_usable_base=qstats(width), parent_median_usable_base=median_base,
            local_base_below_quarter_parent_median=int((width<.25*median_base).sum()),
            baseline_area_sum=float(areas0[take].sum()), candidate_area_sum=float(areas1[take].sum()),
            projected_inside_existing_close=int((inside&take).sum())))
    order = np.argsort(angles)[-20:][::-1]
    top = [dict(G7_quad_id=int(ids[i]), native_fan_corner=int(corners[i]),
        native_triangle_id=int(4*ids[i]+corners[i]), angle_degrees=float(angles[i]),
        baseline_area=float(areas0[i]), candidate_area=float(areas1[i]),
        candidate_centroid=points[i].tolist(), frozen_close_normalized_xy=projected[i].tolist(),
        projected_inside_existing_close=bool(inside[i]), parent_index=int(parent_owner[i]),
        parent_arc_fraction=float(logical_out[i, 0]), parent_across_u=float(logical_out[i, 2])) for i in order]
    report = dict(kind='SPINE_RELATIVE_NORMAL_TURNOVER_SOURCE_AND_CAMERA_CONCENTRATION',
        candidate_root=str(args.root), total_turnover_triangles=len(ids),
        mapped_parent_centroids=int((parent_owner>=0).sum()), unmapped_centroids=int((parent_owner<0).sum()),
        changed_baseline_area_sum=changed_base_area,
        turnover_baseline_area=qstats(areas0), turnover_candidate_area=qstats(areas1),
        turnover_baseline_area_sum=float(areas0.sum()), turnover_candidate_area_sum=float(areas1.sum()),
        turnover_fraction_of_changed_baseline_area=float(areas0.sum()/changed_base_area),
        minimum_changed_baseline_area=min_changed0, minimum_changed_candidate_area=min_changed1,
        source_material_t=qstats(uvcharts[:, 0]),
        projected_inside_existing_close=int(inside.sum()), parent_concentration=groups,
        top_angle_triangles=top,
        method='All exact changed quads, same native arithmetic fan. For dot<=0 centroids, existing G7 source chart is interpolated on the same triangle; already-certified parent atlas exact membership gives along/across. Query symmetry and taper selection match frozen v4. No nearest world coordinates, new ridge measurement, collision test or generated geometry.',
        limitations=['A triangle centroid can lie outside the support even though one of its controls moves; unmapped centroids are retained, not discarded.',
            'Projected close-frame inclusion does not mean visible; no depth/occlusion test is performed.',
            'Parent node-envelope and width thresholds only describe concentration; none is an acceptance gate.',
            'Normal turnover relative to baseline does not prove a self-intersection.'],
        elapsed_seconds=time.perf_counter()-started)
    with args.output.open('x', encoding='utf8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(output=str(args.output), total=len(ids), mapped=report['mapped_parent_centroids'],
        projected_inside_existing_close=int(inside.sum()), baseline_area_fraction=report['turnover_fraction_of_changed_baseline_area'],
        parents=groups, elapsed_seconds=report['elapsed_seconds'])), flush=True)


if __name__ == '__main__': main()
