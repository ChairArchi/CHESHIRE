"""Actual small local meshes under one intrinsic engineering view.

This is an internal causal diagnostic, not a replacement for the failed
whole-column presentation camera. Geometry, normals and topology are not
processed. Every state uses the same camera, material, lights and pixels.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
FAST_PATH = HERE.parent/'fold_junction_development_20261015/fast_render.py'
FAST_SHA = '45a48c67b5f260f83d74e1b481ac1e3d37dfbc9441a25e3185a8b9621b3c2247'
spec = importlib.util.spec_from_file_location('local_diagnostic_frozen_loader', FAST_PATH)
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)
digest, write = fast.digest, fast.write


def unit(value):
    value = np.asarray(value, np.float64)
    length = np.linalg.norm(value)
    if not np.isfinite(length) or length < 1e-12:
        raise ValueError('Finite nonzero intrinsic direction required.')
    return value/length


def checked_manifest(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    names = set(value.get('meshes', {}))
    if (value.get('schema') != 'CHESHIRE_LOCAL_FORMATION_DIAGNOSTIC_V1' or
            names not in ({'NEUTRAL', 'FORMED', 'DELIVERED'},
                          {'NEUTRAL', 'FORMED', 'CARRIER', 'DELIVERED'})):
        raise ValueError('Exact neutral/formed/[carrier]/delivered local mesh manifest required.')
    records = {}
    for name, record in value['meshes'].items():
        record = dict(record)
        p = Path(record['geometry'])
        p = p.resolve() if p.is_absolute() else (path.parent/p).resolve()
        record['geometry'] = str(p)
        if digest(p) != record['geometry_sha256']:
            raise ValueError('Actual local mesh bytes changed: '+name)
        records[name] = record
    for source, checksum in value.get('sources', {}).items():
        p = Path(source)
        p = p if p.is_absolute() else path.parent/p
        if digest(p) != checksum:
            raise ValueError('Local source provenance changed: '+str(p))
    return value, records


def main():
    import bpy
    from mathutils import Matrix, Vector
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    manifest_path, output = args.manifest.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError('Earlier local diagnostic is preserved: '+str(output))
    if digest(FAST_PATH) != FAST_SHA:
        raise ValueError('Frozen exact native loader changed.')
    manifest_sha = digest(manifest_path)
    manifest, records = checked_manifest(manifest_path)
    result_path = manifest_path.parent/'RESULT.json'
    diagnostic_result = (dict(path=str(result_path), sha256=digest(result_path))
                         if result_path.is_file() else None)
    frame = manifest['frame']
    center = np.asarray(frame['center'], np.float64)
    normal = unit(frame['normal'])
    tangent = unit(np.asarray(frame['tangent'])-normal*np.dot(frame['tangent'], normal))
    across = unit(np.cross(normal, tangent))
    back = unit(normal+.25*across+.15*tangent)
    up = unit(tangent-back*np.dot(tangent, back))
    right = unit(np.cross(up, back))
    up = unit(np.cross(back, right))
    radius = 0.
    for record in records.values():
        xyz, faces = fast.render.load_arrays(record)
        relative = xyz-center
        radius = max(radius, float(np.abs(relative@right).max()),
                     float(np.abs(relative@up).max()))
        del xyz, faces
    if not radius > 0:
        raise ValueError('Actual shared local extent is empty.')
    scale = 2.35*radius
    started = time.perf_counter()
    output.mkdir(parents=True)
    snapshot = output/'source_snapshot'
    snapshot.mkdir()
    snapshots = {}
    for source in (Path(__file__).resolve(), FAST_PATH, fast.PRESERVED):
        target = snapshot/source.name
        shutil.copyfile(source, target)
        snapshots[source.name] = dict(source=str(source), snapshot=str(target), sha256=digest(source))
    shutil.copyfile(manifest_path, snapshot/'INPUT_MANIFEST.json')
    shared = fast.render.scaffold.setup_scene()
    scene, camera = shared.setup_scene(900, 32)
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    lights = []
    for name, offset, energy, size in (
            ('LocalKey', 3*normal-2*across+3*tangent, 130., .9),
            ('LocalFill', 2*normal+3*across+.2*tangent, 35., 1.3),
            ('LocalRim', -normal-2*across+2*tangent, 70., .7)):
        data = bpy.data.lights.new(name, 'AREA')
        data.shape = 'DISK'; data.size = size*scale; data.energy = energy*scale*scale
        obj = bpy.data.objects.new(name, data); scene.collection.objects.link(obj)
        obj.location = center+scale*offset
        obj.rotation_euler = (Vector(center)-obj.location).to_track_quat('-Z','Y').to_euler()
        lights.append(dict(name=name, position=list(obj.location), power=data.energy, size=data.size))
    camera.location = center+4*scale*back
    camera.rotation_mode = 'QUATERNION'
    camera.rotation_quaternion = Matrix((Vector(right), Vector(up), Vector(back))).transposed().to_quaternion()
    camera.data.ortho_scale = scale
    camera.data.clip_start = scale*.001; camera.data.clip_end = scale*100.
    order = [name for name in ('NEUTRAL', 'FORMED', 'CARRIER', 'DELIVERED') if name in records]
    objects = {}
    for name in order:
        expected = records[name]
        obj, counts, loading = fast.add_native_object(Path(expected['geometry']), expected, name, shared)
        obj.hide_render = True
        objects[name] = (obj, counts, loading)
    def actual_conditions(obj):
        if scene.camera != camera or len(obj.data.materials) != 1:
            raise ValueError('Local common camera or material binding changed.')
        mat = obj.data.materials[0]
        if mat != objects['NEUTRAL'][0].data.materials[0]:
            raise ValueError('Exact shared local material instance required.')
        bs = mat.node_tree.nodes.get('Principled BSDF')
        bg = scene.world.node_tree.nodes.get('Background')
        return dict(resolution=[scene.render.resolution_x, scene.render.resolution_y],
            resolution_percentage=scene.render.resolution_percentage,
            samples=scene.cycles.samples, engine=scene.render.engine,
            denoising=scene.cycles.use_denoising, view_transform=scene.view_settings.view_transform,
            camera=dict(position=list(camera.location), target=center.tolist(),
                rotation_quaternion=list(camera.rotation_quaternion), ortho_scale=camera.data.ortho_scale,
                clip_start=camera.data.clip_start, clip_end=camera.data.clip_end,
                right=right.tolist(), up=up.tolist(), back=back.tolist()),
            lights=[dict(name=item['name'], position=list(bpy.data.objects[item['name']].location),
                rotation=list(bpy.data.objects[item['name']].rotation_euler),
                power=bpy.data.lights[item['name']].energy, size=bpy.data.lights[item['name']].size)
                for item in lights],
            material=dict(name=mat.name, base_color=list(bs.inputs['Base Color'].default_value),
                roughness=bs.inputs['Roughness'].default_value),
            world=dict(color=list(bg.inputs[0].default_value), strength=bg.inputs[1].default_value),
            all_flat=True, normal_maps=False, modifiers=[])
    conditions = actual_conditions(objects['NEUTRAL'][0])
    stages = {}
    for name in order:
        obj, counts, loading = objects[name]
        obj.hide_render = False
        before = fast.render.scaffold.geometry_signature(obj, counts, False)
        if actual_conditions(obj) != conditions:
            raise ValueError('Local view conditions differ before rendering: '+name)
        png = output/(name+'.png'); scene.render.filepath = str(png)
        bpy.ops.render.render(write_still=True)
        after = fast.render.scaffold.geometry_signature(obj, counts, False)
        if before != after or len(obj.data.edges) or actual_conditions(obj) != conditions:
            raise ValueError('Actual local geometry or edge-free flags changed during rendering.')
        obj.hide_render = True
        stages[name] = dict(saved_geometry=records[name], geometry_counts=counts,
            display_readback=after, loading=loading, image=dict(path=str(png), sha256=digest(png)),
            conditions=conditions)
        print('LOCAL_DIAGNOSTIC_VIEW_DONE '+name, flush=True)
    if digest(manifest_path) != manifest_sha or checked_manifest(manifest_path) != (manifest, records):
        raise ValueError('Actual local input changed during rendering.')
    if diagnostic_result and digest(result_path) != diagnostic_result['sha256']:
        raise ValueError('Actual local source diagnosis changed during rendering.')
    for record in snapshots.values():
        if digest(record['source']) != record['sha256'] or digest(record['snapshot']) != record['sha256']:
            raise ValueError('Executed local diagnostic source changed.')
    write(output/'RECEIPT.json', dict(kind='ACTUAL_LOCAL_FORMATION_CAUSAL_DIAGNOSTIC',
        input_manifest=dict(path=str(manifest_path), sha256=manifest_sha, value=manifest),
        source_diagnostic_result=diagnostic_result,
        conditions=conditions, stages=stages, source_snapshots=snapshots,
        code_sha256=fast.code_hashes(), local_renderer_sha256=digest(__file__),
        version=bpy.app.version_string, elapsed_seconds=time.perf_counter()-started,
        actual_saved_arrays_only=True, same_camera_material_lights_resolution=True,
        geometry_processing=False, smooth_shading=False, baseline_full_rerendered=False,
        internal_engineering_diagnostic=True, beauty_adoption=False,
        scope='One intrinsic local view of the exact same node interval in neutral, true formed and delivered geometry. '
              'Optional original-carrier patch is a fourth actual state, not a deformation variant. '
              'This different local camera is internal engineering evidence only; it cannot conceal or reverse the failed whole-column close verdict.'))
    print('LOCAL_FORMATION_DIAGNOSTIC_COMPLETE '+str(output), flush=True)


if __name__ == '__main__':
    main()
