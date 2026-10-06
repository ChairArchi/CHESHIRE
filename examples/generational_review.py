"""Task 16 evidence audit and fixed supplemental views, without new analysis."""
import argparse
import gzip
import hashlib
import json
from math import dist
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "rhino"))
sys.path.insert(0,str(ROOT / "examples"))
from cheshire_worker import mesh_from_data,mesh_to_data
from cheshire.validation import inspect_mesh
from generational_study import run_choreography
from generational_weight_study import read,write,compressed,BASELINE

# Observations from the matched saved G0-G5 sheets, not metric-based scores.
OBSERVATIONS={
    "P01_vertex_bias": ("G2 blunts the broad shoulder peaks; G3 begins rounding them.","G4/G5 give pillows and fine repetitive bands, with sampled crossings.","REJECT: rounding and crossings"),
    "P02_face_bias": ("Secondary shoulder facets and support lobes emerge at G2/G3.","Some secondary relief persists, but fine generations mostly round and rib it.","WEAK: useful probe direction, incomplete hierarchy"),
    "P03_VF_pair_bias": ("VF emphasis retains shoulder/lintel ridges better than L4.","G4/G5 retain those ridges but mainly add repeated bands.","WEAK: useful probe direction, incomplete hierarchy"),
    "P04_edge_pair_bias": ("G2 briefly facets the supports; G3 smooths this away.","G4/G5 produce rounded supports and a smooth lintel.","REJECT: rounding"),
    "C05_meso_face_lock": ("Meso lobes and shoulder folds develop.","Fine bands pinch and fold; crossings invalidate preference.","REJECT: crossings/local flags"),
    "C06_vertex_pulse": ("The V pulse flattens G1 shoulder peaks; later F bias adds shallow facets.","The broad forms mostly become rounded pillows with small repetitive relief.","REJECT: weak meso persistence"),
    "C07_diagonal_alternation": ("The class reversal changes facets, but weakens the secondary structure.","Late alternation gives shallow bands over a rounded gate.","REJECT: no useful hierarchy from alternation"),
    "C08_face_then_edges": ("G2/G3 show split support lobes and a faceted lintel.","The edge release weakens those folds; fine result remains ribbed and locally flagged.","REJECT: repetitive tail and local flags"),
    "C09_meso_ridge_hold": ("G2/G3 differentiate paired support lobes, shoulder ridges and lintel bands.","Meso ridges persist into G5; fine detail is still repeated corrugation.","RETAIN PARTIAL: ridge-hold example, same observed family as C11"),
    "C10_nested_face_emphasis": ("Extrapolation retains sharper shoulder stars and split support masses.","Deep fans/pinching persist, with many local flags and crossings.","REJECT: aggressive folds/crossings"),
    "C11_interpolation_release": ("G2/G3 retain secondary support lobes, shoulder peaks and lintel ridges.","G4/G5 keep this meso subdivision with an attenuated but repetitive fine surface.","BEST PARTIAL: split-lobe/ridge retention; micro transition incomplete"),
    "C12_class_lock_low_extrusion": ("The meso prefix creates secondary folds.","Persistent fine class bias produces dense local inversion/pinching flags; zero sampled crossings is insufficient.","REJECT: local flags and repetitive ribs"),
    "R13_restrained_ridges": ("The restrained C09 prefix keeps paired support lobes and shoulder/lintel ridges.","Later detail becomes rounded corrugation; flags remain higher than C11.","WEAK: no clearer hierarchy than C11"),
    "R14_detail_class_shift": ("The C09-like meso structure is initially readable.","The fine V shift rounds off part of the secondary structure; fewer final flags but no distinct micro vocabulary.","RETAIN PARTIAL: quieter fine-tail comparison, not a separate family"),
    "R15_release_ridge_hold": ("The C11 meso prefix is preserved.","The VF tail strengthens repetitive bands and local pinching rather than finer branches.","REJECT: more flags without better hierarchy"),
    "R16_delayed_micro_class": ("The C11 meso prefix is preserved.","More late extrusion adds subordinate-size corrugation, but not a convincing new nested scale; flags increase.","REJECT: repetitive micro transition/local flags"),
}


def audit(study):
    source=read(study / "C0.json")
    assert read(study / "zero_weight_regression.json")["status"] == "PASS"
    stages=[]; output_metadata_checks=[]
    for path in sorted((study / "cases").glob("*/summary.json")):
        summary=read(path); request=read(path.parent / "request.json")
        process=read(study / f"logs/{path.parent.name}/process.json")
        assert request["mesh"] == source and summary["source_immutable"]
        assert request["runtime_identity"]["ignore_environment"] and request["runtime_identity"]["no_user_site"]
        assert not request["spatial_modulation"] and len(request["schedule"])==5
        assert all(set(row)=={"wf","w1","we","w2","wp","w3","w4"} for row in request["schedule"])
        assert process["exit_code"] == 0 and process["stop"] is None and process["seconds"] <= 60
        assert process["peak_combined_resident_bytes"] <= 4*1024**3
        with gzip.open(path.parent / "result.json.gz","rt",encoding="utf-8") as stream:
            full=json.load(stream)
        for stage,thin in zip(full["stages"],summary["stages"]):
            g=stage["generation"]; actual=inspect_mesh(mesh_from_data(stage["mesh"]))
            output_metadata_checks.append(dict(case=path.parent.name,generation=g,
                backend_output_matches_actual=stage["metadata"]["output"]==actual))
            assert stage["mesh"] == read(path.parent / f"G{g}.json")
            assert len(stage["origin_lineage"]) == stage["vertex_count"]
            assert all(row["generation"]==g for row in stage["origin_lineage"])
            assert set(row["class"] for row in stage["origin_lineage"])=={"VERTEX_DERIVED","EDGE_DERIVED","FACE_DERIVED"}
            assert stage["vertex_count"] <= 50000 and stage["face_count"] <= 50000
            expected=(22*4**(g-1)) if g > 1 else 0
            assert thin["later_stencil"]["eligible_faces"] == expected
            assert thin["later_stencil"]["fallback_faces"] == (22 if g==1 else 0)
            assert thin["statistics"]["components"]==1 and thin["statistics"]["boundary_edge_count"]==0
            if g==1 and path.parent.name!="CONTROL_S":
                assert stage["mesh"]==read(study / "cases/CONTROL_L4/G1.json")
            stages.append(dict(case=path.parent.name,generation=g,vertices=stage["vertex_count"],faces=stage["face_count"],
                eligible=expected,fallback=thin["later_stencil"]["fallback_faces"],fan=len(thin["diagnostics"]["opposed_fan_normals"]),
                bilinear=len(thin["diagnostics"]["bilinear_admissibility_warning_faces"]),
                crossings=thin["sampled_crossings"]["sampled_transverse_crossings"],generation_seconds=stage["generation_seconds"]))
    operator=(ROOT / "src/cheshire/weighted_subdivision.py").read_bytes().replace(b"\r\n",b"\n")
    original=subprocess.check_output(["git","show",BASELINE+":src/cheshire/weighted_subdivision.py"],cwd=ROOT).replace(b"\r\n",b"\n")
    assert operator==original
    write(study / "evidence_audit.json",dict(baseline=BASELINE,stages=stages,
        equation_1_2_3_source_unchanged=True,operator_sha256=hashlib.sha256(original).hexdigest(),
        source_and_schedules_checked=True,origins_and_eligibility_checked=True,worker_isolation_and_limits_checked=True,
        output_metadata_checks=output_metadata_checks,semantic_lineage="NOT IMPLEMENTED"))
    # Standard closed control is independently compared with public COMPAS.
    expected=mesh_from_data(source)
    errors=[]
    for g in range(1,6):
        expected=expected.subdivided(scheme="catmullclark",k=1)
        actual=mesh_from_data(read(study / f"cases/CONTROL_S/G{g}.json"))
        error=max(dist(actual.vertex_coordinates(v),expected.vertex_coordinates(v)) for v in actual.vertices())
        assert error <= 1e-9
        errors.append(dict(generation=g,max_coordinate_distance=error))
    write(study / "standard_control_regression.json",dict(status="PASS",absolute_coordinate_tolerance=1e-9,
        closed_C0_public_COMPAS_control=True,checkpoints=errors))
    print("AUDIT PASS",len(stages),"completed stages; stale bbox metadata:",sum(not c["backend_output_matches_actual"] for c in output_metadata_checks),flush=True)


def report(study):
    """Read existing diagnostics; annotate topological warning locations only."""
    source=mesh_from_data(read(study / "C0.json"))
    junctions={v for v in source.vertices() if source.vertex_coordinates(v)[2]==2600.}
    rows=[]; locations=[]
    for path in sorted((study / "cases").glob("*/summary.json")):
        name=path.parent.name
        if name.startswith("REPEAT_"): continue
        data=read(path); stages=[]
        for stage in data["stages"]:
            d=stage["diagnostics"]; g=stage["generation"]
            mesh=mesh_from_data(read(path.parent / f"G{g}.json"))
            fan=set(d["opposed_fan_normals"]); bilinear=set(d["bilinear_admissibility_warning_faces"])
            flagged=fan|bilinear
            extraordinary=set(d["extraordinary_association"]["extraordinary_vertices"])
            near_extra=extraordinary|{n for v in extraordinary for n in mesh.vertex_neighbors(v)}
            near_junction=junctions|{n for v in junctions for n in mesh.vertex_neighbors(v)}
            directly_extra={f for f in flagged if set(mesh.face_vertices(f))&extraordinary}
            extra_faces={f for f in flagged if set(mesh.face_vertices(f))&near_extra}
            junction_faces={f for f in flagged if set(mesh.face_vertices(f))&near_junction}
            naked={f for f in flagged if any(mesh.is_vertex_on_boundary(v) for v in mesh.face_vertices(f))}
            a=d["extraordinary_association"]
            locations.append(dict(case=name,generation=g,warning_faces=len(flagged),
                directly_incident_to_extraordinary=len(directly_extra),within_extraordinary_one_hop=a["near_warning_faces"],
                outside_extraordinary_one_hop=a["far_warning_faces"],within_original_junction_one_hop=len(junction_faces),
                at_naked_boundaries=len(naked),elsewhere_from_both_one_hop_neighborhoods=len(flagged)-len(junction_faces|extra_faces)))
            stages.append(dict(generation=g,fan=len(fan),bilinear=len(bilinear),
                crossings=stage["sampled_crossings"]["sampled_transverse_crossings"],
                crossing_limit=stage["sampled_crossings"]["sample_limit_reached"],
                eligible=stage["later_stencil"]["eligible_faces"],fallback=stage["later_stencil"]["fallback_faces"]))
        if name in OBSERVATIONS:
            meso,micro,decision=OBSERVATIONS[name]
            review=dict(macro="Same L4 G1: broad paired supports and shoulder/lintel peaks span adjacent original faces; opening legible.",
                meso=meso,micro=micro,persistence="Support/lintel organization persists; inspect the matched G0-G5 sheet for which folds persist or are erased.",
                identity="Gate and central opening remain visually legible; distorted supports and pinching are visible, not repaired.",decision=decision)
        else:
            review=dict(decision="Retained reference control",macro="S rounds the carrier; L4 makes the common broad G1 deformation.",
                meso="No claimed hierarchy success",micro="Reference smoothing/relief",persistence="Reference",identity="Opening legible")
        if any(s["crossings"] for s in stages):
            assert name not in ("C09_meso_ridge_hold","C11_interpolation_release","R14_detail_class_shift")
        rows.append(dict(case=name,stages=stages,visual_review=review))
    assert len([r for r in rows if r["case"] in OBSERVATIONS])==16
    write(study / "final_review.json",dict(design_status="PARTIAL_SUCCESS",attempted_design_schedules=16,controls=2,
        BEST_PARTIAL_SCHEDULE="C11_interpolation_release",FIRST_GROTESQUE_GATE_CANDIDATE=None,
        retained_partial_examples=["C11_interpolation_release","C09_meso_ridge_hold","R14_detail_class_shift"],
        distinct_successful_hierarchical_families=0,regional_modulation="SKIPPED: convincing hierarchy was not established",
        C1_transfer="SKIPPED: convincing C0 schedule was not established",cases=rows,
        conclusion="THE CURRENT EXTENDED CATMULL-CLARK SUBSET REMAINS MORPHOLOGICALLY INSUFFICIENT FOR THE TARGET HIERARCHY. This bounded C0 study supports testing another scheme next; it does not prove every possible Catmull-Clark schedule fails."))
    write(study / "warning_locations.json",dict(note="Overlapping observational counts, no causal attribution. Original junction means retained original C0 vertices at source Z=2600, with their current one-hop topology. All sources/outputs closed; no naked-boundary warnings. Extraordinary counts reuse Task15 diagnostics.",
        original_junction_vertex_ids=sorted(junctions),stages=locations))
    lines=["# Task 16 actual evidence","","PARTIAL_SUCCESS. No FIRST_GROTESQUE_GATE_CANDIDATE; no regional field or C1 transfer.","",
        "16 design schedules + S/L4 controls, all G0-G5 retained. One exact C11 repeat is a reproducibility check, not another design schedule.","",
        "| Case | Fan G1-G5 | Bilinear G1-G5 | Sampled crossings G1-G5 | Decision |","|---|---|---|---|---|"]
    for row in rows:
        columns=[row["case"]]+[", ".join(str(s[k]) for s in row["stages"]) for k in ("fan","bilinear","crossings")]+[row["visual_review"]["decision"]]
        lines.append("| "+" | ".join(columns)+" |")
    lines.extend(["","Crossings are bounded fan-triangle approximations, maximum 30 per generation; adjacent and coplanar contacts are excluded. Zero does not certify global collision freedom.","",
        "Open `retained_final.png`, `retained_detail.png`, `final_wire.png`, `final_detail_wire.png`, `final_front.png`, `final_silhouette.png` and the individual progression sheets. All use saved actual geometry with fixed camera/scale; these are HEADLESS, not Rhino captures.","",
        "Per-generation counts, bounding boxes, face-area/edge distributions, actual seven weights, timing, corner motion and original-face residual approximation are in `cases/*/summary.json`. Immediate origins, applications/fallbacks and face-root chains are in `result.json.gz` and `checkpoint.json.gz`. Shared residual vertices can belong to several original-face groups; semantic inheritance is NOT IMPLEMENTED.","",
        "`metadata_recording_correction.json` records 13 initial stage output boxes corrected in both compressed copies. Original pre-stencil boxes remain labeled; geometry, weights, lineage and diagnostic results never changed.","",
        "The new Rhino mode runs successfully through the real isolated external worker. Actual Rhino host insertion, viewport, Undo and cancellation are PENDING.",""])
    (study / "START_HERE.md").write_text("\n".join(lines),encoding="utf-8")
    print("FINAL REVIEW",len(rows),"control/design cases,",len(locations),"warning-location stages",flush=True)


def correct_initial_metadata(study):
    """Keep pre-stencil backend boxes labeled, and record actual output boxes.

    Early probe execution preceded this metadata-only correction. Geometry,
    parameters, lineage and diagnostics are untouched. Original metadata is
    preserved under backend_before_face_stencil_output, never discarded.
    """
    records=[]
    for path in sorted((study / "cases").glob("*/result.json.gz")):
        if not (path.parent / "crossing_audit.json").exists():
            continue
        for filename in ("result.json.gz","checkpoint.json.gz"):
            artifact=path.parent / filename
            with gzip.open(artifact,"rt",encoding="utf-8") as stream:
                result=json.load(stream)
            changed=False
            for stage in result["stages"]:
                actual=inspect_mesh(mesh_from_data(stage["mesh"]))
                metadata=stage["metadata"]
                if metadata["output"] != actual:
                    original=metadata["output"]
                    metadata["backend_before_face_stencil_output"]=original
                    metadata["output"]=actual
                    metadata["output_metadata_correction"]="Task16 initial recording correction: original Task14 backend box retained above; actual post-equation4 output box recorded. Geometry/weights/lineage unchanged."
                    records.append(dict(case=path.parent.name,artifact=filename,generation=stage["generation"],
                        original_backend_box=original["bounding_box"],actual_output_box=actual["bounding_box"]))
                    changed=True
            if changed:
                compressed(artifact,result)
    write(study / "metadata_recording_correction.json",dict(scope="Metadata only; mesh JSON/OBJ, parameters, existing diagnostics and origins unchanged. Original boxes preserved in corrected metadata.",
        source_fix="Wrapper now inspects actual mesh after equation4 rather than retaining the pre-stencil backend output box.",records=records))
    print("Explicit initial output metadata correction:",len(records),"records across final/checkpoint copies",flush=True)


def detail_views(study,names,label):
    """Wire, oblique detail, fixed front shade and front silhouette comparison."""
    from generational_weight_study import views
    stats=read(study / "source_statistics.json"); x0,z0=stats["bbox_min"][0],stats["bbox_min"][2]
    bounds=[x0-1000,x0+5000,z0-700,z0+4600]
    crop=[x0+400,x0+2200,z0+2000,z0+3800]
    frames=[]; sheets=[]
    for kind,camera,area,wire,silhouette in (("wire","oblique",bounds,True,False),
        ("detail_wire","oblique",crop,True,False),("front","front",bounds,False,False),
        ("silhouette","front",bounds,False,True)):
        files=[]
        for name in names:
            g=read(study / f"cases/{name}/summary.json")["generations_reached"]
            file=f"{label}_{kind}_{name}.png"
            frames.append(dict(mesh=f"cases/{name}/G{g}.json",label=name+f" G{g} {kind}",camera=camera,bounds=area,
                wireframe=wire,silhouette=silhouette,width=500,height=550,file=file))
            files.append(file)
        sheets.append(dict(file=f"{label}_{kind}.png",title=label+" "+kind+": fixed camera/scale, actual geometry",images=files,columns=min(4,len(files)),width=500,height=550))
    plan=study / f"{label}_supplemental_plan.json"; write(plan,dict(frames=frames,sheets=sheets))
    result=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT / "tools/morphology_projection.ps1"),"-PlanPath",str(plan)],
        cwd=ROOT,capture_output=True,text=True,timeout=300)
    (study / f"{label}_supplemental_log.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
    result.check_returncode()


def repeat(study,name):
    """One real deterministic repeat, excluding elapsed-time metadata."""
    from generational_weight_study import execute
    execute(study,"REPEAT_"+name,read(study / f"schedules/{name}.json"))
    matches=[]
    for g in range(6):
        a=study / f"cases/{name}/G{g}.json"; b=study / f"cases/REPEAT_{name}/G{g}.json"
        assert read(a)==read(b)
        assert a.with_suffix(".obj").read_bytes()==b.with_suffix(".obj").read_bytes()
        matches.append(dict(generation=g,geometry="EXACT JSON and OBJ-byte identity"))
    write(study / "reproducibility.json",dict(case=name,checkpoints=matches,status="PASS"))


def worker_smoke(study):
    """Real bridge worker, poisoned parent, exact saved-original gate anchor."""
    import os
    from time import monotonic
    from exchange import GENERATIONAL_MODE,validate_request,validate_response
    from generational_display import comparison_items
    from worker_process import worker_launch_options
    directory=study / "worker_smoke"; directory.mkdir(exist_ok=False)
    original=read(ROOT / "output/task12/8c5ff45c-7810-455d-a4ba-c1339c67eccd/request.json")["mesh"]
    request=validate_request(dict(protocol=1,run_id=str(uuid4()),source=dict(document_serial=7,object_id="headless-saved-original-gate"),
        mode=GENERATIONAL_MODE,mesh=original))
    write(directory / "request.json",request)
    fake=directory / ".rhinocode/py39-rh8/Lib"; fake.mkdir(parents=True)
    for name in ("argparse","re","pathlib"):
        (fake / (name+".py")).write_text("raise AssertionError('SRE module mismatch: poisoned parent')\n",encoding="utf-8")
    prior={key:os.environ.get(key) for key in ("PYTHONHOME","PYTHONPATH")}
    try:
        os.environ["PYTHONHOME"]=str(fake.parent)
        os.environ["PYTHONPATH"]=str(fake)
        launch=worker_launch_options(ROOT,directory / "request.json",directory / "response.json")
        assert not any(k.upper() in ("PYTHONHOME","PYTHONPATH") for k in launch["env"])
        started=monotonic()
        with (directory / "worker_stdout.txt").open("w") as out,(directory / "worker_stderr.txt").open("w") as err:
            child=subprocess.run(**launch,stdout=out,stderr=err,timeout=60)
    finally:
        for key,value in prior.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
    assert child.returncode==0,(directory / "worker_stderr.txt").read_text()
    response=validate_response(read(directory / "response.json"),request)
    identity=response["runtime_identity"]
    assert identity["ignore_environment"] and identity["no_user_site"]
    assert Path(identity["executable"]).resolve() == (ROOT / ".venv/Scripts/python.exe").resolve()
    assert identity["version"].startswith("3.12.") and ".rhinocode" not in identity["re_file"].lower()
    assert response["carrier"]["mesh"] == read(study / "C0.json")
    assert response["status"]=="SUCCESS"
    comparisons=[]
    for variant,name in zip(response["variants"],("CONTROL_L4","C11_interpolation_release")):
        for stage in variant["stages"]:
            assert stage["mesh"] == read(study / f"cases/{name}/G{stage['generation']}.json")
            comparisons.append(dict(case=name,generation=stage["generation"],geometry="EXACT JSON identity"))
    items=comparison_items(response)
    assert len(items)==5
    write(study / "worker_smoke.json",dict(status="PASS",seconds=monotonic()-started,exit_code=child.returncode,
        runtime_identity=identity,poisoned_parent_environment=True,exact_checkpoint_comparisons=comparisons,
        display_labels=[row[0] for row in items],actual_Rhino_host="NOT RUN; real external worker and bridge contract only"))
    print("WORKER SMOKE PASS",len(comparisons),"exact checkpoints",flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("phase",choices=("audit","correct-initial-metadata","detail","repeat","worker","report"))
    parser.add_argument("--directory",type=Path,default=ROOT / "output/task16/study")
    parser.add_argument("--names",nargs="+"); parser.add_argument("--label",default="representatives")
    parser.add_argument("--case")
    args=parser.parse_args()
    if args.phase=="audit": audit(args.directory)
    elif args.phase=="correct-initial-metadata": correct_initial_metadata(args.directory)
    elif args.phase=="detail": detail_views(args.directory,args.names,args.label)
    elif args.phase=="repeat": repeat(args.directory,args.case)
    elif args.phase=="report": report(args.directory)
    else: worker_smoke(args.directory)


if __name__ == "__main__": main()
