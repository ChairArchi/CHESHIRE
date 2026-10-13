"""One authored CENTRAL_SPINDLE G0 input on the unchanged quad carrier.

This changes the initial design input, including its authored event layout.
It reuses the existing seed_mass.evaluate construction rather than the earlier
SPAN legacy_core.  The downstream selected G1--G7 recipe is not defined or
modified here.  Importing this file does not generate geometry or write files.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import sys
import types

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/'src'))
CASE = INPUT_CASE = 'CENTRAL_SPINDLE'
INPUT_METHOD = 'seed_mass.evaluate; authored input change from prior SPAN legacy_core'
CARRIER = dict(rings=25, sectors=16, radius=.78)

_spec = importlib.util.spec_from_file_location('distinct_input_frozen_seed_mass',
    REPO/'experiments/column_development_20261011/seed_mass.py')
seed = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = seed
_spec.loader.exec_module(seed)

RECIPE = dict(
    radius=[.44, .50, .66, 1.15, 1.85, 1.15, .64, .44],
    valley=.18,
    events=[
        seed.event('CENTRE_X', 0., .50, .18, .30, .10, .20, .28, 1.10, .20),
        seed.event('CENTRE_Y', np.pi/2, .50, .18, .30, .10, .20, .28, 1.10, -.20),
        seed.event('CENTRAL_DIAGONAL', .65, .50, .20, .12, .04, .10, .14, 1.05, .15),
    ],
)


def code_hashes():
    """Hash this input definition and its actual transitive repository modules.

    Frozen spec-loaded modules can be absent from sys.modules, so their module
    globals are followed explicitly.  Third-party package files are excluded.
    """
    queue, seen = [seed], set()
    paths = {Path(__file__).resolve()}
    while queue:
        current = queue.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        filename = getattr(current, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        if not path.is_relative_to(REPO) or path.suffix != '.py':
            continue
        paths.add(path)
        queue.extend(value for value in vars(current).values()
                     if isinstance(value, types.ModuleType))
    return {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def build():
    """Return (actual G0 mesh, unchanged chart, component arrays, recipe copy)."""
    mesh, chart = seed.variation.carrier(copy.deepcopy(CARRIER))
    recipe = copy.deepcopy(RECIPE)
    xyz, parts = seed.evaluate(chart, recipe)
    if (mesh.generation != 0 or mesh.faces.shape != (400, 4) or
            xyz.shape != (402, 3) or chart.shape != xyz.shape or
            not np.isfinite(xyz).all()):
        raise ValueError('The fixed CENTRAL_SPINDLE input did not retain the original unsplit carrier.')
    mesh.xyz = xyz
    mesh.surface = 'mean'
    return mesh, chart, parts, recipe
