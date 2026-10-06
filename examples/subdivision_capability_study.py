"""Serial bounded Task 17 study, exact polygons and per-generation evidence.

Examples (repository .venv): --init; --run DS_STANDARD U01_early_expansion;
--run F05_face_mass; --run HYBRID_A --hybrid 2 --recipe <selected JSON>.
No schedule overwrite, optimizer or gate-integrity feedback.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"rhino")); sys.path.insert(0,str(ROOT/"examples"))
from compas.datastructures import Mesh
from cheshire import inspect_mesh,save_mesh,load_mesh
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.weighted_doosabin import STANDARD
from cheshire_worker import mesh_to_data,RUNTIME_IDENTITY
from subdivision_capability import schedules,refinements,run_capability
from carrier_scale_study import extra_diagnostics
from weighted_subdivision_study import bounded_child

STUDY=ROOT/"output/task17/study"
BASELINE="bba4fd7d6e3a2af8c87c91fb9aeec70c4cd37b7b"


def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(data,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
    temporary.replace(path)


def polygon_mesh(data):
    """Saved experimental polygons, preserving IDs/cycles; no triangulation."""
    mesh=Mesh()
    for vertex in data["vertices"]:
        x,y,z=vertex["xyz"]; mesh.add_vertex(key=vertex["id"],x=x,y=y,z=z)
    for face in data["faces"]:
        mesh.add_face(face["vertices"],fkey=face["id"])
    if mesh_to_data(mesh)!=data:
        raise ValueError("COMPAS changed saved polygon topology.")
    return mesh


def initialise():
    task16=ROOT/"output/task16/study"
    evidence=ROOT/"output/task17/study"
    source_path=task16/"C0.json" if (task16/"C0.json").is_file() else evidence/"C0.json"
    reference=task16/"cases/C11_interpolation_release" if (task16/"cases/C11_interpolation_release/G5.json").is_file() else evidence/"cases/C11_REFERENCE"
    STUDY.mkdir(parents=True,exist_ok=False)
    source=read(source_path)
    write(STUDY/"C0.json",source); save_mesh(polygon_mesh(source),STUDY/"C0.obj")
    write(STUDY/"inputs.json",dict(baseline=BASELINE,runtime_identity=RUNTIME_IDENTITY,
        source_sha256=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),source=inspect_mesh(polygon_mesh(source)),
        limits=dict(vertices=120000,faces=120000,generations=6,worker_seconds=60,audit_seconds=30,resident_bytes=4*1024**3,storage_bytes=3*1024**3),
        global_budget_unchanged=True,scaling="w10 ratio * global mean current INPUT edge length, along unit COMPAS current face normal; CHESHIRE choice",
        monitor="Read-only primary-corner descendant landmarks; no geometry feedback, gate score or threshold.",
        semantic_lineage="NOT IMPLEMENTED",reference="https://doi.org/10.2312/COMPAESTH/COMPAESTH10/075-081"))
    cases={"DS_STANDARD":dict(schedule=[STANDARD.copy() for _ in range(6)],kind="control",intention="Trusted standard DS topology/rounding control."),**schedules()}
    for name,recipe in cases.items(): write(STUDY/"recipes"/(name+".json"),recipe)
    # Exact existing C11 control; no CC search, no changed weights.
    control=STUDY/"cases/C11_REFERENCE"; control.mkdir(parents=True)
    monitor=GateIntegrityMonitor(polygon_mesh(source)); records=[]
    for generation in range(6):
        for suffix in ("json","obj"):
            shutil.copyfile(reference/f"G{generation}.{suffix}",control/f"G{generation}.{suffix}")
        mesh=polygon_mesh(read(control/f"G{generation}.json"))
        records.append(dict(generation=generation,statistics=inspect_mesh(mesh),monitor=monitor.evaluate(mesh,{v:v for v in monitor.xyz},generation=generation),
            geometry="Exact Task16 C11 output copied; only original retained corners monitored, later edge/face points unassociated."))
    from generational_study import choreographies,BEST_SCHEDULE
    write(control/"summary.json",dict(status="REFERENCE",stages=records,recipe=choreographies()[BEST_SCHEDULE],
        original_directory="output/task16/study/cases/C11_interpolation_release",no_new_CC_schedule=True))
    for filename in ("summary.json","crossing_audit.json"):
        prior=reference/filename if reference.parent.name=="cases" and reference.name=="C11_interpolation_release" else reference/("task16_original_"+filename)
        shutil.copyfile(prior,control/("task16_original_"+filename))


def one(directory,recipe_path,hybrid):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=False)
    recipe=read(recipe_path); source=polygon_mesh(read(STUDY/"C0.json")); original=mesh_to_data(source)
    write(directory/"request.json",dict(mesh=original,baseline=BASELINE,recipe=recipe,cc_prefix=hybrid,runtime_identity=RUNTIME_IDENTITY))
    write(directory/"G0.json",original); save_mesh(source,directory/"G0.obj")
    monitor=GateIntegrityMonitor(source)
    records=[dict(generation=0,statistics=inspect_mesh(source),monitor=monitor.evaluate(source,{v:v for v in source.vertices()},generation=0))]
    write(directory/"summary.json",dict(status="PARTIAL",recipe=recipe,cc_prefix=hybrid,stages=records,generations_reached=0))
    started=perf_counter(); audit=[]
    def retain(mesh,stage):
        generation=stage["generation"]; data=mesh_to_data(mesh)
        diagnostics=extra_diagnostics(mesh)
        write(directory/f"G{generation}.json",data); save_mesh(mesh,directory/f"G{generation}.obj")
        reloaded=load_mesh(directory/f"G{generation}.obj"); keys=list(mesh.vertices()); index={v:i for i,v in enumerate(keys)}
        assert [reloaded.vertex_coordinates(v) for v in reloaded.vertices()]==[mesh.vertex_coordinates(v) for v in keys]
        assert [reloaded.face_vertices(f) for f in reloaded.faces()]==[[index[v] for v in mesh.face_vertices(f)] for f in mesh.faces()]
        stage["diagnostics"]=diagnostics; stage["OBJ_roundtrip"]="PASS exact ordered coordinates and polygon cycles"
        with gzip.open(directory/f"G{generation}_lineage.json.gz","wt",encoding="utf-8",compresslevel=1) as stream:
            json.dump(stage,stream,separators=(",",":"),allow_nan=False)
        record={k:v for k,v in stage.items() if k not in ("metadata","face_families","corner_parents","lineage","cc_origin_lineage","sampling_parents")}
        record["statistics"]=inspect_mesh(mesh)
        record["checkpoint_elapsed_seconds"]=perf_counter()-started
        record["family_counts"]=stage["metadata"].get("family_counts",{})
        record["fallback_faces"]=stage["metadata"].get("fallback_faces",0)
        record["fallback_groups"]=stage["metadata"].get("fallback_groups",[])
        records.append(record)
        # Existing crossing diagnostic on an explicit evenly spaced face sample,
        # bounded independently. This is not a whole-mesh collision certificate.
        sample=data["faces"] if len(data["faces"])<=4096 else [data["faces"][i*len(data["faces"])//4096] for i in range(4096)]
        used={v for face in sample for v in face["vertices"]}
        audit.append(dict(id=f"G{generation}",mesh=dict(vertices=[v for v in data["vertices"] if v["id"] in used],faces=sample)))
        write(directory/"response.json",dict(variants=audit,sample_scope="At most 4096 evenly spaced actual faces per generation, no geometry changes."))
        write(directory/"summary.json",dict(status="PARTIAL",recipe=recipe,cc_prefix=hybrid,stages=records,generations_reached=generation,
            source_immutable=mesh_to_data(source)==original,semantic_lineage="NOT IMPLEMENTED"))
        print(directory.name,"G"+str(generation),record["statistics"]["face_count"],round(record["checkpoint_elapsed_seconds"],2),flush=True)
        if diagnostics["degenerate_fan_faces"]:
            raise ValueError("Degenerate diagnostic fan faces; checkpoint retained without repair.")
    result=run_capability(source,recipe["schedule"],cc_prefix=hybrid,publish=retain)
    write(directory/"summary.json",dict(status=result["status"],reason=result["reason"],recipe=recipe,cc_prefix=hybrid,stages=records,
        generations_reached=records[-1]["generation"],source_immutable=result["source_immutable"],semantic_lineage="NOT IMPLEMENTED",
        elapsed_seconds=perf_counter()-started))


def execute(names,hybrid=0,recipe_path=None):
    for name in names:
        path=STUDY/"cases"/name
        if path.exists(): raise ValueError("Existing attempt preserved: "+str(path))
        if sum(p.stat().st_size for p in STUDY.rglob("*") if p.is_file())>=3*1024**3:
            raise ValueError("Study storage ceiling reached.")
        recipe=Path(recipe_path) if recipe_path else STUDY/"recipes"/(name+".json")
        if not recipe.exists() and name in refinements():
            write(recipe,refinements()[name])
        process=bounded_child([str(Path(__file__).resolve()),"--study",str(STUDY),"--one",str(path),"--recipe",str(recipe),"--hybrid",str(hybrid)],STUDY/"logs"/name,60)
        write(STUDY/"logs"/name/"process.json",process)
        summary=read(path/"summary.json") if (path/"summary.json").exists() else dict(stages=[],generations_reached=0)
        if process["exit_code"]:
            summary.update(status="PARTIAL" if summary["stages"] else "FAILED",reason=process["stop"] or "Worker exception; see stderr.txt")
            write(path/"summary.json",summary)
        print(name,summary.get("status"),summary.get("generations_reached"),process,flush=True)
        if (path/"response.json").exists():
            audit=bounded_child([str(ROOT/"tools/morphology_crossings.py"),str(path)],STUDY/"logs"/(name+"_crossings"),30)
            write(STUDY/"logs"/(name+"_crossings")/"process.json",audit)
            print(name,"crossings",audit,flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--init",action="store_true"); parser.add_argument("--run",nargs="+")
    parser.add_argument("--one",type=Path); parser.add_argument("--recipe",type=Path); parser.add_argument("--hybrid",type=int,default=0)
    parser.add_argument("--study",type=Path,default=STUDY)
    args=parser.parse_args()
    # A fresh task-local output path permits reproduction without overwriting evidence.
    STUDY=(ROOT/args.study).resolve()
    if not STUDY.is_relative_to((ROOT/"output/task17").resolve()):
        parser.error("Study output must remain within this repository's output/task17.")
    if args.init: initialise()
    elif args.one: one(args.one,args.recipe,args.hybrid)
    elif args.run: execute(args.run,args.hybrid,args.recipe)
    else: parser.error("Choose --init, --run or --one.")
