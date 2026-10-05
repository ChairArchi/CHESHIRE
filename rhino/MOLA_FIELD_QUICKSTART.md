# MolaFieldStudy: heterogeneous, cap-only G1/G2/G3

In Rhino 8 ScriptEditor / Python 3, run `rhino/CHESHIRE_Run.py` on the UI thread, select the **original existing Mesh**, and choose **MolaFieldStudy**. The existing MeshGrammar and MolaTaperStudy modes remain available. No previous output is selected automatically. All eligible planar convex triangles/quads participate; excluded original faces keep their geometry and appear magenta in driver previews. No repair, remeshing, smoothing, randomness, new operator or dependency is added.

The exact standalone Mola DLL path is saved once in ignored `output/local_settings.json` as `mola_dll_path`. If valid, both Mola modes reuse it automatically. If missing/invalid, the existing text input asks once. Choose **SetMolaDllPath** to replace it explicitly (after mesh selection; no study is launched), or edit that local preference. The DLL must stay outside CHESHIRE. Neither the preference nor DLL is committed or included in review bundles. The existing lazy Python.NET/CoreCLR .NET 8 loader and environment isolation stay in use.

Two separate fields are computed **only on eligible original face arithmetic centroids**:

- **Height driver:** normalized world Z, clamped to `[0,1]`; `original_height_ratio = 0.05 + 0.30 * height_driver`.
- **Taper driver:** normalized centroid distance from the original input bounding-box center in the XZ plane; `original_fraction = 0.15 + 0.60 * taper_driver`.

An effectively zero eligible range maps to `0.5`, with a constant-field notice for either driver. The threshold is the greater of `1e-9 * input bbox diagonal` and `2e-15 * largest absolute input coordinate`; it is recorded with bounds/centroids/distances in response metadata. No percentile clipping or combined ornament score. These are deterministic synthetic geometric controls with no architectural or cultural meaning.

| Generation | Selected parents | Height scale | Fraction |
| --- | --- | ---: | --- |
| G1 | Eligible original faces | 1.00 | Original mapped fraction |
| G2 | Only G1's newly generated caps | 0.65 | `clamp(original_fraction + 0.10, 0.05, 0.85)` |
| G3 | Only G2's newly generated caps | 0.40 | `clamp(original_fraction - 0.05, 0.05, 0.85)` |

Every call uses the real `FaceSubdivision.ExtrudeTapered` with a top cap. Actual height is `original_height_ratio * sqrt(current_selected_face_area) * height_scale`. Current cap areas are measured afresh, not inferred from old/idealized areas. Parent faces are replaced. Earlier side faces are retained and never recursively selected. New sides/caps have explicit role and generation; complete immediate lineage and inherited root-face IDs carry the two original drivers and original parameters across generations. Geometry areas are marked RECOMPUTE and measured explicitly.

Display shows **ORIGINAL REFERENCE**, **HEIGHT DRIVER**, **TAPER DRIVER**, and each reached **G1/G2/G3**, with TextDots. Driver colors are flat per original face: black low, white high, magenta excluded. Only driver display corners are duplicated to avoid averaging adjacent face values; calculation topology and lineage stay unchanged, with original vertex IDs recorded on the preview. All copies keep scale/orientation and translate only along world X. Use Shaded mode to see colors. Original fingerprint checks, one Undo insertion, Esc cancellation, 60-second timeout and rollback remain active.

The worker reports eligible/excluded originals, processed faces/caps, both driver ranges, actual heights/fractions, input/output counts, budget status and elapsed time for each generation, plus the five original faces with greatest actual G1 height. Full request, driver values, parameters, root fields, role/generation records, lineage, backend identity and diagnostics remain in unique ignored `output/task10/<run_id>/` directories. A later failure/excessive generation stops before execution and preserves completed generations as PARTIAL. A constant or effectively uniform control is reported as visually weak rather than ornament success.

Validated intermediate checkpoints are also displayable if the worker times out/exits before final reporting. The original-driver assessment is available from the first checkpoint; older checkpoints without optional descriptive metadata still insert valid geometry. Command history explicitly reports the last completed generation, and its TextDot is marked **last valid; PARTIAL**. Geometry validation is unchanged. To verify in Rhino, run `rhino/CHESHIRE_Run.py` and choose **MolaFieldStudy**: expect original reference, height/taper driver previews and G1/G2/G3, or just the reached generations ending in the PARTIAL label.

Limits are unchanged: **5,000 original faces / 20,000 original vertices; 1,000 selected parents per generation; 50,000 faces/vertices per result; three generations; 60 seconds per worker**. The one-pass adapter's `source_is_result=True` applies existing result limits to previously validated G1/G2 meshes rather than mistakenly applying original-input limits again. It does not raise the result budget. Numerical cap nonplanarity or float32 collapse can stop recursion; no tolerance relaxation or projection is performed. No global collision/intersection or fabrication-readiness claim.

For a small real-worker vertical control, after configuring the DLL locally:

```powershell
.\.venv\Scripts\python.exe examples\mola_field_study.py
```

Use `--dll "<absolute official DLL path>"` once if not configured. To explicitly replay a retained **original request**, use `--input-request "output/task09/<your_run_id>/request.json"`; do not pass a response/generated stage. The smoke retains actual `G0.obj`, reached `G1.obj`/`G2.obj`/`G3.obj`, `drivers.json`, response and stdout/stderr. It is headless evidence, not a Rhino host run.

Task 09's gate selection/calculation/insertion is user-confirmed working. The Task 10 worker also reached G3 on that retained original gate: G0 **1,030 / 936**, G1 **4,374 / 4,280**, G2 **7,718 / 7,624**, G3 **11,062 / 10,968** vertices/faces, processing 936 parents each time. Saved real-geometry projections show non-uniform G1 and additional cap levels in G2/G3; G3's increment is subtle at whole-gate scale. No parameters were changed to dramatize it. **MolaFieldStudy Rhino viewport/Undo/cancellation checks remain PENDING**; diagnostic projections are labeled headless and are not fabricated Rhino screenshots.

Focused tests: `tests/test_mola_field_study.py`; real-backend cases require the existing `CHESHIRE_MOLA_DLL` environment setting. Run the full suite using `.\.venv\Scripts\python.exe -m pytest -q`. See [Mola quickstart](MOLA_QUICKSTART.md) for optional installation, upstream attribution and licensing limitations.
