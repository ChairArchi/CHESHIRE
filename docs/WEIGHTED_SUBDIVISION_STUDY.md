# Weighted subdivision study (Task 14)

The attached request is titled Task 14. No separate Task 15 specification was
included. This experiment implements one **CHESHIRE Extended-CC Experimental
Subset**, not Digital Grotesque or an exact Hansmeyer application.

See [the equation and assumptions note](WEIGHTED_SUBDIVISION_REFERENCE.md).
Existing subdivision, Mola, field inheritance and Rhino modes retain their
behavior; no dependencies or budgets change.

## Inspect in Rhino

Run `rhino/CHESHIRE_Run.py` in Rhino 8 ScriptEditor, Python 3, on the UI thread.
Select the ORIGINAL mesh and choose **WeightedSubdivisionStudy**. No Mola
DLL is needed. The isolated repository worker compares S (zero weights), U
(fixed attenuated generation schedule), and F (the same schedule with separate
source Z/extrusion and current normal-variation/interpolation drivers).
It displays ORIGINAL and completed S/U/F G1/G2 at the same scale, with X offsets.
Existing timeout, Esc cancellation, source fingerprint, Undo and rollback apply.
Full semantic lineage is **NOT IMPLEMENTED**; topology/source associations and
positive control-cage sampling records are provided separately.

Actual Rhino-host validation is **PENDING**. A real external worker on the saved
gate and a mocked partial insertion check passed; neither is a Rhino-host check.

## Reproduce without Rhino

Use a new destination; existing attempted case folders are never overwritten:

```powershell
.\.venv\Scripts\python.exe examples\weighted_subdivision_study.py --directory output\task14\reproduce --source small
.\.venv\Scripts\python.exe examples\weighted_subdivision_study.py --directory output\task14\reproduce --source gate --input output\task14\study\gate_source.json
.\.venv\Scripts\python.exe examples\weighted_subdivision_study.py --directory output\task14\reproduce --views
```

Exact schedules live in `rhino/weighted_study.py`. A case can be reproduced
with `--one NEW_FOLDER --source small --kind U --recipe attenuated --generations 6`.
For the gate use `--source gate --input SAVED_SOURCE_JSON --generations 2`.
S always uses zero weights, independent of the ignored recipe argument.

Each case retains G0..Gn OBJ/JSON, full compressed records, separate driver
values, exact effective point weights, source associations, counts/bbox/timing,
fan diagnostics, and a bounded crossing audit. OBJ reload checks actual ordered
coordinates and face cycles, not counts alone. Batch workers are serial and
bounded to 60 seconds/4 GiB with the existing available-memory floor. Direct
`--one` is a single-process diagnostic; geometry count/generation budgets still
apply. Diagnostic projection uses the existing System.Drawing tool.

## Observed result and limits

The six-face column reached G6: **24,578 vertices / 24,576 quads**. Most exploratory
recipes were stopped deliberately at G5 (6,146 / 6,144). The exact original gate
is 1,030 vertices / 936 faces (400 triangles, 536 quads), with 10 open components.
S/U/F G2 each have **14,522 vertices / 13,376 quads**, still 10 components and
2,272 boundary edges. G3 would exceed the unchanged 50k ceiling.

Uniform ribs on the gate had **28 sampled transverse crossings**. It is retained
as a problematic exploration, excluded from the default mode. Strong column
recipes also show opposing diagnostic fan normals (fold/pinch warning), without
sampled non-adjacent crossings. The default attenuated S/U/F comparisons have
zero sampled crossings and no degenerate/opposed diagnostic fans.

The new mechanism produces corrugation and changes intermediate forms, but the
gate still reads mostly as repetitive surface relief. F visibly reduces detail
at low source Z and retains stronger articulation toward the crown. This is
explainable spatial modulation, not convincing broad grotesque-like hierarchy.
No branching, new holes, exact fractal, fabrication or collision-free claim.

All views are fixed-camera headless polygon projections with common bounds,
light and registered crops; wireframes include back-facing edges. They are
approximate evidence, not Rhino screenshots. The bounded crossing diagnostic
excludes adjacent-face/coplanar contacts; zero is not a global guarantee.
Task 13's static outputs remain intact. Its old execution hashes correctly
require the Task 13 baseline checkout for replay after this source change.
