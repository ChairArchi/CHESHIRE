"""Small public review package: approved renders, reports and check records only.

No PLY, OBJ, NPZ, BLEND, checkpoints or field grids are copied or uploaded.
No geometry changes or repeated mesh tests. Full originals remain local.
"""
from pathlib import Path
import hashlib, json, shutil
from review_boards import ROOT, board

HERE = Path(__file__).resolve().parent
DEST = HERE.parents[1] / 'docs' / 'iaac_mandelbrot_20261011'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8', newline='\n')


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    images = DEST / 'images'; images.mkdir(exist_ok=True)
    image_names = ['input_field_front', 'input_field_oblique', 'input_field_side',
                   'input_field_stages', 'fold_modes_geometry_front',
                   'fold_modes_geometry_oblique', 'fold_modes_geometry_side',
                   'fold_modes_field_front', 'fold_modes_field_oblique',
                   'fold_modes_field_side', 'fold_logic_oblique', 'catalogue_front',
                   'D02_INTERLEAVED_stages']
    for name in image_names:
        shutil.copy2(ROOT / 'review' / (name + '.png'), images / (name + '.png'))
    preferred = ROOT / 'input_field/DIRECTIONAL_FIELD/G02_CC'
    board([(view, preferred / 'preview' / (view + '.png'))
           for view in ('front', 'oblique', 'side')], images / 'preferred_three_views.png',
          cols=3, cell=(340, 630),
          title='D02 input + field G2 + CC / actual mesh / self-intersections confirmed')
    shutil.copy2(preferred / 'preview/front.png', images / 'preferred_front.png')
    shutil.copy2(HERE / 'SOURCES.md', DEST / 'SOURCES.md')
    report = (HERE / 'REPORT.md').read_text(encoding='utf8')
    report = report.replace('`review/', '`images/').replace('E 드라이브', '로컬 출력 저장소')
    (DEST / 'REPORT.md').write_text(report, encoding='utf8')
    selected = json.loads((HERE / 'INDEX.json').read_text(encoding='utf8'))['selected_results']
    checks = []
    for row in selected:
        core = row['core_check']
        if isinstance(core, dict):
            core = {k: v for k, v in core.items() if k not in ('path', 'elapsed_seconds')}
        checks.append(dict(artifact=row['id'], validation=core, symmetry=row['symmetry']))
    write_json(DEST / 'technical/validation_summary.json', dict(
        provenance='Existing saved checks, copied without rerunning geometry tests',
        actual_mesh_checks=checks, actual_mesh_payload_public=False,
        intersection_scope='CGAL detect_only=True first_only=True; nonzero witnesses are not an exhaustive count',
        unchecked='Other intermediate and catalogue meshes unless a saved check is listed',
        thickness_structure_fabrication='NOT_CHECKED'))
    shutil.copy2(preferred / 'preview/render_receipt.json', DEST / 'technical/render_receipt.json')
    shutil.copy2(ROOT / 'variations/catalogue.json', DEST / 'technical/catalogue_parameters.json')
    write_json(DEST / 'technical/failed_trials.json', dict(
        D03=json.loads((ROOT / 'directional/D03_CREASE_DRIFT/assessment.json').read_text()),
        V16=json.loads((ROOT / 'variations/V16_FULL/FAILED_G01/failure.json').read_text()),
        uniform_pleats=dict(ids='F01-F06', status='DESIGN_DIRECTION_STOPPED',
                           reason='Uniform directional folding does not match the observed direction-dependent reference logic',
                           intersection_status='NOT_CHECKED')))
    manifest = dict(
        branch='experiment/iaac-mandelbrot-growth-20261011',
        source_commit='45f3541', source_directory='experiments/iaac_mandelbrot_20261011',
        preferred_artifact='input_field/DIRECTIONAL_FIELD/G02_CC',
        disclosure='Modelled sectional/axial mass deformation + Mandelbulb attraction + CC, NOT crease-driven folding or recovered IAAC implementation',
        geometry_payloads_public=False,
        original_outputs='Preserved locally; no original mesh, checkpoint, BLEND or field-grid payload is included',
        files=[])
    allowed = [DEST / (name + '.md') for name in ('README', 'FOR_GPT', 'REPORT', 'SOURCES')]
    allowed += [images / (name + '.png') for name in image_names + ['preferred_three_views', 'preferred_front']]
    allowed += [DEST / 'technical' / (name + '.json') for name in
                ('validation_summary', 'render_receipt', 'catalogue_parameters', 'failed_trials')]
    for path in allowed:
        data = path.read_bytes()
        if path.suffix in ('.md', '.json'):
            # Match the LF text bytes Git publishes, not Windows checkout endings.
            data = data.replace(b'\r\n', b'\n')
            path.write_bytes(data)
        manifest['files'].append(dict(path=path.relative_to(DEST).as_posix(),
                                      bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    manifest['package_bytes_excluding_manifest'] = sum(row['bytes'] for row in manifest['files'])
    write_json(DEST / 'MANIFEST.json', manifest)
    print(json.dumps(dict(directory=str(DEST), files=len(manifest['files']),
                          bytes=manifest['package_bytes_excluding_manifest']), ensure_ascii=False))


if __name__ == '__main__':
    main()
