"""Compose receipt-verified NESTED02 / candidate review PNGs at native 900px.

Only the report canvas, headings and captions are new. Original render pixels
are pasted without cropping, scaling, retouching or color changes. Both sides
must have the matched final 900px conditions. Existing outputs are preserved.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'package.py'
spec = importlib.util.spec_from_file_location('fold_junction_board_package', PACKAGE)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
render = package.render
digest = render.digest
LABELS = {'close_oblique': '근접 · Close oblique',
          'body_oblique': '몸체 · Body oblique', 'front': '전체 · Front'}


def font(size, bold=False):
    paths = ([Path('C:/Windows/Fonts/malgunbd.ttf')] if bold else []) + [
        Path('C:/Windows/Fonts/malgun.ttf'), Path('C:/Windows/Fonts/malgun.ttc'),
        Path('C:/Windows/Fonts/arial.ttf')]
    for path in paths:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size), str(path)
    return ImageFont.load_default(size=size), 'Pillow default'


def wrapped(draw, text, left, top, selected_font, max_width, fill, line_height):
    """Wrap by measured pixels, including Korean strings without spaces."""
    line = ''
    for character in text:
        trial = line + character
        if character == '\n' or (line and draw.textlength(trial, font=selected_font) > max_width):
            draw.text((left, top), line, font=selected_font, fill=fill)
            top += line_height
            line = '' if character == '\n' else character
        else:
            line = trial
    if line:
        draw.text((left, top), line, font=selected_font, fill=fill)
        top += line_height
    return top


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.ROOT)
    parser.add_argument('--variant', default='DEVELOPED')
    parser.add_argument('--output', type=Path, required=True,
                        help='New .png report path; a JSON receipt and code snapshot are also saved.')
    parser.add_argument('--views', nargs='+', choices=render.VIEWS, default=list(render.VIEWS))
    parser.add_argument('--caption', default='',
                        help='Optional short reviewer caption, recorded verbatim as author supplied.')
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    name = render.checked_name(args.variant)
    if output.suffix.lower() != '.png' or len(set(args.views)) != len(args.views):
        parser.error('Output must be .png and requested views must be unique.')
    receipt_output = output.with_suffix('.json')
    code_output = output.with_name(output.stem + '_SOURCE_review_board.py')
    if any(path.exists() for path in (output, receipt_output, code_output)):
        raise FileExistsError('Earlier report, receipt or source snapshot is preserved.')
    binding = render.source_binding()
    expected, generation = render.candidate_state(root, name, binding)
    rendered, rendering, inventory = package.checked_render(root, name, 'review', expected,
                                                            generation, binding)
    if rendered['resolution_matched_to_source'] is not True:
        raise ValueError('A final matched-resolution render is required; previews cannot be upscaled.')
    render.require_close(rendered['conditions'], binding['conditions'])
    if rendered['conditions']['resolution'] != [900, 900]:
        raise ValueError('Both source and final candidate must be 900 x 900.')
    by_view = {record['view']: record for record in inventory}
    if any(view not in by_view for view in args.views):
        raise ValueError('Requested view is absent from the actual final render receipt.')
    hashes = dict(board=digest(__file__), package=digest(PACKAGE), renderer=render.code_hashes())
    title_font, title_font_path = font(34, True)
    label_font, label_font_path = font(25, True)
    text_font, text_font_path = font(21)
    margin, gap, panel, header, row_title, footer = 28, 24, 900, 170, 48, 85
    width = 2 * margin + 2 * panel + gap
    height = header + len(args.views) * (row_title + panel + 22) + footer
    board = Image.new('RGB', (width, height), '#11171d')
    draw = ImageDraw.Draw(board)
    draw.text((margin, 22), 'CHESHIRE · NESTED02 / ' + name, font=title_font, fill='#edf4f8')
    draw.text((margin, 73), '같은 카메라 · 재질 · 조명 · 24 samples · 900px · flat shading',
              font=text_font, fill='#a6c8cf')
    caption = args.caption or '기존 주름과 근접 접속을 같은 시점에서 비교합니다.'
    caption_bottom = wrapped(draw, caption, margin, 109, text_font, width - 2 * margin,
                             '#c5d0da', 29)
    if caption_bottom > header - 7:
        raise ValueError('Caption is too long; use at most two short lines.')
    placements = []
    for index, view in enumerate(args.views):
        row_top = header + index * (row_title + panel + 22)
        draw.text((margin, row_top), 'NESTED02  /  ' + LABELS[view], font=label_font, fill='#edf4f8')
        draw.text((margin + panel + gap, row_top), name + '  /  ' + LABELS[view],
                  font=label_font, fill='#edf4f8')
        for side, left in (('reference', margin), ('candidate', margin + panel + gap)):
            record = by_view[view]
            with Image.open(record[side]) as original:
                original.load()
                if original.format != 'PNG' or original.size != (panel, panel):
                    raise ValueError('Actual PNG has unexpected size or format: ' + record[side])
                if original.mode not in ('RGB', 'RGBA'):
                    raise ValueError('Actual PNG must contain unchanged RGB channels.')
                if original.mode == 'RGBA' and original.getchannel('A').getextrema() != (255, 255):
                    raise ValueError('Opaque render required for an exact RGB report panel.')
                image = original.convert('RGB')
            top = row_top + row_title
            board.paste(image, (left, top))
            crop = board.crop((left, top, left + panel, top + panel))
            if ImageChops.difference(crop, image).getbbox() is not None:
                raise ValueError('Report panel changed actual render RGB pixels.')
            placements.append(dict(view=view, side=side, path=record[side],
                source_sha256=record[side + '_sha256'], box=[left, top, left + panel, top + panel]))
    count_text = (f"{name}: {expected['vertices']:,} vertices / {expected['triangles']:,} triangles. "
                  '원본 렌더 픽셀 1:1 · 좌표와 형상은 보고서에서 변경하지 않았습니다.')
    wrapped(draw, count_text, margin, height - footer + 12, text_font, width - 2 * margin,
            '#a9b8c3', 29)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'xb') as stream:
        board.save(stream, format='PNG')
    with Image.open(output) as saved:
        saved.load()
        if saved.size != board.size or ImageChops.difference(saved.convert('RGB'), board).getbbox() is not None:
            raise ValueError('PNG report roundtrip changed pixels.')
        for record in placements:
            with Image.open(record['path']) as original:
                actual = original.convert('RGB')
            if ImageChops.difference(saved.crop(record['box']).convert('RGB'), actual).getbbox() is not None:
                raise ValueError('Saved report panel differs from its actual PNG source.')
            if digest(record['path']) != record['source_sha256']:
                raise ValueError('Original PNG changed during report composition.')
    if (render.source_binding() != binding or render.candidate_state(root, name, binding) != (expected, generation) or
            package.checked_render(root, name, 'review', expected, generation, binding) !=
            (rendered, rendering, inventory) or
            dict(board=digest(__file__), package=digest(PACKAGE), renderer=render.code_hashes()) != hashes):
        raise ValueError('Report inputs or executed source changed.')
    shutil.copyfile(__file__, code_output)
    if digest(code_output) != hashes['board']:
        raise ValueError('Report source snapshot differs.')
    result = dict(kind='MATCHED_900_NATIVE_PIXEL_REVIEW_BOARD', source_variant=name,
        views=args.views, board=dict(path=str(output), sha256=digest(output), size=list(board.size)),
        generation_receipt=generation, render_receipt=rendering,
        source_geometry=expected, original_render_panels=placements,
        original_render_pixels_unchanged=True, scaling=False, cropping=False, retouching=False,
        exact_RGB_PNG_roundtrip=True, all_flat=True, samples=24,
        caption=caption, caption_author_supplied=bool(args.caption),
        fonts=dict(title=title_font_path, labels=label_font_path, caption=text_font_path),
        executed_code_sha256=hashes,
        source_snapshot=dict(path=str(code_output), sha256=digest(code_output)))
    with open(receipt_output, 'x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(board=str(output), receipt=str(receipt_output), size=list(board.size)),
                     ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
