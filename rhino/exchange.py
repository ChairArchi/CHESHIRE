"""Small standard-library-only JSON contract shared by Rhino and its worker."""

import json
from math import isfinite
import os
from pathlib import Path
import tempfile
from uuid import UUID


MAX_INPUT_FACES = 5000
MAX_INPUT_VERTICES = 20000
MAX_STAGE_COUNT = 50000
MAX_STEPS = 4
TIMEOUT_SECONDS = 60


def finite_json(value):
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("Exchange data contains a non-finite number.")
    if isinstance(value, dict):
        for item in value.values():
            finite_json(item)
    elif isinstance(value, list):
        for item in value:
            finite_json(item)


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    finite_json(value)
    return value


def write_json_atomic(path, value):
    """Replace only this run's response after a complete finite serialization."""
    path = Path(path)
    content = json.dumps(value, allow_nan=False, separators=(",", ":"))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=path.name + ".", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def validate_mesh_data(data, max_vertices=MAX_STAGE_COUNT, max_faces=MAX_STAGE_COUNT):
    """Explicit integer IDs, ordered corners; no repair or coordinate merging."""
    if not isinstance(data, dict):
        raise ValueError("Mesh exchange must be an object.")
    vertices, faces = data.get("vertices"), data.get("faces")
    if not isinstance(vertices, list) or not isinstance(faces, list) or not vertices or not faces:
        raise ValueError("A nonempty vertex list and face list are required.")
    if len(vertices) > max_vertices or len(faces) > max_faces:
        raise ValueError(f"Demo input/stage count limit exceeded ({len(vertices)} vertices / {len(faces)} faces).")
    vertex_ids, face_ids = set(), set()
    for row in vertices:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] in vertex_ids:
            raise ValueError("Vertex IDs must be distinct integers.")
        xyz = row.get("xyz")
        if not isinstance(xyz, list) or len(xyz) != 3 or any(
            type(value) not in (int, float) or not isfinite(value) for value in xyz
        ):
            raise ValueError("Every vertex needs three finite XYZ coordinates.")
        vertex_ids.add(row["id"])
    for row in faces:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] in face_ids:
            raise ValueError("Face IDs must be distinct integers.")
        corners = row.get("vertices")
        if not isinstance(corners, list) or len(corners) not in (3, 4) or any(type(key) is not int for key in corners):
            raise ValueError("Only explicit triangle/quad corner lists are supported.")
        if len(set(corners)) != len(corners) or not set(corners) <= vertex_ids:
            raise ValueError("Face corners must be distinct existing vertex IDs.")
        face_ids.add(row["id"])
    return data


def validate_request(request):
    finite_json(request)
    if not isinstance(request, dict) or request.get("protocol") != 1:
        raise ValueError("Unsupported CHESHIRE request protocol.")
    if not isinstance(request.get("run_id"), str) or str(UUID(request["run_id"])) != request["run_id"]:
        raise ValueError("A canonical UUID run identity is required.")
    source = request.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("object_id"), str) or type(source.get("document_serial")) is not int:
        raise ValueError("Source document and object identity are required.")
    strength = request.get("strength")
    if type(strength) not in (int, float) or not isfinite(strength) or not 0 <= strength <= 0.03:
        raise ValueError("Demo strength must be finite, from 0 to 0.03 of the bounding-box diagonal.")
    validate_mesh_data(request.get("mesh"), MAX_INPUT_VERTICES, MAX_INPUT_FACES)
    return request


def validate_response(response, request):
    """Reject stale identities or incomplete/invalid published stage records."""
    finite_json(response)
    if not isinstance(response, dict) or response.get("protocol") != 1 or response.get("run_id") != request["run_id"] or response.get("source") != request["source"]:
        raise ValueError("Response does not match the initiating request/document/object.")
    stages = response.get("stages")
    if not isinstance(stages, list) or len(stages) > MAX_STEPS:
        raise ValueError("Invalid completed-stage list.")
    status = response.get("status")
    if status not in ("SUCCESS", "PARTIAL", "FAILED") or (status == "SUCCESS" and len(stages) != MAX_STEPS) or (status == "FAILED" and stages):
        raise ValueError("Inconsistent worker status/completed stages.")
    if status == "PARTIAL" and not stages:
        raise ValueError("PARTIAL requires at least one valid completed step.")
    for number, stage in enumerate(stages, 1):
        if stage.get("generation") != number or stage.get("validated") is not True:
            raise ValueError("Only consecutive validated completed stages may be displayed.")
        mesh = validate_mesh_data(stage.get("mesh"))
        if stage.get("vertex_count") != len(mesh["vertices"]) or stage.get("face_count") != len(mesh["faces"]):
            raise ValueError("Stage counts do not match its mesh.")
    driver = response.get("driver")
    if stages:
        validate_mesh_data(driver["mesh"])
        ids = [row["id"] for row in driver["mesh"]["vertices"]]
        values = driver.get("values")
        if not isinstance(values, list) or [row["id"] for row in values] != ids:
            raise ValueError("G1 field must be aligned to its pre-displacement driver mesh.")
        if any(row["value"] is not None and (type(row["value"]) not in (int, float) or not 0 <= row["value"] <= 1) for row in values):
            raise ValueError("Invalid driver field values.")
    return response
