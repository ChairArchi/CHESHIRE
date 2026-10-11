"""Bounded broad return / matched CC and preserved OVERLAP anchor comparison.

G3 optionally adds two broad authored meso returns; G4 adds no event. Both
use the same existing CC component only, with material-profile tag protection.
No new field, recursive child schedule, separate smoothing or physical origami.
ANCHOR inherits OVERLAP G2's two existing field passes and adds only matched CC.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('broad_return_preserved_coherence',
    HERE.parent/'fold_coherence_20261012/study.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
t, profile = base.t, base.profile
ROOT = Path('E:/CHESHIRE_DATA/fold_return_20261012')
SOURCE = Path('E:/CHESHIRE_DATA/fold_coherence_20261012/CURVED/SPAN/G02')
ANCHOR_SOURCE = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G02')
RECIPE = dict(name='two_broad_counter_swept_returns_with_matched_existing_CC_v1',
    source=str(SOURCE), maximum_generation=4, stages=[3, 4],
    variants=dict(CONTROL='No new authored return', RETURN='Two broad meso returns at G3 only',
        ANCHOR='Actual OVERLAP G2, no new return or field, same existing CC'),
    parent_height_offsets=[.20, -.20], parent_direction_width_offsets=[.25, -.25],
    meso_event=dict(span=.085, expansion=.10, constriction=.23, reexpansion=.20,
        return_depth=.50, overlap_width=.52, sweep=-.24, bend_height=.035,
        sweep_span=.26, mirror=False),
    averaging_gain=.65, vertex_memory=.25, stencil_gain=0., normal_gain=0.,
    surface='vf', field_displacement=False, recursive_children=False,
    protection='1 minus inherited/fresh authored material-profile tags, before constructive XY reflection',
    limitation='Tags protect control points, not whole walls or fold angles; not a mechanical folding solver.')


def meso_events(parents):
    if len(parents) != 2:
        raise ValueError('This bounded design expects exactly two source macro returns.')
    events = []
    for parent, dh, dd in zip(parents, RECIPE['parent_height_offsets'],
            RECIPE['parent_direction_width_offsets']):
        event = dict(RECIPE['meso_event'],
            id='BROAD_MESO_OF_'+parent['id'], parent_event_id=parent['id'],
            height=parent['height']+dh*parent['span'],
            direction=parent['direction']+dd*parent['overlap_width'])
        events.append(event)
    return events


def generate(variant, stage, *, root=ROOT, source_g2=None):
    root = Path(root).resolve()
    override = Path(source_g2).resolve() if source_g2 is not None else None
    origin = override or (ANCHOR_SOURCE if variant == 'ANCHOR' else SOURCE)
    source = origin if stage == 3 else root/variant/'SPAN'/'G03'
    folder = root/variant/'SPAN'/f'G{stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved: '+str(folder))
    previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
    if stage == 4:
        origin = Path(previous['source_g2'])
        if override is not None and override != origin.resolve():
            raise ValueError('--source-g2 differs from the preserved G3 source.')
    source_g2 = origin
    if previous['quick_integrity'] != 'PASS':
        raise ValueError('Failed parent remains preserved.')
    inherited_field_passes = 2 if variant == 'ANCHOR' else 0
    if previous['field_passes_total'] != inherited_field_passes:
        raise ValueError('Unexpected inherited field history for '+variant)
    if stage == 4 and previous['candidate'] != variant:
        raise ValueError('Wrong preserved variant source.')
    mesh, chart, tags = t.load(source)
    if mesh.generation != stage-1:
        raise ValueError('Wrong actual control generation.')
    old_count = len(mesh.xyz)
    input_surface = mesh.surface
    bank = previous.get('event_bank', previous.get('authored_return_events'))
    if bank is None:
        raise ValueError('Source authored return bank is missing.')
    tags = np.maximum(tags, base.tags_for(chart, bank))
    inherited_tags = tags.copy()
    inherited_core = inherited_tags >= 1-1e-12
    events = meso_events(bank) if stage == 3 and variant == 'RETURN' else []
    pre_event = mesh.xyz.copy()
    raw_return = sum((profile.reflected_event(chart, e) for e in events),
        np.zeros_like(mesh.xyz))
    applied_return = raw_return*(1-tags)[:, None]
    existing = t.prior.helpers.existing
    existing.reflect(applied_return, chart, existing.symmetry(chart))
    mesh.xyz += applied_return
    new_tags = base.tags_for(chart, events)*(np.linalg.norm(applied_return, axis=1) > 1e-12)
    tags = np.maximum(tags, new_tags)  # Register new return tags before CC placement.
    bank = list(bank)+events
    post_event = mesh.xyz.copy()
    refined, outchart, outtags, inactive_op = t.memory.refine(mesh, chart, tags)
    outtags = np.maximum(outtags, base.tags_for(outchart, bank))
    recipe = dict(t.ancestry.RECIPE, averaging_gain=.65, vertex_memory=.25,
        stencil_gain=0., normal_gain=0., surface='vf')
    out, op = t.growth.step(mesh, **recipe)
    if not np.array_equal(out.faces, refined.faces):
        raise ValueError('Active/inactive topology differs.')
    raw_placement = out.xyz-refined.xyz
    placement = raw_placement*(1-outtags)[:, None]
    existing.reflect(placement, outchart, existing.symmetry(outchart))
    out.xyz = refined.xyz+placement
    norm = lambda value: np.linalg.norm(value, axis=1)
    core = outtags >= 1-1e-12
    source_core_motion = norm(out.xyz[:old_count]-pre_event)[inherited_core]
    composition = dict(RECIPE, source=str(source_g2), variant=variant,
        inherited_field_passes=inherited_field_passes, new_field_passes=0)
    if variant == 'ANCHOR':
        composition['name'] = 'anchored_overlap_existing_CC_only_v1'
    meta = dict(candidate=variant, input_case='SPAN', parent=str(source),
        source_g2=str(source_g2), source_path=str(source), input_surface=input_surface,
        composition_recipe=composition, task36_recipe=recipe,
        composition_adapter=str(Path(__file__).resolve()), composition_adapter_snapshot='broad_return_study.py',
        operation='Optional two broad counter-swept meso return events, then matched existing CC component with profile-tag protection',
        authored_event_description='RETURN G3 has two authored coherent meso events, not fractal-emergent folds; CONTROL, ANCHOR and all G4 stages add none',
        new_authored_events=events, event_bank=bank, new_authored_event_count=len(events),
        authored_events_total=len(bank), inherited_authored_event_count=len(bank)-len(events),
        active_placement=True, field_enabled=False, added_field_passes=0,
        field_passes_total=inherited_field_passes, source_field_passes_total=previous['field_passes_total'], recursive_children=False,
        inactive_refinement_recipe=dict(active=False, mode='interpolating', source='current', surface='vf'),
        incoming_old_vertex_count=old_count, inherited_core_count=int(inherited_core.sum()),
        inherited_core_return_maximum=float(norm(applied_return[inherited_core]).max()) if inherited_core.any() else None,
        source_core_placement_maximum=float(norm(placement[:old_count])[inherited_core].max()) if inherited_core.any() else None,
        source_core_total_movement=dict(count=len(source_core_motion),
            maximum=float(source_core_motion.max()) if len(source_core_motion) else None,
            median=float(np.median(source_core_motion)) if len(source_core_motion) else None,
            moved_over_1e_12=int((source_core_motion > 1e-12).sum())),
        maximum_raw_return_step=float(norm(raw_return).max()),
        maximum_return_step=float(norm(applied_return).max()),
        return_moved_controls=int((norm(applied_return) > 1e-12).sum()),
        new_return_tagged_controls=int((new_tags > 0).sum()),
        tag_core_count=int(core.sum()), maximum_placement_step=float(norm(placement).max()),
        incoming_old_vertex_placement_maximum=float(norm(placement[:old_count]).max()),
        exact_core_placement_maximum=float(norm(placement[core]).max()) if core.any() else None,
        note='G counts subdivision passes. Authored return event counts are separate; no physical folding or fractal-emergent-fold claim. CONTROL versus RETURN is a bounded design comparison including resulting tag/CC differences.')
    arrays = dict(pre_event_xyz=pre_event, post_event_xyz=post_event,
        raw_return_displacement=raw_return, applied_return_displacement=applied_return,
        source_inherited_tags=inherited_tags, source_new_feature_tags=new_tags,
        refined_xyz=refined.xyz, pre_placement_xyz=refined.xyz,
        raw_placement_displacement=raw_placement, applied_placement_displacement=placement,
        averaging_component=op['averaging_component'], stencil_component=op['stencil_component'],
        normal_component=op['normal_component'], input_edges=inactive_op['input_edges'],
        parent_face=inactive_op['parent_face'], carried_tags=outtags)
    base.save(folder, out, outchart, outtags, meta, arrays)
    shutil.copy2(__file__, folder/'broad_return_study.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=('CONTROL', 'RETURN', 'ANCHOR'), required=True)
    parser.add_argument('--stage', type=int, choices=(3, 4), required=True)
    parser.add_argument('--root', type=Path, default=ROOT, help='Output root; existing results are preserved')
    parser.add_argument('--source-g2', type=Path, help='Optional G2 folder override; G4 must match its saved G3 provenance')
    args = parser.parse_args()
    generate(args.variant, args.stage, root=args.root, source_g2=args.source_g2)
