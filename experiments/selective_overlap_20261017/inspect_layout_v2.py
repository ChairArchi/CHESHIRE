"""Independent same-sampling source/waist QA; never modifies input geometry.

The retained V1 helper supplies native plane-section measurements. This version
accepts a baseline regenerated at a different declared carrier density, checks
the original constructor, and measures broad material guard strips explicitly.
No self-intersection, manufacturing, or aesthetic certification is made.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree
from scipy.signal import find_peaks


HERE = Path(__file__).resolve().parent
V1 = HERE / "inspect_layout.py"
V1_SHA = "c09ff79b55154f1ce0f9e45e9bd1fac5fd917bafa699fcc28d5b87ffdb4137bc"
if hashlib.sha256(V1.read_bytes()).hexdigest() != V1_SHA:
    raise ValueError("The immutable V1 measurement helper changed")
spec = importlib.util.spec_from_file_location("selective_waist_measurement_v1", V1)
v1 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v1
spec.loader.exec_module(v1)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def bit_exact(a, b):
    return a.shape == b.shape and a.dtype == b.dtype and a.tobytes(order="C") == b.tobytes(order="C")


def controls(stage):
    with np.load(Path(stage)/"control_quad.npz", allow_pickle=False) as z:
        return z["xyz"], z["faces"], z["chart"]


def source_dependencies(meta):
    records = meta["source_code_sha256"]
    for path, digest in records.items():
        if v1.sha(path) != digest:
            raise ValueError("Actual source dependency changed: " + path)
    source = next(Path(p) for p in records if p.replace("\\", "/").endswith("experiments/end_rule_revision_20261014/replay.py"))
    name = "selective_independent_dense_original_replay"
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, records


def constructor_qa(stage, baseline_stage):
    meta = read(Path(stage)/"generation.json")
    baseline = read(Path(baseline_stage)/"generation.json")
    replay, records = source_dependencies(meta)
    seed = replay.early.seed
    legacy = seed.source.old.repair.legacy
    original = {str(k): value for k, value in legacy.EVENTS.items()}
    if original != meta["original_legacy_events"]:
        raise ValueError("Recorded original events do not match the historical kernel")
    if meta["original_seed_recipe"] != baseline["original_seed_recipe"]:
        raise ValueError("Source proportion/bridge/terminal recipe changed")
    sampling = meta["carrier_sampling"]
    if sampling != baseline["carrier_sampling"]:
        raise ValueError("This comparison requires matched declared carrier sampling")
    carrier, chart = seed.variation.carrier(sampling)
    actual, faces, saved_chart = controls(stage)
    if not np.array_equal(chart, saved_chart) or not np.array_equal(carrier.faces, faces):
        raise ValueError("Saved source is not the original declared carrier")
    resolved = meta["resolved_legacy_events"]
    fixed = ("expansion", "constriction", "reexpansion", "return_depth", "mirror")
    for group, events in resolved.items():
        for event in events:
            if set(event) != set(original[group][0]) or not any(all(event[k] == template[k] for k in fixed) for template in original[group]):
                raise ValueError("A source event changed the original amplitude/template family")
    before = legacy.EVENTS
    try:
        legacy.EVENTS = {int(k): copy.deepcopy(value) for k, value in resolved.items()}
        regenerated, parts = seed.legacy_core(chart, copy.deepcopy(meta["original_seed_recipe"]), "SPAN")
    finally:
        legacy.EVENTS = before
    if not bit_exact(regenerated, actual):
        raise ValueError("Actual source differs from its original constructor reevaluation")
    field_path = Path(stage)/"operation_fields.npz"
    with np.load(field_path, allow_pickle=False) as z:
        exact_parts = {k: bit_exact(value, z[k]) for k, value in parts.items()}
        if not all(exact_parts.values()) or not np.array_equal(sum(z[k] for k in parts), actual):
            raise ValueError("Saved operation parts do not reproduce the actual source")
        with np.load(Path(baseline_stage)/"operation_fields.npz", allow_pickle=False) as b:
            unchanged = {k: bit_exact(z[k], b[k]) for k in ("proportion", "overrunning_return", "terminal_return")}
        if not all(unchanged.values()):
            raise ValueError("Non-fold source components changed")
    return dict(original_constructor_XYZ_exact=True, declared_carrier_faces_and_chart_exact=True,
                sampling=sampling, same_sampling_baseline=True, original49_or25_identity_claimed=False,
                operation_parts_exact=exact_parts, non_fold_components_exact=unchanged,
                source_dependencies_verified=len(records), operation_fields=v1.record(field_path),
                source_generation=v1.record(Path(stage)/"generation.json"),
                original_constructor=v1.record(next(p for p in records if p.replace("\\", "/").endswith("experiments/column_development_20261011/seed_mass.py"))),
                self_intersection_certified=False)


def canonical_cycles(rows):
    first = np.argmin(rows, axis=1)
    return np.take_along_axis(rows, (np.arange(rows.shape[1])[None, :]+first[:, None]) % rows.shape[1], axis=1)


def symmetry(stage):
    x, q, chart = controls(stage)
    _, _, native, _ = v1.load(stage)
    lookup = {tuple(row): i for i, row in enumerate(np.sort(q, axis=1))}
    tree = cKDTree(chart)
    output = {}
    for axis, coordinate in (("x", 0), ("y", 1)):
        target = chart.copy()
        target[:, coordinate+1] *= -1
        distance, pairs = tree.query(target, k=1)
        if distance.max() > 1e-12 or not np.array_equal(pairs[pairs], np.arange(len(x))):
            raise ValueError("Material mirror correspondence is ambiguous")
        face_pairs = np.array([lookup[tuple(row)] for row in np.sort(pairs[q], axis=1)])
        if not np.array_equal(canonical_cycles(pairs[q][:, [0, 3, 2, 1]]), canonical_cycles(q[face_pairs])):
            raise ValueError("Actual reflected source topology has the wrong orientation")
        native_pairs = np.r_[pairs, len(x)+face_pairs]
        reflected = native.copy()
        reflected[:, coordinate] *= -1
        error = float(np.max(np.linalg.norm(native[native_pairs]-reflected, axis=1)))
        if error > 1e-9:
            raise ValueError("Actual native source symmetry failed")
        output[axis] = dict(actual_native_coordinate_error=error, oriented_control_topology_exact=True,
                            material_pair_involution=True)
    return dict(axes=output, nearest_XYZ_used=False, coordinates_repaired=False, passed=True)


def exact_guard_qa(baseline_stage, stage):
    bx, bq, bc = controls(baseline_stage)
    x, q, c = controls(stage)
    if not np.array_equal(bq, q) or not np.array_equal(bc, c):
        raise ValueError("Exact material correspondence changed")
    meta = read(Path(stage)/"generation.json")
    original, resolved = meta["original_legacy_events"], meta["resolved_legacy_events"]
    append_only = resolved["1"][:len(original["1"])] == original["1"] and all(resolved[g] == original[g] for g in ("2", "3"))
    extras = resolved["1"][len(original["1"]):] if append_only else []
    warp = PchipInterpolator([0, .15, .33, .50, .70, .85, 1], [0, .18, .34, .51, .72, .86, 1])
    supports = [[float(e["height"]-2.2*e["span"]), float(e["height"]+.05+2*e["span"])] for e in extras]
    delta = np.linalg.norm(x-bx, axis=1)
    strips = []
    for name, (lo, hi), _ in v1.WAIST_GUARDS:
        mask = (c[:, 0] >= lo-1e-10) & (c[:, 0] <= hi+1e-10)
        full_faces = np.all(mask[q], axis=1)
        actual_exact = bit_exact(x[mask], bx[mask])
        s0, s1 = (float(v) for v in warp([lo, hi]))
        support_disjoint = append_only and all(b <= s0 or a >= s1 for a, b in supports)
        strips.append(dict(name=name, material_t=[lo, hi], original_warped_s=[s0, s1],
                           controls=int(mask.sum()), actual_control_coordinates_bit_exact=actual_exact,
                           changed_controls=int(np.sum(delta[mask] > 1e-12)), maximum_control_displacement=float(delta[mask].max()),
                           interior_native_triangles=int(full_faces.sum()*4),
                           interior_native_strip_bit_exact=bit_exact(x[q[full_faces]], bx[q[full_faces]]),
                           conservative_full_extra_supports_disjoint=support_disjoint,
                           continuum_pointwise_guard_invariance_supported=bool(support_disjoint and actual_exact)))
    caps = (c[:, 0] < 1e-10) | (c[:, 0] > 1-1e-10)
    return dict(original_all_groups_retained_and_G1_extras_appended=append_only,
                appended_primary_events=len(extras), conservative_extra_supports=supports,
                support_rule="Existing PCHIP knots[-2.2,2] plus original local_h shift[0,.05]; no post-XYZ mask.",
                exact_caps=bit_exact(x[caps], bx[caps]),
                total_changed_controls=int(np.sum(delta > 1e-12)), maximum_displacement=float(delta.max()),
                RMS_displacement=float(np.sqrt(np.mean(delta*delta))), guards=strips,
                horizontal_section_identity_does_not_follow_from_material_guard_identity=True)


def derived_core_guard_qa(baseline_stage, stage):
    """Independently reconstruct the explicitly declared narrow-core rule."""
    bx, bq, chart = controls(baseline_stage)
    x, q, candidate_chart = controls(stage)
    if not np.array_equal(bq, q) or not np.array_equal(chart, candidate_chart):
        raise ValueError("Core material correspondence changed")
    rings = v1.material_rings(bx, chart)
    t = np.array([r["material_t"] for r in rings])
    radius = np.array([r["area_equivalent_radius_proxy"] for r in rings])
    dt = float(np.median(np.diff(t)))
    peaks, info = find_peaks(-radius, prominence=.15, distance=max(1, int(round((4/48)/dt))))
    derived = []
    for i, prominence in zip(peaks, info["prominences"]):
        if not .18 < t[i] < .86:
            continue
        lo = hi = int(i)
        limit = radius[i]+.15*prominence
        while lo > 0 and radius[lo-1] <= limit:
            lo -= 1
        while hi+1 < len(t) and radius[hi+1] <= limit:
            hi += 1
        derived.append(dict(t=float(t[i]), interval=[float(t[lo]-.5*dt), float(t[hi]+.5*dt)]))
    meta = read(Path(stage)/"generation.json")
    declared = meta.get("waist_guards", [])
    if len(declared) != len(derived) or any(abs(a["t"]-b["t"]) > 1e-12 or not np.allclose(a["interval"], b["interval"], atol=1e-12, rtol=0) for a, b in zip(derived, declared)):
        raise ValueError("Declared narrow guard rule differs from the actual baseline")
    original, resolved = meta["original_legacy_events"], meta["resolved_legacy_events"]
    append = resolved["1"][:len(original["1"])] == original["1"] and all(resolved[g] == original[g] for g in ("2", "3"))
    extras = resolved["1"][len(original["1"]):] if append else []
    supports = [(e["height"]-2.2*e["span"], e["height"]+.05+2*e["span"]) for e in extras]
    warp = PchipInterpolator([0, .15, .33, .50, .70, .85, 1], [0, .18, .34, .51, .72, .86, 1])
    union = np.zeros(len(x), bool)
    results = []
    for guard in derived:
        lo, hi = guard["interval"]
        mask = (chart[:, 0] >= lo) & (chart[:, 0] <= hi)
        union |= mask
        s0, s1 = (float(v) for v in warp([lo, hi]))
        separated = append and all(b <= s0 or a >= s1 for a, b in supports)
        equal = bit_exact(x[mask], bx[mask])
        full_faces = np.all(mask[q], axis=1)
        results.append(dict(material_t=guard["interval"], centre_material_t=guard["t"],
                            controls=int(mask.sum()), actual_coordinates_bit_exact=equal,
                            interior_native_triangles=int(full_faces.sum()*4),
                            native_strip_bit_exact=bit_exact(x[q[full_faces]], bx[q[full_faces]]),
                            extras_conservative_support_disjoint=separated,
                            continuum_pointwise_invariance_supported=bool(separated and equal)))
    return dict(derivation_independently_verified=True,
                rule="Original-baseline material-ring equivalent area radius; minima prominence .15 and separation 4/48; radius<=minimum+.15*prominence; half-ring margin.",
                declared_core_controls=int(union.sum()), all_core_coordinates_bit_exact=bit_exact(x[union], bx[union]),
                distinct_from_broad_original49_guards=True, guards=results)


def main(args):
    baseline = v1.measure(args.baseline)
    baseline_proof = constructor_qa(args.baseline, args.baseline)
    results = {}
    for item in args.candidate:
        name, path = item.split("=", 1)
        path = Path(path)
        measured = v1.measure(path)
        comparison = v1.compare(baseline, measured)
        results[name] = dict(measurements=measured, comparison=comparison,
                             waist_summary=v1.guard_summary(args.baseline, path, comparison),
                             constructor_QA=constructor_qa(path, args.baseline), actual_symmetry_QA=symmetry(path),
                             exact_guard_QA=exact_guard_qa(args.baseline, path),
                             derived_narrow_core_QA=derived_core_guard_qa(args.baseline, path))
    result = dict(schema="CHESHIRE_MATCHED_DENSE_G0_LAYOUT_QA_V2", baseline=baseline,
                  baseline_constructor_QA=baseline_proof, baseline_symmetry=symmetry(args.baseline), candidates=results,
                  inspector=v1.record(__file__), retained_measurement_helper=v1.record(V1),
                  guard_scope="Original49-derived broad material waist intervals, measured on this matched dense sampling; no old49/new193 XYZ identity claim.",
                  geometry_modified=False, no_G4_replay=True, aesthetic_score=False,
                  self_intersection_or_manufacturing_certified=False)
    if args.output:
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(dict(schema=result["schema"], baseline=baseline["native_quality"],
                          candidates={k: dict(native=v["measurements"]["native_quality"], guards=v["exact_guard_QA"]) for k, v in results.items()},
                          output=str(args.output) if args.output else None), ensure_ascii=True, allow_nan=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--output", type=Path)
    main(parser.parse_args())
