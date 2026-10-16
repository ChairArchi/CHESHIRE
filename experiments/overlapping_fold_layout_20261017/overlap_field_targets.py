"""Move the two existing finite Mandel fields closer using their original kernel.

The historical classifier already computes finite_inside(field1) OR
finite_inside(field2). This adapter changes only their centres/axial range,
builds actual fresh outside-point grids with the original helper, and binds
each grid to the exact stage parameters. It does not overlap render meshes,
perform CSG, change Task36, change field response, or reuse a mismatched cache.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time

import numpy as np


PARAMETER_KEYS = ('powers', 'centres', 'axial', 'scales', 'orientation',
                  'roll', 'offset_y', 'iterations', 'convention')
_ACTIVE = False


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024**2), b''):
            h.update(block)
    return h.hexdigest()


@dataclass
class OverlapRecord:
    metadata: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)


def _overrides(values):
    values = dict(values)
    if set(values)-{'centres', 'axial'}:
        raise ValueError('This overlapping-field test changes only centres and axial range.')
    if 'centres' in values:
        centres = np.asarray(values['centres'], float)
        if (centres.shape != (2,) or not np.isfinite(centres).all() or
                not 0 < centres[0] < centres[1] < 10):
            raise ValueError('Two ordered interior field centres required.')
        values['centres'] = centres.tolist()
    if 'axial' in values:
        axial = float(values['axial'])
        if not np.isfinite(axial) or not 0 < axial <= 5:
            raise ValueError('Positive bounded axial field range required.')
        values['axial'] = axial
    return values


def _probe(variation, cfg):
    """Actual original classifier calls prove the two-field logical union."""
    xy = np.array([[.30, .30], [.60, .60], [.90, .30], [.30, .90]])
    z = np.linspace(0., 10., 161)
    points = np.column_stack((np.repeat(xy, len(z), axis=0), np.tile(z, len(xy))))
    each = []
    for centre, power in zip(cfg['centres'], cfg['powers']):
        single = dict(cfg, centres=[centre], powers=[power])
        each.append(variation.classify(points, single))
    inside = variation.classify(points, cfg)
    expected = each[0] | each[1]
    if not np.array_equal(inside, expected):
        raise ValueError('Original two-field classifier is not the asserted logical union.')
    evidence = dict(probe_points=points, inside_first=each[0], inside_second=each[1],
                    inside_union=inside)
    metrics = dict(sample_count=len(points), inside_first=int(each[0].sum()),
                   inside_second=int(each[1].sum()), inside_both=int((each[0]&each[1]).sum()),
                   inside_union=int(inside.sum()), union_is_exact_OR=True,
                   scope='Deterministic sparse finite-classifier probes, not volume/geometry certification.')
    return evidence, metrics


@contextmanager
def overlapping_field(early, cfgOverrides, cacheRoot):
    """Yield .metadata/.evidence while actual original G1/G2 fields are evaluated.

    ``early.ancestry_field`` still sets iterations to 4 then 8 and calls its
    original apply_field. Both the field recipe and tree lookup attributes are
    restored on exit, including errors. Only n4/fraction=.55 is supported.
    """
    global _ACTIVE
    if _ACTIVE:
        raise RuntimeError('Nested overlapping-field adapters are not supported.')
    overrides = _overrides(cfgOverrides)
    root = Path(cacheRoot).resolve()
    original_recipe = early.prior.field_recipe
    original_trees = early._field_trees
    base = original_recipe('n4', .55)
    if (base['powers'] != [4, 4] or base['orientation'] != 'Z' or
            base['roll'] != 0 or len(base['centres']) != 2):
        raise ValueError('The actual original n4/Z/no-roll two-field recipe is required.')
    intended = dict(base, **overrides)
    source_paths = [Path(early.prior.__file__), Path(early.prior.helpers.__file__),
                    Path(early.prior.variation.__file__),
                    Path(early.prior.variation.base.__file__),
                    Path(early.ancestry.loop.__file__)]
    kernel_hashes = {str(path.resolve()): _sha(path) for path in source_paths}
    record = OverlapRecord(metadata=dict(
        schema='CHESHIRE_EXISTING_TWO_FINITE_FIELDS_OVERLAP_V1',
        original_cfg=base, cfg_overrides=overrides, intended_cfg=intended,
        original_kernel_code_sha256=kernel_hashes,
        adapter_sha256=_sha(Path(__file__).resolve()), fresh_cache_root=str(root),
        cache_records={}, field_recipe_calls=[],
        mechanism='Original finite_inside(domain1) OR finite_inside(domain2), followed by original nearest sampled outside target response.',
        actual_mesh_CSG=False, render_only_overlap=False, original_kernel_changed=False,
        response_fraction_and_budgets_unchanged=True,
        original_cache_reused=False, attributes_restored=False))

    def recipe(variant, fraction=.55):
        if variant != 'n4' or float(fraction) != .55:
            raise ValueError('Overlapping adapter is limited to original n4/fraction .55.')
        cfg = dict(original_recipe(variant, fraction), **overrides)
        record.metadata['field_recipe_calls'].append(dict(variant=variant, fraction=fraction))
        return cfg

    def trees(cfg, selected):
        iterations = int(cfg['iterations'])
        if iterations not in (4, 8):
            raise ValueError('Only the actual selected G1=4/G2=8 finite iterations are supported.')
        expected = dict(intended, iterations=iterations)
        if cfg != expected:
            raise ValueError('Actual evaluated field config differs from declared overlap.')
        # Do not use the historical cache validator: these are genuinely new
        # field parameters. The original grid/helper constructs matching trees.
        old_cache = Path(selected['metadata']['field_cache']).resolve()
        if root == old_cache or old_cache in root.parents or root in old_cache.parents:
            raise ValueError('New field caches must be separate from the original frozen cache.')
        started = time.perf_counter()
        observed_trees, observed = early.prior.helpers.outside_trees(cfg, root)
        cache = Path(observed).resolve()
        if not cache.is_relative_to(root):
            raise ValueError('Original helper escaped the fresh candidate cache root.')
        field_json, outside_grid = cache/'field.json', cache/'outside_grid.npz'
        info = json.loads(field_json.read_text(encoding='utf8'))
        parameters = {key: cfg[key] for key in PARAMETER_KEYS}
        if info['parameters'] != parameters:
            raise ValueError('Fresh outside cache parameters do not equal the evaluated field.')
        with np.load(outside_grid, allow_pickle=False) as stored:
            points = stored['points']
            if (points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all() or
                    not len(points)):
                raise ValueError('Fresh outside grid is empty or invalid.')
            # Check the whole newly stored finite outside lattice in chunks.
            for first in range(0, len(points), 100_000):
                if early.prior.variation.classify(points[first:first+100_000], cfg).any():
                    raise ValueError('Fresh outside grid contains an inside sample.')
        binding = dict(path=str(cache), field_json_sha256=_sha(field_json),
            outside_grid_sha256=_sha(outside_grid), actual_field_parameters=parameters,
            fresh_cache_root=str(root), fresh_cache_matches_actual_cfg=True,
            every_saved_outside_point_confirmed=True, outside_points=len(points),
            adapter_sha256=record.metadata['adapter_sha256'],
            original_kernel_code_sha256=kernel_hashes,
            original_cache_reused=False, cache_build_and_verify_seconds=time.perf_counter()-started)
        probes, metrics = _probe(early.prior.variation, cfg)
        binding['actual_union_probe'] = metrics
        baseline_probes, baseline_metrics = _probe(early.prior.variation,
                                                  dict(base, iterations=iterations))
        binding['baseline_union_probe'] = baseline_metrics
        binding['extra_overlap_probe_samples'] = metrics['inside_both']-baseline_metrics['inside_both']
        record.metadata['cache_records'][str(iterations)] = binding
        record.evidence.update({'iter'+str(iterations)+'_'+key: value for key, value in probes.items()})
        record.evidence.update({'baseline_iter'+str(iterations)+'_'+key: value
                                for key, value in baseline_probes.items()})
        return observed_trees, binding

    early.prior.field_recipe = recipe
    early._field_trees = trees
    _ACTIVE = True
    try:
        yield record
    finally:
        early.prior.field_recipe = original_recipe
        early._field_trees = original_trees
        _ACTIVE = False
        record.metadata['attributes_restored'] = True
        for path, expected in kernel_hashes.items():
            if _sha(path) != expected:
                raise ValueError('Frozen field kernel source changed during overlap evaluation.')
