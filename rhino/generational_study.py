"""Task 16 opt-in C0 choreography, separate from existing Rhino modes."""
from collections import defaultdict
from copy import deepcopy
from math import dist, fsum
from statistics import median
from time import perf_counter

from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.weighted_subdivision import STANDARD
from cheshire_worker import mesh_to_data, RUNTIME_IDENTITY
from carrier_study import BUDGET, LOCAL_SCHEDULES, DIMENSIONS, coarse_gate

PARAMETERS = ("wf", "w1", "we", "w2", "wp", "w3", "w4")
BEST_SCHEDULE = "C11_interpolation_release"


def schedule_rows(class_values, *, base=None):
    """Five explicit rows; no implicit tail or random parameter selection."""
    base = base or LOCAL_SCHEDULES["L4_macro_corner"][:5]
    if len(class_values) != 5 or len(base) != 5:
        raise ValueError("Exactly five explicit generation rows are required.")
    return [{**row, "w3": w3, "w4": w4} for row,(w3,w4) in zip(base,class_values)]


CONTROLS = {
    "CONTROL_S": schedule_rows([(0,0)]*5,base=[STANDARD.copy() for _ in range(5)]),
    "CONTROL_L4": schedule_rows([(0,0)]*5),
}


def direct_probes():
    return {
        "P01_vertex_bias": dict(intention="Keep L4 macro generation; favor immediately V-derived corners at G2-G5.",
            schedule=schedule_rows([(0,0),(.7,0),(.7,0),(.7,0),(.7,0)])),
        "P02_face_bias": dict(intention="Keep L4 macro generation; favor immediately F-derived corners at G2-G5.",
            schedule=schedule_rows([(0,0),(-.7,0),(-.7,0),(-.7,0),(-.7,0)])),
        "P03_VF_pair_bias": dict(intention="Keep L4 macro generation; favor the V/F diagonal over the E/E diagonal at G2-G5.",
            schedule=schedule_rows([(0,0),(0,.7),(0,.7),(0,.7),(0,.7)])),
        "P04_edge_pair_bias": dict(intention="Keep L4 macro generation; favor the E/E diagonal over the V/F diagonal at G2-G5.",
            schedule=schedule_rows([(0,0),(0,-.7),(0,-.7),(0,-.7),(0,-.7)])),
    }


def choreographies():
    """Eight explainable follow-ups to the four retained direct probes."""
    seed=deepcopy(LOCAL_SCHEDULES["L4_macro_corner"][:5])
    reduced=deepcopy(seed)
    for row,wf,we,wp in zip(reduced[2:],(.06,.025,.012),(-.02,-.008,-.004),(.012,.006,.003)):
        row.update(wf=wf,we=we,wp=wp)
    release=deepcopy(seed)
    release[1].update(w1=-1.05,w2=-.9)
    release[2].update(wf=.07,w1=-1.1,w2=-1.,we=-.025,wp=.015)
    release[3].update(wf=.04,w1=-.9,w2=-.8,we=-.015,wp=.008)
    release[4].update(wf=.025,w1=-.7,w2=-.55,we=-.01,wp=.004)
    quiet=deepcopy(seed)
    quiet[1].update(wf=.14,we=-.04,wp=.04)
    for row,wf,we,wp in zip(quiet[2:],(.04,.012,.006),(-.015,-.004,-.002),(.008,.003,.001)):
        row.update(wf=wf,we=we,wp=wp)
    definitions=[
        ("C05_meso_face_lock",[(0,0),(-.9,.4),(-1.05,.55),(-.65,.4),(-.35,.3)],seed,
         "Favor the previous face class during meso formation, then lessen bias while keeping broad L4 deformation."),
        ("C06_vertex_pulse",[(0,0),(.65,.35),(-.65,.4),(-.2,.2),(0,.15)],seed,
         "One V-derived G2 pulse, reverse to F-derived G3, then restrain fine bias; avoid P01's sustained positive bias."),
        ("C07_diagonal_alternation",[(0,0),(-.5,.75),(.45,-.6),(-.35,.55),(.2,-.25)],seed,
         "Alternate both class relation and diagonal emphasis with a weaker fine tail; no assumption that alternation succeeds."),
        ("C08_face_then_edges",[(0,0),(-.8,.6),(-.8,.85),(0,-.35),(-.25,.2)],seed,
         "Meso F/VF emphasis, release to edge diagonal at G4, then a small face bias at G5."),
        ("C09_meso_ridge_hold",[(0,0),(-.5,.85),(-.65,1.05),(-.3,.8),(-.25,.5)],reduced,
         "Strong meso VF-diagonal emphasis with attenuated normal extrusion; preserve point-class structure into fine stages."),
        ("C10_nested_face_emphasis",[(0,0),(-1.15,.55),(-1.05,.9),(-.8,.7),(-.55,.45)],seed,
         "Test slight meso extrapolation beyond F-derived corners, reducing it in the fine tail; retain any failure."),
        ("C11_interpolation_release",[(0,0),(-.8,.5),(-.6,.8),(-.4,.5),(-.3,.3)],release,
         "Pair F/VF bias with stronger existing edge/corner interpolation at G2/G3, then attenuate all fine controls."),
        ("C12_class_lock_low_extrusion",[(0,0),(-.7,.7),(-.7,.8),(-.65,.8),(-.6,.65)],quiet,
         "Maintain later F/VF class bias while rapidly decreasing normal extrusion; test if meso structure survives without ribs."),
    ]
    result={}
    for name,pairs,base,intention in definitions:
        result[name]=dict(intention=intention,schedule=schedule_rows(pairs,base=base),
            generation_intentions=["G1: unchanged L4 broad gate deformation",f"G2: begin meso class relationship {pairs[1]}",
                f"G3: meso differentiation {pairs[2]}",f"G4: fine-stage balance {pairs[3]}",f"G5: fine-stage balance {pairs[4]}"])
    return result


def refinements():
    """Four declared final refinements of the visually retained C09/C11."""
    candidates=choreographies()
    ridge=deepcopy(candidates["C09_meso_ridge_hold"]["schedule"])
    release=deepcopy(candidates["C11_interpolation_release"]["schedule"])
    shifted=deepcopy(ridge)
    shifted[3].update(wf=.04,we=-.015,wp=.006)
    shifted[4].update(wf=.025,we=-.008,wp=.003)
    fine=deepcopy(release)
    fine[3].update(wf=.07,we=-.02,wp=.01,w1=-.65,w2=-.45)
    fine[4].update(wf=.045,we=-.014,wp=.005,w1=-.45,w2=-.3)
    specs=[
        ("R13_restrained_ridges",ridge,[(0,0),(-.45,.8),(-.5,.95),(-.3,.85),(-.2,.65)],
         "Reduce C09 meso extrapolation, preserve VF-biased finer placement; check whether secondary lobes survive with fewer flags."),
        ("R14_detail_class_shift",shifted,[(0,0),(-.55,.9),(-.65,.9),(.2,.45),(-.2,.2)],
         "C09-like meso pulse followed by a restrained V-derived fine shift then F reversal; test a subordinate finer rhythm."),
        ("R15_release_ridge_hold",release,[(0,0),(-.8,.5),(-.6,.8),(-.35,.75),(-.2,.65)],
         "Keep C11 meso interpolation and maintain a restrained VF ridge tail, without C12's very low extrusion."),
        ("R16_delayed_micro_class",fine,[(0,0),(-.8,.5),(-.6,.8),(-.25,1.),(.1,.6)],
         "Preserve C11 meso prefix, then release existing interpolation while adding a smaller face-class/normal-extrusion articulation."),
    ]
    result={}
    for name,base,pairs,intention in specs:
        rows=[{**row,"w3":w3,"w4":w4} for row,(w3,w4) in zip(base,pairs)]
        result[name]=dict(intention=intention,schedule=rows,
            generation_intentions=["G1: same L4 macro deformation",f"G2: selected meso bias {pairs[1]}",
                f"G3: retain selected secondary formation {pairs[2]}",f"G4: declared fine refinement {pairs[3]}",f"G5: declared fine tail {pairs[4]}"])
    return result


def run_choreography(source, schedule, *, generations=5, publish=None):
    """Fresh geometry each step, explicit immediate origins and face-root chains."""
    if type(generations) is not int or not 1 <= generations <= 5:
        raise ValueError("Request one to five generations from the explicit schedule.")
    if len(schedule) != 5 or any(set(row) != set(PARAMETERS) for row in schedule):
        raise ValueError("Each of five generations must serialize exactly the seven verified parameters.")
    before=deepcopy(source.__data__)
    mesh=source; origins=None; roots={f:f for f in source.faces()}
    result=dict(stages=[],status="FAILED",reason=None,schedule=deepcopy(schedule),
        requested_generations=generations,semantic_lineage="NOT IMPLEMENTED",spatial_modulation=False)
    started=perf_counter()
    for generation in range(1,generations+1):
        step_started=perf_counter()
        try:
            ratios=schedule[generation-1]
            scale=fsum(dist(mesh.vertex_coordinates(u),mesh.vertex_coordinates(v)) for u,v in mesh.edges())/mesh.number_of_edges()
            weights={key:value*scale if key in ("wf","we","wp") else value for key,value in ratios.items()}
            refined=generational_subdivide_once(mesh,weights,origin_lineage=origins,budget=BUDGET,current_generation=generation-1)
            motion={v:dist(mesh.vertex_coordinates(v),refined.mesh.vertex_coordinates(v)) for v in mesh.vertices()}
            residual={v:dist(refined.mesh.vertex_coordinates(v),
                [fsum(mesh.vertex_coordinates(p)[i]*w for p,w in parents) for i in range(3)])
                for v,parents in refined.sampling_parents.items()}
            grouped=defaultdict(set)
            next_roots={}
            for face in refined.metadata["face_sources"]:
                root=roots[face["source_face"]]
                next_roots[face["id"]]=root
                grouped[root].update(refined.mesh.face_vertices(face["id"]))
            grouped_residual=[dict(original_face=root,vertex_count=len(vertices),
                median=median(residual[v] for v in vertices),max=max(residual[v] for v in vertices)) for root,vertices in sorted(grouped.items())]
            stage=dict(generation=generation,mesh=mesh_to_data(refined.mesh),ratios=dict(ratios),weights=weights,
                global_mean_edge_length=scale,generation_seconds=perf_counter()-step_started,
                vertex_count=refined.mesh.number_of_vertices(),face_count=refined.mesh.number_of_faces(),
                metadata=refined.metadata,origin_lineage=[dict(id=v,**row) for v,row in sorted(refined.origin_lineage.items())],
                face_roots=[dict(id=f,original_face=root) for f,root in sorted(next_roots.items())],
                sampling_parents=[dict(id=v,parents=[dict(id=p,weight=w) for p,w in rows]) for v,rows in refined.sampling_parents.items()],
                retained_corner_motion=dict(count=len(motion),median=median(motion.values()),max=max(motion.values()),
                    note="Actual previous vertices to their retained corner points; not full surface displacement."),
                placement_residual_by_original_face=grouped_residual,
                placement_residual_note="Distance from actual point to positive input control-cage sample. Vertex sets grouped by topological original-face descendants; shared vertices appear in multiple groups. Not semantic inheritance or exact surface displacement.")
            result["stages"].append(stage); result["status"]="PARTIAL"
            mesh,origins,roots=refined.mesh,refined.origin_lineage,next_roots
            if publish:
                publish(result)
        except (ValueError,ArithmeticError) as error:
            result["reason"]=f"G{generation} stopped: {error}"
            break
    else:
        result["status"]="SUCCESS"
    assert source.__data__ == before
    result["source_immutable"]=True
    result["elapsed_seconds"]=perf_counter()-started
    return result


def run_generational_study(request, publish=None):
    """Concise Rhino comparison of the useful partial result, not a design win.

    Explicitly construct the unchanged C0 fixture at the selected gate's bbox
    center/floor. This is a carrier study, not automatic retopology or fitting.
    Gate dimensions and world-axis orientation are required; no rescaling.
    """
    from exchange import GENERATIONAL_MODE, validate_mesh_data
    coordinates=[row["xyz"] for row in request["mesh"]["vertices"]]
    low=[min(p[i] for p in coordinates) for i in range(3)]
    high=[max(p[i] for p in coordinates) for i in range(3)]
    size=[hi-lo for lo,hi in zip(low,high)]
    if abs(size[0]-DIMENSIONS["width"])>4e-5 or abs(size[2]-DIMENSIONS["height"])>3.5e-5 or not any(abs(size[1]-depth)<=9e-6 for depth in (500.,900.)):
        raise ValueError("GenerationalWeightStudy requires the axis-aligned original gate (4000 x 900 x 3500) or C0 (4000 x 500 x 3500), in original units; no fitting or rescaling.")
    origin=[(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]]
    source=coarse_gate(origin)
    response=dict(protocol=1,run_id=request["run_id"],source=request["source"],mode=GENERATIONAL_MODE,
        recipe_version="16.0",runtime_identity=RUNTIME_IDENTITY,status="FAILED",reason=None,variants=[],
        carrier=dict(mesh=mesh_to_data(source),origin=origin,dimensions=DIMENSIONS,selected_bbox_dimensions=size,
            note="Unchanged 500-depth Task15 C0 fixture, positioned at selected bbox center/floor. The saved original gate has depth 900; this documented Task15 carrier difference is retained. Selected mesh is not transformed or retopologized."),
        best_schedule=BEST_SCHEDULE,design_status="PARTIAL_SUCCESS",first_grotesque_gate_candidate=None,
        regional_modulation=False,semantic_lineage="NOT IMPLEMENTED",
        evidence_note="Retained split support lobes and lintel ridges improve meso persistence; fine articulation remains repetitive. Runtime exchange/budget validation is not a collision or local regularity certificate. See retained Task16 offline diagnostics.")
    for name,schedule in (("CONTROL_L4",CONTROLS["CONTROL_L4"]),
                          ("BEST_NEW",choreographies()[BEST_SCHEDULE]["schedule"])):
        def checkpoint(result):
            stage=result["stages"][-1]
            validate_mesh_data(stage["mesh"])
            if stage["metadata"]["budget"]["status"] != "SAFE":
                raise ValueError("Unsafe generational checkpoint.")
            stage["validated"]=True
            variant=dict(id=name,**result)
            if response["variants"] and response["variants"][-1]["id"] == name:
                response["variants"][-1]=variant
            else:
                response["variants"].append(variant)
            response["status"]="PARTIAL"
            if publish:
                publish(response)
        result=run_choreography(source,schedule,publish=checkpoint)
        variant=dict(id=name,**result)
        if response["variants"] and response["variants"][-1]["id"] == name:
            response["variants"][-1]=variant
        else:
            response["variants"].append(variant)
        if result["status"] != "SUCCESS":
            response["reason"]=result["reason"]
            break
    completed=any(row["stages"] for row in response["variants"])
    response["status"]=("SUCCESS" if len(response["variants"])==2 and all(row["status"]=="SUCCESS" for row in response["variants"])
                        else "PARTIAL" if completed else "FAILED")
    if publish:
        publish(response)
    return response
