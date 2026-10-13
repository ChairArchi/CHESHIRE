"""Matched original, actual 3D Mandelbulb addition, and controlled leaf addition."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_ornament_boards_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
CHECKER = HERE.parent / 'whole_column_detail_20261013/surface_boards.py'
CHECKER_SHA256 = 'b2276f3fbda604637f90a6f4dec7cc71528687c92ec8dcd7dfe3cea6bb5ea6f0'
spec = importlib.util.spec_from_file_location('local_ornament_frozen_image_checks', CHECKER)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def verify(root):
    if render.digest(CHECKER) != CHECKER_SHA256:
        raise ValueError('Preserved original source-image checker changed.')
    root = Path(root).resolve()
    info, placement, parent_info, parent_source, binding = render.source_state(root)
    original_images, original_receipt, original_views = checks.checked_images(parent_info,
        parent_source, render.SOURCE / 'views/receipt.json', render.prior.code_hashes())
    for item in original_images:
        item['reused_reference'] = True
    states = [dict(candidate='ORIGINAL_G7', source=parent_source, images=original_images)]
    for name in render.VARIANTS:
        path = root / name / 'views/receipt.json'
        receipt = render.read_json(path)
        if (receipt.get('candidate') != name or receipt.get('binding') != binding or
                receipt.get('saved_variant') != info['variants'][name] or
                receipt.get('saved_placement') != placement or
                receipt.get('original_body') != parent_source or
                receipt.get('code_sha256') != render.code_hashes() or
                receipt.get('added_geometry_sha256') != info['variants'][name]['geometry_sha256'] or
                receipt.get('original_body_loaded_once') is not True or
                receipt.get('original_body_unchanged_in_blender') is not True or
                receipt.get('body_geometry_processing') is not False or
                receipt.get('added_geometry_processing') is not False or
                receipt.get('fusion_performed') is not False or
                receipt.get('new_source_growth_G8') is not False or
                receipt.get('source_growth_generation') != 7 or receipt.get('modifiers') != [] or
                receipt.get('smooth_shading') is not False):
            raise ValueError('Actual source/variant/placement/renderer provenance mismatch: ' + name)
        render.verify_snapshots(receipt.get('render_source_snapshots'))
        if receipt['original_body_counts']['source_arrays'] != {
                key + '_sha256': parent_info['checks']['native_' + key + '_sha256'] for key in ('xyz', 'faces')}:
            raise ValueError('Original native body arrays do not match actual saved source.')
        if receipt['original_body_display_readback'] != receipt['original_body_counts']['expected_display_arrays']:
            raise ValueError('Actual original body readback mismatch.')
        expected = info['variants'][name]
        if receipt['added_geometry_counts']['source_arrays'] != {
                key: expected[key] for key in ('xyz_sha256', 'faces_sha256')}:
            raise ValueError('Actual saved added geometry array mismatch.')
        if (receipt['version'] != original_receipt['version'] or
                receipt['conditions'] != original_receipt['conditions']):
            raise ValueError('Actual original/variant Blender, material or light conditions differ.')
        render.require_close(receipt['conditions'], render.base.expected_conditions())
        records = receipt.get('images')
        if not isinstance(records, list) or len(records) != 3 or {item['view'] for item in records} != set(render.VIEWS):
            raise ValueError('Exactly three distinct actual variant PNGs required.')
        images = []
        for item in records:
            view = item['view']
            render.require_close(receipt['actual_views'][view], original_views[view], 'matched-camera.' + name + '.' + view)
            if receipt['views'][view] != json.loads(json.dumps(render.VIEWS[view])):
                raise ValueError('Declared camera differs.')
            image_path = path.parent / (view + '.png')
            if item['filename'] != image_path.name or render.digest(image_path) != item['sha256']:
                raise ValueError('Actual variant PNG changed.')
            with Image.open(image_path) as image:
                if image.size != (900, 900) or image.format != 'PNG':
                    raise ValueError('Actual 900-square native PNG required.')
                image.verify()
            images.append(dict(path=str(image_path), **item, receipt=str(path),
                receipt_sha256=render.digest(path), reused_reference=False))
        states.append(dict(candidate=name, source=expected, images=images,
            render_source_snapshots=receipt['render_source_snapshots'],
            original_body_display_readback=receipt['original_body_display_readback']))
    if states[1]['original_body_display_readback'] != states[2]['original_body_display_readback']:
        raise ValueError('The two variants did not retain the same actual original body.')
    return dict(passed=True, root=str(root), states=states, binding=binding,
        saved_placement=placement, reused_original_images=3, new_actual_variant_images=6,
        source_images=9, comparison_columns=3, conditions=original_receipt['conditions'],
        actual_views=original_views, Blender_version=original_receipt['version'],
        source_growth_generation=7, new_source_growth_G8=False, fusion_performed=False,
        original_body_unchanged=True, renderer_geometry_processing=False, crop=False, resize=False,
        image_checker_sha256=CHECKER_SHA256, render_code_sha256=render.code_hashes(),
        scope='Original saved G7 native PNGs and two actual local-added-geometry variants with identical cameras, material, lights, sampling and flat native shading. Original body is immutable and was loaded once for both candidate renders; additions are separate baked meshes, not a union or new source subdivision generation. Attachment, component aesthetics and intersection freedom are not certified by source/image verification.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier matched comparison preserved.')
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = ('Original G7', '3D Mandelbulb', 'Controlled leaf cluster')
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (2700, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), 'SPAN | ' + view + ' | original body + local ornament comparison', font=title, fill='black')
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
            sources.append(dict(candidate=state['candidate'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    proof.update(boards=boards, comparison_boards=3, boards_script_sha256=render.digest(__file__))
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
    print('LOCAL_ORNAMENT_MATCHED_RENDER_PASS: 3 original + 6 new saved native PNGs', flush=True)


if __name__ == '__main__':
    main()
