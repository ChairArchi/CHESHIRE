PARTIAL

# Task29 results — actual reference audit and full staged search

기존 구현에서 발견한 같은 세대 점 의존성의 차이를 고쳤고, 단순 큐브에서 G8까지 실제 형상을 생성했다.
큰 방향 변화와 2차 접힘은 유지된다. 그러나 후기 형상은 반복되는 작은 비늘·주름과 날카로운 면이 강하다.
한스마이어 레퍼런스 수준의 지속되는 비반복 다중 스케일 구조와 평면 법선의 연속감을 증명하지 못했다.
이 판정은 A–C에 이어 D64, E24, 추가 G8 연장과 잠금 제거 대조까지 수행한 뒤 내렸다.

## Repository and verification

Baseline: `a9e456fcc7711ae5920457c49890bc28aa045f1d`. Branch: `experiment/task29-reference-generative-search`.
The exact new local commit is recorded after committing in `analysis/repository_commit.json`;
this tracked report cannot include its own self-referential commit hash. No push or merge. Task30 is a plan only.

All applicable tests: **838 passed, zero skipped**, 45.76 seconds, with actual HDMola 1.0.0 configured under coreclr.
The preceding default run passed 816 and skipped 22 optional-backend tests. Two test environment attempts are retained:
an inaccessible old default pytest temp directory, then a workspace temp path that violated an existing negative
repository-identity fixture's outside-repository assumption. A fresh external temp directory resolved both.
No production behavior or existing tests were changed to pass those checks.
There are 20 new focused mathematical/topology cases. Passing tests establish implementation consistency,
not Digital Grotesque fidelity.

The actual G0–G8 lead regenerates with exact XYZ, oriented polygons, point classes, original-cage association,
ancestry and resolved operator state. Actual G7 reload continues to exact G8. Every generation's OBJ is reread exactly.
The installed Rhino 8.18 writes and rereads the final 3DM with exact coordinates and oriented polygons;
`RhinoDoc.OpenHeadless` opens its one actual mesh. Display normals only are computed in the native file.
No geometry welding, smoothing, triangulation, scaling or repair is applied to the lead export.
GPU depth ordering was independently verified on a two-triangle fixture.
All 1346 actual generated candidate stages, parent links and flat-render source/image hashes were audited.
Legacy weighted/generational/sharp source content matches the Task28 baseline. Original results coexist with the new path.

## Equations and scale decision

The actual [Bridges 2010 paper](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf), including Figure 2,
was read rather than relying on Task28 summaries. Full transcription and the ambiguity analysis are in
`analysis/reference_equation_audit.md`.

The legacy path uses original face centroids for Eq2 and Eq3, and later moves faces separately using Eq4/10.
The reference path completes Eq1/4 then Eq10 faces, feeds those faces to Eq2 and Eq3, and completes Eq11 edges.
Eq3 uses **original endpoint midpoints**, not extruded Eq2 edges; this agrees with Figure 2 and the neutral CC mask.
Consequently face displacement propagates to edges and corners, except at coefficient cancellation;
edge extrusion does not feed the same-iteration corner. Eq4 uses previous-generation input point provenance.
Eq10's completion order is explicit because the paper does not publish executable scheduling code.
This is an audited published-equation implementation with documented conventions, not the unpublished DGII program.

Local Sf = mean current face-perimeter edge length; Se = mean the two incident Sf;
Sv = mean incident Sf. Global S = mean unique current edge length. wf/we/wp are ratios multiplied by S.
Face normals are unit area-vector normals; edge normals are arithmetic incident unit-normal means without
renormalization; vertex normals are normalized incident means. Local scalar and vertex-normal conventions
are deterministic choices where the paper does not specify a unique implementation.

## Mechanism matrix

Same cube and exact five-row schedule, same flat normals, clay, camera and 2600-unit frame:
M0 LEGACY_ISOLATED/GLOBAL_SCALE; M1 REFERENCE_COUPLED/GLOBAL_SCALE; M2 REFERENCE_COUPLED/LOCAL_INCIDENT_SCALE.
G0–G5 saved for all. M0 vs M1 already changes G1 extents from 1467.1 to 1579.1 units.
M1/M2 are exactly identical at G1/G2 while symmetric incident scales coincide. Their corresponding-coordinate
RMS differences at G3/G4/G5 are 4.9233/4.6358/5.1421 units. Local scale has a real later effect, but no convincing
hierarchy advantage large enough to claim success. Continue M2 as the reference/local hypothesis, not because a score proved it superior.

## Exact seed recovery and count policy

18 actual saved recipe/schedule records from Tasks20–28 were reread and SHA256 checked before sampling.
The inventory records originating commit, actual parameters, generation, implementation, visual behavior and known failure.
Historical gate support, crease-only wrappers, dynamic-profile semantics and Mola experiments remain evidence;
they are not smuggled into the cube. H1/H1B absolute offsets are divided by initial side1000 before use as ratios.
Old Task25 efficient/uncalibrated flow recipes were also recovered as sources without claiming they worked on the cube.

Weight order below: wf,w1,we,w2,wp,w3,w4,w6,w7. Ratios after explicit normalization:

| seed | exact round-trip decimal row | u map |
|---|---|---|
| C11A | `0.3,-1.0,-0.08,-0.7,0.1,0.0,0.0,0.0,0.0` | {} |
| C11B | `0.16,-1.05,-0.05,-0.9,0.045,-0.8,0.5,0.0,0.0` | {} |
| C26 | `0.0,-0.7,0.0,-2.8,0.0,0.0,0.0,0.25,0.65` | {"(3,3)": 1.0, "(4,4)": -0.2} |
| H1 | `-0.28,0.8,0.32,-2.8,0.52,0.0,0.0,-0.9,0.8` | {"(3,3)": 2.0, "(4,4)": -1.0, "(5,5)": 2.5, "(6,6)": -1.5} |
| H1B | `0.13,-0.35,0.13,-0.65,0.13,0.0,0.0,0.0,0.0` | {"(3,3)": 2.0, "(4,4)": -1.0, "(5,5)": 2.5, "(6,6)": -1.5} |
| CURVE | `0.0,-0.18,0.0,-0.3,0.0,-0.9,0.5,0.0,0.0` | {} |
| AMP | `0.0,-0.18,0.0,-0.3,0.0,-3.0,1.5,0.0,0.0` | {} |
| GENTLE | `0.0,0.0,0.0,0.0,0.0,-0.6,0.35,0.0,0.0` | {} |
| H1_NO_ATTR | `-0.28,0.8,0.32,-2.8,0.52,0.0,0.0,0.0,0.0` | {} |
| T28_G3 | `0.11199999999999999,-0.735,-0.034999999999999996,-0.63,0.0315,-0.6,0.35,0.0,0.0` | {} |

The actual search reuses C11A/B, C26, H1, H1B, CURVE, AMP, GENTLE and exact Task28 G3;
it includes interpolation, 1.25/1.3 strength expansion, offset sign reversal and cross-generation combinations.
ZERO is retained only as historical reference and neutral mathematical calibration, never used in the lead.

**480 search candidate definitions**, plus three matrix controls, one exact locking ablation and eleven later
continuation definition records = **495 executed definition records**, **20 actual G8 lineages**.
Counts were not reduced for time or memory.

| phase | actual experiment |
|---|---|
| A | 256 deterministic 8×8×4 nonstationary schedules, all G1–G3 |
| B | 32 visually selected A finalists × four nonzero late schedules = 128, actual G4/G5 |
| C | eight visually selected B finalists, actual G6/G7/G8 |
| D | four bases × eight intrinsic rules = 32; another 32 field/threshold/sign retention rules = 64 total |
| E | three strongest initial D bases × two scopes × two timings × two thresholds = 24 |
| later extensions | four initial D, four additional D and three changed E paths to G8; these are eleven continuations |
| exact ablation | selected DX00 fields/rows without locking, same actual G2, actual G3–G8 |

All 256 A, 128 B, eight C late progressions, 64 D, 24 E and later G8 followups were viewed through contact pages.
Cheap extent/dihedral/normal/scale diagnostics assisted inspection. They did not decide the lead or success.

## Intrinsic and topology findings

D was required because globally scheduled modified subdivision continued to produce repeated cells and softened meso form.
Initial D tests NORMAL_VARIATION, ORIGINAL_EDGE_DISTANCE, PLANARITY, LOCAL_SCALE with two bounded strengths.
Additional D uses current geometry fields with vertex locking at normal-disagreement thresholds 0.12/0.28.
These are explicit CHESHIRE experiments motivated by the paper's attribute/tagged-vertex discussion.
Locking is evaluated again each generation; it preserves the current input position only where that step's mask is true.
It is not a permanent cage constraint or arbitrary ID-based displacement.

The exact ablation holds all eight base rows, intrinsic field and intervals constant and removes only locking.
`rule_contribution_isolation.png` isolates base vs intrinsic-only vs intrinsic-plus-locks, and separately compares
the same D00_3 lineage with/without the one G4 weld. The lock contribution is retention of sharper clusters,
with a substantial cost in persistent facet-angle discontinuity. Intrinsic-only variation also changes neighbouring development.
Neither establishes the requested sustained non-repeating small hierarchy.

E was required after D remained insufficient. The opt-in REFERENCE_COUPLED_LOCAL_TOPOLOGY path joins current
generated edge/face points at a threshold proportional to the smaller of their incident scales.
It deterministically selects disjoint pairs, logs coordinates and exact old/new indices, and rejects pinched polygons,
invalid oriented edge incidence, duplicate faces or disconnected vertex links. Pre-weld meshes survive every proposal.
24 proposals: **three valid changed connectivity, thirteen no eligible merges, eight explicit invalid rejections**.
The three changed paths have new valence distributions but all retain genus0/Euler2. No valid porosity or holes were produced.
At the final matching physical scale their visual difference is small; welding did not unlock new recursive motifs.
Some historical early rejection logs say PROPOSED with an invalid_reason; category outcomes record REJECTED_EXPLICITLY,
and no rejected mesh is continued. The later logging fix makes rejection status explicit without rewriting history.
The [official Digital Grotesque II description](https://michael-hansmeyer.com/digital-grotesque-II.html)
motivates a topology hypothesis; this bounded joining experiment does not reproduce its unpublished algorithm.

## Actual selected lineage and full schedule

Lead **FINAL_DX00**. Actual ancestry: input cube → A000 G1/G2 → DX00 G3/G4/G5 → FINAL_DX00 G6/G7/G8.
`lead/lineage_manifest.json` hashes the original candidate and copied actual lead mesh at each stage.
No alternate G3 and no reconstructed stage was substituted.

| generation | wf | w1 | we | w2 | wp | w3 | w4 | w6 | w7 |
|---|---|---|---|---|---|---|---|---|---|
| G1 | -0.28 | 0.8 | 0.32 | -2.8 | 0.52 | 0.0 | 0.0 | 0.0 | 0.0 |
| G2 | 0.16 | -1.05 | -0.05 | -0.9 | 0.045 | -0.8 | 0.5 | 0.0 | 0.0 |
| G3 | 0.11199999999999999 | -0.735 | -0.034999999999999996 | -0.63 | 0.0315 | -0.6 | 0.35 | 0.0 | 0.0 |
| G4 | 0.0 | -0.18 | 0.0 | -0.3 | 0.0 | -0.9 | 0.5 | 0.0 | 0.0 |
| G5 | 0.11199999999999999 | -0.735 | -0.034999999999999996 | -0.63 | 0.0315 | -0.6 | 0.35 | 0.0 | 0.0 |
| G6 | 0.11199999999999999 | -0.735 | -0.034999999999999996 | -0.63 | 0.0315 | -0.6 | 0.35 | 0.0 | 0.0 |
| G7 | 0.11199999999999999 | -0.735 | -0.034999999999999996 | -0.63 | 0.0315 | -0.6 | 0.35 | 0.0 | 0.0 |
| G8 | 0.11199999999999999 | -0.735 | -0.034999999999999996 | -0.63 | 0.0315 | -0.6 | 0.35 | 0.0 | 0.0 |

Every G1–G8 is REFERENCE_COUPLED + LOCAL_INCIDENT_SCALE, with genuine nonzero modified controls.
G3–G8 add the same declared intrinsic rule. No topology weld in the lead. No all-zero, standard-CC or smoothing generation.
G5–G8 repeat the exact nonzero base regime rather than trend toward zero; spatial weights remain recomputed from current geometry.
Exact intrinsic JSON:

```json
{
  "field": "NORMAL_VARIATION",
  "start": 3,
  "gain": 3,
  "lock_threshold": 0.12,
  "controls": {
    "wf": [
      -0.1,
      0.18
    ],
    "w1": [
      -0.35,
      0.35
    ],
    "w2": [
      -0.7,
      0.35
    ],
    "w3": [
      -0.8,
      0.8
    ],
    "w4": [
      0.35,
      -0.35
    ]
  }
}
```

Signal s = clip(3 × (1 − norm(mean incident unit face normals)), 0, 1).
Each specified effective control is base + low + (high−low)s; face/edge signals are the mean corner/endpoint signals.
Other controls are unchanged. Lock mask uses the unscaled current normal-disagreement ≥0.12.
Locked input vertices G3–G8: 74,242,926,2942,13382,55406. Actual per-step scales, signal, mask,
input edges, parent-face/corner mapping and original-cage association are saved, not inferred from renders.

| generation | vertices | original polygons | mean current edge | median adjacent normal angle (degrees) |
|---|---|---|---|---|
| G0 | 8 | 6 | 1000.000 | 90.00 |
| G1 | 26 | 24 | 681.661 | 77.73 |
| G2 | 98 | 96 | 331.637 | 43.92 |
| G3 | 386 | 384 | 157.927 | 42.42 |
| G4 | 1,538 | 1,536 | 81.089 | 42.91 |
| G5 | 6,146 | 6,144 | 41.645 | 33.81 |
| G6 | 24,578 | 24,576 | 22.837 | 35.90 |
| G7 | 98,306 | 98,304 | 12.247 | 36.79 |
| G8 | 393,218 | 393,216 | 6.551 | 37.83 |

G8 remains closed oriented combinatorial genus0: Euler2, zero zero-area faces, finite double-precision coordinates.
It is not certified self-intersection-free, watertight as a physical solid, or printable.

## Retention and visual judgment

First macro: G1. First meso: G2. G3 is the first intrinsic local variation; no generation conclusively demonstrates
the requested **persistent non-repeating** differentiated small scale. G5–G8 generate further facets and local folds,
but much of that information remains correlated with descendant cells.

Nine diagnostic patches (three born each at G1/G2/G3) follow saved face anchors to G8.
Fixed birth-normal depth ranges for representative equivalent patches are 19.999→169.741,
48.832→121.801 and 4.996→56.507 units. All tracked patches survive.
These depth ranges measure later geometry in an ancestral region, not the identity or retention ratio of a specific named ridge.
Normal/extent/RMS curves and three alternative lineages are saved. Increased amplitude may be new folding or drift;
it does not prove retained hierarchy. The actual progression shows persistent broad lobes and secondary directional changes,
while specific early sharp tips contract and fine motifs remain repetitive.

Final 700-unit identical detail crops reveal the repetitive fine folds directly.
There is partial apparent continuity along some silhouettes as facet size falls, but substantial angular clusters remain.
G8 mean edge is 6.551 units while median adjacent normal angle remains **37.83°**, p90 **91.26°**.
Dense topology by itself did not make the local normal changes small. Three qualifying scales and substantial flat-normal
continuity cannot be marked passed. Repeated fine motifs remain a major/dominant component of the small-scale surface.

Task28's actual chosen G5 column vs Task29's actual G8 cube are rendered at the same 2600-unit frame, clay,
light and oblique angles. Camera targets translate from old Z900 to new origin; neither model is scaled.
Task29 has visibly stronger retained angular secondary clusters and additional fine activity; Task28 is smoother
and loses earlier detail. The specimens differ, so this image is a contextual comparison, not a single-variable operator A/B.
The matrix and rule isolation are the controlled comparisons. Task29 improves evidence and retained activity,
but does not achieve the target Digital Grotesque quality.

## What is actually limiting

Hardware did not stop the experiment. The measured guarded generation/render jobs total
372.820s; peak sampled tree plus driver is
1,272,594,432 bytes (1.185 GiB).
These are job-duration sums, not the entire task's elapsed time. Exact replay/OBJ validation took 10.225s;
native operation took 7.080s excluding RhinoCore cold startup, native host peak 564,768,768 bytes.
Resource/job logs contain each real stage/job time. No face-count or elapsed-time cap curtailed the requested search.

The original isolated dependencies were a material equation-fidelity problem and are now an explicit legacy mode.
Correcting them and local scale was necessary but not sufficient in the tested families.
Geometry-driven scalar rules retain cube symmetry for geometrically equivalent regions; they can differentiate
unequal neighbours but cannot create unique local treatment out of exact symmetry by themselves.
Repeated CC ancestry and broadly shared scalar weight regimes continue to seed cell motifs.
Keeping folds by freezing corner positions preserves sharp normal jumps and promotes dense angular texture.
The minimal valid edge collapses change valence without introducing a useful porous motif generator.
These are conclusions about this bounded experiment, not proof that every Hansmeyer-style system is incapable.

## Review files and next task

Open `renders/FINAL_LEAD_PROGRESSION.png` first, then `lead_details.png`, `rule_contribution_isolation.png`,
`mechanism_matrix.png`, and the search pages. All primary renders use flat normals.
Only the render's declared diagonal 0–2 display triangulation and float32 display conversion are used;
saved NPZ/OBJ/3DM retain double coordinates and original quads. Intentional detail crops disclose vertices outside frame.

Full root: `E:/CHESHIRE_DATA/task29/`. Review archive: `CHESHIRE_TASK29_REVIEW.zip`.
Model/continuation archive: `MODEL.zip`. Archive manifest/CRC/SHA verification is written in `analysis/archive_validation.json`.
Read `docs/TASK29_HANDOFF.md` for exact commands and `docs/TASK30_CONSOLIDATION_PLAN.md` for consolidation decisions.
Task30 has not started.
