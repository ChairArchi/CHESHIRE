"""Inventory saved LATE/CURVED/RULED development and diagnosis receipts only.

No mesh loading, generation, hash audit or geometric validation is performed.
Re-run after a selected stage finishes to collect its existing records.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json


HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/fold_coherence_20261012')
DEFAULT_OUTPUT = HERE.parents[1]/'docs/fold_coherence_20261012/DEVELOPMENT_INDEX.json'
COUNTS = ('physical_vertices', 'physical_triangles', 'control_vertices', 'control_quads')
QUICK = ('quick_integrity', 'finite', 'components', 'watertight', 'winding_consistent',
         'minimum_triangle_area', 'minimum_area_threshold', 'geometric_reflection_error',
         'reflected_triangle_sets_identical')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def files(folder):
    expected = dict(mesh='column.ply', geometry='geometry.npz',
                    checkpoint='checkpoint.npz', control='control_quad.npz',
                    operation_fields='operation_fields.npz', blend='column.blend',
                    generation_record='generation.json', recipe_record='recipe.json')
    result = {key: str(folder/name) for key, name in expected.items()
              if (folder/name).is_file()}
    result['code_snapshots'] = [str(p) for p in sorted(folder.glob('*.py'))]
    result['views'] = {view: str(folder/'preview'/f'{view}.png')
                       for view in ('front', 'oblique', 'side')
                       if (folder/'preview'/f'{view}.png').is_file()}
    result['detail_views'] = [str(p) for p in sorted((folder/'detail').glob('*.png'))]
    result['render_receipts'] = [str(p) for p in (
        folder/'preview/render_receipt.json', folder/'detail/render_receipt.json')
        if p.is_file()]
    return result


def field_count(record):
    """Read recorded cumulative passes; interpret the saved G2 operation slices."""
    if 'field_passes_total' in record:
        return record['field_passes_total'], 'generation.json field_passes_total'
    if record.get('candidate') in ('INTERPOLATED', 'TASK36_ONLY', 'WITH_FIELD'):
        source = Path(record['source'])/'generation.json'
        total = read(source).get('field_passes_total')
        if total is not None:
            omitted = int(record['candidate'] != 'WITH_FIELD')
            return total-omitted, ('Source G2 receipt minus its final field pass for '
                                   'pre-field slices; snapshot_probe.py operation order')
    return None, 'Not recorded; not inferred from visual complexity or G number'


def collect(folder, root, recipes):
    d = read(folder/'generation.json')
    family = folder.relative_to(root).parts[0]
    recipe = (d.get('late_activation_recipe') if family == 'LATE' else
              d.get('curved_activation_recipe') if family == 'CURVED' else
              d.get('composition_recipe') if family == 'RULED' or
              d.get('candidate') == 'CURVED_PREFIELD' else None)
    recipe_key = recipe.get('name') if recipe else None
    if recipe_key:
        recipes[recipe_key] = recipe
    passes, pass_source = field_count(d)
    core_path = folder/'core_validation.json'
    core = read(core_path) if core_path.is_file() else {}
    si = core.get('self_intersection', d.get('self_intersection', 'NOT_RECORDED'))
    field = d.get('field') or {}
    entry = dict(folder=str(folder), family=family, candidate=d.get('candidate'),
                 case=d.get('input_case'), stage=d.get('stage'), files=files(folder),
                 source=d.get('source'), parent=d.get('parent'), source_g0=d.get('source_g0'),
                 counts={key: d.get(key) for key in COUNTS},
                 counts_source='Existing generation.json from saved actual mesh; not recomputed',
                 subdivision_passes_total=d.get('subdivision_passes_total'),
                 new_subdivision_passes=d.get('new_subdivision_passes', 1),
                 field_passes_total=passes, field_passes_source=pass_source,
                 added_field_passes=d.get('added_field_passes', 0),
                 new_field_queries=d.get('new_field_queries'),
                 current_field_escape_iterations=field.get('field_iterations'),
                 active_placement=d.get('active_placement'),
                 field_enabled=d.get('field_enabled'),
                 task36_recipe=d.get('task36_recipe'), surface_policy=d.get('surface'),
                 authoritative_recipe=recipe_key,
                 quick_checks={key: d.get(key) for key in QUICK},
                 quick_checks_source=str(folder/'generation.json'),
                 self_intersection=si,
                 self_intersection_source=str(core_path if core else folder/'generation.json'),
                 intersection_scope=core.get('intersection_scope'),
                 fabrication_thickness_structure=core.get('fabrication_thickness_structure',
                     d.get('fabrication_thickness_structure', 'NOT_CHECKED')),
                 operation=d.get('operation'),
                 new_authored_event_count=len(d.get('new_authored_events', [])),
                 inherited_event_bank_count=len(d.get('event_bank', [])))
    if family == 'LATE':
        entry['recipe_scope_note'] = (
            'late_activation_recipe is authoritative for this G0-based schedule. '
            'The receipt generic composition_recipe is inherited study helper CFG; '
            'only its child/tag/profile settings apply, not its G2 scope or gain schedule.')
    elif family == 'CURVED':
        entry['recipe_scope_note'] = (
            'curved_activation_recipe / composition_recipe describe the actual G0 schedule: '
            'existing Task36 CC averaging and vertex-memory schedule, returns and capped field. '
            'CC is not a separate geometric smoothing pass.')
    elif family == 'RULED':
        entry['recipe_scope_note'] = (
            'Starts at actual CURVED/SPAN/G02 (zero field passes, two original returns). '
            'Repeats one fixed existing Task36 kernel at G3 onward; no child returns or field. '
            'Different gains and return schedule from CURVED, not a single-variable field ablation.')
    elif d.get('candidate') == 'CURVED_PREFIELD':
        entry['recipe_scope_note'] = (
            'Actual CURVED recipe inherited from its source. This slice omits only the '
            'current field pass; earlier generations retain their field responses. '
            'Materializing the slice adds no refinement, authored return or field query.')
    else:
        entry['recipe_scope_note'] = (
            'Saved causal operation slice, not a new design generation. Generic study CFG '
            'does not establish its field history; follow the source and slice operation.')
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--max-stage', type=int, default=6)
    args = parser.parse_args()
    folders = []
    for family in ('LATE', 'CURVED', 'RULED'):
        folders += [p.parent for p in sorted((args.root/family/'SPAN').glob('G*/generation.json'))
                    if int(p.parent.name[1:]) <= args.max_stage]
    folders += [p.parent for p in sorted((args.root/'DIAGNOSIS').rglob('generation.json'))
                if int(p.parent.name[1:]) <= args.max_stage]
    recipes = {}
    assets = {p.relative_to(args.root).as_posix(): collect(p, args.root, recipes) for p in folders}
    result = dict(schema='cheshire_saved_development_inventory_v1',
                  collected_utc=datetime.now(timezone.utc).isoformat(),
                  external_output_root=str(args.root), collector=str(Path(__file__).resolve()),
                  scope='Existing LATE/SPAN, CURVED/SPAN, RULED/SPAN and DIAGNOSIS receipts only',
                  collection_policy='Read existing JSON and path presence only. No mesh checks, '
                      'hashes, new generation, receipt edits or original code changes.',
                  iteration_note='G labels count subdivision passes. Field pass counts are separate; '
                      'escape iterations are classifier iterations within a field evaluation.',
                  recipes=recipes, assets=assets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    print(json.dumps(dict(output=str(args.output), assets=len(assets),
                         stages=list(assets)), ensure_ascii=True))


if __name__ == '__main__':
    main()
