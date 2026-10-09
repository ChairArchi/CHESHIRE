# B: first proof and stop

- `output/INPUT.png`, `output/TARGET.png`, `output/OUTPUT.png`: actual meshes.
- `output/checkpoint_B.png`: all three side by side, same camera and scale;
  each centered for display only. OBJ coordinates preserve original space.
- Separate `INPUT.obj`, `TARGET.obj`, `OUTPUT.obj` support mesh inspection.
- `output/checkpoint.json` records triangle hit indices, distances and
  barycentric coordinates for every input vertex.

240 of 240 input rays hit the target. OUTPUT preserves INPUT's x/z values
and two boundary loops. Its y coordinates change from the constant -2.5 to
the range [-0.9,-0.5501909338]: the frame bends over the target surface.
This is a geometric mapping, not merely adjacent display objects.

One causal check held INPUT and its connectivity fixed and changed only
TARGET's depth radius from 0.9 to 1.35. Every output point changed;
displacement range 0.2750954669 to 0.45. Thus TARGET directly drives OUTPUT.
This is a single verification, not a parameter campaign; no alternative
form was rendered or selected from that check.

Minimum checks: each hit agrees with its target triangle barycentric point
to <1e-9; positive ray distances; preserved x/z; nonconstant output depth;
annular topology Euler 0 and two boundary loops. Images were visually
reviewed. This proves the limited mapping relation only, not recursive
symmetry, target-shape optimization, a watertight output or ornament.

**Status: awaiting user review before any larger experiment.**
