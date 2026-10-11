"""Small comparison boards assembled only from saved actual-mesh renders."""
from pathlib import Path
import argparse

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
DEFAULT_OUTPUT = HERE.parents[1] / 'docs/fold_transfer_20261012/images'
SPAN_G3 = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
CELL = 416
LEFT = 160
MARGIN = 18
TITLE = 56
HEAD = 44
FOOT = 46
BG = (237, 237, 233)
FG = (30, 34, 36)


def font(size):
    for path in ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/segoeui.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def board(path, title, columns, row_labels, sources, footer):
    if len(sources) != len(row_labels) or any(len(row) != len(columns) for row in sources):
        raise ValueError('Every labelled row must have the declared number of columns.')
    missing = [str(p) for row in sources for p in row if not p.is_file()]
    if missing:
        raise FileNotFoundError('Missing actual render; no placeholder created:\n' + '\n'.join(missing))
    width = LEFT + MARGIN + CELL * len(columns) + MARGIN
    height = TITLE + HEAD + CELL * len(row_labels) + FOOT
    canvas = Image.new('RGB', (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((MARGIN, 15), title, fill=FG, font=font(25))
    for col, label in enumerate(columns):
        x = LEFT + MARGIN + col * CELL
        draw.text((x + 12, TITLE + 10), label, fill=FG, font=font(19))
    for row, label in enumerate(row_labels):
        y = TITLE + HEAD + row * CELL
        for number, line in enumerate(label.split('\n')):
            draw.text((MARGIN, y + 16 + 25 * number), line, fill=FG,
                      font=font(19 if number == 0 else 16))
        for col, source in enumerate(sources[row]):
            x = LEFT + MARGIN + col * CELL
            with Image.open(source) as saved:
                actual = ImageOps.contain(saved.convert('RGB'), (CELL, CELL), Image.Resampling.LANCZOS)
            canvas.paste(actual, (x + (CELL - actual.width) // 2, y + (CELL - actual.height) // 2))
            draw.rectangle((x, y, x + CELL - 1, y + CELL - 1), outline=(210, 211, 207))
    draw.text((MARGIN, height - FOOT + 14), footer, fill=FG, font=font(15))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, optimize=True, compress_level=7)
    print('BOARD', path, canvas.size, path.stat().st_size, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--span-g3', type=Path, default=SPAN_G3)
    parser.add_argument('--boards', nargs='+', choices=('progression', 'views', 'field', 'detail'),
                        default=['progression', 'views', 'field'])
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    families = dict(SPAN=root / 'SPAN', COUNTER=root / 'COUNTER_MATCHED')
    render = lambda folder, view: folder / 'preview' / (view + '.png')
    if 'progression' in args.boards:
        rows = []
        for name in ('SPAN', 'COUNTER'):
            g3 = args.span_g3 if name == 'SPAN' else root / 'COUNTER/G03'
            rows.append([render(root / 'inputs' / name / 'G00', 'front'),
                         render(g3, 'front'), render(families[name] / 'RETURN_ONLY/G04', 'front')])
        board(output / 'transfer_progression.png', 'Fold transfer | two actual initial masses',
              ['Initial mass G0', 'Existing growth G3', 'Small returns G4'],
              ['SPAN', 'COUNTER\nmatched G4'], rows,
              'Front camera shared. G4 = RETURN_ONLY. SPAN G3 is preserved OVERLAP; COUNTER G3 is its own saved growth.')
    if 'views' in args.boards:
        rows = [[render(families[name] / 'RETURN_ONLY/G04', view)
                 for view in ('front', 'oblique', 'side')] for name in ('SPAN', 'COUNTER')]
        board(output / 'selected_views.png', 'G4 small returns | actual mesh in three views',
              ['Front', 'Oblique', 'Side'], ['SPAN\nRETURN_ONLY G4', 'COUNTER\nmatched\nRETURN_ONLY G4'], rows,
              'Same view cameras and material. RETURN_ONLY has no fourth field pass; it is the geometric-return comparison.')
    if 'field' in args.boards:
        modes = ('RETURN_ONLY', 'UNPROTECTED', 'PROTECTED')
        rows, labels = [], []
        for name in ('SPAN', 'COUNTER'):
            for view in ('front', 'side'):
                rows.append([render(families[name] / mode / 'G04', view) for mode in modes])
                labels.append(name + '\n' + view + ' / G4' + ('\nmatched' if name == 'COUNTER' else ''))
        board(output / 'field_comparison.png', 'G4 field comparison | preserved return / unrestricted / protected',
              list(modes), labels, rows,
              'COUNTER uses COUNTER_MATCHED only. More visible detail is not a claim of better fold hierarchy or fabrication readiness.')
    if 'detail' in args.boards:
        modes = ('RETURN_ONLY', 'UNPROTECTED', 'PROTECTED')
        rows = [[root / 'SPAN' / mode / 'G04/detail' / (view + '.png') for mode in modes]
                for view in ('front_meso', 'side_meso')]
        board(output / 'detail_comparison.png', 'SPAN G4 | identical actual-geometry close-up cameras',
              list(modes), ['Front meso\nz = 2.8 / span 4', 'Side meso\nz = 5.0 / span 4'], rows,
              'Both cameras use the saved fixed meso views. Images are resized in full; no geometry edits, crops, retouching or maps.')


if __name__ == '__main__':
    main()
