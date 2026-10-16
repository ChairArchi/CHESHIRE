"""Read-only local directional audit of eight previously ray-mapped G6 quads.

This loads preserved arrays, never generates geometry/rays/renders, and writes
one new compact JSON. Run from this repository with its existing Python venv.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np


REPO = Path(__file__).resolve().parents[2]
RAYS = REPO / 'experiments/fold_junction_development_20261015/diagnosis_visible_face_owners_results.json'
G6 = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states/G06_MIDDLE')
PARENT = Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial13_causal_parent_generation/ACTUAL_G6_PARENT')
OUTPUT = REPO / 'docs/fold_junction_development_20261015/DIRECTION_ALIGNMENT_AUDIT.json'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def unit(vector):
    length = np.linalg.norm(vector)
    if not np.isfinite(length) or length <= 1e-15:
        raise ValueError('Undefined local direction; no fallback.')
    return vector / length


def line_angle(a, b):
    # Unoriented line comparison: a and -a represent the same fold direction.
    return float(np.degrees(np.arccos(np.clip(abs(unit(a) @ unit(b)), 0., 1.))))


def summary(rows, key):
    values = np.asarray([row[key] for row in rows if key in row])
    return dict(count=len(values), minimum=float(values.min()),
                median=float(np.median(values)), maximum=float(values.max()))


def audit():
    receipt = json.loads(RAYS.read_text(encoding='utf8'))
    parent_receipt = json.loads(PARENT.with_suffix('.json').read_text(encoding='utf8'))
    paths = [RAYS, G6/'control_quad.npz', G6/'evidence.npz', G6/'generation.json',
             PARENT.with_suffix('.json'), PARENT.with_suffix('.npz'), Path(__file__)]
    hashes = {str(path): sha(path) for path in paths}
    for path in (G6/'control_quad.npz', G6/'evidence.npz'):
        if hashes[str(path)] != receipt['source_bindings'][str(path)]:
            raise ValueError('G6 source does not match the old exact ray receipt.')
    if hashes[str(PARENT.with_suffix('.npz'))] != parent_receipt['array_file_sha256']:
        raise ValueError('Saved actual G6 parent arrays changed.')
    hits = receipt['rays']
    with np.load(G6/'control_quad.npz', allow_pickle=False) as saved:
        quads = saved['faces'][[hit['G6_quad_id'] for hit in hits]]
        xyz = saved['xyz']
        chart = saved['chart']
        positions = xyz[quads].copy()
        charts = chart[quads].copy()
        del xyz, chart
    with np.load(G6/'evidence.npz', allow_pickle=False) as saved:
        phase = saved['directional_phase'][quads]
    tree = parent_receipt['tree']['parent']
    needed = ('parameter', 'formation_shoulder_cross', 'formation_shoulder_arc',
              'controller_shoulder_xyz', 'family_id', 'axis')
    with np.load(PARENT.with_suffix('.npz'), allow_pickle=False) as saved:
        parent = {key: saved[tree[key]['npz_key']] for key in needed}
    if str(parent['axis']) != 'theta':
        raise ValueError('This audit requires the actual theta-longitudinal parent.')
    parameters = parent['parameter']
    crosses = parent['formation_shoulder_cross']
    arcs = parent['formation_shoulder_arc']
    shoulder = parent['controller_shoulder_xyz']
    rows = []
    for index, hit in enumerate(hits):
        signs = np.sign(positions[index].mean(axis=0))
        signs[2] = 1.
        if np.any(signs == 0.):
            raise ValueError('An axis-straddling sample needs explicit treatment.')
        point = positions[index] * signs
        uv = np.column_stack([charts[index, :, 0],
            np.arctan2(abs(charts[index, :, 2]), abs(charts[index, :, 1]))])
        centre = uv.mean(axis=0)
        uv_delta = uv - centre
        xyz_delta = point - point.mean(axis=0)
        jacobian, _, rank, _ = np.linalg.lstsq(uv_delta, xyz_delta, rcond=None)
        if rank != 2:
            raise ValueError('Degenerate local material chart; no fallback.')
        covector = np.linalg.lstsq(uv_delta, phase[index]-phase[index].mean(), rcond=None)[0]
        # dphi = phi_t dt + phi_theta dtheta = 0.
        # Push its material null direction through the actual local Jacobian.
        iso = covector[1]*jacobian[0] - covector[0]*jacobian[1]
        actual_edges = np.roll(point, -1, axis=0) - point
        edge_middle_angles = [line_angle(edge, iso) for edge in actual_edges]
        best_middle_edge = int(np.argmin(edge_middle_angles))
        edge_uv_delta = np.roll(uv, -1, axis=0) - uv
        selected_edge_uv = edge_uv_delta[best_middle_edge]
        if abs(selected_edge_uv[0]) <= 1e-12:
            edge_family = 'constant_t_theta_row'
        elif abs(selected_edge_uv[1]) <= 1e-9:
            edge_family = 'constant_theta_t_row'
        else:
            edge_family = 'mixed_material_edge'
        t, theta = centre
        if not parameters[0] <= theta <= parameters[-1]:
            raise ValueError('Parent theta extrapolation is prohibited.')
        lower = np.interp(theta, parameters, crosses[:, 0])
        upper = np.interp(theta, parameters, crosses[:, -1])
        inside = bool(lower <= t <= upper)
        row = dict(previous_ray_image_xy=hit['normalized_image_xy'],
            G6_quad_id=hit['G6_quad_id'], G3_face_id=hit['G3_face_id'],
            prior_native_triangle_id=hit['global_native_triangle_id'],
            prior_native_fan_corner=hit['native_fan_corner'],
            event_owner=hit['event_owner'], role=hit['role_name'],
            G6_quad_vertex_ids=quads[index].tolist(),
            canonical_reflection_signs=signs.tolist(),
            quad_centre_material_t=float(t), quad_centre_material_theta=float(theta),
            local_X_t=jacobian[0].tolist(), local_X_theta=jacobian[1].tolist(),
            local_phase_covector_t_theta=covector.tolist(),
            local_phase_isoline_tangent=unit(iso).tolist(),
            affine_material_to_xyz_maximum_residual=float(np.linalg.norm(
                uv_delta @ jacobian-xyz_delta, axis=1).max()),
            best_quad_edge_to_material_theta_degrees=min(line_angle(edge, jacobian[1]) for edge in actual_edges),
            phase_isoline_to_material_theta_degrees=line_angle(iso, jacobian[1]),
            edge_angles_to_middle_phase_isoline_degrees=edge_middle_angles,
            best_quad_edge_to_middle_phase_isoline_degrees=float(edge_middle_angles[best_middle_edge]),
            best_middle_phase_edge_index=best_middle_edge,
            best_middle_phase_edge_material_family=edge_family,
            best_middle_phase_edge_material_delta=selected_edge_uv.tolist(),
            absolute_cos_2_best_middle_phase_edge_angle=float(abs(np.cos(2*np.radians(edge_middle_angles[best_middle_edge])))),
            adjacent_edge_family_line_angle_degrees=line_angle(actual_edges[0], actual_edges[1]),
            inside_measured_family4_shoulder=inside,
            measured_family4_material_t_range=[float(lower), float(upper)])
        if inside:
            j = int(np.clip(np.searchsorted(parameters, theta), 1, len(parameters)-1))
            fraction = (theta-parameters[j-1])/(parameters[j]-parameters[j-1])
            t_row = (1-fraction)*crosses[j-1] + fraction*crosses[j]
            arc_row = (1-fraction)*arcs[j-1] + fraction*arcs[j]
            if np.any(np.diff(t_row) <= 0.) or np.any(np.diff(arc_row) <= 0.):
                raise ValueError('Measured shoulder coordinates must be ordered.')
            alpha = float(np.interp(t, t_row, arc_row) / arc_row[-1])
            same_arc_fraction = np.asarray([
                [np.interp(alpha*arcs[r, -1], arcs[r], shoulder[r, :, d])
                 for d in range(3)] for r in range(len(parameters))])
            derivatives = np.gradient(same_arc_fraction, parameters, axis=0)
            tangent = np.asarray([np.interp(theta, parameters, derivatives[:, d]) for d in range(3)])
            row.update(measured_family4_physical_arc_fraction=alpha,
                measured_family4_shoulder_flow_tangent=unit(tangent).tolist(),
                best_quad_edge_to_measured_shoulder_flow_degrees=min(line_angle(edge, tangent) for edge in actual_edges),
                material_theta_to_measured_shoulder_flow_degrees=line_angle(jacobian[1], tangent),
                phase_isoline_to_measured_shoulder_flow_degrees=line_angle(iso, tangent))
        rows.append(row)
    changed = [str(path) for path in paths if sha(path) != hashes[str(path)]]
    if changed:
        raise ValueError('Read-only source changed during audit: '+repr(changed))
    keys = ('best_quad_edge_to_material_theta_degrees',
        'phase_isoline_to_material_theta_degrees',
        'best_quad_edge_to_middle_phase_isoline_degrees',
        'best_quad_edge_to_measured_shoulder_flow_degrees',
        'material_theta_to_measured_shoulder_flow_degrees',
        'phase_isoline_to_measured_shoulder_flow_degrees')
    return dict(kind='SAVED_G6_EIGHT_QUAD_DIRECTION_ALIGNMENT_AUDIT', date='2026-10-15',
        sources_and_sha256=hashes, source_hashes_verified_before_and_after=True,
        old_ray_receipt_kind=receipt['kind'], old_ray_camera=receipt['camera'],
        current_geometry='Preserved replay G06_MIDDLE control surface; intermediate native was not stored.',
        evaluation_location='Centres of the eight G6 quads previously hit by exact native-fan orthographic rays. No new rays are cast.',
        measured_parent_family=int(parent['family_id']),
        measured_parent_parameter_range=[float(parameters[0]), float(parameters[-1])],
        tangent_derivation=dict(material='Least-squares actual quad XYZ versus local [material t, canonical theta]; X_theta is only the material-row tangent.',
            middle_wrinkle='Fit the G6 MIDDLE parent-wrinkle phase covector [phi_t,phi_theta] on the same quad; push [phi_theta,-phi_t] through the local Jacobian. This is not a separately measured NESTED CHILD/SMALL ornament direction.',
            shoulder='At each query material t/theta, interpolate its physical cross-shoulder arc fraction from the saved 65x129 actual G6 family4 grid. Sample that same arc fraction along all65 theta stations; np.gradient in actual theta then linear interpolation gives the measured shoulder-flow tangent.',
            comparison='Unoriented line angle arccos(abs(dot(unit(a),unit(b)))) in degrees; best edge is minimum over the actual four quad edges.'),
        angle_summaries={key:summary(rows,key) for key in keys}, samples=rows,
        interpretation='These sampled quad rows retain material-theta orientation, while G6 MIDDLE parent-wrinkle phase isolines usually cross those rows. The minimum angle to all four native quad edges separately checks whether the other edge family follows MIDDLE. The measured original-family4 macro shoulder-flow direction can differ materially from either. This establishes differences between those reference directions; it does not establish wrong placement of NESTED ornaments relative to their MIDDLE wrinkle parent or the need for retopology.',
        hierarchy_semantics=dict(original_macro='Original eight G0/G2 PCHIP families and actual measured family4 shoulder are macro references, not automatically the parent intended by the user.',
            middle_wrinkle='G6 MIDDLE phase itself generates a distinct wrinkle layer; its isolines were measured in this audit.',
            nested_child_small='NESTED CHILD and SMALL use scalar functions of the same wrapped MIDDLE phase. Their ideal unmodulated isolines are parallel to MIDDLE-phase isolines wherever the derivative is nonzero and the phase is smooth. Actual resulting ridge directions were not measured.',
            attached_ornament='Older owner>0 CAP/WALL/directional attachments were not sampled: all eight audited faces have SOURCE owner0.'),
        causal_scope='No automatic conclusion that MIDDLE wrinkles should align with original macro rails. For CHILD/SMALL, phase orientation is inherited; absence of an independent along-ribbon forming coordinate distinguishes parallel nested profiles from branching anatomy, but does not alone prove an aesthetic defect.',
        limitations=[
            'Eight selected visible hit quads are not a global or area-weighted statistic.',
            'Material X_theta is not assumed to be the true mature S-fold tangent.',
            'The family4 shoulder is a saved measured parent lattice, not independently estimated principal curvature or ground-truth ridge direction; detection and sampling variation affect its derivative.',
            'Only seven sample quad centres lie inside this saved family4 shoulder; the eighth has no shoulder-flow comparison.',
            'The measured MIDDLE phase is a G6 parent-wrinkle field, not an independent later ornament field. CHILD/SMALL theoretical level sets are functions of this same phase; actual final crest orientation is not measured.',
            'Local quad affine Jacobians and piecewise-linear shoulder interpolation are numerical approximations on existing geometry.',
            'No model generation, new raycast, render, geometry edit, global retopology or beauty test is performed.'
        ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Evidence is new-only: '+str(args.output))
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(args.output), angles=result['angle_summaries']), indent=2))


if __name__ == '__main__':
    main()
