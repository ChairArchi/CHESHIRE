"""One whole-column, parent-linked relief sequence on selected actual MIDDLE G7.

The existing saved CC ancestry transports the MIDDLE displacement frame.
Two normal-field passes operate only inside parent-related shoulder bands.
No new subdivision, topology event, candidate matrix, or old geometry replay.
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
PARENT = Path('E:/CHESHIRE_DATA/experiments/whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial01')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


finish = module('parent_linked_frozen_finish', HERE.parent/'whole_column_detail_20261013/finish_surface.py')
operator = module('parent_linked_fixed_operator', HERE/'parent_folds.py')
loader, core = finish.loader, finish.core
digest, write = finish.digest, finish.write


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def checked(folder, info, names):
    for name, key in names:
        if digest(folder/name) != info[key]:
            raise ValueError('Preserved source changed: '+str(folder/name))


def carry(values, edges, faces):
    """Existing CC chart association: old vertex, input edge, input face IDs."""
    return np.concatenate([values, values[edges].mean(axis=1), values[faces].mean(axis=1)])


def load():
    info = read(PARENT/'generation.json')
    if (info.get('candidate') != 'MIDDLE_SURFACE' or info.get('subdivision_generation') != 7
            or info.get('selected_stage') != 'MIDDLE' or info.get('added_CC_passes') != 1
            or not info['checks']['passed'] or not info['symmetry']['passed']):
        raise ValueError('Actual selected verified MIDDLE SURFACE G7 required.')
    checked(PARENT, info, (('control_quad.npz', 'control_file_sha256'),
        ('evidence.npz', 'evidence_file_sha256')))
    for name, checksum in info['geometry_code_sha256'].items():
        if digest(REPO/Path(name.replace('\\', '/'))) != checksum:
            raise ValueError('Frozen parent code changed: '+name)
    middle = Path(info['parent_stage'])
    middle_info = read(middle/'generation.json')
    if (middle_info.get('candidate') != 'MIDDLE' or middle_info.get('subdivision_generation') != 6
            or digest(middle/'generation.json') != info['parent_stage_generation_sha256']
            or middle_info['control_file_sha256'] != info['parent_stage_control_sha256']):
        raise ValueError('Actual MIDDLE G6 frame ancestry required.')
    checked(middle, middle_info, (('control_quad.npz', 'control_file_sha256'),
        ('evidence.npz', 'evidence_file_sha256')))
    original = Path(middle_info['source'])
    if digest(original/'control_quad.npz') != middle_info['source_control_sha256']:
        raise ValueError('Original DEPTH_08 G6 changed.')
    data = loader.arrays(PARENT/'control_quad.npz',
        ('xyz', 'faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'))
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    if (mesh.generation != 7 or mesh.surface != 'mean' or
            mesh.faces.shape != (info['control_quads'], 4) or len(mesh.xyz) != info['control_vertices']):
        raise ValueError('Saved actual parent arrays disagree with their receipt.')
    frame = loader.arrays(middle/'evidence.npz', ('directional_phase', 'feature_support'))
    faces6 = loader.arrays(middle/'control_quad.npz', ('faces',))['faces']
    xyz6 = loader.arrays(original/'control_quad.npz', ('xyz',))['xyz']
    evidence = loader.arrays(PARENT/'evidence.npz', ('input_edges', 'mirror_x_vertex_pairs',
        'mirror_y_vertex_pairs', 'mirror_x_face_pairs', 'mirror_y_face_pairs'))
    edges = evidence.pop('input_edges')
    if (edges.ndim != 2 or edges.shape[1] != 2 or edges.min() < 0 or edges.max() >= len(xyz6)
            or len(mesh.xyz) != len(xyz6)+len(edges)+len(faces6)
            or frame['directional_phase'].shape != (len(xyz6),)
            or frame['feature_support'].shape != (len(xyz6),)):
        raise ValueError('Actual saved CC V/E/F ancestry required.')
    height = float(middle_info['operator_metadata']['physical_height'])
    zmin, zmax = middle_info['operator_metadata']['actual_input_z_bounds']
    if not np.isclose(zmax-zmin, height, rtol=0, atol=1e-12):
        raise ValueError('Recorded original physical height differs.')
    phase = frame['directional_phase']
    carried_phase = np.arctan2(carry(np.sin(phase), edges, faces6),
        carry(np.cos(phase), edges, faces6))
    z = carry((xyz6[:, 2]-zmin)/height, edges, faces6)
    support = carry(frame['feature_support'], edges, faces6)
    ancestry = dict(middle_frame=str(middle), middle_generation_sha256=digest(middle/'generation.json'),
        middle_evidence_sha256=middle_info['evidence_file_sha256'],
        original_coordinate_source=str(original), original_control_sha256=middle_info['source_control_sha256'],
        method='Actual saved CC old-vertex / input-edge mean / input-face mean association; circular sin/cos transport for phase.',
        phase_scope='Registered MIDDLE displacement shoulder coordinates; not a detection of all semantic or curvature ridges.')
    return mesh, data['chart'], evidence, carried_phase, z, support, height, info, ancestry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'PARENT_LINKED/SPAN/G07'
    if folder.exists() or (root/'SUMMARY.json').exists():
        raise FileExistsError('Earlier sequence is preserved; no overwrite.')
    if root == PARENT.resolve() or PARENT.resolve() in root.parents:
        raise ValueError('Parent is read-only.')
    finish.memory_guard()
    print('LOAD selected actual MIDDLE SURFACE G7 and registered parent frame', flush=True)
    mesh, chart, pairs, phase, z, support, height, parent, ancestry = load()
    hashes = dict(parent['geometry_code_sha256'])
    for path in (HERE/'study.py', HERE/'parent_folds.py'):
        hashes[str(path.relative_to(REPO))] = digest(path)
    source_generation_sha256 = digest(PARENT/'generation.json')
    vertex_pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    print('APPLY parent-linked CHILD then GRANDCHILD normal fields on whole actual G7', flush=True)
    out, metadata, state = operator.build(mesh, chart, vertex_pairs, phase, z, support, height)
    if (out.generation != 7 or not np.array_equal(out.faces, mesh.faces)
            or out.xyz.shape != mesh.xyz.shape):
        raise ValueError('Same actual G7 topology required.')
    state.update(mirror_x_face_pairs=pairs['mirror_x_face_pairs'],
        mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    print('VERIFY actual reflected XYZ and oriented G7 quads', flush=True)
    symmetry = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='PARENT_LINKED',
        source=str(PARENT), source_generation=7, source_control_sha256=parent['control_file_sha256'],
        source_generation_json_sha256=source_generation_sha256,
        parent_stage=str(PARENT), parent_control_sha256=parent['control_file_sha256'],
        parent_generation_json_sha256=source_generation_sha256,
        geometry_code_sha256=hashes, added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=2, cumulative_normal_field_passes=parent['cumulative_normal_field_passes']+2,
        added_mandelbulb_evaluations=0, operator_metadata=metadata, frame_ancestry=ancestry,
        symmetry=symmetry, user_density_baseline='MIDDLE; preserve large grooves and broad-surface breathing room.',
        design_scope='One fixed whole-column parent-linked relief sequence on the selected saved MIDDLE G7; global FINE was not applied.',
        methodology_scope='Existing actual-input incident-normal displacement with registered compact parent bands and two authored dependent profiles; no topological branching claim.',
        intermediate_scope='CHILD is not separately saved as a native mesh; its saved delta reconstructs the actual intermediate from the unchanged parent controls.',
        validation_scope='Saved finite/closed-oriented/connectivity/no-orphan/native-area checks once, plus actual G7 reflected control XYZ and oriented quads.',
        exclusions=['Additional subdivision', 'Parameter alternatives', 'Independent full geometry replay',
            'Native triangle-set sorting', 'Self-intersection repair', 'Fabrication suitability', 'Aesthetic certification'])
    del mesh, pairs, phase, z, support
    gc.collect()
    print('SAVE one actual final G7 and required mesh checks', flush=True)
    record = core.save(folder, out, chart, context, state)
    if (digest(PARENT/'control_quad.npz') != parent['control_file_sha256']
            or digest(PARENT/'generation.json') != source_generation_sha256):
        raise ValueError('Preserved selected parent changed during sequence.')
    write(root/'SUMMARY.json', dict(source=str(PARENT), source_generation=7,
        candidate='PARENT_LINKED', input_case='SPAN', folder=str(folder), subdivision_generation=7,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=2,
        generation_json_sha256=digest(folder/'generation.json'),
        checks=record['checks'], symmetry=symmetry, operator_metadata=metadata, frame_ancestry=ancestry,
        geometry_code_sha256=hashes, visual_success='PENDING_ACTUAL_WHOLE_AND_CLOSE_RENDER_REVIEW'))
    print('DONE one whole-column parent-linked G7; no added CC', flush=True)


if __name__ == '__main__':
    main()
