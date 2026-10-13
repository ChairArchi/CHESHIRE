"""Continue one new input through the unchanged selected G5--G7 recipe.

This adapter replaces historical fixed file paths with actual new parents.
All geometric build functions and their coefficients are reused unchanged.
G7 intermediate checkpoints save controls/evidence; the final saves native
triangles. One subprocess per stage releases dense arrays between operations.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


core = module('transfer_late_core', HERE.parent/'connected_fold_growth_20261012/study.py')
loader = module('transfer_late_actual_mirror', HERE.parent/'design_one_20261013/study.py')
finish = module('transfer_late_cc_finish', HERE.parent/'whole_column_detail_20261013/finish_surface.py')
fold5 = module('transfer_late_directional_g5', HERE.parent/'coherent_fold_detail_20261013/fold_operator.py')
fold6 = module('transfer_late_directional_g6', HERE.parent/'directional_g6_20261013/g6_operator.py')
whole = module('transfer_late_middle', HERE.parent/'whole_column_detail_20261013/whole_field.py')
linked = module('transfer_late_connected_ribs', HERE.parent/'parent_linked_folds_20261013/connected_ribs.py')
wide = module('transfer_late_medium_root', HERE.parent/'medium_root_folds_20261013/root_folds.py')
mirror = loader.mirror
PAIR_KEYS = ('mirror_x_vertex_pairs', 'mirror_y_vertex_pairs', 'mirror_x_face_pairs', 'mirror_y_face_pairs')
STAGES = ('G05_DIRECTIONAL', 'G06_DEPTH08', 'G06_MIDDLE', 'G07_SURFACE',
    'G07_LINKED_RAW', 'G07_LINKED_FINISHED', 'G07_WIDE_RAW', 'G07_FINAL')


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


def arrays(path, keys=None):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in (data.files if keys is None else keys)}


def folder(root, stage):
    return root/'states'/stage


def load(root, stage):
    path = folder(root, stage)
    info = read(path/'generation.json')
    if info['input_case'] != 'WAIST_FULL' or not info['checks']['passed']:
        raise ValueError('Verified actual new input required: '+stage)
    if sha(path/'control_quad.npz') != info['control_file_sha256']:
        raise ValueError('Actual new control file changed: '+stage)
    data = arrays(path/'control_quad.npz')
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if mesh.generation != info['subdivision_generation']:
        raise ValueError('Actual saved subdivision differs.')
    return mesh, data['chart'], info


def evidence(root, stage, keys=None):
    return arrays(folder(root, stage)/'evidence.npz', keys)


def pairs(root, stage, mesh):
    path = folder(root, stage)/'evidence.npz'
    with np.load(path, allow_pickle=False) as data:
        if all(key in data.files for key in PAIR_KEYS):
            return {key: data[key] for key in PAIR_KEYS}
    if stage != 'G04_NEUTRAL':
        raise ValueError('Actual propagated reflection IDs missing: '+stage)
    # G4 original evidence may contain only the actual CC ancestry. Propagate
    # from the newly constructed G3, never from historical SPAN IDs or chart.
    g3 = evidence(root, 'G03_SIDEWALL', PAIR_KEYS[:2])
    faces3 = arrays(folder(root, 'G03_SIDEWALL')/'control_quad.npz', ('faces',))['faces']
    edges4 = evidence(root, stage, ('input_edges',))['input_edges']
    result = {}
    for label in ('x', 'y'):
        key = 'mirror_'+label+'_vertex_pairs'
        vp = mirror.refine_mirror_pairs(faces3, edges4, g3[key])
        result[key] = vp
        result['mirror_'+label+'_face_pairs'] = mirror.face_involution(mesh.faces, vp)
    return result


def propagate(mesh, state, incoming_pairs):
    result = {}
    for label in ('x', 'y'):
        vp = incoming_pairs['mirror_'+label+'_vertex_pairs']
        fp = incoming_pairs['mirror_'+label+'_face_pairs']
        result['mirror_'+label+'_vertex_pairs'] = mirror.refine_mirror_pairs(mesh.faces, state['input_edges'], vp)
        result['mirror_'+label+'_face_pairs'] = finish.child_face_pairs(mesh.faces, state, vp, fp)
    return result


def carry(values, edges, faces):
    return np.concatenate([values, values[edges].mean(axis=1), values[faces].mean(axis=1)])


def bind(root, stage, source, metadata, split=0, normal=0, cumulative=0, smoothing=0, raw=None):
    src = folder(root, source)
    info = read(src/'generation.json')
    result = dict(input_case='WAIST_FULL', candidate=stage, stage_id=stage,
        source=str(src), source_generation=info['subdivision_generation'],
        source_control_sha256=info['control_file_sha256'],
        source_generation_json_sha256=sha(src/'generation.json'),
        parent_stage=str(src), parent_control_sha256=info['control_file_sha256'],
        parent_generation_json_sha256=sha(src/'generation.json'),
        geometry_code_sha256=read(root/'RECIPE.json')['geometry_code_sha256'],
        operator_metadata=metadata, added_subdivision_passes=split,
        added_CC_passes=split, added_topology_events=0, added_mandelbulb_evaluations=0,
        added_normal_field_passes=normal, cumulative_normal_field_passes=cumulative,
        smoothing_passes_this_stage=smoothing,
        recipe_scope='Unchanged selected original geometric operators and coefficients; only G0 radius profile differs.',
        validation_scope='Actual new parent hashes and reflection IDs; one native integrity check per rendered stage. G7 intermediate control checkpoints explicitly omit native meshes.',
        exclusions=['Parameter retuning', 'New geometric algorithm', 'Full independent replay',
            'Native triangle-set sorting', 'Self-intersection repair', 'Fabrication certification'])
    if raw is not None:
        p = folder(root, raw)
        r = read(p/'generation.json')
        result.update(raw_field_stage=str(p), raw_field_control_sha256=r['control_file_sha256'],
            raw_field_generation_json_sha256=sha(p/'generation.json'))
    return result


def save(root, stage, mesh, chart, state, context, native=True):
    dest = folder(root, stage)
    if dest.exists():
        raise FileExistsError('Preserved actual stage: '+str(dest))
    proof = loader.actual_symmetry(mesh, state)
    context = dict(context, symmetry=proof)
    if native:
        record = core.save(dest, mesh, chart, context, state)
    else:
        finite = bool(np.isfinite(mesh.xyz).all())
        if not finite:
            raise ValueError('Nonfinite control-only intermediate.')
        dest.mkdir(parents=True)
        np.savez_compressed(dest/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
            chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
            generation=np.array(mesh.generation), surface=np.array(mesh.surface))
        np.savez_compressed(dest/'evidence.npz', **state)
        record = dict(context, subdivision_generation=int(mesh.generation),
            checkpoint_kind='CONTROL_AND_EVIDENCE_ONLY', native_surface='NOT_STORED_INTERMEDIATE',
            control_vertices=len(mesh.xyz), control_quads=len(mesh.faces),
            control_file_sha256=sha(dest/'control_quad.npz'), evidence_file_sha256=sha(dest/'evidence.npz'),
            checks=dict(passed=finite and proof['passed'], finite=finite,
                control_xyz_sha256=ah(mesh.xyz), control_faces_sha256=ah(mesh.faces), chart_sha256=ah(chart),
                scope='Finite actual controls and actual XYZ/oriented quad reflection; topology follows unchanged verified operators. Native mesh/area not checked at this intermediate.'),
            visual_success='NOT_ASSESSED')
        core.write(dest/'generation.json', record)
        print('SAVED CONTROL-ONLY', stage, 'G', mesh.generation, flush=True)
    return record


def directional(root, stage):
    source = 'G04_NEUTRAL' if stage == 'G05_DIRECTIONAL' else 'G05_DIRECTIONAL'
    mesh, chart, parent = load(root, source)
    old_pairs = pairs(root, source, mesh)
    g3 = evidence(root, 'G03_SIDEWALL')
    g4 = evidence(root, 'G04_NEUTRAL', ('parent_face', 'input_edges'))
    if stage == 'G05_DIRECTIONAL':
        out, meta, state = fold5.build(mesh, g4, g3, 'DIRECTIONAL')
    else:
        g5 = evidence(root, source, ('parent_face', 'input_edges'))
        out, meta, state = fold6.build(mesh, g5, g4, g3, 'DEPTH_08')
    edges = state['input_edges']
    outchart = carry(chart, edges, mesh.faces)
    state.update(propagate(mesh, state, old_pairs))
    del g3, g4, old_pairs
    gc.collect()
    save(root, stage, out, outchart, state, bind(root, stage, source, meta, split=1))


def middle(root):
    stage, source = 'G06_MIDDLE', 'G06_DEPTH08'
    mesh, chart, parent = load(root, source)
    state6 = evidence(root, source, ('input_face_support', 'parent_face'))
    face_support = state6['input_face_support'][state6['parent_face']]
    degree = np.bincount(mesh.faces.ravel(), minlength=len(mesh.xyz))
    support = np.bincount(mesh.faces.ravel(), weights=np.repeat(face_support, 4), minlength=len(mesh.xyz))/degree
    actual_pairs = pairs(root, source, mesh)
    vp = dict(X=actual_pairs['mirror_x_vertex_pairs'], Y=actual_pairs['mirror_y_vertex_pairs'])
    out, meta, state = whole.build(mesh, chart, vp, support, 'MIDDLE')
    state.update(actual_pairs)
    lo, hi = meta['actual_input_z_bounds']
    state['frame_normalized_z'] = (mesh.xyz[:, 2]-lo)/(hi-lo)
    del state6, degree, face_support, support
    gc.collect()
    save(root, stage, out, chart, state, bind(root, stage, source, meta, normal=1, cumulative=1))


def surface(root):
    stage, source = 'G07_SURFACE', 'G06_MIDDLE'
    mesh, chart, parent = load(root, source)
    frame = evidence(root, source, ('directional_phase', 'feature_support', 'frame_normalized_z'))
    actual_pairs = pairs(root, source, mesh)
    finish.memory_guard()
    out, outchart, state = core.refine(mesh, chart)
    state.update(propagate(mesh, state, actual_pairs))
    edges = state['input_edges']
    phase = frame['directional_phase']
    state['parent_phase'] = np.arctan2(carry(np.sin(phase), edges, mesh.faces), carry(np.cos(phase), edges, mesh.faces))
    state['normalized_z'] = carry(frame['frame_normalized_z'], edges, mesh.faces)
    state['feature_support'] = carry(frame['feature_support'], edges, mesh.faces)
    meta = dict(implementation='REFERENCE_COUPLED_NEUTRAL_CC', weights={},
        physical_height=parent['operator_metadata']['physical_height'],
        frame_scope='Actual new MIDDLE phase/support/z through actual new CC V/E/F IDs; no historical SPAN frame imported.')
    del mesh, chart, frame, actual_pairs, edges, phase
    gc.collect()
    save(root, stage, out, outchart, state, bind(root, stage, source, meta, split=1, cumulative=1), native=False)


def fields(root, stage):
    source = 'G07_SURFACE' if stage == 'G07_LINKED_RAW' else 'G07_LINKED_FINISHED'
    mesh, chart, parent = load(root, source)
    actual_pairs = pairs(root, source, mesh)
    frame = evidence(root, 'G07_SURFACE', ('parent_phase', 'normalized_z', 'feature_support'))
    height = read(folder(root, 'G07_SURFACE')/'generation.json')['operator_metadata']['physical_height']
    vp = dict(X=actual_pairs['mirror_x_vertex_pairs'], Y=actual_pairs['mirror_y_vertex_pairs'])
    finish.memory_guard()
    op = linked if stage == 'G07_LINKED_RAW' else wide
    out, meta, state = op.build(mesh, chart, vp, frame['parent_phase'], frame['normalized_z'], frame['feature_support'], height)
    state.update({key: actual_pairs[key] for key in PAIR_KEYS[2:]})
    cumulative = 3 if stage == 'G07_LINKED_RAW' else 5
    smoothing = 0 if stage == 'G07_LINKED_RAW' else 4
    del mesh, actual_pairs, frame, vp
    gc.collect()
    save(root, stage, out, chart, state, bind(root, stage, source, meta, normal=2,
        cumulative=cumulative, smoothing=smoothing), native=False)


def filter_saved(root, stage):
    if stage == 'G07_LINKED_FINISHED':
        source, raw_stage, cumulative = 'G07_SURFACE', 'G07_LINKED_RAW', 3
    else:
        source, raw_stage, cumulative = 'G07_LINKED_FINISHED', 'G07_WIDE_RAW', 5
    mesh, chart, parent = load(root, source)
    raw_info = read(folder(root, raw_stage)/'generation.json')
    if sha(folder(root, raw_stage)/'control_quad.npz') != raw_info['control_file_sha256']:
        raise ValueError('Actual raw dependency changed.')
    raw_xyz = arrays(folder(root, raw_stage)/'control_quad.npz', ('xyz',))['xyz']
    if raw_xyz.shape != mesh.xyz.shape:
        raise ValueError('Same-topology delta finish requires matching controls.')
    raw_faces_hash = raw_info['checks']['control_faces_sha256']
    if raw_faces_hash != ah(mesh.faces):
        raise ValueError('Actual raw/baseline faces differ.')
    actual_pairs = pairs(root, source, mesh)
    unfiltered = raw_xyz-mesh.xyz
    del raw_xyz
    degree = np.bincount(mesh.faces.ravel(), minlength=len(mesh.xyz))
    finish.memory_guard()
    delta = unfiltered
    for index in range(3):
        print(stage, 'SAVED DELTA FILTER', index+1, '/ 3', flush=True)
        delta = wide.finish.uniform_displacement_pass(delta, mesh.faces, degree)
    vp = dict(X=actual_pairs['mirror_x_vertex_pairs'], Y=actual_pairs['mirror_y_vertex_pairs'])
    ids, pp = whole._mirror_pairs(vp, len(mesh.xyz))
    filtered, representative, fixed_x, fixed_y = whole._transport(delta, ids, pp)
    del delta, ids, pp, representative, fixed_x, fixed_y, degree
    out = core.ArrayMesh(mesh.xyz+filtered, mesh.faces, mesh.classes, mesh.rest, mesh.anchors, 7)
    out.surface = 'mean'
    state = dict(unfiltered_delta=unfiltered, filtered_delta=filtered, **actual_pairs)
    meta = dict(finish_iterations=3, alpha=.5, equation='delta_next=.5*delta+.5*uniform_actual_edge_neighbor_mean(delta)',
        baseline_geometry_filtered=False, amplitude_multiplier_applied=False,
        input_xyz_sha256=ah(mesh.xyz), raw_xyz_sha256=raw_info['checks']['control_xyz_sha256'],
        output_xyz_sha256=ah(out.xyz), normal_fields_computed_this_finish=0,
        before=wide.finish.displacement_stats(unfiltered), after=wide.finish.displacement_stats(filtered))
    del mesh, actual_pairs, vp
    gc.collect()
    save(root, stage, out, chart, state, bind(root, stage, source, meta, cumulative=cumulative,
        smoothing=3, raw=raw_stage), native=stage == 'G07_FINAL')


def recipe_proof():
    base = REPO/'docs/generation_workflow_20261013/receipts'
    checks = {
        'g5_directional': fold5.RECIPE == read(base/'07_directional_g5.json')['coherent_rules'],
        'g6_depth08': fold6.RECIPE == read(base/'08_depth08_g6.json')['directional_rules'],
        'g6_middle': whole.RECIPE == read(base/'09_middle_g6.json')['operator_metadata']['recipe'],
        'g7_linked': linked.RECIPE == read(base/'11_linked_raw_g7.json')['operator_metadata']['recipe'],
        'g7_wide': wide.RECIPE == read(base/'13_wide_raw_g7.json')['operator_metadata']['recipe'],
        'saved_delta_finish': wide.finish.ITERATIONS == 3 and wide.finish.ALPHA == .5,
    }
    if not all(checks.values()):
        raise ValueError('Original selected recipe mismatch: '+str(checks))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--stage', choices=STAGES, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    recipe_proof()
    for name, expected in read(root/'RECIPE.json')['geometry_code_sha256'].items():
        if sha(REPO/name) != expected:
            raise ValueError('Frozen geometric source changed: '+name)
    if folder(root, args.stage).exists():
        raise FileExistsError('Existing stage is preserved.')
    print('TRANSFER unchanged recipe', args.stage, flush=True)
    if args.stage in ('G05_DIRECTIONAL', 'G06_DEPTH08'):
        directional(root, args.stage)
    elif args.stage == 'G06_MIDDLE':
        middle(root)
    elif args.stage == 'G07_SURFACE':
        surface(root)
    elif args.stage in ('G07_LINKED_RAW', 'G07_WIDE_RAW'):
        fields(root, args.stage)
    else:
        filter_saved(root, args.stage)
    print('DONE', args.stage, flush=True)


if __name__ == '__main__':
    main()
