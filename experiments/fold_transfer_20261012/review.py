"""Core checks on the two selected G4 meshes; compact records, no sweep."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
DOC = HERE.parents[1]/'docs/fold_transfer_20261012'


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


def collect(validate=False):
    DOC.mkdir(parents=True, exist_ok=True)
    technical = DOC/'technical'
    technical.mkdir(exist_ok=True)
    folders = {
        'SPAN_G0': ROOT/'inputs/SPAN/G00',
        'COUNTER_G0': ROOT/'inputs/COUNTER/G00',
        'SPAN_G3': Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03'),
        'COUNTER_G3': ROOT/'COUNTER/G03',
    }
    for case, label in [('SPAN', 'SPAN'), ('COUNTER', 'COUNTER_MATCHED')]:
        for variant in ('RETURN_ONLY', 'UNPROTECTED', 'PROTECTED'):
            folders[f'{case}_{variant}_G4'] = ROOT/label/variant/'G04'
    summaries = {}
    keys = ['input_source', 'parent', 'physical_vertices', 'physical_triangles',
        'subdivision_passes_total', 'field_passes_total', 'quick_integrity',
        'minimum_triangle_area', 'geometric_reflection_error', 'watertight',
        'winding_consistent', 'components', 'inherited_core_count',
        'inherited_core_return_maximum', 'fully_protected_feature_count',
        'raw_field_moved_core', 'applied_field_moved_core',
        'old_controls_field_maximum', 'maximum_return_step',
        'raw_field_moved_controls', 'applied_field_moved_controls',
        'self_intersection', 'fabrication_thickness_structure']
    index = {}
    for name, path in folders.items():
        meta = json.loads((path/'generation.json').read_text(encoding='utf8'))
        summaries[name] = {k: meta[k] for k in keys if k in meta}
        if (path/'core_validation.json').exists():
            existing_core = json.loads((path/'core_validation.json').read_text(encoding='utf8'))
            summaries[name]['self_intersection'] = existing_core['self_intersection']
            summaries[name]['core_validation'] = str(path/'core_validation.json')
        index[name] = dict(folder=str(path), geometry=str(path/'geometry.npz'),
            mesh=str(path/'column.ply'), checkpoint=str(path/'control_quad.npz'),
            generation_record=str(path/'generation.json'),
            views={v: str(path/'preview'/(v+'.png')) for v in ('front', 'oblique', 'side')})
    selected = [folders['SPAN_RETURN_ONLY_G4'], folders['COUNTER_RETURN_ONLY_G4']]
    if validate:
        spec = importlib.util.spec_from_file_location('existing_core_review', HERE.parent/'curved_fold_side_20261011/review.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        validations = [core.validate(folder) for folder in selected]
        dump(technical/'core_validation.json', validations)
    else:
        validations = json.loads((technical/'core_validation.json').read_text(encoding='utf8')) if (technical/'core_validation.json').exists() else []
    for result in validations:
        for name, entry in index.items():
            if Path(entry['folder']) == Path(result['folder']):
                summaries[name]['self_intersection'] = result['self_intersection']
                summaries[name]['core_validation'] = str(Path(result['folder'])/'core_validation.json')
    dump(technical/'generation_summary.json', summaries)
    transfer = HERE/'transfer_check.json'
    if transfer.exists():
        shutil.copy2(transfer, technical/transfer.name)
    dump(DOC/'INDEX.json', dict(output_root=str(ROOT), branch='experiment/fold-transfer-20261012',
        source_parent_commit='442d641', assets=index,
        preserved_diagnostic=str(ROOT/'COUNTER'),
        diagnostic_note='Initial COUNTER G4 used carried G2 tags while SPAN freshly registered G3 tags. Invalid as strict matched transfer; retained without overwrite. COUNTER_MATCHED corrects only initialization, with the same recipe.',
        selected=[str(p) for p in selected], G5_generated=False,
        limits=['Two actual G0 masses on one shared 25-ring/16-sector chart/topology, H10 reference units',
            'No arbitrary-mesh or gate transfer demonstrated', 'No physical origami or dihedral locking',
            'Thickness, structure and fabrication unverified'],
        original_operators_modified=False, large_artifacts_in_git=False))
    print('REVIEW_RECORDS', DOC, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate', action='store_true')
    collect(p.parse_args().validate)
