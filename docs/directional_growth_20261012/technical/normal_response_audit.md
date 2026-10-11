# Task36 normal_response — read-only mathematical audit

Sources inspected, without edits or extra tests:
`src/cheshire/task36_growth.py:74-123` and
`src/cheshire/reference_subdivision.py:62-80,128-148`.
This describes the existing CHESHIRE operator, not IAAC original equations.

## Actual contrast definitions and signs

Let h_f be the minimum face-centre distance to its supporting edge lines,
n_f the incoming unit face normal, c_f the arithmetic incoming face centre,
and N(f) the four edge-adjacent faces. Task36 computes

`C_f = dot(c_f - mean(c_N(f)), n_f) / max(h_f, 1e-12)`.

For edge e between faces a/b, let m_e be its endpoint midpoint and
`u_e = unit(n_a + n_b)`. It computes

`C_e = dot(m_e - (c_a+c_b)/2, u_e) / max(min(h_a,h_b), 1e-12)`.

These are signed local normal-projected contrasts, not exact curvature,
physical strain or preserved crease tags. A positive crest-like signal tends
to point outward; a negative valley-like signal tends inward. Saddle regions
and irregular sampling need not admit a simple global convex/concave label.

Define `A = face_gain*h_f*(1+feedback*tanh(2*face_bend))` and
`B = edge_gain*min(h_a,h_b)`. `sf/se` are the reference operator's local scales.

| Mode | resolved wf | resolved we |
|---|---|---|
| class_signed | -A/sf | +B/se |
| face_geometry | +A*tanh(2*C_f)/sf | +B/se |
| all_geometry | +A*tanh(2*C_f)/sf | +B*tanh(2*C_e)/se |

The two minus signs in face_geometry cancel. Therefore this is a signed
contrast amplification response, not smoothing. Near C_f=0, direct face-normal
placement vanishes; near large positive/negative contrast it saturates within
the existing support-scaled amplitude. Terminal masks are applied afterwards.

## Face -> edge coupling is material

Reference subdivision completes face positions BEFORE edge positions:

`E_new = ((F_a+F_b)*(1+w1) + (V_a+V_b)*(1-w1))/4 + mean(n_a,n_b)*we*se`.

With this recipe's w1=.5, each completed face contributes .375 to the new edge.
Thus face_geometry changes edge positions even though its direct we control
is unchanged. all_geometry changes both that inherited face contribution and
the direct edge-normal term; these may cancel or reinforce.

Important distinction: contrast C_e uses the UNIT averaged direction u_e,
but the reference edge offset uses the ARITHMETIC MEAN face normal, whose
magnitude is at most one and can be near zero across opposing faces. The
preliminary feedback-scaled edge_vector earlier in Task36 is replaced by the
coupled result; that preliminary vector is not the final coupled formula.

## Component gains and vertex_gain=0

For identical incoming OVERLAP/G2 controls, define I=interpolated placement,
S=standard CC result, G=weighted-stencil result with wf/we/wp zero, and C=full
coupled result. Task36 resolves

`I + averaging_gain*(S-I) + stencil_gain*(G-S) + normal_gain*(C-G)`

with its declared vertex-memory and terminal restrictions. The active recipe
is averaging=0, stencil=1, normal=1. Normal response modifies C-G, including
face-to-edge propagation; it does not modify the common stencil/ancestry
controls. Setting normal_gain=0 would remove this mode distinction before the
field. Averaging=0 disables the explicit STANDARD CC averaging component,
not every weighted positional combination in the stencil.

Current vertex_gain=0 makes wp=0: no DIRECT vertex-normal extrusion. The extra
all_geometry multiplier on wp consequently has no effect in this recipe.
In general, wp=0 alone does not freeze vertices because reference vertex
positions also depend on completed face points and stencils. Here the separate
vertex_memory=1 explicitly keeps incoming vertices unchanged through Task36
placement. The subsequent finite field is free to move those old vertices.
Therefore neither vertex_gain=0 nor Task36 vertex retention means final-cycle
vertices are fixed, and neither constitutes semantic legacy-crease protection.

## Expected opportunity and failure risk — inference, not a test result

- Signed response can deepen valleys and raise existing crests while reducing
  compulsory face-in/edge-out cells on low-contrast areas.
- Positive face and edge signals can both act outward on broad convex regions,
  producing cushion-like expansion instead of sharper returns.
- Existing ancestry stencils remain active; switching normal_response alone
  cannot guarantee removal of parallel grids or creation of new macro nodes.
- Support-scaled offsets still become smaller with subdivision. These modes
  change local sign/amplitude, not the wavelength, physical folding mechanism
  or material coordinate direction. No actual torsion claim follows.

No new test, collision repair, threshold change or generic algorithm was added
for this audit. Judge the two actual candidate renders separately.
