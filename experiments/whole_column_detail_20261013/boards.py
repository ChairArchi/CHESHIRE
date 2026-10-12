"""Compare the saved source and two cumulative whole-column G6 stages."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('whole_column_boards_render', HERE / 'render.py')
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
    parent_info, parent_source = render.parent_state()
    source_views = {'front': render.VIEWS['front']}
    front_hashes = dict(render=render.PARENT_RENDER_SHA256, frozen_renderer=render.FROZEN_SHA256,
        broad_camera_recipe=hashes['broad_camera_recipe'], shared_material_scene_recipe=hashes['shared_material_scene_recipe'])
    front, rf, vf = checked_images(parent_info, parent_source, render.PARENT / 'views/receipt.json',
        source_views, front_hashes, exact_views=False)
    body_hashes = dict(render=render.BODY_RENDER_SHA256, frozen_renderer=render.FROZEN_SHA256,
        parent_renderer=render.PARENT_RENDER_SHA256, broad_camera_recipe=hashes['broad_camera_recipe'],
        shared_material_scene_recipe=hashes['shared_material_scene_recipe'])
    bodies, rb, vb = checked_images(parent_info, parent_source, render.BODY_REFERENCE / 'receipt.json',
        {'body_oblique': render.VIEWS['body_oblique']}, body_hashes, exact_views=False)
    closes, rc, vc = checked_images(parent_info, parent_source, root / 'reference_views/receipt.json',
        {'close_oblique': render.VIEWS['close_oblique']}, hashes)
    for image in front + bodies:
        image['reused_reference'] = True
    for image in closes:
        image['reused_reference'] = False
    states = [dict(candidate='DEPTH_08', source=parent_source, images=front + bodies + closes)]
    reference_views = dict(**vf, **vb, **vc)
    receipts = [rf, rb, rc]
    for stage in render.STAGES:
        folder, info, source = render.source_state(root, stage)
        images, receipt, views = checked_images(info, source, folder / 'views/receipt.json', render.VIEWS, hashes)
        if receipt.get('added_CC_passes') != 0 or receipt.get('source_generation') != 6:
            raise ValueError('Cumulative stages must declare actual G6 and zero added CC passes.')
        for key, value in (('parent_control_sha256', parent_source['control_sha256']),
                           ('parent_geometry_sha256', parent_source['source_sha256']),
                           ('parent_generation_sha256', parent_source['generation_sha256'])):
            if source[key] != value:
                raise ValueError('All references must depict the actual design source.')
        for view in render.VIEWS:
            render.require_close(views[view], reference_views[view], 'matched-camera.' + view)
        for image in images:
            image['reused_reference'] = False
        states.append(dict(candidate=stage, source=source, images=images))
        receipts.append(receipt)
    for receipt in receipts[1:]:
        if receipt['version'] != rf['version'] or receipt['conditions'] != rf['conditions']:
            raise ValueError('Actual Blender version or material/scene conditions differ.')
    return dict(passed=True, new_root=str(root), states=states,
        subdivision_generation=6, stage_added_CC_passes=0, stage_order=['DEPTH_08', 'MIDDLE', 'FINE'],
        reused_parent_images=2, new_parent_close_images=1, new_design_images=6,
        new_images=7, source_images=9, conditions=rf['conditions'], actual_views=reference_views,
        Blender_version=rf['version'], crop=False, resize=False,
        scope='Saved geometry/code/native-array receipts, same actual camera/material conditions and PNG hashes; cumulative design stages, not subdivision generations; no full lineage or geometry/aesthetic certification.')


def compose(root, proof):
    root = Path(root).resolve()
    output = root / 'images'
    if str(root) != proof['new_root'] or output.exists() or (root / 'RENDER_VERIFICATION.json').exists():
        raise FileExistsError('Fresh verified comparison root required.')
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 27)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    output.mkdir()
    boards = []
    labels = ('출발 형상 · DEPTH_08 G6', '중간 접힘 단계 · MIDDLE G6', '미세 접힘 누적 단계 · FINE G6')
    view_labels = dict(front='전체 정면', body_oblique='본체 사선', close_oblique='근접 사선')
    for view in render.VIEWS:
        canvas = Image.new('RGB', (2700, 1020), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 12), f'SPAN · {view_labels[view]} · 전체 기둥의 누적 변형 단계 비교 · 실제 G6 / 추가 CC 0회', font=title, fill='black')
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
    print('RENDER_VERIFICATION_PASS: 2 reused originals + 7 fresh originals / 3 cumulative G6 stages', flush=True)


if __name__ == '__main__':
    main()
