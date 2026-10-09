# A: first implementation checkpoint

## Isolation and input

- Orphan branch `research/hansmeyer-cleanroom`.
- Worktree `C:/Users/USER/CHESHIRE/cleanroom/hansmeyer`.
- Newly written generation code: `src/subdivision.py`.
- Runner: `run_checkpoint.py`; geometry renderer: `src/render.py`.
- Input: boundary of four vertically stacked unit hexahedra, x/y in
  [-0.5,0.5], z in [-2,2], rings at z=-2,-1,0,1,2.
  Shared rings; no internal faces, ornament, grooves or pre-shaped bulges.
  G0: 20 vertices, 36 edges, 18 faces.

## Primary source and direct implementation

Michael Hansmeyer, *Subdivision Beyond Smoothness* (2010), attached
`C:/Users/USER/Downloads/075-081 (1).pdf`, printed pp. 76-78.

- CC eqs. (1)-(3): face, edge and vertex placement; original CC connectivity.
- CC eq. (4): provenance-sensitive face weights after a CC generation.
  V/E/F corner identities are retained. If switching from DS, use eq. (1)
  until CC establishes those identities again.
- DS eqs. (5)-(6): modified quad and triangle weights, with face-normal
  extrusion; inset face / edge face / vertex face connectivity.
- Section 3.1: non-stationary weights and CC/DS switching.
- Section 3.2.1: two z-axis weight sets with clamped linear interpolation.
- Section 2.2: subsequent DS source-face classes F/E/V have distinct w1.

No vertex fusing, valence limits, topology attractors or crease locking yet.
Modified DS deliberately accepts only triangles/quads, the published cases;
all tested DS inputs satisfy this. No inferred n-gon modification is claimed.

## Explicit choices, not original published settings

G1/G2/G3 fixed schedules:

| weight | G1 | G2 | G3 |
|---|---:|---:|---:|
| w1 | -0.6 | 0.8 | -0.35 |
| w2 | 0.3 | -0.5 | 0.4 |
| w3 | 0 | 0.65 | -0.4 |
| w4 | 0 | -0.3 | 0.5 |
| w10 | 0.035 | -0.025 | 0.02 |
| w11 | -0.012 | 0.018 | -0.009 |
| w12 | 0.008 | -0.012 | 0.006 |

Multiply w1,w2,w10,w11,w12 by s(z)=0.65+0.7*clamp((z+2)/4,0,1).
For DS add source-face offset F:0, E:0.3, V:-0.2 to w1 before multiplying.
CC does not use this DS offset. DS uses only w1 and w10.
Every evaluated value at the two axis sets is saved in `output/checkpoint.json`.

Face normal = unit polygon normal times current perimeter. Edge/vertex
normal = arithmetic mean of incident scaled face normals. The paper allows
perimeter scaling; averaging and evaluation positions are our choices.
In CC eq. (3), E means original edge midpoints, the standard CC interpretation.
The prose's use of 'edge midpoints' is ambiguous; using the newly displaced
edge points there would not recover standard CC. This choice is disclosed.

The image is a visual reference only. Its silhouette was not traced and its
unpublished original parameter schedule is not claimed. The other attached
architecture/material papers provide context, not additional numerical rules.
