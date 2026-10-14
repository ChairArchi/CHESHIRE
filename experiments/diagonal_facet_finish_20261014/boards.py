"""Verify two actual saved body renders under one identical selective-normal mask."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('diagonal_facet_board_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
STATES = ('SOURCE_SELECTIVE', 'ACCENT_SELECTIVE')


def snapshot_source(root):
    source = Path(__file__).resolve()
    relative = Path('experiments') / HERE.name / 'boards.py'
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


def checked_images(path, receipt, binding):
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != 4 or
            {item['view'] for item in records} != set(binding['views'])):
        raise ValueError('Exactly four distinct actual matched images required.')
    images = []
    for item in records:
        view = item['view']
        png = path.parent / (view + '.png')
        render.require_close(receipt['actual_views'][view], binding['actual_reference_views'][view], 'camera.' + view)
        if item['filename'] != png.name or render.digest(png) != item['sha256']:
            raise ValueError('Actual saved PNG changed.')
        with Image.open(png) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Actual 900-square native PNG required.')
            image.verify()
        images.append(dict(view=view, path=str(png), sha256=item['sha256'],
            receipt=str(path), receipt_sha256=render.digest(path), reused_reference=False))
    return images


def verify(root):
    root = Path(root).resolve()
    hashes = render.code_hashes()
    binding = render.source_binding(root)
    if render.read_json(root / 'SOURCE_BINDING.json') != binding:
        raise ValueError('Frozen original source/mask/camera binding differs.')
    candidate_path, candidate_expected, candidate = render.candidate_state(root, binding)
    states, receipts = [], []
    flat_quads, actual_mask = render.mask_state(root)
    if actual_mask != binding['mask']:
        raise ValueError('Actual saved selective mask differs.')
    # Recompute the mapping from the actual source indices to verify all flag hashes.
    flags, expected_mapping = render.selective_flags(render.SOURCE, binding['saved_source'], flat_quads)
    del flags, flat_quads
    for state in STATES:
        path = root / state / 'views/receipt.json'
        receipt = render.read_json(path)
        is_source = state == 'SOURCE_SELECTIVE'
        expected = binding['saved_source'] if is_source else candidate_expected
        geometry = render.SOURCE if is_source else candidate_path
        expected_candidate = None if is_source else candidate
        if (receipt.get('state') != state or receipt.get('source_binding') != binding or
                receipt.get('candidate_binding') != expected_candidate or receipt.get('code_sha256') != hashes or
                receipt.get('saved_geometry') != expected or
                Path(receipt.get('geometry_path', '')).resolve() != geometry.resolve() or
                receipt.get('mask_mapping') != expected_mapping or
                receipt.get('geometry_unchanged_in_renderer') is not True or
                receipt.get('geometry_processing') is not False or receipt.get('geometry_smoothing') is not False or
                receipt.get('selective_normal_interpolation') is not True or
                receipt.get('shading') != 'FLAT_ON_SAVED_QUADS_SMOOTH_ELSEWHERE' or
                receipt.get('modifiers') != [] or receipt.get('normal_maps') is not False or
                receipt.get('remesh') is not False or receipt.get('Boolean_fusion') is not False or
                receipt.get('ornaments_added') is not False or receipt.get('source_growth_generation') != 7 or
                receipt.get('new_source_growth_G8') is not False):
            raise ValueError('Actual source/candidate/selective-mask render provenance differs: ' + state)
        render.verify_snapshot(receipt['render_source_snapshot'])
        render.require_close(receipt['views'], binding['views'], 'declared-cameras.' + state)
        counts = receipt['geometry_counts']
        if (counts['source_arrays'] != {key: expected[key] for key in ('xyz_sha256', 'faces_sha256')} or
                any(counts[key] != expected[key] for key in ('vertices', 'triangles'))):
            raise ValueError('Actual saved native array hashes/counts differ.')
        readback = receipt['display_readback']
        if (readback.get('geometry') != counts['expected_display_arrays'] or
                readback.get('polygons') != expected['triangles'] or
                readback.get('smooth_polygons') != expected_mapping['smooth_polygons'] or
                readback.get('flat_polygons') != expected_mapping['flat_polygons'] or
                readback.get('use_smooth_flags_sha256') != expected_mapping['smooth_flags_sha256'] or
                readback.get('geometry_unchanged') is not True or readback.get('modifiers') != [] or
                readback.get('custom_normal_map') is not False):
            raise ValueError('Actual native coordinates/indices/selective-normal flags differ.')
        render.require_close(receipt['conditions'], dict(binding['reference_conditions'],
            smooth_polygons=expected_mapping['smooth_polygons']))
        if receipt['version'] != binding['reference_Blender_version']:
            raise ValueError('Frozen source/candidate Blender versions differ.')
        states.append(dict(state=state, saved_geometry=expected, images=checked_images(path, receipt, binding),
            display_readback=readback, geometry_counts=counts))
        receipts.append(receipt)
    if (receipts[0]['conditions'] != receipts[1]['conditions'] or
            states[0]['display_readback']['use_smooth_flags_sha256'] != states[1]['display_readback']['use_smooth_flags_sha256'] or
            states[0]['display_readback']['geometry']['triangle_indices_int32_sha256'] !=
            states[1]['display_readback']['geometry']['triangle_indices_int32_sha256']):
        raise ValueError('Actual source/candidate index, selective flags or rendering conditions differ.')
    return dict(passed=True, root=str(root), states=states, source_binding=binding,
        candidate_binding=candidate, shared_mask=actual_mask, actual_native_mapping=expected_mapping,
        source_images=8, new_actual_images=8, comparison_columns=2,
        actual_views=binding['actual_reference_views'], conditions=receipts[0]['conditions'],
        native_triangle_indices_identical=True, actual_polygon_smooth_flags_identical=True,
        coordinates_match_each_actual_saved_body=True, geometry_unchanged_by_renderer=True,
        geometric_success_certified=False, aesthetic_success_certified=False,
        normal_interpolation_is_geometry_improvement=False, modifiers=[], normal_maps=False,
        renderer_geometry_processing=False, crop=False, resize=False,
        source_growth_generation=7, new_source_growth_G8=False, ornaments_added=False,
        render_code_sha256=hashes, boards_code_sha256=render.digest(__file__),
        scope='Two actual saved entire-body meshes at four frozen cameras under the exact same saved selective-flat-quad mask. Every native triangle has exactly one checked original quad-center ID and every original quad has four fan triangles. Actual display coordinates match each saved body; native index and use_smooth flag hashes match before/after. This verifies provenance and equal presentation conditions, not geometric quality, self-intersection freedom or aesthetic success.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier actual comparison preserved.')
    snapshot = snapshot_source(root)
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = ('Source | same selective flat mask', 'Accent | same selective flat mask')
    boards = []
    for view in proof['actual_views']:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), 'SPAN | ' + view + ' | actual saved body + shared selective-normal mask', font=title, fill='black')
        sources = []
        for column, state in enumerate(proof['states']):
            draw.text((column * 900 + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in state['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Actual source PNG changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Actual native image dimensions changed.')
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
    print('DIAGONAL_FACET_MATCHED_RENDER_PASS: 4 source + 4 accent PNGs, identical native indices and selective mask', flush=True)


if __name__ == '__main__':
    main()
