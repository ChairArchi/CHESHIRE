"""Task32 serial research runner; immutable stages and existing RAM/process guard.

No elapsed-time cutoff. Solver iterations are a declared numerical budget;
nonconverged outputs remain labelled and preserved. Old study writers are
never called. Resume verifies bytes, source identity and completed requests.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
from time import perf_counter
import traceback
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO/'src'), str(REPO/'examples'), str(REPO/'tools')]
from task29_search import load_mesh, save_mesh
from task31_study import basic_gate
from hero_design_sprint import guarded, windows_memory
from cheshire.reference_subdivision import subdivide, metrics
from cheshire.task32_morphology import displace_hierarchy, metric_growth
from cheshire.task32_patches import branch_patches

ROOT = Path('E:/CHESHIRE_DATA/task32')
SOURCES = ['tools/task32_research.py', 'src/cheshire/task32_morphology.py',
           'src/cheshire/task32_patches.py',
           'src/cheshire/reference_subdivision.py', 'src/cheshire/progressive_gates.py',
           'examples/task29_search.py', 'examples/hero_design_sprint.py',
           'tools/task31_study.py']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def source_identity():
    return {name: sha(REPO/name) for name in SOURCES}


def preflight(mesh, operation):
    memory = windows_memory()
    faces = len(mesh.faces)*4 if operation == 'cc' else len(mesh.faces)
    # Conservative small-mesh estimate includes topology sorts, render fan,
    # optimizer arrays; actual process-wide existing guard remains decisive.
    estimate = 512*1024**2 + faces*4000
    if estimate > min(12*1024**3, memory['available_bytes']*.55):
        raise ValueError('Forecast exceeds RAM-derived allocation; keep prefix.')
    disk = shutil.disk_usage(ROOT)
    if disk.free < 4*1024**3 + faces*1000:
        raise ValueError('Insufficient retained-checkpoint disk reserve.')
    return dict(predicted_faces=faces, conservative_RAM_bytes=estimate,
                available_RAM_bytes=memory['available_bytes'], disk_free_bytes=disk.free)


def initialize():
    ROOT.mkdir(parents=True, exist_ok=False)
    prior = read(REPO/'studies/task31/ARTIFACTS.json')
    proof = []
    for r in prior['files']:
        path = Path(prior['root'])/r['path']
        if path.stat().st_size != r['bytes'] or sha(path) != r['sha256']:
            raise ValueError('Task31 protection manifest mismatch: '+str(path))
        proof.append(r)
    write_new(ROOT/'preservation/task31_before.json', dict(root=prior['root'], files=proof))
    write_new(ROOT/'preservation/start.json', dict(
        UTC=datetime.now(timezone.utc).isoformat(), baseline='17c0415b8d7bdead8763949bfa8d95f18fad908c',
        branch='experiment/task32-relational-morphology', task31_verified_files=len(proof),
        source_files=source_identity(), cpu_count=os.cpu_count(),
        available_RAM=windows_memory(), disk_free_bytes=shutil.disk_usage(ROOT).free,
        packages={p:importlib.metadata.version(p) for p in ('numpy','scipy','compas','trimesh','pyrender','Pillow')},
        prior_backup='E:/REPOSITORY_BACKUPS/ALICE_CHESHIRE_20261009_dbe03c97'))
    print('Task32 initialized; protected Task31 hashes verified:', len(proof), flush=True)


def run(definition_path):
    definition_path = Path(definition_path)
    d = read(definition_path)
    name = d['id']
    if not name or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in name):
        raise ValueError('Safe explicit experiment identity required.')
    dest = ROOT/'candidates'/name
    sources = source_identity()
    request = dict(definition=d, definition_sha256=sha(definition_path), sources=sources)
    if dest.exists():
        if read(dest/'request.json') != request:
            raise ValueError('Changed definition/source: use a new experiment ID, never overwrite.')
    else:
        write_new(dest/'request.json', request)
    checkpoints = []
    mesh = basic_gate()
    branch_state = None
    operations = [dict(kind='input')]+d['steps']
    for index, step in enumerate(operations):
        path = dest/f'S{index:02}'
        parent = dest/f'S{index-1:02}' if index else None
        if path.exists():
            proof = read(path/'task32_identity.json')
            if proof['step'] != step or proof['sources'] != sources:
                raise ValueError('Checkpoint request/source mismatch.')
            for name2, expected in proof['files'].items():
                if sha(path/name2) != expected:
                    raise ValueError('Corrupt or incomplete checkpoint: '+str(path/name2))
            if proof['parent_mesh_sha256'] != (sha(parent/'mesh.npz') if parent else None):
                raise ValueError('Checkpoint parent mismatch.')
            mesh = load_mesh(path)
            if (path/'branch_state.npz').exists():
                with np.load(path/'branch_state.npz') as z:
                    branch_state={k:z[k].copy() for k in z.files}
            checkpoints.append(str(path))
            continue
        pre = preflight(mesh, step['kind'])
        start = perf_counter()
        if step['kind'] == 'input':
            meta, state = dict(input='Exact gate_input RECT False; unresolved original units'), None
        elif step['kind'] == 'cc':
            mesh, meta, state = subdivide(mesh, step.get('row', {}))
            if branch_state is not None:
                branch_state={k:v[state['parent_face']] for k,v in branch_state.items()}
        elif step['kind'] == 'hierarchy':
            mesh, meta, state = displace_hierarchy(mesh, step['spec'], step.get('level', 0))
        elif step['kind'] == 'growth':
            mesh, meta, state = metric_growth(mesh, step['spec'])
        elif step['kind'] == 'patches':
            mesh, meta, state = branch_patches(mesh, step['spec'], branch_state if step.get('children') else None)
            branch_state={k:state[k] for k in ('face_scope','cap_mask','scope_level')}
        else:
            raise ValueError('Unknown opt-in experiment operation.')
        seconds = perf_counter()-start
        summary = save_mesh(path, mesh, dict(**meta, operation_seconds=seconds, preflight=pre), state, parent)
        if branch_state is not None:
            np.savez_compressed(path/'branch_state.npz',**branch_state)
        write_new(path/'task32_identity.json', dict(step=step, sources=sources,
            parent_mesh_sha256=sha(parent/'mesh.npz') if parent else None,
            files={f.name:sha(f) for f in path.iterdir() if f.is_file()}))
        checkpoints.append(str(path))
        print(d['id'], path.name, step['kind'], len(mesh.xyz), len(mesh.faces),
              round(seconds, 3), 's', meta.get('termination', ''), flush=True)
        if not summary['finite'] or summary['zero_area_faces']:
            raise ValueError('Invalid geometry retained and stopped; no silent repair.')
    final = dest/'completed.json'
    if not final.exists():
        write_new(final, dict(id=d['id'], final_stage=checkpoints[-1], stages=checkpoints,
            definition_sha256=sha(definition_path), sources=sources, metrics=metrics(mesh)))


def render(request, tag):
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in tag):
        raise ValueError('Safe render identity required.')
    # Reuse exactly Task31's clay/camera/visibility renderer, redirect its ONLY
    # write root to this study in this isolated worker. No old study entrypoint.
    import task31_views
    task31_views.ROOT = ROOT
    task31_views.render(Path(request), tag)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['initialize','run','render'])
    p.add_argument('--definition', type=Path)
    p.add_argument('--request', type=Path)
    p.add_argument('--tag')
    p.add_argument('--worker', action='store_true')
    a = p.parse_args()
    if a.action == 'initialize':
        initialize()
    elif a.worker:
        try:
            run(a.definition) if a.action == 'run' else render(a.request, a.tag)
        except BaseException:
            traceback.print_exc()
            raise
    else:
        stem = a.definition.stem if a.action == 'run' else a.tag
        logs = ROOT/'logs'/stem
        # Each attempt receives new logs, including failed resumption attempts.
        attempt = 1
        while (logs/f'attempt_{attempt:03}').exists():
            attempt += 1
        args = [a.action, '--worker']
        args += ['--definition', str(a.definition)] if a.action == 'run' else ['--request', str(a.request), '--tag', a.tag]
        result = guarded(args, logs/f'attempt_{attempt:03}', worker_script=Path(__file__))
        print(stem, result, flush=True)
        if result['exit_code']:
            raise SystemExit(result['exit_code'])


if __name__ == '__main__':
    main()
