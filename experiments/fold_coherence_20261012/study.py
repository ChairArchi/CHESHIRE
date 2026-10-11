"""Two finite design compositions from actual G2, stopping at G5.

Existing Task36 components, PCHIP returns and sampled finite Mandelbulb field.
No new solver, remeshing, XYZ smoothing, random texture or arbitrary-input claim.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('coherence_existing_transfer', HERE.parent/'fold_transfer_20261012/study.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
import fold_profile as profile

CFG = json.loads((HERE/'recipe.json').read_text(encoding='utf8'))
ROOT = Path('E:/CHESHIRE_DATA/fold_coherence_20261012')
SOURCES = dict(SPAN=Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G02'),
    COUNTER=Path('E:/CHESHIRE_DATA/fold_transfer_20261012/COUNTER/G02'))


def tags_for(chart, bank):
    mask = np.zeros(len(chart))
    for event in bank:
        scale = event['span']/.12
        mask = np.maximum(mask, profile.profile_mask(chart, [event],
            inner=CFG['memory_inner_at_span_012']*scale,
            outer=CFG['memory_outer_at_span_012']*scale))
    return mask


def children(parents, stage):
    rule = CFG['first_child' if stage == 3 else 'later_child']
    events = []
    for i, parent in enumerate(parents):
        event = dict(parent)
        event.update(id=f'G{stage}_FLOW_CHILD_OF_'+parent['id'], mirror=False,
            height=parent['height']+rule['height_offsets'][i % 2]*parent['span'],
            direction=parent['direction']+rule['direction_offsets'][i % 2]*parent['overlap_width'],
            span=parent['span']*rule['span_scale'],
            overlap_width=parent['overlap_width']*rule['width_scale'],
            sweep=parent['sweep']*rule['sweep_scale'],
            return_depth=parent['return_depth']*rule['return_scale'])
        for key in ('expansion', 'constriction', 'reexpansion'):
            event[key] = parent[key]*rule['radial_scale']
        event.update(bend_height=.05*event['span']/.12, sweep_span=.32*event['span']/.12)
        events.append(event)
    return events


def save(folder, mesh, chart, tags, meta, arrays):
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved: '+str(folder))
    physical = t.growth.native(mesh)
    triangles = physical.faces[:, :3]
    pchart = np.concatenate([chart, t.face_values(mesh, chart)])
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    _, errors, matches = t.prior.reflection_state(physical.xyz, triangles, pchart)
    area = float(actual.area_faces.min())
    quick = dict(finite=bool(np.isfinite(physical.xyz).all()), components=int(actual.body_count),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        minimum_triangle_area=area, minimum_area_threshold=1e-12,
        geometric_reflection_error=errors, reflected_triangle_sets_identical=matches)
    passed = (quick['finite'] and quick['components'] == 1 and quick['watertight']
        and quick['winding_consistent'] and area > 1e-12 and max(errors) < 1e-9 and all(matches))
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
        generation=np.array(mesh.generation), surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(folder/'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder/'checkpoint.npz', xyz=physical.xyz, faces=triangles,
        chart=pchart, generation=np.array(mesh.generation))
    np.savez_compressed(folder/'operation_fields.npz', **arrays)
    actual.export(folder/'column.ply')
    meta.update(stage=folder.name, composition_recipe=meta.get('composition_recipe', CFG), physical_vertices=len(physical.xyz),
        physical_triangles=len(triangles), control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
        subdivision_passes_total=mesh.generation, surface=mesh.surface,
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED',
        original_operators_modified=False, separate_geometric_smoothing=False,
        feature_memory_scope='Authored material-profile tags only; no fold-angle or mechanical memory', **quick)
    (folder/'generation.json').write_text(json.dumps(meta, indent=2), encoding='utf8')
    for name in ('study.py', 'recipe.json', 'fold_profile.py'):
        shutil.copy2(HERE/name, folder/name)
    print('GENERATED', str(folder), len(triangles), 'area', area, 'sym', errors,
        meta['quick_integrity'], flush=True)
    if not passed:
        raise ValueError('Quick failure retained; no repair or relaxed threshold.')


def generate(root, variant, case, stage):
    source = SOURCES[case] if stage == 3 else root/variant/case/f'G{stage-1:02}'
    folder = root/variant/case/f'G{stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved: '+str(folder))
    mesh, chart, tags = t.load(source)
    if mesh.generation != stage-1:
        raise ValueError('Wrong actual control generation.')
    if stage == 3:
        bank = [dict(e) for e in t.overlap.EVENTS]
        tags = tags_for(chart, bank)  # same fresh registration on both G2 inputs
        parents = bank
    else:
        previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
        if previous['quick_integrity'] != 'PASS':
            raise ValueError('Failed parent remains preserved.')
        bank = previous['event_bank']
        parents = previous['new_authored_events']
        tags = np.maximum(tags, tags_for(chart, bank))
    inherited_core = tags >= 1-1e-12
    pre_event = mesh.xyz.copy()
    events = children(parents, stage) if variant == 'FLOW' else []
    raw_return = sum((profile.reflected_event(chart, e) for e in events), np.zeros_like(mesh.xyz))
    returned = raw_return*(1-tags)[:, None]
    t.prior.helpers.existing.reflect(returned, chart, t.prior.helpers.existing.symmetry(chart))
    mesh.xyz += returned
    new_tags = tags_for(chart, events)*(np.linalg.norm(returned, axis=1)>1e-12)
    tags = np.maximum(tags, new_tags)
    bank = list(bank)+events
    post_event = mesh.xyz.copy()
    refined, outchart, outtags, inactive_op = t.memory.refine(mesh, chart, tags)
    outtags = np.maximum(outtags, tags_for(outchart, bank))
    stencil, normal = CFG['task36_gains'][str(stage)]
    recipe = dict(t.ancestry.RECIPE, stencil_gain=stencil, normal_gain=normal, surface='vf')
    out, op = t.growth.step(mesh, **recipe)
    if not np.array_equal(out.faces, refined.faces):
        raise ValueError('Active and inactive existing split topology differs.')
    raw_placement = out.xyz-refined.xyz
    placement = raw_placement*(1-outtags)[:, None]
    t.prior.helpers.existing.reflect(placement, outchart, t.prior.helpers.existing.symmetry(outchart))
    out.xyz = refined.xyz+placement
    pre_field = out.xyz.copy()
    field_xyz, payload, field_log = t.field(out, outchart, CFG['field_iterations'],
        CFG['field_budgets'][str(stage)], CFG['target_factors'][str(stage)])
    raw_field = field_xyz-pre_field
    applied = raw_field*(1-outtags)[:, None]
    t.prior.helpers.existing.reflect(applied, outchart, t.prior.helpers.existing.symmetry(outchart))
    out.xyz = pre_field+applied
    core = outtags >= 1-1e-12
    save(folder, out, outchart, outtags,
        dict(candidate=variant, input_case=case, parent=str(source), source_g2=str(SOURCES[case]),
            input_source=f'E:/CHESHIRE_DATA/fold_transfer_20261012/inputs/{case}/G00',
            operation='Existing scaled continuous returns, reduced Task36 components, tag-only finite field',
            task36_recipe=recipe, new_authored_events=events, event_bank=bank, field=field_log,
            field_passes_total=stage, added_field_passes=1, field_memory_rule='1-tags on all old/new controls; no blanket old-point pin',
            maximum_return_step=float(np.linalg.norm(returned, axis=1).max()),
            inherited_core_count=int(inherited_core.sum()),
            inherited_core_return_maximum=float(np.linalg.norm(returned[inherited_core], axis=1).max()) if inherited_core.any() else None,
            maximum_placement_step=float(np.linalg.norm(placement, axis=1).max()),
            maximum_field_step=float(np.linalg.norm(applied, axis=1).max()),
            field_moved_controls=int((np.linalg.norm(applied, axis=1)>1e-12).sum()),
            tag_core_count=int(core.sum()), tag_core_field_maximum=float(np.linalg.norm(applied[core], axis=1).max()) if core.any() else None,
            note='Parameters are shared across both actual inputs. Declared geometric returns, not fractal-emergent or physical folds.'),
        dict(pre_event_xyz=pre_event, post_event_xyz=post_event, raw_return_displacement=raw_return,
            applied_return_displacement=returned, pre_placement_xyz=refined.xyz,
            raw_placement_displacement=raw_placement, applied_placement_displacement=placement,
            input_edges=inactive_op['input_edges'], parent_face=inactive_op['parent_face'],
            pre_field_xyz=pre_field, raw_field_displacement=raw_field,
            applied_field_displacement=applied, carried_tags=outtags, field_weight=1-outtags,
            canonical_nearest_outside_target=payload['canonical_nearest_outside_target'],
            finite_inside=payload['finite_inside']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--stage', type=int, choices=(3, 4, 5), required=True)
    p.add_argument('--variants', nargs='+', choices=('RESERVE', 'FLOW'), default=['RESERVE', 'FLOW'])
    p.add_argument('--cases', nargs='+', choices=('SPAN', 'COUNTER'), default=['SPAN', 'COUNTER'])
    args = p.parse_args()
    for variant in args.variants:
        for case in args.cases:
            generate(args.root, variant, case, args.stage)
