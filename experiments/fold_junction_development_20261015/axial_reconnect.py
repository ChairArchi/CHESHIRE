"""Reconnect inherited folded body returns by constrained axial redistribution.

Use a mature source's old-G4 ID prefix, its actual G4 material chart/quads,
SOURCE-face ancestry and exact reflection involutions. This is a localized
Z-coordinate design edit, not coordinate fairing or historical growth replay.
XY, radial protrusion and all connectivity are unchanged at this level.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d


def _pava(values):
    """Least-squares nondecreasing regression; unit weights, O(n)."""
    values = np.asarray(values, dtype=float)
    means = np.empty(len(values), dtype=float)
    weights = np.empty(len(values), dtype=float)
    starts = np.empty(len(values), dtype=np.int64)
    stops = np.empty(len(values), dtype=np.int64)
    count = 0
    for index, value in enumerate(values):
        means[count], weights[count] = value, 1.
        starts[count], stops[count] = index, index+1
        count += 1
        while count > 1 and means[count-2] > means[count-1]:
            weight = weights[count-2]+weights[count-1]
            means[count-2] = (means[count-2]*weights[count-2]+
                              means[count-1]*weights[count-1])/weight
            weights[count-2] = weight
            stops[count-2] = stops[count-1]
            count -= 1
    result = np.empty_like(values)
    for index in range(count):
        result[starts[index]:stops[index]] = means[index]
    return result


def _slope_summary(values, height):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return dict(count=0)
    return dict(count=int(len(values)), negative=int(np.count_nonzero(values < -1e-9)),
                below_015_height=int(np.count_nonzero(values < .15*height)),
                quantiles=np.quantile(values, [0., .01, .05, .5, .95, 1.]).tolist())


def build(xyz, quads, chart, body_face_mask, vertex_pairs, *, strength=1.,
          interior=(.12, .90), minimum_chart_radius=.97,
          floor_height_fraction=.30, trigger_height_fraction=.12,
          interval_padding=.032, monotone_smoothing_sigma=2.):
    """Return ``(axial_displacement_xyz, JSON-safe diagnosis)``.

    ``body_face_mask`` must come from actual event-zero G3 face ancestry,
    transported to these G4 faces. Only vertices whose EVERY incident face is
    SOURCE can move; attached roots, their interface vertices and terminals
    stay fixed. Equal material cross coordinates identify source meridians.

    A suspect tip interval is fitted with a positive-slope isotonic target
    between its exact original endpoints. Positive Gaussian averaging of the
    nondecreasing residual retains monotonicity and softens isotonic steps;
    affine endpoint normalization pins the local endpoints exactly. This is
    local constrained axial redistribution, never XYZ neighbor smoothing.
    ``strength=1`` enforces the fitted interval slope; a partial blend can
    retain axial inversion and is measured honestly in the returned stats.
    """
    xyz, quads, chart = np.asarray(xyz), np.asarray(quads), np.asarray(chart)
    body = np.asarray(body_face_mask, dtype=bool)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or chart.shape != xyz.shape or
            quads.ndim != 2 or quads.shape[1] != 4 or body.shape != (len(quads),)):
        raise ValueError('Actual matching G4 XYZ, material chart, quads and SOURCE face ancestry required.')
    if not np.isfinite(xyz).all() or not np.isfinite(chart).all() or not 0 <= strength <= 1:
        raise ValueError('Finite source and strength in [0,1] required.')
    nv = len(xyz)
    ids = np.arange(nv, dtype=np.int64)
    pairs = {}
    for axis in ('X', 'Y'):
        key = axis if axis in vertex_pairs else 'mirror_'+axis.lower()+'_vertex_pairs'
        p = np.asarray(vertex_pairs[key])
        if (p.shape != (nv,) or p.dtype.kind not in 'iu' or p.min() < 0 or p.max() >= nv or
                not np.array_equal(p[p], ids)):
            raise ValueError('Exact G4 reflection involutions required: '+axis)
        pairs[axis] = p
    if not np.array_equal(pairs['X'][pairs['Y']], pairs['Y'][pairs['X']]):
        raise ValueError('Reflection involutions must commute.')
    height = float(np.ptp(xyz[:, 2]))
    if height <= 0:
        raise ValueError('Positive actual physical height required.')
    incident = np.bincount(quads.ravel(), minlength=nv)
    owned_incident = np.bincount(quads[~body].ravel(), minlength=nv)
    source_vertex = (incident > 0) & (owned_incident == 0)
    radius = np.linalg.norm(chart[:, 1:], axis=1)
    available = source_vertex & (radius > minimum_chart_radius)
    # Exclude cap samples and final terminal turns before interval detection.
    available &= (chart[:, 0] >= interior[0]) & (chart[:, 0] <= interior[1])
    cross_key = np.rint(chart[:, 1:]*1e10).astype(np.int64)
    order = np.lexsort((chart[:, 0], cross_key[:, 1], cross_key[:, 0]))
    key_change = np.any(cross_key[order][1:] != cross_key[order][:-1], axis=1)
    group_bounds = np.r_[0, np.flatnonzero(key_change)+1, nv]
    raw_delta = np.zeros(nv, dtype=float)
    before_slopes, after_edges = [], []
    changed_intervals, skipped = [], []
    source_columns = 0
    for first, last in zip(group_bounds[:-1], group_bounds[1:]):
        column = order[first:last]
        if len(column) < 5 or np.max(radius[column]) <= minimum_chart_radius:
            continue
        source_columns += 1
        t = chart[column, 0]
        # Duplicate chart coordinates are attached-event aliases; never choose
        # an arbitrary XYZ layer. Break those locations out of source runs.
        duplicate = np.r_[False, np.diff(t) <= 1e-10] | np.r_[np.diff(t) <= 1e-10, False]
        usable = available[column] & ~duplicate
        runs = np.flatnonzero(np.diff(np.r_[False, usable, False]))
        for ra, rb in zip(runs[::2], runs[1::2]):
            v = column[ra:rb]
            s, z = chart[v, 0], xyz[v, 2]
            if len(v) < 7:
                continue
            slopes = np.diff(z)/np.diff(s)
            before_slopes.append(slopes)
            after_edges.append(np.column_stack([v[:-1], v[1:]]))
            bad = slopes < trigger_height_fraction*height
            clusters = np.flatnonzero(np.diff(np.r_[False, bad, False]))
            proposed = []
            for ca, cb in zip(clusters[::2], clusters[1::2]):
                left = max(0, int(np.searchsorted(s, s[ca]-interval_padding, side='right')-1))
                right = min(len(s)-1, int(np.searchsorted(s, s[cb]+interval_padding, side='left')))
                while right-left >= 2 and ((z[right]-z[left])/(s[right]-s[left]) < .18*height):
                    if left == 0 and right == len(s)-1:
                        break
                    left, right = max(0, left-2), min(len(s)-1, right+2)
                if proposed and left <= proposed[-1][1]:
                    proposed[-1] = (proposed[-1][0], max(right, proposed[-1][1]))
                else:
                    proposed.append((left, right))
            for left, right in proposed:
                st, old = s[left:right+1], z[left:right+1]
                secant = float((old[-1]-old[0])/(st[-1]-st[0]))
                if secant <= .02*height:
                    skipped.append(dict(first_vertex=int(v[left]), last_vertex=int(v[right]),
                                        reason='No positive feasible endpoint height within SOURCE run.', secant=secant))
                    continue
                floor = min(floor_height_fraction*height, .65*secant)
                baseline = floor*(st-st[0])
                residual = old-baseline
                lower, upper = residual[0], residual[-1]
                monotone = np.r_[lower, np.clip(_pava(residual[1:-1]), lower, upper), upper]
                if monotone_smoothing_sigma > 0 and upper-lower > 1e-12:
                    filtered = gaussian_filter1d(monotone, monotone_smoothing_sigma, mode='nearest')
                    monotone = lower+(filtered-filtered[0])*(upper-lower)/(filtered[-1]-filtered[0])
                target = baseline+monotone
                target[0], target[-1] = old[0], old[-1]
                if np.any(np.diff(target)/np.diff(st) < floor-1e-8):
                    raise ValueError('Positive-slope isotonic target violated its declared constraint.')
                local = strength*(target-old)
                raw_delta[v[left:right+1]] = local
                if np.max(abs(local)) > 1e-10:
                    changed_intervals.append(dict(first_vertex=int(v[left]), last_vertex=int(v[right]),
                        material_t=[float(st[0]), float(st[-1])], samples=int(len(st)),
                        endpoint_secant=secant, target_minimum_slope=float(floor),
                        maximum_abs_z_change=float(abs(local).max())))
    px, py = pairs['X'], pairs['Y']
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, px[py]))
    delta = np.zeros_like(xyz)
    delta[:, 2] = raw_delta[representative]
    # Mirror-union the protected set. If source lineage is asymmetric, do not
    # transfer motion onto a root or boundary merely to impose symmetry.
    movable = available & available[px] & available[py] & available[px[py]]
    delta[~movable] = 0.
    edges = np.concatenate(after_edges) if after_edges else np.empty((0,2),dtype=np.int64)
    before = np.concatenate(before_slopes) if before_slopes else np.empty(0)
    znew = xyz[:,2]+delta[:,2]
    after = ((znew[edges[:,1]]-znew[edges[:,0]])/
             (chart[edges[:,1],0]-chart[edges[:,0],0])) if len(edges) else np.empty(0)
    if not np.isfinite(delta).all() or np.any(delta[:, :2] != 0):
        raise ValueError('Axial-only finite displacement invariant failed.')
    if not np.array_equal(delta[:,2], delta[px,2]) or not np.array_equal(delta[:,2], delta[py,2]):
        raise ValueError('Axial reflection transport failed.')
    stats = dict(operator='LOCAL_SOURCE_MERIDIAN_AXIAL_ISOTONIC_RECONNECTION_V1',
        physical_height=height, strength=float(strength), interior_material_t=list(interior),
        source_faces=int(body.sum()), exclusive_source_vertices=int(source_vertex.sum()),
        eligible_interior_source_vertices=int(available.sum()), material_meridians=source_columns,
        changed_vertices=int(np.count_nonzero(delta[:,2])),
        maximum_abs_z_displacement=float(abs(delta[:,2]).max()),
        displacement_quantiles=np.quantile(abs(delta[:,2]),[0,.5,.9,.99,1]).tolist(),
        material_meridian_slopes_before=_slope_summary(before,height),
        material_meridian_slopes_after=_slope_summary(after,height),
        corrected_intervals=changed_intervals, skipped_intervals=skipped,
        exact_X_Y_preserved=True, exact_radial_envelope_preserved=True,
        attached_root_incident_vertices_fixed=True, boundary_terminal_exclusion=True,
        reflection_transport='Minimum actual X/Y orbit ID; Z vector component is reflection invariant.',
        scope='Local coarse-level source-body axial redistribution; no connectivity change, no XYZ neighbor fairing. Partial strength does not guarantee removal of inversion. No claim of collision freedom or automatic visual improvement.')
    return delta, stats


reconnect = build
