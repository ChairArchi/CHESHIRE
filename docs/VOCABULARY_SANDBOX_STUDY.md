# Task 21 — Vocabulary expansion sandbox

CHESHIRE experimental branch `experiment/task21-vocabulary-sandbox` starts
from Task 20 `9afa414eca1353a7678432538902f55d87edcd41`. Main, Task 17's
checkpoint, and the Task 19/20 branches are preserved. This is a headless
geometry study, not a Digital Grotesque reproduction.

Task 20 provided differentiated, nested cap/ring/side branches, but its
strongest Hero still read as repeated parent-face cells. Task 21 tests whether
directional growth, sharp ridges, and connected routing cohorts can make
larger ornament assemblies. No terminal smoothing is used.

## Geometry and grammar contract

Only two new face-local event types enter the isolated experimental module:
`DirectionalExtrusion` and `Roof`. Geometry comes from the official external
HDMola 1.0.0 assembly, loaded through the existing pythonnet/CoreCLR .NET 8
adapter. CHESHIRE supplies deterministic local frames, selection, composition,
budgets, routing patches, and constructive ancestry. It does not implement a
replacement Mola algorithm. COMPAS remains the mesh foundation.

Actual reflection verifies `Extrude(Vec3[], Vec3, Single, Boolean)` and
`Roof(Vec3[], Single, Single)`. Probe evidence includes a unit quad, elongated
quad, nonplanar quad, triangle, and actual C07/Hero quads at three area ranks.
Raw probes retain returned coordinates, face order, repeat comparisons, and
boundary evidence. Twelve full-mesh single-face wrapper probes establish the
closed-mesh and positive-lineage contracts on actual saved references.

Direction extrusion retains the original unsplit boundary and creates one
side per ordered corner plus a cap. Its roles are
`DIRECTIONAL_EXTRUSION_SIDE` and `DIRECTIONAL_EXTRUSION_CAP`.
Roof is accepted only for eligible quads: two new ridge vertices, four
children in verified `RIDGE_END, RIDGE_SIDE, RIDGE_END, RIDGE_SIDE` order.
There is no invented ridge cap, strip role, stitching, weld, or repair.

LinearSplitQuad and LinearSplitQuadBorder produce real directional bands in
the raw probe. Variable minimum/maximum width is nondeterministic in the
tested call. Deterministic fixed-width/border calls subdivide outer edges;
their untouched neighbors would then require conforming refinement or
stitching. They are excluded from the closed-gate grammar. ExtrudeToPoint is
reflected but not used; no third event type is added just to enlarge the list.

For direction, `N` is the oriented first-triangle normal compatible with the
Mola constructor. `T1` projects the selected architectural world axis into
that tangent plane; `T2 = N × T1`. Outward signs derive from the source
gate centerline. Degenerate projections use a deterministic ordered-edge
fallback with a fixed sign. A connected patch can first project its common
axis into an area-weighted mean plane. Each face then constructs its own
orthonormal frame. All frames, signs, cyclic Roof rotations, direction vectors,
and offsets are recorded. A warped quad's Roof constructor normal is
recomputed after its orientation-preserving cyclic rotation and recorded
separately; the input is never flattened.

Roof can choose only between the quad constructor's two directions, through a
cyclic input rotation. A preferred patch axis is therefore a target, not a
guarantee that neighboring actual ridges are parallel or meet. Later runs
record the actual ridge axis and its absolute dot product with `T1`; earlier
records without that diagnostic remain explicitly unavailable.

Routing patches are actual face-adjacency components with matching positive
source support, constructive role/history class, and broad orientation class.
They coordinate axis, rule, and parameter family. Every Mola call still acts
on one face. Parent/root counts describe graph ancestry, not visual proof of
an assembly. Quiet branches and exclusion counts are explicit.

New vertex ancestry describes positive constructive parents before the
separately recorded geometric offset. It is not a displacement interpolation
coefficient. Roof's two ridge points use verified positive edge-midpoint
weights. No unique source-corner anchor is guessed for those points.

The exact first five saved C07 stages are frozen for every study recipe;
their ordered geometry hashes are checked in every worker. The separately
retained full C07 reference has 30,208 faces; the experimental prefix ends
after its first InsetFrame at 4,480 faces. A03, D02, and the Task 20 Hero
fragments are loaded from serialized recipes, not numerically reconstructed.

Early Phase-A routing also reordered construction while grouping patches.
That was corrected to preserve the existing selector order. An independent
reverse-event audit recovers each early Hero input and proves exact oriented
face/vertex coordinates up to key renumbering against Task 20. Early outputs
and their source hashes remain intact. The corrected full Hero control and
final Hero replays check ordered identity rather than hiding this distinction.

Screening uses task-local 150,000 faces; deep cases 300,000. The optional
production ceiling is 750,000 and the study storage ceiling is 6 GiB.
Existing process isolation, interpreter identity, cancellation, timeout,
memory guard, and global budgets remain unchanged. Per-stage contacts use a
bounded 4,096-face sample and a 30-contact cap. Zero is `CLEAN_SAMPLE`, a
positive count below the cap is `LOW_CONTACT`, and a cap hit is `UNSTABLE`.
Zero never means globally collision-free. A separate exact geometry cohort
tracks the 12 contacts already present in the full frozen Stage-5 audit;
zero cohort retention after geometry changes does not certify resolution.

All views project actual polygons using the existing Task 19 front, oblique,
and registered-detail cameras, identical scale, and the same simple gray
lighting. Diagnostic views color constructive roles, complete positive
signatures, latest new-event patches, and depth; mixed ancestry remains mixed.
No image generation, beauty camera, mesh cleanup, or smoothing is used.

## Reproduce

Use the existing Python 3.12 `.venv`, unchanged dependencies, official external
DLL, and installed .NET 8 runtime. Supply the DLL path explicitly; nothing
is copied into CHESHIRE or installed into Rhino.

```powershell
.\.venv\Scripts\python.exe -E -s examples\vocabulary_probe.py --dll <official-DLL> --probe
.\.venv\Scripts\python.exe -E -s examples\vocabulary_probe.py --dll <official-DLL> --wrappers
.\.venv\Scripts\python.exe -E -s examples\vocabulary_study.py --init --dll <official-DLL>
.\.venv\Scripts\python.exe -E -s examples\vocabulary_study.py --phase A --run A_R04 --dll <official-DLL>
.\.venv\Scripts\python.exe -E -s examples\vocabulary_verify.py A
.\.venv\Scripts\python.exe -E -s examples\vocabulary_review.py A
powershell -NoProfile -ExecutionPolicy Bypass -File tools\vocabulary_projection.ps1 -PlanPath output\task21\study\A_projection_plan.json
```

Initialization is intentionally fresh-only. Serialize additional families
using `vocabulary_recipes.composition_recipes()` / `assembly_recipes()` or
copy a delivered recipe into the study's `recipes` directory. Completed valid
cases resume only after request, source/operator hashes, and artifact hashes
match. The final review archive contains the actual study, full finalist/Hero
checkpoints, and shared exact prefix once. It excludes external binaries.

For an extracted review package, the study is already initialized: do not run
`--init` over it. Supply the external official DLL to regenerate a delivered
serialized recipe. A source-version change correctly invalidates resume and
creates a new attempt. No old attempt is overwritten.

```powershell
.\.venv\Scripts\python.exe -E -s examples\vocabulary_study.py --phase HERO --run HERO_ORDERED_RIDGES --dll <official-DLL>
.\.venv\Scripts\python.exe -E -s examples\vocabulary_verify.py HERO
```

Primary terminal verification requires regenerating the primary cases omitted
from the compact archive. Full finalist/refinement/Hero geometry is included.
`vocabulary_delivery.py` audits independent Hero workers and prepares fixed
comparison plans; its exact primary-geometry counting also needs those omitted
primary terminals. The delivered `delivery_totals.json` retains that completed
audit. `studies/task21/recipes.json` stores every exact declaration, quiet rule,
operator order, and parameter without reconstructing them by hand.

## Actual experiment

| Phase | Completed phase cases | Technically valid | Purpose |
|---|---:|---:|---|
| A | 20 | 13 | Ten directional and ten ridge recipes |
| B | 50 | 31 | Five composition families, ten recipes each |
| C | 14 | 3 | Connected routing/mean-plane/quiet assembly comparisons |
| F | 14 | 13 | Thirteen promotions plus the exact old Hero control |
| R | 24 | 24 | Twenty-two refinements plus two exact DS handoff diagnostics |
| HERO | 2 | 1 | Two deliberate final compositions |
| REPLAY | 2 | 1 | Two independent full-worker reproductions |

There were **127 actual external whole-gate worker attempts**, including one
repeat of the rejected Hero during a resume check. Eighty-six attempts were
technically valid. The 126 selected phase cases are not distinct designs:
promotions, handoff diagnostics, and replays are explicit repeats. Primary
search contains 84 recipes (20 A + 50 B + 14 C), with 47 technical successes.
The 64 B/C recipes meet the substantial composition-search target.

Primary geometry has 81 exact coordinate/oriented-polygon classes. A_R01/A_R05,
B4_01/B4_09, and B5_03/B5_10 each share an exact result. Different preferred
Roof axes can select the same discrete constructor orientation; these are not
visibly different designs. All promoted finalists pass exact coordinate and
oriented polygon multiset checks. Two early promotions differ in key order.
A_R04's sampled contacts change from 21 to 15 at promotion without geometry
improvement. The identity audit preserves both counts and source versions.

All ten B1 lateral-fin compositions hit the bounded contact cap. Small stable
directional shifts mostly retained the panel motif. Large-side Roof variants
yielded sharp creases; the strongest B5 variants retained the differentiated
Hero branches. Linear split failed the integration gate, so B3/B4 explicitly
use alternative directional/ridge/existing cap-frame compositions. The strip
representative is its raw probe, not a fabricated whole-gate strip result.

Six selected sources received three refinements each. After sideways/upward
roof-end growth contacted neighboring envelopes, two of those sources received
two extra front-biased end variants each. There are 22 refinements, at most
five per source. Heights, normal ratio, gable inset, and explicit upper-region
quiet thresholds changed; the macro weights were never reopened. All completed,
but stability did not produce a visual breakout from the repeated scaffold.

Two DS handoff diagnostics replay B4_05 and B4_10 exactly, retaining pre-DS,
post-DS, and post-nested-inset checkpoints. Each coordinate/cycle hash matches
the actual primary checkpoint. Fixed detail comparisons show lost crest
definition and rounder panels after DS. Their density is not treated as a new
ornament scale. The largest actual terminal had 146,946 faces. Summed worker
time was 5,268 seconds; largest sampled driver/process-tree memory was
1,243,607,040 bytes. Evidence occupied about 1.68 GiB before packaging.

## Morphology library

Seven context-bound fragments are retained:

- `C11_MACRO_MASS`: exact existing two-stage macro preparation.
- `C07_GATE_BACKBONE`: exact five-stage experimental prefix.
- `A03_ANGULAR_CAP`: existing gate-legible angular cap language.
- `D02_ORDERED_FRAME`: existing ordered intermediate DS language.
- `HERO_CAP_RING`: existing ring and raised-cap descendants.
- `HERO_SIDE_FIN`: existing Task-20 side branch and nested frame.
- `NEW_FLANK_RIDGE`: larger-side Roof fragment from F_B5_01.

Each entry records its actual source/stages, required input role/context,
operator sequence/parameters, intent, positive constructive ancestry, geometry
hash, and failure boundaries. Arbitrary transplantation is not established.
`NEW_DIRECTIONAL_FIN` is excluded: offset plates/shelves did not form a coherent
fin assembly. `NEW_STRIP_FIELD` is excluded by boundary/determinism contracts.
Repetitive cap-centered Roof is also omitted. A verified experimental wrapper
does not automatically become a useful morphology-library fragment.

## Conditional nonlinear fixture

Both new operators worked on real faces while strong candidates remained
cell-bound, so the condition was met. One isolated two-quad fixture was tested;
**zero nonlinear whole-gate cases** were run.

Hansmeyer describes treating coincident vertices as one and threshold-based
joining as ways to alter topology and introduce nonlinear behavior. This is
the conceptual precedent, not a CHESHIRE implementation specification.
See [Design by Subdivision, Bridges 2010, pp. 169–170](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf).

Authentic directional extrusion creates 14 vertices and 10 faces from two
adjacent unit quads. Threshold is frozen at `1e-5 * original_mean_edge`.
Only new vertices with the same constructive source-corner parent can pair;
source boundary vertices are protected. Two pairs qualify geometrically.
Their alias quotient would have edges incident to four faces and repeated
directed edge incidence because facing interior walls remain. It is rejected
before COMPAS could overwrite halfedge incidence. No alias is applied, no wall
deleted, and the complete before checkpoint/rejected proposal are retained.
The unchanged fixture stops the phase. No accepted new topology is produced;
this is not a general verdict on nonlinear constructions.

## Final geometry and visual assessment

| Result | Faces | Depth / terminal signatures | Sampled contacts | Assessment |
|---|---:|---|---:|---|
| Task-20 Hero control | 18,544 | 4 / 10 | 0 | Exact differentiated baseline |
| F_B5_01 | 20,764 | 4 / 11 | 3 | Strongest broad flank crests; two bilinear warnings |
| R_B5_02_2 | 20,448 | 4 / 12 | 1 | Best directional plates; remain local |
| R_B5_03_4 | 22,999 | 4 / 13 | 1 | Existing branches + Roof + front-biased end shelves |
| HERO_ORDERED_RIDGES | 22,576 | 5 / 13 | 0 | Upper flank crests and nested small crests |
| HERO_BRANCHING_PLATES | 21,564 | 4 / 14 | 30, capped | Rejected crest-on-plate combination |

The ordered Hero concentrates large Roof events above a serialized threshold
and adds small crests within existing side frames. The branching Hero retains
lateral plates and places small Roof events on their upper caps. Its Stage 11
parent is stable; Stage 12 hits the contact cap. That offending mesh is retained.
A third Hero was not invented to fill the quota.

Both recipes reproduce in independent workers: ordered coordinates/cycles,
decoded lineage/history/events, signatures, routing tables, and all downstream
geometry checkpoints match exactly. The valid Hero resumed by verified skip.
The rejected one intentionally reran and reproduced the cap stop. Gzip
container timestamps are not used as semantic equality.

Large flank creases form some aligned chevrons/ribbons across adjoining cells.
F_B5_01 has 20 patches spanning parent cells and roots; the ordered Hero has
ten. This supports partial alignment, not a dominant multi-cell assembly.
Four-window/panel groupings still dominate the meso reading. New fine crests
are crisp but thin; directional shelves remain small. Aggressive end/branch
growth produces pinching/contact clusters. Intermediate DS weakens detail.

Result labels compare actual evidence within this bounded study:

- **BEST_NEW_OPERATOR:** Roof on larger flank faces.
- **BEST_DIRECTIONAL_ORNAMENT:** R_B5_02_2, plates rather than a successful fin assembly.
- **BEST_RIDGE_OR_STRIP_ASSEMBLY:** F_B5_01, partial ridge alignment; no accepted strips.
- **BEST_BRANCHING_COMPOSITION:** R_B5_03_4, stable ridge/end differentiation.
- **BEST_GATE_LEGIBLE:** frozen F_A03_CONTRAST; additions did not clearly improve it.
- **BEST_GEOMETRIC_ORDER:** frozen F_D02_CONTRAST, retained as the strongest ordered reference.
- **MAX_ORNAMENT_CAPABILITY:** HERO_ORDERED_RIDGES, added sharp vocabulary and depth five.
- **MOST_INFORMATIVE_FAILURE:** HERO_BRANCHING_PLATES, stable parent to capped crest stage.
- **GROTESQUE_GATE_CANDIDATE:** none established.

The single dominant explanation is **A: these face-local constructions retain
the parent-cell scaffold**. Connected routing coordinates axes/rules but does
not change cell junctions. This is an empirical result of the tested vocabulary
and backbone, not proof that all face-local methods fail or nonlinear topology
is necessary. No next solution is implemented.

No human acceptance review or Rhino host run occurred. Evidence is headless
COMPAS/CoreCLR geometry, independent replays, diagnostics, and agent inspection
of fixed actual-polygon views. No Grotesque milestone or Digital Grotesque
equivalence is claimed. There is no strong near-candidate to justify production;
the conditional 750,000-face run and new Rhino mode are omitted. Existing modes
are unchanged.

## Integrity and delivery verification

Principal results are the ordered Hero and R_B5_03_4. Both retain support order,
lintel-above-support landmarks, all source anchors, and closed one-component
manifold topology. Relative overall W/H/D changes are respectively
`+12.625 / +13.176 / +119.406%` and `+12.625 / +13.159 / +120.200%`.
Landmark opening W/H changes are `+0.404 / -19.044%` and `+0.471 / -19.128%`.
Opening-center X/Z drifts normalized by source W/H are `(0, +0.058637)` and
`(-0.000000687, +0.058328)`. Both support bases move up 452.806 source units
(`0.129373` source height), largely inherited from the frozen backbone.
These corner-descendant landmarks are approximations, not exact free opening
clearance; complete anchor data remain in each stage monitor.

Principal terminal contact samples are zero and one; zero unchanged pairs from
the 12-pair frozen Stage-5 cohort remain. This does not prove those original
intersections resolved. Principal terminal fan/bilinear/degeneracy warnings
are zero. Wider retained terminals have up to two fan and two bilinear warnings;
all IDs and offending stages are preserved. There is no silent repair.

The complete existing suite ran **once**, with the official DLL available:
**759 passed in 42.34 seconds**. Eight focused tests cover live construction,
roles/boundaries/lineage, deterministic frames/patches, serialization, exact
mixed plate/ridge repetition, old-engine compatibility, and nonlinear rejection.
Real Hero worker replays establish whole-gate repetition. No existing test or
identity guard was weakened. A fresh external pytest temp root is required by
the existing wrong-repository identity test.

`git diff --check` passed. Final distribution audit, commit/push identities,
35-answer report, test logs, and archive inventory accompany delivery. Only
the experimental Task-21 branch is published. Main, Task-17's checkpoint, and
Task-19/20 branches remain protected.
