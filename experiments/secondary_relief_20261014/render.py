"""Render one saved triangle-native secondary relief, without geometry processing."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/secondary_relief_20261014/trial01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/volume_junction_target_20261014/trial01/volume_finish_clean')
SOURCE_GEOMETRY_SHA256 = '74db70348be271c24f6284a94680c3d9136cb2c25a339b563c89e30b91a16122'
HELPER = HERE.parent / 'volume_junction_target_20261014/render.py'
HELPER_SHA256 = '366db5b07c43e5b0aface45493f4f76284a3ee525dbc72d71c25fd7ffec0af05'
CLEAN_RENDER = HERE.parent / 'volume_junction_target_20261014/clean_render.py'
CLEAN_RENDER_SHA256 = '33e25954fc657191c19b273163f5135556995ade6ca57c6ffde1882ddd95ba7a'
spec = importlib.util.spec_from_file_location('secondary_relief_frozen_scene_helpers', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
digest, require_close = helper.digest, helper.require_close
VIEWS, base = helper.VIEWS, helper.base


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def code_hashes():
    if digest(HELPER) != HELPER_SHA256 or digest(CLEAN_RENDER) != CLEAN_RENDER_SHA256:
        raise ValueError('Frozen native/source renderer changed.')
    return dict(render=digest(__file__), preserved_scene_helper_sha256=HELPER_SHA256,
        source_clean_renderer_sha256=CLEAN_RENDER_SHA256, preserved_renderer_hashes=helper.code_hashes())


def operation_record(info):
    recipe = info.get('recipe')
    if not isinstance(recipe, dict) or not recipe:
        raise ValueError('Actual saved secondary-relief recipe required.')
    for key, value in dict(normal_displacement_passes=1, added_topology_events=0,
            added_subdivision_passes=0, source_triangle_indices_unchanged=True,
            exact_XY_vertex_ID_symmetry=True, source_unchanged=True).items():
        if (info.get(key) is not value if isinstance(value, bool) else info.get(key) != value):
            raise ValueError('Actual saved secondary-relief operation differs: ' + key)
    for key, value in dict(added_source_subdivision_passes=0, added_topology_events=0,
            added_voxel_passes=0, added_mandelbulb_evaluations=0,
            added_normal_displacement_passes=1, source_geometry_averaged=False,
            original_growth_G8=False).items():
        if (recipe.get(key) is not value if isinstance(value, bool) else recipe.get(key) != value):
            raise ValueError('Actual saved secondary-relief recipe differs: ' + key)
    return dict(recipe=recipe, normal_displacement_passes=1,
        added_subdivision_passes=0, added_topology_events=0, added_voxel_passes=0,
        source_triangle_indices_unchanged=True, renderer_geometry_processing=False,
        distinction='One low-amplitude normal displacement on the accepted clean remesh. The inherited analytic theta/height phase does not track actual fold ridges or recover original feature memory. This is not growth G8, CC, voxel processing, branching ornament, or source-geometry smoothing. Actual generator recipe is retained verbatim; renderer applies no geometry processing.')


def source_state(root):
    root = Path(root).resolve()
    if root == SOURCE.resolve() or SOURCE.resolve() in root.parents:
        raise ValueError('Accepted clean source is read-only.')
    info = read_json(root / 'RECEIPT.json')
    request = read_json(root / 'RUN_REQUEST.json')
    parent = read_json(SOURCE / 'FINISH_RECEIPT.json')
    checks = read_json(SOURCE / 'VERIFICATION.json')
    if (info.get('candidate') != 'SECONDARY_RELIEF' or
            Path(info.get('source', '')).resolve() != SOURCE.resolve() or
            info.get('source_geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            parent.get('geometry_sha256') != SOURCE_GEOMETRY_SHA256 or
            digest(SOURCE / 'geometry.npz') != SOURCE_GEOMETRY_SHA256 or
            not checks.get('all_required_checks_pass') or
            request.get('source_finish_receipt_sha256') != digest(SOURCE / 'FINISH_RECEIPT.json') or
            request.get('source_verification_sha256') != digest(SOURCE / 'VERIFICATION.json') or
            info.get('inherited_topology_verification_sha256') != digest(SOURCE / 'VERIFICATION.json')):
        raise ValueError('Actual accepted clean source and secondary-relief receipt binding required.')
    if request.get('recipe') != info.get('recipe'):
        raise ValueError('Actual request and saved recipe differ.')
    operation_record(info)
    geometry = root / 'geometry.npz'
    if Path(info.get('geometry', '')).resolve() != geometry.resolve() or digest(geometry) != info['geometry_sha256']:
        raise ValueError('Actual secondary-relief geometry changed.')
    if info['faces_sha256'] != parent['faces_sha256']:
        raise ValueError('Actual accepted clean triangle indices must remain unchanged.')
    for relative, checksum in info['geometry_code_sha256'].items():
        if digest(REPO / relative) != checksum or digest(root / 'source_snapshot' / relative) != checksum:
            raise ValueError('Actual generator/source snapshot changed: ' + relative)
    return info, parent, dict(geometry=str(geometry), geometry_sha256=info['geometry_sha256'],
        receipt=str(root / 'RECEIPT.json'), receipt_sha256=digest(root / 'RECEIPT.json'),
        run_request=str(root / 'RUN_REQUEST.json'), run_request_sha256=digest(root / 'RUN_REQUEST.json'),
        source_geometry=str(SOURCE / 'geometry.npz'), source_geometry_sha256=SOURCE_GEOMETRY_SHA256,
        source_finish_receipt_sha256=digest(SOURCE / 'FINISH_RECEIPT.json'),
        source_verification_sha256=digest(SOURCE / 'VERIFICATION.json'))


def snapshot_sources(root):
    records = []
    for name in ('render.py', 'boards.py'):
        source = HERE / name
        relative = Path('experiments') / HERE.name / name
        target = Path(root) / 'source_snapshot_render' / relative
        checksum = digest(source)
        if target.exists():
            if digest(target) != checksum:
                raise ValueError('Earlier rendering source snapshot differs: ' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        records.append(dict(source=str(source), relative_path=relative.as_posix(),
                            snapshot=str(target), sha256=checksum))
    verify_snapshots(records)
    return records


def verify_snapshots(records):
    if not isinstance(records, list) or len(records) != 2:
        raise ValueError('Actual two rendering-script snapshots required.')
    expected = {f'experiments/{HERE.name}/{name}': digest(HERE / name) for name in ('render.py', 'boards.py')}
    if {item['relative_path']: item['sha256'] for item in records} != expected:
        raise ValueError('Actual rendering scripts differ from saved snapshots.')
    for item in records:
        if any(digest(item[key]) != item['sha256'] for key in ('source', 'snapshot')):
            raise ValueError('Actual rendering source/snapshot changed.')


def render_state(root, info, source, hashes, snapshots):
    import bpy
    import numpy as np
    from mathutils import Vector
    output = Path(root) / 'views'
    if output.exists():
        raise FileExistsError('Earlier saved native renders preserved.')
    shared_spec = importlib.util.spec_from_file_location('secondary_relief_frozen_native_scene', base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    with np.load(source['geometry'], allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    if (xyz.shape != (info['vertices'], 3) or not np.isfinite(xyz).all() or
            faces.shape != (info['triangles'], 3) or faces.dtype.kind not in 'iu' or
            faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Actual finite indexed triangle-native arrays required.')
    arrays = {key + '_sha256': hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()
              for key, value in (('xyz', xyz), ('faces', faces))}
    if any(arrays[key] != info[key] for key in arrays):
        raise ValueError('Actual saved native array hashes differ.')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for previous in list(bpy.data.meshes):
        if previous.users == 0:
            bpy.data.meshes.remove(previous)
    mesh = bpy.data.meshes.new('Actual saved SECONDARY_RELIEF native triangles')
    mesh.vertices.add(len(xyz))
    mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
    del xyz
    mesh.loops.add(3 * len(faces))
    mesh.loops.foreach_set('vertex_index', faces.ravel())
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * len(faces), 3, dtype=np.int32))
    mesh.polygons.foreach_set('loop_total', np.full(len(faces), 3, np.int32))
    del faces
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new('Actual saved SECONDARY_RELIEF native triangles', mesh)
    bpy.context.collection.objects.link(obj)
    shared.material(obj)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, base.expected_conditions())
    output.mkdir()
    actual_views, images = {}, []
    for name, (position, target, scale) in VIEWS.items():
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        actual_views[name] = dict(position=list(camera.location), target=list(target), scale=float(camera.data.ortho_scale))
        require_close(actual_views[name], dict(position=list(position), target=list(target), scale=scale), 'camera.' + name)
        path = output / (name + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        images.append(dict(view=name, filename=path.name, sha256=digest(path)))
    verify_snapshots(snapshots)
    if code_hashes() != hashes or source_state(root)[2] != source:
        raise ValueError('Actual saved source/result/code changed during rendering.')
    receipt = dict(candidate='SECONDARY_RELIEF', kind='ACTUAL_SAVED_SECONDARY_RELIEF_RENDER',
        source=source, source_arrays=arrays, vertices=info['vertices'], triangles=info['triangles'],
        operation_record=operation_record(info), blender_version=bpy.app.version_string,
        views=VIEWS, actual_views=actual_views, conditions=conditions, images=images,
        code_sha256=hashes, render_source_snapshots=snapshots,
        geometry_processing_in_renderer=False, smooth_shading=False,
        scope='Saved triangle-native relief on the accepted clean remesh; source triangle IDs retained. One actual generator normal-displacement pass, no added CC, voxel or topology event; not growth G8, actual-ridge tracking or inherited feature-memory reconstruction. Renderer displays saved native arrays at float32, without geometry processing, maps or smooth shading; no aesthetic certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('SECONDARY_RELIEF_RENDER_DONE', len(images), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    info, _, source = source_state(args.root)
    snapshots = snapshot_sources(args.root)
    render_state(args.root, info, source, hashes, snapshots)


if __name__ == '__main__':
    main()
