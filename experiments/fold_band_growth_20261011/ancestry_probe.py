"""Bounded reuse of existing Task36 ancestry-aware placement plus finite field.

One existing Task36 quad split per cycle, then full_loop.apply_field on the
same controls. No original operator edits, additional split, or new solver.
Task36 terminal constraints and its support-radius scale remain explicit.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
sys.path.insert(0, str(HERE))
import full_loop as loop
from cheshire import task36_growth
from cheshire.reference_subdivision import ArrayMesh

prior = loop.prior
RECIPE = dict(mode='coupled', averaging_gain=0., stencil_gain=1., normal_gain=1.,
              decompose=True, vertex_memory=1., face_gain=.65, edge_gain=.18,
              feedback=1., inherited_bias=.8, diagonal_tension=-.65,
              edge_tension=.5, vertex_tension=-.8, ancestry_gain=1.,
              cap_mode='plane_only', surface='mean')
ALGORITHM = 'EXISTING_TASK36_ANCESTRY_PLUS_FINITE_FIELD_V1'
LATE_RETURN = dict(id='DIAGONAL_WAIST_RETURN', direction=.65, height=.52,
                   span=.09, expansion=.55, constriction=.26, reexpansion=.42,
                   return_depth=.70, overlap_width=1.10, sweep=.38, mirror=False)


def load_control(path):
    with np.load(path, allow_pickle=False) as data:
        mesh = ArrayMesh(data['xyz'].copy(), data['faces'].copy(),
                         data['classes'].copy(), data['rest'].copy(),
                         data['anchors'].copy(), int(data['generation']))
        chart = data['chart'].copy()
    mesh.surface = 'mean'
    return mesh, chart


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('E:/CHESHIRE_DATA/fold_band_growth_20261011'))
    parser.add_argument('--stages', type=int, choices=(1, 2, 3), default=2)
    parser.add_argument('--name', default='ANCESTRY_LOOP')
    parser.add_argument('--staged-field', action='store_true',
                        help='Existing finite escape schedule 4/8/18; changes occupancy, not a pure frequency filter.')
    parser.add_argument('--late-return', action='store_true',
                        help='At G3 only, add one declared existing PCHIP return across the waist; not fractal-emergent folding.')
    args = parser.parse_args()
    root = args.root.resolve()
    family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('Family must remain beneath the output root.')
    source = root / 'inputs' / 'SPAN_SPARSE' / 'G00'
    xyz, quads, chart = prior.load_quads(source / 'control_quad.npz')
    # Recover the declared source carrier's actual reference chart/rest, rather
    # than treating the folded source XYZ as a new rest-state terminal policy.
    mesh, source_chart = prior.variation.carrier(dict(rings=25, sectors=16, radius=.78))
    if not np.array_equal(mesh.faces, quads) or not np.array_equal(source_chart, chart):
        raise ValueError('Source no longer matches the declared unsplit carrier lineage.')
    mesh.xyz = xyz.copy()
    mesh.anchors[:, 0] = np.arange(len(quads))
    mesh.surface = 'mean'
    trees = None
    fieldpath = None
    for gen in range(1, args.stages + 1):
        cfg = prior.field_recipe('n4', .55)
        if args.staged_field:
            cfg['iterations'] = (4, 8, 18)[gen-1]
        elif cfg['iterations'] != 18:
            raise ValueError('The default comparison fixes 18 internal field iterations.')
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, source=str(source), recipe=RECIPE,
                         stage=gen, field_recipe=cfg, fraction=.55,
                         field_budget=[.35, .28, .22][gen-1], local_target_factor=gen)
        if args.staged_field:
            signature.update(staged_field=True, internal_iteration_schedule=[4, 8, 18])
        if args.late_return:
            signature.update(late_authored_return=LATE_RETURN, return_stage=3)
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists() or json.loads(saved.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Existing different or incomplete experiment is preserved: ' + str(folder))
            mesh, chart = load_control(folder / 'control_quad.npz')
            print('REUSED', str(family), gen, flush=True)
            continue
        incoming = mesh.xyz.copy()
        incoming_quads = mesh.faces.copy()
        nv = len(incoming)
        out, op = task36_growth.step(mesh, **RECIPE)
        edges = op['input_edges']
        chart_out = np.concatenate([chart, chart[edges].mean(1), chart[incoming_quads].mean(1)])
        interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[incoming_quads].mean(1)])
        if len(out.xyz) != len(chart_out) or len(out.faces) != 4 * len(incoming_quads):
            raise ValueError('Unexpected Task36 birth ordering or subdivision count.')
        if not np.array_equal(out.xyz[:nv], incoming):
            raise ValueError('Declared Task36 vertex_memory=1 failed to retain old vertices before the field.')
        pairs = prior.helpers.existing.symmetry(chart_out)
        raw_displacement = out.xyz - interpolated
        applied = raw_displacement.copy()
        prior.helpers.existing.reflect(applied, chart_out, pairs)
        out.xyz = interpolated + applied
        # Preserve the existing decomposition; reflect new vectors, never
        # average existing XYZ. Averaging gain is explicitly zero.
        reflected_components = {}
        for key in ('averaging_component', 'stencil_component', 'normal_component'):
            gain = RECIPE[key.removesuffix('_component') + '_gain']
            value = gain * op[key]
            prior.helpers.existing.reflect(value, chart_out, pairs)
            reflected_components['applied_' + key] = value
        prior.reflection_state(out.xyz, out.faces, chart_out)
        post_task36 = out.xyz.copy()
        if trees is None or args.staged_field:
            trees, fieldpath = prior.helpers.outside_trees(cfg, root)
        out.xyz, field_payload, field_log = loop.apply_field(out.xyz, out.faces,
            chart_out, cfg, trees, .55, [.35, .28, .22][gen-1], gen)
        post_field = out.xyz.copy()
        return_displacement = np.zeros_like(out.xyz)
        if args.late_return and gen == 3:
            canonical = chart_out.copy()
            canonical[:, 1:] = np.abs(canonical[:, 1:])
            return_displacement = prior.smooth_deep.smooth_event(canonical, LATE_RETURN)
            return_displacement[:, :2] *= np.where(chart_out[:, 1:] < 0, -1, 1)
            prior.helpers.existing.reflect(return_displacement, chart_out, pairs)
            out.xyz += return_displacement
        physical = task36_growth.native(out)
        triangles = physical.faces[:, :3]
        physical_chart = np.concatenate([chart_out, chart_out[out.faces].mean(1)])
        actual = trimesh.Trimesh(physical.xyz, triangles, process=False)
        _, errors, matches = prior.reflection_state(physical.xyz, triangles, physical_chart)
        minimum_area = float(actual.area_faces.min())
        if (not np.isfinite(physical.xyz).all() or not actual.is_watertight or
                not actual.is_winding_consistent or minimum_area <= 1e-12):
            raise ValueError('Quick integrity failed; no repair or threshold change.')
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'control_quad.npz', xyz=out.xyz, faces=out.faces,
            chart=chart_out, classes=out.classes, rest=out.rest, anchors=out.anchors,
            generation=np.array(out.generation))
        np.savez_compressed(folder / 'geometry.npz', xyz=physical.xyz, faces=triangles)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=physical.xyz, faces=triangles,
            chart=physical_chart, classes=physical.classes, rest=physical.rest,
            anchors=physical.anchors, generation=np.array(physical.generation))
        np.savez_compressed(folder / 'operation_fields.npz', **op, **reflected_components,
            interpolated_xyz=interpolated, raw_task36_displacement=raw_displacement,
            applied_task36_displacement=applied, post_task36_xyz=post_task36,
            post_field_xyz=post_field, return_displacement=return_displacement,
            post_return_xyz=out.xyz, **field_payload)
        actual.export(folder / 'gate.ply')
        shutil.copy2(__file__, folder / 'ancestry_recipe.py')
        old_total = np.linalg.norm(out.xyz[:nv] - incoming, axis=1)
        metadata = dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source / 'checkpoint.npz'),
            parent=str(source / 'checkpoint.npz') if gen == 1 else str(folder.parent / f'G{gen-1:02}' / 'checkpoint.npz'),
            operation='Exactly one existing ancestry-aware Task36 coupled quad split, no standard CC averaging component, then finite nearest-outside field' + ('; one existing authored PCHIP waist return at G3' if args.late_return and gen == 3 else ''),
            cycle_order=['Task36_coupled_placement_and_one_quad_split', 'finite_nearest_outside_field'] + (['authored_PCHIP_return'] if args.late_return and gen == 3 else []),
            quad_splits_per_cycle=1, subdivision_passes_total=gen, field_passes_total=gen,
            growth_cycles_total=gen, task36_recipe=RECIPE, field_recipe=cfg, field_step=field_log,
            field_cache=fieldpath, field_used=True, feature_memory=False,
            field_iterations=cfg['iterations'], staged_field=args.staged_field,
            field_staging_interpretation='4/8/18 is an existing CHESHIRE hypothesis; lower finite iterations expand occupancy and change target geometry, not a pure frequency filter. Three growth cycles remain.' if args.staged_field else None,
            authored_return_event=LATE_RETURN if args.late_return and gen == 3 else None,
            authored_return_provenance='Existing smooth_deep.smooth_event radial/axial PCHIP displacement, added once after the G3 field. It is deliberately authored, not generated by the fractal equation.' if args.late_return else None,
            maximum_return_step=float(np.linalg.norm(return_displacement,axis=1).max()),
            step_budget_scope='Field budget only; Task36 placement and optional authored return are separate and summed motion may exceed the field budget.',
            ancestry_rule='Existing V/E/F class pattern enables weighted inherited-diagonal placement. Input anchors retain original cage face IDs; parent_face records immediate lineage. This is not crease-feature memory.',
            ancestry_eligible_faces=int(op['eligible'].sum()), incoming_faces=len(incoming_quads),
            original_anchor_count=int(len(np.unique(out.anchors[:, 0]))),
            control_vertices=len(out.xyz), control_quads=len(out.faces),
            physical_vertices=len(physical.xyz), physical_triangles=len(triangles),
            watertight=bool(actual.is_watertight), winding_consistent=bool(actual.is_winding_consistent),
            components=int(len(actual.split(only_watertight=False))),
            minimum_triangle_area=minimum_area, minimum_area_threshold=1e-12, minimum_area_pass=True,
            geometric_reflection_error=errors, reflected_triangle_sets_identical=matches,
            task36_maximum_step=float(np.linalg.norm(applied, axis=1).max()),
            task36_raw_to_reflected_maximum_change=float(np.linalg.norm(raw_displacement-applied, axis=1).max()),
            old_task36_vertex_maximum_step=float(np.linalg.norm(applied[:nv], axis=1).max()),
            previous_control_vertex_max_movement=float(old_total.max()),
            previous_control_vertices_moved=int((old_total > 1e-12).sum()),
            component_maxima={key:float(np.linalg.norm(value,axis=1).max()) for key,value in reflected_components.items()},
            component_log_scope='Raw decomposition bases retained under original Task36 keys; applied_* arrays include declared gains (averaging gain is zero).',
            CC_standard_averaging_gain=0., separate_geometric_smoothing=False,
            task36_terminal_policy='Existing plane_only: terminal V/E Z components constrained, terminal face displacement zero, terminal normal gains suppressed; later field can move these points. Not free-cap placement.',
            physical_surface='Existing Task36 mean quad-centre triangle fans after the final operation, not independent geometry controls',
            provenance='Existing CHESHIRE Task36/reference weighted stencils reused as a declared experiment; not IAAC original formulas or recovered executable source',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication_thickness_structure='NOT_CHECKED')
        prior.base.dump(folder / 'generation.json', metadata)
        print('GENERATED', str(family), gen, 'eligible', metadata['ancestry_eligible_faces'],
              'of',len(incoming_quads),'actual',len(physical.xyz),len(triangles),
              'task36_max',metadata['task36_maximum_step'],'old_field_max',metadata['previous_control_vertex_max_movement'],
              'area',minimum_area,'symmetry',errors,flush=True)
        mesh, chart = out, chart_out


if __name__ == '__main__':
    main()
