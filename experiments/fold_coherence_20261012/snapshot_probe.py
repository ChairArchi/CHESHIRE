"""Render stored early-stage operation slices; no new growth or field query."""
from pathlib import Path
import shutil
import numpy as np
import study as coherence


def main():
    source = coherence.SOURCES['SPAN']
    mesh, chart, _ = coherence.t.load(source)
    with np.load(source/'operation_fields.npz', allow_pickle=False) as saved:
        slices = {name: saved[key].copy() for name, key in [
            ('INTERPOLATED', 'interpolated_authored_xyz'),
            ('TASK36_ONLY', 'post_task36_xyz'), ('WITH_FIELD', 'post_field_xyz')]}
    if not np.array_equal(slices['WITH_FIELD'], mesh.xyz):
        raise ValueError('Recorded after-field slice does not match saved actual G2 controls.')
    for name, xyz in slices.items():
        mesh.xyz = xyz
        folder = coherence.ROOT/'DIAGNOSIS/SPAN'/name/'G02'
        coherence.save(folder, mesh, chart, np.zeros(len(chart)),
            dict(candidate=name, input_case='SPAN', source=str(source),
                operation='Materialized saved intermediate controls from the existing G2 operation record; no new growth',
                comparison='Identical G2 control connectivity and mean-fan physical surface policy for all three slices',
                interpolated_reference_limit='Midpoint/mean authored-G1 control interpolation, not a certified identical resampling of every incoming nonplanar face',
                new_field_queries=0, new_subdivision_passes=0,
                investigation='Separate cell placement from the subsequent nearest-outside field response; causal within this saved operation only'),
            dict(materialized_control_xyz=xyz))
        shutil.copy2(__file__, folder/'snapshot_probe.py')


if __name__ == '__main__':
    main()
