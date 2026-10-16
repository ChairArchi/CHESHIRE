"""Regenerate the selected late fold recipe on actual new early-generation parents.

The candidate directory must contain verified ``states/G03_SIDEWALL`` and
``states/G04_NEUTRAL`` controls/evidence.  An ancestry vector is consumed at its
actual saved length; there is no historical face-count, atlas, or old-XYZ
pullback.  G5/G6 normals, local scales and directional fields are recomputed by
the existing operators.  Their root phase frame is explicitly the inherited
real root frame, which may precede the new G3 macro deformation.

Run one stage per subprocess to release dense arrays.  G06_MIDDLE and G07_FINAL
save native arithmetic-centre fans; the other late checkpoints save controls
and evidence.  ``--native`` also stores native fans for a requested intermediate.
``--check-input`` reads and validates the actual G3/G4 without writing outputs.
This is an exploratory visual prototype, not an intersection/printing certificate.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCHEMA = 'CHESHIRE_EARLY_DYNAMIC_ACTUAL_PARENT_LATE_REPLAY_V1'
PAIR_KEYS = ('mirror_x_vertex_pairs', 'mirror_y_vertex_pairs',
             'mirror_x_face_pairs', 'mirror_y_face_pairs')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


late = module('early_dynamic_frozen_late_recipe',
              HERE.parent/'recipe_transfer_20261013/late.py')
STAGES = late.STAGES


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def folder(root, stage):
    return Path(root)/'states'/stage


def checked_files(root, stage):
    path = folder(root, stage)
    info = read(path/'generation.json')
    if not info.get('checks', {}).get('passed', False):
        raise ValueError('Actual parent integrity is not passed: '+stage)
    for filename, key in (('control_quad.npz', 'control_file_sha256'),
                          ('evidence.npz', 'evidence_file_sha256')):
        if key not in info or sha(path/filename) != info[key]:
            raise ValueError('Actual parent file is not hash bound: '+stage+'/'+filename)
    return info


def load(root, stage):
    """Load one verified actual parent; never import historical geometry."""
    path = folder(root, stage)
    info = checked_files(root, stage)
    data = late.arrays(path/'control_quad.npz')
    required = ('xyz', 'faces', 'chart', 'classes', 'rest', 'anchors',
                'generation', 'surface')
    if any(key not in data for key in required):
        raise ValueError('Incomplete actual control associations: '+stage)
    mesh = late.core.ArrayMesh(data['xyz'], data['faces'], data['classes'],
                              data['rest'], data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    chart = data['chart']
    if (mesh.generation != info['subdivision_generation'] or
            mesh.xyz.ndim != 2 or mesh.xyz.shape[1] != 3 or
            chart.shape != mesh.xyz.shape or not np.isfinite(mesh.xyz).all() or
            not np.isfinite(chart).all() or mesh.faces.ndim != 2 or
            mesh.faces.shape[1] != 4 or mesh.faces.dtype.kind not in 'iu' or
            not mesh.faces.size or mesh.faces.min() < 0 or
            mesh.faces.max() >= len(mesh.xyz)):
        raise ValueError('Invalid actual generation/controls/chart: '+stage)
    for key, value in (('control_xyz_sha256', mesh.xyz),
                       ('control_faces_sha256', mesh.faces), ('chart_sha256', chart)):
        expected = info['checks'].get(key)
        if expected is not None and ah(value) != expected:
            raise ValueError('Actual parent array hash differs: '+stage+'/'+key)
    return mesh, chart, info


def code_hashes():
    """Bind all transitive experiment/source modules loaded by the old adapter."""
    paths = {Path(__file__).resolve()}
    for obj in tuple(sys.modules.values()):
        filename = getattr(obj, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        try:
            rel = path.relative_to(REPO)
        except ValueError:
            continue
        if path.suffix == '.py' and rel.parts[0] in ('experiments', 'src'):
            paths.add(path)
    return {path.relative_to(REPO).as_posix(): sha(path) for path in sorted(paths)}


def input_proof(root, evaluate_fields=False):
    """Check actual ancestry, explicit involutions, and inherited root inputs."""
    mesh3, chart3, info3 = load(root, 'G03_SIDEWALL')
    mesh4, chart4, info4 = load(root, 'G04_NEUTRAL')
    if mesh3.generation != 3 or mesh4.generation != 4:
        raise ValueError('Actual G3 and G4 required; path relabelling is forbidden.')
    g3 = late.evidence(root, 'G03_SIDEWALL')
    g4 = late.evidence(root, 'G04_NEUTRAL', ('parent_face', 'input_edges'))
    parent = late.fold5._int_vector(g4, 'parent_face', len(mesh4.faces))
    owners = late.fold5._int_vector(g3, 'face_event_ids', len(mesh3.faces))
    roles = late.fold5._int_vector(g3, 'face_roles', len(mesh3.faces))
    if (parent.min() < 0 or parent.max() >= len(mesh3.faces) or
            np.any(owners < 0) or not np.isin(roles, [0, 1, 2]).all() or
            not np.array_equal(owners > 0, roles > 0)):
        raise ValueError('Actual G4 -> G3 ownership/role ancestry differs.')
    # One actual neutral CC step must record each parent's four children.
    counts = np.bincount(parent, minlength=len(mesh3.faces))
    if not np.all(counts == 4):
        raise ValueError('G4 ancestry is not an actual complete four-child split.')
    root_frame, radius, _basis = late.fold5._root_frame(g3)
    actual_pairs3 = late.pairs(root, 'G03_SIDEWALL', mesh3)
    actual_pairs4 = late.pairs(root, 'G04_NEUTRAL', mesh4)
    proof3 = late.loader.actual_symmetry(mesh3, actual_pairs3)
    proof4 = late.loader.actual_symmetry(mesh4, actual_pairs4)
    for label in ('x', 'y'):
        key = 'mirror_'+label+'_vertex_pairs'
        propagated = late.mirror.refine_mirror_pairs(mesh3.faces, g4['input_edges'],
                                                   actual_pairs3[key])
        if not np.array_equal(propagated, actual_pairs4[key]):
            raise ValueError('Actual G4 reflection IDs do not descend from actual G3.')
    result = dict(
        schema=SCHEMA, status='PASS',
        g3=dict(folder=str(folder(root, 'G03_SIDEWALL')),
                control_sha256=info3['control_file_sha256'],
                evidence_sha256=info3['evidence_file_sha256'],
                generation_json_sha256=sha(folder(root, 'G03_SIDEWALL')/'generation.json'),
                vertices=len(mesh3.xyz), quads=len(mesh3.faces), symmetry=proof3),
        g4=dict(folder=str(folder(root, 'G04_NEUTRAL')),
                control_sha256=info4['control_file_sha256'],
                evidence_sha256=info4['evidence_file_sha256'],
                generation_json_sha256=sha(folder(root, 'G04_NEUTRAL')/'generation.json'),
                vertices=len(mesh4.xyz), quads=len(mesh4.faces), symmetry=proof4),
        candidate=info4.get('dynamic_candidate', info4.get('candidate', root.name)),
        inherited_root_radius=radius,
        inherited_root_frame={key: value.tolist() for key, value in root_frame.items()},
        phase_frame_scope='Inherited actual root PCA from the early constructive event; not a post-macro PCA fit. G5/G6 actual incoming centroids, normals and local scales are recomputed.',
        supported_g3_faces=int(np.count_nonzero(owners)),
        four_actual_children_per_parent=True,
        fixed_atlas_or_historical_face_count_assumed=False,
        old_final_xyz_read_or_pulled_back=False,
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    if evaluate_fields:
        controls, fields = late.fold5.resolved_fields(mesh4, g4, g3, 'DIRECTIONAL')
        result['evaluated_actual_g4_fields'] = dict(
            passed=all(np.isfinite(value).all() for value in controls.values()),
            supported_faces=int(np.count_nonzero(fields['input_face_support'])),
            actual_normals_sha256=ah(fields['input_face_normals']),
            actual_phase_sha256=ah(fields['face_phase']),
            scalar_range=[float(fields['face_scalar'].min()), float(fields['face_scalar'].max())],
            geometry_generated=False)
    del mesh3, mesh4, chart3, chart4, g3, g4, actual_pairs3, actual_pairs4
    gc.collect()
    return result


def prepare(root):
    """Freeze code and verified actual parents in a separate late receipt."""
    proof = input_proof(root)
    recipe = dict(
        schema=SCHEMA, candidate=proof['candidate'], actual_input=proof,
        fixed_late_recipe_checks=late.recipe_proof(), geometry_code_sha256=code_hashes(),
        stage_order=list(STAGES), native_default_stages=['G06_MIDDLE', 'G07_FINAL'],
        algorithms='Existing directional coupled G4->G5, half-period G5->G6, whole-column MIDDLE, then optional existing linked/medium/small G7 sequence.',
        geometry_scope='Actual early candidate G4 controls -> new descendants. No old final mesh, old displacement pullback, synthetic chart atlas, whole-geometry averaging, new Mandelbulb pass, or Tissue invocation.',
        phase_frame_scope=proof['phase_frame_scope'],
        limitations=['Visual prototype; native closed-manifold integrity does not establish collision freedom.',
                     'Mandelbulb and full-XYZ Tissue ornaments are a separate subsequent adapter.',
                     'Global X/Y reflection corresponds to actual saved IDs; local symmetry variations belong to the early candidate.'])
    early_recipe = root/'RECIPE.json'
    if early_recipe.exists():
        recipe['early_recipe_sha256'] = sha(early_recipe)
    target = root/'LATE_RECIPE.json'
    if target.exists():
        if read(target) != recipe:
            raise FileExistsError('Frozen late recipe differs; preserve this candidate and use a new root.')
    else:
        late.core.write(target, recipe)
    for rel, expected in recipe['geometry_code_sha256'].items():
        source, dest = REPO/rel, root/'late_source_snapshot'/rel
        if dest.exists():
            if sha(dest) != expected:
                raise ValueError('Frozen late source snapshot changed: '+rel)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
    return recipe


def check_binding(root):
    recipe = read(root/'LATE_RECIPE.json')
    if recipe['schema'] != SCHEMA:
        raise ValueError('Different late pipeline schema.')
    for rel, expected in recipe['geometry_code_sha256'].items():
        if sha(REPO/rel) != expected or sha(root/'late_source_snapshot'/rel) != expected:
            raise ValueError('Executed late source or snapshot changed: '+rel)
    if 'early_recipe_sha256' in recipe and sha(root/'RECIPE.json') != recipe['early_recipe_sha256']:
        raise ValueError('Early candidate recipe changed during late regeneration.')
    for stage, key in (('G03_SIDEWALL', 'g3'), ('G04_NEUTRAL', 'g4')):
        proof = recipe['actual_input'][key]
        if (sha(folder(root, stage)/'control_quad.npz') != proof['control_sha256'] or
                sha(folder(root, stage)/'evidence.npz') != proof['evidence_sha256'] or
                sha(folder(root, stage)/'generation.json') != proof['generation_json_sha256']):
            raise ValueError('Actual early candidate parent changed: '+stage)
    return recipe


def bind(root, stage, source, metadata, split=0, normal=0, cumulative=0,
         smoothing=0, raw=None):
    parent = checked_files(root, source)
    recipe = read(root/'LATE_RECIPE.json')
    source_path = folder(root, source)
    result = dict(
        input_case=parent.get('input_case', 'EARLY_DYNAMIC'),
        candidate=recipe['candidate'], dynamic_candidate=recipe['candidate'],
        stage_id=stage, late_pipeline_schema=SCHEMA,
        source=str(source_path), parent_stage=str(source_path),
        source_generation=parent['subdivision_generation'],
        source_control_sha256=parent['control_file_sha256'],
        source_evidence_sha256=parent['evidence_file_sha256'],
        source_generation_json_sha256=sha(source_path/'generation.json'),
        parent_control_sha256=parent['control_file_sha256'],
        parent_generation_json_sha256=sha(source_path/'generation.json'),
        geometry_code_sha256=recipe['geometry_code_sha256'],
        late_recipe_sha256=sha(root/'LATE_RECIPE.json'),
        operator_metadata=metadata, added_subdivision_passes=split,
        added_CC_passes=split, added_topology_events=0,
        added_mandelbulb_evaluations=0, added_tissue_invocations=0,
        added_normal_field_passes=normal, cumulative_normal_field_passes=cumulative,
        smoothing_passes_this_stage=smoothing,
        baseline_geometry_averaged=False,
        recipe_scope=recipe['geometry_scope'], phase_frame_scope=recipe['phase_frame_scope'],
        actual_new_early_parents=recipe['actual_input'],
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED',
        visual_success='NOT_ASSESSED')
    if raw is not None:
        raw_path = folder(root, raw)
        raw_info = checked_files(root, raw)
        result.update(raw_field_stage=str(raw_path),
                      raw_field_control_sha256=raw_info['control_file_sha256'],
                      raw_field_generation_json_sha256=sha(raw_path/'generation.json'))
    return result


FORCE_NATIVE = False


def save(root, stage, mesh, chart, state, context, native=True):
    """Store real controls/evidence and explicitly requested native geometry."""
    dest = folder(root, stage)
    if dest.exists():
        raise FileExistsError('Actual stage is immutable: '+str(dest))
    proof = late.loader.actual_symmetry(mesh, state)
    context = dict(context, symmetry=proof)
    native = FORCE_NATIVE or stage in ('G06_MIDDLE', 'G07_FINAL')
    if native:
        record = late.core.save(dest, mesh, chart, context, state)
    else:
        finite = bool(np.isfinite(mesh.xyz).all() and np.isfinite(chart).all())
        if not finite:
            raise ValueError('Nonfinite actual intermediate.')
        if any(np.asarray(value).dtype == object for value in state.values()):
            raise ValueError('Evidence must be NPZ-safe actual arrays.')
        dest.mkdir(parents=True)
        np.savez_compressed(dest/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
            chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
            generation=np.array(mesh.generation), surface=np.array(mesh.surface))
        np.savez_compressed(dest/'evidence.npz', **state)
        record = dict(context, subdivision_generation=int(mesh.generation),
            checkpoint_kind='CONTROL_AND_EVIDENCE_ONLY',
            native_surface='NOT_STORED_INTERMEDIATE', control_vertices=len(mesh.xyz),
            control_quads=len(mesh.faces),
            control_file_sha256=sha(dest/'control_quad.npz'),
            evidence_file_sha256=sha(dest/'evidence.npz'),
            checks=dict(passed=finite and proof['passed'], finite=finite,
                control_xyz_sha256=ah(mesh.xyz), control_faces_sha256=ah(mesh.faces),
                chart_sha256=ah(chart),
                scope='Finite actual controls and actual oriented-quad/XYZ reflection. Native fans/area are checked at G6_MIDDLE and G7_FINAL.'),
            visual_success='NOT_ASSESSED')
        late.core.write(dest/'generation.json', record)
        print('SAVED CONTROL-ONLY', stage, 'G', mesh.generation, flush=True)
    # Read back the actual arrays rather than relying on the write succeeding.
    loaded_mesh, loaded_chart, _info = load(root, stage)
    if (not np.array_equal(loaded_mesh.xyz, mesh.xyz) or
            not np.array_equal(loaded_mesh.faces, mesh.faces) or
            not np.array_equal(loaded_chart, chart)):
        raise ValueError('Actual saved control readback differs: '+stage)
    return record


# The established functions evaluate actual new parents after rebinding only
# their orchestration/load/save functions. Their geometric code is unchanged.
late.load = load
late.bind = bind
late.save = save


def run(root, stage, native=False):
    global FORCE_NATIVE
    root = Path(root).resolve()
    FORCE_NATIVE = bool(native)
    if folder(root, stage).exists():
        raise FileExistsError('Actual saved stage is immutable: '+stage)
    if not (root/'LATE_RECIPE.json').exists():
        prepare(root)
    recipe = check_binding(root)
    late.recipe_proof()
    started = time.perf_counter()
    if stage in ('G05_DIRECTIONAL', 'G06_DEPTH08'):
        late.directional(root, stage)
    elif stage == 'G06_MIDDLE':
        late.middle(root)
    elif stage == 'G07_SURFACE':
        late.surface(root)
    elif stage in ('G07_LINKED_RAW', 'G07_WIDE_RAW'):
        late.fields(root, stage)
    else:
        late.filter_saved(root, stage)
    check_binding(root)
    record = read(folder(root, stage)/'generation.json')
    receipt = dict(schema=SCHEMA, status='PASS', stage=stage,
                   elapsed_seconds=time.perf_counter()-started,
                   late_recipe_sha256=sha(root/'LATE_RECIPE.json'),
                   generation_json_sha256=sha(folder(root, stage)/'generation.json'),
                   actual_control_sha256=record['control_file_sha256'],
                   actual_evidence_sha256=record['evidence_file_sha256'],
                   actual_input=recipe['actual_input'],
                   native_geometry_stored=(folder(root, stage)/'geometry.npz').exists(),
                   old_final_xyz_read_or_pulled_back=False,
                   visual_success='NOT_ASSESSED',
                   self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    late.core.write(folder(root, stage)/'LATE_EXECUTION_RECEIPT.json', receipt)
    print('DONE ACTUAL-PARENT LATE', stage,
          'seconds='+str(round(receipt['elapsed_seconds'], 3)), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--stage', choices=STAGES)
    choice.add_argument('--check-input', action='store_true')
    parser.add_argument('--native', action='store_true',
                        help='Also save native fans at this intermediate stage.')
    args = parser.parse_args()
    if args.check_input:
        print(json.dumps(input_proof(args.root.resolve(), evaluate_fields=True),
                         ensure_ascii=False, indent=2, allow_nan=False))
    else:
        run(args.root, args.stage, native=args.native)


if __name__ == '__main__':
    main()
