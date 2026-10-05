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
MOLA_MODE = "MOLA_TAPER_STUDY"
MOLA_VARIANTS = [("A", 0.10, 0.25), ("B", 0.30, 0.25), ("C", 0.10, 0.65)]


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
    mode = request.get("mode", "MESH_GRAMMAR")
    if mode == MOLA_MODE:
        if not isinstance(request.get("mola_dll"), str) or not Path(request["mola_dll"]).is_absolute():
            raise ValueError("Mola requires an explicit absolute standalone DLL path.")
        selection = request.get("selected_faces")
        if selection != "ALL_ELIGIBLE_PLANAR":
            if not isinstance(selection, list) or any(type(k) is not int for k in selection) or len(set(selection)) != len(selection):
                raise ValueError("Mola selection must be explicit distinct face IDs or ALL_ELIGIBLE_PLANAR.")
            keys = {row["id"] for row in validate_mesh_data(request.get("mesh"))["faces"]}
            if len(selection) > 1000 or not set(selection) <= keys:
                raise ValueError("Mola selection exceeds 1000 faces or contains unknown IDs.")
    elif mode == "MESH_GRAMMAR":
        strength = request.get("strength")
        if type(strength) not in (int, float) or not isfinite(strength) or not 0 <= strength <= 0.03:
            raise ValueError("Demo strength must be finite, from 0 to 0.03 of the bounding-box diagonal.")
    else:
        raise ValueError("Unsupported CHESHIRE experiment mode.")
    validate_mesh_data(request.get("mesh"), MAX_INPUT_VERTICES, MAX_INPUT_FACES)
    return request


def validate_response(response, request):
    """Reject stale identities or incomplete/invalid published stage records."""
    finite_json(response)
    if not isinstance(response, dict) or response.get("protocol") != 1 or response.get("run_id") != request["run_id"] or response.get("source") != request["source"]:
        raise ValueError("Response does not match the initiating request/document/object.")
    if request.get("mode") == MOLA_MODE:
        return _validate_mola_response(response, request)
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


def _validate_mola_response(response, request):
    variants = response.get("variants")
    status = response.get("status")
    if response.get("mode") != MOLA_MODE or not isinstance(variants, list) or len(variants) > 3:
        raise ValueError("Invalid Mola study response.")
    if status not in ("SUCCESS", "PARTIAL", "FAILED") or (status == "SUCCESS" and len(variants) != 3) or (status == "PARTIAL" and not variants) or (status == "FAILED" and variants):
        raise ValueError("Inconsistent Mola study status.")
    if not isinstance(response.get("selected_faces"), list) or len(response["selected_faces"]) > (MAX_INPUT_FACES if status == "FAILED" else 1000):
        raise ValueError("Invalid Mola selected-face list.")
    selected = response["selected_faces"]
    if len(set(selected)) != len(selected) or not set(selected) <= {row["id"] for row in request["mesh"]["faces"]}:
        raise ValueError("Mola selected-face IDs do not match input.")
    if isinstance(request["selected_faces"], list) and selected != request["selected_faces"]:
        raise ValueError("Mola response selection differs from explicit request.")
    for variant, (name, ratio, fraction) in zip(variants, MOLA_VARIANTS):
        if variant.get("name") != name or variant.get("height_ratio") != ratio or variant.get("fraction") != fraction or variant.get("validated") is not True:
            raise ValueError("Mola variants must follow fixed A/B/C settings.")
        mesh = validate_mesh_data(variant.get("mesh"))
        if variant.get("vertex_count") != len(mesh["vertices"]) or variant.get("face_count") != len(mesh["faces"]):
            raise ValueError("Mola variant counts do not match mesh.")
        if [row["id"] for row in variant.get("parameters", [])] != selected:
            raise ValueError("Mola parameters must align with selected input faces.")
        for domain in ("vertices", "faces"):
            ids = [row["id"] for row in mesh[domain]]
            if [row["id"] for row in variant.get("lineage", {}).get(domain, [])] != ids:
                raise ValueError("Mola lineage must align with output IDs.")
    return response
