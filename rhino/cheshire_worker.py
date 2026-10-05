"""Fixed four-step demo in CHESHIRE's Python 3.12 .venv; no Rhino imports."""

import sys
import pathlib
import re
from pathlib import Path

# Allows the external script to work with the existing src checkout as well as
# its editable installation, without installing anything into Rhino.
ROOT = Path(__file__).resolve().parents[1]


def check_runtime_identity(identity):
    """Reject a redirected interpreter/stdlib or an unrelated CHESHIRE copy."""
    expected = ROOT / ".venv/Scripts/python.exe"
    if Path(identity["executable"]).resolve() != expected.resolve():
        raise RuntimeError(f"Worker Python must be {expected}; got {identity['executable']}.")
    if Path(identity["prefix"]).resolve() != (ROOT / ".venv").resolve():
        raise RuntimeError("Worker Python prefix does not match this repository's .venv.")
    for name in ("pathlib_file", "re_file"):
        if ".rhinocode" in {part.casefold() for part in Path(identity[name]).resolve().parts}:
            raise RuntimeError(f"Worker stdlib is contaminated by Rhino: {identity[name]}.")
    if identity.get("cheshire_file") is not None and not Path(identity["cheshire_file"]).resolve().is_relative_to(ROOT):
        raise RuntimeError(f"CHESHIRE package is outside this repository: {identity['cheshire_file']}.")


RUNTIME_IDENTITY = {
    "executable": sys.executable, "version": sys.version, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
    "pathlib_file": str(Path(pathlib.__file__).resolve()), "re_file": str(Path(re.__file__).resolve()),
    "ignore_environment": bool(sys.flags.ignore_environment), "no_user_site": bool(sys.flags.no_user_site),
}
check_runtime_identity(RUNTIME_IDENTITY)  # Before argparse, COMPAS, or CHESHIRE imports.

import argparse
from copy import deepcopy
from time import perf_counter

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cheshire
RUNTIME_IDENTITY["cheshire_file"] = str(Path(cheshire.__file__).resolve())
check_runtime_identity(RUNTIME_IDENTITY)

from compas.datastructures import Mesh
from cheshire import (
    ExecutionBudget, FieldSpec, Rule, analyze_vertex_attributes, build_scalar_field,
    displace_vertices_along_normals, estimate_quad_subdivision, identity_lineage,
    inherit_fields, plan_execution, subdivide_quad_once, validate_lineage_coverage,
    validate_mesh,
)
from exchange import (
    MAX_STAGE_COUNT, MAX_STEPS, TIMEOUT_SECONDS, read_json, validate_mesh_data,
    validate_request, validate_response, write_json_atomic,
)


RECIPE = {
    "name": "CHESHIRE normal-variation mesh-grammar experiment",
    "order": "bilinear quad subdivision → measure → power map → positive rule → outward displacement → validate",
    "attribute": "approximate_curvature", "interpretation": "incident-normal variation proxy, not exact curvature",
    "mapping": "power", "exponent": 2.0, "lower_percentile": 0.0, "upper_percentile": 100.0,
    "selection": "valid mapped values > 0", "strength_schedule": "user_strength / (2 ** step_index), step_index starts at 0",
    "nonplanar_policy": "bilinear", "maximum_steps": MAX_STEPS,
    "scope": "Our experimental recipe; not Digital Grotesque or modified Catmull-Clark. No ornament claim or global collision guarantee.",
}
SPECS = [FieldSpec("source_face", "face", "categorical", "CATEGORICAL"),
         FieldSpec("driver", "vertex", "scalar", "RECOMPUTE")]


def mesh_to_data(mesh):
    return {"vertices": [{"id": key, "xyz": list(mesh.vertex_coordinates(key))} for key in mesh.vertices()],
            "faces": [{"id": key, "vertices": list(mesh.face_vertices(key))} for key in mesh.faces()]}


def mesh_from_data(data):
    validate_mesh_data(data)
    mesh = Mesh()
    for row in data["vertices"]:
        x, y, z = row["xyz"]
        mesh.add_vertex(key=row["id"], x=x, y=y, z=z)
    for row in data["faces"]:
        mesh.add_face(row["vertices"], fkey=row["id"])
    return mesh


def lineage_data(lineage):
    return {domain: [{"id": child, "parents": [{"id": ref.key, "weight": ref.weight} for ref in refs]}
                     for child, refs in parents.items()]
            for domain, parents in (("vertices", lineage.vertex_parents), ("faces", lineage.face_parents))}


def run_experiment(request, publish=None):
    """Four fixed applications only; append/publish after full step validation."""
    validate_request(request)
    start = perf_counter()
    mesh = mesh_from_data(request["mesh"])
    fields = {"source_face": {key: key for key in mesh.faces()}}
    response = {"protocol": 1, "run_id": request["run_id"], "source": deepcopy(request["source"]),
                "recipe": deepcopy(RECIPE), "strength": request["strength"], "status": "FAILED",
                "reason": None, "stages": [], "driver": None, "runtime_identity": deepcopy(RUNTIME_IDENTITY)}
    budget = ExecutionBudget(MAX_STAGE_COUNT, max_vertices=MAX_STAGE_COUNT, max_generation=MAX_STEPS)
    rule = Rule("positive driver", "driver", "vertex", "greater_than", 0.0, operator="normal_displacement")
    for step_index in range(MAX_STEPS):
        step_start = perf_counter()
        try:
            if perf_counter() - start >= TIMEOUT_SECONDS:
                raise ValueError("Whole-worker 60-second demo limit reached before the next step.")
            before, fields_before = mesh_to_data(mesh), deepcopy(fields)
            estimate = estimate_quad_subdivision(mesh, nonplanar_policy="bilinear")
            refined = subdivide_quad_once(mesh, budget=budget, current_generation=step_index, nonplanar_policy="bilinear")
            if validate_lineage_coverage(mesh, refined.mesh, refined.lineage):
                raise ValueError("Subdivision immediate-parent lineage is incomplete.")
            inherited = inherit_fields(refined.lineage, fields, SPECS)
            measured = analyze_vertex_attributes(refined.mesh)
            mapped = build_scalar_field(measured, "approximate_curvature", mapping="power", exponent=2.0,
                                        lower_percentile=0.0, upper_percentile=100.0)
            plan = plan_execution(refined.mesh, {"driver": mapped}, rule, budget, current_generation=step_index,
                                  cost_profile={"topology_preserving": True})
            if plan["status"] != "SAFE":
                raise ValueError("Displacement blocked by budget: " + " ".join(plan["reasons"]))
            effective = request["strength"] / (2 ** step_index)
            moved = displace_vertices_along_normals(refined.mesh, mapped["values"],
                                                  selected_vertices=plan["selected_vertices"], strength=effective, direction="outward")
            problems = validate_mesh(moved.mesh)
            if problems:
                raise ValueError("Completed step invalid: " + " ".join(problems))
            # Validates the displaced result against the same operator surface
            # contract, without allocating another subdivision or rejecting a
            # final valid stage merely because its NEXT subdivision is too big.
            estimate_quad_subdivision(moved.mesh, nonplanar_policy="bilinear")
            unchanged_topology = identity_lineage(moved.mesh)
            if validate_lineage_coverage(refined.mesh, moved.mesh, unchanged_topology):
                raise ValueError("Displacement changed topology or lost lineage coverage.")
            carried = inherit_fields(unchanged_topology, inherited.values, SPECS)
            if any(carried.unresolved_counts.values()) or mesh_to_data(mesh) != before or fields != fields_before:
                raise ValueError("Unresolved source-face inheritance or mutated source input.")
            values = mapped["values"]
            usable = [value for value in values.values() if value is not None]
            raw = [row["approximate_curvature"] for row in measured.values() if row["approximate_curvature"] is not None]
            notice = None
            if not usable:
                notice = "All driver values unavailable; no movement."
            elif min(usable) == max(usable) or max(usable) == 0:
                notice = "Usable driver values are constant/zero after mapping; no hidden alternative field."
            stage = {"generation": step_index + 1, "mesh": mesh_to_data(moved.mesh), "validated": True,
                     "vertex_count": moved.mesh.number_of_vertices(),
                     "face_count": moved.mesh.number_of_faces(), "policy": refined.nonplanar_policy,
                     "estimated_vertex_count": estimate["estimated_output_vertices"], "estimated_face_count": estimate["estimated_output_faces"],
                     "field_min": min(usable) if usable else None, "field_max": max(usable) if usable else None,
                     "raw_proxy_min": min(raw) if raw else None, "raw_proxy_max": max(raw) if raw else None,
                     "unavailable_count": sum(value is None for value in values.values()),
                     "selected_count": moved.selected_count, "moved_count": moved.moved_count,
                     "skipped_count": moved.skipped_count, "not_selected_count": len(values) - moved.selected_count,
                     "effective_strength": effective, "maximum_displacement": moved.max_displacement,
                     "base_scale": moved.base_scale, "elapsed_seconds": perf_counter() - step_start, "notice": notice,
                     "lineage": lineage_data(refined.lineage), "displacement_lineage": "identity; keys/connectivity checked",
                     "fields": {"source_face": [{"id": key, "value": value} for key, value in carried.values["source_face"].items()]},
                     "recompute_fields": carried.recompute_fields, "lineage_coverage": []}
            if step_index == 0:
                response["driver"] = {"label": "G1 driver: normal-variation proxy → power(2)",
                                      "mesh": mesh_to_data(refined.mesh), "values": [{"id": key, "value": value} for key, value in values.items()],
                                      "raw_values": [{"id": key, "value": row["approximate_curvature"]} for key, row in measured.items()],
                                      "parameters": mapped["parameters"], "measured_on": "G1 pre-displacement subdivided mesh"}
            response["stages"].append(stage)
            mesh, fields = moved.mesh, carried.values
            response["status"] = "PARTIAL"
            response["reason"] = "Completed-stage checkpoint; worker still running."
        except (ValueError, ArithmeticError, KeyError, TypeError) as error:
            response["status"] = "PARTIAL" if response["stages"] else "FAILED"
            response["reason"] = f"G{step_index + 1} stopped: {type(error).__name__}: {error}"
            break
        if publish is not None:
            publish(validate_response(response, request))
    else:
        response["status"], response["reason"] = "SUCCESS", None
    response["elapsed_seconds"] = perf_counter() - start
    validate_response(response, request)
    if publish is not None:
        publish(response)
    return response


def main():
    print("Worker Python: " + RUNTIME_IDENTITY["executable"] + " | " + RUNTIME_IDENTITY["version"].splitlines()[0], flush=True)
    print("Worker stdlib: re=" + RUNTIME_IDENTITY["re_file"] + "; pathlib=" + RUNTIME_IDENTITY["pathlib_file"], flush=True)
    print("CHESHIRE package: " + RUNTIME_IDENTITY["cheshire_file"], flush=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("response", type=Path)
    args = parser.parse_args()
    if args.request.resolve().parent != args.response.resolve().parent or args.response.exists():
        raise ValueError("Use new per-run request/response paths in one unique run directory.")
    request = validate_request(read_json(args.request))
    if request.get("mode") == "MOLA_TAPER_STUDY":
        from mola_study import run_mola_study
        response = run_mola_study(request, publish=lambda value: write_json_atomic(args.response, value))
    else:
        response = run_experiment(request, publish=lambda value: write_json_atomic(args.response, value))
    completed = "A/B/C completed" if request.get("mode") == "MOLA_TAPER_STUDY" else "G1/G2/G3/G4 completed"
    print(response["status"] + ": " + (response["reason"] or completed))
    return 0 if response["status"] in ("SUCCESS", "PARTIAL") else 1


if __name__ == "__main__":
    # The optional study imports these exchange helpers; reuse this worker
    # module rather than executing its startup checks a second time.
    sys.modules["cheshire_worker"] = sys.modules[__name__]
    raise SystemExit(main())
