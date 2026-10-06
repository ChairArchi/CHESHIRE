# Task 18: source-space spatial activity stress test

**Outcome E is best supported.** Spatial activity changes where articulation
occurs and suppresses some uniform repetition, but the tested fields do not
produce convincing macro → meso → micro differentiation. Ordered diffusion
is not justified as a default. Distance-static is sufficient for the weak
regional modulation observed here. Tests passing establish reproducibility
and contracts, not design success.

## Checkpoint and distribution

Task 17 was clean at `ec5c3bcd0efd9aac08dfe4a6a813ab2aaf35ce20` and annotated
as `checkpoint/task17-subdivision-base`. All 100 baseline tracked text files
and historical tracked paths were audited. No external DLL, vendored source,
upstream/review archive, environment, local settings or secret blocked
publication. Usage examples with machine paths were generalized. No project
LICENSE or HDMola license assumption was added.

The documentation checkpoint passed **729 tests in 32.73 seconds** and diff
checks. The previously empty origin received main at
`ff338662889bc74e4443f8e783d68f90c41da89b` and the baseline tag. See
[checkpoint](CHECKPOINT_TASK17.md) and [external boundaries](../THIRD_PARTY_NOTICES.md).
The final experimental commit/push/archive identities are recorded in the
review bundle delivery metadata; large output remains outside git.

## Established mechanisms and experimental hypothesis

Existing CC/DS subdivision stencils, graph shortest-path distance and explicit
neighbor averaging are the prior mechanisms. Their geometry equations are
unchanged; the earlier [CC reference](WEIGHTED_SUBDIVISION_REFERENCE.md) and
[DS reference](TASK17_REFERENCE.md) document the implemented subset.
Generation-dependent BROAD → MEDIUM → FINE activity is the CHESHIRE
experimental hypothesis. No direct precedent, uniqueness, Digital Grotesque
reproduction, algorithm equivalence or fabrication equivalence is asserted.

The hypothesis is that source-space activity ordering, without new geometry
vocabulary, can organize nested scales better than uniform, static, reversed
or permuted activity. All controls use the same C0, recipes and count ceiling.

## Frozen source fields

C0 is the exact Task17 24-vertex / 44-edge / 22-face closed coarse gate.
Its established depth remains 500; this does not reinterpret the earlier
900-depth dense gate. Canonical fields live on its sorted vertex adjacency
graph. All seeds are synthetic controls, not architectural labels:

| Layout | Exact C0 vertex IDs | Registration |
|---|---|---|
| A SHOULDER_PAIR | 6, 7, 9, 10 | Two inner support/lintel junctions, front/back |
| B FOUR_CORNER_FRAME | 0, 3, 6, 7, 9, 10, 12, 13 | Two outer lower regions plus the two inner upper junctions |
| C UPPER_BIAS | 18, 19, 20, 21 | Sparse symmetric upper lintel corners |

IDs, coordinates, initial 0/1 values, graph, parameters, resulting values,
statistics and SHA-256 hashes were frozen before geometry review in
[fields.json](../studies/task18/fields.json). Seed locations were never tuned.

Distance is unweighted graph hop distance `d` from the seed set, with
`phi = max(0, 1 - d/3)`. Disconnected values are unavailable (`null`), not
invented. The explicit diffusion is:

`phi_next(v) = (1-lambda)*phi(v) + lambda*mean(phi(neighbors(v)))`.

Lambda is 0.5; FINE uses 1 iteration, MEDIUM 4, BROAD 12. Each resulting
field is divided by its own maximum. This matches peak activity, **not total
mass**; breadth/amplitude coupling remains a limitation. Raw degree-weighted
mass conservation and symmetry are tested. No SciPy, stochastic process,
reaction-diffusion or additional dependency is used.

| Seed | FINE spread | MEDIUM spread | BROAD spread | Distance spread |
|---|---:|---:|---:|---:|
| A | 0.3731 | 0.9179 | 1.1515 | 0.9091 |
| B | 0.3414 | 0.6617 | 0.8003 | 0.6154 |
| C | 0.2623 | 0.7805 | 1.3253 | 0.8889 |

Spread is activity-weighted hop distance from seeds. Min/max/mean, variance,
normalized entropy and effective occupied fraction are retained separately.
The three concentration scales differ numerically on every seed graph.

## Inheritance and weight mapping

All four source fields are propagated in parallel, so changing scale later
selects an inherited version of the original source field. CC uses its existing
positive sampling parents: retained corners keep identity, edge points use
the endpoint average, face points use the parent-face average. DS uses the
existing positive standard DS corner coefficients. These describe scalar
control-cage association; they do not explain negative geometric coefficients
or invent architectural/categorical ancestry. Missing values remain null and
block modulation. Actual study field coverage is 100% at every generation.

CC face weights use the mean descendant vertex activity, edge weights the
endpoint mean and corner weights their vertex activity. Optional local w3/w4
were added to the existing later face stencil. DS uses each input face's
mean activity for the appropriate existing FACE/EDGE/VERTEX w1/w10 pair;
an explicit local pair override was added. No stencil equation changes.

The standard quiet values are verified in the implementation: CC
wf/w1/we/w2/wp/w3/w4 and all six DS family parameters are zero. Each parameter
uses `w_local = w_quiet + (w_active-w_quiet)*phi`. Exact endpoints avoid
cancellation: phi=1 returns the original active value directly. Scheduled
normal-extrusion ratios still multiply the current global mean input edge
length; activity itself comes from source space, not current geometry.
Unsupported weighted DS n-gons keep the established standard COMPAS fallback,
including zero extrusion. No repair or triangulation is introduced.

## Matrix and controls

Exact recipes are loaded from existing code and frozen in
[recipes.json](../studies/task18/recipes.json): C11 CC, R15 DS and HYBRID_B
(C11 G1–G3, unchanged global G4–G6 R13 rows). R15 was selected because Task17
recorded no local fold or sampled contact warnings at any generation.

| Strategy | G1 | G2–G3 | G4 onward |
|---|---|---|---|
| U | Uniform 1 | Uniform 1 | Uniform 1 |
| S | MEDIUM | MEDIUM | MEDIUM |
| M | BROAD | MEDIUM | FINE |
| R | FINE | MEDIUM | BROAD |
| P | MEDIUM | FINE | BROAD |
| D | Distance | Distance | Distance |

Stage A ran **45 primary cases plus three A-seed distance controls**, all to
G4. Stage B ran **12 declared informative cases**: A-seed DS U/S/M/R/P/D to
G6; C-seed CC U/M to G5; C-seed HYBRID U/S/M/R to G6. Selection retained the
complete clean DS control comparison, the lower-warning but weak upper CC
case and its exact reference, and a handoff comparison including reverse.
No gate drift threshold or automatic beauty ranking selected cases.
There are no invented C11 G6 rows: its existing five-row schedule stops G5.
One additional fresh-directory G4 replay is a reproduction check, not another
unique design case. **Stage C and optional coupling were skipped** because
the actual images did not support ordered hierarchical differentiation.

Every uniform checkpoint exactly reproduces the saved Task16/17 geometry
hash, including CC G5 and DS/HYBRID G6. The nine Stage-A uniform cases are
three unique geometries repeated across seeds, not independent design probes.

## Diagnostics and visual evidence

Separate measurements include displacement distribution, top-decile mass,
effective spatial fraction, top-20%-threshold connected face patches, normal
variation at two graph radii and coarse source-seed support persistence.
No aggregate hierarchy score is used. Displacement is measured from the
positive immediate sampling position, **not excess displacement over standard
subdivision**. Standard smoothing therefore contributes. Patch threshold ties
are included; the active fraction can exceed 20%. Persistent source support
does not prove geometrically nested patches.

The existing mean pairwise incident-normal angle/pi is used at radius one,
then on incident faces of one neighbor ring at radius two, at at most 1,024
evenly spaced vertices. This is a comparative normal proxy, not a formal
curvature spectrum. The GateIntegrityMonitor remains read-only, measuring
descendant landmark clouds rather than exact free opening clearance.
CSV records and nine SVG diagnostic-versus-opening-drift plots are retained.

All 48 completed Stage-A cases have matched whole and front sheets; warning
cases remain included and labeled. Stage B also has every checkpoint, fixed
detail and wire comparisons. There are 54 contact sheets and 692 individual
frames. Camera/scale/light/crop reuse frozen Task17 bounds without per-candidate
fitting. Nonplanar polygon painting is approximate and these are **headless
images**, not Rhino screenshots. No geometry or camera masks warnings.

Compact evidence is [tracked here](../studies/task18/evidence/); complete
per-case requests/responses/fields/meshes and trajectories are in the ZIP's
`output/task18/study/`.

## Actual results and negative controls

All 60 unique cases completed the requested generations with finite, closed,
one-component manifold topology. Only **22 trajectories are warning-free**:
16 Stage-A DS cases and six deep DS cases. CC/HYBRID histories retain local
fold warnings even when their terminal mesh has no recorded local warning.

| A-seed DS at G6 | Patches | Largest patch fraction | Normal proxy r2 | Opening H drift % |
|---|---:|---:|---:|---:|
| U | 3,400 | 0.0063 | 0.04156 | -26.60 |
| S | 1,694 | 0.0358 | 0.02502 | -29.72 |
| M | 679 | 0.1785 | 0.01838 | -27.20 |
| R | 2,512 | 0.0074 | 0.03838 | -32.25 |
| P | 2,704 | 0.0077 | 0.03599 | -29.97 |
| D | 1,882 | 0.0274 | 0.02602 | -29.94 |

M has fewer, larger high-displacement regions. This is a measurable spatial
effect, **not the requested independent micro scale**. Its fine-generation
normal variation is lower; the detail sheets show broad rounded shoulders
with faint repetitive relief. S and D are close in normal variation, drift
and visible weak detail. Diffusion has not demonstrated an advantage over
ordinary distance mapping for useful hierarchy.

R/P retain more repeated small relief than M. M does not materially beat them
on the design target. Uniform CC retains the strongest angular/corrugated
articulation but 364 opposed-fan flags at G4 and 80 at G5. Upper-field M reduces
these to 24 at G4 and zero at G5, with warnings earlier and substantial lost
detail. Hybrid fields mainly soften the CC-to-DS surface; no independent third
scale appears. DS benefits most in stable **regional control**, without a
hierarchy success for any grammar.

Sampled nonadjacent transverse contacts are three at G4 for each uniform
HYBRID reference (including its deep replay), zero elsewhere. Zero sampled
contacts is not a collision guarantee: only up to 4,096 evenly spaced actual
faces per generation are audited, adjacent/coplanar overlaps are excluded,
and diagnostic fans are approximate for nonplanar polygons. Four unsupported
DS pentagons retain standard placement from G2 onward; hybrid starts the
equivalent fallback after its first DS step.

Activity concentration does not consistently preserve gate identity. DS M
reduces outer width expansion versus U (20.27% versus 25.36%), while opening
height still shrinks 27.20%. DS S/D shrink it about 30%; reverse shrinks 32.25%.
Upper HYBRID M drifts -27.79% in opening height versus U -23.97%. Reducing
activity and outer growth does not imply preserving the opening. Ground,
center and support/lintel trajectories remain individually recorded, never
fed back into subdivision.

Outcome E is primary; C and D are secondary findings about the tested controls.
Localization is a useful controllable effect, but it mostly removes uniform
detail or rounds the carrier. B is not claimed as successful hierarchy, and
A is unsupported. Keep the activity interface and simple distance control;
retain diffusion as experimental evidence, without promoting ordered diffusion.

The next falsifiable hypothesis is that a bounded nonlinear rule producing
persistent local topology branches, under the same source seeds and comparable
count budget, can retain a meso structure while adding a separate smaller
structure that these fixed stencils lose. It must outperform the retained
uniform/static controls without added crossings. **No such rule was implemented.**
The experiment does not prove that every possible spatial field is insufficient:
C0 has only 24 source vertices, interpolation attenuates fine support, fields
share a peak rather than total mass, and only these exact schedules were tested.

## Runtime, verification and replay

The explicit repository .venv, sanitized environment, `-E -s`, shell=False,
separate logs and existing bounded subprocess wrapper were reused. Geometry
count ceilings remain task-local 120k / six generations; other modes and
global budgets are unchanged. Experiments run serially, with 120 seconds per
case and 30 per crossing audit. Resume verifies request, complete generation
coverage, geometry, field hashes, terminal OBJ and crossing records. Interrupted
attempts are preserved rather than deleted.

The existing direct-child working-set counter misses the actual Python process
below Windows' venv redirector. Its reported peak is **not actual worker peak**.
A scoped process snapshot measured the real worker at 396,918,784 bytes; an
actual peak is unavailable. The physical available-memory floor, count limits
and timeouts remain active. This existing instrumentation limitation is recorded,
not silently fixed or disguised. Task17 evidence is untouched.

The read-only full lineage/OBJ audit exceeded its initial 120-second diagnostic
window while rendering ran concurrently. That attempt and logs are preserved;
the audit was repeated serially with its own 300-second verification window.
This does not raise experiment generations or geometry budgets. Topology-only
sampling caches are accepted only after exact ordered vertex IDs/face cycles
match every actual output; modulated geometry is never reused across cases.

Focused field/operator checks passed (21). The final full suite ran once after
implementation stabilized: **736 passed in 33.17 seconds**, including the
unchanged optional backend. `git diff --check` passed. The serial audit passed
262 exact topology/source-field checks and 130 exact ordered OBJ roundtrips;
all uniform references match and no whole-view vertex lies outside the fixed
camera bounds. The audit retry took 169.875 seconds. Geometry workers totaled
611.828 seconds, crossing audits 89.793 seconds, with no experiment/audit
failures. Retained task output is about 565 MB against the 2 GiB cap. Exact
archive identity and final source commit are in the review delivery record.
Stage-A stores terminal OBJ plus JSON previews; Stage-B stores every OBJ/JSON
checkpoint. The declared task-local storage limit is **2 GiB**. No old evidence
was deleted, no dependency was installed and no third-party source was rebuilt.

Rhino host was unavailable (no Rhino process or connected tool). No new
SpatialActivityStudy mode was added: the conditional design evidence did not
warrant promoting the weak study into an interactive feature. Existing Rhino
modes remain unchanged. Actual host insertion/cancellation are not claimed.

Replay needs only the existing core .venv and the tracked frozen inputs:

```powershell
.\.venv\Scripts\python.exe -E -s examples/spatial_activity_prepare.py output/task18/replay
.\.venv\Scripts\python.exe -E -s examples/spatial_activity_study.py --study output/task18/replay --run A
# Deepen the source IDs declared in studies/task18/evidence/stage_B_decision.json:
.\.venv\Scripts\python.exe -E -s examples/spatial_activity_study.py --study output/task18/replay --run B --cases <declared source IDs>
# Canonical retained evidence: regenerate tables, plans and plots.
.\.venv\Scripts\python.exe -E -s examples/spatial_activity_review.py --observations --plan A --plots
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/capability_projection.ps1 -PlanPath output/task18/study/views/A_plan.json
```

The fresh-directory smoke replay matched its canonical G0–G4 geometry/field
hashes and a second invocation resumed the completed output. The prompt's
23 delivery questions are also answered by the result record and final report.
