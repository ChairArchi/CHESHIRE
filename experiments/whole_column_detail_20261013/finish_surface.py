"""One actual neutral CC surface pass on an explicitly supplied saved G6 stage.

The required stage is MIDDLE or FINE; this script never chooses between them.
It preserves both saved G6 states and writes an actual G7 under SURFACE.
No new directional field, amplitude variant, or attached topology event is
introduced. Geometric and visual effects of the neutral pass remain separate.
"""
from pathlib import Path
import argparse
import ctypes
import gc
import importlib.util
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/whole_column_detail_20261013/trial01')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


study = module('whole_column_finish_existing_study', HERE/'study.py')
loader, core = study.loader, study.core
mirror, digest, write = loader.mirror, study.digest, study.write
SOURCE = study.SOURCE


def memory_guard():
    """Require 11 GiB available physical memory immediately before actual CC."""
    required = 11*1024**3
    if sys.platform == 'win32':
        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                ('total', ctypes.c_ulonglong), ('available', ctypes.c_ulonglong),
                ('page_total', ctypes.c_ulonglong), ('page_available', ctypes.c_ulonglong),
                ('virtual_total', ctypes.c_ulonglong), ('virtual_available', ctypes.c_ulonglong),
                ('extended_available', ctypes.c_ulonglong)]
        status = Memory()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError('Cannot read available physical memory.')
        available = int(status.available)
    else:
        meminfo = Path('/proc/meminfo')
        if not meminfo.is_file():
            raise OSError('Cannot establish available physical memory for G7.')
        values = dict(line.split(':', 1) for line in meminfo.read_text().splitlines())
        available = int(values['MemAvailable'].strip().split()[0])*1024
    if available < required:
        raise MemoryError('Actual G7 neutral CC requires at least 11 GiB available physical memory; no generation performed.')
    return dict(required_available_bytes=required, available_bytes_before_CC=available,
        available_GiB_before_CC=available/1024**3, passed=True)


def child_face_pairs(incoming_faces, refinement, vertex_pair, incoming_face_pair):
    """Transport actual CC child IDs without sorting the seven-million quads.

    The frozen CC emits one child per incoming face corner, in face-major
    order. Reflection maps the old corner vertex to exactly one corner of the
    existing reflected incoming face. This supplies the reflected child ID.
    Actual reflected G7 oriented cycles are checked afterwards by the loader.
    """
    parent = refinement['parent_face']
    corners = refinement['parent_corner']
    expected_count = 4*len(incoming_faces)
    if parent.shape != (expected_count,) or corners.shape != parent.shape:
        raise ValueError('Actual all-quad CC parent/corner maps required.')
    result = np.empty(expected_count, dtype=np.int64)
    for start in range(0, expected_count, 100000):
        stop = min(start+100000, expected_count)
        ids = np.arange(start, stop, dtype=np.int64)
        parents = parent[start:stop]
        old_vertices = corners[start:stop]
        if (not np.array_equal(parents, ids//4) or
                not np.array_equal(old_vertices, incoming_faces[parents, ids % 4])):
            raise ValueError('Actual CC ordering differs from frozen face-major corner order.')
        reflected_parent = incoming_face_pair[parents]
        matches = incoming_faces[reflected_parent] == vertex_pair[old_vertices, None]
        if not np.all(matches.sum(axis=1) == 1):
            raise ValueError('Actual reflected incoming corner has no unique correspondence.')
        result[start:stop] = 4*reflected_parent+np.argmax(matches, axis=1)
    return mirror.involution(result, expected_count, 'Actual G7 child face mirror')


def load_stage(folder, stage):
    info = json.loads((folder/'generation.json').read_text(encoding='utf8'))
    if (info.get('candidate') != stage or info.get('input_case') != 'SPAN' or
            info.get('subdivision_generation') != 6 or info.get('source_generation') != 6 or
            info.get('added_CC_passes') != 0 or not info['checks']['passed'] or
            not info['symmetry']['passed'] or Path(info['source']).resolve() != SOURCE.resolve()):
        raise ValueError('Actual verified saved whole-column '+stage+' G6 required.')
    for name, key in (('control_quad.npz', 'control_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')):
        if digest(folder/name) != info[key]:
            raise ValueError('Preserved chosen stage changed: '+name)
    if digest(SOURCE/'control_quad.npz') != info['source_control_sha256']:
        raise ValueError('Preserved original DEPTH_08 G6 changed.')
    for name, checksum in info['geometry_code_sha256'].items():
        if digest(REPO/Path(name.replace('\\', '/'))) != checksum:
            raise ValueError('Frozen geometry code changed: '+name)
    data = loader.arrays(folder/'control_quad.npz',
        ('xyz', 'faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'))
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if (mesh.generation != 6 or mesh.surface != 'mean' or
            mesh.faces.shape != (info['control_quads'], 4) or
            len(mesh.xyz) != info['control_vertices'] or np.any(mesh.faces < 0)):
        raise ValueError('Actual chosen G6 controls disagree with their saved receipt.')
    pairs = loader.arrays(folder/'evidence.npz', ('mirror_x_vertex_pairs',
        'mirror_y_vertex_pairs', 'mirror_x_face_pairs', 'mirror_y_face_pairs'))
    for label in ('x', 'y'):
        mirror.involution(pairs['mirror_'+label+'_vertex_pairs'], len(mesh.xyz), label+' input vertices')
        mirror.involution(pairs['mirror_'+label+'_face_pairs'], len(mesh.faces), label+' input faces')
    return mesh, data['chart'], pairs, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--stage', choices=('MIDDLE', 'FINE'), required=True,
        help='Explicit saved G6 stage for a technical surface preview; no automatic design adoption.')
    args = parser.parse_args()
    root = args.root.resolve()
    incoming = root/args.stage/'SPAN/G06'
    folder = root/'SURFACE'/args.stage/'SPAN/G07'
    summary_file = root/('SURFACE_'+args.stage+'_SUMMARY.json')
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Preserved original current G6 is read-only.')
    if folder.exists() or summary_file.exists():
        raise FileExistsError('Earlier surface finish is preserved; no overwrite.')
    print('LOAD supplied actual G6 technical preview', args.stage, flush=True)
    mesh, chart, pairs, parent = load_stage(incoming, args.stage)
    parent_generation_sha256 = digest(incoming/'generation.json')
    parent_control_sha256 = parent['control_file_sha256']
    hashes = dict(parent['geometry_code_sha256'])
    hashes[str((HERE/'finish_surface.py').relative_to(REPO))] = digest(HERE/'finish_surface.py')
    guard = memory_guard()
    print('REFINE one existing neutral CC pass, actual G6 -> G7; available GiB',
        round(guard['available_GiB_before_CC'], 2), flush=True)
    out, outchart, state = core.refine(mesh, chart)
    if out.generation != 7 or len(out.faces) != 4*len(mesh.faces):
        raise ValueError('Exactly one actual neutral CC pass required.')
    print('PROPAGATE actual X/Y vertex and child-face IDs', flush=True)
    for axis, label in (('X', 'x'), ('Y', 'y')):
        vertex_pair = pairs['mirror_'+label+'_vertex_pairs']
        incoming_face_pair = pairs['mirror_'+label+'_face_pairs']
        state['mirror_'+label+'_vertex_pairs'] = mirror.refine_mirror_pairs(
            mesh.faces, state['input_edges'], vertex_pair)
        state['mirror_'+label+'_face_pairs'] = child_face_pairs(
            mesh.faces, state, vertex_pair, incoming_face_pair)
        gc.collect()
    print('VERIFY actual reflected G7 XYZ and oriented quad cycles', flush=True)
    proof = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate=args.stage+'_SURFACE',
        selected_stage=args.stage, source=str(SOURCE), source_generation=6,
        source_control_sha256=parent['source_control_sha256'],
        source_generation_json_sha256=parent['source_generation_json_sha256'],
        parent_stage=str(incoming), parent_control_sha256=parent_control_sha256,
        parent_generation_json_sha256=parent_generation_sha256,
        parent_stage_control_sha256=parent_control_sha256,
        parent_stage_generation_sha256=parent_generation_sha256,
        geometry_code_sha256=hashes, added_CC_passes=1, neutral_passes=1,
        neutral_CC_passes=1, added_topology_events=0, added_normal_field_passes=0,
        cumulative_normal_field_passes=parent['cumulative_normal_field_passes'],
        added_mandelbulb_evaluations=0, symmetry=proof, memory_guard=guard,
        operator_metadata=dict(implementation='REFERENCE_COUPLED_NEUTRAL_CC',
            input_generation=6, output_generation=7, weights={},
            weight_scope='All existing normal, affine, and later-generation weights default to zero.',
            chart_scope='Existing core.refine linear V/E/F chart transport.',
            new_directional_field_passes=0, renderer_subdivision_modifiers=0),
        design_scope='Technical surface preview on the explicitly supplied whole-column G6 state; detail-density design adoption remains separate.',
        topology_scope='Actual CC tessellation changes are saved as G7; no attached sweep/topology event.',
        validation_scope='Existing finite/closed-oriented/control connectivity/no-orphan/native-area checks once at save, plus actual G7 reflected XYZ and oriented control cycles.',
        visual_status='PENDING_MATCHED_RENDER_REVIEW',
        exclusions=['Additional field recipe', 'Amplitude alternatives',
            'Independent full geometry replay', 'Native triangle-set sorting',
            'Self-intersection repair', 'Fabrication suitability', 'Aesthetic certification'])
    del mesh, chart, pairs
    gc.collect()
    print('SAVE actual G7 and required existing mesh checks', flush=True)
    record = core.save(folder, out, outchart, context, state)
    if record['native_triangles'] != 4*record['control_quads']:
        raise ValueError('Actual native G7 must be explicit arithmetic quad-centre fans.')
    if (digest(incoming/'control_quad.npz') != parent_control_sha256 or
            digest(incoming/'generation.json') != parent_generation_sha256 or
            digest(SOURCE/'control_quad.npz') != parent['source_control_sha256']):
        raise ValueError('Preserved source or chosen G6 changed during finish.')
    write(summary_file, dict(input_case='SPAN', candidate=args.stage+'_SURFACE',
        selected_stage=args.stage, source=str(SOURCE), source_generation=6,
        source_control_sha256=parent['source_control_sha256'], parent_stage=str(incoming),
        parent_stage_control_sha256=parent_control_sha256,
        parent_stage_generation_sha256=parent_generation_sha256, folder=str(folder),
        subdivision_generation=7, added_CC_passes=1, neutral_passes=1,
        added_topology_events=0, added_normal_field_passes=0,
        control_vertices=record['control_vertices'], control_quads=record['control_quads'],
        native_vertices=record['native_vertices'], native_triangles=record['native_triangles'],
        control_file_sha256=record['control_file_sha256'],
        geometry_file_sha256=record['geometry_file_sha256'],
        evidence_file_sha256=record['evidence_file_sha256'],
        generation_json_sha256=digest(folder/'generation.json'),
        checks=record['checks'], symmetry=proof, memory_guard=guard,
        geometry_code_sha256=hashes, visual_success='PENDING_MATCHED_RENDER_REVIEW'))
    print('DONE actual G7 neutral surface finish', args.stage,
        'native triangles', record['native_triangles'], flush=True)


if __name__ == '__main__':
    main()
