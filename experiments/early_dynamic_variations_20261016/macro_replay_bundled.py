"""Connected-selection driver fork; original macro_replay.py is preserved."""
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
SCHEMA = "CHESHIRE_ACTUAL_EARLY_DYNAMIC_BUNDLED_G2_REPLAY_V1"


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


def _seed(replay, recipe):
    mesh, chart, parts, source_recipe, _ = replay.exact_original_seed((1.,) * 8)
    before = mesh.xyz.copy()
    length = float(recipe.get("length_scale", recipe.get("axial_length_scale", 1.)))
    if not np.isfinite(length) or not 0.5 <= length <= 2.:
        raise ValueError("length_scale must be finite and in [0.5, 2].")
    if recipe.get("seed_mode") == "fresh_profile_carrier":
        profile = recipe["fresh_radius_profile"]
        knots, values = np.asarray(profile["knots"],float), np.asarray(profile["values"],float)
        if (knots.shape != values.shape or knots.ndim != 1 or len(knots)<3 or
                np.any(np.diff(knots)<=0) or knots[0]!=0 or knots[-1]!=1 or
                not np.isfinite(values).all() or np.any(values<=0)):
            raise ValueError("Finite positive new carrier radius profile required.")
        radius = PchipInterpolator(knots,values)(chart[:,0])
        mesh.xyz = np.column_stack((radius*chart[:,1], radius*chart[:,2],
                                    10.*length*chart[:,0]))
        mesh.rest = mesh.xyz.copy()
        parts = dict(fresh_seed_xyz=mesh.xyz.copy(), fresh_profile_radius=radius,
                     original_seed_xyz_reference_only=before,
                     inherited_material_height=chart[:,0].copy())
        source_recipe = dict(seed_mode="fresh_profile_carrier", radius_profile=profile,
            length_scale=length, original_topology_and_chart_retained=True,
            original_seed_geometry_used=False,
            rest_scope="Actual G0 rest updated to fresh seed; unchanged G1 operator subsequently recovers its canonical positive-cage association.")
        return mesh, chart, parts, source_recipe
    scales = np.asarray(recipe.get("radius_scale_profile", [1.] * 8), float)
    if scales.shape != (8,) or not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("Eight finite positive radial multipliers required.")
    knots = recipe.get("material_axial_knots")
    t = chart[:, 0]
    if knots is not None:
        if isinstance(knots, dict):
            knots = [knots["source"], knots["target"]]
        k, v = map(lambda q: np.asarray(q, float), knots)
        if (k.ndim != 1 or k.shape != v.shape or len(k) < 2 or
                not np.isfinite([k, v]).all() or np.any(np.diff(k) <= 0) or
                np.any(np.diff(v) <= 0) or k[0] != 0 or k[-1] != 1 or
                v[0] != 0 or v[-1] != 1):
            raise ValueError("Monotone unit-endpoint axial source/target knots required.")
        remapped_t = PchipInterpolator(k, v)(t)
    else:
        remapped_t = t
    if not np.array_equal(scales, np.ones(8)):
        radial = PchipInterpolator([0., .06, .14, .28, .50, .72, .90, 1.], scales)(t)
        mesh.xyz[:, :2] *= radial[:, None]
    if length != 1. or knots is not None:
        mesh.xyz[:, 2] = length * (before[:, 2] + 10. * (remapped_t - t))
    parts = dict(parts, original_seed_xyz=before,
                 dynamic_seed_displacement=mesh.xyz - before,
                 dynamic_axial_material_coordinate=remapped_t)
    return mesh, chart, parts, source_recipe


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
    """Generate real G0--G4. One fresh process per recipe is recommended.

    Required bundled_fields are injected on actual G2 before WALL and G3.
    Optional macro_field retains the inherited stage-3 API but is disabled by
    all C01-C04 recipes (macro_fields={}).
    The connected selection pass retains one root + three canonical sidewalls.
    It trims disconnected angular masks to explicit native cyclic arcs.
    """
    started = time.perf_counter()
    root = Path(output_root).resolve()
    if root.exists():
        raise FileExistsError("Preserved candidate exists; choose a fresh output root.")
    repo = Path(source_repo or DEFAULT_SOURCE_REPO).resolve()
    recipe = copy.deepcopy(recipe)
    case = str(recipe.get("id", recipe.get("name", "EARLY_DYNAMIC")))
    replay_path = repo / "experiments/end_rule_revision_20261014/replay.py"
    replay = load_module("dynamic_replay_" + uuid.uuid4().hex, replay_path)
    early = replay.early
    selected = early.selected_receipts()
    selector_path = HERE / "sidewall_connected_selection.py"
    selector = load_module("connected_selector_" + uuid.uuid4().hex, selector_path)
    hashes = early.code_hashes()
    hashes[replay_path.relative_to(repo).as_posix()] = digest(replay_path)
    bundled_path = HERE / "early_bundled_fields.py"
    bundled = load_module("bundled_G2_fields_" + uuid.uuid4().hex, bundled_path)
    own_sources = [Path(__file__).resolve(), selector_path, bundled_path]
    if macro_field is None and recipe.get("macro_fields"):
        module_path = HERE / "early_macro_fields.py"
        fields = load_module("dynamic_fields_" + uuid.uuid4().hex, module_path)
        macro_field = fields.apply_macro_field
        own_sources.append(module_path)
    elif macro_field is not None:
        file = sys.modules.get(macro_field.__module__)
        if file is not None and getattr(file, "__file__", None):
            own_sources.append(Path(file.__file__).resolve())
    overlap_events = copy.deepcopy(early.overlap.EVENTS)
    overrides = recipe.get("overlap_events", [])
    if overrides:
        if len(overrides) != len(overlap_events):
            raise ValueError("First pass retains exactly two overlap events.")
        overlap_events = [_merge(base, new) for base, new in zip(overlap_events, overrides)]
    root_recipe = _merge(early.core.patch_growth.RECIPE, recipe.get("root_recipe", {}))
    side_recipe = _merge(early.sidewall.RECIPE, recipe.get("sidewall_recipe", {}))
    task36 = _merge(early.ancestry.RECIPE, recipe.get("task36_recipe", {}))
    axial_recipe = copy.deepcopy(replay.RECIPE)
    axial_recipe.update(source_case=case, original_G0_geometry_loaded_exactly=(recipe.get("seed_mode") != "fresh_profile_carrier"),
        early_dynamic_seed_modifications=copy.deepcopy({k:recipe[k] for k in
            ("length_scale","axial_length_scale","material_axial_knots","radius_scale_profile")
            if k in recipe}),
        unchanged=["Original G0 topology and inherited material chart",
                   "Raw finite-field target search, cache and field step budgets"],
        scope="Historical axial attenuation applied to the actual dynamic parents; other recipe overrides are recorded separately.")
    changes = [(early.overlap, "EVENTS", overlap_events),
               (early.core.patch_growth, "RECIPE", root_recipe),
               (early.sidewall, "RECIPE", side_recipe),
               (early.ancestry, "RECIPE", task36),
               (replay, "RECIPE", axial_recipe),
               (early.sidewall, "_plans", lambda mesh, layout, cfg: selector.connected_beta_plans(early.sidewall, mesh, layout, cfg))]
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
                    historical_recipe_references=selected,
                    common_G1_G2_axial_attenuation=axial_recipe,
                    material_chart_policy="Inherited material labels retained; axial remap changes physical XYZ only.",
                    macro_field_injection="Actual G02_OVERLAP before WALL rail measurement and G3 events; optional G3 macro remains disabled for C01-C04.",
                    field_cache_policy="Original finite-field targets/cache remain unchanged in world units.",
                    selection_mode="connected_beta_arc",
                    original_beta_sector_placement_changed_explicitly=True,
                    genuine_early_replay=True, mature_G7_sampling_used=False,
                    fabrication_certified=False)
    write(root / "RECIPE.json", contract)
    write(root / "RECIPE_EARLY.json", dict(recipe=recipe, overlap_events=overlap_events,
           root_event=root_recipe, sidewall_event=side_recipe, task36=task36))
    records, nodes = {}, []

    def save(stage, mesh, chart, state, metadata=None, parent=None,
             pairs=None, guides=(), rails=()):
        context = dict(input_case="EARLY_DYNAMIC", candidate=case, transfer_schema=SCHEMA,
            dynamic_recipe=recipe, geometry_code_sha256=hashes,
            selected_recipe_receipt=selected[stage]["path"],
            selected_recipe_receipt_sha256=selected[stage]["sha256"],
            recipe_scope="Historical selected operators on actual changed early parents; overrides explicitly recorded.",
            self_intersection="NOT_CHECKED_VISUAL_PROTOTYPE", fabrication="NOT_CHECKED",
            **(metadata or {}))
        if parent is not None:
            context.update(source=str(folders[parent]), parent_stage=str(folders[parent]),
                source_generation=records[parent]["subdivision_generation"],
                source_control_sha256=records[parent]["control_file_sha256"],
                source_generation_json_sha256=digest(folders[parent] / "generation.json"))
        record, evidence = replay._frozen_early_save(folders[stage], mesh, chart,
                    context, state, pairs=pairs, guides=guides, rails=rails)
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
            mesh, chart, state, meta = early.ancestry_field(mesh, chart, 2, selected["G02_OVERLAP"])
            if not recipe.get("bundled_fields"):
                raise ValueError("A declared actual G2 bundled field is required.")
            before = mesh.xyz.copy()
            values, bundled_evidence, bundled_meta = bundled.apply_bundled_field(
                mesh.xyz, chart, recipe["bundled_fields"],
                vertex_pairs=early._pairs(mesh, chart, state), stage=2)
            # Positive native fan areas and unchanged oriented topology are
            # integrity gates. Dot-to-old normals is a deformation diagnostic,
            # since deliberately bent folds can turn through ninety degrees.
            q = mesh.faces
            oldp, newp = before[q], values[q]
            oldc, newc = oldp.mean(1), newp.mean(1)
            oldfan = np.cross(oldp-oldc[:,None], np.roll(oldp,-1,axis=1)-oldc[:,None])
            newfan = np.cross(newp-newc[:,None], np.roll(newp,-1,axis=1)-newc[:,None])
            area = .5*np.linalg.norm(newfan,axis=2)
            dot = np.einsum("fki,fki->fk",oldfan,newfan)
            if not np.isfinite(area).all() or float(area.min()) <= 1e-14:
                raise ValueError("Bundled G2 native fan area failed; no repair.")
            mesh.xyz = values
            state.update({"bundled_"+str(k):np.asarray(v) for k,v in bundled_evidence.items()})
            state["bundled_native_old_new_fan_dot"] = dot
            bundled_meta.update(minimum_native_triangle_area=float(area.min()),
                native_fans_turned_over_90_degrees=int(np.count_nonzero(dot<=0)),
                old_normal_dot_is_not_collision_or_signed_area_certificate=True,
                directed_native_topology_unchanged=True)
            meta = dict(meta, bundled_field=bundled_meta)
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
            macro_meta = dict(applied=False, reason="Empty macro field recipe; exact no-op.")
            if macro_field is not None and recipe.get("macro_fields"):
                before = mesh.xyz.copy()
                values, macro_evidence, macro_meta = macro_field(mesh.xyz, chart,
                    recipe["macro_fields"], roles={"face_role_counts":{
                        str(int(k)):int(v) for k,v in zip(*np.unique(evidence["face_roles"],return_counts=True))}},
                    vertex_pairs=early._pairs(mesh,chart,evidence),stage=3)
                values = np.asarray(values, dtype=float)
                if values.shape != mesh.xyz.shape or not np.isfinite(values).all():
                    raise ValueError("Macro field returned invalid actual G3 XYZ.")
                mesh.xyz = values
                evidence.update({"macro_" + str(k):np.asarray(v) for k,v in macro_evidence.items()})
                evidence["macro_actual_displacement"] = values-before
            evidence = save("G03_SIDEWALL", mesh, chart, evidence,
                dict(event_recipe=side_recipe, added_topology_events=3,
                     macro_field=macro_meta), "G03_ROOT")
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
                     added_topology_events=0, macro_field=macro_meta), "G03_SIDEWALL", pairs=pairs)
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
        print("ACTUAL_EARLY_REPLAY_READY",case,receipt["elapsed_seconds"],flush=True)
        return receipt
    except Exception as exc:
        write(root / "FAILED_REPLAY.json",dict(schema=SCHEMA,candidate=case,error=repr(exc),
              completed_stages=nodes,elapsed_seconds=time.perf_counter()-started,
              geometry_preserved=True,no_silent_repair=True))
        raise


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
