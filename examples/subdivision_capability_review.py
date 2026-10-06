"""Matched, unembellished headless views of actual Task17 polygons."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from subdivision_capability_study import STUDY,read,write


def observations():
    records=[]
    for directory in sorted((STUDY/"cases").iterdir()):
        if not (directory/"summary.json").exists(): continue
        summary=read(directory/"summary.json"); stages=summary["stages"]; last=stages[-1]
        original=directory/"task16_original_summary.json"
        if original.exists():
            reference={s["generation"]:s for s in read(original)["stages"]}
            for s in stages:
                if s["generation"] in reference: s["diagnostics"]=reference[s["generation"]]["diagnostics"]
        audit_path=directory/"crossing_audit.json"
        if not audit_path.exists(): audit_path=directory/"task16_original_crossing_audit.json"
        audit=read(audit_path) if audit_path.exists() else {}
        row=dict(id=directory.name,status=summary["status"],reason=summary.get("reason"),generations_reached=last["generation"],
            final_family_counts=last.get("family_counts"),final_fallback_faces=last.get("fallback_faces"),
            trajectory=[dict(generation=s["generation"],family_counts=s.get("family_counts"),fallback_faces=s.get("fallback_faces"),
                fallback_groups=s.get("fallback_groups"),statistics=s["statistics"],monitor=s["monitor"],
                diagnostic_counts={key:len(s["diagnostics"][key]) if key in s.get("diagnostics",{}) else None for key in ("degenerate_fan_faces","opposed_fan_normals","bilinear_admissibility_warning_faces")}) for s in stages],
            crossings=audit.get("candidates"),crossing_scope=("Original retained Task16 scope: "+audit.get("scope","") if original.exists() else "At most 4096 evenly spaced actual faces per generation; transverse nonadjacent contacts only."))
        records.append(row)
        m=last["monitor"]; d=last.get("diagnostics",{})
        print(directory.name,summary["status"],"G"+str(last["generation"]),"opening",{k:round(v,3) if v is not None else None for k,v in m["opening_normalized"].items()},
            "dim%",{k:round(v,1) for k,v in m["dimensions_drift_percent"].items()},"fan/bilinear",len(d.get("opposed_fan_normals",[])),len(d.get("bilinear_admissibility_warning_faces",[])),
            "crossings",[a["sampled_transverse_crossings"] for a in audit.get("candidates",[])])
    write(STUDY/"raw_trajectories.json",records)


def plan(names,label="progress",details=False,checkpoints=None,bounds_from=None):
    atlas=STUDY/"views"; atlas.mkdir(exist_ok=True)
    paths=[p for name in names for p in sorted((STUDY/"cases"/name).glob("G?.json"))]
    for name in names:
        if not list((STUDY/"cases"/name).glob("G?.json")):
            raise ValueError("No completed checkpoint for "+name)
    if not paths: raise ValueError("No completed geometry.")
    # Union extent from actual geometry; one shared scale, not separate fitting.
    coordinates=[v["xyz"] for p in paths for v in read(p)["vertices"]]
    u=[p[0]+.65*p[1] for p in coordinates]; z=[p[2]+.3*p[1] for p in coordinates]
    width=max(u)-min(u); height=max(z)-min(z)
    oblique=[min(u)-.06*width,max(u)+.06*width,min(z)-.06*height,max(z)+.06*height]
    xs=[p[0] for p in coordinates]; zs=[p[2] for p in coordinates]
    front=[min(xs)-.06*width,max(xs)+.06*width,min(zs)-.06*height,max(zs)+.06*height]
    source=read(STUDY/"C0.json")["vertices"]; center=sum(v["xyz"][0] for v in source)/len(source)
    # Fixed source-registered LEFT inner shoulder, same crop even if it moves away.
    detail=[center-2100,center-450,1800,3450]
    if bounds_from:
        shared=read(bounds_from)["bounds"]
        oblique,front,detail=(shared[key] for key in ("oblique","front","detail"))
    frames=[]; sheets=[]; w,h=650,670
    for name in names:
        available=sorted((STUDY/"cases"/name).glob("G?.json"))
        images=[]
        for path in available:
            file=f"{label}_{name}_{path.stem}.png"; images.append(file)
            frames.append(dict(mesh="../cases/"+name+"/"+path.name,file=file,width=w,height=h,bounds=oblique,camera="oblique",label=name+" / "+path.stem))
        sheets.append(dict(file=f"{label}_{name}_progression.png",title=name+" / actual retained generations",images=images,columns=4,width=w,height=h))
    last=[(name,STUDY/"cases"/name/f"G{checkpoints[name]}.json" if checkpoints and name in checkpoints else sorted((STUDY/"cases"/name).glob("G?.json"))[-1]) for name in names]
    images=[f"{label}_{name}_{path.stem}.png" for name,path in last]
    sheets.append(dict(file=f"{label}_terminal_comparison.png",title="Same-scale comparison / explicitly selected completed checkpoints",images=images,columns=min(4,len(images)),width=w,height=h))
    if details:
        for kind,bounds,camera,extra in (("front",front,"front",dict(silhouette=True)),("wire",oblique,"oblique",dict(wireframe=True)),("detail",detail,"oblique",{})):
            images=[]
            for name,path in last:
                file=f"{label}_{name}_{kind}.png"; images.append(file)
                frames.append(dict(mesh="../cases/"+name+"/"+path.name,file=file,width=w,height=h,bounds=bounds,camera=camera,label=name+" / "+path.stem+" / "+kind,**extra))
            sheets.append(dict(file=f"{label}_{kind}_comparison.png",title=kind+" / fixed registered camera and scale",images=images,columns=min(4,len(images)),width=w,height=h))
    write(atlas/(label+"_plan.json"),dict(frames=frames,sheets=sheets,bounds=dict(oblique=oblique,front=front,detail=detail),
        caveat="Approximate polygon painter, fixed orthographic projection; nonplanar polygons shade from first three corners. Not Rhino, collision evidence or a hidden-line certificate. Detail crop is unchanged when geometry leaves it."))
    print(atlas/(label+"_plan.json"))


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("names",nargs="*"); parser.add_argument("--label",default="progress"); parser.add_argument("--details",action="store_true")
    parser.add_argument("--observations",action="store_true")
    parser.add_argument("--at",nargs="*",default=[],help="Explicit selected terminal images, CASE=GENERATION; progression still retains all reached generations.")
    parser.add_argument("--bounds-from",type=Path,help="Reuse the exact whole/detail scale from another retained plan.")
    args=parser.parse_args()
    if args.observations: observations()
    if args.names: plan(args.names,args.label,args.details,dict((name,int(g)) for name,g in (item.split("=") for item in args.at)),args.bounds_from)
