"""Connected angular-sector selection on a real cyclic sweep boundary.

Angular PCA coordinates need not be monotone along the boundary. A sector can
therefore select disconnected strips. Keep a single contiguous cyclic arc,
without changing coordinates or weakening the original disk/topology gates.
"""
from __future__ import annotations

import numpy as np


def cyclic_runs(mask):
    """Return oriented contiguous index runs, including the wraparound run."""
    mask = np.asarray(mask, bool)
    if mask.ndim != 1 or not len(mask):
        raise ValueError("A nonempty cyclic boolean mask is required.")
    if mask.all():
        return [np.arange(len(mask), dtype=np.int64)]
    starts = np.flatnonzero(mask & ~np.roll(mask, 1))
    runs = []
    for start in starts:
        run = []
        i = int(start)
        while mask[i]:
            run.append(i)
            i = (i+1) % len(mask)
        runs.append(np.asarray(run, np.int64))
    return runs


def ranked_sector_arcs(beta, centre, halfwidth, occupied=None, gap_columns=1):
    """Rank actual masked arcs by nearest angular sample, then retained size.

    The search never grows beyond the requested sector. A native column gap
    prevents sibling strips from sharing sidewall boundary vertices.
    """
    beta = np.asarray(beta, float)
    if beta.ndim != 1 or not len(beta) or not np.isfinite(beta).all():
        raise ValueError("Finite ordered cyclic boundary angles required.")
    if not np.isfinite([centre, halfwidth]).all() or not 0 < halfwidth < np.pi:
        raise ValueError("Finite angular centre and positive sub-pi halfwidth required.")
    if gap_columns < 0 or int(gap_columns) != gap_columns:
        raise ValueError("Native gap columns must be a nonnegative integer.")
    difference = np.arctan2(np.sin(beta-centre), np.cos(beta-centre))
    original = np.abs(difference) < halfwidth
    occupied = np.zeros(len(beta), bool) if occupied is None else np.asarray(occupied, bool)
    if occupied.shape != beta.shape:
        raise ValueError("Occupied columns must align with the cyclic boundary.")
    blocked = occupied.copy()
    for step in range(1, gap_columns+1):
        blocked |= np.roll(occupied, step) | np.roll(occupied, -step)
    eligible = original & ~blocked
    arcs = cyclic_runs(eligible)
    arcs.sort(key=lambda a:(float(np.min(np.abs(difference[a]))), -len(a),
                            float(np.mean(np.abs(difference[a]))), int(a[0])))
    return arcs, dict(original_columns=np.flatnonzero(original).tolist(),
                     occupied_or_gap_columns=np.flatnonzero(blocked).tolist(),
                     candidate_cyclic_arcs=[a.tolist() for a in arcs],
                     gap_columns=int(gap_columns))


def connected_beta_plans(sidewall, mesh, layout, recipe):
    """Historical Task32 plan adapter with explicit connected-arc ownership.

    All original disk_boundary, PCA, normal and sibling-vertex gates remain.
    Only the original angular proposal's selected columns can be discarded.
    """
    plans, used_vertices = [], set()
    occupied = np.zeros(len(layout["beta"]), bool)
    root_normal = layout["frame"]["normal"]
    for index, centre in enumerate(recipe["beta_centres"]):
        arcs, selection = ranked_sector_arcs(layout["beta"], centre,
                    recipe["beta_halfwidth"], occupied, gap_columns=1)
        original = np.asarray(selection["original_columns"], np.int64)
        record = dict(sibling_index=index, beta_centre=centre,
            beta_halfwidth=recipe["beta_halfwidth"], parent_rows=recipe["parent_rows"],
            original_boundary_columns=original.tolist(),
            selection_rule="Single native cyclic arc inside the authored beta sector; one empty column between siblings; original disk gates retained.",
            selection_mode="connected_beta_arc", connected_selection=selection)
        attempts = []
        for columns in arcs:
            selected = np.flatnonzero(np.isin(layout["row"], recipe["parent_rows"]) &
                                     np.isin(layout["column"], columns))
            try:
                if len(selected) < recipe["minimum_patch_faces"]:
                    raise ValueError("Insufficient actual sidewall multi-face support.")
                vertices, _, _ = sidewall.growth.disk_boundary(mesh, selected)
                if used_vertices.intersection(map(int, vertices)):
                    raise ValueError("Sibling sidewall strips share vertices.")
                local = sidewall.growth._pca(mesh, selected, recipe)
                diagnostics = sidewall._normal_diagnostics(mesh, selected, root_normal)
                direction = local["major"].copy()
                if np.dot(direction, layout["frame"]["major"]) < 0:
                    direction *= -1
                record.update(proposal_status="accepted", boundary_columns=columns.tolist(),
                    planned_input_faces=selected.tolist(), selected_tokens=selected.tolist(),
                    selected_boundary_beta=layout["beta"][columns].tolist(),
                    discarded_boundary_columns=np.setdiff1d(original,columns).tolist(),
                    direction=direction.tolist(), pca_origin=local["origin"].tolist(),
                    pca_major=local["major"].tolist(), pca_minor=local["minor"].tolist(),
                    pca_extent=local["extent"].tolist(), normal_diagnostics=diagnostics,
                    previous_candidate_rejections=attempts)
                used_vertices.update(map(int, vertices))
                occupied[columns] = True
                break
            except ValueError as exc:
                attempts.append(dict(columns=columns.tolist(), reason=str(exc)))
        else:
            record.update(proposal_status="rejected", boundary_columns=[],
                planned_input_faces=[], selected_tokens=[], selected_boundary_beta=[],
                reason="No valid connected cyclic arc within the authored beta sector.",
                candidate_rejections=attempts)
        plans.append(record)
    return plans
