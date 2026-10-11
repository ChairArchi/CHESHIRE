"""Index selected results and assemble comparisons; no geometry mutation."""
from pathlib import Path
import json, shutil
from fold_review import mirror_check
from review_boards import ROOT, board

HERE = Path(__file__).resolve().parent


def main():
    review = ROOT / 'review'
    modes = [('D02 / overlapping', 'D02_INTERLEAVED', 'DIRECTIONAL_FIELD'),
             ('D04 / deeper return', 'D04_DEEP_RETURN', 'D04_DEEP_RETURN_FIELD'),
             ('D05 / curved path', 'D05_CURVED_PATH', 'D05_CURVED_PATH_FIELD')]
    for _, cage, field in modes[1:]:
        mirror_check(ROOT / 'directional' / cage / 'CC2')
        mirror_check(ROOT / 'input_field' / field / 'G02_CC')
    for view in ('front', 'oblique', 'side'):
        for group, title in [('geometry', 'Modelled inputs / same 2 CC passes'),
                             ('field', 'Same field / G2 + 1 presentation CC')]:
            entries = [(label, ROOT / ('directional/' + cage + '/CC2' if group == 'geometry'
                                      else 'input_field/' + field + '/G02_CC') /
                        'preview' / (view + '.png')) for label, cage, field in modes]
            board(entries, review / ('fold_modes_' + group + '_' + view + '.png'),
                  cols=3, cell=(340, 630), title=title + ' / ' + view)
    sidecar = dict(status='FAILED_DESIGN_INTENT', candidate='D03_CREASE_DRIFT',
                   reason='Angle change was used in every surface term: continuous-surface reparametrization, not a transported physical fold path.',
                   consequence='Only sampling and discrete CC differences; preserved without claiming successful directional change.',
                   successor='D05_CURVED_PATH separates material ridge/return values from physical direction.')
    for path in ('directional/D03_CREASE_DRIFT', 'input_field/D03_CREASE_DRIFT_FIELD'):
        (ROOT / path / 'assessment.json').write_text(json.dumps(sidecar, indent=2), encoding='utf8')
    paths = ['columns/NEAREST/G01', 'columns/NEAREST/G03',
             'columns/NEAREST/G03_CC_VIEW', 'variations/V24_TURN/G04']
    paths += ['directional/' + name + '/CC2' for _, name, _ in modes]
    paths += ['input_field/' + name + '/G02_CC' for name in
              ['CYLINDER_NO_FIELD', 'CYLINDER_FIELD', 'DIRECTIONAL_NO_FIELD',
               'DIRECTIONAL_FIELD', 'D04_DEEP_RETURN_FIELD', 'D05_CURVED_PATH_FIELD']]
    entries = []
    for relative in paths:
        folder = ROOT / relative
        item = dict(id=relative, checkpoint=str(folder / 'checkpoint.npz'),
                    mesh=str(folder / 'gate.ply'), geometry=str(folder / 'geometry.npz'),
                    generation_record=str(folder / 'generation.json'),
                    images={view: str(folder / 'preview' / (view + '.png'))
                            for view in ('front', 'oblique', 'side')})
        for file, key in [('gate.validation.json', 'core_check'), ('symmetry.json', 'symmetry')]:
            path = folder / file
            item[key] = json.loads(path.read_text(encoding='utf8')) if path.exists() else 'NOT_CHECKED'
        entries.append(item)
    index = dict(branch='experiment/iaac-mandelbrot-growth-20261011',
                 base_commit='66c6a3404ad042830709e7c923c7cd5d8464d07f',
                 code_directory=str(HERE), output_root=str(ROOT), selected_results=entries,
                 additional_catalogue=str(ROOT / 'variations/catalogue.json'),
                 failed_projection=str(ROOT / 'variations/V16_FULL/FAILED_G01/failure.json'),
                 failed_fold_direction=str(ROOT / 'directional/D03_CREASE_DRIFT/assessment.json'),
                 sources=str(HERE / 'SOURCES.md'),
                 physical_origami_constraints='NOT_ENFORCED', fabrication='NOT_CHECKED')
    (HERE / 'INDEX.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf8')
    for filename in ('INDEX.json', 'README.md', 'REPORT.md', 'SOURCES.md'):
        if (HERE / filename).exists(): shutil.copy2(HERE / filename, review / filename)
    print('Review package:', review, flush=True)


if __name__ == '__main__':
    main()
