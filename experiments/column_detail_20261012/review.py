"""Small actual-render boards and descriptive scale records, no aesthetic score."""
from pathlib import Path
import argparse
import importlib.util
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/column_detail_20261012')
BASE = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
FONT = 'C:/Windows/Fonts/arial.ttf'

def board(path, items, rows, size=540):
    image = Image.new('RGB', (size*len(items), 65+(size+38)*len(rows)), '#eeeee9')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT, 20)
    for col, (label, _) in enumerate(items):
        draw.text((size*col+12, 18), label, font=font, fill='#17232b')
    for row, (label, subpath) in enumerate(rows):
        y = 65+row*(size+38)
        draw.text((12, y+6), label, font=font, fill='#17232b')
        for col, (_, folder) in enumerate(items):
            with Image.open(folder/subpath) as source:
                image.paste(source.convert('RGB').resize((size,size)), (col*size,y+38))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)

def records(items):
    result = {}
    for label, folder in items:
        with np.load(folder/'geometry.npz', allow_pickle=False) as data:
            xyz, faces = data['xyz'], data['faces']
            height = float(np.ptp(xyz[:,2]))
        generation = json.loads((folder/'generation.json').read_text(encoding='utf8'))
        info = dict(folder=str(folder), vertices=len(xyz), triangles=len(faces),
                    height_model_units=height,
                    subdivision_passes=generation['subdivision_passes_total'],
                    field_passes=generation['field_passes_total'])
        file = folder/'operation_fields.npz'
        if file.exists():
            with np.load(file, allow_pickle=False) as fields:
                for name in ('applied_task36_displacement','displacement'):
                    if name not in fields:
                        continue
                    length = np.linalg.norm(fields[name],axis=1)
                    nonzero = length[length>1e-12]
                    info[name] = dict(nonzero_points=len(nonzero),
                        model_unit_quantiles=dict(zip(('p10','p50','p90','maximum'),
                            [float(v) for v in np.quantile(nonzero,[.1,.5,.9,1.])])) if len(nonzero) else {},
                        median_over_column_height=float(np.median(nonzero)/height) if len(nonzero) else 0.)
        result[label] = info
    result['interpretation'] = ('Placement-vector lengths describe this operation, not minimum readable ornament, '
        'thickness, print resolution or a physical-unit claim. Triangle count is tessellation, not an aesthetic score.')
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate', nargs='*', default=[])
    args = parser.parse_args()
    out = ROOT/'review'
    items = [('OVERLAP G3 / source', BASE), ('CONTINUED G4',ROOT/'CONTINUED/G04'),
             ('NESTED G4',ROOT/'NESTED/G04')]
    for family in ('NESTED_STRONG','RETURN_DETAIL','RETURN_HYBRID'):
        for folder in sorted((ROOT/family).glob('G[0-9][0-9]')):
            if (folder/'geometry.npz').exists():
                items.append((family.replace('_',' ')+' '+folder.name,folder))
    board(out/'whole_comparison.png', items, [(v, 'preview/'+v+'.png') for v in ('front','oblique','side')],size=400)
    detail_rows = [('Front lower / camera span 4.0','detail/front_meso.png'),
                   ('Side waist / camera span 4.0','detail/side_meso.png'),
                   ('Front upper selected region / camera span 1.2','detail/front_zone.png'),
                   ('Side lower selected region / camera span 1.2','detail/side_zone.png')]
    board(out/'detail_comparison.png', items, detail_rows,size=400)
    nested = [items[0]] + [item for item in items if item[0].startswith('NESTED')]
    board(out/'nested_progression.png', nested, [('Front','preview/front.png'),
          ('Upper front / span 1.2','detail/front_zone.png'),('Lower side / span 1.2','detail/side_zone.png')])
    returns = [items[0]] + [item for item in items if item[0].startswith('RETURN ')]
    if len(returns)>1:
        board(out/'return_progression.png',returns,[('Front','preview/front.png'),
            ('Upper front / span 1.2','detail/front_zone.png'),('Lower side / span 1.2','detail/side_zone.png')])
    (out/'scale_records.json').write_text(json.dumps(records(items),indent=2),encoding='utf8')
    if args.validate:
        spec = importlib.util.spec_from_file_location('existing_core_checks', HERE.parent/'curved_fold_side_20261011/review.py')
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        results = {}
        for name in args.validate:
            folder = ROOT/name
            file = folder/'core_validation.json'
            results[name] = json.loads(file.read_text(encoding='utf8')) if file.exists() else old.validate(folder)
        (out/'core_validation.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    print('REVIEW_SAVED',out,flush=True)

if __name__ == '__main__':
    main()
