"""Independent actual G4 native QA and float64 triangle-PLY export.

Only completed genuine early replays are exported. No G5--G7 geometry, ornament,
render-based quality score or repair is introduced. --inspect-only writes nothing.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import time

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

SCHEMAS = {"CHESHIRE_ACTUAL_EARLY_DYNAMIC_REPLAY_V1",
           "CHESHIRE_ACTUAL_EARLY_DYNAMIC_CONNECTED_REPLAY_V1",
           "CHESHIRE_ACTUAL_EARLY_DYNAMIC_BUNDLED_G2_REPLAY_V1",
           "CHESHIRE_ACTUAL_EARLY_DYNAMIC_BRANCHING_REPLAY_V1"}
CHUNK = 131072


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1<<20),b""):h.update(block)
    return h.hexdigest()


def ah(array):return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()
def record(path):return dict(path=str(Path(path).resolve()),sha256=sha(path))
def read(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def topology(xyz,triangles):
    x,t=np.asarray(xyz),np.asarray(triangles)
    if x.ndim!=2 or x.shape[1]!=3 or t.ndim!=2 or t.shape[1]!=3 or not len(t):
        raise ValueError("Positive native triangle geometry is required")
    if not np.isfinite(x).all() or t.min()<0 or t.max()>=len(x):
        raise ValueError("Nonfinite coordinates or invalid native triangle indices")
    minimum=float("inf");maximum=0.;volume=0.
    for begin in range(0,len(t),CHUNK):
        p=x[t[begin:begin+CHUNK]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
        areas=np.linalg.norm(cross,axis=1)/2
        minimum=min(minimum,float(areas.min()));maximum=max(maximum,float(areas.max()))
        volume+=float(np.einsum("ij,ij->",p[:,0],np.cross(p[:,1],p[:,2]))/6)
    a=t.ravel();b=np.roll(t,-1,axis=1).ravel()
    lo=np.minimum(a,b).astype(np.uint64);hi=np.maximum(a,b).astype(np.uint64)
    keys=lo*np.uint64(len(x))+hi
    order=np.argsort(keys,kind="quicksort");sorted_keys=keys[order]
    starts=np.r_[0,np.flatnonzero(np.diff(sorted_keys))+1]
    counts=np.diff(np.r_[starts,len(keys)])
    direction=(a[order]>b[order]).astype(np.int64)
    sums=np.add.reduceat(direction,starts)
    oriented_bad=int(((counts==2)&(sums!=1)).sum())
    unique=sorted_keys[starts];edge_a=(unique//len(x)).astype(np.int64);edge_b=(unique%len(x)).astype(np.int64)
    graph=csr_matrix((np.ones(len(unique),np.uint8),(edge_a,edge_b)),shape=(len(x),len(x)))
    components=int(connected_components(graph,directed=False,return_labels=False))
    used=len(np.unique(t));euler=int(len(x)-len(unique)+len(t))
    result=dict(vertices=len(x),triangles=len(t),edges=len(unique),components=components,
        orphan_vertices=len(x)-used,Euler_characteristic=euler,
        boundary_edges=int((counts==1).sum()),nonmanifold_edges=int((counts>2).sum()),
        inconsistent_oriented_edges=oriented_bad,minimum_triangle_area=minimum,
        maximum_triangle_area=maximum,finite=True,signed_volume=volume,
        self_intersection_certified=False,fabrication_certified=False)
    result["passed"]=bool(components==1 and used==len(x) and euler==2 and
        np.all(counts==2) and oriented_bad==0 and minimum>1e-14)
    if not result["passed"]:raise ValueError("Native topology/positive-area QA failed: "+str(result))
    return result


def snapshots(receipt):
    checked=[]
    for original,row in receipt["source_snapshots"].items():
        path=Path(row["snapshot"])
        if sha(path)!=row["sha256"]:raise ValueError("Executed snapshot changed: "+str(path))
        checked.append(dict(original=original,snapshot=str(path),sha256=row["sha256"],
                            current_source_matches=Path(original).exists() and sha(original)==row["sha256"]))
    return checked


def stage_inputs(folder,name):
    stage=folder/"states"/name;meta=read(stage/"generation.json")
    control=stage/"control_quad.npz"
    if sha(control)!=meta["control_file_sha256"]:raise ValueError("Saved control changed")
    with np.load(control) as z:values={k:z[k] for k in ("xyz","faces","chart")}
    return stage,meta,values


def normalized_g2(current,baseline):
    x,q,c=(current[k] for k in ("xyz","faces","chart"));b=baseline["xyz"]
    if not np.array_equal(q,baseline["faces"]) or not np.array_equal(c,baseline["chart"]):
        return dict(correspondence=False,comparison_performed=False,reason="G2 material topology/chart differ; no nearest-point match invented.")
    h=float(np.ptp(x[:,2]));hb=float(np.ptp(b[:,2]));origin=np.array([0.,0.,x[:,2].min()]);ob=np.array([0.,0.,b[:,2].min()])
    if min(h,hb)<=0:raise ValueError("Invalid G2 height")
    normalized=np.linalg.norm((x-origin)/h-(b-ob)/hb,axis=1)
    aligned=x.copy();aligned[:,2]=ob[2]+(x[:,2]-origin[2])*hb/h
    residual=np.linalg.norm(aligned-b,axis=1);raw=np.linalg.norm(x-b,axis=1)
    return dict(correspondence=True,comparison_performed=True,material_vertices=len(x),
        actual_height_ratio=h/hb,raw_paired_distance_quantiles=np.quantile(raw,[0,.5,.9,.99,1]).tolist(),
        height_normalized_distance_quantiles=np.quantile(normalized,[0,.5,.9,.99,1]).tolist(),
        height_normalized_RMS=float(np.sqrt(np.mean(normalized**2))),
        axial_only_rescaled_distance_quantiles=np.quantile(residual,[0,.5,.9,.99,1]).tolist(),
        normalization_scope="QA only: (X,Y,Z-Zmin)/height; second metric rescales Z only to baseline height. Saved geometry/render coordinates are unchanged.",
        aesthetic_score=False)


def actual_symmetry(stage,control,native,meta):
    n=len(control["xyz"]);rows={}
    with np.load(stage/"evidence.npz") as z:
        for label,axis in (("X",0),("Y",1)):
            vp=z["mirror_"+label.lower()+"_vertex_pairs"];fp=z["mirror_"+label.lower()+"_face_pairs"]
            if vp.shape!=(n,) or not np.array_equal(vp[vp],np.arange(n)):
                raise ValueError("Actual G4 mirror map is invalid")
            target=control["xyz"].copy();target[:,axis]*=-1
            error=float(np.max(np.abs(control["xyz"][vp]-target)))
            native_map=np.r_[vp,n+fp]
            if len(native_map)!=len(native):raise ValueError("Native fan mirror correspondence count differs")
            target=native.copy();target[:,axis]*=-1
            ne=float(np.max(np.abs(native[native_map]-target)))
            if max(error,ne)>1e-9:raise ValueError("Actual reflection coordinate QA failed")
            rows[label]=dict(control_maximum_error=error,native_maximum_error=ne,coordinate_check_passed=True)
    if not meta.get("symmetry",{}).get("passed",False):raise ValueError("Executed oriented mirror receipt did not pass")
    return dict(passed=True,axes=rows,declared_oriented_connectivity_proof=meta["symmetry"],
        independent_check_scope="Actual coordinate involutions on saved controls/native fan centres; oriented cycle proof is hash-bound producer evidence.")


def export_ply(path,x,t):
    if len(x)>=2**32:raise ValueError("PLY uint32 vertex-index budget exceeded")
    header=("ply\nformat binary_little_endian 1.0\ncomment Actual early G4 native triangles\n"
        f"element vertex {len(x)}\nproperty double x\nproperty double y\nproperty double z\n"
        f"element face {len(t)}\nproperty list uchar uint vertex_indices\nend_header\n").encode("ascii")
    dtype=np.dtype([("count","u1"),("indices","<u4",(3,))])
    if path.exists():raise FileExistsError(path)
    with path.open("wb") as f:
        f.write(header)
        for begin in range(0,len(x),CHUNK):np.asarray(x[begin:begin+CHUNK],dtype="<f8").tofile(f)
        for begin in range(0,len(t),CHUNK):
            piece=t[begin:begin+CHUNK];data=np.empty(len(piece),dtype=dtype);data["count"]=3;data["indices"]=piece;data.tofile(f)
    vertices=np.memmap(path,mode="r",offset=len(header),dtype="<f8",shape=x.shape)
    faces=np.memmap(path,mode="r",offset=len(header)+24*len(x),dtype=dtype,shape=(len(t),))
    for begin in range(0,len(x),CHUNK):
        if not np.array_equal(vertices[begin:begin+CHUNK],x[begin:begin+CHUNK]):raise ValueError("PLY vertex readback differs")
    for begin in range(0,len(t),CHUNK):
        p=faces[begin:begin+CHUNK]
        if not np.all(p["count"]==3) or not np.array_equal(p["indices"],t[begin:begin+CHUNK]):raise ValueError("PLY triangle readback differs")
    expected=len(header)+24*len(x)+13*len(t)
    if path.stat().st_size!=expected:raise ValueError("PLY payload size differs")
    del vertices,faces
    return dict(**record(path),bytes=expected,vertex_dtype="little-endian float64",index_dtype="little-endian uint32",full_vertex_readback_exact=True,full_triangle_readback_exact=True)


def main(a):
    start=time.perf_counter();found={}
    for path in sorted(a.root.rglob("RECEIPT.json")):
        r=read(path)
        if r.get("status")!="PASS":continue
        if r.get("schema") not in SCHEMAS:
            if r.get("genuine_early_replay") or r.get("final_stage")=="G04_NEUTRAL":
                raise ValueError("Unsupported completed early-replay schema (not silently skipped): "+str(r.get("schema"))+" at "+str(path))
            continue
        if r.get("final_stage")!="G04_NEUTRAL" or not r.get("genuine_early_replay"):raise ValueError("Completed record is not an actual initial G4 replay")
        sid=r["candidate"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+",sid):raise ValueError("Unsafe candidate ID")
        if sid in found:raise ValueError("Multiple completed producers for "+sid)
        found[sid]=(path,r)
    if "B00" not in found:raise ValueError("Completed B00 baseline is required")
    if a.expected_count is not None and len(found)!=a.expected_count:
        raise ValueError("Expected "+str(a.expected_count)+" completed candidates; found "+str(len(found)))
    _,_,g2base=stage_inputs(found["B00"][0].parent,"G02_OVERLAP")
    _,_,g4base=stage_inputs(found["B00"][0].parent,"G04_NEUTRAL")
    base_height=float(np.ptp(g4base["xyz"][:,2]));rows=[]
    if not a.inspect_only:
        if a.output is None:raise ValueError("--output is required for export")
        a.output.mkdir(parents=True,exist_ok=False);(a.output/"source_snapshot").mkdir()
        shutil.copyfile(__file__,a.output/"source_snapshot"/Path(__file__).name)
    for sid,(path,r) in sorted(found.items()):
        folder=path.parent;stage,meta,control=stage_inputs(folder,"G04_NEUTRAL")
        if meta["control_file_sha256"]!=r["final"]["control_file_sha256"]:raise ValueError("Receipt final control binding differs")
        if sha(folder/"RECIPE.json")!=r["recipe_sha256"]:raise ValueError("Executed recipe changed")
        geometry=stage/"geometry.npz"
        if sha(geometry)!=meta["geometry_file_sha256"]:raise ValueError("Native geometry changed")
        with np.load(geometry) as z:x=z["xyz"];t=z["faces"]
        if ah(x)!=meta["checks"]["native_xyz_sha256"] or ah(t)!=meta["checks"]["native_faces_sha256"]:raise ValueError("Actual native arrays differ from executed hashes")
        checked=snapshots(r);quality=topology(x,t);sym=actual_symmetry(stage,control,x,meta)
        _,_,g2=stage_inputs(folder,"G02_OVERLAP");difference=normalized_g2(g2,g2base)
        box=np.array([x.min(axis=0),x.max(axis=0)]);span=box[1]-box[0]
        row=dict(id=sid,source_receipt=record(path),actual_geometry=record(geometry),quality=quality,
            actual_symmetry=sym,G2_material_shape_comparison=difference,bbox=box.tolist(),physical_extent=span.tolist(),
            actual_height_to_B00_control_height=float(span[2]/base_height),requested_G0_length_scale=r["final"]["dynamic_recipe"].get("length_scale",1.),
            executed_source_snapshots=checked,source_assets_modified=False,beauty_score=False,
            native_mean_fans_preserved=True,self_intersection_or_fabrication_certified=False)
        if not a.inspect_only:
            target=a.output/sid;target.mkdir();row["model"]=export_ply(target/f"CHESHIRE_EARLY_{sid}_G4_NATIVE_FULL.ply",x,t)
            (target/"EXPORT_RECEIPT.json").write_text(json.dumps(row,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
        rows.append(row);print("NATIVE_G4_QA_READY",sid,len(x),len(t),quality["minimum_triangle_area"],flush=True)
    result=dict(kind="ACTUAL_INITIAL_G4_NATIVE_EXPORT_AND_INDEPENDENT_QA",passed=True,completed_count=len(rows),variants=rows,
        source_root=str(a.root.resolve()),accepted_receipt_schemas=sorted(SCHEMAS),baseline_id="B00",final_stage="G04_NEUTRAL",no_G5_G7_or_late_ornament=True,
        failed_replays_preserved=[str(p) for p in sorted(a.root.rglob("FAILED_REPLAY.json"))],
        all_exported_geometry_full_readback_exact=not a.inspect_only,inspection_only=a.inspect_only,
        source=record(__file__),elapsed_seconds=time.perf_counter()-start)
    if not a.inspect_only:(a.output/"NATIVE_EXPORT_AND_QA.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    print("NATIVE_G4_AGGREGATE_READY",len(rows),result["elapsed_seconds"],flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--output",type=Path);p.add_argument("--inspect-only",action="store_true");p.add_argument("--expected-count",type=int);main(p.parse_args())
