# CONTINUED column control ? stop after G4

Actual source: OVERLAP/G3. No gate synthesis or authored macro-return addition.
Existing Task36 class_signed recurrence plus finite18 nearest-outside field:
G4 fraction .55, field-only budget .16, local target factor2. This target search
is coarser than the lead G3 factor3 and is explicitly recorded; the finite
classifier is unchanged. Global generation4 is handled independently of the
old three-entry schedules. G5 budget .12 is implemented but was not run.

Actual G4: 204,802 physical vertices / 409,600 triangles; one connected
component, closed, winding consistent, X/Y reflection preserved. Maximum
reflection error 5.354e-15. Minimum triangle area 6.45252e-8 against unchanged
1e-12 threshold. Task36 placement max .153732; field-only budget .16. These
are separate motion terms. Self-intersection, thickness, structural performance
and fabrication are not checked here.

Actual identical-camera front/oblique/side renders show that the inherited
large return, diagonal flange and deep side cavity remain. Smaller actual
geometric ridges accumulate, but mainly as a dense grid/crust around the neck,
ends and broad panels. A distinct small-scale fold hierarchy does not clearly
emerge. This is useful persistence/control evidence, not aesthetic success.

Stop after G4: the current trend did not justify fourfold additional faces
at G5. No G5 mesh exists. Source assets and the actual G4 mesh/checkpoint/3views
are preserved; no collision repair, threshold change, renderer edit or commit.
The G3->G4 comparison also changes budget and target refinement, so do not
attribute its full visual difference to subdivision alone.

Actual files: CONTINUED/G04/geometry.npz, control_quad.npz, checkpoint.npz,
gate.ply, operation_fields.npz, column.blend and preview/*.png.
