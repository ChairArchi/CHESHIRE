"""Column-only control: continue existing OVERLAP Task36/field recurrence.

G4 is generated first for actual render review. G5 is opt-in only after that
review. No authored fold is added, and no source operator/renderer is edited.
Global generation IDs 4/5 are deliberately independent of old three-entry
budget/target schedules. This does not claim physical folding or IAAC code.
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
spec = importlib.util.spec_from_file_location('continued_preserved_ancestry', OLD / 'ancestry_probe.py')
ancestry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ancestry)
prior = ancestry.prior
RECIPE = ancestry.RECIPE.copy()
ALGORITHM = 'EXISTING_OVERLAP_COLUMN_RECURRENCE_G4_G5_V1'
OLD_ROOT = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011')
BUDGETS = {4: .16, 5: .12}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03'))
    p.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/column_detail_20261012'))
    p.add_argument('--name', default='CONTINUED')
    p.add_argument('--through', choices=(4, 5), type=int, default=4)
    args = p.parse_args()
    source = args.source.resolve()
    root = args.root.resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('Candidate must remain beneath output root.')
    source_meta = json.loads((source / 'generation.json').read_text(encoding='utf8'))
    if source_meta.get('quick_integrity') != 'PASS':
        raise ValueError('The control branch must start from the preserved passing OVERLAP/G3.')
    mesh, chart = ancestry.load_control(source / 'control_quad.npz')
    if mesh.generation != 3:
        raise ValueError('Expected actual global G3 control state.')
    source_counts = dict(vertices=len(mesh.xyz), quads=len(mesh.faces))
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = 18
    trees = None
    for gen in range(4, args.through + 1):
        parent = source if gen == 4 else root / family / f'G{gen-1:02}'
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, lead_source=str(source), parent=str(parent),
            source_control_counts=source_counts, stage=gen, task36_recipe=RECIPE,
            field_recipe=cfg, fraction=.55, field_budget=BUDGETS[gen],
            local_target_factor=2, new_authored_return_events=[])
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists():
                raise FileExistsError('Incomplete existing candidate preserved: ' + str(folder))
            meta = json.loads(saved.read_text(encoding='utf8'))
            if meta['signature'] != signature or meta['quick_integrity'] != 'PASS':
                raise FileExistsError('Different or failed existing candidate preserved: ' + str(folder))
            mesh, chart = ancestry.load_control(folder / 'control_quad.npz')
            print('REUSED', args.name, gen, flush=True)
            continue
        if mesh.generation != gen - 1:
            raise ValueError('Global generation and actual control state disagree.')
        incoming = mesh.xyz.copy()
        incoming_faces = mesh.faces.copy()
        nv = len(incoming)
        out, op = ancestry.task36_growth.step(mesh, **RECIPE)
        edges = op['input_edges']
        chart_out = np.concatenate([chart, chart[edges].mean(1), chart[incoming_faces].mean(1)])
        interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[incoming_faces].mean(1)])
        if len(out.xyz) != len(chart_out) or len(out.faces) != 4 * len(incoming_faces):
            raise ValueError('Unexpected existing Task36 birth order or split count.')
        if not np.array_equal(out.xyz[:nv], incoming):
            raise ValueError('Task36 vertex_memory=1 changed old controls before field placement.')
        pairs = prior.helpers.existing.symmetry(chart_out)
        raw_task36 = out.xyz - interpolated
        applied_task36 = raw_task36.copy()
        prior.helpers.existing.reflect(applied_task36, chart_out, pairs)
        out.xyz = interpolated + applied_task36
        post_task36_xyz = out.xyz.copy()
        if trees is None:
            trees, field_cache = prior.helpers.outside_trees(cfg, OLD_ROOT)
        out.xyz, field_payload, field_log = ancestry.loop.apply_field(
            out.xyz, out.faces, chart_out, cfg, trees, .55, BUDGETS[gen], 2)
        physical = ancestry.task36_growth.native(out)
        triangles = physical.faces[:, :3]
        physical_chart = np.concatenate([chart_out, chart_out[out.faces].mean(1)])
        _, symmetry_error, triangle_match = prior.reflection_state(physical.xyz, triangles, physical_chart)
        actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
        minimum_area = float(actual.area_faces.min())
        components = len(trimesh.graph.connected_components(actual.face_adjacency,
            nodes=np.arange(len(triangles)), min_len=1))
        checks = dict(finite=bool(np.isfinite(physical.xyz).all()),
            watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
            components=components, minimum_triangle_area=minimum_area,
            minimum_area_threshold=1e-12, minimum_area_pass=minimum_area > 1e-12,
            geometric_reflection_error=symmetry_error, reflected_triangle_sets_identical=triangle_match)
        quick_pass = (checks['finite'] and checks['watertight'] and checks['winding_consistent']
            and checks['minimum_area_pass'] and components == 1)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
            chart=physical_chart, classes=physical.classes, rest=physical.rest,
            anchors=physical.anchors, generation=np.array(physical.generation))
        np.savez_compressed(folder / 'control_quad.npz', xyz=out.xyz, faces=out.faces,
            chart=chart_out, classes=out.classes, rest=out.rest, anchors=out.anchors,
            generation=np.array(out.generation))
        np.savez_compressed(folder / 'operation_fields.npz', **op, **field_payload,
            interpolated_xyz=interpolated, raw_task36_displacement=raw_task36,
            applied_task36_displacement=applied_task36,
            post_task36_xyz=post_task36_xyz, post_field_xyz=out.xyz)
        actual.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'continued_recipe.py')
        metadata = dict(signature=signature, candidate=args.name, stage=f'G{gen:02}',
            source=str(parent / 'checkpoint.npz'), parent=str(parent / 'checkpoint.npz'),
            lead_source=str(source / 'checkpoint.npz'), origin_g1=source_meta.get('origin_g1'),
            study_scope='Column-only detail recurrence control; no gate synthesis',
            operation='Exactly one existing Task36 coupled split, then finite escape-18 nearest-outside attraction',
            cycle_order=['Task36_coupled_split', 'finite_nearest_outside_field'],
            task36_recipe=RECIPE, normal_response='Existing default class_signed',
            field_recipe=cfg, field_step=field_log, field_cache=field_cache,
            field_iterations=18, field_passes_total=gen, subdivision_passes_total=gen,
            growth_cycles_total=gen, new_growth_cycles_after_lead=gen-3,
            new_authored_return_events=0,
            inherited_return_provenance=source_meta.get('inherited_authored_return_provenance'),
            return_policy='Lead G3 geometry inherited without additional events or amplification',
            field_target_refinement=2,
            target_resolution_change='G3 lead used factor3; G4/G5 use factor2, a coarser local target search. Same finite classifier and coarse fallback; no monotonic target-precision claim.',
            step_budget_scope='Field-only budget; Task36 displacement is separate and total motion can exceed the field budget',
            task36_maximum_step=float(np.linalg.norm(applied_task36, axis=1).max()),
            previous_control_maximum_total_movement=float(np.linalg.norm(out.xyz[:nv]-incoming, axis=1).max()),
            ancestry_eligible_faces=int(op['eligible'].sum()), incoming_faces=len(incoming_faces),
            original_anchor_count=int(len(np.unique(out.anchors[:,0]))),
            physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
            control_vertices=len(out.xyz), control_quads=len(out.faces),
            feature_memory=False, CC_standard_averaging_gain=0., separate_geometric_smoothing=False,
            task36_terminal_policy='Existing plane_only constraints retained; field may subsequently move old vertices/terminals',
            symmetry='Reflected new Task36 vectors and canonical-quarter field; no posthoc XYZ averaging',
            physical_surface='Existing arithmetic quad-centre triangle fans; render fans are not next controls',
            source_status='Existing CHESHIRE recurrence, not IAAC original formulas or physical folding',
            quick_integrity='PASS' if quick_pass else 'FAILED_PRESERVED_NO_REPAIR',
            aesthetic_status='PENDING_ACTUAL_RENDER_REVIEW',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED', **checks)
        prior.base.dump(folder / 'generation.json', metadata)
        print('GENERATED', args.name, gen, len(physical.xyz), len(triangles),
            'task36_max', metadata['task36_maximum_step'], 'field_budget', BUDGETS[gen],
            'area', minimum_area, 'symmetry', symmetry_error,
            'quick', metadata['quick_integrity'], flush=True)
        if not quick_pass:
            raise ValueError('Quick integrity failed; actual geometry and failure preserved, no repair.')
        mesh, chart = out, chart_out


if __name__ == '__main__':
    main()
