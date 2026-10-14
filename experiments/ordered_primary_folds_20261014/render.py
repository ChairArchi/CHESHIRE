"""Render the actual ordered-primary G7 column against the latest NESTED.

Existing baseline PNGs are reused. Only the saved new geometry is loaded;
the renderer performs no geometry processing or shading correction.
"""
from pathlib import Path
import argparse
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/experiments/ordered_primary_folds_20261014/trial01')
PRESERVED = HERE.parent/'parent_nested_folds_20261014/render.py'
PRESERVED_SHA = '2f7777d71643cd179e8d6a33e7c729f915b1e7830aba84b29777f10675423f36'
BASE = Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02')
BASE_RECEIPT_SHA = 'ab212bf9222980a25cb6d0c5ca31aa82ad0fe5f48b64864d9ed8e8d5fbb02524'
BASE_RENDER_SHA = 'd0bbb3d1cfafb14d92660dd1e003cab19a69dfca20e42722c9ec0ccb773cf508'
BASE_GEOMETRY_SHA = 'cde95d13f64d86739ac25e134e67024533d6be4fafec7a5d4c7a46896b65403e'
VIEWS = ('close_oblique', 'body_oblique', 'front')
spec = importlib.util.spec_from_file_location('ordered_primary_preserved_renderer', PRESERVED)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
scaffold, base = previous.scaffold, previous.base
digest, read_json, require_close = previous.digest, previous.read_json, previous.require_close
write, verify_snapshot = previous.write, previous.verify_snapshot


def code_hashes():
    if digest(PRESERVED) != PRESERVED_SHA:
        raise ValueError('Preserved actual parent-nested renderer changed.')
    return dict(renderer=digest(__file__), preserved_renderer_sha256=PRESERVED_SHA,
                preserved_renderer_code=previous.code_hashes())


def source_binding():
    receipt_path = BASE/'RECEIPT.json'
    render_path = BASE/'NESTED_FLAT/review/receipt.json'
    if digest(receipt_path) != BASE_RECEIPT_SHA or digest(render_path) != BASE_RENDER_SHA:
        raise ValueError('Latest NESTED actual receipts changed.')
    receipt = read_json(receipt_path)
    expected = receipt['variants']['NESTED']
    geometry = Path(expected['geometry'])
    if digest(geometry) != BASE_GEOMETRY_SHA or expected['geometry_sha256'] != BASE_GEOMETRY_SHA:
        raise ValueError('Latest NESTED actual saved source changed.')
    r = read_json(render_path)
    if (r['saved_geometry'] != expected or
            r['candidate_binding'] != dict(receipt=str(receipt_path), receipt_sha256=BASE_RECEIPT_SHA) or
            r['code_sha256'] != previous.code_hashes() or r['state'] != 'NESTED' or
            r['phase'] != 'review' or r['geometry_unchanged_by_renderer'] is not True or
            r['all_flat'] is not True or r['geometry_processing'] is not False or
            r['normal_maps'] is not False or r['modifiers'] != []):
        raise ValueError('Latest NESTED all-flat render provenance differs.')
    verify_snapshot(r['source_snapshot'])
    for record in receipt['source_snapshots'].values():
        verify_snapshot(record)
    previous.previous.frozen.previous.display_proof(r, expected)
    require_close(r['conditions'], base.expected_conditions())
    if (set(r['actual_views']) != set(VIEWS) or len(r['images']) != len(VIEWS) or
            {item['view'] for item in r['images']} != set(VIEWS)):
        raise ValueError('Latest actual close/body/front source images required.')
    images = []
    for item in r['images']:
        view = item['view']
        image = render_path.parent/(view+'.png')
        if item['filename'] != image.name or digest(image) != item['sha256']:
            raise ValueError('Latest NESTED actual source image changed.')
        scaffold.verify_native_png(image)
        require_close(r['actual_views'][view], r['source_binding']['actual_views'][view],
                      'actual-source-camera.'+view)
        images.append(dict(view=view, path=str(image), sha256=item['sha256'],
                           reused_reference=True, receipt=str(render_path),
                           receipt_sha256=BASE_RENDER_SHA))
    return dict(state='CURRENT_NESTED', source_native_path=str(geometry),
        source_native_geometry_sha256=BASE_GEOMETRY_SHA,
        source_receipt=str(receipt_path), source_receipt_sha256=BASE_RECEIPT_SHA,
        source_render_receipt=str(render_path), source_render_receipt_sha256=BASE_RENDER_SHA,
        saved_geometry=expected, views={v:r['source_binding']['views'][v] for v in VIEWS},
        actual_views=r['actual_views'], conditions=r['conditions'], Blender_version=r['version'],
        geometry_counts=r['geometry_counts'], display_readback=r['display_readback'], images=images)


def candidate_state(root, binding):
    receipt_path = root/'RECEIPT.json'
    receipt = read_json(receipt_path)
    if (Path(receipt.get('comparison_source_native_path', '')).resolve() !=
            Path(binding['source_native_path']).resolve() or
            receipt.get('comparison_source_native_geometry_sha256') !=
            binding['source_native_geometry_sha256']):
        raise ValueError('Candidate must bind to the latest actual NESTED source.')
    variants = receipt.get('variants')
    if not isinstance(variants, dict) or set(variants) != {'ORDERED'}:
        raise ValueError('Exactly one saved ORDERED candidate required.')
    expected = variants['ORDERED']
    geometry = root/'ORDERED/geometry.npz'
    if (Path(expected.get('geometry', '')).resolve() != geometry.resolve() or
            digest(geometry) != expected.get('geometry_sha256') or
            any(expected.get(key) != binding['saved_geometry'][key]
                for key in ('faces_sha256', 'vertices', 'triangles'))):
        raise ValueError('Saved candidate or shared native connectivity differs.')
    snapshots = receipt.get('source_snapshots')
    if not isinstance(snapshots, dict) or not snapshots:
        raise ValueError('Executed generator source snapshots required.')
    for record in snapshots.values():
        verify_snapshot(record)
    return expected, dict(receipt=str(receipt_path), receipt_sha256=digest(receipt_path))


def snapshot(root):
    source = Path(__file__).resolve()
    target = root/'source_snapshot_render/experiments'/HERE.name/source.name
    checksum = digest(source)
    if target.exists():
        if digest(target) != checksum:
            raise ValueError('Earlier renderer snapshot preserved.')
    else:
        import shutil
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    root = args.root.resolve()
    output = root/'ORDERED_FLAT/review'
    if output.exists():
        raise FileExistsError('Earlier actual candidate render preserved.')
    binding = source_binding()
    expected, candidate = candidate_state(root, binding)
    hashes, snap = code_hashes(), snapshot(root)
    shared = scaffold.setup_scene()
    obj, counts = scaffold.add_native_object(Path(expected['geometry']), expected,
                                             'Actual saved ordered-primary column', shared)
    scaffold.set_smooth_flags(obj, False)
    scene, camera = shared.setup_scene(900, 24)
    conditions = base.actual_conditions(bpy, scene, camera, obj)
    require_close(conditions, binding['conditions'])
    if bpy.app.version_string != binding['Blender_version']:
        raise ValueError('Actual source/candidate Blender version differs.')
    before = scaffold.geometry_signature(obj, counts, False)
    actual_views, images = scaffold.render_views(scene, camera, binding['views'], output)
    after = scaffold.geometry_signature(obj, counts, False)
    if before != after:
        raise ValueError('Actual saved mesh or all-flat flags changed during rendering.')
    for view in VIEWS:
        require_close(actual_views[view], binding['actual_views'][view], 'matched-camera.'+view)
    if (source_binding() != binding or candidate_state(root, binding) != (expected, candidate) or
            code_hashes() != hashes):
        raise ValueError('Actual source/candidate/code changed during rendering.')
    verify_snapshot(snap)
    result = dict(state='ORDERED', phase='review', saved_geometry=expected, candidate_binding=candidate,
        source_binding=binding, geometry_counts=counts, display_readback=after, conditions=conditions,
        actual_views=actual_views, images=images, geometry_unchanged_by_renderer=True, all_flat=True,
        geometry_processing=False, normal_maps=False, modifiers=[], version=bpy.app.version_string,
        code_sha256=hashes, source_snapshot=snap,
        comparison_scope='Latest actual NESTED versus ordered-primary G7 design. Existing source PNGs are reused; the saved candidate alone is loaded and rendered. Same cameras, material, lights, resolution, samples, native faces/counts and all-flat shading. No geometry processing or normal-map detail is performed by the renderer.')
    previous.previous.frozen.previous.display_proof(result, expected)
    write(output/'receipt.json', result)
    print('ORDERED_PRIMARY_RENDER_DONE: three actual close/body/front PNGs; saved mesh and all-flat readbacks verified', flush=True)


if __name__ == '__main__':
    main()
