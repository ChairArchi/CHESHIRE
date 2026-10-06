# Consolidated gate visual prototype

Restart Rhino if earlier CHESHIRE modules were already imported. In **Rhino 8 ScriptEditor / Python 3**, open **`rhino/CHESHIRE_Run.py`**, run on the UI thread, select the **original gate Mesh once**, and choose **VisualPrototype**. The saved external Mola DLL path is reused. This one mode produces three fixed alternatives; there are no recipe or strength prompts. Existing modes and their defaults are unchanged.

Display contains **ORIGINAL REFERENCE**, **A - CURVED RIBS**, **B - CROWN FANS**, and **C - DIAGONAL TERRACES**, where reached. All use the same model units/orientation and world-X-only display offsets. Calculation geometry has no display offsets. Unique layers/TextDots, source/document fingerprint checks, one Undo insertion, failure rollback, Esc cancellation and the whole-worker **60-second timeout** use the existing bridge. Inspect Shaded and Wireframe manually; normals are recomputed normally, with no display-mode or material change. Interrupted candidates display their last validated checkpoint with a PARTIAL label.

## Fixed recipes, version 12.3

Fields use the **original** bounding box: `u=(x-min_x)/width`, `v=(z-min_z)/height`. Original face centers are arithmetic corner means. The study assumes world Z is gate height and world Y is facade depth; it does not rotate or repair the input. Face selections require `abs(original_face_normal_y)>0.85`. Original normalized vertex coordinates and normal-Y weights are inherited through verified lineage.

| Candidate | Spatial organization and operator order |
| --- | --- |
| A — Curved ribs | COMPAS quad1; broad normal displacement along two winding ribbons; a smaller core wave; terminal boundary-preserving CC1. **No face extrusion.** |
| B — Crown fans | Mola on four crown/shoulder clusters; caps plus at most two directional **cluster-perimeter** sides; one further cap generation. Interior neighboring tiles never grow side branches toward each other. |
| C — Diagonal terraces | COMPAS quad1; Mola inside mirrored diagonal bands; narrower cap selection; finer cap accents in the upper portion. No terminal smoothing. |

A ribbon centers are `0.24+0.09*cos(2*pi*v/0.85)` and `0.76-0.09*cos(2*pi*v/0.85)`. Broad/core widths are `0.105/0.052`; each Gaussian `exp(-(distance/width)^2)` is zero beyond two widths and is weighted by inherited original normal-Y magnitude. The fine wave multiplies by `0.5+0.5*cos(2*pi*v/0.12)`. Displacement strengths are `0.030/0.004` of each step's current bbox diagonal. Existing boundary vertices remain unselected. CC uses the existing one-level wrapper: fixed naked-boundary vertices and crease 2 only on naked edges.

B cluster centers are `(0.17,0.68)`, `(0.83,0.68)`, `(0.36,0.90)`, `(0.64,0.90)`, with normalized ellipse radii `(0.14,0.16)` and squared ellipse distance `<1`. Height ratios are `0.42`, then `0.30` on caps / `0.20` on sides, then `0.27` on primary caps / `0.18` on side-derived caps. Fractions are `0.22/0.48/0.56`. Perimeter sides border an unselected original face or a naked edge. Choose maximum positive world-Z and outward world-X normal components (away from `u=0.5`), each exceeding `0.15`; ties use the smaller face ID. Only eligible planar faces execute. On the actual gate, eight proposed second-stage faces were explicitly rejected as nonplanar and retained unchanged; their IDs/reasons are recorded. No projection or tolerance relaxation occurs.

C bands use distance from `v+0.72*abs(u-0.5)` to `{0.30,0.66,1.00}`, with initial/core widths `0.065/0.038`. After quad1, initial selection uses inherited vertex-coordinate means on each child face. The second selection uses that footprint on new caps; final cap accents require inherited original face-center `v>0.55`. Height ratios are `0.38/0.34/0.28`, fractions `0.16/0.42/0.60`. Actual height always uses the current selected face area via the unchanged Mola adapter.

Every alternative starts independently from the same original mesh. The experimental implementation is isolated in `rhino/visual_prototype.py`. It reuses the existing adapters and inheritance functions, with no core refactor, new geometry mathematics, dependency or operator library. Limits remain **5,000 original faces / 20,000 original vertices, 1,000 selected Mola faces per call, 50,000 vertices/faces per result, at most four operations per alternative, 60 seconds for the entire worker**. Budgets run before execution. A failed alternative does not substitute another recipe or erase earlier valid candidates.

## Evidence and limits

Actual saved-gate run `8c5ff45c-7810-455d-a4ba-c1339c67eccd` completed all three alternatives in **20.82 seconds**:

| Output | Vertices | Faces |
| --- | ---: | ---: |
| Original | 1,030 | 936 |
| A | 14,522 | 13,376 |
| B | 3,214 | 3,120 |
| C | 8,278 | 7,700 |

The original is unchanged and its 10 open components remain separate. Step records preserve actual geometry, masks/selections, exact parameters, immediate-parent lineage, inherited root/coordinate/region fields, roles, fresh COMPAS face-area measurements, exclusions and budgets. A's **terminal CC semantic lineage is NOT IMPLEMENTED**; its preceding stages and explicit source-step association remain available. B/C lineage is available throughout. No stale fields or roles are attached to A's CC topology.

The same-scale whole-gate and shoulder/crown close-ups show distinct organizations, but **the grotesque-like design target remains weak**. A avoids quilting but its small wave is subdued and loses definition under CC. B concentrates angular tiers and perimeter fins around the crown/shoulders, while its interiors still read as tiled clusters with some pinched-looking junctions. C produces diagonal hierarchy and quiet areas, but band edges remain pixelated by the original grid and repeated caps remain evident. These are reproducible alternatives, not a claim of exact fractal geometry or Digital Grotesque reproduction.

Earlier extrusion-plus-displacement and internally branching trials showed sampled surface crossings and were rejected. Final diagnostic checks found **zero sampled non-adjacent transverse crossings** in A/B/C using COMPAS line/triangle intersections with segment bounds. That diagnostic explicitly fan-triangulates quads for checking only, excludes adjacent/coplanar contacts, and does **not** certify global collision freedom or fabrication suitability. Delivered geometry is never triangulated or repaired. Projected overlaps and dense wireframe junctions still require viewport inspection.

Outputs live in ignored `output/task12/<run UUID>/`: original/candidate geometry in request/response JSON, all intermediate stages, recipes and worker logs. The headless example also exports `ORIGINAL.obj`, `A.obj`, `B.obj`, `C.obj` and `recipes.json`:

```powershell
.\.venv\Scripts\python.exe examples\visual_prototype.py --input-request output\task10\62392f8e-9d94-4503-8c87-75193126a9ea\request.json
```

Supply an explicit retained original request; the example reuses the ignored DLL preference or accepts `--dll "<exact official standalone DLL path>"`. No DLL or local settings are distributed.

**Verification:** headless real-worker execution and focused automated checks pass; **VisualPrototype execution inside Rhino remains PENDING**. Prior MolaFieldStudy display is user-confirmed, but does not verify this new mode. Review images are labeled headless projections of saved geometry, not Rhino screenshots; fixed projection, gray polygon lighting, scale and world-space crops are shared across all candidates. Depth sorting/shading are approximate. Manual host checks are selection/display, original preservation, repeated-run separation, Undo, Esc, document/source changes and interrupted checkpoints.
