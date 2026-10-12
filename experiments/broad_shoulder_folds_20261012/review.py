"""Verify image conditions and compose uncropped equal-sized comparisons."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

from render import VIEWS, MODES

LABELS = ('현재 선택안', '넓은 어깨의 벌브 제외 대조', '같은 어깨의 중간 능선·옆골 시험')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, required=True)
    args = parser.parse_args()
    output = args.root/'images'
    if output.exists():
        raise FileExistsError('Earlier comparisons preserved.')
    output.mkdir()
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 28)
    label = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    verification, boards = [], []
    for case in ('SPAN', 'COUNTER'):
        folders = [args.root/mode/case/'G06' for mode in MODES]
        for mode, folder in zip(MODES, folders):
            receipt_path = folder/'views/receipt.json'
            receipt = json.loads(receipt_path.read_text(encoding='utf8'))
            source_folder = (args.parent_root if mode == 'BASELINE' else args.root)/mode/case/'G06'
            source = (source_folder/'geometry.npz').resolve()
            if (receipt['views'] != json.loads(json.dumps(VIEWS)) or
                receipt['resolution'] != 900 or receipt['samples'] != 24 or
                receipt['material'] != 'Existing uniform mineral; flat geometric normals' or
                receipt['modifiers'] != [] or receipt['normal_maps'] is not False or
                Path(receipt['source']).resolve() != source or receipt['source_sha256'] != digest(source)):
                raise ValueError('Render source/camera/material conditions differ: '+str(folder))
            files = []
            for view in VIEWS:
                path = folder/'views'/f'{view}.png'
                with Image.open(path) as im:
                    if im.size != (900, 900):
                        raise ValueError('Wrong image dimensions.')
                    im.verify()
                files.append(dict(view=view, path=str(path), sha256=digest(path)))
            verification.append(dict(input_case=case, candidate=mode, geometry=str(source),
                geometry_sha256=digest(source), render_receipt_sha256=digest(receipt_path), images=files))
        for view in VIEWS:
            paths = [folder/'views'/f'{view}.png' for folder in folders]
            canvas = Image.new('RGB', (2700, 1020), 'white')
            draw = ImageDraw.Draw(canvas)
            draw.text((24, 12), f'{case} · {view} · 동일 카메라·재질 / 실제 G6 대안 비교', font=title, fill='black')
            for index, (path, text) in enumerate(zip(paths, LABELS)):
                draw.text((index*900+24, 61), text, font=label, fill='black')
                with Image.open(path) as im:
                    canvas.paste(im.convert('RGB'), (index*900, 105))
            target = output/f'{case}_{view}.png'
            canvas.save(target)
            boards.append(dict(output=str(target), output_sha256=digest(target), resize=False, crop=False,
                sources=[dict(path=str(path), sha256=digest(path)) for path in paths]))
    (output/'SOURCE_LIST.json').write_text(json.dumps(boards, ensure_ascii=False, indent=2), encoding='utf8')
    (args.root/'RENDER_VERIFICATION.json').write_text(json.dumps(dict(passed=True,
        actual_mesh_states=len(verification), source_images=24, crop=False, resize=False, states=verification), indent=2), encoding='utf8')
    print('RENDER_VERIFICATION_PASS', len(verification), 'states / 24 images / 8 boards', flush=True)


if __name__ == '__main__':
    main()
