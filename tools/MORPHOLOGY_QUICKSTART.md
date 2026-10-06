# Bounded morphology study

Run these commands from the repository in Windows PowerShell, using its existing `.venv`. This study reuses the saved Task 12 original gate and ignored official DLL preference. It installs nothing and never touches an open Rhino document.

The delivered atlas is in `output/task13/study/atlas/index.html`, with `output/task13/study/START_HERE.md` as its reading guide. The initialization example below uses a different directory name; choose a fresh name rather than overwriting a retained study. To reproduce a delivered candidate, use `--study output\task13\study --candidate <id>` while the recorded implementation/runtime still match.

```powershell
.\.venv\Scripts\python.exe -E -s tools\morphology.py --study output\task13\overnight --init --source output\task12\8c5ff45c-7810-455d-a4ba-c1339c67eccd\request.json --baseline-response output\task12\8c5ff45c-7810-455d-a4ba-c1339c67eccd\response.json
.\.venv\Scripts\python.exe -E -s tools\morphology.py --study output\task13\overnight --phase baseline
.\.venv\Scripts\python.exe -E -s tools\morphology.py --study output\task13\overnight --resume --phase screen
```

Initialization writes all 27 initial candidate files before any geometry runs. A/B/C are dispatch IDs; A001 etc. identify immutable experiments. Append explicit JSON rows with `--append path/to/additions.json`; each row includes its reason, changed parameters, full recipe and hash. Combined variations are limited to 12. Repeat rows name `repeat_of`. A changed recipe requires a new ID. `--candidate B008` runs a fresh reproduction of that retained recipe, checks its deterministic output, and preserves the earlier result. Every worker/replay counts toward the hard 60-worker ceiling.

```powershell
.\.venv\Scripts\python.exe -E -s tools\morphology.py --study output\task13\overnight --candidate B008
.\.venv\Scripts\python.exe -E -s tools\morphology_atlas.py --study output\task13\overnight --representatives A000 A011 B000 B008 B010 C000 C010 C011
```

For the delivered selection and its small mask/accent measurements, use the retained notes:

```powershell
.\.venv\Scripts\python.exe -E -s tools\morphology_atlas.py --study output\task13\study --representatives A000 A007 A011 B000 B008 B009 B010 C000 C010
.\.venv\Scripts\python.exe -E -s examples\morphology_review.py --study output\task13\study --representatives A000 A007 A011 B000 B008 B009 B010 C000 C010 --recommendations A011 B009 C010 --notes output\task13\study\notes.json
```

The review script performs postprocessing only and records its own source hash separately from the immutable execution-tree hash. It compares actual C masks on the identical Quad1 source and A coordinate differences against A007 before/after CC; retained-point measurements are not semantic CC lineage. Some outputs exceed Task 12's exact whole frame. Primary frames/crops remain unchanged; supplementary context sheets add the same fixed 5% margin for every output, without fitting individual candidates.

Resume requires identical source, runtime, every recipe, and implementation files including the runner/audit/projection tree. Run IDs and timings are excluded from deterministic output checks. The original mesh is copied afresh for every candidate; no welding or coordinate conversion occurs. `quad_levels`, `cc_levels`, `side_directions` and `maximum_sides_per_parent` describe fixed behavior and cannot be swept. The Boolean `study_cap_only` is a B-only experimental control; omitted means the exact Task 12 perimeter rule. Widths, periods, centers, radii and slope use original normalized coordinates; displacement strength scales by each step's bbox diagonal; Mola height ratios scale by current face area. Model units are unconfirmed unless source metadata supplies them.

Only one geometry/audit process runs at a time. Workers use the explicit venv executable, sanitized environment, `-E -s`, explicit cwd and `shell=False`. Existing backend preflights enforce 5,000/20,000 original face/vertex limits, 1,000 Mola selections, 50,000 output vertices/faces and unchanged family order. Workers stop after 60 seconds. A validated earlier checkpoint remains **PARTIAL**. Place a `STOP` file in the study directory to stop between candidates; remove it before `--resume`. Resource stops preserve records and require investigation. New study storage is capped at 3 GiB. Windows physical memory/working sets enforce combined resident <= min(4 GiB, 25% RAM), available >= max(2 GiB, 15% RAM), where measurable. Experiments cut off at 2.5 hours; atlas work has the remaining half-hour of the three-hour ceiling. The ceiling is never a runtime target.

Responses are compressed without losing geometry, fields, roles or lineage. Actual output OBJ, diagnostics and summaries remain in ignored `output/task13`. A terminal CC derivative has semantic lineage **NOT IMPLEMENTED**; its pre-CC record stays intact. The reused Task 12 crossing check is fixed, serial and bounded to 30 seconds per audit. It excludes adjacent/coplanar/edge-only contacts and stops after 30 transverse face-pair crossings. Zero sampled crossings does not certify global collision freedom.

Open `atlas/index.html` offline. Contact sheets include exact baselines, fixed Task 12 oblique projection/scale/lighting, registered shoulder/crown crops and clearly labeled HEADLESS geometry. Crossing candidates remain visible in a rejected group. Duplicate meshes are identified rather than counted as additional form discoveries. Use `START_HERE.md` for observations and representative records.

For Rhino inspection, create a **new disposable document** and import `atlas/ORIGINAL.obj` plus chosen `representatives/<id>/<id>.obj`. They share the same coordinates; use layers to show one at a time, keep the camera fixed, and inspect both Shaded and Wireframe. No new Rhino mode or automatic insertion is implemented. Headless checks do not verify Rhino import, display, Undo or cancellation inside the host.
