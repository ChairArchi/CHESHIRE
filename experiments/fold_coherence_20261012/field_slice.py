"""Materialize one saved pre-field surface; no new query or growth operation."""
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
import study as base


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=int, choices=(3, 4, 5, 6), required=True)
    args = parser.parse_args()
    source = base.ROOT/'CURVED/SPAN'/f'G{args.stage:02}'
    folder = base.ROOT/'DIAGNOSIS/CURVED_PREFIELD'/f'G{args.stage:02}'
    mesh, chart, tags = base.t.load(source)
    previous = json.loads((source/'generation.json').read_text(encoding='utf8'))
    with np.load(source/'operation_fields.npz', allow_pickle=False) as saved:
        before = saved['pre_field_xyz'].copy()
        after = before+saved['applied_field_displacement']
    if not np.allclose(after, mesh.xyz, rtol=0, atol=1e-13):
        raise ValueError('Saved operation does not match actual control state.')
    mesh.xyz = before
    base.save(folder, mesh, chart, tags,
        dict(candidate='CURVED_PREFIELD', input_case='SPAN', source=str(source),
            composition_recipe=previous['composition_recipe'],
            operation='Materialized saved pre-field controls; no new subdivision, return or field query',
            comparison='Identical control topology and physical-surface policy to the saved CURVED stage',
            new_field_queries=0, new_subdivision_passes=0,
            field_passes_total=previous['field_passes_total']-1,
            event_bank=previous['event_bank'],
            new_authored_events=previous['new_authored_events'],
            scope='Causal slice of this operation only; earlier generations still contain their field responses'),
        dict(materialized_control_xyz=before))
    shutil.copy2(__file__, folder/'field_slice.py')


if __name__ == '__main__':
    main()
