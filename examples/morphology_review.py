"""Postprocessing only: mask comparisons, measured accent attenuation and guide.

This does not change candidate execution code or any retained mesh/lineage.
Its own identity is recorded separately from the immutable runner identity.
"""

import argparse
from collections import Counter
from html import escape
import hashlib
import json
from math import dist, sqrt
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from morphology import (LIMITS, assert_identity, digest, load_record, monitored_process,
                        read_json, remembered_mola_path, study_storage, write_json_atomic)


def review(directory, representatives, recommendations, notes, *, reuse_views=False):
    manifest = read_json(directory / "manifest.json")
    assert_identity(manifest, remembered_mola_path(ROOT))
    results = manifest["results"]
    atlas = directory / "atlas"
    plan = read_json(atlas / "projection_plan.json")
    def variant(cid):
        return load_record(directory / results[cid]["record"])["variants"][0]
    control = variant("A007")
    control_points = [{r["id"]: r["xyz"] for r in control["steps"][index]["mesh"]["vertices"]} for index in (2, 3)]
    accents = []
    for cid in ("A000", "A005", "A006", "A008"):
        value = variant(cid)
        difference = []
        common_ids = set(control_points[0])
        for index, reference in zip((2, 3), control_points):
            xyz = {r["id"]: r["xyz"] for r in value["steps"][index]["mesh"]["vertices"]}
            d = [dist(xyz[key], reference[key]) for key in common_ids]
            difference.append({"maximum": max(d), "rms": sqrt(sum(x*x for x in d)/len(d)), "retained_points": len(d)})
        accents.append({"candidate_id": cid, "control": "A007", "pre_CC": difference[0], "CC_retained_points": difference[1],
            "rms_retention_ratio": difference[1]["rms"]/difference[0]["rms"],
            "interpretation": "Geometric coordinate difference against zero-accent control on retained keys; NOT semantic CC lineage."})
        del value
    del control
    masks, frames = [], []
    baseline = variant("C000")
    reference = set(baseline["steps"][1]["parameters"]["selected_faces"])
    quad_source = baseline["steps"][0]["mesh"]
    quad_hash = digest(quad_source)
    del baseline
    for row in manifest["candidates"]:
        cid = row["candidate_id"]
        if cid[0] != "C" or row["phase"] == "repeat" or not results.get(cid, {}).get("record"):
            continue
        value = variant(cid)
        assert digest(value["steps"][0]["mesh"]) == quad_hash, "Source quad tessellation changed"
        selected = set(value["steps"][1]["parameters"]["selected_faces"])
        masks.append({"candidate_id": cid, "selected": len(selected), "intersection_with_baseline": len(selected & reference),
            "added": len(selected-reference), "removed": len(reference-selected),
            "jaccard_with_baseline": len(selected & reference)/len(selected | reference), "mask_sha256": digest(sorted(selected)),
            "quad_source_sha256": quad_hash})
        # Presentation of an ACTUAL selection, not a new operator or saved OBJ.
        mask = {"vertices": quad_source["vertices"], "faces": [r for r in quad_source["faces"] if r["id"] in selected]}
        write_json_atomic(atlas / f"geometry/{cid}-mask.json", mask)
        frames.append({"mesh": f"geometry/{cid}-mask.json", "label": f"{cid} / selection only / {len(selected)} faces",
            "bounds": plan["registered_bounds"]["whole"], "width": 450, "height": 500, "wireframe": False,
            "file": f"images/{cid}-mask.png"})
        del value, mask
    mask_plan = {"frames": frames, "sheets": [{"file": "C_masks.png", "title": "C actual initial Mola masks on identical original Quad1 / no remeshing",
        "columns": 4, "width": 450, "height": 500, "images": [f["file"] for f in frames]}]}
    # Keep the exact Task 12 registered frames. Also show every whole output
    # in one shared 5%-padded context frame, so boundary excursions are visible.
    # This is a fixed addition to ALL frames, never per-candidate auto-fitting.
    b = plan["registered_bounds"]["whole"]
    du, dv = .05*(b[1]-b[0]), .05*(b[3]-b[2])
    context = [b[0]-du,b[1]+du,b[2]-dv,b[3]+dv]
    context_warnings = {}
    for family in "ABC":
        images = []
        for row in manifest["candidates"]:
            cid = row["candidate_id"]
            if cid[0] != family or row["phase"] == "repeat" or not results.get(cid,{}).get("record"):
                continue
            path = atlas / f"geometry/{cid}.json"
            mesh = read_json(path)
            from morphology_atlas import projection
            p = [projection(v["xyz"]) for v in mesh["vertices"]]
            outside = sum(not(context[0]<=q[0]<=context[1] and context[2]<=q[1]<=context[3]) for q in p)
            if outside: context_warnings[cid] = outside
            frame = {"mesh":f"geometry/{cid}.json", "label":cid+" / common 5% context margin",
                "bounds":context,"width":450,"height":500,"wireframe":False,"file":f"images/{cid}-context.png"}
            mask_plan["frames"].append(frame); images.append(frame["file"])
            del mesh, p
        mask_plan["sheets"].append({"file":f"{family}_context.png", "title":family+" entire outputs: fixed Task 12 camera + shared 5% context margin",
            "columns":4,"width":450,"height":500,"images":images})
    mask_plan["shared_context_bounds"] = context
    previous_plan = read_json(atlas / "mask_projection_plan.json") if reuse_views else None
    if reuse_views and (digest(previous_plan) != digest(mask_plan) or
            any(not (atlas/frame["file"]).is_file() for frame in mask_plan["frames"]+mask_plan["sheets"])):
        raise ValueError("Retained view inputs/files differ; cannot reuse projections.")
    write_json_atomic(atlas / "mask_projection_plan.json", mask_plan)
    options = {"args": ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/morphology_projection.ps1"),
        "-PlanPath", str(atlas / "mask_projection_plan.json")], "cwd": str(ROOT), "shell": False,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    performance = (read_json(directory / "review_analysis.json")["mask_performance"] if reuse_views else
        monitored_process(options, atlas, 600, directory, time.time()-manifest["started_utc"],
            atlas / "mask_stdout.txt", atlas / "mask_stderr.txt", wall_limit=LIMITS["wall_seconds"]))
    if performance["returncode"]:
        raise RuntimeError("Selection-mask projection failed")
    evidence = {"postprocessing_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n",b"\n")).hexdigest(),
        "execution_code_sha256": manifest["identities"]["code"], "A_accent_comparisons": accents, "C_mask_comparisons": masks,
        "mask_performance": performance, "representatives": representatives, "recommendations": recommendations,
        "observations": notes, "shared_context_bounds":context,"context_frame_outside_vertices":context_warnings,
        "rhino_host": "NOT CHECKED for Task 13; these are headless saved-mesh projections",
        "collision_scope": "Fixed Task 12 diagnostic excludes adjacent/coplanar/edge-only contacts; zero is not global clearance."}
    write_json_atomic(directory / "review_analysis.json", evidence)
    compact = read_json(directory / "results.json")
    for row in compact:
        cid = row["candidate_id"]
        row["visual_assessment"] = notes.get(cid, "Contact sheet viewed; individual detail not visually reviewed")
        if row.get("fixed_frame_outside_vertices"):
            row["visual_assessment"] += f" Fixed Task 12 whole frame: {row['fixed_frame_outside_vertices']} projected vertices outside bounds; see the separate shared 5%-margin context sheet."
        results[cid]["visual_assessment"] = row["visual_assessment"]
    write_json_atomic(directory / "results.json", compact)
    manifest["review_analysis_sha256"] = digest(evidence)
    manifest["storage_bytes"] = study_storage(directory)
    manifest["delivery_wall_seconds"] = time.time()-manifest["started_utc"]
    write_json_atomic(directory / "manifest.json", manifest)
    # Refresh static cards, then attach the small, explicit mask/attenuation evidence.
    from morphology_atlas import write_index
    write_index(directory, compact)
    index_path = atlas / "index.html"
    html = index_path.read_text(encoding="utf-8")
    observations = ''.join(f'<p><b>{escape(cid)}</b>: {escape(text)}</p>' for cid,text in notes.items())
    comparison = '<h2>Observed differences and limits</h2>' + observations
    comparison += '<p><a href="C_masks.png">C selection-mask comparison</a> · <a href="A000_raw_CC.png">Baseline A raw/CC</a> · <a href="A011_raw_CC.png">A011 raw/CC</a></p>'
    comparison += '<p>Some output vertices exceed the exact Task 12 whole frame. Separate context sheets use the same camera/light with a fixed 5% margin for every candidate: <a href="A_context.png">A full context</a> · <a href="B_context.png">B full context</a> · <a href="C_context.png">C full context</a>. Primary frames and detail crops remain unchanged.</p>'
    comparison += '<details><summary>Small measured comparisons (no beauty score)</summary><pre>' + escape(json.dumps({"A_accent":accents,"C_masks":masks},indent=2)) + '</pre></details>'
    html = html.replace('<div class="cards">', comparison + '<div class="cards">')
    index_path.write_text(html, encoding="utf-8")
    all_attempt_results = list(results.values()) + manifest.get("replays", [])
    status = Counter(r["execution_status"] for r in all_attempt_results)
    rejected = sum(r["geometry_screen"] == "crossing detected" for r in results.values())
    unique = len({r["recipe_sha256"] for r in manifest["candidates"]})
    duplicates = [(cid,r["duplicate_of"]) for cid,r in results.items() if r.get("duplicate_of")]
    processes = [r["process"] for r in all_attempt_results] + [r["audit_process"] for r in all_attempt_results if "audit_process" in r]
    peak = max((p["peak_combined_resident_bytes"] for p in processes if p.get("peak_combined_resident_bytes") is not None), default=None)
    minimum = min((p["minimum_available_bytes"] for p in processes if p.get("minimum_available_bytes") is not None), default=None)
    summary = {"attempted":len(manifest["attempts"]), "distinct_recipe_configurations":unique, "execution_counts":dict(status),
        "sampled_crossing_rejected":rejected, "duplicate_outputs":duplicates, "baseline_matches":manifest["baseline_gate"],
        "repeat_matches":{cid:r["repeat_match"] for cid,r in results.items() if "repeat_match" in r},
        "CLI_replays":manifest.get("replays", []),
        "geometry_and_audit_active_seconds":manifest["active_seconds"], "delivery_wall_seconds":manifest["delivery_wall_seconds"],
        "peak_combined_resident_bytes":peak, "minimum_available_bytes":minimum, "storage_bytes":manifest["storage_bytes"],
        "limits":manifest["limits"], "system_memory":manifest["system_memory"], "runtime":manifest["runtime"],
        "fixed_frame_warnings": {r["candidate_id"]:r["fixed_frame_outside_vertices"] for r in compact if r.get("fixed_frame_outside_vertices")},
        "candidate_records":{cid:r["record"] for cid,r in results.items()},
        "setup_issues_corrected_before_geometry": ["Mesh has no bounding_box method in installed COMPAS; used public compas.geometry.bounding_box.",
            "Explicit candidate directory creation added before atomic candidate writes.", "CIM access denied; standard Windows memory APIs and CPU registry description used."],
        "geometry_failures":{cid:r["reason"] for cid,r in results.items() if r["execution_status"] != "completed"}}
    write_json_atomic(directory / "performance_and_failures.json", summary)
    memory_text = (f"Peak combined geometry-runner/child resident {peak/1024**2:.1f} MiB; minimum available RAM {minimum/1024**3:.2f} GiB."
                   if peak is not None and minimum is not None else "Resident/available memory: NOT MEASURED.")
    physical = manifest["system_memory"]
    limit_text = (f"Measured RAM {physical['physical_bytes']/1024**3:.2f} GiB: resident cap {physical['resident_limit_bytes']/1024**3:.2f} GiB, available floor {physical['available_floor_bytes']/1024**3:.2f} GiB."
                  if physical["status"] == "MEASURED" else "Physical memory: NOT MEASURED; serial/count limits retained.")
    a = accents[0]
    shift = next(r for r in masks if r["candidate_id"] == "C007")
    paragraphs = ["# CHESHIRE Task 13 — start here",
        "Open [the offline atlas](atlas/index.html) or [FIRST LOOK](atlas/FIRST_LOOK.png). Nine actual representatives include baselines and weak controls. All views are **HEADLESS**, using Task 12's registered oblique projection, scale, crops and gray light.",
        f"**{len(manifest['attempts'])} attempted / {status['completed']} completed**, covering **{unique} distinct recipes** plus {len(manifest['attempts'])-unique} deliberate repeat/replay checks. Partial {status['partial']}; skipped {status['budget skip']}; timeouts {status['timeout']}; failures {status['failure']}; sampled-crossing rejected {rejected}. Exact A/B/C baseline records, three family repeats and the CLI replay matched. Duplicates are not form discoveries.",
        f"Geometry/audits: {manifest['active_seconds']/60:.2f} active minutes; atlas/analysis wall time {manifest['delivery_wall_seconds']/60:.2f} minutes. {memory_text} {limit_text} Storage {manifest['storage_bytes']/1024**2:.1f} MiB. One worker/audit at a time; 60 seconds per candidate, 30 per audit; max 60 workers; 2.5-hour experiment cutoff within three hours; 3 GiB storage. Existing count/selection/order budgets stay unchanged; projection resources are recorded separately.",
        "**Inspect first: " + ", ".join(recommendations) + ".** These span different organizations; they are not an optimized aesthetic ranking.",
        f"**A011 / A000 / A007:** wider core, longer fine period and higher fine-to-broad ratio change geometry, but articulation remains subtle. The weak zero-accent A007 control shows the macro field dominates. Baseline accent RMS coordinate contribution is {a['pre_CC']['rms']:.2f} model units before CC and {a['CC_retained_points']['rms']:.2f} afterward ({100*a['rms_retention_ratio']:.1f}% retained). Smoothing is only part of the weakness. This measures retained points, not semantic CC lineage.",
        "**B009 / B000 / B008:** two broader shoulder clusters leave the crown quiet, while the baseline uses four clusters. Extent/count changes distribution more clearly than small height changes. The matched cap-only control removes perimeter fans while retaining identical initial roots/cap settings. Tiled interiors and narrow, pinched-looking junctions remain; nonplanar exclusions are explicit.",
        f"**C010 / C007 / C008:** wider band spacing and smaller cap tips change the distribution, but edges remain grid-stepped. A +0.025 center shift adds {shift['added']} selected faces and removes {shift['removed']}; height-only C008 preserves the baseline mask exactly. See [actual masks](atlas/C_masks.png). This demonstrates fixed-grid sensitivity, not resolution independence.",
        "The grotesque-like target remains weak. A larger-scale grammar/selection experiment is a more useful next step than another broad parameter sweep. This limited study does not prove the approach impossible.",
        "Rhino-host checks: **NOT PERFORMED**. Zero sampled crossings excludes adjacent/coplanar/edge-only contacts and does not establish global clearance. Headless depth sorting is approximate. Some outputs exceed the exact Task 12 frame; cards flag them and supplementary context sheets use one shared 5% margin for every candidate. Primary frames/crops remain intact.",
        "The original 1,030-vertex / 936-face gate and its ten open components stay separate; units remain unconfirmed. No repair/welding/remeshing. A's terminal CC semantic lineage is **NOT IMPLEMENTED**; raw records remain intact. Full records, recipes, metrics and paths are listed in performance_and_failures.json. The ZIP includes source/diff/tests, hashes, the atlas and nine representatives' meshes/full records; other full records remain in ignored output.",
        "Import atlas/ORIGINAL.obj and chosen representative OBJ files into a **disposable Rhino document** on separate layers. Keep camera/scale fixed and inspect Shaded/Wireframe. Replay from the repository using the saved DLL preference:",
        "```powershell\n.\\.venv\\Scripts\\python.exe -E -s tools\\morphology.py --study output\\task13\\study --candidate A011\n.\\.venv\\Scripts\\python.exe -E -s tools\\morphology.py --study output\\task13\\study --candidate B009\n.\\.venv\\Scripts\\python.exe -E -s tools\\morphology.py --study output\\task13\\study --candidate C010\n```",
        "Matching source/code/runtime identities are required. Replays preserve prior outputs and count toward the ceiling. See tools/MORPHOLOGY_QUICKSTART.md for resume/STOP/atlas commands; no installation is required."]
    if (directory / "test_summary.json").exists():
        tests = read_json(directory / "test_summary.json")
        paragraphs.append("Final verification: " + tests["pytest_result"] + "; git diff --check: " + tests["diff_check"] + ".")
    (directory / "START_HERE.md").write_text("\n\n".join(paragraphs)+"\n",encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--representatives", nargs="+", required=True)
    parser.add_argument("--recommendations", nargs="+", required=True)
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--reuse-views", action="store_true", help="Reuse only matching retained projection inputs/images.")
    args = parser.parse_args()
    if len(args.representatives) > 9 or len(args.recommendations) > 3:
        parser.error("At most nine FIRST LOOK entries and three recommendations.")
    review(args.study.resolve(),args.representatives,args.recommendations,read_json(args.notes),reuse_views=args.reuse_views)
