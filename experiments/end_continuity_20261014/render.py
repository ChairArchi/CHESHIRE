"""Fast saved-mesh comparison: context views first, detail views only after selection."""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial01')
FROZEN = HERE.parent/'flow_fold_finish_20261014/render.py'
FROZEN_SHA = '991f51a0f86c75f7e150e1c70c064782e2a83b4ede064d504c5136d2348f4588'
BASE = Path('E:/CHESHIRE_DATA/experiments/flow_fold_finish_20261014/trial03')
BASE_RECEIPT_SHA = '8c16e50324097ba6612e7a5e7ceb671ceb217e65dc3fd1f97d3af3f2aa7eb57f'
BASE_RENDER_SHA = 'c025feb18942c2e21b52bcf0927bd869de684bd85f4caba10defb5281d1484b8'
BASE_GEOMETRY_SHA = '5bbd72fca4e4789dd6df1bfa947f38db72ad014c6c4afaf47733cff05aea9c1e'
spec = importlib.util.spec_from_file_location('end_continuity_frozen_native', FROZEN)
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)
scaffold, base = frozen.scaffold, frozen.base
digest, read_json, require_close = frozen.digest, frozen.read_json, frozen.require_close
array_hash = frozen.array_hash


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def code_hashes():
    if digest(FROZEN) != FROZEN_SHA:
        raise ValueError('Frozen actual renderer changed.')
    return dict(renderer=digest(__file__), frozen_renderer_sha256=FROZEN_SHA,
                frozen_renderer_code=frozen.code_hashes())


def source_binding():
    receipt_path, render_path = BASE/'RECEIPT.json', BASE/'FLOW_FLAT/views/receipt.json'
    if digest(receipt_path) != BASE_RECEIPT_SHA or digest(render_path) != BASE_RENDER_SHA:
        raise ValueError('Actual current FLOW03 receipts changed.')
    expected = read_json(receipt_path)['variants']['FLOW']
    geometry = Path(expected['geometry'])
    if digest(geometry) != BASE_GEOMETRY_SHA or expected['geometry_sha256'] != BASE_GEOMETRY_SHA:
        raise ValueError('Actual current FLOW03 source changed.')
    r = read_json(render_path)
    candidate = dict(receipt=str(receipt_path), receipt_sha256=BASE_RECEIPT_SHA, variant=expected)
    if (r['candidate_binding'] != candidate or r['saved_geometry'] != expected or
            r['code_sha256'] != frozen.code_hashes() or r['state'] != 'FLOW_FLAT' or
            r['geometry_processing'] is not False or r['geometry_unchanged_in_renderer'] is not True or
            r['smooth_shading'] is not False or r['modifiers'] != [] or r['normal_maps'] is not False):
        raise ValueError('Actual current FLOW03 all-flat render provenance differs.')
    frozen.verify_snapshot(r['render_source_snapshot'])
    frozen.previous.display_proof(r, expected)
    require_close(r['conditions'], base.expected_conditions())
    camera_binding = dict(views=r['views'], actual_reference_views=r['actual_views'])
    images = frozen.previous.image_records(r, render_path, camera_binding, True)
    return dict(source_native_path=str(geometry), source_native_geometry_sha256=BASE_GEOMETRY_SHA,
        source_receipt=str(receipt_path), source_receipt_sha256=BASE_RECEIPT_SHA,
        source_render_receipt=str(render_path), source_render_receipt_sha256=BASE_RENDER_SHA,
        saved_geometry=expected, views=r['views'], actual_views=r['actual_views'],
        conditions=r['conditions'], Blender_version=r['version'], images=images)


def variants(root, binding):
    path = root/'RECEIPT.json'
    receipt = read_json(path)
    if (Path(receipt['source_native_path']).resolve() != Path(binding['source_native_path']).resolve() or
            receipt['source_native_geometry_sha256'] != binding['source_native_geometry_sha256']):
        raise ValueError('Candidate receipt must bind to actual latest FLOW03 baseline.')
    result = receipt['variants']
    if not 1 <= len(result) <= 2:
        raise ValueError('One or two focused saved candidates only.')
    for name, expected in result.items():
        if (not name.replace('_', '').isalnum() or
                digest(expected['geometry']) != expected['geometry_sha256'] or
                any(expected[key] != binding['saved_geometry'][key] for key in ('faces_sha256','vertices','triangles'))):
            raise ValueError('Candidate saved geometry or shared native connectivity differs.')
        if expected.get('stored_generation_json'):
            generation = Path(expected['stored_generation_json'])
            if digest(generation) != expected['stored_generation_json_sha256']:
                raise ValueError('Actual preserved generation record changed.')
            g = read_json(generation)
            if (g['geometry_file_sha256'] != expected['geometry_sha256'] or
                    g['checks']['native_xyz_sha256'] != expected['xyz_sha256'] or
                    g['checks']['native_faces_sha256'] != expected['faces_sha256'] or
                    g['native_vertices'] != expected['vertices'] or g['native_triangles'] != expected['triangles']):
                raise ValueError('Actual stored generation/file/array binding differs.')
    return result, dict(receipt=str(path), receipt_sha256=digest(path))


def snapshot(root):
    source = Path(__file__).resolve()
    target = root/'source_snapshot_render'/source.name
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Earlier renderer snapshot preserved.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return dict(source=str(source), snapshot=str(target), sha256=checksum)


def update_coordinates(obj, expected, shared_counts):
    """Keep the original Blender face buffer; update only actual saved XYZ."""
    import numpy as np
    with np.load(expected['geometry'], allow_pickle=False) as saved:
        xyz = saved['xyz']
    if array_hash(xyz) != expected['xyz_sha256'] or xyz.shape != (expected['vertices'], 3):
        raise ValueError('Actual saved candidate XYZ differs.')
    display = np.ascontiguousarray(xyz, dtype=np.float32)
    obj.data.vertices.foreach_set('co', display.ravel())
    obj.data.update()
    counts = copy.deepcopy(shared_counts)
    counts['source_arrays']['xyz_sha256'] = expected['xyz_sha256']
    counts['expected_display_arrays']['xyz_float32_sha256'] = array_hash(display.ravel())
    return counts


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--phase', choices=('context', 'detail'), default='context')
    parser.add_argument('--variant', action='append')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    binding = source_binding()
    candidates, candidate_receipt = variants(root, binding)
    chosen = args.variant or list(candidates)
    if any(name not in candidates for name in chosen) or (args.phase == 'detail' and len(chosen) != 1):
        raise ValueError('Only one selected candidate may receive detail views.')
    hashes, snap = code_hashes(), snapshot(root)
    views = ('close_oblique', 'body_oblique') if args.phase == 'context' else ('front', 'macro')
    shared = scaffold.setup_scene()
    obj, shared_counts = scaffold.add_native_object(Path(candidates[chosen[0]]['geometry']), candidates[chosen[0]], 'Actual saved focused candidate', shared)
    scaffold.set_smooth_flags(obj, False)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, binding['conditions'])
    if bpy.app.version_string != binding['Blender_version']:
        raise ValueError('Actual source/candidate Blender version differs.')
    for index, name in enumerate(chosen):
        expected = candidates[name]
        counts = shared_counts if index == 0 else update_coordinates(obj, expected, shared_counts)
        output = root/(name+'_FLAT')/args.phase
        if output.exists():
            raise FileExistsError('Actual earlier candidate views preserved.')
        before = scaffold.geometry_signature(obj, counts, False)
        actual_views, images = scaffold.render_views(scene, camera, {v:binding['views'][v] for v in views}, output)
        after = scaffold.geometry_signature(obj, counts, False)
        if before != after:
            raise ValueError('Actual native coordinates/indices/all-flat flags changed while rendering.')
        for view in views:
            require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.'+view)
        if variants(root, binding) != (candidates, candidate_receipt) or code_hashes() != hashes or any(digest(snap[k]) != snap['sha256'] for k in ('source','snapshot')):
            raise ValueError('Actual saved source/candidate/code changed during render.')
        write(output/'receipt.json', dict(state=name, phase=args.phase, saved_geometry=expected,
            candidate_binding=candidate_receipt, source_binding=binding, geometry_counts=counts,
            display_readback=after, conditions=conditions, actual_views=actual_views, images=images,
            geometry_unchanged_by_renderer=True, all_flat=True, geometry_processing=False,
            normal_maps=False, modifiers=[], version=bpy.app.version_string, code_sha256=hashes,
            source_snapshot=snap, reused_Blender_face_buffer=index>0,
            native_face_binding_scope='First candidate native faces loaded and read back. Following candidates reuse those unchanged Blender indices; identical saved index hashes are bound by generator receipt/file hashes.',
            comparison_scope='Current FLOW03 versus stored candidate. Whole replay differs in carrier and lacks later FLOW finish; this is an overall source-coherence diagnostic, not an isolated surface-finish or end-only comparison.'))
        print('END_CONTEXT_RENDERED', name, args.phase, len(images), flush=True)
    print('END_CONTINUITY_PHASE_DONE', args.phase, flush=True)


if __name__ == '__main__':
    main()
