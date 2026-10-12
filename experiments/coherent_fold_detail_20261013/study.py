"""One actual coherent spatial-rule CC step from frozen SIDEWALL_FAN G4.

Three new states share topology and ancestry with the frozen COMBINED baseline.
Coefficients and phase fields are new CHESHIRE hypotheses.
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
PARENT_ROOT = Path('E:/CHESHIRE_DATA/experiments/sidewall_fan_growth_20261013/trial01')
BASELINE_ROOT = Path('E:/CHESHIRE_DATA/experiments/late_detail_rules_20261013/trial01')
BASE_COMMIT = 'd4eb66497dee172697dfa4c653d5bd403afa6dd3'
CASES = ('SPAN', 'COUNTER')


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = load_module('coherent_frozen_connected_core', HERE.parent/'connected_fold_growth_20261012/study.py')
fold = load_module('coherent_actual_operator', HERE/'fold_operator.py')
digest, write = core.digest, core.write
MODES = fold.MODES


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def geometry_code_hashes():
    frozen = read_json(PARENT_ROOT/'RECIPE.json')['geometry_code_sha256']
    for name, checksum in frozen.items():
        if digest(REPO/name) != checksum:
            raise ValueError('Frozen parent generation code changed: '+name)
    return dict(frozen, **{str(path.relative_to(REPO)): digest(path)
        for path in (HERE/'study.py', HERE/'fold_operator.py')})


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
    verification_path = PARENT_ROOT/'VERIFICATION.json'
    verified = read_json(verification_path)
    if verified['status'] != 'PASS' or verified['expected_cases'] != list(CASES):
        raise ValueError('Frozen complete two-input sidewall verification required.')
    baseline_proof = read_json(BASELINE_ROOT/'VERIFICATION.json')
    if baseline_proof['status'] != 'PASS':
        raise ValueError('Frozen baseline independent PASS required.')
    sources = {}
    for case in CASES:
        folder = PARENT_ROOT/'SIDEWALL_FAN'/case
        stages = {name: stage_source(folder/name) for name in ('G03_events', 'G04', 'G05')}
        for generation, name, proof in zip((3, 4, 5), stages, verified['cases'][case]['stages']):
            info = read_json(Path(stages[name]['path'])/'generation.json')
            if (proof['passed'] is not True or proof['semantics']['actual_generation'] != generation or
                    proof['generation_json_sha256'] != stages[name]['generation_sha256'] or
                    info['subdivision_generation'] != generation or info['input_case'] != case or
                    info['candidate'] != 'SIDEWALL_FAN'):
                raise ValueError('Exact verified SIDEWALL_FAN lineage required: '+case)
        sources[case] = dict(stages['G04'], g3=stages['G03_events'], neutral=stages['G05'],
            parent_verification=str(verification_path), parent_verification_sha256=digest(verification_path),
            parent_recipe=str(PARENT_ROOT/'RECIPE.json'), parent_recipe_sha256=digest(PARENT_ROOT/'RECIPE.json'))
        baseline = stage_source(BASELINE_ROOT/'COMBINED'/case/'G05')
        baseline_info = read_json(Path(baseline['path'])/'generation.json')
        proof = baseline_proof['cases'][case]['states']['COMBINED']
        if (proof['passed'] is not True or proof['generation_json_sha256'] != baseline['generation_sha256'] or
                baseline_info['preserved_parent']['control_sha256'] != sources[case]['control_sha256']):
            raise ValueError('Baseline must share the exact actual G4 parent.')
        sources[case].update(baseline=baseline, baseline_verification=str(BASELINE_ROOT/'VERIFICATION.json'),
            baseline_verification_sha256=digest(BASELINE_ROOT/'VERIFICATION.json'),
            baseline_render_verification=str(BASELINE_ROOT/'RENDER_VERIFICATION.json'),
            baseline_render_verification_sha256=digest(BASELINE_ROOT/'RENDER_VERIFICATION.json'))
    return sources


def check_stage(source):
    folder = Path(source['path'])
    for filename, key in (('control_quad.npz', 'control_sha256'), ('geometry.npz', 'geometry_sha256'),
            ('evidence.npz', 'evidence_sha256'), ('generation.json', 'generation_sha256')):
        if digest(folder/filename) != source[key]:
            raise ValueError('Read-only source changed: '+str(folder/filename))


def load_arrays(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def load_parent(source):
    check_stage(source); check_stage(source['g3']); check_stage(source['neutral']); check_stage(source['baseline'])
    folder = Path(source['path'])
    data = load_arrays(folder/'control_quad.npz')
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if mesh.generation != 4 or mesh.surface != 'mean' or mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0):
        raise ValueError('Actual frozen mean-native all-quad G4 required.')
    core.topology(mesh)
    return mesh, data['chart'], load_arrays(folder/'evidence.npz'), load_arrays(Path(source['g3']['path'])/'evidence.npz')


def refine(mesh, chart, g4_evidence, g3_evidence, mode):
    incoming = core.topology(mesh)
    out, metadata, state = fold.build(mesh, g4_evidence, g3_evidence, mode)
    face_chart = core.mean_incident(chart[incoming['a']], incoming['fi'], len(mesh.faces))
    outchart = np.concatenate([chart, chart[incoming['edges']].mean(1), face_chart])
    out.surface = 'mean'
    state = dict(state, implementation=np.array('REFERENCE_COUPLED_COHERENT_FOLD_CC'),
        chart_scope=np.array('Linear V/E/F transport; duplicate chart values after sweeps are not an injective surface parametrisation'))
    return out, outchart, metadata, state


def run_state(root, case, mode, source):
    core.memory_guard()
    hashes = geometry_code_hashes()
    mesh, chart, g4_evidence, g3_evidence = load_parent(source)
    mesh, chart, metadata, evidence = refine(mesh, chart, g4_evidence, g3_evidence, mode)
    del g4_evidence, g3_evidence
    context = dict(input_case=case, candidate=mode, source=source['path'],
        source_control_sha256=source['control_sha256'], source_generation=4, source_surface='mean',
        preserved_parent=source, geometry_code_sha256=hashes, coherent_rules=fold.RECIPE,
        operator_metadata=metadata, added_CC_passes=1, added_topology_events=0,
        added_field_passes=0, added_mandelbulb_evaluations=0,
        lineage='Frozen SIDEWALL_FAN G4 -> one actual spatially differentiated coherent-rule CC G5',
        comparison_scope='Three coherent normal-control schedules from one actual G4. Role/geometry/root-frame signals evaluated before one CC step; not a factorial or exact reference replication.')
    folder = root/mode/case/'G05'
    record = core.save(folder, mesh, chart, context, evidence)
    if hashes != geometry_code_hashes():
        raise ValueError('Geometry code changed during actual run.')
    check_stage(source); check_stage(source['g3']); check_stage(source['neutral']); check_stage(source['baseline'])
    del mesh, chart, evidence
    gc.collect()
    return record


def recipe():
    return dict(base_commit=BASE_COMMIT, cases=list(CASES), modes=list(MODES),
        source_generation=4, final_generation=5, added_CC_passes=1,
        coherent_rules=fold.RECIPE, geometry_code_sha256=geometry_code_hashes(),
        preserved_parent_root=str(PARENT_ROOT), frozen_baseline_root=str(BASELINE_ROOT),
        topology_scope='Same ordered CC connectivity in all three new conditions and frozen COMBINED baseline; intersections allowed, no repair.',
        visual_scope='Matched original renders; actual fine folds and hierarchy assessed separately from numerical PASS.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--mode', nargs='+', choices=MODES, default=list(MODES))
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case) or len(set(args.mode)) != len(args.mode):
        parser.error('Repeated cases/modes are not allowed.')
    root = args.root.resolve()
    sources = source_index()
    root.mkdir(parents=True, exist_ok=True)
    for name, value in (('RECIPE.json', recipe()), ('source_index.json', sources)):
        path = root/name
        if path.exists():
            if read_json(path) != value:
                raise FileExistsError('Earlier recipe/source preserved: '+str(path))
        else:
            write(path, value)
    for case in args.case:
        for mode in args.mode:
            run_state(root, case, mode, sources[case])
    states = []
    for mode in MODES:
        for case in CASES:
            path = root/mode/case/'G05/generation.json'
            if path.is_file():
                states.append(read_json(path))
    write(root/'SUMMARY.json', dict(states=states, all_six_complete=len(states) == 6,
        quick_integrity_passed=all(item['checks']['passed'] for item in states),
        actual_replay_and_symmetry='PENDING', visual_success='NOT_ASSESSED'))


if __name__ == '__main__':
    main()
