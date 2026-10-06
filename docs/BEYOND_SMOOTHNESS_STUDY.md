# Task 22: beyond smoothness

This is an isolated study of subdivision-point placement. Task21's Roof vocabulary
added crests but retained repeated parent-cell panels. Task22 investigates whether
literal motif attraction, finite nonstationary weights and temporary corner locks
change that organization. Technical validity does not establish design success.

The exact protected baseline is `0090fc816c8d7a1bcb755114a859c295047c7b0b`.
Work belongs to `experiment/task22-beyond-smoothness`; main, Task17's checkpoint
and Task19/20/21 branches remain protected. Existing geometry backends, Rhino
modes, dependencies and global defaults are unchanged.

## Reference and implementation

See [the reference contract](BEYOND_SMOOTHNESS_REFERENCE.md) for primary sources
and the separation of REFERENCE-GROUNDED, CHESHIRE-DEFINED and EXPERIMENTAL RECIPE.
The new wrapper evaluates the existing Extended CC points first, then applies
literal unnormalized Eq10/11 sums using original input corners/endpoints.

`w(i)=a+b*(i-1)^q`, with explicit positive q and a finite requested horizon,
applies to all nine controls. Every recipe serializes declarations and evaluated
rows. Motifs are connectivity-only `(valence, incident_face_count)`, unknown u=0.
Positive products move along vectors toward active corners; negative products
reverse them. Symmetric sums cancel and sufficiently large products overshoot.

Literal lock groups retain only persistent CC corner descendants for their first
L sharp iterations. New edge/face points never acquire those tags. The L0/1/3/6
hexahedron comparison demonstrates fixed tips, with a weak continuous-edge
effect. No stronger descendant-edge lock or projection is substituted.

Source-distance experiments use frozen graph edge hops, inherited through
positive constructive samples. Planarity experiments reuse the existing
incident-normal variation proxy. Their local interpolation/averaging conventions
are CHESHIRE choices, not a new differential curvature calculation.

Strict zero-feature regressions match exact coordinates, polygons, constructive
sampling and origins for cube, column and C0. A real saved Task21 C11 stage is
matched by ordered geometry SHA. The actual C07 continuation also exactly matches
the unchanged backend with 2,560 eligible later-generation Eq4 faces. There are
no ordering differences. Original source geometry is checked for immutability.

## Execution and evidence

Heavy data use an explicit external root; no C-drive fallback is allowed.
Recipes use relative references. NTFS write/read/delete and free-space checks
precede execution. Existing birth-verified process isolation, interpreter
environment isolation, cancellation, 900-second case timeout, 4GiB process-tree
plus driver limit and available-memory floor remain in effect.

The same first five C07 operators and ordered geometry hashes are frozen. The
secondary substrate is the real Task21 ordered pre-ridge core. Existing corner
landmarks are recovered from verified constructive records and checked against
the exact old monitor at S05/S10/S12; 88 C07 and 392 ordered landmarks remain.
No nearest-coordinate or generic dominant-parent assignment is used.

Each reached generation retains actual mesh, immediate positive associations,
known CC origins, source/role/event ancestry, motif histogram, requested and
effective weights, locks and diagnostics. Signed geometric coefficients are
not invented semantic inheritance weights. Checkpoints and all event stages
are preserved before technical stopping; no automatic repair occurs.

High-dihedral edges use a declared 45-degree threshold. Connected edge structures
are counted across frozen S05 cells and, separately, original coarse C0 faces.
`cross_cell_sharp_components` is a comparative connectivity diagnostic: a chain
crossing cells does not prove a coherent visible motif or hierarchy.

Crossing checks use at most 4,096 deterministically spaced ordered faces and a
30-contact stopping cap. Nonadjacent transverse polygon-fan contacts are sampled;
coplanar/adjacent contacts are excluded. Zero sampled contacts is not a collision
certificate. Face fan and bilinear warnings remain explicit.

VALID_SHARP means admissible under these checks, even if visually smooth/weak.
BOUNDARY_SHARP retains localized fan/bilinear warnings or nonzero sampled
contacts. UNSTABLE means degenerate/zero-area geometry, topology failure or the
crossing cap. A separate process/resource stop is not proof of geometric collapse.

All comparisons are actual gray polygon projections with the Task21 fixed front,
oblique and registered-detail bounds. Overlays show motifs, literal locks,
high-angle adjacency, source cells and diagnostic warnings. Painter ordering and
first-triangle shading are limited headless evidence, not a Rhino host check.
All gate and Hero vertices remain within the fixed whole-gate bounds.
Per-case camera fitting, terminal smoothing, generated imagery and beautifying
renders are absent. The lower supports and any fold artifacts remain visible.

Actual final comparisons: [front](../studies/task22/evidence/FINAL_front.png),
[oblique](../studies/task22/evidence/FINAL_oblique.png),
[registered detail](../studies/task22/evidence/FINAL_detail.png) and
[matched control mechanisms](../studies/task22/evidence/FINAL_control_mechanisms.png).
Additional tracked images show literal locks, source-cell ancestry and retained warnings.

## Simple-control findings

Forty-three primary configurations were executed as 72 cube/column cases, plus
four six-generation literal lock comparisons. Eight graph-distance and eight
normal-variation cases are secondary comparisons. All explicit recipes are in
[the recipe catalogue](../studies/task22/recipes.json); compact per-stage evidence
is in [summaries](../studies/task22/summaries).

Weak motif terms with ordinary corner averaging round off over generations.
C26_column, with w1=-0.7, w2=-2.8, w6=0.25, w7=0.65 and u3=1/u4=-0.2, reaches
119.60 degrees at G5 without sampled contacts. Its matched old-interpolation
control C30 reaches 54.0 degrees; face-only C31 reaches 50.2; edge-only C32 reaches
119.6 with localized warnings. Thus edge repositioning in this interpolation
neighborhood contributes a real crease, while the face term alone does not.
The angular box/column is a capability result, not hierarchical ornament.

C35's quadratic attenuation retains a crease but does not establish a consistent
visual advantage over fixed C26. L6 literal locking produces a visible fixed-tip
spike; it does not retain an entire source edge. Distance/proxy cases modify
local form but do not establish a stronger ornament grammar and are not preferred
gate components.

C24 retains actual contact-cap failures. C43_cube is the analytic collapse
control: w1=3, w2=5, wf=-0.5 times mean edge length sends all 26 generated points
to the origin at G1. Its 24 faces have zero area despite closed/manifold graph
topology. The failure is retained without repair. C38's separate transient
available-memory stop is logged and distinguished from that geometry failure.

## Basic gate atlas

Fifty-five causally distinct declarations were attempted: G1=25, G2=8, G3=6,
G4=8, G5=8. Forty-six completed their requested schedules, with 46 different
ordered terminal geometry hashes. Numerical differences often remain visually
subtle. Two Roof/frame selectors had no eligible faces and stopped explicitly;
seven pure/locked cases reached the geometric stopping criteria. Last retained
meshes comprise 34 VALID_SHARP, 14 BOUNDARY_SHARP and seven UNSTABLE. Two of the
34 valid meshes belong to the empty-selector stops, so completed valid meshes
number 32. All completed results retain closed one-component manifold topology.

G1_17 has 1.696% high-angle edges, a 129.08-degree maximum and no sampled contacts
or fan/bilinear warnings. Its matched old-only G1_25 has 1.674% and the same
maximum: much of the gate's angle change comes from existing interpolation.
Motif attraction's clearer independent contribution is established on the
matched simple controls, not claimed as a new major gate layer.

G1_24 confines literal locking to initial valence6/8 corners. Broad valence3
locking in G2_03/04/05/06/08 reaches the 30-contact cap; no hidden descendant-edge
policy substitutes for those failures. Two-generation G2_01/02 lose much of the
first-generation angle contrast. The gate lock study therefore does not establish
a persistent coherent large crease network.

G3_05 adds Roof on inherited extrusion-side ancestry and completes at 28,624 faces
without sampled contacts or fan/bilinear warnings. G4_06 preserves the old nested
fragment at 74,352 faces with ornament depth 4 and no sampled contacts/warnings.
G5_06 reaches 90,316 faces/depth 5 but retains 14 opposed-fan and 32 bilinear warnings
with zero terminal sampled contacts. All stage-level warnings remain available;
terminal zero does not establish that earlier intersections were resolved.

The frozen C07 reference has 110 cross-cell sharp components, including 18
crossing coarse C0 face ancestry. The original ordered Hero has 329 cross-cell
components, 1,994 confined components and three crossing C0 ancestry. G5_06 has
many sharp connected components, but its visible panel arrangement persists.
Connectivity counts are not evidence of an architectural or ornamental breakout.

The new wrapper initially passed a Path object to the old Inset adapter's string
DLL contract. Three development attempts failed after retaining their last
normal checkpoint. Only the Task22 caller was corrected; all three identical
recipes then completed. Their original requests, errors and source revisions
remain in the external study. This was an integration error, not mesh collapse.

Sixteen finalists retain the matched face/edge ablations, motif-only weak control,
Eq7 control, literal lock, three pure/locked gate comparisons, Roof, nested and
ordered comparisons, one boundary case and two genuine geometric failures.
The six refinement bases are C26_column, G1_17, G1_24, G3_05, G4_06 and G5_06.
Each receives three fully serialized variants (18 total, below the 24-case cap).
The variations attenuate motif classes, apply finite quadratic attenuation,
or shift face/edge balance. Frozen macro values and old nested fragments remain.

## Final decision and visual review

The 18 refinements complete as nine VALID_SHARP, seven BOUNDARY_SHARP and two
UNSTABLE. R1_2 stops at G5 despite attenuating weights; R1_3 stops at G3 after a
small face/edge-balance change. Stable gate variants remain visually similar.
No refinement establishes a new major formal layer or a useful macro-to-micro
progression. The original, simpler G1_24 is retained as the single limited Hero.

HERO_SHARP_GATE completes at 17,922 vertices / 35,840 edges / 17,920 faces. Its
ordered geometry SHA is
`4a9e988e7a64abb5cec8cc4901db55b75dd8b504ae6f0265f14368d4b1356b2a`.
Two independent workers exactly match every reached geometry, immediate/cumulative
lineage and branch-signature checkpoint. The Hero also exactly matches the reviewed
G1_24. This is a reproducible crease/locking capability specimen, not a design
success designation. Three weak Heroes are not manufactured.

| Comparative label | Actual case | Scope |
|---|---|---|
| BEST_SHARP_GATE | HERO_SHARP_GATE / G1_24 | Clean local locked junctions; panels persist |
| BEST_SHARP_ORNAMENT | G4_06 | Readable depth 4 nested ornament; repeated cells |
| BEST_GEOMETRIC_ORDER | G3_05 | Clean side Roof comparison within Task22 |
| MAX_ORNAMENT_CAPABILITY | G5_06 | Depth5 ordered derivative, 14 fan/32 bilinear warnings |
| MOST_INFORMATIVE_FAILURE | G2_03 | Broad literal locking reaches actual contact cap |

The original Task21 ordered Hero retains clearer overall ridge order than the
new ordered derivatives. The labels above are relative partial-capability
comparisons, not awards for achieving the design target. C43's zero-area collapse
is a separate analytic failure reference.

The required nine visual questions have these answers:

1. Less melted? Some lintel seams are more angular; the whole gate is still rounded.
2. Actual folds/creases/spikes? Yes on controls, and localized gate seams/tips.
3. Stronger large-panel angles? Yes relative to an extra standard-CC generation;
   the old-only matched control explains much of the increase.
4. Parent-cell tiling? It continues to dominate the ornament.
5. Cross-cell structures? Connected high-angle edges cross cells, but a coherent
   new visible cross-cell motif has not been established.
6. Clearer cap/ridge languages? Existing small ridges and nested frames remain
   legible; the new subdivision often rounds inherited detail and adds repetition.
7. Lower supports smooth? Yes, excessively smooth for the intended articulation.
8. Still a gate? Yes: support order, lintel relationships and all original anchors
   remain. Geometry is displaced relative to the original floor and dimensions.
9. Meaningful sharpness or collapse? Clean creases are separate from retained
   contact-cap and zero-area failures. Very large angles alone prove neither.

GROTESQUE_GATE_CANDIDATE is **not established**. Gate readability, reproducibility
and clean local creases pass. Visibly distinct new macro/meso/micro hierarchy,
a major formal layer from point repositioning, and escape from panel dominance
fail. Small inherited ornament is legible and no smoothing finisher is added,
but rounded supports and loss of detail remain. Catastrophic failures are excluded
from preferred outputs; this is still partial computational ornament.

The single strongest remaining technical limitation is the lack of a coherent,
persistent crease network across coarse parent cells: local motif values and
corner locks change junctions without reorganizing the inherited panel scaffold.
No 500k/750k production run is justified or attempted; face density is not used
to rescue that limitation. No new Rhino mode or host session is claimed.

## Integrity, tests and distribution

All principal cases retain original source anchors, left/right support order,
lintel-above-support relationships and closed one-component manifold topology.
The read-only monitor approximates corner-descendant landmark clouds, not free
opening clearance. Relative to C0, principal terminal drift is:

| Case | W/H/D change % | Opening W/H change % | Support base rise, source units |
|---|---|---|---|
| HERO_SHARP_GATE | +12.097 / +12.785 / +115.786 | +0.071 / -18.958 | 453.608 |
| G3_05 | +11.923 / +12.733 / +114.688 | +0.043 / -18.978 | 455.707 |
| G4_06 | +12.254 / +12.785 / +116.774 | +0.651 / -19.169 | 453.608 |
| G5_06 | +12.568 / +12.923 / +118.621 | +0.407 / -18.986 | 453.608 |

Most rise/dimensional drift is inherited from C07 (base rise 452.806). The source
height is 3,500; opening-center Z drift is roughly 0.0584–0.0597 source height and
X drift is numerical zero. No floor constraint or opening repair is invented.
Hero, G3_05 and G4_06 have zero terminal sampled contacts/fan/bilinear/degeneracy
warnings. G5_06 has zero sampled terminal contacts with 14 fan/32 bilinear warnings.
The frozen C07 4,096-face sample finds 11 contacts; earlier Task21's different
cohort found 12. These samples do not establish exact intersection resolution.

The complete suite ran **once**, using the unchanged venv and the real official
DLL: **776 passed in 38.35s**. Seventeen focused tests plus strict actual saved-stage
regressions and the independent Hero workers verify the new mechanisms. Existing
tests and runtime guards are unchanged. Native projections are headless evidence;
actual Rhino host checks were not performed.

The existing Task21 distribution policy is applied through a Task22-local entry
because its original entry pins the Task21 branch. Artifact/path/secret rules are
preserved, with own Task22 projection images permitted and Task21/Task17 tag-object
protection added. The final audit and `git diff --check` accompany publication.
Only the experimental Task22 branch is committed/pushed; no merge is performed.
Publication SHA and protected remote refs are recorded separately in
`artifacts/logs/git_delivery.json` in the review archive, avoiding a self-referential
commit hash in tracked documentation.

The review ZIP contains relevant first-party source/tests, exact recipes,
equation evidence, histograms/locks, compact tables, contact sheets, selected real
meshes, all Hero checkpoints and failure/test logs. Frozen inputs make replay
independent of an old output folder. Heavy screening geometry stays external;
DLLs, environments, upstream material, papers and local settings are excluded.

## Reproduction

Use the unchanged repository venv. Set `$artifactRoot` to the extracted review
archive's `artifacts` directory or an existing configured study root. Set
`$officialDll` separately to the user's official standalone assembly for recipes
with existing Mola finishes; it is never copied or redistributed.

```powershell
.\.venv\Scripts\python.exe examples/beyond_smoothness_evidence.py --output-root $artifactRoot --restore-recipes
.\.venv\Scripts\python.exe examples/beyond_smoothness_study.py --output-root $artifactRoot --phase REPLAY --run HERO_SHARP_GATE --dll $officialDll
.\.venv\Scripts\python.exe examples/beyond_smoothness_views.py --output-root $artifactRoot --phases REFERENCE HERO --selected HERO_SHARP_GATE --checkpoints
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/vocabulary_projection.ps1 -PlanPath "$artifactRoot/projection_plan.json"
```

Completed successful cases resume only after request/source/dependency/code and
artifact hashes match. Committing identical source bytes changes provenance but
does not invalidate a result; changing source bytes does. Interrupted attempts
are retained separately. First-party source snapshots pin earlier worker revisions
used during development; heavyweight screening geometry is excluded from Git.
