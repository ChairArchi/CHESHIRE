"""Small serial study of actual meshes; retained recipes, checkpoints and views.

Run with the repository .venv. No external libraries or DLLs are required.
"""
import argparse
import gzip
import hashlib
import json
from math import dist, hypot
from pathlib import Path
import subprocess
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))
sys.path.insert(0, str(ROOT / "tools"))
from compas.datastructures import Mesh
from compas.geometry import Box, cross_vectors, subtract_vectors
from cheshire import save_mesh, load_mesh, inspect_mesh
from cheshire.execution import ExecutionBudget
from cheshire_worker import mesh_from_data, mesh_to_data
from weighted_study import run_candidate, SCHEDULES
from worker_process import worker_environment
from morphology import windows_memory

BASELINE = "7ece1afa00774a42251f202c106cdb2d6dacd350"
GATE = ROOT / "output/task12/8c5ff45c-7810-455d-a4ba-c1339c67eccd/request.json"


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def source(which, input_path=None):
    if input_path is not None:
        data=json.loads(input_path.read_text(encoding="utf-8"))
        return mesh_from_data(data.get("mesh",data))
    if which == "small":
        return Mesh.from_shape(Box(2, 2, 6))
    return mesh_from_data(json.loads(GATE.read_text(encoding="utf-8"))["mesh"])


def geometry_diagnostics(mesh):
    diagonal = hypot(*inspect_mesh(mesh)["bounding_box"])
    threshold = max(diagonal*diagonal*1e-14, 1e-20)
    degenerate, opposed = [], []
    for f in mesh.faces():
        p = mesh.face_coordinates(f)
        normals = [cross_vectors(subtract_vectors(p[i], p[0]), subtract_vectors(p[i+1], p[0])) for i in range(1,len(p)-1)]
        if any(hypot(*n) <= threshold for n in normals):
            degenerate.append(f)
        if len(normals) == 2 and sum(a*b for a,b in zip(*normals)) < 0:
            opposed.append(f)
    return dict(**inspect_mesh(mesh), components=len(mesh.connected_vertices()),
        degenerate_fan_faces=degenerate, opposed_fan_normals=opposed,
        note="Fan-triangle area/opposed normals are diagnostic approximations for nonplanar quads, not repairs or a collision certificate.")


def one(directory, which, kind, recipe, generations, input_path=None):
    directory.mkdir(parents=True, exist_ok=False)
    original = source(which,input_path)
    input_data = mesh_to_data(original)
    write(directory / "request.json", {"mesh": input_data, "baseline": BASELINE, "study": kind,
        "recipe": recipe, "generations": generations, "budget": {"max_faces":50000, "max_vertices":50000},
        "input_sha256": hashlib.sha256(json.dumps(input_data,sort_keys=True).encode()).hexdigest()})
    save_mesh(original, directory / "G0.obj")
    write(directory / "G0.json", input_data)
    result = run_candidate(original, study=kind, schedule=SCHEDULES[recipe], generations=generations)
    records = []
    for stage in result["stages"]:
        number = stage["generation"]
        mesh = mesh_from_data(stage["mesh"])
        save_mesh(mesh, directory / f"G{number}.obj")
        loaded = load_mesh(directory / f"G{number}.obj")
        original_keys = list(mesh.vertices())
        assert list(loaded.vertices()) == list(range(len(original_keys)))
        assert all(loaded.vertex_coordinates(i) == mesh.vertex_coordinates(key) for i,key in enumerate(original_keys))
        indices = {v:i for i,v in enumerate(original_keys)}
        assert [loaded.face_vertices(f) for f in loaded.faces()] == [[indices[v] for v in mesh.face_vertices(f)] for f in mesh.faces()]
        write(directory / f"G{number}.json", stage["mesh"])
        stage["diagnostics"] = geometry_diagnostics(mesh)
        records.append({k:v for k,v in stage.items() if k not in ("mesh","metadata","drivers","source_z","sampling_parents")})
    with gzip.open(directory / "result.json.gz", "wt", encoding="utf-8") as stream:
        json.dump(result,stream,allow_nan=False)
    last = result["stages"][-1] if result["stages"] else None
    write(directory / "response.json", {"variants": [{"id":directory.name,"mesh":last["mesh"]}] if last else []})
    write(directory / "summary.json", dict(status=result["status"], reason=result["reason"], study=kind,
        recipe=recipe, exact_schedule=result["schedule"], generations_reached=len(records), stages=records,
        elapsed_seconds=result["elapsed_seconds"], semantic_lineage="NOT IMPLEMENTED", obj_roundtrip="PASS"))
    print(directory.name,result["status"],[(r["vertex_count"],r["face_count"]) for r in records],flush=True)


def bounded_child(args, directory, seconds=60):
    directory.mkdir(parents=True, exist_ok=True)
    start = monotonic()
    peak = 0
    with (directory / "stdout.txt").open("w") as out, (directory / "stderr.txt").open("w") as err:
        child = subprocess.Popen([str(ROOT / ".venv/Scripts/python.exe"),"-E","-s",*args],
            cwd=ROOT, env=worker_environment(), shell=False, stdout=out, stderr=err,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        reason = None
        try:
            while child.poll() is None:
                memory = windows_memory(child.pid)
                if memory["status"] != "MEASURED":
                    reason="MEMORY MEASUREMENT UNAVAILABLE"
                peak = max(peak, memory.get("combined_resident_bytes", 0) or 0)
                if monotonic()-start > seconds:
                    reason="TIMEOUT"
                if peak > 4*1024**3:
                    reason="MEMORY LIMIT"
                if memory.get("available_bytes", 0) < memory.get("available_floor_bytes", 0):
                    reason="AVAILABLE MEMORY FLOOR"
                if reason:
                    child.terminate()
                    child.wait(timeout=10)
                    break
                import time
                time.sleep(.25)
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
    return dict(exit_code=child.returncode,stop=reason,seconds=monotonic()-start,peak_combined_resident_bytes=peak)


def execute(study_dir, which, input_path=None):
    mesh = source(which,input_path)
    study_dir.mkdir(parents=True, exist_ok=True)
    write(study_dir / f"{which}_source.json", mesh_to_data(mesh))
    save_mesh(mesh,study_dir / f"{which}_source.obj")
    if which == "small":
        cases = [("S_standard", "S", "ribs",6)] + [("U_"+name,"U",name,5) for name in SCHEDULES] + [("F_"+name,"F",name,5) for name in ("ribs","attenuated")]
    else:
        cases = [("S_standard","S","ribs",2),("U_ribs","U","ribs",2), ("F_ribs","F","ribs",2), ("F_attenuated","F","attenuated",2)]
    # Exact growth estimates, not an increased offline ceiling.
    estimates=[]; v,e,f=mesh.number_of_vertices(),mesh.number_of_edges(),mesh.number_of_faces()
    corners=sum(len(mesh.face_vertices(k)) for k in mesh.faces())
    b=sum(mesh.is_edge_on_boundary(edge) for edge in mesh.edges())
    for g in range(1,8):
        v,f=v+e+f,corners
        b*=2; e=(4*f+b)//2; corners=4*f
        estimates.append(dict(generation=g,vertices=v,faces=f,within_50k=max(v,f)<=50000))
    write(study_dir / f"{which}_preflight.json",dict(baseline=BASELINE, source=inspect_mesh(mesh),
        estimates=estimates, memory=windows_memory(), resident_cap_bytes=4*1024**3,
        note="Serial fresh workers, 60s per generation study; 50k result ceiling unchanged. No raised offline ceiling.",cases=cases))
    for name,kind,recipe,generations in cases:
        path=study_dir / which / name
        logs=study_dir / "logs" / which / name
        if path.exists():
            raise ValueError("Do not overwrite an existing attempted schedule: "+str(path))
        command=[str(Path(__file__).resolve()),"--one",str(path),"--source",which,
            "--kind",kind,"--recipe",recipe,"--generations",str(generations)]
        if input_path:
            command.extend(["--input",str(input_path.resolve())])
        result=bounded_child(command,logs)
        write(logs / "process.json",result)
        print(which,name,result,flush=True)
        if result["exit_code"]:
            print((logs / "stderr.txt").read_text(),flush=True)
        if (path / "response.json").exists():
            audit=bounded_child([str(ROOT / "tools/morphology_crossings.py"),str(path)],logs / "audit",30)
            write(logs / "audit/process.json",audit)
            print("audit",name,audit,flush=True)


def views(study_dir):
    frames=[]; sheets=[]
    for which in ("small","gate"):
        folder=study_dir / which
        if not folder.exists():
            continue
        meshes=[(which+" SOURCE",study_dir / f"{which}_source.json")]
        for case in sorted(folder.iterdir()):
            summary=json.loads((case / "summary.json").read_text())
            g=summary["generations_reached"]
            if g:
                meshes.append((case.name+f" G{g}",case / f"G{g}.json"))
        projected=[]
        for _,path in meshes:
            data=json.loads(path.read_text())
            projected.extend((v["xyz"][0]+.65*v["xyz"][1],v["xyz"][2]+.30*v["xyz"][1]) for v in data["vertices"])
        lo_u,hi_u=min(p[0] for p in projected),max(p[0] for p in projected)
        lo_v,hi_v=min(p[1] for p in projected),max(p[1] for p in projected)
        pad=.05*max(hi_u-lo_u,hi_v-lo_v)
        bounds=[lo_u-pad,hi_u+pad,lo_v-pad,hi_v+pad]
        groups=[("whole",bounds,False,meshes), ("wire",bounds,True,meshes)]
        # Identical registered crown crop, using original coordinates only.
        src=json.loads((study_dir / f"{which}_source.json").read_text())
        orig=[(v["xyz"][0]+.65*v["xyz"][1],v["xyz"][2]+.30*v["xyz"][1]) for v in src["vertices"]]
        u0,u1=min(p[0] for p in orig),max(p[0] for p in orig); v0,v1=min(p[1] for p in orig),max(p[1] for p in orig)
        crop=[u0+.35*(u1-u0),u0+.80*(u1-u0),v0+.62*(v1-v0),v1+.05*(v1-v0)]
        groups.append(("detail_wire",crop,True,meshes))
        checkpoints=[]
        for name in ("U_ribs","F_ribs"):
            for g in (1,3,5,6):
                path=folder / name / f"G{g}.json"
                if path.exists():
                    checkpoints.append((name+f" G{g}",path))
        groups.append(("generations",bounds,False,checkpoints))
        for group,bound,wire,items in groups:
            files=[]
            for label,path in items:
                filename=f"{which}_{group}_{len(frames):02d}.png"
                frames.append(dict(mesh=path.relative_to(study_dir).as_posix(),label=label,
                    bounds=bound,width=550,height=600,wireframe=wire,file=filename))
                files.append(filename)
            if files:
                sheets.append(dict(file=f"{which}_{group}.png",title=f"{which.upper()} {group} / actual retained polygons", columns=min(4,len(files)),width=550,height=600,images=files))
        # A concise matched-generation comparison separate from attempted cases.
        core=[meshes[0]]
        g=6 if which == "small" else 2
        for name,label in (("S_standard","STANDARD"),("U_attenuated_G6" if which == "small" else "U_attenuated","UNIFORM"),("F_attenuated_G6" if which == "small" else "F_attenuated","FIELD")):
            path=folder / name / f"G{g}.json"
            if path.exists():
                core.append((label+f" G{g}",path))
        for group,bound,wire in (("core",bounds,False),("core_wire",crop,True)):
            files=[]
            for label,path in core:
                filename=f"{which}_{group}_{len(frames):02d}.png"
                frames.append(dict(mesh=path.relative_to(study_dir).as_posix(),label=label,bounds=bound,width=650,height=700,wireframe=wire,file=filename))
                files.append(filename)
            sheets.append(dict(file=f"{which}_{group}.png",title=f"{which.upper()} matched S/U/F generation / no presentation smoothing",columns=4,width=650,height=700,images=files))
    write(study_dir / "projection_plan.json",dict(frames=frames,sheets=sheets))
    process=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT / "tools/morphology_projection.ps1"),"-PlanPath",str(study_dir / "projection_plan.json")],cwd=ROOT,timeout=600,capture_output=True,text=True)
    (study_dir / "projection_log.txt").write_text(process.stdout+process.stderr,encoding="utf-8")
    if process.returncode:
        raise ValueError(process.stderr)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,default=ROOT / "output/task14/study")
    parser.add_argument("--source",choices=("small","gate"),default="small")
    parser.add_argument("--input",type=Path,help="Explicit saved mesh/request JSON; enables reproduction from the review ZIP.")
    parser.add_argument("--one",type=Path)
    parser.add_argument("--kind",default="U")
    parser.add_argument("--recipe",default="ribs")
    parser.add_argument("--generations",type=int,default=6)
    parser.add_argument("--views",action="store_true")
    args=parser.parse_args()
    if args.one:
        one(args.one,args.source,args.kind,args.recipe,args.generations,args.input)
    elif args.views:
        views(args.directory)
    else:
        execute(args.directory,args.source,args.input)


if __name__ == "__main__":
    main()
