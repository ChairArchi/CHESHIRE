# CHESHIRE

**Computational Hybrid Exploration for Surface Handling, Iteration & Rule-based Engine**

CHESHIRE is a standalone deterministic computational design engine for transforming arbitrary polygon meshes through explicit, traceable rules. Its long-term aim is to measure geometric and topological attributes, map them into scalar fields, select and apply transformation rules, inherit provenance and tags, and iterate. It is independent from ALICE and has no dependency on it.

**Status:** early experimental research software.

Planned pipeline:

**Mesh → Measure → Map → Rule → Transform → Inherit → Repeat**

Task 01 currently implements only mesh infrastructure: COMPAS-based OBJ loading, inspection, basic validation, export, and reload. No transformation or rule engine is implemented.

## Setup and tests

Use Python 3.12 on Windows. In VS Code, select `.venv\Scripts\python.exe` as the Python interpreter.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

Direct dependencies are pinned in `pyproject.toml`: COMPAS 2.15.1 and pytest 9.1.1 (test extra). Their required transitive dependencies are installed automatically.

## Usage

```python
from cheshire import load_mesh, inspect_mesh, validate_mesh, save_mesh

mesh = load_mesh("input.obj")
print(inspect_mesh(mesh))
print(validate_mesh(mesh))  # List of problems; [] means basic checks passed.
save_mesh(mesh, "output/mesh.obj")
```

Only OBJ is supported. I/O rejects zero vertices, zero faces, and non-finite XYZ coordinates with `ValueError`; inspection and validation never modify the mesh. `bounding_box` contains axis-aligned dimensions `[x, y, z]`, or `None` for empty/non-finite geometry. Topology flags use COMPAS methods and return `None` when unavailable.

Loading uses COMPAS's raw `OBJReader` because `Mesh.from_obj()` welds vertices. Original vertex indices, unused vertices, and polygon faces are retained; malformed faces that COMPAS would change are rejected. Positive and relative negative face indices are supported. Saving uses `Mesh.to_obj(unweld=False)` with at least 17 decimal places, increasing precision for small coordinates (up to 324) to preserve Python floats. Very small coordinates produce larger text files. No welding, triangulation, or repair occurs.

This interface preserves vertex positions and polygon connectivity only. OBJ materials, textures, normals, grouping, standalone points/lines, and custom mesh attributes are not preserved. Basic validation does not certify manifoldness, degeneracy, or absence of self-intersections; topology flags describe COMPAS's mesh representation.
