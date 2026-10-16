"""Small read-only saved-curve projection and previous audit scope correction."""
from pathlib import Path
import argparse
import json

import numpy as np


def project(points):
    position = np.asarray([-18., 28., 12.])
    target = np.asarray([-.6, .72, 6.6])
    forward = target-position; forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    relative = points-target
    return np.column_stack((.5+relative@right/1.25, .5-relative@up/1.25))


def clip_line(a, b):
    lo, hi = 0., 1.
    d = b-a
    for axis in range(2):
        if abs(d[axis]) < 1e-15:
            if not 0 <= a[axis] <= 1: return None
        else:
            t0, t1 = -a[axis]/d[axis], (1-a[axis])/d[axis]
            lo, hi = max(lo, min(t0, t1)), min(hi, max(t0, t1))
            if hi <= lo: return None
    return lo, hi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--old-audit', type=Path, required=True)
    parser.add_argument('--corrected-audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for p in (args.corrected_audit, args.output):
        if p.exists(): raise FileExistsError('New-only audit output.')
    previous = json.loads(args.old_audit.read_text(encoding='utf8'))
    exact = previous.pop('saved_sparse_differential_plus_baseline_equal_export')
    previous['saved_sparse_differential_plus_baseline_equal_export_at_listed_ids'] = exact
    previous['exported_tiny_changed_controls_not_in_sparse_archive'] = previous['exact_changed_controls']-previous['meaningful_changed_controls']
    previous['sparse_scope_correction'] = 'Exact equality was checked at every saved sparse ID only. The exporter stores IDs with displacement norm>1e-12. Another404 exported controls differ by<=1e-12 and are absent from this archive. Complete native/control archives remain the actual full output. No global sparse-plus-baseline bitwise-equality claim is made.'
    previous['supersedes'] = str(args.old_audit)
    args.corrected_audit.write_text(json.dumps(previous, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    receipt = json.loads((args.root/'RECEIPT.json').read_text(encoding='utf8'))
    rows = []
    for pi, info in enumerate(receipt['foundation']):
        saved = json.loads(Path(info['evidence']['description']).read_text(encoding='utf8'))
        tree = saved['tree']['foundation']['source_curve']
        with np.load(saved['array_file'], allow_pickle=False) as z:
            xyz = z[tree['xyz']['npz_key']]
            s = z[tree['s']['npz_key']]
        for sx, sy in ((1., 1.), (-1., 1.), (1., -1.), (-1., -1.)):
            points = xyz.copy(); points[:, 0] *= sx; points[:, 1] *= sy
            xy = project(points)
            count = int(np.all((xy>=0)&(xy<=1), axis=1).sum())
            intervals, clipped_xy = [], []
            for k in range(len(points)-1):
                span = clip_line(xy[k], xy[k+1])
                if span is None: continue
                a, b = span
                intervals.append([float(s[k]+a*(s[k+1]-s[k])), float(s[k]+b*(s[k+1]-s[k]))])
                clipped_xy.extend([((1-a)*xy[k]+a*xy[k+1]).tolist(), ((1-b)*xy[k]+b*xy[k+1]).tolist()])
            visible_arc = sum(b-a for a, b in intervals)
            rows.append(dict(parent_index=pi, component=info['component'], mirror_components=info['mirror_component_orbit'],
                reflection=[sx, sy], total_stations=len(points), projected_inside_stations=count,
                source_arc_length=float(s[-1]-s[0]), projected_in_frame_source_arc_length=visible_arc,
                projected_in_frame_arc_fraction=visible_arc/(s[-1]-s[0]),
                projected_in_frame_arc_intervals=intervals,
                projected_path_bounds=[xy.min(axis=0).tolist(), xy.max(axis=0).tolist()],
                clipped_in_frame_bounds=([np.min(clipped_xy, axis=0).tolist(), np.max(clipped_xy, axis=0).tolist()] if clipped_xy else None)))
    report = dict(kind='SAVED_SELECTED_PARENT_CURVES_FROZEN_CLOSE_PROJECTION', candidate_root=str(args.root),
        camera=dict(position=[-18,28,12], target=[-.6,.72,6.6], orthographic_scale=1.25, resolution=[900,900]),
        parent_curves=rows,
        method='Saved certified G6 phase-guide station XYZ and physical arc; each XY mirror is projected by the frozen close camera. Existing polyline segments are clipped to the unit image rectangle; physical source-arc intervals are interpolated. No new curve measurement or geometry/ray generation.',
        limitations=['Frame inclusion does not establish visible coverage; no occlusion test or current G7-facing-normal test.',
            'Adaptive station counts are not area or arc-weighted coverage; clipped source arc supplies the latter polyline estimate.',
            'Four reflected guides may duplicate physical paths for a self-symmetric orbit; per-reflection counts must not be summed as unique coverage.',
            'Guide centre projection omits finite ornament width, node relief and silhouette changes.'])
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(dict(corrected_audit=str(args.corrected_audit), projection=str(args.output),
        per_reflection=[{k:r[k] for k in ('parent_index','reflection','projected_inside_stations','projected_in_frame_source_arc_length','projected_in_frame_arc_fraction')} for r in rows]), indent=2))


if __name__ == '__main__': main()
