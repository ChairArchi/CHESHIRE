"""Read-only saved coffer foundation and static source-correspondence review."""
from pathlib import Path
import argparse
import ast
import json

import numpy as np


REPO = Path(__file__).resolve().parents[2]
HERE = REPO/'experiments/hansmeyer_reconstruction_20261015'


def leaves(item, path=()):
    if isinstance(item, dict) and 'npz_key' in item:
        return {path:item}
    if isinstance(item, dict):
        result = {}
        for key, value in item.items(): result.update(leaves(value, path+(key,)))
        return result
    if isinstance(item, list):
        result = {}
        for index, value in enumerate(item): result.update(leaves(value, path+(str(index),)))
        return result
    return {}


def function_ast(path, name):
    tree = ast.parse(path.read_text(encoding='utf8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
        node.body.pop(0)
    return ast.dump(node, include_attributes=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('New-only audit output.')
    preflight = json.loads((args.root/'PREFLIGHT.json').read_text(encoding='utf8'))
    cached = []
    for info in preflight['selected']:
        if not info.get('reused_source_domain'): continue
        new = json.loads(Path(info['evidence']['description']).read_text(encoding='utf8'))
        old = json.loads(Path(info['predecessor_evidence']['description']).read_text(encoding='utf8'))
        new_foundation = leaves(new['tree']['foundation'])
        old_foundation = leaves(old['tree']['foundation'])
        if new_foundation.keys() != old_foundation.keys():
            raise ValueError('Reused cached foundation array paths changed.')
        comparisons = []
        with np.load(new['array_file'], allow_pickle=False) as zn, np.load(old['array_file'], allow_pickle=False) as zo:
            for path in new_foundation:
                a = zn[new_foundation[path]['npz_key']]
                b = zo[old_foundation[path]['npz_key']]
                same = a.dtype == b.dtype and np.array_equal(a, b)
                comparisons.append(dict(scope='foundation', path='/'.join(path), exact_array_equal=same, shape=list(a.shape)))
            for key in ('xyz0','source_chart0','parent_width','actual_parent_depth','node_height',
                        'raw_parent_width','raw_parent_depth','requested_base_width','usable_base_width',
                        'logical_chi','logical_s','node_envelope','cell_count','neutral_refined',
                        'quads_refined','source_chart_refined','logical_refined','activity_refined',
                        'source_uv_refined','source_chart_transfer'):
                an, ao = new['tree']['formation'][key], old['tree']['formation'][key]
                a, b = zn[an['npz_key']], zo[ao['npz_key']]
                same = a.dtype == b.dtype and np.array_equal(a, b)
                comparisons.append(dict(scope='formation_invariant', path=key, exact_array_equal=same, shape=list(a.shape)))
            formation = new['tree']['formation']
            formed = zn[formation['formed_refined']['npz_key']]
            neutral = zn[formation['neutral_refined']['npz_key']]
            delta = zn[formation['delta_refined']['npz_key']]
            subtraction_equal = np.array_equal(formed-neutral, delta)
        if not all(c['exact_array_equal'] for c in comparisons) or not subtraction_equal:
            raise ValueError('A source, neutral, topology or phase invariant changed in reused parent.')
        cached.append(dict(component=info['component'], exact_array_comparisons=comparisons,
            formed_minus_neutral_exact_delta=subtraction_equal, local_section_gate_passed=info['local_section_gate']['passed']))
    static = {name:function_ast(HERE/'recursive_spine_operator.py', name)==function_ast(HERE/'recursive_spine_operator_v2.py', name)
              for name in ('quintic','unit','incident','topology','coupled')}
    if not all(static.values()): raise ValueError('Coffer revision changed a shared forming/correspondence helper.')
    report = dict(kind='COFFER_REUSED_SOURCE_AND_FORMING_CORRESPONDENCE_REVIEW', root=str(args.root),
        preflight_passed=preflight['passed'], requested_canonical_orbits=preflight['requested_canonical_orbits'],
        selected_components=[i['component'] for i in preflight['selected']], rejected=preflight['rejected'],
        shared_operator_helper_AST_equal=static, reused_parents=cached,
        reviewed_invariants=[
            'Cached reconstruction uses immutable original registered source_curve frame, and copies tangent before its normal projection.',
            'Source XYZ/chart, physical guide measures, usable-width/height budgets, longitudinal phase, neutral refined geometry, topology, activity and affine source transfer are unchanged for reused parents.',
            'New caller requires exact refined source topology/chart equality before reusing certified source UV.',
            'New families use the existing covered-source curve solver and affine source-coordinate partition; local UV Jacobians and per-parent coarse positive-area overlaps are checked.',
            'G7 transfer uses exact saved material chart and actual mirror vertex maps. Distinct-family support conflicts are checked at all eligible actual G7 representative controls, before export.',
            'Full native geometry is arithmetic-fan conversion of the final saved G7 control geometry.'
        ],
        qualifications=[
            'Per-parent source-UV nonoverlap is numerical, and is not a 3D collision certificate.',
            'The inter-family conflict gate tests all actual G7 controls, not a separate continuous union-atlas overlap theorem.',
            'Same-family reflected footprints use maximum support taper. Exact output symmetry does not independently certify a visually smooth internal reflection join.',
            'The local section gate is a fitted forming-frame structural test over adequately tall core samples; it does not certify each individual pocket depth, collision freedom or beauty.',
            'This audit reads already-saved arrays and code. No formation, new surface measurement, parameter test, geometry output, ray or image is generated.'
        ])
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(dict(output=str(args.output), selected=report['selected_components'],
        reused_exact=[dict(component=p['component'], comparisons=len(p['exact_array_comparisons'])) for p in cached],
        shared_operator_helpers=static), indent=2))


if __name__ == '__main__': main()
