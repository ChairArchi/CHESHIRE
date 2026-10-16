"""Matched flat native-triangle rendering without an unused Blender edge graph.

The native XYZ/triangle arrays, cameras, material, lights and samples are the
same as render.py. Mesh.update is deliberately omitted: Blender 4.5 otherwise
builds all edges even with calc_edges=False when its edge array is empty.
Only immutable, all-flat, unmodified triangle meshes are supported here.
"""
from pathlib import Path
import argparse
import copy
import gc
import importlib.util
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
PRESERVED = HERE / 'render.py'
spec = importlib.util.spec_from_file_location('fast_native_preserved_renderer', PRESERVED)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
digest, write = render.digest, render.write


def code_hashes():
    return dict(fast_renderer=digest(__file__), preserved_matched_renderer=render.code_hashes(),
        mesh_loading='Exact float32/int32 display arrays; no Mesh.update or edge generation; all flat.')


def assign_original_material(obj, shared):
    """Execute the preserved material recipe without its per-polygon loop."""
    import bpy
    template_mesh = bpy.data.meshes.new('Material recipe template; no polygons')
    template = bpy.data.objects.new('Material recipe template; not linked', template_mesh)
    shared.material(template)
    if len(template.data.materials) != 1:
        raise ValueError('Preserved material recipe must produce exactly one material.')
    material = template.data.materials[0]
    obj.data.materials.clear()
    obj.data.materials.append(material)
    bpy.data.objects.remove(template, do_unlink=True)
    bpy.data.meshes.remove(template_mesh)


def set_flat_flags(obj):
    """Set actual flat flags without triggering implicit edge construction."""
    flags = np.zeros(len(obj.data.polygons), dtype=bool)
    obj.data.polygons.foreach_set('use_smooth', flags)
    if len(obj.data.edges):
        raise ValueError('The edge-free native display unexpectedly acquired edges.')


def add_native_object(path, expected, name, shared):
    import bpy
    started = time.perf_counter()
    xyz, faces = render.load_arrays(expected)
    loaded = time.perf_counter()
    nv, nf = len(xyz), len(faces)
    if nv > np.iinfo(np.int32).max or faces.max() > np.iinfo(np.int32).max:
        raise ValueError('Blender display triangle indices exceed signed int32.')
    arrays = dict(xyz_sha256=expected['xyz_sha256'], faces_sha256=expected['faces_sha256'])
    display_xyz, display_faces = np.asarray(xyz, np.float32), np.asarray(faces, np.int32)
    display_hashes = dict(xyz_float32_sha256=render.scaffold.array_hash(display_xyz),
        triangle_indices_int32_sha256=render.scaffold.array_hash(display_faces))
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
    # Do not call Mesh.update: it auto-builds edges if the edge array is empty.
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign_original_material(obj, shared)
    set_flat_flags(obj)
    counts = dict(vertices=nv, triangles=nf, source_arrays=arrays, expected_display_arrays=display_hashes)
    render.scaffold.geometry_signature(obj, counts, False)
    loading = dict(source_load_and_verification_seconds=loaded-started,
        Blender_array_construction_seconds=time.perf_counter()-loaded,
        seconds=time.perf_counter()-started, Blender_edges=len(mesh.edges),
        edge_graph_omitted=True, Mesh_update_called=False, material_recipe_unchanged=True,
        material_recipe_executed_on_zero_polygon_template=True,
        supported_scope='Exact saved all-flat native triangles, no modifiers or smooth normals.')
    return obj, counts, loading


def snapshot(root, name, phase):
    folder = root / 'source_snapshot_render' / name / phase
    if folder.exists():
        raise FileExistsError('Earlier render source snapshots are preserved: ' + str(folder))
    folder.mkdir(parents=True)
    records = {}
    for source in (Path(__file__).resolve(), PRESERVED):
        target = folder / source.name
        shutil.copyfile(source, target)
        record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
        render.verify_snapshot(record)
        records[source.name] = record
    return records


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.ROOT)
    parser.add_argument('--variant', default='DEVELOPED')
    parser.add_argument('--views', nargs='+', choices=render.VIEWS, default=list(render.VIEWS))
    parser.add_argument('--resolution', type=int, default=900)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if len(set(args.views)) != len(args.views) or not 64 <= args.resolution <= 4096:
        parser.error('Unique views and resolution between 64 and 4096 are required.')
    root, name = args.root.resolve(), render.checked_name(args.variant)
    phase = 'review' if args.resolution == 900 else f'preview_{args.resolution}'
    output = root / (name + '_FLAT') / phase
    if output.exists():
        raise FileExistsError('Earlier actual renders are preserved: ' + str(output))
    binding = render.source_binding()
    expected, candidate = render.candidate_state(root, name, binding)
    hashes, snapshots = code_hashes(), snapshot(root, name, phase)
    shared = render.scaffold.setup_scene()
    print('FAST_NATIVE_LOAD ' + name + ': exact arrays, no unused edge graph', flush=True)
    obj, counts, loading = add_native_object(Path(expected['geometry']), expected,
                                              'Actual saved ' + name, shared)
    print('FAST_NATIVE_LOADED ' + str(loading), flush=True)
    scene, camera = shared.setup_scene(args.resolution, 24)
    conditions = render.base.actual_conditions(bpy, scene, camera, obj)
    expected_conditions = copy.deepcopy(binding['conditions'])
    expected_conditions['resolution'] = [args.resolution, args.resolution]
    render.require_close(conditions, expected_conditions)
    if bpy.app.version_string != binding['Blender_version']:
        raise ValueError('Original/candidate Blender versions differ.')
    before = render.scaffold.geometry_signature(obj, counts, False)
    actual_views, images = render.scaffold.render_views(scene, camera,
        {view:binding['views'][view] for view in args.views}, output)
    after = render.scaffold.geometry_signature(obj, counts, False)
    if before != after or len(obj.data.edges):
        raise ValueError('Exact saved triangle display changed or acquired an edge graph.')
    for view in args.views:
        render.require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.' + view)
    if (render.source_binding() != binding or render.candidate_state(root, name, binding) != (expected, candidate) or
            code_hashes() != hashes):
        raise ValueError('Actual sources or executed adapter changed during rendering.')
    for record in snapshots.values():
        render.verify_snapshot(record)
    same_native = all(expected[key] == binding['saved_geometry'][key]
                      for key in ('vertices', 'triangles', 'faces_sha256'))
    result = dict(state=name, phase=phase, saved_geometry=expected, candidate_binding=candidate,
        source_binding=binding, geometry_counts=counts, display_readback=after, conditions=conditions,
        actual_views=actual_views, images=images, geometry_unchanged_by_renderer=True,
        all_flat=True, geometry_processing=False, normal_maps=False, modifiers=[],
        version=bpy.app.version_string, code_sha256=hashes,
        source_snapshot=snapshots['fast_render.py'], source_snapshots=snapshots,
        mesh_loading=loading, resolution_matched_to_source=args.resolution == 900,
        native_connectivity_matched_to_source=same_native,
        diagnostic_display_fan=bool(expected.get('diagnostic_display_fan', False)),
        comparison_scope='Actual saved native XYZ/triangles versus preserved NESTED02 PNGs. '
            'Preserved cameras, material, lights, samples and all-flat flags. '
            'Only Blender\'s unused edge graph is omitted; exact displayed arrays are read back. '
            'Resolution/connectivity matching are recorded separately.')
    write(output / 'receipt.json', result)
    print('FAST_MATCHED_RENDER_DONE ' + name + ': ' + ', '.join(args.views), flush=True)


if __name__ == '__main__':
    main()
