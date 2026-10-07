# Task26 preserved-state handoff

Read `TASK26_STOP_HANDOFF.md` before resuming. Task26 new mesh experiments were
stopped when the user supplied Task27's safe-start instruction. Task27 did not
start because there was no preservation commit or stop handoff at that check.
Only existing-file verification, reporting and preservation continued.

Baseline is `b4000cf85bc0768821976bab4b454ca35b8ccca3`; branch is
`experiment/task26-progressive-gates`. The actual preservation SHA is recorded
in the stop handoff after committing and in external `release.json`. Check
actual Git ancestry and working-tree status; do not assume HEAD is the intended
baseline. Never reset, clean or overwrite the preserved branch or external data.

## Files to inspect

`E:/CHESHIRE_DATA/task26/FINAL_REPORT.md`, `stage_manifest.json`, `release.json`
and `deliverables.json` describe the preserved package. Read their actual
status; no absent artifact should be treated as delivered. Recipes are in
`recipes/`; previous forecast-stop attempts and superseded renders remain.
Source hashes in requests and the generation snapshot identify the code that
actually ran. The older module snapshot differs by a comment-only orientation
correction from the current file; do not silently replace it.

Retained whole-gate model: `LEAD_BALANCED_G7`, attempt_002, generation 7,
1,245,184 quads. Its OBJ, keyed geometry, state, operator, request, summary and
preflight are in `designs/LEAD_BALANCED_G7/attempt_002`. Native file is
`dcc/LEAD_BALANCED_G7.3dm`. All useful parent checkpoints and OBJs remain in
their own input/design directories. Final camera-linked views are in
`renders/lead` and `renders/progression_selected`; shared-parent G7 comparisons
are in `renders/balanced_comparison`.

The native file is one original-coordinate mesh on
`TASK26_LEAD_BALANCED_G7`, named `LEAD_BALANCED_G7_FULL_RESOLUTION`. Units are
None. Open in Rhino 8 and use Zoom Extents; no unit conversion is appropriate
without new evidence. Actual native read/headless open succeeded; the neutral
captures are separate OpenGL renders, not an interactive Rhino capture.

## Source and state

`src/cheshire/progressive_gates.py` builds matched shared-ring cages, transports
material XYZ and constructive vertex/face reflection maps, resolves physical
support and verifies oriented symmetry. `examples/progressive_gates.py` saves
one actual whole-gate CC/fold generation per recipe and wraps existing RAM
guards. The existing fold API gained optional per-vertex point support; absent
support keeps the old behavior. The optional measured-total memory prediction
subtracts already-resident worker memory only once.

The final full state retains complete face history/source cells/signatures,
current structural point origins, actual networks/sharpness, semantic parts,
material coordinates, constructive reflection pairs, generations, completed
recipes and recorded metadata corrections. Load keyed geometry together with
`load_state` plus `restore_gate`. OBJ alone does not retain this continuation.
Do not re-fit generated geometry to input rings or mistake material XYZ for
deformed geometry.

Task26's parts describe a continuous swept U. They do not yet supply Task27's
separate vertical/horizontal member-length and circumferential coordinate rules.
The auxiliary profile waist/bulge is deliberately authored in the input, and
the selected lead does not descend from that profile input.

## Reproduce or continue only when requested

Use existing Python 3.12.10/COMPAS 2.15.1 environment. Large runs are sequential
and memory guarded. For a new recipe ID, set its parent to an actual saved
successful checkpoint; `--run` saves a new attempt and actual request hashes:

```powershell
.\.venv\Scripts\python.exe examples\progressive_gates.py --output-root E:/CHESHIRE_DATA/task26 --run NEW_RECIPE_ID
```

Do not run this placeholder without first creating the intended recipe.
For a fresh reproduction, use a different root, run `--initialize`, copy the
preserved exact recipes, and run the selected parent chain listed in RESULTS.
Before high-resolution G7, run `--calibrate` against that fresh run's actual
process records. Its existing same-level calibration references original
process-file hashes and must not be copied and presented as fresh measurement.
Use a newly calibrated recipe rather than lowering the live RAM guard.

Installed review extras are pinned in `pyproject.toml`. Capture existing states:

```powershell
.\.venv\Scripts\python.exe tools\progressive_gate_views.py --output-root E:/CHESHIRE_DATA/task26 --names LEAD_BALANCED_G7 --tag NEW_CAPTURE_TAG --views front oblique underside detail detail_angle mantle detail_wire --resolution 1800
```

Use a new tag to preserve existing views. Wrap large utilities using the
existing `hero_design_sprint.guarded` process-tree guard as done in logs.
`progressive_gate_native_monitor.py` similarly guards Rhino export and refuses
to overwrite its existing native-run log.

Official local optional test dependency is
`C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll`; use CoreCLR and do not bundle
the DLL. Full test log: `output/task26_pytest_final.txt` (803 passed).
Focused post-guard-change log: `output/task26_targeted_final.txt` (6 passed).
Run tests outside the repo for basetemp because artifact-identity tests inspect
repository contents. New changes justify new relevant tests; do not claim a
full 804-test run from the existing two logs.

## Design status

See RESULTS for the exact comparisons, revisions, numbers and distinctions.
The retained surface has coherent broad bulk but still granular fine relief;
status is PARTIAL for multi-scale folding, with successful execution/export/
depth-correct visual evidence. Its closed topology does not imply absent
intersections, a thick printable volume or engineering validation.

No Task27 input, output folder, experimental branch or generated model was
created. The next run must independently confirm the documented preservation
commit and safe process termination before applying the profile-first brief.
