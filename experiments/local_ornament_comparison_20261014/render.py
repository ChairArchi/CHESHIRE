"""Render two saved local additions against one immutable original native body."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01')
VARIANTS = ('MANDELBULB', 'LEAF_CLUSTER')
HELPER = HERE.parent / 'finite_fork_folds_20261013/render.py'
HELPER_SHA256 = '8d3d1a29285ecc94b84b2fd9ece0990df8d86e2808b67b9c730b859f3f9f69ee'
SOURCE_GEOMETRY_SHA256 = '98a88c6727045e0a5aad67df6cd6295de6c14655a78ac0ca95812a5f37841e91'
spec = importlib.util.spec_from_file_location('local_ornament_frozen_native_helpers', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
digest, read_json, require_close = helper.digest, helper.read_json, helper.require_close
SOURCE, VIEWS, base, prior = helper.PARENT, helper.VIEWS, helper.base, helper.prior


def code_hashes():
    if digest(HELPER) != HELPER_SHA256:
        raise ValueError('Preserved native render helper changed.')
    return dict(render=digest(__file__), native_helper_sha256=HELPER_SHA256,
                preserved_renderer_hashes=helper.code_hashes())


def source_state(root):
    root = Path(root).resolve()
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Original SPAN source is read-only.')
    info = read_json(root / 'RECEIPT.json')
    placement = read_json(root / 'PLACEMENT.json')
    parent_info, parent_source = helper.parent_state()
    if (info.get('source_native_geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            Path(info.get('source_native_path', '')).resolve() != Path(parent_source['source']).resolve() or
            parent_source['source_sha256'] != SOURCE_GEOMETRY_SHA256 or
            info.get('placement_sha256') != digest(root / 'PLACEMENT.json')):
        raise ValueError('Actual original G7 and common placement binding required.')
    variants = info.get('variants')
    if not isinstance(variants, dict) or set(variants) != set(VARIANTS):
        raise ValueError('Exactly two actual saved local-addition variants required.')
    for name in VARIANTS:
        path = root / name / 'geometry.npz'
        if (Path(variants[name].get('geometry', '')).resolve() != path.resolve() or
                digest(path) != variants[name]['geometry_sha256']):
            raise ValueError('Actual saved added geometry differs: ' + name)
        for key in ('xyz_sha256', 'faces_sha256'):
            checksum = variants[name].get(key)
            if not isinstance(checksum, str) or len(checksum) != 64:
                raise ValueError('Actual added array hash required: ' + name + '.' + key)
    binding = dict(root=str(root), receipt=str(root / 'RECEIPT.json'),
        receipt_sha256=digest(root / 'RECEIPT.json'), placement=str(root / 'PLACEMENT.json'),
        placement_sha256=digest(root / 'PLACEMENT.json'), original_source=parent_source)
    return info, placement, parent_info, parent_source, binding


def snapshot_sources(root):
    records = []
    for name in ('render.py', 'boards.py'):
        source = HERE / name
        relative = Path('experiments') / HERE.name / name
        target = Path(root) / 'source_snapshot_render' / relative
        checksum = digest(source)
        if target.exists():
            if digest(target) != checksum:
                raise ValueError('Earlier rendering snapshot differs.')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        records.append(dict(source=str(source), relative_path=relative.as_posix(),
                            snapshot=str(target), sha256=checksum))
    verify_snapshots(records)
    return records


def verify_snapshots(records):
    if not isinstance(records, list) or len(records) != 2:
        raise ValueError('Actual two rendering source snapshots required.')
    expected = {f'experiments/{HERE.name}/{name}': digest(HERE / name) for name in ('render.py', 'boards.py')}
    if {item['relative_path']: item['sha256'] for item in records} != expected:
        raise ValueError('Actual rendering scripts differ from saved snapshots.')
    for item in records:
        if any(digest(item[key]) != item['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Rendering source/snapshot changed.')


def array_hash(array):
    import numpy as np
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()


def add_native_object(path, expected, name, shared):
    import bpy
    import numpy as np
    if digest(path) != expected['geometry_sha256']:
        raise ValueError('Saved native geometry changed before load: ' + name)
    with np.load(path, allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all() or
            faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or faces.dtype.kind not in 'iu' or
            faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Actual finite saved native triangles required: ' + name)
    arrays = dict(xyz_sha256=array_hash(xyz), faces_sha256=array_hash(faces))
    if any(arrays[key] != expected[key] for key in arrays):
        raise ValueError('Actual native array hash differs: ' + name)
    nv, nf = len(xyz), len(faces)
    if (('vertices' in expected and expected['vertices'] != nv) or
            ('triangles' in expected and expected['triangles'] != nf)):
        raise ValueError('Actual saved geometry counts differ: ' + name)
    display_xyz = np.asarray(xyz, np.float32)
    display_faces = np.asarray(faces, np.int32)
    display_hashes = dict(xyz_float32_sha256=array_hash(display_xyz), triangle_indices_int32_sha256=array_hash(display_faces))
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(nv)
    mesh.vertices.foreach_set('co', display_xyz.ravel())
    del xyz, display_xyz
    mesh.loops.add(3 * nf)
    mesh.loops.foreach_set('vertex_index', display_faces.ravel())
    del faces, display_faces
    mesh.polygons.add(nf)
    mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * nf, 3, dtype=np.int32))
    mesh.polygons.foreach_set('loop_total', np.full(nf, 3, np.int32))
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    shared.material(obj)
    return obj, dict(vertices=nv, triangles=nf, source_arrays=arrays, expected_display_arrays=display_hashes)


def body_signature(obj, counts):
    """Read back the actual body positions and native triangle connectivity."""
    import numpy as np
    mesh = obj.data
    if (len(obj.modifiers) or obj.hide_render or not np.array_equal(np.asarray(obj.matrix_world), np.eye(4)) or
            len(mesh.vertices) != counts['vertices'] or
            len(mesh.polygons) != counts['triangles'] or len(mesh.loops) != 3 * counts['triangles']):
        raise ValueError('Immutable original body state changed.')
    xyz = np.empty(3 * len(mesh.vertices), np.float32)
    mesh.vertices.foreach_get('co', xyz)
    xyz_hash = array_hash(xyz)
    del xyz
    indices = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get('vertex_index', indices)
    indices_hash = array_hash(indices)
    del indices
    smooth = np.empty(len(mesh.polygons), bool)
    mesh.polygons.foreach_get('use_smooth', smooth)
    if smooth.any():
        raise ValueError('Original body must retain actual flat native shading.')
    result = dict(xyz_float32_sha256=xyz_hash, triangle_indices_int32_sha256=indices_hash)
    if result != counts['expected_display_arrays']:
        raise ValueError('Actual original body geometry was modified inside Blender.')
    return result


def main():
    import bpy
    from mathutils import Vector
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    if any((root / name / 'views').exists() for name in VARIANTS):
        raise FileExistsError('Earlier actual variant renders preserved.')
    hashes = code_hashes()
    info, placement, parent_info, parent_source, binding = source_state(root)
    snapshots = snapshot_sources(root)
    spec = importlib.util.spec_from_file_location('local_ornament_frozen_scene', base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for previous in list(bpy.data.meshes):
        if previous.users == 0:
            bpy.data.meshes.remove(previous)
    expected_body = dict(geometry_sha256=SOURCE_GEOMETRY_SHA256,
        xyz_sha256=parent_info['checks']['native_xyz_sha256'],
        faces_sha256=parent_info['checks']['native_faces_sha256'])
    body, body_counts = add_native_object(Path(parent_source['source']), expected_body, 'Immutable original SPAN G7', shared)
    original_mesh_pointer = body.data.as_pointer()
    scene, camera = shared.setup_scene(900, 24)
    original_conditions = base.actual_conditions(bpy, scene, camera, body)
    require_close(original_conditions, base.expected_conditions())
    for name in VARIANTS:
        expected = info['variants'][name]
        path = root / name / 'geometry.npz'
        added, added_counts = add_native_object(path, expected, 'Saved local ' + name, shared)
        require_close(base.actual_conditions(bpy, scene, camera, added), original_conditions)
        output = root / name / 'views'
        output.mkdir()
        actual_views, images = {}, []
        for view, (position, target, scale) in VIEWS.items():
            camera.location = position
            camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
            camera.data.ortho_scale = scale
            actual_views[view] = dict(position=list(camera.location), target=list(target), scale=float(camera.data.ortho_scale),
                forward=list(camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))))
            require_close(actual_views[view], dict(position=list(position), target=list(target), scale=scale,
                forward=list((Vector(target) - Vector(position)).normalized())), 'camera.' + view)
            path_png = output / (view + '.png')
            scene.render.filepath = str(path_png)
            bpy.ops.render.render(write_still=True)
            images.append(dict(view=view, filename=path_png.name, sha256=digest(path_png)))
        actual_body = body_signature(body, body_counts)
        if body.data.as_pointer() != original_mesh_pointer:
            raise ValueError('Original body mesh was replaced or reloaded.')
        verify_snapshots(snapshots)
        if code_hashes() != hashes or source_state(root)[4] != binding:
            raise ValueError('Actual saved data/source/code changed during comparison.')
        result = dict(candidate=name, kind='ORIGINAL_G7_PLUS_ACTUAL_SAVED_LOCAL_ADDITION_RENDER',
            binding=binding, saved_variant=expected, saved_placement=placement,
            added_geometry=str(path), added_geometry_sha256=expected['geometry_sha256'],
            added_geometry_counts=added_counts, original_body=parent_source,
            original_body_counts=body_counts, original_body_display_readback=actual_body,
            original_body_loaded_once=True, original_body_unchanged_in_blender=True,
            body_geometry_processing=False, added_geometry_processing=False, modifiers=[], smooth_shading=False,
            source_growth_generation=7, new_source_growth_G8=False, fusion_performed=False,
            version=bpy.app.version_string, views=VIEWS, actual_views=actual_views,
            conditions=original_conditions, images=images, code_sha256=hashes,
            render_source_snapshots=snapshots,
            scope='Original saved G7 native body loaded once and retained unchanged for both variants. Each candidate adds its actual independently saved ornament mesh only. No body smoothing, remesh, G8, normal/shading map, renderer modifier or fusion. Body and addition use flat native triangles; float32 display. Attachment and aesthetic quality require actual visual review; intersections are not certified.')
        (output / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
        mesh = added.data
        bpy.data.objects.remove(added, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        gc.collect()
        print('LOCAL_ORNAMENT_RENDERED', name, len(images), 'views; original body retained', flush=True)


if __name__ == '__main__':
    main()
