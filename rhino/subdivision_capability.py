"""Task-local DS capability experiment; no changes to existing CC modes."""
from copy import deepcopy
from math import dist, fsum, isfinite
from time import perf_counter

from cheshire.execution import ExecutionBudget
from cheshire.gate_integrity import GateIntegrityMonitor
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.weighted_doosabin import weighted_doosabin_once, PARAMETERS, STANDARD

BUDGET=ExecutionBudget(max_vertices=120000,max_faces=120000,max_generation=6)


def row(face,edge=None,vertex=None):
    """Interpolation, extrusion ratio; all six values explicit in each row."""
    return {f"{parameter}_{family}":value for family,pair in zip(("face","edge","vertex"),(face,edge or face,vertex or face))
            for parameter,value in zip(("w1","w10"),pair)}


def schedules():
    uniform={
        "U01_early_expansion":[(.25,.35),(.15,.22),(.1,.13),(.05,.07),(0,.035),(0,.018)],
        "U02_interpolation_release":[(.15,.2),(.7,.15),(1.1,.08),(.6,.04),(.2,.02),(0,.01)],
        "U03_sign_change":[(.2,.18),(-.55,-.1),(.65,.14),(-.4,-.06),(.35,.055),(-.2,.025)],
        "U04_contraction_pulse":[(-.6,.3),(-.5,.25),(.5,.12),(.25,.08),(.15,.04),(.05,.025)],
    }
    families={
        "F05_face_mass":[row((.2,.25)),row((.65,.45),(-.35,0),(-.3,.04)),row((.7,.3),(-.4,.02),(-.2,.05)),row((.45,.18),(-.3,0),(0,.08)),row((.25,.09),(-.15,0),(.15,.07)),row((.1,.04),(0,0),(.1,.035))],
        "F06_edge_release":[row((.1,.2)),row((-.25,.08),(.8,.35),(-.3,.02)),row((-.4,.04),(1.,.4),(-.2,.04)),row((-.3,.03),(.65,.22),(.25,.12)),row((-.2,.015),(.35,.12),(.35,.14)),row((-.1,.008),(.2,.05),(.2,.075))],
        "F07_vertex_crown":[row((.2,.25)),row((.25,.2),(-.2,.03),(-.3,0)),row((.15,.1),(-.3,0),(.8,.4)),row((0,.04),(-.2,.02),(1.,.4)),row((0,.02),(-.1,.01),(.6,.2)),row((0,.01),(0,.005),(.3,.1))],
        "F08_family_alternation":[row((.15,.25)),row((.8,.4),(-.2,0),(-.2,0)),row((-.3,0),(.9,.4),(-.3,.02)),row((-.2,.02),(-.2,.02),(.9,.35)),row((.55,.2),(-.15,0),(.1,.04)),row((-.1,.01),(.4,.12),(.3,.08))],
        "F09_nested_insets":[row((-.45,.3)),row((-.65,.35),(.4,.04),(.3,.07)),row((-.7,.26),(.55,.03),(.4,.09)),row((-.55,.16),(.4,.02),(.55,.15)),row((-.4,.1),(.25,.015),(.45,.12)),row((-.25,.055),(.15,.01),(.3,.07))],
        "F10_edge_frame_vertex_peaks":[row((.15,.3)),row((-.3,.1),(.45,.32),(-.2,.02)),row((-.4,.06),(.6,.28),(.4,.14)),row((-.35,.025),(.4,.1),(.7,.25)),row((-.25,.015),(.25,.06),(.55,.18)),row((-.1,.01),(.15,.025),(.35,.09))],
        "F11_signed_family_folds":[row((.3,.4)),row((.6,.25),(-.55,-.18),(.3,.12)),row((-.5,-.1),(.7,.28),(.4,.15)),row((.4,.12),(-.35,-.07),(.6,.2)),row((-.25,-.04),(.35,.1),(.35,.09)),row((.15,.04),(-.15,-.02),(.2,.05))],
        "F12_interpolation_frames":[row((.4,.18)),row((-.55,.06),(.85,.08),(-.35,.04)),row((-.65,.04),(1.15,.06),(.45,.1)),row((-.45,.02),(.7,.035),(.9,.16)),row((-.3,.01),(.45,.02),(.6,.1)),row((-.15,.005),(.25,.01),(.4,.055))],
    }
    intentions={
        "U01_early_expansion":"Broad early outward displacement, then uniform attenuation.",
        "U02_interpolation_release":"Moderate macro displacement; meso interpolation expansion; quiet fine tail.",
        "U03_sign_change":"Restrained uniform inward/outward pulses and interpolation sign changes.",
        "U04_contraction_pulse":"Contract face islands early, then release interpolation at smaller scales.",
        "F05_face_mass":"Face-family masses, quiet edge connectors; smaller vertex activation later.",
        "F06_edge_release":"Contract face islands while meso edge families form bands; late vertex relief.",
        "F07_vertex_crown":"Face macro prefix; late vertex-family crowns, restrained connecting edges.",
        "F08_family_alternation":"Face then edge then vertex emphasis, with a subordinate alternating tail.",
        "F09_nested_insets":"Repeated face insets against wider edge frames; late vertex-family peaks.",
        "F10_edge_frame_vertex_peaks":"Meso edge framing followed by localized vertex-family fine emphasis.",
        "F11_signed_family_folds":"Signed family displacement pulses; test folds without source attraction.",
        "F12_interpolation_frames":"Interpolation-led nested framing, then vertex-family smaller crowns.",
    }
    return {**{name:dict(schedule=[row(pair) for pair in pairs],intention=intentions[name],kind="uniform") for name,pairs in uniform.items()},
            **{name:dict(schedule=rows,intention=intentions[name],kind="family") for name,rows in families.items()}}


def validate_schedule(schedule):
    if not isinstance(schedule,list) or len(schedule)!=6 or any(not isinstance(r,dict) or set(r)!=set(PARAMETERS) or
        any(type(v) not in (int,float) or not isfinite(v) for v in r.values()) for r in schedule):
        raise ValueError("Six explicit finite DS family rows are required; no implicit tail.")


def refinements():
    """Four declared follow-ups after actual twelve-probe images/diagnostics.

    F09 adds angular nested facets; F06/F10/F12 introduce edge frames but
    crossings/fold flags are substantial. These new recipes test subordinate
    scales with less extrapolation. Prior outputs and parameters remain intact.
    """
    specs={
        "R13_restrained_insets":("F09 inset mechanism with less extrapolation and normal displacement; test nesting without the dense opposed-fan tail.",
            [row((-.45,.3)),row((-.5,.24),(.15,.015),(.1,.025)),row((-.5,.18),(.25,.015),(.2,.05)),row((-.35,.1),(.2,.01),(.3,.08)),row((-.2,.055),(.1,.005),(.2,.055)),row((-.1,.025),(.05,.002),(.1,.025))]),
        "R14_delayed_crown":("Keep inset meso prefix; a later restrained vertex-family pulse should create subordinate localized peaks.",
            [row((-.45,.3)),row((-.6,.12),(-.2,.025),(.1,.025)),row((-.55,.1),(.2,.025),(-.2,.025)),row((-.3,.02),(-.2,.005),(.45,.14)),row((-.25,.03),(.15,.025),(.35,.07)),row((-.15,.025),(.1,.01),(.2,.04))]),
        "R15_restrained_edge_frames":("F10 edge-to-vertex sequence with reduced meso extrapolation; retain framed vocabulary rather than repair old crossings.",
            [row((.15,.3)),row((-.3,.08),(.2,.13),(-.2,.02)),row((-.4,.04),(.25,.12),(.15,.05)),row((-.25,.02),(.2,.045),(.35,.11)),row((-.15,.01),(.15,.03),(.25,.07)),row((-.05,.005),(.1,.015),(.15,.035))]),
        "R16_interpolation_nests":("F12 interpolation-led frames with a weaker edge release and later smaller vertex-family crowns.",
            [row((.4,.18)),row((-.5,.06),(.3,.05),(-.2,.04)),row((-.55,.04),(.5,.06),(.2,.05)),row((-.35,.02),(.3,.025),(.3,.08)),row((-.2,.01),(.2,.02),(.2,.04)),row((-.1,.005),(.1,.01),(.1,.02))]),
    }
    return {name:dict(intention=intention,schedule=rows,kind="declared_refinement",decision_basis="Actual F09/F10/F12 angular-family morphology and recorded fold/crossing warnings; no gate drift constraints.") for name,(intention,rows) in specs.items()}


def run_capability(source,schedule,*,generations=6,cc_prefix=0,publish=None):
    """Streaming checkpoints. Monitor outputs never influence the geometry loop.

    w10 ratios use current global mean input edge length, then unit COMPAS face
    normal. Hybrid uses C11 unchanged through G2/G3; the DS tail uses the same
    selected schedule's GLOBAL generation rows, without hybrid-specific tuning.
    """
    validate_schedule(schedule)
    if type(generations) is not int or not 1<=generations<=6 or cc_prefix not in (0,2,3) or cc_prefix>generations:
        raise ValueError("One to six generations; optional unchanged C11 prefix of two or three.")
    before=deepcopy(source.__data__); mesh=source; families=None; cc_origins=None
    anchors={v:v for v in source.vertices()}; monitor=GateIntegrityMonitor(source)
    result=dict(status="PARTIAL",reason=None,stages=[],schedule=deepcopy(schedule),cc_prefix=cc_prefix,
        spatial_modulation=False,semantic_lineage="NOT IMPLEMENTED",source_immutable=True)
    started=perf_counter()
    for generation in range(1,generations+1):
        try:
            scale=fsum(dist(mesh.vertex_coordinates(u),mesh.vertex_coordinates(v)) for u,v in mesh.edges())/mesh.number_of_edges()
            if generation<=cc_prefix:
                from generational_study import choreographies,BEST_SCHEDULE
                ratios=choreographies()[BEST_SCHEDULE]["schedule"][generation-1]
                weights={k:v*scale if k in ("wf","we","wp") else v for k,v in ratios.items()}
                step=generational_subdivide_once(mesh,weights,origin_lineage=cc_origins,budget=BUDGET,current_generation=generation-1)
                cc_origins=step.origin_lineage
                next_anchors={v:anchors.get(v) for v in step.mesh.vertices()}
                scheme="C11_CC"
            else:
                ratios=schedule[generation-1]
                weights={k:v*scale if k.startswith("w10_") else v for k,v in ratios.items()}
                step=weighted_doosabin_once(mesh,weights,face_families=families,budget=BUDGET,current_generation=generation-1)
                next_anchors={v:anchors.get(parent) for v,parent in step.corner_parents.items()}
                families=step.face_families
                scheme="WEIGHTED_DS"
            stage=dict(generation=generation,scheme=scheme,ratios=ratios,weights=weights,global_mean_edge_length=scale,
                metadata=step.metadata,monitor=monitor.evaluate(step.mesh,next_anchors,generation=generation))
            if scheme=="WEIGHTED_DS":
                stage["face_families"]=step.face_families
                stage["corner_parents"]=step.corner_parents
                stage["lineage"]={domain:[dict(id=key,parents=[dict(id=p.key,weight=p.weight) for p in parents]) for key,parents in getattr(step.lineage,domain).items()]
                                  for domain in ("vertex_parents","face_parents")}
            else:
                stage["cc_origin_lineage"]=cc_origins
                stage["sampling_parents"]=step.sampling_parents
            if publish:
                publish(step.mesh,stage)
            result["stages"].append({k:v for k,v in stage.items() if k not in ("metadata","face_families","corner_parents","lineage","cc_origin_lineage","sampling_parents")})
            mesh,anchors=step.mesh,next_anchors
        except (ValueError,ArithmeticError) as error:
            result["reason"]=f"G{generation} technical stop: {error}"; break
    else:
        result["status"]="SUCCESS"
    result["source_immutable"]=source.__data__==before
    if not result["source_immutable"]:
        raise AssertionError("Source mutated.")
    result["elapsed_seconds"]=perf_counter()-started
    return result
