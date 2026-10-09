# ALICE → CHESHIRE gate exchange v1

Status: small opt-in geometry handoff. Independent repositories/environments; no
cross-project Python imports. ALICE interprets/aligns images, extracts structure and
generates base geometry/parameters. CHESHIRE validates a file input and owns subdivision
and deformation. Existing research algorithms and Task31 checkpoints are unchanged.

## Directory and identity

A NEW export directory contains `mesh.obj` and `manifest.json`.
Manifest `schema` is `alice-cheshire-gate/1`. OBJ contains only vertices and oriented
polygon faces with dense zero-based identities in metadata (OBJ indices are one-based).
No welding, triangulation, remeshing, repair, materials or automatic semantic labeling.
ALICE's current exporter preserves its loaded triangle faces; CHESHIRE's existing OBJ
reader retains positions/connectivity and vertex identity.

`input_id` and `mesh.sha256` both equal SHA256 of the exact OBJ bytes. `mesh` also has
`file: mesh.obj`, `vertices` and `faces`. `source` records original basename, SHA256 and
the declared full 40-character producer Git `revision`. The source revision is a
provenance declaration, not independently inferred from geometry. Export scale changes
the input identity. Keep the original source and revision separately for recovery.

## Frame and scale

Canonical ALICE source: X right, Y up, Z back. Target: X right, Y front, Z up.
Apply `(x,y,z) → scale * (x,-z,y)` about the existing origin. Matrix
`[[1,0,0],[0,0,-1],[0,1,0]]` has determinant +1: face winding stays unchanged.
No centering, fitting, source repair or translation. Manifest `frame` declares
`source_axes: X_RIGHT_Y_UP_Z_BACK`, `axes: X_RIGHT_Y_FRONT_Z_UP`, that `rotation`, and
a finite positive `scale`. Reversing the frame uses `(X,Z,-Y)/scale`.

`unit` is `m`, `mm` or `design_unit`. Scale must be supplied explicitly. A normalized
primary height of 1 does not recover an object's metres or millimetres. Use `design_unit`
until a physical scale is established. Never apply this transform to an unaligned/raw
reconstruction or infer the frame from its filename.

## Minimum semantics and parameters

`semantics` has `support_left`, `support_right`, `upper`: null for unknown, otherwise
unique dense OBJ face-index lists. These are caller-declared geometric regions, not
historical typology or Task31 point classes. No face relabeling occurs on import.
`openings` is null for unknown, or a list of records with `bounds: [[xmin,ymin,zmin],
[xmax,ymax,zmax]]` in the TARGET frame and unit. An empty list explicitly declares no
opening observation. Bounds alone do not prove a through-passage or collision-free solid.
Roles may overlap intentionally; membership and observation confidence remain upstream
research metadata. Do not fabricate confident labels for the current coarse mass.

`parameters` is an explicit finite JSON object (empty when absent). It records intended
controls only: import/check does not execute it, choose an operator, lower a budget or
override a frozen recipe. An eventual design runner must explicitly select its existing
operator and supported controls. No general architecture grammar is introduced here.

For a design caller, record the intended operator and its existing API names in this
object: normal displacement uses `strength`, `direction`, `scale_mode` and an explicit
field/selection; reference CC/DS uses the exact `scheme`, `generation`, `row.weights`
or `weights`, `scale` and optional intrinsic definition from the existing step contract.
Regional development additionally carries the declared `descriptor`, `memory`, `contrast`,
`born` and `edit` definition. Record `max_faces`, `max_vertices` and time/generation limits
alongside the controls. These values must be checked by the invoking runner before
allocation; the exchange checker itself does not dispatch or accept them as authorization.

## Validation and usage

ALICE exporter: `tools/export_cheshire_gate.py`, using ALICE's own environment. It writes
17-digit XYZ and refuses existing output directories. Scene transforms are handled by
the existing ALICE loader; precision already lost in a saved GLB cannot be recovered.

From CHESHIRE root:

```powershell
.\.venv\Scripts\python.exe -B tools\check_gate_exchange.py output\alice_gate_NEW
.\.venv\Scripts\python.exe -B tools\check_gate_exchange.py output\alice_gate_NEW --probe-subdivision
```

`cheshire.gate_exchange.load_gate_input(directory)` returns the validated existing
COMPAS Mesh and manifest. It checks schema, hashes, declared revision/frame/units,
counts, finite metadata, semantic references and existing mesh validation. Unsupported
or missing fields, tampering and invalid geometry fail; nothing is repaired or overwritten.
The optional probe uses the existing one-step neutral global quad adapter with its
unchanged bilinear admissibility policy and a local 50,000 vertex/face ceiling. It writes
no result geometry. Passing the probe is not Task31 reference-operator compatibility,
research hierarchy, Rhino-host verification, self-intersection or fabrication certification.

An exchange is an INITIAL seed, not a continuation state. Source class/rest/anchor arrays,
regional memberships and actual parent supports must be initialized by a future explicit
design runner. Never substitute OBJ for a saved Task31 NPZ checkpoint. Frozen Task31
gate/cube definitions, units and coordinates remain separate from this opt-in input.
