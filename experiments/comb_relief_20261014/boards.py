"""Verify and compose saved source/fine-comb relief under equal all-flat shading."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('comb_relief_board_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / source.name
    target = Path(root) / 'source_snapshot_boards' / relative
    checksum = render.digest(source)
    if target.exists():
        if render.digest(target) != checksum:
            raise ValueError('Earlier boards source snapshot differs.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    record = dict(source=str(source), relative_path=relative.as_posix(), snapshot=str(target), sha256=checksum)
    verify_snapshot(record)
    return record


def verify_snapshot(record):
    if (record.get('sha256') != render.digest(__file__) or
            any(render.digest(record[key]) != record['sha256'] for key in ('source', 'snapshot'))):
        raise ValueError('Actual boards source/snapshot changed.')


def verify(root):
    root = Path(root).resolve()
    hashes = render.code_hashes()
    binding, source_flat, geometry, expected, candidate = render.saved_state(root)
    path = root / 'RELIEF_FLAT/views/receipt.json'
    receipt = render.read_json(path)
    if (receipt.get('state') != 'RELIEF_FLAT' or receipt.get('source_binding') != binding or
            receipt.get('candidate_binding') != candidate or receipt.get('source_flat_reference') != source_flat or
            receipt.get('saved_geometry') != expected or
            Path(receipt.get('geometry_path', '')).resolve() != geometry.resolve() or
            receipt.get('code_sha256') != hashes or receipt.get('geometry_unchanged_in_renderer') is not True or
            receipt.get('geometry_processing') is not False or receipt.get('geometry_smoothing') is not False or
            receipt.get('shading') != 'ALL_FLAT_NATIVE_TRIANGLES' or receipt.get('smooth_shading') is not False or
            receipt.get('smooth_polygons') != 0 or receipt.get('normal_maps') is not False or
            receipt.get('modifiers') != [] or receipt.get('remesh') is not False or
            receipt.get('Boolean_fusion') is not False or receipt.get('ornaments_added') is not False or
            receipt.get('selective_mask_dependency') is not False or
            receipt.get('source_growth_generation') != 7 or receipt.get('new_source_growth_G8') is not False):
        raise ValueError('Actual saved relief/body/source/flat-render provenance differs.')
    render.verify_snapshot(receipt['render_source_snapshot'])
    counts, readback = receipt['geometry_counts'], receipt['display_readback']
    if (counts['source_arrays'] != {key: expected[key] for key in ('xyz_sha256', 'faces_sha256')} or
            any(counts[key] != expected[key] for key in ('vertices', 'triangles')) or
            readback.get('geometry') != counts['expected_display_arrays'] or
            readback.get('smooth_polygons') != 0 or readback.get('all_use_smooth') is not False or
            readback.get('geometry_unchanged') is not True or readback.get('modifiers') != [] or
            readback.get('use_smooth_flags_sha256') != render.array_hash(np.zeros(expected['triangles'], bool))):
        raise ValueError('Actual saved coordinates/native indices/all-flat flags differ.')
    additions = dict(added_native_vertices=expected['vertices'] - binding['saved_source']['vertices'],
        added_native_triangles=expected['triangles'] - binding['saved_source']['triangles'])
    if (any(receipt.get(key) != value for key, value in additions.items()) or
            receipt.get('source_native_vertices') != binding['saved_source']['vertices'] or
            receipt.get('source_native_triangles') != binding['saved_source']['triangles'] or
            receipt.get('native_topology_changed') != (expected['faces_sha256'] != binding['saved_source']['faces_sha256']) or
            receipt.get('generator_validation_evidence') != expected.get('validation')):
        raise ValueError('Actual native-count changes or hash-bound generator evidence differ.')
    render.require_close(receipt['conditions'], source_flat['conditions'])
    render.require_close(receipt['conditions'], render.base.expected_conditions())
    render.require_close(receipt['views'], binding['views'])
    if receipt['version'] != source_flat['Blender_version']:
        raise ValueError('Source/candidate Blender versions differ.')
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != 4 or
            {item['view'] for item in records} != set(binding['views'])):
        raise ValueError('Four actual relief all-flat PNGs required.')
    images = []
    for item in records:
        view = item['view']
        png = path.parent / (view + '.png')
        if item['filename'] != png.name or render.digest(png) != item['sha256']:
            raise ValueError('Actual relief all-flat PNG changed.')
        render.require_close(receipt['actual_views'][view], source_flat['actual_views'][view], 'matched-camera.' + view)
        with Image.open(png) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Actual 900-square native PNG required.')
            image.verify()
        images.append(dict(view=view, path=str(png), sha256=item['sha256'], reused_reference=False,
            receipt=str(path), receipt_sha256=render.digest(path)))
    return dict(passed=True, root=str(root), states=[source_flat,
        dict(state='RELIEF_FLAT', saved_geometry=expected, images=images, display_readback=readback, geometry_counts=counts)],
        source_binding=binding, candidate_binding=candidate, source_images=8,
        reused_source_flat_images=4, new_relief_flat_images=4, comparison_columns=2,
        conditions=receipt['conditions'], actual_views=source_flat['actual_views'],
        native_triangle_indices_identical=(expected['faces_sha256'] == binding['saved_source']['faces_sha256']),
        native_indices_match_each_actual_saved_body=True, actual_all_flat_normal_flags_verified_per_body=True,
        actual_all_flat_flag_hashes_identical=(readback['use_smooth_flags_sha256'] == source_flat['display_readback']['use_smooth_flags_sha256']),
        native_count_changes=additions, generator_validation_evidence=expected.get('validation'),
        generator_validation_scope='Carried from the hash-bound generator receipt; not re-executed or independently certified by this image verification.',
        coordinates_match_each_actual_saved_body=True, geometry_unchanged_by_renderer=True,
        selective_mask_dependency=False, geometric_success_certified=False, aesthetic_success_certified=False,
        crop=False, resize=False, modifiers=[], normal_maps=False, renderer_geometry_processing=False,
        source_growth_generation=7, new_source_growth_G8=False, ornaments_added=False,
        render_code_sha256=hashes, boards_code_sha256=render.digest(__file__),
        scope='Two actual saved entire-body meshes at four matched cameras under identical all-flat native shading. Source images are actual reused originals; candidate images are actual saved-mesh renders. Candidate native topology/counts may differ. Native coordinate/index readbacks match each body\'s own saved arrays; all use_smooth flags are independently verified false for each body. Generator control/boundary evidence is carried separately under the candidate receipt hash. No selective-mask dependency or render geometry operation. This verifies provenance and equal comparison conditions, not geometric/aesthetic success or self-intersection freedom.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier actual comparison preserved.')
    snapshot = snapshot_source(root)
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = ('Source | all-flat native shading', 'Fine comb relief | all-flat native shading')
    boards = []
    for view in proof['actual_views']:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), 'SPAN | ' + view + ' | actual saved source / fine comb relief', font=title, fill='black')
        sources = []
        for column, state in enumerate(proof['states']):
            draw.text((column * 900 + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in state['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Actual source PNG changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Actual source dimensions changed.')
                canvas.paste(image.convert('RGB'), (column * 900, 105))
            sources.append(dict(state=state['state'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    verify_snapshot(snapshot)
    proof.update(boards=boards, comparison_boards=4, boards_source_snapshot=snapshot)
    for path in (output / 'SOURCE_LIST.json', root / 'RENDER_VERIFICATION.json'):
        path.write_text(json.dumps(proof, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.DEFAULT_ROOT)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    proof = verify(args.root)
    if not args.verify_only:
        compose(proof)
    print('COMB_RELIEF_MATCHED_RENDER_PASS: 4 reused source + 4 actual RELIEF PNGs, each body saved arrays/all-flat flags verified', flush=True)


if __name__ == '__main__':
    main()
