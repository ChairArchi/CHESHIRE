"""Fixed, bounded weighted subdivision experiment; no recipe language."""
from math import dist, fsum
from time import perf_counter

from cheshire.attributes import analyze_vertex_attributes
from cheshire.execution import ExecutionBudget
from cheshire.mapping import smoothstep
from cheshire.validation import inspect_mesh
from cheshire.weighted_subdivision import STANDARD, weighted_subdivide_once
from cheshire_worker import mesh_from_data, mesh_to_data, RUNTIME_IDENTITY


# Extrusions below are ratios of the generation's GLOBAL mean input edge
# length. Thus U uses exactly the same coordinate-unit weights everywhere.
SCHEDULES = {
    "round_relief": [dict(wf=.28, w1=0, we=0, w2=0, wp=0), dict(wf=.12, w1=-.3, we=-.04, w2=-.3, wp=.02), dict(wf=.10, w1=-.3, we=-.03, w2=-.2, wp=.01)],
    "ribs": [dict(wf=.30, w1=-.65, we=-.12, w2=-.5, wp=.04), dict(wf=.16, w1=-.6, we=-.06, w2=-.6, wp=.03), dict(wf=.09, w1=-.4, we=-.04, w2=-.35, wp=.02)],
    "reverse_ribs": [dict(wf=-.25, w1=-.6, we=.10, w2=-.5, wp=-.03), dict(wf=-.14, w1=-.6, we=.06, w2=-.5, wp=-.02), dict(wf=-.08, w1=-.4, we=.03, w2=-.3, wp=-.01)],
    "interpolation": [dict(wf=.04, w1=-1.4, we=0, w2=-1.2, wp=0), dict(wf=.05, w1=-1.2, we=0, w2=-1.0, wp=0), dict(wf=.06, w1=-.8, we=0, w2=-.6, wp=0)],
    "fold_probe": [dict(wf=.48, w1=-1.6, we=-.22, w2=-1.3, wp=.10), dict(wf=.25, w1=-1.3, we=-.12, w2=-1.1, wp=.06), dict(wf=.14, w1=-.8, we=-.06, w2=-.6, wp=.03)],
    "attenuated": [dict(wf=.22, w1=-.6, we=-.08, w2=-.4, wp=.02), dict(wf=.08, w1=-.4, we=-.03, w2=-.3, wp=.01), dict(wf=.035, w1=-.25, we=-.01, w2=-.15, wp=0)],
}
DEFAULT_SCHEDULE = "attenuated"


def generation_weights(schedule, generation):
    """G1 macro, G2 meso, G3+ fine; reuse the recorded final row."""
    if type(generation) is not int or generation < 1 or not schedule:
        raise ValueError("A positive generation and nonempty fixed schedule are required.")
    return dict(schedule[min(generation-1, len(schedule)-1)])


def point_drivers(mesh, source_z):
    measured = analyze_vertex_attributes(mesh)
    intrinsic = {v: row["approximate_curvature"] for v, row in measured.items()}
    groups = {"corner": {v: [v] for v in mesh.vertices()},
              "face": {f: mesh.face_vertices(f) for f in mesh.faces()},
              "edge": {tuple(sorted(e)): list(e) for e in mesh.edges()}}
    result = {}
    for kind, points in groups.items():
        result[kind] = {}
        for key, vertices in points.items():
            z = fsum(source_z[v] for v in vertices) / len(vertices)
            present = [intrinsic[v] for v in vertices if intrinsic[v] is not None]
            raw = fsum(present)/len(present) if present else None
            # Fixed scale [0, .5] means a right angle reaches one; no changing
            # percentile range or fictitious curvature definition.
            result[kind][key] = dict(source_z=z, extrinsic=smoothstep(z),
                normal_variation=raw, intrinsic=None if raw is None else smoothstep(min(1.0, 2*raw)))
    return result


def run_candidate(source, *, study="U", schedule=None, generations=2, budget=None, publish=None):
    start = perf_counter()
    budget = budget or ExecutionBudget(50000, 50000, generations)
    schedule = [STANDARD.copy()] if study == "S" else (schedule or SCHEDULES[DEFAULT_SCHEDULE])
    if study not in ("S", "U", "F"):
        raise ValueError("Only S/U/F studies are defined.")
    z = {v: source.vertex_coordinates(v)[2] for v in source.vertices()}
    lo, hi = min(z.values()), max(z.values())
    z = {v: (value-lo)/(hi-lo) if hi != lo else 0.0 for v, value in z.items()}
    mesh = source
    result = dict(id=study, study=study, schedule=schedule, schedule_tail="repeat final row",
                  requested_generations=generations, stages=[], status="FAILED", reason=None,
                  semantic_lineage="NOT IMPLEMENTED", source=inspect_mesh(source))
    for generation in range(1, generations+1):
        try:
            ratios = STANDARD.copy() if study == "S" else generation_weights(schedule, generation)
            edge_scale = fsum(dist(mesh.vertex_coordinates(u), mesh.vertex_coordinates(v)) for u, v in mesh.edges()) / mesh.number_of_edges()
            base = {k: v*edge_scale if k in ("wf", "we", "wp") else v for k, v in ratios.items()}
            drivers = point_drivers(mesh, z) if study == "F" else None
            overrides = {}
            if drivers:
                for kind, rows in drivers.items():
                    overrides[kind] = {}
                    for key, d in rows.items():
                        # Z alone controls extrusion amplitude; normal variation
                        # alone controls interpolation. Contributions never mix.
                        amp = .08 + .92*d["extrinsic"]
                        bend = d["intrinsic"] if d["intrinsic"] is not None else 0.0
                        overrides[kind][key] = ({"wf": base["wf"]*amp} if kind == "face" else
                            {"we": base["we"]*amp, "w1": base["w1"]-.35*bend} if kind == "edge" else
                            {"wp": base["wp"]*amp, "w2": base["w2"]-.25*bend})
            refined = weighted_subdivide_once(mesh, base, point_weights=overrides,
                budget=budget, current_generation=generation-1)
            next_z = {child: fsum(z[parent]*weight for parent, weight in refs)
                      for child, refs in refined.sampling_parents.items()}
            metadata = refined.metadata
            field_rows = []
            for point in metadata["points"]:
                key = tuple(point["source"]) if point["point_class"] == "edge" else point["source"]
                if drivers:
                    field_rows.append(dict(id=point["id"], point_class=point["point_class"], **drivers[point["point_class"]][key]))
            ranges = {}
            for kind in ("face", "edge", "corner"):
                rows = [p["weights"] for p in metadata["points"] if p["point_class"] == kind]
                ranges[kind] = {k: [min(r[k] for r in rows), max(r[k] for r in rows)] for k in rows[0]}
            field_ranges = {key: ([min(values), max(values)] if values else None)
                for key in ("source_z", "extrinsic", "normal_variation", "intrinsic")
                for values in [[row[key] for row in field_rows if row[key] is not None]]}
            stage = dict(generation=generation, mesh=mesh_to_data(refined.mesh), validated=True,
                metadata=metadata, ratios=ratios, global_mean_edge_length=edge_scale, weights=base,
                weight_ranges=ranges, drivers=field_rows, field_ranges=field_ranges,
                source_z=[dict(id=v, value=value) for v, value in next_z.items()],
                sampling_parents=[dict(id=v, parents=[dict(id=p, weight=w) for p,w in refs]) for v,refs in refined.sampling_parents.items()],
                vertex_count=refined.mesh.number_of_vertices(), face_count=refined.mesh.number_of_faces())
            result["stages"].append(stage)
            mesh, z = refined.mesh, next_z
            result["status"] = "PARTIAL"
            if publish:
                publish(result)
        except (ValueError, ArithmeticError) as error:
            result["reason"] = f"G{generation} stopped: {error}"
            break
    else:
        result["status"] = "SUCCESS"
    result["elapsed_seconds"] = perf_counter()-start
    return result


def run_weighted_study(request, publish=None):
    from exchange import validate_response, WEIGHTED_MODE
    source = mesh_from_data(request["mesh"])
    response = dict(protocol=1, run_id=request["run_id"], source=request["source"], mode=WEIGHTED_MODE,
                    runtime_identity=RUNTIME_IDENTITY, recipe_version="14.1", variants=[], status="FAILED", reason=None)
    for study in ("S", "U", "F"):
        def checkpoint(candidate):
            response["variants"] = [v for v in response["variants"] if v["id"] != study] + [candidate]
            response["status"] = "PARTIAL"
            if publish:
                publish(validate_response(response, request))
        candidate = run_candidate(source, study=study, publish=checkpoint)
        response["variants"] = [v for v in response["variants"] if v["id"] != study] + [candidate]
    response["status"] = "SUCCESS" if all(v["status"] == "SUCCESS" for v in response["variants"]) else "PARTIAL" if any(v["stages"] for v in response["variants"]) else "FAILED"
    response["reason"] = "; ".join(v["reason"] for v in response["variants"] if v["reason"]) or None
    return validate_response(response, request)
