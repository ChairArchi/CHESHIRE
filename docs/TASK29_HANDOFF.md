# Task29 handoff

Verdict: **PARTIAL**, after the complete A–E search and a matched locking ablation.
Task29 is finished research evidence; Task30 has not started. Do not push or merge this branch automatically.

Repository: `C:/Users/USER/CHESHIRE`.
Task28 baseline: `a9e456fcc7711ae5920457c49890bc28aa045f1d`.
Branch: `experiment/task29-reference-generative-search`.
Exact Task29 local commit: external `analysis/repository_commit.json` and `git log -1` on this branch.
Canonical artifact root: `E:/CHESHIRE_DATA/task29/`.

## Read and view first

1. `FINAL_REPORT.md` and `analysis/FINAL_DIAGNOSIS.md`.
2. `renders/FINAL_LEAD_PROGRESSION.png`, then `lead_details.png`.
3. `renders/rule_contribution_isolation.png`: first row has the same base rows and cube;
   intrinsic-only vs intrinsic-plus-locks differs only in the lock threshold's presence.
   Second row has the same intrinsic D00_3 lineage without/with a single G4 weld.
4. `renders/mechanism_matrix.png` and all paged A/B/C/D/E sheets.
5. `analysis/reference_equation_audit.md` and `definitions/selected_nonstationary_schedule.json`.

G1 macro and G2 meso remain visible. Small intrinsic variation starts G3, but fine patterns stay strongly
cell-related; dense angular clusters persist. Do not call this Digital Grotesque reproduction or reference-level SUCCESS.
At G8 there are 393,218 vertices, 393,216 original quads, and a 37.83-degree median adjacent normal angle.
The reference operator fixes legacy coupling, but that correction alone did not produce the requested hierarchy.

## Implementation boundaries

`src/cheshire/reference_subdivision.py` is the new opt-in array operator for closed oriented triangle/quad meshes.
`weighted_subdivision.py`, `generational_subdivision.py` and `sharp_subdivision.py` are unchanged legacy paths.
The reference dependency is completed Eq1/4→Eq10 faces, those faces→Eq2/3;
Eq3 uses original endpoint midpoints. Eq11 edge extrusion does not feed the same-iteration vertex mask.
Read the audit's Figure 2 justification and explicit attraction-order/scalar-normal conventions.

Every lead G1–G8 uses REFERENCE_COUPLED/LOCAL_INCIDENT_SCALE. G3–G8 additionally interpolate declared
controls from current normal relationships and lock input vertices whose unscaled normal disagreement ≥0.12.
No lead weld, zero-weight cleanup, external smoothing or smooth-normal evidence.
These intrinsic rules and locks are CHESHIRE experiments, not claims of unpublished Hansmeyer code.

The array operator intentionally does not replace existing boundary/crease kernels or general polygon APIs.
It preserves point classes, positive original-cage association and G1/G2/G3 face anchors for continuation.
Current inputs and provenance feed Eq4; edited triangles/unknown provenance have explicit Eq1 fallback.
`examples/task29_topology.py` is one experimental threshold join, with real pre-weld states and rejection logs.
Three of 24 proposals change connectivity validly; thirteen do nothing, eight are invalid. No valid new genus.

## Replay actual lead, preserving evidence

Use this repository's `.venv/Scripts/python.exe`. The saved definition has round-trip decimal values;
do not retype rounded report weights. `mesh.npz` stores xyz/faces/classes/rest/anchors/generation.
`operator_state.npz` stores exact per-step scale fields, ancestry mappings, intrinsic signal and lock mask.
`summary.json` includes declared/effective mode, base row, parent path/hash and measured geometry diagnostics.
`lead/lineage_manifest.json` identifies each original saved candidate. Copied lead files are the actual stages.

The following read-only replay works without rerunning the broad search or changing saved meshes:

```python
import json
from pathlib import Path
import numpy as np
from cheshire.reference_subdivision import cube, subdivide

root = Path('E:/CHESHIRE_DATA/task29')
definition = json.loads((root / 'definitions/selected_nonstationary_schedule.json').read_text())
m = cube()
for g in range(9):
    if g:
        m, meta, state = subdivide(m, definition['rows'][g-1],
                                  scale_mode=definition['scale'], intrinsic=definition['intrinsic'])
    with np.load(root / f'lead/G{g}/mesh.npz') as z:
        for name in ['xyz', 'faces', 'classes', 'rest', 'anchors']:
            assert np.array_equal(getattr(m, name), z[name]), (g, name)
        assert m.generation == int(z['generation'])
```

Reload continuation using `task29_search.load_mesh(root/'lead/G7')` with the tools/examples paths on `sys.path`,
then call `subdivide` with row8 and the same intrinsic rule; it reproduces G8 exactly.
`tools/task29_evidence.py --verify-export` repeats exact full regeneration, state checks, OBJ write/reread
and actual checkpoint continuation. It rewrites only the exact per-stage OBJ exports and proof JSON,
not meshes; keep the existing proof when simply reviewing evidence.

## Search provenance and counts

480 base search definitions: A256, B128 from 32 A finalists×4, C8, D32+32, E24.
Three matrix controls, eleven existing-variant G8 extension records, and one exact locking-ablation control
give 495 executed definition records and 20 real G8 lineages. 1,346 actual generation checkpoints
exclude G0 and copied lead duplicates; rejected proposals retain pre-weld files rather than a fabricated continuation.
The raw A log is `analysis/round_A_log.json`; the aggregate `broad_search_log.json` links every phase.
All named individual definitions and operator states are retained externally.

The original first-stage commands below create new directories and intentionally refuse candidate overwrites.
They are provenance commands for a fresh artifact root, not a command to run over the completed tree:

```powershell
.venv/Scripts/python.exe examples/task29_search.py --prepare --matrix --tag prep_matrix
.venv/Scripts/python.exe examples/task29_search.py --round-a --tag round_A
.venv/Scripts/python.exe tools/task29_select.py --b
.venv/Scripts/python.exe examples/task29_search.py --continue-file E:/CHESHIRE_DATA/task29/definitions/round_B_selection.json --category round_B --tag round_B
```

Later choices live in `definitions/round_C_selection.json`, `intrinsic_selection.json`,
`intrinsic_retention_selection.json`, `topology_selection.json`, `intrinsic_late_selection.json`,
`final_followups.json` and `lock_ablation_selection.json`; inspect exact filenames in the manifest.
Supply those to the same `--continue-file/--category/--tag` worker using a fresh root when regenerating the search.
Some extra experiment selection files were prepared directly during the sprint; their exact JSON is authoritative.
Task30 may parameterize the hard-coded experiment root; no directory relocation or API consolidation was performed now.

## Tests and native files

838 applicable tests passed, zero skipped; optional HDMola was actually loaded:

```powershell
$env:CHESHIRE_MOLA_DLL='C:/Users/USER/Libraries/HDMola/1.0.0/HDMola.dll'
$env:PYTHONNET_RUNTIME='coreclr'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp C:/Users/Public/Documents/ESTsoft/CreatorTemp/task29_backend_validation_FRESH
```

Choose a new external temp directory: the existing worker-identity negative test assumes tmp_path is outside
the repository, and pytest owns/replaces its basetemp. Do not reuse or remove someone else's temp directory.
Raw successful and setup/fixture-failure logs are saved under `test_logs/`.
The new focused files verify scalar equation fixtures, cancellation/propagation, neutral CC, deterministic
intrinsic fields, actual lock masks and safe topology rejection; they do not test artistic success.

Final OBJ and 3DM are `dcc/TASK29_LEAD.obj` and `dcc/TASK29_LEAD.3dm`.
Installed RhinoCommon 8.18 reread exact XYZ and oriented faces and opened the actual native file headlessly.
`dcc/TASK29_LEAD_import_evidence.json` records counts, file hashes, timings and exact processing.
Analytical sections come from the reread 3DM in `analysis/sections/TASK29_LEAD.json`.
This proves file semantics and opening, not an interactive beauty viewport or absence of self-intersections.

Native provenance command (Rhino 8 required; no visible application window):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/task29_native.ps1 -ArtifactRoot E:/CHESHIRE_DATA/task29 -ObjPath E:/CHESHIRE_DATA/task29/dcc/TASK29_LEAD.obj -Name TASK29_LEAD
```

The stored lead's original quads and double coordinates are retained. Display rendering alone splits quads
on diagonal0–2 and uses float32; error, camera matrices, physical width, clipping and source/image hashes are logged.
All judgment uses flat normals. Intentional detail crops differ from unclipped fixed-scale progression.

## Deliverables and Task30

`CHESHIRE_TASK29_REVIEW.zip` includes all saved experiments, images, definitions, diagnostics,
checkpoints, final model and exact source snapshot. `MODEL.zip` is the smaller lead/continuation/native package.
`analysis/file_inventory.json` and `analysis/archive_validation.json` record payload hashes and actual ZIP checks.
The reference paper itself and installed third-party binaries are not distributed in these packages.

Use `docs/TASK30_CONSOLIDATION_PLAN.md`. Keep evidence and legacy compatibility; do not erase experimental
failures. Resolve artistic limitations as explicit open limitations, rather than disguising them with renamed APIs.
