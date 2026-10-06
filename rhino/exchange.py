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
MOLA_FIELD_MODE = "MOLA_FIELD_STUDY"
MOLA_SURFACE_MODE = "MOLA_SURFACE_STUDY"
VISUAL_MODE = "VISUAL_PROTOTYPE"
WEIGHTED_MODE = "WEIGHTED_SUBDIVISION_STUDY"
GENERATIONAL_MODE = "GENERATIONAL_WEIGHT_STUDY"
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
    if mode in (MOLA_MODE, MOLA_FIELD_MODE, MOLA_SURFACE_MODE, VISUAL_MODE):
        if not isinstance(request.get("mola_dll"), str) or not Path(request["mola_dll"]).is_absolute():
            raise ValueError("Mola requires an explicit absolute standalone DLL path.")
        selection = request.get("selected_faces")
        if mode in (MOLA_FIELD_MODE, MOLA_SURFACE_MODE, VISUAL_MODE) and selection != "ALL_ELIGIBLE_PLANAR":
            name = {MOLA_FIELD_MODE: "MolaFieldStudy", MOLA_SURFACE_MODE: "MolaSurfaceStudy", VISUAL_MODE: "VisualPrototype"}[mode]
            raise ValueError(name + " uses all eligible ORIGINAL planar faces.")
        if selection != "ALL_ELIGIBLE_PLANAR":
            if not isinstance(selection, list) or any(type(k) is not int for k in selection) or len(set(selection)) != len(selection):
                raise ValueError("Mola selection must be explicit distinct face IDs or ALL_ELIGIBLE_PLANAR.")
            keys = {row["id"] for row in validate_mesh_data(request.get("mesh"))["faces"]}
            if len(selection) > 1000 or not set(selection) <= keys:
                raise ValueError("Mola selection exceeds 1000 faces or contains unknown IDs.")
    elif mode in (WEIGHTED_MODE, GENERATIONAL_MODE):
        pass  # Fixed S/U/F study; no Mola DLL or user-defined recipe.
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
    if request.get("mode") == MOLA_FIELD_MODE:
        return _validate_field_response(response, request)
    if request.get("mode") == MOLA_SURFACE_MODE:
        return _validate_surface_response(response, request)
    if request.get("mode") == VISUAL_MODE:
        return _validate_visual_response(response, request)
    if request.get("mode") == WEIGHTED_MODE:
        return _validate_weighted_response(response, request)
    if request.get("mode") == GENERATIONAL_MODE:
        return _validate_generational_response(response)
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


def _validate_generational_response(response):
    """Separate opt-in contract; existing weighted response stays strict."""
    variants=response.get("variants")
    if response.get("mode") != GENERATIONAL_MODE or response.get("recipe_version") != "16.0" or not isinstance(variants,list) or len(variants)>2:
        raise ValueError("Invalid generational study response.")
    if [row.get("id") for row in variants] != ["CONTROL_L4","BEST_NEW"][:len(variants)]:
        raise ValueError("Generational comparison must be control then best.")
    carrier=validate_mesh_data(response.get("carrier",{}).get("mesh"))
    if len(carrier["vertices"]) != 24 or len(carrier["faces"]) != 22:
        raise ValueError("Generational study requires the unchanged C0 carrier.")
    completed=False
    for variant in variants:
        stages=variant.get("stages"); state=variant.get("status"); schedule=variant.get("schedule")
        if variant.get("semantic_lineage") != "NOT IMPLEMENTED" or not isinstance(stages,list) or len(stages)>5:
            raise ValueError("Invalid generational checkpoints/semantic status.")
        if not isinstance(schedule,list) or len(schedule)!=5 or any(set(row)!={"wf","w1","we","w2","wp","w3","w4"} for row in schedule):
            raise ValueError("Five explicit seven-parameter generation rows are required.")
        if state not in ("SUCCESS","PARTIAL","FAILED") or (state=="SUCCESS" and len(stages)!=5) or (state=="PARTIAL" and not stages) or (state=="FAILED" and stages):
            raise ValueError("Inconsistent generational checkpoint status.")
        previous=carrier
        for g,stage in enumerate(stages,1):
            data=validate_mesh_data(stage.get("mesh"))
            metadata=stage.get("metadata",{})
            if stage.get("generation") != g or stage.get("validated") is not True or stage.get("ratios") != schedule[g-1]:
                raise ValueError("Only consecutive validated scheduled generations are displayable.")
            if stage.get("vertex_count") != len(data["vertices"]) or stage.get("face_count") != len(data["faces"]) or len(data["faces"]) != sum(len(f["vertices"]) for f in previous["faces"]):
                raise ValueError("Generational growth/counts disagree.")
            if len(data["vertices"]) != len(previous["vertices"])+len(previous["faces"])+metadata.get("input",{}).get("edge_count",-100000) or metadata.get("budget",{}).get("status") != "SAFE":
                raise ValueError("Invalid generational vertex growth/budget.")
            origins=stage.get("origin_lineage",[]); ids={v["id"] for v in data["vertices"]}
            if len(origins)!=len(ids) or {r.get("id") for r in origins} != ids or any(r.get("generation")!=g or r.get("class") not in ("VERTEX_DERIVED","EDGE_DERIVED","FACE_DERIVED") for r in origins):
                raise ValueError("Immediate-generation origin classes must cover actual output IDs.")
            previous=data; completed=True
    state=response.get("status")
    if state not in ("SUCCESS","PARTIAL","FAILED") or (state=="SUCCESS" and (len(variants)!=2 or any(row["status"]!="SUCCESS" for row in variants))) or (state=="PARTIAL" and not completed) or (state=="FAILED" and completed):
        raise ValueError("Inconsistent generational response status.")
    return response


def _validate_weighted_response(response, request):
    variants = response.get("variants")
    if response.get("mode") != WEIGHTED_MODE or response.get("recipe_version") != "14.1" or not isinstance(variants, list):
        raise ValueError("Invalid weighted study response.")
    if [v.get("id") for v in variants] != list("SUF")[:len(variants)]:
        raise ValueError("Weighted studies must be the consecutive S/U/F prefix.")
    completed = False
    for variant in variants:
        stages = variant.get("stages")
        if variant.get("semantic_lineage") != "NOT IMPLEMENTED" or not isinstance(stages, list) or len(stages) > 2:
            raise ValueError("Invalid weighted checkpoints/semantic status.")
        state = variant.get("status")
        if state not in ("SUCCESS", "PARTIAL", "FAILED") or (state == "SUCCESS" and len(stages) != 2) or (state == "PARTIAL" and not stages) or (state == "FAILED" and stages):
            raise ValueError("Inconsistent weighted candidate status.")
        previous = request["mesh"]
        for number, stage in enumerate(stages, 1):
            data = validate_mesh_data(stage.get("mesh"))
            if stage.get("generation") != number or stage.get("validated") is not True:
                raise ValueError("Only consecutive validated weighted checkpoints are displayable.")
            if stage.get("vertex_count") != len(data["vertices"]) or stage.get("face_count") != len(data["faces"]):
                raise ValueError("Weighted checkpoint counts disagree.")
            metadata = stage.get("metadata", {})
            expected_v = len(previous["vertices"]) + metadata.get("input", {}).get("edge_count", -100000) + len(previous["faces"])
            expected_f = sum(len(f["vertices"]) for f in previous["faces"])
            if len(data["vertices"]) != expected_v or len(data["faces"]) != expected_f or metadata.get("budget", {}).get("status") != "SAFE" or metadata.get("semantic_lineage") != "NOT IMPLEMENTED":
                raise ValueError("Invalid weighted growth/budget/lineage metadata.")
            ids = {v["id"] for v in data["vertices"]}
            points = metadata.get("points", [])
            if len(points) != len(ids) or {p.get("id") for p in points} != ids or any(p.get("point_class") not in ("face", "edge", "corner") for p in points):
                raise ValueError("Generated point classes must cover actual output IDs.")
            previous_ids = {v["id"] for v in previous["vertices"]}
            rows = stage.get("sampling_parents", [])
            if len(rows) != len(ids) or {r.get("id") for r in rows} != ids:
                raise ValueError("Control-cage sampling associations must cover actual IDs.")
            for row in rows:
                parents = row.get("parents", [])
                if not parents or any(p.get("id") not in previous_ids or type(p.get("weight")) not in (int,float) or p["weight"] <= 0 for p in parents) or abs(sum(p["weight"] for p in parents)-1) > 1e-9:
                    raise ValueError("Invalid positive control-cage association.")
            if variant["id"] == "F" and (len(stage.get("drivers", [])) != len(ids) or {r.get("id") for r in stage["drivers"]} != ids):
                raise ValueError("Separate field drivers must cover actual generated points.")
            previous = data
            completed = True
    state = response.get("status")
    if state not in ("SUCCESS", "PARTIAL", "FAILED") or (state == "SUCCESS" and (len(variants) != 3 or any(v["status"] != "SUCCESS" for v in variants))) or (state == "PARTIAL" and not completed) or (state == "FAILED" and completed):
        raise ValueError("Inconsistent weighted response status.")
    return response


def face_driver_display_data(data, rows, field):
    """Flat face colors by duplicating display corners only; calculation unchanged."""
    validate_mesh_data(data)
    coordinates = {row["id"]: row["xyz"] for row in data["vertices"]}
    samples = {row["id"]: row[field] for row in rows}
    vertices, faces, values, source_ids = [], [], {}, []
    for face in data["faces"]:
        corners = []
        for key in face["vertices"]:
            display_id = len(vertices)
            vertices.append({"id": display_id, "xyz": coordinates[key].copy()})
            values[display_id] = samples.get(face["id"])
            source_ids.append(key)
            corners.append(display_id)
        faces.append({"id": face["id"], "vertices": corners})
    return {"vertices": vertices, "faces": faces}, values, source_ids


def _validate_field_response(response, request):
    stages, status = response.get("stages"), response.get("status")
    if response.get("mode") != MOLA_FIELD_MODE or not isinstance(stages, list) or len(stages) > 3:
        raise ValueError("Invalid MolaFieldStudy generation list.")
    if status not in ("SUCCESS", "PARTIAL", "FAILED") or (status == "SUCCESS" and len(stages) != 3) or (status == "PARTIAL" and not stages) or (status == "FAILED" and stages):
        raise ValueError("Inconsistent MolaFieldStudy status/generations.")
    eligible = response.get("eligible_faces")
    roots = {row["id"] for row in request["mesh"]["faces"]}
    if not isinstance(eligible, list) or len(set(eligible)) != len(eligible) or not set(eligible) <= roots:
        raise ValueError("Invalid original eligible face IDs.")
    rows = response.get("drivers", {}).get("faces", [])
    if [row["id"] for row in rows] != eligible:
        raise ValueError("Original face driver values must align with eligibility.")
    if any(not 0 <= row[field] <= 1 for row in rows for field in ("height_driver", "taper_driver")):
        raise ValueError("Invalid normalized face driver.")
    previous_mesh, selected = request["mesh"], eligible
    for generation, stage in enumerate(stages, 1):
        if stage.get("generation") != generation or stage.get("validated") is not True or stage.get("processed_faces") != selected:
            raise ValueError("MolaFieldStudy must recurse on only the previous generation's caps.")
        mesh = validate_mesh_data(stage.get("mesh"))
        if stage.get("vertex_count") != len(mesh["vertices"]) or stage.get("face_count") != len(mesh["faces"]):
            raise ValueError("Field study output counts do not match mesh.")
        if stage.get("input_vertex_count") != len(previous_mesh["vertices"]) or stage.get("input_face_count") != len(previous_mesh["faces"]):
            raise ValueError("Field study input counts do not match prior mesh.")
        params = stage.get("parameters", [])
        if [row["id"] for row in params] != selected or any(row["root_face"] not in eligible for row in params):
            raise ValueError("Recursive parameters do not align with selected faces/roots.")
        caps = stage.get("cap_faces")
        if not isinstance(caps, list) or len(caps) != len(selected) or len(set(caps)) != len(caps):
            raise ValueError("Each processed face must have exactly one new cap.")
        roles = stage.get("face_roles", [])
        if [row["id"] for row in roles] != [row["id"] for row in mesh["faces"]]:
            raise ValueError("Face roles must cover the displayed generation.")
        actual_caps = [row["id"] for row in roles if row["role"] == "cap" and row["generation"] == generation]
        if caps != actual_caps:
            raise ValueError("Recursion cap IDs disagree with generated roles.")
        for domain in ("vertices", "faces"):
            entries = stage.get("lineage", {}).get(domain, [])
            if [row["id"] for row in entries] != [row["id"] for row in mesh[domain]]:
                raise ValueError("Recursive immediate-parent lineage must cover output IDs.")
            parent_ids = {row["id"] for row in previous_mesh[domain]}
            if any(not entry["parents"] or any(ref["id"] not in parent_ids for ref in entry["parents"]) for entry in entries):
                raise ValueError("Recursive lineage parent is absent from the immediate input.")
        if stage.get("budget", {}).get("status") != "SAFE" or stage.get("lineage_coverage") != []:
            raise ValueError("Only budget-safe generations with verified coverage may be displayed.")
        previous_mesh, selected = mesh, caps
    return response


def _validate_surface_response(response, request):
    if response.get("mode") != MOLA_SURFACE_MODE:
        raise ValueError("Invalid surface study mode.")
    _validate_field_response({**response, "mode": MOLA_FIELD_MODE, "status": response.get("raw_status")}, request)
    derivatives = response.get("derivatives")
    if not isinstance(derivatives, list) or [row.get("source_generation") for row in derivatives] != [1, 3]:
        raise ValueError("Surface derivatives must refer separately to raw G1 and G3.")
    stages = {stage["generation"]: stage for stage in response["stages"]}
    for row in derivatives:
        if row.get("source_run") != request["run_id"] or row.get("terminal_derivative") is not True or row.get("semantic_lineage") != "NOT IMPLEMENTED":
            raise ValueError("CC1 requires terminal source association and explicit unimplemented semantic lineage.")
        if any(name in row for name in ("fields", "lineage", "face_roles", "cap_faces", "parameters")):
            raise ValueError("Raw semantic data cannot be reassigned to CC1 topology.")
        status = row.get("status")
        if status not in ("SUCCESS", "PENDING", "BLOCKED", "UNAVAILABLE", "REJECTED"):
            raise ValueError("Invalid CC1 derivative status.")
        if status != "SUCCESS":
            if "mesh" in row or row.get("validated") is True or not isinstance(row.get("reason"), str) or not row["reason"]:
                raise ValueError("An incomplete derivative cannot contain display geometry.")
            continue
        mesh = validate_mesh_data(row.get("mesh"))
        stage = stages.get(row["source_generation"])
        if stage is None or row.get("validated") is not True or row.get("scheme") != "catmullclark" or row.get("level") != 1:
            raise ValueError("Only a validated one-level CC derivative of an available raw stage is allowed.")
        if row.get("input", {}).get("vertex_count") != stage["vertex_count"] or row.get("input", {}).get("face_count") != stage["face_count"]:
            raise ValueError("CC1 source counts do not match its raw stage.")
        counts, budget = row.get("output", {}), row.get("budget", {})
        if counts.get("vertex_count") != len(mesh["vertices"]) or counts.get("face_count") != len(mesh["faces"]) or any(len(face["vertices"]) != 4 for face in mesh["faces"]):
            raise ValueError("CC1 output counts/topology do not match the display mesh.")
        if budget.get("status") != "SAFE" or budget.get("estimated_output_vertices") != len(mesh["vertices"]) or budget.get("estimated_output_faces") != len(mesh["faces"]):
            raise ValueError("CC1 must match its safe preflight estimate.")
        if row.get("boundary_preservation", {}).get("status") != "PASS" or row.get("components_before") != row.get("components_after"):
            raise ValueError("CC1 boundary/component verification did not pass.")
    status = response.get("status")
    if status not in ("SUCCESS", "PARTIAL", "FAILED") or (status == "PARTIAL" and not stages) or (status == "FAILED" and stages):
        raise ValueError("Inconsistent surface study status.")
    if status == "SUCCESS" and (response["raw_status"] != "SUCCESS" or any(row["status"] != "SUCCESS" for row in derivatives)):
        raise ValueError("Surface SUCCESS requires both completed CC1 comparisons and the raw recipe.")
    return response


def _validate_visual_response(response, request):
    variants, recipes = response.get("variants"), response.get("recipes")
    if response.get("mode") != VISUAL_MODE or not isinstance(variants, list) or not isinstance(recipes, list) or not 1 <= len(recipes) <= 3:
        raise ValueError("Invalid visual prototype alternatives.")
    ids = [row.get("id") for row in recipes]
    if len(set(ids)) != len(ids) or any(key not in ("A", "B", "C") for key in ids):
        raise ValueError("Invalid fixed visual study recipe IDs.")
    if len(variants) > len(recipes) or len({row.get("id") for row in variants}) != len(variants):
        raise ValueError("Duplicate or extra visual candidates.")
    for row in variants:
        if row.get("id") not in ids or row.get("validated") is not True or row.get("status") not in ("SUCCESS", "PARTIAL"):
            raise ValueError("Only validated available visual candidates can be displayed.")
        steps = row.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
            raise ValueError("Visual candidates require bounded completed operations.")
        operators = {"A": ["COMPAS.quad", "CHESHIRE.normal_displacement", "CHESHIRE.normal_displacement", "COMPAS.catmullclark"],
                     "B": ["Mola.ExtrudeTapered"] * 3, "C": ["COMPAS.quad"] + ["Mola.ExtrudeTapered"] * 3}[row["id"]]
        if [step.get("operator") for step in steps] != operators[:len(steps)] or (row["status"] == "SUCCESS" and len(steps) != len(operators)):
            raise ValueError("Visual result must follow its fixed recipe; incomplete execution is PARTIAL.")
        previous = request["mesh"]
        for index, step in enumerate(steps, 1):
            mesh = validate_mesh_data(step.get("mesh"))
            if step.get("index") != index or step.get("validated") is not True or step.get("budget", {}).get("status") != "SAFE":
                raise ValueError("Visual operations must be consecutive validated budget-safe checkpoints.")
            if step.get("input_vertex_count") != len(previous["vertices"]) or step.get("input_face_count") != len(previous["faces"]):
                raise ValueError("Visual operation input counts disagree with its immediate source.")
            if step.get("inspection", {}).get("vertex_count") != len(mesh["vertices"]) or step.get("inspection", {}).get("face_count") != len(mesh["faces"]):
                raise ValueError("Visual operation counts disagree with actual geometry.")
            terminal = step.get("terminal_derivative")
            if terminal is not None:
                if index != len(steps) or terminal.get("source_run") != request["run_id"] or terminal.get("source_candidate") != row["id"] or terminal.get("source_step") != index - 1:
                    raise ValueError("CC1 must be terminal with an explicit source-stage association.")
                if terminal.get("semantic_lineage") != "NOT IMPLEMENTED" or any(name in step for name in ("lineage", "fields", "face_roles")):
                    raise ValueError("Terminal CC topology cannot receive invented semantic lineage or stale fields.")
                if terminal.get("boundary_preservation", {}).get("status") != "PASS" or terminal.get("scheme") != "catmullclark" or terminal.get("level") != 1:
                    raise ValueError("Terminal surface policy was not verified.")
            else:
                if step.get("lineage_coverage") != []:
                    raise ValueError("Missing visual operation lineage verification.")
                for domain in ("vertices", "faces"):
                    entries = step.get("lineage", {}).get(domain, [])
                    if [entry["id"] for entry in entries] != [item["id"] for item in mesh[domain]]:
                        raise ValueError("Visual lineage must cover actual output IDs.")
                    parents = {item["id"] for item in previous[domain]}
                    if any(not entry["parents"] or any(ref["id"] not in parents for ref in entry["parents"]) for entry in entries):
                        raise ValueError("Visual lineage must refer to the immediate input.")
            previous = mesh
        if row.get("mesh") != previous or row.get("vertex_count") != len(previous["vertices"]) or row.get("face_count") != len(previous["faces"]):
            raise ValueError("Visual result must be its last validated checkpoint.")
        expected = "NOT IMPLEMENTED" if steps[-1].get("terminal_derivative") else "AVAILABLE_IN_STEPS"
        if row.get("semantic_lineage") != expected:
            raise ValueError("Visual semantic lineage status is inconsistent.")
    status = response.get("status")
    if status not in ("SUCCESS", "PARTIAL", "FAILED") or (status == "FAILED" and variants) or (status == "PARTIAL" and not variants):
        raise ValueError("Invalid visual study status.")
    if status == "SUCCESS" and (len(variants) != len(recipes) or any(row["status"] != "SUCCESS" for row in variants)):
        raise ValueError("Visual SUCCESS requires all requested alternatives completed.")
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
