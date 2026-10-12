"""Branch from preserved actual root sidewalls, then two neutral CC passes.

The exact ROOT_ONLY G3 parent is loaded from the completed connected pilot.
Only the new SIDEWALL_FAN alternative is generated. Existing ROOT_ONLY and
BRANCHED G5 renders remain the matched visual references, without regeneration.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = HERE.parent/'connected_fold_growth_20261012'
PARENT_ROOT = Path('E:/CHESHIRE_DATA/experiments/connected_fold_growth_20261012/trial01')
CASES = ('SPAN', 'COUNTER')
MODE = 'SIDEWALL_FAN'
BASE_COMMIT = 'd016293aa0e77346c5f697126800d3af856e5ea3'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


core = load_module('sidewall_existing_connected_study', BASE/'study.py')
patch = load_module('sidewall_actual_patch_operator', HERE/'patch_sidewall.py')
digest, write = core.digest, core.write


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def geometry_code_hashes():
    paths = (HERE/'study.py', HERE/'patch_sidewall.py', BASE/'study.py',
        BASE/'patch_growth.py', REPO/'src/cheshire/task32_patches.py',
        REPO/'src/cheshire/reference_subdivision.py')
    return {str(path.relative_to(REPO)): digest(path) for path in paths}


def source_index():
    verification_path = PARENT_ROOT/'VERIFICATION_RECHECK_01.json'
    verification = read_json(verification_path)
    if verification['status'] != 'PASS':
        raise ValueError('Preserved actual parent verification must PASS.')
    original_recipe = read_json(PARENT_ROOT/'RECIPE.json')
    for name, checksum in original_recipe['geometry_code_sha256'].items():
        if digest(REPO/name) != checksum:
            raise ValueError('Frozen connected geometry code changed: '+name)
    sources = {}
    for case in CASES:
        folder = PARENT_ROOT/'ROOT_ONLY'/case/'G03_events'
        info = read_json(folder/'generation.json')
        stage = verification['cases'][case]['states']['ROOT_ONLY']['stages'][0]
        if (stage['passed'] is not True or stage['semantics']['actual_generation'] != 3 or
            stage['generation_json_sha256'] != digest(folder/'generation.json') or
            info['subdivision_generation'] != 3 or info['candidate'] != 'ROOT_ONLY' or
            info['input_case'] != case or info['accepted_canonical_events_by_level'] != [1, 0, 0]):
            raise ValueError('Exact preserved root G3 source required: '+case)
        mapping = {'control_sha256': ('control_quad.npz', 'control_file_sha256'),
            'geometry_sha256': ('geometry.npz', 'geometry_file_sha256'),
            'evidence_sha256': ('evidence.npz', 'evidence_file_sha256'),
            'events_sha256': ('events.json', 'events_file_sha256')}
        observed = {}
        for key, (filename, metadata_key) in mapping.items():
            observed[key] = digest(folder/filename)
            if observed[key] != info[metadata_key]:
                raise ValueError('Parent data changed: '+str(folder/filename))
        sources[case] = dict(path=str(folder), **observed,
            generation_sha256=digest(folder/'generation.json'),
            parent_verification=str(verification_path),
            parent_verification_sha256=digest(verification_path),
            parent_recipe=str(PARENT_ROOT/'RECIPE.json'),
            parent_recipe_sha256=digest(PARENT_ROOT/'RECIPE.json'),
            original_wall_source=info['source'],
            original_wall_control_sha256=info['source_control_sha256'])
    return sources


def load_parent(source):
    folder = Path(source['path'])
    for name, key in (('control_quad.npz', 'control_sha256'), ('geometry.npz', 'geometry_sha256'),
            ('evidence.npz', 'evidence_sha256'), ('events.json', 'events_sha256'),
            ('generation.json', 'generation_sha256')):
        if digest(folder/name) != source[key]:
            raise ValueError('Read-only parent changed: '+str(folder/name))
    mesh, chart = core.load_source(folder)
    if mesh.surface != 'mean':
        raise ValueError('Preserved ROOT_ONLY mean-native control required.')
    with np.load(folder/'evidence.npz', allow_pickle=False) as data:
        evidence = {key: data[key] for key in data.files}
    return mesh, chart, evidence, read_json(folder/'events.json')


def run_state(root, case, source):
    core.memory_guard()
    code_hashes = geometry_code_hashes()
    mesh, chart, parent_evidence, parent_events = load_parent(source)
    mesh, chart, events, evidence = patch.build(mesh, chart, parent_evidence, parent_events)
    del parent_evidence, parent_events
    accepted = sum(item['status'] == 'accepted' for item in events)
    rejected = sum(item['status'] == 'rejected' for item in events)
    if any(item['level'] != 1 or item['parent_event_id'] != 1 for item in events):
        raise ValueError('This pilot only adds immediate root-sidewall children.')
    counts = [1, accepted, 0]
    if not np.array_equal(evidence['accepted_event_counts_by_level'], counts):
        raise ValueError('Inherited root/new sidewall event counts differ.')
    context = dict(input_case=case, candidate=MODE, source=source['path'],
        source_control_sha256=source['control_sha256'], source_generation=3,
        source_surface='mean', preserved_parent=source, geometry_code_sha256=code_hashes,
        event_recipe=patch.RECIPE, constructive_event_count=1+accepted,
        inherited_canonical_root_events=1, new_canonical_sidewall_events=accepted,
        reflected_constructive_event_instances=4*(1+accepted),
        reflected_new_sidewall_event_instances=4*accepted,
        attempted_canonical_events=1+len(events), rejected_canonical_events=rejected,
        accepted_canonical_events_by_level=counts,
        event_count_scope='One inherited canonical root plus new root-sidewall events; events.json contains only new events. Four reflected instances per accepted event.',
        added_field_passes=0, added_mandelbulb_evaluations=0,
        topology_scope='Actual preserved root sidewalls with new shared-boundary child walls/caps; no Boolean or intersection repair.',
        lineage='Preserved ROOT_ONLY G3 -> SIDEWALL_FAN topology events at G3 -> actual neutral CC G4 -> actual neutral CC G5')
    folder = root/MODE/case/'G03_events'
    record = core.save(folder, mesh, chart, context, evidence)
    write(folder/'events.json', events)
    record['events_file_sha256'] = digest(folder/'events.json')
    write(folder/'generation.json', record)
    del evidence, events
    for generation in (4, 5):
        parent = folder
        mesh, chart, refinement = core.refine(mesh, chart)
        if mesh.generation != generation:
            raise ValueError('Actual subdivision generation differs from path.')
        folder = root/MODE/case/f'G{generation:02d}'
        record = core.save(folder, mesh, chart, dict(context, parent=str(parent),
            parent_generation_sha256=digest(parent/'generation.json'),
            neutral_CC_passes_added=generation-3), refinement)
        gc.collect()
    if code_hashes != geometry_code_hashes():
        raise ValueError('Generation code changed during actual run.')
    for filename, key in (('control_quad.npz', 'control_sha256'), ('geometry.npz', 'geometry_sha256'),
            ('evidence.npz', 'evidence_sha256'), ('events.json', 'events_sha256'),
            ('generation.json', 'generation_sha256')):
        if digest(Path(source['path'])/filename) != source[key]:
            raise ValueError('Read-only preserved parent changed during generation.')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case):
        parser.error('Repeated cases are not allowed.')
    root = args.root.resolve()
    sources = source_index()
    root.mkdir(parents=True, exist_ok=True)
    recipe = dict(base_commit=BASE_COMMIT, cases=list(CASES), candidate=MODE,
        source_generation=3, final_generation=5, neutral_CC_passes=2,
        patch_growth=patch.RECIPE, geometry_code_sha256=geometry_code_hashes(),
        preserved_parent_root=str(PARENT_ROOT),
        comparison_scope='Existing ROOT_ONLY and BRANCHED G5 versus new SIDEWALL_FAN G5; all share the exact root and two neutral CC passes. Several authored branch conditions change together.')
    for name, value in (('RECIPE.json', recipe), ('source_index.json', sources)):
        path = root/name
        if path.exists():
            if read_json(path) != value:
                raise FileExistsError('Earlier source/recipe preserved.')
        else:
            write(path, value)
    for case in args.case:
        run_state(root, case, sources[case])
        gc.collect()
    states = []
    for case in CASES:
        receipt = root/MODE/case/'G05/generation.json'
        if receipt.is_file():
            states.append(read_json(receipt))
    write(root/'SUMMARY.json', dict(states=states, all_two_complete=len(states) == 2,
        quick_integrity_passed=all(state['checks']['passed'] for state in states),
        actual_replay_and_symmetry='PENDING', visual_success='NOT_ASSESSED'))


if __name__ == '__main__':
    main()
