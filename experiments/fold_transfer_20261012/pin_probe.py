"""One saved-vector ablation of G5 blanket inherited-point field pinning.

Reuse the exact pre-field state, sampled raw field vectors, tags and topology.
No new subdivision, authored return, field query, smoothing or SI validation.
"""
from pathlib import Path
import importlib.util
import json
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('transfer_pin_driver', HERE/'study.py')
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)
ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
DIAGNOSIS = HERE.parents[1]/'docs/fold_transfer_20261012/technical/g5_pin_diagnosis.json'
EPS = 1e-12


def edge_diagnosis(pre, faces, before, after, old_count, shape_only=False):
    """Observe relative neighbor movement on saved unique control edges."""
    edges = np.unique(np.sort(np.concatenate([
        faces[:, [i, (i+1) % 4]] for i in range(4)]), axis=1), axis=0)
    vectors = pre[edges[:, 1]]-pre[edges[:, 0]]
    lengths = np.linalg.norm(vectors, axis=1)
    valid = lengths > EPS
    old_new = (edges[:, 0] < old_count) != (edges[:, 1] < old_count)
    new_new = (edges[:, 0] >= old_count) & (edges[:, 1] >= old_count)
    source_active = (np.linalg.norm(before, axis=1) > EPS)[edges].any(axis=1)

    if shape_only:
        mask = old_new & source_active
        usable = mask & valid
        pair = edges[usable]
        edge = vectors[usable]
        length = lengths[usable]

        def quantiles(values):
            return dict(p10=float(np.percentile(values, 10)) if len(values) else None,
                median=float(np.median(values)) if len(values) else None,
                p90=float(np.percentile(values, 90)) if len(values) else None)

        result = dict(unique_control_edges=len(edges), old_control_count=old_count,
            selected_edges=int(mask.sum()), excluded_short_edges=int((mask & ~valid).sum()),
            measured_edges=int(usable.sum()))
        for name, delta in (('PROTECTED', before), ('TAG_ONLY', after)):
            difference = delta[pair[:, 1]]-delta[pair[:, 0]]
            difference_norm = np.linalg.norm(difference, axis=1)
            nonzero = difference_norm > EPS
            cosine = np.einsum('ij,ij->i', difference[nonzero], edge[nonzero])
            cosine /= difference_norm[nonzero]*length[nonzero]
            result[name] = dict(
                post_pre_edge_length_ratio=quantiles(np.linalg.norm(edge+difference, axis=1)/length),
                cosine_delta_difference_pre_edge=quantiles(np.clip(cosine, -1, 1)),
                cosine_measured_edges=int(nonzero.sum()),
                cosine_excluded_zero_delta_difference=int((~nonzero).sum()))
        return result

    def summary(delta):
        active = (np.linalg.norm(delta, axis=1) > EPS)[edges].any(axis=1)
        difference = np.linalg.norm(delta[edges[:, 1]]-delta[edges[:, 0]], axis=1)
        groups = dict(
            old_new_all=old_new,
            old_new_source_moving_fixed_cohort=old_new & source_active,
            old_new_variant_moving=old_new & active,
            new_new_variant_moving=new_new & active)
        result = {}
        for name, mask in groups.items():
            usable = mask & valid
            ratio = difference[usable]/lengths[usable]
            result[name] = dict(selected_edges=int(mask.sum()),
                excluded_short_edges=int((mask & ~valid).sum()),
                measured_edges=int(usable.sum()),
                p50=float(np.percentile(ratio, 50)) if len(ratio) else None,
                p90=float(np.percentile(ratio, 90)) if len(ratio) else None,
                p99=float(np.percentile(ratio, 99)) if len(ratio) else None,
                maximum=float(ratio.max()) if len(ratio) else None,
                fraction_above_half=float(np.mean(ratio > .5)) if len(ratio) else None,
                fraction_above_one=float(np.mean(ratio > 1)) if len(ratio) else None)
        return result

    return dict(unique_control_edges=len(edges), old_control_count=old_count,
        PROTECTED=summary(before), TAG_ONLY=summary(after))


def main():
    targets = [ROOT/(case+'_G5_TAG_ONLY')/'G05' for case in ('SPAN', 'COUNTER')]
    for target in targets:
        if target.exists() and any(target.iterdir()):
            raise FileExistsError('Existing stage preserved: '+str(target))
    if DIAGNOSIS.exists():
        raise FileExistsError('Existing diagnosis preserved: '+str(DIAGNOSIS))
    report = dict(
        operation='Saved-vector G5 blanket inherited-point pin ablation only',
        definition='norm(delta[j]-delta[i]) / norm(pre_field_xyz[j]-pre_field_xyz[i])',
        edge_source='Unique sorted endpoint pairs of the four control-quad edges; not rendered triangle edges',
        short_edge_exclusion_threshold=EPS,
        short_edge_exclusion_rule='Exclude input edge length <= threshold',
        moving_threshold=EPS,
        moving_rule='At least one endpoint has applied displacement norm > threshold',
        fixed_cohort='old_new_source_moving_fixed_cohort uses PROTECTED moving edges for both variants',
        all_cohort='old_new_all includes all old/new edges regardless of movement, after short-edge exclusion',
        interpretation='Neighbor displacement observation only; ratios do not establish intersections, visual causation or fabrication validity',
        self_intersection='NOT_CHECKED_INTERMEDIATE', cases={})
    for case, target in zip(('SPAN', 'COUNTER'), targets):
        source = ROOT/(case+'_G5_FROM_RETURN')/'PROTECTED/G05'
        previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
        mesh, chart, tags = transfer.load(source)
        old_parent = Path(previous['parent'])
        old_count = json.loads((old_parent/'generation.json').read_text(encoding='utf8'))['control_vertices']
        with np.load(source/'operation_fields.npz', allow_pickle=False) as data:
            arrays = {name: data[name].copy() for name in data.files}
        pre = arrays['pre_field_xyz']
        raw = arrays['raw_field_displacement']
        baseline = arrays['applied_field_displacement']
        if pre.shape != mesh.xyz.shape or raw.shape != pre.shape or not np.array_equal(tags, arrays['carried_tags']):
            raise ValueError('Saved pre-field, raw displacement or tags do not align.')
        if not np.array_equal(mesh.xyz, pre+baseline):
            raise ValueError('Saved PROTECTED actual controls differ from saved pre-field plus applied vectors.')
        weight = 1-tags
        applied = raw*weight[:, None]
        transfer.prior.helpers.existing.reflect(applied, chart,
            transfer.prior.helpers.existing.symmetry(chart))
        mesh.xyz = pre+applied
        core = tags >= 1-EPS
        norm = np.linalg.norm(applied, axis=1)
        raw_norm = np.linalg.norm(raw, axis=1)
        source_weight = arrays['field_weight'].copy()
        source_raw_active = arrays['field_active'].copy()
        arrays.update(applied_field_displacement=applied, field_weight=weight,
            source_protected_field_displacement=baseline,
            source_protected_field_weight=source_weight,
            actual_field_active=norm > EPS,
            raw_field_active=source_raw_active)
        # field_displacement and field_active are the inherited raw-query
        # payload; applied_field_displacement/actual_field_active describe
        # this candidate's actual weighted and reflected operation.
        meta = dict(input_case=case, input_source=previous['input_source'],
            parent=str(source), original_g4_parent=str(old_parent),
            operation='Saved G5 raw field vectors with tag-only weights; blanket old-control field pin removed',
            same_pre_field_and_raw_field_source=str(source/'operation_fields.npz'),
            field=previous['field'], field_passes_total=previous['field_passes_total'],
            added_field_passes=0, added_subdivision_passes=0,
            added_return_events=0, new_authored_events=[],
            reused_g5_authored_events=previous['new_authored_events'],
            event_bank=previous['event_bank'], memory_applied=True,
            protected_field=True, blanket_old_control_pin=False,
            field_memory_rule='Both inherited and newborn controls use 1-carried_tags; exact tag cores stay fixed',
            feature_memory_scope='Material-profile tags only; untagged inherited controls can move; no fold-angle/mechanical memory',
            old_control_count=old_count,
            old_controls_field_moved=int((norm[:old_count] > EPS).sum()),
            old_controls_field_maximum=float(norm[:old_count].max()),
            fully_protected_feature_count=int(core.sum()),
            raw_field_moved_core=int((raw_norm[core] > EPS).sum()),
            applied_field_moved_core=int((norm[core] > EPS).sum()),
            tag_core_field_maximum=float(norm[core].max()) if core.any() else None,
            raw_field_moved_controls=int((raw_norm > EPS).sum()),
            applied_field_moved_controls=int((norm > EPS).sum()),
            raw_field_maximum=float(raw_norm.max()), applied_field_maximum=float(norm.max()),
            newborn_applied_difference_from_protected_maximum=float(np.linalg.norm(applied[old_count:]-baseline[old_count:], axis=1).max()),
            raw_query_payload_scope='field_displacement/field_active inherited unchanged as raw query evidence; actual applied vectors and active mask saved separately',
            rule='Exactly one changed pin rule on the same saved G5 pre-field controls, raw field samples, tags and topology',
            note='Global G5 and four already sampled field passes remain unchanged; this adapter samples no field and performs no subdivision or return')
        transfer.save(target, mesh, chart, tags, meta, arrays)
        shutil.copy2(__file__, target/'pin_probe.py')
        report['cases'][case] = dict(source=str(source), candidate=str(target),
            same_saved_pre_field_and_raw_vectors=True,
            tag_core_count=int(core.sum()), tag_core_field_maximum=meta['tag_core_field_maximum'],
            old_controls_field_moved=meta['old_controls_field_moved'],
            old_controls_field_maximum=meta['old_controls_field_maximum'],
            newborn_applied_difference_from_protected_maximum=meta['newborn_applied_difference_from_protected_maximum'],
            edge_observation=edge_diagnosis(pre, mesh.faces, baseline, applied, old_count))
        print(case, 'old moved', meta['old_controls_field_moved'], 'old max',
            meta['old_controls_field_maximum'], 'core max', meta['tag_core_field_maximum'], flush=True)
    DIAGNOSIS.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSIS.write_text(json.dumps(report, indent=2), encoding='utf8')
    print('DIAGNOSIS', str(DIAGNOSIS), flush=True)


if __name__ == '__main__':
    main()
