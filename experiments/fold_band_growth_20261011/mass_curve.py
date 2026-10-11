"""Two finite whole-mass curve-controlled normal-placement passes.

G1 gives all V/E/F births the SAME signed expansion/constriction response.
G2 repeats a weaker common response and introduces only a small V/F contrast.
This tests mass movement versus cell texture; it is geometric normal placement,
not origami, physical buckling or recovered original IAAC equations. Puffy
inflation or recess loss remains a possible aesthetic failure.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('mass_physical_curve', HERE / 'curve_growth.py')
curve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curve)
roles = curve.roles
prior = curve.prior
ALGORITHM = 'FINITE_COMMON_MASS_CURVE_NORMAL_OFFSET_V1'


def control_curves():
    expansion, ex_vertices, ex_segments, ex_definition = curve.attractor_curves('sweep')
    circles, _, _, _ = curve.attractor_curves('circle')
    contraction = circles[1:2].copy()
    contraction[:, :, :2] *= .72 / 1.05
    co_vertices = contraction.reshape(-1, 3)
    co_segments = np.column_stack([np.arange(64), np.arange(1, 65)])
    return dict(expansion_curves=expansion, expansion_vertices=ex_vertices, expansion_segments=ex_segments,
        constriction_curves=contraction, constriction_vertices=co_vertices, constriction_segments=co_segments), dict(
        expansion=ex_definition, constriction=dict(mode='circle', height=5., radius=.72, samples=65),
        expansion_range=1., constriction_range=1.05,
        activation='C1 compact smoothstep(clamp(1-closest_segment_distance/range,0,1)), no positive floor')


def compact_weight(xyz, vertices, segments, attractor_range):
    query = xyz.copy(); query[:, :2] = np.abs(query[:, :2])
    distance = curve.closest_segment_distance(query, vertices, segments)
    t = np.clip(1. - distance / attractor_range, 0., 1.)
    return t * t * (3. - 2. * t), distance


def mass_step(xyz, quads, chart, generation, budget):
    if generation not in (1, 2) or not np.isfinite(budget) or budget <= 0.:
        raise ValueError('Two finite stages and a positive finite total-distance budget required.')
    # Reuse existing exact split, birth classification and INPUT normals.
    # The activation is zero here; it contributes no role displacement.
    refined, outquads, outchart, payload, _ = roles.role_step(xyz, quads, chart, generation,
        'vertex_face', budget, .3, activation_fn=lambda p, c, g: np.zeros(len(p)))
    curves, definition = control_curves()
    expansion, ex_distance = compact_weight(refined, curves['expansion_vertices'], curves['expansion_segments'], 1.)
    constriction, co_distance = compact_weight(refined, curves['constriction_vertices'], curves['constriction_segments'], 1.05)
    common_factor = 1. if generation == 1 else .55
    common_distance = common_factor * (.60 * expansion - .48 * constriction)
    birth_weights = np.zeros(3) if generation == 1 else np.array([.05, 0., -.08])
    birth_distance = .3 * birth_weights[payload['birth_class']] * expansion
    total_requested = common_distance + birth_distance
    bound_factor = np.minimum(1., budget / np.maximum(np.abs(total_requested), 1e-15))
    common_displacement = payload['normal'] * (common_distance * bound_factor)[:, None]
    birth_displacement = payload['normal'] * (birth_distance * bound_factor)[:, None]
    pairs, _, _ = prior.reflection_state(refined, outquads, outchart)
    prior.helpers.existing.reflect(common_displacement, outchart, pairs)
    prior.helpers.existing.reflect(birth_displacement, outchart, pairs)
    displacement = common_displacement + birth_displacement
    result = refined + displacement
    if generation == 1 and np.any(birth_displacement):
        raise ValueError('Stage one must have zero deliberate birth contrast.')
    if np.linalg.norm(displacement, axis=1).max() > budget + 1e-12:
        raise ValueError('Applied total normal displacement exceeds its declared budget.')
    payload.update(pre_mass_xyz=refined, expansion_weight=expansion, constriction_weight=constriction,
        expansion_curve_distance=ex_distance, constriction_curve_distance=co_distance,
        requested_common_normal_distance=common_distance, requested_birth_normal_distance=birth_distance,
        total_requested_normal_distance=total_requested, total_budget_factor=bound_factor,
        common_displacement=common_displacement, birth_displacement=birth_displacement, displacement=displacement)
    length = np.linalg.norm(displacement, axis=1)
    log = dict(common_coefficients=dict(expansion=.60, constriction=-.48), common_stage_factor=common_factor,
        birth_coefficients=birth_weights.tolist(), birth_absolute_placement=.3,
        maximum_common_step=float(np.linalg.norm(common_displacement, axis=1).max()),
        maximum_birth_step=float(np.linalg.norm(birth_displacement, axis=1).max()),
        maximum_actual_step=float(length.max()), maximum_requested_step=float(np.abs(total_requested).max()),
        budget_clamped_points=int((bound_factor < 1.).sum()),
        expansion_weight_range=[float(expansion.min()), float(expansion.max())],
        constriction_weight_range=[float(constriction.min()), float(constriction.max())],
        common_birth_displacement_distinction='Common scalar response for all V/E/F; input normals still differ by geometric support',
        moved_by_birth=[int((length[payload['birth_class'] == k] > 1e-12).sum()) for k in range(3)],
        old_vertex_maximum_step=float(length[:len(xyz)].max()))
    return result, outquads, outchart, payload, curves, definition, log


def self_test():
    initial, chart = prior.variation.carrier(dict(rings=9, sectors=16, radius=.78))
    before = initial.xyz.copy()
    xyz, quads = initial.xyz.copy(), initial.faces.copy(); logs = []
    for gen, budget in ((1, .50), (2, .28)):
        xyz, quads, chart, payload, _, _, log = mass_step(xyz, quads, chart, gen, budget)
        px, pt, pc = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(px, pt, process=False)
        _, errors, matches = prior.reflection_state(px, pt, pc)
        assert np.isfinite(px).all() and mesh.is_watertight and mesh.is_winding_consistent
        assert mesh.area_faces.min() > 1e-12 and max(errors) < 1e-9 and all(matches)
        assert np.array_equal(payload['displacement'], payload['common_displacement'] + payload['birth_displacement'])
        assert log['moved_by_birth'][0] > 0 and log['maximum_actual_step'] <= budget + 1e-12
        assert log['maximum_birth_step'] == 0. if gen == 1 else log['maximum_birth_step'] <= .024 + 1e-12
        logs.append(dict(generation=gen, maximum_common=log['maximum_common_step'],
            maximum_birth=log['maximum_birth_step'], minimum_area=float(mesh.area_faces.min()), reflection_errors=errors))
    assert np.array_equal(initial.xyz, before)
    print('SELF_TEST_PASS', json.dumps(logs), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='E:/CHESHIRE_DATA/fold_band_growth_20261011/FIELD_SEED/G01')
    parser.add_argument('--output-root', default='E:/CHESHIRE_DATA/fold_band_growth_20261011')
    parser.add_argument('--name', default='MASS_CURVE')
    parser.add_argument('--stages', type=int, choices=(1, 2), default=1)
    parser.add_argument('--budgets', nargs=2, type=float, default=[.50, .28])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test(); return
    if not np.isfinite(args.budgets).all() or min(args.budgets) <= 0.:
        raise ValueError('Two positive finite total normal-distance budgets required.')
    source = prior.helpers.checkpoint_path(args.source); control = source.parent / 'control_quad.npz'
    xyz, quads, chart = prior.load_quads(control)
    source_vertices, source_quads = len(xyz), len(quads)
    _, source_errors, _ = prior.reflection_state(xyz, quads, chart)
    source_meta = json.loads((source.parent / 'generation.json').read_text(encoding='utf8'))
    inherited_field = int(source_meta.get('field_passes_total', 0))
    inherited_subdivision = int(source_meta.get('subdivision_passes_total', 0))
    inherited_role = int(source_meta.get('role_offset_passes_total', 0))
    inherited_growth = int(source_meta.get('growth_passes_total', inherited_field + inherited_role))
    _, definition = control_curves()
    root = Path(args.output_root).resolve(); family = Path(args.name)
    if family.is_absolute() or '..' in family.parts:
        raise ValueError('--name must remain beneath --output-root.')
    hashes = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  control_sha256=hashlib.sha256(control.read_bytes()).hexdigest())
    for gen in range(1, args.stages + 1):
        folder = root / family / f'G{gen:02}'
        signature = dict(algorithm=ALGORITHM, **hashes, stage=gen, curves=definition,
            common_expansion=.60, common_constriction=-.48, common_stage_factors=[1., .55],
            birth_coefficients=[[0., 0., 0.], [.05, 0., -.08]], birth_absolute_placement=.3,
            maximum_step=args.budgets[gen - 1])
        signature = json.loads(json.dumps(signature))
        if folder.exists() and any(folder.iterdir()):
            saved = folder / 'generation.json'
            if not saved.exists() or json.loads(saved.read_text(encoding='utf8')).get('signature') != signature:
                raise FileExistsError('Different settings or incomplete stage: ' + str(folder))
            xyz, quads, chart = prior.load_quads(folder / 'control_quad.npz')
            if not all((folder / name).exists() for name in ('operation_fields.npz', 'attractor_curves.npz', 'gate.ply')):
                raise FileExistsError('Stage lacks actual output artifacts: ' + str(folder))
            print('REUSED', str(family), gen, flush=True); continue
        old_count, old_faces = len(xyz), len(quads)
        xyz, quads, chart, payload, curves, _, log = mass_step(xyz, quads, chart, gen, args.budgets[gen - 1])
        px, pt, pc = prior.physical_quads(xyz, quads, chart, gen)
        mesh = trimesh.Trimesh(px, pt, process=False)
        if not np.isfinite(px).all() or not mesh.is_watertight or not mesh.is_winding_consistent:
            raise ValueError('Invalid actual output; no repair performed.')
        _, errors, matches = prior.reflection_state(px, pt, pc)
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / 'geometry.npz', xyz=px, faces=pt)
        np.savez_compressed(folder / 'checkpoint.npz', xyz=px, faces=pt, chart=pc)
        np.savez_compressed(folder / 'control_quad.npz', xyz=xyz, faces=quads, chart=chart)
        np.savez_compressed(folder / 'operation_fields.npz', **payload)
        np.savez_compressed(folder / 'attractor_curves.npz', **curves)
        mesh.export(folder / 'gate.ply'); shutil.copy2(__file__, folder / 'mass_curve_recipe.py')
        prior.base.dump(folder / 'generation.json', dict(signature=signature, candidate=str(family), stage=f'G{gen:02}',
            source=str(source), parent=str(source) if gen == 1 else str(folder.parent / f'G{gen - 1:02}' / 'checkpoint.npz'),
            operation='Existing bilinear split and common expansion-minus-constriction normal response across all V/E/F; weak birth contrast only at second pass',
            mass_offset=log, curve_definition=definition, mass_generation=gen,
            source_control_vertices=source_vertices, source_control_quads=source_quads,
            source_vertices=source_vertices + source_quads, source_triangles=4 * source_quads,
            previous_control_vertices=old_count, previous_faces=old_faces,
            control_vertices=len(xyz), control_quads=len(quads), physical_vertices=len(px), physical_triangles=len(pt),
            subdivision_passes_total=inherited_subdivision + gen, subdivision_passes_this_study=gen,
            field_passes_total=inherited_field, field_passes_this_study=0,
            inherited_field_passes=inherited_field, mass_offset_passes_total=gen,
            source_growth_passes=inherited_growth, growth_passes_total=inherited_growth + gen,
            previous_control_vertex_max_movement=log['old_vertex_maximum_step'],
            previous_control_vertices_moved=log['moved_by_birth'][0], maximum_actual_step=log['maximum_actual_step'],
            moved_vertices=sum(log['moved_by_birth']), minimum_triangle_area=float(mesh.area_faces.min()),
            minimum_area_threshold=1e-12, minimum_area_pass=bool(mesh.area_faces.min() > 1e-12),
            source_reflection_error=source_errors, geometric_reflection_error=errors, reflected_triangle_sets_identical=matches,
            watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
            physical_surface='Existing Task36 arithmetic quad-centre fans; render centres have no independent movement',
            endpoint_lock=False, old_vertex_holdout=False, support_shrinkage=False,
            separate_geometric_smoothing=False, CC_coordinate_averaging=False, random_noise=False,
            field_used_this_study=False, curves_rendered=False, physical_fold_solver=False,
            provenance='Finite composition of existing normals, signed offsets and physical curve distances; test constants are not recovered original IAAC equations',
            limitations='Common signed normal placement may inflate, erase recesses or intersect; this is not a fold solver. Whole-mass improvement must be judged from actual views. Thickness, structure and fabrication unverified.',
            self_intersection='NOT_CHECKED_INTERMEDIATE', fabrication='NOT_CHECKED'))
        print('GENERATED', str(family), gen, len(px), len(pt), 'common_max', log['maximum_common_step'],
              'birth_max', log['maximum_birth_step'], 'minimum_area', mesh.area_faces.min(), flush=True)


if __name__ == '__main__':
    main()
