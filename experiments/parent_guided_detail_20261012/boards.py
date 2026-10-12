"""Uncropped, equal-camera comparisons of saved native geometry renders."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

MODES = ('BASELINE', 'VALLEY_PRIORITY', 'FLOW_CHAIN')
LABELS = ('현재 선택안', '부모 골 우선 시험', '중간 접힘 + 부모 방향 디테일 시험')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--meso-root', type=Path)
    parser.add_argument('--active-root', type=Path)
    args = parser.parse_args()
    out = args.root/'images'
    out.mkdir(exist_ok=True)
    title = ImageFont.truetype(r'C:\Windows\Fonts\malgunbd.ttf', 28)
    text = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 23)
    records = []
    for case in ('SPAN', 'COUNTER'):
        for view in ('front_micro', 'oblique_micro', 'side_micro', 'front'):
            paths = [args.root/mode/case/'G06/views'/f'{view}.png' for mode in MODES]
            images = [Image.open(path).convert('RGB') for path in paths]
            assert all(im.size == images[0].size for im in images)
            w, h = images[0].size
            canvas = Image.new('RGB', (3*w, h+145), 'white')
            draw = ImageDraw.Draw(canvas)
            draw.text((24, 13), f'{case} · {view} · 실제 G6 메시 / 동일 카메라·재질', font=title, fill='black')
            for i, (im, label) in enumerate(zip(images, LABELS)):
                draw.text((i*w+24, 61), label, font=text, fill='black')
                canvas.paste(im, (i*w, 105))
            draw.text((24, h+111), '왼쪽↔가운데: 성장 우선순위 대조 / 오른쪽: 접힘·배치·밀도 재구성의 복합 시험', font=text, fill='black')
            path = out/f'{case}_{view}.png'
            canvas.save(path)
            records.append(dict(output=str(path), sources=[str(p) for p in paths], crop=False, resize=False))
    (out/'SOURCE_LIST.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf8')
    if bool(args.meso_root) != bool(args.active_root):
        raise ValueError('Supply both optional alternative roots for matched four-way boards.')
    if args.meso_root:
        alternatives = []
        for case in ('SPAN', 'COUNTER'):
            folders = [args.root/'BASELINE'/case/'G06', args.root/'FLOW_CHAIN'/case/'G06',
                args.meso_root/'MESO_ONLY_PATCH'/case/'G06', args.active_root/'ACTIVE_FOLDS'/case/'G06']
            labels = ['현재 선택안', '중간 접힘 + 부모 방향 벌브 시험', '국소 새 벌브 제외 대조', '활성 접힘 시험: 국소 벌브 대체']
            for view in ('front_micro', 'oblique_micro', 'side_micro', 'front'):
                paths = [folder/'views'/f'{view}.png' for folder in folders]
                images = [Image.open(path).convert('RGB') for path in paths]
                if not all(im.size == images[0].size for im in images):
                    raise ValueError('Image sizes differ.')
                w, h = images[0].size
                canvas = Image.new('RGB', (2*w, 2*(h+55)+75), 'white')
                draw = ImageDraw.Draw(canvas)
                draw.text((24, 12), f'{case} · {view} · 동일 카메라·재질 / 실제 G6', font=title, fill='black')
                for index, (im, label) in enumerate(zip(images, labels)):
                    x, y = (index % 2)*w, 65+(index//2)*(h+55)
                    draw.text((x+24, y), label, font=text, fill='black')
                    canvas.paste(im, (x, y+45))
                target = out/f'{case}_{view}_alternatives.png'
                canvas.save(target)
                alternatives.append(dict(output=str(target), view=view, crop=False, resize=False,
                    sources=[dict(image=str(path), image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        geometry=str(folder/'geometry.npz'), generation=str(folder/'generation.json'),
                        render_receipt=str(folder/'views/receipt.json')) for path, folder in zip(paths, folders)]))
        (out/'ALTERNATIVES_SOURCE_LIST.json').write_text(json.dumps(alternatives, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
