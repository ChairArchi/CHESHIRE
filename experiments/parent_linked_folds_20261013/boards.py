"""Compare the actual saved MIDDLE_SURFACE G7 and PARENT_LINKED G7."""
from pathlib import Path
import argparse
import importlib.util
import json
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('parent_linked_boards_render', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
SHARED_BOARDS = HERE.parent / 'whole_column_detail_20261013/surface_boards.py'
spec = importlib.util.spec_from_file_location('parent_linked_frozen_image_checks', SHARED_BOARDS)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def verify(root):
    root = Path(root).resolve()
    folder, info, source = render.source_state(root)
    parent_info, parent_source = render.parent_state()
    old_images, old_receipt, old_views = checks.checked_images(parent_info, parent_source,
        render.PARENT / 'views/receipt.json', render.surface.code_hashes())
    images, receipt, views = checks.checked_images(info, source, folder / 'views/receipt.json', render.code_hashes())
    if (old_receipt.get('source_generation') != 6 or old_receipt.get('added_CC_passes') != 1 or
        receipt.get('source_generation') != 7 or receipt.get('added_CC_passes') != 0 or
        receipt.get('added_normal_field_passes') != 2):
        raise ValueError('Actual G7-to-G7 correspondence with two field passes and zero added CC passes required.')
    if receipt['version'] != old_receipt['version'] or receipt['conditions'] != old_receipt['conditions']:
        raise ValueError('Actual Blender version or material/scene conditions differ.')
    for view in render.VIEWS:
        render.require_close(views[view], old_views[view], 'matched-camera.' + view)
    for image in old_images:
        image['reused_reference'] = True
    for image in images:
        image['reused_reference'] = False
    return dict(passed=True, root=str(root), source_generation=7, subdivision_generation=7,
        added_CC_passes=0, added_normal_field_passes=2,
        states=[dict(candidate='MIDDLE_SURFACE', subdivision_generation=7, source=parent_source, images=old_images),
                dict(candidate='PARENT_LINKED', subdivision_generation=7, source=source, images=images)],
        reused_parent_images=3, new_images=3, source_images=6, conditions=receipt['conditions'],
        actual_views=views, Blender_version=receipt['version'], crop=False, resize=False,
        image_check_script_sha256=render.digest(SHARED_BOARDS),
        scope='Only preserved MIDDLE_SURFACE G7 and new saved PARENT_LINKED G7; saved code/native-array/image receipts and matched camera/material checks; no other trial replay or geometry/aesthetic certification.')


def compose(proof):
    root = Path(proof['root'])
    output = root / 'images'
    if output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Fresh verified parent-linked comparison output required.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    labels = ('MIDDLE SURFACE · 실제 G7', 'PARENT LINKED · 형상장 2회 누적 · 실제 G7')
    view_labels = dict(front='전체 정면', body_oblique='본체 사선', close_oblique='근접 사선')
    boards = []
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN · {view_labels[view]} · 부모 접힘 연계 변형 · 실제 G7 / 추가 CC 0회', font=title, fill='black')
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
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    proof = verify(args.root)
    if not args.verify_only:
        compose(proof)
    print('PARENT_LINKED_RENDER_VERIFICATION_PASS: 3 reused G7 originals + 3 new G7 originals', flush=True)


if __name__ == '__main__':
    main()
