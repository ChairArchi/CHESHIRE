"""Verify reusable topology-only lineage and all actual retained field outputs.

Uniform geometry is recomputed once per grammar, never reused as modulated
geometry. Positive parent associations are shared only after exact ordered
topology equality is verified for every checkpoint in every case.
"""
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spatial_activity_study import ROOT, STUDY, FROZEN, read, write, digest, polygon_mesh, mesh_to_data
from cheshire.activity import ActivityField, inherit_values
from cheshire.execution import ExecutionBudget
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.weighted_doosabin import weighted_doosabin_once
from cheshire.mesh_io import load_mesh


def topology(data):
    return dict(vertices=[v["id"] for v in data["vertices"]], faces=data["faces"])


def verify():
    outcomes = read(STUDY/"outcomes.json"); caches = {}; topology_hashes = {}
    source = read(FROZEN/"C0.json"); frozen = read(FROZEN/"fields.json")
    for grammar in ("CC", "DS", "HYBRID"):
        candidates = [r for r in outcomes if r.get("spec", {}).get("grammar")==grammar and r["spec"]["strategy"]=="U" and r["status"]=="SUCCESS"]
        candidate = max(candidates, key=lambda r:r["generations_reached"])
        directory = STUDY/"cases"/candidate["id"]; records = read(directory/"summary.json")["stages"]
        mesh = polygon_mesh(source); origins = None; families = None; caches[grammar] = {}; topology_hashes[grammar] = {}
        for record in records[1:]:
            g = record["generation"]
            if record["scheme"]=="CC":
                step = generational_subdivide_once(mesh,record["weights"],origin_lineage=origins,
                    budget=ExecutionBudget(120000,120000,6),current_generation=g-1)
                origins = step.origin_lineage
                parents = step.sampling_parents
                lineage = dict(sampling_parents=parents,origin_lineage=origins)
            else:
                step = weighted_doosabin_once(mesh,record["weights"],face_families=families,
                    budget=ExecutionBudget(120000,120000,6),current_generation=g-1)
                families = step.face_families
                parents = {v:[(p.key,p.weight) for p in refs] for v,refs in step.lineage.vertex_parents.items()}
                lineage = dict(sampling_parents=parents,face_families=families,corner_parents=step.corner_parents,
                    face_parents={f:[(p.key,p.weight) for p in refs] for f,refs in step.lineage.face_parents.items()})
            actual = read(directory/f"G{g}.json")
            if digest(mesh_to_data(step.mesh)) != record["geometry_hash"]:
                raise AssertionError("Uniform recomputation changed actual geometry.")
            topology_hashes[grammar][g] = digest(topology(actual)); caches[grammar][g] = parents
            path = STUDY/"lineage_cache"/grammar/f"G{g}.json.gz"; path.parent.mkdir(parents=True,exist_ok=True)
            with gzip.open(path,"wt",encoding="utf-8",compresslevel=1) as stream:
                json.dump(dict(generation=g,grammar=grammar,source_case=candidate["id"],
                    topology_hash=topology_hashes[grammar][g],
                    policy="Actual existing operator positive sampling and constructive origins; reusable only under verified identical ordered IDs/cycles. Signed geometry and semantic tags are not inferred.",**lineage),stream,separators=(",",":"))
            mesh = step.mesh
        print("cached",grammar,len(caches[grammar]),flush=True)
    checked=[]; obj_checks=[]; clipping=[]
    bounds=read(FROZEN/"camera.json")["bounds"]
    for outcome in outcomes:
        if outcome["status"]!="SUCCESS": continue
        spec=outcome["spec"]; directory=STUDY/"cases"/outcome["id"]
        records=read(directory/"summary.json")["stages"]
        bank={k:{int(v):x for v,x in values.items()} for k,values in frozen["layouts"][spec["seed"]]["fields"].items()}
        for record in records:
            g=record["generation"]; data=read(directory/f"G{g}.json")
            if g:
                if digest(topology(data))!=topology_hashes[spec["grammar"]][g]:
                    raise AssertionError("Topology-dependent cache is invalid for "+spec["id"])
                bank={k:inherit_values(values,caches[spec["grammar"]][g]) for k,values in bank.items()}
                if {k:digest(values) for k,values in bank.items()}!=record["propagated_field_hashes"]:
                    raise AssertionError("Inherited scalar fields differ for "+spec["id"])
                with gzip.open(directory/f"G{g}_fields.json.gz","rt",encoding="utf-8") as stream: saved=json.load(stream)
                if {k:digest(values) for k,values in saved.items()}!=record["propagated_field_hashes"]:
                    raise AssertionError("Saved field channels changed.")
                checked.append(dict(id=spec["id"],generation=g,topology="EXACT",field_hashes="EXACT"))
            for camera in ("oblique","front"):
                low,high,bottom,top=bounds[camera]
                outside=0
                for v in data["vertices"]:
                    x,y,z=v["xyz"]; u=x+.65*y if camera=="oblique" else x; height=z+.3*y if camera=="oblique" else z
                    outside+=not (low<=u<=high and bottom<=height<=top)
                if outside: clipping.append(dict(id=spec["id"],generation=g,camera=camera,outside_vertices=outside))
            if g==spec["generations"] or spec["stage"]=="B":
                loaded=load_mesh(directory/f"G{g}.obj")
                index={v["id"]:i for i,v in enumerate(data["vertices"])}
                if [loaded.vertex_coordinates(v) for v in loaded.vertices()] != [v["xyz"] for v in data["vertices"]] or [loaded.face_vertices(f) for f in loaded.faces()] != [[index[v] for v in f["vertices"]] for f in data["faces"]]:
                    raise AssertionError("OBJ roundtrip changed coordinates or polygon cycles.")
                obj_checks.append(dict(id=spec["id"],generation=g,status="EXACT ordered coordinates/cycles"))
        print("verified",spec["id"],flush=True)
    write(STUDY/"verification.json",dict(topology_and_source_field_checks=checked,obj_roundtrips=obj_checks,
        uniform_exact=all(r["uniform_exact_all_generations"] for r in outcomes if r.get("spec",{}).get("strategy")=="U"),
        whole_camera_clipping=clipping,semantic_lineage="Activity-only positive source associations; architectural/categorical semantics remain unavailable",
        cache_scope="Same fixed-topology uniform grammar per generation, with exact ordered topology checked for every modulated output; no cross-case geometry cache"))
    print("PASS",len(checked),"field/topology checks",len(obj_checks),"OBJ checks; whole-view clipping",len(clipping),flush=True)


if __name__=="__main__": verify()
