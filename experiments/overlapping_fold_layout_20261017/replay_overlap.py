"""Original SPAN kernel with six/eight overlapping seed-fold events on declared denser carrier sampling."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import uuid

import numpy as np
from scipy.interpolate import PchipInterpolator


HERE = Path(__file__).resolve().parent
_LOCAL_REPO = HERE.parents[1]
DEFAULT_SOURCE_REPO = (_LOCAL_REPO if (_LOCAL_REPO / "experiments/end_rule_revision_20261014/replay.py").is_file()
                       else _LOCAL_REPO / "worktrees/connected-fold-growth-20261012")
STAGES = ("G00_INPUT", "G01_ANCESTRY", "G02_OVERLAP", "G03_WALL",
          "G03_ROOT", "G03_SIDEWALL", "G04_NEUTRAL")
SCHEMA = "CHESHIRE_OVERLAPPING_ORIGINAL_SEED_LAYOUT_REPLAY_V1"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                   allow_nan=False) + "\n", encoding="utf-8")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def _merge(base, overrides):
    out = copy.deepcopy(base)
    for key, value in overrides.items():
        if key not in out:
            raise ValueError("Unknown historical recipe key: " + key)
        out[key] = copy.deepcopy(value)
    return out


@contextmanager
def scoped_attributes(changes):
    """Restore imported module attributes even when a candidate fails."""
    originals = [(obj, key, getattr(obj, key)) for obj, key, _ in changes]
    try:
        for obj, key, value in changes:
            setattr(obj, key, value)
        yield
    finally:
        for obj, key, value in reversed(originals):
            setattr(obj, key, value)


ALLOWED_SETTINGS = {
    "top_level": ["id", "name", "label_ko", "family", "description_ko", "carrier_sampling", "field_layout", "seed_events", "overlap_events", "root_recipe", "sidewall_recipe", "split_regions", "experimental", "fabrication_certified"],
    "event_changes": ["id", "template_index", "height", "span", "direction", "sweep", "overlap_width"],
    "event_amplitudes_fixed": ["expansion", "constriction", "reexpansion", "return_depth", "mirror"],
    "root_recipe": ["root_parameter_centre", "root_parameter_halfwidth", "root_cross_centre", "root_cross_sweep", "root_cross_halfwidth"],
    "sidewall_recipe": ["parent_rows", "beta_centres", "beta_halfwidth"],
    "split_regions": "Existing regional w3/w4 face and w1 edge coefficients only; no normal-amplitude changes.",
    "G0": "Original SPAN legacy_core constructor with original radius/caps/amplitudes; actual internal legacy EVENTS positions/count/width/direction may change.",
    "seed_events": "Group 1 allows two, six or eight existing templates; groups 2 and 3 retain their original event count. Only height/span/direction/sweep/overlap_width vary.",
    "field_layout": "Optional existing two-Mandel classification-union centres/axial overlap; same kernel/powers and explicit fresh cache.",
    "global_Task36": "Unchanged selected recipe; regional split adapter acts inside the same reference subdivision.",
    "finite_Mandel": "Original kernel/powers/iterations/response/budgets/axial attenuation; optional declared centres/axial layout uses a separately bound matching fresh cache.",
    "selectors": "Original root ellipse and original sidewall beta-sector plan; no connected-arc replacement.",
    "forbidden": ["length_scale", "axial_length_scale", "radius_scale_profile", "material_axial_knots", "macro_fields", "bundled_fields", "fresh_radius_profile", "seed_mode", "CSG", "task36_recipe"]}


def _validate_recipe(recipe):
    unknown=set(recipe)-set(ALLOWED_SETTINGS["top_level"])
    if unknown:raise ValueError("Non-inherited design settings are forbidden: "+", ".join(sorted(unknown)))
    for key in ("root_recipe","sidewall_recipe"):
        unknown=set(recipe.get(key,{}))-set(ALLOWED_SETTINGS[key])
        if unknown:raise ValueError("Only existing selection positions/directions may change in "+key+": "+", ".join(sorted(unknown)))
    if recipe.get("sidewall_recipe",{}).get("beta_centres") is not None and len(recipe["sidewall_recipe"]["beta_centres"])!=3:
        raise ValueError("The inherited study keeps three original sidewall events.")


def _events(original, requested):
    if not requested:return copy.deepcopy(original)
    if not 2<=len(requested)<=4:raise ValueError("Two to four inherited return events required.")
    result=[]
    for i,change in enumerate(requested):
        change=copy.deepcopy(change)
        template=int(change.pop("template_index",i%2))
        if template not in (0,1):raise ValueError("Inherited event template is zero or one.")
        base=copy.deepcopy(original[template])
        allowed=set(ALLOWED_SETTINGS["event_changes"])-{"template_index"}
        for key in list(change):
            if key in ALLOWED_SETTINGS["event_amplitudes_fixed"]:
                if change[key]!=base[key]:raise ValueError("Inherited event amplitude cannot change: "+key)
                change.pop(key)
        if set(change)-allowed:raise ValueError("Unsupported inherited event keys.")
        base.update(change)
        if not 0<base["height"]<1 or base["span"]<=0 or base["overlap_width"]<=0:
            raise ValueError("Interior material height and positive inherited event widths required.")
        result.append(base)
    return result


def resolved_seed_events(original, requested):
    """Expose authored EVENTS parameters; evaluate the unchanged legacy functions."""
    out=copy.deepcopy(original)
    allowed={"template_index","id","height","span","direction","sweep","overlap_width"}
    for group,items in (requested or {}).items():
        group=int(group)
        if group not in (1,2,3):raise ValueError("Unknown original seed event group.")
        count=len(items)
        if (group==1 and count not in (2,6,8)) or (group!=1 and count!=len(original[group])):
            raise ValueError("Original major-event multiplicity must be two, six or eight.")
        resolved=[]
        for i,item in enumerate(items):
            item=copy.deepcopy(item)
            if set(item)-allowed:raise ValueError("Seed amplitudes/formulas are immutable.")
            template=int(item.pop("template_index",i%len(original[group])))
            if not 0<=template<len(original[group]):raise ValueError("Unknown original seed template.")
            event=copy.deepcopy(original[group][template]);event.update(item)
            if not (0<event["height"]<1 and event["span"]>0 and event["overlap_width"]>0):
                raise ValueError("Interior seed location and positive widths required.")
            if not all(np.isfinite(event[k]) for k in ("height","span","direction","sweep","overlap_width")):
                raise ValueError("Finite seed parameters required.")
            resolved.append(event)
        out[group]=resolved
    return out


def declared_sampling(recipe):
    cfg=dict(rings=49,sectors=16,radius=.78)
    requested=recipe.get("carrier_sampling",cfg)
    if requested!=cfg:raise ValueError("This density-matched comparison declares original carrier sampling 49/16/.78 only.")
    return cfg


def _seed(replay, recipe):
    original_mesh,original_chart,original_parts,source_recipe,_=replay.exact_original_seed((1.,)*8)
    source=replay.early.seed
    legacy=source.source.old.repair.legacy
    inherited=copy.deepcopy(legacy.EVENTS)
    original_xyz,regenerated_parts=source.legacy_core(original_chart,copy.deepcopy(source_recipe),"SPAN")
    proof=dict(xyz=bool(np.array_equal(original_xyz,original_mesh.xyz)),
               parts={k:bool(np.array_equal(regenerated_parts[k],original_parts[k])) for k in regenerated_parts})
    if not proof["xyz"] or not all(proof["parts"].values()):
        raise ValueError("Original 25-ring SPAN constructor failed exact preserved-source replay.")
    sampling=declared_sampling(recipe)
    mesh,chart=source.variation.carrier(copy.deepcopy(sampling))
    mesh.anchors[:,0]=np.arange(len(mesh.faces));mesh.surface="mean"
    baseline_xyz,baseline_parts=source.legacy_core(chart,copy.deepcopy(source_recipe),"SPAN")
    resolved=resolved_seed_events(inherited,recipe.get("seed_events"))
    with scoped_attributes([(legacy,"EVENTS",resolved)]):
        xyz,parts=source.legacy_core(chart,copy.deepcopy(source_recipe),"SPAN")
    if not np.array_equal(sum(parts.values()),xyz):
        raise ValueError("Seed operation components do not reconstruct actual coordinates.")
    if not recipe.get("seed_events") and not np.array_equal(xyz,baseline_xyz):
        raise ValueError("Same-density baseline replay differed.")
    mesh.xyz=xyz
    delta=np.linalg.norm(xyz-baseline_xyz,axis=1)
    effective=dict(original_SPAN_recipe=copy.deepcopy(source_recipe),
                   original_legacy_events=inherited,resolved_legacy_events=resolved,
                   carrier_sampling=sampling,original25_constructor_exact=proof,
                   same_original_constructor=True,original_t_warp_unchanged=True,
                   constructor="seed_mass.legacy_core -> iaac_input.initial -> original smooth_event/memory/smooth_valley",
                   original_source_G0_exact=False,
                   declared_sampling_baseline_exact=bool(np.array_equal(xyz,baseline_xyz)),
                   G0_change_reference="Original two-event seed reevaluated at the same declared49 carrier.",
                   G0_maximum_change=float(delta.max()),
                   G0_RMS_change=float(np.sqrt(np.mean(delta**2))),
                   G0_changed_controls=int(np.count_nonzero(delta>1e-12)))
    return mesh,chart,parts,effective


def association_adapter(early, sampling):
    """Route the frozen G1 association carrier parameter, without changing its body."""
    original_ancestry=early.ancestry_field
    variation=early.prior.variation
    original_carrier=variation.carrier
    declared_reference=dict(rings=25,sectors=16,radius=.78)
    def ancestry(mesh,chart,generation,selected):
        if generation!=1:return original_ancestry(mesh,chart,generation,selected)
        calls=[]
        def routed_carrier(cfg):
            requested=copy.deepcopy(cfg)
            actual=copy.deepcopy(sampling) if cfg==declared_reference else cfg
            calls.append(dict(requested=requested,actual=copy.deepcopy(actual),
                              declared_sampling_override=bool(cfg==declared_reference)))
            return original_carrier(actual)
        with scoped_attributes([(variation,"carrier",routed_carrier)]):
            values=list(original_ancestry(mesh,chart,generation,selected))
        if not any(c["declared_sampling_override"] for c in calls):
            raise ValueError("Expected original G1 carrier association was not observed.")
        values[3]=dict(values[3],carrier_association_parameter_routing=dict(
            original_function="original ancestry_field and original variation.carrier",
            original_requested_sampling=declared_reference,declared_sampling=copy.deepcopy(sampling),
            actual_calls=calls,parameter_only=True,original_function_body_unchanged=True,
            restored_after_G1=True))
        return tuple(values)
    return ancestry


def load_live_state(root, stage="G04_NEUTRAL", source_repo=None):
    """Return (ArrayMesh, chart, generation_metadata, evidence) from saved state."""
    repo = Path(source_repo or DEFAULT_SOURCE_REPO).resolve()
    sys.path.insert(0, str(repo / "src"))
    from cheshire.reference_subdivision import ArrayMesh
    folder = Path(root) / "states" / stage
    info = read(folder / "generation.json")
    if not info["checks"]["passed"]:
        raise ValueError("A failed stage cannot become a live parent.")
    for name, key in (("control_quad.npz", "control_file_sha256"),
                      ("evidence.npz", "evidence_file_sha256")):
        if digest(folder / name) != info[key]:
            raise ValueError("Saved parent binding changed: " + name)
    with np.load(folder / "control_quad.npz", allow_pickle=False) as z:
        mesh = ArrayMesh(z["xyz"], z["faces"], z["classes"], z["rest"],
                         z["anchors"], int(z["generation"]))
        mesh.surface = str(z["surface"])
        chart = z["chart"]
    with np.load(folder / "evidence.npz", allow_pickle=False) as z:
        evidence = {key: z[key] for key in z.files}
    return mesh, chart, info, evidence


def replay_macro(recipe, output_root, *, source_repo=None, macro_field=None,
                 verify_baseline=False):
    """Replay actual original-seed constructor through inherited G4; no new shape formulas."""
    started = time.perf_counter()
    root = Path(output_root).resolve()
    if root.exists():
        raise FileExistsError("Preserved candidate exists; choose a fresh output root.")
    repo = Path(source_repo or DEFAULT_SOURCE_REPO).resolve()
    recipe = copy.deepcopy(recipe)
    _validate_recipe(recipe)
    sampling=declared_sampling(recipe)
    if verify_baseline and recipe.get("seed_events"):raise ValueError("Baseline-source verification is reserved for K00.")
    case = str(recipe.get("id", recipe.get("name", "EARLY_DYNAMIC")))
    replay_path = repo / "experiments/end_rule_revision_20261014/replay.py"
    replay = load_module("dynamic_replay_" + uuid.uuid4().hex, replay_path)
    early = replay.early
    selected = early.selected_receipts()
    hashes = early.code_hashes()
    hashes[replay_path.relative_to(repo).as_posix()] = digest(replay_path)
    own_sources = [Path(__file__).resolve()]
    if macro_field is not None:
        raise ValueError("External macro geometry fields are forbidden in the inherited study.")
    regional = None
    if recipe.get("split_regions"):
        module_path = HERE.parent / "inherited_rule_variations_20261017" / "regional_split_controls.py"
        regional = load_module("inherited_regional_splits_"+uuid.uuid4().hex,module_path)
        own_sources.append(module_path)
    field_adapter=None
    if recipe.get("field_layout"):
        module_path=HERE/"overlap_field_targets.py"
        field_adapter=load_module("overlap_field_layout_"+uuid.uuid4().hex,module_path)
        own_sources.append(module_path)
    overlap_events = _events(early.overlap.EVENTS,recipe.get("overlap_events"))
    root_recipe = _merge(early.core.patch_growth.RECIPE, recipe.get("root_recipe", {}))
    side_recipe = _merge(early.sidewall.RECIPE, recipe.get("sidewall_recipe", {}))
    task36 = copy.deepcopy(early.ancestry.RECIPE)
    axial_recipe = copy.deepcopy(replay.RECIPE)
    changes = [(early,"ancestry_field",association_adapter(early,sampling)),
               (early.overlap, "EVENTS", overlap_events),
               (early.core.patch_growth, "RECIPE", root_recipe),
               (early.sidewall, "RECIPE", side_recipe),
               (early.ancestry, "RECIPE", task36),
               (replay, "RECIPE", axial_recipe)]
    root.mkdir(parents=True)
    folders = {stage: root / "states" / stage for stage in STAGES}
    snapshots = {}
    for rel, expected in hashes.items():
        source = repo / rel
        target = root / "source_snapshot" / "historical" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if digest(target) != expected:
            raise ValueError("Historical snapshot binding failed.")
        snapshots[str(source)] = dict(snapshot=str(target), sha256=expected)
    for source in own_sources:
        target = root / "source_snapshot" / "driver" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots[str(source)] = dict(snapshot=str(target), sha256=digest(source))
    contract = dict(schema=SCHEMA, candidate=case, recipe=recipe,
                    source_repo=str(repo), source_snapshots=snapshots,
                    allowed_settings=ALLOWED_SETTINGS,
                    frozen_operator_code_sha256={k:v for k,v in hashes.items() if "inherited_rule_variations_20261017" not in k and "inherited_strong_layout_20261017" not in k and "overlapping_fold_layout_20261017" not in k},
                    wrapper_code_sha256={str(p):digest(p) for p in own_sources},
                    historical_recipe_references=selected,
                    common_G1_G2_axial_attenuation=axial_recipe,
                    material_chart_policy="Declared original carrier chart at actual49 sampling, followed by original linear V/E/F transport only.",
                    actual_G0_geometry_unchanged=False,
                    declared_carrier_sampling=sampling,
                    original25_G0_constructor_proof="Separate exact check before actual49 source sampling.",
                    dense_baseline_policy="K00 keeps original two events at same49 density; no old25 G4 identity claim.",
                    G1_association_adapter=dict(parameter_only=True,source_path=str(Path(__file__).resolve()),source_sha256=digest(__file__)),
                    original_seed_constructor_replayed=True,
                    regional_split_injection="Inside actual G1-to-G2 Task36 reference subdivision only.",
                    field_cache_policy=("Same original finite-field parameters/cache" if field_adapter is None else "Declared centres/axial layout via same classification kernel; new source-bound cache."),
                    declared_field_layout=copy.deepcopy(recipe.get("field_layout")),
                    genuine_early_replay=True, mature_G7_sampling_used=False,
                    fabrication_certified=False)
    write(root / "RECIPE.json", contract)
    write(root / "RECIPE_EARLY.json", dict(recipe=recipe, overlap_events=overlap_events,
           root_event=root_recipe, sidewall_event=side_recipe, task36=task36))
    records, nodes = {}, []

    def save(stage, mesh, chart, state, metadata=None, parent=None,
             pairs=None, guides=(), rails=()):
        context = dict(input_case="OVERLAPPING_FOLD_LAYOUT", candidate=case, transfer_schema=SCHEMA,
            dynamic_recipe=recipe, geometry_code_sha256=hashes,
            selected_recipe_receipt=selected[stage]["path"],
            selected_recipe_receipt_sha256=selected[stage]["sha256"],
            recipe_scope="Original SPAN constructor and inherited operators; actual seed-fold positions/count/widths/directions and declared later selection controls vary.",
            self_intersection="NOT_CHECKED_VISUAL_PROTOTYPE", fabrication="NOT_CHECKED",
            **(metadata or {}))
        if parent is not None:
            context.update(source=str(folders[parent]), parent_stage=str(folders[parent]),
                source_generation=records[parent]["subdivision_generation"],
                source_control_sha256=records[parent]["control_file_sha256"],
                source_generation_json_sha256=digest(folders[parent] / "generation.json"))
        record, evidence = replay._frozen_early_save(folders[stage], mesh, chart,
                    context, state, pairs=pairs, guides=guides, rails=rails)
        required_area = 1e-12 if stage in ("G00_INPUT","G01_ANCESTRY","G02_OVERLAP","G03_WALL") else 1e-14
        record["checks"]["minimum_native_triangle_area_threshold"] = required_area
        if record["checks"]["minimum_native_triangle_area"] <= required_area:
            record["checks"]["passed"] = False
            write(folders[stage]/"generation.json",record)
            raise ValueError("Original stage area gate failed; no relaxed threshold.")
        write(folders[stage]/"generation.json",record)
        records[stage] = record
        nodes.append(dict(id=stage, folder=str(folders[stage]), generation=int(mesh.generation),
                          generation_json_sha256=digest(folders[stage] / "generation.json")))
        write(root / "STAGES_EARLY.json", dict(schema=SCHEMA, candidate=case,
              status="IN_PROGRESS", stages=nodes))
        return evidence

    try:
        field_context=(field_adapter.overlapping_field(early,recipe["field_layout"],root/"field_cache")
                       if field_adapter is not None else nullcontext(None))
        with scoped_attributes(changes), field_context as field_recorder:
            mesh, chart, parts, source_recipe = _seed(replay, recipe)
            save("G00_INPUT", mesh, chart, parts, dict(original_seed_recipe=source_recipe))
            mesh, chart, state, meta = early.ancestry_field(mesh, chart, 1, selected["G01_ANCESTRY"])
            save("G01_ANCESTRY", mesh, chart, state, meta, "G00_INPUT")
            if regional is None:
                mesh, chart, state, meta = early.ancestry_field(mesh, chart, 2, selected["G02_OVERLAP"])
            else:
                with regional.regional_controls(early, chart, 2, recipe["split_regions"]) as recorder:
                    mesh, chart, state, meta = early.ancestry_field(mesh, chart, 2, selected["G02_OVERLAP"])
                state.update({"regional_"+str(k):np.asarray(v) for k,v in recorder.evidence.items()})
                meta["regional_split_controls"]=recorder.metadata
            save("G02_OVERLAP", mesh, chart, state, meta, "G01_ANCESTRY")
            mesh, chart, state, meta, guides, rails = early.wall_stage(mesh, chart)
            save("G03_WALL", mesh, chart, state, meta, "G02_OVERLAP", guides=guides, rails=rails)
            mesh, chart, events, evidence = early.core.patch_growth.build(mesh, chart, "ROOT_ONLY")
            if sum(e["status"] == "accepted" for e in events) != 1:
                raise ValueError("The first pass requires one accepted canonical root.")
            evidence = save("G03_ROOT", mesh, chart, evidence,
                dict(event_recipe=root_recipe, added_topology_events=1), "G03_WALL")
            write(folders["G03_ROOT"] / "events.json", events)
            mesh, chart, events, evidence = early.sidewall.build(mesh, chart, evidence, events)
            if sum(e["status"] == "accepted" for e in events) != 3:
                raise ValueError("The first pass requires three accepted canonical sidewalls.")
            evidence = save("G03_SIDEWALL", mesh, chart, evidence,
                dict(event_recipe=side_recipe, added_topology_events=3), "G03_ROOT")
            write(folders["G03_SIDEWALL"] / "events.json", events)
            parent_faces = mesh.faces
            parent_pairs = early._pairs(mesh, chart, evidence)
            mesh, chart, refinement = early.core.refine(mesh, chart)
            pairs = {axis:early.mirror.refine_mirror_pairs(parent_faces,
                         refinement["input_edges"], pair) for axis,pair in parent_pairs.items()}
            if mesh.generation != 4:
                raise ValueError("Expected actual subdivision generation four.")
            pf = refinement["parent_face"]
            refinement.update(face_roles=evidence["face_roles"][pf],
                              face_event_ids=evidence["face_event_ids"][pf])
            save("G04_NEUTRAL", mesh, chart, refinement,
                dict(neutral_CC_passes_added=1, added_CC_passes=1,
                     added_topology_events=0), "G03_SIDEWALL", pairs=pairs)
            if verify_baseline:
                proof=dict(original25_xyz=source_recipe["original25_constructor_exact"]["xyz"],
                           original25_parts=all(source_recipe["original25_constructor_exact"]["parts"].values()),
                           same49_source_constructor_exact=source_recipe["declared_sampling_baseline_exact"])
                write(root/"BASELINE_SOURCE_QA.json",dict(
                    reference="Original variation.carrier(49/16/.78) plus unchanged legacy_core",
                    arrays_bit_exact=proof,passed=all(proof.values()),
                    original25_G4_identity_claimed=False))
                if not all(proof.values()):raise ValueError("Original source constructor proof failed.")

        if field_adapter is not None:
            write(root/"FIELD_LAYOUT.json",field_recorder.metadata)
            np.savez_compressed(root/"FIELD_LAYOUT_EVIDENCE.npz",**field_recorder.evidence)
        for source, item in snapshots.items():
            if digest(source) != item["sha256"] or digest(item["snapshot"]) != item["sha256"]:
                raise ValueError("Executed code changed while replay was running.")
        receipt = dict(schema=SCHEMA, candidate=case, status="PASS", genuine_early_replay=True,
             final_stage="G04_NEUTRAL", stages=nodes, final=records["G04_NEUTRAL"],
             recipe_file=str(root / "RECIPE.json"), recipe_sha256=digest(root / "RECIPE.json"),
             source_snapshots=snapshots, elapsed_seconds=time.perf_counter()-started,
             whole_original_files_changed=False, self_intersections_certified=False)
        write(root / "STAGES_EARLY.json", dict(schema=SCHEMA,candidate=case,status="PASS",stages=nodes))
        write(root / "RECEIPT.json", receipt)
        print("ACTUAL_INHERITED_REPLAY_READY",case,receipt["elapsed_seconds"],flush=True)
        return receipt
    except Exception as exc:
        write(root / "FAILED_REPLAY.json",dict(schema=SCHEMA,candidate=case,error=repr(exc),
              completed_stages=nodes,elapsed_seconds=time.perf_counter()-started,
              geometry_preserved=True,no_silent_repair=True))
        raise


replay_inherited = replay_macro
replay_strong = replay_macro
replay_overlap = replay_macro


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recipe",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--source-repo",type=Path,default=DEFAULT_SOURCE_REPO)
    p.add_argument("--verify-baseline",action="store_true")
    args = p.parse_args()
    replay_macro(read(args.recipe),args.output,source_repo=args.source_repo,
                 verify_baseline=args.verify_baseline)


if __name__ == "__main__":
    main()
