"""Actual connected parent/child surface construction, then neutral CC.

This pilot returns to saved WALL G3, before the G6 Mandelbulb finish. Topology
events do not increment G. Every candidate receives two actual CC refinements
to G5, including the no-event smoothing control. No prior result is overwritten.
"""
from pathlib import Path
import argparse
import ctypes
import gc
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh, topology, subdivide, mean_incident

_spec = importlib.util.spec_from_file_location('connected_patch_growth', HERE/'patch_growth.py')
patch_growth = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(patch_growth)

CASES = ('SPAN', 'COUNTER')
MODES = ('SMOOTH_CONTROL', 'ROOT_ONLY', 'BRANCHED')
BASELINE_ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_guided_detail_20261012/trial02')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def geometry_code_hashes():
    paths = (HERE/'study.py', HERE/'patch_growth.py',
        REPO/'src/cheshire/task32_patches.py', REPO/'src/cheshire/reference_subdivision.py')
    return {str(path.relative_to(REPO)): digest(path) for path in paths}


def memory_guard():
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
            ('total', ctypes.c_ulonglong), ('available', ctypes.c_ulonglong),
            ('page_total', ctypes.c_ulonglong), ('page_available', ctypes.c_ulonglong),
            ('virtual_total', ctypes.c_ulonglong), ('virtual_available', ctypes.c_ulonglong),
            ('extended_available', ctypes.c_ulonglong)]
    if sys.platform == 'win32':
        status = Memory(); status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError('Cannot read physical memory availability.')
        if status.available < 3*1024**3:
            raise MemoryError('At least 3 GB physical memory required for this G5 pilot.')


def load_source(path):
    path = Path(path)
    with np.load(path/'control_quad.npz', allow_pickle=False) as data:
        mesh = ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
            data['anchors'], int(data['generation']))
        mesh.surface = str(data['surface'])
        chart = data['chart']
    if mesh.generation != 3 or mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0):
        raise ValueError('Saved closed WALL G3 all-quad input required.')
    topology(mesh)
    return mesh, chart


def refine(mesh, chart):
    """Actual neutral Catmull--Clark, with independent linear chart transport."""
    incoming = topology(mesh)
    out, metadata, state = subdivide(mesh, {'weights': {}})
    out.surface = 'mean'
    face_chart = mean_incident(chart[incoming['a']], incoming['fi'], len(mesh.faces))
    outchart = np.concatenate([chart, chart[incoming['edges']].mean(1), face_chart])
    state = dict(state, implementation=np.array('REFERENCE_COUPLED_NEUTRAL_CC'),
        chart_scope=np.array('Linear V/E/F transport; duplicate chart values after sweeps are not an injective surface parametrisation'))
    return out, outchart, state


def native(mesh):
    """Explicit arithmetic quad-centre fans; no renderer geometry modifier."""
    if mesh.faces.shape[1] != 4 or np.any(mesh.faces < 0):
        raise ValueError('This pilot saves explicit all-quad centre fans only.')
    q = mesh.faces
    centres = mesh.xyz[q].mean(1)
    xyz = np.concatenate([mesh.xyz, centres])
    faces = np.column_stack([q.ravel(), np.roll(q, -1, axis=1).ravel(),
        np.repeat(len(mesh.xyz)+np.arange(len(q)), 4)])
    return xyz, faces


def quick_checks(mesh, xyz, triangles):
    observed = topology(mesh)
    edges = observed['edges']
    graph = coo_matrix((np.ones(len(edges), np.int8), (edges[:, 0], edges[:, 1])),
        shape=(len(mesh.xyz), len(mesh.xyz))).tocsr()
    components = int(connected_components(graph, directed=False, return_labels=False))
    minimum = float('inf')
    for start in range(0, len(triangles), 150000):
        points = xyz[triangles[start:start+150000]]
        areas = .5*np.linalg.norm(np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0]), axis=1)
        minimum = min(minimum, float(areas.min()))
    values = dict(finite=bool(np.isfinite(xyz).all()), closed_oriented_control=True,
        control_components=components, control_Euler=int(len(mesh.xyz)-len(edges)+len(mesh.faces)),
        no_orphan_controls=bool(np.all(observed['degree'] > 0)), minimum_native_triangle_area=minimum,
        control_xyz_sha256=array_hash(mesh.xyz), control_faces_sha256=array_hash(mesh.faces),
        chart_sha256=array_hash(mesh._chart_for_receipt), native_xyz_sha256=array_hash(xyz),
        native_faces_sha256=array_hash(triangles),
        symmetry_scope='Independent actual replay and propagated reflection proof pending',
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED')
    values['passed'] = bool(values['finite'] and components == 1 and values['control_Euler'] == 2
        and values['no_orphan_controls'] and minimum > 1e-14)
    return values


def save(folder, mesh, chart, context, state=None):
    if folder.exists():
        raise FileExistsError('Earlier result preserved: '+str(folder))
    mesh._chart_for_receipt = chart
    xyz, triangles = native(mesh)
    checked = quick_checks(mesh, xyz, triangles)
    folder.mkdir(parents=True)
    np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
        chart=chart, classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
        generation=np.array(mesh.generation), surface=np.array('mean'))
    np.savez_compressed(folder/'geometry.npz', xyz=xyz, faces=triangles)
    if state is not None:
        if any(np.asarray(value).dtype == object for value in state.values()):
            raise ValueError('Evidence arrays cannot contain Python objects.')
        np.savez_compressed(folder/'evidence.npz', **state)
    record = dict(context, subdivision_generation=int(mesh.generation),
        native_surface='Explicit arithmetic quad-centre fans', control_vertices=len(mesh.xyz),
        control_quads=len(mesh.faces), native_vertices=len(xyz), native_triangles=len(triangles),
        control_file_sha256=digest(folder/'control_quad.npz'),
        geometry_file_sha256=digest(folder/'geometry.npz'), checks=checked,
        visual_success='NOT_ASSESSED')
    if state is not None:
        record['evidence_file_sha256'] = digest(folder/'evidence.npz')
    write(folder/'generation.json', record)
    print('SAVED', context['input_case'], context['candidate'], folder.name,
        'native_triangles', len(triangles), 'quick_integrity', checked['passed'], flush=True)
    if not checked['passed']:
        raise ValueError('Failure preserved; no mesh repair performed: '+str(folder))
    return record


def source_index():
    sources = {}
    for case in CASES:
        receipt = BASELINE_ROOT/'BASELINE'/case/'G06/generation.json'
        metadata = json.loads(receipt.read_text(encoding='utf8'))
        source = Path(metadata['source'])
        actual = digest(source/'control_quad.npz')
        if actual != metadata['source_control_sha256']:
            raise ValueError('Preserved WALL source hash differs: '+case)
        sources[case] = dict(path=str(source), control_sha256=actual,
            original_receipt=str(receipt), original_receipt_sha256=digest(receipt))
    return sources


def run_state(root, case, mode, source):
    memory_guard()
    source_path = Path(source['path'])
    mesh, chart = load_source(source_path)
    source_surface = mesh.surface
    if mode == 'SMOOTH_CONTROL':
        events, evidence = [], {}
    else:
        mesh, chart, events, evidence = patch_growth.build(mesh, chart, mode)
    mesh.surface = 'mean'
    event_count = sum(item['status'] == 'accepted' for item in events)
    context = dict(input_case=case, candidate=mode, source=str(source_path),
        source_control_sha256=source['control_sha256'], source_generation=3,
        geometry_code_sha256=geometry_code_hashes(),
        event_recipe=patch_growth.RECIPE, constructive_event_count=event_count,
        reflected_constructive_event_instances=4*event_count,
        attempted_canonical_events=len(events),
        rejected_canonical_events=sum(item['status'] == 'rejected' for item in events),
        accepted_canonical_events_by_level=[sum(item['status'] == 'accepted' and item['level'] == level
            for item in events) for level in range(3)],
        event_count_scope='Canonical-quarter accepted events; reflected event instances counted separately',
        added_field_passes=0, added_mandelbulb_evaluations=0,
        topology_scope='Actual attached patch sidewalls/caps, followed by two neutral CC refinements; no Boolean or collision repair',
        source_surface=str(source_surface),
        lineage='Saved WALL G3 -> topology events at G3 -> actual neutral CC G4 -> actual neutral CC G5')
    folder = root/mode/case/'G03_events'
    record = save(folder, mesh, chart, context, evidence)
    write(folder/'events.json', events)
    record['events_file_sha256'] = digest(folder/'events.json')
    write(folder/'generation.json', record)
    for generation in (4, 5):
        parent = folder
        mesh, chart, refinement = refine(mesh, chart)
        if mesh.generation != generation:
            raise ValueError('Actual subdivision generation differs from path.')
        folder = root/mode/case/f'G{generation:02d}'
        record = save(folder, mesh, chart, dict(context, parent=str(parent),
            parent_generation_sha256=digest(parent/'generation.json'),
            neutral_CC_passes_added=generation-3), refinement)
        gc.collect()
    if digest(source_path/'control_quad.npz') != source['control_sha256']:
        raise ValueError('Read-only source changed during run.')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--mode', nargs='+', choices=MODES, default=list(MODES))
    args = parser.parse_args()
    if len(set(args.case)) != len(args.case) or len(set(args.mode)) != len(args.mode):
        parser.error('Duplicate case/mode requests are not allowed.')
    sources = source_index()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    recipe = dict(base_commit='0ff7387fcfe2fb00cbc0b5d45858576bff664d44',
        cases=list(CASES), modes=list(MODES), source_generation=3, final_generation=5,
        neutral_CC_passes=2, patch_growth=patch_growth.RECIPE,
        geometry_code_sha256=geometry_code_hashes())
    for name, value in (('RECIPE.json', recipe), ('source_index.json', sources)):
        path = root/name
        if path.exists():
            if json.loads(path.read_text(encoding='utf8')) != value:
                raise FileExistsError('Earlier recipe/source index preserved.')
        else:
            write(path, value)
    for case in args.case:
        for mode in args.mode:
            run_state(root, case, mode, sources[case])
            gc.collect()
    states = []
    for mode in MODES:
        for case in CASES:
            receipt = root/mode/case/'G05/generation.json'
            if receipt.is_file():
                states.append(json.loads(receipt.read_text(encoding='utf8')))
    write(root/'SUMMARY.json', dict(states=states, all_six_complete=len(states) == 6,
        quick_integrity_passed=all(item['checks']['passed'] for item in states),
        actual_replay_and_symmetry='PENDING', visual_success='NOT_ASSESSED'))


if __name__ == '__main__':
    main()
