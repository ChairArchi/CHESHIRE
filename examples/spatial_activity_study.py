"""Frozen source fields, bounded serial workers and resumable Task 18 cases.

--init freezes fields before morphology; --run A screens the fixed matrix.
--run B --cases <Stage-A IDs> deepens declared informative cases.
"""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from math import dist, fsum
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"rhino")); sys.path.insert(0, str(ROOT/"examples"))
from cheshire.activity import ActivityField, diffuse, distance_values, distances, field_statistics, lerp_weight, peak_normalize, scale_at, source_graph
from cheshire.activity_diagnostics import hierarchy_diagnostics
from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.weighted_doosabin import weighted_doosabin_once, SUFFIX
from cheshire import inspect_mesh, save_mesh
from cheshire_worker import mesh_to_data, RUNTIME_IDENTITY
from generational_study import BEST_SCHEDULE, choreographies
from subdivision_capability import refinements
from subdivision_capability_study import read, write, polygon_mesh
from weighted_subdivision_study import bounded_child
from carrier_scale_study import extra_diagnostics

FROZEN = ROOT/"studies/task18"
STUDY = ROOT/"output/task18/study"
BASELINE = "ec5c3bcd0efd9aac08dfe4a6a813ab2aaf35ce20"
STORAGE_BUDGET = 2*1024**3
SEEDS = {"A_SHOULDER_PAIR": (6, 7, 9, 10),
         "B_FOUR_CORNER_FRAME": (0, 3, 6, 7, 9, 10, 12, 13),
         "C_UPPER_BIAS": (18, 19, 20, 21)}
TIMES = {"BROAD": 12, "MEDIUM": 4, "FINE": 1}


def digest(data):
    canonical = json.loads(json.dumps(data, allow_nan=False))
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def directory_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())


def exact_recipes():
    cc = deepcopy(choreographies()[BEST_SCHEDULE]["schedule"])
    ds = deepcopy(refinements()["R15_restrained_edge_frames"]["schedule"])
    hybrid = cc[:3]+deepcopy(refinements()["R13_restrained_insets"]["schedule"])[3:]
    return {"CC": cc, "DS": ds, "HYBRID": hybrid}


def initialise():
    if (FROZEN/"fields.json").exists():
        raise ValueError("Frozen definitions already exist; do not retune seeds after review.")
    source = read(ROOT/"output/task17/study/C0.json")
    mesh = polygon_mesh(source); graph = source_graph(mesh)
    FROZEN.mkdir(parents=True, exist_ok=True); STUDY.mkdir(parents=True, exist_ok=True)
    write(FROZEN/"C0.json", source)
    layouts = {}
    for name, ids in SEEDS.items():
        initial = {v: float(v in ids) for v in graph}; d = distances(graph, ids)
        fields = {scale: peak_normalize(diffuse(graph, initial, rate=.5, iterations=time)) for scale, time in TIMES.items()}
        fields["DISTANCE"] = distance_values(graph, ids, radius=3)
        stats = {name: field_statistics(values, d) for name, values in fields.items()}
        if not stats["FINE"]["distance_weighted_spread"] < stats["MEDIUM"]["distance_weighted_spread"] < stats["BROAD"]["distance_weighted_spread"]:
            raise ValueError("Diffusion scales not separated on the frozen topology.")
        layouts[name] = dict(source_vertex_ids=list(ids), source_coordinates=[dict(id=v, xyz=mesh.vertex_coordinates(v)) for v in ids],
            initial=initial, distances=d, fields=fields, statistics=stats,
            field_hashes={name: digest(values) for name, values in fields.items()})
    fields = dict(baseline=BASELINE, source_hash=digest(source), representation="C0 vertex adjacency graph; unweighted hop distance",
        graph=graph, layouts=layouts, diffusion_rate=.5, iterations=TIMES,
        normalization="Divide final nonnegative diffusion values by maximum (peak=1); differing total mass is reported, not concealed",
        distance_radius=3, schedule_phases="G1 early; G2/G3 middle; G4+ late",
        seed_policy="Explicit synthetic IDs frozen before morphology review; no architectural significance",
        quiet_values="All implemented CC wf/w1/we/w2/wp/w3/w4 and DS family w1/w10 standard values are zero")
    write(FROZEN/"fields.json", fields); write(FROZEN/"recipes.json", exact_recipes())
    write(STUDY/"inputs.json", dict(storage_budget_bytes=STORAGE_BUDGET, worker_seconds=120, audit_seconds=30,
        resident_cap_bytes=4*1024**3, max_vertices=120000, max_faces=120000, max_generation=6,
        stage_A_generations=4, cc_deep_generation=5, cc_G6="Unavailable: the unchanged C11 schedule has only five explicit rows",
        fields_hash=digest(fields), runtime_identity=RUNTIME_IDENTITY,
        storage_policy="A: terminal OBJ, JSON previews G0-G4; B: all checkpoint OBJ/JSON. No A intermediate OBJ.",
        parallelism="Serial isolated workers; deterministic case order; no threads or shared geometry state"))
    cases = []
    for seed in SEEDS:
        for grammar in ("CC", "DS", "HYBRID"):
            for strategy in ("U", "S", "M", "R", "P"):
                cases.append(case_spec("A", seed, grammar, strategy, 4))
    for grammar in ("CC", "DS", "HYBRID"):
        cases.append(case_spec("A", "A_SHOULDER_PAIR", grammar, "D", 4))
    write(STUDY/"matrix_A.json", cases)
    print(json.dumps({name: {s: round(r["distance_weighted_spread"], 4) for s, r in data["statistics"].items()} for name, data in layouts.items()}))


def case_spec(stage, seed, grammar, strategy, generations):
    fields = read(FROZEN/"fields.json"); recipes = read(FROZEN/"recipes.json")
    return dict(id=f"{stage}_{seed}_{grammar}_{strategy}", stage=stage, seed=seed, grammar=grammar, strategy=strategy,
        generations=generations, schedule=recipes[grammar][:generations],
        fields_hash=digest(fields), source_hash=fields["source_hash"],
        field_assignments=[scale_at(strategy, g) for g in range(1, generations+1)],
        source_field_hashes=fields["layouts"][seed]["field_hashes"],
        implementation_hash=implementation_hash(),
        budget=dict(max_vertices=120000, max_faces=120000, max_generation=6),
        scaling="Normal-extrusion ratio times global mean current input edge length; interpolation unchanged")


def implementation_hash():
    paths = ["src/cheshire/activity.py", "src/cheshire/activity_diagnostics.py",
        "src/cheshire/generational_subdivision.py", "src/cheshire/weighted_subdivision.py",
        "src/cheshire/weighted_doosabin.py", "examples/spatial_activity_study.py"]
    return digest({name: hashlib.sha256((ROOT/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in paths})


def modulation(mesh, field, weights, scheme, families=None):
    """Activity -> existing parameters. Missing coverage is a technical stop."""
    if any(field.vertex(v) is None for v in mesh.vertices()):
        raise ValueError("Unavailable descendant activity; do not invent source ancestry.")
    if scheme == "CC":
        points = {"face": {}, "edge": {}, "corner": {}}
        later = {}
        for f in mesh.faces():
            phi = field.face(mesh, f)
            points["face"][f] = {"wf": lerp_weight(0, weights["wf"], phi)}
            later[f] = {k: lerp_weight(0, weights[k], phi) for k in ("w3", "w4")}
        for edge in mesh.edges():
            points["edge"][edge] = {k: lerp_weight(0, weights[k], field.edge(edge)) for k in ("w1", "we")}
        for v in mesh.vertices():
            points["corner"][v] = {k: lerp_weight(0, weights[k], field.vertex(v)) for k in ("w2", "wp")}
        return dict(point_weights=points, face_weights=later)
    pairs = {}
    for f in mesh.faces():
        suffix = SUFFIX[families[f]["class"]] if families else "face"
        pairs[f] = {k: lerp_weight(0, weights[k+"_"+suffix], field.face(mesh, f)) for k in ("w1", "w10")}
    return dict(face_weights=pairs)


def run_case(spec, *, publish=None):
    frozen = read(FROZEN/"fields.json"); original = read(FROZEN/"C0.json")
    if spec["source_hash"] != digest(original) or spec["fields_hash"] != digest(frozen):
        raise ValueError("Frozen source/fields changed.")
    if spec["implementation_hash"] != implementation_hash():
        raise ValueError("Study implementation changed; an exact new request is required.")
    source = polygon_mesh(original); mesh = source; before = deepcopy(source.__data__)
    layout = frozen["layouts"][spec["seed"]]
    bank = {name: ActivityField(name, {int(v): x for v, x in data.items()}) for name, data in layout["fields"].items()}
    # Three sparse source region indicators are propagated separately for
    # readable persistence. No architectural or categorical tag is invented.
    indicators = {name: ActivityField(name, {v: float(v in ids) for v in source.vertices()}) for name, ids in SEEDS.items()}
    anchors = {v: v for v in source.vertices()}; monitor = GateIntegrityMonitor(source)
    origins = None; families = None; active = None; records = []
    budget = ExecutionBudget(**spec["budget"])
    if publish:
        publish(mesh, dict(generation=0, statistics=inspect_mesh(mesh), geometry_hash=digest(mesh_to_data(mesh)),
            monitor=monitor.evaluate(mesh, anchors, generation=0), source_coverage=1.0), bank)
    started = perf_counter()
    for generation, ratios in enumerate(spec["schedule"], 1):
        scale = fsum(dist(mesh.vertex_coordinates(u), mesh.vertex_coordinates(v)) for u, v in mesh.edges())/mesh.number_of_edges()
        scheme = "CC" if spec["grammar"] == "CC" or (spec["grammar"] == "HYBRID" and generation <= 3) else "DS"
        weights = {k: value*scale if k in ("wf", "we", "wp") or k.startswith("w10_") else value for k, value in ratios.items()}
        name = scale_at(spec["strategy"], generation)
        field = ActivityField("UNIFORM", {v: 1.0 for v in mesh.vertices()}) if name == "UNIFORM" else bank[name]
        local = modulation(mesh, field, weights, scheme, families)
        if scheme == "CC":
            step = generational_subdivide_once(mesh, weights, origin_lineage=origins, budget=budget,
                current_generation=generation-1, **local)
            origins = step.origin_lineage; parents = step.sampling_parents
            next_anchors = {v: anchors.get(v) for v in step.mesh.vertices()}
        else:
            step = weighted_doosabin_once(mesh, weights, face_families=families, budget=budget,
                current_generation=generation-1, **local)
            families = step.face_families; parents = step.lineage.vertex_parents
            next_anchors = {v: anchors.get(p) for v, p in step.corner_parents.items()}
        bank = {k: field.inherited(parents) for k, field in bank.items()}
        indicators = {k: field.inherited(parents) for k, field in indicators.items()}
        diagnostics, active = hierarchy_diagnostics(mesh, step.mesh, parents,
            {k: f.values for k, f in indicators.items()}, previous_active=active)
        warnings = extra_diagnostics(step.mesh)
        local_data = (dict(point_weights={kind: [[list(key) if isinstance(key, tuple) else key, row] for key, row in rows.items()]
                        for kind, rows in local["point_weights"].items()},
                        face_weights=list(local["face_weights"].items())) if scheme == "CC" else
                      dict(face_weights=list(local["face_weights"].items())))
        record = dict(generation=generation, scheme=scheme, activity_scale=name,
            input_activity=field_statistics(field.values), propagated_field_hashes={k: digest(dict(f.values)) for k, f in bank.items()},
            source_coverage=min(sum(x is not None for x in f.values.values())/len(f.values) for f in bank.values()),
            statistics=inspect_mesh(step.mesh), ratios=ratios, global_mean_edge_length=scale, weights=weights,
            local_weight_semantics="CC face mean / edge endpoint mean / corner scalar; DS input-face mean selects current family pair",
            local_weight_hash=digest(local_data),
            hierarchy=diagnostics, monitor=monitor.evaluate(step.mesh, next_anchors, generation=generation),
            diagnostics=warnings, fallback_faces=step.metadata.get("fallback_faces", 0),
            fallback_groups=step.metadata.get("fallback_groups", []),
            geometry_hash=digest(mesh_to_data(step.mesh)), checkpoint_elapsed_seconds=perf_counter()-started)
        if publish:
            publish(step.mesh, record, bank)
        records.append(record); mesh, anchors = step.mesh, next_anchors
    if source.__data__ != before:
        raise AssertionError("Source mutated.")
    return dict(status="SUCCESS", stages=records, generations_reached=len(records), source_immutable=True,
        elapsed_seconds=perf_counter()-started, semantic_lineage="Only scalar activity inherits positive existing sampling associations; architectural/categorical lineage NOT IMPLEMENTED")


def valid_completed(directory, spec):
    """Resume only content-verified exact requests with complete geometry."""
    try:
        request = read(directory/"request.json"); result = read(directory/"summary.json")
        if request["spec"] != spec or result["status"] != "SUCCESS" or result["generations_reached"] != spec["generations"]:
            return False
        if not (directory/"crossing_audit.json").is_file():
            return False
        if [r["generation"] for r in result["stages"]] != list(range(spec["generations"]+1)):
            return False
        audit = read(directory/"crossing_audit.json")
        if [r["id"] for r in audit["candidates"]] != [f"G{g}" for g in range(1, spec["generations"]+1)]:
            return False
        if not (directory/f"G{spec['generations']}.obj").is_file():
            return False
        for record in result["stages"]:
            if digest(read(directory/f"G{record['generation']}.json")) != record["geometry_hash"]:
                return False
            if record["generation"]:
                with gzip.open(directory/f"G{record['generation']}_fields.json.gz", "rt", encoding="utf-8") as stream:
                    channels = json.load(stream)
                if {k: digest(v) for k, v in channels.items()} != record["propagated_field_hashes"]:
                    return False
        return True
    except (OSError, ValueError, KeyError):
        return False


def one(spec, directory):
    directory.mkdir(parents=True, exist_ok=False)
    original = read(FROZEN/"C0.json")
    write(directory/"request.json", dict(mesh=original, spec=spec, runtime_identity=RUNTIME_IDENTITY))
    records = []; samples = []
    def retain(mesh, record, bank):
        generation = record["generation"]; data = mesh_to_data(mesh)
        write(directory/f"G{generation}.json", data)
        if spec["stage"] != "A" or generation == spec["generations"]:
            save_mesh(mesh, directory/f"G{generation}.obj")
        if generation:
            # Compressed descendant field values, without duplicating huge
            # standard metadata for every point. Immediate parents are the
            # existing deterministic operator, with frozen code/recipe hashes.
            with gzip.open(directory/f"G{generation}_fields.json.gz", "wt", encoding="utf-8", compresslevel=1) as stream:
                json.dump({k: dict(f.values) for k, f in bank.items()}, stream, separators=(",", ":"), allow_nan=False)
            faces = data["faces"]; sampled = faces if len(faces)<=4096 else [faces[i*len(faces)//4096] for i in range(4096)]
            used = {v for f in sampled for v in f["vertices"]}
            samples.append(dict(id=f"G{generation}", mesh=dict(vertices=[v for v in data["vertices"] if v["id"] in used], faces=sampled)))
        records.append(record)
        write(directory/"response.json", dict(variants=samples, geometry_hashes={f"G{r['generation']}": r["geometry_hash"] for r in records},
            field_scope="Source graph activity inherited only through positive documented sampling parents; crossing meshes are <=4096 actual-face samples"))
        write(directory/"summary.json", dict(status="PARTIAL", spec=spec, stages=records, generations_reached=generation))
        print(spec["id"], f"G{generation}", mesh.number_of_faces(), flush=True)
    try:
        result = run_case(spec, publish=retain)
        result["stages"] = records; result["spec"] = spec
        write(directory/"summary.json", result)
    except Exception as error:
        write(directory/"failure.json", dict(type=type(error).__name__, reason=str(error), generations_reached=records[-1]["generation"] if records else 0))
        raise


def execute(stage, names):
    if stage == "A":
        cases = read(STUDY/"matrix_A.json")
    else:
        source_specs = {r["id"]: r for r in read(STUDY/"matrix_A.json")}
        if not names:
            raise ValueError("Declare informative Stage-B source IDs after inspecting Stage A.")
        cases = [case_spec("B", source_specs[name]["seed"], source_specs[name]["grammar"], source_specs[name]["strategy"],
                  5 if source_specs[name]["grammar"]=="CC" else 6) for name in names]
        path = STUDY/"matrix_B.json"
        if path.exists() and read(path) != cases:
            raise ValueError("Do not change a started deep matrix.")
        write(path, cases)
    for spec in cases:
        if stage=="A" and names and spec["id"] not in names:
            continue
        if directory_bytes(STUDY)>STORAGE_BUDGET:
            raise ValueError("Task-local storage budget exhausted; prior evidence preserved.")
        directory = STUDY/"cases"/spec["id"]; logs = STUDY/"logs"/spec["id"]
        if valid_completed(directory, spec):
            print(spec["id"], "RESUMED content-verified", flush=True); continue
        if directory.exists():
            # Preserve interrupted evidence instead of deleting/overwriting it.
            attempt = 1
            while (STUDY/"interrupted"/f"{spec['id']}_{attempt}").exists(): attempt += 1
            destination = STUDY/"interrupted"/f"{spec['id']}_{attempt}"; destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(directory), str(destination))
        write(STUDY/"requests"/(spec["id"]+".json"), spec)
        process = bounded_child([str(Path(__file__).resolve()), "--study", str(STUDY), "--one", spec["id"]], logs, 120)
        write(logs/"process.json", process); print(spec["id"], process, flush=True)
        if (directory/"response.json").is_file():
            audit = bounded_child([str(ROOT/"tools/morphology_crossings.py"), str(directory)], logs/"audit", 30)
            write(logs/"audit/process.json", audit)
            print("audit", spec["id"], audit, flush=True)
        if process["exit_code"]:
            print((logs/"stderr.txt").read_text(), flush=True)
    write(STUDY/"storage.json", dict(actual_bytes=directory_bytes(STUDY), budget_bytes=STORAGE_BUDGET))


def main():
    global STUDY
    parser = argparse.ArgumentParser(); parser.add_argument("--init", action="store_true")
    parser.add_argument("--run", choices=("A", "B")); parser.add_argument("--cases", nargs="*")
    parser.add_argument("--one"); parser.add_argument("--study", type=Path, default=STUDY)
    args = parser.parse_args(); STUDY = args.study.resolve()
    if not STUDY.is_relative_to(ROOT/"output/task18"):
        raise ValueError("Task-local study directory required.")
    if args.init: initialise()
    if args.one:
        one(read(STUDY/"requests"/(args.one+".json")), STUDY/"cases"/args.one)
    if args.run: execute(args.run, args.cases)


if __name__ == "__main__":
    main()
