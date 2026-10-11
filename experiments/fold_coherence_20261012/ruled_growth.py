"""Bounded repeated existing-subdivision control from the same CURVED G2.

No added authored child returns, field displacement or topology engine.
The same support-scaled Task36 kernel repeats on its own incoming geometry.
This is a comparison, not an exact reconstruction of another project.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ruled_preserved_curved', HERE/'curved_activation.py')
curved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(curved)
base, t = curved.base, curved.t
ROOT = base.ROOT
RULE = dict(name='repeated_existing_support_scaled_kernel_v1', maximum_generation=6,
    averaging_gain=.8, stencil_gain=.35, normal_gain=.75, vertex_memory=.35,
    extra_authored_returns=False, field_displacement=False,
    separate_geometric_smoothing=False,
    feature_protection='Inherited authored extrema tags; no whole-face or angle lock')


def generate(stage):
    source = ROOT/'CURVED/SPAN/G02' if stage == 3 else ROOT/'RULED/SPAN'/f'G{stage-1:02}'
    folder = ROOT/'RULED/SPAN'/f'G{stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing result preserved: '+str(folder))
    previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
    if previous['quick_integrity'] != 'PASS':
        raise ValueError('Failed source remains preserved.')
    mesh, chart, tags = t.load(source)
    if mesh.generation != stage-1:
        raise ValueError('Wrong actual control generation.')
    bank = previous['event_bank']
    tags = np.maximum(tags, base.tags_for(chart, bank))
    old_count = len(mesh.xyz)
    before = mesh.xyz.copy()
    refined, outchart, outtags, _ = t.memory.refine(mesh, chart, tags)
    outtags = np.maximum(outtags, base.tags_for(outchart, bank))
    recipe = dict(t.ancestry.RECIPE,
        **{k: RULE[k] for k in ('averaging_gain', 'stencil_gain', 'normal_gain', 'vertex_memory')},
        surface='vf')
    out, op = t.growth.step(mesh, **recipe)
    if not np.array_equal(out.faces, refined.faces):
        raise ValueError('Active/inactive topology differs.')
    raw = out.xyz-refined.xyz
    applied = raw*(1-outtags)[:, None]
    existing = t.prior.helpers.existing
    existing.reflect(applied, outchart, existing.symmetry(outchart))
    out.xyz = refined.xyz+applied
    core = outtags >= 1-1e-12
    norm = lambda a: np.linalg.norm(a, axis=1)
    base.save(folder, out, outchart, outtags,
        dict(candidate='RULED', input_case='SPAN', parent=str(source),
            source_g2=str(ROOT/'CURVED/SPAN/G02'),
            composition_recipe=RULE, task36_recipe=recipe,
            operation='Same existing support-scaled subdivision kernel repeated on incoming geometry',
            event_bank=bank, new_authored_events=[], added_field_passes=0,
            field_passes_total=0, field_enabled=False,
            active_placement=True, maximum_placement_step=float(norm(applied).max()),
            incoming_old_vertex_count=old_count,
            incoming_old_vertex_total_movement_maximum=float(norm(out.xyz[:old_count]-before).max()),
            tag_core_count=int(core.sum()),
            exact_core_placement_maximum=float(norm(applied[core]).max()) if core.any() else None,
            note='G1/G2 source also has no field. This isolates repeated existing geometric subdivision from nearest-outside target displacement. Not mechanical folding or a Hansmeyer reproduction.'),
        dict(pre_placement_xyz=refined.xyz, raw_placement_displacement=raw,
            applied_placement_displacement=applied, carried_tags=outtags,
            averaging_component=op['averaging_component'],
            stencil_component=op['stencil_component'], normal_component=op['normal_component'],
            support_radius=op['support_radius'], face_bend=op['face_bend'],
            parent_face=op['parent_face'], input_edges=op['input_edges']))
    shutil.copy2(__file__, folder/'ruled_growth.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=int, choices=(3, 4, 5, 6), required=True)
    args = parser.parse_args()
    generate(args.stage)
