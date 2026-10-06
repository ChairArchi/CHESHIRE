"""Independent task evidence checks, terminal crossings and exact OBJ reloads."""
import argparse
import gzip
import json
from math import isclose, isfinite
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"examples")); sys.path.insert(0,str(ROOT/"tools")); sys.path.insert(0,str(ROOT/"rhino"))
from cheshire import load_mesh
from cheshire_worker import mesh_to_data
from subdivision_capability_study import read,write,polygon_mesh
from ornament_review import cases,STUDY
from ornament_process import bounded_worker
from ornament_study import digest,file_hash

def nested_components(events):
    """Count connected event genealogies; multiple roots may merge via DS."""
    roots={}; representatives={}; nested=set()
    def find(key):
        while representatives[key]!=key:
            representatives[key]=representatives[representatives[key]]; key=representatives[key]
        return key
    for event in events:
        ancestors=event["parent_event_ids"]
        branch=set().union(*(roots[key] for key in ancestors)) if ancestors else {event["id"]}
        roots[event["id"]]=branch
        for key in branch: representatives.setdefault(key,key)
        if ancestors:
            nested.update(branch)
            first=min(branch)
            for key in branch: representatives[find(key)]=find(first)
    groups={}
    for key in sorted(nested): groups.setdefault(find(key),[]).append(key)
    return dict(nested_root_count=len(nested),independent_nested_event_components=len(groups),
        merged_root_groups=[keys for keys in groups.values() if len(keys)>1],
        scope="Connected components of nested discrete-event ancestry; subdivision alone creates no event node. Root count is not disjoint-tree count.")

def verify(phase):
    source=polygon_mesh(read(STUDY/"C0.json")); source_ids=set(source.faces()); results=[]
    for case in cases(phase):
        if not (case/"terminal.json").exists(): continue
        summary=read(case/"summary.json")
        cache=case/"verification.json"
        if cache.exists():
            previous=read(cache)
            if previous.get("output_sha256")==summary.get("output_sha256") and previous.get("artifacts_manifest_sha256")==digest(summary.get("artifacts")) and all(file_hash(case/name)==value for name,value in summary["artifacts"].items()):
                results.append(previous); print(phase,case.parent.name,"VERIFIED CACHE",flush=True); continue
        data=read(case/"terminal.json"); mesh=polygon_mesh(data)
        if not (case/"terminal.obj").exists():
            results.append(dict(id=case.parent.name,status=summary["status"],verification="No exported terminal; process failure")); continue
        reload=load_mesh(case/"terminal.obj"); vertex_keys=list(mesh.vertices()); index={v:i for i,v in enumerate(vertex_keys)}
        assert [reload.vertex_coordinates(v) for v in reload.vertices()]==[mesh.vertex_coordinates(v) for v in vertex_keys]
        assert [reload.face_vertices(f) for f in reload.faces()]==[[index[v] for v in mesh.face_vertices(f)] for f in mesh.faces()]
        if summary.get("artifacts"):
            assert all(file_hash(case/name)==value for name,value in summary["artifacts"].items())
        assert digest(data)==summary["output_sha256"]
        checkpoint_count=0; terminal_components=None
        for path in [case/"terminal_lineage.json.gz",*sorted(case.glob("S*_lineage.json.gz"))]:
            with gzip.open(path,"rt",encoding="utf-8") as stream: lineage=json.load(stream)
            geometry=data if path.name.startswith("terminal") else read(case/(path.name.split("_")[0]+".json"))
            assert set(map(int,lineage["history"]))=={f["id"] for f in geometry["faces"]}
            event_map={e["id"]:e for e in lineage["events"]}
            for row in lineage["history"].values():
                assert set(map(int,row["source"]))<=source_ids and isclose(sum(row["source"].values()),1,abs_tol=1e-9)
                assert all(w>0 and isfinite(w) for w in row["source"].values())
                assert row["depth"]==max((event_map[e]["ornament_depth"] for e in row["events"]),default=0)
                assert all(any(e["stage"]==stage and any(c["role"]==role for c in e["children"]) for e in (event_map[k] for k in row["events"])) for stage,role in row["roles"])
            for event in lineage["events"]:
                assert event["ornament_depth"]==max((event_map[k]["ornament_depth"] for k in event["parent_event_ids"]),default=0)+1
            if path.name.startswith("terminal"): terminal_components=nested_components(lineage["events"])
            checkpoint_count+=1
        sample=data["faces"] if len(data["faces"])<=4096 else [data["faces"][i*len(data["faces"])//4096] for i in range(4096)]
        used={v for f in sample for v in f["vertices"]}
        audit=case/"terminal_audit"; audit.mkdir(exist_ok=True)
        write(audit/"request.json",dict(mesh=read(STUDY/"C0.json")))
        write(audit/"response.json",dict(variants=[dict(id=case.parent.name,mesh=dict(vertices=[v for v in data["vertices"] if v["id"] in used],faces=sample))]))
        if not (audit/"crossing_audit.json").exists():
            process=bounded_worker([ROOT/"tools/morphology_crossings.py",audit],audit/"logs",90)
            write(audit/"process.json",process)
            if process["exit_code"]: raise ValueError("Terminal audit failed: "+str(case))
        crossing=read(audit/"crossing_audit.json")["candidates"][0]
        camera=read(ROOT/"studies/task18/camera.json")["bounds"]
        clips={}
        for view in ("front","oblique"):
            bounds=camera[view]; clips[view]=sum(not(bounds[0]<=p[0]+(.65*p[1] if view=="oblique" else 0)<=bounds[1] and
                bounds[2]<=p[2]+(.30*p[1] if view=="oblique" else 0)<=bounds[3]) for p in [v["xyz"] for v in data["vertices"]])
        result=dict(id=case.parent.name,path=str(case.relative_to(STUDY)),status=summary["status"],
            vertices=mesh.number_of_vertices(),faces=mesh.number_of_faces(),edges=mesh.number_of_edges(),
            finite=all(isfinite(x) for v in data["vertices"] for x in v["xyz"]),valid=mesh.is_valid(),manifold=mesh.is_manifold(),closed=mesh.is_closed(),components=len(mesh.connected_vertices()),
            OBJ_exact_roundtrip=True,verified_lineage_checkpoints=checkpoint_count,source_ancestry_verified=True,event_depth_DAG_verified=True,
            sampled_crossings=crossing["sampled_transverse_crossings"],crossing_sample_faces=len(sample),crossing_cap=crossing["sample_limit_reached"],whole_camera_clipped_vertices=clips,
            technically_valid=summary["status"]=="SUCCESS" and not crossing["sample_limit_reached"],
            output_sha256=summary["output_sha256"],artifacts_manifest_sha256=digest(summary["artifacts"]),nested_ancestry_components=terminal_components)
        write(cache,result)
        results.append(result); print(phase,result["id"],result["technically_valid"],result["sampled_crossings"],flush=True)
    write(STUDY/(phase+"_verification.json"),results)

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("phase",choices=("A","B","R","E","REPLAY")); parser.add_argument("--study",type=Path,default=STUDY); args=parser.parse_args()
    STUDY=args.study.resolve()
    import ornament_review
    ornament_review.STUDY=STUDY
    if not STUDY.is_relative_to(ROOT/"output/task19"): parser.error("Study must remain in output/task19")
    verify(args.phase)
