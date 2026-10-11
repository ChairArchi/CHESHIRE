"""One existing regional ancestry-stencil G5 comparison on both G4 inputs.

Only the existing quad split and regional stencil displacement are used.
No new field, separate normal displacement, smoothing or authored return.
This tests cell lineage, not automatic recognition of architectural features.
"""
from pathlib import Path
import importlib.util
import json
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('transfer_stencil_driver', HERE/'study.py')
transfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transfer)
ROOT = Path('E:/CHESHIRE_DATA/fold_transfer_20261012')
REGION = dict(inner=.010, outer=.050)


def main():
    recipe = dict(transfer.ancestry.RECIPE, normal_gain=0., surface='vf')
    for case, label in [('SPAN', 'SPAN'), ('COUNTER', 'COUNTER_MATCHED')]:
        parent = ROOT/label/'RETURN_ONLY/G04'
        previous = json.loads((parent/'generation.json').read_text(encoding='utf8'))
        mesh, chart, tags = transfer.load(parent)
        bank = previous['event_bank']
        tags = np.maximum(tags, transfer.tag_mask(chart, bank))
        refined, chart_out, carried, _ = transfer.memory.refine(mesh, chart, tags)
        carried = np.maximum(carried, transfer.tag_mask(chart_out, bank))
        candidate, op = transfer.growth.step(mesh, **recipe)
        if not np.array_equal(candidate.faces, refined.faces):
            raise ValueError('Existing stencil and inactive refinement topology differ.')
        raw = candidate.xyz-refined.xyz
        zone = transfer.memory.feature_mask(chart_out, bank, **REGION)
        delta = raw*((1-carried)*zone)[:, None]
        transfer.prior.helpers.existing.reflect(delta, chart_out, transfer.prior.helpers.existing.symmetry(chart_out))
        candidate.xyz = refined.xyz+delta
        core = carried >= 1-1e-12
        folder = ROOT/(case+'_G5_STENCIL')/'G05'
        transfer.save(folder, candidate, chart_out, carried,
            dict(input_case=case, input_source=previous['input_source'], parent=str(parent),
                operation='Existing Task36 ancestry stencil only, in authored legacy-profile neighborhoods',
                task36_recipe=recipe, activation_profile=REGION, event_bank=bank,
                new_authored_events=[], added_field_passes=0,
                field_passes_total=previous['field_passes_total'], memory_applied=True,
                inherited_core_count=int(core.sum()),
                inherited_core_displacement_maximum=float(np.linalg.norm(delta[core], axis=1).max()) if core.any() else None,
                old_controls_displacement_maximum=float(np.linalg.norm(delta[:len(mesh.xyz)], axis=1).max()),
                maximum_stencil_step=float(np.linalg.norm(delta, axis=1).max()),
                active_controls=int((np.linalg.norm(delta, axis=1)>1e-12).sum()),
                rule='Same ancestry recipe and region on both actual inputs; no input-specific tuning',
                note='Parent cell V/F diagonal and face-edge stencils, not fold-angle memory or automatic large-feature recognition'),
            dict(pre_stencil_xyz=refined.xyz, raw_stencil_displacement=raw,
                applied_stencil_displacement=delta, activation=zone, carried_tags=carried,
                stencil_component=op['stencil_component'], input_edges=op['input_edges']))
        shutil.copy2(__file__, folder/'stencil_probe.py')


if __name__ == '__main__':
    main()
