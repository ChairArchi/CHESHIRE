"""Unchanged MolaFieldStudy followed by two independent terminal CC1 copies."""

from time import perf_counter

from cheshire.surface import assess_catmull_clark, catmull_clark_once
from cheshire_worker import mesh_from_data, mesh_to_data
from exchange import MOLA_FIELD_MODE, MOLA_SURFACE_MODE, TIMEOUT_SECONDS, validate_request, validate_response
from mola_field_study import run_mola_field_study


def compare_raw_stages(raw, request, publish=None, *, budget=None, start=None):
    """Also supports an explicitly identified successful raw result in examples.

    Raw records are read only. Derivatives have source-stage association, with
    no reassignment of roles, fields or lineage to their changed topology.
    """
    start = perf_counter() if start is None else start
    validate_request(request)
    validate_response(raw, {**request, "mode": MOLA_FIELD_MODE})
    response = _comparison_response(raw)
    stages = {stage["generation"]: stage for stage in raw["stages"]}
    for record in response["derivatives"]:
        generation = record["source_generation"]
        step_start = perf_counter()
        stage = stages.get(generation)
        if stage is None:
            record.update(status="UNAVAILABLE", reason=f"Raw G{generation} was not reached.")
        else:
            try:
                if perf_counter() - start >= TIMEOUT_SECONDS:
                    raise ValueError("Whole-worker 60-second limit reached before CC1.")
                data = stage["mesh"]
                edges = {tuple(sorted((u, v))) for face in data["faces"]
                         for u, v in zip(face["vertices"], face["vertices"][1:] + face["vertices"][:1])}
                assessment = assess_catmull_clark(vertices=len(data["vertices"]), edges=len(edges),
                    faces=len(data["faces"]), corners=sum(len(face["vertices"]) for face in data["faces"]), budget=budget)
                record["budget"] = assessment
                if assessment["status"] != "SAFE":
                    record.update(status="BLOCKED", reason="Before copying/subdivision: " + " ".join(assessment["reasons"]))
                else:
                    result = catmull_clark_once(mesh_from_data(data), budget=budget)
                    record.update(result.metadata)
                    record.update(status="SUCCESS", reason=None, validated=True, mesh=mesh_to_data(result.mesh))
            except Exception as error:
                record.update(status="REJECTED", reason=f"{type(error).__name__}: {error}")
        record["elapsed_seconds"] = perf_counter() - step_start
        response["elapsed_seconds"] = perf_counter() - start
        if publish is not None:
            publish(validate_response(response, request))
    complete = raw["status"] == "SUCCESS" and all(row["status"] == "SUCCESS" for row in response["derivatives"])
    response["status"] = "SUCCESS" if complete else ("PARTIAL" if raw["stages"] else "FAILED")
    reasons = [f"G{row['source_generation']}+CC1 {row['status']}: {row['reason']}"
               for row in response["derivatives"] if row["status"] != "SUCCESS"]
    if raw.get("reason"):
        reasons.insert(0, raw["reason"])
    response["reason"] = "; ".join(reasons) or None
    response["elapsed_seconds"] = perf_counter() - start
    validate_response(response, request)
    if publish is not None:
        publish(response)
    return response


def _comparison_response(raw):
    return {**raw, "mode": MOLA_SURFACE_MODE, "raw_status": raw["status"],
            "status": "PARTIAL" if raw["stages"] else "FAILED",
            "reason": raw.get("reason") or "Raw checkpoints retained; terminal comparisons pending.",
            "rhino_host_status": "PENDING for MolaSurfaceStudy; MolaFieldStudy display is user-confirmed.",
            "derivatives": [{"source_run": raw["run_id"], "source_generation": generation,
                             "status": "PENDING", "reason": "Terminal CC1 not completed.",
                             "terminal_derivative": True, "semantic_lineage": "NOT IMPLEMENTED"}
                            for generation in (1, 3)]}


def run_mola_surface_study(request, publish=None):
    validate_request(request)
    start = perf_counter()
    def raw_checkpoint(raw):
        if publish is not None:
            publish(validate_response(_comparison_response(raw), request))
    # The existing recipe and all raw metadata remain owned by the old mode.
    raw = run_mola_field_study({**request, "mode": MOLA_FIELD_MODE}, publish=raw_checkpoint)
    return compare_raw_stages(raw, request, publish, start=start)
