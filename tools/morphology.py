"""Serial, bounded Task 13 experiments; no geometry pipeline or Rhino UI."""

import argparse
from copy import deepcopy
import ctypes
from ctypes import wintypes
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rhino"))
from cheshire import save_mesh, inspect_mesh
from compas.geometry import bounding_box
from cheshire_worker import mesh_from_data
from exchange import VISUAL_MODE, read_json, write_json_atomic, validate_request, validate_response
from local_settings import remembered_mola_path
from visual_prototype import RECIPES
from worker_process import worker_launch_options

GIB = 1024 ** 3
LIMITS = {"workers": 60, "worker_seconds": 60, "audit_seconds": 30,
          "wall_seconds": 10800, "experiment_cutoff_seconds": 9000,
          "storage_bytes": 3 * GIB, "original_faces": 5000, "original_vertices": 20000,
          "output_faces": 50000, "output_vertices": 50000, "mola_selection": 1000}
VOLATILE = {"run_id", "source_run", "elapsed_seconds", "runtime_identity"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def deterministic(value):
    if isinstance(value, dict):
        return {key: deterministic(item) for key, item in value.items() if key not in VOLATILE}
    if isinstance(value, list):
        return [deterministic(item) for item in value]
    return value


def code_identity():
    paths = [ROOT / "pyproject.toml"]
    for directory in ("src/cheshire", "rhino", "tools"):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.suffix in (".py", ".ps1", ".json"))
    files = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
             for path in sorted(paths)}
    return {"sha256": digest(files), "files": files}


def runtime_identity(dll):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    except OSError:
        cpu = "NOT MEASURED"
    dotnet = Path(os.environ["ProgramFiles"]) / "dotnet/dotnet.exe"
    from worker_process import worker_environment
    runtimes = subprocess.check_output([str(dotnet), "--list-runtimes"], env=worker_environment(),
        text=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).splitlines()
    return {"executable": str(Path(sys.executable).resolve()), "python": sys.version,
            "platform": platform.platform(), "logical_processors": os.cpu_count(), "cpu": cpu,
            "dependencies": {name: importlib.metadata.version(name) for name in ("compas", "pythonnet", "pytest")},
            "installed_dotnet_runtimes": runtimes, "gpu": "NOT MEASURED; not used by this study",
            "dll_sha256": hashlib.sha256(Path(dll).read_bytes()).hexdigest(),
            "runtime_config_sha256": hashlib.sha256((ROOT / "src/cheshire/mola.runtimeconfig.json").read_bytes()).hexdigest()}


def windows_memory(child_pid=None):
    """Standard Windows physical memory and process working sets, bytes."""
    if os.name != "nt":
        return {"status": "NOT MEASURED"}
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [(name, ctypes.c_ulonglong) for name in
            ("total", "available", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in
            ("peak", "resident", "quota_peak_paged", "quota_paged", "quota_peak_nonpaged", "quota_nonpaged", "page", "peak_page")]
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        status = MemoryStatus(); status.length = ctypes.sizeof(status)
        if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        resident = 0
        for pid in (os.getpid(), child_pid):
            if pid is None:
                continue
            handle = kernel.OpenProcess(0x0400 | 0x0010, False, pid)
            if not handle:
                raise OSError("Cannot measure child working set")
            try:
                counters = Counters(); counters.cb = ctypes.sizeof(counters)
                if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                    raise OSError("GetProcessMemoryInfo failed")
                resident += counters.resident
            finally:
                kernel.CloseHandle(handle)
        return {"status": "MEASURED", "physical_bytes": status.total, "available_bytes": status.available,
                "combined_resident_bytes": resident, "resident_limit_bytes": min(4 * GIB, status.total // 4),
                "available_floor_bytes": max(2 * GIB, int(.15 * status.total))}
    except (OSError, AttributeError):
        return {"status": "NOT MEASURED"}


def source_request(source, dll):
    request = {"protocol": 1, "mode": VISUAL_MODE, "run_id": str(uuid4()), "source": deepcopy(source["source"]),
               "mesh": deepcopy(source["mesh"]), "mola_dll": dll, "selected_faces": "ALL_ELIGIBLE_PLANAR"}
    validate_request(request)
    return request


def candidate(family, number, changes=None, *, phase="screen", reason="", repeat_of=None):
    recipe = deepcopy(next(row for row in RECIPES if row["id"] == family))
    recipe["parameters"].update(deepcopy(changes or {}))
    if recipe["parameters"].get("study_cap_only"):
        recipe["parameters"]["side_policy"] = "Study cap-only ablation; no perimeter-side growth."
        recipe["order"][1] = "cap-only Mola (study ablation)"
    return {"candidate_id": f"{family}{number:03d}", "recipe": recipe, "phase": phase,
            "changed_parameters": deepcopy(changes or {}), "reason": reason, "repeat_of": repeat_of,
            "recipe_sha256": digest(recipe)}


def initial_candidates():
    rows = [candidate(f, 0, phase="baseline", reason="Exact delivered 12.3 baseline gate") for f in "ABC"]
    screens = {
        "A": [("narrow ribbon", {"width": .07875}), ("broad ribbon", {"width": .13125}),
              ("less sway", {"ribbon_sway": .0675}), ("longer broad period", {"ribbon_period": 1.0625}),
              ("shorter fine period", {"accent_period": .09}), ("longer fine period", {"accent_period": .15}),
              ("no fine accent control", {"accent_strength": 0}), ("fine/broad ratio +25%", {"accent_strength": .005})],
        "B": [("compact separated clusters", {"radii": [.105, .12]}), ("broader clusters", {"radii": [.175, .20]}),
              ("two shoulder clusters", {"centers": [[.17, .68], [.83, .68]]}),
              ("initial height -25%", {"height_ratios": [.315, .30, .27]}),
              ("perimeter-side height -25%", {"side_height_ratio": .15}),
              ("perimeter-side height +25%", {"side_height_ratio": .25}),
              ("second taper -25%", {"fractions": [.22, .36, .56]}),
              ("paired cap-only ablation", {"study_cap_only": True})],
        "C": [("shallower band slope", {"chevron_slope": .54}), ("steeper band slope", {"chevron_slope": .90}),
              ("narrow band", {"width": .04875}), ("broad band", {"width": .08125}),
              ("band spacing +25%", {"band_centers": [.21, .66, 1.085]}),
              ("core/band ratio -25%", {"core_width": .0285}),
              ("normalized centers shifted +.025", {"band_centers": [.325, .685, 1.025]}),
              ("all tier heights -25%", {"height_ratios": [.285, .255, .21]})]}
    for family, variants in screens.items():
        rows.extend(candidate(family, n, values, reason=reason) for n, (reason, values) in enumerate(variants, 1))
    return rows


def check_candidate(row):
    family, cid = row["recipe"]["id"], row["candidate_id"]
    if family not in "ABC" or not re.fullmatch(r"[ABC]\d{3}", cid) or cid[0] != family:
        raise ValueError("Separate A/B/C family ID and matching candidate_id are required.")
    if digest(row["recipe"]) != row["recipe_sha256"]:
        raise ValueError("Recipe identity changed; create a new candidate ID.")
    p = row["recipe"]["parameters"]
    for key in ("width", "core_width", "ribbon_period", "accent_period"):
        if key in p and p[key] <= 0:
            raise ValueError("Widths and periods must be positive.")
    if "core_width" in p and p["core_width"] >= p["width"]:
        raise ValueError("Core width must remain inside band/ribbon width.")
    for height in p.get("height_ratios", []) + [p[k] for k in ("side_height_ratio", "side_cap_height_ratio") if k in p]:
        if not 0 < height <= .5:
            raise ValueError("Height ratio outside the unchanged Mola adapter bounds.")
    if any(not 0 < value < .9 for value in p.get("fractions", [])):
        raise ValueError("Taper outside the unchanged Mola adapter bounds.")
    if "study_cap_only" in p and type(p["study_cap_only"]) is not bool:
        raise ValueError("The study ablation flag must be Boolean.")
    fixed = next(r for r in RECIPES if r["id"] == family)["parameters"]
    for key in ("quad_levels", "cc_levels", "side_directions", "maximum_sides_per_parent"):
        if key in fixed and p.get(key) != fixed[key]:
            raise ValueError(f"{key} describes fixed behavior and is not a sweep control.")


def gzip_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as stream:
        json.dump(value, stream, separators=(",", ":"), allow_nan=False)
    temporary.replace(path)


def load_record(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def study_storage(directory):
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def resource_reason(memory):
    if memory["status"] == "MEASURED":
        if memory["available_bytes"] < memory["available_floor_bytes"]:
            return "Available system memory below floor"
        if memory["combined_resident_bytes"] > memory["resident_limit_bytes"]:
            return "Combined runner/child resident memory exceeded cap"
    return None


def monitored_process(options, directory, seconds, study, elapsed, stdout_path, stderr_path, *, wall_limit=None):
    started = time.monotonic(); stop = None; samples = []
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(**options, stdout=stdout, stderr=stderr)
        try:
            while process.poll() is None:
                memory = windows_memory(process.pid); samples.append(memory)
                stop = resource_reason(memory)
                if time.monotonic() - started >= seconds:
                    stop = "timeout"
                elif elapsed + time.monotonic() - started >= (wall_limit or LIMITS["experiment_cutoff_seconds"]):
                    stop = "Batch experiment cutoff reached"
                elif study_storage(study) >= LIMITS["storage_bytes"]:
                    stop = "New study storage cap reached"
                if stop:
                    process.terminate(); process.wait(timeout=10)
                    break
                time.sleep(.25)
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=10)
    measured = [m for m in samples if m["status"] == "MEASURED"]
    return {"returncode": process.returncode, "stop_reason": stop, "wall_seconds": time.monotonic() - started,
            "memory_status": "MEASURED" if measured else "NOT MEASURED",
            "peak_combined_resident_bytes": max((m["combined_resident_bytes"] for m in measured), default=None),
            "minimum_available_bytes": min((m["available_bytes"] for m in measured), default=None)}


def classify_response(response, process):
    if process["stop_reason"] == "timeout":
        return "partial" if response and response.get("variants") else "timeout"
    if not response:
        return "failure"
    if response["status"] == "SUCCESS" and process["returncode"] == 0:
        return "completed"
    if response.get("variants"):
        return "partial"
    if "blocked before" in (response.get("reason") or "").lower() or "1000-face" in (response.get("reason") or ""):
        return "budget skip"
    return "failure"


def metrics(variant):
    result = {"vertices": variant["vertex_count"], "faces": variant["face_count"],
              "completed_steps": len(variant["steps"]), "semantic_lineage": variant["semantic_lineage"], "stages": []}
    for step in variant["steps"]:
        p = step["parameters"]
        params = p.get("actual_parameters", [])
        heights = [row["height"] for row in params if "height" in row]
        area_map = {row["id"]: row["value"] for row in step.get("fields", {}).get("face_area", [])}
        areas = list(area_map.values())
        roles = step.get("face_roles", [])
        roots = {row["id"]: row["value"] for row in step.get("fields", {}).get("root_face", [])}
        active = [r["id"] for r in roles if r["created_step"] == step["index"] and r["role"] in ("side", "cap")]
        result["stages"].append({"index": step["index"], "operator": step["operator"], "inspection": step["inspection"],
            "budget": step["budget"], "proposed": len(p.get("proposed_faces", [])), "selected": len(p.get("selected_faces", [])),
            "excluded": len(step["excluded_selected_faces"]), "root_coverage_count": len({roots[k] for k in active}),
            "height_range": [min(heights), max(heights)] if heights else None,
            "area_range": [min(areas), max(areas)] if areas else None,
            "new_sides": sum(r["role"] == "side" and r["created_step"] == step["index"] for r in roles),
            "new_caps": sum(r["role"] == "cap" and r["created_step"] == step["index"] for r in roles),
            "tier_area_ranges": {role: [min(values), max(values)] if values else None for role in ("side", "cap")
                for values in [[area_map[r["id"]] for r in roles if r["role"] == role and r["created_step"] == step["index"]]]},
            "maximum_displacement": p.get("maximum_displacement"),
            "terminal_surface_metrics": step.get("terminal_derivative")})
    final_mesh = mesh_from_data(variant["mesh"])
    result["components"] = len(final_mesh.connected_vertices())
    return result


def assert_identity(manifest, dll):
    current = {"source": digest(read_json(manifest["source_path"])["mesh"]),
               "code": code_identity()["sha256"], "runtime": digest(runtime_identity(dll))}
    if current != manifest["identities"]:
        raise ValueError("Source/code/runtime identity mismatch: resume/reproduction refused.")
    for row in manifest["candidates"]:
        check_candidate(row)


def initialize(directory, source_path, baseline_path):
    dll = remembered_mola_path(ROOT)
    if dll is None:
        raise RuntimeError("Existing official DLL preference is missing; no installation or search.")
    source = read_json(source_path)
    source_request(source, dll)
    directory.mkdir(parents=True, exist_ok=False)
    write_json_atomic(directory / "source.json", {"source": source["source"], "mesh": source["mesh"]})
    mesh = mesh_from_data(source["mesh"])
    code, runtime = code_identity(), runtime_identity(dll)
    rows = initial_candidates()
    (directory / "candidates").mkdir()
    manifest = {"schema": 1, "baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "started_utc": time.time(), "active_seconds": 0, "source_path": str((directory / "source.json").resolve()),
        "baseline_response": str(baseline_path.resolve()), "source_info": {"inspection": inspect_mesh(mesh),
            "components": len(mesh.connected_vertices()),
            "bounding_box_corners": bounding_box([mesh.vertex_coordinates(k) for k in mesh.vertices()]),
            "units": source["source"].get("unit_system", "UNCONFIRMED model coordinate units")},
        "identities": {"source": digest(source["mesh"]), "code": code["sha256"], "runtime": digest(runtime)},
        "code": code, "runtime": runtime, "system_memory": windows_memory(), "limits": LIMITS,
        "candidates": rows, "results": {}, "attempts": [], "baseline_gate": {}, "stop_reason": None, "additions": []}
    write_json_atomic(directory / "manifest.json", manifest)
    for row in rows:
        write_json_atomic(directory / "candidates" / (row["candidate_id"] + ".json"), row)
    return manifest


def append_candidates(directory, path):
    manifest = read_json(directory / "manifest.json")
    dll = remembered_mola_path(ROOT)
    assert_identity(manifest, dll)
    additions = read_json(path)
    ids = {r["candidate_id"] for r in manifest["candidates"]}
    for row in additions:
        check_candidate(row)
        if row["candidate_id"] in ids:
            raise ValueError("Candidate IDs are immutable and unique.")
        ids.add(row["candidate_id"])
    combined = sum(r["phase"] == "combined" for r in manifest["candidates"] + additions)
    if combined > 12 or len(manifest["candidates"]) + len(additions) > LIMITS["workers"]:
        raise ValueError("Combined variation/worker ceiling exceeded.")
    manifest["candidates"].extend(additions)
    manifest["additions"].append({"at_utc": time.time(), "rows": additions})
    for row in additions:
        write_json_atomic(directory / "candidates" / (row["candidate_id"] + ".json"), row)
    write_json_atomic(directory / "manifest.json", manifest)


def execute(directory, *, resume=False, phase=None, selected=None):
    manifest_path = directory / "manifest.json"
    manifest = read_json(manifest_path)
    dll = remembered_mola_path(ROOT)
    assert_identity(manifest, dll)
    if manifest["stop_reason"] and manifest["stop_reason"] != "STOP file":
        raise ValueError("Stopped study requires investigation: " + manifest["stop_reason"])
    manifest["stop_reason"] = None
    source = read_json(manifest["source_path"])
    rows = [r for r in manifest["candidates"] if (phase is None or r["phase"] == phase) and (selected is None or r["candidate_id"] == selected)]
    if not rows:
        raise ValueError("No matching candidate.")
    started = time.monotonic()
    for row in rows:
        cid = row["candidate_id"]
        if cid in manifest["results"] and selected is None:
            if resume:
                continue
            raise ValueError("Existing result: use --resume or --candidate for a fresh replay.")
        used = manifest["active_seconds"] + time.monotonic() - started
        wall = time.time() - manifest["started_utc"]
        stop = resource_reason(windows_memory())
        if (directory / "STOP").exists(): stop = "STOP file"
        elif used >= LIMITS["experiment_cutoff_seconds"] or wall >= LIMITS["experiment_cutoff_seconds"]: stop = "Batch experiment cutoff reached"
        elif len(manifest["attempts"]) >= LIMITS["workers"]: stop = "60-worker ceiling reached"
        elif study_storage(directory) >= LIMITS["storage_bytes"]: stop = "New study storage cap reached"
        if stop:
            manifest["stop_reason"] = stop; break
        if row["phase"] != "baseline" and set(manifest["baseline_gate"]) != set("ABC"):
            raise ValueError("All three exact baselines must pass before exploration.")
        check_candidate(row)
        attempt = len(manifest["attempts"]) + 1
        run = directory / "runs" / (cid + f"-{attempt:02d}")
        run.mkdir(parents=True, exist_ok=False)
        request = source_request(source, dll)
        write_json_atomic(run / "request.json", request)
        recipe_path = directory / "candidates" / (cid + ".json")
        if read_json(recipe_path) != row:
            raise ValueError("Explicit candidate file differs from manifest.")
        options = worker_launch_options(ROOT, run / "request.json", run / "response.json")
        options["args"][3] = str(ROOT / "tools/morphology_worker.py")
        options["args"].append(str(recipe_path))
        manifest["attempts"].append({"candidate_id": cid, "run": run.relative_to(directory).as_posix(), "status": "running"})
        write_json_atomic(manifest_path, manifest)
        process = monitored_process(options, run, LIMITS["worker_seconds"], directory, used,
                                    run / "worker_stdout.txt", run / "worker_stderr.txt")
        response = None
        if (run / "response.json").exists():
            response = validate_response(read_json(run / "response.json"), request)
        status = classify_response(response, process)
        result = {"candidate_id": cid, "execution_status": status, "process": process,
                  "geometry_screen": "not checked", "visual_assessment": "not visually reviewed",
                  "run": run.relative_to(directory).as_posix(), "reason": (response or {}).get("reason"),
                  "recipe_sha256": row["recipe_sha256"], "record": None}
        if response and response["variants"]:
            variant = response["variants"][0]
            result.update(geometry_sha256=digest(variant["mesh"]), deterministic_sha256=digest(deterministic(variant)), metrics=metrics(variant))
            save_mesh(mesh_from_data(variant["mesh"]), run / "output.obj")
            gzip_json(run / "response.json.gz", response)
            result["record"] = (run / "response.json.gz").relative_to(directory).as_posix()
            prior = next((k for k, v in manifest["results"].items() if v.get("geometry_sha256") == result["geometry_sha256"]), None)
            result["duplicate_of"] = prior
            if row["phase"] == "baseline":
                old = next(v for v in read_json(manifest["baseline_response"])["variants"] if v["id"] == row["recipe"]["id"])
                match = status == "completed" and digest(deterministic(old)) == result["deterministic_sha256"]
                result["baseline_match"] = match
                if not match:
                    manifest["stop_reason"] = "Baseline geometry/lineage/parameter regression"
                else:
                    manifest["baseline_gate"][row["recipe"]["id"]] = result["deterministic_sha256"]
            if row.get("repeat_of") or (selected and cid in manifest["results"]):
                reference = manifest["results"][row.get("repeat_of") or cid]
                result["repeat_match"] = all(result[k] == reference[k] for k in ("geometry_sha256", "deterministic_sha256"))
                if not result["repeat_match"]:
                    manifest["stop_reason"] = "Fresh-process repeat changed deterministic output"
            # Same fixed Task 12 diagnostic in its own serial, bounded process.
            audit_options = worker_launch_options(ROOT, run / "request.json", run / "response.json")
            audit_options["args"] = audit_options["args"][:3] + [str(ROOT / "tools/morphology_crossings.py"), str(run)]
            audit = monitored_process(audit_options, run, LIMITS["audit_seconds"], directory,
                manifest["active_seconds"] + time.monotonic() - started, run / "audit_stdout.txt", run / "audit_stderr.txt")
            result["audit_process"] = audit
            if (run / "crossing_audit.json").exists() and audit["returncode"] == 0:
                crossing = read_json(run / "crossing_audit.json")["candidates"][0]
                result["crossing_audit"] = crossing
                result["geometry_screen"] = "crossing detected" if crossing["sampled_transverse_crossings"] else "no sampled crossing"
            # Retain every complete stage/field/lineage in gzip; discard only this
            # runner's redundant uncompressed response after atomic compression.
            (run / "response.json").unlink()
        stderr = (run / "worker_stderr.txt").read_text(encoding="utf-8")
        reason = result.get("reason") or stderr[-1500:]
        if status != "completed" and any(word in reason.casefold() for word in
            ("original study input changed", "lost available lineage", "runtime", "coreclr", "pythonnet", "dll", "stdlib", "sre module", "outside this repository")):
            manifest["stop_reason"] = "Shared runtime/source/lineage blocker: " + reason
        if row["phase"] == "baseline" and status != "completed":
            manifest["stop_reason"] = "Baseline failed: " + reason
        if process["stop_reason"] and process["stop_reason"] != "timeout":
            manifest["stop_reason"] = process["stop_reason"]
        if digest(source["mesh"]) != manifest["identities"]["source"] or digest(read_json(manifest["source_path"])["mesh"]) != manifest["identities"]["source"]:
            manifest["stop_reason"] = "Source mutation"
        if selected and cid in manifest["results"]:
            manifest.setdefault("replays", []).append(result)
        else:
            manifest["results"][cid] = result
        manifest["attempts"][-1]["status"] = status
        write_json_atomic(run / "summary.json", result)
        write_json_atomic(manifest_path, manifest)
        print(cid, status, result["geometry_screen"], result.get("metrics", {}).get("faces"), flush=True)
        del response
        if manifest["stop_reason"]:
            break
    manifest["active_seconds"] += time.monotonic() - started
    manifest["wall_seconds"] = time.time() - manifest["started_utc"]
    manifest["storage_bytes"] = study_storage(directory)
    write_json_atomic(manifest_path, manifest)
    if manifest["stop_reason"]:
        raise RuntimeError(manifest["stop_reason"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--baseline-response", type=Path)
    parser.add_argument("--append", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--phase", choices=("baseline", "screen", "combined", "repeat"))
    parser.add_argument("--candidate")
    args = parser.parse_args()
    directory = args.study.resolve()
    if not directory.is_relative_to(ROOT / "output/task13"):
        parser.error("Studies must be in this repository's ignored output/task13 directory.")
    if args.init:
        if args.source is None or args.baseline_response is None:
            parser.error("Initialization needs an explicit original --source and --baseline-response.")
        initialize(directory, args.source, args.baseline_response)
    elif args.append:
        append_candidates(directory, args.append)
    else:
        execute(directory, resume=args.resume, phase=args.phase, selected=args.candidate)


if __name__ == "__main__":
    main()
