"""Finite adapter exposing two scales in the existing authored fold profile.

The PCHIP knots/values, rounded angular wave and terminal window are reused
unchanged. bend_height and sweep_span default to the original .05 and .32.
Tags follow the same adjusted material trajectory; no crease-angle locking,
automatic feature extraction, smoothing or physical fold solver is added.
"""
from pathlib import Path
import importlib.util

import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('coherence_preserved_transfer_profile',
    HERE.parent/'fold_transfer_20261012/study.py')
_transfer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_transfer)
_deep = _transfer.prior.smooth_deep
_legacy = _deep.legacy


def _parameters(event):
    h, span, width, direction, sweep = [float(event[key])
        for key in ('height', 'span', 'overlap_width', 'direction', 'sweep')]
    bend = float(event.get('bend_height', .05))
    sweep_span = float(event.get('sweep_span', .32))
    if not np.isfinite([h, span, width, direction, sweep, bend, sweep_span]).all() or min(span, width, sweep_span) <= 0:
        raise ValueError('Finite fold parameters and positive span, width, sweep_span required.')
    return h, span, width, direction, sweep, bend, sweep_span


def smooth_event(chart, event):
    """Original smooth_deep event with only bend/sweep scales exposed."""
    chart = np.asarray(chart, dtype=float)
    s = chart[:, 0]
    theta = np.arctan2(chart[:, 2], chart[:, 1])
    h, span, width, direction, sweep, bend, sweep_span = _parameters(event)
    centre = direction+sweep*np.sin(np.pi*(s-h)/sweep_span)
    centres = [centre, np.pi-centre] if event.get('mirror', False) else [centre]
    e, c, r = event['expansion'], event['constriction'], event['reexpansion']
    rp = [0, .1*e, .62*e, e, .3*e, -c, -.35*c, r, .4*r, 0]
    zp = event['return_depth']*np.array([0, 0, .2, 1, .6, -.6, -1, -.2, 0, 0])
    result = np.zeros((len(chart), 3))
    for a in centres:
        d = _legacy.angle_distance(theta, a)
        q = np.clip(abs(d)/width, 0, 1)
        rounded = (np.sqrt(q*q+.12**2)-.12)/(np.sqrt(1+.12**2)-.12)
        wave = 1-1.5*rounded+.5*rounded**3
        local_h = h+bend*q**1.4
        u = (s-local_h)/span
        radial = _deep.curve(u, rp)
        radial *= wave
        result[:, :2] += radial[:, None]*np.column_stack([np.cos(theta), np.sin(theta)])
        result[:, 2] += _deep.curve(u, zp)*wave
    result *= _legacy.window(s-.5, .40, .49)[:, None]
    result[np.linalg.norm(chart[:, 1:], axis=1) < 1e-10] = 0
    return result


def reflected_event(chart, event):
    """Reuse canonical-quarter evaluation and constructive XY reflection."""
    canonical = chart.copy()
    canonical[:, 1:] = np.abs(canonical[:, 1:])
    delta = smooth_event(canonical, event)
    delta[:, :2] *= np.where(chart[:, 1:] < 0, -1, 1)
    existing = _transfer.prior.helpers.existing
    existing.reflect(delta, chart, existing.symmetry(chart))
    return delta


def profile_mask(chart, events, inner=.003, outer=.010):
    """Existing extrema-tag rule on the same exposed profile trajectory."""
    chart = np.asarray(chart, dtype=float)
    if chart.ndim != 2 or chart.shape[1] != 3 or not np.isfinite(chart).all():
        raise ValueError('Finite material chart triples required.')
    if not np.isfinite([inner, outer]).all() or not 0 <= inner < outer:
        raise ValueError('Finite plateau widths require 0 <= inner < outer.')
    s = chart[:, 0]
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    mask = np.zeros(len(chart))
    plateau = _transfer.memory._plateau
    for event in events:
        h, span, width, direction, sweep, bend, sweep_span = _parameters(event)
        centre = direction+sweep*np.sin(np.pi*(s-h)/sweep_span)
        centres = [centre, np.pi-centre] if event.get('mirror', False) else [centre]
        for a in centres:
            d = np.arctan2(np.sin(theta-a), np.cos(theta-a))
            angular_q = np.abs(d)/width
            angular = plateau(angular_q, .60, .95)
            local_h = h+bend*np.minimum(angular_q, 1.)**1.4
            axial_distance = np.min(np.abs(s[:, None]
                - (local_h[:, None]+span*np.array([-.35, .15, .75]))), axis=1)
            mask = np.maximum(mask, angular*plateau(axial_distance, inner, outer))
    mask[np.linalg.norm(chart[:, 1:], axis=1) < 1e-10] = 0.
    return mask
