"""Load the actual reviewed Task17 evidence, rather than rerun a search in Rhino."""
from copy import deepcopy
import hashlib
import re

from carrier_study import coarse_gate,DIMENSIONS
from cheshire_worker import ROOT,RUNTIME_IDENTITY,mesh_to_data
from exchange import CAPABILITY_MODE,read_json,validate_mesh_data,validate_response


def run_subdivision_capability_study(request,publish=None):
    study=ROOT/"output/task17/study"
    manifest_path=study/"selections.json"
    if not manifest_path.is_file():
        raise ValueError("Task17 reviewed outputs are required at output/task17/study; extract the Task17 review bundle or reproduce the documented study first.")
    manifest=read_json(manifest_path)
    source_path=study/"C0.json"
    if hashlib.sha256(source_path.read_bytes()).hexdigest()!=manifest["source_file_sha256"]:
        raise ValueError("Task17 source evidence changed; no cached comparison loaded.")
    saved=read_json(source_path)
    points=[v["xyz"] for v in request["mesh"]["vertices"]]
    low=[min(p[i] for p in points) for i in range(3)]; high=[max(p[i] for p in points) for i in range(3)]
    size=[b-a for a,b in zip(low,high)]
    if abs(size[0]-4000)>4e-5 or abs(size[2]-3500)>3.5e-5 or not any(abs(size[1]-d)<=9e-6 for d in (500,900)):
        raise ValueError("SubdivisionCapabilityStudy requires the axis-aligned original gate or C0, at original units; no fitting or rescaling.")
    origin=[(low[i]+high[i])/2 for i in (0,1)]+[low[2]]
    stored=[(min(v["xyz"][i] for v in saved["vertices"])+max(v["xyz"][i] for v in saved["vertices"]))/2 for i in (0,1)]+[min(v["xyz"][2] for v in saved["vertices"])]
    translation=[a-b for a,b in zip(origin,stored)]
    def positioned(data):
        copy=deepcopy(data)
        for v in copy["vertices"]: v["xyz"]=[x+d for x,d in zip(v["xyz"],translation)]
        return copy
    response=dict(protocol=1,run_id=request["run_id"],source=request["source"],mode=CAPABILITY_MODE,recipe_version="17.0",status="FAILED",reason=None,
        carrier=dict(mesh=mesh_to_data(coarse_gate(origin)),origin=origin,dimensions=DIMENSIONS),variants=[],runtime_identity=RUNTIME_IDENTITY,
        cached_reviewed_outputs=True,semantic_lineage="NOT IMPLEMENTED",translation=translation,
        monitor_coordinate_frame="Saved-study coordinates: normalized drift is translation invariant; absolute anchor/center values refer to saved C0.",
        design_status=manifest["design_status"],evidence_note=manifest["evidence_note"],
        display_policy="Calculation and OBJ polygons unchanged. Rhino n-gons use display-only fan triangles plus MeshNgon boundary groups; nonplanar polygons are approximate surfaces.")
    entries=manifest["display"]
    if not isinstance(entries,list) or not 1<=len(entries)<=5:
        raise ValueError("Only the concise reviewed Task17 comparison may be loaded.")
    for entry in entries:
        name,generation=entry["case"],entry["generation"]
        if not isinstance(name,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}",name) or type(generation) is not int or not 0<=generation<=6:
            raise ValueError("Invalid local evidence case/generation.")
        path=study/"cases"/name/f"G{generation}.json"
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry["file_sha256"]:
            raise ValueError("Reviewed output changed: "+name)
        data=read_json(path); validate_mesh_data(data,120000,120000,allow_polygons=True)
        response["variants"].append(dict(id=name,generation=generation,roles=entry["roles"],mesh=positioned(data),
            vertex_count=len(data["vertices"]),face_count=len(data["faces"]),validated=True,source_file_sha256=entry["file_sha256"],
            semantic_lineage="NOT IMPLEMENTED",family_counts=entry.get("family_counts",{}),recipe=entry.get("recipe"),
            monitor=entry.get("monitor"),warnings=entry.get("warnings")))
        response["status"]="PARTIAL"; validate_response(response,request)
        if publish: publish(response)
    response["status"]="SUCCESS"; validate_response(response,request)
    if publish: publish(response)
    return response
