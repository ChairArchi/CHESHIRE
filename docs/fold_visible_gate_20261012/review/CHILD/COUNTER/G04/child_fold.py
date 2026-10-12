"""One bounded descendant read from the actual newly redeveloped parent wall.

This is an owned-corridor geometric experiment, not a recursive general engine.
It never searches the old authored event band for a stronger unrelated feature.
"""
import numpy as np
from scipy.signal import find_peaks

from wall_fold import measure_rails


def measure_child(sampler, parent_rails):
    """Find a real parent trough, then measure its outward shoulder on native XYZ.

    Detection uses unfiltered actual triangle samples projected onto the pooled
    parent normal, in +/-20% of its owned material strip around the emitted
    guide. A strict majority of central plateau rays must contain a trough with
    prominence >=4% of parent depth. The descendant uses only their bracketed
    extent; missing interior detections interpolate material trough positions
    between valid rays and are explicitly marked. The chosen shoulder is toward
    upper_cross. Its 35--75% physical arc interval owns the new footprint, with
    its midpoint at 55%. No child support reaches the measured parent valley.
    """
    if str(parent_rails.get('axis', '')) != 'height':
        raise ValueError('Longitudinal parent rails required for a descendant.')
    parameter = np.asarray(parent_rails['parameter'], dtype=float)
    lower, middle, upper = [np.asarray(parent_rails[key], dtype=float)
        for key in ('lower_cross', 'guide_cross', 'upper_cross')]
    depth = np.asarray(parent_rails['depth'], dtype=float)
    normal = np.asarray(parent_rails['normal'], dtype=float)
    if (parameter.ndim != 1 or len(parameter) < 5 or
        any(a.shape != parameter.shape for a in (lower, middle, upper, depth)) or
        normal.shape != (len(parameter), 3) or
        not np.isfinite(np.concatenate([parameter, lower, middle, upper, depth, normal.ravel()])).all() or
        not np.all(np.diff(parameter) > 0) or np.any(depth <= 0) or
        not np.all((lower < middle) & (middle < upper))):
        raise ValueError('Finite ordered parent rails and positive depths required.')
    corridor = .2*(upper-lower)
    search_lower = np.maximum(lower, middle-corridor)
    search_upper = np.minimum(upper, middle+corridor)
    fraction = np.linspace(0., 1., 257)
    cross = search_lower[:, None]+(search_upper-search_lower)[:, None]*fraction
    uv = np.stack([np.broadcast_to(parameter[:, None], cross.shape), cross], axis=2)
    source, source_ids, source_bary = sampler.sample(uv, records=True)
    profile = np.einsum('nkj,nj->nk', source, normal)
    valid = np.zeros(len(parameter), dtype=bool)
    valley = np.full(len(parameter), np.nan)
    prominence = np.zeros(len(parameter))
    trough_index = np.full(len(parameter), -1, dtype=int)
    for i in range(len(parameter)):
        peaks, properties = find_peaks(-profile[i], prominence=.04*depth[i])
        if len(peaks):
            # Only emitted-guide proximity selects among actual detected peaks;
            # the strongest unrelated macro relief is never an alternate seed.
            selected = np.argmin(np.abs(cross[i, peaks]-middle[i]))
            index = peaks[selected]
            valley[i] = cross[i, index]
            prominence[i] = properties['prominences'][selected]
            trough_index[i] = index
            valid[i] = True
    q = np.abs((parameter-parameter.mean())/(np.ptp(parameter)/2))
    central = q <= .6+1e-12
    detected = central & valid
    if detected.sum() <= central.sum()/2:
        raise ValueError(f'Actual parent trough absent on majority of central rays: {detected.sum()}/{central.sum()}.')
    valid_indices = np.flatnonzero(detected)
    first, last = valid_indices[0], valid_indices[-1]
    if last-first+1 < 5:
        raise ValueError('Too little bracketed actual parent extent for a child.')
    selected = np.arange(first, last+1)
    child_parameter = parameter[selected]
    measured_mask = valid[selected]
    # Interpolation is strictly between detected endpoints. No endpoint
    # extrapolation and no synthetic trough outside the owned corridor.
    parent_valley = np.interp(child_parameter, parameter[valid_indices], valley[valid_indices])
    outward_upper = upper[selected]
    wall_fraction = np.linspace(0., 1., 129)
    wall_cross = parent_valley[:, None]+(outward_upper-parent_valley)[:, None]*wall_fraction
    wall_uv = np.stack([np.broadcast_to(child_parameter[:, None], wall_cross.shape), wall_cross], axis=2)
    wall_xyz, wall_ids, wall_bary = sampler.sample(wall_uv, records=True)
    arc = np.concatenate([np.zeros((len(selected), 1)),
        np.cumsum(np.linalg.norm(np.diff(wall_xyz, axis=1), axis=2), axis=1)], axis=1)
    if np.any(arc[:, -1] <= 1e-10):
        raise ValueError('Actual parent outward shoulder has no physical arc.')
    raw = np.array([[np.interp(f*arc[i, -1], arc[i], wall_cross[i])
        for f in (.35, .55, .75)] for i in range(len(selected))])
    t = (child_parameter-child_parameter.mean())/(np.ptp(child_parameter)/2)
    # Material coordinates retain their actual measured arc locations. A low
    # degree fit in this nonlinear chart can violate physical exclusion margins
    # despite looking smooth in UV. Only the actual XYZ rails are pooled by
    # measure_rails below; interpolation between rays remains piecewise linear.
    diagnostic_coefficients = np.polyfit(t, raw, 2)
    owned_coordinates = raw
    child_lower, child_middle, child_upper = owned_coordinates.T
    if not np.all((parent_valley < child_lower) & (child_lower < child_middle) &
        (child_middle < child_upper) & (child_upper < outward_upper)):
        raise ValueError('Pooled child footprint escaped its actual owned shoulder.')
    pooled_arc_fraction = np.array([[np.interp(value, wall_cross[i], arc[i])/arc[i, -1]
        for value in owned_coordinates[i]] for i in range(len(selected))])
    if np.any(pooled_arc_fraction[:, 0] < .25):
        raise ValueError('Pooled child footprint infringes parent-valley exclusion margin.')
    width_fraction = pooled_arc_fraction[:, 2]-pooled_arc_fraction[:, 0]
    if np.any((width_fraction < .25) | (width_fraction > .55)):
        raise ValueError('Pooled child footprint has ceased to be a smaller shoulder interval.')
    child_guide = dict(axis=np.array('height'), parameter=child_parameter,
        lower_cross=child_lower, guide_cross=child_middle, upper_cross=child_upper)
    result = measure_rails(sampler, child_guide, angle_degrees=30.)
    own_cap = result['depth_cap'].copy()
    parent_depth = depth[selected]
    cap = np.minimum(own_cap, .4*parent_depth)
    result['depth_cap'] = cap
    result['depth'] = np.minimum(result['depth_uncapped'], cap)
    result['depth_capped'] = result['depth_uncapped'] > cap
    result['valley_fit'] = result['centre_fit']-result['depth'][:, None]*result['normal']
    result.update(parent_depth=parent_depth, member_radius_depth_cap=own_cap,
        parent_depth_ratio_cap=np.array(.4), parent_valley_cross=parent_valley,
        parent_valley_measured_mask=measured_mask,
        parent_upper_cross=outward_upper, child_owned_arc_fraction=pooled_arc_fraction,
        measured_child_cross=raw,
        diagnostic_child_material_fit_coefficients=diagnostic_coefficients,
        child_material_coordinate_rule=np.array('Measured physical-arc positions; piecewise linear between rays. XYZ rails alone use cubic pooling.'),
        parent_search_parameter=parameter, parent_search_lower_cross=search_lower,
        parent_search_upper_cross=search_upper, parent_search_valid=valid,
        parent_search_central=central, parent_search_trough_indices=trough_index,
        parent_search_prominence=prominence, parent_search_profile=profile,
        parent_search_uv=uv, parent_search_xyz=source,
        parent_search_triangle_ids=source_ids, parent_search_barycentric=source_bary,
        parent_shoulder_uv=wall_uv, parent_shoulder_xyz=wall_xyz,
        parent_shoulder_triangle_ids=wall_ids, parent_shoulder_barycentric=wall_bary,
        parent_shoulder_arc=arc,
        central_parent_detection_count=np.array(int(detected.sum())),
        central_parent_ray_count=np.array(int(central.sum())),
        interpolated_ray_count=np.array(int((~measured_mask).sum())),
        parent_corridor_fraction=np.array(.2), parent_prominence_depth_ratio=np.array(.04),
        parent_exclusion_minimum_arc_fraction=np.array(.25),
        interpolation_policy=np.array('Bracketed material trough coordinates only; actual native shoulder samples retained'),
        lineage=np.array('One actual measured WALL-parent shoulder to one bounded child; no general recurrence'))
    return result
