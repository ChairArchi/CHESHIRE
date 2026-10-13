"""Render one saved FINITE_FORK G7; no geometry processing occurs in Blender."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/finite_fork_folds_20261013/trial02')
PARENT = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
PARENT_RENDER = HERE.parent / 'medium_root_folds_20261013/finish_render.py'
PARENT_RENDER_SHA256 = '212aefe64f0115ce4c5be5fe5b18056e299842b890f881e25bcca828474b5c14'
spec = importlib.util.spec_from_file_location('finite_fork_frozen_parent_renderer', PARENT_RENDER)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
digest, read_json, require_close = prior.digest, prior.read_json, prior.require_close
VIEWS = prior.VIEWS
base = prior.raw.parent.surface.raw.base
COUNT_KEYS = ('source_generation', 'added_CC_passes', 'added_topology_events',
    'added_normal_field_passes', 'cumulative_normal_field_passes', 'added_mandelbulb_evaluations')


def code_hashes():
    if digest(PARENT_RENDER) != PARENT_RENDER_SHA256:
        raise ValueError('Preserved actual G7 renderer changed.')
    return dict(render=digest(__file__), parent_renderer=PARENT_RENDER_SHA256,
                parent_code_sha256=prior.code_hashes())


def saved_state(folder, info):
    return prior.raw.parent.saved_state(folder, info)


def parent_state():
    info = read_json(PARENT / 'generation.json')
    if (info.get('candidate') != 'WIDE_ROOT_FINISHED' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes_this_finish') != 0 or
        info.get('finish_smoothing_passes') != 3):
        raise ValueError('Actual preserved WIDE_ROOT_FINISHED SPAN G7 required.')
    return info, saved_state(PARENT, info)


def operation_record(info):
    """Keep geometry averaging, pooled normals and filtered displacement separate."""
    operator = info.get('operator_metadata')
    if not isinstance(operator, dict) or not operator:
        raise ValueError('Actual saved operator metadata required.')
    expected = dict(source_geometry_averaged=True, geometry_smoothing_steps=72,
        taubin_pairs=36, taubin_lambda=.50, taubin_mu=-.53,
        normal_pooling_steps=3, delta_smoothing_steps=3, normal_field_passes=1,
        added_CC_passes=0, added_topology_events=0, added_mandelbulb_evaluations=0)
    if any(operator.get(key) != value for key, value in expected.items()):
        raise ValueError('One fixed saved geometry-fairing/normal-pooling/delta-filter sequence required.')
    separate = dict(source_geometry_averaged=operator['source_geometry_averaged'],
        geometry_taubin=dict(steps=operator['geometry_smoothing_steps'], pairs=operator['taubin_pairs'],
                            lambda_value=operator['taubin_lambda'], mu_value=operator['taubin_mu']),
        normal_pooling_steps=operator['normal_pooling_steps'],
        delta_smoothing_steps=operator['delta_smoothing_steps'])
    if 'normal_pooling_scope' in operator:
        separate['normal_pooling_scope'] = operator['normal_pooling_scope']
    return dict(counts={key: info[key] for key in COUNT_KEYS if key in info},
                generator_operations=separate, operator_metadata=operator,
                renderer_geometry_processing='NONE: only saved native arrays are displayed',
                distinction='Source-geometry Taubin averaging, normal pooling and new-delta filtering are separate generator operations; none is a subdivision generation or render modifier.')


def source_state(root):
    root = Path(root).resolve()
    if root == PARENT.resolve() or PARENT.resolve() in root.parents:
        raise ValueError('Preserved G7 source is read-only.')
    folder = root / 'FINITE_FORK/SPAN/G07'
    info = read_json(folder / 'generation.json')
    parent_info, parent_source = parent_state()
    if (info.get('candidate') != 'FINITE_FORK' or info.get('input_case') != 'SPAN' or
        info.get('source_generation') != 7 or info.get('subdivision_generation') != 7 or
        info.get('added_CC_passes') != 0 or info.get('added_topology_events') != 0 or
        info.get('added_normal_field_passes') != 1 or info.get('added_mandelbulb_evaluations') != 0 or
        Path(info.get('source', '')).resolve() != PARENT.resolve() or
        Path(info.get('parent_stage', '')).resolve() != PARENT.resolve() or
        info.get('source_control_sha256') != parent_source['control_sha256'] or
        info.get('source_generation_json_sha256') != parent_source['generation_sha256']):
        raise ValueError('Actual original SPAN G7 plus one saved FINITE_FORK field required; no new CC/topology/Mandelbulb.')
    if ('cumulative_normal_field_passes' in info and info['cumulative_normal_field_passes'] !=
            parent_info['cumulative_normal_field_passes'] + 1):
        raise ValueError('New normal pass must be counted separately from actual source history.')
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
    shared_spec = importlib.util.spec_from_file_location('finite_fork_frozen_native_scene', base.SHARED_RENDER)
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
        mesh = bpy.data.meshes.new('Saved FINITE_FORK native G7')
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
        obj = bpy.data.objects.new('Saved FINITE_FORK native G7', mesh)
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
        scope='Saved FINITE_FORK native G7 continuing the preserved SPAN G7; generator geometry averaging, normal pooling and delta filtering stay separately recorded. Renderer applies no geometry averaging, subdivision, modifier, maps or smooth shading; float32 display; no geometry/aesthetic certification.')
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
