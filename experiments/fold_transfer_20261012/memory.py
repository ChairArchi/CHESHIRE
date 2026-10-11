"""Small adapter for existing surface-aware refinement and authored fold tags.

This does not detect creases, lock dihedral angles, or implement origami.
Tags are scalar material bands around declared smooth_deep profile extrema.
No input geometry is averaged, repaired, exported, or otherwise modified here.
"""
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
from cheshire import task36_growth


def _face_sampling(mesh):
    """Match Task36.step/native's inherited V/F diagonal eligibility exactly."""
    q = mesh.faces
    cls = mesh.classes[q]
    iv = np.argmax(cls == 0, axis=1)
    jf = np.argmax(cls == 2, axis=1)
    valid = (((cls == 0).sum(1) == 1) & ((cls == 1).sum(1) == 2)
        & ((cls == 2).sum(1) == 1) & ((iv + 2) % 4 == jf))
    return valid, q[np.arange(len(q)), iv], q[np.arange(len(q)), jf]


def refine(mesh, chart, memory):
    """One existing inactive Task36 split, with matched attribute sampling.

    Mean input: F samples its arithmetic centre. VF input: eligible F samples
    the inherited V/F diagonal midpoint, just as the geometric operator does.
    All old coordinates and old tag values remain exact. Scalar memory (N,)
    and a collection of scalar tags (N,K) retain their respective shapes.
    Output VF fans preserve the incoming fan surface before later deformation;
    a zero tag/displacement alone is not a claim about an entire active patch.
    """
    q = np.asarray(mesh.faces)
    if q.ndim != 2 or q.shape[1] != 4 or np.any(q < 0):
        raise ValueError('Existing closed all-quad control state required.')
    chart = np.asarray(chart, dtype=float)
    memory = np.asarray(memory, dtype=float)
    nv = len(mesh.xyz)
    if chart.shape != (nv, 3) or not np.isfinite(chart).all():
        raise ValueError('One finite material chart triple per input control required.')
    if memory.ndim not in (1, 2) or len(memory) != nv or not np.isfinite(memory).all():
        raise ValueError('Finite scalar tag(s) per input control required.')
    surface = getattr(mesh, 'surface', 'mean')
    if surface not in ('mean', 'vf'):
        raise ValueError('Explicit existing mean or vf input surface required.')
    eligible, vertex_ids, face_ids = _face_sampling(mesh)
    diagonal = eligible if surface == 'vf' else np.zeros(len(q), dtype=bool)
    out, op = task36_growth.step(mesh, active=False, mode='interpolating',
        source='current', surface='vf')
    edges = op['input_edges']

    def interpolate(values):
        face = values[q].mean(1)
        face[diagonal] = ((values[vertex_ids] + values[face_ids]) / 2)[diagonal]
        return np.concatenate([values, values[edges].mean(1), face])

    chart_out = interpolate(chart)
    memory_out = interpolate(memory)
    if not np.array_equal(out.xyz[:nv], mesh.xyz):
        raise ValueError('Inactive refinement unexpectedly moved old controls.')
    if not np.array_equal(memory_out[:nv], memory):
        raise ValueError('Attribute interpolation unexpectedly changed old memory.')
    out.surface = 'vf'
    op.update(refinement_source_surface=np.array(surface),
        refinement_output_surface=np.array('vf'),
        attribute_face_diagonal_mask=diagonal,
        attribute_face_vertex_ids=vertex_ids,
        attribute_face_face_ids=face_ids)
    return out, chart_out, memory_out, op


def _plateau(distance, inner, outer):
    t = np.clip((distance - inner) / (outer - inner), 0., 1.)
    return 1. - t*t*(3. - 2.*t)


def feature_mask(chart, events, inner=.003, outer=.010):
    """Authored extrema tags in normalized height and canonical quarter-angle.

    Axial distance <= inner gives an exact-one plateau; >= outer is zero.
    The angular plateau extends to |d|/width=.60, fading to zero at .95.
    The three tagged radial-profile extrema are u=-.35, +.15 and +.75.
    Widths are normalized material-height units, not world-space thickness.
    Pole samples have no angular direction and receive zero. A finite sample
    set still needs its actual exact-core count recorded by the caller.
    """
    chart = np.asarray(chart, dtype=float)
    if chart.ndim != 2 or chart.shape[1] != 3 or not np.isfinite(chart).all():
        raise ValueError('Finite material chart triples required.')
    if not np.isfinite([inner, outer]).all() or not 0. <= inner < outer:
        raise ValueError('Finite plateau widths require 0 <= inner < outer.')
    s = chart[:, 0]
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    mask = np.zeros(len(chart))
    for event in events:
        h, span, width, direction, sweep = [float(event[key])
            for key in ('height', 'span', 'overlap_width', 'direction', 'sweep')]
        if not np.isfinite([h, span, width, direction, sweep]).all() or min(span, width) <= 0.:
            raise ValueError('Declared finite smooth_deep event parameters required.')
        centre = direction + sweep*np.sin(np.pi*(s-h)/.32)
        centres = [centre, np.pi-centre] if event.get('mirror', False) else [centre]
        for a in centres:
            d = np.arctan2(np.sin(theta-a), np.cos(theta-a))
            angular_q = np.abs(d)/width
            angular = _plateau(angular_q, .60, .95)
            local_h = h + .05*np.minimum(angular_q, 1.)**1.4
            axial_distance = np.min(np.abs(s[:, None]
                - (local_h[:, None] + span*np.array([-.35, .15, .75]))), axis=1)
            mask = np.maximum(mask, angular*_plateau(axial_distance, inner, outer))
    mask[np.linalg.norm(chart[:, 1:], axis=1) < 1e-10] = 0.
    return mask
