"""Three fixed spatial studies, isolated from the working engine and recipes."""

from copy import deepcopy
from math import cos, exp, hypot, pi
from time import perf_counter

from cheshire import (ExecutionBudget, FieldSpec, check_execution_budget, displace_vertices_along_normals,
                      identity_lineage, inherit_fields, inspect_mesh, subdivide_quad_once,
                      validate_lineage_coverage, validate_mesh)
from cheshire.mola import eligible_planar_faces, extrude_tapered_once
from cheshire.surface import catmull_clark_once
from cheshire_worker import RUNTIME_IDENTITY, lineage_data, mesh_from_data, mesh_to_data
from exchange import MAX_STAGE_COUNT, MAX_STEPS, TIMEOUT_SECONDS, VISUAL_MODE, validate_request, validate_response


RECIPE_VERSION = "12.3"
RECIPES = [
    {"id": "A", "label": "A - CURVED RIBS", "layout": "Continuous winding ribs with a finer wave along their cores; no tiled face extrusion.",
     "order": ["global quad1 without smoothing", "broad ribbon normal field", "fine core normal field", "terminal CC1"],
     "parameters": {"ribbon_centers": [0.24, 0.76], "ribbon_sway": 0.09, "ribbon_period": 0.85,
                    "width": 0.105, "core_width": 0.052, "macro_strength": 0.030, "accent_strength": 0.004,
                    "accent_period": 0.12, "field_cutoff_widths": 2, "quad_levels": 1, "cc_levels": 1}},
    {"id": "B", "label": "B - CROWN FANS", "layout": "Separated crown/shoulder clusters; growth turns onto upward and outward side faces.",
     "order": ["cluster Mola", "cap and directional sides Mola", "new caps Mola"],
     "parameters": {"centers": [[0.17, 0.68], [0.83, 0.68], [0.36, 0.90], [0.64, 0.90]],
                    "radii": [0.14, 0.16], "height_ratios": [0.42, 0.30, 0.27], "fractions": [0.22, 0.48, 0.56],
                    "side_directions": ["world +Z", "world X away from bbox center"], "maximum_sides_per_parent": 2,
                    "side_height_ratio": 0.20, "side_cap_height_ratio": 0.18,
                    "side_policy": "Only cluster-perimeter sides against unselected original faces or naked edges; no internal neighboring-tile branches."}},
    {"id": "C", "label": "C - DIAGONAL TERRACES", "layout": "Mirrored diagonal bands; quad refinement precedes selective stepped relief and finer cap accents.",
     "order": ["global quad1 without smoothing", "diagonal band Mola", "narrow band caps Mola", "upper core caps Mola"],
     "parameters": {"chevron_slope": 0.72, "band_centers": [0.30, 0.66, 1.00], "width": 0.065,
                    "core_width": 0.038, "accent_min_z": 0.55, "height_ratios": [0.38, 0.34, 0.28],
                    "fractions": [0.16, 0.42, 0.60], "quad_levels": 1}},
]
SPECS = [FieldSpec("root_face", "face", "categorical", "CATEGORICAL"),
         FieldSpec("root_u", "face", "scalar", "CONTINUOUS"), FieldSpec("root_v", "face", "scalar", "CONTINUOUS"),
         FieldSpec("facade", "face", "scalar", "CONTINUOUS"), FieldSpec("region", "face", "categorical", "CATEGORICAL"),
         FieldSpec("source_u", "vertex", "scalar", "CONTINUOUS"), FieldSpec("source_v", "vertex", "scalar", "CONTINUOUS"),
         FieldSpec("source_facade", "vertex", "scalar", "CONTINUOUS"), FieldSpec("face_area", "face", "scalar", "RECOMPUTE")]


def ribbon_distance(u, v, parameters):
    shift = parameters["ribbon_sway"] * cos(2 * pi * v / parameters["ribbon_period"])
    return min(abs(u - (center + sign * shift)) for center, sign in zip(parameters["ribbon_centers"], (1, -1)))


def band_distance(u, v, parameters):
    coordinate = v + parameters["chevron_slope"] * abs(u - 0.5)
    return min(abs(coordinate - center) for center in parameters["band_centers"])


def _initial_fields(mesh, recipe):
    xyz = {key: mesh.vertex_coordinates(key) for key in mesh.vertices()}
    low = [min(p[a] for p in xyz.values()) for a in range(3)]
    extent = [max(p[a] for p in xyz.values()) - low[a] for a in range(3)]
    if extent[0] <= 0 or extent[2] <= 0:
        raise ValueError("Study requires nonzero world-X width and world-Z height; no automatic orientation.")
    uv = {key: [(p[0] - low[0]) / extent[0], (p[2] - low[2]) / extent[2]] for key, p in xyz.items()}
    fields = {"root_face": {key: key for key in mesh.faces()}, "root_u": {}, "root_v": {}, "facade": {}, "region": {},
              "source_u": {key: p[0] for key, p in uv.items()}, "source_v": {key: p[1] for key, p in uv.items()},
              "source_facade": {key: abs(mesh.vertex_normal(key)[1]) for key in mesh.vertices()}}
    p = recipe["parameters"]
    for key in mesh.faces():
        u, v = [sum(uv[k][a] for k in mesh.face_vertices(key)) / len(mesh.face_vertices(key)) for a in range(2)]
        facade = abs(mesh.face_normal(key)[1])
        if recipe["id"] == "A":
            region = "ribbon" if ribbon_distance(u, v, p) < p["width"] else "quiet"
        elif recipe["id"] == "B":
            region = "cluster" if min(((u - x) / p["radii"][0]) ** 2 + ((v - z) / p["radii"][1]) ** 2
                                      for x, z in p["centers"]) < 1 else "quiet"
        else:
            region = "diagonal" if band_distance(u, v, p) < p["width"] else "quiet"
        fields["root_u"][key], fields["root_v"][key], fields["facade"][key] = u, v, facade
        fields["region"][key] = region if facade > 0.85 else "quiet"
    return fields


def _face_uv(mesh, fields, key):
    return [sum(fields[name][k] for k in mesh.face_vertices(key)) / len(mesh.face_vertices(key))
            for name in ("source_u", "source_v")]


def run_visual_prototype(request, publish=None, *, recipes=None, budget=None):
    """Bounded fixed alternatives; every stage is checkpointed with actual geometry."""
    validate_request(request)
    start = perf_counter()
    original = mesh_from_data(request["mesh"])
    recipes = deepcopy(RECIPES if recipes is None else recipes)
    budget = budget if budget is not None else ExecutionBudget(MAX_STAGE_COUNT, MAX_STAGE_COUNT, MAX_STEPS)
    response = {"protocol": 1, "mode": VISUAL_MODE, "run_id": request["run_id"], "source": deepcopy(request["source"]),
                "status": "FAILED", "reason": None, "variants": [], "attempts": [], "recipe_version": RECIPE_VERSION,
                "recipes": recipes, "input_inspection": inspect_mesh(original), "runtime_identity": deepcopy(RUNTIME_IDENTITY),
                "rhino_host_status": "PENDING for VisualPrototype.",
                "limitations": ["World Z height and world Y facade orientation; no auto-alignment or welding.",
                                "No global collision/fabrication guarantee; inspect intersections and pinching.",
                                "CC1 is terminal; semantic lineage NOT IMPLEMENTED on that derivative."]}

    def checkpoint():
        response["status"] = "PARTIAL" if response["variants"] else "FAILED"
        response["reason"] = "Validated study checkpoint; remaining recipes/operations still pending."
        response["elapsed_seconds"] = perf_counter() - start
        if mesh_to_data(original) != request["mesh"]:
            raise ValueError("Original study input changed.")
        if publish is not None:
            publish(validate_response(response, request))

    for recipe in recipes:
        candidate = {"id": recipe["id"], "label": recipe["label"], "recipe": recipe, "status": "PARTIAL",
                     "reason": "Recipe still running.", "steps": [], "semantic_lineage": "AVAILABLE_IN_STEPS"}
        mesh, fields, roles = original, None, {key: {"role": "original", "created_step": 0} for key in original.faces()}
        last_caps, last_result = [], None
        candidate_start = perf_counter()

        def assessment(output_vertices, output_faces):
            if perf_counter() - start >= TIMEOUT_SECONDS:
                raise ValueError("Whole-worker 60-second limit reached before operation.")
            result = check_execution_budget(budget, input_faces=mesh.number_of_faces(), input_vertices=mesh.number_of_vertices(),
                estimated_output_faces=output_faces, estimated_output_vertices=output_vertices, current_generation=len(candidate["steps"]))
            if result["status"] != "SAFE":
                raise ValueError("Operation blocked before execution: " + " ".join(result["reasons"]))
            return result

        def record(output, operator, parameters, checked_budget, lineage=None, backend=None, exclusions=None, terminal=None):
            nonlocal mesh, fields, roles
            problems = validate_mesh(output)
            if problems or not output.is_valid() or not output.is_manifold():
                raise ValueError("Invalid study output: " + " ".join(problems))
            step = {"index": len(candidate["steps"]) + 1, "operator": operator, "parameters": parameters,
                    "input_vertex_count": mesh.number_of_vertices(), "input_face_count": mesh.number_of_faces(),
                    "mesh": mesh_to_data(output), "inspection": inspect_mesh(output), "budget": checked_budget,
                    "backend": backend, "excluded_selected_faces": exclusions or [], "validated": True}
            if lineage is not None:
                coverage = validate_lineage_coverage(mesh, output, lineage)
                inherited = inherit_fields(lineage, fields, SPECS)
                if coverage or any(inherited.unresolved_counts.values()):
                    raise ValueError("Study lost available lineage or source fields.")
                fields = inherited.values
                step.update(lineage=lineage_data(lineage), lineage_coverage=coverage,
                            fields={**{name: [{"id": key, "value": value} for key, value in values.items()] for name, values in fields.items()},
                                    "face_area": [{"id": key, "value": output.face_area(key)} for key in output.faces()]},
                            face_roles=[{"id": key, **roles[key]} for key in output.faces()], recompute_fields=inherited.recompute_fields)
            else:
                step["terminal_derivative"] = terminal
                candidate["semantic_lineage"] = "NOT IMPLEMENTED"
            mesh = output
            candidate["steps"].append(step)
            candidate.update(mesh=step["mesh"], validated=True, vertex_count=mesh.number_of_vertices(), face_count=mesh.number_of_faces())
            if candidate not in response["variants"]:
                response["variants"].append(candidate)
            checkpoint()

        def mola(proposed, ratio, fraction, selection_rule):
            nonlocal last_caps, last_result, roles
            proposed = sorted(set(proposed))
            eligible, excluded = eligible_planar_faces(mesh)
            eligible = set(eligible)
            selected = [key for key in proposed if key in eligible]
            exclusions = [row for row in excluded if row["id"] in set(proposed)]
            if not selected:
                raise ValueError("Spatial/role selection has no eligible planar faces; no fallback or repair.")
            if len(selected) > 1000:
                raise ValueError("Selection exceeds unchanged 1000-face limit; no truncation.")
            extra = sum(len(mesh.face_vertices(key)) for key in selected)
            checked = assessment(mesh.number_of_vertices() + extra, mesh.number_of_faces() + extra)
            actual_ratios = {key: ratio[key] for key in selected} if isinstance(ratio, dict) else ratio
            result = extrude_tapered_once(mesh, selected_faces=selected, height_ratio=actual_ratios, fraction=fraction,
                                         dll_path=request["mola_dll"], budget=budget, source_is_result=bool(candidate["steps"]))
            roles = {key: roles[key] if role == "unchanged" else {"role": role, "created_step": len(candidate["steps"]) + 1}
                     for key, role in result.face_roles.items()}
            last_caps = [key for key, role in result.face_roles.items() if role == "cap"]
            last_result = result
            record(result.mesh, "Mola.ExtrudeTapered", {"selection_rule": selection_rule, "proposed_faces": proposed,
                   "selected_faces": selected, "height_ratio": ratio, "fraction": fraction, "cap_top": True,
                   "actual_parameters": [{"id": key, **value} for key, value in result.parameters.items()]},
                   checked, result.lineage, result.backend, exclusions)

        try:
            fields = _initial_fields(mesh, recipe)
            p = recipe["parameters"]
            if recipe["id"] in ("A", "C"):
                checked = assessment(mesh.number_of_vertices() + mesh.number_of_edges() + mesh.number_of_faces(),
                                     sum(len(mesh.face_vertices(key)) for key in mesh.faces()))
                result = subdivide_quad_once(mesh, budget=budget)
                roles = {key: {"role": "quad_child", "created_step": 1} for key in result.mesh.faces()}
                record(result.mesh, "COMPAS.quad", {"levels": 1, "nonplanar_policy": "reject"}, checked, result.lineage,
                       {"name": result.backend, "version": result.backend_version})
                if recipe["id"] == "C":
                    selected = [key for key in mesh.faces() if fields["facade"][key] > 0.85 and band_distance(*_face_uv(mesh, fields, key), p) < p["width"]]
            else:
                selected = [key for key in mesh.faces() if fields["region"][key] != "quiet"]
            if recipe["id"] == "A":
                for name, width, strength in (("broad ribbon", p["width"], p["macro_strength"]),
                                              ("fine core wave", p["core_width"], p["accent_strength"])):
                    values = {}
                    for key in mesh.vertices():
                        u, v = fields["source_u"][key], fields["source_v"][key]
                        distance = ribbon_distance(u, v, p)
                        value = exp(-(distance / width) ** 2) if distance < p["field_cutoff_widths"] * width else 0.0
                        if name == "fine core wave":
                            value *= 0.5 + 0.5 * cos(2 * pi * v / p["accent_period"])
                        values[key] = min(1.0, fields["source_facade"][key]) * value
                    selected_vertices = [key for key in mesh.vertices() if not mesh.is_vertex_on_boundary(key)]
                    checked = assessment(mesh.number_of_vertices(), mesh.number_of_faces())
                    result = displace_vertices_along_normals(mesh, values, selected_vertices, strength=strength)
                    record(result.mesh, "CHESHIRE.normal_displacement", {"field": name, "strength": strength,
                           "scale_mode": "bbox_diagonal", "selected_vertices": selected_vertices,
                           "values": [{"id": key, "value": value} for key, value in values.items()],
                           "moved_count": result.moved_count, "maximum_displacement": result.max_displacement,
                           "skipped_vertices": [{"id": key, "reason": reason} for key, reason in result.skipped_vertices.items()]}, checked, identity_lineage(mesh))
                checked = assessment(mesh.number_of_vertices() + mesh.number_of_edges() + mesh.number_of_faces(),
                                     sum(len(mesh.face_vertices(key)) for key in mesh.faces()))
                result = catmull_clark_once(mesh, budget=budget)
                record(result.mesh, "COMPAS.catmullclark", {"levels": 1}, checked, terminal={"source_run": request["run_id"],
                       "source_candidate": recipe["id"], "source_step": len(candidate["steps"]), **result.metadata})
            else:
                cluster_roots = set(selected)
                mola(selected, p["height_ratios"][0], p["fractions"][0], recipe["layout"])
            if recipe["id"] == "B":
                selected = last_caps.copy()
                by_parent = {}
                for key, role in last_result.face_roles.items():
                    if role == "side":
                        parent = last_result.lineage.face_parents[key][0].key
                        by_parent.setdefault(parent, []).append(key)
                for parent, sides in sorted(by_parent.items()):
                    sides = [key for key in sides if not any(neighbor is not None and neighbor != parent and neighbor in cluster_roots
                             for neighbor in original.edge_faces(tuple(mesh.face_vertices(key)[:2])))]
                    if not sides:
                        continue
                    sign = -1 if fields["root_u"][sides[0]] < 0.5 else 1
                    for axis, direction in ((2, 1), (0, sign)):
                        side = max(sides, key=lambda key: (direction * mesh.face_normal(key)[axis], -key))
                        if direction * mesh.face_normal(side)[axis] > 0.15:
                            selected.append(side)
            elif recipe["id"] == "C":
                selected = [key for key in last_caps if band_distance(*_face_uv(mesh, fields, key), p) < p["core_width"]]
            if recipe["id"] != "A":
                ratios = {key: p["height_ratios"][1] if key in last_caps else p["side_height_ratio"] for key in selected} if recipe["id"] == "B" else p["height_ratios"][1]
                primary_caps = set(last_caps)
                mola(selected, ratios, p["fractions"][1], recipe["order"][1 if recipe["id"] != "C" else 2])
                selected = last_caps if recipe["id"] == "B" else [key for key in last_caps if fields["root_v"][key] > p["accent_min_z"]]
                ratios = {key: p["height_ratios"][2] if last_result.lineage.face_parents[key][0].key in primary_caps else p["side_cap_height_ratio"] for key in selected} if recipe["id"] == "B" else p["height_ratios"][2]
                mola(selected, ratios, p["fractions"][2], recipe["order"][-1])
            candidate["status"], candidate["reason"] = "SUCCESS", None
        except Exception as error:
            candidate["reason"] = f"{type(error).__name__}: {error}"
            candidate["status"] = "PARTIAL" if candidate["steps"] else "FAILED"
        candidate["elapsed_seconds"] = perf_counter() - candidate_start
        response["attempts"].append({"id": recipe["id"], "status": candidate["status"], "reason": candidate["reason"]})
        checkpoint()
    response["status"] = "SUCCESS" if len(response["variants"]) == len(recipes) and all(row["status"] == "SUCCESS" for row in response["variants"]) else ("PARTIAL" if response["variants"] else "FAILED")
    response["reason"] = None if response["status"] == "SUCCESS" else "; ".join(f"{row['id']}: {row['reason']}" for row in response["attempts"] if row["status"] != "SUCCESS")
    response["elapsed_seconds"] = perf_counter() - start
    validate_response(response, request)
    if publish is not None:
        publish(response)
    return response
