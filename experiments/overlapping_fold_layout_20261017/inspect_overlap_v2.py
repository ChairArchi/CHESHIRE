"""Original-kernel overlapping-fold QA with a matched-sampling baseline.

The historical 25-ring SPAN is reproduced separately. K00 is the unchanged
two-event constructor at declared 49-ring sampling, not the historical G4.
Variants change only permitted original EVENTS and optional finite-field layout.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import re
import shutil
import sys
import time
import uuid

import numpy as np

HERE = Path(__file__).resolve().parent
SCHEMA = "CHESHIRE_OVERLAPPING_ORIGINAL_SEED_LAYOUT_REPLAY_V1"
COMMON_PATH = HERE.parent / "inherited_rule_variations_20261017/inspect_inherited.py"
COMMON_SHA = "0a0286c7374e1130ed23cb641bce6d8e35d69b34678b07fb087373a34068d664"
ORIGINAL_RECIPE_SHA = "6226ab8043dbd50732da3be842e9a0d2fb3f6fd8a1906dc5d9e1936564a615e1"
SEED_KEYS = {"template_index", "id", "height", "span", "direction", "sweep", "overlap_width"}


def load_module(path, prefix):
    spec = importlib.util.spec_from_file_location(prefix + uuid.uuid4().hex, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


def common():
    import hashlib
    if hashlib.sha256(COMMON_PATH.read_bytes()).hexdigest() != COMMON_SHA:
        raise ValueError("The reused independent native QA/PLY helper changed")
    return load_module(COMMON_PATH, "strong_common_")


def resolved_events(original, requested):
    """Resolve parameters independently; never invoke the producer's resolver."""
    result = copy.deepcopy(original)
    for group_name, requests in (requested or {}).items():
        group = int(group_name)
        if group not in (1, 2, 3) or str(group) != str(group_name):
            raise ValueError("An original seed event group is required")
        if (group == 1 and len(requests) not in (2, 6, 8)) or (group != 1 and len(requests) != len(original[group])):
            raise ValueError("Declared original-event multiplicity is not permitted")
        values = []
        for i, request in enumerate(requests):
            if set(request) - SEED_KEYS:
                raise ValueError("A seed amplitude or unknown construction parameter changed")
            index = request.get("template_index", i % len(original[group]))
            if not isinstance(index, int) or not 0 <= index < len(original[group]):
                raise ValueError("Unknown original seed template index")
            value = copy.deepcopy(original[group][index])
            value.update({k: v for k, v in request.items() if k != "template_index"})
            if not all(np.isfinite(value[k]) for k in ("height", "span", "direction", "sweep", "overlap_width")):
                raise ValueError("Finite original-event parameters required")
            if not 0 < value["height"] < 1 or min(value["span"], value["overlap_width"]) <= 0:
                raise ValueError("Invalid seed event location or support")
            values.append(value)
        result[group] = values
    return result


def integer_groups(value):
    return {int(k): v for k, v in value.items()}


def seed_reference(q, contract, g0, evidence, meta, original_g0, original_recipe):
    """Reevaluate the frozen legacy constructor, not an exported XYZ delta."""
    repo = Path(contract["source_repo"])
    sys.path.insert(0, str(repo / "src"))
    source = load_module(repo / "experiments/column_development_20261011/seed_mass.py", "independent_seed_")
    inherited = copy.deepcopy(source.source.old.repair.legacy.EVENTS)
    seed_events = contract["recipe"].get("seed_events")
    resolved = resolved_events(inherited, seed_events)
    actual = meta["original_seed_recipe"]
    sampling = contract["recipe"].get("carrier_sampling", dict(rings=49, sectors=16, radius=.78))
    if sampling != dict(rings=49, sectors=16, radius=.78) or contract["declared_carrier_sampling"] != sampling:
        raise ValueError("The comparison requires matched declared 49/16/.78 sampling")
    carrier, chart = source.variation.carrier(copy.deepcopy(sampling))
    if not q.exact(carrier.faces, g0["faces"]) or not q.exact(chart, g0["chart"]):
        raise ValueError("Declared carrier topology/chart do not regenerate the saved G0")
    if actual["original_SPAN_recipe"] != original_recipe:
        raise ValueError("Original radius/end/bridge recipe changed")
    if integer_groups(actual["original_legacy_events"]) != inherited or integer_groups(actual["resolved_legacy_events"]) != resolved:
        raise ValueError("Saved original/resolved seed EVENTS differ")
    if actual["same_original_constructor"] is not True or actual["original_t_warp_unchanged"] is not True:
        raise ValueError("Original constructor and original material t map are required")
    if contract.get("original_seed_constructor_replayed") is not True:
        raise ValueError("The actual original seed constructor was not declared")
    if contract["actual_G0_geometry_unchanged"] is not False or actual["original_source_G0_exact"] is not False:
        raise ValueError("49-ring sampling cannot claim original 25-ring G0 equality")
    original25, parts25 = source.legacy_core(original_g0["chart"].copy(), copy.deepcopy(original_recipe), "SPAN")
    if not q.exact(original25, original_g0["xyz"]):
        raise ValueError("The original 25-ring constructor did not reproduce historical SPAN XYZ")
    with np.load(q.ORIGINAL_G0.parent / "operation_fields.npz", allow_pickle=False) as z:
        proof25 = {key: q.exact(parts25[key], z[key]) for key in parts25}
    if not all(proof25.values()) or actual["original25_constructor_exact"] != dict(xyz=True, parts=proof25):
        raise ValueError("Original 25-ring component proof differs")
    baseline_xyz, baseline_parts = source.legacy_core(chart.copy(), copy.deepcopy(original_recipe), "SPAN")
    legacy = source.source.old.repair.legacy
    previous = legacy.EVENTS
    try:
        legacy.EVENTS = copy.deepcopy(resolved)
        xyz, parts = source.legacy_core(g0["chart"].copy(), copy.deepcopy(original_recipe), "SPAN")
    finally:
        legacy.EVENTS = previous
    if not q.exact(xyz, g0["xyz"]) or not q.exact(sum(parts.values()), xyz):
        raise ValueError("Saved G0 is not the exact original-kernel evaluation of declared parameters")
    with np.load(evidence, allow_pickle=False) as z:
        for key in ("proportion", "proven_deep_fold", "overrunning_return", "terminal_return"):
            if not q.exact(z[key], parts[key]):
                raise ValueError("Actual seed operation field differs from independent reevaluation: " + key)
    for key in ("proportion", "overrunning_return", "terminal_return"):
        if not q.exact(parts[key], baseline_parts[key]):
            raise ValueError("A non-fold source component changed at matched sampling: " + key)
    delta = np.linalg.norm(xyz - baseline_xyz, axis=1)
    cap = (g0["chart"][:, 0] == 0) | (g0["chart"][:, 0] == 1)
    sampling_exact = q.exact(xyz, baseline_xyz)
    if actual["declared_sampling_baseline_exact"] != sampling_exact or actual["carrier_sampling"] != sampling:
        raise ValueError("Actual sampling baseline declaration differs")
    return dict(passed=True, original_constructor_source=q.record(repo / "experiments/column_development_20261011/seed_mass.py"),
                independently_re_evaluated_original_kernel=True, exact_saved_XYZ_and_four_operation_fields=True,
                declared_carrier_sampling=sampling, exact_regenerated_carrier_faces_and_chart=True,
                original25_constructor_XYZ_and_components_byte_exact=True,
                original25_G4_identity_claimed=False, matched_sampling_two_event_baseline_exact=sampling_exact,
                original_seed_recipe_unchanged=True, original_t_warp_unchanged=True,
                original_legacy_events=inherited, resolved_legacy_events=resolved,
                actual_major_EVENT_count=len(resolved[1]),
                three_nonfold_components_exact_at_matched_sampling=True,
                changed_controls=int(np.count_nonzero(delta > 1e-12)),
                coordinate_delta_quantiles=np.quantile(delta, [0, .5, .9, .99, 1]).tolist(),
                RMS_coordinate_delta=float(np.sqrt(np.mean(delta ** 2))),
                original_cap_coordinate_delta_maximum=float(delta[cap].max()),
                new_XYZ_warp_or_new_primitive=False)


def settings_checks(q, contract, resolved, originals):
    extra = {"seed_events", "carrier_sampling", "field_layout"}
    allowed_top = set(contract["allowed_settings"]["top_level"])
    if set(contract["recipe"]) - (q.TOP_KEYS | extra):
        raise ValueError("Undeclared strong-layout construction setting")
    if allowed_top not in (q.TOP_KEYS | {"seed_events", "carrier_sampling"}, q.TOP_KEYS | extra):
        raise ValueError("Strong-layout allowed-settings inventory differs")
    # Project only the later parameter vocabulary onto the already frozen
    # independent whitelist. This is not a G0 equality test: seed_reference
    # independently evaluates and reports the intentionally changed G0 above.
    later = copy.deepcopy(contract)
    for key in extra:
        later["recipe"].pop(key, None)
    later["allowed_settings"]["top_level"] = list(q.TOP_KEYS)
    later["actual_G0_geometry_unchanged"] = True
    resolved_later = copy.deepcopy(resolved)
    resolved_later["recipe"] = later["recipe"]
    checks = q.recipe_checks(later, resolved_later, originals)
    checks["requested_settings"] = contract["recipe"]
    checks["G0_equality_checked_separately"] = True
    return checks


def field_checks(q, folder, contract, states, originals):
    layout = contract["recipe"].get("field_layout")
    if not layout:
        for name in ("G01_ANCESTRY", "G02_OVERLAP"):
            if states[name][1]["field_recipe"] != originals[name]["field_recipe"]:
                raise ValueError("An undeclared finite-field layout changed")
        return dict(applied=False, original_finite_field_recipes_exact=True)
    if set(layout) - {"centres", "axial"}:
        raise ValueError("Only original finite-field centres/axial range may change")
    centres = np.asarray(layout.get("centres", originals["G01_ANCESTRY"]["field_recipe"]["centres"]), float)
    axial = float(layout.get("axial", originals["G01_ANCESTRY"]["field_recipe"]["axial"]))
    if centres.shape != (2,) or not np.isfinite(centres).all() or not 0 < centres[0] < centres[1] < 10 or not 0 < axial <= 5:
        raise ValueError("Finite ordered two-field layout required")
    path, evidence = folder / "FIELD_LAYOUT.json", folder / "FIELD_LAYOUT_EVIDENCE.npz"
    meta = q.read(path)
    if meta["cfg_overrides"] != layout or not meta["attributes_restored"]:
        raise ValueError("Field adapter scope/configuration differs")
    if any(meta[k] is not False for k in ("actual_mesh_CSG", "render_only_overlap", "original_kernel_changed", "original_cache_reused")):
        raise ValueError("The explicit operation is the original field union, not mesh CSG or old-cache substitution")
    if meta["response_fraction_and_budgets_unchanged"] is not True:
        raise ValueError("Original field response/budget policy changed")
    if contract["declared_field_layout"] != layout:
        raise ValueError("Declared field-layout contract and executed recipe differ")
    snapshots = contract["source_snapshots"]
    adapter_paths = [p for p in snapshots if Path(p).name == "overlap_field_targets.py"]
    if len(adapter_paths) != 1 or snapshots[adapter_paths[0]]["sha256"] != meta["adapter_sha256"]:
        raise ValueError("Actual field adapter source is not snapshot-bound")
    for source, digest in meta["original_kernel_code_sha256"].items():
        q.checked(source, digest)
        if source not in snapshots or snapshots[source]["sha256"] != digest:
            raise ValueError("The fresh-cache/classifier kernel is not an executed source snapshot")
    repo = Path(contract["source_repo"])
    sys.path.insert(0, str(repo / "src"))
    seed = load_module(repo / "experiments/column_development_20261011/seed_mass.py", "field_probe_reference_")
    variation = seed.variation
    param_keys = ("powers", "centres", "axial", "scales", "orientation", "roll", "offset_y", "iterations", "convention")
    rows = []
    with np.load(evidence, allow_pickle=False) as saved:
        for name, iterations in (("G01_ANCESTRY", 4), ("G02_OVERLAP", 8)):
            actual = states[name][1]
            cfg = dict(originals[name]["field_recipe"], **layout)
            if actual["field_recipe"] != cfg:
                raise ValueError("The actual evaluated field recipe differs from the declared existing-field layout")
            cache = actual["field_cache"]
            if cache != meta["cache_records"][str(iterations)]:
                raise ValueError("Stage actual cache binding differs from the final adapter record")
            root = Path(cache["fresh_cache_root"]).resolve()
            cache_path = Path(cache["path"]).resolve()
            if root != (folder / "field_cache").resolve() or not cache_path.is_relative_to(root):
                raise ValueError("The actual field cache must be in this fresh candidate's cache root")
            field_json = q.checked(cache_path / "field.json", cache["field_json_sha256"])
            grid = q.checked(cache_path / "outside_grid.npz", cache["outside_grid_sha256"])
            params = {k: cfg[k] for k in param_keys}
            info = q.read(field_json)
            if info["parameters"] != params or cache["actual_field_parameters"] != params:
                raise ValueError("Fresh outside-grid parameters differ from actual apply-field parameters")
            if cache["original_cache_reused"] or not cache["fresh_cache_matches_actual_cfg"] or not cache["every_saved_outside_point_confirmed"]:
                raise ValueError("Fresh-cache producer checks did not pass")
            with np.load(grid, allow_pickle=False) as z:
                points = z["points"]
            if points.ndim != 2 or points.shape[1] != 3 or not len(points) or not np.isfinite(points).all():
                raise ValueError("Actual outside lattice is invalid")
            if cache["outside_points"] != len(points) or cache["adapter_sha256"] != meta["adapter_sha256"]:
                raise ValueError("Actual outside lattice count or adapter version differs")
            sample_ids = np.unique(np.linspace(0, len(points) - 1, min(1024, len(points)), dtype=np.int64))
            if variation.classify(points[sample_ids], cfg).any():
                raise ValueError("A deterministic independent lattice sample is inside the field union")
            prefix = "iter" + str(iterations) + "_"
            probe = saved[prefix + "probe_points"]
            individual = []
            for centre, power in zip(cfg["centres"], cfg["powers"]):
                individual.append(variation.classify(probe, dict(cfg, centres=[centre], powers=[power])))
            union = variation.classify(probe, cfg)
            if not np.array_equal(union, individual[0] | individual[1]):
                raise ValueError("The original classifier does not equal the asserted two-field logical union")
            for key, expected in (("inside_first", individual[0]), ("inside_second", individual[1]), ("inside_union", union)):
                if not q.exact(saved[prefix + key], expected):
                    raise ValueError("Actual union evidence differs from the independently called original classifier")
            baseline_cfg = originals[name]["field_recipe"]
            baseline_individual = [variation.classify(probe, dict(baseline_cfg, centres=[c], powers=[p]))
                                   for c, p in zip(baseline_cfg["centres"], baseline_cfg["powers"])]
            rows.append(dict(stage=name, actual_field_recipe=cfg, field_json=q.record(field_json),
                             outside_grid=q.record(grid), outside_lattice_points=len(points),
                             independent_outside_samples=len(sample_ids), independent_outside_samples_passed=True,
                             independent_OR_probes=len(probe), inside_both=int((individual[0] & individual[1]).sum()),
                             original_layout_inside_both_same_probes=int((baseline_individual[0] & baseline_individual[1]).sum()),
                             inside_union=int(union.sum()), original_classifier_OR_exact=True,
                             actual_field_parameters_and_fresh_cache_exact=True))
    return dict(applied=True, declared_existing_field_layout=layout, stages=rows,
                adapter_record=q.record(path), probe_evidence=q.record(evidence),
                actual_mesh_CSG=False, independent_check_scope="Original-kernel source/hash, actual stage CFG/cache binding, deterministic outside samples and exact sparse two-domain OR probes; not a volume/solid certificate.")


def slenderness(control_xyz, native_xyz, triangles):
    """Same world-coordinate sections; neither normalize nor edit geometry."""
    levels = np.arange(.25, 10., .5)
    low = np.full((len(levels), 2), np.inf)
    high = np.full((len(levels), 2), -np.inf)
    counts = np.zeros(len(levels), np.int64)
    for begin in range(0, len(triangles), 131072):
        p = native_xyz[triangles[begin:begin + 131072]]
        a, b = p, np.roll(p, -1, axis=1)
        za, zb = a[:, :, 2], b[:, :, 2]
        for i, z in enumerate(levels):
            cross = ((za <= z) & (zb > z)) | ((zb <= z) & (za > z))
            if not cross.any():
                continue
            aa, bb = a[cross], b[cross]
            fraction = (z - aa[:, 2]) / (bb[:, 2] - aa[:, 2])
            xy = aa[:, :2] + fraction[:, None] * (bb[:, :2] - aa[:, :2])
            low[i] = np.minimum(low[i], xy.min(axis=0))
            high[i] = np.maximum(high[i], xy.max(axis=0))
            counts[i] += len(xy)
    sections, slabs = [], []
    for i, z in enumerate(levels):
        sections.append(dict(world_Z=float(z), edge_plane_hits=int(counts[i]),
                             XY_width=(high[i] - low[i]).tolist() if counts[i] else None))
        points = control_xyz[(control_xyz[:, 2] >= z - .25) & (control_xyz[:, 2] < z + .25)]
        interval = np.quantile(points[:, :2], [.05, .95], axis=0) if len(points) else None
        slabs.append(dict(world_Z_interval=[float(z - .25), float(z + .25)], controls=len(points),
                          XY_P05_P95_width=(interval[1] - interval[0]).tolist() if interval is not None else None))
    span = np.ptp(native_xyz, axis=0)
    return dict(world_Z_sections=sections, world_Z_control_slabs=slabs,
                whole_XY_width_over_height=(span[:2] / span[2]).tolist(),
                exact_section_scope="X/Y extrema of stored linear native triangle-plane intersections; duplicate shared-edge hits affect counts, not extrema. These are envelopes, not a closed-section/solid certificate.",
                control_slab_scope="P05-to-P95 control-point envelope proxy; not arc-length- or area-weighted cross sections.",
                fixed_world_Z_reference=[0., 10.], geometry_normalized=False, aesthetic_score=False)


def field_pair_comparison(q, rows):
    by_id = {r["id"]: r for r in rows}
    if not {"K08", "K08_M2"}.issubset(by_id):
        return dict(performed=False, reason="Both completed selected K08 and K08_M2 are required")
    a, b = by_id["K08"], by_id["K08_M2"]
    with np.load(q.checked(a["actual_seed_controls"]["path"], a["actual_seed_controls"]["sha256"]), allow_pickle=False) as z:
        seed_a = {k: z[k] for k in ("xyz", "faces", "chart")}
    with np.load(q.checked(b["actual_seed_controls"]["path"], b["actual_seed_controls"]["sha256"]), allow_pickle=False) as z:
        seed_b = {k: z[k] for k in ("xyz", "faces", "chart")}
    equality = {k: q.exact(seed_a[k], seed_b[k]) for k in seed_a}
    if not all(equality.values()):
        raise ValueError("The K08/M2 matched-field comparison changed the seed geometry")
    section_rows = []
    for before, after in zip(a["slenderness"]["world_Z_sections"], b["slenderness"]["world_Z_sections"]):
        aw, bw = before["XY_width"], after["XY_width"]
        ratio = (np.asarray(bw) / np.asarray(aw)).tolist() if aw and bw and min(aw) > 0 else None
        section_rows.append(dict(world_Z=before["world_Z"], K08_XY_width=aw, M2_XY_width=bw, M2_over_K08=ratio))
    recipes = [copy.deepcopy(r["allowed_settings"]["requested_settings"]) for r in (a, b)]
    for recipe in recipes:
        for key in ("id", "name", "label_ko", "family", "description_ko", "field_layout"):
            recipe.pop(key, None)
    va, vb = a["quality"]["signed_volume"], b["quality"]["signed_volume"]
    ratios = np.asarray([r["M2_over_K08"] for r in section_rows if r["M2_over_K08"] is not None], float)
    return dict(performed=True, matched_G0_arrays_byte_exact=equality,
                field_layout_only_authoring_difference=recipes[0] == recipes[1],
                other_declared_setting_differences_present=recipes[0] != recipes[1],
                exact_native_plane_envelope_width_comparison=section_rows,
                XY_width_ratio_quantiles=np.quantile(ratios, [0, .5, .9, 1], axis=0).tolist() if len(ratios) else None,
                XY_width_ratio_quantile_levels=[0, .5, .9, 1],
                oriented_algebraic_volume=dict(K08=va, K08_M2=vb, M2_over_K08=vb / va if va else None),
                interpretation="Widths and algebraic oriented volume are numerical evidence, not aesthetic success or physical solid volume. Self-intersections can invalidate a material-volume interpretation.")


def inspect_one(q, folder, receipt, original_g0, original_recipe, original_states, baseline_id, baseline_g2):
    if receipt.get("genuine_early_replay") is not True or receipt.get("final_stage") != "G04_NEUTRAL":
        raise ValueError("An actual original-kernel G0-to-G4 replay is required")
    recipe_path = q.checked(folder / "RECIPE.json", receipt["recipe_sha256"])
    contract = q.read(recipe_path)
    resolved_path = folder / "RECIPE_EARLY.json"
    resolved = q.read(resolved_path)
    originals = {s: q.read(original_states / s / "generation.json") for s in q.STAGES}
    if contract["source_snapshots"] != receipt["source_snapshots"]:
        raise ValueError("Saved recipe/receipt executed sources differ")
    sources = q.source_bindings(receipt, originals["G04_NEUTRAL"])
    if contract["frozen_operator_code_sha256"] != originals["G04_NEUTRAL"]["geometry_code_sha256"]:
        raise ValueError("Original selected workflow source inventory changed")
    settings = settings_checks(q, contract, resolved, originals)
    states = {s: q.stage(folder, s) for s in q.STAGES}
    nodes = {row["id"]: row for row in receipt["stages"]}
    stage_bindings = []
    for i, name in enumerate(q.STAGES):
        p, m, _, _ = states[name]
        if q.sha(p / "generation.json") != nodes[name]["generation_json_sha256"] or not m["checks"]["passed"]:
            raise ValueError("Actual stage receipt or producer geometry gate differs")
        for rel, digest in contract["frozen_operator_code_sha256"].items():
            if m["geometry_code_sha256"].get(rel) != digest:
                raise ValueError("A stage used a different historical operator")
        if i and (m["source_control_sha256"] != states[q.STAGES[i - 1]][1]["control_file_sha256"]
                  or m["source_generation_json_sha256"] != q.sha(states[q.STAGES[i - 1]][0] / "generation.json")):
            raise ValueError("Actual stage parent chain differs")
        stage_bindings.append(q.record(p / "generation.json"))
    seed = seed_reference(q, contract, states["G00_INPUT"][2], states["G00_INPUT"][3],
                          states["G00_INPUT"][1], original_g0, original_recipe)
    routing = states["G01_ANCESTRY"][1]["carrier_association_parameter_routing"]
    if not all(routing[k] is True for k in ("parameter_only", "original_function_body_unchanged", "restored_after_G1")):
        raise ValueError("G1 must use parameter-only routing of the original carrier association")
    sampling = seed["declared_carrier_sampling"]
    old_sampling = dict(rings=25, sectors=16, radius=.78)
    if routing["original_requested_sampling"] != old_sampling or routing["declared_sampling"] != sampling:
        raise ValueError("G1 actual association sampling differs")
    overrides = [row for row in routing["actual_calls"] if row["declared_sampling_override"]]
    if len(overrides) != 1 or overrides[0]["requested"] != old_sampling or overrides[0]["actual"] != sampling:
        raise ValueError("Exactly the original G1 association call must be routed to declared sampling")
    adapter = contract["G1_association_adapter"]
    q.checked(adapter["source_path"], adapter["source_sha256"])
    if adapter["parameter_only"] is not True:
        raise ValueError("An original-function-body replacement is not allowed")
    seed_path = states["G00_INPUT"][0] / "geometry.npz"
    q.checked(seed_path, states["G00_INPUT"][1]["geometry_file_sha256"])
    with np.load(seed_path, allow_pickle=False) as z:
        sx, st = z["xyz"], z["faces"]
    seed_native = q.native_fans(states["G00_INPUT"][2], sx, st)
    seed_quality = q.topology(sx, st)
    splits = {}
    for before, after in (("G00_INPUT", "G01_ANCESTRY"), ("G01_ANCESTRY", "G02_OVERLAP"),
                          ("G02_OVERLAP", "G03_WALL"), ("G03_SIDEWALL", "G04_NEUTRAL")):
        splits[after] = q.split_lineage(states[before][2], states[after][2], states[after][3])
    for name in ("G01_ANCESTRY", "G02_OVERLAP"):
        m = states[name][1]
        for key in ("task36_recipe", "field_iterations"):
            if m[key] != originals[name][key]:
                raise ValueError("Original global Task36/finite-field policy changed")
        if m.get("source_rule_revision_recipe", m.get("source_rule_revision", {}).get("recipe")) != originals[name]["source_rule_revision_recipe"]:
            raise ValueError("Original axial policy changed")
    if states["G02_OVERLAP"][1]["authored_return_events"] != resolved["overlap_events"]:
        raise ValueError("Actual G2 returns differ from the declared later recipe")
    fields = field_checks(q, folder, contract, states, originals)
    regional = q.regional_checks(contract["recipe"], states["G01_ANCESTRY"][2],
                                 states["G02_OVERLAP"][3], states["G02_OVERLAP"][1])
    provenance = q.event_provenance(states, resolved)
    final, meta, control, evidence = states["G04_NEUTRAL"]
    if receipt["final"] != meta:
        raise ValueError("Final/native generation record differs")
    geometry = q.checked(final / "geometry.npz", meta["geometry_file_sha256"])
    with np.load(geometry, allow_pickle=False) as z:
        x, t = z["xyz"], z["faces"]
    if q.ah(x) != meta["checks"]["native_xyz_sha256"] or q.ah(t) != meta["checks"]["native_faces_sha256"]:
        raise ValueError("Actual G4 native array bindings differ")
    fans = q.native_fans(control, x, t)
    quality = q.topology(x, t)
    sym = q.symmetry(control, x, evidence)
    sid = receipt["candidate"]
    baseline = None
    if sid == baseline_id:
        if contract["recipe"].get("seed_events") or contract["recipe"].get("field_layout") or not seed["matched_sampling_two_event_baseline_exact"]:
            raise ValueError("The baseline must keep the original two-event generator at declared density")
        baseline = dict(same_sampling_original_two_event_constructor=True,
                        original25_G4_identity_claimed=False)
    bx, bq, bc = (baseline_g2[k] for k in ("xyz", "faces", "chart"))
    g2 = states["G02_OVERLAP"][2]
    if not q.exact(g2["faces"], bq) or not q.exact(g2["chart"], bc):
        raise ValueError("G2 same-material topology/chart correspondence changed")
    delta2 = np.linalg.norm(g2["xyz"] - bx, axis=1)
    row = dict(id=sid, source_receipt=q.record(folder / "RECEIPT.json"), recipe=q.record(recipe_path),
               resolved_recipe=q.record(resolved_path), actual_geometry=q.record(geometry),
               actual_control_geometry=q.record(final / "control_quad.npz"),
               actual_seed_controls=q.record(states["G00_INPUT"][0] / "control_quad.npz"),
               actual_seed_geometry=q.record(seed_path),
               allowed_settings=settings, seed_constructor_QA=seed, seed_native_surface=seed_native,
               seed_quality=seed_quality, executed_code=sources, actual_stage_bindings=stage_bindings,
               split_lineage=splits, regional_split_controls=regional, actual_operation_provenance=provenance,
               finite_field_layout_QA=fields,
               native_surface=fans, quality=quality, actual_symmetry=sym,
               sampling_matched_baseline=baseline,
               G1_carrier_parameter_routing=copy.deepcopy(routing),
               G2_paired_material_displacement_quantiles=np.quantile(delta2, [0, .5, .9, .99, 1]).tolist(),
               G2_changed_controls=int(np.count_nonzero(delta2 > 1e-12)),
               physical_extent=np.ptp(x, axis=0).tolist(), no_G5_G7_or_late_ornament=True,
               slenderness=slenderness(control["xyz"], x, t),
               no_all_variants_original_G0_XYZ_invariance_claim=True,
               no_outside_region_XYZ_invariance_claim=True, user_adopted=False,
               aesthetic_score=False, self_intersection_or_manufacturing_certified=False)
    return row, x, t


def main(a):
    start = time.perf_counter()
    q = common()
    found = {}
    for p in sorted(a.root.rglob("RECEIPT.json")):
        r = q.read(p)
        if r.get("status") != "PASS":
            continue
        if r.get("schema") != SCHEMA:
            if "INHERITED_STRONG_SEED_LAYOUT" in r.get("schema", ""):
                raise ValueError("Unsupported completed strong-layout schema")
            continue
        sid = r["candidate"]
        if a.ids and sid not in a.ids:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_-]+", sid) or sid in found:
            raise ValueError("Invalid or duplicate selected strong-layout candidate")
        found[sid] = (p, r)
    if a.baseline_id not in found or (a.ids and set(found) != set(a.ids)):
        raise ValueError("The matched-sampling baseline and every selected completed candidate are required")
    if a.expected_count is not None and len(found) != a.expected_count:
        raise ValueError("Selected completed candidate count differs")
    q.checked(q.ORIGINAL_G0, q.ORIGINAL_G0_SHA)
    with np.load(q.ORIGINAL_G0, allow_pickle=False) as z:
        original_g0 = {k: z[k] for k in ("xyz", "faces", "chart")}
    original_recipe = q.read(q.checked(q.ORIGINAL_G0.parent / "generation.json", ORIGINAL_RECIPE_SHA))["recipe"]
    baseline_folder = found[a.baseline_id][0].parent
    _, _, baseline_g2, _ = q.stage(baseline_folder, "G02_OVERLAP")
    if not a.inspect_only:
        if a.output is None:
            raise ValueError("--output is required for export")
        a.output.mkdir(parents=True, exist_ok=False)
        (a.output / "source_snapshot").mkdir()
        shutil.copyfile(__file__, a.output / "source_snapshot" / Path(__file__).name)
        shutil.copyfile(COMMON_PATH, a.output / "source_snapshot" / COMMON_PATH.name)
    rows = []
    for sid, (path, receipt) in sorted(found.items()):
        row, x, t = inspect_one(q, path.parent, receipt, original_g0, original_recipe, a.original_states, a.baseline_id, baseline_g2)
        if not a.inspect_only:
            target = a.output / sid; target.mkdir()
            row["model"] = q.export_ply(target / ("CHESHIRE_OVERLAP_" + sid + "_G4_NATIVE_FULL.ply"), x, t)
            q.write(target / "EXPORT_RECEIPT.json", row)
        rows.append(row)
        print("OVERLAP_G4_QA_PASS", sid, len(x), len(t), row["seed_constructor_QA"]["changed_controls"], flush=True)
    result = dict(schema="CHESHIRE_OVERLAP_INHERITED_LAYOUT_EXPORT_QA_V1", passed=True,
                  completed_count=len(rows), selected_ids=sorted(found), baseline_id=a.baseline_id, variants=rows,
                  original_input=q.record(q.ORIGINAL_G0), original_states=str(a.original_states),
                  source=q.record(__file__), reused_geometry_QA_and_PLY_helper=q.record(COMMON_PATH),
                  inspection_only=a.inspect_only, all_exported_geometry_full_readback_exact=not a.inspect_only,
                  original_generator_re_evaluated_for_variants=True, all_variant_G0_equal_to_original_claimed=False,
                  comparison_reference="Original two-event seed and original downstream rules at identical declared49 sampling.",
                  original25_seed_exact_checked_separately=True, original25_G4_identity_claimed=False,
                  no_geometry_repair_or_normalization=True, user_adopted=False,
                  matched_K08_two_field_comparison=field_pair_comparison(q, rows),
                  self_intersection_or_manufacturing_certified=False, elapsed_seconds=time.perf_counter() - start)
    if not a.inspect_only:
        q.write(a.output / "OVERLAP_EXPORT_AND_QA.json", result)
    print("OVERLAP_QA_AGGREGATE_PASS", len(rows), result["elapsed_seconds"], flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--expected-count", type=int)
    p.add_argument("--ids", nargs="*")
    p.add_argument("--baseline-id", default="K00")
    p.add_argument("--inspect-only", action="store_true")
    p.add_argument("--original-states", type=Path, default=Path("E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states"))
    main(p.parse_args())
