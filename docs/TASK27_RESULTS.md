# CHESHIRE / Modern Cliché Task27 results

**PARTIAL.** The actual connected profile gate, four controlled paths, current-geometry feedback, geometric symmetry, exports and tests succeed. The saved sequence develops secondary facets and smaller ridges, but its fine organization remains dominated by repeated CC cells. The required strong hierarchy across large curvature, secondary curvature and smaller ridges is not yet established. More polygons alone would not resolve this finding.

## Preserved starting state and scope

Before code changes, the repository was clean at `53bea0fda2779cb63a6ef31f5b7eb9c5eeff7392`; Task26 preservation `846112578d269b765f1b0b0f395d0cae4dfeadf0` and Task25 reference `b4000cf85bc0768821976bab4b454ca35b8ccca3` existed in its ancestry. `docs/TASK26_STOP_HANDOFF.md` was read, no Task26 worker was running, and `experiment/task27-dynamic-sections` was created. The latest pasted dynamic-section prompt was read through END and copied to `brief/CHESHIRE_TASK27_DYNAMIC_SECTIONS.txt`. All three inherited reference images were inspected. Their geometry is not treated as source CAD. Task26 recipes were not resumed.

The main artifacts are in `E:/CHESHIRE_DATA/task27/`. The final local SHA and clean-tree evidence are recorded after commit in `release.json` and the external FINAL_REPORT. No push, merge or Task28 is part of this execution.

## Exact coarse definitions and connected joint

| Zone | Z | CONTROL W×D | PROFILE W×D | Shape |
| --- | --- | --- | --- | --- |
| base | 0 | 900×500 | 900×500 | ELLIPSE8 |
| lower body | 420 | 900×500 | 1050×580 | ELLIPSE8 |
| body | 1050 | 900×500 | 900×500 | ELLIPSE8 |
| constriction | 1600 | 900×500 | 560×380 | ELLIPSE8 |
| expansion | 2020 | 900×500 | 1040×600 | ELLIPSE8 |
| neck | 2450 | 900×500 | 340×260 | ELLIPSE8 |
| shoulder | 2780 | 900×640 | 1200×640 | RECT8 |
| port | 2900 | 900×640 | 1200×640 | RECT8 |

Every station also stores longitudinal Z/2900 and the column frame T=(0,0,1), U=(1,0,0), V=(0,1,0). Ellipse samples are (W/2 cos(jπ/4), D/2 sin(jπ/4)), j=0..7. RECT8 divides cos/sin by max(|cos|,|sin|). Both support centers are X=-1750.036865234375 and 949.963134765625, Y=-18.533447265625. Original units remain unresolved; Z is up. The horizontal lintel is length 4000, bottom Z=2900, top Z=3500, depth 640; its frame is T=(1,0,0), U=(0,0,1), V=(0,-1,0). Both inputs have nominal 4000×640×3500 bounds. Width 900 at the body leaves 1800 between supports; this is a deliberately new cage, not Task26's 2200 opening.

The profile's neck/body width ratio is 340/900=0.377778; shoulder/neck is 1200/340=3.529412. These large body/neck/shoulder relationships are explicitly authored input, not claimed emergent folds. All dimensions and frames are in `definitions/G0_CONTROL.json`, `G0_PROFILE.json`, `joint_construction.json` and the matching repository study files.

Each support has eight eight-point rings, seven side bands and a triangular foot cap. The beam has a rectangular grid at its ends and both column-port extents/centers. Its bottom cells over each port are removed. All eight perimeter vertices of each column's last ring are shared with the lintel; the two unused port-center bottom vertices are pruned. There are no disconnected overlapping solids or bent cylindrical sweep. Both inputs are one connected, closed, oriented manifold: **160 vertices, 324 edges, 166 faces (150 quads + 16 triangles), Euler 2**. Their actual IDs, oriented face connectivity and semantic parts match. The neck rises into a widening rectangular shoulder and a separate horizontal lintel frame. The side silhouette separates the member directions, although CC still smooths the port corner.

## Existing mathematics and smallest extension

The existing `weighted_subdivision.py`, `generational_subdivision.py`, `creases.py`, `fold_continuation.py`, `progressive_gates.py`, lineage, region/route and Mola compatibility paths were inspected. Existing weighted corner/edge placement, face normal extrusion, Equation (4), positive semantic ancestry and prior-point origin checks are reused. No existing operator is rewritten. The new module only constructs the coarse ports, measures current geometry and supplies local numeric overrides.

CONTROL_CC starts from G0_CONTROL and PROFILE_CC from G0_PROFILE. Both call the existing crease-inactive standard COMPAS CC with empty networks and no additional displacement; the focused test compares the exact vertices/faces to `crease_subdivide_once`. They are not the old modified-CC recipe with nominal offsets set to zero. PROFILE_STATIC maps G0 once and copies the exact numeric face values to actual descendants. Its operators still act on the current mesh, but saved later observations are never consumed by its mapping. PROFILE_DYNAMIC rereads the immediately preceding saved full geometry/state, reconstructs descriptors and maps again. Whole-mesh CC topology is uniform; spatial variation changes point placement, not adaptive topology.

Creases are measured and remain zero, with no active network. No Task26 route deformation field or original-ring refit is used. No Mola operation is required for this mapping; the applicable full suite includes the installed official HDMola compatibility tests.

## Exact descriptors and mapping

Persistent original station-corner IDs remain actual vertices through CC. Their **current XYZ means** place the current measurement planes. Width/depth are extents of intersections with the **actual current part side mesh**, using centroid-fan triangles for nonplanar-quad measurement only. Saved quads remain unchanged. Columns use Z planes, width X and depth Y; lintel uses X planes, width Z and depth Y. Current section width/depth and width derivative are linearly interpolated at each actual face centroid. No authored coordinate or section radius is reapplied.

Each face stores semantic part, actual coarse face ancestry, current centroid/unit normal, width/depth, C/E/S, current T, current longitudinal coordinate, joint distance, h, actual sharpness, neighbor normal contrast K and generation. Longitudinal is (face-axis coordinate − first current station coordinate)/(last − first). T is the normalized difference of adjacent current section-center positions. Joint distance is |face Z − last current column station Z|; on the lintel it is |face X − middle current lintel station X|. Sharpness is max current incident-edge crease. Generation and coarse labels are recorded but are not strength multipliers.

Let W be current local section width, Wb the current body station width, Wn the current neck station width. On the lintel both references are current median thickness. The exact formulas are:

```text
C = clip(1-W/Wb, 0, 1)
E = clip((W/Wn-1)/3, 0, 1)
S = clip(interpolated gradient(current widths, current station positions), -2, 2)
K = mean_neighbors clip((1-dot(current unit face normals))/2, 0, 1)
h = sqrt(sum unsigned current centroid-fan triangle areas)
O = max(0, 1-abs(dot(current normal,T)))
A = .5 + .5*abs(current normal Y)
B = .65 on LINTEL, 1 on column side faces
k = .35 + .4*C + .25*E + .2*min(abs(S),1)
D = 1 - .65*min(K/.35,1)
wf = .08*h*k*O*A*B
w1 = -(.12+.25*C)       we = -.35*wf
w2 = -(.12+.30*C)       wp = .08*wf
w3 = -3*(.45+1.25*C+.35*E)*O*D
w4 = (.35+.30*E)*O
```

All seven coefficients on BASE faces are zero. Face wf/w3/w4 apply directly; edge w1/we are means of the two current incident face rules; corner w2/wp are means of current incident face rules. Theoretical non-base ranges are O∈[0,1], A∈[.5,1], k∈[.35,1.4], D∈[.35,1], wf∈[0,.112h], w1∈[-.37,-.12], w2∈[-.42,-.12], w3∈[-6.15,0], w4∈[0,.65]. Signed we/wp follow their exact linear relations above; base zeros extend the reported w1/w2 ranges to zero.

Existing Eq(4), only for verified preceding CC child point classes, is:

```text
P = ((V*(1+w3)+F*(1-w3))*(1+w4)+(E1+E2)*(1-w4))/4 + wf*n
```

V/F/E1/E2 are actual previous corner/face/edge/edge origins, not inferred from coincident IDs or arbitrary quad geometry. G0 has no previous origins, so G1 uses the existing face-centroid fallback plus wf. Negative w3 can extrapolate the point classes and produce secondary curvature. Existing corner/edge modified-CC weighting and normal extrusion use the stated w1/we and w2/wp. Depth, generation, joint distance and sharpness are recorded diagnostics; they do not receive independent new scalar controls.

`definitions/mapping_definition.json` contains every formula. `configuration.json` records R1 (face_gain=1), R2 (3), R3 (3 plus curvature_gain=.65) and R4 (same numbers as R3, invariant area correction). All offset_ratio=.08, edge_gain=1. There is no per-generation amplitude schedule.

## Actual experiments, corrections and accepted lineage

R1 G3 showed macro profile separation but weak small dimples. R2 changed only face_gain from 1 to 3; the actual G3/G4 comparisons produced stronger secondary facets and smaller ridges, with STATIC repeatedly extrapolating sharp places. R3 added actual neighbor-normal damping. Its later numeric audit found a concrete measurement defect: mirrored folded quads measured COMPAS areas 787.1489577322814 versus 2833.5318606605206, giving different normal offsets and a G5 symmetry residual 2.6579732545. The original operator topology and normals were paired; COMPAS area_polygon signs centroid-fan triangles relative to the first triangle, which makes its folded-quad result depend on the polygon start.

R4 sums unsigned centroid-fan triangle areas, giving 2833.5318606605265 versus 2833.5318606605206 for that pair, with the same numeric config. This fixes the measurement, without averaging coordinates or forcing a mirrored half. R1/R2/R3 geometry, recipes, captures, logs, executed source snapshots and R3 native export remain preserved. R3's execution SUCCESS / old evidence PASS did not certify geometric symmetry; `analysis/symmetry_failure_R3.json` explicitly identifies the rejected result. R4 final evidence enforces 1e-8 coordinate tolerance, mirrored rule values and semantic/ancestry/generation correspondence.

The accepted progression is exactly **G0_PROFILE → R4_PROFILE_DYNAMIC_G1 → G2 → G3 → G4 → G5**. Every worker's request hashes its actual parent geometry/state and executed sources. G4 is the common four-path comparison; the G5 primary lead is an additional true child, not relabeled as a matched G4 control. All intermediate meshes remain stored.

## Per-generation actual parameter data

Values describe the rules consumed to produce output G; current section measurements come from input G−1. Medians include zero base-face rules. Median we=-.35 median wf and median wp=.08 median wf.

| Output G | Measured input body W | Measured input neck W×D | median wf | median w1 | median w2 | median w3 | median w4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 900.000000 | 340.000000×260.000000 | 8.104935 | -0.120000 | -0.120000 | -0.976592 | 0.350000 |
| 2 | 816.750023 | 500.401320×328.629998 | 3.743717 | -0.122146 | -0.122575 | -1.215204 | 0.314014 |
| 3 | 795.450576 | 536.987985×343.320736 | 1.607522 | -0.120506 | -0.120608 | -0.967535 | 0.293400 |
| 4 | 788.512585 | 548.115585×348.912000 | 0.667832 | -0.120000 | -0.120000 | -0.891896 | 0.298450 |
| 5 | 784.910628 | 559.773037×361.270559 | 0.301944 | -0.120025 | -0.120030 | -0.789428 | 0.293563 |

| Output G | wf range | w1 range | w2 range | w3 range | w4 range |
| --- | --- | --- | --- | --- | --- |
| 1 | [0.000000, 18.807490] | [-0.178333, 0.000000] | [-0.190000, 0.000000] | [-1.953895, 0.000000] | [0.000000, 0.602941] |
| 2 | [0.000000, 9.415957] | [-0.192099, 0.000000] | [-0.206519, 0.000000] | [-1.983069, 0.000000] | [0.000000, 0.484464] |
| 3 | [0.000000, 7.685622] | [-0.187931, 0.000000] | [-0.201517, 0.000000] | [-2.023729, 0.000000] | [0.000000, 0.458519] |
| 4 | [0.000000, 6.386070] | [-0.187005, 0.000000] | [-0.200406, 0.000000] | [-2.172207, 0.000000] | [0.000000, 0.470170] |
| 5 | [0.000000, 5.532013] | [-0.184958, 0.000000] | [-0.197950, 0.000000] | [-2.102715, 0.000000] | [0.000000, 0.462829] |

Complete face-level inputs and all seven mapped outputs are `stages/R4_PROFILE_DYNAMIC_GN/descriptors.json.gz` and `rules.json.gz`. The operator audit is `operator.json.gz`; resulting section observations are `observations.json.gz`. STATIC's frozen values are in its saved continuation state, with per-generation `rules.json.gz`.

## Geometry feedback and controlled comparisons

The actual input body changes 900 → 816.750023 → 795.450576 → 788.512585 → 784.910628; neck width changes 340 → 500.401320 → 536.987985 → 548.115585 → 559.773037. Every dynamic input section table is exactly equal to the saved preceding mesh observation after actual file reread, and every parent hash matches. The next-generation controls change beyond h-based shrinking offsets:

| Output G | Changed w3 faces vs inherited preceding rule | Max |Δw3| | Median |Δw3| | Sections exactly match saved preceding observation |
| --- | --- | --- | --- | --- |
| 2 | 600 | 0.992365545 | 0.225001875 | True |
| 3 | 2400 | 1.438648921 | 0.144631013 | True |
| 4 | 9600 | 1.480313564 | 0.186124060 | True |
| 5 | 38400 | 1.600587008 | 0.138301138 | True |

This compares each current face rule to its actual inherited preceding input rule using operator parent faces, not numeric ID coincidence. w1/w2/w4 also change; all exact deltas are in `analysis/R4_G5_evidence.json`. STATIC/DYNAMIC G1 XYZ and topology are exactly equal, isolating the subsequent feedback effect.

| Actual identical-topology pair | RMS displacement | Maximum displacement |
| --- | --- | --- |
| R1_CONTROL_CC_G4 / R1_PROFILE_CC_G4 | 58.810526584 | 140.518625323 |
| R4_PROFILE_STATIC_G1 / R4_PROFILE_DYNAMIC_G1 | 0.000000000 | 0.000000000 |
| R4_PROFILE_STATIC_G2 / R4_PROFILE_DYNAMIC_G2 | 19.785675826 | 164.171411841 |
| R4_PROFILE_STATIC_G3 / R4_PROFILE_DYNAMIC_G3 | 30.534047852 | 225.835327372 |
| R4_PROFILE_STATIC_G4 / R4_PROFILE_DYNAMIC_G4 | 38.838851795 | 279.704374619 |
| R1_PROFILE_CC_G4 / R4_PROFILE_DYNAMIC_G4 | 65.904818345 | 365.761603729 |

Displacements use identical saved point IDs and oriented cycles. They prove material geometric difference, not hierarchical quality by themselves. The main controlled images are `renders/R4_G4_comparison/*_four_path_comparison.png`; the chronological views are `renders/progression_R4/*_sheet.png`. Both use the same original physical scale, target, orthographic camera, clay material and lighting within each view. All camera poses, physical widths, original geometry hashes, derivatives, GPU backend and PNG hashes are saved in their manifests. Progression never combines different revisions.

## Geometry counts, RAM and timing

Both G0 inputs have 160 vertices / 166 faces. Every four-path G1 has 650/648, G2 2594/2592, G3 10370/10368 and G4 41474/41472. The dynamic G5 lead is 165890/165888, with 331776 edges, zero boundary edges, valid closed manifold topology and actual bounds 3996.351909×713.581803×3506.841665. The extra depth/envelope change is retained.

| Output G | Vertices | Faces | Guarded process seconds | Sampled process-tree+driver peak MiB | OBJ bytes |
| --- | --- | --- | --- | --- | --- |
| 1 | 650 | 648 | 1.638 | 175.48 | 58207 |
| 2 | 2594 | 2592 | 2.686 | 188.23 | 239788 |
| 3 | 10370 | 10368 | 5.874 | 231.82 | 973082 |
| 4 | 41474 | 41472 | 21.240 | 404.24 | 4273267 |
| 5 | 165890 | 165888 | 87.324 | 1090.06 | 16991444 |

The guard samples the worker process tree plus its own driver; values are sampled peaks, not exact allocation totals. The preflight is 200 MiB fixed overhead +10,000 bytes/output face, checked against available RAM; the live measured RAM guard and system headroom are retained. No elapsed-time, contact or historical polygon cap constrained design. The final checkpoint/next-rule evidence process took 53.192 s with sampled 1438.168 MiB; native job took 7.838 s including cold startup. No actual RAM hard stop occurred. G6 was not generated because G5 already establishes the remaining cell-periodicity problem, not because a historical face threshold was reached.

## Symmetry and export reread

Reflection uses declared G0 station/grid pairing and actual CC corner/edge/face genealogy thereafter. Correspondences include semantic parts, paired full-gate selection, coarse ancestry, local rules and generation. Front/rear is reconstructed independently and reported separately from LR. No nearest-coordinate pairing or post-hoc coordinate averaging is used.

| Output G | LR max coordinate residual | FR max coordinate residual | LR oriented-face failures | Max mirrored mapped-parameter residual |
| --- | --- | --- | --- | --- |
| 1 | 9.11269327269e-13 | 4.56741380503e-13 | 0 | 1.99840144433e-14 |
| 2 | 1.53477230924e-12 | 1.01724311709e-12 | 0 | 4.17443857259e-14 |
| 3 | 1.81987736523e-12 | 2.28012267145e-12 | 0 | 6.97220059465e-14 |
| 4 | 5.05906427861e-12 | 4.42804395309e-12 | 0 | 1.7852386236e-13 |
| 5 | 7.8514715091e-12 | 5.953805443e-12 | 0 | 7.3985262361e-13 |

At G5 there are 165890 vertex and 165888 face correspondences, zero LR/FR oriented-cycle failures. The 1e-8 tolerance is passed. The earlier `plane_Y_not_enforced` key comes from the reused LR-only helper; the separate FR report supplies the independent numeric verification.

Lead OBJ: `stages/R4_PROFILE_DYNAMIC_G5/R4_PROFILE_DYNAMIC_G5.obj`, **16991444 bytes**, SHA256 `626222df8fdbc4d1b7453f9c31d2ee99c46b55a590dec5ee3e9f88456bd0ab37`. Full actual reread verifies all vertices, original polygon faces and orientation. The saved full geometry/state are independently reloaded, all face ancestry and point-origin coverage checked, sections remeasured exactly, and the next rule mapping reconstructed from the actual G5 geometry. Focused save/reload tests verify exact subsequent geometry/state/rule equality on a smaller checkpoint; no G6 full mesh is claimed.

Lead native: `dcc/R4_PROFILE_DYNAMIC_G5.3dm`, **7199201 bytes**, SHA256 `0d0dcbddc5e1d6d26132a21440790fae36d668e4e095925443f156fa944d385b`. Installed RhinoCommon 8.18.25100.11001 writes and rereads the full original mesh; exact double XYZ and oriented faces match, and headless document opening finds one object on `TASK27_R4_PROFILE_DYNAMIC_G5`. Physical units remain None. `dcc/R4_PROFILE_DYNAMIC_G5_import_evidence.json` records this. Native measured read/write/open time is 2.648871 s, excluding startup, with 441.84 MiB host peak. This is actual native-file/document verification, not an interactive Rhino viewport claim.

Whole, oblique, underside, body, neck/shoulder, mantle and wire images are in `renders/lead_R4/`. Neutral OpenGL capture uses declared triangle/display derivatives; original quads and units in OBJ/state/3DM remain unchanged. The existing orthographic depth correction is reused and its occlusion check saved. Actual reread native plane intersections at X=-1750.036865234375, Y=-18.533447265625 and Z=2450 are in `analysis/sections/R4_PROFILE_DYNAMIC_G5.json` and `renders/geometry/section_comparison.png`. A section can miss a localized ridge; contour smoothness is not used as a surface-hierarchy score.

## Visual success questions and current bottleneck

1. **G0 hierarchy: established.** Exact 900 body / 560 constriction / 1040 expansion / 340 neck / 1200 shoulder widths and the G0 views establish it.
2. **Joint direction: substantially improved.** The shared rectangular ports and separate horizontal beam frame replace the swept bent-pipe construction. Matched CC comparison shows the narrowing neck and spreading shoulder; the smoothed continuous blend is still visible.
3. **Authored forms: explicit.** The two body bulges, two constrictions, neck, shoulder, overall lintel and opening are in G0; they are not emergent ornament.
4. **Generated forms: real.** G2 introduces point-class facets; G3 adds intermediate repeated curvature; G4/G5 introduce smaller ridges/valleys on those facets, absent from G0 and standard PROFILE_CC. Mesh/wire and stage images preserve their actual geometry.
5. **STATIC vs DYNAMIC: materially different.** G1 identical, G4 RMS 38.838852 and maximum 279.704375 on matched topology; dynamic feedback restrains and redistributes the static repeated extrapolation.
6. **Cross-scale hierarchy: weak.** Some secondary facets persist while smaller ridges appear, but star/cell repetition dominates the same-scale forms. The large profile is still mostly authored; strong DG-like hierarchy is not demonstrated. More count and normal variation alone are insufficient evidence.
7. **Actual feedback: established.** Saved parent hashes, exact section equality, changed C/E/T/K and the non-h coefficient change table substantiate it.
8. **Symmetry: established for R4.** Full numeric and oriented-topology checks pass; rejected R3 is retained explicitly.
9. **Bottleneck: local rule mapping, with CC point-class periodicity as a related mathematical limitation.** Coarse organization and connected joint are adequate for this test. Folded-face measurement defect is corrected. G5 resolution and RAM are sufficient to see the repeating behavior; hardware is not the present limiting factor.

The assessment remains **PARTIAL**, even though implementation, feedback and file validation pass. No manually inserted ornament or AI-generated surface image is used to improve that assessment.

## Tests and handoff files

Focused final run: **11 passed in 8.09 s**. Applicable full final run: **815 passed in 41.46 s**, including official installed HDMola.dll with PYTHONNET_RUNTIME=coreclr. Regression tests cover exact standard CC, actual shared ports, static freezing versus feedback, real altered-neck measurement, exact save/reload continuation, folded-face area cycle/reflection invariance, and actual G3 plus next mapped rules symmetry. Source syntax compilation also passes. Logs are in `test_logs/`; the earlier 813-test pre-area-fix run remains distinguishable from final evidence.

See `docs/TASK27_HANDOFF.md` / external `TASK27_HANDOFF.md` for exact checkpoint paths and safe continuation. `CHESHIRE_TASK27_REVIEW.zip` is a focused upload packet with selected real captures, definitions, rules/descriptors, trial summaries, reports, tests and executed sources. `CHESHIRE_TASK27_MODEL.zip` is useful because it contains the actual full lead OBJ/3DM/geometry/state/operator/observations plus G0, definitions and sources. Large prior intermediates and capture derivatives remain external. `stage_manifest.json` indexes all actual stages and capture hashes; `deliverables.json` records actual ZIP reread CRC and every payload SHA256. Final local SHA is in external `release.json`.
