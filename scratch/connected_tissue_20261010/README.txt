CHESHIRE ? Connected Geometric Tissue Experiment

Scope
Frozen six-cycle synthetic CHESHIRE TARGET; no actual ALICE data.
Original archive and accepted LAST/UNUSED comparison are read-only.

Reproduce (PowerShell, from this directory)
..\..\.venv\Scripts\python.exe -B run.py --scale 4 --methods tissue_round,tissue_variable --refinement 2 --protect-folds --output runs/NEW_patch
..\..\.venv\Scripts\python.exe -B run.py --scale 4 --wide --methods tissue_round --protect-folds --output runs/NEW_wide
..\..\.venv\Scripts\python.exe -B run.py --scale 4 --methods frame_bundle --refinement 2 --protect-folds --thickness .0036 --output runs/NEW_bundle
..\..\.venv\Scripts\python.exe -B verify.py
Output must be a new directory. Dependencies are reused from the preserved sibling project; this is a workspace-runnable experiment, not a standalone installer.

Operations actually executed
Blender UNSUBDIV recovers a coarser quad layout from the frozen target.
Face-edge graph selection gives one contiguous patch, not spatially scattered cells.
Actual Tissue QUAD/LAST and boundary merge; collar trial uses actual UNUSED.
A simple four-face open frame forms shared seams. Variable trial uses Tissue shape keys and normal-variation vertex groups.
Weaverbird-style shared-index Frame/Window is implemented locally; the Weaverbird plugin itself is NOT executed.
Blender SIMPLE or Catmull-Clark network refinement; angle-based edge creases; nearest-point reprojection; SOLIDIFY thickness.
Wide result uses shared seam reflection and symmetric solidify offsets.
frame_bundle adds elongated openings and raised rail crowns interpolated through subdivision. It intentionally departs from the target by a small normal relief; it is a separate operation comparison, not an actual Tissue result.

Connectivity
Cells share actual vertices and edges. Recommended wide_protected4 is one closed component, zero boundary and nonmanifold edges, bilateral vertex error 0.
This is a separate front-region shell, NOT joined to the full original opaque target.
tissue_collar joins the generated network to one retained COARSE target boundary ring before subdivision; not to the separate high-density target object.

Scale and limitations
Scale 2: 3361 local faces; scale 4: 919 local faces. Wide scale 4: 19568 selected faces.
Scale 6 was rejected because recovered faces were no longer all quads.
Earlier wide_symmetric4 failed topology. wide_tissue_round4 and wide_symmetric_v2 have symmetry error and are development records only. Use wide_protected4.
Nearest-point projection alone cannot certify preserved ridges: faces can bridge valleys even when vertices lie on target.
audit/surface_audit.json measures sampled vertex, edge-midpoint and triangle-interior distances. Creases reduce typical local bridging but do not eliminate it.
No global self-intersection certification. Closed topology does not prove printability.
Wide uniform perforation is visually too regular; this is a connection feasibility result, not a claim of Hansmeyer-level design success.
Do not reduce detail for FDM at this stage. Shape evaluation remains the user's decision.

Files
Each runs/<trial>/<method>/ contains result.obj, result.ply, result.json, midsurface.json, operations.json, checks.json, and Blender job/log.
review.html contains actual mesh renders with consistent cameras.
verification.json reloads both OBJ and PLY and checks source hashes.

Fold extension
extension/ contains a copy of the existing generator. Only runtime paths and stage-count ceiling were adjusted.
fold8.json and fold10.json append existing pleat_flow / normal_extrude cycles to the frozen six-cycle checkpoint.
This comparison holds resolution fixed. It does not claim additional CC/DS operations: those are in the inherited prefix.

New TARGET reuse
run.py --target path/to/normalized_target.json uses the same operators with a source-hash-specific coarse cache. JSON contains vertices and polygon faces; Z up, X mirror plane. This is not an ALICE adapter.

Section-mass branch
extension/section_mass_early.json introduces support-section scaling, actual MOLA tapered extrusions, CC/DS and the first pleat/extrude pair. section_mass_full.json resumes the remaining five pairs. Profiles are configurable and derive axis and height bounds from actual support-role geometry. No new mathematical reproduction claim about Hansmeyer.
