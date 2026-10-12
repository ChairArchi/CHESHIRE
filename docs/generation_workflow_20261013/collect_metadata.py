"""Collect the selected CHESHIRE lineage; never load or generate mesh arrays.

Only small JSON receipts and source-code bytes are read. Original files are
untouched. The output is a new documentation snapshot, not a geometry runner.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E = Path('E:/CHESHIRE_DATA')
NODES = [
    ('seed_g0', 0, E/'fold_band_growth_20261011/inputs/SPAN_SPARSE/G00', 'seed', 0),
    ('ancestry_g1', 1, E/'fold_band_growth_20261011/ANCESTRY_STAGED/G01', 'task36_and_finite_field', 1),
    ('overlap_g2', 2, Path('C:/Users/USER/CHESHIRE/worktrees/fold-visible-gate-20261012/docs/fold_return_20261012/review_assets/OVERLAP_G02'), 'pchip_returns_task36_and_finite_field', 1),
    ('wall_g3', 3, Path('C:/Users/USER/CHESHIRE/worktrees/parent-guided-detail-20261012/docs/fold_visible_gate_20261012/review/WALL/SPAN/G03'), 'interpolating_split_and_measured_wall', 1),
    ('root_g3', 3, E/'experiments/connected_fold_growth_20261012/trial01/ROOT_ONLY/SPAN/G03_events', 'shared_boundary_root_event', 0),
    ('sidewall_g3', 3, E/'experiments/sidewall_fan_growth_20261013/trial01/SIDEWALL_FAN/SPAN/G03_events', 'shared_boundary_sidewall_events', 0),
    ('neutral_g4', 4, E/'experiments/sidewall_fan_growth_20261013/trial01/SIDEWALL_FAN/SPAN/G04', 'neutral_cc', 1),
    ('directional_g5', 5, E/'experiments/coherent_fold_detail_20261013/trial01/DIRECTIONAL/SPAN/G05', 'directional_cc', 1),
    ('depth08_g6', 6, E/'experiments/directional_g6_20261013/trial01/DEPTH_08/SPAN/G06', 'directional_cc', 1),
    ('middle_g6', 6, E/'experiments/whole_column_detail_20261013/trial01/MIDDLE/SPAN/G06', 'whole_normal_field', 0),
    ('middle_surface_g7', 7, E/'experiments/whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07', 'neutral_cc', 1),
    ('linked_raw_g7', 7, E/'experiments/parent_linked_folds_20261013/trial02/PARENT_LINKED/SPAN/G07', 'dependent_normal_fields', 0),
    ('linked_finished_g7', 7, E/'experiments/parent_linked_folds_20261013/trial03/PARENT_LINKED/SPAN/G07', 'saved_delta_filter', 0),
    ('wide_raw_g7', 7, E/'experiments/medium_root_folds_20261013/trial01/WIDE_ROOT/SPAN/G07', 'dependent_normal_fields_and_delta_filters', 0),
    ('wide_finished_g7', 7, E/'experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07', 'saved_delta_filter', 0),
]
# Each edge names the actual input field, rather than assuming top-level
# "source" is always the immediate parent. Finishes have two geometry inputs.
EDGES = [
    ('seed_g0', 'ancestry_g1', 'source', None, None),
    ('ancestry_g1', 'overlap_g2', 'source', None, None),
    ('overlap_g2', 'wall_g3', 'input.source', None, 'input.source_control_sha256'),
    ('wall_g3', 'root_g3', 'source', None, 'source_control_sha256'),
    ('root_g3', 'sidewall_g3', 'source', 'preserved_parent.generation_sha256', 'source_control_sha256'),
    ('sidewall_g3', 'neutral_g4', 'parent', 'parent_generation_sha256', None),
    ('neutral_g4', 'directional_g5', 'source', 'preserved_parent.generation_sha256', 'source_control_sha256'),
    ('directional_g5', 'depth08_g6', 'source', None, 'source_control_sha256'),
    ('depth08_g6', 'middle_g6', 'source', 'source_generation_json_sha256', 'source_control_sha256'),
    ('middle_g6', 'middle_surface_g7', 'parent_stage', 'parent_stage_generation_sha256', 'parent_stage_control_sha256'),
    ('middle_surface_g7', 'linked_raw_g7', 'source', 'source_generation_json_sha256', 'source_control_sha256'),
    ('middle_surface_g7', 'linked_finished_g7', 'parent_stage', 'parent_generation_json_sha256', 'parent_control_sha256'),
    ('linked_raw_g7', 'linked_finished_g7', 'raw_field_stage', 'raw_field_generation_json_sha256', 'raw_field_control_sha256'),
    ('linked_finished_g7', 'wide_raw_g7', 'source', 'source_generation_json_sha256', 'source_control_sha256'),
    ('linked_finished_g7', 'wide_finished_g7', 'parent_stage', 'parent_generation_json_sha256', 'parent_control_sha256'),
    ('wide_raw_g7', 'wide_finished_g7', 'raw_field_stage', 'raw_field_generation_json_sha256', 'raw_field_control_sha256'),
]
# Observed by the read-only ancestry audit on 2026-10-13. These historical
# receipts lack their own control-file hash. They are not retroactive bindings.
EARLY_OBSERVED = {
    'seed_g0': 'cff9089de50aac6019684829cd70303d77e3fceaaabf3f090a06636f4f6cbf55',
    'ancestry_g1': '866fbfcd5813b8f5a521a5a9fdb0a868f57146421db08db100272800247ff980',
    'overlap_g2': '8c46cbbf4edf8b5904a806d46f92e4968355e4e2f561607ecc977f273e09e62f',
    'wall_g3': '96577a663a14452f4b24cc4972a5b0126fd3af0ae6f89cdbe2056a8f294d9624',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def get(record, dotted):
    if not dotted:
        return None
    for key in dotted.split('.'):
        if not isinstance(record, dict) or key not in record:
            return None
        record = record[key]
    return record


def norm_folder(value):
    path = Path(value)
    return (path.parent if path.suffix else path).resolve()


def main():
    output = HERE/'LINEAGE.json'
    if output.exists():
        raise FileExistsError('Existing documentation snapshot is preserved.')
    records, nodes, code_checks = {}, [], {}
    for index, (node_id, generation, folder, operation, splits) in enumerate(NODES):
        path = folder/'generation.json'
        raw = path.read_bytes()
        data = json.loads(raw.decode('utf8'))
        records[node_id] = data
        snapshot = HERE/'receipts'/f'{index:02d}_{node_id}.json'
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if snapshot.exists():
            raise FileExistsError(snapshot)
        snapshot.write_bytes(raw)
        actual_g = data.get('subdivision_generation', data.get('subdivision_passes_total'))
        if actual_g is None and 'recipe' in data:
            actual_g = data['recipe'].get('output_generation')
        if actual_g is None and data.get('stage') == 'G00':
            actual_g = 0
        if actual_g != generation:
            raise ValueError('Receipt generation differs: '+node_id)
        for relative, expected in data.get('geometry_code_sha256', {}).items():
            relative = relative.replace('\\', '/')
            item = code_checks.setdefault(relative, dict(path=relative, expected_sha256=expected))
            if item['expected_sha256'] != expected:
                raise ValueError('Conflicting frozen code hash: '+relative)
        nodes.append(dict(id=node_id, generation=generation, operation=operation,
            subdivision_passes_added=splits, receipt=str(path), receipt_sha256=sha(path),
            receipt_snapshot=str(snapshot.relative_to(HERE)).replace('\\', '/'),
            control_file=str(folder/'control_quad.npz'),
            control_file_exists=(folder/'control_quad.npz').is_file(),
            recorded_control_sha256=data.get('control_file_sha256'),
            observed_early_control_sha256=EARLY_OBSERVED.get(node_id),
            control_vertices=data.get('control_vertices'), control_quads=data.get('control_quads'),
            generation_basis='Actual saved receipt; WALL uses recipe.output_generation.'))
    by_id = {item['id']: item for item in nodes}
    edges = []
    for parent_id, child_id, path_key, receipt_hash_key, control_hash_key in EDGES:
        parent, child = by_id[parent_id], records[child_id]
        declared_path = get(child, path_key)
        path_matches = norm_folder(declared_path) == Path(parent['receipt']).parent.resolve()
        expected_receipt, expected_control = get(child, receipt_hash_key), get(child, control_hash_key)
        own_control = parent['recorded_control_sha256'] or parent['observed_early_control_sha256']
        receipt_match = None if expected_receipt is None else expected_receipt == parent['receipt_sha256']
        control_match = None if expected_control is None else expected_control == own_control
        if not path_matches or receipt_match is False or control_match is False:
            raise ValueError('Metadata dependency mismatch: '+parent_id+' -> '+child_id)
        edges.append(dict(parent=parent_id, child=child_id, input_field=path_key,
            path_matches=path_matches, recorded_receipt_hash_field=receipt_hash_key,
            recorded_receipt_sha256=expected_receipt, receipt_hash_matches=receipt_match,
            recorded_control_hash_field=control_hash_key, recorded_control_sha256=expected_control,
            control_hash_matches_record_or_early_observation=control_match,
            historical_control_binding_present=expected_control is not None))
    for item in code_checks.values():
        item['observed_sha256'] = sha(REPO/item['path'])
        item['matches'] = item['observed_sha256'] == item['expected_sha256']
        if not item['matches']:
            raise ValueError('Frozen source differs: '+item['path'])
    result = dict(schema='CHESHIRE_SELECTED_WORKFLOW_DOCUMENTATION_V1',
        date='2026-10-13', timezone='Asia/Seoul', input_case='SPAN',
        basis_commit='657b3ab927d067630071a12fc14bd2b0a8d0681e',
        current_result='wide_finished_g7', generation_definition='Actual quad subdivision passes, including Task36 custom subdivision; not all passes are neutral Catmull-Clark.',
        scope='Documentation only. No geometry generation, new modeling formula, full replay, or native mesh check.',
        validation=dict(receipt_nodes=len(nodes), metadata_edges=len(edges),
            actual_subdivision_passes=sum(node['subdivision_passes_added'] for node in nodes),
            all_receipt_generations_match=True, all_dependency_metadata_checks_passed=True,
            frozen_code_files=len(code_checks), all_recorded_frozen_code_hashes_match=True,
            control_npz_rehashed_by_this_collector=False, mesh_arrays_loaded=False,
            initial_two_edges_lack_historical_parent_control_hashes=True),
        nodes=nodes, edges=edges, frozen_code_checks=list(code_checks.values()),
        exclusions=['Old ANCESTRY_STAGED G2/G3 continuation', 'BRANCHED cap descendants',
            'SIDEWALL_FAN neutral G5', 'COMBINED and ROLE_CURVATURE G5',
            'DEPTH_16', 'DESIGN_A G6', 'FINE and FINE_SURFACE', 'parent_linked trial01',
            'Old RELAXED_G06 Mandelbulb finish and gate branches'],
        unexecuted_hypotheses=['Optional G7 Mandelbulb surface finish; user discussion only, no generation or adoption.'])
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(result['validation'], ensure_ascii=True))


if __name__ == '__main__':
    main()
