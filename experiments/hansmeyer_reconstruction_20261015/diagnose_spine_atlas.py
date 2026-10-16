"""One actual-parent raw/refined atlas diagnosis; no full model or render."""
from pathlib import Path
import json
import numpy as np
import run_spine_reconstruction_v3 as run


def jacobian(chart, quads):
    triangles = np.concatenate((quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]))
    points = chart[triangles]
    angle = np.arctan2(points[:, :, 2], points[:, :, 1])
    centre = np.arctan2(points[:, :, 2].mean(axis=1), points[:, :, 1].mean(axis=1))
    angle = centre[:, None]+np.arctan2(np.sin(angle-centre[:, None]), np.cos(angle-centre[:, None]))
    uv = np.stack((points[:, :, 0], angle), axis=-1)
    det = run.cross2(uv[:, 1]-uv[:, 0], uv[:, 2]-uv[:, 0])
    opposite = det*np.median(det) < 0.
    return dict(triangles=len(det), degenerate=int(np.count_nonzero(abs(det) <= 1e-15)),
        flipped=int(opposite.sum()), determinant_quantiles=np.quantile(det, [0., .01, .1, .5, .9, .99, 1.]).tolist()), det


def main():
    root = run.REPO/'docs/hansmeyer_reconstruction_20261015/spine_atlas_diagnosis01'
    if root.exists():
        raise FileExistsError('Frozen diagnosis output already exists.')
    report = json.loads(run.GRAPH.read_text(encoding='utf8'))
    with np.load(report['evidence']['path'], allow_pickle=False) as z:
        graph = {key:z[key] for key in z.files}
    with np.load(report['source_control'], allow_pickle=False) as z:
        xyz, q, chart = z['xyz'], z['faces'], z['chart']
    with np.load(run.STATES/'G06_MIDDLE/evidence.npz', allow_pickle=False) as z:
        phase = z['directional_phase']
    with np.load(run.STATES/'G03_SIDEWALL/control_quad.npz', allow_pickle=False) as z:
        q3, chart3 = z['faces'], z['chart']
    with np.load(run.STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z:
        owners = z['face_event_ids']
    cap = np.all(chart3[q3, 0] == 0., axis=1)|np.all(chart3[q3, 0] == 1., axis=1)
    surface = run.NativeSurface(xyz, q, phase, np.repeat((owners == 0)&~cap, 64), chart)
    candidate = run.canonical_candidates(report, graph, float(np.ptp(xyz[:, 2])))[0]
    strip, info, evidence = run.prepare_parent(surface, graph, report['components'][candidate[1]], candidate[2], float(np.ptp(xyz[:, 2])))
    delta, qf, cf, meta, state = run.spine.form(strip, periodic=info['periodic'],
        cell_count=info['node_count'], phase_origin=info['phase_origin'], total_length=info['total_length'])
    rows = len(strip['s']); ns = rows if info['periodic'] else rows-1
    r, u = np.meshgrid(np.arange(ns), np.arange(8), indexing='ij'); nxt = (r+1)%rows
    q0 = np.stack((r*9+u, nxt*9+u, nxt*9+u+1, r*9+u+1), axis=-1).reshape(-1, 4)
    raw, dr = jacobian(strip['chart0'].reshape(-1, 3), q0)
    refined, df = jacobian(cf, qf)
    centre_derivative = np.gradient(strip['xyz0'][:, 4], strip['s'], axis=0)
    normals = strip['normal']; centre_derivative -= normals*np.einsum('ij,ij->i', centre_derivative, normals)[:, None]
    centre_derivative /= np.linalg.norm(centre_derivative, axis=1)[:, None]
    nominal_t = np.cross(strip['across'], normals)
    angle = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', centre_derivative, nominal_t), -1., 1.)))
    nf = len(q0); bad = (dr*np.median(dr) < 0.)|(abs(dr) <= 1e-15)
    raw_bad_rows = np.unique(np.tile(np.arange(nf)//8, 2)[bad])
    summary = dict(component=info['component'], raw=raw, refined=refined,
        actual_recentered_curve_vs_nominal_tangent_degrees=np.quantile(angle, [0., .1, .5, .9, .99, 1.]).tolist(),
        raw_bad_rows=raw_bad_rows.tolist(),
        scope='One preparation and diagnostic of source correspondences, no candidate model/export/render.')
    root.mkdir(parents=True)
    saved = run.receipt_helper.save_tree(root, 'PREPARED_PARENT', dict(strip=strip, info=info,
        evidence=evidence, formation=state, raw_determinant=dr, refined_determinant=df,
        nominal_vs_actual_tangent_angle=angle))
    summary['saved_parent'] = saved
    summary['source_helper_hashes'] = {str(path):run.sha(path) for path in
        (Path(__file__), Path(run.__file__), run.HERE/'recursive_spine_operator.py', run.HERE/'native_strip_surface.py')}
    run.write(root/'DIAGNOSIS.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
