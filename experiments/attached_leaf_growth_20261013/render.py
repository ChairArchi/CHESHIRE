"""Render one saved attached-leaf G7 native mesh, with no Blender geometry processing."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/attached_leaf_growth_20261013/trial01')
HELPER_RENDER = HERE.parent / 'finite_fork_folds_20261013/render.py'
HELPER_RENDER_SHA256 = '8d3d1a29285ecc94b84b2fd9ece0990df8d86e2808b67b9c730b859f3f9f69ee'
spec = importlib.util.spec_from_file_location('attached_leaf_frozen_native_helpers', HELPER_RENDER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
digest, read_json, require_close = helper.digest, helper.read_json, helper.require_close
PARENT, VIEWS, base, prior = helper.PARENT, helper.VIEWS, helper.base, helper.prior
saved_state, parent_state = helper.saved_state, helper.parent_state
COUNT_KEYS = ('source_generation', 'added_CC_passes', 'added_topology_events',
    'added_normal_field_passes', 'cumulative_normal_field_passes', 'added_mandelbulb_evaluations',
    'source_geometry_averaged')


def code_hashes():
    if digest(HELPER_RENDER) != HELPER_RENDER_SHA256:
        raise ValueError('Preserved native-render/source helpers changed.')
    return dict(render=digest(__file__), native_helpers_renderer=HELPER_RENDER_SHA256,
                preserved_native_code_sha256=helper.code_hashes())


def operation_record(info):
    operator = info.get('operator_metadata')
    if not isinstance(operator, dict) or not operator:
        raise ValueError('Actual saved connected-patch operator metadata required.')
    events = info.get('added_topology_events')
    if isinstance(events, bool) or not isinstance(events, int) or events < 0:
        raise ValueError('Actual nonnegative topology-event count required.')
    if operator.get('added_topology_events') != events:
        raise ValueError('Operator and generation must record the same actual event count.')
    return dict(counts={key: info[key] for key in COUNT_KEYS if key in info},
        operator_metadata=operator,
        renderer_geometry_processing='NONE: saved native arrays only',
        distinction='Connected patch events alter topology while subdivision remains G7. Actual event counts are read from saved metadata; no normal-field, Mandelbulb, Taubin, normal-pooling or delta-filter operations are introduced by this renderer.')


def source_state(root):
    root = Path(root).resolve()
    if root == PARENT.resolve() or PARENT.resolve() in root.parents:
        raise ValueError('Preserved SPAN G7 source is read-only.')
    folder = root / 'ATTACHED_LEAF/SPAN/G07'
    info = read_json(folder / 'generation.json')
    parent_info, parent_source = parent_state()
    if (info.get('candidate') != 'ATTACHED_LEAF' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 0 or
        info.get('added_mandelbulb_evaluations') != 0 or
        info.get('source_geometry_averaged') is not False or
        Path(info.get('source', '')).resolve() != PARENT.resolve() or
        Path(info.get('parent_stage', '')).resolve() != PARENT.resolve() or
        info.get('source_control_sha256') != parent_source['control_sha256'] or
        info.get('source_generation_json_sha256') != parent_source['generation_sha256']):
        raise ValueError('Actual original SPAN G7 plus saved attached patches required; no new CC/normal field/Mandelbulb.')
    if ('cumulative_normal_field_passes' in info and info['cumulative_normal_field_passes'] !=
            parent_info['cumulative_normal_field_passes']):
        raise ValueError('No new normal pass: inherited cumulative count must remain unchanged.')
    operation_record(info)
    source = saved_state(folder, info)
    source.update(parent_source=str(PARENT), parent_control_sha256=parent_source['control_sha256'],
                  parent_geometry_sha256=parent_source['source_sha256'],
                  parent_generation_sha256=parent_source['generation_sha256'])
    return folder, info, source, (parent_info, parent_source)


def render_state(info, source, output, hashes):
    import bpy
    import numpy as np
    from mathutils import Vector
    shared_spec = importlib.util.spec_from_file_location('attached_leaf_frozen_native_scene', base.SHARED_RENDER)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    if output.exists():
        raise FileExistsError('Existing native renders preserved: ' + str(output))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for old_mesh in list(bpy.data.meshes):
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
    with np.load(source['source'], allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
        if (xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all() or
            faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or
            not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(xyz)):
            raise ValueError('Finite saved native XYZ and indexed triangles required.')
        arrays = {key + '_sha256': hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()
                  for key, array in (('xyz', xyz), ('faces', faces))}
        if any(arrays[key + '_sha256'] != info['checks']['native_' + key + '_sha256']
               for key in ('xyz', 'faces')):
            raise ValueError('Actual loaded native hashes differ from saved result.')
        vertex_count, face_count = len(xyz), len(faces)
        mesh = bpy.data.meshes.new('Saved ATTACHED_LEAF native G7')
        mesh.vertices.add(vertex_count)
        mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
        del xyz
        mesh.loops.add(3 * face_count)
        mesh.loops.foreach_set('vertex_index', faces.ravel())
        del faces
        mesh.polygons.add(face_count)
        mesh.polygons.foreach_set('loop_start', np.arange(0, 3 * face_count, 3, dtype=np.int32))
        mesh.polygons.foreach_set('loop_total', np.full(face_count, 3, dtype=np.int32))
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new('Saved ATTACHED_LEAF native G7', mesh)
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
        actual_views[name] = dict(position=list(camera.location), target=list(target),
            scale=float(camera.data.ortho_scale),
            forward=list(camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))))
        require_close(actual_views[name], dict(position=list(position), target=list(target), scale=scale,
            forward=list((Vector(target) - Vector(position)).normalized())), 'camera.' + name)
        path = output / (name + '.png')
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        images.append(dict(view=name, filename=path.name, sha256=digest(path)))
    if (any(digest(source[key]) != source[checksum] for key, checksum in (
            ('source', 'source_sha256'), ('control_source', 'control_sha256'),
            ('generation_source', 'generation_sha256'))) or code_hashes() != hashes):
        raise ValueError('Saved native/control/metadata or renderer changed during render.')
    receipt = dict(candidate=info['candidate'], input_case=info['input_case'],
        source_generation=info['source_generation'], subdivision_generation=info['subdivision_generation'],
        added_CC_passes=info['added_CC_passes'], added_topology_events=info['added_topology_events'],
        added_normal_field_passes=info['added_normal_field_passes'],
        added_mandelbulb_evaluations=info['added_mandelbulb_evaluations'],
        operation_record=operation_record(info), native_vertices=vertex_count, native_triangles=face_count,
        version=bpy.app.version_string, views=VIEWS, actual_views=actual_views,
        conditions=conditions, code_sha256=hashes, source_arrays=arrays, images=images, **source,
        scope='Saved ATTACHED_LEAF native G7 continuing the original SPAN G7. Connected topology events are read from actual generation metadata, not counted as subdivision. Renderer applies no geometry processing, maps or smooth shading; float32 display; no independent geometry/aesthetic certification.')
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print('RENDERED', info['candidate'], 'actual G7', len(images), 'views', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source, _ = source_state(args.root)
    render_state(info, source, folder / 'views', hashes)
    if source_state(args.root)[2] != source:
        raise ValueError('Saved source/result changed while rendering.')


if __name__ == '__main__':
    main()
