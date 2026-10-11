"""Two existing Task36 normal-response options on identical OVERLAP G2.

Exactly one G3 ancestry split plus finite escape18 nearest-outside attraction.
Only normal_response differs from the preserved class_signed OVERLAP G3.
No new authored fold, shape warp, smoothing, stencil or solver is introduced.
"""
from pathlib import Path
import argparse
import json
import shutil

import numpy as np
import trimesh

import overlap_probe as overlap

ancestry = overlap.ancestry
prior = overlap.prior
MODES = dict(face_geometry='FACE_RESPONSE', all_geometry='SIGNED_RESPONSE')
ALGORITHM = 'EXISTING_OVERLAP_G2_NORMAL_RESPONSE_COMPARISON_G3_V1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/directional_growth_20261012'))
    parser.add_argument('--response', choices=tuple(MODES), required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    source = root/'OVERLAP'/'G02'
    folder = root/MODES[args.response]/'G03'
    source_meta = json.loads((source/'generation.json').read_text(encoding='utf8'))
    if source_meta['quick_integrity'] != 'PASS':
        raise ValueError('Failed preserved input cannot silently be reused as successful geometry.')
    recipe = overlap.RECIPE.copy()
    recipe['normal_response'] = args.response
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = 18
    signature = dict(algorithm=ALGORITHM, source=str(source), task36_recipe=recipe,
        field_recipe=cfg, fraction=.55, field_budget=.22, local_target_factor=3,
        new_authored_return_events=[], inherited_growth_cycles=2, current_growth_cycles=1)
    if folder.exists() and any(folder.iterdir()):
        record = folder/'generation.json'
        if not record.exists() or json.loads(record.read_text(encoding='utf8')).get('signature') != signature:
            raise FileExistsError('Different or incomplete output preserved: '+str(folder))
        print('REUSED',str(folder),flush=True)
        return
    mesh, chart = ancestry.load_control(source/'control_quad.npz')
    if mesh.generation != 2:
        raise ValueError('Requires the actual saved OVERLAP G2 controls.')
    incoming, incoming_faces = mesh.xyz.copy(), mesh.faces.copy()
    nv = len(incoming)
    out, op = ancestry.task36_growth.step(mesh, **recipe)
    edges = op['input_edges']
    chart_out = np.concatenate([chart, chart[edges].mean(1), chart[incoming_faces].mean(1)])
    interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[incoming_faces].mean(1)])
    if len(out.faces) != 4*len(incoming_faces) or len(out.xyz) != len(chart_out):
        raise ValueError('Unexpected existing split count or birth ordering.')
    if not np.array_equal(out.xyz[:nv], incoming):
        raise ValueError('Existing Task36 old-vertex retention failed before field.')
    if np.any(op['resolved_wp']):
        raise ValueError('This comparison must retain zero direct vertex normal gain.')
    pairs = prior.helpers.existing.symmetry(chart_out)
    raw_task36 = out.xyz-interpolated
    applied_task36 = raw_task36.copy()
    prior.helpers.existing.reflect(applied_task36, chart_out, pairs)
    out.xyz = interpolated+applied_task36
    post_task36 = out.xyz.copy()
    trees, field_cache = prior.helpers.outside_trees(cfg, overlap.OLD_ROOT)
    cached = json.loads((Path(field_cache)/'field.json').read_text(encoding='utf8'))['parameters']
    if cached['iterations'] != 18:
        raise ValueError('Field cache does not match fixed escape18 classifier.')
    out.xyz, field_payload, field_log = ancestry.loop.apply_field(
        out.xyz, out.faces, chart_out, cfg, trees, .55, .22, 3)
    physical = ancestry.task36_growth.native(out)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart_out, chart_out[out.faces].mean(1)])
    _, errors, matches = prior.reflection_state(physical.xyz, triangles, physical_chart)
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    area = float(actual.area_faces.min())
    checks = dict(finite=bool(np.isfinite(physical.xyz).all()), watertight=bool(actual.is_watertight),
        winding_consistent=bool(actual.is_winding_consistent), components=int(actual.body_count),
        minimum_triangle_area=area, minimum_area_threshold=1e-12, minimum_area_pass=area>1e-12,
        geometric_reflection_error=errors, reflected_triangle_sets_identical=matches)
    passed = checks['finite'] and checks['watertight'] and checks['winding_consistent'] and checks['minimum_area_pass']
    folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder/'checkpoint.npz', xyz=physical.xyz, faces=triangles, chart=physical_chart,
        classes=physical.classes, rest=physical.rest, anchors=physical.anchors,generation=np.array(physical.generation))
    np.savez_compressed(folder/'control_quad.npz', xyz=out.xyz, faces=out.faces, chart=chart_out,
        classes=out.classes, rest=out.rest, anchors=out.anchors,generation=np.array(out.generation))
    np.savez_compressed(folder/'operation_fields.npz', **op, **field_payload,
        incoming_g2_xyz=incoming, interpolated_xyz=interpolated, raw_task36_displacement=raw_task36,
        applied_task36_displacement=applied_task36, post_task36_xyz=post_task36, post_field_xyz=out.xyz)
    actual.export(folder/'gate.ply')
    shutil.copy2(__file__,folder/'response_recipe.py')
    coefficients={}
    for key in ('resolved_wf','resolved_we','resolved_wp'):
        values=op[key]
        coefficients[key]=dict(minimum=float(values.min()), maximum=float(values.max()),
            positive=int((values>1e-12).sum()), negative=int((values < -1e-12).sum()),
            zero=int((np.abs(values)<=1e-12).sum()))
    metadata=dict(signature=signature,candidate=MODES[args.response],stage='G03',
        source=str(source/'checkpoint.npz'),parent=str(source/'checkpoint.npz'),
        operation='One existing Task36 ancestry split with alternate existing geometry normal response, then the unchanged escape18 nearest-outside field',
        task36_recipe=recipe, normal_response=args.response,
        normal_response_scope='face_geometry changes existing face-normal coefficient using face contrast; all_geometry also changes edge-normal coefficient using edge contrast. Existing vertex_gain=0 means its vertex-normal response is exactly zero.',
        direct_vertex_normal_gain=0.,direct_vertex_normal_response_nonzero=False,
        resolved_normal_coefficients=coefficients,
        ancestry_eligible_faces=int(op['eligible'].sum()),incoming_faces=len(incoming_faces),
        task36_maximum_step=float(np.linalg.norm(applied_task36,axis=1).max()),
        old_task36_vertex_maximum_step=float(np.linalg.norm(applied_task36[:nv],axis=1).max()),
        field_recipe=cfg,field_step=field_log,field_cache=field_cache,field_iterations=18,
        internal_iteration_schedule=[4,8,18],inherited_growth_cycles=2,current_growth_cycles=1,
        growth_cycles_total=3,field_passes_total=3,subdivision_passes_total=3,new_quad_splits_this_branch=1,
        new_authored_return_events=0,inherited_authored_return_provenance=source_meta['authored_return_events'],
        return_policy='The two authored G2 source deformations are inherited; no new or amplified return at G3.',
        physical_vertices=len(physical.xyz),physical_triangles=len(triangles),control_vertices=len(out.xyz),control_quads=len(out.faces),
        step_budget_scope='The .22 maximum applies only to field displacement; Task36 placement is separate.',
        feature_memory=False,CC_standard_averaging_gain=0.,separate_geometric_smoothing=False,
        task36_terminal_policy='Unchanged existing plane_only constraints; subsequent field may move terminal controls.',
        physical_surface='Existing mean quad-centre triangle fans, created after field; not next-generation controls.',
        symmetry='Existing reflection of new displacement vectors and canonical field queries in X/Y; no posthoc XYZ averaging.',
        provenance='Existing CHESHIRE normal_response options reused, not new IAAC source recovery or a new geometry solver.',
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
        self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication_thickness_structure='NOT_CHECKED',**checks)
    prior.base.dump(folder/'generation.json',metadata)
    print('GENERATED',MODES[args.response],'G3',len(physical.xyz),len(triangles),
        'task36 max',metadata['task36_maximum_step'],'minimum area',area,'quick',metadata['quick_integrity'],flush=True)
    if not passed:
        raise ValueError('Failed geometry and metadata preserved; no repair or threshold change.')


if __name__=='__main__':
    main()
