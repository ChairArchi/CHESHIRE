"""Compose actual native G0 renders; no geometry or image content synthesis."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = ROOT / 'review_selected'
    out.mkdir(exist_ok=False)
    fontpath = 'C:/Windows/Fonts/malgun.ttf'
    title = ImageFont.truetype(fontpath, 28)
    body = ImageFont.truetype(fontpath, 20)
    board = Image.new('RGB', (1800, 744), '#171d21')
    draw = ImageDraw.Draw(board)
    draw.text((30, 15), '초기 형상 비교 · 동일한 원형 접힘 연산 / 동일한 193링 샘플링', font=title, fill='white')
    rows = [('B193', '원형', '기존 큰 접힘 2개 + 보조 접힘 3개'),
            ('K08_193', '이전 겹침안', '큰 접힘 8개를 여러 높이에 배치'),
            ('L08_PRIMARY_193', '선택한 겹침안', '원형 유지 + 넓은 마디에 큰 접힘 6개 추가')]
    sources = []
    for i, (ident, label, caption) in enumerate(rows):
        path = ROOT / 'G0_REVIEW_RENDER_v2' / (ident + '_whole.png')
        picture = Image.open(path).convert('RGB').resize((600, 600), Image.Resampling.LANCZOS)
        board.paste(picture, (600 * i, 62))
        draw.text((600 * i + 25, 670), label, font=title, fill='white')
        draw.text((600 * i + 25, 710), caption, font=body, fill='#c0cbd0')
        sources.append(dict(id=ident, render=str(path), sha256=sha(path)))
    dest = out / 'G0_COMPARISON.png'
    board.save(dest)
    color = Image.new('RGB', (1200, 1335), '#171d21')
    picture = ROOT / 'G0_REVIEW_RENDER_v2/L08_PRIMARY_193_source_roles.png'
    color.paste(Image.open(picture).convert('RGB'), (0, 0))
    d = ImageDraw.Draw(color)
    d.text((40, 1202), '주황: 원형 구조   파랑: 추가 접힘의 영향   회색: 원형 목의 중심', font=title, fill='white')
    d.text((40, 1250), '넓은 마디의 옆면과 끝을 겹치고, 잘록한 구간은 남기는 배치', font=title, fill='#c0cbd0')
    destcolor = out / 'G0_SELECTED_COLOR.png'
    color.save(destcolor)
    (out / 'BOARD_RECEIPT.json').write_text(json.dumps(dict(
        kind='ACTUAL_NATIVE_RENDER_COMPOSITION', source_renders=sources,
        color_source=dict(path=str(picture), sha256=sha(picture)),
        comparison=dict(path=str(dest), sha256=sha(dest)),
        colors=dict(path=str(destcolor), sha256=sha(destcolor)),
        geometry_generated_in_this_step=False), ensure_ascii=False, indent=2), encoding='utf8')
    print(dest)


if __name__ == '__main__':
    main()
