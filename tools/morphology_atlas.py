"""Compact offline atlas of retained Task 13 records; no invented views."""

import argparse
import csv
from html import escape
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from morphology import (ROOT, digest, deterministic, load_record, read_json, write_json_atomic,
                        mesh_from_data, save_mesh, study_storage, LIMITS, assert_identity,
                        remembered_mola_path, monitored_process)


def projection(point):
    x, y, z = point
    return [x + .65 * y, z + .30 * y]


def registered_bounds(source, baseline):
    points = [projection(row["xyz"]) for mesh in [source["mesh"]] + [row["mesh"] for row in baseline["variants"]]
              for row in mesh["vertices"]]
    whole = [min(p[0] for p in points), max(p[0] for p in points), min(p[1] for p in points), max(p[1] for p in points)]
    xyz = [row["xyz"] for row in source["mesh"]["vertices"]]
    low = [min(p[a] for p in xyz) for a in range(3)]; high = [max(p[a] for p in xyz) for a in range(3)]
    width, height = high[0] - low[0], high[2] - low[2]
    result = {"whole": whole}
    for name, u, v in (("shoulder", .18, .68), ("crown", .38, .90)):
        p = projection([low[0] + u * width, low[1], low[2] + v * height])
        result[name] = [p[0] - .13 * width, p[0] + .13 * width, p[1] - .14 * height, p[1] + .14 * height]
    return result


def prepare(directory, representatives):
    manifest = read_json(directory / "manifest.json")
    assert_identity(manifest, remembered_mola_path(ROOT))
    source = read_json(manifest["source_path"])
    baseline = read_json(manifest["baseline_response"])
    atlas = directory / "atlas"
    atlas.mkdir(exist_ok=True); (atlas / "geometry").mkdir(exist_ok=True); (atlas / "images").mkdir(exist_ok=True)
    bounds = registered_bounds(source, baseline)
    plan = {"projection": {"u": "x+0.65*y", "v": "z+0.30*y", "depth": "0.65*x-y+0.30*z",
             "lighting": "Task 12 first-three-corner normal, gray=130+100*abs(dot(normal,[.3,-.8,.5]))",
             "limitations": "Approximate painter ordering; fan crossings diagnostic separate. No Rhino host verification."},
            "registered_bounds": bounds, "frames": [], "sheets": []}
    def frame(cid, name, mesh, crop="whole", wire=False):
        geometry = f"geometry/{name}.json"
        write_json_atomic(atlas / geometry, mesh)
        width, height = (450, 500) if crop == "whole" else (750, 780)
        file = f"images/{name}-{crop}{'-wire' if wire else ''}.png"
        plan["frames"].append({"mesh": geometry, "label": cid + (" / RAW pre-CC" if name.endswith("-raw") else ""),
            "bounds": bounds[crop], "width": width, "height": height, "wireframe": wire, "file": file})
        return file
    frame("ORIGINAL / unchanged 10 components", "ORIGINAL", source["mesh"])
    save_mesh(mesh_from_data(source["mesh"]), atlas / "ORIGINAL.obj")
    compact = []
    for row in manifest["candidates"]:
        cid = row["candidate_id"]
        if cid not in manifest["results"]:
            continue
        result = manifest["results"][cid]
        summary = {**{k: v for k, v in result.items() if k not in ("crossing_audit", "metrics")},
                   "phase": row["phase"], "changed_parameters": row["changed_parameters"], "recipe": row["recipe"],
                   "metrics": result.get("metrics"), "crossing_count": result.get("crossing_audit", {}).get("sampled_transverse_crossings")}
        if not result.get("record"):
            compact.append(summary); continue
        response = load_record(directory / result["record"])
        variant = response["variants"][0]
        screen = result["geometry_screen"]
        if row["phase"] != "repeat":
            frame(cid + " / " + screen, cid, variant["mesh"])
            points = [projection(v["xyz"]) for v in variant["mesh"]["vertices"]]
            b = bounds["whole"]
            summary["fixed_frame_outside_vertices"] = sum(not (b[0] <= p[0] <= b[1] and b[2] <= p[1] <= b[3]) for p in points)
        if cid in representatives:
            frame(cid + " / shaded shoulder", cid, variant["mesh"], "shoulder")
            frame(cid + " / wire shoulder", cid, variant["mesh"], "shoulder", True)
            frame(cid + " / shaded crown", cid, variant["mesh"], "crown")
            frame(cid + " / wire crown", cid, variant["mesh"], "crown", True)
            target = directory / "representatives" / cid
            target.mkdir(parents=True, exist_ok=True)
            save_mesh(mesh_from_data(variant["mesh"]), target / (cid + ".obj"))
            # One full compressed record retains every checkpoint, field and parent.
            import shutil
            shutil.copyfile(directory / result["record"], target / "response.json.gz")
            write_json_atomic(target / "recipe.json", row)
            write_json_atomic(target / "summary.json", result)
            if cid[0] == "A":
                raw = variant["steps"][2]["mesh"]
                frame(cid + " / RAW pre-CC", cid + "-raw", raw, "shoulder")
                frame(cid + " / RAW pre-CC wire", cid + "-raw", raw, "shoulder", True)
                save_mesh(mesh_from_data(raw), target / (cid + "-RAW.obj"))
        compact.append(summary)
        del response, variant
    by_id = {r["candidate_id"]: r for r in compact}
    for family in "ABC":
        ids = [row["candidate_id"] for row in manifest["candidates"] if row["recipe"]["id"] == family and row["phase"] != "repeat" and row["candidate_id"] in by_id and by_id[row["candidate_id"]].get("record")]
        plan["sheets"].append({"file": f"{family}_contact.png", "title": f"{family}: baseline {family}000 then controlled variants / crossings remain labeled",
            "columns": 4, "width": 450, "height": 500, "images": [f"images/{cid}-whole.png" for cid in ids]})
    plan["sheets"].append({"file": "FIRST_LOOK.png", "title": "FIRST LOOK: diverse baseline/variant/weak examples, not aesthetic ranking",
        "columns": 3, "width": 450, "height": 500, "images": [f"images/{cid}-whole.png" for cid in representatives]})
    for cid in representatives:
        family = cid[0]
        if family == "A":
            plan["sheets"].append({"file": f"{cid}_raw_CC.png", "title": cid + ": matched raw / terminal CC1 shoulder",
                "columns": 2, "width": 750, "height": 780, "images": [f"images/{cid}-raw-shoulder.png", f"images/{cid}-shoulder.png",
                    f"images/{cid}-raw-shoulder-wire.png", f"images/{cid}-shoulder-wire.png"]})
    if "B008" in by_id:
        # The paired baseline and cap-only control have identical roots/cap settings.
        plan["sheets"].append({"file": "B_ablation.png", "title": "B000 perimeter sides / B008 cap-only: same initial roots and cap parameters",
            "columns": 2, "width": 450, "height": 500, "images": ["images/B000-whole.png", "images/B008-whole.png"]})
    write_json_atomic(atlas / "projection_plan.json", plan)
    write_json_atomic(directory / "results.json", compact)
    fields = ["candidate_id", "phase", "execution_status", "geometry_screen", "crossing_count", "duplicate_of", "record"]
    with (directory / "results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(compact)
    return plan, compact


def write_index(directory, rows):
    atlas = directory / "atlas"
    cards = []
    for row in rows:
        cid = row["candidate_id"]
        image = f"images/{cid}-whole.png"
        if row["phase"] == "repeat":
            image = f"images/{row['duplicate_of']}-whole.png"
        group = "rejected" if row["geometry_screen"] == "crossing detected" else "candidate"
        cards.append(f'<article class="{group}" id="{cid}"><h2>{cid} — {escape(row["execution_status"])}</h2>'
            f'<p>{escape(row["geometry_screen"])}; crossings: {row["crossing_count"]}; duplicate: {row.get("duplicate_of") or "none"}</p>'
            f'<a href="{image}"><img loading="lazy" src="{image}" alt="HEADLESS {cid}"></a>'
            f'<p>{escape(row["visual_assessment"])}</p><p>{escape(row.get("reason") or "")}</p>'
            f'<details><summary>Reproducible recipe and metrics</summary><pre>{escape(json.dumps(row["recipe"],indent=2))}</pre>'
            f'<pre>{escape(json.dumps(row.get("metrics"),indent=2))}</pre></details>'
            f'<p>Full record: {escape(row.get("record") or "none")}</p></article>')
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    html += '<title>CHESHIRE Task 13 — actual morphology atlas</title><style>body{font:16px system-ui;max-width:1500px;margin:2rem auto;padding:1rem;color:#25313c;background:#eee} img{max-width:100%} .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:1rem}article{background:white;padding:1rem} .rejected{border:4px solid #b74028}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}a{color:#135380}</style>'
    html += '<h1>CHESHIRE morphology atlas</h1><p>HEADLESS saved geometry. Same Task 12 oblique projection, scale, crops and gray lighting. Approximate polygon depth sorting; no Rhino-host verification. Zero sampled crossings does not establish global clearance. Source seams are preserved.</p>'
    html += '<p><a href="../START_HERE.md">START HERE</a> · <a href="FIRST_LOOK.png">FIRST LOOK</a> · <a href="A_contact.png">A contact sheet</a> · <a href="B_contact.png">B contact sheet</a> · <a href="C_contact.png">C contact sheet</a> · <a href="B_ablation.png">B ablation</a></p>'
    html += '<h2>Read first</h2><a href="FIRST_LOOK.png"><img src="FIRST_LOOK.png" alt="FIRST LOOK actual fixed-camera meshes"></a>'
    html += '<div class="cards">' + ''.join(cards) + '</div></html>'
    (atlas / "index.html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--representatives", nargs="+", required=True)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= len(args.representatives) <= 9:
        parser.error("FIRST LOOK must have at most nine representatives.")
    directory = args.study.resolve()
    plan, rows = prepare(directory, args.representatives)
    if not args.prepare_only:
        # Existing Windows drawing facilities; this never imports Rhino or .NET Mola.
        import time
        manifest = read_json(directory / "manifest.json")
        options = {"args": ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(ROOT / "tools/morphology_projection.ps1"), "-PlanPath", str(directory / "atlas/projection_plan.json")],
            "cwd": str(ROOT), "shell": False, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        process = monitored_process(options, directory / "atlas", 1800, directory,
            time.time() - manifest["started_utc"], directory / "atlas/projection_stdout.txt",
            directory / "atlas/projection_stderr.txt", wall_limit=LIMITS["wall_seconds"])
        write_json_atomic(directory / "atlas/projection_performance.json", process)
        if process["returncode"]:
            raise RuntimeError("Projection failed; keep actual records for diagnosis.")
    write_index(directory, rows)
    if study_storage(directory) >= LIMITS["storage_bytes"]:
        raise RuntimeError("Study storage cap reached")
    print(directory / "atlas/index.html")


if __name__ == "__main__":
    main()
