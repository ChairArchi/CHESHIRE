# CHESHIRE / Modern Cliché Task26 preservation results

Task25 baseline: `b4000cf85bc0768821976bab4b454ca35b8ccca3`.
Branch: `experiment/task26-progressive-gates`.
Large artifacts: `E:/CHESHIRE_DATA/task26/`.

The user requested a change of direction in Task27 while Task26's final
reporting and packaging were outstanding. New geometry experiments stopped.
This document preserves the experiments already performed; the stop is not
evidence of algorithm failure. Task27 has not started. Its safe-start rule
must be checked against `TASK26_STOP_HANDOFF.md` and actual Git history.

Execution, geometry exports and neutral depth-correct captures succeeded.
The design assessment is **PARTIAL**: the large member forms and junctions
are readable, but the new fine surface remains granular and cell-periodic.
Digital Grotesque's broad-to-middle-to-small fold hierarchy is not established.
No thickness, fabrication suitability or structural load transfer is certified.

## Inputs and matched comparisons

The fresh rectangular and rounded whole gates have identical vertex IDs,
oriented face connectivity, part labels, stations and nominal scale: 74
vertices, 80 faces, nine shared eight-point rings and triangular foot caps.
The joint really shares ring vertices and edges. It is a continuous swept U
carrier, not separate cylinders and boxes. Its rotated shoulder section can
still read as a bent tube; connectivity alone does not resolve that issue.

Original Z-up frame: X symmetry plane `-400.036865234375`, reference Y plane
`-18.533447265625`; physical units remain unresolved. Nominal width/height/depth
are 4000/3500/500, support width/depth 900/500, opening 2200/2600. The section
parameters 450 and 250 are half-width and half-depth, not diameters.

The initial comparisons were RECT_EARLY, RECT_DELAYED and ROUND_EARLY. Each
used one fold that itself includes one CC subdivision, plus two ordinary CC
steps: total generation 3, 4,864 faces. Equal fold parameters and material-space
support were used. Early folding followed by smoothing retains broad softened
forms; delaying the same absolute offsets until smaller cells exist produces
more serration. Rounded sections soften the base envelope but do not create
a convincing member hierarchy by themselves.

ROUND_PROFILE and a separate three-station column probe explicitly put scale
0.72 at Z=1300 and 1.12 at Z=2600 in the input. Those waists and bulges are
designed input profiles, not folds discovered by subdivision. This was an
auxiliary Task26 experiment, not the required main profile-first route of
Task27, and must not be presented as completing Task27.

Macro revisions included ROUND_BODY, RECT_BODY and ROUND_GROOVE. BODY produced
stronger noise; GROOVE preserved a more useful large envelope and was advanced.
At the common ROUND_GROOVE_SMOOTH_G3 ancestor, separate actual comparisons
tested standard CC with all creases disabled, inherited crease CC, transferred
Task25 coefficients, and distributed versus concentrated physical support.
The Task25 transfer replaces H1's original routes, band and sharpness with new
Task26 routes/support: it is not an exact H1 replay.

## Continuation and selection

The selected saved ancestor chain is:

| Saved stage | Absolute CC generation | Faces |
| --- | ---: | ---: |
| INPUT_ROUND | 0 | 80 |
| ROUND_EARLY_G1 | 1 | 304 |
| ROUND_GROOVE_G2 | 2 | 1,216 |
| ROUND_GROOVE_SMOOTH_G3 | 3 | 4,864 |
| FOLD_DISTRIBUTED_G4 | 4 | 19,456 |
| FOLD_DISTRIBUTED_SMOOTH_G5 | 5 | 77,824 |
| LEAD_REVISED_G6 | 6 | 311,296 |
| LEAD_BALANCED_G7 / attempt_002 | 7 | 1,245,184 |

The six-image presentation omits generations 4 and 6; their real checkpoints
and OBJs remain saved. It does not combine different candidate ancestries.

A stronger G6 continuation amplified local granularity. LEAD_REVISED_G6 reduced
the negative face stencil. Three final G7 alternatives share that actual G6
parent: ordinary inherited-crease CC (LEAD_FINAL_G7), negative face stencil
(LEAD_ARTICULATED_G7), and the milder convex Task25 face stencil
(LEAD_BALANCED_G7). The ordinary CC result loses much fine relief; the negative
stencil adds oscillation. BALANCED is the retained compromise, not a claim of
DG-level detail. Its new little ridges/valleys remain weaker than the intended
multi-scale organization. The original Task24 four-way underside curl was not
restored or proved to be the generative cause here.

BALANCED has zero wf/we/wp offsets but nonstandard coefficients
`w1=-0.18, w2=-0.3, w3=-0.9, w4=0.5`, other w values zero, and the recorded
valence u-map. Offset-free does **not** mean standard CC. All operations use
the existing pointwise CC/fold stencils; no new Mola generation was used.

Distributed support is evaluated in transported original material XYZ, with
fixed physical zone widths, and biases the front. It is not a shrinking graph
hop radius. Whole-gate reflection is inherited from actual old-corner, edge
and face correspondences; no nearest-point pairing, half-mesh substitution
or coordinate averaging is used. Paired and independently routed G4 trials
selected the same reflected edge sets in this case; there was no demonstrated
geometric divergence. Early right-route descriptive metadata accidentally
retained left seed labels. The correction is explicitly recorded during later
continuation and changes metadata, not geometry, edge selection or sharpness.

## Retained model and verification

Selected checkpoint:
`E:/CHESHIRE_DATA/task26/designs/LEAD_BALANCED_G7/attempt_002/`.
OBJ: `LEAD_BALANCED_G7.obj`, 138,795,053 bytes, SHA256
`849a493cf2e38112e90a37df48252c4dec3f0f12c4414889f58dbb8fc9e6e76b`.
Native: `E:/CHESHIRE_DATA/task26/dcc/LEAD_BALANCED_G7.3dm`, 68,205,372 bytes,
SHA256 `da07b10f94eb37872e1a4a97efcc482187ebbb6b167e66ffb2d8b586a660cdf7`.

It has 1,245,186 vertices, 1,245,184 quads, 2,490,368 edges and zero boundary
edges; COMPAS reports closed/manifold. Bounding dimensions are
4151.937274894672 / 686.0534475838842 / 3549.317375344388. A closed manifold
topology is not proof of absent self-intersection or a printable solid.

Actual OBJ rereading preserves all XYZ and oriented polygon cycles exactly.
RhinoCommon 8.18.25100.11001 wrote and reread the actual native file, compared
all coordinates and face cycles, and opened one object with OpenHeadless.
Units are None; there was no rescale, weld, repair or geometric triangulation.
Headless native validation is distinct from a Rhino viewport capture.

Final constructive symmetry residual is 2.4933470057773444e-12 model units,
with all vertex/face pairs and zero oriented face failures. Front/rear symmetry
is not enforced. Full saved checkpoint reload passed: complete face history,
source cells, signatures, point origins, material coordinates and current crease
edges were verified, then every OBJ point/face and all symmetry pairs were
checked again. `analysis/LEAD_BALANCED_G7_checkpoint_reread.json` is the actual
record. Ten direct saved-geometry comparisons also completed. Timing comparison
RMS displacement is 94.99; paired/independent route comparison is exactly zero;
BALANCED versus its same-parent G7 CC alternative has RMS 2.396 and maximum
119.115 model units. Coordinate differences alone are not evidence of hierarchy.

Corrected captures use installed pyrender 0.1.45/OpenGL on RTX 3070, neutral
clay and real GPU depth occlusion. Quads are split 0-2 only in the separately
recorded display index stream; original polygon meshes remain intact. No AI
image, bump or hidden displacement is used. Final whole/detail sequence is
`renders/progression_selected`; final front, oblique, underside, joint, mantle
and wire views are `renders/lead`. Matched cameras, scale, lights and source
hashes are in each camera manifest. Actual native mesh-plane sections are
stored separately and overlaid in `renders/geometry`.

Early `renders/initial` and `macro_symmetry` RGB already had GPU occlusion, but
their auxiliary depth values used pyrender's incorrect orthographic depth
conversion. They remain archived; corrected `initial_v2` and later captures
supersede them. `analysis/depth_order_check.json` verifies insertion-order
invariance using actual overlapping triangles. Cinema4D's installed headless
entry point exited during the probe; its cause was not established.

## Resources, tests and remaining limitations

Generation runs were sequential and retained separate attempts. Predictive
memory stops remain saved, not reported as geometric failures. The G7 forecast
was calibrated from actual whole-process peaks; the final repeated exact-face
level used the two completed G7 measurements plus a 20% margin, with a strict
same-output-count guard. Extrapolated levels retain the separately recorded
35% margin model. Live 65%-of-available / 12-GiB maximum and 2-GiB system floor
were not relaxed. File byte size was never used as RAM usage.

BALANCED's operation/pairing took 234.51 s, checkpoint writing 59.83 s, OBJ
writing 16.65 s and OBJ rereading 5.31 s. Its guarded generation process tree
plus driver peaked at 4,795,301,888 bytes and completed in 371.98 s. Native
export/validation peaked at 1,149,534,208 bytes / 24.83 s; final capture peaked
at 1,765,294,080 bytes / 25.47 s. Exact stage/process records remain external.

Executed full suite with the official installed Mola DLL/CoreCLR: **803 passed
in 42.41 s**. After the final exact-level memory guard test was added, **6
focused tests passed in 1.95 s**. This does not claim an 804-test full-suite run.
The earlier environment without optional DLL had 781 passed / 22 skipped.
Logs are retained; the DLL is not redistributed.

During preservation, the first checkpoint validator was deliberately terminated
after inspection showed that COMPAS `has_edge` rebuilds the entire edge set per
query. Its interrupted attempt log remains. The corrected adjacency lookup
completed the same full check in 35.74 s, peak 3,072,237,568 bytes; no generation
was performed or geometry changed. The saved-geometry comparison ran for 53.33 s,
peak 1,536,958,464 bytes. These two read-only verification jobs initially
overlapped; the interrupted validation's process peak is 3,509,043,200 bytes.
Generation, native export and capture measurements above are separate completed
jobs; their values do not describe this verification overlap.

Tests cover matched connected cages, oriented reflection, material/state
inheritance and save/reload continuation, bounded support, route metadata and
resource prediction accounting. New whole-gate generation, rendering and native
export are actual runs, not test substitutes. Packaging and checkpoint-reread
utilities are reported by their actual subsequent preservation records.

The retained gate is useful as a control and as material-coordinate/symmetry/
capture infrastructure. It is not an adequate profile-first answer: a distinct
body → neck → spreading seat → horizontal lintel relation, part-specific local
length/circumference rules and a convincing small-fold hierarchy remain for a
separate authorized Task27 run. Global collision analysis, fabrication repair,
thickness and structural verification were not performed. The user-requested
stop records direction reconsideration, not a general algorithm verdict.
