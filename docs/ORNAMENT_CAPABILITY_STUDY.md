# Nested topology ornament capability study — Task 19

Experimental branch: `experiment/task19-ornament-capability`, starting at
`9a948d7e34ee0113930ad771e58281850608a624`. Main and existing tags are preserved.

**Delivered result:** explicit nested geometry reaches ornament depth 4, but the
whole gate still reads mainly as repeated oval/panel motifs. No result is labeled
`GROTESQUE_GATE_CANDIDATE`, and Digital-Grotesque-level visual capability is not
established. This is a technical advance with an incomplete design outcome.

Task 18 established regional activity control, but its ordered distance and
diffusion fields did not produce convincing macro–meso–micro hierarchy. This
study pauses weight-only development and tests discrete local topology events
between the existing subdivision stages. All cases use the exact tracked
22-face C0 beam-column gate, without manual face selection or carrier edits.

## Verified vocabulary and attribution

The user-supplied official HDMola 1.0.0 standalone DLL executes under the existing
Python.NET 3.0.5 / .NET 8.0.14 CoreCLR runtime. No binary, upstream source,
dependency or Grasshopper installation is copied or changed.

Actual assembly reflection and repeated real unit-quad, triangle and warped-quad
calls are retained in `operator_api_evidence.json` in the review bundle. The DLL
SHA256 is `91c6863ee1bfe370dae028389b7d966f36fa58b321d6b2706e111084c8fba5de`.

Two operations are used:

- **TaperedExtrusion:** actual `FaceSubdivision.ExtrudeTapered(Vec3[], Single,
  Single, Boolean)`, with a top cap. The verified nonplanar call uses Mola's
  first-triangle normal, not an invented Newell normal.
- **InsetFrame:** actual `FaceSubdivision.Offset(Vec3[], Single)` with negative
  width. It returns ordered annular sides and one inner cap without splitting
  the original boundary. Width is a serialized fraction of the shortest local
  input edge. On a planar face this initially changes tessellation, not height.

There is no `SplitFrame` symbol. The actual `Frame` symbol was probed but rejected:
it splits source boundaries, has incompatible corner-face orientation on the
unit fixture, and its independently generated inner corners disagree on the
warped fixture. No stitching, welding or neighbor repair was introduced.

Mola owns these face algorithms; public COMPAS 2.15.1 supplies subdivision
topology. CHESHIRE owns the grammar, deterministic selectors, event assembly,
recursion, lineage, budgets and diagnostics. Existing weighted CC/DS equations,
legacy planar Mola adapter, dependencies and Rhino defaults are unchanged.

The isolated event adapter explicitly accepts only projected convex triangles
and quads; quads also pass the existing conservative bilinear Jacobian test.
It retains source XYZ exactly and checks returned side/cap order, shared cap
coordinates, taper formulas, cap orientation, inset containment, connectivity,
components and immediate lineage. Unsupported faces are explicitly excluded by
the serialized eligibility contract. Nothing is flattened or triangulated for
geometry production. Mola's float32 output is used in normalized local frames.

## Constructive lineage

Each event records a unique stage/parent ID, stage index, operator, immediate
parent face, positive C0 source ancestry, prior DS family when available,
parent event IDs and every child's role: `FRAME_SIDE`, `INNER_CAP`,
`EXTRUSION_SIDE` or `EXTRUSION_CAP`. Roles are assigned from the verified return
construction and order; coordinate matching verifies that contract but never
classifies roles after the fact.

CC child faces inherit their verified single source face. DS faces retain their
verified positive control-cage parent mixture, separate from signed geometric
stencils. Mixed faces keep the union of ancestor events but only the intersection
of parent role tokens. Thus an edge between a cap and side cannot pretend to be
an unambiguous cap descendant. New event faces inherit existing DS routing labels
where available, explicitly recorded as inheritance; they are not called newly
constructed DS families. New event vertices receive no invented CC point class.

`ornament_depth` is the maximum actual event-chain depth in a face's ancestry.
Subdivision increases operator lineage depth but not ornament depth. Mixed DS
faces can contain multiple histories, so maximum depth alone is not a unique
semantic parent. Strict common-role selection establishes the nested event
chains. Positive offset vertex associations identify constructive source corners;
they do not claim that displaced coordinates equal a positive interpolation.

The streaming field named `independent_nested_trees` counts first-event roots
with nested descendants. Roots can merge through DS; this field is not a count
of disjoint trees. The independent delivery diagnostic additionally computes
connected components of the event DAG, stores merged-root groups and reports
`independent_nested_event_components`. The preferred two candidates have 176
and 96 independent nested genealogies respectively. Positive source-region
coverage describes ancestry support, not spatial area occupied by ornament.
Parent event sets include known transitive ancestors; immediate parent faces
remain recorded separately. Arbitrary user attributes are not invented.

## Screening and retained evidence

There are 36 primary serialized recipes, nine per family:

| Family | Intended structure |
|---|---|
| A | C11 CC masses → inset frame → CC/DS → cap/side descendant taper → finish |
| B | C11 masses → R13/R15 DS → separate FACE/EDGE/VERTEX family event → DS |
| C | Macro CC → event → subdivision → different child-role event, with deliberate depth-three cases |
| D | R13/R15 DS structure → family frame → inner-cap taper → restrained DS |

Each request contains every generation's exact values, selection rules, operator
hashes, source hash and one-sentence intended mechanism. Existing `Rule` evaluates
normalized centroid height; family, source-region, common role, normal and relative
area predicates provide additional deterministic gates. Selected and excluded
IDs are generated diagnostics, never hand-authored recipe inputs.

The initial A01/C01 weighted-CC inter-event attempts hit the sampled crossing cap.
Those failures remain intact; standard CC between thin event faces replaced that
combination in the revised primary recipes. The pilot B01/D01 completed outputs
were reused rather than rerun. Thus 36 primary recipes required 38 actual attempts.

Stage A uses a local 120,000-face ceiling; finalists/refinements use 250,000.
Global budgets are untouched. The optional 400,000 ceiling is not assumed.
Screening retains terminals, event selections, compressed lineage, diagnostics
and matched views; finalists retain every exact stage and immediate parents.
The task-local storage ceiling is 4 GiB. Workers run serially with explicit venv
Python `-E -s`, sanitized environment, fixed cwd and stdout/stderr logs. Memory
samples include the Windows venv redirector's recursive descendants and driver;
4 GiB resident and the existing physical-memory floor stop unsafe processes.
Timeout/cancellation terminates the scoped worker tree. No new threads are used.

Completed valid cases resume only when request and all saved artifact hashes
match. Failed attempts remain in separate numbered directories. Screening audits
event stages and independently audits all terminals. Deep runs audit every stage
before growth. Crossings use at most 4,096 evenly spaced actual faces, diagnostic
fan triangles and the existing 30-contact cap. Adjacent/coplanar contacts are
excluded. Zero sampled crossings is not a collision-free certificate.

Independent checks verify exact ordered OBJ coordinates/polygon cycles, all
checkpoint face-history coverage, C0 ancestry normalization, event-depth DAGs,
finite/manifold/closed state and whole-camera clipping. Fold/fan and bilinear
warnings are retained rather than repaired. GateIntegrityMonitor remains a
read-only source-corner landmark approximation, not exact aperture clearance.

## Visual review and delivery

All primary outputs, including stopped boundaries, have matched whole front and
oblique views. The original Task-18 whole and registered-detail camera bounds
are frozen for this study; the opening is not cropped away. Finalists/refinements
also have detail, wireframe and constructive depth views (gray/blue/orange/purple).
Depth colors prove ancestry, not visual hierarchy. Images are headless projections
of actual polygon output; no generated images, hidden smoothing or camera fitting.

Review considers architectural macro read, distinct meso articulation, nested
micro geometry, legible computational order, non-uniformity and gate identity.
The four named selections are comparative labels, not an automatic assertion of
`GROTESQUE_GATE_CANDIDATE`. A valid mesh or high event depth cannot establish that
design milestone. Results and final decisions are recorded below at delivery.

The strongest remaining limits are assessed after finalist refinement, including
repetitive cap tiling, detail erasure under finishing, fold/crossing instability,
unsupported CC-after-DS n-gons and genuine differences between event ancestry and
visible independent ornament. No extra unplanned operator will be added to hide
a weak result. Actual new Rhino host verification is separate from headless checks.

## Reproduction

Run from the repository using its existing `.venv`; provide the official external
DLL explicitly. No DLL search or installation is performed:

```powershell
.\.venv\Scripts\python.exe -E -s examples/ornament_probe.py --dll <official-HDMola.dll>
.\.venv\Scripts\python.exe -E -s examples/ornament_study.py --init --dll <official-HDMola.dll>
.\.venv\Scripts\python.exe -E -s examples/ornament_study.py --run A01 A02 --dll <official-HDMola.dll>
.\.venv\Scripts\python.exe -E -s examples/ornament_review.py A
powershell -NoProfile -File tools/ornament_projection.ps1 -PlanPath output/task19/study/A_projection_plan.json
.\.venv\Scripts\python.exe -E -s examples/ornament_verify.py A
```

`--init` refuses an existing directory. Use `--study output/task19/<fresh-name>`
for independent reproduction; copy the delivered frozen recipes into its recipes
directory before executing finalist/refinement IDs. Never overwrite prior evidence.

## Actual results

| Phase | Recipes | Technically valid | Observation |
|---|---:|---:|---|
| A | 36 | 25 | 38 attempts including two retained weighted-CC pilot failures |
| B | 11 | 10 | At least two viable finalists per family; one DS zero-normal boundary |
| R | 12 | 11 | Three refinements each for four visually selected grammars |
| Fresh replay | 1 | 1 | Exact preferred geometry at every stage and decoded event lineage |

Stage-A family validity is A 6/9, B 6/9, C 5/9 and D 8/9. Two declared-stage
completions independently hit the terminal crossing cap; execution completion
and geometric validity are explicitly separate. Other stops include count
budgets, sampled crossing explosions, unsupported CC-after-DS n-gons and an
undefined DS extrusion normal. No result was repaired to pass.

Family C provides the strongest partial hierarchy. C06 follows C11 G1/G2 →
frame → R15 DS → inner-cap taper → standard DS → descendant frame → restrained
R15 DS → smaller descendant taper. The last event is left unsmoothed. Large
lobes contain annular frames and visibly smaller raised caps in the registered
detail view. C07 branches CC cap descendants and confines events to explicit
lintel ancestry, leaving the supports less articulated. These are real generated
geometry and constructive nesting, although the motif remains repetitive.

| Comparative label | Recipe ID | Faces | Event depth | Sampled crossings | Opposed-fan warnings |
|---|---|---:|---:|---:|---:|
| MAX_ORNAMENT_CAPABILITY | F_C06_BOLDER_MESO | 82,370 | 4 | 0 | 12 |
| GATE_LEGIBLE_ORNAMENT | F_C07_RETAIN_TERMINAL_EVENT | 30,208 | 4 | 0 | 0 |
| BEST_GEOMETRIC_ORDER | F_B03 | 44,850 | 2 | 0 | 0 |
| MOST_INFORMATIVE_FAILURE | F_C07_BOLDER_MESO | 736 | 1 | 30, capped | 100 |

The preferred two and geometric-order result have zero bilinear warnings. The
failed aggressive case has eight. Opposed fan normals are diagnostic warnings,
not a proof that a bilinear patch is singular. Crossing samples remain bounded
to 4,096 faces and exclude adjacent/coplanar contacts. The 30-contact failure
used every one of its 736 faces. It stops immediately after the strengthened
first taper; the baseline C07 trajectory remains separately available.

The max-capability recipe contains 704 discrete events: 176 at each depth 1–4.
Its terminal depth counts are 5,454 / 53,508 / 18,304 / 4,224 / 880 at depths
0–4. The gate-legible recipe has 3,552 events and 96 independent nested roots;
CC creates branching descendants while DS predominantly retains one inner-cap
chain. The committed depth table distinguishes rooted starts from merged event
genealogies and includes source ancestry coverage and operator lineage depth.

No 400,000-face escalation was used. The maximum actual output is 168,434 faces;
sampled peak case-tree-plus-driver working set is 1,188,151,296 bytes (about
1.11 GiB). Case workers total 2,199.47 seconds, including their stage audits.
Retained study storage before final projections/archive is 1,445,681,714 bytes,
within the 4 GiB plan. New events add nested ring/cap geometry; additional
finishing mainly adds sampling density and rounds existing motifs. The unsmoothed
C07 refinement reduces 120,832 to 30,208 faces while retaining depth 4. More faces
do not establish more independent ornament.

The single strongest remaining limitation is **insufficient differentiated
local branching**: cap-centered oval/panel motifs dominate at several scales.
Finishing erases contrast, but removing it alone does not solve repetition and
can expose more local warnings. The study does not prove that HDMola is incapable;
it limits the current two-operator grammar. A future experiment should target
distinct cap/side descendant branching before another subdivision scheme or
larger library is considered. No further feature is implemented here.

## Gate drift and host status

| Landmark observation | Max capability | Gate-legible |
|---|---:|---:|
| Opening width / original | 100.64% | 99.93% |
| Opening height / original | 75.33% | 81.70% |
| Width / depth / height extent drift | +11.64 / +99.87 / +12.59% | +11.85 / +112.92 / +12.62% |
| Mean support-base lift, original coordinate units | 502.46 | 459.48 |

Both retain left/right support ordering and the lintel-above-support relation.
These are source-corner-cloud observations, not exact free-aperture measurements
or fabrication constraints. Whole front/oblique comparisons have zero clipped
vertices across all 59 primary/finalist/refinement terminals. Detail crops remain
registered to the same original shoulder region.

Family E was not activated: adding field selection would not address the observed
motif limitation. The conditional strong-result Rhino mode was not added. No
active Rhino host was observed, so actual Rhino host checks are **NOT TESTED**.
Existing modes remain intact; delivered OBJ geometry can be inspected separately.

Full suite, run once after implementation stabilized with the real external DLL:
**743 passed in 31.72s**. The preferred case's fresh isolated replay matches every
stage geometry hash and its decoded terminal event lineage exactly; a real
resume check skips it without launching another worker. Test logs, fixed recipes,
API evidence and concise results are tracked under `studies/task19/`; complete
geometry, checkpoints, selections and matched views are in the review archive.
