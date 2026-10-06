"""Serial Task 15 experiment, with explicit carrier and schedule phase gates."""
import argparse
import gzip
import hashlib
import json
from math import dist
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "rhino"))
sys.path.insert(0,str(ROOT / "examples"))
from cheshire import save_mesh,load_mesh
from cheshire.subdivision import _local_face,_require_bilinear_quad
from cheshire_worker import mesh_from_data,mesh_to_data,RUNTIME_IDENTITY
from carrier_study import coarse_gate,carrier_ladder,carrier_statistics,expanded_schedule,LOCAL_SCHEDULES,run_uniform,topology_warning_association,DIMENSIONS,generation_schedules,schedule_extensions
from weighted_study import SCHEDULES
from weighted_subdivision_study import geometry_diagnostics,bounded_child

BASELINE="9c637bb5ea17d43c7450394832689254c61d7363"


def write(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def compressed(path,data):
    with gzip.open(path,"wt",encoding="utf-8") as stream:
        json.dump(data,stream,allow_nan=False)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def initialise(study,dense_path):
    study.mkdir(parents=True,exist_ok=False)
    (study / "carriers").mkdir()
    dense=mesh_from_data(read(dense_path).get("mesh",read(dense_path)))
    stats=carrier_statistics(dense)
    origin=[(stats["bbox_min"][i]+stats["bbox_max"][i])/2 for i in (0,1)]+[stats["bbox_min"][2]]
    carriers={**carrier_ladder(coarse_gate(origin)),"DENSE":dense}
    report={}
    for name,mesh in carriers.items():
        write(study / f"carriers/{name}.json",mesh_to_data(mesh))
        save_mesh(mesh,study / f"carriers/{name}.obj")
        report[name]=carrier_statistics(mesh)
        v,e,f=mesh.number_of_vertices(),mesh.number_of_edges(),mesh.number_of_faces()
        b=sum(mesh.is_edge_on_boundary(edge) for edge in mesh.edges())
        corners=sum(len(mesh.face_vertices(k)) for k in mesh.faces())
        growth=[]
        for generation in range(1,7):
            v,f=v+e+f,corners
            b*=2; e=(4*f+b)//2; corners=4*f
            growth.append(dict(generation=generation,vertices=v,faces=f,budget="SAFE" if max(v,f)<=50000 else "BLOCKED"))
        report[name]["growth_preflight"]=growth
    write(study / "carrier_statistics.json",report)
    write(study / "inputs.json",dict(baseline=BASELINE,dimensions=DIMENSIONS,origin=origin,
        construction="Boundary of five adjacent occupied cells; shared grid IDs; interfaces not emitted; 22 planar outward quads.",
        dense_input_sha256=hashlib.sha256(json.dumps(mesh_to_data(dense),sort_keys=True).encode()).hexdigest(),
        confounds="C0/C1/C2 isolate resolution on exactly the same closed surface. DENSE also differs in depth (900 vs 500), detail, components (10 vs 1) and boundaries (568 vs 0).",
        limits=dict(vertices=50000,faces=50000,generations=6,worker_seconds=60,audit_seconds=30,resident_bytes=4*1024**3,storage_bytes=3*1024**3),
        runtime_identity=RUNTIME_IDENTITY))
    print({name:(s["vertex_count"],s["face_count"]) for name,s in report.items()},flush=True)


def extra_diagnostics(mesh):
    result=geometry_diagnostics(mesh)
    failed=[]; examples=[]
    for face in mesh.faces():
        if len(mesh.face_vertices(face)) != 4:
            continue
        try:
            local,_=_local_face(mesh.face_coordinates(face))
            _require_bilinear_quad(local,face)
        except ValueError as error:
            failed.append(face)
            if len(examples)<3:
                examples.append(dict(face=face,reason=str(error)))
    result["bilinear_admissibility_warning_faces"]=failed
    result["bilinear_warning_examples"]=examples
    result["bilinear_warning_scope"]="Existing Task 07.1 conservative local Jacobian test, diagnostic only; failure is not proof of a global crossing. Geometry is not changed."
    result["extraordinary_association"]=topology_warning_association(mesh,sorted(set(failed)|set(result["opposed_fan_normals"])))
    return result


def one(directory,input_path,schedule_path,generations):
    directory.mkdir(parents=True,exist_ok=False)
    original=mesh_from_data(read(input_path)); before=mesh_to_data(original)
    schedule=read(schedule_path)
    operator=ROOT / "src/cheshire/weighted_subdivision.py"
    baseline_operator=subprocess.check_output(["git","show",BASELINE+":src/cheshire/weighted_subdivision.py"],cwd=ROOT)
    assert operator.read_bytes().replace(b"\r\n",b"\n") == baseline_operator.replace(b"\r\n",b"\n")
    write(directory / "request.json",dict(mesh=before,schedule=schedule,requested_generations=generations,baseline=BASELINE,
        operator_unchanged=True,operator_sha256=hashlib.sha256(baseline_operator).hexdigest(),runtime_identity=RUNTIME_IDENTITY,
        budget=dict(max_faces=50000,max_vertices=50000,max_generation=6),spatial_modulation=False))
    write(directory / "G0.json",before); save_mesh(original,directory / "G0.obj")
    base_stats=carrier_statistics(original)
    previous=original
    started=perf_counter()
    last_checkpoint=started
    def retain_summary(result):
        summaries=[{key:value for key,value in stage.items() if key not in
                    ("mesh","metadata","drivers","sampling_parents","source_z")} for stage in result["stages"]]
        write(directory / "summary.json",dict(status=result["status"],reason=result["reason"],generations_reached=len(summaries),schedule=schedule,
            spatial_modulation=False,source_immutable=mesh_to_data(original)==before,stages=summaries,semantic_lineage="NOT IMPLEMENTED"))
        write(directory / "response.json",dict(variants=[dict(id=f"G{s['generation']}",mesh=s["mesh"]) for s in result["stages"]]))
    def checkpoint(result):
        nonlocal previous,last_checkpoint
        stage=result["stages"][-1]; generation=stage["generation"]
        mesh=mesh_from_data(stage["mesh"])
        moved=[dist(previous.vertex_coordinates(v),mesh.vertex_coordinates(v)) for v in previous.vertices()]
        stage["retained_corner_motion"]=dict(count=len(moved),median=median(moved),max=max(moved),
            note="Previous vertices retained as corner points, not a semantic field or full-surface displacement measure.")
        stage["statistics"]=carrier_statistics(mesh)
        stage["bbox_change_from_G0"]=[a-b for a,b in zip(stage["statistics"]["bounding_box"],base_stats["bounding_box"])]
        stage["diagnostics"]=extra_diagnostics(mesh)
        write(directory / f"G{generation}.json",stage["mesh"])
        save_mesh(mesh,directory / f"G{generation}.obj")
        reloaded=load_mesh(directory / f"G{generation}.obj")
        keys=list(mesh.vertices()); index={v:i for i,v in enumerate(keys)}
        assert [reloaded.vertex_coordinates(v) for v in reloaded.vertices()] == [mesh.vertex_coordinates(v) for v in keys]
        assert [reloaded.face_vertices(f) for f in reloaded.faces()] == [[index[v] for v in mesh.face_vertices(f)] for f in mesh.faces()]
        stage["OBJ_roundtrip"]="PASS ordered coordinates and face cycles"
        now=perf_counter()
        stage["checkpoint_elapsed_seconds"]=now-started
        stage["seconds_since_previous_checkpoint"]=now-last_checkpoint
        stage["timing_note"]="Measured monotonic wall time, including generation, diagnostics and OBJ exports; not backend-only time."
        compressed(directory / "checkpoint.json.gz",result)
        # Also keep a readable partial response if the process is interrupted.
        retain_summary(result)
        previous=mesh
        last_checkpoint=now
    result=run_uniform(original,schedule,generations=generations,publish=checkpoint)
    assert mesh_to_data(original) == before
    compressed(directory / "result.json.gz",result)
    retain_summary(result)
    print(directory.name,result["status"],result["reason"],[(s["vertex_count"],s["face_count"]) for s in result["stages"]],flush=True)


def execute_case(study,phase,name,carrier,schedule,generations=6):
    directory=study / phase / name
    schedule_dir=study / "schedules"; schedule_dir.mkdir(exist_ok=True)
    schedule_path=schedule_dir / (phase+"_"+name+".json")
    if directory.exists() or schedule_path.exists():
        raise ValueError("Existing attempts are preserved; choose a new study/case path.")
    if sum(p.stat().st_size for p in study.rglob("*") if p.is_file()) >= 3*1024**3:
        raise ValueError("Study storage cap reached before starting another case.")
    write(schedule_path,expanded_schedule(schedule))
    logs=study / "logs" / phase / name
    process=bounded_child([str(Path(__file__).resolve()),"--one",str(directory),"--input",str(study / f"carriers/{carrier}.json"),
        "--schedule",str(schedule_path),"--generations",str(generations)],logs,60)
    write(logs / "process.json",process)
    print(phase,name,process,flush=True)
    if process["exit_code"]:
        print((logs / "stderr.txt").read_text(),flush=True)
    if (directory / "response.json").exists():
        audit=bounded_child([str(ROOT / "tools/morphology_crossings.py"),str(directory)],logs / "audit",30)
        write(logs / "audit/process.json",audit)
        print("audit",name,audit,flush=True)
        if (directory / "crossing_audit.json").exists():
            summary=read(directory / "summary.json")
            crossings={r["id"]:r for r in read(directory / "crossing_audit.json")["candidates"]}
            for stage in summary["stages"]:
                stage["sampled_crossings"]=crossings.get("G"+str(stage["generation"]))
            write(directory / "summary.json",summary)


def run_local(study):
    for name,schedule in LOCAL_SCHEDULES.items():
        execute_case(study,"local",name,"C0",schedule,3)


def run_primary(study,fold):
    if fold not in LOCAL_SCHEDULES or not (study / f"local/{fold}/crossing_audit.json").exists():
        raise ValueError("Choose a retained, diagnosed C0 local schedule first.")
    write(study / "primary_selection.json",dict(A="Task14 attenuated",B=fold,
        A_schedule=expanded_schedule(SCHEDULES["attenuated"]),B_schedule=LOCAL_SCHEDULES[fold],
        rule="Identical dimensionless generation schedule, Task14 global mean edge scaling, same 50k budget; no spatial field.",
        purpose="Resolve carrier resolution before generation-schedule development."))
    for label,schedule in (("A",SCHEDULES["attenuated"]),("B",LOCAL_SCHEDULES[fold])):
        for carrier in ("C0","C1","C2","DENSE"):
            execute_case(study,"primary",label+"_"+carrier,carrier,schedule)


def run_schedules(study,carrier):
    decision=read(study / "review_decisions.json")
    if decision.get("selected_carrier") != carrier or not all((study / f"primary/{label}_{scale}/crossing_audit.json").exists() for label in ("A","B") for scale in ("C0","C1","C2","DENSE")):
        raise ValueError("Resolve and record the complete primary carrier comparison before schedule development.")
    write(study / "generation_schedule_plan.json",dict(carrier=carrier,spatial_modulation=False,
        fixed_control="T00 repeats seed G1 ratios; Task14 edge scaling unchanged",schedules=generation_schedules(),
        purpose="G1 macro, G2/G3 meso, G4+ fine; all same carrier, camera and 50k budget."))
    for name,schedule in generation_schedules().items():
        execute_case(study,"generation",name,carrier,schedule)


def run_extensions(study,carrier):
    if read(study / "review_decisions.json").get("selected_carrier") != carrier or not all((study / f"generation/{name}/crossing_audit.json").exists() for name in generation_schedules()):
        raise ValueError("Inspect the first eight diagnosed schedules on the selected carrier before follow-ups.")
    write(study / "schedule_extension_plan.json",dict(carrier=carrier,schedules=schedule_extensions(),spatial_modulation=False,
        reason="Constant strong T00 crossed. Retain it, add a moderate constant control, and strengthen only the fine tail of the diagnosed T03 prefix."))
    for name,schedule in schedule_extensions().items():
        execute_case(study,"generation",name,carrier,schedule)


def views(study,phase):
    sources=[(name,study / f"carriers/{name}.json") for name in ("C0","C1","C2","DENSE")]
    cases=sorted((study / phase).glob("*/summary.json"))
    finals=[]
    for summary_path in cases:
        summary=read(summary_path); g=summary["generations_reached"]
        if g:
            finals.append((summary_path.parent.name+f" G{g}",summary_path.parent / f"G{g}.json"))
    all_points=[]
    for _,path in sources+finals:
        all_points.extend((v["xyz"][0]+.65*v["xyz"][1],v["xyz"][2]+.30*v["xyz"][1]) for v in read(path)["vertices"])
    low_u,high_u=min(p[0] for p in all_points),max(p[0] for p in all_points)
    low_v,high_v=min(p[1] for p in all_points),max(p[1] for p in all_points)
    pad=.05*max(high_u-low_u,high_v-low_v)
    bounds=[low_u-pad,high_u+pad,low_v-pad,high_v+pad]
    frames=[]; sheets=[]
    groups=[("sources",sources,True,bounds),("final",finals,False,bounds)]
    if phase=="primary":
        for summary_path in cases:
            items=[]
            for generation in (0,1,2,3,5,6):
                path=summary_path.parent / f"G{generation}.json"
                if path.exists():
                    items.append((summary_path.parent.name+f" G{generation}",path))
            groups.append(("progress_"+summary_path.parent.name,items,False,bounds))
    if phase=="generation":
        # Every schedule gets the same checkpoint panel; no favorable camera.
        for summary_path in cases:
            items=[]
            for generation in (0,1,2,3,5,6):
                path=summary_path.parent / f"G{generation}.json"
                if path.exists():
                    items.append((summary_path.parent.name+f" G{generation}",path))
            groups.append(("progress_"+summary_path.parent.name,items,False,bounds))
    original=read(study / "carrier_statistics.json")["C0"]
    x0,z0=original["bbox_min"][0],original["bbox_min"][2]
    crop=[x0+500,x0+2300,z0+2050,z0+3650]
    groups.append(("detail_wire",finals,True,crop))
    for name,items,wire,bound in groups:
        files=[]
        for label,path in items:
            filename=f"{phase}_{name}_{len(frames):02d}.png"
            frames.append(dict(mesh=path.relative_to(study).as_posix(),label=label,bounds=bound,width=550,height=600,wireframe=wire,file=filename))
            files.append(filename)
        if files:
            sheets.append(dict(file=f"{phase}_{name}.png",title=f"{phase} {name}: actual polygons; same scale, no presentation smoothing",columns=min(4,len(files)),width=550,height=600,images=files))
    plan=study / (phase+"_projection_plan.json")
    write(plan,dict(frames=frames,sheets=sheets))
    process=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT / "tools/morphology_projection.ps1"),"-PlanPath",str(plan)],cwd=ROOT,capture_output=True,text=True,timeout=600)
    (study / (phase+"_projection_log.txt")).write_text(process.stdout+process.stderr,encoding="utf-8")
    if process.returncode:
        raise ValueError(process.stderr)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=("init","local","primary","schedules","extensions","views"),nargs="?")
    parser.add_argument("--directory",type=Path,default=ROOT / "output/task15/study")
    parser.add_argument("--dense-input",type=Path,default=ROOT / "output/task14/study/gate_source.json")
    parser.add_argument("--fold",default="L4_macro_corner")
    parser.add_argument("--carrier",choices=("C0","C1","C2"),default="C0")
    parser.add_argument("--view-phase",default="local")
    parser.add_argument("--one",type=Path)
    parser.add_argument("--input",type=Path)
    parser.add_argument("--schedule",type=Path)
    parser.add_argument("--generations",type=int,default=6)
    args=parser.parse_args()
    if args.one:
        one(args.one,args.input,args.schedule,args.generations)
    elif args.phase=="init":
        initialise(args.directory,args.dense_input)
    elif args.phase=="local":
        run_local(args.directory)
    elif args.phase=="primary":
        run_primary(args.directory,args.fold)
    elif args.phase=="schedules":
        run_schedules(args.directory,args.carrier)
    elif args.phase=="extensions":
        run_extensions(args.directory,args.carrier)
    elif args.phase=="views":
        views(args.directory,args.view_phase)
    else:
        parser.error("Choose a phase or one retained input/schedule case.")


if __name__ == "__main__":
    main()
