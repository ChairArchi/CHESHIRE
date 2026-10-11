"""Copy a small review set, leaving geometry and full logs on E:. No hash audit."""
from pathlib import Path
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/directional_growth_20261012')
BASE = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011/ANCESTRY_STAGED')
DOC = REPO / 'docs/directional_growth_20261012'


def main():
    images = DOC / 'images'
    technical = DOC / 'technical'
    images.mkdir(parents=True, exist_ok=True)
    technical.mkdir(parents=True, exist_ok=True)
    for name in ('early_comparison.png', 'final_comparison.png', 'response_comparison.png',
                 'CORRIDOR_progression.png', 'OVERLAP_progression.png'):
        source = ROOT / 'review' / name
        if source.exists():
            shutil.copy2(source, images / name)
    shutil.copy2(HERE / 'SOURCE_NOTES.md', DOC / 'SOURCE_NOTES.md')
    records = {}
    for family in ('CORRIDOR', 'OVERLAP', 'FACE_RESPONSE', 'SIGNED_RESPONSE'):
        records[family] = {}
        for folder in sorted((ROOT / family).glob('G[0-9][0-9]')):
            if not (folder / 'generation.json').exists():
                continue
            key = family + '_' + folder.name
            shutil.copy2(folder / 'generation.json', technical / (key + '.json'))
            paths = {kind: str(folder / filename) for kind, filename in
                     [('mesh', 'gate.ply'), ('authoritative_mesh', 'geometry.npz'),
                      ('checkpoint', 'checkpoint.npz'), ('next_control', 'control_quad.npz'),
                      ('operation_fields', 'operation_fields.npz'), ('blender', 'column.blend')]}
            paths['renders'] = {view: str(folder / 'preview' / (view + '.png'))
                                for view in ('front', 'oblique', 'side')}
            if (folder / 'core_validation.json').exists():
                shutil.copy2(folder / 'core_validation.json', technical / (key + '_core.json'))
                paths['core_validation'] = str(folder / 'core_validation.json')
            records[family][folder.name] = paths
    for source in (ROOT / 'visual_review').glob('*.md'):
        shutil.copy2(source, technical / source.name)
    check = ROOT / 'review/core_validation.json'
    if check.exists():
        shutil.copy2(check, technical / 'core_validation.json')
    index = dict(shared_G1=str(BASE / 'G01'), baseline_G2=str(BASE / 'G02'),
                 baseline_G3=str(BASE / 'G03'), actual_output_root=str(ROOT),
                 code=str(HERE), candidates=records,
                 recommendation='See REPORT.md for visual selection; these are CHESHIRE comparisons, not an IAAC reproduction or fabrication certification.',
                 format='geometry.npz float64 triangles are authoritative and also drive the renders; PLY is the exchange copy. Render fan centres do not become next controls.',
                 scope='Two G2 approaches; OVERLAP receives G3 and two existing normal-response comparisons from the same G2. No new returns added at G3. Only explicit selected core checks; no full regression or hash audit.')
    (DOC / 'INDEX.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf8')
    print('PACKAGED', str(DOC), flush=True)


if __name__ == '__main__':
    main()
