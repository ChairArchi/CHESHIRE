"""Original SPAN genealogy with inherited event positions, splits and directions only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
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
SCHEMA = "CHESHIRE_INHERITED_POSITION_SPLIT_DIRECTION_REPLAY_V1"


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
    "top_level": ["id", "name", "label_ko", "family", "description_ko", "overlap_events", "root_recipe", "sidewall_recipe", "split_regions", "experimental", "fabrication_certified"],
    "event_changes": ["id", "template_index", "height", "span", "direction", "sweep", "overlap_width"],
    "event_amplitudes_fixed": ["expansion", "constriction", "reexpansion", "return_depth", "mirror"],
    "root_recipe": ["root_parameter_centre", "root_parameter_halfwidth", "root_cross_centre", "root_cross_sweep", "root_cross_halfwidth"],
    "sidewall_recipe": ["parent_rows", "beta_centres", "beta_halfwidth"],
    "split_regions": "Existing regional w3/w4 face and w1 edge coefficients only; no normal-amplitude changes.",
    "G0": "Exact immutable original SPAN control XYZ, topology and inherited chart.",
    "global_Task36": "Unchanged selected recipe; regional split adapter acts inside the same reference subdivision.",
    "finite_Mandel": "Unchanged cache, powers, iteration schedule, fraction, budgets and original axial attenuation.",
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


def _seed(replay, recipe):
    mesh,chart,parts,source_recipe,_=replay.exact_original_seed((1.,)*8)
    return mesh,chart,parts,source_recipe


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
    """Replay exact original G0 through actual inherited G4; no new shape fields."""
    started = time.perf_counter()
    root = Path(output_root).resolve()
    if root.exists():
        raise FileExistsError("Preserved candidate exists; choose a fresh output root.")
    repo = Path(source_repo or DEFAULT_SOURCE_REPO).resolve()
    recipe = copy.deepcopy(recipe)
    _validate_recipe(recipe)
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
        module_path = HERE / "regional_split_controls.py"
        regional = load_module("inherited_regional_splits_"+uuid.uuid4().hex,module_path)
        own_sources.append(module_path)
    overlap_events = _events(early.overlap.EVENTS,recipe.get("overlap_events"))
    root_recipe = _merge(early.core.patch_growth.RECIPE, recipe.get("root_recipe", {}))
    side_recipe = _merge(early.sidewall.RECIPE, recipe.get("sidewall_recipe", {}))
    task36 = copy.deepcopy(early.ancestry.RECIPE)
    axial_recipe = copy.deepcopy(replay.RECIPE)
    changes = [(early.overlap, "EVENTS", overlap_events),
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
                    frozen_operator_code_sha256={k:v for k,v in hashes.items() if "inherited_rule_variations_20261017" not in k},
                    wrapper_code_sha256={str(p):digest(p) for p in own_sources},
                    historical_recipe_references=selected,
                    common_G1_G2_axial_attenuation=axial_recipe,
                    material_chart_policy="Exact original inherited chart, followed by original linear V/E/F transport only.",
                    actual_G0_geometry_unchanged=True,
                    regional_split_injection="Inside actual G1-to-G2 Task36 reference subdivision only.",
                    field_cache_policy="Original finite-field targets/cache remain unchanged in world units.",
                    genuine_early_replay=True, mature_G7_sampling_used=False,
                    fabrication_certified=False)
    write(root / "RECIPE.json", contract)
    write(root / "RECIPE_EARLY.json", dict(recipe=recipe, overlap_events=overlap_events,
           root_event=root_recipe, sidewall_event=side_recipe, task36=task36))
    records, nodes = {}, []

    def save(stage, mesh, chart, state, metadata=None, parent=None,
             pairs=None, guides=(), rails=()):
        context = dict(input_case="INHERITED_RULE_VARIATIONS", candidate=case, transfer_schema=SCHEMA,
            dynamic_recipe=recipe, geometry_code_sha256=hashes,
            selected_recipe_receipt=selected[stage]["path"],
            selected_recipe_receipt_sha256=selected[stage]["sha256"],
            recipe_scope="Exact original SPAN G0 and inherited operators; only positions, widths, directions and declared split controls vary.",
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
        with scoped_attributes(changes):
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
                baseline = Path("E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states/G04_NEUTRAL/control_quad.npz")
                with np.load(baseline, allow_pickle=False) as z:
                    proof = {k:bool(np.array_equal(z[k], v)) for k,v in
                             (("xyz",mesh.xyz),("faces",mesh.faces),("chart",chart))}
                write(root / "BASELINE_REPLAY_QA.json", dict(reference=str(baseline),
                      reference_sha256=digest(baseline), arrays_bit_exact=proof,
                      passed=all(proof.values())))
                if not all(proof.values()):
                    raise ValueError("Actual baseline replay differed from preserved G4.")
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
