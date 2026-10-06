# Generational point-class study (Task 16)

**PARTIAL_SUCCESS.** The new face stencil retains secondary support lobes and
shoulder/lintel ridges more clearly than Task 15 L4. The G4/G5 transition still
produces repeated corrugation or rounds off the secondary detail. No
`FIRST_GROTESQUE_GATE_CANDIDATE` is designated. This is not Digital Grotesque
reproduction or a demonstrated three-scale hierarchy.

Baseline: `9a02d99899da2179dca3bb74e9891a697dd24177`. Python 3.12.10 and COMPAS
2.15.1 remain unchanged. No dependency, new geometry operator beyond the
requested face stencil, repair, remeshing, field system or core refactor.

The [reference note](WEIGHTED_SUBDIVISION_REFERENCE.md) gives equation (4),
notation, evaluation order and the immediate V/F/E/E ancestry contract. The
opt-in [implementation](../src/cheshire/generational_subdivision.py) calls the
unchanged Task 14 operator and changes only eligible face-point positions.
Normals, edge/corner rules, boundary policy, topology and budgets stay intact.
Immediate origin records and topological original-face chains are retained;
full semantic inheritance is explicitly **NOT IMPLEMENTED**.

## Actual execution and correctness

The exact saved Task 15 C0 is the only design carrier: 24 vertices, 44 edges,
22 faces; width/depth/height 4000/500/3500, opening width/height 2200/2600.
Its origin is `[-400.036865234375,-18.533447265625,0]`. There is no carrier
matrix, spatial modulation or terminal smoothing in this study.

Before design runs, new `w3=w4=0` C0 G1-G5 geometry matched the saved Task 15
L4 checkpoints **exactly** in ordered XYZ and connectivity. New origin attributes
are additional metadata, so complete attributed objects are not byte-identical.
Independent coefficient tests check nonzero equation (4); tests also cover
rotation/reversal of the face cycle, ancestry failures, reset of origin classes,
source immutability, serialization and a budget-stopped Rhino checkpoint.
Standard control S matches public COMPAS Catmull-Clark at all five generations
within absolute coordinate distance `1e-9`.

| Generation | V | E | F | Eligible input faces | Task 14 fallback |
|---|---:|---:|---:|---:|---:|
| G0 | 24 | 44 | 22 | — | — |
| G1 | 90 | 176 | 88 | 0 | 22 |
| G2 | 354 | 704 | 352 | 88 | 0 |
| G3 | 1410 | 2816 | 1408 | 352 | 0 |
| G4 | 5634 | 11264 | 5632 | 1408 | 0 |
| G5 | 22530 | 45056 | 22528 | 5632 | 0 |

Every serious case reaches G5, remains one connected closed mesh, and retains
G0-G5 JSON/OBJ with exact ordered-coordinate/connectivity OBJ reload checks.
G1's intentional fallback is `first_generation_no_previous_origins`. No later
fallback occurs on C0. Focused malformed-ancestry tests record explicit missing,
stale and false-incidence fallbacks without guessing from coordinates.
Each run uses a fresh explicit `.venv` worker, `-E -s`, existing sanitized
environment, 60-second timeout, 50k vertex/face caps, 4 GiB combined resident
memory cap and 3 GiB study storage limit. Crossing audits have a separate
30-second bound. No budget was weakened.

## Design evidence

Sixteen deterministic design schedules were executed: four class-direction
probes, eight declared choreographies and four declared final refinements.
Controls S and L4 are additional. One exact C11 repeat checks reproducibility;
it is not a seventeenth design schedule. No randomness, grid or aesthetic score.
Definitions serialize all seven controls separately for all five generations,
including actual coordinate-unit extrusion values and point-origin diagnostics.

The strongest partial schedule is **C11_interpolation_release**. C09 is a
ridge-hold comparison; R14 tests a quieter fine tail. These share an observed
split-lobe/ridge family. They are not presented as three different successful
morphological families. C11 retains the G1 broad support massing, G2/G3 paired
support lobes, shoulder peaks and lintel bands into G5. The gate, left/right
supports, lintel and central opening remain legible in matched front/oblique
views. Pinching at folds and loss of some sharp G3 detail remain visible.

C11 ratios (CHESHIRE design choices, not a published Hansmeyer schedule):

| G | wf (w10) | w1 | we (w11) | w2 | wp (w12) | w3 | w4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | .30 | -1.00 | -.080 | -.70 | .100 | 0 | 0 |
| 2 | .16 | -1.05 | -.050 | -.90 | .045 | -.8 | .5 |
| 3 | .07 | -1.10 | -.025 | -1.00 | .015 | -.6 | .8 |
| 4 | .04 | -.90 | -.015 | -.80 | .008 | -.4 | .5 |
| 5 | .025 | -.70 | -.010 | -.55 | .004 | -.3 | .3 |

`wf/we/wp` multiply the current **global mean input edge length**, unchanged
from Task 14. Other weights are dimensionless. All are uniform spatially.
For C11, median edge length falls 577 → 335 → 168 → 80 → 39 units; median
retained-corner motion falls 193 → 87 → 55 → 31 → 12 units. These describe
geometry and attenuation, not an aesthetic score or proof of hierarchy.
Original-face residuals measure distance to positive control-cage sampling,
not exact surface displacement; shared vertices occur in multiple groups.

| Partial example | Fan warnings G1-G5 | Bilinear warnings G1-G5 | Sampled crossings G1-G5 |
|---|---|---|---|
| C11 | 8,100,352,364,80 | 0,8,44,20,0 | 0,0,0,0,0 |
| C09 | 8,100,360,688,248 | 0,8,156,208,0 | 0,0,0,0,0 |
| R14 | 8,108,348,304,72 | 0,24,124,8,0 | 0,0,0,0,0 |
| L4 control | 8,16,0,0,4 | 0,0,0,0,0 | 0,0,0,0,0 |

Intermediate warnings matter: a quiet G5 does not erase G2-G4 pinching.
C11's G1 warnings touch extraordinary/junction vertices, but most later flags
are elsewhere. At G5 all 80 flags lie outside those current one-hop
neighborhoods; none touch naked boundaries because this mesh is closed.
The retained Task 15 valence association is observational, not causal.
Original junctions mean retained source vertices at Z=2600 and their current
one-hop neighborhoods; they are geometric landmarks, not semantic labels.

P01 has 16 sampled crossings at G5; C05 reaches the 30-contact limit at G5;
C10 reaches it at G4 and G5. They are rejected from preference, with geometry
and exact failed parameters retained. C08/C12/R15/R16 have substantial local
flags despite no sampled transverse crossings. Zero sampled crossings never
certifies global collision freedom: the existing diagnostic approximates quads
with fan triangles and excludes adjacent/coplanar contacts. No geometry repair.

**THE CURRENT EXTENDED CATMULL-CLARK SUBSET REMAINS MORPHOLOGICALLY INSUFFICIENT
FOR THE TARGET HIERARCHY.** This bounded study supports testing another scheme
such as weighted Doo-Sabin next; it does not prove every possible Catmull-Clark
schedule fails. No Doo-Sabin implementation begins here. The success-gated
regional field and C1 transfer were skipped.

## Rhino and reproduction

Run the existing `rhino/CHESHIRE_Run.py` in Rhino 8 ScriptEditor / Python 3,
select the original axis-aligned gate, then choose **GenerationalWeightStudy**.
It constructs the unchanged C0 fixture at the selected bbox X/Y center and Z
floor. The original dense gate has depth 900; the Task 15 C0 has depth 500.
This documented difference is retained explicitly. No fitting, retopology,
rescaling or transformation of the selected source occurs. The mode accepts
the original 4000×900×3500 or C0 4000×500×3500 bbox in original units; other
dimensions/orientations are rejected clearly.

The five displays are C0 SOURCE, L4 CONTROL G5, BEST NEW G1/G3/G5. TextDots
and new layers use the existing X-only offsets, insertion rollback/Undo,
source fingerprint, cancellation and timeout. Labels call C11 a partial
hierarchy. Only completed checkpoints survive partial failure. No DLL or
Mola runtime is required by this mode. Existing modes/defaults stay unchanged.

The real worker was tested from a normal Windows shell with simulated Rhino
Python variables. It imported its own Python 3.12 stdlib and repository
CHESHIRE, finished both comparisons, and matched all ten saved C0 L4/C11
checkpoints exactly. A second bounded study execution also matched C11's
G0-G5 geometry JSON and OBJ bytes exactly. **Actual Rhino host insertion,
viewport, Undo and cancellation checks remain PENDING.** All supplied images
are labeled HEADLESS and use saved actual geometry, fixed camera/scale/light
and registered detail crop, without presentation smoothing.

Study and evidence commands (from the repository, using its existing outputs):

```powershell
.\.venv\Scripts\python.exe examples\generational_review.py audit
.\.venv\Scripts\python.exe examples\generational_review.py report
.\.venv\Scripts\python.exe examples\generational_weight_study.py views --names CONTROL_L4 C11_interpolation_release R14_detail_class_shift --label comparison
```

For fresh geometry reproduction, call `run_choreography` from
`rhino/generational_study.py` with `mesh_from_data(C0.json)` and the five rows
in the chosen `schedules/*.json`; no prior Task 15 output is needed. The
offline CLI's `--one NEW_DIRECTORY --input C0.json --schedule DEFINITION.json`
additionally checks the preserved baseline operator in this Git repository.
`init` deliberately requires saved Task 15 geometry for the regression gate.
Existing case directories are never overwritten by new experiments.

Delivery evidence lives in ignored `output/task16/study/`: `START_HERE.md`,
all schedule definitions, G0-G5 meshes, compressed origin/stencil/checkpoint
records, stage diagnostics and warning locations, real crossing contacts,
same-camera progression/whole/detail/wire/front sheets, regression/audit and
worker logs. `metadata_recording_correction.json` records a development-only
metadata fix: 13 early output bbox records in both compressed copies were
corrected from the pre-stencil box to the actual saved geometry's box. The
original boxes remain labeled; geometry, weights, lineage and diagnostics did
not change. The source now records actual post-stencil output directly.

The review ZIP contains source, focused/existing tests, references, this actual
evidence and final test/diff logs. It excludes `.git`, `.venv`, external DLLs,
upstream source, machine settings and prior experiment bundles. No push.
