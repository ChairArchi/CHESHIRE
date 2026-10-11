"""Compact G5 receipts and selected core validation, without regression sweeps."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
DOC = HERE.parents[1]/'docs/fold_transfer_20261012'


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


def main(validate=False, validate_tag_only=False):
    keys = ['parent', 'input_source', 'physical_vertices', 'physical_triangles',
        'subdivision_passes_total', 'field_passes_total', 'added_field_passes',
        'quick_integrity', 'watertight', 'components', 'minimum_triangle_area',
        'geometric_reflection_error', 'inherited_core_count', 'inherited_core_return_maximum',
        'maximum_return_step', 'fully_protected_feature_count', 'raw_field_moved_core',
        'applied_field_moved_core', 'old_controls_field_maximum', 'raw_field_moved_controls',
        'applied_field_moved_controls', 'raw_field_maximum', 'applied_field_maximum',
        'self_intersection', 'fabrication_thickness_structure', 'operation',
        'task36_recipe', 'activation_profile', 'maximum_stencil_step',
        'active_controls', 'inherited_core_displacement_maximum',
        'old_controls_displacement_maximum', 'new_authored_events',
        'original_g4_parent', 'same_pre_field_and_raw_field_source',
        'blanket_old_control_pin', 'old_control_count', 'old_controls_field_moved',
        'tag_core_field_maximum', 'newborn_applied_difference_from_protected_maximum',
        'feature_memory_scope', 'reused_g5_authored_events']
    assets, summaries = {}, {}
    for case in ('SPAN', 'COUNTER'):
        variants = ('REFINED_ONLY', 'RETURN_ONLY', 'PROTECTED') if case == 'SPAN' else ('RETURN_ONLY', 'PROTECTED')
        for variant in variants:
            folder = ROOT/(case+'_G5_FROM_RETURN')/variant/'G05'
            name = case+'_'+variant+'_G5'
            meta = json.loads((folder/'generation.json').read_text(encoding='utf8'))
            summaries[name] = {k: meta[k] for k in keys if k in meta}
            assets[name] = dict(folder=str(folder), geometry=str(folder/'geometry.npz'),
                mesh=str(folder/'column.ply'), checkpoint=str(folder/'control_quad.npz'),
                generation_record=str(folder/'generation.json'),
                views={v: str(folder/'preview'/(v+'.png')) for v in ('front', 'oblique', 'side')})
    for case in ('SPAN', 'COUNTER'):
        folder = ROOT/(case+'_G5_STENCIL')/'G05'
        name = case+'_STENCIL_G5'
        meta = json.loads((folder/'generation.json').read_text(encoding='utf8'))
        summaries[name] = {k: meta[k] for k in keys if k in meta}
        summaries[name].update(self_intersection='NOT_CHECKED_INTERMEDIATE',
            validation_scope='Saved quick integrity only; no additional core or self-intersection validation performed')
        assets[name] = dict(folder=str(folder), geometry=str(folder/'geometry.npz'),
            mesh=str(folder/'column.ply'), checkpoint=str(folder/'control_quad.npz'),
            generation_record=str(folder/'generation.json'),
            views={v: str(folder/'preview'/(v+'.png')) for v in ('front', 'oblique', 'side')})
    for case in ('SPAN', 'COUNTER'):
        folder = ROOT/(case+'_G5_TAG_ONLY')/'G05'
        name = case+'_TAG_ONLY_G5'
        meta = json.loads((folder/'generation.json').read_text(encoding='utf8'))
        summaries[name] = {k: meta[k] for k in keys if k in meta}
        assets[name] = dict(folder=str(folder), geometry=str(folder/'geometry.npz'),
            mesh=str(folder/'column.ply'), checkpoint=str(folder/'control_quad.npz'),
            generation_record=str(folder/'generation.json'),
            views={v: str(folder/'preview'/(v+'.png')) for v in ('front', 'oblique', 'side')})
    if validate:
        spec = importlib.util.spec_from_file_location('existing_g5_core', HERE.parent/'curved_fold_side_20261011/review.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        results = [core.validate(Path(assets[case+'_PROTECTED_G5']['folder'])) for case in ('SPAN', 'COUNTER')]
        dump(DOC/'technical/g5_core_validation.json', results)
    if validate_tag_only:
        spec = importlib.util.spec_from_file_location('existing_tag_only_core', HERE.parent/'curved_fold_side_20261011/review.py')
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        results = [core.validate(Path(assets[case+'_TAG_ONLY_G5']['folder'])) for case in ('SPAN', 'COUNTER')]
        dump(DOC/'technical/g5_tag_only_core_validation.json', results)
    for name, asset in assets.items():
        if name.endswith('_STENCIL_G5'):
            continue
        path = Path(asset['folder'])/'core_validation.json'
        if path.exists():
            result = json.loads(path.read_text(encoding='utf8'))
            summaries[name]['self_intersection'] = result['self_intersection']
            summaries[name]['core_validation'] = str(path)
    dump(DOC/'technical/g5_summary.json', summaries)
    dump(DOC/'G5_INDEX.json', dict(assets=assets, source_commit='1d8673f',
        starting_variant='RETURN_ONLY G4 on both actual inputs; not the visually weaker protected-field G4',
        recurrence='Same G5 rule on both inputs, no input-specific tuning',
        resolution_control='SPAN inactive VF refinement only; no new geometric displacement',
        field_passes='G4 source has three; G5 RETURN_ONLY has three; G5 PROTECTED has four',
        stencil_field_passes='G5 STENCIL starts from RETURN_ONLY G4 and retains its three field passes; it adds no field or authored G5 return',
        stencil_validation='Quick integrity PASS in saved generation records; self-intersection NOT_CHECKED_INTERMEDIATE; --validate still selects only SPAN/COUNTER PROTECTED',
        pin_ablation='TAG_ONLY reuses the exact saved G5 pre-field controls, raw field samples, tags and topology; removes only blanket inherited-control pinning. Field passes remain four; no new field query or subdivision.',
        images={name: 'images/'+name+'.png' for name in (
            'g5_progression', 'g5_views', 'g5_detail', 'g5_stencil_comparison',
            'g5_stencil_fronts', 'g5_fold_lineage', 'g5_pin_comparison', 'g5_tag_only_views')},
        comparisons=dict(
            PROTECTED_vs_TAG_ONLY=dict(cases=['SPAN', 'COUNTER'],
                changed_rule='Only blanket inherited-control pin removed; scalar tag weights remain on both old and new controls',
                source_arrays='Same saved pre_field_xyz and raw_field_displacement; newborn applied vectors unchanged',
                single_variable_ablation=True),
            REFINED_ONLY_vs_STENCIL=dict(available_cases=['SPAN'],
                reference='SPAN_REFINED_ONLY_G5', candidate='SPAN_STENCIL_G5',
                scope='Same RETURN_ONLY G4 input and VF split; STENCIL adds regional ancestry-stencil displacement. Neither branch adds a G5 authored return or field pass.',
                isolated_stencil_comparison=True),
            FIELD_vs_STENCIL=dict(cases=['SPAN', 'COUNTER'],
                field_variant='PROTECTED', stencil_variant='STENCIL',
                scope='PROTECTED adds derived G5 authored return events and a protected finite field pass; STENCIL adds regional ancestry stencils with no G5 return or field. Both operator and return-event content differ.',
                single_variable_ablation=False)),
        smoothing=False, G6_generated=False,
        execution_events=[dict(attempt=1, result='Inactive SPAN refinement saved; subsequent field call failed before final output',
            cause='Importing the transfer file as study occupied the legacy fractal study module name: AttributeError ArtifactRoot',
            resolution='Load transfer driver under a distinct module name; preserve and reuse the already saved resolution control',
            geometry_parameters_changed=False),
            dict(attempt=2, result='Two actual G5 continuations generated with the original shared recipe; pre-field states saved separately')]))
    print('G5_RECORDS', DOC, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate', action='store_true')
    p.add_argument('--validate-tag-only', action='store_true')
    args = p.parse_args()
    main(args.validate, args.validate_tag_only)
