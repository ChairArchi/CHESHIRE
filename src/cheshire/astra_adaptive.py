"""Experimental geometry-selected conforming centroid/old-edge growth.

Only the insert-centres/flip-old-edges connectivity is inspired by sqrt(3).
Area selection, dominant signed hinges, and fraction-weighted Laplacian motion
are new research rules, not the original adaptive algorithm or smoothing mask.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology, fields, mean_incident
from .astra_rotating import features


def step(mesh, *, fold=.35, relaxation=.04, feedback=1., bias=0.,
         source='current', polarity=1., selection='adaptive', hinge='mean',
         quantile=.5):
    if not np.isfinite([fold, relaxation, feedback, bias, quantile]).all():
        raise ValueError('Nonfinite parameter.')
    if not (0 <= fold <= 2 and 0 <= relaxation <= 1 and 0 <= feedback <= 3
            and 0 <= quantile <= 1):
        raise ValueError('Invalid declared parameter range.')
    if source not in ('current', 'rest') or selection not in ('adaptive', 'uniform'):
        raise ValueError('Unknown observation source or selection.')
    if hinge not in ('mean', 'dominant') or polarity not in (-1., 1.):
        raise ValueError('Unknown hinge or polarity.')
    # Validate actual embedding as well as the selected observation embedding.
    t, actual, _ = features(mesh)
    observed = mesh if source == 'current' else ArrayMesh(
        mesh.rest, mesh.faces, mesh.classes, mesh.rest, mesh.anchors, mesh.generation)
    _, obs, feat = features(observed)
    x = mesh.xyz; q = mesh.faces[:, :3]; nv = len(x); nf = len(q)
    area = obs['area']
    threshold = float(np.quantile(area, quantile))
    tolerance = max(float(area.max()) * 1e-12, np.finfo(float).tiny)
    selected = np.ones(nf, bool) if selection == 'uniform' else area >= threshold - tolerance
    face_angles = feat['edge_angle'][t['fe'][:, :3]]
    dominant_tolerance = 1e-12
    dominant_mask = np.abs(face_angles) >= np.abs(face_angles).max(1)[:, None] - dominant_tolerance
    dominant = (face_angles * dominant_mask).sum(1) / dominant_mask.sum(1)
    bend = feat['signed_bend'] if hinge == 'mean' else dominant
    response = np.tanh(bias + feedback * 3 * bend)
    requested = polarity * fold * feat['inradius'] * response
    offset = np.where(selected, requested, 0.)
    selected_ids = np.flatnonzero(selected)
    centre_ids = np.full(nf, -1, np.int64)
    centre_ids[selected] = nv + np.arange(len(selected_ids))
    centres = actual['c'][selected] + actual['nf'][selected] * offset[selected, None]
    e = t['edges']; ef = t['ef']
    fraction = mean_incident(np.repeat(selected.astype(float), 3), q.ravel(), nv)
    neighbor = mean_incident(x[e[:, ::-1].ravel()], e.ravel(), nv)
    old = x + (relaxation * fraction)[:, None] * (neighbor - x)
    xyz = np.concatenate([old, centres])
    rest = np.concatenate([mesh.rest, mesh.rest[q[selected]].mean(1)])
    sign = feat['edge_orientation']
    a = np.where(sign > 0, e[:, 0], e[:, 1])
    b = np.where(sign > 0, e[:, 1], e[:, 0])
    both = selected[ef].all(1)
    # Preserve rotating's exact ordering for the all-selected case.
    l = centre_ids[ef[both, 0]]; r = centre_ids[ef[both, 1]]
    faces = [np.stack([np.column_stack([a[both], r, l]),
                      np.column_stack([b[both], l, r])], axis=1).reshape(-1, 3)]
    parents = [np.repeat(ef[both], 2, axis=0)]
    corners = [np.column_stack([np.column_stack([a[both], b[both]]).ravel(),
                               np.full((2 * both.sum(), 2), -1, np.int64)])]
    kinds = [np.full(2 * both.sum(), 2, np.int8)]
    # At a selected/unselected boundary, retain the original edge and fan it
    # only on the selected side. The unsplit face is emitted once below.
    for side in (0, 1):
        mask = ~both & selected[ef[:, side]]
        first, second = (a[mask], b[mask]) if side == 0 else (b[mask], a[mask])
        parent = ef[mask, side]
        faces.append(np.column_stack([first, second, centre_ids[parent]]))
        parents.append(np.column_stack([parent, np.full(len(parent), -1, np.int64)]))
        corners.append(np.column_stack([first, second, np.full(len(parent), -1, np.int64)]))
        kinds.append(np.ones(len(parent), np.int8))
    unsplit = np.flatnonzero(~selected)
    faces.append(q[unsplit]); parents.append(np.column_stack([unsplit, np.full(len(unsplit), -1, np.int64)]))
    corners.append(q[unsplit]); kinds.append(np.zeros(len(unsplit), np.int8))
    faces = np.concatenate(faces); parents = np.concatenate(parents)
    corners = np.concatenate(corners); kinds = np.concatenate(kinds)
    anchors = mesh.anchors[parents[:, 0]].copy()
    merged = parents[:, 1] >= 0
    anchors[merged] = np.where(anchors[merged] == mesh.anchors[parents[merged, 1]], anchors[merged], -1)
    out = ArrayMesh(xyz, np.column_stack([faces, np.full(len(faces), -1, np.int64)]),
                    np.r_[np.zeros(nv, np.int8), np.full(len(selected_ids), 2, np.int8)],
                    rest, anchors, mesh.generation + 1)
    if not np.isfinite(out.xyz).all():
        raise ValueError('Nonfinite output.')
    topology(out)
    p = out.xyz[faces]
    out_area = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1) / 2
    if np.any(out_area <= 1e-12):
        raise ValueError('Degenerate output triangle.')
    state = dict(input_edges=e, input_faces=q.copy(), parent_faces=parents,
                 parent_corner=corners[:, 0], parent_old_corners=corners,
                 child_construction=kinds, selected_faces=selected,
                 selected_face_ids=selected_ids, selected_centroid_ids=centre_ids,
                 flipped_edges=both, feature_area=area, feature_inradius=feat['inradius'],
                 feature_signed_bend=bend, feature_mean_bend=feat['signed_bend'],
                 feature_dominant_bend=dominant, feature_edge_angle=feat['edge_angle'],
                 dominant_hinge_ties=dominant_mask, requested_offset=requested,
                 resolved_offset=offset, response=response,
                 vertex_selected_incident_fraction=fraction,
                 old_vertex_displacement=old-x,
                 new_face_displacement=centres-actual['c'][selected])
    meta = dict(implementation='ASTRA_ADAPTIVE_TRIANGLE',
                parameters=dict(fold=fold, relaxation=relaxation, feedback=feedback,
                                bias=bias, source=source, polarity=polarity,
                                selection=selection, hinge=hinge, quantile=quantile),
                selection_threshold=threshold, selection_tolerance=tolerance,
                dominant_hinge_tolerance=dominant_tolerance,
                selected_faces=int(selected.sum()), flipped_edges=int(both.sum()),
                child_construction_codes={'0':'retained face', '1':'unflipped fan', '2':'flipped edge'},
                topology='Insert only selected centres; flip old edges iff both adjacent faces selected; conforming closed triangles.',
                limitations='Own selection and signed-offset rules; fixed genus. Rest observes evolving rest embedding, not fixed initial attributes. Current placement/normals; relaxation weighted by selected incident-face fraction. No global clamp. Contact validation remains external.')
    return out, meta, state
