"""Fixed G1/G2/G3 face-field experiment: only the latest caps recurse."""

from copy import deepcopy
from math import fsum, hypot, isfinite, sqrt
from time import perf_counter

from cheshire import ExecutionBudget, FieldSpec, check_execution_budget, inherit_fields, validate_lineage_coverage
from cheshire.mola import eligible_planar_faces, extrude_tapered_once
from cheshire_worker import RUNTIME_IDENTITY, lineage_data, mesh_from_data, mesh_to_data
from exchange import MAX_STAGE_COUNT, TIMEOUT_SECONDS, finite_json, validate_request, validate_response

MODE = "MOLA_FIELD_STUDY"
HEIGHT_SCALES = (1.0, 0.65, 0.40)
TAPER_OFFSETS = (0.0, 0.10, -0.05)
SPECS = [FieldSpec("root_face", "face", "categorical", "CATEGORICAL"),
         FieldSpec("height_driver", "face", "scalar", "CONTINUOUS"),
         FieldSpec("taper_driver", "face", "scalar", "CONTINUOUS"),
         FieldSpec("height_ratio", "face", "scalar", "CONTINUOUS"),
         FieldSpec("original_fraction", "face", "scalar", "CONTINUOUS"),
         FieldSpec("face_area", "face", "scalar", "RECOMPUTE")]


def _normalized(values, threshold, name):
    if not values:
        return {}, [f"{name}: no eligible original faces."]
    low, high = min(values.values()), max(values.values())
    if high-low <= threshold:
        return {key: 0.5 for key in values}, [f"{name}: effectively zero range; constant 0.5."]
    return {key: min(1.0, max(0.0, (v-low)/(high-low))) for key, v in values.items()}, []


def original_face_fields(mesh, eligible):
    """Separate original-centroid Z and XZ radial fields, in world coordinates."""
    xyz = [mesh.vertex_coordinates(k) for k in mesh.vertices()]
    low = [min(p[a] for p in xyz) for a in range(3)]
    high = [max(p[a] for p in xyz) for a in range(3)]
    center = [low[a]/2+high[a]/2 for a in range(3)]
    diagonal = hypot(*(high[a]-low[a] for a in range(3)))
    if not isfinite(diagonal):
        raise ValueError("Unrepresentable input bounding-box scale.")
    # Translation-independent geometric threshold, plus a floating precision
    # floor for large world coordinates. No clipping percentiles or noise.
    threshold = max(diagonal*1e-9, max(abs(v) for p in xyz for v in p)*2e-15)
    centroids = {key: [fsum(p[a]/len(mesh.face_vertices(key)) for p in mesh.face_coordinates(key))
                       for a in range(3)] for key in eligible}
    z = {key: point[2] for key, point in centroids.items()}
    distances = {key: hypot(point[0]-center[0], point[2]-center[2]) for key, point in centroids.items()}
    height, hw = _normalized(z, threshold, "height_driver")
    taper, tw = _normalized(distances, threshold, "taper_driver")
    rows = [{"id": key, "centroid": centroids[key], "xz_distance": distances[key],
             "height_driver": height[key], "taper_driver": taper[key],
             "height_ratio": 0.05+0.30*height[key], "original_fraction": 0.15+0.60*taper[key]} for key in eligible]
    finite_json(rows)
    return {"faces": rows, "bbox_center": center, "zero_range_tolerance": threshold,
            "height_formula": "clamp((original_centroid_z-min_z)/(max_z-min_z),0,1); ratio=0.05+0.30*driver",
            "taper_formula": "normalize(original_centroid XZ distance from input bbox center); fraction=0.15+0.60*driver",
            "constant_policy": "0.5 when the eligible range is effectively zero", "warnings": hw+tw}


def _range(values):
    values = list(values)
    return [min(values), max(values)] if values else [None, None]


def run_mola_field_study(request, publish=None, *, budget=None):
    """Bounded study; a failed/excessive generation retains prior checkpoints."""
    validate_request(request)
    start = perf_counter()
    original = mesh_from_data(request["mesh"])
    eligible, excluded = eligible_planar_faces(original)
    drivers = original_face_fields(original, eligible)
    response = {"protocol": 1, "mode": MODE, "run_id": request["run_id"], "source": deepcopy(request["source"]),
                "status": "FAILED", "reason": None, "stages": [], "eligible_faces": eligible, "excluded_faces": excluded,
                "drivers": drivers, "runtime_identity": deepcopy(RUNTIME_IDENTITY), "top_five_g1": [],
                "recipe": {"operator": "FaceSubdivision.ExtrudeTapered", "cap_top": True, "maximum_generations": 3,
                           "height_scales": list(HEIGHT_SCALES), "taper_offsets": list(TAPER_OFFSETS),
                           "taper_clamp": [0.05, 0.85], "height_units": "input mesh coordinate units",
                           "next_selection": "only the immediately previous generation's newly created caps",
                           "scope": "Synthetic geometric controls; no architectural/cultural meaning or global collision guarantee."}}
    budget = budget if budget is not None else ExecutionBudget(MAX_STAGE_COUNT, MAX_STAGE_COUNT, 3)
    fields = {"root_face": {key: key for key in original.faces()}}
    for name in ("height_driver", "taper_driver", "height_ratio", "original_fraction"):
        fields[name] = {key: None for key in original.faces()}
        fields[name].update({row["id"]: row[name] for row in drivers["faces"]})
    roles = {key: {"role": "original", "generation": 0} for key in original.faces()}
    mesh, selected = original, eligible.copy()
    for index, (height_scale, taper_offset) in enumerate(zip(HEIGHT_SCALES, TAPER_OFFSETS)):
        generation, step_start = index+1, perf_counter()
        try:
            if perf_counter()-start >= TIMEOUT_SECONDS:
                raise ValueError("Whole-worker 60-second study limit reached.")
            if not selected:
                raise ValueError("No eligible caps/faces to process; no ornament generated.")
            extra = sum(len(mesh.face_vertices(k)) for k in selected)
            assessment = check_execution_budget(budget, input_faces=mesh.number_of_faces(), input_vertices=mesh.number_of_vertices(),
                estimated_output_faces=mesh.number_of_faces()+extra, estimated_output_vertices=mesh.number_of_vertices()+extra,
                current_generation=index)
            response["next_budget"] = {"generation": generation, **assessment}
            if len(selected) > 1000:
                raise ValueError("Study selection exceeds the unchanged 1000-face cap; no truncation.")
            if assessment["status"] != "SAFE":
                raise ValueError("Generation blocked before Mola: " + " ".join(assessment["reasons"]))
            if index and any(roles[k] != {"role": "cap", "generation": index} for k in selected):
                raise ValueError("Recursion selection is not exclusively the previous generation's new caps.")
            ratios = {key: fields["height_ratio"][key]*height_scale for key in selected}
            fractions = {key: fields["original_fraction"][key] if index == 0 else
                         min(0.85, max(0.05, fields["original_fraction"][key]+taper_offset)) for key in selected}
            # Record actual current areas: never substitute an original area
            # or idealized (1-fraction)^2 estimate for a backend-generated cap.
            areas = {key: mesh.face_area(key) for key in selected}
            if any(not isfinite(a) or a <= 0 for a in areas.values()):
                raise ValueError("Selected current face area is invalid.")
            before = mesh_to_data(mesh)
            result = extrude_tapered_once(mesh, selected_faces=selected, height_ratio=ratios, fraction=fractions,
                dll_path=request["mola_dll"], budget=budget, source_is_result=bool(index))
            coverage = validate_lineage_coverage(mesh, result.mesh, result.lineage)
            inherited = inherit_fields(result.lineage, fields, SPECS)
            if coverage or mesh_to_data(mesh) != before or mesh_to_data(original) != request["mesh"]:
                raise ValueError("Incomplete lineage or changed source input.")
            # Excluded original faces intentionally have unavailable drivers.
            # Every selected descendant must retain the known ORIGINAL fields.
            next_caps, next_roles = [], {}
            for key, role in result.face_roles.items():
                if role == "unchanged":
                    next_roles[key] = roles[key].copy()
                else:
                    next_roles[key] = {"role": role, "generation": generation}
                    if any(inherited.values[name][key] is None for name in fields):
                        raise ValueError("A generated face lost its original driver/root lineage.")
                    if role == "cap":
                        next_caps.append(key)
            if len(next_caps) != len(selected):
                raise ValueError("Exactly one new cap per processed face is required.")
            params = []
            for parent, values in result.parameters.items():
                expected_height = ratios[parent]*sqrt(areas[parent])
                if abs(values["height"]-expected_height) > 1e-9*max(expected_height, 1e-300):
                    raise ValueError("Backend parameter height disagrees with measured current face area.")
                params.append({"id": parent, "root_face": fields["root_face"][parent],
                               "height_driver": fields["height_driver"][parent], "taper_driver": fields["taper_driver"][parent],
                               "original_height_ratio": fields["height_ratio"][parent],
                               "original_fraction": fields["original_fraction"][parent],
                               "current_face_area": areas[parent], "height_scale": height_scale, **values})
            fresh_areas = [{"id": k, "value": result.mesh.face_area(k)} for k in result.mesh.faces()]
            finite_json(fresh_areas)
            stage = {"generation": generation, "validated": True, "mesh": mesh_to_data(result.mesh),
                     "vertex_count": result.counts["output_vertices"], "face_count": result.counts["output_faces"],
                     "input_vertex_count": result.counts["input_vertices"], "input_face_count": result.counts["input_faces"],
                     "eligible_original_count": len(eligible), "excluded_original_count": len(excluded),
                     "processed_faces": selected.copy(), "caps_processed": len(selected) if index else 0,
                     "processed_face_count": len(selected), "cap_faces": next_caps,
                     "height_driver_range": _range(row["height_driver"] for row in params),
                     "taper_driver_range": _range(row["taper_driver"] for row in params),
                     "height_range": _range(row["height"] for row in params), "fraction_range": _range(fractions.values()),
                     "parameters": params, "face_roles": [{"id": k, **v} for k, v in next_roles.items()],
                     "fields": {**{name: [{"id": k, "value": v} for k, v in mapping.items()] for name, mapping in inherited.values.items()},
                                "face_area": fresh_areas},
                     "lineage": lineage_data(result.lineage), "lineage_coverage": coverage,
                     "recompute_fields": inherited.recompute_fields, "backend": result.backend,
                     "budget": assessment, "warnings": result.warnings+inherited.warnings, "elapsed_seconds": perf_counter()-step_start}
            if index == 0:
                response["top_five_g1"] = sorted([{key: row[key] for key in
                    ("root_face", "height_driver", "taper_driver", "height", "fraction")} for row in params],
                    key=lambda row: (-row["height"], row["root_face"]))[:5]
            response["stages"].append(stage)
            mesh, selected, fields, roles = result.mesh, next_caps, inherited.values, next_roles
            response["status"], response["reason"] = "PARTIAL", "Validated generation checkpoint; study still running."
        except Exception as error:
            response["status"] = "PARTIAL" if response["stages"] else "FAILED"
            response["reason"] = f"G{generation} stopped: {type(error).__name__}: {error}"
            break
        if publish is not None:
            publish(validate_response(response, request))
    else:
        response["status"], response["reason"] = "SUCCESS", None
    response["elapsed_seconds"] = perf_counter()-start
    hr = _range(row["height_driver"] for row in drivers["faces"])
    tr = _range(row["taper_driver"] for row in drivers["faces"])
    response["variation_assessment"] = "Effectively uniform drivers; visually weak study." if (
        not eligible or (hr[0] == hr[1] and tr[0] == tr[1])) else "Non-uniform original drivers; inspect retained geometry for visual strength."
    response["rhino_host_status"] = "PENDING for MolaFieldStudy; existing modes user-confirmed working."
    validate_response(response, request)
    if publish is not None:
        publish(response)
    return response
