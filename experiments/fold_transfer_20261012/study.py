"""Bounded transfer test of existing return/refinement/field operations.

Two real G0 masses, one shared recipe. G4 compares a matched field pass with
and without inherited-point/feature protection. No physical origami, new
fractal equation, automatic crease extraction or general mesh engine.
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
sys.path.insert(0, str(HERE.parent/'directional_growth_20261012'))
import inputs
import memory
import overlap_probe as overlap

ancestry = overlap.ancestry
prior = ancestry.prior
growth = ancestry.task36_growth
CFG = json.loads((HERE/'recipe.json').read_text(encoding='utf8'))
OLD_BASE = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
OLD_FIELDS = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011')
TREES = {}


def load(folder):
    mesh, chart = ancestry.load_control(folder/'control_quad.npz')
    with np.load(folder/'control_quad.npz', allow_pickle=False) as data:
        mesh.surface = str(data['surface']) if 'surface' in data else 'mean'
        tags = data['memory'].copy() if 'memory' in data else np.zeros(len(mesh.xyz))
    return mesh, chart, tags


def face_values(mesh, values):
    q = mesh.faces
    result = values[q].mean(1)
    if getattr(mesh, 'surface', 'mean') == 'vf':
        cls = mesh.classes[q]
        iv, jf = np.argmax(cls == 0, axis=1), np.argmax(cls == 2, axis=1)
        valid = ((cls == 0).sum(1) == 1) & ((cls == 1).sum(1) == 2)
        valid &= ((cls == 2).sum(1) == 1) & ((iv+2) % 4 == jf)
        rows = np.arange(len(q))
        result[valid] = ((values[q[rows, iv]]+values[q[rows, jf]])/2)[valid]
    return result


def tag_mask(chart, events):
    return memory.feature_mask(chart, events, inner=CFG['memory_inner'], outer=CFG['memory_outer'])


def events_from(parents, stage):
    rule = CFG[f'g{stage}_rule']
    result = []
    for i, parent in enumerate(parents):
        event = dict(parent)
        event.update(id=f'G{stage}_CHILD_OF_'+parent['id'], mirror=False,
            height=parent['height']+rule['height_offset_in_parent_spans'][i % 2]*parent['span'],
            direction=parent['direction']+rule['direction_offset_in_parent_widths'][i % 2]*parent['overlap_width'],
            span=parent['span']*rule['span_scale'],
            overlap_width=parent['overlap_width']*rule['width_scale'],
            sweep=parent['sweep']*rule['sweep_scale'],
            return_depth=parent['return_depth']*rule['return_scale'])
        for key in ('expansion', 'constriction', 'reexpansion'):
            event[key] = parent[key]*rule['radial_scale']
        result.append(event)
    return result


def reflected_event(chart, event):
    canonical = chart.copy()
    canonical[:, 1:] = np.abs(canonical[:, 1:])
    delta = prior.smooth_deep.smooth_event(canonical, event)
    delta[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
    prior.helpers.existing.reflect(delta, chart, prior.helpers.existing.symmetry(chart))
    return delta


def field(mesh, chart, iterations, budget, factor):
    cfg = prior.field_recipe('n4', CFG['field_fraction'])
    cfg['iterations'] = iterations
    if iterations not in TREES:
        TREES[iterations] = prior.helpers.outside_trees(cfg, OLD_FIELDS)
    trees, cache = TREES[iterations]
    xyz, payload, log = ancestry.loop.apply_field(mesh.xyz, mesh.faces, chart,
        cfg, trees, CFG['field_fraction'], budget, factor)
    return xyz, payload, dict(log, cache=cache, recipe=cfg)


def save(folder, mesh, chart, tags, meta, arrays):
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing stage preserved: '+str(folder))
    physical = growth.native(mesh)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart, face_values(mesh, chart)])
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    _, errors, matches = prior.reflection_state(physical.xyz, triangles, physical_chart)
    area = float(actual.area_faces.min())
    quick = dict(finite=bool(np.isfinite(physical.xyz).all()),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        components=int(actual.body_count), minimum_triangle_area=area,
        minimum_area_threshold=1e-12, minimum_area_pass=area > 1e-12,
        geometric_reflection_error=errors, reflected_triangle_sets_identical=matches)
    passed = quick['finite'] and quick['watertight'] and quick['winding_consistent']
    passed &= quick['components'] == 1 and quick['minimum_area_pass'] and max(errors) < 1e-9 and all(matches)
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces, chart=chart,
        classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
        generation=np.array(mesh.generation), surface=np.array(mesh.surface), memory=tags)
    np.savez_compressed(folder/'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder/'checkpoint.npz', xyz=physical.xyz, faces=triangles,
        chart=physical_chart, generation=np.array(mesh.generation))
    np.savez_compressed(folder/'operation_fields.npz', **arrays)
    actual.export(folder/'column.ply')
    for name in ('study.py', 'memory.py', 'recipe.json'):
        shutil.copy2(HERE/name, folder/name)
    meta.update(candidate=folder.parent.name, stage=folder.name,
        shared_recipe=CFG, surface=mesh.surface,
        control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
        physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        subdivision_passes_total=mesh.generation,
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED',
        feature_memory_scope=meta.get('feature_memory_scope',
            'Material-profile tags and inherited control points; no dihedral-angle or mechanical folding guarantee'),
        separate_geometric_smoothing=False, original_operators_modified=False, **quick)
    (folder/'generation.json').write_text(json.dumps(meta, indent=2), encoding='utf8')
    print('GENERATED', str(folder), len(triangles), 'area', area, 'sym', errors,
          meta['quick_integrity'], flush=True)
    if not passed:
        raise ValueError('Quick geometry failure preserved; no repair or relaxed threshold.')


def base(root, case, source, reuse_span=False):
    if reuse_span:
        # This is the exact source and recipe already executed for OVERLAP.
        # Reuse it instead of repeating a large successful reconstruction.
        return OLD_BASE
    mesh, chart, tags = load(source)
    mesh.anchors[:, 0] = np.arange(len(mesh.faces))
    for stage in (1, 2, 3):
        folder = root/case/f'G{stage:02}'
        if (folder/'generation.json').exists():
            saved = json.loads((folder/'generation.json').read_text(encoding='utf8'))
            if saved['quick_integrity'] != 'PASS' or saved['shared_recipe'] != CFG or Path(saved['input_source']).resolve() != source.resolve():
                raise ValueError('Different or failed existing source is preserved.')
            mesh, chart, tags = load(folder)
            continue
        before_event = mesh.xyz.copy()
        if stage == 2:
            mesh.xyz += sum((reflected_event(chart, e) for e in overlap.EVENTS), np.zeros_like(mesh.xyz))
            tags = np.maximum(tags, tag_mask(chart, overlap.EVENTS))
        incoming, faces = mesh.xyz.copy(), mesh.faces.copy()
        out, op = growth.step(mesh, **ancestry.RECIPE)
        edges = op['input_edges']
        chart_out = np.concatenate([chart, chart[edges].mean(1), chart[faces].mean(1)])
        tags_out = np.concatenate([tags, tags[edges].mean(1), tags[faces].mean(1)])
        interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[faces].mean(1)])
        delta = out.xyz-interpolated
        prior.helpers.existing.reflect(delta, chart_out, prior.helpers.existing.symmetry(chart_out))
        out.xyz = interpolated+delta
        pre_field = out.xyz.copy()
        out.xyz, payload, field_log = field(out, chart_out, CFG['field_iterations'][stage-1],
            CFG['field_budgets'][stage-1], stage)
        save(folder, out, chart_out, tags_out,
            dict(input_case=case, input_source=str(source), parent=str(source if stage == 1 else folder.parent/f'G{stage-1:02}'),
                operation='Same OVERLAP Task36/finite-field recipe from a different actual G0; two existing returns before G2 only',
                task36_recipe=ancestry.RECIPE, authored_events=overlap.EVENTS if stage == 2 else [],
                field_passes_total=stage, field=field_log,
                event_bank=overlap.EVENTS if stage >= 2 else [],
                memory_applied=False, memory_policy='Tag lineage carried for later comparison; baseline G1-G3 field remains unchanged'),
            dict(pre_event_xyz=before_event, post_event_xyz=incoming,
                pre_field_xyz=pre_field, task36_displacement=delta, inherited_tags=tags_out, **payload))
        mesh, chart, tags = out, chart_out, tags_out
    return root/case/'G03'


def late(root, case, source, stage, label=None, input_source=None, save_refinement_control=False):
    mesh, chart, tags = load(source)
    previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
    bank = previous.get('event_bank', overlap.EVENTS)
    if stage == 4:
        bank = overlap.EVENTS
        parents = overlap.EVENTS
        # Both baselines were unprotected. Register their legacy bank at the
        # same G3 chart state; do not mix carried baseline tags on one input
        # with freshly registered tags on the reused input.
        tags = tag_mask(chart, bank)
    else:
        parents = previous['new_authored_events']
    tags = np.maximum(tags, tag_mask(chart, bank))
    nv = len(mesh.xyz)
    refined, chart_out, inherited_tags, refine_op = memory.refine(mesh, chart, tags)
    inherited_tags = np.maximum(inherited_tags, tag_mask(chart_out, bank))
    inherited_field_passes = previous['field_passes_total']
    if save_refinement_control:
        save(root/(label or case)/'REFINED_ONLY'/f'G{stage:02}', refined, chart_out, inherited_tags,
            dict(input_case=case, input_source=str(input_source or previous.get('input_source')),
                parent=str(source), operation='Inactive native VF refinement only; resolution control with no geometric deformation',
                field_passes_total=inherited_field_passes, added_field_passes=0,
                event_bank=bank, new_authored_events=[], memory_applied=False,
                note='More triangles alone preserve the incoming geometric surface; this is not a new folding pass'),
            dict(input_edges=refine_op['input_edges'], parent_face=refine_op['parent_face']))
    new_events = events_from(parents, stage)
    raw_return = sum((reflected_event(chart_out, e) for e in new_events), np.zeros_like(refined.xyz))
    return_delta = raw_return*(1-inherited_tags)[:, None]
    prior.helpers.existing.reflect(return_delta, chart_out, prior.helpers.existing.symmetry(chart_out))
    pre_return = refined.xyz.copy()
    refined.xyz += return_delta
    new_tags = tag_mask(chart_out, new_events)*(np.linalg.norm(return_delta, axis=1) > 1e-12)
    tags_out = np.maximum(inherited_tags, new_tags)
    event_bank = list(bank)+new_events
    fields_common = dict(pre_return_xyz=pre_return, raw_return_displacement=raw_return,
        applied_return_displacement=return_delta, inherited_tags=inherited_tags,
        new_feature_tags=new_tags, carried_tags=tags_out,
        input_edges=refine_op['input_edges'], parent_face=refine_op['parent_face'])
    core = inherited_tags >= 1-1e-12
    meta = dict(input_case=case, input_source=str(input_source or previous.get('input_source', root/'inputs'/case/'G00')), parent=str(source),
        operation='Existing surface-preserving inactive Task36 split, derived continuous PCHIP return events, then matched finite field',
        new_authored_events=new_events, event_bank=event_bank,
        rule='Same parent-to-child event rule for both inputs; no case-specific event or coordinate tuning',
        inherited_core_count=int(core.sum()),
        inherited_core_return_maximum=float(np.linalg.norm(return_delta[core], axis=1).max()) if core.any() else None,
        maximum_return_step=float(np.linalg.norm(return_delta, axis=1).max()),
        note='Returns are authored parametric geometric sequences, not fractal-emergent folds or origami mechanics',
        field_passes_total=inherited_field_passes, added_field_passes=0, memory_applied=True,
        sampling='G3 remains mean; one inactive split switches children to native VF. Subsequent VF splits sample the inherited V/F diagonal. No change to the input surface before displacement.')
    folder = root/(label or case)/'RETURN_ONLY'/f'G{stage:02}'
    save(folder, refined, chart_out, tags_out, dict(meta), fields_common)
    post_return = refined.xyz.copy()
    raw_xyz, payload, field_log = field(refined, chart_out, 18, CFG[f'g{stage}_field_budget'], CFG['target_factor_late'])
    raw_delta = raw_xyz-post_return
    variants = ('UNPROTECTED', 'PROTECTED') if stage == 4 else ('PROTECTED',)
    for variant in variants:
        weight = np.ones(len(refined.xyz))
        if variant == 'PROTECTED':
            weight = 1-tags_out
            weight[:nv] = 0
        applied = raw_delta*weight[:, None]
        prior.helpers.existing.reflect(applied, chart_out, prior.helpers.existing.symmetry(chart_out))
        refined.xyz = post_return+applied
        core = tags_out >= 1-1e-12
        log = dict(meta, field=field_log, field_passes_total=inherited_field_passes+1, added_field_passes=1,
            protected_field=variant == 'PROTECTED',
            field_memory_rule='All inherited controls fixed during field; propagated and new feature tags attenuate newborn field vectors' if variant == 'PROTECTED' else 'No field memory; exact same pre-field geometry and raw field queries',
            fully_protected_feature_count=int(core.sum()),
            raw_field_moved_core=int((np.linalg.norm(raw_delta[core], axis=1) > 1e-12).sum()),
            applied_field_moved_core=int((np.linalg.norm(applied[core], axis=1) > 1e-12).sum()),
            old_controls_field_maximum=float(np.linalg.norm(applied[:nv], axis=1).max()),
            raw_field_moved_controls=int((np.linalg.norm(raw_delta, axis=1) > 1e-12).sum()),
            applied_field_moved_controls=int((np.linalg.norm(applied, axis=1) > 1e-12).sum()),
            raw_field_maximum=float(np.linalg.norm(raw_delta, axis=1).max()),
            applied_field_maximum=float(np.linalg.norm(applied, axis=1).max()),
            feature_memory_scope='Point/tag protection during new operations; does not preserve dihedral angles or every point on a deformed face')
        arrays = dict(fields_common, **payload)
        arrays.update(pre_field_xyz=post_return, raw_field_displacement=raw_delta,
            applied_field_displacement=applied, field_weight=weight)
        save(root/(label or case)/variant/f'G{stage:02}', refined, chart_out, tags_out, log, arrays)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/fold_transfer_20261012'))
    parser.add_argument('--cases', nargs='+', choices=('SPAN', 'COUNTER'), default=['SPAN', 'COUNTER'])
    parser.add_argument('--stage', type=int, choices=(4, 5), default=4)
    parser.add_argument('--label', help='Output label only; one selected input. Does not alter the shared recipe.')
    parser.add_argument('--input', type=Path, help='Another actual G0 control_quad.npz folder on the same documented column chart/topology. No case-specific rule changes.')
    parser.add_argument('--name', help='Output name for --input; must be a single relative path part.')
    args = parser.parse_args()
    root = args.root.resolve()
    def valid_name(value):
        return bool(value) and value not in ('.', '..') and all(c.isascii() and (c.isalnum() or c in '_-') for c in value)
    if args.label and (len(args.cases) != 1 or not valid_name(args.label)):
        raise ValueError('One relative output label requires one input case.')
    if args.input:
        if not valid_name(args.name) or args.label:
            raise ValueError('--input requires one relative --name and no --label.')
        source = args.input.resolve()
        supplied, chart, _ = load(source)
        reference, expected_chart = inputs.seed.variation.carrier(inputs.CARRIER)
        if supplied.generation != 0 or supplied.surface != 'mean' or not np.array_equal(chart, expected_chart) or not np.array_equal(supplied.faces, reference.faces) or not np.array_equal(supplied.classes, reference.classes) or not np.array_equal(supplied.rest, reference.rest):
            raise ValueError('Input adapter scope is the documented unsplit column chart/topology, not arbitrary meshes.')
        baseline = base(root, args.name, source) if args.stage == 4 else root/args.name/'PROTECTED/G04'
        late(root, args.name, baseline, args.stage, input_source=source)
        return
    seeds = inputs.prepare(root)
    for case in args.cases:
        source = base(root, case, seeds[case], reuse_span=case == 'SPAN') if args.stage == 4 else root/(args.label or case)/'PROTECTED/G04'
        late(root, case, source, args.stage, args.label, input_source=seeds[case])


if __name__ == '__main__':
    main()
