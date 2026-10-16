"""Audited whole-column distribution on the exact liked native hybrid."""
from pathlib import Path
import argparse
import json
import shutil
import time
from assemble_structural_tissue_20261016 import main as assemble, SOURCE
from cheshire.ornament_assembly import record


def main(patch_index, qa_index, selection, output, visual_prototype=False):
    started = time.perf_counter()
    patches = json.loads(patch_index.read_text(encoding='utf-8-sig'))
    qa = json.loads(qa_index.read_text(encoding='utf-8-sig'))
    intersections_passed = bool(qa.get('all_new_geometry_proper_self_and_outside_passed'))
    if not intersections_passed and not visual_prototype:
        raise ValueError('Self, outside-native, and inter-patch QA must pass before assembly.')
    if qa['patch_index'] != record(patch_index):
        raise ValueError('QA belongs to a different patch index.')
    if len(qa['patches']) != len(patches['patches']):
        raise ValueError('Audited patch count differs.')
    for patch, audit in zip(patches['patches'], qa['patches']):
        if record(patch['path']) != audit['patch'] or (not visual_prototype and not audit['passed']):
            raise ValueError('An actual patch changed after QA.')
    selection_binding = record(selection)
    assemble(patch_index, output)
    receipt_path = output/'SYNTHESIS_RECEIPT.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    # Retain the native structural assembly kind understood by the exact export
    # and rendering tools. Scope and proof are recorded explicitly below.
    snapshot = output/'source_snapshot'/Path(__file__).name
    shutil.copyfile(__file__, snapshot)
    base_faces = receipt['assembly']['counts']['base_triangles']
    removed = receipt['assembly']['counts']['removed_native_triangles']
    receipt.update(scope='WHOLE_COLUMN_DISTRIBUTED_FULLXYZ_STRUCTURAL_TISSUE',
        distributed_patch_count=len(patches['patches']),
        removed_native_face_fraction=removed/base_faces,
        selection=selection_binding, geometry_review_index=record(qa_index),
        visual_prototype=bool(visual_prototype),
        all_new_geometry_intersections_resolved=intersections_passed,
        proper_new_patch_self_intersections=0 if intersections_passed else None,
        proper_new_to_surviving_native_intersections=0 if intersections_passed else None,
        proper_inter_patch_intersections=0 if intersections_passed else None,
        new_geometry_proper_crossing_decomposition_checked=intersections_passed,
        intersection_observations=qa.get('intersection_observations'),
        original_unchanged_carrier_self_intersections_not_certified=True,
        baseline_bindings=SOURCE,
        whole_distribution_wrapper=record(snapshot),
        whole_distribution_elapsed_seconds=time.perf_counter()-started)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('WHOLE_DISTRIBUTION_ASSEMBLED', len(patches['patches']), removed/base_faces, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--patch-index', type=Path, required=True)
    p.add_argument('--qa-index', type=Path, required=True)
    p.add_argument('--selection', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--visual-prototype', action='store_true')
    a = p.parse_args()
    main(a.patch_index, a.qa_index, a.selection, a.out, a.visual_prototype)
