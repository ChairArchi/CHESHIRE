"""Independent inspection and unchanged native export of inherited-rule replays.

This inspector does not generate, repair, normalize or rate geometry. The saved
original SPAN input and actual split/event ancestry are the comparison basis.
--inspect-only writes nothing. Export requires a fresh output directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import time

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
SCHEMA = "CHESHIRE_INHERITED_POSITION_SPLIT_DIRECTION_REPLAY_V1"
ORIGINAL_G0 = Path("E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00/control_quad.npz")
ORIGINAL_G0_SHA = "cff9089de50aac6019684829cd70303d77e3fceaaabf3f090a06636f4f6cbf55"
ORIGINAL_STATES = Path("E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states")
CHUNK = 131072
STAGES = ("G00_INPUT", "G01_ANCESTRY", "G02_OVERLAP", "G03_WALL", "G03_ROOT", "G03_SIDEWALL", "G04_NEUTRAL")
# The established operators are hash-bound independently of the new driver and
# regional parameter adapter. Additional dependencies remain recorded as such.
FROZEN_OPERATORS = (
    "experiments/end_rule_revision_20261014/replay.py",
    "experiments/recipe_transfer_20261013/early.py",
    "experiments/connected_fold_growth_20261012/patch_growth.py",
    "experiments/sidewall_fan_growth_20261013/patch_sidewall.py",
    "src/cheshire/task36_growth.py",
    "src/cheshire/task32_patches.py",
    "src/cheshire/reference_subdivision.py",
)
TOP_KEYS = {"id", "name", "label_ko", "family", "description_ko", "overlap_events",
            "root_recipe", "sidewall_recipe", "split_regions", "experimental", "fabrication_certified"}
EVENT_KEYS = {"id", "template_index", "height", "span", "direction", "sweep", "overlap_width"}
FIXED_EVENT_KEYS = {"expansion", "constriction", "reexpansion", "return_depth", "mirror"}
ROOT_KEYS = {"root_parameter_centre", "root_parameter_halfwidth", "root_cross_centre",
             "root_cross_sweep", "root_cross_halfwidth"}
SIDE_KEYS = {"parent_rows", "beta_centres", "beta_halfwidth"}
REGION_KEYS = {"enabled", "t_centre", "t_halfwidth", "theta_centre", "theta_halfwidth", "w3", "w4", "w1"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ah(a):
    return hashlib.sha256(np.ascontiguousarray(a).view(np.uint8)).hexdigest()


def record(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def checked(path, digest):
    if sha(path) != digest:
        raise ValueError("Bound replay artifact changed: " + str(path))
    return Path(path)


def exact(a, b):
    return a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def stage(folder, name):
    p = Path(folder) / "states" / name
    m = read(p / "generation.json")
    c = checked(p / "control_quad.npz", m["control_file_sha256"])
    e = checked(p / "evidence.npz", m["evidence_file_sha256"])
    with np.load(c, allow_pickle=False) as z:
        arrays = {k: z[k] for k in ("xyz", "faces", "chart")}
    return p, m, arrays, e


def native_fans(control, x, t):
    v, q = control["xyz"], control["faces"]
    if x.dtype != np.dtype("float64") or q.ndim != 2 or q.shape[1] != 4:
        raise ValueError("Float64 quad-control/native surface is required")
    if len(x) != len(v) + len(q) or t.shape != (4 * len(q), 3) or not exact(x[:len(v)], v):
        raise ValueError("Actual control/native counts or retained XYZ differ")
    for begin in range(0, len(q), CHUNK):
        end = min(begin + CHUNK, len(q))
        faces = q[begin:end]
        centres = v[faces].mean(axis=1)
        if not exact(x[len(v) + begin:len(v) + end], centres):
            raise ValueError("Native face centres are not exact control means")
        ids = np.broadcast_to((len(v) + np.arange(begin, end))[:, None], faces.shape)
        expected = np.stack((faces, np.roll(faces, -1, axis=1), ids), axis=2).reshape(-1, 3)
        if not np.array_equal(t[4 * begin:4 * end], expected):
            raise ValueError("Native four-fan order/winding differs")
    return {"control_vertices": len(v), "control_quads": len(q), "native_vertices": len(x),
            "native_triangles": len(t), "exact_mean_centres": True, "exact_four_fans": True}


def topology(x, t):
    if x.ndim != 2 or x.shape[1] != 3 or t.ndim != 2 or t.shape[1] != 3 or not len(t):
        raise ValueError("Nonempty triangular geometry required")
    if t.dtype.kind not in "iu" or not np.isfinite(x).all() or t.min() < 0 or t.max() >= len(x):
        raise ValueError("Invalid coordinates or triangle indices")
    minimum, area, volume = float("inf"), 0., 0.
    for begin in range(0, len(t), CHUNK):
        p = x[t[begin:begin + CHUNK]]
        ar = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1) / 2
        minimum = min(minimum, float(ar.min()))
        area += float(ar.sum())
        volume += float(np.einsum("ij,ij->", p[:, 0], np.cross(p[:, 1], p[:, 2])) / 6)
    a, b = t.ravel(), np.roll(t, -1, axis=1).ravel()
    keys = np.minimum(a, b).astype(np.uint64) * np.uint64(len(x)) + np.maximum(a, b).astype(np.uint64)
    order = np.argsort(keys)
    keys = keys[order]
    starts = np.r_[0, np.flatnonzero(np.diff(keys)) + 1]
    counts = np.diff(np.r_[starts, len(keys)])
    directions = np.add.reduceat((a[order] > b[order]).astype(np.int64), starts)
    unique = keys[starts]
    graph = csr_matrix((np.ones(len(unique), np.uint8),
                        ((unique // len(x)).astype(np.int64), (unique % len(x)).astype(np.int64))),
                       shape=(len(x), len(x)))
    components = int(connected_components(graph, directed=False, return_labels=False))
    orphan = len(x) - len(np.unique(t))
    chi = int(len(x) - len(unique) + len(t))
    passed = bool(components == 1 and orphan == 0 and chi == 2 and np.all(counts == 2)
                  and np.all(directions == 1) and minimum > 0)
    result = dict(passed=passed, vertices=len(x), triangles=len(t), edges=len(unique),
                  components=components, orphan_vertices=orphan, Euler_characteristic=chi,
                  boundary_edges=int((counts == 1).sum()), nonmanifold_edges=int((counts > 2).sum()),
                  inconsistent_oriented_edges=int(((counts == 2) & (directions != 1)).sum()),
                  minimum_triangle_area=minimum, surface_area=area, signed_volume=volume, finite=True,
                  self_intersection_certified=False, fabrication_certified=False)
    if not passed:
        raise ValueError("Independent native topology QA failed: " + str(result))
    return result


def split_lineage(parent, child, evidence):
    """Check actual saved V/E/F order, four children and inherited material chart."""
    q, out = parent["faces"], child["faces"]
    nv = len(parent["xyz"])
    with np.load(evidence, allow_pickle=False) as z:
        edges, pf = z["input_edges"], z["parent_face"]
        saved_corner = "parent_corner" in z
        pc = z["parent_corner"] if saved_corner else out[:, 1]
    expected_edges = np.unique(np.sort(np.stack((q, np.roll(q, -1, axis=1)), axis=2).reshape(-1, 2), axis=1), axis=0)
    if not np.array_equal(edges, expected_edges) or not np.array_equal(pf, np.repeat(np.arange(len(q)), 4)):
        raise ValueError("Actual split edge order or four-child parent map differs")
    if not np.array_equal(pc, q.ravel()):
        raise ValueError("Actual child parent-corner identities differ")
    lookup = {tuple(e): i for i, e in enumerate(edges)}
    ef = np.array([[lookup[tuple(sorted((int(a), int(b))))] for a, b in zip(f, np.roll(f, -1))] for f in q])
    expected = np.stack((nv + np.roll(ef, 1, axis=1), q, nv + ef,
                         np.broadcast_to((nv + len(edges) + np.arange(len(q)))[:, None], q.shape)), axis=2).reshape(-1, 4)
    chart = np.concatenate((parent["chart"], parent["chart"][edges].mean(axis=1), parent["chart"][q].mean(axis=1)))
    if not np.array_equal(out, expected) or not exact(child["chart"], chart):
        raise ValueError("Actual child quad cycles or V/E/F material chart differ")
    return dict(passed=True, parent_quads=len(q), child_quads=len(out), input_edges=len(edges),
                exact_four_child_cycles=True, exact_parent_corner_IDs=True,
                parent_corner_evidence="saved array" if saved_corner else "actual child corner IDs",
                exact_material_chart=True)


def symmetry(control, native, evidence):
    x, q = control["xyz"], control["faces"]
    result = {}
    with np.load(evidence, allow_pickle=False) as z:
        for name, axis in (("x", 0), ("y", 1)):
            vp, fp = z["mirror_" + name + "_vertex_pairs"], z["mirror_" + name + "_face_pairs"]
            if vp.shape != (len(x),) or fp.shape != (len(q),) or vp.min() < 0 or vp.max() >= len(x) or fp.min() < 0 or fp.max() >= len(q):
                raise ValueError("Invalid mirror map indices")
            if not np.array_equal(vp[vp], np.arange(len(x))) or not np.array_equal(fp[fp], np.arange(len(q))):
                raise ValueError("Actual mirrors are not involutions")
            mapped = vp[q][:, ::-1]
            reflected = q[fp]
            cycles = np.zeros(len(q), bool)
            for shift in range(4):
                cycles |= np.all(mapped == np.roll(reflected, shift, axis=1), axis=1)
            if not cycles.all():
                raise ValueError("Actual mirror quad cycles are not orientation-reversed matches")
            target = x.copy(); target[:, axis] *= -1
            err = float(np.max(np.abs(x[vp] - target)))
            npair = np.r_[vp, len(x) + fp]
            target = native.copy(); target[:, axis] *= -1
            nerr = float(np.max(np.abs(native[npair] - target)))
            if max(err, nerr) > 1e-9:
                raise ValueError("Actual reflection coordinates fail")
            result[name.upper()] = dict(control_maximum_error=err, native_maximum_error=nerr,
                                        involution=True, oriented_quad_cycles=True)
    return dict(passed=True, axes=result)


def source_bindings(receipt, baseline_meta):
    sources = []
    bound = {}
    for original, row in receipt["source_snapshots"].items():
        current = checked(original, row["sha256"])
        snapshot = checked(row["snapshot"], row["sha256"])
        sources.append(dict(current=record(current), snapshot=record(snapshot)))
        bound[str(current).replace("\\", "/")] = row["sha256"]
    original_hashes = baseline_meta["geometry_code_sha256"]
    frozen = []
    for rel, original_digest in original_hashes.items():
        matches = [digest for p, digest in bound.items() if p.endswith("/" + rel)]
        if len(matches) != 1 or matches[0] != original_digest:
            raise ValueError("Established operator source hash differs or is missing: " + rel)
        frozen.append(dict(relative_path=rel, sha256=matches[0]))
    if not set(FROZEN_OPERATORS).issubset(original_hashes):
        raise ValueError("Required original operator inventory is incomplete")
    return dict(snapshots=sources, frozen_operators=frozen,
                original_workflow_source_count=len(frozen),
                verification_scope="Saved driver/current+snapshot hashes, recipe whitelist and independently checked arrays; not general filesystem instrumentation.")


def export_ply(path, x, t):
    if x.dtype != np.dtype("float64") or len(x) >= 2 ** 32:
        raise ValueError("Float64 XYZ and uint32 vertex-index budget required")
    header = ("ply\nformat binary_little_endian 1.0\ncomment Actual inherited-rule G4 native four-fan surface\n"
              f"element vertex {len(x)}\nproperty double x\nproperty double y\nproperty double z\n"
              f"element face {len(t)}\nproperty list uchar uint vertex_indices\nend_header\n").encode("ascii")
    dtype = np.dtype([("count", "u1"), ("indices", "<u4", (3,))])
    with Path(path).open("xb") as f:
        f.write(header)
        for begin in range(0, len(x), CHUNK):
            np.asarray(x[begin:begin + CHUNK], dtype="<f8").tofile(f)
        for begin in range(0, len(t), CHUNK):
            part = t[begin:begin + CHUNK]
            payload = np.empty(len(part), dtype=dtype); payload["count"] = 3; payload["indices"] = part
            payload.tofile(f)
    vx = np.memmap(path, mode="r", offset=len(header), dtype="<f8", shape=x.shape)
    ft = np.memmap(path, mode="r", offset=len(header) + 24 * len(x), dtype=dtype, shape=(len(t),))
    for begin in range(0, len(x), CHUNK):
        if not np.array_equal(vx[begin:begin + CHUNK].view(np.uint64), x[begin:begin + CHUNK].view(np.uint64)):
            raise ValueError("PLY float64 XYZ bits differ")
    for begin in range(0, len(t), CHUNK):
        part = ft[begin:begin + CHUNK]
        if not np.all(part["count"] == 3) or not np.array_equal(part["indices"], t[begin:begin + CHUNK]):
            raise ValueError("PLY native face readback differs")
    expected = len(header) + 24 * len(x) + 13 * len(t)
    if Path(path).stat().st_size != expected:
        raise ValueError("PLY payload size differs")
    del vx, ft
    return dict(**record(path), bytes=expected, full_vertex_readback_exact=True,
                full_triangle_readback_exact=True, vertex_dtype="little-endian float64", index_dtype="little-endian uint32")


def recipe_checks(contract, resolved, originals):
    recipe = contract["recipe"]
    if set(recipe) - TOP_KEYS:
        raise ValueError("Undeclared deformation settings: " + str(set(recipe) - TOP_KEYS))
    settings = contract["allowed_settings"]
    for key, expected in (("top_level", TOP_KEYS), ("event_changes", EVENT_KEYS),
                          ("event_amplitudes_fixed", FIXED_EVENT_KEYS),
                          ("root_recipe", ROOT_KEYS), ("sidewall_recipe", SIDE_KEYS)):
        if set(settings[key]) != expected:
            raise ValueError("Producer/independent settings whitelist differs: " + key)
    for key, allowed in (("root_recipe", ROOT_KEYS), ("sidewall_recipe", SIDE_KEYS)):
        if set(recipe.get(key, {})) - allowed:
            raise ValueError("Non-position event recipe change: " + key)
    if contract.get("actual_G0_geometry_unchanged") is not True or contract.get("mature_G7_sampling_used") is not False:
        raise ValueError("Original-input/early-only declarations differ")
    if recipe.get("fabrication_certified", False):
        raise ValueError("This inspector does not provide fabrication certification")
    templates = originals["G02_OVERLAP"]["authored_return_events"]
    requests = recipe.get("overlap_events")
    events = []
    if requests:
        if not 2 <= len(requests) <= 4:
            raise ValueError("Inherited return count must be two to four")
        for i, change in enumerate(requests):
            if set(change) - (EVENT_KEYS | FIXED_EVENT_KEYS):
                raise ValueError("Unknown inherited-return parameter")
            index = change.get("template_index", i % 2)
            if index not in (0, 1):
                raise ValueError("Unknown return template")
            value = dict(templates[index])
            for key in FIXED_EVENT_KEYS & set(change):
                if change[key] != value[key]:
                    raise ValueError("Return amplitude changed: " + key)
            value.update({k: v for k, v in change.items() if k != "template_index"})
            if not 0 < value["height"] < 1 or min(value["span"], value["overlap_width"]) <= 0:
                raise ValueError("Invalid material event bounds")
            events.append(value)
    else:
        events = templates
    if resolved["overlap_events"] != events or resolved["recipe"] != recipe:
        raise ValueError("Resolved actual returns differ from the declared inherited templates")
    for kind, stage_id in (("root", "G03_ROOT"), ("sidewall", "G03_SIDEWALL")):
        reference = dict(originals[stage_id]["event_recipe"])
        reference.update(recipe.get(kind + "_recipe", {}))
        if resolved[kind + "_event"] != reference:
            raise ValueError("Undeclared event geometry change: " + kind)
    if len(resolved["sidewall_event"]["beta_centres"]) != 3:
        raise ValueError("The original three sidewall events are required")
    task36 = originals["G01_ANCESTRY"]["task36_recipe"]
    if resolved["task36"] != task36:
        raise ValueError("Global Task36 recipe changed")
    axial = originals["G01_ANCESTRY"]["source_rule_revision_recipe"]
    if contract["common_G1_G2_axial_attenuation"] != axial:
        raise ValueError("The common original axial field policy changed")
    regions = recipe.get("split_regions", [])
    for region in regions:
        if set(region) - REGION_KEYS:
            raise ValueError("Unknown regional split parameter")
        if region.get("enabled", True):
            required = ("t_centre", "t_halfwidth", "theta_centre", "theta_halfwidth")
            if not all(k in region and np.isfinite(region[k]) for k in required):
                raise ValueError("Finite inherited material regions required")
            if min(region["t_halfwidth"], region["theta_halfwidth"]) <= 0:
                raise ValueError("Positive regional support required")
        for key, lo, hi in (("w3", -1, 1), ("w4", -1, 2), ("w1", -2, 2)):
            if key in region and (not np.isfinite(region[key]) or not lo <= region[key] <= hi):
                raise ValueError("Existing resolved split coefficient domain exceeded")
    return dict(passed=True, actual_return_count=len(events), only_allowed_settings=True,
                exact_original_return_amplitudes=True, exact_global_Task36_recipe=True,
                exact_original_axial_policy=True, no_external_XYZ_field_requested=True,
                requested_settings=recipe)


def plateau(q, start):
    q = np.abs(np.asarray(q, float))
    t = np.clip((q - start) / (1 - start), 0., 1.)
    s = t*t*t*(10. + t*(-15. + 6.*t))
    return np.where(q >= 1. - 1e-12, 0., np.clip(1. - s, 0., 1.))


def regional_checks(recipe, g1, evidence, meta):
    regions = [r for r in recipe.get("split_regions", [])
               if r.get("enabled", True) and any(k in r for k in ("w3", "w4", "w1"))]
    if not regions:
        if meta.get("regional_split_controls", {}).get("applied", False):
            raise ValueError("A disabled regional adapter was applied")
        return dict(applied=False, no_regional_XYZ_field=True)
    with np.load(evidence, allow_pickle=False) as z:
        edges = z["input_edges"]
        fcoords = g1["chart"][g1["faces"]].mean(axis=1)
        ecoords = g1["chart"][edges].mean(axis=1)
        def masks(coords):
            theta = np.arctan2(np.abs(coords[:, 2]), np.abs(coords[:, 1]))
            return np.array([plateau((coords[:, 0] - r["t_centre"]) / r["t_halfwidth"], .60) *
                             plateau((theta - r["theta_centre"]) / r["theta_halfwidth"], .65) for r in regions])
        fm, em = masks(fcoords), masks(ecoords)
        for key, expected in (("incoming_face_material_coordinates", fcoords),
                              ("incoming_edge_material_coordinates", ecoords),
                              ("face_region_masks", fm), ("edge_region_masks", em)):
            if not exact(z["regional_" + key], expected):
                raise ValueError("Regional material/mask evidence differs: " + key)
        counts = {}
        for key in ("w3", "w4", "w1"):
            raw = z["regional_raw_resolved_" + key]
            relevant = [(mask, r[key]) for mask, r in zip(em if key == "w1" else fm, regions) if key in r]
            if relevant:
                total = sum(mask for mask, _ in relevant)
                numerator = sum(mask * float(value) for mask, value in relevant)
                strength = np.minimum(total, 1.)
                expected = raw * (1 - strength) + numerator / np.maximum(total, 1.)
                expected[total == 0] = raw[total == 0]
            else:
                strength = np.zeros(len(raw)); expected = raw.copy()
            for stored in ("regional_modified_resolved_" + key, "resolved_" + key,
                           "regional_call_0_actual_" + key, "regional_call_1_actual_" + key):
                if not exact(z[stored], expected):
                    raise ValueError("Actual existing regional coefficient differs: " + stored)
            if not exact(z["regional_modified_support_" + key], strength):
                raise ValueError("Regional coefficient support differs")
            counts[key] = int(np.count_nonzero(raw != expected))
        for name in (k for k in z.files if k.startswith("regional_raw_resolved_")
                     and k.removeprefix("regional_raw_resolved_") not in ("w3", "w4", "w1")):
            key = name.removeprefix("regional_raw_resolved_")
            if not exact(z[name], z["resolved_" + key]):
                raise ValueError("An undeclared regional coefficient changed: " + key)
    m = meta["regional_split_controls"]
    if not m["applied"] or m["source_XYZ_warp"] or m["new_operator"] or not m["subdivide_restored"]:
        raise ValueError("Regional operator scope declaration differs")
    return dict(applied=True, independently_recomputed_material_masks=True,
                actual_resolved_existing_coefficients_exact=True, normal_controls_unchanged=True,
                modified_counts=counts, no_regional_XYZ_field=True,
                scope="Existing coefficients only; legitimate face/edge coupling halo is allowed.")


def event_provenance(states, resolved):
    _, _, wall, _ = states["G03_WALL"]
    _, _, root, re = states["G03_ROOT"]
    _, _, side, se = states["G03_SIDEWALL"]
    centre = wall["chart"][wall["faces"]].mean(axis=1)
    recipe = resolved["root_event"]
    theta = np.arctan2(centre[:, 2], centre[:, 1])
    q = (centre[:, 0] - recipe["root_parameter_centre"]) / recipe["root_parameter_halfwidth"]
    u = (theta - (recipe["root_cross_centre"] + recipe["root_cross_sweep"] * np.sin(np.pi*q))) / recipe["root_cross_halfwidth"]
    canonical = np.all(wall["chart"][wall["faces"], 1:] > recipe["seam_tolerance"], axis=(1, 2))
    selected = np.flatnonzero(canonical & (q*q + u*u < 1.))
    with np.load(re, allow_pickle=False) as z:
        if not np.array_equal(z["event_001_selected_input_faces"], selected):
            raise ValueError("ROOT selected parents do not match the original chart ellipse")
    children = []
    with np.load(se, allow_pickle=False) as z:
        beta = z["root_boundary_beta"]
        row, col = z["parent_root_sidewall_row"], z["parent_root_sidewall_column"]
        sr = resolved["sidewall_event"]
        for i, c in enumerate(sr["beta_centres"]):
            difference = np.arctan2(np.sin(beta - c), np.cos(beta - c))
            columns = np.flatnonzero(np.abs(difference) < sr["beta_halfwidth"])
            expected = np.flatnonzero(np.isin(row, sr["parent_rows"]) & np.isin(col, columns))
            prefix = "event_" + f"{i + 2:03d}" + "_"
            if not np.array_equal(z[prefix + "selected_parent_source_face_ids"], expected):
                raise ValueError("SIDEWALL selected parent identities differ from original inherited beta/rows")
            if not np.all(z[prefix + "selected_parent_event_ids"] == 1) or not np.all(z[prefix + "selected_parent_roles"] == 1):
                raise ValueError("SIDEWALL escaped the inherited root wall")
            children.append(dict(event_id=i + 2, selected_parent_faces=len(expected),
                                 exact_parent_source_ids_sha256=ah(expected)))
        g3event, g3role = z["face_event_ids"], z["face_roles"]
        if g3event.shape != (len(side["faces"]),) or g3role.shape != g3event.shape:
            raise ValueError("Actual G3 event/role dimensions differ")
    with np.load(states["G04_NEUTRAL"][3], allow_pickle=False) as z:
        pf = z["parent_face"]
        if not np.array_equal(z["face_event_ids"], g3event[pf]) or not np.array_equal(z["face_roles"], g3role[pf]):
            raise ValueError("G4 operation colors do not follow actual G3 parents")
        ev, ct = np.unique(z["face_event_ids"], return_counts=True)
    return dict(passed=True, root_selection_count=len(selected), root_selection_ids_sha256=ah(selected),
                root_original_chart_ellipse_exact=True, sidewall_original_beta_rows_exact=True,
                sidewall_events=children, G4_event_counts={str(int(k)): int(v) for k, v in zip(ev, ct)},
                G4_roles_events_actual_parent_transport_exact=True,
                color_meaning="Actual operation and selected-parent provenance; not curvature classification or total XYZ-displacement attribution.")


def inspect_one(folder, receipt, original_g0, baseline_g4, baseline_meta, original_states):
    if receipt.get("genuine_early_replay") is not True or receipt.get("final_stage") != "G04_NEUTRAL":
        raise ValueError("An actual initial G4 replay is required")
    recipe_path = checked(folder / "RECIPE.json", receipt["recipe_sha256"])
    contract = read(recipe_path)
    resolved_path = folder / "RECIPE_EARLY.json"
    resolved = read(resolved_path)
    originals = {s: read(original_states / s / "generation.json") for s in STAGES}
    settings = recipe_checks(contract, resolved, originals)
    if contract["source_snapshots"] != receipt["source_snapshots"]:
        raise ValueError("Receipt/recipe executed snapshots differ")
    sources = source_bindings(receipt, baseline_meta)
    if contract["frozen_operator_code_sha256"] != baseline_meta["geometry_code_sha256"]:
        raise ValueError("Original selected workflow code inventory differs")
    states = {s: stage(folder, s) for s in STAGES}
    g0 = states["G00_INPUT"][2]
    for key in ("xyz", "faces", "chart"):
        if not exact(g0[key], original_g0[key]):
            raise ValueError("Original SPAN G0 byte identity differs: " + key)
    stage_bindings = []
    nodes = {n["id"]: n for n in receipt["stages"]}
    for i, name in enumerate(STAGES):
        p, m, _, _ = states[name]
        if sha(p / "generation.json") != nodes[name]["generation_json_sha256"]:
            raise ValueError("Stage generation receipt binding differs")
        if not m["checks"]["passed"]:
            raise ValueError("Producer stage checks did not pass")
        for rel, digest in contract["frozen_operator_code_sha256"].items():
            if m["geometry_code_sha256"].get(rel) != digest:
                raise ValueError("Stage actual historical operator hash differs: " + rel)
        if i and (m["source_control_sha256"] != states[STAGES[i - 1]][1]["control_file_sha256"]
                  or m["source_generation_json_sha256"] != sha(states[STAGES[i - 1]][0] / "generation.json")):
            raise ValueError("Actual stage parent chain differs")
        stage_bindings.append(record(p / "generation.json"))
    splits = {}
    for before, after in (("G00_INPUT", "G01_ANCESTRY"), ("G01_ANCESTRY", "G02_OVERLAP"),
                          ("G02_OVERLAP", "G03_WALL"), ("G03_SIDEWALL", "G04_NEUTRAL")):
        splits[after] = split_lineage(states[before][2], states[after][2], states[after][3])
    for name in ("G01_ANCESTRY", "G02_OVERLAP"):
        m = states[name][1]
        for key in ("task36_recipe", "field_recipe", "field_iterations"):
            if m[key] != originals[name][key]:
                raise ValueError("Original global subdivision/finite field policy changed: " + name + "/" + key)
        if m.get("source_rule_revision_recipe", m.get("source_rule_revision", {}).get("recipe")) != originals[name]["source_rule_revision_recipe"]:
            raise ValueError("Actual original axial field policy changed: " + name)
    if states["G02_OVERLAP"][1]["authored_return_events"] != resolved["overlap_events"]:
        raise ValueError("Saved actual G2 returns differ from resolved settings")
    regional = regional_checks(contract["recipe"], states["G01_ANCESTRY"][2],
                               states["G02_OVERLAP"][3], states["G02_OVERLAP"][1])
    events = event_provenance(states, resolved)
    final, meta, control, evidence = states["G04_NEUTRAL"]
    if receipt["final"] != meta:
        raise ValueError("Whole/final generation receipt differs")
    geometry = checked(final / "geometry.npz", meta["geometry_file_sha256"])
    with np.load(geometry, allow_pickle=False) as z:
        x, t = z["xyz"], z["faces"]
    if ah(x) != meta["checks"]["native_xyz_sha256"] or ah(t) != meta["checks"]["native_faces_sha256"]:
        raise ValueError("Actual native array hashes differ")
    fans = native_fans(control, x, t)
    quality = topology(x, t)
    sym = symmetry(control, x, evidence)
    sid = receipt["candidate"]
    baseline = None
    if sid == "I00":
        baseline = {key: exact(control[key], baseline_g4[key]) for key in ("xyz", "faces", "chart")}
        if not all(baseline.values()):
            raise ValueError("I00 is not an exact original end-rule G4 replay")
    g2, b2 = states["G02_OVERLAP"][2], None
    with np.load(original_states / "G02_OVERLAP/control_quad.npz", allow_pickle=False) as z:
        b2 = {k: z[k] for k in ("xyz", "faces", "chart")}
    if not exact(g2["faces"], b2["faces"]) or not exact(g2["chart"], b2["chart"]):
        raise ValueError("G2 fixed-topology material correspondence differs")
    distance = np.linalg.norm(g2["xyz"] - b2["xyz"], axis=1)
    row = dict(id=sid, source_receipt=record(folder / "RECEIPT.json"), recipe=record(recipe_path),
               resolved_recipe=record(resolved_path), actual_geometry=record(geometry),
               actual_control_geometry=record(final / "control_quad.npz"),
               original_SPAN_G0_all_three_arrays_byte_exact=True, allowed_settings=settings,
               executed_code=sources, actual_stage_bindings=stage_bindings, split_lineage=splits,
               regional_split_controls=regional, actual_operation_provenance=events,
               native_surface=fans, quality=quality, actual_symmetry=sym, I00_original_G4_byte_exact=baseline,
               G2_paired_material_displacement_quantiles=np.quantile(distance, [0, .5, .9, .99, 1]).tolist(),
               physical_extent=np.ptp(x, axis=0).tolist(), no_G5_G7_or_late_ornament=True,
               no_outside_region_XYZ_invariance_claim=True, aesthetic_score=False,
               self_intersection_or_fabrication_certified=False)
    return row, x, t


def main(a):
    start = time.perf_counter()
    found = {}
    for p in sorted(a.root.rglob("RECEIPT.json")):
        r = read(p)
        if r.get("status") != "PASS":
            continue
        if r.get("schema") != SCHEMA:
            if "INHERITED_POSITION_SPLIT_DIRECTION" in r.get("schema", ""):
                raise ValueError("Unsupported completed inherited schema: " + str(p))
            continue
        sid = r.get("candidate", r.get("id"))
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", sid) or sid in found:
            raise ValueError("Invalid or duplicate inherited candidate identifier")
        found[sid] = (p, r)
    if "I00" not in found or (a.expected_count is not None and len(found) != a.expected_count):
        raise ValueError("Completed I00 and the requested number of actual inherited replays are required")
    checked(a.original_g0, ORIGINAL_G0_SHA)
    with np.load(a.original_g0, allow_pickle=False) as z:
        original_g0 = {k: z[k] for k in ("xyz", "faces", "chart")}
    baseline_meta = read(a.original_states / "G04_NEUTRAL/generation.json")
    with np.load(checked(a.original_states / "G04_NEUTRAL/control_quad.npz", baseline_meta["control_file_sha256"]), allow_pickle=False) as z:
        baseline_g4 = {k: z[k] for k in ("xyz", "faces", "chart")}
    if not a.inspect_only:
        if a.output is None:
            raise ValueError("--output is required for export")
        a.output.mkdir(parents=True, exist_ok=False)
        (a.output / "source_snapshot").mkdir()
        shutil.copyfile(__file__, a.output / "source_snapshot" / Path(__file__).name)
    rows = []
    for sid, (p, r) in sorted(found.items()):
        row, x, t = inspect_one(p.parent, r, original_g0, baseline_g4, baseline_meta, a.original_states)
        if not a.inspect_only:
            target = a.output / sid; target.mkdir()
            row["model"] = export_ply(target / ("CHESHIRE_INHERITED_" + sid + "_G4_NATIVE_FULL.ply"), x, t)
            write(target / "EXPORT_RECEIPT.json", row)
        rows.append(row)
        print("INHERITED_G4_QA_PASS", sid, len(x), len(t), flush=True)
    result = dict(schema="CHESHIRE_INHERITED_RULE_EXPORT_QA_V1", passed=True, completed_count=len(rows),
                  variants=rows, original_input=record(a.original_g0), original_states=str(a.original_states),
                  source=record(__file__), inspection_only=a.inspect_only,
                  all_exported_geometry_full_readback_exact=not a.inspect_only,
                  no_geometry_repair_or_normalization=True, aesthetic_score=False,
                  self_intersection_or_manufacturing_certified=False, elapsed_seconds=time.perf_counter() - start)
    if not a.inspect_only:
        write(a.output / "INHERITED_EXPORT_AND_QA.json", result)
    print("INHERITED_QA_AGGREGATE_PASS", len(rows), result["elapsed_seconds"], flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--expected-count", type=int)
    p.add_argument("--inspect-only", action="store_true")
    p.add_argument("--original-g0", type=Path, default=ORIGINAL_G0)
    p.add_argument("--original-states", type=Path, default=ORIGINAL_STATES)
    main(p.parse_args())
