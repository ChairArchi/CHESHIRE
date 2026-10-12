"""Compare actual G6 parent/design: one old front plus five fresh original PNGs."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('design_one_boards_render', HERE / 'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def checked_images(info, source, receipt_path, views, hashes, exact_views=True):
    receipt = render.read_json(receipt_path)
    if (receipt.get('candidate') != info['candidate'] or receipt.get('input_case') != 'SPAN' or
        receipt.get('subdivision_generation') != 6 or receipt.get('code_sha256') != hashes or
        any(receipt.get(key) != value for key, value in source.items())):
        raise ValueError('Saved source/render-code receipt differs: ' + str(receipt_path))
    render.require_close(receipt['conditions'], render.base.expected_conditions())
    if any(receipt['source_arrays'][key + '_sha256'] != info['checks']['native_' + key + '_sha256'] for key in ('xyz', 'faces')):
        raise ValueError('Rendered native-array hash differs from saved generation.')
    records = {item['view']: item for item in receipt['images']}
    if len(records) != len(receipt['images']) or (exact_views and set(records) != set(views)):
        raise ValueError('Distinct matching source images required.')
    images, actual = [], {}
    for view, (position, target, scale) in views.items():
        direction = [t - p for p, t in zip(position, target)]
        length = math.sqrt(sum(x*x for x in direction))
        expected = dict(position=list(position), target=list(target), scale=scale, forward=[x / length for x in direction])
        render.require_close(receipt['actual_views'][view], expected, 'camera.' + view)
        if receipt['views'][view] != json.loads(json.dumps(views[view])):
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


def verify(root):
    root = Path(root).resolve()
    hashes = render.code_hashes()
    folder, info, source = render.source_state(root)
    if info['added_CC_passes'] != 0:
        raise ValueError('Topology design events must not be labeled as G7.')
    new_images, rn, new_views = checked_images(info, source, folder / 'views/receipt.json', render.VIEWS, hashes)
    if rn.get('added_CC_passes') != 0 or rn.get('source_generation') != 6:
        raise ValueError('Design receipt must declare actual G6 plus zero CC passes.')
    parent_info, parent_source = render.parent_state()
    old_hashes = dict(render=render.PARENT_RENDER_SHA256, frozen_renderer=render.FROZEN_SHA256,
        broad_camera_recipe=hashes['broad_camera_recipe'], shared_material_scene_recipe=hashes['shared_material_scene_recipe'])
    front, rf, front_view = checked_images(parent_info, parent_source, render.PARENT / 'views/receipt.json',
        {'front': render.VIEWS['front']}, old_hashes, exact_views=False)
    bodies, rb, body_views = checked_images(parent_info, parent_source, root / 'reference_views/receipt.json',
        {k: v for k, v in render.VIEWS.items() if k != 'front'}, hashes)
    for receipt in (rf, rb):
        if receipt['version'] != rn['version'] or receipt['conditions'] != rn['conditions']:
            raise ValueError('Actual Blender version or material/scene conditions differ.')
    if dict(**front_view, **body_views) != new_views:
        raise ValueError('Actual parent/design cameras differ.')
    for key, value in (('parent_control_sha256', parent_source['control_sha256']),
                       ('parent_geometry_sha256', parent_source['source_sha256']),
                       ('parent_generation_sha256', parent_source['generation_sha256'])):
        if source[key] != value:
            raise ValueError('Reference images must depict the actual design parent.')
    for image in front:
        image['reused_reference'] = True
    for image in bodies + new_images:
        image['reused_reference'] = False
    return dict(passed=True, new_root=str(root), states=[
        dict(candidate='DEPTH_08', source=parent_source, images=front + bodies),
        dict(candidate='DESIGN_A', source=source, images=new_images)],
        subdivision_generation=6, design_added_CC_passes=0, reused_parent_images=1,
        new_parent_body_images=2, new_design_images=3, new_images=5, source_images=6,
        conditions=rn['conditions'], actual_views=new_views, Blender_version=rn['version'], crop=False, resize=False,
        scope='Saved geometry/code/native-array receipts, same actual camera/material conditions and PNG hashes; no full lineage or geometry/aesthetic certification.')


def compose(root, proof):
    root = Path(root).resolve()
    output = root / 'images'
    if str(root) != proof['new_root'] or output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Fresh verified comparison root required.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    boards = []
    labels = ('PARENT · DEPTH_08 G6', 'DESIGN_A · G6 + 조형 연산 / 추가 CC 0회')
    for view in render.VIEWS:
        canvas = Image.new('RGB', (1800, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN · {view} · 실제 G6 부모와 디자인안 · 기존 1장 + 신규 5장', font=title, fill='black')
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
        compose(args.root, proof)
    print('RENDER_VERIFICATION_PASS: 1 reused parent front + 5 fresh originals', flush=True)


if __name__ == '__main__':
    main()
