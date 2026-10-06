"""Matched geometry views and concise tables; selection remains visual, not scored."""
import argparse
import csv
import gzip
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples"))
from subdivision_capability_study import read,write

STUDY=ROOT/"output/task19/study"

def cases(phase):
    result=[]
    for folder in sorted((STUDY/phase).glob("*")):
        attempts=sorted(folder.glob("attempt_*"))
        completed=[p for p in attempts if (p/"summary.json").exists() and read(p/"summary.json")["status"]=="SUCCESS"]
        if completed: result.append(completed[-1])
        elif attempts and (attempts[-1]/"summary.json").exists() and read(attempts[-1]/"summary.json")["status"]!="RUNNING": result.append(attempts[-1])
    return result

def views(phase):
    camera=read(ROOT/"studies/task18/camera.json")["bounds"]
    directory=STUDY/"views"/phase; directory.mkdir(parents=True,exist_ok=True)
    frames=[]; sheets=[]; table=[]
    verification={r["id"]:r for r in read(STUDY/(phase+"_verification.json"))} if (STUDY/(phase+"_verification.json")).exists() else {}
    for case in cases(phase):
        summary=read(case/"summary.json"); name=case.parent.name
        if not (case/"terminal.json").exists(): continue
        last=summary["stages"][-1] if summary["stages"] else {}
        table.append(dict(id=name,status=summary["status"],reason=summary.get("reason"),
            faces=last.get("statistics",{}).get("face_count"),vertices=last.get("statistics",{}).get("vertex_count"),
            edges=last.get("statistics",{}).get("edge_count"),ornament_depth=last.get("ornament",{}).get("maximum"),
            nested_trees=last.get("ornament",{}).get("independent_nested_trees"),events=last.get("ornament",{}).get("event_count"),
            runtime_seconds=summary.get("runtime_seconds"),fold_warnings=len(last.get("diagnostics",{}).get("opposed_fan_normals",[])),
            bilinear_warnings=len(last.get("diagnostics",{}).get("bilinear_admissibility_warning_faces",[]))))
        check=verification.get(name,{})
        table[-1].update(sampled_crossings=check.get("sampled_crossings"),technically_valid=check.get("technically_valid"))
        if check.get("crossing_cap"):
            table[-1]["status"]="TERMINAL_CROSSING_CAP"
        for view in (("front","oblique") if phase=="A" else ("front","oblique","detail","wire","depth")):
            frame=dict(mesh=str(case.relative_to(STUDY)/"terminal.json"),file=f"views/{phase}/{name}_{view}.png",
                label=f"{name} / {table[-1]['status']} / F={table[-1]['faces']} / event depth {table[-1]['ornament_depth']}",
                camera="front" if view=="front" else "oblique",width=1000,height=1000,
                bounds=camera[view if view in camera else "detail"],wireframe=view=="wire")
            if view=="depth":
                with gzip.open(case/"terminal_lineage.json.gz","rt",encoding="utf-8") as stream:
                    import json
                    lineage=json.load(stream)
                write(directory/(name+"_depth.json"),{k:v["depth"] for k,v in lineage["history"].items()})
                frame["depthfile"]=f"views/{phase}/{name}_depth.json"
            frames.append(frame)
    groups="ABCD" if phase=="A" else [phase]
    for group in groups:
        for view in ("front","oblique") if phase=="A" else ("oblique","detail","depth"):
            images=[f["file"] for f in frames if f["file"].endswith("_"+view+".png") and (phase!="A" or Path(f["file"]).name.startswith(group))]
            if images: sheets.append(dict(file=f"views/{phase}/{group}_{view}_sheet.png",title=f"Task19 {phase}/{group} {view}; exact polygon outputs, failures explicit",images=images,columns=3,width=1000,height=1000))
    write(STUDY/(phase+"_projection_plan.json"),dict(frames=frames,sheets=sheets))
    write(STUDY/(phase+"_table.json"),table)
    if table:
        with (STUDY/(phase+"_table.csv")).open("w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(table[0])); writer.writeheader(); writer.writerows(table)
    print(phase,"cases",len(table),"frames",len(frames))

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("phase",choices=("A","B","R","E")); parser.add_argument("--study",type=Path,default=STUDY); args=parser.parse_args()
    STUDY=args.study.resolve()
    if not STUDY.is_relative_to(ROOT/"output/task19"): parser.error("Study must remain in output/task19")
    views(args.phase)
