"""Build one actual voxel/smooth target and project requested original controls.

Run with Blender in background mode. This writes a separate geometric target,
not a renderer modifier or an edited source. The caller alone applies eligible
projection displacements to its original G7 control topology and checks them.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import math
import shutil
import sys
import time
import traceback

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


RECIPE = dict(
    schema='CHESHIRE_ACTUAL_VOLUME_JUNCTION_TARGET_20261014',
    voxel_size_height_fraction=.0018,
    remesh_mode='VOXEL', remesh_adaptivity=0.,
    remesh_use_remove_disconnected=False, remesh_use_smooth_shade=False,
    smooth_factor=.65, smooth_iterations=6, smooth_axes=[True, True, True],
    maximum_projection_distance_height_fraction=.0075,
    eligible_rule='A nearest target point exists within .0075H, actual measured point distance <= .0075H, and normalized original-source normal dot normalized actual-target normal >= 0.',
    target_scope='Full original saved native geometry -> applied Blender voxel remesh -> applied Smooth modifier. Actual post-modifier target arrays are saved once.',
    application_scope='Only requested canonical original G7 controls are queried. This script does not apply any projected point to source geometry.',
    interpretation='One geometric volumetric target; no render smoothing trick, Mandelbulb evaluation, source subdivision, added source topology or automatic aesthetic certification.',
)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def array_hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def actual_properties(modifier):
    """Snapshot actual scalar/vector RNA settings, including defaults."""
    result = {}
    for prop in modifier.bl_rna.properties:
        key = prop.identifier
        if key == 'rna_type':
            continue
        try:
            value = getattr(modifier, key)
            if isinstance(value, (str, bool, int, float)):
                result[key] = value
            elif prop.is_array:
                result[key] = list(value)
        except (AttributeError, TypeError, ValueError):
            continue
    return result


def purge_unused_meshes():
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    gc.collect()


def summary(value):
    value = np.asarray(value, float)
    finite = value[np.isfinite(value)]
    return dict(count=int(value.size), finite_count=int(finite.size),
        minimum=float(finite.min()) if finite.size else None,
        maximum=float(finite.max()) if finite.size else None,
        quantiles=np.quantile(finite, [0., .5, .9, .99, 1.]).tolist() if finite.size else None)


def load_native(path):
    """Same saved-native foreach_set path as the existing frozen renderer."""
    with np.load(path, allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all() or
            faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or
            faces.dtype.kind not in 'iu' or faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Finite saved native XYZ and actual indexed triangles required.')
    counts = dict(vertices=len(xyz), triangles=len(faces),
        xyz_sha256=array_hash(xyz), faces_sha256=array_hash(faces),
        xyz_dtype=str(xyz.dtype), faces_dtype=str(faces.dtype))
    mesh = bpy.data.meshes.new('CHESHIRE original saved native geometry')
    mesh.vertices.add(len(xyz))
    mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
    del xyz
    count = len(faces)
    mesh.loops.add(3*count)
    mesh.loops.foreach_set('vertex_index', faces.ravel())
    del faces
    mesh.polygons.add(count)
    mesh.polygons.foreach_set('loop_start', np.arange(0, 3*count, 3, dtype=np.int32))
    mesh.polygons.foreach_set('loop_total', np.full(count, 3, dtype=np.int32))
    gc.collect()
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new('CHESHIRE actual volume target', mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj, counts


def build_target(obj, height):
    modifier = obj.modifiers.new('Actual fixed voxel target', 'REMESH')
    modifier.mode = 'VOXEL'
    modifier.voxel_size = height*RECIPE['voxel_size_height_fraction']
    modifier.adaptivity = 0.
    modifier.use_remove_disconnected = False
    modifier.use_smooth_shade = False
    voxel_properties = actual_properties(modifier)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    purge_unused_meshes()
    voxel_counts = dict(vertices=len(obj.data.vertices), polygons=len(obj.data.polygons))
    if not voxel_counts['vertices'] or not voxel_counts['polygons']:
        raise ValueError('Fixed voxel target produced no actual geometry.')
    print('VOXEL_APPLIED', voxel_counts, flush=True)
    modifier = obj.modifiers.new('Actual fixed target smoothing', 'SMOOTH')
    modifier.factor = .65
    modifier.iterations = 6
    modifier.use_x = modifier.use_y = modifier.use_z = True
    modifier.vertex_group = ''
    smooth_properties = actual_properties(modifier)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    purge_unused_meshes()
    if len(obj.modifiers):
        raise ValueError('The saved target must have both geometry modifiers applied.')
    obj.data.update()
    obj.data.calc_loop_triangles()
    xyz = np.empty((len(obj.data.vertices), 3), np.float32)
    triangles = np.empty((len(obj.data.loop_triangles), 3), np.int32)
    obj.data.vertices.foreach_get('co', xyz.ravel())
    obj.data.loop_triangles.foreach_get('vertices', triangles.ravel())
    if not len(triangles) or not np.isfinite(xyz).all() or triangles.min() < 0 or triangles.max() >= len(xyz):
        raise ValueError('Actual post-modifier target arrays are invalid.')
    record = dict(remesh_actual_properties=voxel_properties,
        smooth_actual_properties=smooth_properties, after_voxel_counts=voxel_counts,
        target_vertex_count=len(xyz), target_triangle_count=len(triangles),
        target_polygon_count=len(obj.data.polygons),
        target_xyz_sha256=array_hash(xyz), target_triangles_sha256=array_hash(triangles),
        target_xyz_dtype=str(xyz.dtype), target_triangles_dtype=str(triangles.dtype),
        object_matrix_world=[list(row) for row in obj.matrix_world], remaining_modifier_count=0,
        target_triangle_scope='Actual Blender calc_loop_triangles of the applied post-Smooth target mesh.')
    return xyz, triangles, record


def project(obj, source_xyz, source_normals, maximum_distance):
    bpy.context.view_layer.update()
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get(), epsilon=0.)
    if bvh is None:
        raise ValueError('Actual target BVH could not be built.')
    count = len(source_xyz)
    points = source_xyz.copy()
    normals = np.zeros((count, 3), float)
    distance = np.full(count, np.inf)
    normal_dot = np.full(count, -1., float)
    face_index = np.full(count, -1, np.int64)
    eligible = np.zeros(count, bool)
    source_length = np.linalg.norm(source_normals, axis=1)
    counts = dict(rejected_invalid_source_normal=0, rejected_no_nearest_within_distance=0,
        rejected_actual_distance=0, rejected_target_normal=0, rejected_opposed_normal=0, accepted=0)
    for index, point in enumerate(source_xyz):
        if source_length[index] <= 1e-12:
            counts['rejected_invalid_source_normal'] += 1
            continue
        location, normal, triangle, bvh_distance = bvh.find_nearest(Vector(point), maximum_distance)
        if location is None:
            counts['rejected_no_nearest_within_distance'] += 1
            continue
        points[index] = location
        distance[index] = float(np.linalg.norm(points[index]-point))
        face_index[index] = int(triangle)
        target_normal = np.asarray(normal, float)
        normal_length = np.linalg.norm(target_normal)
        if not math.isfinite(distance[index]) or distance[index] > maximum_distance:
            counts['rejected_actual_distance'] += 1
            continue
        if not np.isfinite(target_normal).all() or normal_length <= 1e-12:
            counts['rejected_target_normal'] += 1
            continue
        normals[index] = target_normal/normal_length
        normal_dot[index] = float(np.dot(source_normals[index]/source_length[index], normals[index]))
        if normal_dot[index] < 0.:
            counts['rejected_opposed_normal'] += 1
            continue
        eligible[index] = True
        counts['accepted'] += 1
        if (index+1) % 25000 == 0:
            print('PROJECT', index+1, '/', count, 'accepted', counts['accepted'], flush=True)
    if sum(counts.values()) != count:
        raise ValueError('Actual projection acceptance/rejection counts do not partition the request.')
    if (not np.isfinite(points).all() or not np.isfinite(normals).all() or
            np.any(distance[eligible] > maximum_distance) or np.any(normal_dot[eligible] < 0.)):
        raise ValueError('Actual accepted target projections violate the fixed guard.')
    state = dict(points=points, normal=normals, distance=distance, eligible=eligible,
        normal_dot=normal_dot, target_face_index=face_index)
    record = dict(requested_canonical_control_count=count, rejection_counts=counts,
        actual_distance=summary(distance), eligible_distance=summary(distance[eligible]),
        eligible_source_target_normal_dot=summary(normal_dot[eligible]),
        maximum_projection_distance=maximum_distance,
        bvh='mathutils.bvhtree.BVHTree.FromObject of the actual target with all modifiers already applied',
        no_hit_storage='Original source point, zero target normal, distance=+inf, face_index=-1, eligible=False.',
        rejected_hit_storage='Actual nearest point retained for evidence; eligible=False prevents application.',
        target_normal_scope='Actual BVH geometric normal; normalized before the original-source-normal dot guard.',
        arrays={key+'_sha256': array_hash(value) for key, value in state.items()})
    return state, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if not bpy.app.background:
        raise RuntimeError('Run this geometric target script in a dedicated Blender background process.')
    root = args.root.resolve()
    request_json, request_npz = root/'projection_request.json', root/'projection_request.npz'
    target_path, projection_path = root/'target_geometry.npz', root/'projection_result.npz'
    receipt_path, failure_path = root/'TARGET_RECEIPT.json', root/'TARGET_FAILURE.json'
    if any(path.exists() for path in (target_path, projection_path, receipt_path, failure_path)):
        raise FileExistsError('Existing target/projection/checkpoint preserved; select a new empty target root.')
    request = json.loads(request_json.read_text(encoding='utf-8'))
    requested_npz = Path(request['request_npz']).resolve()
    if requested_npz != request_npz:
        raise ValueError('Request NPZ must be projection_request.npz beside the request JSON.')
    source = Path(request['source_native_path']).resolve()
    if root == source.parent or root in source.parents or source.parent in root.parents:
        raise ValueError('Target root must be separate from the preserved original native source directory.')
    height, maximum_distance = float(request['height']), float(request['max_distance'])
    if not math.isfinite(height) or height <= 0. or not math.isclose(maximum_distance, .0075*height, rel_tol=1e-12, abs_tol=1e-15):
        raise ValueError('Positive physical source height and fixed .0075H maximum distance required.')
    hashes = dict(source_native_sha256=digest(source), request_json_sha256=digest(request_json),
        request_npz_sha256=digest(request_npz), build_target_code_sha256=digest(__file__))
    for key in ('source_native_sha256', 'request_npz_sha256'):
        if key in request and request[key] != hashes[key]:
            raise ValueError('Actual request/source bytes differ from requested binding: '+key)
    snapshot = root/'source_snapshot_target'
    snapshot.mkdir(parents=True, exist_ok=False)
    for path in (Path(__file__), request_json, request_npz):
        shutil.copyfile(path, snapshot/path.name)
    with np.load(request_npz, allow_pickle=False) as data:
        source_xyz = data['xyz']
        vertex_ids = data['vertex_ids']
        source_normals = data['source_normals']
    if (source_xyz.ndim != 2 or source_xyz.shape[1] != 3 or not len(source_xyz) or
            source_normals.shape != source_xyz.shape or not np.isfinite(source_xyz).all() or not np.isfinite(source_normals).all() or
            vertex_ids.shape != (len(source_xyz),) or vertex_ids.dtype.kind not in 'iu' or
            vertex_ids.min() < 0 or len(np.unique(vertex_ids)) != len(vertex_ids)):
        raise ValueError('Finite requested original G7 canonical XYZ/normals and unique actual vertex IDs required.')
    started = time.perf_counter()
    phase = 'LOAD_NATIVE'
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        purge_unused_meshes()
        print('LOAD actual original saved native geometry', flush=True)
        obj, native_record = load_native(source)
        phase = 'APPLY_FIXED_VOXEL_AND_SMOOTH'
        print('BUILD fixed actual voxel target', 'voxel_size', height*.0018, flush=True)
        target_xyz, target_triangles, target_record = build_target(obj, height)
        np.savez_compressed(target_path, xyz=target_xyz, triangles=target_triangles)
        del target_xyz, target_triangles
        gc.collect()
        phase = 'PROJECT_ORIGINAL_CANONICAL_CONTROLS'
        print('PROJECT original canonical controls', len(source_xyz), flush=True)
        state, projection_record = project(obj, source_xyz, source_normals, maximum_distance)
        state['vertex_ids'] = vertex_ids.copy()
        np.savez_compressed(projection_path, **state)
        if (digest(source) != hashes['source_native_sha256'] or digest(request_json) != hashes['request_json_sha256'] or
                digest(request_npz) != hashes['request_npz_sha256'] or digest(__file__) != hashes['build_target_code_sha256']):
            raise ValueError('Original source, request or frozen target builder changed during execution.')
        record = dict(date='2026-10-14', timezone='Asia/Seoul', recipe=RECIPE,
            source_native_path=str(source), request_json=str(request_json), request_npz=str(request_npz),
            height=height, target_path=str(target_path), projection_path=str(projection_path),
            target_file_sha256=digest(target_path), projection_file_sha256=digest(projection_path),
            input_hashes=hashes, native_source=native_record, actual_target=target_record,
            actual_projection=projection_record,
            original_request_arrays={key+'_sha256': array_hash(value) for key, value in dict(
                xyz=source_xyz, vertex_ids=vertex_ids, source_normals=source_normals).items()},
            blender_version=bpy.app.version_string, blender_version_tuple=list(bpy.app.version),
            elapsed_target_and_projection_seconds=time.perf_counter()-started,
            source_files_unchanged=True, original_G7_geometry_modified=False,
            geometry_target_saved=True, renderer_geometry_processing=False,
            source_output_subdivision_generations=0, added_source_topology_events=0,
            self_intersection='NOT_CERTIFIED', fabrication='NOT_CHECKED',
            visual_success='NOT_ASSESSED_BY_TARGET_BUILDER')
        write(receipt_path, record)
        print('DONE target and eligible projection evidence', flush=True)
    except Exception as error:
        write(failure_path, dict(date='2026-10-14', timezone='Asia/Seoul', phase=phase,
            error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(),
            recipe=RECIPE, input_hashes=hashes, blender_version=bpy.app.version_string,
            elapsed_seconds=time.perf_counter()-started, original_G7_geometry_modified=False,
            partial_target_exists=target_path.exists(), partial_projection_exists=projection_path.exists()))
        raise


if __name__ == '__main__':
    main()
