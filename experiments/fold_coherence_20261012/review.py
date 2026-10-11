"""Collect saved receipts; reuse the core checker only on the two final meshes."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/fold_coherence_20261012')
DOC = HERE.parents[1]/'docs/fold_coherence_20261012'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', action='store_true')
    args = parser.parse_args()
    if args.core:
        spec = importlib.util.spec_from_file_location('preserved_column_core_checker',
            HERE.parent/'curved_fold_side_20261011/review.py')
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
    assets, summary, validations = {}, [], []
    for variant, stages in [('RESERVE', [3]), ('FLOW', [3, 4, 5])]:
        for case in ('SPAN', 'COUNTER'):
            for stage in stages:
                folder = ROOT/variant/case/f'G{stage:02}'
                meta = json.loads((folder/'generation.json').read_text(encoding='utf8'))
                key = f'{variant}_{case}_G{stage}'
                assets[key] = dict(folder=str(folder), mesh=str(folder/'column.ply'),
                    geometry=str(folder/'geometry.npz'), checkpoint=str(folder/'control_quad.npz'),
                    operation_fields=str(folder/'operation_fields.npz'),
                    generation_record=str(folder/'generation.json'),
                    views={v: str(folder/'preview'/f'{v}.png') for v in ('front', 'oblique', 'side')})
                if variant == 'FLOW' and stage == 5:
                    if args.core:
                        validations.append(checker.validate(folder))
                    elif (folder/'core_validation.json').exists():
                        validations.append(json.loads((folder/'core_validation.json').read_text(encoding='utf8')))
                keys = ('candidate', 'input_case', 'stage', 'parent', 'source_g2',
                    'physical_vertices', 'physical_triangles', 'subdivision_passes_total',
                    'field_passes_total', 'quick_integrity', 'maximum_return_step',
                    'maximum_placement_step', 'maximum_field_step', 'field_moved_controls',
                    'inherited_core_count', 'inherited_core_return_maximum', 'tag_core_count',
                    'tag_core_field_maximum', 'minimum_triangle_area', 'geometric_reflection_error',
                    'new_authored_events', 'task36_recipe', 'field_memory_rule')
                summary.append({k: meta[k] for k in keys})
    dump(DOC/'INDEX.json', dict(assets=assets, external_output_root=str(ROOT),
        original_commit='d57e679', branch='experiment/fold-coherence-20261012',
        code=str(HERE), scope='Two existing G2 inputs on their shared material chart; no arbitrary-mesh claim.'))
    dump(DOC/'technical/generation_summary.json', summary)
    if validations:
        dump(DOC/'technical/core_validation.json', validations)
    print('COLLECTED', len(assets), 'new saved stages; core records', len(validations), flush=True)


if __name__ == '__main__':
    main()
