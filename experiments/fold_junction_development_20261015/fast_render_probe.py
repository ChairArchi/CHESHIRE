"""Small actual Blender pixel/normal equivalence check for edge-free loading."""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_edge_free_probe', HERE / 'fast_render.py')
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)
render = fast.render


def fixture():
    rings, sectors = 17, 48
    xyz = []
    for row, z in enumerate(np.linspace(.15, 9.88, rings)):
        for angle in np.linspace(0., 2 * np.pi, sectors, endpoint=False):
            radius = .8 + .12 * np.cos(3 * angle) * np.sin(np.pi * row / (rings-1))
            xyz.append([radius*np.cos(angle), radius*np.sin(angle), z + .045*np.sin(5*angle)])
    xyz += [[0., 0., .15], [0., 0., 9.88]]
    faces = []
    for row in range(rings-1):
        for sector in range(sectors):
            a, b = row*sectors+sector, row*sectors+(sector+1) % sectors
            faces += [[a, b, b+sectors], [a, b+sectors, a+sectors]]
    for sector in range(sectors):
        nxt = (sector+1) % sectors
        faces += [[rings*sectors, nxt, sector],
                  [rings*sectors+1, (rings-1)*sectors+sector, (rings-1)*sectors+nxt]]
    return np.array(xyz, np.float64), np.array(faces, np.int64)


def face_normals(obj):
    array = np.empty((len(obj.data.polygons), 3), np.float32)
    obj.data.polygons.foreach_get('normal', array.ravel())
    return array


def image_pixels(path):
    import bpy
    image = bpy.data.images.load(str(path), check_existing=False)
    values = np.empty(len(image.pixels), np.float32)
    image.pixels.foreach_get(values)
    bpy.data.images.remove(image)
    return values


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resolution', type=int, default=128)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Earlier equivalence output is preserved.')
    output.mkdir(parents=True)
    xyz, faces = fixture()
    path = output / 'fixture.npz'
    np.savez_compressed(path, xyz=xyz, faces=faces)
    expected = dict(geometry=str(path), geometry_sha256=render.digest(path),
        xyz_sha256=render.scaffold.array_hash(xyz), faces_sha256=render.scaffold.array_hash(faces),
        vertices=len(xyz), triangles=len(faces))
    binding = render.source_binding()
    results = {}
    normals, pixels = {}, {}
    hashes = dict(probe=render.digest(__file__), fast_renderer=fast.code_hashes())
    for mode in ('preserved_edges', 'edge_free'):
        shared = render.scaffold.setup_scene()
        started = time.perf_counter()
        if mode == 'preserved_edges':
            obj, counts = render.scaffold.add_native_object(path, expected, 'Actual native verification', shared)
            render.scaffold.set_smooth_flags(obj, False)
            loading = dict(seconds=time.perf_counter()-started, Blender_edges=len(obj.data.edges))
        else:
            obj, counts, loading = fast.add_native_object(path, expected, 'Actual native verification', shared)
        before = render.scaffold.geometry_signature(obj, counts, False)
        normals[mode] = face_normals(obj)
        scene, camera = shared.setup_scene(args.resolution, 24)
        conditions = render.base.actual_conditions(bpy, scene, camera, obj)
        expected_conditions = copy.deepcopy(binding['conditions'])
        expected_conditions['resolution'] = [args.resolution, args.resolution]
        render.require_close(conditions, expected_conditions)
        views, images = render.scaffold.render_views(scene, camera, {'front':binding['views']['front']}, output/mode)
        after = render.scaffold.geometry_signature(obj, counts, False)
        if before != after or not np.array_equal(normals[mode], face_normals(obj)):
            raise ValueError('Source arrays/flags/normals changed during the small render.')
        pixels[mode] = image_pixels(output/mode/'front.png')
        results[mode] = dict(loading=loading, Blender_edges_after_render=len(obj.data.edges),
            geometry_signature=after, face_normals_sha256=render.scaffold.array_hash(normals[mode]),
            pixel_sha256=render.scaffold.array_hash(pixels[mode]), conditions=conditions,
            actual_views=views, images=images)
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        del obj, mesh
        gc.collect()
    a, b = results['preserved_edges'], results['edge_free']
    exact = (a['geometry_signature'] == b['geometry_signature'] and
        np.array_equal(normals['preserved_edges'], normals['edge_free']) and
        np.array_equal(pixels['preserved_edges'], pixels['edge_free']) and
        a['images'][0]['sha256'] == b['images'][0]['sha256'] and
        a['Blender_edges_after_render'] > 0 and b['Blender_edges_after_render'] == 0)
    render.require_close(a['conditions'], b['conditions'])
    render.require_close(a['actual_views'], b['actual_views'])
    if hashes != dict(probe=render.digest(__file__), fast_renderer=fast.code_hashes()):
        raise ValueError('Executed small-pair verification source changed.')
    result = dict(kind='ACTUAL_BLENDER_EDGE_FREE_NATIVE_EQUIVALENCE', passed=exact,
        Blender_version=bpy.app.version_string, fixture=expected,
        original_native_arrays_and_all_flat_flags_exact=True,
        face_normals_bit_identical=np.array_equal(normals['preserved_edges'], normals['edge_free']),
        rendered_pixels_bit_identical=np.array_equal(pixels['preserved_edges'], pixels['edge_free']),
        PNG_files_byte_identical=a['images'][0]['sha256'] == b['images'][0]['sha256'],
        no_edge_graph_after_edge_free_render=b['Blender_edges_after_render'] == 0,
        results=results, executed_code_sha256=hashes,
        scope='Small synthetic closed corrugated column, same preserved front camera, original material/'
            'lights, 24 samples and flat shading; test resolution explicitly reduced. No actual design was rendered.')
    render.write(output/'EQUIVALENCE_RECEIPT.json', result)
    print('EDGE_FREE_EQUIVALENCE ' + str(exact) + ' ' + str(output), flush=True)
    if not exact:
        raise ValueError('Edge-free native loading failed the actual small-pair equivalence test.')


if __name__ == '__main__':
    main()
