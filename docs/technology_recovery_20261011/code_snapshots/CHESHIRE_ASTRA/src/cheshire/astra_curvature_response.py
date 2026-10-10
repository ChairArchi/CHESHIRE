"""Coherent curvature response hypothesis on exact midpoint triangle refinement.

Signed edge-angle curvature and scalar graph averaging are geometric features;
no XYZ averaging is performed. Nonmonotonic response is our research hypothesis,
not an established ridge-splitting or Digital Grotesque reconstruction method.
All lengths (radius, amplitude, reference_length) use the input coordinate unit.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology, mean_incident
from .astra_rotating import features


def _normals(xyz, faces):
    p = xyz[faces]
    cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    normal = np.column_stack([np.bincount(faces.ravel(),
        weights=np.repeat(cross[:, k], 3), minlength=len(xyz)) for k in range(3)])
    length = np.linalg.norm(normal, axis=1)
    if np.any(length <= 1e-15):
        raise ValueError('Undefined current vertex normal.')
    return normal / length[:, None]


def _curvature(mesh, radius, iterations, reference_length):
    t, f, feat = features(mesh)
    q = mesh.faces[:, :3]; e = t['edges']; nv = len(mesh.xyz)
    area = np.bincount(q.ravel(), weights=np.repeat(f['area'] / 3, 3), minlength=nv)
    if np.any(area <= 1e-15):
        raise ValueError('Zero observed vertex area.')
    integrated = np.bincount(e.ravel(), weights=np.repeat(f['lengths'] * feat['edge_angle'] / 4, 2), minlength=nv)
    curvature = integrated / area
    initial = curvature * reference_length
    scalar = initial.copy(); diffusion_distance2 = np.zeros(nv)
    alpha = np.zeros(nv); weight = np.zeros(len(e))
    if radius > 0 and iterations:
        lengths = f['lengths']
        weight = np.exp(-.5 * (lengths / radius) ** 2) / lengths ** 2
        ids = e.ravel(); neighbors = e[:, ::-1].ravel(); weights = np.repeat(weight, 2)
        total = np.bincount(ids, weights=weights, minlength=nv)
        dt = radius ** 2 / (2 * iterations)
        alpha = np.minimum(.45, dt * total)
        mean_length2 = np.divide(np.bincount(ids, weights=np.repeat(weight * lengths ** 2, 2), minlength=nv), total, out=np.zeros(nv), where=total > 0)
        for _ in range(iterations):
            avg = np.divide(np.bincount(ids, weights=weights * scalar[neighbors], minlength=nv), total, out=scalar.copy(), where=total > 0)
            scalar += alpha * (avg - scalar)
        # A local RMS random-walk-step estimate, not a geodesic kernel radius.
        diffusion_distance2 = iterations * alpha * mean_length2
    return t, dict(raw_signed_curvature=curvature, raw_dimensionless_q=initial,
                  observed_vertex_area=area, observed_edge_angle=feat['edge_angle'],
                  observed_edge_length=f['lengths'], diffused_q=scalar,
                  diffusion_alpha=alpha, diffusion_edge_weight=weight,
                  diffusion_local_rms_distance=np.sqrt(diffusion_distance2))


def step(mesh, *, amplitude=15., radius=100., reference_length=100.,
         iterations=6, response='nonmonotonic', q0=1., source='current', polarity=1.):
    if not np.isfinite([amplitude, radius, reference_length, q0, polarity]).all():
        raise ValueError('Nonfinite parameter.')
    if amplitude < 0 or radius < 0 or reference_length <= 0 or not 0 < q0 <= 100:
        raise ValueError('Invalid physical parameter range.')
    if isinstance(iterations, bool) or not isinstance(iterations, (int, np.integer)) or not 0 <= iterations <= 32:
        raise ValueError('Use an integer of 0..32 bounded scalar iterations.')
    if response not in ('monotonic', 'nonmonotonic') or source not in ('current', 'rest') or polarity not in (-1., 1.):
        raise ValueError('Unknown response/source/polarity.')
    topology_actual, _, _ = features(mesh)
    observed = mesh if source == 'current' else ArrayMesh(mesh.rest, mesh.faces,
        mesh.classes, mesh.rest, mesh.anchors, mesh.generation)
    t, feature = _curvature(observed, radius, iterations, reference_length)
    x = mesh.xyz; q = mesh.faces[:, :3]; nv = len(x); e = t['edges']; ne = len(e)
    base = np.concatenate([x, x[e].mean(1)])
    rest = np.concatenate([mesh.rest, mesh.rest[e].mean(1)])
    mid = t['fe'][:, :3] + nv
    a, b, c = q.T; ab, bc, ca = mid.T
    faces = np.stack([np.column_stack([a, ab, ca]), np.column_stack([ab, b, bc]),
                      np.column_stack([ca, bc, c]), np.column_stack([ab, bc, ca])], axis=1).reshape(-1, 3)
    scalar = feature['diffused_q']
    transferred = np.r_[scalar, scalar[e].mean(1)]
    if response == 'monotonic':
        resolved = np.tanh(transferred)
    else:
        # Clipping only a saturated scalar argument avoids cubic overflow;
        # no coordinate clamp or bounding box is applied.
        bounded_q = np.clip(transferred, -64 * q0, 64 * q0)
        resolved = np.tanh(bounded_q * (1 - (bounded_q / q0) ** 2))
    normals = _normals(base, faces)
    displacement = polarity * amplitude * resolved[:, None] * normals
    xyz = base + displacement
    parents = np.repeat(np.arange(len(q)), 4)
    out = ArrayMesh(xyz, np.column_stack([faces, np.full(len(faces), -1, np.int64)]),
        np.r_[np.zeros(nv, np.int8), np.ones(ne, np.int8)], rest,
        mesh.anchors[parents].copy(), mesh.generation + 1)
    if not np.isfinite(out.xyz).all() or not np.isfinite(transferred).all():
        raise ValueError('Nonfinite output or curvature feature.')
    topology(out)
    p = out.xyz[faces]
    if np.any(np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1) <= 2e-12):
        raise ValueError('Degenerate output triangle.')
    state = dict(feature, base_xyz=base, current_vertex_normals=normals,
        transferred_q=transferred, resolved_response=resolved,
        resolved_displacement=displacement, parent_faces=parents,
        input_faces=q.copy(), input_edges=e, new_vertex_parent_edges=e.copy(),
        new_vertex_parent_faces=t['ef'].copy(),
        vertex_parent_edges=np.r_[np.full(nv, -1, np.int64), np.arange(ne)],
        retained_vertex_parent=np.r_[np.arange(nv), np.full(ne, -1, np.int64)])
    rms = feature['diffusion_local_rms_distance']
    meta = dict(implementation='ASTRA_CURVATURE_RESPONSE',
        parameters=dict(amplitude=amplitude, radius=radius, reference_length=reference_length,
            iterations=int(iterations), response=response, q0=q0, source=source, polarity=polarity),
        length_units='Input coordinate unit; q = signed mean curvature * reference_length.',
        curvature_formula='H_v=sum_edges(length*oriented_dihedral)/(4*barycentric_vertex_area)',
        diffusion='Scalar weighted graph averaging only; weight=exp(-.5*(edge_length/radius)^2)/edge_length^2; dt=radius^2/(2*iterations); per-vertex alpha capped .45.',
        diffusion_rms_min=float(rms.min()), diffusion_rms_max=float(rms.max()),
        topology='Exact midpoint 1-to-4 triangle refinement before all-vertex normal displacement.',
        limitations='Radius is requested physical diffusion scale, not an exact geodesic kernel. Reported RMS is local random-walk step estimate. Rest observes evolving midpoint rest embedding. Nonmonotonic response is unverified crest/shoulder hypothesis; no bifurcation or artistic-success claim. No repair; contact validation external.')
    return out, meta, state
