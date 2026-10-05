"""Exactly three independent Mola variants of the original input, no Rhino imports."""

from copy import deepcopy
from time import perf_counter

from cheshire import FieldSpec, inherit_fields, validate_lineage_coverage
from cheshire.mola import eligible_planar_faces, extrude_tapered_once
from cheshire_worker import RUNTIME_IDENTITY, lineage_data, mesh_from_data, mesh_to_data
from exchange import MOLA_MODE, MOLA_VARIANTS, TIMEOUT_SECONDS, finite_json, validate_request, validate_response


def run_mola_study(request, publish=None):
    validate_request(request)
    start = perf_counter()
    source = mesh_from_data(request["mesh"])
    selected, excluded = eligible_planar_faces(source)
    if isinstance(request["selected_faces"], list):
        selected = request["selected_faces"].copy()
        excluded = [{"id": key, "reason": "Not explicitly selected."} for key in source.faces() if key not in selected]
    response = {"protocol": 1, "mode": MOLA_MODE, "run_id": request["run_id"], "source": deepcopy(request["source"]),
                "status": "FAILED", "reason": None, "variants": [], "selected_faces": selected,
                "excluded_faces": excluded, "runtime_identity": deepcopy(RUNTIME_IDENTITY),
                "operator": "FaceSubdivision.ExtrudeTapered", "height_units": "input mesh coordinate units",
                "selection_policy": request["selected_faces"], "study_settings": "CHESHIRE settings, not author parameters"}
    specs = [FieldSpec("source_face", "face", "categorical", "CATEGORICAL"),
             FieldSpec("face_area", "face", "scalar", "RECOMPUTE")]
    fields = {"source_face": {key: key for key in source.faces()}}
    for name, ratio, fraction in MOLA_VARIANTS:
        step_start = perf_counter()
        try:
            if perf_counter()-start >= TIMEOUT_SECONDS:
                raise ValueError("Whole-worker 60-second study limit reached.")
            result = extrude_tapered_once(source, selected_faces=selected, height_ratio=ratio,
                                         fraction=fraction, dll_path=request["mola_dll"])
            inherited = inherit_fields(result.lineage, fields, specs)
            coverage = validate_lineage_coverage(source, result.mesh, result.lineage)
            if coverage or any(inherited.unresolved_counts.values()) or mesh_to_data(source) != request["mesh"]:
                raise ValueError("Incomplete lineage/inheritance or mutated original input.")
            # Fresh geometry-derived field, explicitly measured on each result.
            areas = [{"id": key, "value": result.mesh.face_area(key)} for key in result.mesh.faces()]
            finite_json(areas)
            variant = {"name": name, "height_ratio": ratio, "fraction": fraction,
                       "mesh": mesh_to_data(result.mesh), "validated": True,
                       "vertex_count": result.counts["output_vertices"], "face_count": result.counts["output_faces"],
                       "counts": result.counts, "backend": result.backend,
                       "parameters": [{"id": key, **values} for key, values in result.parameters.items()],
                       "face_roles": [{"id": key, "role": role} for key, role in result.face_roles.items()],
                       "lineage": lineage_data(result.lineage), "lineage_coverage": coverage,
                       "fields": {"source_face": [{"id": key, "value": v} for key, v in inherited.values["source_face"].items()],
                                  "face_area": areas}, "recompute_fields": inherited.recompute_fields,
                       "warnings": result.warnings, "elapsed_seconds": perf_counter()-step_start}
            response["variants"].append(variant)
            response["status"], response["reason"] = "PARTIAL", "Validated variant checkpoint; study still running."
        except Exception as error:
            response["status"] = "PARTIAL" if response["variants"] else "FAILED"
            response["reason"] = f"{name} stopped: {type(error).__name__}: {error}"
            break
        if publish is not None:
            publish(validate_response(response, request))
    else:
        response["status"], response["reason"] = "SUCCESS", None
    response["elapsed_seconds"] = perf_counter()-start
    validate_response(response, request)
    if publish is not None:
        publish(response)
    return response
