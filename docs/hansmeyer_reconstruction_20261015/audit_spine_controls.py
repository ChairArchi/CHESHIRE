"""Read-only exact-control and arithmetic-fan review of an exported SPINE.

This does not load native mesh archives, generate geometry, cast rays, render,
or certify collision freedom or beauty. Existing exporter receipt bindings are
recorded rather than rehashing their large archives.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import time

import numpy as np


REPO = Path(__file__).resolve().parents[2]
STATES = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
RAYS = REPO/'experiments/fold_junction_development_20261015/diagnosis_visible_face_owners_results.json'
CHUNK = 65536
QUANTILES = [0., .1, .5, .9, .99, 1.]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stat(path):
    s = Path(path).stat()
    return dict(size=s.st_size, mtime_ns=s.st_mtime_ns)


def quantile(values):
    a = np.asarray(values)
    return dict(count=len(a), probabilities=QUANTILES,
                values=np.quantile(a, QUANTILES).tolist()) if len(a) else dict(count=0)


def get_array(z, tree, key):
    return z[tree[key]['npz_key']]


def registered_anchor(base, out, q7, q6_id, fan_corner, bary, metadata):
    """Carry G6 fan logical-square point to its exact G7 native fan.

    The logical square records ancestry only. It is not an inverse in world
    space, a newly measured crest, or a claim that G6 and G7 positions coincide.
    """
    corners = np.asarray([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
    midpoint = np.asarray([.5, .5])
    i = int(fan_corner)
    uv = np.asarray(bary)@np.stack((corners[i], corners[(i+1)%4], midpoint))
    found = []
    for child in range(4):
        cuv = np.stack(((corners[(child-1)%4]+corners[child])/2,
                       corners[child], (corners[child]+corners[(child+1)%4])/2,
                       midpoint))
        centre = cuv.mean(axis=0)
        for corner in range(4):
            tri = np.stack((cuv[corner], cuv[(corner+1)%4], centre))
            local = np.linalg.solve((tri[1:]-tri[0]).T, uv-tri[0])
            weights = np.r_[1-local.sum(), local]
            if np.all(weights >= -1e-10) and np.all(weights <= 1+1e-10):
                found.append((child, corner, weights))
    if not found:
        raise ValueError('Registered ancestry point has no containing G7 native fan.')
    child, corner, weights = found[0]
    gid = 4*int(q6_id)+child
    ids = q7[gid]
    def evaluate(xyz):
        p = xyz[ids]
        return weights@np.stack((p[corner], p[(corner+1)%4], p.mean(axis=0)))
    before, after = evaluate(base), evaluate(out)
    duplicate_gap = 0.
    for c, k, b in found[1:]:
        ids2 = q7[4*int(q6_id)+c]
        p = out[ids2]
        value = b@np.stack((p[k], p[(k+1)%4], p.mean(axis=0)))
        duplicate_gap = max(duplicate_gap, float(np.linalg.norm(value-after)))
    if duplicate_gap > 1e-11:
        raise ValueError('Shared boundary ancestry evaluation is discontinuous.')
    return dict(**metadata, source_G6_quad_id=int(q6_id),
        source_G6_fan_corner=int(fan_corner), source_G6_barycentric=np.asarray(bary).tolist(),
        source_logical_square_uv=uv.tolist(), candidate_G7_quad_id=gid,
        candidate_native_triangle_id=4*gid+corner, candidate_native_fan_corner=corner,
        candidate_native_barycentric=weights.tolist(), G7_quad_control_ids=ids.tolist(),
        native_face_centre_id=len(base)+gid,
        baseline_xyz=before.tolist(), candidate_xyz=after.tolist(),
        displacement=(after-before).tolist(), displacement_length=float(np.linalg.norm(after-before)),
        shared_boundary_evaluation_gap=duplicate_gap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Evidence output is new-only.')
    started = time.perf_counter()
    receipt_path = args.root/'RECEIPT.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf8'))
    variants = receipt['variants']
    bpath, cpath = (Path(variants[k]['control_quad']) for k in ('REFERENCE_NESTED', 'SPINE'))
    stats = {str(p):stat(p) for p in (receipt_path, bpath, cpath, RAYS)}
    print('AUDIT load exact saved controls, no native mesh archives', flush=True)
    with np.load(bpath, allow_pickle=False) as z:
        base, q7 = z['xyz'], z['faces']
    with np.load(cpath, allow_pickle=False) as z:
        out, candidate_q = z['xyz'], z['faces']
    if base.shape != out.shape or not np.array_equal(q7, candidate_q):
        raise ValueError('Exported candidate changed accepted control topology.')
    del candidate_q
    q6path = STATES/'G06_MIDDLE/control_quad.npz'
    stats[str(q6path)] = stat(q6path)
    with np.load(q6path, allow_pickle=False) as z:
        q6 = z['faces']
    if not np.array_equal(q7.reshape(-1, 4, 4)[:, :, 1], q6):
        raise ValueError('Saved G6 to G7 old-corner ancestry is not exact.')
    del q6
    gc.collect()
    lengths = np.linalg.norm(out-base, axis=1)
    changed = np.any(base != out, axis=1)
    meaningful = lengths > 1e-12
    sparse_path = args.root/'SPARSE_DELTA.npz'
    stats[str(sparse_path)] = stat(sparse_path)
    with np.load(sparse_path, allow_pickle=False) as z:
        sparse_ids, sparse_delta = z['ids'], z['delta']
    if not np.array_equal(sparse_ids, np.flatnonzero(meaningful)):
        raise ValueError('Saved sparse meaningful control IDs differ from exported output.')
    if not np.array_equal(out[sparse_ids], base[sparse_ids]+sparse_delta):
        raise ValueError('Exported controls are not the saved differential plus accepted controls.')
    print('AUDIT topology and sparse/export equality passed; changed-quad fan orientation', flush=True)
    angles, ratios = [], []
    changed_quads = 0
    turnover = 0
    nonfinite = 0
    baseline_degenerate = 0
    candidate_degenerate = 0
    maximum = []
    for start in range(0, len(q7), CHUNK):
        block = q7[start:start+CHUNK]
        take = np.flatnonzero(changed[block].any(axis=1))
        if not len(take):
            continue
        gids = start+take
        block = block[take]
        p, r = base[block], out[block]
        n0 = np.cross(np.roll(p, -1, axis=1)-p, p.mean(axis=1)[:, None]-p)
        n1 = np.cross(np.roll(r, -1, axis=1)-r, r.mean(axis=1)[:, None]-r)
        a0, a1 = np.linalg.norm(n0, axis=2), np.linalg.norm(n1, axis=2)
        baseline_degenerate += int((a0 <= 0).sum())
        candidate_degenerate += int((a1 <= 0).sum())
        nonfinite += int((~np.isfinite(n1)).sum())
        cosine = np.einsum('nki,nki->nk', n0, n1)/(a0*a1)
        angle = np.degrees(np.arccos(np.clip(cosine, -1., 1.)))
        ratio = a1/a0
        angles.append(angle.ravel()); ratios.append(ratio.ravel())
        changed_quads += len(block)
        turnover += int((cosine <= 0.).sum())
        flat_top = np.argsort(angle.ravel())[-12:]
        for flat in flat_top:
            row, corner = divmod(int(flat), 4)
            maximum.append(dict(G7_quad_id=int(gids[row]), native_fan_corner=corner,
                native_triangle_id=4*int(gids[row])+corner,
                G3_face_id=int(gids[row]//256),
                baseline_triangle_xyz=np.stack((p[row, corner], p[row, (corner+1)%4], p[row].mean(axis=0))).tolist(),
                candidate_triangle_xyz=np.stack((r[row, corner], r[row, (corner+1)%4], r[row].mean(axis=0))).tolist(),
                angle_degrees=float(angle[row, corner]), area_ratio=float(ratio[row, corner])))
        maximum = sorted(maximum, key=lambda x:x['angle_degrees'], reverse=True)[:12]
    angles, ratios = np.concatenate(angles), np.concatenate(ratios)
    # Prior visible anchors retain exact ancestry; image coordinates never place
    # or shape the ornament and no new view-dependent query is made here.
    rays = json.loads(RAYS.read_text(encoding='utf8'))
    anchors = [registered_anchor(base, out, q7, hit['G6_quad_id'], hit['native_fan_corner'],
        hit['barycentric'], dict(label=f'prior_visible_source_sample_{i:02}',
        previous_normalized_image_xy=hit['normalized_image_xy'],
        original_G6_hit_xyz=hit['hit_xyz'], source_phase=hit['phase']))
        for i, hit in enumerate(rays['rays'])]
    # Existing physical cross profiles provide flanking-source anchors. The
    # recorded peak/minima and quartile arc rows are not remeasured or snapped.
    for parent_index, parent in enumerate(receipt['foundation']):
        description = Path(parent['evidence']['description'])
        tree_receipt = json.loads(description.read_text(encoding='utf8'))
        tree = tree_receipt['tree']['foundation']['measurement']
        array_path = Path(tree_receipt['array_file'])
        stats[str(description)], stats[str(array_path)] = stat(description), stat(array_path)
        with np.load(array_path, allow_pickle=False) as z:
            s = get_array(z, tree, 's')
            tris = get_array(z, tree, 'triangle_ids')
            bary = get_array(z, tree, 'barycentric')
            valid = get_array(z, tree, 'valid')
            peak = get_array(z, tree, 'geometric_peak_index')
            shoulders = get_array(z, tree, 'shoulder_indices')
            keys = [key for key in ('geometric_left_index', 'geometric_right_index', 'left_min_index', 'right_min_index') if key in tree]
            side_indices = {key:get_array(z, tree, key) for key in keys}
            for fraction in (.25, .5, .75):
                row = int(np.argmin(np.abs(s-(s[0]+fraction*(s[-1]-s[0])))))
                choices = [('existing_measured_peak', int(peak[row])),
                           ('existing_measured_left_shoulder', int(shoulders[row, 0])),
                           ('existing_measured_right_shoulder', int(shoulders[row, 1])),
                           ('flanking_profile_left_endpoint', 0),
                           ('flanking_profile_right_endpoint', tris.shape[1]-1)]
                choices.extend((key, int(value[row])) for key, value in side_indices.items())
                for role, col in choices:
                    if col < 0 or col >= tris.shape[1] or not valid[row, col]:
                        continue
                    tid = int(tris[row, col])
                    anchors.append(registered_anchor(base, out, q7, tid//4, tid%4,
                        bary[row, col], dict(label=f'parent_{parent_index:02}_{fraction:.2f}_{role}',
                        parent_component=parent['component'], parent_profile_row=row,
                        recorded_profile_column=col, physical_arc_fraction=fraction,
                        physical_arc_s=float(s[row]), description=str(description))))
    if any(stat(path) != before for path, before in stats.items()):
        raise ValueError('A bound read-only input changed during the audit.')
    report = dict(kind='EXPORTED_SPINE_EXACT_CONTROL_AND_REGISTERED_SOURCE_ANCHOR_AUDIT',
        date='2026-10-15', candidate_root=str(args.root), receipt=str(receipt_path),
        receipt_sha256=digest(receipt_path), helper_sha256=digest(__file__),
        source_stat_bindings=stats,
        source_receipt_hash_bindings={k:{'control_quad':variants[k]['control_quad'],
            'control_quad_sha256':variants[k]['control_quad_sha256'],
            'geometry_sha256':variants[k]['geometry_sha256']} for k in ('SPINE', 'REFERENCE_NESTED')},
        large_archive_hashes_recomputed=False,
        exact_control_topology_equal=True, exact_G6_G7_old_corner_ancestry=True,
        saved_sparse_ids_equal_exported_displacement_ids=True,
        saved_sparse_differential_plus_baseline_equal_export=True,
        controls=len(base), quads=len(q7), exact_changed_controls=int(changed.sum()),
        meaningful_changed_controls=int(meaningful.sum()), exact_untouched_controls=int((~changed).sum()),
        moved_control_displacement=quantile(lengths[meaningful]),
        changed_quad_native_fan_review=dict(quads=changed_quads, triangles=len(angles),
            angle_degrees=quantile(angles), area_ratio=quantile(ratios),
            relative_orientation_turnovers_dot_le_zero=turnover,
            angle_over_45_degrees=int((angles>45.).sum()), angle_over_90_degrees=int((angles>90.).sum()),
            baseline_degenerate_triangles=baseline_degenerate,
            candidate_degenerate_triangles=candidate_degenerate,
            candidate_nonfinite_normal_components=nonfinite, largest_angle_triangles=maximum),
        registered_source_anchors=anchors,
        anchor_displacement_summary=quantile([r['displacement_length'] for r in anchors]),
        anchor_semantics='Existing G6 fan triangle/barycentric locations are carried through exact G6-to-G7 CC child provenance using an abstract unit-square parent and containing child native fan. Baseline/candidate evaluation uses the same saved G7 control IDs and arithmetic face centre. These are approximate source anchors, not independently measured mature S crest/valley/merge landmarks. Existing profile endpoints sample flanking source, without certifying calm cloth in the final image.',
        orientation_semantics='Oriented arithmetic-fan normals are compared at the same G7 quad/corner. Dot<=0 records a normal turn of at least90 degrees relative to the accepted baseline, not a global topological inversion certificate. Large normal turns can be intentional ornament relief. Unchanged triangles need no rescan because all of their controls are exactly unchanged.',
        limitations=['No 3D self-intersection or inter-sheet collision test.',
            'Source UV injectivity does not certify embedded 3D geometry.',
            'Area and orientation statistics do not certify beauty or macro preservation.',
            'No world-nearest correspondence, new measurement, generation, render or image.'],
        elapsed_seconds=time.perf_counter()-started)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps(dict(output=str(args.output), changed_quads=changed_quads,
        triangles=len(angles), angle_degrees=quantile(angles), turnovers=turnover,
        candidate_degenerate=candidate_degenerate, anchors=len(anchors),
        anchor_displacement=report['anchor_displacement_summary'], elapsed_seconds=report['elapsed_seconds'])), flush=True)


if __name__ == '__main__':
    main()
