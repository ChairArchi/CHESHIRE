END RULE REVISION / 2026-10-14

One authorized bounded revision after rejection of independent added ornaments.
Original WIDE_ROOT_FINISHED/SPAN/G07 and every earlier checkpoint are read-only.
Heavy data: E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01

SOURCE DIAGNOSIS
Actual SIDEWALL_G3 vertex_source_ids/mirror_signs reorder the inherited WALL IDs.
Current7272 -> originalWALL894 = G1edge(G0[241,257]). Its G2 return/Task36/field
and WALL deltas are zero. G1Task36 movesZ-.019223; finitefield movesZ-.101555.
Neighbor fields also independently pullZ. Other cups have different inherited
contributions, so a WALL parameter change is not a demonstrated remedy.
This is one source-direction hypothesis, not a promise to fix every cup.

SOLE SOURCE RULE CHANGE
G1 and G2 use actual unchanged SPAN G0, Task36 and raw finite-outside query.
w=plateau((t-.63)/.085,.6)*plateau((theta-.86)/.66,.6)
theta=atan2(abs(material_y),abs(material_x)); gainZ=1-.75*w.
Applied field delta becomes(dx,dy,gainZ*dz); its norm/budget cannot increase.
The applied vector is no longer generally directed at the nearest outside point.
Raw queries and revised applied vectors are separately recorded.
Authored PCHIP returns and all Task36 coefficients remain unchanged.

REPLAY AND BOUNDED OUTPUT
replay.py imports the frozen early/late recipe modules read-only, loads exact
original G0 XYZ, reconstructs the original carrier ancillary associations, and
executes the selected G0-G7 sequence with actual revised parents. Geometry-based
rails, normals and frames are recalculated. This is one modified replay, not an
independent unchanged-baseline replay or parameter search.
Late intermediate checkpoints store controls/evidence; final replay G7 also
stores native geometry. Each child process releases dense arrays on exit.

run.py requires exact original/replay topology and associations before combining:
Xfinal=Xoriginal+original_saved_end_mask*(Xreplay-Xoriginal).
This limits the candidate to the original marked ends and transition collar;
out-of-mask XYZ remains exact. Final output is a masked continuation of the
modified replay, not an unqualified whole-column source regeneration.
Actual finite/area/symmetry checks and old/new face-normal diagnostics are saved.
No added ornament mesh, G8, Boolean, remesh or whole-column smoothing is used.

RENDERING
render.py --phase original_only produces source-SMOOTH views and binds existing
FLAT references before candidate generation. Smooth modifies only normal shading;
actual native XYZ/index readbacks remain unchanged. This is not geometry success.
--phase candidate_only renders the one revised body in FLAT and SMOOTH, with
identical four cameras/material/lights/sampling. The body is loaded once per phase.
boards.py verifies and compares geometry under each shading condition separately.

EXECUTION
  python run.py --root NEW_E_ROOT
  blender --background --python render.py -- --root NEW_E_ROOT --phase original_only
  blender --background --python render.py -- --root NEW_E_ROOT --phase candidate_only
  python boards.py --root NEW_E_ROOT
The original-only render may be run while the revised replay is computing.
Use existing CHESHIRE venv/Blender4.5.4, TEMP/TMP on E. Never overwrite a trial.
If replay fails, preserve logs/state; no automatic parameter adjustment is allowed.

Acceptance is visible continuity of the existing ends under matched conditions,
with retained whole-column flow. Smooth appearance alone is not a successful
geometry revision. Results/decision are in docs/end_rule_revision_20261014.
