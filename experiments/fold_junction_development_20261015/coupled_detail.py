"""Fresh-geometry, coupled V/E/F relief without averaging source positions.

The parent and child cages already exist.  This operator returns only a new
detail displacement in their actual old-vertex / edge / face ID order.  Its
face offsets contribute to the same-generation edge and old-vertex offsets,
as in the completed-face part of modified Catmull--Clark.  It is a CHESHIRE
detail rule, not a reconstruction of the unpublished Digital Grotesque code.
"""
import hashlib

import numpy as np


CHUNK = 65536


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _unit(value):
    lengths = np.linalg.norm(value, axis=1)
    return np.divide(value, lengths[:, None], out=np.zeros_like(value),
                     where=lengths[:, None] > 0.)


def _incident_sum(values, faces, count):
    result = np.zeros((count, values.shape[1]), dtype=float)
    for start in range(0, len(faces), CHUNK):
        q = faces[start:start+CHUNK]
        value = values[start:start+CHUNK]
        for component in range(value.shape[1]):
            result[:, component] += np.bincount(q.ravel(),
                weights=np.repeat(value[:, component], 4), minlength=count)
    return result


def _incident_min(values, faces, count):
    result = np.full(count, np.inf)
    for corner in range(4):
        np.minimum.at(result, faces[:, corner], values)
    return result


def _summary(values):
    return np.quantile(values, [0., .1, .5, .9, .99, 1.]).tolist()


def _reflect(delta, pairs):
    """Canonical vector transport using actual CHILD vertex involutions."""
    count = len(delta)
    ids = np.arange(count)
    if not isinstance(pairs, dict) or set(pairs) != {'X', 'Y'}:
        raise ValueError('mirror_pairs must contain actual child X and Y vertex maps.')
    px, py = (np.asarray(pairs[key]) for key in ('X', 'Y'))
    for key, pair in (('X', px), ('Y', py)):
        if (pair.shape != (count,) or pair.dtype.kind not in 'iu' or
                pair.min() < 0 or pair.max() >= count or
                not np.array_equal(pair[pair], ids)):
            raise ValueError('Invalid actual child reflection map: '+key)
    if not np.array_equal(px[py], py[px]):
        raise ValueError('Actual child X/Y reflections must commute.')
    pxy = px[py]
    representative = np.minimum(np.minimum(ids, px), np.minimum(py, pxy))
    result = delta[representative].copy()
    result[(ids == px[representative]) | (ids == pxy[representative]), 0] *= -1.
    result[(ids == py[representative]) | (ids == pxy[representative]), 1] *= -1.
    result[px == ids, 0] = 0.
    result[py == ids, 1] = 0.
    return result, (px, py)


def split_detail(xyz_parent, faces_parent, faces_child, edges, degree,
                 phase_parent, body_support, height, mirror_pairs=None, *,
                 gain=1.0, weights=(.30, -.10, -.03),
                 maximum_height_fraction=.0025):
    """Return ``(child_detail_delta, JSON_safe_metadata)``.

    ``edges`` is the saved input-edge order, ``degree`` the actual parent
    vertex valence, and phase/support are arrays on the parent vertices.
    Child rows use the established CHESHIRE V/E/F corner convention:
    [previous_edge+nv, parent_vertex, next_edge+nv, parent_face+nv+ne].
    Optional mirror maps refer to ALL child vertices, not parent vertices.

    No subdivision, interpolation of source XYZ, source fairing, topology
    event, or independent axial motif occurs here.  Geometric face scale and
    unsigned normal dispersion are freshly measured from the supplied cage.
    The short-edge and quad-width bounds constrain new relief only; they are
    not a remote-sheet collision or signed-curvature certificate.
    """
    x, q, child = map(np.asarray, (xyz_parent, faces_parent, faces_child))
    edges, degree = np.asarray(edges), np.asarray(degree)
    phase, support = np.asarray(phase_parent), np.asarray(body_support)
    height, gain, maximum_height_fraction = map(float,
        (height, gain, maximum_height_fraction))
    weight = np.asarray(weights, dtype=float)
    if (x.ndim != 2 or x.shape[1] != 3 or x.dtype.kind != 'f' or
            not len(x) or not np.isfinite(x).all()):
        raise ValueError('Finite floating-point actual parent XYZ required.')
    nv, nf, ne = len(x), len(q), len(edges)
    if (q.ndim != 2 or q.shape[1] != 4 or not nf or q.dtype.kind not in 'iu' or
            q.min() < 0 or q.max() >= nv or edges.shape != (ne, 2) or
            not ne or edges.dtype.kind not in 'iu' or edges.min() < 0 or
            edges.max() >= nv or np.any(edges[:, 0] >= edges[:, 1])):
        raise ValueError('Actual parent quads and sorted-endpoint input edges required.')
    if (child.shape != (4*nf, 4) or child.dtype.kind not in 'iu' or
            degree.shape != (nv,) or not np.isfinite(degree).all() or
            np.any(degree < 3) or np.any(degree != np.floor(degree))):
        raise ValueError('Actual closed-quad child rows and parent valences required.')
    if (phase.shape != (nv,) or support.shape != (nv,) or
            not np.isfinite(phase).all() or not np.isfinite(support).all() or
            np.any(support < 0.) or np.any(support > 1.)):
        raise ValueError('Finite parent phase and body_support in [0,1] required.')
    if (not np.isfinite([height, gain, maximum_height_fraction]).all() or
            height <= 0. or gain < 0. or maximum_height_fraction <= 0. or
            weight.shape != (3,) or not np.isfinite(weight).all()):
        raise ValueError('Positive height/cap, nonnegative gain and three finite weights required.')
    face_degree = np.bincount(q.ravel(), minlength=nv)
    edge_degree = np.bincount(edges.ravel(), minlength=nv)
    if not np.array_equal(degree, face_degree) or not np.array_equal(degree, edge_degree):
        raise ValueError('Supplied valence differs from actual closed-quad incidence.')
    # Recover actual parent edge incidence from the saved CHILD IDs rather
    # than sorting/rebuilding a competing topology or assuming an edge order.
    fe = child[:, 2].reshape(nf, 4)-nv
    if fe.min() < 0 or fe.max() >= ne:
        raise ValueError('Child edge-point IDs are outside the saved edge range.')
    for start in range(0, nf, CHUNK):
        end = min(start+CHUNK, nf)
        c = child[4*start:4*end].reshape(end-start, 4, 4)
        expected_face = np.arange(start, end)[:, None]+nv+ne
        expected_edges = np.sort(np.stack((q[start:end],
            np.roll(q[start:end], -1, axis=1)), axis=-1), axis=-1)
        if (not np.array_equal(c[:, :, 1], q[start:end]) or
                not np.all(c[:, :, 3] == expected_face) or
                not np.array_equal(c[:, :, 0], np.roll(fe[start:end], 1, axis=1)+nv) or
                not np.array_equal(edges[fe[start:end]], expected_edges)):
            raise ValueError('Actual saved child V/E/F incidence does not match its parent.')
    if not np.all(np.bincount(fe.ravel(), minlength=ne) == 2):
        raise ValueError('Every actual parent edge must have two incident faces.')
    left, right = np.full(ne, nf, dtype=np.int64), np.full(ne, -1, dtype=np.int64)
    for corner in range(4):
        np.minimum.at(left, fe[:, corner], np.arange(nf))
        np.maximum.at(right, fe[:, corner], np.arange(nf))
    if np.any(left == right):
        raise ValueError('Parent edge repeats inside a single parent face.')
    normals = np.empty((nf, 3))
    scale_face = np.empty(nf)
    phase_face_support = np.empty(nf)
    vertex_modulation = support*(.2+.8*np.sin(phase)**2)
    for start in range(0, nf, CHUNK):
        end = min(start+CHUNK, nf)
        p = x[q[start:end]]
        centre = p.mean(axis=1)
        offsets = p-centre[:, None]
        segments = np.roll(p, -1, axis=1)-p
        lengths = np.linalg.norm(segments, axis=2)
        newell = np.cross(offsets, np.roll(offsets, -1, axis=1)).sum(axis=1)
        if np.any(lengths <= 0.) or np.any(np.linalg.norm(newell, axis=1) <= 0.):
            raise ValueError('Degenerate parent segment or polygon normal; no geometry repair.')
        normals[start:end] = _unit(newell)
        # Twice the smallest centre-to-support-line distance is an incoming
        # physical width; a long, narrow quad cannot use its long edge scale.
        width = 2.*np.min(np.linalg.norm(np.cross(offsets, segments), axis=2)/lengths, axis=1)
        scale_face[start:end] = np.minimum(lengths.min(axis=1), width)
        phase_face_support[start:end] = vertex_modulation[q[start:end]].mean(axis=1)
    mean_normal = _incident_sum(normals, q, nv)/degree[:, None]
    vertex_normals = _unit(mean_normal)
    normal_dispersion = np.clip(1.-np.linalg.norm(mean_normal, axis=1), 0., 1.)
    # A continuous, nonzero response even on strong bends.  It reduces the
    # next relief's strength rather than fairing or locking source geometry.
    curvature_response = 1./(1.+2.*normal_dispersion)
    face_response = np.empty(nf)
    for start in range(0, nf, CHUNK):
        face_response[start:start+CHUNK] = curvature_response[q[start:start+CHUNK]].mean(axis=1)
    edge_lengths = np.linalg.norm(x[edges[:, 1]]-x[edges[:, 0]], axis=1)
    scale_edge = np.minimum(edge_lengths, np.minimum(scale_face[left], scale_face[right]))
    scale_vertex = _incident_min(scale_face, q, nv)
    if (not np.isfinite(scale_face).all() or np.any(scale_face < 0.) or
            not np.isfinite(scale_vertex).all()):
        raise ValueError('Invalid fresh physical detail widths.')
    wf, we, wp = weight*gain
    maximum = height*maximum_height_fraction
    signed_face = np.clip(wf*scale_face*phase_face_support*face_response, -maximum, maximum)
    df = normals*signed_face[:, None]
    edge_normals = (normals[left]+normals[right])/2.
    edge_modulation = vertex_modulation[edges].mean(axis=1)
    edge_response = curvature_response[edges].mean(axis=1)
    signed_edge = np.clip(we*scale_edge*edge_modulation*edge_response, -maximum, maximum)
    de = (df[left]+df[right])/4.+edge_normals*signed_edge[:, None]
    signed_vertex = np.clip(wp*scale_vertex*vertex_modulation*curvature_response, -maximum, maximum)
    # Eq3's completed-face contribution: (mean incident df)/valence.
    dv = _incident_sum(df, q, nv)/(degree*degree)[:, None]
    dv += vertex_normals*signed_vertex[:, None]
    result = np.concatenate((dv, de, df))
    # Keep the complete displacement physically local, including coupling
    # received from a wider neighbouring face.  Clipping affects new detail
    # vectors only; raw V/E/F equations above remain explicit and measurable.
    local_limit = np.concatenate((
        (abs(wf)/degree+abs(wp))*scale_vertex,
        (.5*abs(wf)+abs(we))*scale_edge,
        abs(wf)*scale_face))
    local_limit = np.minimum(maximum, local_limit)
    before = np.linalg.norm(result, axis=1)
    clipped = before > local_limit+1e-14*height
    ratio = np.divide(local_limit, before, out=np.ones_like(before), where=before > 0.)
    result *= np.minimum(1., ratio)[:, None]
    symmetry = 'None; caller retains responsibility for actual model symmetry.'
    if mirror_pairs is not None:
        result, (px, py) = _reflect(result, mirror_pairs)
        # Share a conservative bound across every exact reflection orbit.
        orbit_limit = np.minimum(local_limit, local_limit[px])
        orbit_limit = np.minimum(orbit_limit, orbit_limit[py])
        norm = np.linalg.norm(result, axis=1)
        result *= np.minimum(1., np.divide(orbit_limit, norm,
            out=np.ones_like(norm), where=norm > 0.))[:, None]
        local_limit = orbit_limit
        symmetry = 'Canonical actual child X/Y ID vector transport; fixed plane components zero; conservative orbit minimum cap.'
    norms = np.linalg.norm(result, axis=1)
    if not np.isfinite(result).all() or np.max(norms-local_limit, initial=0.) > 1e-12*height:
        raise ValueError('Nonfinite or over-budget new coupled detail.')
    metadata = dict(implementation='FRESH_COUPLED_VEF_DETAIL_V1',
        parent_vertices=nv, parent_edges=ne, parent_faces=nf,
        child_vertices=len(result), child_faces=len(child),
        gain=gain, weights=dict(wf=float(weight[0]), we=float(weight[1]), wp=float(weight[2])),
        effective_weights=dict(wf=float(wf), we=float(we), wp=float(wp)),
        height=height, maximum_height_fraction=maximum_height_fraction,
        amplitude_cap=maximum, maximum_displacement=float(norms.max(initial=0.)),
        displacement_quantiles=_summary(norms),
        moved_vertices=int(np.count_nonzero(norms)),
        local_width_quantiles=_summary(scale_face),
        normal_dispersion_quantiles=_summary(normal_dispersion),
        curvature_response_quantiles=_summary(curvature_response),
        complete_vector_clipped_vertices=int(np.count_nonzero(clipped)),
        support='mean on each incident face/edge of body_support*(.2+.8*sin(parent_phase)^2); vertex support directly sampled. No hard phase islands.',
        physical_scale='face min(shortest actual edge, twice minimum face-centre to edge-support-line distance); edge min(actual length, incident face widths); vertex minimum incident face width.',
        curvature_response='1/(1+2*(1-norm(mean incident actual unit face normals))); continuous unsigned incoming geometric response.',
        coupling='df=nf*offset_f; de=(df_left+df_right)/4+mean(nf_left,nf_right)*offset_e; dv=sum_incident(df)/valence^2+unit(mean_incident(nf))*offset_v.',
        final_cap='Complete new detail vector norm capped by the sum-of-absolute-weight local width bound and H*maximum_height_fraction; source positions never capped or averaged.',
        fresh_normals=True, source_XYZ_smoothed=False, added_subdivision_passes=0,
        output_is_detail_delta=True, topology_changed=False, symmetry=symmetry,
        parent_xyz_sha256=_hash(x), parent_faces_sha256=_hash(q),
        child_faces_sha256=_hash(child), edge_order_sha256=_hash(edges),
        input_phase_sha256=_hash(phase), input_body_support_sha256=_hash(support),
        fresh_face_normal_sha256=_hash(normals), detail_delta_sha256=_hash(result),
        limitation='Coupled relief only. Local width and normal dispersion do not establish global self-intersection freedom, semantic termination repair or visual improvement. A face coupling contribution may reach an adjacent zero-support old vertex.')
    return result, metadata
