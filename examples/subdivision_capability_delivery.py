"""Serialize explicit human visual selections and verify the real worker path."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parent))
from subdivision_capability_study import ROOT,STUDY,read,write,bounded_child
from subdivision_capability_review import observations

DECISIONS={
    "U01_early_expansion":"Broad inflated masses; insufficient meso/micro differentiation; sampled crossings.",
    "U02_interpolation_release":"Uniform faceted panels; later fold/crossing warnings, no useful third scale.",
    "U03_sign_change":"Technically quiet but mostly rounded/faceted carrier; weak hierarchy.",
    "U04_contraction_pulse":"Pointed macro bases and narrowed opening; fine stages add little distinct structure.",
    "F05_face_mass":"Broader lobes, but late surface rhythm resembles corrugation; crossing evidence from G2.",
    "F06_edge_release":"Distinct framed panels/bands; dense fold and crossing warnings exclude it as a stable best.",
    "F07_vertex_crown":"Localized secondary peaks, then many opposed-fan/fold warnings and sampled crossings.",
    "F08_family_alternation":"Family pulses add patchwork folds; warning-heavy rather than coherent hierarchy.",
    "F09_nested_insets":"Angular nested facets are distinct from C11; opposed-fan warnings start G3 and grow. Retained as vocabulary evidence, excluded as stable best.",
    "F10_edge_frame_vertex_peaks":"Frames then peaks, with meso-stage crossings and many fold warnings.",
    "F11_signed_family_folds":"Signed folds already have sampled crossings at G1; excluded from stable selections.",
    "F12_interpolation_frames":"Angular frames and many smaller facets, but dense fold/crossing evidence; not a reliable micro hierarchy.",
    "R13_restrained_insets":"Strongest clean DS partial checkpoint at G3: macro pinnacles plus meso angular insets. G4/G5 have 30 opposed-fan warnings each; G6 smooths away much meso detail.",
    "R14_delayed_crown":"Delayed pulse changes local facets, but several later opposed-fan warnings remain and fine articulation is weak.",
    "R15_restrained_edge_frames":"Gate-legible partial checkpoint at G4: supports/lintel/opening remain clear with meso framing. Quiet diagnostics, but G6 mostly rounds the form.",
    "R16_interpolation_nests":"Technically quiet and legible; subdued framing fades toward rounded panels. Weaker articulation than selected checkpoints.",
    "DS_STANDARD":"Standard rounding/topology control, not a hierarchy candidate.",
    "HYBRID_A":"C11 prefix through G2 preserved exactly. DS replaces thin ribs with broader panels, but erases detail and adds crossing/fold warnings; no third-scale success.",
    "HYBRID_B":"C11 prefix through G3 preserved exactly. Better retention of shoulder/lintel organization than A; late DS softens ribs, without an independent micro structure. G4 sampled crossings and later fold warnings remain.",
    "C11_REFERENCE":"Exact unchanged Task16 reference; useful macro/meso articulation, repetitive fine corrugation.",
}
CHOICES=[("C11_REFERENCE",5,["TASK16 C11 CONTROL"]),
    ("R13_restrained_insets",3,["BEST WEIGHTED DS","MAX_CAPABILITY_CANDIDATE"]),
    ("R15_restrained_edge_frames",4,["GATE_LEGIBLE_CANDIDATE"]),
    ("HYBRID_B",6,["BEST CC-DS HYBRID"])]


def generate():
    observations(); raw={r["id"]:r for r in read(STUDY/"raw_trajectories.json")}
    outcomes=[]
    for name,record in raw.items():
        summary=read(STUDY/"cases"/name/"summary.json")
        outcomes.append(dict(id=name,recipe=summary.get("recipe"),technical_status=summary["status"],
            cc_prefix=summary.get("cc_prefix",0),
            actual_generation_parameters=[{key:s.get(key) for key in ("generation","scheme","ratios","weights","global_mean_edge_length")} for s in summary["stages"] if s["generation"]>0],
            technical_stop_reason=summary.get("reason"),actual_generations=record["generations_reached"],
            visual_outcome=DECISIONS[name],selected_checkpoints=[dict(generation=g,roles=roles) for case,g,roles in CHOICES if case==name],
            weak_or_excluded_reason=DECISIONS[name],no_parameter_repair=True))
    write(STUDY/"outcomes.json",outcomes)
    display=[]
    for name,g,roles in CHOICES:
        stage=next(s for s in raw[name]["trajectory"] if s["generation"]==g)
        audit=next((r for r in raw[name].get("crossings",[]) or [] if r["id"]==f"G{g}"),None)
        summary=read(STUDY/"cases"/name/"summary.json")
        display.append(dict(case=name,generation=g,roles=roles,file_sha256=hashlib.sha256((STUDY/f"cases/{name}/G{g}.json").read_bytes()).hexdigest(),
            family_counts=stage["family_counts"],monitor=stage["monitor"],recipe=summary.get("recipe"),
            warnings=dict(**stage["diagnostic_counts"],sampled_crossings=None if audit is None else audit["sampled_transverse_crossings"],
                note="Approximate local diagnostics and bounded crossing sample, not a global collision certificate.")))
    write(STUDY/"selections.json",dict(source_file_sha256=hashlib.sha256((STUDY/"C0.json").read_bytes()).hexdigest(),
        design_status="PARTIAL_SUCCESS",full_macro_meso_micro_demonstrated=False,display=display,
        evidence_note="DS adds angular inset/frame vocabulary, but no tested result has convincing stable macro-meso-micro hierarchy. R13 G3 is the clean capability checkpoint; R15 G4 is gate-legible. Hybrid B retains C11 masses while softening ribs; crossing/fold warnings remain.",
        selections_are_visual_descriptions=True,gate_monitor_is_not_a_constraint=True,
        digital_grotesque_assessment="Not supported by these tested schedules; stable independent fine-scale differentiation remains missing, not a proof of impossibility for all future subdivision grammars."))
    rows=[]; fallback=[]
    for name in ("R13_restrained_insets","R15_restrained_edge_frames"):
        for stage in raw[name]["trajectory"]:
            m=stage["monitor"]; n=m["opening_normalized"]; c=m["opening_center_drift_over_source_width_height"]; d=m["dimensions_drift_percent"]
            rows.append(dict(case=name,generation=stage["generation"],selected=any(case==name and g==stage["generation"] for case,g,_ in CHOICES),
                opening_width_ratio=n["width"],opening_height_ratio=n["height"],opening_center_x_ratio=n["center_x"],opening_center_z_ratio=n["center_z"],
                opening_center_x_drift_over_source_width=c["x"],opening_center_z_drift_over_source_height=c["z"],
                outer_width_drift_percent=d["width"],outer_height_drift_percent=d["height"],outer_depth_drift_percent=d["depth"],
                ground_mean_displacement=m["support_base_displacement"]["mean"],missing_anchor_count=len(m["missing_source_anchor_ids"]),
                left_before_right=m["macro_relations"].get("left_median_left_of_right"),lintel_above_supports=m["macro_relations"].get("lintel_median_above_support_medians")))
    with (STUDY/"selected_integrity_trajectories.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    for name,record in raw.items():
        for s in record["trajectory"]:
            if s["family_counts"]:
                fallback.append(dict(case=name,generation=s["generation"],**s["family_counts"],fallback_faces=s["fallback_faces"],fallback_groups=json.dumps(s["fallback_groups"])))
    with (STUDY/"family_fallback_counts.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(fallback[0])); writer.writeheader(); writer.writerows(fallback)
    lines=["# Task 17 results", "", "Baseline: `bba4fd7d6e3a2af8c87c91fb9aeec70c4cd37b7b`. No push.","",
        "**PARTIAL SUCCESS:** weighted DS adds angular inset/frame vocabulary. No tested result clearly demonstrates stable macro → meso → micro hierarchy. Sixteen deterministic design schedules, a standard control and exactly two justified hybrid probes all reached G6. Completion describes numerical/topological execution, not clean geometry or design success.","",
        "## Capability checks", "", "Both cyclic quad/triangle equations were independently verified. Three zero-weight generations match public COMPAS DS on closed quad and triangular fixtures within `1e-12`, with equal oriented topology/counts and deterministic output. The focused checks also verify family construction, immediate lineage, fallback, monitor independence, local budget, serialization, source immutability and unchanged C11 handoff. COMPAS remains 2.15.1. See [reference note](TASK17_REFERENCE.md).", "",
        "The C0 carrier is exactly 24 V / 44 E / 22 F. Its vertex valences are 12 degree-three, eight degree-four and four degree-five. No carrier-resolution or CC parameter search was performed.", "",
        "| G | Vertices | Edges | Faces | FACE | EDGE | VERTEX | Weighted fallback input faces |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in raw["DS_STANDARD"]["trajectory"]:
        if s["generation"]==0: continue
        stats=s["statistics"]; f=s["family_counts"]
        lines.append(f"| {s['generation']} | {stats['vertex_count']} | {stats['edge_count']} | {stats['face_count']} | {f['FACE_DERIVED']} | {f['EDGE_DERIVED']} | {f['VERTEX_DERIVED']} | {s['fallback_faces']} |")
    lines += ["", "Fallback is four pentagons from G2 onward: VERTEX_DERIVED at G2, FACE_DERIVED thereafter. It affects 4/90 input faces at G2 (4.44%) and 4/22,530 at G6 (0.0178%), and does not dominate. These faces keep actual standard COMPAS placement, including zero extrusion; they are never triangulated to obtain weighted stencils.","",
        "## Separate visual selections", "", "- **MAX_CAPABILITY_CANDIDATE / BEST WEIGHTED DS:** `R13_restrained_insets`, **G3**, a clean partial checkpoint with large pointed support/shoulder masses and angular meso insets. No independent useful micro scale is claimed.",
        "- **GATE_LEGIBLE_CANDIDATE:** `R15_restrained_edge_frames`, **G4**, a separate partial checkpoint with the opening, two support bodies and lintel clear, and weaker meso framing. This is a descriptive selection, without a gate threshold.",
        "- **Best handoff comparison:** `HYBRID_B`, **G6**, C11 through G3 then unchanged global G4–G6 rows of R13. It preserves more C11 shoulder/lintel organization than A, but fails to add a convincing micro scale and retains warnings.", "",
        "R13's strongest clean angular articulation occurs around G2–G3. Its G4/G5 each have 30 opposed-fan warnings; G6 returns to zero recorded local warnings while smoothing away meso detail. R15 has zero recorded fan/bilinear warnings and sampled contacts at every generation. Keeping all stages shows why the selected checkpoint need not be the highest generation.", "",
        "## Read-only gate trajectories", "", "Values below are G0-relative **descendant-landmark approximations**, not exact free opening clearance. Raw centers, normalized center drift, equal-anchor cloud spread, region relations and ground displacement are serialized in `raw_trajectories.json` and `selected_integrity_trajectories.csv`.", "",
        "| Case/G | Opening W drift % | Opening H drift % | Outer W drift % | Outer H drift % | Outer D drift % | Mean base Z displacement |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        mark=" **selected**" if r["selected"] else ""
        lines.append(f"| {r['case']} G{r['generation']}{mark} | {100*(r['opening_width_ratio']-1):.2f} | {100*(r['opening_height_ratio']-1):.2f} | {r['outer_width_drift_percent']:.2f} | {r['outer_height_drift_percent']:.2f} | {r['outer_depth_drift_percent']:.2f} | {r['ground_mean_displacement']:.2f} |")
    lines += ["", "For both selected DS cases through G6, all 24 source anchors and all macro regions remain represented; left remains predominantly left of right, and lintel landmarks remain predominantly above support/opening relations. Opening center X stays at its source value; center Z and support-base displacement drift. Macro rounding/narrowing and pointed, displaced bases begin G1, before useful meso insets at G2–G3. No categorical gate-identity collapse was observed in these two cases; the monitor does not define an admissible range. Drift never stopped or modified recursion.","",
        "## Warnings and handoff outcome", "", "All actual meshes remain finite, one component, closed and manifold, with no diagnostic degenerate fan faces. Several schedules nevertheless have nonadjacent transverse contact evidence and many local fold warnings. Their numerical SUCCESS is not a clean-geometry acceptance. Every weak/excluded reason and actual warning count remains in `outcomes.json`, the raw trajectories and per-generation lineage records.","",
        "Crossing audits reuse the existing COMPAS query on at most 4,096 evenly spaced actual faces per generation. They exclude adjacent/coplanar contacts and cap contacts at 30. Zero sampled contacts does not establish global collision freedom. Retained C11 audit results are explicitly the original Task16 scope.","",
        "The independent R13 angular inset vocabulary justified two handoff probes, without establishing hierarchy success. Hybrid A copies C11 G1/G2 exactly; B copies G1/G2/G3 exactly. DS uses the selected six-row R13 schedule at absolute generation numbers, reseeding the first DS input as SOURCE_FACE/FACE pair, without hybrid-specific tuning. Both reach G6. Neither produces a convincing third scale: they soften/replace narrow late CC ribs with broader panels and folds, rather than adding an independent micro vocabulary. Both histories retain local warnings; A has sampled contacts after handoff and B has three sampled contacts at G4.","",
        "**On actual evidence, Digital-Grotesque-level hierarchical complexity does not remain technically plausible within the tested CHESHIRE subdivision schedules.** This is a limitation of the tested framework, not proof that every future subdivision grammar is incapable. The single remaining limitation is stable independent later-scale differentiation: strong family pulses create folds/crossings or repeated angular relief, while restrained tails smooth away the meso structure. No Digital Grotesque reproduction, porosity or mathematical branching is claimed.","",
        "## Reproduction and Rhino", "", "Recipes serialize all six values at every generation in `output/task17/study/recipes`. Normal extrusion ratios multiply the current global mean input edge length, along the unit current face normal. No fields or source attraction are applied. `outcomes.json` also retains the two exact hybrid recipes/prefixes.","",
        "Use the repository venv and a fresh task-local reproduction directory:","", "```powershell", ".\\.venv\\Scripts\\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --init", ".\\.venv\\Scripts\\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --run DS_STANDARD U01_early_expansion U02_interpolation_release U03_sign_change U04_contraction_pulse", "# Run the eight F05–F12 cases, then four R13–R16 cases by their exact recipe IDs, with the same --study argument.", ".\\.venv\\Scripts\\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --run HYBRID_A --hybrid 2 --recipe output/task17/study/recipes/R13_restrained_insets.json", ".\\.venv\\Scripts\\python.exe -E -s examples/subdivision_capability_study.py --study output/task17/reproduction --run HYBRID_B --hybrid 3 --recipe output/task17/study/recipes/R13_restrained_insets.json", "```", "", "Attempted recipes are never overwritten. `--init` copies the existing exact C0/C11 evidence rather than rerunning or changing Task16. It uses the original Task16 evidence when present, otherwise the bundled Task17 C0/C11 copies. `examples/subdivision_capability_delivery.py --generate` serializes the already reviewed canonical study; it does not rank new reproduction results automatically.","",
        "Rhino entry: `rhino/CHESHIRE_Run.py` → **SubdivisionCapabilityStudy**. It loads SHA-verified reviewed outputs from `output/task17/study`, including the selected intermediate DS checkpoints and hybrid, instead of repeating a search within a 60-second interactive run. The C0 template and results are translated to the selected original gate bbox center/floor; scale/orientation stay fixed and the selection stays untouched. C0's established 500-depth template versus the original dense gate's 900 depth remains documented. Best DS and max-capability roles share one mesh/label to avoid duplicate output.", "",
        "Existing environment isolation, timeout/cancellation, per-run directories, atomic response checkpoints, X-only display offsets, TextDots/layers, undo and failure cleanup remain in use. Other modes/default count ceilings are unchanged. Only this mode opts into 120k polygon exchange. Rhino display tessellates n-gons into an explicit fan and stores their original ordered boundaries as MeshNgon groups; calculation/OBJ polygons remain intact. The display approximation is labeled and never fed back into subdivision.","",
        "**Rhino host status:** no running Rhino host was available; no actual host insertion, MeshNgon API execution, UI cancellation or screenshots are claimed. A real isolated .venv subprocess smoke run validates the actual selected cached outputs and response path; standard-library display-plan/loader tests cover the new bridge branch. All images are headless approximate polygon projections, with fixed camera/scale/light and registered crop. `all_*` and `selected_*` plans share exact bounds. Geometry that leaves the detail crop is not recentered.","",
        "Verification ran the full 729-test suite once: 725 passed, and four legacy launcher tests exposed eager capability-only .NET imports. Those imports were moved into the new branch and the original call form restored for existing modes. All four affected checks and all nine Task17 checks then passed (13 passed in the focused follow-up); existing tests were not changed or weakened. Both logs are retained, and the full suite was not repeated.","",
        "Complete-suite/diff logs, final commit identity, archive size/hash and inventory are in the review manifest and delivery record. Semantic field lineage remains NOT IMPLEMENTED; constructive immediate parents and C0 anchor associations are retained separately.",""]
    (ROOT/"docs/TASK17_RESULTS.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")


def smoke():
    sys.path.insert(0,str(ROOT/"rhino"))
    from exchange import CAPABILITY_MODE,validate_response
    directory=ROOT/"output/task17/worker_smoke"/str(uuid4()); directory.mkdir(parents=True)
    request=dict(protocol=1,run_id=directory.name,source=dict(object_id="HEADLESS_WORKER_SMOKE",document_serial=1),mode=CAPABILITY_MODE,mesh=read(STUDY/"C0.json"))
    write(directory/"request.json",request); original=(directory/"request.json").read_bytes()
    process=bounded_child([str(ROOT/"rhino/cheshire_worker.py"),str(directory/"request.json"),str(directory/"response.json")],directory/"logs",60)
    if process["exit_code"]: raise RuntimeError("Worker smoke failed: "+str(process))
    response=read(directory/"response.json"); validate_response(response,request)
    assert response["status"]=="SUCCESS" and response["cached_reviewed_outputs"]
    for variant in response["variants"]:
        assert variant["mesh"]==read(STUDY/f"cases/{variant['id']}/G{variant['generation']}.json")
    assert (directory/"request.json").read_bytes()==original
    write(ROOT/"output/task17/worker_smoke_result.json",dict(status="PASS",process=process,run_id=directory.name,
        runtime_identity=response["runtime_identity"],source_request_immutable=True,all_selected_meshes_exact=True,
        variants=[dict(id=v["id"],generation=v["generation"],vertex_count=v["vertex_count"],face_count=v["face_count"],roles=v["roles"]) for v in response["variants"]],
        note="Real Windows .venv -E -s worker subprocess, no Rhino host."))
    print("Worker smoke PASS",[(v["id"],v["face_count"]) for v in response["variants"]],process)


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--generate",action="store_true"); parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args()
    if args.generate: generate()
    if args.smoke: smoke()
