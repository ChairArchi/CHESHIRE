"""A bounded 2x2 input/field comparison, not a recovered IAAC experiment.

Identical 25x32 cylinder topology, two bilinear refinements, one presentation CC.
Only the input coordinates and field enable switch differ between the 4 cases.
"""
from pathlib import Path
import argparse
import shutil
import study as base
import column_study as column
import variation_study as variation
from cheshire import task33_folds as folds
from cheshire.reference_subdivision import subdivide, topology


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directional-inputs', nargs='*')
    parser.add_argument('--field-only', action='store_true')
    args = parser.parse_args()
    root = base.ArtifactRoot(Path(base.DEFAULT_ROOT))
    cfg = variation.recipe('INPUT_FIELD_TEST', rings=25, sectors=32)
    trees, field_path = variation.grid(cfg, root)
    inputs = args.directional_inputs or ('CYLINDER', 'DIRECTIONAL')
    for input_name in inputs:
        for enabled in ((True,) if args.field_only else (False, True)):
            name = input_name + ('_FIELD' if enabled else '_NO_FIELD')
            family = 'input_field/' + name
            if input_name == 'CYLINDER':
                mesh, chart = variation.carrier(cfg)
                source = 'Same topology plain cylinder, radius .78, height 10'
            else:
                input_id = 'D02_INTERLEAVED' if input_name == 'DIRECTIONAL' else input_name
                source_path = 'directional/' + input_id + '/CAGE'
                mesh, chart = base.load(root.resolve(source_path))
                source = source_path + ' (explicitly modelled, not fractal)'
            metadata = dict(input_source=source, field_enabled=enabled, recipe=cfg,
                            field_path=field_path, experiment='2x2 input versus field',
                            source_status='CHESHIRE reconstruction test, not recovered IAAC code')
            for generation in range(3):
                stage = 'INPUT' if generation == 0 else f'G{generation:02}'
                target = root.resolve(family + '/' + stage)
                if generation:
                    if enabled:
                        mesh, chart, record, meta = variation.advance(mesh, chart, cfg, generation, trees)
                    else:
                        mesh, state, _, _ = folds.refine(mesh, dict(carrier=mesh.rest, chart=chart),
                                                        carrier_smoothing=False, smooth_geometry=False)
                        chart = state['chart']; column.reflect(mesh, chart)
                        record = {}; meta = dict(operation='Bilinear quad refinement only',
                                                 CC_coordinate_averaging=False,
                                                 separate_geometric_smoothing=False)
                else:
                    record = {}; meta = dict(operation='Input coordinates only')
                previous = 'INPUT' if generation == 1 else f'G{generation-1:02}'
                if not (target / 'checkpoint.npz').exists():
                    base.save(root, family, stage, mesh, chart, record,
                              dict(meta, **metadata, parent=None if generation == 0 else family + '/' + previous),
                              mirror_callback=column.reflect)
                    shutil.copy2(__file__, target / 'input_field_recipe.py')
                print(name, stage, len(mesh.xyz), len(mesh.faces), flush=True)
            t = topology(mesh)
            curved, _, _ = subdivide(mesh, {})
            chart = base.interpolate_chart(chart, t, len(mesh.faces))
            column.reflect(curved, chart)
            target = root.resolve(family + '/G02_CC')
            if not (target / 'checkpoint.npz').exists():
                base.save(root, family, 'G02_CC', curved, chart, {}, dict(metadata,
                          parent=family + '/G02', operation='One neutral CC presentation pass',
                          CC_coordinate_averaging=True, separate_geometric_smoothing=False,
                          fractal_growth_generation=False), mirror_callback=column.reflect)
                shutil.copy2(__file__, target / 'input_field_recipe.py')


if __name__ == '__main__':
    main()
