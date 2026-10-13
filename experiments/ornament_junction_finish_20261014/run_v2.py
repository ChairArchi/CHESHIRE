"""Smooth-target correction of the existing SPAN overlap band, before detail.

Current G7 geometry is restricted to its actual old G4 vertex prefix. Three
actual neutral CC target computations reconstruct a repair surrogate on the
existing G7 IDs; a bounded target-minus-source delta is locally blended.
No source subdivision beyond G7 or historical design replay is claimed.
"""
from pathlib import Path
import argparse
import gc
import importlib.util
import json
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


SOURCE_LOADER = HERE.parent/'finite_fork_folds_20261013/run.py'
previous = module('junction_preserved_source_loader', SOURCE_LOADER)
operator = module('junction_selected_target_operator', HERE/'junction_operator_v2.py')
core, loader, digest, write = previous.core, previous.loader, previous.digest, previous.write
SOURCE = previous.SOURCE
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/ornament_junction_finish_20261014/trial02')
G5 = Path('E:/CHESHIRE_DATA/experiments/coherent_fold_detail_20261013/trial01/DIRECTIONAL/SPAN/G05')
G6 = Path('E:/CHESHIRE_DATA/experiments/directional_g6_20261013/trial01/DEPTH_08/SPAN/G06')
G7 = Path('E:/CHESHIRE_DATA/experiments/whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07')
POLYGON = np.array([[84, 870], [75, 810], [110, 745], [178, 670], [260, 616],
    [355, 568], [525, 525], [735, 487], [810, 502], [850, 558], [823, 623],
    [752, 682], [682, 718], [546, 764], [407, 822], [231, 858]], float)
CAMERA = dict(position=[-18., 28., 12.], target=[-.6, .72, 6.6], scale=1.25,
    image_size=[900, 900], feather_pixels=32., visible_depth_tolerance=.10,
    scope='Approximate trace of the user-marked band in the exact saved close camera; original native image is not edited.')


def project(xyz):
    pos, target = np.array(CAMERA['position']), np.array(CAMERA['target'])
    forward = target-pos
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0., 0., 1.])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    relative = xyz-target
    pixels = np.column_stack([450+relative@right*720, 450-relative@up*720])
    depth = (xyz-pos)@forward
    return pixels, depth


def polygon_distance(points):
    inside = np.zeros(len(points), bool)
    distance2 = np.full(len(points), np.inf)
    x, y = points.T
    for a, b in zip(POLYGON, np.roll(POLYGON, -1, axis=0)):
        crossing = (a[1] > y) != (b[1] > y)
        intersection = (b[0]-a[0])*(y-a[1])/(b[1]-a[1]+1e-30)+a[0]
        inside ^= crossing & (x < intersection)
        edge = b-a
        s = np.clip((points-a)@edge/(edge@edge), 0., 1.)
        difference = points-(a+s[:, None]*edge)
        distance2 = np.minimum(distance2, np.einsum('ij,ij->i', difference, difference))
    return inside, np.sqrt(distance2)


def selection(mesh, coarse_count, pairs, coarse_faces):
    depth_image = np.full(900*900, np.inf)
    for start in range(0, len(mesh.xyz), 262144):
        pixel, depth = project(mesh.xyz[start:start+262144])
        xy = np.rint(pixel).astype(np.int64)
        valid = np.all((xy >= 0) & (xy < 900), axis=1)
        np.minimum.at(depth_image, xy[valid, 1]*900+xy[valid, 0], depth[valid])
    xyz = mesh.xyz[:coarse_count]
    pixel, depth = project(xyz)
    inside, distance = polygon_distance(pixel)
    xy = np.clip(np.rint(pixel).astype(np.int64), 0, 899)
    visible = depth <= depth_image[xy[:, 1]*900+xy[:, 0]]+CAMERA['visible_depth_tolerance']
    canonical = (xyz[:, 0] < 0) & (xyz[:, 1] > 0)
    weight = np.clip(distance/CAMERA['feather_pixels'], 0., 1.)
    weight = weight*weight*(3-2*weight)
    weight[~(inside & visible & canonical)] = 0.
    px, py = pairs['mirror_x_vertex_pairs'][:coarse_count], pairs['mirror_y_vertex_pairs'][:coarse_count]
    if max(px.max(), py.max()) >= coarse_count:
        raise ValueError('Actual old G4 prefix does not carry its reflection orbits.')
    weight = np.maximum.reduce([weight, weight[px], weight[py], weight[px[py]]])
    # Pin a two-edge collar inside the selected support. Polygon feather and
    # visible-depth boundaries therefore cannot leak into adjacent old geometry.
    active = weight > 0
    for _ in range(2):
        boundary_faces = np.any(~active[coarse_faces], axis=1)
        blocked = np.unique(coarse_faces[boundary_faces])
        active[blocked] = False
    weight[~active] = 0.
    if np.count_nonzero(weight) < 100:
        raise ValueError('User-marked visible region has insufficient coarse support.')
    return weight, dict(camera=CAMERA, pixel_polygon=POLYGON.tolist(),
        canonical_visible_count=int(np.count_nonzero((weight > 0) & canonical)),
        reflected_selected_coarse_count=int(np.count_nonzero(weight)),
        boundary_collar_edges=2, selection_sha256=previous.prior.array_hash(weight),
        target='Original WALL-born irregular overlap band in the user annotation; not later top Task32 events or ATTACHED_LEAF.')


def load_lifts(mesh):
    bindings, stages = [], []
    g5info = json.loads((G5/'generation.json').read_text(encoding='utf-8'))
    g4 = Path(g5info['source'])
    for incoming, outgoing in [(g4, G5), (G5, G6), (G6, G7)]:
        info = json.loads((incoming/'generation.json').read_text(encoding='utf-8'))
        next_info = json.loads((outgoing/'generation.json').read_text(encoding='utf-8'))
        if (digest(incoming/'control_quad.npz') != info['control_file_sha256'] or
                digest(outgoing/'evidence.npz') != next_info['evidence_file_sha256']):
            raise ValueError('Preserved hierarchy bytes changed.')
        with np.load(incoming/'control_quad.npz', allow_pickle=False) as data:
            faces = data['faces']; count = len(data['xyz'])
        with np.load(outgoing/'evidence.npz', allow_pickle=False) as data:
            edges = data['input_edges']
        if count+len(edges)+len(faces) != next_info['control_vertices']:
            raise ValueError('Saved V/E/F birth counts do not match the next stage.')
        stages.append(dict(input_edges=edges, input_faces=faces))
        bindings.append(dict(input=str(incoming), output=str(outgoing),
            input_generation_sha256=digest(incoming/'generation.json'),
            input_control_sha256=info['control_file_sha256'],
            output_generation_sha256=digest(outgoing/'generation.json'),
            output_evidence_sha256=next_info['evidence_file_sha256']))
    if next_info['control_vertices'] != len(mesh.xyz):
        raise ValueError('Saved hierarchy does not reach actual current G7 controls.')
    return g5info['source'], stages, bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    started = time.perf_counter()
    root = args.root.resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError('Earlier output preserved; select a new empty root.')
    guard = previous.base.finish.memory_guard()
    root.mkdir(parents=True, exist_ok=True)
    print('LOAD actual original SPAN G7 and saved linear hierarchy', flush=True)
    mesh, chart, pairs, coords, height, source, ancestry, frame = previous.load()
    source_hash = previous.prior.array_hash(mesh.xyz)
    coarse_path, lifts, hierarchy = load_lifts(mesh)
    coarse_info = json.loads((Path(coarse_path)/'generation.json').read_text(encoding='utf-8'))
    coarse_count = coarse_info['control_vertices']
    mask, region = selection(mesh, coarse_count, pairs, lifts[0]['input_faces'])
    hashes = dict(source['geometry_code_sha256'])
    hashes.update(operator.code_hashes())
    for path in (Path(__file__), SOURCE_LOADER, HERE.parent/'finite_fork_folds_20261013/fold_operator.py'):
        hashes[path.relative_to(REPO).as_posix()] = digest(path)
    for rel, expected in hashes.items():
        path = REPO/rel.replace('\\', '/')
        if digest(path) != expected:
            raise ValueError('Frozen source mismatch: '+rel)
        dest = root/'source_snapshot'/rel.replace('\\', '/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    request = dict(date='2026-10-14', timezone='Asia/Seoul', basis_commit='723f778e550ba82bf0b7be0846b4475daa407d15',
        source=str(SOURCE), source_receipt_sha256=previous.SOURCE_RECEIPT_SHA256,
        candidate='JUNCTION_TARGET', input_case='SPAN', subdivision_generation=7,
        purpose='One correction after crumpled delta-only trial01; smooth local target on the same original marked SPAN, retaining protrusion and actual coarse/fine rim anchors.',
        new_detail_deferred=True, new_micro_lip_geometry_executed=False,
        excluded_inputs=['CENTRAL_SPINDLE', 'FINITE_FORK', 'ATTACHED_LEAF'],
        recipe=operator.RECIPE, selected_region=region, hierarchy=hierarchy)
    write(root/'RUN_REQUEST.json', request)
    write(root/'RECIPE.json', dict(request, geometry_code_sha256=hashes, frame_bindings=frame))
    reflection = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    print('BUILD smooth neutral-CC target from current coarse guide; locally blend target minus actual G7', flush=True)
    out, metadata, state = operator.build(mesh, chart, reflection,
        lifts[0]['input_faces'], coarse_count, mask, lifts, height)
    state.update(mirror_x_face_pairs=pairs['mirror_x_face_pairs'], mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    if previous.prior.array_hash(mesh.xyz) != source_hash or not np.array_equal(out.faces, mesh.faces):
        raise ValueError('Actual input mutated or topology changed.')
    symmetry = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='JUNCTION_TARGET', source=str(SOURCE), source_generation=7,
        source_control_sha256=source['control_file_sha256'], source_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256,
        parent_stage=str(SOURCE), parent_control_sha256=source['control_file_sha256'],
        parent_generation_json_sha256=previous.SOURCE_RECEIPT_SHA256, geometry_code_sha256=hashes,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=0,
        cumulative_normal_field_passes=source['cumulative_normal_field_passes'], added_mandelbulb_evaluations=0,
        source_geometry_averaged=True, operator_metadata=metadata, selected_region=region,
        hierarchy=hierarchy, frame_ancestry=ancestry, symmetry=symmetry, memory_guard_before_load=guard,
        methodology_scope='Current G7 old-G4-prefix local fairing; three actual neutral CC target evaluations on exact saved topology; locally blend target minus actual G7, suppressing residual rather than only lifting a guide delta. Output remains G7; target computations are recorded separately from added source generations.',
        exclusions=['Microdetail generation', 'New large ornament', 'G8', 'Whole-column smoothing',
            'Task32-cap assumption for WALL event0', 'Collision repair', 'Fabrication certification', 'Aesthetic certification'])
    del mesh, coords, reflection, lifts, pairs
    gc.collect()
    folder = root/'JUNCTION_TARGET/SPAN/G07'
    print('SAVE actual repaired G7 and required full mesh checks once', flush=True)
    record = core.save(folder, out, chart, context, state)
    if digest(SOURCE/'generation.json') != previous.SOURCE_RECEIPT_SHA256:
        raise ValueError('Original source changed.')
    previous.base.checked(SOURCE, source, (('control_quad.npz', 'control_file_sha256'), ('evidence.npz', 'evidence_file_sha256')))
    for rel, expected in hashes.items():
        if digest(REPO/rel) != expected:
            raise ValueError('Source code changed during execution: '+rel)
    write(root/'SUMMARY.json', dict(date='2026-10-14', timezone='Asia/Seoul', source=str(SOURCE),
        candidate='JUNCTION_TARGET', input_case='SPAN', folder=str(folder), subdivision_generation=7,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=0, added_mandelbulb_evaluations=0,
        source_geometry_averaged=True, generation_json_sha256=digest(folder/'generation.json'),
        control_vertices=len(out.xyz), control_quads=len(out.faces), native_triangles=record['native_triangles'],
        checks=record['checks'], symmetry=symmetry, operator_metadata=metadata, selected_region=region,
        hierarchy=hierarchy, geometry_code_sha256=hashes,
        elapsed_generation_seconds=time.perf_counter()-started, actual_generation_process_memory=previous.process_memory(),
        visual_success='PENDING_ACTUAL_MATCHED_RENDER_REVIEW'))
    print('DONE local junction repair candidate; no small detail generation', flush=True)


if __name__ == '__main__':
    main()
