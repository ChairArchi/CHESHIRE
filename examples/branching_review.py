"""Actual polygon comparisons, branch-role colors and tabular Task-20 evidence."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples"))
from subdivision_capability_study import read,write

STUDY=ROOT/"output/task20/study"


def gz_read(path):
    with gzip.open(path,"rt",encoding="utf-8") as stream: return json.load(stream)


def cases(phase):
    result=[]
    for root in sorted((STUDY/phase).glob("*")):
        attempts=sorted(p for p in root.glob("attempt_*") if (p/"summary.json").exists() and read(p/"summary.json")["status"]!="RUNNING")
        good=[p for p in attempts if read(p/"summary.json").get("technically_valid")]
        if good or attempts: result.append((good or attempts)[-1])
    return result


def views(phase):
    camera=read(ROOT/"studies/task19/camera.json")["bounds"]
    folder=STUDY/"views"/phase; folder.mkdir(parents=True,exist_ok=True)
    frames=[]; table=[]; sheets=[]
    for case in cases(phase):
        summary=read(case/"summary.json"); name=case.parent.name
        if not summary.get("stages") or not (case/"terminal.json").exists(): continue
        last=summary["stages"][-1]; stats=summary.get("terminal_statistics",last["statistics"]); branches=read(case/"branch_signatures.json")
        crossing=read(case/"terminal_crossings.json")
        row=dict(id=name,family=summary["recipe"]["family"],status=summary["status"],technically_valid=summary.get("technically_valid",False),
            stop_reason=summary["reason"],completed_stage=last["stage"]["id"],faces=stats["face_count"],vertices=stats["vertex_count"],edges=stats["edge_count"],
            manifold=stats["is_manifold"],closed=stats["is_closed"],boundary_edges=stats["boundary_edge_count"],
            components=last["diagnostics"].get("components"),degenerate_faces=last["diagnostics"]["degenerate_fan_faces"],
            fan_warnings=len(last["diagnostics"].get("opposed_fan_normals",[])),bilinear_warnings=len(last["diagnostics"].get("bilinear_admissibility_warning_faces",[])),
            sampled_crossings=crossing["sampled_transverse_crossings"],crossing_cap=crossing["sample_limit_reached"],
            ornament_depth=last["ornament"]["maximum"],branch_signatures=branches["unique_branch_signatures"],signature_dominance=branches["dominant_signature_fraction"],
            nested_components=branches["independent_nested_event_components"],finish=summary["recipe"]["finish_mode"],runtime_seconds=summary["runtime_seconds"])
        verification=read(case/"verification.json") if (case/"verification.json").exists() else {}
        row["known_backbone_contacts_retained"]=verification.get("known_backbone_contact_pairs_retained_unchanged")
        table.append(row)
        chosen_views=("front","oblique","detail") if phase=="A" else ("front","oblique","detail","wire","depth","roles")
        for view in chosen_views:
            frame=dict(mesh=str(case.relative_to(STUDY)/"terminal.json"),file=f"views/{phase}/{name}_{view}.png",
                label=f"{name} / {'VALID' if row['technically_valid'] else 'STOP'} / F={row['faces']} / branches={row['branch_signatures']} / {row['finish']}",
                camera="front" if view=="front" else "oblique",bounds=camera[view if view in camera else "detail"],width=900,height=900,wireframe=view=="wire")
            if view=="depth":
                lineage=gz_read(case/"terminal_lineage.json.gz")
                colour={f:r["depth"] for f,r in lineage["history"].items()}
            elif view=="roles":
                signatures=gz_read(case/"terminal_signatures.json.gz"); paths=signatures["paths"]
                codes={"FRAME_SIDE":1,"INNER_CAP":2,"EXTRUSION_SIDE":3,"EXTRUSION_CAP":4}
                colour={}
                for f,rows in signatures["faces"].items():
                    roles={paths[i][-1].split(":")[1] if paths[i] else "SOURCE" for i,w in rows if w>0}
                    colour[f]=codes.get(next(iter(roles)),0) if len(roles)==1 else 5
                frame["legend"]="ROLE: side blue / inner orange / extrusion side purple / cap green / mixed dark"
            else: colour=None
            if colour is not None:
                path=folder/(name+"_"+view+".json"); write(path,colour); frame["depthfile"]=str(path.relative_to(STUDY))
            frames.append(frame)
        if (case/"PRE_FINISH.json.gz").exists():
            path=folder/(name+"_PRE_FINISH.json"); write(path,gz_read(case/"PRE_FINISH.json.gz"))
            frames.append(dict(mesh=str(path.relative_to(STUDY)),file=f"views/{phase}/{name}_PRE_FINISH.png",label=name+" / PRE_FINISH",camera="oblique",bounds=camera["detail"],width=900,height=900))
            sheets.append(dict(file=f"views/{phase}/{name}_finish_comparison.png",title=name+" identical pre-finish input; NO FINISH vs one finish",images=[f"views/{phase}/{name}_PRE_FINISH.png",f"views/{phase}/{name}_detail.png"],columns=2,width=900,height=900))
    for family in ("ABCDE" if phase=="A" else [phase]):
        for view in ("oblique","detail"):
            images=[f["file"] for f in frames if f["file"].endswith("_"+view+".png") and (phase!="A" or Path(f["file"]).name.startswith(family))]
            if images: sheets.append(dict(file=f"views/{phase}/{family}_{view}_sheet.png",title=f"Task20 {phase}/{family} {view}; fixed camera and actual outputs",images=images,columns=3,width=900,height=900))
    write(STUDY/(phase+"_projection_plan.json"),dict(frames=frames,sheets=sheets))
    write(STUDY/(phase+"_table.json"),table)
    if table:
        with (STUDY/(phase+"_table.csv")).open("w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(table[0])); writer.writeheader(); writer.writerows(table)
    print(phase,len(table),"cases",len(frames),"views",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("phase"); parser.add_argument("--study",type=Path,default=STUDY)
    args=parser.parse_args(); STUDY=args.study.resolve()
    if not STUDY.is_relative_to(ROOT/"output/task20"): parser.error("Study must remain in output/task20")
    views(args.phase)
