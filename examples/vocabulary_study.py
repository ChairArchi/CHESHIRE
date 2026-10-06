"""Task-21 isolated, serial and resumable vocabulary sandbox."""
import argparse
from collections import Counter
import gzip
import json
from math import acos,degrees,fsum
import os
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
for folder in ("rhino","examples","tools"): sys.path.insert(0,str(ROOT/folder))
from cheshire import inspect_mesh,save_mesh
from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.vocabulary import VocabularyRecipe as BranchingRecipe,run_vocabulary as run_branching
from cheshire.branching import content_hash
from cheshire_worker import mesh_to_data,RUNTIME_IDENTITY
from subdivision_capability_study import read,write,polygon_mesh
from carrier_scale_study import extra_diagnostics
from ornament_study import digest,file_hash,verified_resume,distributions,operator_versions,gz_write
from branching_process import bounded_worker
from vocabulary_recipes import pure_recipes as primary_recipes,references

STUDY=ROOT/"output/task21/study"
SCREEN_PHASES={"A","B","C"}


def versions(dll):
    data=operator_versions(dll)
    data["CHESHIRE"]["branching.py"]=file_hash(ROOT/"src/cheshire/branching.py")
    data["CHESHIRE"]["vocabulary.py"]=file_hash(ROOT/"src/cheshire/vocabulary.py")
    data["study_driver"]=file_hash(Path(__file__))
    data["worker_guard"]=file_hash(ROOT/"tools/branching_process.py")
    return data


def normal_variation(mesh):
    normals={f:mesh.face_normal(f) for f in mesh.faces()}; angles=[]
    for u,v in mesh.edges():
        a,b=mesh.halfedge[u][v],mesh.halfedge[v][u]
        if a is not None and b is not None:
            angles.append(degrees(acos(max(-1,min(1,fsum(x*y for x,y in zip(normals[a],normals[b])))))))
    angles.sort(); n=len(angles)
    return dict(mean=fsum(angles)/n if n else None,median=angles[n//2] if n else None,p90=angles[int(.9*(n-1))] if n else None,max=max(angles,default=None),units="degrees between adjacent COMPAS face normals")


def initialise(dll):
    STUDY.mkdir(parents=True,exist_ok=False)
    source=read(ROOT/"studies/task19/C0.json"); write(STUDY/"C0.json",source)
    base=references()["C07"]
    frozen=read(ROOT/"studies/task20/backbone.json")
    if frozen["recipe"]!=base: raise ValueError("Frozen Task-19 recipe mismatch.")
    write(STUDY/"backbone.json",frozen)
    write(STUDY/"plan.json",dict(baseline="9afa414eca1353a7678432538902f55d87edcd41",screen_faces=150000,deep_faces=300000,
        optional_production_faces=750000,storage_ceiling_bytes=6*1024**3,worker_seconds=900,operators=versions(dll),
        screen="20 pure vocabulary cases; B/C compositions frozen after actual Phase-A review",finish="NONE; intermediate subdivision must prepare meaningful structure",
        retention="A/B/C terminal only; F/R/HERO full downstream checkpoints plus shared frozen prefix"))
    for recipe in primary_recipes(): write(STUDY/"recipes"/(recipe.id+".json"),recipe.to_data())
    refs=references()
    paths={"C07":"references/C07.json","A03":"R/F_A03_CONTRAST/attempt_001/terminal.json","D02":"R/F_D02_CONTRAST/attempt_001/terminal.json","HERO":"B/HERO_ROLE_ASSEMBLY/attempt_001/terminal.json"}
    for label,path in paths.items():
        actual=ROOT/"output/task20/study"/path
        if actual.exists(): write(STUDY/"references"/(label+".json"),read(actual))
        write(STUDY/"references"/(label+"_recipe.json"),refs[label])
    import shutil
    if (ROOT/"output/task20/study/backbone_crossing_check").exists():
        shutil.copytree(ROOT/"output/task20/study/backbone_crossing_check",STUDY/"backbone_crossing_check")
    write(STUDY/"references/C0.json",source)
    # Common exact geometry is included once, not copied into each finalist.
    # Shared prefix geometry/lineage is created once by the first exact worker;
    # a fresh source checkout needs no previous large Task-19 output directory.


def make_request(path,phase,dll):
    return dict(recipe=read(path),phase=phase,mesh=read(STUDY/"C0.json"),input_sha256=file_hash(STUDY/"C0.json"),
        operator_versions=versions(dll),max_faces=150000 if phase in SCREEN_PHASES else 750000 if phase=="PRODUCTION" else 300000,
        retain_checkpoints=phase not in SCREEN_PHASES,mola_dll=str(Path(dll).resolve()),backbone=read(STUDY/"backbone.json"))


def crossing(directory,geometry,label):
    directory.mkdir(parents=True,exist_ok=True)
    sample=geometry["faces"] if len(geometry["faces"])<=4096 else [geometry["faces"][i*len(geometry["faces"])//4096] for i in range(4096)]
    used={v for f in sample for v in f["vertices"]}
    write(directory/"request.json",dict(mesh=read(STUDY/"C0.json")))
    write(directory/"response.json",dict(variants=[dict(id=label,mesh=dict(vertices=[v for v in geometry["vertices"] if v["id"] in used],faces=sample))]))
    process=bounded_worker([ROOT/"tools/morphology_crossings.py",directory],directory/"logs",90)
    write(directory/"process.json",process)
    if process["exit_code"]: raise ValueError("Crossing diagnostic failed; no further growth.")
    return read(directory/"crossing_audit.json")["candidates"][0]


def one(directory,request):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(STUDY): raise ValueError("Output must remain inside Task 21 study.")
    directory.mkdir(parents=True,exist_ok=False); write(directory/"request.json",request)
    write(directory/"worker_identity.json",dict(pid=os.getpid(),runtime=RUNTIME_IDENTITY))
    source=polygon_mesh(request["mesh"]); monitor=GateIntegrityMonitor(source)
    recipe=BranchingRecipe.from_data(request["recipe"]); started=perf_counter(); records=[]; audits={}
    def retain(mesh,history,events,anchors,parents,vertex_parents,stage,tracker):
        index=stage["stage_index"]; geometry=mesh_to_data(mesh); geometry_hash=digest(geometry)
        if index<=recipe.backbone_stages and geometry_hash!=request["backbone"]["geometry_sha256"][str(index)]:
            raise ValueError("Exact saved C07 prefix geometry mismatch.")
        if index<=recipe.backbone_stages:
            shared=STUDY/"references"/f"BACKBONE_S{index:02d}.json.gz"
            if not shared.exists():
                gz_write(shared,geometry)
                gz_write(STUDY/"references"/f"BACKBONE_S{index:02d}_lineage.json.gz",dict(history=history,events=events,
                    face_parents={k:[dict(id=p.key,weight=p.weight) for p in refs] for k,refs in parents.items()},
                    vertex_parents={k:[dict(id=p.key,weight=p.weight) for p in refs] for k,refs in vertex_parents.items()}))
                gz_write(STUDY/"references"/f"BACKBONE_S{index:02d}_signatures.json.gz",tracker.to_data())
        diagnostics=extra_diagnostics(mesh)
        stage.update(statistics=inspect_mesh(mesh),diagnostics=diagnostics,distributions=distributions(mesh),
            normal_variation=normal_variation(mesh),monitor=monitor.evaluate(mesh,anchors,generation=index),
            geometry_sha256=geometry_hash,elapsed_seconds=perf_counter()-started)
        write(directory/"terminal.json",geometry)
        gz_write(directory/"terminal_lineage.json.gz",dict(history=history,events=events))
        gz_write(directory/"terminal_signatures.json.gz",tracker.to_data())
        if request["retain_checkpoints"] and index>recipe.backbone_stages:
            gz_write(directory/f"S{index:02d}.json.gz",geometry)
            gz_write(directory/f"S{index:02d}_lineage.json.gz",dict(history=history,events=events,
                face_parents={k:[dict(id=p.key,weight=p.weight) for p in refs] for k,refs in parents.items()},
                vertex_parents={k:[dict(id=p.key,weight=p.weight) for p in refs] for k,refs in vertex_parents.items()}))
            gz_write(directory/f"S{index:02d}_signatures.json.gz",tracker.to_data())
        if "selection" in stage:
            gz_write(directory/f"S{index:02d}_routing.json.gz",dict(selection=stage["selection"],events=stage["events"],backend=stage["backend"]))
        finish=False
        # Reuse only an audit of exactly identical geometry within this worker.
        if ("events" in stage and not stage.get("quiet")) or finish or request["phase"] not in SCREEN_PHASES:
            if geometry_hash not in audits: audits[geometry_hash]=crossing(directory/f"audit_S{index:02d}",geometry,f"S{index:02d}")
            stage["crossings"]=audits[geometry_hash]
        record={k:v for k,v in stage.items() if k not in ("selection","events","backend")}
        records.append(record)
        write(directory/"summary.json",dict(status="RUNNING",request_sha256=digest(request),recipe=request["recipe"],stages=records,runtime_seconds=perf_counter()-started))
        print(recipe.id,index,stage["stage"]["operator"],mesh.number_of_faces(),stage["branches"]["unique_branch_signatures"],round(perf_counter()-started,2),flush=True)
        if diagnostics["degenerate_fan_faces"]: raise ValueError("Degenerate fan faces; retained without repair.")
        if stage.get("crossings",{}).get("sample_limit_reached"): raise ValueError("Severe sampled crossing cap reached; no further growth.")
    result=run_branching(source,recipe,dll_path=request["mola_dll"],budget=ExecutionBudget(request["max_faces"],request["max_faces"]*2,48),publish=retain)
    mesh=result["mesh"]; geometry=mesh_to_data(mesh); save_mesh(mesh,directory/"terminal.obj")
    write(directory/"terminal.json",geometry)
    if digest(geometry) not in audits: audits[digest(geometry)]=crossing(directory/"audit_terminal",geometry,"terminal")
    terminal_cross=audits[digest(geometry)]
    write(directory/"terminal_crossings.json",terminal_cross)
    write(directory/"branch_signatures.json",result["signatures"].diagnostics(result["history"],result["events"]))
    gz_write(directory/"branch_tables.json.gz",result["branch_tables"])
    artifacts={p.name:file_hash(p) for p in directory.iterdir() if p.is_file() and p.name!="summary.json"}
    summary=dict(status=result["status"],reason=result["reason"],recipe=request["recipe"],request_sha256=digest(request),
        stages=records,attempted_stages=[{k:v for k,v in s.items() if k in ("stage","stage_index","failure")} for s in result["stages"]],
        source_immutable=result["source_immutable"],output_sha256=digest(geometry),artifacts=artifacts,runtime_seconds=perf_counter()-started,
        technically_valid=result["status"]=="SUCCESS" and not terminal_cross["sample_limit_reached"],terminal_statistics=inspect_mesh(mesh),
        shared_backbone_checkpoints="references/BACKBONE_S01..S05.json.gz; exact hashes checked at every stage")
    write(directory/"summary.json",summary)


def execute(ids,phase,dll):
    for name in ids:
        if sum(p.stat().st_size for p in STUDY.rglob("*") if p.is_file()) >6*1024**3: raise ValueError("Task storage ceiling reached.")
        request=make_request(STUDY/"recipes"/(name+".json"),phase,dll); root=STUDY/phase/name
        attempts=sorted(root.glob("attempt_*")) if root.exists() else []
        if any(verified_resume(p,request) for p in attempts): print(name,"RESUME verified, skipped",flush=True); continue
        directory=root/f"attempt_{len(attempts)+1:03d}"; path=STUDY/"requests"/phase/(name+".json"); write(path,request)
        process=bounded_worker([Path(__file__).resolve(),"--one",directory,"--request",path,"--study",STUDY],STUDY/"logs"/phase/f"{name}_{directory.name}",900)
        if not (directory/"summary.json").exists(): write(directory/"summary.json",dict(status="FAILED",reason="See worker stderr",stages=[]))
        summary=read(directory/"summary.json"); summary["process"]=process
        if process["exit_code"]: summary.update(status="PROCESS_STOP",reason=process["stop"] or "Worker exception; see stderr",technically_valid=False)
        write(directory/"summary.json",summary)
        print(name,summary["status"],summary.get("reason"),round(process["seconds"],2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--init",action="store_true"); parser.add_argument("--run",nargs="+")
    parser.add_argument("--phase",choices=("A","B","C","F","R","HERO","REPLAY","PRODUCTION"),default="A"); parser.add_argument("--dll",type=Path)
    parser.add_argument("--one",type=Path); parser.add_argument("--request",type=Path); parser.add_argument("--study",type=Path,default=STUDY)
    args=parser.parse_args(); STUDY=args.study.resolve()
    if not STUDY.is_relative_to(ROOT/"output/task21"): parser.error("Output must remain in output/task21")
    if args.one: one(args.one,read(args.request))
    elif args.init: initialise(args.dll)
    elif args.run: execute(args.run,args.phase,args.dll)
    else: parser.error("Choose --init, --run or --one")
