"""Two narrow-direction authored returns before one existing growth cycle.

Finite design composition, not a new fold solver. Preserve ANCESTRY_STAGED
G1, add existing smooth_deep PCHIP events on its controls, then exactly one
Task36 split and the same escape-8 nearest-outside field. No XYZ smoothing,
posthoc vertex averaging, random texture or fractal-emergent-fold claim.
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
OLD = HERE.parent / 'fold_band_growth_20261011'
sys.path.insert(0, str(OLD))
spec = importlib.util.spec_from_file_location('overlap_preserved_ancestry', OLD / 'ancestry_probe.py')
ancestry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ancestry)
prior = ancestry.prior
RECIPE = ancestry.RECIPE.copy()
EVENTS = [
    dict(id='LOWER_DIAGONAL_RETURN', direction=.35, height=.39, span=.12,
         expansion=.48, constriction=.28, reexpansion=.38, return_depth=.72,
         overlap_width=.46, sweep=.28, mirror=False),
    dict(id='UPPER_CROSSING_RETURN', direction=1.18, height=.61, span=.12,
         expansion=.46, constriction=.26, reexpansion=.36, return_depth=.68,
         overlap_width=.46, sweep=.28, mirror=False),
]
ALGORITHM = 'EXISTING_OVERLAPPING_PCHIP_RETURN_TASK36_FIELD_G2_V1'
OLD_ROOT = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011')


def continue_g3(args):
    """One unchanged continuation; the G2 authored returns are NOT reapplied."""
    root = args.root.resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('Family must stay beneath the output root.')
    source = root / family / 'G02'
    folder = root / family / 'G03'
    incoming_meta = json.loads((source / 'generation.json').read_text(encoding='utf8'))
    if incoming_meta['quick_integrity'] != 'PASS':
        raise ValueError('Preserved failed G2 cannot silently become a successful continuation.')
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = 18
    signature = dict(algorithm=ALGORITHM + '_CONTINUATION_G3', source=str(source),
        origin_g1=incoming_meta['source'], stage=3, task36_recipe=RECIPE,
        field_recipe=cfg, fraction=.55, field_budget=.22, local_target_factor=3,
        new_authored_return_events=[])
    if folder.exists() and any(folder.iterdir()):
        saved = folder / 'generation.json'
        if not saved.exists() or json.loads(saved.read_text(encoding='utf8'))['signature'] != signature:
            raise FileExistsError('Different/incomplete G3 preserved: ' + str(folder))
        print('REUSED', str(folder), flush=True)
        return
    mesh, chart = ancestry.load_control(source / 'control_quad.npz')
    if mesh.generation != 2:
        raise ValueError('The continuation requires actual OVERLAP G2 controls.')
    incoming = mesh.xyz.copy()
    source_faces = mesh.faces.copy()
    nv = len(incoming)
    out, op = ancestry.task36_growth.step(mesh, **RECIPE)
    edges = op['input_edges']
    chart_out = np.concatenate([chart, chart[edges].mean(1), chart[source_faces].mean(1)])
    interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[source_faces].mean(1)])
    if len(out.xyz) != len(chart_out) or len(out.faces) != 4 * len(source_faces):
        raise ValueError('Unexpected existing Task36 birth order or split count.')
    if not np.array_equal(out.xyz[:nv], incoming):
        raise ValueError('Task36 vertex_memory=1 changed old controls before the field.')
    pairs = prior.helpers.existing.symmetry(chart_out)
    raw_task36 = out.xyz - interpolated
    applied_task36 = raw_task36.copy()
    prior.helpers.existing.reflect(applied_task36, chart_out, pairs)
    out.xyz = interpolated + applied_task36
    post_task36_xyz = out.xyz.copy()
    trees, field_cache = prior.helpers.outside_trees(cfg, OLD_ROOT)
    out.xyz, field_payload, field_log = ancestry.loop.apply_field(
        out.xyz, out.faces, chart_out, cfg, trees, .55, .22, 3)
    physical = ancestry.task36_growth.native(out)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart_out, chart_out[out.faces].mean(1)])
    _, symmetry_error, triangle_match = prior.reflection_state(physical.xyz, triangles, physical_chart)
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    minimum_area = float(actual.area_faces.min())
    checks = dict(finite=bool(np.isfinite(physical.xyz).all()),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        components=int(len(actual.split(only_watertight=False))),
        minimum_triangle_area=minimum_area, minimum_area_threshold=1e-12,
        minimum_area_pass=minimum_area > 1e-12,
        geometric_reflection_error=symmetry_error, reflected_triangle_sets_identical=triangle_match)
    quick_pass = checks['finite'] and checks['watertight'] and checks['winding_consistent'] and checks['minimum_area_pass']
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
        chart=physical_chart, classes=physical.classes, rest=physical.rest,
        anchors=physical.anchors, generation=np.array(physical.generation))
    np.savez_compressed(folder / 'control_quad.npz', xyz=out.xyz, faces=out.faces,
        chart=chart_out, classes=out.classes, rest=out.rest, anchors=out.anchors,
        generation=np.array(out.generation))
    np.savez_compressed(folder / 'operation_fields.npz', **op, **field_payload,
        incoming_g2_xyz=incoming, interpolated_xyz=interpolated,
        raw_task36_displacement=raw_task36, applied_task36_displacement=applied_task36,
        post_task36_xyz=post_task36_xyz, post_field_xyz=out.xyz)
    actual.export(folder / 'gate.ply')
    shutil.copy2(__file__, folder / 'overlap_recipe.py')
    metadata = dict(signature=signature, candidate=args.name, stage='G03',
        source=str(source / 'checkpoint.npz'), parent=str(source / 'checkpoint.npz'),
        origin_g1=incoming_meta['source'],
        operation='Actual OVERLAP G2 continuation: exactly one existing Task36 split and finite escape-18 field; no new authored return',
        cycle_order=['Task36_coupled_split', 'finite_nearest_outside_field'],
        new_authored_return_events=0,
        inherited_authored_return_provenance=incoming_meta['authored_return_events'],
        return_policy='G2 source-control deformations are inherited as actual geometry; no repeat, amplification or new return at G3',
        task36_recipe=RECIPE, task36_maximum_step=float(np.linalg.norm(applied_task36, axis=1).max()),
        ancestry_eligible_faces=int(op['eligible'].sum()), incoming_faces=len(source_faces),
        field_recipe=cfg, field_step=field_log, field_cache=field_cache,
        field_iterations=18, internal_iteration_schedule=[4, 8, 18],
        field_passes_total=3, subdivision_passes_total=3, growth_cycles_total=3,
        new_quad_splits_this_branch=2,
        step_budget_scope='The .22 budget applies to field movement only; Task36 placement is separate',
        physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        control_vertices=len(out.xyz), control_quads=len(out.faces),
        feature_memory=False, CC_standard_averaging_gain=0., separate_geometric_smoothing=False,
        task36_terminal_policy='Existing plane_only constraints retained; later field may move terminals',
        symmetry='Reflected new Task36 vectors and canonical field queries in X/Y; no posthoc XYZ averaging',
        physical_surface='Existing Task36 mean quad-centre fans after field; render-only fans are not next controls',
        source_status='CHESHIRE existing operators, not IAAC original executable formulas',
        quick_integrity='PASS' if quick_pass else 'FAILED_PRESERVED_NO_REPAIR',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED', **checks)
    prior.base.dump(folder / 'generation.json', metadata)
    print('GENERATED', args.name, 'G3', len(physical.xyz), len(triangles),
        'new_return', 0, 'task36_max', metadata['task36_maximum_step'],
        'minimum_area', minimum_area, 'symmetry', symmetry_error,
        'quick', metadata['quick_integrity'], flush=True)
    if not quick_pass:
        raise ValueError('Quick integrity failed; geometry and failure metadata preserved, no repair.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=OLD_ROOT / 'ANCESTRY_STAGED/G01')
    p.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/directional_growth_20261012'))
    p.add_argument('--name', default='OVERLAP')
    p.add_argument('--stage', choices=(2, 3), type=int, default=2,
        help='G2 authors two returns; G3 continues saved G2 once without adding returns.')
    args = p.parse_args()
    if args.stage == 3:
        continue_g3(args)
        return
    source = args.source.resolve()
    root = args.root.resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('Family must stay beneath the output root.')
    folder = root / family / 'G02'
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = 8
    signature = dict(algorithm=ALGORITHM, source=str(source), stage=2,
        return_events=EVENTS, return_order='On source G1 controls, before Task36 and field',
        task36_recipe=RECIPE, field_recipe=cfg, fraction=.55,
        field_budget=.28, local_target_factor=2)
    if folder.exists() and any(folder.iterdir()):
        saved = folder / 'generation.json'
        if not saved.exists() or json.loads(saved.read_text(encoding='utf8'))['signature'] != signature:
            raise FileExistsError('Different/incomplete existing candidate preserved: ' + str(folder))
        print('REUSED', str(folder), flush=True)
        return
    mesh, chart = ancestry.load_control(source / 'control_quad.npz')
    if mesh.generation != 1:
        raise ValueError('This bounded comparison requires the preserved G1 control state.')
    source_xyz = mesh.xyz.copy()
    source_faces = mesh.faces.copy()
    pairs = prior.helpers.existing.symmetry(chart)
    canonical = chart.copy()
    canonical[:, 1:] = np.abs(canonical[:, 1:])
    returns = []
    for event in EVENTS:
        displacement = prior.smooth_deep.smooth_event(canonical, event)
        displacement[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
        prior.helpers.existing.reflect(displacement, chart, pairs)
        returns.append(displacement)
    return_displacement = np.sum(returns, axis=0)
    mesh.xyz = source_xyz + return_displacement
    prior.reflection_state(mesh.xyz, mesh.faces, chart)
    authored_xyz = mesh.xyz.copy()
    nv = len(authored_xyz)
    out, op = ancestry.task36_growth.step(mesh, **RECIPE)
    edges = op['input_edges']
    chart_out = np.concatenate([chart, chart[edges].mean(1), chart[source_faces].mean(1)])
    interpolated = np.concatenate([authored_xyz, authored_xyz[edges].mean(1), authored_xyz[source_faces].mean(1)])
    if len(out.xyz) != len(chart_out) or len(out.faces) != 4 * len(source_faces):
        raise ValueError('Unexpected existing Task36 birth order or split count.')
    if not np.array_equal(out.xyz[:nv], authored_xyz):
        raise ValueError('Task36 vertex_memory=1 unexpectedly changed old controls before the field.')
    out_pairs = prior.helpers.existing.symmetry(chart_out)
    raw_task36 = out.xyz - interpolated
    applied_task36 = raw_task36.copy()
    prior.helpers.existing.reflect(applied_task36, chart_out, out_pairs)
    out.xyz = interpolated + applied_task36
    post_task36_xyz = out.xyz.copy()
    # Cache/query implementation is unchanged and reuses the old field root.
    trees, field_cache = prior.helpers.outside_trees(cfg, OLD_ROOT)
    out.xyz, field_payload, field_log = ancestry.loop.apply_field(
        out.xyz, out.faces, chart_out, cfg, trees, .55, .28, 2)
    physical = ancestry.task36_growth.native(out)
    triangles = physical.faces[:, :3]
    physical_chart = np.concatenate([chart_out, chart_out[out.faces].mean(1)])
    _, symmetry_error, triangle_match = prior.reflection_state(physical.xyz, triangles, physical_chart)
    actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
    minimum_area = float(actual.area_faces.min())
    checks = dict(finite=bool(np.isfinite(physical.xyz).all()),
        watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
        components=int(len(actual.split(only_watertight=False))),
        minimum_triangle_area=minimum_area, minimum_area_threshold=1e-12,
        minimum_area_pass=minimum_area > 1e-12,
        geometric_reflection_error=symmetry_error, reflected_triangle_sets_identical=triangle_match)
    quick_pass = checks['finite'] and checks['watertight'] and checks['winding_consistent'] and checks['minimum_area_pass']
    folder.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
    np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
        chart=physical_chart, classes=physical.classes, rest=physical.rest,
        anchors=physical.anchors, generation=np.array(physical.generation))
    np.savez_compressed(folder / 'control_quad.npz', xyz=out.xyz, faces=out.faces,
        chart=chart_out, classes=out.classes, rest=out.rest, anchors=out.anchors,
        generation=np.array(out.generation))
    np.savez_compressed(folder / 'operation_fields.npz', **op, **field_payload,
        pre_authored_source_xyz=source_xyz, post_authored_source_xyz=authored_xyz,
        source_return_displacement=return_displacement,
        source_return_event_0=returns[0], source_return_event_1=returns[1],
        source_chart=chart, interpolated_authored_xyz=interpolated,
        raw_task36_displacement=raw_task36, applied_task36_displacement=applied_task36,
        post_task36_xyz=post_task36_xyz, post_field_xyz=out.xyz)
    actual.export(folder / 'gate.ply')
    shutil.copy2(__file__, folder / 'overlap_recipe.py')
    metadata = dict(signature=signature, candidate=args.name, stage='G02',
        source=str(source / 'checkpoint.npz'), parent=str(source / 'checkpoint.npz'),
        operation='Two declared narrow-angular overlapping PCHIP returns on source G1, then exactly one existing Task36 split and finite escape-8 field',
        cycle_order=['authored_PCHIP_returns_on_G1_controls', 'Task36_coupled_split', 'finite_nearest_outside_field'],
        authored_return_events=EVENTS,
        authored_return_provenance='Existing smooth_deep.smooth_event radial/axial PCHIP displacement; designed geometry, not fractal-emergent or physical origami folding',
        authored_return_state_frame='Source G1 control vertices; before the sole G2 split',
        direction_interpretation='Chart-direction-selective radial/axial folding with height-varying active sector; no claim that an angular mask is actual torsion',
        authored_return_event_maxima=[float(np.linalg.norm(d, axis=1).max()) for d in returns],
        maximum_combined_authored_return_step=float(np.linalg.norm(return_displacement, axis=1).max()),
        source_return_active_fraction=float((np.linalg.norm(return_displacement, axis=1) > 1e-10).mean()),
        task36_recipe=RECIPE, task36_maximum_step=float(np.linalg.norm(applied_task36, axis=1).max()),
        ancestry_eligible_faces=int(op['eligible'].sum()), incoming_faces=len(source_faces),
        field_recipe=cfg, field_step=field_log, field_cache=field_cache,
        field_iterations=8, field_passes_total=2, subdivision_passes_total=2,
        new_quad_splits_this_branch=1, new_authored_return_events=2,
        step_budget_scope='The .28 budget applies to field movement only; authored returns and Task36 are separate operations',
        physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
        control_vertices=len(out.xyz), control_quads=len(out.faces),
        feature_memory=False, CC_standard_averaging_gain=0., separate_geometric_smoothing=False,
        task36_terminal_policy='Existing plane_only constraints retained; return window excludes ends, later field may move terminals',
        symmetry='Canonical-quarter authored vectors and field queries reflected in X/Y; no posthoc XYZ averaging',
        physical_surface='Existing Task36 mean quad-centre fans after field; render-only fans are not next controls',
        source_status='CHESHIRE existing operators, not IAAC original executable formulas',
        quick_integrity='PASS' if quick_pass else 'FAILED_PRESERVED_NO_REPAIR',
        self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED', **checks)
    prior.base.dump(folder / 'generation.json', metadata)
    print('GENERATED', args.name, 'G2', len(physical.xyz), len(triangles),
        'return_max', metadata['maximum_combined_authored_return_step'],
        'task36_max', metadata['task36_maximum_step'], 'minimum_area', minimum_area,
        'symmetry', symmetry_error, 'quick', metadata['quick_integrity'], flush=True)
    if not quick_pass:
        raise ValueError('Quick integrity failed; geometry and failure metadata preserved, no repair.')


if __name__ == '__main__':
    main()
