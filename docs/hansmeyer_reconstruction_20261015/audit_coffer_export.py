"""Cheap read-only full-control/source-chart and sparse differential audit.

No native triangle archive, orientation scan, new measurement, ray, model,
render or large-file hash is produced.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
from audit_spine_controls import registered_anchor, quantile, get_array, RAYS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError('New-only audit output.')
    rp = args.root/'RECEIPT.json'
    receipt = json.loads(rp.read_text(encoding='utf8'))
    variants = receipt['variants']
    with np.load(variants['REFERENCE_NESTED']['control_quad'], allow_pickle=False) as z:
        base, q, chart = z['xyz'], z['faces'], z['chart']
    with np.load(variants['SPINE']['control_quad'], allow_pickle=False) as z:
        out, qc, cc = z['xyz'], z['faces'], z['chart']
    if not np.array_equal(q, qc) or not np.array_equal(chart, cc):
        raise ValueError('Saved exported topology or source chart differs from accepted baseline.')
    del qc, cc, chart
    lengths = np.linalg.norm(out-base, axis=1)
    exact = np.any(out != base, axis=1)
    meaningful = lengths > 1e-12
    with np.load(args.root/'SPARSE_DELTA.npz', allow_pickle=False) as z:
        ids, delta = z['ids'], z['delta']
    if not np.array_equal(ids, np.flatnonzero(meaningful)):
        raise ValueError('Sparse listed IDs differ from exported meaningful changes.')
    if not np.array_equal(out[ids], base[ids]+delta):
        raise ValueError('Sparse listed differential plus baseline differs from saved export.')
    tiny = exact&~meaningful
    source_rays = json.loads(RAYS.read_text(encoding='utf8'))
    anchors = [registered_anchor(base, out, q, hit['G6_quad_id'], hit['native_fan_corner'], hit['barycentric'],
        dict(label=f'prior_visible_source_sample_{i:02}', previous_normalized_image_xy=hit['normalized_image_xy'],
             original_G6_hit_xyz=hit['hit_xyz'], source_phase=hit['phase'])) for i, hit in enumerate(source_rays['rays'])]
    for pi, info in enumerate(receipt['foundation']):
        saved = json.loads(Path(info['evidence']['description']).read_text(encoding='utf8'))
        tree = saved['tree']['foundation']['measurement']
        with np.load(saved['array_file'], allow_pickle=False) as z:
            s = get_array(z, tree, 's')
            tris = get_array(z, tree, 'triangle_ids')
            bary = get_array(z, tree, 'barycentric')
            valid = get_array(z, tree, 'valid')
            peak = get_array(z, tree, 'geometric_peak_index')
            shoulder = get_array(z, tree, 'shoulder_indices')
        for fraction in (.25, .5, .75):
            row = int(np.argmin(np.abs(s-(s[0]+fraction*(s[-1]-s[0])))))
            choices = [('existing_measured_peak', int(peak[row])),
                ('existing_measured_left_shoulder', int(shoulder[row, 0])),
                ('existing_measured_right_shoulder', int(shoulder[row, 1])),
                ('flanking_profile_left_endpoint', 0), ('flanking_profile_right_endpoint', tris.shape[1]-1)]
            for role, col in choices:
                if col<0 or col>=tris.shape[1] or not valid[row,col]: continue
                tid = int(tris[row,col])
                anchors.append(registered_anchor(base, out, q, tid//4, tid%4, bary[row,col],
                    dict(label=f'parent_{pi:02}_{fraction:.2f}_{role}', parent_component=info['component'],
                        parent_profile_row=row, recorded_profile_column=col, physical_arc_fraction=fraction,
                        physical_arc_s=float(s[row]), description=info['evidence']['description'])))
    report = dict(kind='COFFER_EXPORT_EXACT_CONTROL_SOURCE_AND_SPARSE_DIFFERENTIAL_AUDIT',
        root=str(args.root), receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),
        controls=len(base), quads=len(q), exact_topology_equal=True, exact_source_chart_equal=True,
        sparse_listed_ids_equal_exported_meaningful_ids=True,
        saved_sparse_differential_plus_baseline_equal_export_at_listed_ids=True,
        exact_changed_controls=int(exact.sum()), meaningful_changed_controls=int(meaningful.sum()),
        exact_untouched_controls=int((~exact).sum()),
        tiny_changed_controls_omitted_from_sparse=int(tiny.sum()),
        maximum_unlisted_tiny_displacement=float(lengths[tiny].max()) if tiny.any() else 0.,
        meaningful_control_displacements=quantile(lengths[meaningful]),
        selected_components=[info['component'] for info in receipt['foundation']],
        section_gates_passed=[info['local_section_gate']['passed'] for info in receipt['foundation']],
        source_anchors=anchors, source_anchor_displacements=quantile([a['displacement_length'] for a in anchors]),
        prior_close_anchor_changed_count=sum(a['displacement_length']>1e-12 for a in anchors[:len(source_rays['rays'])]),
        scope='Same exact exported control IDs and unchanged material source chart. Existing G6 triangle/bary locations carry through original child/fan provenance to the same G7 native evaluation. Approximate registered source anchors, not newly measured final crest/valley/merge landmarks.',
        limitations=['No self-intersection or orientation scan.', 'No image beauty certificate.',
            'Sparse equality is exact only at listed IDs; complete control/native archives preserve all smaller changes.',
            'Large-file hashes were not repeated; original receipt bindings are recorded by the production exporter.'])
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps(dict(output=str(args.output), controls=report['meaningful_changed_controls'],
        tiny=report['tiny_changed_controls_omitted_from_sparse'], source_anchors=len(anchors),
        close_anchors_changed=report['prior_close_anchor_changed_count'],
        displacement=report['meaningful_control_displacements']), indent=2))


if __name__ == '__main__': main()
