"""Read the small ALICE gate exchange contract; no geometry repair or execution."""
import hashlib
import json
from math import isfinite
from pathlib import Path
import re

from .mesh_io import load_mesh
from .validation import inspect_mesh, validate_mesh

SCHEMA = "alice-cheshire-gate/1"
ROTATION = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]


def load_gate_input(directory):
    """Fail explicitly on malformed metadata as well as invalid geometry."""
    try:
        return _load_gate_input(directory)
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed gate exchange metadata: " + str(error)) from error


def _load_gate_input(directory):
    """Return geometry and its manifest after checking identity, frame and metadata.

    This validates an exchange, not a Task31 continuation checkpoint or solid.
    Regions refer to dense OBJ face indices. Unknown semantics remain None.
    """
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported gate exchange schema.")
    # Reject non-finite numeric metadata, including deformation parameters.
    def finite(value):
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("Non-finite exchange metadata.")
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
    finite(manifest)
    source = manifest["source"]
    if not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ValueError("Source identity requires SHA256.")
    if not re.fullmatch(r"[0-9a-f]{40}", source["revision"]):
        raise ValueError("Declare the source producer's full Git revision.")
    frame = manifest["frame"]
    scale = frame["scale"]
    if (frame["source_axes"] != "X_RIGHT_Y_UP_Z_BACK"
            or frame["axes"] != "X_RIGHT_Y_FRONT_Z_UP"
            or frame["rotation"] != ROTATION
            or isinstance(scale, bool) or not isinstance(scale, (int, float)) or scale <= 0):
        raise ValueError("Unsupported frame or scale.")
    if manifest["unit"] not in {"m", "mm", "design_unit"}:
        raise ValueError("Declare m, mm or design_unit; never infer physical units.")
    if not isinstance(manifest["parameters"], dict):
        raise ValueError("Parameters must be an explicit object; they are not executed.")
    geometry = manifest["mesh"]
    if any(type(geometry[name]) is not int or geometry[name] <= 0 for name in ("vertices", "faces")):
        raise ValueError("Mesh counts must be positive integers.")
    # V1 deliberately has exactly one local OBJ; no arbitrary paths or sidecars.
    path = root / "mesh.obj"
    if geometry["file"] != "mesh.obj" or not path.resolve().is_relative_to(root):
        raise ValueError("Mesh must remain inside the exchange directory.")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    sha = h.hexdigest()
    if geometry["sha256"] != sha or manifest["input_id"] != sha:
        raise ValueError("Mesh identity/hash mismatch.")
    mesh = load_mesh(path)
    errors = validate_mesh(mesh)
    if errors:
        raise ValueError("Invalid exchange mesh: " + repr(errors))
    if (geometry["vertices"], geometry["faces"]) != (mesh.number_of_vertices(), mesh.number_of_faces()):
        raise ValueError("Mesh count mismatch.")
    semantic = manifest["semantics"]
    if not isinstance(semantic, dict) or set(semantic) != {"support_left", "support_right", "upper", "openings"}:
        raise ValueError("Declare all four semantic fields; use null for unknown.")
    for role in ("support_left", "support_right", "upper"):
        faces = semantic[role]
        if faces is not None and (not isinstance(faces, list)
                or any(type(i) is not int or not 0 <= i < mesh.number_of_faces() for i in faces)
                or len(set(faces)) != len(faces)):
            raise ValueError("Invalid semantic face indices: " + role)
    openings = semantic["openings"]
    if openings is not None:
        if not isinstance(openings, list):
            raise ValueError("Openings must be a list or null for unknown.")
        for opening in openings:
            bounds = opening["bounds"]
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or any(not isinstance(p, list) or len(p) != 3 for p in bounds)
                    or any(type(v) not in (int, float) for p in bounds for v in p)
                    or any(a >= b for a, b in zip(*bounds))):
                raise ValueError("Opening bounds must be a nonempty XYZ box in the target frame.")
    return mesh, manifest


def describe_gate_input(directory):
    mesh, manifest = load_gate_input(directory)
    return dict(input_id=manifest["input_id"], unit=manifest["unit"],
                mesh=inspect_mesh(mesh), semantics=manifest["semantics"],
                parameters_executed=False,
                continuation_checkpoint=False)
