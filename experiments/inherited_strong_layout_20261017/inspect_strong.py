"""Independent original-kernel seed replay QA and unchanged native G4 export.

The baseline must equal the historical SPAN. A variant's G0 is deliberately
different: its reference is a fresh evaluation of the unchanged legacy_core
with the declared existing EVENTS parameters. No XYZ warp is used here.
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
SCHEMA = "CHESHIRE_INHERITED_STRONG_SEED_LAYOUT_REPLAY_V1"
COMMON_PATH = HERE.parent / "inherited_rule_variations_20261017/inspect_inherited.py"
COMMON_SHA = "0a0286c7374e1130ed23cb641bce6d8e35d69b34678b07fb087373a34068d664"
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
        if (group == 1 and not 2 <= len(requests) <= 4) or (group != 1 and len(requests) != len(original[group])):
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
    if actual["original_SPAN_recipe"] != original_recipe:
        raise ValueError("Original radius/end/bridge recipe changed")
    if integer_groups(actual["original_legacy_events"]) != inherited or integer_groups(actual["resolved_legacy_events"]) != resolved:
        raise ValueError("Saved original/resolved seed EVENTS differ")
    if actual["same_original_constructor"] is not True or actual["original_t_warp_unchanged"] is not True:
        raise ValueError("Original constructor and original material t map are required")
    if contract.get("original_seed_constructor_replayed") is not True:
        raise ValueError("The actual original seed constructor was not declared")
    if contract["actual_G0_geometry_unchanged"] != (not bool(seed_events)):
        raise ValueError("The declaration must distinguish baseline from parameterized G0")
    if not q.exact(g0["faces"], original_g0["faces"]) or not q.exact(g0["chart"], original_g0["chart"]):
        raise ValueError("Original unsplit carrier topology/material chart changed")
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
    delta = np.linalg.norm(xyz - original_g0["xyz"], axis=1)
    cap = (g0["chart"][:, 0] == 0) | (g0["chart"][:, 0] == 1)
    original_exact = q.exact(xyz, original_g0["xyz"])
    if actual["original_source_G0_exact"] != original_exact:
        raise ValueError("Actual G0 equality declaration is inaccurate")
    return dict(passed=True, original_constructor_source=q.record(repo / "experiments/column_development_20261011/seed_mass.py"),
                independently_re_evaluated_original_kernel=True, exact_saved_XYZ_and_four_operation_fields=True,
                exact_original_carrier_faces_and_chart=True, original_G0_XYZ_byte_exact=original_exact,
                original_seed_recipe_unchanged=True, original_t_warp_unchanged=True,
                original_legacy_events=inherited, resolved_legacy_events=resolved,
                changed_controls=int(np.count_nonzero(delta > 1e-12)),
                coordinate_delta_quantiles=np.quantile(delta, [0, .5, .9, .99, 1]).tolist(),
                RMS_coordinate_delta=float(np.sqrt(np.mean(delta ** 2))),
                original_cap_coordinate_delta_maximum=float(delta[cap].max()),
                new_XYZ_warp_or_new_primitive=False)


def settings_checks(q, contract, resolved, originals):
    if set(contract["recipe"]) - (q.TOP_KEYS | {"seed_events"}):
        raise ValueError("Undeclared strong-layout construction setting")
    if set(contract["allowed_settings"]["top_level"]) != q.TOP_KEYS | {"seed_events"}:
        raise ValueError("Strong-layout allowed-settings inventory differs")
    # Project only the later parameter vocabulary onto the already frozen
    # independent whitelist. This is not a G0 equality test: seed_reference
    # independently evaluates and reports the intentionally changed G0 above.
    later = copy.deepcopy(contract)
    later["recipe"].pop("seed_events", None)
    later["allowed_settings"]["top_level"] = list(q.TOP_KEYS)
    later["actual_G0_geometry_unchanged"] = True
    resolved_later = copy.deepcopy(resolved)
    resolved_later["recipe"] = later["recipe"]
    checks = q.recipe_checks(later, resolved_later, originals)
    checks["requested_settings"] = contract["recipe"]
    checks["G0_equality_checked_separately"] = True
    return checks


def inspect_one(q, folder, receipt, original_g0, original_recipe, original_states, baseline_id):
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
        for key in ("task36_recipe", "field_recipe", "field_iterations"):
            if m[key] != originals[name][key]:
                raise ValueError("Original global Task36/finite-field policy changed")
        if m.get("source_rule_revision_recipe", m.get("source_rule_revision", {}).get("recipe")) != originals[name]["source_rule_revision_recipe"]:
            raise ValueError("Original axial policy changed")
    if states["G02_OVERLAP"][1]["authored_return_events"] != resolved["overlap_events"]:
        raise ValueError("Actual G2 returns differ from the declared later recipe")
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
        if contract["recipe"].get("seed_events") or not seed["original_G0_XYZ_byte_exact"]:
            raise ValueError("The selected baseline must be the unchanged original SPAN")
        baseline_path = original_states / "G04_NEUTRAL/control_quad.npz"
        with np.load(baseline_path, allow_pickle=False) as z:
            baseline = {k: q.exact(control[k], z[k]) for k in ("xyz", "faces", "chart")}
        if not all(baseline.values()):
            raise ValueError("Baseline actual G4 differs from the original replay")
    with np.load(original_states / "G02_OVERLAP/control_quad.npz", allow_pickle=False) as z:
        bx, bq, bc = z["xyz"], z["faces"], z["chart"]
    g2 = states["G02_OVERLAP"][2]
    if not q.exact(g2["faces"], bq) or not q.exact(g2["chart"], bc):
        raise ValueError("G2 same-material topology/chart correspondence changed")
    delta2 = np.linalg.norm(g2["xyz"] - bx, axis=1)
    row = dict(id=sid, source_receipt=q.record(folder / "RECEIPT.json"), recipe=q.record(recipe_path),
               resolved_recipe=q.record(resolved_path), actual_geometry=q.record(geometry),
               actual_control_geometry=q.record(final / "control_quad.npz"),
               allowed_settings=settings, seed_constructor_QA=seed, seed_native_surface=seed_native,
               seed_quality=seed_quality, executed_code=sources, actual_stage_bindings=stage_bindings,
               split_lineage=splits, regional_split_controls=regional, actual_operation_provenance=provenance,
               native_surface=fans, quality=quality, actual_symmetry=sym,
               baseline_original_G4_byte_exact=baseline,
               G2_paired_material_displacement_quantiles=np.quantile(delta2, [0, .5, .9, .99, 1]).tolist(),
               G2_changed_controls=int(np.count_nonzero(delta2 > 1e-12)),
               physical_extent=np.ptp(x, axis=0).tolist(), no_G5_G7_or_late_ornament=True,
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
        raise ValueError("The original baseline and every selected completed candidate are required")
    if a.expected_count is not None and len(found) != a.expected_count:
        raise ValueError("Selected completed candidate count differs")
    q.checked(q.ORIGINAL_G0, q.ORIGINAL_G0_SHA)
    with np.load(q.ORIGINAL_G0, allow_pickle=False) as z:
        original_g0 = {k: z[k] for k in ("xyz", "faces", "chart")}
    original_recipe = q.read(q.ORIGINAL_G0.parent / "generation.json")["recipe"]
    if not a.inspect_only:
        if a.output is None:
            raise ValueError("--output is required for export")
        a.output.mkdir(parents=True, exist_ok=False)
        (a.output / "source_snapshot").mkdir()
        shutil.copyfile(__file__, a.output / "source_snapshot" / Path(__file__).name)
        shutil.copyfile(COMMON_PATH, a.output / "source_snapshot" / COMMON_PATH.name)
    rows = []
    for sid, (path, receipt) in sorted(found.items()):
        row, x, t = inspect_one(q, path.parent, receipt, original_g0, original_recipe, a.original_states, a.baseline_id)
        if not a.inspect_only:
            target = a.output / sid; target.mkdir()
            row["model"] = q.export_ply(target / ("CHESHIRE_STRONG_" + sid + "_G4_NATIVE_FULL.ply"), x, t)
            q.write(target / "EXPORT_RECEIPT.json", row)
        rows.append(row)
        print("STRONG_G4_QA_PASS", sid, len(x), len(t), row["seed_constructor_QA"]["changed_controls"], flush=True)
    result = dict(schema="CHESHIRE_STRONG_INHERITED_LAYOUT_EXPORT_QA_V1", passed=True,
                  completed_count=len(rows), selected_ids=sorted(found), baseline_id=a.baseline_id, variants=rows,
                  original_input=q.record(q.ORIGINAL_G0), original_states=str(a.original_states),
                  source=q.record(__file__), reused_geometry_QA_and_PLY_helper=q.record(COMMON_PATH),
                  inspection_only=a.inspect_only, all_exported_geometry_full_readback_exact=not a.inspect_only,
                  original_generator_re_evaluated_for_variants=True, all_variant_G0_equal_to_original_claimed=False,
                  no_geometry_repair_or_normalization=True, user_adopted=False,
                  self_intersection_or_manufacturing_certified=False, elapsed_seconds=time.perf_counter() - start)
    if not a.inspect_only:
        q.write(a.output / "STRONG_EXPORT_AND_QA.json", result)
    print("STRONG_QA_AGGREGATE_PASS", len(rows), result["elapsed_seconds"], flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--expected-count", type=int)
    p.add_argument("--ids", nargs="*")
    p.add_argument("--baseline-id", default="J00")
    p.add_argument("--inspect-only", action="store_true")
    p.add_argument("--original-states", type=Path, default=Path("E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states"))
    main(p.parse_args())
