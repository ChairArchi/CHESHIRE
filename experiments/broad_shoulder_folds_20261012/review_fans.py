"""Matched four-way real-mesh comparison, preserving both prior stages."""
from pathlib import Path
import argparse
import json
from PIL import Image, ImageDraw, ImageFont

from render import VIEWS
from review import digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True, help='Fresh rooted fan output')
    p.add_argument('--broad-root', type=Path, required=True)
    p.add_argument('--baseline-root', type=Path, required=True)
    args = p.parse_args()
    output = args.root/'images'
    if output.exists():
        raise FileExistsError('Earlier comparisons preserved.')
    output.mkdir()
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 28)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    modes = ('BASELINE', 'CLEAR_ONLY', 'BROAD_ACTIVE', 'ROOTED_FANS')
    labels = ('현재 선택안', '넓은 어깨의 벌브 제외 대조', '중간 능선·옆골 시험', '같은 능선에 작은 사선 접힘 추가')
    records, states = [], []
    for case in ('SPAN', 'COUNTER'):
        folders = [args.broad_root/mode/case/'G06' for mode in modes[:3]]
        folders.append(args.root/'ROOTED_FANS'/case/'G06')
        for mode, folder in zip(modes, folders):
            receipt_path = folder/'views/receipt.json'
            receipt = json.loads(receipt_path.read_text(encoding='utf8'))
            source = (args.baseline_root/'BASELINE'/case/'G06/geometry.npz').resolve() if mode == 'BASELINE' else (folder/'geometry.npz').resolve()
            if (receipt['views'] != json.loads(json.dumps(VIEWS)) or
                receipt['resolution'] != 900 or receipt['samples'] != 24 or
                receipt['material'] != 'Existing uniform mineral; flat geometric normals' or
                receipt['modifiers'] != [] or receipt['normal_maps'] is not False or
                Path(receipt['source']).resolve() != source or receipt['source_sha256'] != digest(source)):
                raise ValueError('Render source/camera/material differs: '+str(folder))
            images = []
            for view in VIEWS:
                path = folder/'views'/f'{view}.png'
                with Image.open(path) as im:
                    if im.size != (900, 900):
                        raise ValueError('Image dimensions differ.')
                    im.verify()
                images.append(dict(view=view, path=str(path), sha256=digest(path)))
            states.append(dict(input_case=case, candidate=mode, geometry=str(source), geometry_sha256=digest(source),
                render_receipt_sha256=digest(receipt_path), images=images))
        for view in VIEWS:
            paths = [folder/'views'/f'{view}.png' for folder in folders]
            canvas = Image.new('RGB', (1800, 1980), 'white')
            draw = ImageDraw.Draw(canvas)
            draw.text((24, 12), f'{case} · {view} · 동일 카메라·재질 / 실제 G6', font=title, fill='black')
            for index, (path, text) in enumerate(zip(paths, labels)):
                x, y = index%2*900, 65+index//2*955
                draw.text((x+24, y), text, font=label, fill='black')
                with Image.open(path) as im:
                    canvas.paste(im.convert('RGB'), (x, y+45))
            target = output/f'{case}_{view}.png'
            canvas.save(target)
            records.append(dict(output=str(target), sha256=digest(target), crop=False, resize=False,
                sources=[dict(path=str(path), sha256=digest(path)) for path in paths]))
    (output/'SOURCE_LIST.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf8')
    (args.root/'RENDER_VERIFICATION.json').write_text(json.dumps(dict(passed=True, actual_mesh_states=8,
        source_images=32, crop=False, resize=False, states=states), indent=2), encoding='utf8')
    print('FAN_RENDER_VERIFICATION_PASS 8 states / 32 images / 8 boards', flush=True)


if __name__ == '__main__':
    main()
