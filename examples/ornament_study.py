"""Task 19 serial, content-verified resumable study. No global budget changes."""
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
from math import dist, fsum, isfinite
import os
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"rhino")); sys.path.insert(0,str(ROOT/"examples")); sys.path.insert(0,str(ROOT/"tools"))
from cheshire import inspect_mesh, save_mesh
from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.ornament import OrnamentRecipe, run_ornament
from cheshire_worker import mesh_to_data, RUNTIME_IDENTITY
from subdivision_capability_study import polygon_mesh, read, write
from carrier_scale_study import extra_diagnostics
from ornament_recipes import primary_recipes
from ornament_process import bounded_worker

STUDY=ROOT/"output/task19/study"

def digest(data): return sha256(json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def file_hash(path): return sha256(Path(path).read_bytes()).hexdigest()

def operator_versions(dll):
    import compas
    names=("ornament.py","mola.py","weighted_subdivision.py","generational_subdivision.py","weighted_doosabin.py")
    return dict(COMPAS=compas.__version__,Python=sys.version,HDMola_SHA256=file_hash(dll),
        CHESHIRE={name:file_hash(ROOT/"src/cheshire"/name) for name in names})

def verified_resume(directory, request):
    path=Path(directory)/"summary.json"
    if not path.exists(): return False
    summary=read(path)
    return summary.get("status")=="SUCCESS" and summary.get("request_sha256")==digest(request) and bool(summary.get("artifacts")) and all(
        (Path(directory)/name).is_file() and file_hash(Path(directory)/name)==hash_value for name,hash_value in summary["artifacts"].items())

def distributions(mesh):
    def stats(values):
        values=sorted(values); n=len(values)
        return dict(min=values[0],p10=values[int(.1*(n-1))],median=values[(n-1)//2],p90=values[int(.9*(n-1))],max=values[-1],mean=fsum(values)/n)
    return dict(edge_length=stats([dist(mesh.vertex_coordinates(u),mesh.vertex_coordinates(v)) for u,v in mesh.edges()]),
        face_area=stats([mesh.face_area(f) for f in mesh.faces()]))

def gz_write(path,data):
    with gzip.open(path,"wt",encoding="utf-8",compresslevel=1) as stream: json.dump(data,stream,separators=(",",":"),allow_nan=False)

def initialise(dll):
    STUDY.mkdir(parents=True,exist_ok=False)
    source=read(ROOT/"studies/task18/C0.json")
    write(STUDY/"C0.json",source); save_mesh(polygon_mesh(source),STUDY/"C0.obj")
    write(STUDY/"plan.json",dict(baseline="9a948d7e34ee0113930ad771e58281850608a624",source_sha256=digest(source),
        stage_A_faces=120000,finalist_faces=250000,exceptional_faces=400000,storage_ceiling_bytes=4*1024**3,
        process_resident_ceiling_bytes=4*1024**3,worker_seconds=900,crossing_sample_faces=4096,
        screening="36 structurally varied recipes, 9 each A-D",finalists="10-12, all checkpoints",refinements="Top four, 3 each initially; <=20",
        stage_A_retention="Terminal exact polygon JSON/OBJ, compressed terminal history and events, diagnostics, matched views; no intermediate geometry",
        finalist_retention="All stage exact polygon JSON and compressed history, events and immediate vertex/face parents",
        operator_versions=operator_versions(dll)))
    for recipe in primary_recipes(): write(STUDY/"recipes"/(recipe.id+".json"),recipe.to_data())

def make_request(recipe_path,phase,dll):
    return dict(recipe=read(recipe_path),phase=phase,source_sha256=file_hash(STUDY/"C0.json"),
        mesh=read(STUDY/"C0.json"),
        operator_versions=operator_versions(dll),max_faces=120000 if phase=="A" else 250000,
        retain_checkpoints=phase!="A",mola_dll=str(Path(dll).resolve()))

def one(directory,request):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(STUDY): raise ValueError("Worker output must remain inside the current task study.")
    directory.mkdir(parents=True,exist_ok=False)
    write(directory/"request.json",request)
    write(directory/"worker_identity.json",dict(pid=os.getpid(),runtime=RUNTIME_IDENTITY))
    source=polygon_mesh(read(STUDY/"C0.json")); monitor=GateIntegrityMonitor(source)
    records=[]; started=perf_counter(); audit=[]
    def retain(mesh,history,events,anchors,parents,vertex_parents,stage):
        diagnostics=extra_diagnostics(mesh); geometry=mesh_to_data(mesh); index=stage["stage_index"]
        stage.update(statistics=inspect_mesh(mesh),diagnostics=diagnostics,distributions=distributions(mesh),
            monitor=monitor.evaluate(mesh,anchors,generation=index),geometry_sha256=digest(geometry),elapsed_seconds=perf_counter()-started)
        if request["retain_checkpoints"]:
            write(directory/f"S{index:02d}.json",geometry)
            gz_write(directory/f"S{index:02d}_lineage.json.gz",dict(history=history,events=events,
                face_parents={k:[dict(id=p.key,weight=p.weight) for p in refs] for k,refs in parents.items()},
                vertex_parents={k:[dict(id=p.key,weight=p.weight) for p in refs] for k,refs in vertex_parents.items()}))
        write(directory/"terminal.json",geometry)
        gz_write(directory/"terminal_lineage.json.gz",dict(history=history,events=events))
        record={k:v for k,v in stage.items() if k not in ("selection","events","backend")}
        if "selection" in stage: gz_write(directory/f"S{index:02d}_event.json.gz",dict(selection=stage["selection"],events=stage["events"],backend=stage["backend"]))
        records.append(record)
        write(directory/"summary.json",dict(status="RUNNING",request_sha256=digest(request),recipe=request["recipe"],stages=records,runtime_seconds=perf_counter()-started))
        # Screening audits event checkpoints and independently checks terminals.
        # Deep/refinement runs audit every stage before permitting further growth.
        if "events" in stage or request["phase"]!="A":
            sample=geometry["faces"] if len(geometry["faces"])<=4096 else [geometry["faces"][i*len(geometry["faces"])//4096] for i in range(4096)]
            used={v for f in sample for v in f["vertices"]}
            write(directory/"response.json",dict(variants=[dict(id=f"S{index:02d}",mesh=dict(vertices=[v for v in geometry["vertices"] if v["id"] in used],faces=sample))]))
            result=bounded_worker([ROOT/"tools/morphology_crossings.py",directory],directory/f"crossing_S{index:02d}",60)
            write(directory/f"crossing_S{index:02d}/process.json",result)
            if result["exit_code"]: raise ValueError("Crossing diagnostic failed; no further growth.")
            crossing=read(directory/"crossing_audit.json"); write(directory/f"S{index:02d}_crossings.json",crossing)
            if any(r["sample_limit_reached"] for r in crossing["candidates"]):
                raise ValueError("Severe sampled crossing cap reached; no further growth.")
        print(request["recipe"]["id"],index,stage["stage"]["operator"],mesh.number_of_faces(),stage["ornament"]["maximum"],round(perf_counter()-started,2),flush=True)
        if diagnostics["degenerate_fan_faces"]: raise ValueError("Degenerate fan faces; checkpoint retained without repair.")
    result=run_ornament(source,OrnamentRecipe.from_data(request["recipe"]),dll_path=request["mola_dll"],
        budget=ExecutionBudget(request["max_faces"],request["max_faces"]*2,32),publish=retain)
    mesh=result["mesh"]; save_mesh(mesh,directory/"terminal.obj")
    if not (directory/"terminal.json").exists(): write(directory/"terminal.json",mesh_to_data(mesh))
    if request["retain_checkpoints"]: write(directory/"S00.json",mesh_to_data(source))
    artifacts={p.name:file_hash(p) for p in directory.iterdir() if p.is_file() and p.name not in ("summary.json","response.json","crossing_audit.json")}
    summary=dict(status=result["status"],reason=result["reason"],request_sha256=digest(request),recipe=request["recipe"],
        stages=records,attempted_stages=[{k:v for k,v in r.items() if k in ("stage","failure","stage_index")} for r in result["stages"]],
        runtime_seconds=perf_counter()-started,source_immutable=result["source_immutable"],artifacts=artifacts,
        output_sha256=digest(mesh_to_data(mesh)))
    write(directory/"summary.json",summary)

def execute(ids,phase,dll):
    for name in ids:
        if sum(p.stat().st_size for p in STUDY.rglob("*") if p.is_file())>4*1024**3: raise ValueError("Task-local storage ceiling reached.")
        recipe=STUDY/"recipes"/(name+".json"); request=make_request(recipe,phase,dll)
        root=STUDY/phase/name
        attempts=sorted(root.glob("attempt_*")) if root.exists() else []
        if any(verified_resume(path,request) for path in attempts):
            print(name,"RESUME verified, skipped",flush=True); continue
        directory=root/f"attempt_{len(attempts)+1:03d}"
        request_path=STUDY/"requests"/phase/(name+".json"); write(request_path,request)
        process=bounded_worker([Path(__file__).resolve(),"--one",directory,"--request",request_path,"--study",STUDY],
            STUDY/"logs"/phase/f"{name}_{directory.name}",900)
        if not (directory/"summary.json").exists(): write(directory/"summary.json",dict(status="FAILED",stages=[],reason=process))
        summary=read(directory/"summary.json"); summary["process"]=process
        if process["exit_code"]: summary.update(status="PROCESS_STOP",reason=process["stop"] or "Worker exception; see stderr")
        write(directory/"summary.json",summary)
        print(name,summary["status"],summary.get("reason"),round(process["seconds"],2),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--init",action="store_true"); parser.add_argument("--run",nargs="+")
    parser.add_argument("--phase",choices=("A","B","R","E","REPLAY"),default="A"); parser.add_argument("--dll",type=Path)
    parser.add_argument("--one",type=Path); parser.add_argument("--request",type=Path); parser.add_argument("--study",type=Path,default=STUDY)
    args=parser.parse_args(); STUDY=args.study.resolve()
    if not STUDY.is_relative_to(ROOT/"output/task19"): parser.error("Output must stay inside output/task19")
    if args.one: one(args.one,read(args.request))
    elif args.init: initialise(args.dll)
    elif args.run: execute(args.run,args.phase,args.dll)
    else: parser.error("Choose --init, --run or --one")
