# CHESHIRE execution paths — current index, 2026-10-09

Use this index for present work. Task reports, recipes, handoffs and `studies/` snapshots
retain their research-time statements. The public COMPAS engine and later ArrayMesh
reference studies are separate supported paths; legacy operators are not replaced.

| Path | Entry | Input / output | Purpose |
| --- | --- | --- | --- |
| General mesh API | `cheshire` exports, `examples/quad_subdivision.py` | OBJ/COMPAS mesh; fields, budgets, transforms and lineage | Existing compatibility API; bounded one-step operations |
| Existing Rhino studies | `rhino/CHESHIRE_Run.py` in Rhino 8 | Existing selected Mesh → JSON → external `.venv` worker → comparison objects and `output/task*/<run>` | Host selection/display; Task31 is not a new launcher default |
| Task30 reference pipeline | `cheshire.subdivision_pipeline` | ArrayMesh, declared CC/DS steps, face roles, NPZ state | Small explicit pipeline; closed topology restrictions remain |
| Task31 regional generation | `cheshire.regional_generation` | Mesh, roles, persistent memberships, declared step and definition | Existing `birth`, `coarse_edit`, `advance`; actual multi-parent supports preserved |
| Frozen Task31 research | `tools/task31_study.py`, `tools/task31_evidence.py` | Task30 baseline + Task31 definitions/checkpoints → candidates, lead, proofs | Completed research; not a general design runner |
| Task31 rendering/native review | `tools/task31_views.py`, `task31_native.ps1`, `task31_finish.py` | Saved geometry → renders/3DM/review package | Writes research artifacts; never rerun casually in completed directories |
| Independent ALICE input | `tools/check_gate_exchange.py <NEW export> --probe-subdivision` | Canonical OBJ + manifest → validation and one bounded neutral probe | Small initial-input boundary, not Task31 continuation |

## Exact Task31 reproduction and preservation

Frozen root: `E:/CHESHIRE_DATA/task31`; baseline: `E:/CHESHIRE_DATA/task30`.
Task31 reads Task30 `definitions/final_selected_pipeline.json` (U_67_LOCK_END4).
Task31 `definitions/verified_cube_pipeline.json` and `verified_gate_pipeline.json`
bind the selected FOLD_OPEN_85 definitions to the base pipeline hash.
`lead/cube` and `lead/gate` contain G0–G8 and actual G2_post_edit.

Do not execute `task31_study.py prepare` against the completed root. Even the evidence
script's `--existing` verification path rewrites OBJ and validation/log artifacts.
Use the API into a NEW output directory for design work, or the P0 read-only hash/ZIP
verification record for preservation. This consolidation deliberately does not replay
the full five-million-face gate into its frozen directories.

Minimal continuation sequence in an isolated working directory:

1. Load the actual `mesh.npz` AND `regional_state.npz` using `task31_study.load(path)`.
2. Select the exact next Task30 step and selected Task31 definition. Do not reconstruct
   memberships from face IDs; do not replace a DS multi-parent association by one ancestor.
3. Call `regional_generation.advance(mesh, roles, members, step, definition)`.
4. At the declared birth/edit boundary use the existing `birth`/`coarse_edit` ordering,
   retaining separate G2 pre/post-edit states. Preserve wall CHANNEL memberships.
5. Save double XYZ, polygons, classes, rest association, anchors, regional state,
   actual operator arrays, parent links, source revision and exact resolved parameters.
6. Compare geometry AND state with the saved reference when replaying; an OBJ/render
   is an exchange/display artifact rather than a checkpoint.

For the short design deadline, fork low-generation states into fresh candidate directories
and keep a face/time/memory limit in the invoking runner. G8 gate has 5,021,696 faces:
do not start broad G8 sweeps just to organize code. Controlled shape variation is the
next separate design task; the frozen study's PARTIAL verdict is unchanged.

## Helpers that must remain callable

`task31_study` uses `examples/task29_search` for mesh state I/O,
`examples/cross_cell_crease_study` for record/hash helpers, and
`examples/hero_design_sprint` for guarded workers. `task31_finish` uses
`tools/task30_views` for sheets. They are not unused merely because of Task numbers.
`weighted_subdivision`, `generational_subdivision`, `sharp_subdivision`, crease/fold,
ornament/branching and gate experiments retain their separate behavior and regressions.
`examples/` is partly executable library support, not a disposable samples directory.

## Dependencies and paths

Python 3.12, COMPAS 2.15.1; install test/review/mola extras only for the corresponding path.
HDMola is an external DLL, with Python.NET 3.0.5 and .NET 8 CoreCLR. The current local
preference is in ignored `output/local_settings.json`; no DLL or environment is bundled.
`tools/task30_reference_read.py` retains its historical local PyMuPDF cache path and
Downloads defaults; the `reference` extra declares that optional PDF dependency for
a fresh environment. Do not run this import-executing historical script as a checker.

New input checks accept explicit paths. Historical Task29–31 roots stay unchanged for
replay; portable `ArtifactRoot` remains available without rewriting frozen recipe paths.
`docs/` provides current guidance, `studies/` provides immutable snapshots, `output/`
and E:/ hold actual run artifacts and local tools. `output/` is not wholesale cleanup.

```powershell
$env:CHESHIRE_MOLA_DLL = 'C:\Users\USER\Libraries\HDMola\1.0.0\HDMola.dll'
$env:PYTHONNET_RUNTIME = 'coreclr'
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --basetemp C:\Users\Public\Documents\ESTsoft\CreatorTemp\cheshire_tests_NEW
```

Actual Rhino UI/Undo/cancellation checks remain distinct from headless/native/unit tests.

## Task33: deep-fold research

The opt-in `tools/task33_research.py` path uses the original Task31 RECT G0
carrier, finite material-coordinate folds, native pre/post checkpoints and
the existing measured-RAM worker guard. It supports this carrier only; it is
not the arbitrary-mesh API or a Rhino launcher default. Task01–32 source and
frozen recipes are unchanged. [Results](TASK33_RESULTS.md) and
[diagnosis](TASK33_DIAGNOSIS.md) distinguish measured facts from hypotheses.

```powershell
.\.venv\Scripts\python.exe -B tools/task33_research.py --action run --request studies/task33/definitions/depth_binding_gate.json --tag MY_NEW_GATE
```

Every tag must be fresh. Outputs go to `E:/CHESHIRE_DATA/task33`; the runner
refuses an existing candidate/log directory. The request declares when macro,
meso and fine scales start. Each important refinement/reconstruction writes
native mesh, operator, material chart, fold controls, ancestry and SHA-linked
parents. `--action measure/evidence/planar/progression/tracks/export` takes a
small JSON request such as `{"candidate":"MY_NEW_GATE"}` and a fresh tag.
`audit` and `render` take explicit item/stage requests; examples are preserved
in the external Task33 `definitions` directory. Full validation and an
explicit mirrored triangle checkpoint precede the separate `deliver` OBJ
exchange. Native checkpoints remain authoritative for replay.

The reference `nested_notch_control.json` retains constant longitudinal fold
height; `strong_binding_ablation.json` is an aggressive comparison, not the
recommended starting recipe. Fine amplitude may not exceed meso amplitude in
notch mode. No remote publishing or repository/package rename is involved.
