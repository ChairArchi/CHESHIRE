"""Bounded Task 16 experiment, with regression gate before design search."""
import argparse
from copy import deepcopy
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "rhino"))
sys.path.insert(0,str(ROOT / "examples"))
from cheshire import load_mesh,save_mesh
from cheshire_worker import mesh_from_data,mesh_to_data,RUNTIME_IDENTITY
from carrier_study import coarse_gate,carrier_statistics
from carrier_scale_study import extra_diagnostics
from generational_study import CONTROLS,direct_probes,choreographies,refinements,run_choreography
from weighted_subdivision_study import bounded_child

BASELINE="9a02d99899da2179dca3bb74e9891a697dd24177"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def compressed(path,data):
    with gzip.open(path,"wt",encoding="utf-8") as stream:
        json.dump(data,stream,allow_nan=False)


def initialize(study):
    study.mkdir(parents=True,exist_ok=False)
    previous=ROOT / "output/task15/study"
    source=read(previous / "carriers/C0.json")
    origin=read(previous / "inputs.json")["origin"]
    assert mesh_to_data(coarse_gate(origin)) == source
    write(study / "C0.json",source); save_mesh(mesh_from_data(source),study / "C0.obj")
    write(study / "source_statistics.json",carrier_statistics(mesh_from_data(source)))
    regression=[]
    result=run_choreography(mesh_from_data(source),CONTROLS["CONTROL_L4"])
    for stage in result["stages"]:
        g=stage["generation"]
        old=read(previous / f"primary/B_C0/G{g}.json")
        assert stage["mesh"] == old
        regression.append(dict(generation=g,geometry="EXACT JSON identity to saved Task15 B_C0",
            eligible=stage["metadata"]["later_generation_face_stencil"]["eligible_faces"],
            fallback=stage["metadata"]["later_generation_face_stencil"]["fallback_faces"]))
    assert result["status"] == "SUCCESS" and len(regression)==5
    write(study / "zero_weight_regression.json",dict(status="PASS",checkpoints=regression,
        tolerance="Exact ordered XYZ/connectivity identity, stronger than a floating-point tolerance; mesh origin attributes are new explicit metadata.",
        existing_equations_unchanged=True))
    write(study / "inputs.json",dict(baseline=BASELINE,source="Exact saved Task15 C0; no carrier search",
        source_sha256=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),
        reference="https://archive.bridgesmathart.org/2010/bridges2010-167.pdf#page=2",
        dimensions=read(previous / "inputs.json")["dimensions"],origin=origin,
        versions={key:version(key) for key in ("compas","pytest","pythonnet")},runtime_identity=RUNTIME_IDENTITY,
        limits=dict(vertices=50000,faces=50000,generations=5,worker_seconds=60,audit_seconds=30,resident_bytes=4*1024**3,storage_bytes=3*1024**3)))
    print("REGRESSION PASS: new w3=w4=0 matches saved Task15 G1-G5 exactly",flush=True)


def one(directory,source_path,schedule_path):
    directory.mkdir(parents=True,exist_ok=False)
    source=mesh_from_data(read(source_path)); source_data=mesh_to_data(source)
    schedule=read(schedule_path)["schedule"]
    baseline_operator=subprocess.check_output(["git","show",BASELINE+":src/cheshire/weighted_subdivision.py"],cwd=ROOT)
    assert (ROOT / "src/cheshire/weighted_subdivision.py").read_bytes().replace(b"\r\n",b"\n") == baseline_operator.replace(b"\r\n",b"\n")
    write(directory / "request.json",dict(mesh=source_data,schedule=schedule,definition=read(schedule_path),
        runtime_identity=RUNTIME_IDENTITY,baseline=BASELINE,spatial_modulation=False,requested_generations=5,
        limits=dict(vertices=50000,faces=50000,generations=5)))
    write(directory / "G0.json",source_data); save_mesh(source,directory / "G0.obj")
    original=carrier_statistics(source); started=perf_counter()
    def retain(result):
        stages=[]
        for stage in result["stages"]:
            thin={k:v for k,v in stage.items() if k not in ("mesh","metadata","origin_lineage","face_roots","sampling_parents")}
            thin["later_stencil"]={k:v for k,v in stage["metadata"]["later_generation_face_stencil"].items() if k not in ("applications","fallbacks")}
            thin["origin_class_counts"]=stage["metadata"]["origin_classes"]
            stages.append(thin)
        write(directory / "summary.json",dict(status=result["status"],reason=result["reason"],stages=stages,
            generations_reached=len(stages),schedule=schedule,source_immutable=mesh_to_data(source)==source_data,
            semantic_lineage="NOT IMPLEMENTED",spatial_modulation=False))
        write(directory / "response.json",dict(variants=[dict(id=f"G{s['generation']}",mesh=s["mesh"]) for s in result["stages"]]))
    def checkpoint(result):
        stage=result["stages"][-1]; g=stage["generation"]; mesh=mesh_from_data(stage["mesh"])
        stage["statistics"]=carrier_statistics(mesh)
        stage["bbox_change_from_G0"]=[a-b for a,b in zip(stage["statistics"]["bounding_box"],original["bounding_box"])]
        stage["diagnostics"]=extra_diagnostics(mesh)
        write(directory / f"G{g}.json",stage["mesh"]); save_mesh(mesh,directory / f"G{g}.obj")
        loaded=load_mesh(directory / f"G{g}.obj"); keys=list(mesh.vertices()); indices={v:i for i,v in enumerate(keys)}
        assert [loaded.vertex_coordinates(v) for v in loaded.vertices()] == [mesh.vertex_coordinates(v) for v in keys]
        assert [loaded.face_vertices(f) for f in loaded.faces()] == [[indices[v] for v in mesh.face_vertices(f)] for f in mesh.faces()]
        stage["OBJ_roundtrip"]="PASS exact ordered XYZ and face cycles"
        stage["checkpoint_elapsed_seconds"]=perf_counter()-started
        compressed(directory / "checkpoint.json.gz",result); retain(result)
    result=run_choreography(source,schedule,publish=checkpoint)
    compressed(directory / "result.json.gz",result); retain(result)
    print(directory.name,result["status"],result["reason"],flush=True)


def execute(study,name,definition,source_path=None):
    if read(study / "zero_weight_regression.json")["status"] != "PASS":
        raise ValueError("Zero-weight regression must pass before experiments.")
    if (study / f"cases/{name}").exists() or (study / f"schedules/{name}.json").exists():
        raise ValueError("Retain previous attempts; case/schedule already exists.")
    if sum(p.stat().st_size for p in study.rglob("*") if p.is_file()) >= 3*1024**3:
        raise ValueError("Study storage cap reached.")
    (study / "schedules").mkdir(exist_ok=True)
    schedule_path=study / f"schedules/{name}.json"; write(schedule_path,definition)
    directory=study / f"cases/{name}"; logs=study / f"logs/{name}"
    process=bounded_child([str(Path(__file__).resolve()),"--one",str(directory),"--input",str(source_path or study / "C0.json"),
        "--schedule",str(schedule_path)],logs,60)
    write(logs / "process.json",process); print(name,process,flush=True)
    if (directory / "response.json").exists():
        audit=bounded_child([str(ROOT / "tools/morphology_crossings.py"),str(directory)],logs / "audit",30)
        write(logs / "audit/process.json",audit)
        if (directory / "crossing_audit.json").exists():
            summary=read(directory / "summary.json")
            crossings={row["id"]:row for row in read(directory / "crossing_audit.json")["candidates"]}
            for stage in summary["stages"]:
                stage["sampled_crossings"]=crossings[f"G{stage['generation']}"]
            write(directory / "summary.json",summary)
        print("audit",name,audit,flush=True)
    if process["exit_code"]:
        print((logs / "stderr.txt").read_text(),flush=True)


def run_plan(study,plan):
    for name,definition in read(plan).items():
        execute(study,name,definition)


def views(study,names,label):
    cases=[(name,read(study / f"cases/{name}/summary.json")) for name in names]
    source=read(study / "source_statistics.json")
    # Fixed bounds chosen from G0 proportions, never refitted per candidate.
    x0,z0=source["bbox_min"][0],source["bbox_min"][2]
    bounds=[x0-1000,x0+5000,z0-700,z0+4600]
    crop=[x0+400,x0+2200,z0+2000,z0+3800]
    frames=[]; sheets=[]; final_files=[]
    for name,summary in cases:
        files=[]
        for g in range(summary["generations_reached"]+1):
            file=f"{label}_{name}_G{g}.png"
            frames.append(dict(mesh=f"cases/{name}/G{g}.json",label=name+f" G{g}",bounds=bounds,width=500,height=550,wireframe=False,file=file))
            files.append(file)
        sheets.append(dict(file=f"{label}_progress_{name}.png",title=name+": actual G0-G5 / same camera and scale",images=files,columns=3,width=500,height=550))
        final_files.append(files[-1])
    sheets.append(dict(file=f"{label}_final.png",title=label+": actual saved geometry, no presentation smoothing",images=final_files,columns=min(4,len(final_files)),width=500,height=550))
    for name,summary in cases:
        g=summary["generations_reached"]
        frames.append(dict(mesh=f"cases/{name}/G{g}.json",label=name+f" G{g} registered detail",bounds=crop,width=500,height=550,
            wireframe=False,file=f"{label}_{name}_detail.png"))
    sheets.append(dict(file=f"{label}_detail.png",title=label+": registered shoulder crop / same camera and scale",images=[f"{label}_{name}_detail.png" for name,_ in cases],columns=min(4,len(cases)),width=500,height=550))
    plan=study / f"{label}_projection_plan.json"; write(plan,dict(frames=frames,sheets=sheets))
    result=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT / "tools/morphology_projection.ps1"),"-PlanPath",str(plan)],
        cwd=ROOT,capture_output=True,text=True,timeout=600)
    (study / f"{label}_projection_log.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
    result.check_returncode()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",nargs="?",choices=("init","controls","probes","choreographies","refinements","plan","views"))
    parser.add_argument("--directory",type=Path,default=ROOT / "output/task16/study")
    parser.add_argument("--plan",type=Path)
    parser.add_argument("--names",nargs="+")
    parser.add_argument("--label",default="probes")
    parser.add_argument("--one",type=Path); parser.add_argument("--input",type=Path); parser.add_argument("--schedule",type=Path)
    args=parser.parse_args()
    if args.one:
        one(args.one,args.input,args.schedule)
    elif args.phase=="init": initialize(args.directory)
    elif args.phase=="controls":
        for name,schedule in CONTROLS.items(): execute(args.directory,name,dict(intention="Retained unmodified control",schedule=schedule))
    elif args.phase=="probes":
        write(args.directory / "probe_plan.json",direct_probes())
        for name,definition in direct_probes().items(): execute(args.directory,name,definition)
    elif args.phase=="choreographies":
        if not (args.directory / "probe_review.json").exists() or not all((args.directory / f"cases/{name}/crossing_audit.json").exists() for name in direct_probes()):
            raise ValueError("Review and retain all four probes before choreography follow-ups.")
        write(args.directory / "choreography_plan.json",choreographies())
        for name,definition in choreographies().items(): execute(args.directory,name,definition)
    elif args.phase=="refinements":
        if not (args.directory / "choreography_review.json").exists() or not all((args.directory / f"cases/{name}/crossing_audit.json").exists() for name in choreographies()):
            raise ValueError("Review and retain the eight choreographies before final refinements.")
        write(args.directory / "refinement_plan.json",refinements())
        for name,definition in refinements().items(): execute(args.directory,name,definition)
    elif args.phase=="plan": run_plan(args.directory,args.plan)
    elif args.phase=="views": views(args.directory,args.names,args.label)
    else: parser.error("Choose a phase or --one.")


if __name__ == "__main__": main()
