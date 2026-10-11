"""Selected wall corridors on the actual ANCESTRY_STAGED G1 checkpoint.

Existing Task36 placement and finite-field displacement are both masked.
Fixed guides are sampled from the real G1 control surface, with a narrow
protected guide core and compact support on either side. This is declared
guide-band position memory, not a detected crease or physical folding solver.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
sys.path.insert(0, str(HERE.parent / 'fold_band_growth_20261011'))
import ancestry_probe as ancestry

loop = ancestry.loop
prior = ancestry.prior
OLD_ROOT = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011')
ALGORITHM = 'EXISTING_ANCESTRY_FIELD_SELECTED_WALL_CORRIDORS_V1'
# G3 is declared for later direction reversal; it is not run without --stage 3.
EVENTS = {
    2: [dict(name='LOWER_FRONT_WALL', centre=.29, span=.17, theta=np.pi/2, sweep=-.32),
        dict(name='UPPER_SIDE_SHOULDER', centre=.74, span=.15, theta=0., sweep=.32)],
    3: [dict(name='LOWER_SIDE_WALL', centre=.28, span=.17, theta=0., sweep=.38),
        dict(name='UPPER_FRONT_SHOULDER', centre=.75, span=.15, theta=np.pi/2, sweep=-.38)],
}
GUIDE_RANGE = .82
CORE_INNER = .07
CORE_OUTER = .17
ANGLE_RANGE = .52


def smoothstep(t):
    t = np.clip(t, 0., 1.)
    return t*t*(3.-2.*t)


def guide_curves(source_xyz, source_chart, generation):
    """Nearest material samples on the actual legacy surface, no new shape."""
    canonical = source_chart.copy()
    canonical[:, 1:] = np.abs(canonical[:, 1:])
    theta = np.arctan2(canonical[:, 2], canonical[:, 1])
    tree = cKDTree(np.column_stack([canonical[:, 0], theta/(np.pi/2)]))
    guides = []
    for event in EVENTS[generation]:
        s = np.linspace(event['centre']-event['span'], event['centre']+event['span'], 65)
        t = (s-event['centre'])/event['span']
        angle = event['theta'] + event['sweep']*np.cos(t*np.pi/2)
        _, indices = tree.query(np.column_stack([s, angle/(np.pi/2)]))
        # Repeated material samples are removed, retaining their order.
        keep = np.r_[True, indices[1:] != indices[:-1]]
        indices = indices[keep]
        points = source_xyz[indices].copy()
        points[:, :2] = np.abs(points[:, :2])
        keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1)>1e-12]
        points, indices = points[keep], indices[keep]
        if len(points) < 2:
            raise ValueError('Legacy surface guide has no nonzero segments.')
        segments = np.column_stack([np.arange(len(points)-1), np.arange(1, len(points))])
        guides.append(dict(event=event, points=points, segments=segments, source_indices=indices))
    return guides


def corridor_weights(xyz, chart, guides):
    """Independent height/direction gates and compact physical distance."""
    query = xyz.copy()
    query[:, :2] = np.abs(query[:, :2])
    s = chart[:, 0]
    angle = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    combined = np.zeros(len(xyz))
    protection = np.zeros(len(xyz))
    payload = {}
    for index, guide in enumerate(guides):
        event = guide['event']
        t = (s-event['centre'])/event['span']
        desired = event['theta'] + event['sweep']*np.cos(np.clip(t, -1., 1.)*np.pi/2)
        height_gate = 1. - smoothstep((np.abs(t)-.68)/.32)
        direction_gate = 1. - smoothstep(np.abs(angle-desired)/ANGLE_RANGE)
        distance = loop.curves.closest_segment_distance(query, guide['points'], guide['segments'])
        support = 1.-smoothstep(distance/GUIDE_RANGE)
        legacy = 1.-smoothstep((distance-CORE_INNER)/(CORE_OUTER-CORE_INNER))
        zone = height_gate*direction_gate
        activation = zone*support
        combined = np.maximum(combined, activation)
        protection = np.maximum(protection, zone*legacy)
        payload[f'guide_{index}_distance'] = distance
        payload[f'guide_{index}_zone'] = zone
    factor = 1. - .95*protection
    factor[protection >= 1.-1e-12] = 0.
    weights = combined*factor
    # Caps and endpoint rings are outside these finite axial windows naturally.
    payload.update(corridor_activation=combined, legacy_guide_weight=protection,
                   legacy_factor=factor, final_corridor_weight=weights)
    return weights, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/directional_growth_20261012'))
    parser.add_argument('--stage', type=int, choices=(2, 3), default=2)
    args = parser.parse_args()
    root = args.root.resolve()
    legacy = OLD_ROOT/'ANCESTRY_STAGED'/'G01'
    source = legacy if args.stage == 2 else root/'CORRIDOR'/'G02'
    folder = root/'CORRIDOR'/f'G{args.stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing candidate preserved: '+str(folder))
    mesh, chart = ancestry.load_control(source/'control_quad.npz')
    legacy_mesh, legacy_chart = ancestry.load_control(legacy/'control_quad.npz')
    guides = guide_curves(legacy_mesh.xyz, legacy_chart, args.stage)
    incoming, incoming_faces = mesh.xyz.copy(), mesh.faces.copy()
    nv = len(incoming)
    out, op = ancestry.task36_growth.step(mesh, **ancestry.RECIPE)
    edges = op['input_edges']
    chart_out = np.concatenate([chart, chart[edges].mean(1), chart[incoming_faces].mean(1)])
    interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[incoming_faces].mean(1)])
    if len(out.faces) != 4*len(incoming_faces) or not np.array_equal(out.xyz[:nv], incoming):
        raise ValueError('Existing one-split / old-vertex retention invariant failed.')
    pairs = prior.helpers.existing.symmetry(chart_out)
    raw_task36 = out.xyz-interpolated
    prior.helpers.existing.reflect(raw_task36, chart_out, pairs)
    placement_weight, placement_masks = corridor_weights(interpolated, chart_out, guides)
    applied_task36 = raw_task36*placement_weight[:, None]
    prior.helpers.existing.reflect(applied_task36, chart_out, pairs)
    out.xyz = interpolated+applied_task36
    post_task36 = out.xyz.copy()
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = (4, 8, 18)[args.stage-1]
    trees, fieldpath = prior.helpers.outside_trees(cfg, OLD_ROOT)
    cache = json.loads((Path(fieldpath)/'field.json').read_text(encoding='utf8'))['parameters']
    if cache['iterations'] != cfg['iterations']:
        raise ValueError('Field bank does not match the active classifier.')
    raw_output, field_payload, field_log = loop.apply_field(out.xyz, out.faces, chart_out,
        cfg, trees, .55, (.35, .28, .22)[args.stage-1], args.stage)
    raw_field = raw_output-post_task36
    field_weight, field_masks = corridor_weights(post_task36, chart_out, guides)
    applied_field = raw_field*field_weight[:, None]
    prior.helpers.existing.reflect(applied_field, chart_out, pairs)
    out.xyz = post_task36+applied_field
    physical = ancestry.task36_growth.native(out)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart_out, chart_out[out.faces].mean(1)])
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    _, errors, matches = prior.reflection_state(physical.xyz, triangles, physical_chart)
    area = float(actual.area_faces.min())
    if not np.isfinite(physical.xyz).all() or not actual.is_watertight or not actual.is_winding_consistent or area <= 1e-12:
        raise ValueError('Quick integrity failed; no repair or threshold change.')
    old_movement = np.linalg.norm(out.xyz[:nv]-incoming, axis=1)
    held = field_weight[:nv] == 0.
    if held.any() and not np.array_equal(out.xyz[:nv][held], incoming[held]):
        raise ValueError('Inactive old controls unexpectedly moved.')
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder/'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder/'checkpoint.npz', xyz=physical.xyz, faces=triangles, chart=physical_chart,
        classes=physical.classes, rest=physical.rest, anchors=physical.anchors, generation=np.array(physical.generation))
    np.savez_compressed(folder/'control_quad.npz', xyz=out.xyz, faces=out.faces, chart=chart_out,
        classes=out.classes, rest=out.rest, anchors=out.anchors, generation=np.array(out.generation))
    field_payload['raw_field_displacement'] = raw_field
    field_payload['applied_field_displacement'] = applied_field
    field_payload['field_displacement'] = applied_field
    field_payload['displacement'] = applied_field
    field_payload['raw_finite_inside'] = field_payload['finite_inside'].copy()
    field_payload['raw_field_active'] = field_payload['field_active'].copy()
    field_payload['field_region_eligible'] = field_weight > 0.
    field_payload['field_active'] = np.linalg.norm(applied_field, axis=1) > 1e-12
    np.savez_compressed(folder/'operation_fields.npz', **op, **field_payload,
        interpolated_xyz=interpolated, raw_task36_displacement=raw_task36,
        applied_task36_displacement=applied_task36, post_task36_xyz=post_task36, final_xyz=out.xyz,
        **{'placement_'+k:v for k,v in placement_masks.items()}, **{'field_'+k:v for k,v in field_masks.items()})
    np.savez_compressed(folder/'legacy_guides.npz',
        **{f'guide_{i}_{k}':g[k] for i,g in enumerate(guides) for k in ('points','segments','source_indices')})
    actual.export(folder/'gate.ply')
    shutil.copy2(__file__, folder/'corridor_recipe.py')
    field_log['raw_field_moved_vertices'] = field_log['field_moved_vertices']
    field_log['field_moved_vertices'] = int((np.linalg.norm(applied_field,axis=1)>1e-12).sum())
    field_log['maximum_raw_field_step'] = field_log['maximum_field_step']
    field_log['maximum_field_step'] = float(np.linalg.norm(applied_field,axis=1).max())
    metadata = dict(candidate='CORRIDOR', stage=f'G{args.stage:02}', algorithm=ALGORITHM,
        source=str(source/'checkpoint.npz'), parent=str(source/'checkpoint.npz'), legacy_source=str(legacy/'control_quad.npz'),
        operation='One existing Task36 ancestry split and finite field pass, both restricted to selected actual legacy-wall corridors',
        task36_recipe=ancestry.RECIPE, events=EVENTS[args.stage], field_recipe=cfg, field_cache=fieldpath, field_step=field_log,
        guide_range=GUIDE_RANGE, angle_range=ANGLE_RANGE, core_inner=CORE_INNER, core_outer=CORE_OUTER, activation_floor=0.,
        guide_provenance='Nearest material samples from the actual G1 control surface; fixed world polylines, not rendered geometry',
        memory_scope='Narrow authored guide-core attenuation and inactive old control position retention; no automatic crease detection or dihedral preservation guarantee',
        field_payload_scope='finite_inside/raw_finite_inside/raw_field_active describe the unmasked classifier; field_region_eligible is the corridor mask and field_active records actual nonzero applied movement.',
        inherited_growth_cycles=1, growth_cycles_total=args.stage, new_growth_cycles=args.stage-1,
        field_iterations=cfg['iterations'], internal_iteration_schedule=[4,8,18],
        subdivision_passes_total=args.stage, field_passes_total=args.stage, quad_splits_per_cycle=1,
        ancestry_eligible_faces=int(op['eligible'].sum()), source_control_vertices=nv, source_control_quads=len(incoming_faces),
        control_vertices=len(out.xyz), control_quads=len(out.faces), physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        placement_active_fraction=float((placement_weight>0.).mean()), field_region_active_fraction=float((field_weight>0.).mean()),
        maximum_task36_step=float(np.linalg.norm(applied_task36,axis=1).max()),
        maximum_raw_task36_step=float(np.linalg.norm(raw_task36,axis=1).max()),
        old_task36_vertex_maximum_step=float(np.linalg.norm(applied_task36[:nv],axis=1).max()),
        old_controls_zero_weight_held=int(held.sum()),
        old_controls_exactly_held=int(np.all(out.xyz[:nv] == incoming, axis=1).sum()),
        old_controls_field_moved=int((old_movement>1e-12).sum()),
        previous_control_vertex_max_movement=float(old_movement.max()),
        geometry_outside_region_note='Inactive old control vertices stay exact; splitting nonplanar quads and replacing mean fans can still change the physical interpolated surface outside active corridors.',
        minimum_triangle_area=area, minimum_area_threshold=1e-12, minimum_area_pass=True,
        geometric_reflection_error=errors, reflected_triangle_sets_identical=matches,
        components=int(actual.body_count), watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        separate_geometric_smoothing=False, CC_standard_averaging_gain=0., authored_return=False, shape_warp=False,
        task36_terminal_policy='Inherited plane_only policy remains; no new end condition.',
        provenance='Existing CHESHIRE operators with selected-region and guide memory composition. Not IAAC original code or a physical folding solver.',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED')
    prior.base.dump(folder/'generation.json', metadata)
    print('GENERATED CORRIDOR', args.stage, 'active placement',metadata['placement_active_fraction'],
        'field',metadata['field_region_active_fraction'],'held old',metadata['old_controls_exactly_held'],
        'max placement',metadata['maximum_task36_step'],'max field',field_log['maximum_field_step'], flush=True)


if __name__ == '__main__':
    main()
