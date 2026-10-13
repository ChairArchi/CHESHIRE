"""One-command input-only transfer of the selected CHESHIRE G0--G7 recipe.

G0 is a distinct macro mass from the existing input evaluator. Every G1--G7 operator and coefficient
is reused unchanged. Child processes run serially to release dense arrays.
No historical geometry or frozen modeling code is overwritten.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/distinct_input_transfer_20261013/trial01')
INPUT_DEFINITION = dict(case='CENTRAL_SPINDLE', generator='existing seed_mass.evaluate', radius=[.44,.50,.66,1.15,1.85,1.15,.64,.44], valley=.18, event_layout='Three central returns; no inherited legacy deep-fold component')
EARLY = ('G00_INPUT', 'G01_ANCESTRY', 'G02_OVERLAP', 'G03_WALL', 'G03_ROOT', 'G03_SIDEWALL', 'G04_NEUTRAL')
LATE = ('G05_DIRECTIONAL', 'G06_DEPTH08', 'G06_MIDDLE', 'G07_SURFACE',
    'G07_LINKED_RAW', 'G07_LINKED_FINISHED', 'G07_WIDE_RAW', 'G07_FINAL')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def manifest(root):
    stages = []
    for stage in EARLY+LATE:
        dest = root/'states'/stage
        path = dest/'generation.json'
        if not path.is_file():
            continue
        record = read(path)
        stages.append(dict(id=stage, folder=str(dest), generation=record['subdivision_generation'],
            generation_json_sha256=sha(path), candidate=record['candidate'],
            native_available=(dest/'geometry.npz').is_file(),
            checks_passed=record['checks']['passed']))
    result = dict(schema='CHESHIRE_RECIPE_TRANSFER_STAGES_V1', input_case='CENTRAL_SPINDLE',
        stages=stages, generation_scope='Actual quad subdivision count; same-G detail stages have separate IDs.')
    write(root/'STAGES.json', result)
    return stages


def child(root, filename, *args):
    env = os.environ.copy()
    temp = root/'temp'
    temp.mkdir(exist_ok=True)
    env.update(TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    subprocess.run([sys.executable, '-X', 'utf8', '-B', '-u', str(HERE/filename),
        '--root', str(root), *args], check=True, cwd=REPO, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--resume', action='store_true', help='Continue unchanged code after an external interruption; never overwrite a saved stage.')
    args = parser.parse_args()
    root = args.root.resolve()
    if root.exists() and not args.resume:
        raise FileExistsError('Existing output is preserved; explicit unchanged-code resume required.')
    if shutil.disk_usage(root.anchor).free < 30*1024**3:
        raise OSError('At least 30 GiB free on the output drive is required.')
    root.mkdir(parents=True, exist_ok=True)
    before = time.monotonic()
    basis = read(REPO/'docs/generation_workflow_20261013/LINEAGE.json')
    frozen = {item['path']: item['expected_sha256'] for item in basis['frozen_code_checks']}
    for name, expected in frozen.items():
        if sha(REPO/name) != expected:
            raise ValueError('Historical frozen code differs: '+name)
    request = dict(date='2026-10-13', timezone='Asia/Seoul', input_case='CENTRAL_SPINDLE',
        basis_commit='ae21b874ce256ebbfc17e64759a6f0095c327e01',
        original_geometry_commit='657b3ab927d067630071a12fc14bd2b0a8d0681e',
        changed_input_only=dict(field='G0 complete macro geometry', definition=INPUT_DEFINITION),
        unchanged=['G0 carrier/chart/topology and X/Y/Z coordinate contract', 'All G1--G7 geometric formulas and selected modes',
            'Mandelbulb world volumes, iterations and movement budgets', 'Material root window and child beta windows',
            'All phase, amplitude, envelope and smoothing values'],
        stage_sequence=list(EARLY+LATE), run_file_sha256=sha(HERE/'run.py'),
        scope='One distinct macro input on the same closed carrier and aligned chart; not arbitrary-input generality or aesthetic success certification.')
    request_path = root/'RUN_REQUEST.json'
    if request_path.exists():
        if read(request_path) != request:
            raise ValueError('Resume request/code differs from the preserved request.')
    else:
        write(request_path, request)
    early_complete = (root/'STAGES_EARLY.json').is_file() and all((root/'states'/s/'generation.json').is_file() for s in EARLY)
    if not early_complete:
        print('BEGIN one new input through unchanged early G0--G4 recipe', flush=True)
        child(root, 'early.py')
    early_recipe = read(root/'RECIPE_EARLY.json')
    hashes = dict(frozen)
    for name, checksum in early_recipe['geometry_code_sha256'].items():
        name = name.replace('\\', '/')
        if name in hashes and hashes[name] != checksum:
            raise ValueError('Conflicting original geometric code hashes: '+name)
        hashes[name] = checksum
    for name in ('run.py', 'early.py', 'late.py', 'input_seed.py', '../recipe_transfer_20261013/late.py'):
        path = (HERE/name).resolve()
        hashes[str(path.relative_to(REPO)).replace('\\', '/')] = sha(path)
    recipe = dict(schema='CHESHIRE_DISTINCT_INPUT_FIXED_DOWNSTREAM_V1', **request,
        geometry_code_sha256=hashes, early_recipe=early_recipe,
        late_fixed_selection=['DIRECTIONAL', 'DEPTH_08', 'MIDDLE', 'neutral CC',
            'connected_ribs V2', 'saved delta S3', 'MEDIUM then SMALL with S2 each', 'saved delta S3'],
        historical_same_G_fine_mode='FINE excluded exactly as in the selected baseline',
        storage_scope='G0--G6 and final G7 have actual native meshes; four G7 intermediates have actual controls/evidence only.',
        visual_success='PENDING_MATCHED_ACTUAL_RENDER_REVIEW')
    recipe_path = root/'RECIPE.json'
    if recipe_path.exists():
        if read(recipe_path) != recipe:
            raise ValueError('Resume recipe/code differs from the preserved recipe.')
    else:
        write(recipe_path, recipe)
    for name, expected in hashes.items():
        path = REPO/name
        if sha(path) != expected:
            raise ValueError('Geometric source changed: '+name)
        snapshot = root/'source_snapshot'/name
        if not snapshot.exists():
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, snapshot)
    stages = manifest(root)
    for stage in LATE:
        dest = root/'states'/stage
        if (dest/'generation.json').is_file():
            if not args.resume or not read(dest/'generation.json')['checks']['passed']:
                raise ValueError('Existing failed stage remains preserved: '+stage)
            print('REUSE verified own stage', stage, flush=True)
            continue
        print('BEGIN unchanged selected stage', stage, flush=True)
        child(root, 'late.py', '--stage', stage)
        stages = manifest(root)
    stages = manifest(root)
    if len(stages) != 15 or not all(item['checks_passed'] for item in stages):
        raise ValueError('Incomplete actual transfer sequence.')
    final = read(root/'states/G07_FINAL/generation.json')
    for name, expected in hashes.items():
        if sha(REPO/name) != expected:
            raise ValueError('Frozen source changed during the sequence: '+name)
    write(root/'SUMMARY.json', dict(date='2026-10-13', timezone='Asia/Seoul',
        input_case='CENTRAL_SPINDLE', complete_generation_sequence=True, actual_final_generation=7,
        actual_saved_states=15, changed_input_only=request['changed_input_only'],
        unchanged_downstream_recipe_completed_without_retuning=True, all_required_stage_checks_passed=True,
        native_stage_count=sum(item['native_available'] for item in stages),
        control_only_intermediate_count=sum(not item['native_available'] for item in stages),
        final_control_vertices=final['control_vertices'], final_control_quads=final['control_quads'],
        final_native_triangles=final['native_triangles'], final_symmetry=final['symmetry'],
        elapsed_generation_seconds=time.monotonic()-before,
        source_snapshot_files=len(hashes), recipe_sha256=sha(recipe_path), stages_sha256=sha(root/'STAGES.json'),
        visual_success='PENDING_MATCHED_ACTUAL_RENDER_REVIEW',
        generality_scope='One distinct G0 macro geometry on the same aligned closed carrier, not arbitrary topology.',
        exclusions=['New reference research', 'Parameter search', 'Full baseline regeneration',
            'Full independent transfer replay', 'Self-intersection/fabrication certification']))
    print('DONE full input-only G0--G7 generation sequence; renders pending', flush=True)


if __name__ == '__main__':
    main()
