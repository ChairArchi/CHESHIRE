# Task 15: carrier scale and generation schedules

**Mixed result:** carrier resolution changes the scale of deformation and the available generation count. C0 develops broader forms than C1/C2 or the dense gate. However, none of the ten subsequent schedules establishes clear macro → meso → micro articulation. Most stable results round the broad forms; stronger fine detail becomes repetitive or crosses. This is a bounded study result, not design success or a general impossibility claim.

Baseline: `9c637bb5ea17d43c7450394832689254c61d7363` (`Add weighted subdivision grammar prototype`). The Task 14 operator, dependencies, existing Rhino modes, Mola integration, fields, budgets and lineage code are unchanged. Experiments live in `rhino/carrier_study.py` and `examples/carrier_scale_study.py`; geometry runs through the existing Task 14 uniform weighted-subdivision study.

The user's replacement section 10 takes precedence over the attachment's earlier spatial-study plan: resolve carrier scale, select one carrier, compare 8–16 schedules without spatial fields, then permit one regional demonstration **only after useful hierarchy exists**. That gate was not met. Spatial weights, an influence preview, intrinsic feedback and the conditional `CarrierScaleStudy` Rhino mode were therefore not implemented.

## Carriers and actual growth

C0 is the exterior boundary of five adjacent occupied rectangular grid cells. Shared corner IDs create connected support/lintel junctions; interior interfaces are never emitted. It has 22 planar outward quads, finite coordinates, one closed manifold component and positive volume 4,140,000,000. The architectural opening remains open to the ground; it is not a naked topological boundary of the solid.

Dimensions are width 4000, height 3500, depth 500, opening width 2200 and opening height 2600. Coordinates were translated by `[-400.036865234375, -18.533447265625, 0]` to register the saved gate's X/Y bounding-box center and ground Z. No detail fitting, welding or simplification occurs. C1/C2 use one/two ordinary COMPAS quad refinements of exactly C0's surface, preserving all original vertices and without smoothing.

| Carrier | Input V / E / F | Components / boundary edges | Bbox X / Y / Z | A and B reach | Final V / F |
| --- | --- | --- | --- | --- | --- |
| C0 | 24 / 44 / 22 | 1 / 0 | 4000 / 500 / 3500 | G5 | 22530 / 22528 |
| C1 | 90 / 176 / 88 | 1 / 0 | 4000 / 500 / 3500 | G4 | 22530 / 22528 |
| C2 | 354 / 704 / 352 | 1 / 0 | 4000 / 500 / 3500 | G3 | 22530 / 22528 |
| DENSE | 1030 / 1956 / 936 | 10 / 568 | 4000 / 900 / 3500 | G2 | 14522 / 13376 |

| Carrier | Mean / median face area | Mean / median edge length | Extraordinary interior vertices |
| --- | --- | --- | --- |
| C0 | 1211818.18 / 1100000 | 1218.18 / 900 | 16 |
| C1 | 302954.55 / 275000 | 609.09 / 450 | 16 |
| C2 | 75738.64 / 68750 | 304.55 / 225 | 16 |
| DENSE | 37115.38 / 44217.91 | 215.17 / 232.44 | 195 |

Complete area/edge distributions, actual valence histograms and every extraordinary vertex's ID/XYZ are in `carrier_statistics.json`. C0 valences are `{3:12, 4:8, 5:4}`; the valence-5 vertices lie at the four inner support/lintel junction corners. None is classified as an error.

C0/C1/C2 isolate starting resolution on the same surface. DENSE is the exact retained mixed-face gate (400 triangles / 536 quads), and also differs in depth, detail, components and boundaries. Its comparison cannot attribute all differences to resolution alone. Sources were saved before generation; the source comparison figures use these unchanged saved files.

## Carrier selection before schedule development

Six deterministic local fold-neighborhood attempts ran on C0 through G3. Every attempt and warning remains in the bundle. Original `L0_reference_fold` has actual sampled crossings (8 at G1, 30 at G2/G3, reaching the diagnostic contact limit). `L4_macro_corner` was selected for broad support/shoulder deformation with zero sampled crossings and no conservative bilinear warnings through G3; fan-normal warning counts were 8 / 16 / 0. `L5_gentle_fold` was also quiet but visually gentler.

Primary A is unchanged Task 14 `attenuated`; primary B is L4. Each uses exactly the same six explicitly serialized rows on all four carriers, with no retuning or fields. As in Task 14, `wf/we/wp` are ratios of the generation's **global mean input edge length**, while `w1/w2` are dimensionless interpolation values. Thus refining the initial carrier reduces both the input cell size and the physical extrusion scale; this study tests that existing mechanism, not a new scale-invariant variant.

L4 rows in `(wf, w1, we, w2, wp)` order:

| Generation | Exact ratios |
| --- | --- |
| G1 | `(0.30, -1.0, -0.08, -0.7, 0.10)` |
| G2 | `(0.16, -0.85, -0.05, -0.6, 0.045)` |
| G3 | `(0.08, -0.55, -0.025, -0.35, 0.015)` |
| G4 | `(0.08, -0.55, -0.025, -0.35, 0.015)` |
| G5 | `(0.08, -0.55, -0.025, -0.35, 0.015)` |
| G6, not reached | `(0.08, -0.55, -0.025, -0.35, 0.015)` |

| Pair | Actual visual progression |
| --- | --- |
| A/C0 | G1 changes whole supports/lintel; G3 rounds broad forms; G5 mostly further rounding. |
| B/C0 | G1 forms broad support/shoulder lobes; G3 preserves them with facets; G5 loses much meso detail. Best macro carrier, weak hierarchy. |
| A/C1 | G1 adds repeated support/shoulder lobes; G3 rounds them; G4 retains small repeated ripples. |
| B/C1 | G1 repeats smaller lobes than C0; G3 refines those lobes; G4 reads as ribbed supports and shoulder buttons. |
| A/C2 | G1 adds many fine cells; G3 rounds them into shallow repeated corrugation. |
| B/C2 | G1/G2 articulate a repeated small-cell pattern; G3 remains tiled/ribbed. |
| A/DENSE | G1 fine tiled relief; G2 softens it, without broad restructuring. |
| B/DENSE | G1/G2 repeat fine surface undulations, with 28 sampled crossings at G2. Unsafe control. |

C0 was selected only after all eight primary runs and their matched views were reviewed. The gate silhouette and opening remain recognizable, but dimensions are not constrained: B/C0 G5 bbox is approximately 4363 × 865.5 × 3856.3, and feet move below the original ground. No opening-dimension or envelope preservation claim is made.

## Ten non-stationary schedule attempts on C0

All ten use identical C0 input, camera, scale, 50,000-vertex/face limits, and no spatial fields. Each retains G0–G5; G6 is blocked before geometry execution. Every planned generation, including blocked G6, has its own serialized row. There are 24 executed cases overall (6 local, 8 primary, 10 schedule) and 16 unique schedules including repeated controls.

| Schedule | Intent and observed limitation at G5 | Fan / bilinear warnings | Sampled crossings |
| --- | --- | --- | --- |
| T00 fixed | Repeats L4 G1; noisy repetitive folds, unsafe | 9000 / 1284 | 30, limit reached |
| T01 seed | L4 schedule; broad forms remain, fine hierarchy weak | 4 / 0 | 0 |
| T02 macro attenuation | Strong early extrusion, weaker later controls; mostly rounds | 0 / 0 | 0 |
| T03 meso interpolation | Stronger G2/G3 interpolation distinction; detail fades in fine tail | 0 / 0 | 0 |
| T04 edge then face | Alternating point-class emphasis; stable, still rounds | 0 / 0 | 0 |
| T05 corner then edge | Early corner emphasis; broad shoulders, weak smaller articulation | 0 / 0 | 0 |
| T06 delayed meso | Stronger G3; intermediate facets attenuate rather than persist | 0 / 0 | 0 |
| T07 alternating sign | Alternating extrusion signs; stable, no clear nested organization | 0 / 0 | 0 |
| T08 fixed moderate | Repeats L4 G2; repeated corrugation, locally warning-prone | 1084 / 20 | 0 |
| T09 meso fine | T03 prefix plus stronger G4/G5 detail; repeated relief and crossings | 24 / 0 | 8 |

T08/T09 were explicit follow-ups after the first eight: T00 was unsuitable as a safe constant control, and T03's fine tail erased detail. T08 is **not** certified locally clean merely because its crossing sample is zero. T09's stronger fine tail produces actual contacts, not useful hierarchy. The original attempts and extension rationale are retained, with no overwritten recipes. T03 is a representative quiet weak result, not a successful final schedule.

## Diagnostics and limits

Every completed stage records bbox and change from G0, face/edge distributions, counts, actual effective weights, previous retained-corner median/max motion, fan and existing conservative bilinear warnings, topology associations and separate crossing audit. Actual total process and audit times are measured. The first executed cases predate explicit per-checkpoint timing instrumentation: their `checkpoint_timing.json` reports clearly labeled mesh-file timestamp estimates, including processing/exports, rather than invented backend timings. Reproduction runs now record monotonic checkpoint times. Retained-corner motion is not a full-surface displacement metric. COMPAS polygon areas/volumes and viewer triangle fans approximate nonplanar quads; they are not exact bilinear integrals.

Extraordinary association is observational: a face is nearby if incident to an extraordinary vertex or its one-hop neighbor. B/C0's four final fan warnings are nearby, but B/C1 G1 has 16 nearby versus 80 distant warnings; B/C2 G1 has 16 nearby versus 640 distant warnings. A on the same topology can finish without warnings. Support/lintel transitions show concentrated facets and some pinching, but extraordinary topology alone is not established as the cause. Exact corner/valence examples and overlays are retained.

Opposed diagnostic fan normals can occur on a saddle quad that passes the conservative bilinear test. Neither should be silently relabeled as a proven global inversion. Sampled nonadjacent transverse crossings use the existing COMPAS triangle diagnostic, excluding adjacent/coplanar contact, capped at 30 contacts per stage. Zero sampled crossings is not a global collision certificate. All executed stages are finite and had zero degenerate-fan warnings; topology remains one closed component for C0/C1/C2 and ten open components for DENSE. No cleanup or repair occurs.

Global subdivision first exhausts count budgets at C0 G6, C1 G5, C2 G4 and DENSE G3. Each next closed-carrier step requires 90,114 vertices / 90,112 faces; DENSE G3 requires 55,786 / 53,504. Local refinement would be most relevant to preserving selected C0 G3 meso regions beyond G5, but the present limitation is meaningful articulation, so extra polygons alone are not justified as a solution. No adaptive refinement is implemented.

The study uses fresh serial subprocesses with the explicit repository venv, `-E -s`, existing sanitized environment, explicit cwd, `shell=False`, logs, 60-second geometry/30-second audit deadlines, 4 GiB combined resident cap, existing available-memory floor and 3 GiB study storage preflight. Per-case process and runtime identity records confirm actual execution. Checkpoints survive later budget stops as PARTIAL. Full semantic lineage remains **NOT IMPLEMENTED**; existing point-class identities, positive control-cage sampling associations and immediate face relationships remain recorded separately from geometry coefficients.

## Reproduce and review

Unzip the review bundle, read its `REVIEW_MANIFEST.md`, then inspect `output/task15/study/primary_sources.png`, `primary_final.png`, `generation_all_final.png`, `generation_detail_shaded.png`, progression panels and `topology_warning_locations.svg`. These are actual saved polygons under one fixed headless projection and registered detail crop; wire images include back edges. There is no presentation smoothing. These images are not Rhino captures.

Reproduce one case into a new, unused output directory using its exact saved source/schedule:

```powershell
.\.venv\Scripts\python.exe examples\carrier_scale_study.py --one output\task15\reproduce_T03 --input output\task15\study\carriers\C0.json --schedule output\task15\study\schedules\generation_T03_meso_interpolation.json --generations 6
.\.venv\Scripts\python.exe tools\morphology_crossings.py output\task15\reproduce_T03
```

The direct single-case command is a normal-shell diagnostic. The phased batch runner bounds each child separately. For a fresh study, initialize with an explicit retained DENSE JSON, then run `local`, review/select B, run `primary`, record the carrier choice in `review_decisions.json`, and run `schedules` on that carrier only. `extensions` preserves the first eight. Existing case directories are rejected to prevent overwriting attempts. `examples/carrier_study_review.py audit` verifies delivered evidence; its `views`/`diagnostics` commands reproduce the small follow-up figures and observational overlay.

Actual Rhino execution for Task 15 is **NOT RUN**. No conditional new mode was added because the schedule gate failed. Existing launcher/display/cancellation/Undo behavior was not changed. The future conceptual coarse-carrier-plus-fields → CHESHIRE contract remains plausible at the carrier interface, but multi-scale growth and spatial differentiation are not demonstrated here. No ALICE repository or working copy was accessed.
