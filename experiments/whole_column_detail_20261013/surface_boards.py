"""Compare a selected saved whole-column G6 with its one-pass neutral CC G7 finish."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('whole_column_surface_boards_render', HERE / 'surface_render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def checked_images(info, source, receipt_path, hashes):
    receipt = render.read_json(receipt_path)
    if (receipt.get('candidate') != info['candidate'] or receipt.get('input_case') != 'SPAN' or
        receipt.get('subdivision_generation') != info['subdivision_generation'] or receipt.get('code_sha256') != hashes or
        any(receipt.get(key) != value for key, value in source.items())):
        raise ValueError('Saved source/render-code receipt differs: ' + str(receipt_path))
    render.require_close(receipt['conditions'], render.raw.base.expected_conditions())
    if any(receipt['source_arrays'][key + '_sha256'] != info['checks']['native_' + key + '_sha256'] for key in ('xyz', 'faces')):
        raise ValueError('Rendered native-array hash differs from saved generation.')
    records = {item['view']: item for item in receipt['images']}
    if len(records) != len(receipt['images']) or set(records) != set(render.VIEWS):
        raise ValueError('Three distinct matching source images required.')
    images, actual = [], {}
    for view, (position, target, scale) in render.VIEWS.items():
        direction = [t - p for p, t in zip(position, target)]
        length = math.sqrt(sum(x*x for x in direction))
        expected = dict(position=list(position), target=list(target), scale=scale, forward=[x / length for x in direction])
        render.require_close(receipt['actual_views'][view], expected, 'camera.' + view)
        if receipt['views'][view] != json.loads(json.dumps(render.VIEWS[view])):
            raise ValueError('Declared camera differs.')
        path = receipt_path.parent / (view + '.png')
        checksum = render.digest(path)
        if records[view]['filename'] != path.name or records[view]['sha256'] != checksum:
            raise ValueError('Original PNG changed: ' + str(path))
        with Image.open(path) as image:
            if image.size != (900, 900) or image.format != 'PNG':
                raise ValueError('Original 900 by 900 PNG required.')
            image.verify()
        actual[view] = receipt['actual_views'][view]
        images.append(dict(view=view, path=str(path), sha256=checksum,
            receipt=str(receipt_path), receipt_sha256=render.digest(receipt_path)))
    return images, receipt, actual


def verify(root, stage):
    root = Path(root).resolve()
    folder, info, source, (parent_folder, parent_info, parent_source) = render.source_state(root, stage)
    old_images, old_receipt, old_views = checked_images(parent_info, parent_source, parent_folder / 'views/receipt.json', render.raw.code_hashes())
    images, receipt, views = checked_images(info, source, folder / 'views/receipt.json', render.code_hashes())
    if (old_receipt.get('source_generation') != 6 or old_receipt.get('added_CC_passes') != 0 or
        receipt.get('source_generation') != 6 or receipt.get('added_CC_passes') != 1 or
        receipt.get('neutral_passes') != 1 or receipt.get('added_normal_field_passes') != 0):
        raise ValueError('Actual G6-to-G7 one-pass neutral CC correspondence required.')
    if receipt['version'] != old_receipt['version'] or receipt['conditions'] != old_receipt['conditions']:
        raise ValueError('Actual Blender version or material/scene conditions differ.')
    for view in render.VIEWS:
        render.require_close(views[view], old_views[view], 'matched-camera.' + view)
    for image in old_images:
        image['reused_reference'] = True
    for image in images:
        image['reused_reference'] = False
    return dict(passed=True, root=str(root), stage=stage, output_root=str(root / 'SURFACE' / stage),
        source_generation=6, subdivision_generation=7, added_CC_passes=1, neutral_passes=1, added_normal_field_passes=0,
        states=[dict(candidate=stage, subdivision_generation=6, source=parent_source, images=old_images),
                dict(candidate=stage + '_SURFACE', subdivision_generation=7, source=source, images=images)],
        reused_parent_images=3, new_images=3, source_images=6, conditions=receipt['conditions'],
        actual_views=views, Blender_version=receipt['version'], crop=False, resize=False,
        scope='Only selected saved G6 and its one-pass neutral-CC G7; saved code/native-array/image receipts and matched camera/material checks; no other trial replay or geometry/aesthetic certification.')


def compose(proof):
    root = Path(proof['output_root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Fresh verified finish comparison output required.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    stage = proof['stage']
    labels = (f'{stage} · 실제 G6', f'{stage} SURFACE · 중립 CC 1회 적용 · 실제 G7')
    view_labels = dict(front='전체 정면', body_oblique='본체 사선', close_oblique='근접 사선')
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN · {view_labels[view]} · G6 → G7 표면 정리 · 추가 형상장 없음', font=title, fill='black')
        sources = []
        for column, current in enumerate(proof['states']):
            draw.text((900*column + 24, 61), labels[column], font=label, fill='black')
            item = next(image for image in current['images'] if image['view'] == view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Original changed during composition.')
            with Image.open(item['path']) as image:
                if image.size != (900, 900):
                    raise ValueError('Original dimensions changed.')
                canvas.paste(image.convert('RGB'), (900*column, 105))
            sources.append(dict(candidate=current['candidate'], **item))
        path = output / ('SPAN_' + view + '.png')
        canvas.save(path)
        boards.append(dict(view=view, output=str(path), sha256=render.digest(path), sources=sources))
    proof.update(boards=boards, comparison_boards=3, boards_script_sha256=render.digest(__file__))
    for path in (output / 'SOURCE_LIST.json', root / 'RENDER_VERIFICATION.json'):
        path.write_text(json.dumps(proof, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--stage', choices=render.STAGES, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    proof = verify(args.root, args.stage)
    if not args.verify_only:
        compose(proof)
    print('SURFACE_RENDER_VERIFICATION_PASS:', args.stage, '3 reused G6 originals + 3 new G7 originals', flush=True)


if __name__ == '__main__':
    main()
