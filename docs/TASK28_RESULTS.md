# Task28 results: PARTIAL

The existing modified subdivision generates major angular form from a genuinely simple column, then secondary convergent folds, followed by curvature. It does not yet convincingly demonstrate a retained independent third scale. G3 small pleats still follow repeated child-cell placement; late relaxation removes part of them. The selected result is therefore PARTIAL, not SUCCESS. This is the conclusion of actual low-resolution experiments, not an inference from tests or polygon counts.

## Required report items 1-5: identity and input

1. Exact final local commit: authoritative post-commit `release.json` and `FINAL_REPORT.md` under `E:/CHESHIRE_DATA/task28/`. This tracked document cannot embed its own final commit hash without circularity. Baseline: `a9974d39f8e92c01c454e455399ca038fb8513cc`.
2. Branch: `experiment/task28-hansmeyer-benchmark`. Task-only local commit; no push or merge.
3. Tests: **818 passed in 42.93 s**, including the explicitly configured installed optional official Mola backend; **34 mechanism/benchmark tests passed in 2.24 s**. The three new tests check simple closed input vs genuine standard CC, exact saved-origin continuation, and actual nonstationary face-point geometry. Every actual lead child was independently reproduced from saved parent geometry/origins, with exact XYZ, oriented polygons and coarse face ancestry. All captured geometry/image hashes and candidate parent/source hashes passed. Installed RhinoCommon 8.18.25100.11001 reread the 3DM and opened it with RhinoDoc.OpenHeadless: exact double-precision XYZ and oriented faces, one object, no repair. Real GPU insertion-order/depth fixture passed. Logs: `test_logs/`, `analysis/geometry_validation.json`, `analysis/depth_order_check.json`, `dcc/lead_import_evidence.json`.
4. Input: one straight constant-ellipse 8-sided column; three rings at Z=0/650/1800, declared ellipse width900/depth500, angular offset pi/8. The two vertical bands differ only in length. Four coplanar quads per end cap use one center per cap. Frame T=+Z/U=+X/V=+Y. No prebuilt ornament, desired final silhouette, semantic gate route or manual folds. Actual sampled bounding box is 831.491579 x 461.939766 x 1800; declared ellipse diameters are not the octagon's bounding-box dimensions. Original unresolved coordinate units, no rescaling.
5. G0: **26 vertices, 48 edges, 24 quads**, connected closed manifold, Euler characteristic2.

## Items 6-8: machinery and recovered research

6. Confirmed: standard COMPAS CC topology with modified placement; Eq1 wf face-normal extrusion, Eq2 w1 interpolation/we mean edge-normal extrusion, Eq3 w2 corner interpolation/wp incident-normal extrusion; real previous V/F/E/E point classes and Eq4 w3/w4 face-point stencil; serializable origins; nonstationary finite schedules; nonuniform point-class overrides; literal unnormalized Eq10/11 motif attraction w6/w7. Existing crease/sharpness and optional official Mola compatibility are audited and covered by existing tests, but are not used in this lead. Source graph-distance/current normal-variation interpolation and corner locks are existing CHESHIRE additions, unused here. **The existing implementation uses original input centroids in Eq2/Eq3 and isolates same-generation face/edge displacement; this is a subset convention, not a verified complete Digital Grotesque implementation.** No equation was rewritten.

Primary source checked during audit: [Hansmeyer, Design by Subdivision, Bridges 2010](https://archive.bridgesmathart.org/2010/bridges2010-167.pdf). The paper supports the class of weighted interpolation, extrusion, nonstationary/nonuniform and motif mechanisms; it is not used to claim the entire published system has been reproduced. Exact local implementation details: `analysis/hansmeyer_implementation_audit.md`.

7. Fourteen recovered historical entries/control recipes are recorded with actual numbers, commits, generation, source file hash, surviving artifact, and Mola involvement in `analysis/previous_success_inventory.json/.md`. Key replays: Task20/21 C11 macro rows; Task22 C26 motif column; Task24 H1 macro/cleft; Task25 CURVE, AMP, convergence, flow/midgeneration normal-offset continuations. Task26 and Task27 are baseline controls. Old C07's first two CC rows are followed by a Mola Taper, zero CC and InsetFrame; Task25's fuller four-way curl is not attributed to subdivision alone. H1's exact numeric macro is replayed at CC3, original CC4 and CC5 after saved simple CC parents. Those are weight transplants on a new cage, not copies of the old whole gate context.
8. Material contribution: G1 adopts old H1 wf/we/wp=-280/320/520,w1=.8,w2=-2.8 with a matched removal of w6/w7. It changes all98 output points relative to same-parent standard CC (RMS379.766, maximum666.084). G2 uses **exact C11B** and changes all386 points (RMS167.617, maximum331.380), visibly producing secondary cuts within G1 lobes. G3 uses .70 of C11B's continuation plus the exact Task25 convergence Eq4 pair. The later pair is attenuated before zero-valued existing CC. C11/H1/convergence materially shape the progression rather than merely being listed as citations.

## Items 9-11: actual search and selected weights

9. **70 candidate definitions, 253 actual candidate stages.** Initial search:14 replay +32 nonstationary =46 definitions. Corrections:12 PASS3 +6 PASS4 +6 topology-motif follow-up. Duplicate early parents are intentional matched comparisons, not70 independent G1 shapes. Canonical unique geometries by generation: {'1': 8, '2': 25, '3': 61, '4': 25, '5': 13}. All70 terminal thumbnails and parameter definitions are preserved.
10. Meaningful axes: recovered early/middle/later mechanism choices; G3 continuation factors0/.35/.70/1 x three exact old Eq4 pairs; G4 Eq4 factors0/1/3/1 x two G5 continuations; final motif face factors1/2/4 x edge factors1/2 with u3=1/u4=0. Declared numeric ranges: w1[-1.05,.8],w2[-2.8,0],w3[-3,0],w4[0,1.5],w6[-.9,1],w7[0,1.3]. Normal-offset ABSOLUTE ranges wf[-280,130],we[0,320],wp[0,520]; RATIO ranges wf[0,.30],we[-.08,0],wp[0,.10]. Current motif maps, where active, come from old actual topology signatures; declared u ranges[-1.5,2.5], and the final follow-up neutralizes new valence4 points. Offsets and dimensionless coefficients are not mixed.
11. Selected actual lineage: **P4_C033_ZERO, G0-G5**. Every stage is a byte-identical copy from this one candidate; no stages were assembled from different trials. Exact full definitions, resolved world offsets, units and original parent identities: `definitions/generation_weight_schedule.json`, `lead/lineage.json`, each `lead/Gn/request.json` and `state.json.gz`.

| Child | Offset units | wf | w1 | we | w2 | wp | w3 | w4 | w6 | w7 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G1 | ABSOLUTE | -280 | 0.8 | 320 | -2.8 | 520 | 0 | 0 | 0 | 0 |
| G2 | RATIO | 0.16 | -1.05 | -0.05 | -0.9 | 0.045 | -0.8 | 0.5 | 0 | 0 |
| G3 | RATIO | 0.112 | -0.735 | -0.035 | -0.63 | 0.0315 | -0.6 | 0.35 | 0 | 0 |
| G4 | ABSOLUTE | 0 | 0 | 0 | 0 | 0 | -0.2 | 0.116666666667 | 0 | 0 |
| G5 | RATIO | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

RATIO multiplies only wf/we/wp by the actual CURRENT GLOBAL mean edge length. ABSOLUTE uses the old coordinate units. G4 pair is exactly the binary-floating-point result of dividing the recovered Task25 pair by3. G5 all-zero placement matches mathematical standard CC within floating-point roundoff (RMS5.01e-14, maximum4.55e-13); it is a selected late call through the **same recursive backend**, not an external smooth modifier. G0-G3 were not automatically smoothed away.

| Child | Recorded offset scale | Resolved wf | Resolved we | Resolved wp |
|---|---:|---:|---:|---:|
| G1 | 1 | -280 | 320 | 520 |
| G2 | 534.75233168 | 85.5603730688 | -26.737616584 | 24.0638549256 |
| G3 | 278.203884359 | 31.1588350482 | -9.73713595257 | 8.76342235731 |
| G4 | 1 | 0 | 0 | 0 |
| G5 | 51.0228739697 | 0 | 0 | 0 |

## Items 12-18: progression and visual judgment

12. Actual counts and dihedral diagnostics:

| Stage | Vertices | Quads | Median / p90 adjacent-normal angle (degrees) |
|---|---:|---:|---:|
| G0 | 26 | 24 | - |
| G1 | 98 | 96 | 85.731 / 126.198 |
| G2 | 386 | 384 | 38.120 / 109.933 |
| G3 | 1,538 | 1,536 | 33.280 / 101.358 |
| G4 | 6,146 | 6,144 | 12.740 / 41.088 |
| G5 | 24,578 | 24,576 | 5.823 / 18.942 |

Angles measure geometric normal variation, not an automatic beauty or hierarchy score. The nonzero maximum near180degrees reflects locally folded/signed placement, not an asserted collision-free solid.

13. Every generation has `renders/lead/LEAD_Gn_front.png`, `_oblique.png`, `_wire.png`, n=0..5, with shared 4000-unit width, target[0,0,900], fixed camera pose, clay and lighting. Required sheet: `renders/lead_progression.png` (each generation side-by-side), plus `_front.png`. `renders/lead_detail.png` uses one fixed1500-unit crop throughout and does not hide cropping. Candidate gallery: `renders/candidate_contact_sheet.png`; readable pages and individual thumbnails: `candidates/thumbnails/`. Root details: `renders/task27_vs_task28.png`. All primary captures use original XYZ and **flat normals**; quads are split on diagonal0-2 for the GPU only. OBJ/checkpoints/3DM retain the original quads. Camera manifests record float32 display error, physical width, material, light and any clipped vertices. Historical CC4/5 diagnostic thumbnails use explicitly marked4800 width; all other searches use4000. There is no per-candidate fitting.
14. First major angular fold: **G1**, large vertical valleys and protruding lobes absent from G0.
15. Secondary articulation: **G2**, convergent shoulder/cap cuts within earlier lobes. G3 produces smaller pleats inside these regions, but their dependence on the repeated child cells remains visible. Genuine coarse-face ancestry is verified at each stage: every coarse quad has4^g descendant quads. This ancestry proves origin, not visual hierarchy by itself.
16. Curvature begins in parts during **G3** but becomes clear after formation in **G4** and stronger in **G5** (median angle33.280 ->12.740 ->5.823 degrees). Macro valley/shoulder structure remains while some G3 small pleats fade.
17. The selected final silhouette/read is dominated by large lobes/valleys rather than a decorative quad lattice. Nevertheless, **absence of a dominant final grid is insufficient for SUCCESS**: the third articulation scale is not convincingly independent and retained. The stronger late Eq4 alternatives leave repeated fine kinks; the smoother alternative loses some small structure.
18. Task27 accepted R4 G5 (165,888faces) reads as a shaped smooth gate with repeated local cell detail. Task28 creates large folds first from24quads, then secondary folds, then rounds them with24,576quads. This is a stronger macro-generation demonstration; it still does not establish the full required hierarchy. Comparison uses unchanged old accepted Task27 geometry and same clay/light/physical width per row, with camera translation to the respective model/column/fold. Inputs differ (gate vs simple column), so this is a visual mechanism baseline, not a controlled equal-cage contest.

## Items 19-23: limits, resources and classification

19. Mola operations outside modified subdivision in Task28 specimen/lead: **none**. No Taper/Frame/Extrude, noise, ALICE, manual fold, geometry repair, gate routing or generic ornament system.
20. No additional operation was required or used. Old Mola involvement is identified in the recovered inventory; optional Mola DLL usage in full regression tests is validation of existing compatibility and does not enter any Task28 candidate geometry.
21. Measured45 guarded geometry/render jobs: **431.484 seconds summed job wall time**, peak sampled tree+driver **629.58 MiB**, no resource stops. This excludes interactive audit/review/writing, test time, independent final replay audit and cold native-host startup, and is not the whole sprint elapsed time. Native read/write/open:0.859s, native host peak419.85MiB (separate scope). Maximum candidate mesh24,576faces; no >200k resolution rescue. Full tests42.93s. Detailed per-job evidence:`analysis/performance.json` and `logs/*/process.json`.
22. Current observed bottleneck: signed displacement readily generates macro/secondary geometry, but later class interpolation trades repeated small-cell kinks against loss of those details. Almost all newly generated vertices become valence4, leaving little intrinsic motif diversity; eight original valence3 neighborhoods do not solve the full hierarchy problem in the tested attraction ranges. Current same-generation offset isolation is an audited implementation limit worth distinguishing from complete published implementations, **not a demonstrated math bug**. RAM and polygon count were not the limiting factors. No claim is made that all possible parameter space is exhausted.
23. **PARTIAL**, under the prompt's original threshold. Simple input, new angular macro form, secondary structure, later curvature and historical reuse are demonstrated. A convincing macro->meso->independent smaller retained formation without dominant cell repetition is still unproved.

## Visual seven-question test

| Question | Answer from the saved progression |
|---|---|
| Simple G0? | Yes: straight unornamented column. |
| Major new G1/G2 geometry? | Yes: new lobes, deep valleys and shoulder/cap convergence. |
| Early angular/faceted? | Yes: G1-G3 preserved before late relaxation. |
| Later acts on existing folds? | Yes for macro/secondary; part of the small structure is lost. |
| New structures within earlier structures? | Yes at G2; G3 smaller pleats are cell-linked, not convincing independent hierarchy. |
| Curvature after formation? | Yes, particularly G4/G5 using same backend. |
| More than a repeated quad-grid? | Macro/secondary yes; full independent third scale remains unproved. |

The negative/incomplete answers are deliberately visible. They are not relabeled as SUCCESS after the experiment.
