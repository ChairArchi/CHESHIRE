"""Small adapter for the preserved radial inside/outside IAAC reconstruction.

The old operator is imported unchanged. Only its radial field powers are set
to [4, 4], matching FIELD_SEED's finite classifier. Movement remains the old
explicit .22 signed XY response; this is not a matched-amplitude ablation of
nearest-outside attraction (.55), nor recovered IAAC numeric source code.
"""
from pathlib import Path
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'terminal_fold_20261011' / 'iaac_repeat.py'
sys.path.insert(0, str(OLD.parent))
spec = importlib.util.spec_from_file_location('preserved_radial_repeat', OLD)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
prior.VARIANTS['radial_io'] = dict(response='radial_inside_outside', powers=[4, 4])
prior.ALGORITHM = 'PRESERVED_RADIAL_IO_SPARSE_N4_ADAPTER_V1'


if __name__ == '__main__':
    if '--variant' not in sys.argv or sys.argv[sys.argv.index('--variant') + 1] != 'radial_io':
        raise ValueError('This adapter deliberately supports only --variant radial_io.')
    # Capture only explicit CLI output arguments; the delegated implementation
    # performs all normal path/signature checks and refuses conflicting output.
    output = Path(sys.argv[sys.argv.index('--output-root') + 1]).resolve()
    family = sys.argv[sys.argv.index('--name') + 1]
    prior.main()
    for stage in sorted((output / family).glob('G[0-9][0-9]')):
        shutil.copy2(__file__, stage / 'radial_probe_recipe.py')
    (output / family / 'adapter.json').write_text(json.dumps(dict(
        source_operator=str(OLD), wrapper=str(Path(__file__).resolve()),
        modification='Runtime radial field recipe override: powers=[4,4]; old file unchanged',
        comparison='Same sparse input/classifier and step budgets as FIELD_SEED; different movement law/coefficient',
        radial_coefficient=.22, nearest_coefficient=.55,
        centre='Column XY axis; Z unchanged; our reconstructed interpretation',
        exact_IAAC_reproduction=False), indent=2), encoding='utf8')
