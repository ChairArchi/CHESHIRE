"""Bounded CURVED comparison: existing CC component inside late activation.

One requested stage per call, from the same complete G0 through at most G6.
Returns and locally capped finite-field schedule match LATE. The difference
is existing Task36 CC averaging with tag protection, not separate smoothing.
Strong inherited grooves may soften; no success or fabrication claim is made.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('curved_preserved_late_activation', HERE/'late_activation.py')
late = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(late)
base, t, profile = late.base, late.t, late.profile
ROOT, INPUTS = late.ROOT, late.INPUTS
AVERAGING_MEMORY = {1: (.7, .2), 2: (.7, .2), 3: (.35, .6),
    4: (.2, .75), 5: (.2, .75), 6: (.2, .75)}
CURVED_RECIPE = dict(late.LATE_RECIPE, name='curved_existing_CC_local_edge_cap_v1',
    first_active_placement_stage=1, task36_averaging_vertex_memory=AVERAGING_MEMORY,
    task36_stencil_normal_gains={1: (0., 0.), 2: (0., 0.), **late.GAINS},
    existing_CC_averaging_component_enabled=True,
    stage_order='G1 CC only; G2 original returns then CC; G3-G6 derived returns, CC plus reduced components, same capped finite field',
    risk='CC may soften inherited strong grooves. Scalar tag cores do not lock whole faces or fold angles.')


def generate(case, stage):
    g0 = INPUTS/case/'G00'
    source = g0 if stage == 1 else ROOT/'CURVED'/case/f'G{stage-1:02}'
    folder = ROOT/'CURVED'/case/f'G{stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved: '+str(folder))
    previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
    if previous['quick_integrity'] != 'PASS':
        raise ValueError('Failed source remains preserved.')
    mesh, chart, tags = t.load(source)
    if mesh.generation != stage-1:
        raise ValueError('Wrong actual control generation.')
    old_count = len(mesh.xyz)
    bank = [] if stage == 1 else previous['event_bank']
    tags = np.zeros(old_count) if stage == 1 else np.maximum(tags, base.tags_for(chart, bank))
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
    tags = np.maximum(tags, new_tags)  # G2 macro returns are tagged before CC.
    bank = list(bank)+events
    post_event = mesh.xyz.copy()
    refined, outchart, outtags, inactive_op = t.memory.refine(mesh, chart, tags)
    outtags = np.maximum(outtags, base.tags_for(outchart, bank))
    pre_placement = refined.xyz.copy()
    pairs = existing.symmetry(outchart)
    averaging, vertex_memory = AVERAGING_MEMORY[stage]
    stencil, normal = late.GAINS.get(stage, (0., 0.))
    recipe = dict(t.ancestry.RECIPE, averaging_gain=averaging, vertex_memory=vertex_memory,
        stencil_gain=stencil, normal_gain=normal, surface='vf')
    out, op = t.growth.step(mesh, **recipe)
    if not np.array_equal(out.faces, refined.faces):
        raise ValueError('Active/inactive split topology differs.')
    raw_placement = out.xyz-pre_placement
    placement = raw_placement*(1-outtags)[:, None]
    existing.reflect(placement, outchart, pairs)
    out.xyz = pre_placement+placement
    pre_field = out.xyz.copy()
    edge_lengths = late.local_edge_lengths(pre_field, out.faces)
    raw_field = np.zeros_like(pre_field)
    weighted_field = np.zeros_like(pre_field)
    applied = np.zeros_like(pre_field)
    cap_factors = np.ones(len(pre_field))
    field_log, payload = None, {}
    if stage >= 3:
        field_xyz, payload, field_log = t.field(out, outchart, late.ITERATIONS[stage], late.BUDGETS[stage], 2)
        raw_field = field_xyz-pre_field
        weighted_field = raw_field*(1-outtags)[:, None]
        requested = np.linalg.norm(weighted_field, axis=1)
        cap_factors = np.minimum(1., .25*edge_lengths/np.maximum(requested, 1e-15))
        applied = weighted_field*cap_factors[:, None]
        existing.reflect(applied, outchart, pairs)
        out.xyz = pre_field+applied
    core = outtags >= 1-1e-12
    norm = lambda x: np.linalg.norm(x, axis=1)
    meta = dict(candidate='CURVED', input_case=case, parent=str(source), source_g0=str(g0),
        input_source=str(g0), operation='Existing Task36 CC averaging plus tag protection inside the LATE return and capped-field composition',
        composition_recipe=CURVED_RECIPE, curved_activation_recipe=CURVED_RECIPE,
        composition_recipe_scope='Actual CURVED G0-based schedule through maximum G6; shared child/tag rules reused from the study helper',
        new_authored_events=events, event_bank=bank, task36_recipe=recipe,
        inactive_refinement_recipe=dict(active=False, mode='interpolating', source='current', surface='vf'),
        active_placement=True, existing_CC_averaging_component_enabled=True,
        field_enabled=stage >= 3, field=field_log,
        field_passes_total=max(0, stage-2), added_field_passes=int(stage >= 3),
        field_memory_rule='Same as LATE: 1-tags on all old/new controls then .25 times local mean incident control-edge length; reflected',
        field_cap_geometry='Unique undirected control-quad edges measured on actual pre-field controls; scalar lengths only',
        maximum_return_step=float(norm(returned).max()), inherited_core_count=int(inherited_core.sum()),
        inherited_core_return_maximum=float(norm(returned[inherited_core]).max()) if inherited_core.any() else None,
        maximum_placement_step=float(norm(placement).max()),
        incoming_old_vertex_count=old_count,
        incoming_old_vertex_placement_maximum=float(norm(placement[:old_count]).max()),
        incoming_old_vertex_total_movement_maximum=float(norm(out.xyz[:old_count]-pre_event).max()),
        exact_core_placement_maximum=float(norm(placement[core]).max()) if core.any() else None,
        maximum_field_step=float(norm(applied).max()), field_moved_controls=int((norm(applied) > 1e-12).sum()),
        field_locally_capped_controls=int(((cap_factors < 1) & (norm(weighted_field) > 1e-12)).sum()),
        tag_core_count=int(core.sum()), tag_core_field_maximum=float(norm(applied[core]).max()) if core.any() else None,
        note='CC averaging is the existing Task36 component, not separate XYZ smoothing. Strong grooves can soften. Tags protect points, not mechanical folds or whole facets. One stage per invocation.')
    arrays = dict(pre_event_xyz=pre_event, post_event_xyz=post_event,
        raw_return_displacement=raw_return, applied_return_displacement=returned,
        source_inherited_tags=inherited_tags, source_new_feature_tags=new_tags,
        pre_placement_xyz=pre_placement, raw_placement_displacement=raw_placement,
        applied_placement_displacement=placement, input_edges=inactive_op['input_edges'],
        parent_face=inactive_op['parent_face'], pre_field_xyz=pre_field,
        averaging_component=op['averaging_component'], stencil_component=op['stencil_component'],
        normal_component=op['normal_component'],
        raw_field_displacement=raw_field, tag_weighted_field_displacement=weighted_field,
        applied_field_displacement=applied, local_edge_lengths=edge_lengths,
        local_field_step_cap=.25*edge_lengths, field_cap_factors=cap_factors,
        carried_tags=outtags, field_weight=1-outtags)
    for name in ('canonical_nearest_outside_target', 'finite_inside'):
        if name in payload:
            arrays[name] = payload[name]
    base.save(folder, out, outchart, outtags, meta, arrays)
    shutil.copy2(late.__file__, folder/'late_activation.py')
    shutil.copy2(__file__, folder/'curved_activation.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=int, choices=range(1, 7), required=True)
    parser.add_argument('--cases', nargs='+', choices=('SPAN', 'COUNTER'), default=['SPAN'])
    args = parser.parse_args()
    for case in args.cases:
        generate(case, args.stage)
