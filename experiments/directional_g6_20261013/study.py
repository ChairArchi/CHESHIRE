"""One actual DIRECTIONAL G5 -> G6 CC step, at two normal amplitudes.

The half-period signed band and coherent normal compensation are CHESHIRE
hypotheses, not a reproduction of an external published sequence. This runner
does not execute on import. The parent decides whether to run the comparison.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARENT_ROOT = Path('E:/CHESHIRE_DATA/experiments/coherent_fold_detail_20261013/trial01')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/directional_g6_20261013/trial01')
BASE_COMMIT = '569c7b5ed763f39e5821640172ed3a02cf1d03ca'
CASES = ('SPAN', 'COUNTER')
TOLERANCE = 1e-9


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = load_module('directional_g6_frozen_core', HERE.parent/'connected_fold_growth_20261012/study.py')
mirror = load_module('directional_g6_frozen_mirror', HERE.parent/'connected_fold_growth_20261012/verify.py')
fold = load_module('directional_g6_actual_operator', HERE/'g6_operator.py')
digest, write = mirror.digest, core.write
MODES = fold.MODES
METHOD_SCOPE = ('CHESHIRE hypothesis: a half-period root-oriented signed band plus '
    'approximate coherent normal controls, evaluated on actual incoming G5 geometry; '
    'not an external published sequence reproduction or an exact curved-surface offset.')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def geometry_code_hashes():
    frozen = read_json(PARENT_ROOT/'RECIPE.json')['geometry_code_sha256']
    for name, checksum in frozen.items():
        if digest(REPO/name) != checksum:
            raise ValueError('Frozen parent generation code changed: '+name)
    if len(frozen) != 8:
        raise ValueError('Expected eight frozen coherent generation code files.')
    return dict(frozen, **{str(path.relative_to(REPO)): digest(path)
        for path in (HERE/'study.py', HERE/'g6_operator.py')})


def check_stage(source):
    folder = Path(source['path'])
    for filename, key in (('control_quad.npz', 'control_sha256'), ('geometry.npz', 'geometry_sha256'),
            ('evidence.npz', 'evidence_sha256'), ('generation.json', 'generation_sha256')):
        if digest(folder/filename) != source[key]:
            raise ValueError('Read-only source changed: '+str(folder/filename))


def stage_source(folder):
    info = read_json(folder/'generation.json')
    result = dict(path=str(folder), generation_sha256=digest(folder/'generation.json'))
    for filename, key, metadata_key in (
            ('control_quad.npz', 'control_sha256', 'control_file_sha256'),
            ('geometry.npz', 'geometry_sha256', 'geometry_file_sha256'),
            ('evidence.npz', 'evidence_sha256', 'evidence_file_sha256')):
        result[key] = digest(folder/filename)
        if result[key] != info[metadata_key]:
            raise ValueError('Preserved stage changed: '+str(folder/filename))
    return result


def source_index():
    proof_path, index_path, recipe_path = (PARENT_ROOT/name for name in
        ('VERIFICATION.json', 'source_index.json', 'RECIPE.json'))
    verified, inherited, parent_recipe = map(read_json, (proof_path, index_path, recipe_path))
    if (verified['status'] != 'PASS' or verified['expected_cases'] != list(CASES) or
            'DIRECTIONAL' not in verified['expected_modes'] or
            verified['source_index_sha256'] != digest(index_path)):
        raise ValueError('Exact verified two-input coherent DIRECTIONAL parent required.')
    hashes = geometry_code_hashes()
    sources = {}
    for case in CASES:
        source = stage_source(PARENT_ROOT/'DIRECTIONAL'/case/'G05')
        info = read_json(Path(source['path'])/'generation.json')
        proof = verified['cases'][case]['states']['DIRECTIONAL']
        g4 = inherited[case]
        if (proof['passed'] is not True or proof['actual_generation'] != 5 or
                proof['generation_json_sha256'] != source['generation_sha256'] or
                info['subdivision_generation'] != 5 or info['source_generation'] != 4 or
                info['candidate'] != 'DIRECTIONAL' or info['input_case'] != case or
                info['checks']['passed'] is not True or info['preserved_parent'] != g4 or
                info['source_control_sha256'] != g4['control_sha256'] or
                info['geometry_code_sha256'] != parent_recipe['geometry_code_sha256']):
            raise ValueError('Exact frozen actual DIRECTIONAL G5 lineage required: '+case)
        for generation, stage in ((4, g4), (3, g4['g3'])):
            check_stage(stage)
            stage_info = read_json(Path(stage['path'])/'generation.json')
            if (stage_info['subdivision_generation'] != generation or
                    stage_info['input_case'] != case or stage_info['candidate'] != 'SIDEWALL_FAN'):
                raise ValueError('Actual SIDEWALL_FAN G4/G3 ancestry required: '+case)
        sources[case] = dict(source, g4=g4, g3=g4['g3'],
            parent_verification=str(proof_path), parent_verification_sha256=digest(proof_path),
            parent_source_index=str(index_path), parent_source_index_sha256=digest(index_path),
            parent_recipe=str(recipe_path), parent_recipe_sha256=digest(recipe_path))
    if len(hashes) != 10:
        raise ValueError('Expected eight frozen plus two new geometry code files.')
    return sources


def load_arrays(path, keys=None):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in (data.files if keys is None else keys)}


def load_parent(source):
    check_stage(source); check_stage(source['g4']); check_stage(source['g3'])
    folder = Path(source['path'])
    data = load_arrays(folder/'control_quad.npz')
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if (mesh.generation != 5 or mesh.surface != 'mean' or mesh.faces.ndim != 2 or
            mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0) or
            data['chart'].shape != (len(mesh.xyz), 3)):
        raise ValueError('Actual frozen mean-native all-quad G5 and material chart required.')
    core.topology(mesh)
    g5 = load_arrays(folder/'evidence.npz', ('parent_face', 'input_edges'))
    g4 = load_arrays(Path(source['g4']['path'])/'evidence.npz', ('parent_face', 'input_edges'))
    keys = ('face_event_ids', 'mirror_face_signs', 'mirror_x_vertex_pairs', 'mirror_y_vertex_pairs',
        'inherited_root_radius', 'inherited_root_pca_origin', 'inherited_root_pca_major',
        'inherited_root_pca_minor', 'inherited_root_pca_normal', 'inherited_root_pca_extent')
    g3 = load_arrays(Path(source['g3']['path'])/'evidence.npz', keys)
    faces3 = load_arrays(Path(source['g3']['path'])/'control_quad.npz', ('faces',))['faces']
    faces4 = load_arrays(Path(source['g4']['path'])/'control_quad.npz', ('faces',))['faces']
    pairs = {}
    for axis, key in (('X', 'mirror_x_vertex_pairs'), ('Y', 'mirror_y_vertex_pairs')):
        pair4 = mirror.refine_mirror_pairs(faces3, g4['input_edges'], g3[key])
        pairs[axis] = mirror.refine_mirror_pairs(faces4, g5['input_edges'], pair4)
        mirror.involution(pairs[axis], len(mesh.xyz), axis+' actual G5 correspondence')
    return mesh, data['chart'], g5, g4, g3, pairs


def reflection_error(xyz, pair, coordinate):
    maximum = 0.
    for start in range(0, len(xyz), 120000):
        stop = min(start+120000, len(xyz))
        reflected = xyz[pair[start:stop]].copy()
        reflected[:, coordinate] *= -1.
        maximum = max(maximum, float(np.max(np.linalg.norm(xyz[start:stop]-reflected, axis=1), initial=0.)))
    if not np.isfinite(maximum) or maximum > TOLERANCE:
        raise ValueError('Actual XYZ reflection exceeds tolerance.')
    return maximum


def quick_symmetry(folder, mesh, incoming_faces, state, parent_pairs):
    """Actual XYZ plus oriented control quads; no native triangle-set sorting."""
    with np.load(folder/'geometry.npz', allow_pickle=False) as saved:
        xyz = saved['xyz']
    nv, nf = len(mesh.xyz), len(mesh.faces)
    if xyz.shape != (nv+nf, 3) or not np.array_equal(xyz[:nv], mesh.xyz):
        raise ValueError('Saved native XYZ must contain the actual control prefix.')
    for start in range(0, nf, 120000):
        stop = min(start+120000, nf)
        if not np.array_equal(xyz[nv+start:nv+stop], mesh.xyz[mesh.faces[start:stop]].mean(1)):
            raise ValueError('Saved native fan centres differ from actual quad means.')
    result = {}
    for axis, coordinate in (('X', 0), ('Y', 1)):
        pair = mirror.refine_mirror_pairs(incoming_faces, state['input_edges'], parent_pairs[axis])
        mirror.involution(pair, nv, axis+' actual G6 control correspondence')
        face_pair = mirror.face_involution(mesh.faces, pair, label=axis+' actual G6 oriented control faces')
        native_pair = np.r_[pair, nv+face_pair]
        result[axis] = dict(passed=True, actual_control_xyz_max_error=reflection_error(mesh.xyz, pair, coordinate),
            actual_native_xyz_max_error=reflection_error(xyz, native_pair, coordinate),
            oriented_control_faces_identical=True, tolerance=TOLERANCE,
            control_mirror_pair_sha256=core.array_hash(pair), face_mirror_pair_sha256=core.array_hash(face_pair))
        del pair, face_pair, native_pair
    return dict(passed=True, axes=result,
        saved_native_control_prefix_and_actual_quad_centres_exact=True,
        native_oriented_triangle_sets='NOT_INDEPENDENTLY_SORTED_THIS_QUICKCHECK',
        full_independent_geometry_replay='NOT_PERFORMED_THIS_ROUND',
        correspondence='Actual G3 explicit pairs propagated through actual G3/G4/G5 CC input_edges; oriented actual G6 control quads; saved native XYZ reflected with control and fan-centre pairs',
        verifier_helper_sha256=digest(HERE.parent/'connected_fold_growth_20261012/verify.py'))


def run_case(root, case, modes, source):
    core.memory_guard()
    hashes = geometry_code_hashes()
    mesh, chart, g5, g4, g3, pairs = load_parent(source)
    for mode in modes:
        folder = root/mode/case/'G06'
        if folder.exists():
            raise FileExistsError('Earlier result preserved: '+str(folder))
        out, metadata, state = fold.build(mesh, g5, g4, g3, mode)
        incoming = core.topology(mesh)
        face_chart = core.mean_incident(chart[incoming['a']], incoming['fi'], len(mesh.faces))
        outchart = np.concatenate([chart, chart[incoming['edges']].mean(1), face_chart])
        del incoming, face_chart
        if out.generation != 6:
            raise ValueError('Actual G6 output required; no generation relabelling.')
        out.surface = 'mean'
        state = dict(state, implementation=np.array('REFERENCE_COUPLED_DIRECTIONAL_G6_CC'),
            chart_scope=np.array('Linear V/E/F transport; duplicated birth charts are not an injective surface parametrisation'))
        context = dict(input_case=case, candidate=mode, source=source['path'],
            source_control_sha256=source['control_sha256'], source_generation=5, source_surface='mean',
            preserved_parent=source, geometry_code_sha256=hashes, directional_rules=fold.RECIPE,
            operator_metadata=metadata, added_CC_passes=1, added_topology_events=0,
            added_field_passes=0, added_mandelbulb_evaluations=0, methodology_scope=METHOD_SCOPE,
            lineage='Frozen actual DIRECTIONAL G5 -> one actual coupled directional-rule CC G6',
            comparison_scope='Two normal amplitudes (.8, 1.6) at one half period (.35 root radius); no neutral G6 control, factorial claim, role/curvature gate, or visual success assumed.')
        record = core.save(folder, out, outchart, context, state)
        try:
            proof = quick_symmetry(folder, out, mesh.faces, state, pairs)
        except Exception as exc:
            record['checks']['passed'] = False
            record['quick_symmetry'] = dict(passed=False, error=str(exc))
            write(folder/'generation.json', record)
            raise
        record['quick_symmetry'] = proof
        record['checks']['symmetry_scope'] = 'Actual saved native XYZ, actual control XYZ and oriented control quads; explicit propagated IDs. Full independent replay/native oriented triangle sorting not performed this round.'
        write(folder/'generation.json', record)
        write(folder/'quickcheck.json', dict(status='PASS', generation_sha256=digest(folder/'generation.json'),
            quick_integrity=record['checks'], quick_symmetry=proof))
        if hashes != geometry_code_hashes():
            raise ValueError('Geometry code changed during run.')
        del out, outchart, metadata, state, record, proof
        gc.collect()
    check_stage(source); check_stage(source['g4']); check_stage(source['g3'])
    for path_key, hash_key in (('parent_verification', 'parent_verification_sha256'),
            ('parent_source_index', 'parent_source_index_sha256'), ('parent_recipe', 'parent_recipe_sha256')):
        if digest(source[path_key]) != source[hash_key]:
            raise ValueError('Frozen parent provenance changed during run.')


def recipe():
    return dict(base_commit=BASE_COMMIT, cases=list(CASES), modes=list(MODES),
        source_generation=5, final_generation=6, added_CC_passes=1,
        directional_rules=fold.RECIPE, geometry_code_sha256=geometry_code_hashes(),
        preserved_parent_root=str(PARENT_ROOT), methodology_scope=METHOD_SCOPE,
        topology_scope='Inherited connected all-quad topology followed by one actual coupled CC; intersections allowed, no repair.',
        validation_scope='Existing core finite/closed-oriented/control connectivity/native minimum-area checks plus propagated actual XYZ and oriented control-face reflection; no full independent replay or native triangle sorting.',
        visual_scope='Pending matched renders; two amplitudes do not establish a successful fine-fold hierarchy.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--mode', nargs='+', choices=MODES, default=list(MODES))
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case) or len(set(args.mode)) != len(args.mode):
        parser.error('Repeated cases/modes are not allowed.')
    root = args.root.resolve()
    if root == PARENT_ROOT.resolve() or PARENT_ROOT.resolve() in root.parents:
        parser.error('Output must be separate from the preserved parent tree.')
    for case in args.case:
        for mode in args.mode:
            if (root/mode/case/'G06').exists():
                raise FileExistsError('Earlier result preserved: '+str(root/mode/case/'G06'))
    sources = source_index()
    root.mkdir(parents=True, exist_ok=True)
    for name, value in (('RECIPE.json', recipe()), ('source_index.json', sources)):
        path = root/name
        if path.exists():
            if read_json(path) != value:
                raise FileExistsError('Earlier recipe/source index preserved: '+str(path))
        else:
            write(path, value)
    for case in args.case:
        run_case(root, case, args.mode, sources[case])
        gc.collect()
    states, receipts = [], []
    for mode in MODES:
        for case in CASES:
            folder = root/mode/case/'G06'
            if (folder/'generation.json').is_file():
                states.append(read_json(folder/'generation.json'))
                receipts.append(dict(input_case=case, candidate=mode,
                    generation_sha256=digest(folder/'generation.json'),
                    proof=read_json(folder/'quickcheck.json')))
    passed = bool(states) and all(item['checks']['passed'] and
        item['quick_symmetry']['passed'] for item in states)
    complete = len(states) == len(CASES)*len(MODES)
    write(root/'SUMMARY.json', dict(states=states, all_four_complete=complete,
        quick_integrity_passed=passed, full_independent_replay='NOT_PERFORMED_THIS_ROUND',
        methodology_scope=METHOD_SCOPE, visual_success='NOT_ASSESSED'))
    write(root/'QUICKCHECK.json', dict(status='PASS' if complete and passed else 'INCOMPLETE',
        expected_cases=list(CASES), expected_modes=list(MODES), states=receipts,
        scope='Finite/closed-oriented connected control body and native minimum area; actual control/native XYZ reflection and oriented control quads.',
        excluded=['Full independent geometry replay', 'Native oriented triangle-set sorting',
            'Self-intersections', 'Fabrication suitability', 'Aesthetic success']))


if __name__ == '__main__':
    main()
