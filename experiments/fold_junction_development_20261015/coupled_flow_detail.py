"""Continuous inherited-phase relief with balanced completed-face coupling.

There is no cell-centre extrusion motif: a constant phase/amplitude and a
constant normal produce exactly the same offset on old vertices, new edges
and new faces.  Only newly requested detail vectors are returned.  Source XYZ
is used to measure fresh normals and phase gradients and is never averaged.
"""
import hashlib

import numpy as np


CHUNK = 65536


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _unit(value):
    norm = np.linalg.norm(value, axis=1)
    return np.divide(value, norm[:, None], out=np.zeros_like(value), where=norm[:, None] > 0.)


def _sum(values, faces, count):
    values = np.asarray(values)
    scalar = values.ndim == 1
    if scalar:
        values = values[:, None]
    result = np.zeros((count, values.shape[1]))
    for start in range(0, len(faces), CHUNK):
        q = faces[start:start+CHUNK]
        for component in range(values.shape[1]):
            result[:, component] += np.bincount(q.ravel(),
                weights=np.repeat(values[start:start+CHUNK, component], 4), minlength=count)
    return result[:, 0] if scalar else result


def _face_mean(value, faces):
    result = np.empty(len(faces))
    for start in range(0, len(faces), CHUNK):
        result[start:start+CHUNK] = value[faces[start:start+CHUNK]].mean(axis=1)
    return result


def _quantiles(value):
    return np.quantile(value, [0., .1, .5, .9, .99, 1.]).tolist()


def _reflection(delta, caps, maps):
    count = len(delta)
    ids = np.arange(count)
    if not isinstance(maps, dict) or set(maps) != {'X', 'Y'}:
        raise ValueError('Actual child X/Y maps required.')
    px, py = (np.asarray(maps[key]) for key in ('X', 'Y'))
    for key, pair in (('X', px), ('Y', py)):
        if (pair.shape != (count,) or pair.dtype.kind not in 'iu' or
                pair.min() < 0 or pair.max() >= count or
                not np.array_equal(pair[pair], ids)):
            raise ValueError('Invalid actual child reflection map '+key)
    if not np.array_equal(px[py], py[px]):
        raise ValueError('Actual child X/Y involutions must commute.')
    both = px[py]
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, both))
    reflected = delta[representative].copy()
    reflected[(ids == px[representative]) | (ids == both[representative]), 0] *= -1.
    reflected[(ids == py[representative]) | (ids == both[representative]), 1] *= -1.
    reflected[px == ids, 0] = 0.
    reflected[py == ids, 1] = 0.
    orbit_cap = np.minimum(caps, caps[px])
    orbit_cap = np.minimum(orbit_cap, orbit_cap[py])
    return reflected, orbit_cap


def split_detail(xyz_parent, faces_parent, faces_child, edges, degree,
                 phase_parent, body_support, height, mirror_pairs=None, *,
                 gain=1.0, maximum_height_fraction=.0025,
                 phase_multiplier=2.0, phase_warp=.30,
                 amplitude_fraction=.12):
    """Return ``(delta_child, metadata)`` in the actual V/E/F prefix order.

    Parent phase is UNWRAPPED, not atan2-wrapped.  Actual edge/face phases and
    positive amplitude associations are obtained through the supplied birth
    maps.  ``phase_multiplier`` can be 2/4/8 on successive existing levels;
    these are frequencies, not extra subdivision generations.  Optional
    reflection maps refer to all CHILD vertices.  The height cap and local
    intrinsic phase spacing constrain the new delta, never the source XYZ.
    """
    x, q, child, edges, degree = map(np.asarray,
        (xyz_parent, faces_parent, faces_child, edges, degree))
    phase, support = np.asarray(phase_parent), np.asarray(body_support)
    height, gain, maximum_height_fraction, multiplier, warp, amplitude_fraction = map(float,
        (height, gain, maximum_height_fraction, phase_multiplier, phase_warp, amplitude_fraction))
    if (x.ndim != 2 or x.shape[1] != 3 or x.dtype.kind != 'f' or
            not len(x) or not np.isfinite(x).all() or q.ndim != 2 or
            q.shape[1] != 4 or not len(q) or q.dtype.kind not in 'iu'):
        raise ValueError('Finite floating parent XYZ and actual all-quad faces required.')
    nv, nf, ne = len(x), len(q), len(edges)
    if (q.min() < 0 or q.max() >= nv or edges.shape != (ne, 2) or not ne or
            edges.dtype.kind not in 'iu' or edges.min() < 0 or edges.max() >= nv or
            np.any(edges[:, 0] >= edges[:, 1]) or child.shape != (4*nf, 4) or
            child.dtype.kind not in 'iu' or degree.shape != (nv,) or np.any(degree < 3)):
        raise ValueError('Actual closed parent edge/child correspondence and valences required.')
    if (phase.shape != (nv,) or support.shape != (nv,) or not np.isfinite(phase).all() or
            not np.isfinite(support).all() or np.any(support < 0.) or np.any(support > 1.)):
        raise ValueError('Finite unwrapped parent phase and support in [0,1] required.')
    if (not np.isfinite([height, gain, maximum_height_fraction, multiplier, warp, amplitude_fraction]).all() or
            min(height, maximum_height_fraction, multiplier) <= 0. or
            gain < 0. or amplitude_fraction < 0. or abs(warp) >= multiplier):
        raise ValueError('Finite nonnegative gain/amplitude and positive monotone phase frequency required.')
    observed_degree = np.bincount(q.ravel(), minlength=nv)
    if (not np.array_equal(degree, observed_degree) or
            not np.array_equal(degree, np.bincount(edges.ravel(), minlength=nv))):
        raise ValueError('Parent valence differs from actual closed-quad incidence.')
    fe = child[:, 2].reshape(nf, 4)-nv
    if fe.min() < 0 or fe.max() >= ne:
        raise ValueError('Actual child edge IDs are outside saved input-edge order.')
    for start in range(0, nf, CHUNK):
        stop = min(start+CHUNK, nf)
        rows = child[4*start:4*stop].reshape(-1, 4, 4)
        parent = q[start:stop]
        endpoints = np.sort(np.stack((parent, np.roll(parent, -1, axis=1)), axis=-1), axis=-1)
        if (not np.array_equal(rows[:, :, 1], parent) or
                not np.all(rows[:, :, 3] == (nv+ne+np.arange(start, stop))[:, None]) or
                not np.array_equal(rows[:, :, 0]-nv, np.roll(fe[start:stop], 1, axis=1)) or
                not np.array_equal(edges[fe[start:stop]], endpoints)):
            raise ValueError('Saved V/E/F child incidence differs from actual parent.')
    if not np.all(np.bincount(fe.ravel(), minlength=ne) == 2):
        raise ValueError('Every actual parent edge requires two incident faces.')
    left, right = np.full(ne, nf, np.int64), np.full(ne, -1, np.int64)
    face_ids = np.arange(nf)
    for corner in range(4):
        np.minimum.at(left, fe[:, corner], face_ids)
        np.maximum.at(right, fe[:, corner], face_ids)
    if np.any(left == right):
        raise ValueError('Repeated parent edge in one face.')
    normals, g2 = np.empty((nf, 3)), np.zeros(nf)
    invalid_gram, degenerate_normals = 0, 0
    for start in range(0, nf, CHUNK):
        stop = min(start+CHUNK, nf)
        points = x[q[start:stop]]
        rel = points-points.mean(axis=1)[:, None]
        newell = np.cross(rel, np.roll(rel, -1, axis=1)).sum(axis=1)
        degenerate_normals += int(np.count_nonzero(np.linalg.norm(newell, axis=1) == 0.))
        normals[start:stop] = _unit(newell)
        e1, e2 = points[:, 1]-points[:, 3], points[:, 2]-points[:, 0]
        a = np.einsum('ij,ij->i', e1, e1)
        b = np.einsum('ij,ij->i', e1, e2)
        c = np.einsum('ij,ij->i', e2, e2)
        determinant, ac = a*c-b*b, a*c
        d1 = phase[q[start:stop, 1]]-phase[q[start:stop, 3]]
        d2 = phase[q[start:stop, 2]]-phase[q[start:stop, 0]]
        ratio = np.divide(determinant, ac, out=np.zeros_like(ac), where=ac > 0.)
        valid = (determinant > 0.) & (ratio >= 1e-10)
        numerator = c*d1*d1-2*b*d1*d2+a*d2*d2
        block = np.divide(numerator, determinant, out=np.zeros_like(numerator), where=valid)
        valid &= np.isfinite(block) & (block >= 0.)
        invalid_gram += int(np.count_nonzero(~valid))
        # An invalid sliver receives no gradient observation.  Its incident
        # neighbour estimates remain available; no coordinates are repaired.
        block[~valid] = 0.
        g2[start:stop] = block
    if degenerate_normals:
        raise ValueError('Degenerate actual parent polygon normal; no fallback normal.')
    vertex_normal_mean = _sum(normals, q, nv)/degree[:, None]
    vertex_normals = _unit(vertex_normal_mean)
    variation = np.clip(1.-np.linalg.norm(vertex_normal_mean, axis=1), 0., 1.)
    curvature_response = 1./(1.+1.5*variation)
    gradient = np.sqrt(_sum(g2, q, nv)/degree)
    effective_gradient = gradient*(multiplier+warp*np.cos(phase))
    width = np.divide(1.8, effective_gradient,
        out=np.full(nv, .08*height/multiplier), where=effective_gradient > 0.)
    width = np.minimum(width, .08*height/multiplier)
    if not np.isfinite(width).all() or np.any(width < 0.):
        raise ValueError('Invalid actual intrinsic phase width.')
    cap = height*maximum_height_fraction
    amplitude = np.minimum(gain*amplitude_fraction*width, cap)*curvature_response
    # V/E/F share the same positive amplitude field.  Face and edge samples
    # are its actual positive birth associations, not per-cell height scales.
    amp_edge, amp_face = amplitude[edges].mean(axis=1), _face_mean(amplitude, q)
    phase_edge, phase_face = phase[edges].mean(axis=1), _face_mean(phase, q)
    support_edge, support_face = support[edges].mean(axis=1), _face_mean(support, q)
    def scalar(p, amp, region):
        occupancy = .15+.85*np.sin(p)**2
        return amp*region*occupancy*np.cos(multiplier*p+warp*np.sin(p))
    av = scalar(phase, amplitude, support)
    ae = scalar(phase_edge, amp_edge, support_edge)
    af = scalar(phase_face, amp_face, support_face)
    df = normals*af[:, None]
    edge_normals = (normals[left]+normals[right])/2.
    de = (df[left]+df[right])/4.+edge_normals*(.5*ae)[:, None]
    dv = _sum(df, q, nv)/(degree*degree)[:, None]
    dv += vertex_normals*((1.-1./degree)*av)[:, None]
    delta = np.concatenate((dv, de, df))
    # These bounds include the complete same-generation face contributions,
    # not just the independent edge/vertex term.  At constant field all three
    # classes have the same bound and exactly the same requested vector.
    cap_face = amp_face*support_face
    cap_edge = (cap_face[left]+cap_face[right])/4.+.5*amp_edge*support_edge
    cap_vertex = _sum(cap_face, q, nv)/(degree*degree)+(1.-1./degree)*amplitude*support
    limits = np.minimum(cap, np.concatenate((cap_vertex, cap_edge, cap_face)))
    symmetry = 'Not requested; source symmetry remains the caller responsibility.'
    if mirror_pairs is not None:
        delta, limits = _reflection(delta, limits, mirror_pairs)
        symmetry = 'Canonical actual child X/Y ID vector transport and conservative orbit bound.'
    norm = np.linalg.norm(delta, axis=1)
    clipped = norm > limits+1e-14*height
    delta *= np.minimum(1., np.divide(limits, norm,
        out=np.ones_like(norm), where=norm > 0.))[:, None]
    norm = np.linalg.norm(delta, axis=1)
    if not np.isfinite(delta).all() or np.max(norm-limits, initial=0.) > 1e-12*height:
        raise ValueError('Nonfinite or over-budget balanced flow detail.')
    metadata = dict(implementation='BALANCED_CONTINUOUS_PARENT_PHASE_FLOW_DETAIL_V1',
        parent_vertices=nv, parent_edges=ne, parent_faces=nf,
        child_vertices=len(delta), child_faces=len(child),
        gain=gain, phase_multiplier=multiplier, phase_warp=warp,
        amplitude_fraction=amplitude_fraction, maximum_height_fraction=maximum_height_fraction,
        height=height, amplitude_cap=cap, maximum_displacement=float(norm.max(initial=0.)),
        displacement_quantiles=_quantiles(norm), moved_vertices=int(np.count_nonzero(norm)),
        phase_gradient_quantiles=_quantiles(gradient), physical_phase_width_quantiles=_quantiles(width),
        parent_amplitude_quantiles=_quantiles(amplitude), normal_dispersion_quantiles=_quantiles(variation),
        invalid_gram_faces=invalid_gram, degenerate_normal_faces=degenerate_normals,
        complete_vector_clipped_vertices=int(np.count_nonzero(clipped)),
        relief='A=positive_amplitude*body_support*(.15+.85*sin(phi)^2)*cos(multiplier*phi+warp*sin(phi)); actual unwrapped parent phase, no independent axial motif.',
        physical_scale='Parent quad diagonal Gram phase-gradient solve; vertex incident RMS gradient; width=min(1.8/((multiplier+warp*cos(phi))*gradient),.08H/multiplier). Positive width/amplitude associations are carried through actual V/E/F IDs.',
        curvature_response='1/(1+1.5*(1-norm(mean incident actual unit face normals))); continuous fresh incoming normal dispersion.',
        coupling='df=nf*Af; de=(df_left+df_right)/4+mean(nf_left,nf_right)*(.5*Ae); dv=sum_incident(df)/valence^2+unit(mean_incident(nf))*((1-1/valence)*Av).',
        constant_field_balance='For constant A and constant n, df=de=dv=n*A exactly, at every valence; no systematic V/E/F cell-centre contrast.',
        source_XYZ_smoothed=False, fresh_normals=True, output_is_detail_delta=True,
        added_subdivision_passes=0, topology_changed=False, symmetry=symmetry,
        parent_xyz_sha256=_hash(x), parent_faces_sha256=_hash(q),
        child_faces_sha256=_hash(child), edge_order_sha256=_hash(edges),
        input_phase_sha256=_hash(phase), input_body_support_sha256=_hash(support),
        fresh_face_normal_sha256=_hash(normals), detail_delta_sha256=_hash(delta),
        limitations='Continuous phase relief and raw algebraic constant-field balance do not certify aesthetic improvement, terminal/root reconnection or global collision freedom. Invalid Gram observations are excluded by zero contribution; support may reach adjacent nodes through genuine face coupling.')
    return delta, metadata
