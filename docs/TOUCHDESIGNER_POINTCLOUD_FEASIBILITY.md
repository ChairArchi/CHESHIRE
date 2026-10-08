# CHESHIRE × TouchDesigner — Point-cloud Morph Feasibility

**Status:** Research only (2026-10-09). No TouchDesigner runtime test. No CHESHIRE production code modified.

**Branch basis:** GitHub `experiment/task23-cross-cell-crease-hero`. Later local/unpushed Task24–27 work is **not** included.

## Goal / non-goals

- **Goal:** Use CHESHIRE-generated gate meshes as visual anchors, create a gradual black-background / white-particle gate morph, and extract 4–8 still frames for the Modern Cliché panel.
- **Not a goal:** Re-execute CHESHIRE subdivision per video frame; reproduce exact mathematical folding, face lineage or all intermediate topology; replace CHESHIRE renders.
- **Disclosure:** Clearly label the output as an *interpretive point-cloud animation based on CHESHIRE mesh states*, not a literal subdivision simulation.

## Evidence and constraints

- CHESHIRE `src/cheshire/mesh_io.py` exports polygon meshes in OBJ. `src/cheshire/generational_subdivision.py` and the experimental crease modules generate real topology-changing meshes. OBJ I/O does **not** preserve custom per-vertex attributes. For point IDs/groups/crease weights export a separate data file or generate a PLY using an additional **offline visualization-only adapter**.
- TouchDesigner POPs support imported point clouds, GPU-side noise, blending, grouping, point-sprite rendering and still/movie output (official sources below).
- `Blend POP` mixes the **N-th point of each input**. Matching point count does not automatically create meaningful correspondences. Without aligned IDs/order, intermediate motion may fold through itself, swirl randomly or destroy the gate silhouette. **Point mapping is the primary technical risk.**
- TouchDesigner Non-Commercial limits rendered images to **1280 × 1280**. The competition image canvas is 1920 × 1920. Use point-cloud stills as small strip elements in a larger Photoshop/Blender composition, obtain an applicable Educational license, or produce final higher-resolution rendering in Blender; do not assume free TouchDesigner can output 1920px.
- TouchDesigner POP operators documented as of 2026. Verify actual installed build before scripting.

## Required software

1. TouchDesigner with POP family (download: https://derivative.ca/download). Free Non-Commercial is sufficient to prototype.
2. CHESHIRE Python 3.12 codebase (already available). Use its ordinary OBJ exports as input; do **not** embed CHESHIRE itself in TouchDesigner.
3. Offline Python adapter: NumPy, trimesh (and optionally SciPy for nearest-neighbor registration / alignment). Produce PLY or CSV per state with identical point counts and stable point ordering.
4. Blender (optional): inspect meshes, prepare high-resolution stills if licensing is limiting.
5. No paid TouchDesigner plugin needed for MVP.

## Minimal proof of concept

1. Choose **one** gate. Export two or three CHESHIRE mesh states as OBJ: initial, intermediate (optional), deformed. Keep orientation, scale, world axes and opening stable.
2. Sample **10k–30k** points from each as an initial profiling range, not a promise of frame rate. Establish matching indices/IDs, preferably segmented by left pier / right pier / crown / remainder and with consistent spatial normalization. Avoid separately random-sampling each mesh and directly lerping unrelated point indices.
3. Export `gate_00.ply`, `gate_01.ply`, etc. with XYZ `P`, optional `id`, `region`, `birth`, `crease_weight`, `Color`.
4. TouchDesigner draft node graph:
   `Point File In POP (A/B)` → `Blend POP (P, 0..1)` → `Noise POP (animated, subtle, optional)` → `Group POP / Math Mix POP (regions/attributes, optional)` → `Geometry COMP + Point Sprite MAT + Render TOP` (or simpler `Render Simple TOP` if point appearance works) → `Movie File Out TOP (PNG image sequence)`.
5. One fixed camera. Test 4–6s continuous loop and export 6 stills. All stills should clearly read as a gate, with opening legible and controlled particle density.
6. If desired, add apparent subdivision: a second layer of points with per-point reveal times, plus brighter precomputed crease/path lines. This is a **visual motif**, not exact topology subdivision.

## Evaluation and stop conditions

- Gate opening remains legible in at least keyframes 0, 0.5, 1.
- No uncontrolled point correspondence glitches or implausible global crossing.
- Stills look good small enough for a panel; they do not compete with primary hero render.
- Reproducible exports and no changes to CHESHIRE computational pipeline.
- Stop if matching points becomes a research project or if panel is better served with 2–3 static point-cloud stills.

## Technical risks / decisions

- **Highest:** reliable correspondences across topology-changing meshes; use group-aware matching or instead animate one fixed point set procedurally toward selected shape anchors.
- **Medium:** visual density/silhouette/crease readability in a small panel strip.
- **Low for MVP:** rendering file formats and image-sequence export; both official supported paths.
- **Separate:** rendering high-resolution stills requires Education/commercial licensing or a separate renderer.
- **Not verified:** actual TouchDesigner playback performance on user's GPU and working .toe network.

## Official documentation

- Point File In POP: https://docs.derivative.ca/Point_File_In_POP
- Blend POP: https://docs.derivative.ca/Blend_POP
- Noise POP: https://docs.derivative.ca/Noise_POP
- Group POP: https://docs.derivative.ca/Group_POP
- Math Mix POP: https://docs.derivative.ca/Math_Mix_POP
- Point Sprite MAT: https://docs.derivative.ca/Point_Sprite_MAT
- Geometry COMP: https://docs.derivative.ca/Geometry_COMP
- Render Simple TOP: https://docs.derivative.ca/Render_Simple_TOP
- Movie File Out TOP: https://docs.derivative.ca/Movie_File_Out_TOP
- Non-Commercial license: https://docs.derivative.ca/TouchDesigner_Non-Commercial

