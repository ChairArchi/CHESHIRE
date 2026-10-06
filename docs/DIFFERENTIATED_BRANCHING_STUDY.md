# Differentiated branching ornament — Task 20

Task 19 proved constructive topology-event depth 4, but cap-centered oval/panel
motifs still dominated. Extra subdivision often rounded event boundaries without
creating a different ornament. Task 20 tests different descendant actions and
explicit quiet branches, using the same verified operators and original C0 gate.
There is no new subdivision, Mola operator, field model, repair or dependency.

The experiment starts at `838490b8aafb9c2f2961b18b3cda0e89435fd087` on
`experiment/task20-differentiated-branching`. Main, existing tags and the Task-19
branch remain unchanged. Experiments and large output remain outside Git.

## Frozen C07 and verified geometry

The exact saved `F_C07_RETAIN_TERMINAL_EVENT` recipe is loaded from tracked Task-19
evidence. Every primary grammar retains its first five stages verbatim: C11 G1,
C11 G2, first tapered event, standard CC articulation, then its first InsetFrame.
These stages produce 88 / 352 / 736 / 2,944 / 4,480 faces. Their ordered geometry
hashes are checked against the actual Task-19 checkpoints in every worker.
No numerical schedule is reconstructed or retuned. The remainder of C07's
original descent is replaced by the branch experiment; the complete original
C07 is retained as a reference alongside exact C06 and B03.

Geometry still uses public COMPAS topology with the existing CHESHIRE weighted
CC/DS equations, standard zero-weight variants, and the external official
HDMola 1.0.0 assembly. Events call the verified `ExtrudeTapered` or negative
`Offset` (InsetFrame) contract. Source XYZ and shared original boundaries remain
intact. Eligibility stays projected-convex tri/quad with the existing conservative
bilinear check; no flattening, triangulation, welding or neighbor repair is added.
An ineligible route is reported and left quiet. Mola owns the face algorithms;
branch choices, ancestry bookkeeping and composition are CHESHIRE decisions.

## Small serialized branch table

`cheshire.branching` adds `BranchRule`, `BranchTable` and `BranchingRecipe`.
The recipe contains the full exact backbone and its content hash, retained prefix
length, ordered downstream tables/subdivision steps, declared finish and intended
morphology. `studies/task20/branch_table.schema.json` documents the table contract.
Content hashing uses canonical JSON; no opaque design callback is serialized.

Every table evaluates ordered first-match rules on one pre-round mesh snapshot.
It allocates sibling faces before executing any event, so a later rule in that
table cannot consume the earlier rule's newly generated faces. All unmatched
and ineligible faces use explicit `quiet` fallback. A matching quiet rule and an
empty active rule are recorded without a new event or branch token.

Rules use constructive stage/role, exact or minimum event depth, parent operator,
C0 source-region ancestry, existing DS routing family, relative face area and
normalized COMPAS face-normal dot products against world x/y/z. Signed intervals
distinguish up/down/side; absolute intervals are explicit. Role selection retains
Task-19's common-parent-role requirement. Mixed DS parents cannot pretend to be
unambiguous cap descendants. No manual design face IDs or randomness are used.

`FRAME_SIDE`, `INNER_CAP`, `EXTRUSION_SIDE` and `EXTRUSION_CAP` can route
independently. Downstream subdivision remains global, explicitly declared. Quiet
means no topology event, not an immovable patch under global subdivision. No
selective/local CC or DS operation is invented.

## Signatures, with mixed ancestry kept honest

A signature is the constructive sequence `operator:child_role`. An event appends
exactly one token; subdivision appends none. Every face retains a positive
control-cage mixture of paths through verified immediate face parents. DS can
mix paths, and the mixture is kept rather than choosing an arbitrary winner.
These positive associations are semantic ancestry, not signed geometry stencils.

Reports include terminal weighted face mass and overlapping face presence per
path, overlapping event counts, dominant terminal signature fraction, maximum
branch depth, independent nested event components and source C0 faces supporting
multiple positive signatures. Dominance excludes the empty unornamented path.
The independent report also includes generated-but-consumed signatures with
zero terminal mass. Source-region coverage is ancestry support, not surface area.

The original C07 already has five terminal signatures and a 23.53% dominant
fraction despite repeated cap descent. C06 has eight and 63.22%; B03 four and
66.18%. Output side/cap roles alone generate multiple signatures. Neither low
dominance nor many signatures proves visible differentiated descent. Matched
geometry review must establish that different sibling roles actually receive
different later actions and produce visibly different structures.

## Primary grammars and anti-melt policy

44 primary recipes are frozen before screening: A9 / B9 / C9 / D9 / E8.

| Family | Tested relationship |
|---|---|
| A | Inner-cap rings versus side fins; inverse words and direct versus subdivided descent |
| B | Exact event-depth and role-aware alternate descendants; older flanks and quiet caps |
| C | Broad signed orientation classes coupled to constructive cap/side roles |
| D | Exact saved B03/C06 downstream DS rows composed with C07 and cap nesting |
| E | Deterministic role/orientation/area pruning with intentionally quiet siblings |

Most use `FINISH_NONE`. A declared `FINISH_RESTRAINED_CC` or
`FINISH_RESTRAINED_DS` contains at most one terminal stage. Pre-finish geometry,
face counts, edge-length distributions, adjacent face-normal variation,
signatures and event depth are retained separately. Final detail comparison uses
the identical pre-finish input. Finishing is judged for feature survival, not
assumed to improve quality. No automatic extra generation is appended.

## Execution and evidence

Task-local ceilings are 120,000 faces for primary screening and 250,000 for deep
runs/refinement; 500,000 is reserved for one visually justified conditional hero.
Global defaults are unchanged. Serial CoreCLR workers reuse explicit repository
venv Python `-E -s`, sanitized child environment, fixed cwd, process-tree memory
guard, timeout/cancellation cleanup and stdout/stderr files. No threading is added.
The local storage ceiling remains 4 GiB.

One refinement's audit stopped on an unavailable descendant memory measurement.
Inspection exposed a limitation of parent-PID-only discovery after PID reuse.
The isolated Task-20 process guard additionally verifies parent/child creation
ordering and checks creation identity on the same handle before termination,
using [Windows GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes).
Limits and missing-measurement stops remain strict. The old Task-19 guard is
unchanged. The failed attempt is retained; the exact unchanged recipe completes
with the new guard, whose actual audit tree has three verified Python processes.
Guard/source versions are recorded in each request rather than relabeled.

Every attempt stores input, recipe/operator/output hashes, exact stage parameters,
runtime, routing decisions and terminal state. Content-verified resume requires
the same request and every recorded artifact hash. Failures are preserved in
separate attempts without secret parameter reductions.

Events and terminal finishes receive bounded sampled crossing audits; deep runs
audit every checkpoint before growth. Identical geometry reuses only its exact
within-worker audit. Samples use at most 4,096 actual faces and the existing
30-contact cap, excluding adjacent/coplanar contacts. Zero sampled contacts does
not certify global collision freedom. Fan and bilinear warnings are retained.

A focused full audit of all 4,480 frozen Stage-5 backbone faces found 12
non-adjacent diagnostic contact pairs. Some terminal 4,096-face samples miss
these unchanged faces as the terminal count grows. Independent reports therefore
track those exact face-cycle/XYZ contacts separately. A zero terminal sample must
not be called globally clean, and zero unchanged-cohort retention after global
subdivision is not proof that the altered geometry resolved every contact.

Independent checks verify ordered OBJ coordinates/polygon cycles, finite and
manifold/closed/component state, positive C0 and signature mass, event-depth DAGs,
all downstream checkpoint coverage and whole-camera clipping. GateIntegrityMonitor
remains a read-only source-corner landmark approximation, not exact clearance.

Primary workers retain terminal geometry/diagnostics and views. Finalists retain
compressed downstream geometry and immediate lineage; exact common backbone
geometry/lineage/signatures are included once. No intermediate OBJ gallery is
created. The review bundle includes full geometry for finalists/refinements,
while primary screening is represented by frozen recipes, diagnostics and images.

Whole front/oblique and registered detail bounds are exactly the Task-19 camera.
Finalists add wireframe, event-depth and child-role colors. Colors label ancestry,
including dark mixed paths; they do not assert aesthetic hierarchy. Native
headless projections show actual polygons without added smoothing or camera fits.

## Reproduction

Use the existing local environment and supply the official DLL explicitly:

```powershell
.\.venv\Scripts\python.exe -E -s examples/branching_study.py --init --dll <official-HDMola.dll>
.\.venv\Scripts\python.exe -E -s examples/branching_study.py --run A01 A03 --dll <official-HDMola.dll>
.\.venv\Scripts\python.exe -E -s examples/branching_review.py A
powershell -NoProfile -ExecutionPolicy Bypass -File tools/branching_projection.ps1 -PlanPath output/task20/study/A_projection_plan.json
.\.venv\Scripts\python.exe -E -s examples/branching_verify.py A
```

Initialization refuses an existing study. The source runner's `--study` option
permits a separate fresh directory within `output/task20`; frozen delivered
backbone/reference assets must be present. Reproduction never searches drives
for a DLL or modifies Grasshopper. ExecutionPolicy above is process-local only.

## Results

44 primary grammars actually ran: A9 / B9 / C9 / D9 / E8. 43 completed without
a process, budget, degenerate-face or severe crossing-cap stop. This definition
includes two deliberately quiet boundary cases, E06/E08, which produce no new
events. It also includes completed cases with sub-cap sampled contacts or fan /
bilinear warnings. They are explicitly reported, not certified collision-free
or automatically selected as design successes. B03's reverse frame-on-fin event
fails its boundary/orientation contract and is retained without repair.

12 exact promotions retained full downstream checkpoints; 11 completed. Five
promotions received three descendant-only refinements each. Three additional
single-DS finish comparisons bring the refinement count to 18 recipe IDs, with
17 completed. One process-guard failure was retried with identical parameters;
both attempts are retained. One ordinary-resolution Hero combines observed A/B
relationships and quiet side pruning. It completes with 18,544 faces, then an
independent fresh worker reproduces exact ordered geometry, OBJ bytes, terminal
history/events, signatures and branch allocations. Hash-verified resume skips
the unchanged request. No 500k run is justified or executed.

The experiment uses 75 recipe IDs and 77 attempts, including the unchanged
guard retry and Hero replay. Maximum actual output is 139,266 faces. Highest
measured driver plus process-tree resident use is 1,074,458,624 bytes; summed
worker wall time is 2,692.82 seconds. Geometry and views occupy approximately
1.02 GB locally, within the 4 GiB ceiling. The archive omits primary geometry.

### Comparative selections

| Label | Actual result | Qualification |
|---|---|---|
| BEST_BRANCHING_GRAMMAR | HERO_ROLE_ASSEMBLY | Older extrusion sides form flanking plates; inner cap rings carry smaller raised caps; upward side fins carry inner frames |
| BEST_GATE_ORNAMENT | F_A03_CONTRAST | Clear opening/supports and angular panel/rim structure; known inherited contacts remain |
| BEST_ANTI_MELT_RESULT | F_A03_CONTRAST | No terminal smoothing; strongest clear small cap/side distinction |
| MAX_ORNAMENT_CAPABILITY | HERO_ROLE_ASSEMBLY | Stable ordinary depth-four assembly, 10 terminal paths; not a collision-free certificate |
| BEST_GEOMETRIC_ORDER | F_D02_CONTRAST | Ordered DS handoff and small nested cap features; less angular contrast than A/B |
| MOST_INFORMATIVE_FAILURE | F_B05_CONTRAST | Stronger older-flank taper reaches the 30-contact diagnostic cap at Stage 6; no later growth |

Family B provides the most useful larger local departure: original extrusion
sides become flanking plates instead of recursively repeating only the inner
cap. A gives the clearest angular micro contrast. Their combination with a
quiet downward-side branch forms the Hero. Broad orientation and exact depth
gates diversify siblings; orientation alone is subtle at whole-gate scale.
Quiet pruning makes local activity easier to read, but all-quiet output and
uniformly reduced activity do not establish hierarchy.

The Hero has 10 terminal nonempty signatures (14 generated including consumed
paths), 22.28% dominant ornament face mass, depth 4, 96 independent nested event
components and 12 source C0 faces supporting multiple paths. A03_CONTRAST has
7 terminal paths and 32.65% dominance; D02_CONTRAST has 8 and 44.97%. These
figures do not establish visual diversity alone: original C07 has 5 and 23.53%.
The Hero's two visibly different descendant relationships are cap ring to
smaller raised cap and side fin to inner frame, alongside larger lateral plates.
They remain confined to the recurring four-window/panel seed. Increasing depth
added real differing local actions, but did not create a new larger assembly.

**No GROTESQUE_GATE_CANDIDATE or clearly stronger near-candidate is designated.**
The single strongest remaining structural limitation is that differentiated
descendants remain confined to repeated parent-face cap/frame cells; the tested
grammar does not organize distinct branching assemblies beyond those seeds.
This is a result of the tested grammar, not a claim that the entire external
operator library cannot support other morphology. Existing Rhino modes remain
unchanged; the conditional new mode is not added. Actual Rhino-host behavior
is **NOT TESTED**. All presented geometry comparisons are headless.

The tracked [whole](../studies/task20/evidence/C07_vs_HERO_oblique.png) and
[detail](../studies/task20/evidence/C07_vs_HERO_detail.png) pairs use exactly the
same registered camera and scale. The review ZIP includes all primary sheets,
finalist role/depth/wire views and nine-result C0/C07/C06/B03/selection sheets.
The explicit A-I assessment of each finalist is in
`studies/task20/evidence/finalist_visual_review.json`. It is an assessment of
actual projected geometry, not a user review or a Rhino-host verification.

### Where smoothing loses detail

All three matched finish inputs are exactly hash-equal to their retained
no-finish candidates. One saved standard DS stage preserves constructive depth
and signature counts, but rounds the distinct small structures. Prefer the
no-finish result in all three comparisons.

| Same-input comparison | Faces before / after | Mean edge before / after | Mean adjacent normal angle before / after | Visual verdict |
|---|---:|---:|---:|---|
| A03_CONTRAST + one DS | 19,840 / 79,362 | 37.57 / 17.54 | 44.45 / 24.36 degrees | Raised cap rims and side frames round toward the same panel language |
| B05_WIDE_CAP + one DS | 15,344 / 61,378 | 46.12 / 20.75 | 45.37 / 21.70 degrees | Flanking plates survive but small rings lose contrast |
| D02_CONTRAST + one DS | 34,818 / 139,266 | 26.96 / 13.28 | 9.56 / 5.64 degrees | Smoother coherence, weaker tiny cap articulation; no hierarchy gain |

Exact additional rounding begins at `terminal_DS`: Stage 10 for A03_CONTRAST,
Stage 9 for B05_WIDE_CAP and Stage 9 for D02_CONTRAST. No metric is a stand-alone
visual score: normal variation also changes when the mesh is sampled more finely.

The clearest CC melt is A08/F_A08, `terminal_CC`, Stage 8: 12,160 to 48,640 faces,
mean adjacent normal angle 48.70 to 18.32 degrees, 1,508 opposed-fan and 1,666
bilinear warnings after finishing. Raised frame edges become rounded lenses.
B06's `inter_CC`, Stage 8, already rounds branched thin faces and creates 2,308
fan warnings before its later event, despite FINISH_NONE. Frozen C07 Stage 4
already rounds the broad mass; later D-family global DS handoffs round its meso
panels. There is no universal single melt stage; these named checkpoints locate
the observed changes. Stronger taper is also not a remedy: B05_CONTRAST stops
at `older__flank`, Stage 6, after its actual height 0.26/fraction 0.22 event.

### Gate and geometric limits

The monitor below is the existing read-only source-corner descendant landmark
approximation. It is not exact unobstructed clearance, a shape constraint or a
design score. Whole views retain a visible opening, paired supports and a lintel.

| Monitor | Hero | A03_CONTRAST |
|---|---:|---:|
| Opening W / source opening W | 1.00404 | 1.00015 |
| Opening H / source opening H | 0.80956 | 0.81999 |
| Opening center Z drift / source opening H | +0.05864 | +0.06251 |
| Opening center X drift | approximately zero | approximately zero |
| Overall W drift | +12.62% | +12.59% |
| Overall H drift | +13.16% | +13.16% |
| Overall D drift | +119.41% | +119.41% |
| Support-base displacement / source overall H | +0.12937 | +0.12937 |

Both preserve left/right landmark order and lintel-above-support relation; the
substantial depth growth and ground drift are real inherited macro effects.
The detailed monitor records are in the bundled `selections.json`.

Hero, A03_CONTRAST and D02_CONTRAST are finite, valid, closed, manifold, one
component, with zero boundary edges, zero degenerate fan faces and zero terminal
fan/bilinear warnings. Their terminal transverse-contact samples are 0 / 0 / 0.
However A03 retains **all 12 known unchanged Stage-5 contact pairs**. Hero and
D02 retain zero unchanged pairs because those regions change; this does not
prove the changed geometry globally collision-free. The three DS finishes give
5 / 7 / 0 sampled contacts respectively. The stopped aggressive flank gives 30.
Warnings and narrow sampled-zero results remain visible in all comparison tables.

### Verification and delivery

Focused branch/ornament checks pass: 15 tests. The final complete suite reports
**751 passed in 29.00s**; `git diff --check` and the first-party distribution
audit pass. The initial full invocation had 750 passes and one existing identity
test failure: a repository-local temporary root made a fixture intended to
represent an outside CHESHIRE package fall inside the repository. A focused
rerun using the permitted external temporary root passed. The full suite was
then repeated with the corrected temporary root; no assertions, production
identity checks or tests were weakened. Both full logs and the reason for this
necessary repeat are retained. No suite is run per design recipe.

Python 3.12.10, COMPAS 2.15.1 and the existing official HDMola 1.0.0/CoreCLR
environment remain unchanged. No external binary or upstream implementation is
included in Git or the review archive. The experimental branch delivery commit,
remote ref verification and archive size/hash are recorded after commitment in
the ZIP's `output/task20/delivery_record.json` and the final response.

For a fresh source checkout, initialize a new output study with the command
above. To reproduce a delivered finalist/Hero, serialize its entry from
`studies/task20/recipes.json` into that study's `recipes/<ID>.json`, then run
`--phase REPLAY --run <ID> --dll <official-HDMola.dll>` with `--study` pointing
to the same fresh directory. The main review archive already contains those
individual recipe files and all real reference geometry. Old Task-19 output is
optional for reference views, never required to regenerate the frozen prefix.

Naming correction: executed IDs ending `WIDE_CAP` were mislabeled. Their actual
serialized taper fraction is 0.48, so Mola retains 52% of the parent radial size,
versus 70% at fraction 0.30. They are stronger-taper/smaller-top comparisons.
The executed IDs/values/requests remain intact; future recipe generation uses
`STRONGER_TAPER`. No geometry is changed to conceal this naming error.
