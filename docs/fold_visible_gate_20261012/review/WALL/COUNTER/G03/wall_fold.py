"""Bounded redevelopment of measured longitudinal shoulders into coherent walls.

This deliberately changes interior source geometry. It preserves the native
chart and exact patch boundary, rather than claiming to preserve old fold angles
or implement physical origami. Arbitrary meshes and transverse guides are out of
scope. Actual source samples and fitted target rails are both retained.
"""
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'fold_region_growth_20261012'))
from region_fold import unit


def _fit(values, parameter, degree=3):
    t = (parameter-parameter.mean())/(np.ptp(parameter)/2)
    coefficients = np.polyfit(t, values, degree)
    result = np.column_stack([np.polyval(coefficients[:, i], t) for i in range(3)])
    return result, coefficients


def measure_rails(sampler, parent_guide, angle_degrees=40):
    """Read actual lower/centre/upper rails and pool their XYZ over the region.

    The parent guide only provides its owned material strip. Cubic rail fits
    remove inherited longitudinal facet jitter inside that strip. Depth follows
    the smaller fitted physical shoulder chord after removing its tangential
    component, not arc length inflated by source roughness. Actual chord and arc
    widths are saved separately. The depth cap is half the median actual centre
    radius in the local member coordinate system.
    """
    if str(parent_guide.get('axis', '')) != 'height':
        raise ValueError('Longitudinal height-axis parent guide required.')
    if not np.isfinite(angle_degrees) or not 0 < angle_degrees < 75:
        raise ValueError('A finite target wall angle between 0 and 75 degrees is required.')
    parameter = np.asarray(parent_guide['parameter'], dtype=float)
    lower, middle, upper = [np.asarray(parent_guide[key], dtype=float)
        for key in ('lower_cross', 'guide_cross', 'upper_cross')]
    if (parameter.ndim != 1 or len(parameter) < 5 or
        any(a.shape != parameter.shape for a in (lower, middle, upper)) or
        not np.isfinite(np.stack([parameter, lower, middle, upper])).all() or
        not np.all(np.diff(parameter) > 0) or
        not np.all((lower < middle) & (middle < upper))):
        raise ValueError('Finite ordered parent strip coordinates required.')
    fractions = np.linspace(0., 1., 17)
    cross = np.concatenate([lower[:, None]+(middle-lower)[:, None]*fractions,
        middle[:, None]+(upper-middle)[:, None]*fractions[1:]], axis=1)
    uv = np.stack([np.broadcast_to(parameter[:, None], cross.shape), cross], axis=2)
    source, triangle_ids, barycentric = sampler.sample(uv, records=True)
    lower_xyz, centre_xyz, upper_xyz = source[:, 0], source[:, 16], source[:, -1]
    lower_fit, lower_coef = _fit(lower_xyz, parameter)
    centre_fit, centre_coef = _fit(centre_xyz, parameter)
    upper_fit, upper_coef = _fit(upper_xyz, parameter)
    t = (parameter-parameter.mean())/(np.ptp(parameter)/2)
    tangent = unit(np.column_stack([
        np.polyval(np.polyder(centre_coef[:, i]), t) for i in range(3)]))
    across = upper_fit-lower_fit
    across = unit(across-tangent*np.sum(across*tangent, axis=1)[:, None])
    normal = unit(np.cross(tangent, across))
    radial = np.column_stack([centre_xyz[:, :2], np.zeros(len(parameter))])
    orientation = 1. if np.median(np.sum(normal*radial, axis=1)) >= 0 else -1.
    tangent *= orientation
    normal *= orientation
    perpendicular = lambda vector: vector-tangent*np.sum(vector*tangent, axis=1)[:, None]
    left_width = np.linalg.norm(perpendicular(centre_fit-lower_fit), axis=1)
    right_width = np.linalg.norm(perpendicular(upper_fit-centre_fit), axis=1)
    if np.any(np.minimum(left_width, right_width) <= 1e-10):
        raise ValueError('Measured wall shoulder has no positive physical width.')
    uncapped = np.minimum(left_width, right_width)*np.tan(np.deg2rad(angle_degrees))
    radius = np.linalg.norm(centre_xyz[:, :2], axis=1)
    cap = .5*float(np.median(radius))
    if cap <= 1e-10:
        raise ValueError('Positive member-local source radius required for depth cap.')
    depth = np.minimum(uncapped, cap)
    return dict(axis=np.array('height'), parameter=parameter.copy(),
        lower_cross=lower.copy(), guide_cross=middle.copy(), upper_cross=upper.copy(),
        lower_xyz=lower_xyz, centre_xyz=centre_xyz, upper_xyz=upper_xyz,
        lower_fit=lower_fit, centre_fit=centre_fit, upper_fit=upper_fit,
        lower_fit_coefficients=lower_coef, centre_fit_coefficients=centre_coef,
        upper_fit_coefficients=upper_coef, tangent=tangent, across=across, normal=normal,
        left_width=left_width, right_width=right_width,
        measured_left_chord=np.linalg.norm(centre_xyz-lower_xyz, axis=1),
        measured_right_chord=np.linalg.norm(upper_xyz-centre_xyz, axis=1),
        measured_left_arc=np.linalg.norm(np.diff(source[:, :17], axis=1), axis=2).sum(axis=1),
        measured_right_arc=np.linalg.norm(np.diff(source[:, 16:], axis=1), axis=2).sum(axis=1),
        angle_degrees=np.array(float(angle_degrees)), depth=depth, depth_uncapped=uncapped,
        depth_cap=np.full(len(parameter), cap), depth_capped=uncapped > cap,
        valley_fit=centre_fit-depth[:, None]*normal,
        source_sample_uv=uv, source_sample_xyz=source,
        source_triangle_ids=triangle_ids, source_barycentric=barycentric,
        axial_plateau_fraction=np.array(.6), transverse_plateau_fraction=np.array(.65))


def plateau(q, start):
    """Unit plateau followed by a quintic edge fade; exact zero at/outside 1."""
    q = np.abs(np.asarray(q, dtype=float))
    t = np.clip((q-start)/(1-start), 0., 1.)
    smoothstep = t*t*t*(10.+t*(-15.+6.*t))
    return np.where(q >= 1.-1e-12, 0., np.clip(1.-smoothstep, 0., 1.))


def apply_wall(xyz, chart, rails, mode='DEPTH', strength=1):
    """Return native-control displacement and inspectable overlap arrays.

    DEPTH adds a V-shaped displacement to the unmodified interior. WALL blends
    the same strip into its three-rail ruled target, explicitly replacing source
    residual relief there. Both use the same depth and ownership envelope.
    Overlap uses sum(w*proposal)/max(1,sum(w)); it never adds two full patches.
    Strength is a convex intervention in [0,1]. A single rail dict is accepted.
    """
    xyz, chart = np.asarray(xyz, dtype=float), np.asarray(chart, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.shape != chart.shape:
        raise ValueError('Matching native XYZ and material chart arrays required.')
    if not np.isfinite(xyz).all() or not np.isfinite(chart).all():
        raise ValueError('Finite native XYZ and material chart required.')
    if mode not in ('DEPTH', 'WALL') or not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError('Declared mode and finite convex strength in [0,1] required.')
    if isinstance(rails, dict):
        rails = [rails]
    rails = list(rails)
    if not rails:
        raise ValueError('At least one measured rail region required.')
    canonical = xyz.copy()
    signs = np.where(chart[:, 1:] < 0, -1., 1.)
    canonical[:, :2] *= signs
    parameter = chart[:, 0]
    cross = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    all_weights, all_targets, all_v = [], [], []
    for rail in rails:
        if str(rail.get('axis', '')) != 'height':
            raise ValueError('Longitudinal height-axis rails required.')
        samples = np.asarray(rail['parameter'])
        interp = lambda a: (np.interp(parameter, samples, a) if a.ndim == 1 else
            np.column_stack([np.interp(parameter, samples, a[:, i]) for i in range(3)]))
        lower, middle, upper = [interp(np.asarray(rail[key]))
            for key in ('lower_cross', 'guide_cross', 'upper_cross')]
        if np.any((middle-lower <= 0) | (upper-middle <= 0)):
            raise ValueError('Rail strip has unordered transverse boundaries.')
        distance = cross-middle
        width = np.where(distance < 0, middle-lower, upper-middle)
        v = distance/width
        q = (parameter-(samples[0]+samples[-1])/2)/((samples[-1]-samples[0])/2)
        weight = plateau(q, .6)*plateau(v, .65)
        depth = interp(np.asarray(rail['depth']))
        normal = unit(interp(np.asarray(rail['normal'])))
        valley = interp(np.asarray(rail['centre_fit']))-depth[:, None]*normal
        if mode == 'DEPTH':
            target = canonical-depth[:, None]*np.maximum(0., 1.-np.abs(v))[:, None]*normal
        else:
            left = interp(np.asarray(rail['lower_fit']))
            right = interp(np.asarray(rail['upper_fit']))
            # Clamp only the unused outside target; ownership is zero there.
            vm = np.clip(v, -1., 1.)[:, None]
            target = np.where(vm < 0, (1.+vm)*left-vm*valley,
                (1.-vm)*valley+vm*right)
        all_weights.append(weight)
        all_targets.append(target)
        all_v.append(v)
    weights, targets = np.asarray(all_weights), np.asarray(all_targets)
    numerator = np.sum(weights[:, :, None]*(targets-canonical[None]), axis=0)
    denominator = np.maximum(1., weights.sum(axis=0))
    delta = strength*numerator/denominator[:, None]
    delta[:, :2] *= signs
    delta[np.abs(chart[:, 1]) < 1e-10, 0] = 0.
    delta[np.abs(chart[:, 2]) < 1e-10, 1] = 0.
    delta[np.linalg.norm(chart[:, 1:], axis=1) < 1e-10] = 0.
    return delta, dict(weights=weights, targets=targets, transverse=np.asarray(all_v),
        overlap_denominator=denominator, canonical_numerator=numerator,
        strength=np.array(float(strength)), mode=np.array(mode))
