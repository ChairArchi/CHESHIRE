"""Independent terminal, signature and checkpoint checks; no extra design search."""
import argparse
from collections import Counter
import gzip
import json
from math import isclose,isfinite
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
for folder in ("examples","rhino"): sys.path.insert(0,str(ROOT/folder))
from cheshire import load_mesh
from cheshire.branching import BranchSignatures
from cheshire.lineage import ParentRef
from subdivision_capability_study import read,write,polygon_mesh
from ornament_study import digest,file_hash
import branching_review
from branching_review import gz_read

STUDY=ROOT/"output/task20/study"


def baseline_signatures():
    source=polygon_mesh(read(STUDY/"C0.json")); results={}
    for label,name,phase in (("C07","F_C07_RETAIN_TERMINAL_EVENT","R"),("C06","F_C06_BOLDER_MESO","R"),("B03","F_B03","B")):
        case=ROOT/"output/task19/study"/phase/name/"attempt_001"
        tracker=BranchSignatures(source); summary=read(case/"summary.json")
        for record in summary["stages"]:
            index=record["stage_index"]; lineage=gz_read(case/f"S{index:02d}_lineage.json.gz")
            parents={int(f):[ParentRef(r["id"],r["weight"]) for r in rows] for f,rows in lineage["face_parents"].items()}
            tracker.advance(parents,dict(events=[e for e in lineage["events"] if e["stage_index"]==index]))
            if label=="C07" and index<=5:
                from ornament_study import gz_write
                gz_write(STUDY/"references"/f"BACKBONE_S{index:02d}_lineage.json.gz",lineage)
                gz_write(STUDY/"references"/f"BACKBONE_S{index:02d}_signatures.json.gz",tracker.to_data())
        result=tracker.diagnostics({int(k):v for k,v in lineage["history"].items()},lineage["events"])
        write(STUDY/"references"/(label+"_branch_signatures.json"),result)
        from ornament_study import gz_write
        gz_write(STUDY/"references"/(label+"_signature_paths.json.gz"),tracker.to_data())
        results[label]=result
    write(STUDY/"baseline_branch_signatures.json",results)


def verify(phase):
    branching_review.STUDY=STUDY
    source_ids={f["id"] for f in read(STUDY/"C0.json")["faces"]}; results=[]
    camera=read(ROOT/"studies/task19/camera.json")["bounds"]
    for case in branching_review.cases(phase):
        summary=read(case/"summary.json")
        if not summary.get("artifacts"): continue
        assert all(file_hash(case/name)==value for name,value in summary["artifacts"].items())
        if (case/"verification.json").exists():
            previous=read(case/"verification.json")
            if previous.get("audit_version")==2 and previous.get("output_sha256")==summary["output_sha256"] and previous.get("artifacts_sha256")==digest(summary["artifacts"]):
                results.append(previous); print(phase,case.parent.name,"verified artifact cache",flush=True); continue
        data=read(case/"terminal.json"); mesh=polygon_mesh(data); reload=load_mesh(case/"terminal.obj")
        keys=list(mesh.vertices()); index={v:i for i,v in enumerate(keys)}
        assert [reload.vertex_coordinates(v) for v in reload.vertices()]==[mesh.vertex_coordinates(v) for v in keys]
        assert [reload.face_vertices(f) for f in reload.faces()]==[[index[v] for v in mesh.face_vertices(f)] for f in mesh.faces()]
        assert digest(data)==summary["output_sha256"]
        checkpoint_count=0
        for path in [case/"terminal_lineage.json.gz",*sorted(case.glob("S*_lineage.json.gz"))]:
            lineage=gz_read(path); events={e["id"]:e for e in lineage["events"]}
            geometry=data if path.name.startswith("terminal") else gz_read(case/(path.name.split("_")[0]+".json.gz"))
            assert set(map(int,lineage["history"]))=={f["id"] for f in geometry["faces"]}
            for row in lineage["history"].values():
                assert set(map(int,row["source"]))<=source_ids
                assert isclose(sum(row["source"].values()),1,abs_tol=1e-9) and all(isfinite(w) and w>0 for w in row["source"].values())
                assert row["depth"]==max((events[e]["ornament_depth"] for e in row["events"]),default=0)
            for event in events.values():
                assert event["ornament_depth"]==max((events[e]["ornament_depth"] for e in event["parent_event_ids"]),default=0)+1
            signatures=gz_read(case/"terminal_signatures.json.gz" if path.name.startswith("terminal") else case/(path.name.split("_")[0]+"_signatures.json.gz"))
            assert set(map(int,signatures["faces"]))=={f["id"] for f in geometry["faces"]}
            for face,rows in signatures["faces"].items():
                assert all(w>0 and isfinite(w) for _,w in rows) and isclose(sum(w for _,w in rows),1,abs_tol=1e-9)
                assert max(len(signatures["paths"][i]) for i,_ in rows)==lineage["history"][face]["depth"]
            checkpoint_count+=1
        terminal=gz_read(case/"terminal_lineage.json.gz"); terminal_signatures=gz_read(case/"terminal_signatures.json.gz")
        # Fixed original contacts are a separate cohort: changing terminal face
        # count changes the evenly spaced sample and can hide inherited contacts.
        cohort_file=STUDY/"backbone_crossing_check/crossing_audit.json"
        retained=[]
        if cohort_file.exists():
            backbone=gz_read(STUDY/"references/BACKBONE_S05.json.gz")
            source_faces={f["id"]:f for f in backbone["faces"]}; source_xyz={v["id"]:v["xyz"] for v in backbone["vertices"]}
            output_faces={f["id"]:f for f in data["faces"]}; output_xyz={v["id"]:v["xyz"] for v in data["vertices"]}
            for contact in read(cohort_file)["candidates"][0]["contacts"]:
                if all(source_faces[f]==output_faces.get(f) and all(source_xyz[v]==output_xyz.get(v) for v in source_faces[f]["vertices"]) for f in contact["faces"]): retained.append(contact)
        event_counts=Counter()
        for e in terminal["events"]:
            paths={(*p["path"],e["operator"]+":"+role) for p in e["parent_branch_signatures"] for role in {c["role"] for c in e["children"]}}
            event_counts.update(paths)
        stats=read(case/"branch_signatures.json"); stats["constructed_signatures_including_consumed"]=len(event_counts)
        masses={tuple(r["path"]):r for r in stats["signatures"]}
        stats["all_constructed_signature_rows"]=[dict(path=list(p),events=count,terminal_face_mass=masses.get(p,{}).get("terminal_face_mass",0),terminal_face_presence=masses.get(p,{}).get("terminal_face_presence",0)) for p,count in sorted(event_counts.items())]
        write(case/"branch_signature_verification.json",stats)
        clips={}
        for view in ("front","oblique"):
            b=camera[view]
            clips[view]=sum(not(b[0]<=v["xyz"][0]+(.65*v["xyz"][1] if view=="oblique" else 0)<=b[1] and b[2]<=v["xyz"][2]+(.30*v["xyz"][1] if view=="oblique" else 0)<=b[3]) for v in data["vertices"])
        result=dict(id=case.parent.name,technically_valid=summary["technically_valid"],finite=all(isfinite(x) for v in data["vertices"] for x in v["xyz"]),
            valid=mesh.is_valid(),manifold=mesh.is_manifold(),closed=mesh.is_closed(),components=len(mesh.connected_vertices()),
            exact_OBJ_roundtrip=True,positive_source_and_signature_mass_verified=True,event_depth_DAG_verified=True,
            lineage_checkpoints=checkpoint_count,whole_camera_clipped_vertices=clips,
            sampled_crossings=read(case/"terminal_crossings.json")["sampled_transverse_crossings"],
            terminal_signatures=stats["unique_branch_signatures"],constructed_signatures=stats["constructed_signatures_including_consumed"],
            known_backbone_contact_pairs_retained_unchanged=len(retained),known_backbone_contacts=retained,
            cohort_scope="Exact face-cycle/XYZ retention of full C07 Stage-5 contacts. Zero retention after geometry changes does not certify resolution.",
            output_sha256=summary["output_sha256"],artifacts_sha256=digest(summary["artifacts"]),audit_version=2)
        write(case/"verification.json",result); results.append(result)
        print(phase,result["id"],result["technically_valid"],result["sampled_crossings"],flush=True)
    write(STUDY/(phase+"_verification.json"),results)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("phase",nargs="?"); parser.add_argument("--references",action="store_true"); args=parser.parse_args()
    if args.references: baseline_signatures()
    if args.phase: verify(args.phase)
