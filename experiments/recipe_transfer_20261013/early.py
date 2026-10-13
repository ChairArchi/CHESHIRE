"""One fixed selected G0--G4 recipe, with only the G0 radius profile changed.

The frozen operators and their authored values are reused without retuning.
G counts actual quad subdivision, including Task36 custom subdivision; the
attached ROOT_ONLY/SIDEWALL events retain G3.  WALL retains its actual VF fan
surface, whereas ROOT_ONLY deliberately switches that control state to mean.
Importing this module performs no geometry generation or output writes.
"""
from pathlib import Path
import argparse
import copy
import gc
import hashlib
import importlib.util
import json
import sys
import types

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
WORKFLOW = REPO/'docs/generation_workflow_20261013/LINEAGE.json'
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/recipe_transfer_20261013/trial01')
RADIUS_SCALE_PROFILE = (1., .82, .88, 1.20, 1.16, 1.02, .86, 1.)
INPUT_CASE = 'WAIST_FULL'
STAGE_IDS = ('G00_INPUT', 'G01_ANCESTRY', 'G02_OVERLAP', 'G03_WALL',
             'G03_ROOT', 'G03_SIDEWALL', 'G04_NEUTRAL')


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO/relative)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


sparse = module('transfer_early_sparse', 'experiments/fold_band_growth_20261011/sparse_input.py')
overlap = module('transfer_early_overlap', 'experiments/directional_growth_20261012/overlap_probe.py')
wall = module('transfer_early_wall', 'experiments/fold_visible_gate_20261012/study.py')
core = module('transfer_early_core', 'experiments/connected_fold_growth_20261012/study.py')
sidewall = module('transfer_early_sidewall', 'experiments/sidewall_fan_growth_20261013/patch_sidewall.py')
mirror = module('transfer_early_mirror', 'experiments/connected_fold_growth_20261012/verify.py')
seed, ancestry, prior = sparse.seed, overlap.ancestry, overlap.prior
digest, write = core.digest, core.write


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def dependency_paths():
    """Include dynamically imported, transitive repository modules as well.

    Several frozen spec_from_file_location modules are absent from sys.modules;
    following module-valued globals retains their actual source dependencies.
    """
    queue = [sparse, overlap, wall, core, sidewall, mirror]
    queue.extend(value for value in sys.modules.values()
                 if isinstance(value, types.ModuleType))
    seen, paths = set(), {Path(__file__).resolve()}
    while queue:
        current = queue.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        filename = getattr(current, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        if not path.is_relative_to(REPO) or path.suffix != '.py':
            continue
        paths.add(path)
        queue.extend(value for value in vars(current).values()
                     if isinstance(value, types.ModuleType))
    return sorted(paths)


def code_hashes():
    return {path.relative_to(REPO).as_posix(): digest(path)
            for path in dependency_paths()}


def selected_receipts():
    workflow = read(WORKFLOW)
    for checked in workflow['frozen_code_checks']:
        if digest(REPO/checked['path']) != checked['expected_sha256']:
            raise ValueError('Documented frozen source changed: '+checked['path'])
    # The first seven documented nodes are the exact selected early lineage.
    nodes = workflow['nodes'][:7]
    if [node['generation'] for node in nodes] != [0, 1, 2, 3, 3, 3, 4]:
        raise ValueError('Documented selected early lineage differs.')
    result = {}
    for stage, node in zip(STAGE_IDS, nodes):
        path = Path(node['receipt'])
        if digest(path) != node['receipt_sha256']:
            raise ValueError('Selected recipe receipt changed: '+str(path))
        result[stage] = dict(path=str(path), sha256=node['receipt_sha256'],
                             metadata=read(path))
    return result


def seed_input(radius_scale_profile):
    scale = np.asarray(radius_scale_profile, float)
    if scale.shape != (8,) or not np.array_equal(scale, RADIUS_SCALE_PROFILE):
        raise ValueError('Only the single authorized fixed WAIST_FULL radius profile is supported.')
    mesh, chart = seed.variation.carrier(dict(rings=25, sectors=16, radius=.78))
    recipe = copy.deepcopy(seed.RECIPES['SPAN'])
    recipe['radius'][0] *= 1.10
    recipe['radius'][-1] *= 1.10
    recipe['events'][-1]['span'] *= 1.35
    recipe['events'][-1]['return_depth'] *= 1.12
    source_recipe = copy.deepcopy(recipe)
    recipe['radius'] = (np.asarray(recipe['radius'])*scale).tolist()
    mesh.xyz, parts = seed.legacy_core(chart, recipe, 'SPAN')
    mesh.surface = 'mean'
    if mesh.generation != 0:
        raise ValueError('The unsplit input must be actual G0.')
    return mesh, chart, parts, source_recipe, recipe


def _field_trees(cfg, selected):
    """Reuse the already saved, exactly matching field cache, without new grids."""
    info = selected['metadata']
    if cfg != info['field_recipe']:
        raise ValueError('Existing selected finite-field recipe differs.')
    cache = Path(info['field_cache'])
    parameters = read(cache/'field.json')['parameters']
    if any(parameters[key] != cfg[key] for key in parameters):
        raise ValueError('Saved finite-field cache parameters differ.')
    if not (cache/'outside_grid.npz').is_file():
        raise FileNotFoundError('The selected outside field cache is required: '+str(cache))
    # Existing helper performs the original quarter/axis-subset construction.
    # Its grid lookup finds this existing immutable cache before any creation.
    trees, observed = prior.helpers.outside_trees(cfg, overlap.OLD_ROOT)
    if Path(observed).resolve() != cache.resolve():
        raise ValueError('Existing helper selected a different field cache.')
    return trees, dict(path=str(cache), field_json_sha256=digest(cache/'field.json'),
                       outside_grid_sha256=digest(cache/'outside_grid.npz'))


def ancestry_field(mesh, chart, generation, selected):
    """Exactly one selected Task36 split followed by finite field 4 or 8."""
    if generation not in (1, 2) or mesh.generation != generation-1:
        raise ValueError('Only selected G0->G1 and G1->G2 transitions are supported.')
    mesh = copy.deepcopy(mesh)
    chart = np.asarray(chart).copy()
    if generation == 1:
        # Match ancestry_probe's recovery of the original carrier/rest/anchors.
        carrier, carrier_chart = prior.variation.carrier(dict(rings=25, sectors=16, radius=.78))
        if not np.array_equal(carrier.faces, mesh.faces) or not np.array_equal(carrier_chart, chart):
            raise ValueError('Unsplit original carrier correspondence required.')
        carrier.xyz = mesh.xyz.copy()
        carrier.anchors[:, 0] = np.arange(len(mesh.faces))
        carrier.surface = 'mean'
        mesh = carrier
        return_delta = np.zeros_like(mesh.xyz)
    else:
        canonical = chart.copy()
        canonical[:, 1:] = np.abs(canonical[:, 1:])
        pairs = prior.helpers.existing.symmetry(chart)
        returns = []
        for event in overlap.EVENTS:
            value = prior.smooth_deep.smooth_event(canonical, event)
            value[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
            prior.helpers.existing.reflect(value, chart, pairs)
            returns.append(value)
        return_delta = np.sum(returns, axis=0)
        mesh.xyz = mesh.xyz+return_delta
        prior.reflection_state(mesh.xyz, mesh.faces, chart)
    incoming, faces = mesh.xyz.copy(), mesh.faces.copy()
    out, op = ancestry.task36_growth.step(mesh, **ancestry.RECIPE)
    edges = op['input_edges']
    outchart = np.concatenate([chart, chart[edges].mean(1), chart[faces].mean(1)])
    interpolated = np.concatenate([incoming, incoming[edges].mean(1), incoming[faces].mean(1)])
    if not np.array_equal(out.xyz[:len(incoming)], incoming) or len(out.faces) != 4*len(faces):
        raise ValueError('Selected Task36 old-control or split-count policy differs.')
    pairs = prior.helpers.existing.symmetry(outchart)
    applied = out.xyz-interpolated
    prior.helpers.existing.reflect(applied, outchart, pairs)
    out.xyz = interpolated+applied
    post_task36 = out.xyz.copy()
    components = {}
    for key in ('averaging_component', 'stencil_component', 'normal_component'):
        value = ancestry.RECIPE[key.removesuffix('_component')+'_gain']*op[key]
        prior.helpers.existing.reflect(value, outchart, pairs)
        components['applied_'+key] = value
    cfg = prior.field_recipe('n4', .55)
    cfg['iterations'] = 4 if generation == 1 else 8
    trees, cache = _field_trees(cfg, selected)
    budget = .35 if generation == 1 else .28
    out.xyz, field_state, field_log = ancestry.loop.apply_field(
        out.xyz, out.faces, outchart, cfg, trees, .55, budget, generation)
    out.surface = 'mean'
    state = dict(op, **components, **field_state, pre_task36_xyz=incoming,
                 post_task36_xyz=post_task36, authored_return_displacement=return_delta,
                 applied_task36_displacement=applied)
    metadata = dict(task36_recipe=copy.deepcopy(ancestry.RECIPE), field_recipe=cfg,
                    field_cache=cache, field_step=field_log, field_iterations=cfg['iterations'],
                    field_passes_total=generation, subdivision_passes_total=generation,
                    CC_standard_averaging_gain=0., feature_memory=False,
                    authored_return_events=copy.deepcopy(overlap.EVENTS) if generation == 2 else [],
                    cycle_order=(['authored_PCHIP_returns_on_G1_controls'] if generation == 2 else [])+
                    ['Task36_coupled_split', 'finite_nearest_outside_field'])
    return out, outchart, state, metadata


def wall_stage(mesh, chart):
    """Re-measure rails on the new actual G2, then the frozen WALL operation."""
    parents = copy.deepcopy(overlap.EVENTS)
    sampler = wall.native_sampler(mesh, chart)
    guides = [wall.measure_longitudinal(sampler, parent, shoulder_fraction=.55,
                                       frame_mode='region') for parent in parents]
    rails = [wall.wall_fold.measure_rails(sampler, guide, angle_degrees=40.)
             for guide in guides]
    tags = np.zeros(len(mesh.xyz))
    out, outchart, outtags, op = wall.previous.anchor.t.memory.refine(mesh, chart, tags)
    reference = out.xyz.copy()
    delta, fields = wall.wall_fold.apply_wall(reference, outchart, rails, mode='WALL')
    existing = prior.helpers.existing
    existing.reflect(delta, outchart, existing.symmetry(outchart))
    out.xyz = reference+delta
    if out.generation != 3 or out.surface != 'vf':
        raise ValueError('Selected WALL requires actual interpolating VF G3.')
    state = dict(reference_xyz=reference, delta=delta, chart=outchart,
                 input_edges=op['input_edges'], parent_face=op['parent_face'],
                 memory=outtags, **fields)
    metadata = dict(recipe=dict(wall.RECIPE, candidate='WALL'), parent_region_seeds=parents,
                    added_field_passes=0, inherited_field_passes=2,
                    maximum_displacement=float(np.linalg.norm(delta, axis=1).max()),
                    moved_controls=int((np.linalg.norm(delta, axis=1)>1e-12).sum()),
                    geometry_operation='Interior ruled-wall redevelopment',
                    subdivision_operator='Inactive interpolating Task36; old controls preserved before WALL')
    return out, outchart, state, metadata, guides, rails


def _pairs(mesh, chart, state=None):
    if state is not None and 'mirror_x_vertex_pairs' in state:
        return {axis: np.asarray(state['mirror_'+axis.lower()+'_vertex_pairs'])
                for axis in ('X', 'Y')}
    px, py = prior.helpers.existing.symmetry(chart)
    return dict(X=px, Y=py)


def actual_symmetry(mesh, pairs):
    axes, face_pairs = {}, {}
    for axis, coordinate in (('X', 0), ('Y', 1)):
        pair = pairs[axis]
        mirror.involution(pair, len(mesh.xyz), axis+' actual control correspondence')
        reflected = mesh.xyz[pair].copy()
        reflected[:, coordinate] *= -1
        error = float(np.linalg.norm(mesh.xyz-reflected, axis=1).max())
        if not np.isfinite(error) or error > 1e-9:
            raise ValueError('Actual control reflection differs: '+axis)
        face_pairs[axis] = mirror.face_involution(mesh.faces, pair, label=axis+' actual oriented quads')
        axes[axis] = dict(passed=True, actual_control_xyz_max_error=error,
                          oriented_control_faces_identical=True, tolerance=1e-9)
    return dict(passed=True, axes=axes,
                correspondence='Actual source/chart or attached-event IDs; no XYZ repair'), face_pairs


def _save(folder, mesh, chart, context, state, pairs=None, guides=(), rails=()):
    pairs = _pairs(mesh, chart, state) if pairs is None else pairs
    symmetry, fp = actual_symmetry(mesh, pairs)
    state = dict(state, mirror_x_vertex_pairs=pairs['X'], mirror_y_vertex_pairs=pairs['Y'],
                 mirror_x_face_pairs=fp['X'], mirror_y_face_pairs=fp['Y'])
    context = dict(context, symmetry=symmetry)
    if mesh.surface == 'mean':
        record = core.save(folder, mesh, chart, context, state)
        with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
            symmetry['actual_native'] = mirror.actual_native_symmetry(
                saved['xyz'], saved['faces'], mesh.faces, pairs, fp)
        record['symmetry'] = symmetry
    elif mesh.surface == 'vf':
        if folder.exists():
            raise FileExistsError('Earlier result preserved: '+str(folder))
        # core.save forces mean fans; use the frozen Task36 VF native here only.
        native = ancestry.task36_growth.native(mesh)
        triangles = native.faces[:, :3]
        mesh._chart_for_receipt = chart
        checks = core.quick_checks(mesh, native.xyz, triangles)
        pchart = np.concatenate([chart, wall.previous.anchor.t.face_values(mesh, chart)])
        _, native_errors, native_matches = prior.reflection_state(native.xyz, triangles, pchart)
        symmetry.update(actual_native_xyz_max_errors=native_errors,
                        actual_native_triangle_sets_identical=native_matches)
        folder.mkdir(parents=True)
        np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
            chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
            generation=np.array(mesh.generation), surface=np.array('vf'))
        np.savez_compressed(folder/'geometry.npz', xyz=native.xyz, faces=triangles)
        np.savez_compressed(folder/'evidence.npz', **state)
        record = dict(context, symmetry=symmetry, subdivision_generation=int(mesh.generation),
            native_surface='Frozen Task36 native VF diagonal fan; no renderer modifier',
            control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
            native_vertices=len(native.xyz), native_triangles=len(triangles), checks=checks,
            control_file_sha256=digest(folder/'control_quad.npz'),
            geometry_file_sha256=digest(folder/'geometry.npz'),
            evidence_file_sha256=digest(folder/'evidence.npz'), visual_success='NOT_ASSESSED')
        if not checks['passed']:
            write(folder/'generation.json', record)
            raise ValueError('Failure preserved; no geometry repair: '+str(folder))
    else:
        raise ValueError('Unknown actual native surface.')
    minimum = 1e-12 if context['candidate'] in ('SPAN_SPARSE', 'ANCESTRY_STAGED', 'OVERLAP', 'WALL') else 1e-14
    record['checks']['minimum_native_triangle_area_threshold'] = minimum
    if record['checks']['minimum_native_triangle_area'] <= minimum:
        record['checks']['passed'] = False
        write(folder/'generation.json', record)
        raise ValueError('Original stage area threshold failed; no threshold change or repair.')
    for prefix, records in (('guide', guides), ('rails', rails)):
        for index, values in enumerate(records):
            np.savez_compressed(folder/f'{prefix}_{index}.npz', **values)
    record['checks']['symmetry_scope'] = 'Actual control XYZ and oriented quads checked using explicit involutions'
    write(folder/'generation.json', record)
    return record, state


def build(root, radius_scale_profile=RADIUS_SCALE_PROFILE):
    """Save the single authorized input through actual selected G4, once."""
    root = Path(root).resolve()
    folders = {stage: root/'states'/stage for stage in STAGE_IDS}
    if any(folder.exists() for folder in folders.values()):
        raise FileExistsError('Existing early states are preserved; no partial replay or retuning.')
    core.memory_guard()
    selected = selected_receipts()
    hashes = code_hashes()
    records, nodes = {}, []

    def save(stage, mesh, chart, candidate, state, metadata=None, parent=None, pairs=None,
             guides=(), rails=()):
        context = dict(input_case=INPUT_CASE, candidate=candidate,
            transfer_schema='CHESHIRE_FIXED_SELECTED_RECIPE_TRANSFER_V1',
            geometry_code_sha256=hashes, selected_recipe_receipt=selected[stage]['path'],
            selected_recipe_receipt_sha256=selected[stage]['sha256'],
            input_only_change='Eight authorized G0 radial-profile multipliers; all later formulas/values frozen',
            added_normal_field_passes=0, self_intersection='NOT_CHECKED_EXPLORATORY',
            fabrication='NOT_CHECKED', **(metadata or {}))
        if parent is not None:
            context.update(source=str(folders[parent]), source_generation=records[parent]['subdivision_generation'],
                source_control_sha256=records[parent]['control_file_sha256'],
                source_generation_json_sha256=digest(folders[parent]/'generation.json'),
                parent_stage=str(folders[parent]))
        records[stage], state = _save(folders[stage], mesh, chart, context, state,
                                      pairs=pairs, guides=guides, rails=rails)
        nodes.append(dict(id=stage, folder=str(folders[stage]), generation=int(mesh.generation),
                          generation_json_sha256=digest(folders[stage]/'generation.json')))
        write(root/'STAGES_EARLY.json', dict(schema='CHESHIRE_RECIPE_TRANSFER_EARLY_STAGES_V1',
              input_case=INPUT_CASE, status='IN_PROGRESS', stages=nodes))
        return state

    mesh, chart, parts, original_recipe, input_recipe = seed_input(radius_scale_profile)
    if original_recipe != selected['G00_INPUT']['metadata']['recipe']:
        raise ValueError('The original selected SPAN_SPARSE seed recipe differs.')
    recipes = dict(input_case=INPUT_CASE, original_input_recipe=original_recipe,
        input_recipe=input_recipe, radius_scale_profile=list(radius_scale_profile),
        carrier=dict(rings=25, sectors=16, radius=.78),
        task36=copy.deepcopy(ancestry.RECIPE), overlap_events=copy.deepcopy(overlap.EVENTS),
        wall=copy.deepcopy(wall.RECIPE), root_event=copy.deepcopy(core.patch_growth.RECIPE),
        sidewall_event=copy.deepcopy(sidewall.RECIPE),
        field_passes=[dict(iterations=4, fraction=.55, budget=.35, local_target_factor=1),
                      dict(iterations=8, fraction=.55, budget=.28, local_target_factor=2)],
        geometry_code_sha256=hashes, workflow=str(WORKFLOW), workflow_sha256=digest(WORKFLOW))
    root.mkdir(parents=True, exist_ok=True)
    write(root/'RECIPE_EARLY.json', recipes)
    save('G00_INPUT', mesh, chart, 'SPAN_SPARSE', parts,
         dict(recipe=input_recipe, source_input_recipe=original_recipe, subdivision_passes_total=0,
              input_carrier_bilinear_splits=0, field_passes_total=0))

    mesh, chart, state, metadata = ancestry_field(mesh, chart, 1, selected['G01_ANCESTRY'])
    save('G01_ANCESTRY', mesh, chart, 'ANCESTRY_STAGED', state, metadata, 'G00_INPUT')
    del state
    mesh, chart, state, metadata = ancestry_field(mesh, chart, 2, selected['G02_OVERLAP'])
    save('G02_OVERLAP', mesh, chart, 'OVERLAP', state, metadata, 'G01_ANCESTRY')
    del state
    mesh, chart, state, metadata, guides, rails = wall_stage(mesh, chart)
    save('G03_WALL', mesh, chart, 'WALL', state, metadata, 'G02_OVERLAP', guides=guides, rails=rails)
    del state, guides, rails

    source_surface = mesh.surface
    mesh, chart, events, evidence = core.patch_growth.build(mesh, chart, 'ROOT_ONLY')
    accepted = sum(event['status'] == 'accepted' for event in events)
    if accepted != 1:
        raise ValueError('The unchanged ROOT_ONLY recipe did not produce its one canonical root.')
    metadata = dict(event_recipe=core.patch_growth.RECIPE, source_surface=source_surface,
        added_topology_events=accepted, constructive_event_count=accepted,
        reflected_constructive_event_instances=4*accepted,
        accepted_canonical_events_by_level=[1, 0, 0], added_field_passes=0,
        added_mandelbulb_evaluations=0, subdivision_passes_added=0)
    evidence = save('G03_ROOT', mesh, chart, 'ROOT_ONLY', evidence, metadata, 'G03_WALL')
    write(folders['G03_ROOT']/'events.json', events)
    records['G03_ROOT']['events_file_sha256'] = digest(folders['G03_ROOT']/'events.json')
    write(folders['G03_ROOT']/'generation.json', records['G03_ROOT'])
    nodes[-1]['generation_json_sha256'] = digest(folders['G03_ROOT']/'generation.json')

    mesh, chart, events, evidence = sidewall.build(mesh, chart, evidence, events)
    accepted = sum(event['status'] == 'accepted' for event in events)
    if accepted != 3 or not np.array_equal(evidence['accepted_event_counts_by_level'], [1, 3, 0]):
        raise ValueError('The unchanged SIDEWALL_FAN recipe did not produce its three canonical sidewalls.')
    metadata = dict(event_recipe=sidewall.RECIPE, source_surface='mean',
        added_topology_events=accepted, constructive_event_count=1+accepted,
        inherited_canonical_root_events=1, new_canonical_sidewall_events=accepted,
        reflected_constructive_event_instances=4*(1+accepted),
        reflected_new_sidewall_event_instances=4*accepted,
        accepted_canonical_events_by_level=[1, accepted, 0], added_field_passes=0,
        added_mandelbulb_evaluations=0, subdivision_passes_added=0)
    evidence = save('G03_SIDEWALL', mesh, chart, 'SIDEWALL_FAN', evidence, metadata, 'G03_ROOT')
    write(folders['G03_SIDEWALL']/'events.json', events)
    records['G03_SIDEWALL']['events_file_sha256'] = digest(folders['G03_SIDEWALL']/'events.json')
    write(folders['G03_SIDEWALL']/'generation.json', records['G03_SIDEWALL'])
    nodes[-1]['generation_json_sha256'] = digest(folders['G03_SIDEWALL']/'generation.json')

    parent_faces = mesh.faces
    parent_pairs = _pairs(mesh, chart, evidence)
    mesh, chart, refinement = core.refine(mesh, chart)
    pairs = {axis: mirror.refine_mirror_pairs(parent_faces, refinement['input_edges'], pair)
             for axis, pair in parent_pairs.items()}
    if mesh.generation != 4:
        raise ValueError('Neutral refinement must produce actual G4.')
    save('G04_NEUTRAL', mesh, chart, 'SIDEWALL_FAN', refinement,
         dict(neutral_CC_passes_added=1, added_CC_passes=1, added_topology_events=0,
              added_field_passes=0, added_mandelbulb_evaluations=0,
              parent=str(folders['G03_SIDEWALL'])), 'G03_SIDEWALL', pairs=pairs)
    if hashes != code_hashes():
        raise ValueError('Actual early geometry source changed during transfer.')
    write(root/'STAGES_EARLY.json', dict(schema='CHESHIRE_RECIPE_TRANSFER_EARLY_STAGES_V1',
          input_case=INPUT_CASE, status='PASS', stages=nodes, geometry_code_sha256=hashes,
          scope='One input change and fixed G0--G4 recipe; visual transfer not assessed'))
    del mesh, chart, evidence, refinement, parent_faces, parent_pairs
    gc.collect()
    return dict(folders=folders, recipes=recipes, geometry_code_sha256=hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    build(args.root, RADIUS_SCALE_PROFILE)


if __name__ == '__main__':
    main()
