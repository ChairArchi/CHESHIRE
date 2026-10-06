# MolaSurfaceStudy: recursive relief versus one Catmull-Clark level

In Rhino 8, restart Rhino after updating previously imported CHESHIRE modules. Open **`rhino/CHESHIRE_Run.py`** in ScriptEditor / **Python 3**, run on the UI thread, select the **original existing Mesh once**, and choose **MolaSurfaceStudy**. The existing modes and remembered external Mola DLL preference remain available. No installation or changes inside Rhino/Grasshopper are needed.

This mode runs [MolaFieldStudy](MOLA_FIELD_QUICKSTART.md) unchanged, then compares **G1 RAW / G1 + CATMULL-CLARK 1** and **G3 RAW / G3 + CATMULL-CLARK 1**. Its five comparison meshes include **ORIGINAL REFERENCE**. Only completed geometry is inserted; unavailable/blocked CC variants are reported in command history and on their raw comparison labels. Copies use identical model units, orientation and calculation coordinates, with **world-X-only display offsets**. Unique run layers, TextDots, original fingerprints, one Undo insertion, rollback and Esc cancellation use the existing launcher. Switch between Shaded and Wireframe manually; normals are recomputed normally and no global display mode or material is changed.

Each derivative is an independent geometry-only copy using COMPAS **2.15.1** public `mesh.subdivided(scheme="catmullclark", k=1, fixed=boundary_vertices)`. Local inspection of `mesh_subdivide_catmullclark(mesh, k=1, fixed=None)` confirmed that fixed vertices bypass smoothing and nonzero input edge creases keep edge points at the split midpoint. Only naked boundary edges receive **crease 2**, which decrements to 1 on their child edges. Ordinary interior edges/vertices smooth normally. All original boundary vertices stay fixed; every original boundary segment becomes two boundary edges meeting at its original midpoint. No welding, angle-based crease assignment or custom subdivision weights occur. This protects seams, not every architectural silhouette.

Raw G1/G2/G3 geometry, parameters, fields, roles and immediate lineage remain intact. CC meshes are **terminal comparison outputs** in a separate `derivatives` response section; they never feed back into Mola. Metadata records source run/generation, backend/version, one level, boundary verification, connected components, counts, bounding-box dimensions, retained-original-vertex displacement and elapsed time. **Derivative semantic lineage: NOT IMPLEMENTED.** No stale face roles, driver fields, cap selections or identity lineage are attached to CC topology. Matching numeric IDs do not imply semantic identity.

The count estimate is `V + E + F` output vertices and the sum of input face corners for output faces, including triangles. Existing count-budget checks run **before copying/subdivision**, and actual counts must match. Limits stay **50,000 vertices / 50,000 faces per result** and **60 seconds for the whole worker**, including startup and the unchanged three raw generations. Each CC derivative is assessed independently. A blocked G3+CC1 leaves G1+CC1 and raw checkpoints intact; no G2 substitution, limit increase or resolution reduction occurs. Finite coordinates and valid manifold connectivity are required; open components are allowed. No planar-face restriction is imposed on the CC output, and no repair, global collision or fabrication guarantee is supplied.

Each new run saves complete calculation geometry and metadata in ignored `output/task11/<run UUID>/response.json`, with request/stdout/stderr beside it. For a normal Windows-shell replay of the saved original gate:

```powershell
.\.venv\Scripts\python.exe examples\mola_surface_study.py --input-request output\task10\62392f8e-9d94-4503-8c87-75193126a9ea\request.json
```

Use an explicit retained **original request**, not a generated response. The example reuses the ignored DLL preference, or accepts `--dll "<official external DLL path>"`, and saves `G0.obj`, raw G1/G2/G3 OBJ and successful G1/G3 CC1 OBJ in a new run. No DLL or local settings are distributed.

## Actual saved-gate comparison

Task baseline: `ff8a3139a9970141f5418c910a2fabe15601b728`. Actual new worker run: `e163894a-fa4d-445b-b2a6-f35b0e542753`, compared against successful raw run `62392f8e-9d94-4503-8c87-75193126a9ea`. Original geometry and recipe/drivers matched; all raw stage geometry, parameters, fields, roles and lineage matched exactly, with byte-identical raw OBJ files. The worker completed both CC comparisons in about **15.21 seconds total**.

| Pair | Raw vertices / faces | CC1 vertices / faces | Retained vertex displacement, median / max | CC comparison time |
| --- | ---: | ---: | ---: | ---: |
| G1 | 4,374 / 4,280 | 17,298 / 16,720 | 21.254 / 76.330 | 1.40 s |
| G3 | 11,062 / 10,968 | 44,050 / 43,472 | 8.929 / 51.467 | 2.67 s |

Displacements use original model units. Both sources have **10 open components**, **568 boundary edges** and **568 boundary vertices**. Each CC result keeps 10 components and has 1,136 boundary edges. Fixed-vertex movement is **0**; maximum midpoint error is about **1.42e-14**. Both budgets and boundary checks pass. Bounding-box dimensions are unchanged within each pair: G1 `[4146.642472, 1049.959550, 3591.781340]`, G3 `[4180.085939, 1137.072404, 3631.276365]`.

The review bundle includes same-scale whole-gate and close-up projections of these actual meshes, plus a close-up wireframe audit. These are headless polygon projections, **not Rhino screenshots**. The new **MolaSurfaceStudy host run remains PENDING**. The user has confirmed the previous MolaFieldStudy original/driver/G1/G2/G3 display; that confirmation does not verify this new mode's insertion, viewport appearance, Undo or cancellation.

In those retained views, CC1 softens the angular cap rims and reduces distinct flat plateaus. G3's extra stacked tiers remain distinguishable from G1 in close-up, but fine ledges lose crispness and some junctions retain a pinched appearance. At whole-gate scale both remain a repetitive tiled relief, with modest hierarchy differences; smoothing does not introduce larger-scale organization. The wireframe and topology checks confirm that existing seams remain separate, although one projection does not expose every component boundary. This is a visual assessment of the saved geometry, not a claim that smoother is better or that pinching/intersections have been eliminated. Polygon shading and centroid-based depth ordering are approximate; Rhino viewport appearance still needs host inspection.

Four focused checks cover real COMPAS counts/finite output/source immutability, an open nonplanar boundary control, pre-copy budget rejection, and the real isolated worker's unchanged raw semantics/separate derivatives (including independent budget failure and stubbed display orchestration). Run the full suite with the existing optional DLL configured and `.\.venv\Scripts\python.exe -m pytest -q`.
