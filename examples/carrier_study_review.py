"""Reproducible Task 15 evidence checks and small matched comparison figures."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
from html import escape
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))
from cheshire_worker import mesh_from_data, mesh_to_data, RUNTIME_IDENTITY
from carrier_study import carrier_ladder, coarse_gate, generation_schedules, schedule_extensions


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def comparison_views(study):
    """Reuse the first eight frames, then add the two retained follow-ups.

    Keep their exact shared camera and scale, including the unsafe fixed case.
    Add shaded detail alongside the previously retained wire diagnostics.
    """
    old = read(study / "generation_projection_plan.json")
    bounds = old["frames"][4]["bounds"]
    crop = next(f["bounds"] for f in old["frames"] if "detail_wire" in f["file"])
    frames, sheets = [], []
    def frame(case, g, label, area, name):
        mesh_path = f"generation/{case}/G{g}.json"
        # New full views must fit the original eight-case comparison bounds.
        if area == bounds:
            points = [v["xyz"] for v in read(study / mesh_path)["vertices"]]
            assert all(bounds[0] <= x+.65*y <= bounds[1] and bounds[2] <= z+.30*y <= bounds[3] for x,y,z in points)
        file = name+".png"
        frames.append(dict(mesh=mesh_path, label=label, bounds=area, width=550, height=600, wireframe=False, file=file))
        return file
    finals = [f["file"] for f in old["frames"] if "generation_final_" in f["file"]]
    for case in schedule_extensions():
        finals.append(frame(case, 5, case+" G5", bounds, "followup_final_"+case))
        items = [frame(case, g, case+f" G{g}", bounds, f"followup_{case}_G{g}") for g in (0,1,2,3,5)]
        sheets.append(dict(file=f"followup_progress_{case}.png", title=case+": actual generation progression", images=items))
    sheets.append(dict(file="generation_all_final.png", title="All ten schedules: unchanged C0 / budget / camera", images=finals))
    details = []
    for case in ("T01_seed", "T03_meso_interpolation", "T06_delayed_meso", "T08_fixed_moderate", "T09_meso_fine"):
        details.append(frame(case, 5, case+" G5 shoulder detail", crop, "detail_shaded_"+case))
    sheets.append(dict(file="generation_detail_shaded.png", title="Registered shoulder detail: same crop / scale / light", images=details))
    for sheet in sheets:
        sheet.update(columns=min(4,len(sheet["images"])), width=550, height=600)
    plan = study / "followup_projection_plan.json"
    write(plan, dict(frames=frames, sheets=sheets))
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "tools/morphology_projection.ps1"), "-PlanPath", str(plan)], cwd=ROOT, capture_output=True, text=True, timeout=300)
    (study / "followup_projection_log.txt").write_text(result.stdout+result.stderr, encoding="utf-8")
    result.check_returncode()


def diagnostic_views(study):
    """Actual flagged face positions; observational overlay, not a new test."""
    cases = [("primary/B_C0", 5), ("primary/B_C1", 1),
             ("generation/T00_fixed", 5), ("generation/T03_meso_interpolation", 5)]
    bounds = read(study / "generation_projection_plan.json")["frames"][4]["bounds"]
    width, height = 550, 600
    scale = min(500/(bounds[1]-bounds[0]), 500/(bounds[3]-bounds[2]))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1290" viewBox="0 0 1100 1290">',
           '<rect width="1100" height="1290" fill="white"/>',
           '<g font-family="Arial" fill="#18232d"><text x="12" y="22">HEADLESS fixed projection: actual topology and warning locations</text>',
           '<text x="12" y="45">Orange: opposed fan only | Red: conservative bilinear warning | Magenta: extraordinary vertices</text>',
           '<text x="12" y="65">Illustrative overlay, including back faces; no causality or global collision certificate.</text></g>']
    records=[]
    for index,(case,g) in enumerate(cases):
        data=read(study / case / f"G{g}.json")
        stage=read(study / case / "summary.json")["stages"][g-1]
        diagnostic=stage["diagnostics"]
        fan=set(diagnostic["opposed_fan_normals"])
        bilinear=set(diagnostic["bilinear_admissibility_warning_faces"])
        mesh=mesh_from_data(data)
        extra=set(diagnostic["extraordinary_association"]["extraordinary_vertices"])
        coords={v["id"]:v["xyz"] for v in data["vertices"]}
        def project(key):
            x,y,z=coords[key]
            return (25+(x+.65*y-bounds[0])*scale, 65+(bounds[3]-z-.30*y)*scale)
        offset_x=(index%2)*width; offset_y=90+(index//2)*height
        svg.append(f'<g transform="translate({offset_x},{offset_y})"><text x="12" y="18" font-family="Arial">{escape(case)} G{g} | fan {len(fan)} / bilinear {len(bilinear)}</text>')
        faces=data["faces"]
        ordered=sorted(faces, key=lambda f: sum(.65*coords[v][0]-coords[v][1]+.3*coords[v][2] for v in f["vertices"])/len(f["vertices"]))
        # Draw unflagged background first, warnings overlaid to locate all flags.
        for flagged in (False,True):
            for face in ordered:
                f=face["id"]
                if (f in fan or f in bilinear) != flagged:
                    continue
                fill="#c51b35" if f in bilinear else "#e99b26" if f in fan else "#dddddd"
                points=" ".join(f"{x:.2f},{y:.2f}" for x,y in (project(v) for v in face["vertices"]))
                svg.append(f'<polygon points="{points}" fill="{fill}" stroke="#66717b" stroke-width="0.15"/>')
        for v in sorted(extra):
            x,y=project(v)
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#b51abc"><title>vertex {v}, valence {mesh.vertex_degree(v)}</title></circle>')
        svg.append('</g>')
        records.append(dict(case=case,generation=g,extraordinary_association=diagnostic["extraordinary_association"],
            opposed_fan_faces=sorted(fan),bilinear_faces=sorted(bilinear)))
    svg.append('</svg>')
    (study / "topology_warning_locations.svg").write_text("\n".join(svg),encoding="utf-8")
    write(study / "topology_representatives.json",dict(scope="Current topology, near versus far warning rates and actual example corners; no cause inferred.",cases=records))


def audit(study):
    """Check executed evidence, not a duplicate unit-test matrix."""
    inputs=read(study / "inputs.json")
    ladder=carrier_ladder(coarse_gate(inputs["origin"]))
    checks={}
    for name,mesh in ladder.items():
        assert mesh_to_data(mesh) == read(study / f"carriers/{name}.json")
    checks["exact_deterministic_carriers"]="PASS"
    primary=read(study / "primary_selection.json")
    for label in ("A","B"):
        expected=primary[label+"_schedule"]
        for carrier in ("C0","C1","C2","DENSE"):
            directory=study / "primary" / (label+"_"+carrier)
            assert read(directory / "request.json")["schedule"] == expected
            assert read(directory / "G0.json") == read(study / f"carriers/{carrier}.json")
    checks["identical_primary_schedules"]="PASS"
    for name,schedule in {**generation_schedules(),**schedule_extensions()}.items():
        directory=study / "generation" / name
        request=read(directory / "request.json")
        assert request["mesh"] == read(study / "carriers/C0.json")
        assert request["schedule"] == schedule and len(schedule)==6
        assert request["spatial_modulation"] is False
    checks["ten_schedules_one_C0_no_spatial_fields"]="PASS"
    counts={}; cases=[]
    for phase in ("local","primary","generation"):
        summaries=sorted((study / phase).glob("*/summary.json"))
        counts[phase]=len(summaries)
        for path in summaries:
            summary=read(path)
            request=read(path.parent / "request.json")
            assert request["runtime_identity"]["ignore_environment"] and request["runtime_identity"]["no_user_site"]
            process=read(study / "logs" / phase / path.parent.name / "process.json")
            assert process["exit_code"] == 0 and process["stop"] is None
            assert process["seconds"] < 60 and process["peak_combined_resident_bytes"] <= 4*1024**3
            audit_data=read(path.parent / "crossing_audit.json")
            assert len(audit_data["candidates"]) == summary["generations_reached"]
            assert summary["source_immutable"] and not summary["spatial_modulation"]
            assert summary["semantic_lineage"] == "NOT IMPLEMENTED"
            assert len(summary["schedule"]) == 6
            with gzip.open(path.parent / "result.json.gz","rt",encoding="utf-8") as stream:
                full=json.load(stream)
            assert len(full["stages"]) == summary["generations_reached"]
            for stage in summary["stages"]:
                assert stage["validated"]
                assert stage["OBJ_roundtrip"] == "PASS ordered coordinates and face cycles"
                assert max(stage["vertex_count"],stage["face_count"]) <= 50000
                assert stage["statistics"]["components"] == (10 if path.parent.name.endswith("DENSE") else 1)
                assert not stage["diagnostics"]["degenerate_fan_faces"]
            # First study cases predate explicit checkpoint timing instrumentation.
            # Keep real total process timing and label filesystem estimates honestly.
            initial=(path.parent / "G0.json").stat().st_mtime
            previous=initial
            times=[]
            for stage in summary["stages"]:
                timestamp=(path.parent / f"G{stage['generation']}.json").stat().st_mtime
                times.append(dict(generation=stage["generation"],checkpoint_file_UTC=datetime.fromtimestamp(timestamp,timezone.utc).isoformat(),
                    approximate_seconds_since_G0_export=timestamp-initial,
                    approximate_seconds_since_previous_mesh_export=timestamp-previous,
                    measured_checkpoint_seconds=stage.get("checkpoint_elapsed_seconds")))
                previous=timestamp
            write(path.parent / "checkpoint_timing.json",dict(actual_total_process_seconds=process["seconds"],
                note="Initial executed cases have mesh-file modification-time estimates, including processing/exports, not instrumented backend timings. Future runs record monotonic checkpoint times explicitly.",checkpoints=times))
            last=summary["stages"][-1]
            cases.append(dict(case=path.parent.relative_to(study).as_posix(),status=summary["status"],reason=summary["reason"],
                generations=summary["generations_reached"],vertices=last["vertex_count"],faces=last["face_count"],
                bbox=last["statistics"]["bounding_box"],fan_warnings=len(last["diagnostics"]["opposed_fan_normals"]),
                bilinear_warnings=len(last["diagnostics"]["bilinear_admissibility_warning_faces"]),
                sampled_crossings=last["sampled_crossings"]["sampled_transverse_crossings"]))
    assert counts==dict(local=6,primary=8,generation=10)
    checks["all_24_attempts_and_every_completed_checkpoint_retained"]="PASS"
    # Evidence checks are intentionally separate from aesthetic judgments.
    operator=ROOT / "src/cheshire/weighted_subdivision.py"
    original=subprocess.check_output(["git","show",inputs["baseline"]+":src/cheshire/weighted_subdivision.py"],cwd=ROOT)
    assert operator.read_bytes().replace(b"\r\n",b"\n") == original.replace(b"\r\n",b"\n")
    checks["Task14_weighted_operator_unchanged"]="PASS"
    write(study / "evidence_audit.json",dict(checks=checks,counts=counts,cases=cases,
        operator_sha256=hashlib.sha256(original).hexdigest(),runtime_identity=inputs["runtime_identity"]))
    write(study / "environment.json",dict(normal_shell_runtime_identity=RUNTIME_IDENTITY,
        actual_installed_versions={name:version(name) for name in ("compas","pytest","pythonnet")},
        study_workers="Every case separately checked: explicit repository venv, -E -s, sanitized environment; request.json records identity.",
        no_new_dependencies=True,normal_shell_is_not_Rhino_host=True))
    print(checks,flush=True)


def reproduce(study):
    """One real repeat of a representative quiet result, not another sweep."""
    from weighted_subdivision_study import bounded_child
    directory=study / "reproduction/T03"
    if directory.exists():
        raise ValueError("Reproduction output already exists; retain it unchanged.")
    logs=study / "logs/reproduction/T03"
    process=bounded_child([str(ROOT / "examples/carrier_scale_study.py"),"--one",str(directory),
        "--input",str(study / "carriers/C0.json"),"--schedule",str(study / "schedules/generation_T03_meso_interpolation.json"),
        "--generations","6"],logs,60)
    write(logs / "process.json",process)
    assert process["exit_code"] == 0 and process["stop"] is None
    checks=[]
    for generation in range(6):
        filename=f"G{generation}.json"
        expected=read(study / "generation/T03_meso_interpolation" / filename)
        actual=read(directory / filename)
        assert actual==expected
        assert (directory / f"G{generation}.obj").read_bytes() == (study / "generation/T03_meso_interpolation" / f"G{generation}.obj").read_bytes()
        checks.append(dict(generation=generation,json_geometry="IDENTICAL",OBJ_bytes="IDENTICAL",
            mesh_sha256=hashlib.sha256(json.dumps(actual,sort_keys=True).encode()).hexdigest()))
    write(study / "reproducibility.json",dict(case="T03_meso_interpolation",process=process,checkpoints=checks,
        scope="Fresh real subprocess, same source and all six planned rows; G0-G5 actual geometry and OBJ bytes identical, G6 budget blocked."))
    print("T03 real subprocess repeat: identical G0-G5 geometry and OBJ bytes",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=("views","diagnostics","audit","reproduce"))
    parser.add_argument("--directory",type=Path,default=ROOT / "output/task15/study")
    args=parser.parse_args()
    {"views":comparison_views,"diagnostics":diagnostic_views,"audit":audit,"reproduce":reproduce}[args.phase](args.directory)


if __name__ == "__main__":
    main()
