"""One native triangle load, two matched CONTROL/FIELD parent-probe renders.

PROBE_RECEIPT.json binds the full baseline native, its exact control quads,
and sparse float64 control deltas. FIELD native centres are recomputed directly
from updated control corners. The mesh is loaded once; only coordinates change
between renders. Cameras/material/lights/samples/flat flags remain identical.

The shared apply_sparse_control_delta function imports no bpy and can be used
by the probe generator to compute the expected complete native XYZ SHA256.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import shutil
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
FAST_PATH = HERE / 'fast_render.py'
spec = importlib.util.spec_from_file_location('paired_parent_verified_fast_adapter', FAST_PATH)
fast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fast)
render, digest, write = fast.render, fast.digest, fast.write
CHUNK = 65536


def array_hash(value):
    return render.scaffold.array_hash(value)


def apply_sparse_control_delta(native_xyz, control_xyz, quads, ids, delta):
    """Return (complete float64 native XYZ, reconstruction metadata).

    Generator and renderer must call this same function. Every fan centre is
    evaluated as mean(updated_controls[quad]); no interpolated delta shortcut.
    Original native/control arrays are read-only and are never modified.
    """
    native_xyz, control_xyz, quads, ids, delta = map(np.asarray,
        (native_xyz, control_xyz, quads, ids, delta))
    nv, nf = len(control_xyz), len(quads)
    if (native_xyz.dtype != np.dtype('float64') or control_xyz.dtype != np.dtype('float64') or
            control_xyz.shape != (nv, 3) or native_xyz.shape != (nv+nf, 3) or
            quads.shape != (nf, 4) or quads.dtype.kind not in 'iu' or not nv or not nf or
            quads.min() < 0 or quads.max() >= nv or not np.isfinite(native_xyz).all() or
            not np.isfinite(control_xyz).all() or not np.array_equal(native_xyz[:nv], control_xyz)):
        raise ValueError('Exact finite float64 control prefix and matching arithmetic fan layout required.')
    if (ids.ndim != 1 or ids.dtype != np.dtype('int64') or delta.shape != (len(ids), 3) or
            delta.dtype != np.dtype('float64') or not np.isfinite(delta).all() or
            (len(ids) and (ids.min() < 0 or ids.max() >= nv)) or len(np.unique(ids)) != len(ids)):
        raise ValueError('Unique in-range int64 IDs and finite float64 sparse Nx3 deltas required.')
    result = native_xyz.copy()
    result[ids] += delta
    original_fan_exact = True
    for start in range(0, nf, CHUNK):
        stop = min(start+CHUNK, nf)
        block = quads[start:stop]
        if not np.array_equal(native_xyz[nv+start:nv+stop], control_xyz[block].mean(axis=1)):
            original_fan_exact = False
            break
        result[nv+start:nv+stop] = result[block].mean(axis=1)
    if not original_fan_exact:
        raise ValueError('Baseline native centres are not exact original control-corner means.')
    if not np.isfinite(result).all():
        raise ValueError('Sparse control addition produced nonfinite native coordinates.')
    metadata = dict(implementation='FLOAT64_SPARSE_CONTROL_ADDITION_THEN_DIRECT_ALL_FAN_MEANS_V1',
        control_vertices=nv, fan_centres=nf, sparse_ids=len(ids),
        nonzero_sparse_deltas=int(np.count_nonzero(np.linalg.norm(delta, axis=1))),
        baseline_control_prefix_exact=True, baseline_original_fan_centres_exact=True,
        all_fan_centres_recomputed=True, interpolated_fan_delta_used=False,
        source_arrays_modified=False, complete_native_xyz_sha256=array_hash(result))
    return result, metadata


def code_hashes():
    return dict(parent_probe_renderer=digest(__file__), verified_fast_helpers=fast.code_hashes())


def file_binding(receipt, key, root, fallback_sha=None):
    item = receipt[key]
    if isinstance(item, dict):
        path = item.get('path', item.get('geometry'))
        checksum = item.get('sha256', item.get('geometry_sha256', fallback_sha))
    else:
        path = item
        checksum = receipt.get(key + '_sha256', fallback_sha)
    if not path or not checksum:
        raise ValueError('Path/SHA256 binding required: ' + key)
    path = Path(path)
    path = path.resolve() if path.is_absolute() else (root/path).resolve()
    return path, checksum


def verify_native_fan_faces(faces, quads, nv):
    if faces.shape != (4*len(quads), 3):
        raise ValueError('Stored native triangles do not match the exact control fan count.')
    for start in range(0, len(quads), CHUNK):
        stop = min(start+CHUNK, len(quads))
        block = faces[4*start:4*stop].reshape(-1, 4, 3)
        q = quads[start:stop]
        if (not np.array_equal(block[:, :, 0], q) or
                not np.array_equal(block[:, :, 1], np.roll(q, -1, axis=1)) or
                not np.array_equal(block[:, :, 2],
                    np.broadcast_to((nv+np.arange(start, stop))[:, None], q.shape))):
            raise ValueError('Stored native triangle order differs from the exact quad-centre fan.')


def add_arrays_once(xyz, faces, expected, shared):
    """Construct the already-verified native display once, without edge graph."""
    import bpy
    nv, nf = len(xyz), len(faces)
    if nv > np.iinfo(np.int32).max or faces.max() > np.iinfo(np.int32).max:
        raise ValueError('Blender triangle indexing exceeds signed int32.')
    display_xyz, display_faces = np.asarray(xyz, np.float32), np.asarray(faces, np.int32)
    hashes = dict(xyz_float32_sha256=array_hash(display_xyz),
                  triangle_indices_int32_sha256=array_hash(display_faces))
    mesh = bpy.data.meshes.new('Actual matched parent probe; reused native triangles')
    mesh.vertices.add(nv)
    mesh.vertices.foreach_set('co', display_xyz.ravel())
    del display_xyz
    mesh.loops.add(3*nf)
    mesh.loops.foreach_set('vertex_index', display_faces.ravel())
    del display_faces
    mesh.polygons.add(nf)
    mesh.polygons.foreach_set('loop_start', np.arange(0, 3*nf, 3, dtype=np.int32))
    mesh.polygons.foreach_set('loop_total', np.full(nf, 3, dtype=np.int32))
    obj = bpy.data.objects.new('Actual matched parent probe', mesh)
    bpy.context.collection.objects.link(obj)
    fast.assign_original_material(obj, shared)
    fast.set_flat_flags(obj)
    counts = dict(vertices=nv, triangles=nf,
        source_arrays={key:expected[key] for key in ('xyz_sha256', 'faces_sha256')},
        expected_display_arrays=hashes)
    render.scaffold.geometry_signature(obj, counts, False)
    return obj, counts


def set_saved_coordinates(obj, xyz, xyz_sha256, baseline_counts):
    """Update coordinates only; RNA invalidates normals without Mesh.update."""
    import bpy
    if xyz.shape != (baseline_counts['vertices'], 3) or array_hash(xyz) != xyz_sha256:
        raise ValueError('Complete reconstructed native coordinates differ from the probe receipt.')
    display = np.asarray(xyz, np.float32)
    counts = copy.deepcopy(baseline_counts)
    counts['source_arrays']['xyz_sha256'] = xyz_sha256
    counts['expected_display_arrays']['xyz_float32_sha256'] = array_hash(display)
    obj.data.vertices.foreach_set('co', display.ravel())
    del display
    bpy.context.view_layer.update()
    if len(obj.data.edges):
        raise ValueError('Coordinate update unexpectedly created an unused edge graph.')
    render.scaffold.geometry_signature(obj, counts, False)
    return counts


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--views', nargs='+', choices=render.VIEWS, default=['close_oblique'])
    parser.add_argument('--resolution', type=int, default=900)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if len(set(args.views)) != len(args.views) or not 64 <= args.resolution <= 4096:
        parser.error('Unique preserved views and resolution between64and4096 required.')
    root = args.root.resolve()
    phase = 'review' if args.resolution == 900 else f'preview_{args.resolution}'
    receipt_path = root/'PROBE_RECEIPT.json'
    receipt, receipt_sha = render.read_json(receipt_path), digest(receipt_path)
    if set(receipt.get('variants', {})) != {'CONTROL', 'FIELD'}:
        raise ValueError('Exactly CONTROL and FIELD probe records are required.')
    if receipt['variants']['CONTROL'].get('kind') != 'BASELINE' or receipt['variants']['FIELD'].get('kind') != 'CONTROL_DELTA':
        raise ValueError('CONTROL must be BASELINE and FIELD must be CONTROL_DELTA.')
    pair_path = root/'PAIR_RECEIPT.json'
    snapshot_folder = root/'source_snapshot_render'/'parent_probe'/phase
    if pair_path.exists() or snapshot_folder.exists() or any((root/(name+'_FLAT')/phase).exists() for name in ('CONTROL','FIELD')):
        raise FileExistsError('Earlier probe pair, renders or snapshots are preserved.')
    if receipt.get('reconstruction_code_sha256', digest(__file__)) != digest(__file__):
        raise ValueError('Generator and renderer reconstruction source hashes differ.')
    for record in receipt.get('source_snapshots', {}).values():
        render.verify_snapshot(record)
    binding = render.source_binding()
    expected = copy.deepcopy(receipt['baseline_record'])
    native_path, native_sha = file_binding(receipt, 'baseline_native', root, expected['geometry_sha256'])
    control_path, control_sha = file_binding(receipt, 'baseline_control_quad', root)
    if native_sha != expected['geometry_sha256']:
        raise ValueError('Baseline native binding differs from its complete array record.')
    expected['geometry'] = str(native_path)
    if digest(control_path) != control_sha:
        raise ValueError('Exact baseline control quad file changed.')
    field = receipt['variants']['FIELD']
    delta_path = Path(field['control_delta'])
    delta_path = delta_path.resolve() if delta_path.is_absolute() else (root/delta_path).resolve()
    delta_sha = field['control_delta_sha256']
    if digest(delta_path) != delta_sha:
        raise ValueError('Receipt-bound sparse control delta changed.')
    hashes = code_hashes()
    started = time.perf_counter()
    print('PARENT_PROBE_LOAD one actual complete native array set', flush=True)
    native_xyz, native_faces = render.load_arrays(expected)
    with np.load(control_path, allow_pickle=False) as saved:
        control_xyz, quads = saved['xyz'], saved['faces']
    verify_native_fan_faces(native_faces, quads, len(control_xyz))
    with np.load(delta_path, allow_pickle=False) as saved:
        ids, delta, stored_nv = saved['ids'], saved['delta'], saved['control_vertices']
    if (np.asarray(stored_nv).shape != () or np.asarray(stored_nv).dtype.kind not in 'iu' or
            int(stored_nv) != len(control_xyz)):
        raise ValueError('Sparse delta control count differs from the exact native control prefix.')
    field_xyz, reconstruction = apply_sparse_control_delta(native_xyz, control_xyz, quads, ids, delta)
    if reconstruction['complete_native_xyz_sha256'] != field['xyz_sha256']:
        raise ValueError('Full reconstructed float64 FIELD XYZ hash differs from the generator receipt.')
    del control_xyz, quads, ids, delta
    snapshot_folder.mkdir(parents=True)
    snapshots = {}
    for source in (Path(__file__).resolve(), FAST_PATH, fast.PRESERVED):
        target = snapshot_folder/source.name
        shutil.copyfile(source, target)
        record = dict(source=str(source), snapshot=str(target), sha256=digest(source))
        render.verify_snapshot(record)
        snapshots[source.name] = record
    shutil.copyfile(receipt_path, snapshot_folder/'SOURCE_PROBE_RECEIPT.json')
    shared = render.scaffold.setup_scene()
    obj, baseline_counts = add_arrays_once(native_xyz, native_faces, expected, shared)
    del native_faces
    scene, camera = shared.setup_scene(args.resolution, 24)
    preparation_seconds = time.perf_counter()-started
    results = {}
    for name in ('CONTROL','FIELD'):
        counts = (baseline_counts if name == 'CONTROL' else
            set_saved_coordinates(obj, field_xyz, field['xyz_sha256'], baseline_counts))
        declared_xyz_sha = expected['xyz_sha256'] if name == 'CONTROL' else field['xyz_sha256']
        conditions = render.base.actual_conditions(bpy, scene, camera, obj)
        expected_conditions = copy.deepcopy(binding['conditions'])
        expected_conditions['resolution'] = [args.resolution,args.resolution]
        render.require_close(conditions, expected_conditions)
        if bpy.app.version_string != binding['Blender_version']:
            raise ValueError('Actual preserved and probe Blender versions differ.')
        before = render.scaffold.geometry_signature(obj, counts, False)
        print('PARENT_PROBE_RENDER '+name+'; same actual object/native triangles and preserved camera',flush=True)
        output = root/(name+'_FLAT')/phase
        actual_views, images = render.scaffold.render_views(scene,camera,
            {view:binding['views'][view] for view in args.views},output)
        after = render.scaffold.geometry_signature(obj,counts,False)
        if before != after or len(obj.data.edges):
            raise ValueError('Probe coordinates/connectivity/flat flags changed during rendering.')
        for view in args.views:
            render.require_close(actual_views[view],binding['actual_views'][view],'matched-camera.'+view)
        result = dict(state=name,phase=phase,probe_receipt=dict(path=str(receipt_path),sha256=receipt_sha),
            baseline_native=expected,coordinate_source=receipt['variants'][name],
            actual_native_xyz_sha256=declared_xyz_sha,actual_native_faces_sha256=expected['faces_sha256'],
            geometry_counts=counts,display_readback=after,conditions=conditions,actual_views=actual_views,images=images,
            geometry_unchanged_during_render=True,native_faces_unchanged=True,all_flat=True,
            modifiers=[],normal_maps=False,mesh_edges=0,shared_native_object=True,
            source_binding=binding,version=bpy.app.version_string,code_sha256=hashes,
            source_snapshot=snapshots['render_parent_probe.py'],source_snapshots=snapshots,
            reconstruction=(None if name=='CONTROL' else reconstruction),
            geometry_scope=('Complete stored native source' if name=='CONTROL' else
                'Complete native source reconstructed from exact sparse control additions and direct updated-corner fan means; not a stored FIELD native export.'),
            resolution_matched_to_source=args.resolution==900)
        write(output/'receipt.json',result)
        results[name]=dict(receipt=str(output/'receipt.json'),receipt_sha256=digest(output/'receipt.json'),
                           images={item['view']:str(output/item['filename']) for item in images},
                           actual_native_xyz_sha256=declared_xyz_sha,display_readback=after,
                           actual_views=actual_views,conditions=conditions)
    render.require_close(results['CONTROL']['actual_views'],results['FIELD']['actual_views'])
    render.require_close(results['CONTROL']['conditions'],results['FIELD']['conditions'])
    if (digest(receipt_path)!=receipt_sha or digest(native_path)!=native_sha or
            digest(control_path)!=control_sha or digest(delta_path)!=delta_sha or
            code_hashes()!=hashes or render.source_binding()!=binding):
        raise ValueError('Probe files, original source or executed code changed during the matched pair.')
    for record in snapshots.values():
        render.verify_snapshot(record)
    write(pair_path,dict(kind='ACTUAL_PARENT_CONTROL_DELTA_MATCHED_NATIVE_PAIR',
        probe_receipt=dict(path=str(receipt_path),sha256=receipt_sha),baseline_native=expected,
        baseline_control_quad=dict(path=str(control_path),sha256=control_sha),
        control_delta=dict(path=str(delta_path),sha256=delta_sha),reconstruction=reconstruction,
        variants=results,views=args.views,source_binding=binding,all_flat=True,
        modifiers=[],normal_maps=False,native_triangles_loaded_once=True,shared_native_object=True,
        saved_native_faces_unchanged=True,mesh_edges=0,preparation_seconds=preparation_seconds,
        version=bpy.app.version_string,executed_code_sha256=hashes,source_snapshots=snapshots,
        scope='Two actual complete native CONTROL/FIELD meshes at identical preserved cameras/material/lights/'
            '24samples/flat flags. FIELD is exact coordinate reconstruction from the saved sparse delta, '
            'not resampling, smoothing or added geometry. This diagnostic pair is separate from fast_render receipts.'))
    print('ACTUAL_PARENT_PROBE_PAIR_DONE '+str(root),flush=True)


if __name__=='__main__':
    main()
