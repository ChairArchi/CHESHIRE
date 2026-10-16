"""Read-only G0 neck/wing measurements on actual native triangle surfaces.

Section area is an oriented/algebraic proxy, not a solid certificate. Uniform
angular samples distinguish a narrow central body from long isolated wings.
No geometry, recipe, registration or visual result is changed.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


WAIST_GUARDS = (
    ("lower_neck", (.22916666666666666, .3125), (2.5, 3.2)),
    ("middle_neck", (.4375, .5208333333333334), (4.7, 5.2)),
    ("upper_neck", (.75, .7708333333333334), (7.6, 8.0)),
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def record(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def cross2(a, b):
    return a[..., 0]*b[..., 1] - a[..., 1]*b[..., 0]


def weighted_quantiles(values, weights, levels=(.1, .5, .9)):
    order = np.argsort(values)
    v, w = values[order], weights[order]
    c = (np.cumsum(w) - .5*w) / w.sum()
    return np.interp(levels, c, v)


def section(xyz, faces, z, angular_samples=128):
    p = xyz[faces]
    a, b = p, np.roll(p, -1, axis=1)
    za, zb = a[:, :, 2], b[:, :, 2]
    hit = ((za <= z) & (zb > z)) | ((zb <= z) & (za > z))
    active = np.flatnonzero(hit.any(axis=1))
    if not len(active):
        return dict(world_Z=float(z), valid=False)
    if not np.all(hit[active].sum(axis=1) == 2):
        raise ValueError("Unexpected linear triangle/plane intersection")
    aa, bb = a[active][hit[active]], b[active][hit[active]]
    u = (z-aa[:, 2]) / (bb[:, 2]-aa[:, 2])
    points = (aa + u[:, None]*(bb-aa)).reshape(-1, 2, 3)[:, :, :2]
    normal = np.cross(p[active, 1]-p[active, 0], p[active, 2]-p[active, 0])
    tangent = np.column_stack((-normal[:, 1], normal[:, 0]))
    reverse = np.einsum("ij,ij->i", points[:, 1]-points[:, 0], tangent) < 0
    points[reverse] = points[reverse, ::-1]
    length = np.linalg.norm(points[:, 1]-points[:, 0], axis=1)
    points, length = points[length > 1e-12], length[length > 1e-12]
    if not len(points):
        return dict(world_Z=float(z), valid=False)
    a, b = points[:, 0], points[:, 1]
    signed_area = float(cross2(a, b).sum()/2)
    winding = float(np.arctan2(cross2(a, b), np.einsum("ij,ij->i", a, b)).sum()/(2*np.pi))
    samples = (a[:, None, :] + np.array([1/6, .5, 5/6])[None, :, None]*(b-a)[:, None, :]).reshape(-1, 2)
    weights = np.repeat(length/3, 3)
    quantiles = np.column_stack([weighted_quantiles(samples[:, k], weights) for k in (0, 1)])
    angles = np.arange(angular_samples)*2*np.pi/angular_samples
    direction = np.column_stack((np.cos(angles), np.sin(angles)))
    delta = b-a
    denominator = cross2(direction[:, None, :], delta[None, :, :])
    nonparallel = np.abs(denominator) > 1e-13
    radius = np.divide(cross2(a, delta)[None, :], denominator,
                       out=np.full_like(denominator, np.inf), where=nonparallel)
    fraction = np.divide(cross2(a[None, :, :], direction[:, None, :]), denominator,
                         out=np.full_like(denominator, np.inf), where=nonparallel)
    valid = nonparallel & (radius > 1e-10) & (fraction >= -1e-10) & (fraction < 1-1e-10)
    first = np.where(valid, radius, np.inf).min(axis=1)
    last = np.where(valid, radius, -np.inf).max(axis=1)
    ray_hit = np.isfinite(first)
    inside = abs(winding) >= .5
    return dict(world_Z=float(z), valid=True, section_segments=len(points),
                exact_native_XY_envelope_width=np.ptp(points.reshape(-1, 2), axis=0).tolist(),
                boundary_arc_quadrature_XY_P10_P90_width=(quantiles[2]-quantiles[0]).tolist(),
                signed_section_area_proxy=signed_area, area_equivalent_radius_proxy=float(np.sqrt(abs(signed_area)/np.pi)),
                perimeter=float(length.sum()), origin_winding=winding, origin_inside_proxy=inside,
                angular_ray_coverage=float(ray_hit.mean()),
                first_boundary_radius_P10_P50_P90=np.quantile(first[ray_hit], [.1, .5, .9]).tolist(),
                outer_boundary_radius_P10_P50_P90=np.quantile(last[ray_hit], [.1, .5, .9]).tolist(),
                angular_outer_radius_above={str(r): float(np.mean(last > r)) for r in (.7, .9, 1.1, 1.3)},
                central_first_exit_interpretation_valid=inside and bool(ray_hit.all()))


def material_rings(control, chart):
    rows = []
    side = np.linalg.norm(chart[:, 1:], axis=1) > .99
    for t in np.unique(chart[side, 0]):
        ids = np.flatnonzero(side & (chart[:, 0] == t))
        angle = np.mod(np.arctan2(chart[ids, 2], chart[ids, 1]), 2*np.pi)
        ids = ids[np.argsort(angle)]
        xy = control[ids, :2]
        area = float(cross2(xy, np.roll(xy, -1, axis=0)).sum()/2)
        radial = np.linalg.norm(xy, axis=1)
        q = np.quantile(xy, [.1, .9], axis=0)
        rows.append(dict(material_t=float(t), controls=len(ids), world_Z_median=float(np.median(control[ids, 2])),
                         exact_control_XY_width=np.ptp(xy, axis=0).tolist(),
                         control_XY_P10_P90_width=(q[1]-q[0]).tolist(),
                         radial_P10_P50_P90=np.quantile(radial, [.1, .5, .9]).tolist(),
                         signed_projected_ring_area_proxy=area,
                         area_equivalent_radius_proxy=float(np.sqrt(abs(area)/np.pi))))
    return rows


def load(stage):
    stage = Path(stage)
    meta = json.loads((stage / "generation.json").read_text(encoding="utf-8-sig"))
    for name, key in (("control_quad.npz", "control_file_sha256"), ("geometry.npz", "geometry_file_sha256")):
        digest = meta.get(key) or meta.get("actual_files", {}).get(name, {}).get("sha256")
        if not digest or sha(stage/name) != digest:
            raise ValueError("Saved source binding changed: " + str(stage/name))
    with np.load(stage/"control_quad.npz", allow_pickle=False) as z:
        control, quads, chart = z["xyz"], z["faces"], z["chart"]
    with np.load(stage/"geometry.npz", allow_pickle=False) as z:
        xyz, faces = z["xyz"], z["faces"]
    expected_x = np.concatenate((control, control[quads].mean(axis=1)))
    centre = np.broadcast_to((len(control)+np.arange(len(quads)))[:, None], quads.shape)
    expected_t = np.stack((quads, np.roll(quads, -1, axis=1), centre), axis=2).reshape(-1, 3)
    if not np.array_equal(xyz, expected_x) or not np.array_equal(faces, expected_t):
        raise ValueError("Source is not its actual four-fan native geometry")
    return control, chart, xyz, faces


def topology(xyz, triangles):
    if not np.isfinite(xyz).all() or triangles.min() < 0 or triangles.max() >= len(xyz):
        raise ValueError("Invalid actual native geometry")
    a, b = triangles.ravel(), np.roll(triangles, -1, axis=1).ravel()
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    keys = lo*len(xyz) + hi
    order = np.argsort(keys)
    starts = np.r_[0, np.flatnonzero(np.diff(keys[order]))+1]
    counts = np.diff(np.r_[starts, len(keys)])
    directions = np.add.reduceat((a[order] > b[order]).astype(np.int64), starts)
    graph = coo_matrix((np.ones(len(starts)), (lo[order[starts]], hi[order[starts]])), shape=(len(xyz), len(xyz)))
    components = int(connected_components(graph, directed=False, return_labels=False))
    p = xyz[triangles]
    area = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)/2
    result = dict(finite=True, closed_edge_incidence_two=bool(np.all(counts == 2)),
                  oriented_edges=bool(np.all(directions == 1)), components=components,
                  Euler=int(len(xyz)-len(starts)+len(triangles)),
                  no_orphan_vertices=bool(len(np.unique(triangles)) == len(xyz)),
                  minimum_triangle_area=float(area.min()),
                  signed_oriented_volume_proxy=float(np.einsum("ij,ij->", p[:, 0], np.cross(p[:, 1], p[:, 2]))/6))
    result["passed"] = all((result["closed_edge_incidence_two"], result["oriented_edges"],
                            components == 1, result["Euler"] == 2,
                            result["no_orphan_vertices"], result["minimum_triangle_area"] > 1e-12))
    if not result["passed"]:
        raise ValueError("Native source topology/area gate failed")
    return result


def selective_provenance(baseline_stage, stage):
    """Reevaluate declared settings with the unchanged original constructor."""
    stage, baseline_stage = Path(stage), Path(baseline_stage)
    meta = json.loads((stage/"generation.json").read_text(encoding="utf-8-sig"))
    if meta.get("schema") != "CHESHIRE_SELECTIVE_ORIGINAL_FOLD_SOURCE_V1":
        return dict(performed=False, reason="This additional proof targets the selective source schema.")
    for path, digest in meta["source_code_sha256"].items():
        if sha(path) != digest:
            raise ValueError("Constructor dependency changed: " + path)
    for name, item in meta["actual_files"].items():
        if Path(item["path"]).resolve() != (stage/name).resolve() or sha(item["path"]) != item["sha256"]:
            raise ValueError("Selective source file binding changed")
    original, resolved = meta["original_legacy_events"], meta["resolved_legacy_events"]
    if original["1"] != resolved["1"] or len(original["1"]) != 2:
        raise ValueError("The original two primary events were changed")
    amplitude_keys = ("expansion", "constriction", "reexpansion", "return_depth", "mirror")
    allowed = set(original["1"][0])
    for group in ("2", "3"):
        for event in resolved[group]:
            if set(event) != allowed or not any(all(event[k] == template[k] for k in amplitude_keys) for template in original[group]):
                raise ValueError("Secondary event replaced the original parameter/kernel family")
    source_path = next(Path(v) for v in meta["source_code_sha256"] if v.replace("\\", "/").endswith("experiments/end_rule_revision_20261014/replay.py"))
    spec = importlib.util.spec_from_file_location("selective_independent_original_replay", source_path)
    replay = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = replay
    spec.loader.exec_module(replay)
    seed = replay.early.seed
    legacy = seed.source.old.repair.legacy
    control, chart, _, _ = load(stage)
    previous = legacy.EVENTS
    if {str(k): v for k, v in previous.items()} != original:
        raise ValueError("Declared original events differ from the historical kernel")
    baseline_meta = json.loads((baseline_stage/"generation.json").read_text(encoding="utf-8-sig"))
    if meta["original_seed_recipe"] != baseline_meta["original_seed_recipe"]["original_SPAN_recipe"]:
        raise ValueError("Original proportion/bridge/terminal recipe was changed")
    try:
        legacy.EVENTS = {int(k): copy.deepcopy(v) for k, v in resolved.items()}
        actual, parts = seed.legacy_core(chart, copy.deepcopy(meta["original_seed_recipe"]), "SPAN")
    finally:
        legacy.EVENTS = previous
    if not np.array_equal(actual, control):
        raise ValueError("Saved source is not the declared original constructor result")
    with np.load(stage/"operation_fields.npz", allow_pickle=False) as z:
        part_checks = {k: bool(np.array_equal(z[k], value)) for k, value in parts.items()}
        if not all(part_checks.values()) or not np.array_equal(sum(z[k] for k in parts), control):
            raise ValueError("Saved operation fields do not reproduce the source")
        if sha(baseline_stage/"evidence.npz") != baseline_meta["evidence_file_sha256"]:
            raise ValueError("Baseline operation fields changed")
        with np.load(baseline_stage/"evidence.npz", allow_pickle=False) as b:
            unchanged = {k: bool(np.array_equal(z[k], b[k])) for k in ("proportion", "overrunning_return", "terminal_return")}
        if not all(unchanged.values()):
            raise ValueError("Non-fold source parts were changed")
    return dict(performed=True, original_constructor_XYZ_exact=True,
                declared_operation_parts_exact=part_checks, unchanged_non_fold_parts=unchanged,
                original_primary_two_events_exact=True,
                original_source_dependency_hashes_verified=len(meta["source_code_sha256"]),
                original_constructor_path=record(source_path), source_generation=record(stage/"generation.json"),
                post_XYZ_mask_or_projection=False, new_primitive=False, field_overlap_applied=False)


def symmetry_against_baseline(baseline_stage, stage):
    base, chart, _, _ = load(baseline_stage)
    control, candidate_chart, native, _ = load(stage)
    if not np.array_equal(chart, candidate_chart):
        raise ValueError("Material chart correspondence changed")
    with np.load(Path(baseline_stage)/"control_quad.npz", allow_pickle=False) as b, np.load(Path(stage)/"control_quad.npz", allow_pickle=False) as c:
        if not np.array_equal(b["faces"], c["faces"]):
            raise ValueError("Source control topology changed")
    results = {}
    with np.load(Path(baseline_stage)/"evidence.npz", allow_pickle=False) as z:
        for axis, coordinate in (("x", 0), ("y", 1)):
            pair = z["mirror_"+axis+"_vertex_pairs"]
            if not np.array_equal(pair[pair], np.arange(len(pair))):
                raise ValueError("Baseline material mirror is not an involution")
            target = control.copy()
            target[:, coordinate] *= -1
            error = float(np.max(np.linalg.norm(control[pair]-target, axis=1)))
            if error > 1e-9:
                raise ValueError("Actual source reflection symmetry failed")
            native_pair = np.r_[pair, len(control)+z["mirror_"+axis+"_face_pairs"]]
            reflected = native.copy()
            reflected[:, coordinate] *= -1
            native_error = float(np.max(np.linalg.norm(native[native_pair]-reflected, axis=1)))
            if native_error > 1e-9:
                raise ValueError("Actual native source reflection symmetry failed")
            results[axis] = dict(actual_control_reflection_max_error=error,
                                 actual_native_reflection_max_error=native_error, passed=True)
    return dict(same_control_faces_and_chart=True, axes=results,
                map_source=record(Path(baseline_stage)/"evidence.npz"), coordinates_repaired=False)


def measure(stage, z_levels=None):
    control, chart, xyz, faces = load(stage)
    levels = np.arange(.8, 9.20001, .1) if z_levels is None else np.asarray(z_levels)
    rows = [section(xyz, faces, float(z)) for z in levels]
    return dict(source_geometry=record(Path(stage)/"geometry.npz"), source_controls=record(Path(stage)/"control_quad.npz"),
                actual_native_four_fans_exact=True, native_vertices=len(xyz), native_triangles=len(faces),
                native_quality=topology(xyz, faces),
                world_Z_sections=rows, material_t_rings=material_rings(control, chart),
                scope="Source G0. Section envelopes are exact on stored linear triangles. Area is oriented/algebraic; arc quantiles use three-point length quadrature. Material-ring profiles are independent of world-Z sections. No physical-solid, self-intersection or aesthetic certification.")


def intervals(coordinates, selected):
    selected = np.asarray(selected, bool)
    indices = np.flatnonzero(selected)
    if not len(indices):
        return []
    groups = np.split(indices, np.flatnonzero(np.diff(indices) > 1)+1)
    return [[float(coordinates[g[0]]), float(coordinates[g[-1]])] for g in groups]


def compare(baseline, candidate):
    rows = []
    for a, b in zip(baseline["world_Z_sections"], candidate["world_Z_sections"]):
        if not a["valid"] or not b["valid"]:
            continue
        if abs(a["world_Z"]-b["world_Z"]) > 1e-9:
            raise ValueError("World sections are not matched")
        rows.append(dict(world_Z=a["world_Z"],
                         area_proxy_ratio=abs(b["signed_section_area_proxy"])/abs(a["signed_section_area_proxy"]),
                         XY_max_width_ratio=(np.array(b["exact_native_XY_envelope_width"])/a["exact_native_XY_envelope_width"]).tolist(),
                         XY_arc_P10_P90_width_ratio=(np.array(b["boundary_arc_quadrature_XY_P10_P90_width"])/a["boundary_arc_quadrature_XY_P10_P90_width"]).tolist(),
                         first_exit_median_radius_ratio=b["first_boundary_radius_P10_P50_P90"][1]/a["first_boundary_radius_P10_P50_P90"][1],
                         first_exit_valid=a["central_first_exit_interpretation_valid"] and b["central_first_exit_interpretation_valid"],
                         outer_angular_coverage_above_1p1=b["angular_outer_radius_above"]["1.1"]))
    ring_rows = []
    for a, b in zip(baseline["material_t_rings"], candidate["material_t_rings"]):
        if abs(a["material_t"]-b["material_t"]) > 1e-12:
            raise ValueError("Material ring correspondence changed")
        ring_rows.append(dict(material_t=a["material_t"],
                              area_proxy_ratio=abs(b["signed_projected_ring_area_proxy"])/abs(a["signed_projected_ring_area_proxy"]),
                              median_radius_ratio=b["radial_P10_P50_P90"][1]/a["radial_P10_P50_P90"][1]))
    return dict(world_Z=rows, material_t=ring_rows)


def guard_summary(baseline_stage, candidate_stage, comparison):
    base, chart, _, _ = load(baseline_stage)
    control, c, _, _ = load(candidate_stage)
    if not np.array_equal(chart, c):
        raise ValueError("Material guard IDs are not corresponding")
    delta = np.linalg.norm(control-base, axis=1)
    summary = []
    for name, (t0, t1), (z0, z1) in WAIST_GUARDS:
        selected = (chart[:, 0] >= t0-1e-10) & (chart[:, 0] <= t1+1e-10)
        rings = [r for r in comparison["material_t"] if t0-1e-10 <= r["material_t"] <= t1+1e-10]
        sections = [r for r in comparison["world_Z"] if z0-1e-10 <= r["world_Z"] <= z1+1e-10 and r["first_exit_valid"]]
        q = lambda values: np.quantile(values, [0, .5, 1]).tolist()
        summary.append(dict(name=name, material_t=[t0, t1], world_Z=[z0, z1],
                            matching_controls=int(selected.sum()), changed_controls=int(np.sum(delta[selected] > 1e-12)),
                            maximum_control_displacement=float(delta[selected].max()),
                            ring_area_ratio_min_median_max=q([r["area_proxy_ratio"] for r in rings]),
                            ring_median_radius_ratio_min_median_max=q([r["median_radius_ratio"] for r in rings]),
                            world_area_ratio_min_median_max=q([r["area_proxy_ratio"] for r in sections]),
                            world_first_exit_ratio_min_median_max=q([r["first_exit_median_radius_ratio"] for r in sections]),
                            world_arc_P10_P90_width_ratio_median=np.median([r["XY_arc_P10_P90_width_ratio"] for r in sections], axis=0).tolist()))
    return summary


def main(a):
    baseline = measure(a.baseline)
    results = {}
    for item in a.candidate:
        name, path = item.split("=", 1)
        value = measure(Path(path))
        comparison = compare(baseline, value)
        results[name] = dict(measurements=value, comparison=comparison,
                             waist_guards=guard_summary(a.baseline, path, comparison),
                             selective_constructor_QA=selective_provenance(a.baseline, path),
                             actual_symmetry_QA=symmetry_against_baseline(a.baseline, path))
    result = dict(schema="CHESHIRE_G0_WAIST_AND_WING_MEASUREMENT_V1", baseline=baseline, candidates=results,
                  source=record(__file__), geometry_modified=False, aesthetic_score=False,
                  self_intersection_or_manufacturing_certified=False)
    if a.output:
        with a.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", action="append", default=[])
    p.add_argument("--output", type=Path)
    main(p.parse_args())
