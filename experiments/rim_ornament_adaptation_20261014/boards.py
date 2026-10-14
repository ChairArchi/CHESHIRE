"""Verify and compose four-column native original/rim-ornament comparisons."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rim_ornament_boards_renderer', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
CHECKER = HERE.parent / 'whole_column_detail_20261013/surface_boards.py'
CHECKER_SHA256 = 'b2276f3fbda604637f90a6f4dec7cc71528687c92ec8dcd7dfe3cea6bb5ea6f0'
spec = importlib.util.spec_from_file_location('rim_ornament_frozen_image_checks', CHECKER)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def check_receipt(receipt, binding, parent_info, parent_source, original_receipt):
    if (receipt.get('binding') != binding or receipt.get('original_body') != parent_source or
            receipt.get('code_sha256') != render.code_hashes() or
            receipt.get('original_body_loaded_once') is not True or
            receipt.get('original_body_unchanged_in_blender') is not True or
            receipt.get('body_geometry_processing') is not False or
            receipt.get('added_geometry_processing') is not False or
            receipt.get('fusion_performed') is not False or
            receipt.get('new_source_growth_G8') is not False or
            receipt.get('source_growth_generation') != 7 or receipt.get('modifiers') != [] or
            receipt.get('smooth_shading') is not False):
        raise ValueError('Actual immutable body / renderer provenance mismatch.')
    render.verify_snapshots(receipt.get('render_source_snapshots'))
    if receipt['original_body_counts']['source_arrays'] != {
            key + '_sha256': parent_info['checks']['native_' + key + '_sha256'] for key in ('xyz', 'faces')}:
        raise ValueError('Original native body arrays do not match actual saved source.')
    if receipt['original_body_display_readback'] != receipt['original_body_counts']['expected_display_arrays']:
        raise ValueError('Actual original body readback mismatch.')
    if (receipt['version'] != original_receipt['version'] or
            receipt['conditions'] != original_receipt['conditions']):
        raise ValueError('Actual original / variant Blender, material or light conditions differ.')
    render.require_close(receipt['conditions'], render.base.expected_conditions())


def checked_pngs(path, receipt, expected_views):
    records = receipt.get('images')
    if (not isinstance(records, list) or len(records) != len(expected_views) or
            {item['view'] for item in records} != set(expected_views)):
        raise ValueError('Exactly the declared distinct actual PNGs required.')
    images = []
    for item in records:
        view = item['view']
        render.require_close(receipt['actual_views'][view], expected_views[view], 'matched-camera.' + view)
        png = path.parent / (view + '.png')
        if item['filename'] != png.name or render.digest(png) != item['sha256']:
            raise ValueError('Actual PNG changed.')
        with Image.open(png) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Actual 900-square native PNG required.')
            image.verify()
        images.append(dict(path=str(png), **item, receipt=str(path),
            receipt_sha256=render.digest(path), reused_reference=False))
    return images


def verify(root):
    if render.digest(CHECKER) != CHECKER_SHA256:
        raise ValueError('Preserved original source-image checker changed.')
    root = Path(root).resolve()
    info, placement, parent_info, parent_source, binding = render.source_state(root)
    original_images, original_receipt, original_views = checks.checked_images(parent_info,
        parent_source, render.SOURCE / 'views/receipt.json', render.prior.code_hashes())
    for item in original_images:
        item['reused_reference'] = True
    declared_views = render.all_views(placement)
    macro_path = root / 'ORIGINAL_G7/views/receipt.json'
    macro_receipt = render.read_json(macro_path)
    check_receipt(macro_receipt, binding, parent_info, parent_source, original_receipt)
    if (macro_receipt.get('candidate') != 'ORIGINAL_G7' or
            macro_receipt.get('saved_placement') != placement or
            macro_receipt.get('kind') != 'ORIGINAL_G7_REAL_MACRO_REFERENCE'):
        raise ValueError('Actual original body-only macro receipt required.')
    from math import sqrt
    position, target, scale = declared_views['macro']
    difference = [b - a for a, b in zip(position, target)]
    length = sqrt(sum(v * v for v in difference))
    expected_macro = dict(position=list(position), target=list(target), scale=scale,
        forward=[v / length for v in difference])
    render.require_close(macro_receipt['views'], {'macro': declared_views['macro']}, 'declared-original-macro')
    original_images += checked_pngs(macro_path, macro_receipt, {'macro': expected_macro})
    original_views = {**original_views, 'macro': macro_receipt['actual_views']['macro']}
    states = [dict(candidate='ORIGINAL_G7', source=parent_source, images=original_images,
        original_body_display_readback=macro_receipt['original_body_display_readback'])]
    for name in render.VARIANTS:
        path = root / name / 'views/receipt.json'
        receipt = render.read_json(path)
        check_receipt(receipt, binding, parent_info, parent_source, original_receipt)
        expected = info['variants'][name]
        if (receipt.get('candidate') != name or receipt.get('saved_variant') != expected or
                receipt.get('saved_placement') != placement or
                receipt.get('added_geometry_sha256') != expected['geometry_sha256']):
            raise ValueError('Actual saved variant or placement provenance mismatch: ' + name)
        if receipt['added_geometry_counts']['source_arrays'] != {
                key: expected[key] for key in ('xyz_sha256', 'faces_sha256')}:
            raise ValueError('Actual saved added geometry array mismatch.')
        render.require_close(receipt['views'], declared_views, 'declared-cameras.' + name)
        images = checked_pngs(path, receipt, original_views)
        states.append(dict(candidate=name, source=expected, images=images,
            render_source_snapshots=receipt['render_source_snapshots'],
            original_body_display_readback=receipt['original_body_display_readback']))
    if any(state['original_body_display_readback'] != states[0]['original_body_display_readback'] for state in states[1:]):
        raise ValueError('The three variants did not retain the same actual original body.')
    return dict(passed=True, root=str(root), states=states, binding=binding,
        saved_placement=placement, reused_original_images=3, new_original_macro_images=1,
        new_actual_variant_images=12, source_images=16, comparison_columns=4,
        conditions=original_receipt['conditions'], actual_views=original_views,
        Blender_version=original_receipt['version'], source_growth_generation=7,
        new_source_growth_G8=False, fusion_performed=False, original_body_unchanged=True,
        renderer_geometry_processing=False, crop=False, resize=False,
        image_checker_sha256=CHECKER_SHA256, render_code_sha256=render.code_hashes(),
        scope='Three preserved original G7 native PNGs, one actual new body-only macro PNG, and three actual rim-addition variants at four matched cameras. Material, light, sampling and flat native shading are matched. The source body was loaded once and retained unchanged; candidate additions are separate saved meshes. Footprints may differ; occupied volume is not matched. No Boolean union or new source subdivision generation. Attachment aesthetics and intersection freedom are not certified by source/image verification.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Earlier matched comparison preserved.')
    output.mkdir()
    title = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 27)
    label = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 23)
    labels = ('Original G7', 'Mandel ribbon', 'Leaf fan', 'Hybrid')
    boards = []
    for view in proof['actual_views']:
        canvas = Image.new('RGB', (3600, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), 'SPAN | ' + view + ' | original body + adapted rim ornament', font=title, fill='black')
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
    proof.update(boards=boards, comparison_boards=4, boards_script_sha256=render.digest(__file__))
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
    print('RIM_ORNAMENT_MATCHED_RENDER_PASS: 3 reused + 1 actual original macro + 12 actual candidate PNGs', flush=True)


if __name__ == '__main__':
    main()
