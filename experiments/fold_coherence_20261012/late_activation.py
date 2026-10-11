"""One bounded late-detail composition from complete G0, one stage per call.

G1 refines only; G2 adds the original two returns before inactive refinement.
G3-G6 reuse derived PCHIP returns, small Task36 components and the existing
finite field. A local edge-length vector cap adds no geometric smoothing.
No SI repair, new solver, arbitrary-input engine, automatic loop or scheduler.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('late_existing_coherence', HERE/'study.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
t, profile = base.t, base.profile
ROOT = base.ROOT
INPUTS = Path('E:/CHESHIRE_DATA/fold_transfer_20261012/inputs')
GAINS = {3: (.15, .08), 4: (.10, .05), 5: (.08, .04), 6: (.06, .03)}
ITERATIONS = {3: 8, 4: 18, 5: 18, 6: 18}
BUDGETS = {3: .14, 4: .10, 5: .07, 6: .05}
LATE_RECIPE = dict(name='late_activation_local_edge_cap_v1', maximum_generation=6,
    first_active_placement_stage=3, first_field_stage=3,
    task36_stencil_normal_gains=GAINS, field_iterations=ITERATIONS,
    field_budgets=BUDGETS, field_fraction=.55, field_target_factor=2,
    field_cap_fraction_of_mean_incident_control_edge=.25,
    child_rules={k: base.CFG[k] for k in ('first_child', 'later_child', 'profile_scaling')},
    tag_rules={k: base.CFG[k] for k in ('memory_inner_at_span_012', 'memory_outer_at_span_012')},
    blanket_old_control_pin=False, separate_geometric_smoothing=False,
    stage_order='G1 inactive split; G2 original macro returns then inactive split; G3-G6 derived returns, reduced placement, locally capped finite field')


def local_edge_lengths(xyz, faces):
    """Mean incident edge LENGTH, not an average or movement of coordinates."""
    edges = np.unique(np.sort(np.concatenate([
        faces[:, [i, (i+1) % 4]] for i in range(4)]), axis=1), axis=0)
    lengths = np.linalg.norm(xyz[edges[:, 1]]-xyz[edges[:, 0]], axis=1)
    degree = np.bincount(edges.ravel(), minlength=len(xyz))
    total = np.bincount(edges.ravel(), weights=np.repeat(lengths, 2), minlength=len(xyz))
    return np.divide(total, degree, out=np.zeros(len(xyz)), where=degree > 0)


def generate(case, stage):
    g0 = INPUTS/case/'G00'
    source = g0 if stage == 1 else ROOT/'LATE'/case/f'G{stage-1:02}'
    folder = ROOT/'LATE'/case/f'G{stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved: '+str(folder))
    previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
    if previous['quick_integrity'] != 'PASS':
        raise ValueError('Failed source remains preserved.')
    mesh, chart, tags = t.load(source)
    if mesh.generation != stage-1:
        raise ValueError('Wrong actual control generation.')
    bank = [] if stage == 1 else previous['event_bank']
    tags = np.zeros(len(mesh.xyz)) if stage == 1 else np.maximum(tags, base.tags_for(chart, bank))
    inherited_tags = tags.copy()
    inherited_core = inherited_tags >= 1-1e-12
    events = ([dict(e) for e in t.overlap.EVENTS] if stage == 2 else
        base.children(previous['new_authored_events'], stage) if stage >= 3 else [])
    pre_event = mesh.xyz.copy()
    raw_return = sum((profile.reflected_event(chart, e) for e in events), np.zeros_like(mesh.xyz))
    returned = raw_return*(1-tags)[:, None]
    existing = t.prior.helpers.existing
    existing.reflect(returned, chart, existing.symmetry(chart))
    mesh.xyz += returned
    new_tags = base.tags_for(chart, events)*(np.linalg.norm(returned, axis=1) > 1e-12)
    tags = np.maximum(tags, new_tags)
    bank = list(bank)+events
    post_event = mesh.xyz.copy()
    refined, outchart, outtags, inactive_op = t.memory.refine(mesh, chart, tags)
    outtags = np.maximum(outtags, base.tags_for(outchart, bank))
    pre_placement = refined.xyz.copy()
    pairs = existing.symmetry(outchart)
    recipe = None
    raw_placement = np.zeros_like(refined.xyz)
    placement = np.zeros_like(refined.xyz)
    out = refined
    if stage >= 3:
        stencil, normal = GAINS[stage]
        recipe = dict(t.ancestry.RECIPE, averaging_gain=0., stencil_gain=stencil,
            normal_gain=normal, vertex_memory=1., surface='vf')
        out, _ = t.growth.step(mesh, **recipe)
        if not np.array_equal(out.faces, refined.faces):
            raise ValueError('Active/inactive split topology differs.')
        raw_placement = out.xyz-pre_placement
        placement = raw_placement*(1-outtags)[:, None]
        existing.reflect(placement, outchart, pairs)
        out.xyz = pre_placement+placement
    pre_field = out.xyz.copy()
    edge_lengths = local_edge_lengths(pre_field, out.faces)
    raw_field = np.zeros_like(pre_field)
    weighted_field = np.zeros_like(pre_field)
    applied = np.zeros_like(pre_field)
    cap_factors = np.ones(len(pre_field))
    field_log = None
    payload = {}
    if stage >= 3:
        field_xyz, payload, field_log = t.field(out, outchart, ITERATIONS[stage], BUDGETS[stage], 2)
        raw_field = field_xyz-pre_field
        weighted_field = raw_field*(1-outtags)[:, None]
        requested = np.linalg.norm(weighted_field, axis=1)
        cap_factors = np.minimum(1., .25*edge_lengths/np.maximum(requested, 1e-15))
        applied = weighted_field*cap_factors[:, None]
        existing.reflect(applied, outchart, pairs)
        out.xyz = pre_field+applied
    core = outtags >= 1-1e-12
    norm = lambda x: np.linalg.norm(x, axis=1)
    meta = dict(candidate='LATE', input_case=case, parent=str(source), source_g0=str(g0),
        input_source=str(g0), operation='Late activation: authored returns, existing VF split, reduced components, local-edge-capped tag-only finite field',
        late_activation_recipe=LATE_RECIPE,
        composition_recipe_scope='Inherited study helper child/tag settings only; late_activation_recipe defines this G0-based schedule',
        new_authored_events=events, event_bank=bank, task36_recipe=recipe,
        inactive_refinement_recipe=dict(active=False, mode='interpolating', source='current', surface='vf'),
        active_placement=stage >= 3, field_enabled=stage >= 3, field=field_log,
        field_passes_total=max(0, stage-2), added_field_passes=int(stage >= 3),
        field_memory_rule='1-tags on every old/new control, then .25 times local mean incident edge length; constructive XY reflection',
        field_cap_geometry='Unique undirected control-quad edges measured on actual pre-field controls; scalar lengths only, no XYZ averaging',
        maximum_return_step=float(norm(returned).max()), inherited_core_count=int(inherited_core.sum()),
        inherited_core_return_maximum=float(norm(returned[inherited_core]).max()) if inherited_core.any() else None,
        maximum_placement_step=float(norm(placement).max()), maximum_field_step=float(norm(applied).max()),
        field_moved_controls=int((norm(applied) > 1e-12).sum()),
        field_locally_capped_controls=int(((cap_factors < 1) & (norm(weighted_field) > 1e-12)).sum()),
        tag_core_count=int(core.sum()), tag_core_field_maximum=float(norm(applied[core]).max()) if core.any() else None,
        note='G1-G2 have no active cell placement or field. Returns are authored geometry; no mechanical folding or fabrication claim. One requested stage per invocation.')
    arrays = dict(pre_event_xyz=pre_event, post_event_xyz=post_event,
        raw_return_displacement=raw_return, applied_return_displacement=returned,
        source_inherited_tags=inherited_tags, source_new_feature_tags=new_tags,
        pre_placement_xyz=pre_placement, raw_placement_displacement=raw_placement,
        applied_placement_displacement=placement, input_edges=inactive_op['input_edges'],
        parent_face=inactive_op['parent_face'], pre_field_xyz=pre_field,
        raw_field_displacement=raw_field, tag_weighted_field_displacement=weighted_field,
        applied_field_displacement=applied, local_edge_lengths=edge_lengths,
        local_field_step_cap=.25*edge_lengths, field_cap_factors=cap_factors,
        carried_tags=outtags, field_weight=1-outtags)
    for name in ('canonical_nearest_outside_target', 'finite_inside'):
        if name in payload:
            arrays[name] = payload[name]
    base.save(folder, out, outchart, outtags, meta, arrays)
    shutil.copy2(__file__, folder/'late_activation.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=int, choices=range(1, 7), required=True)
    parser.add_argument('--cases', nargs='+', choices=('SPAN', 'COUNTER'), default=['SPAN'])
    args = parser.parse_args()
    for case in args.cases:
        generate(case, args.stage)
