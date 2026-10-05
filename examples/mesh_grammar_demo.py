"""Real external-worker control run; Rhino selection/display remain host checks."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))

from compas.datastructures import Mesh
from compas.geometry import Box
from cheshire import save_mesh
from cheshire_worker import mesh_from_data, mesh_to_data
from exchange import read_json, validate_request, validate_response, write_json_atomic
from worker_process import worker_launch_options


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    run_id = str(uuid4())
    directory = args.output_directory or ROOT / "output/task08" / ("control_" + run_id)
    directory.mkdir(parents=True, exist_ok=False)
    control = Mesh.from_shape(Box(2, 3, 4))  # Existing tests/conftest.py box fixture.
    request = validate_request({"protocol": 1, "run_id": run_id,
                                "source": {"document_serial": 0, "object_id": "programmatic-box-control"},
                                "strength": 0.01, "mesh": mesh_to_data(control)})
    write_json_atomic(directory / "request.json", request)
    launch = worker_launch_options(ROOT, directory / "request.json", directory / "response.json")
    command = launch["args"]
    try:
        completed = subprocess.run(**launch, capture_output=True, text=True, timeout=60)
        log = {"command": command, "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
    except subprocess.TimeoutExpired as error:
        log = {"command": command, "exit_code": None, "timeout_seconds": 60,
               "stdout": (error.stdout or b"").decode("utf-8"), "stderr": (error.stderr or b"").decode("utf-8")}
    write_json_atomic(directory / "worker_command.json", log)
    response = validate_response(read_json(directory / "response.json"), request)
    if log.get("timeout_seconds") or log["exit_code"] != 0:
        response["status"] = "PARTIAL" if response["stages"] else "FAILED"
        response["reason"] = "Worker interrupted; only validated completed checkpoints retained."
        write_json_atomic(directory / "response.json", response)
    save_mesh(control, directory / "G0.obj")
    for stage in response["stages"]:
        if stage["generation"] in (1, 2, 4) or stage is response["stages"][-1]:
            save_mesh(mesh_from_data(stage["mesh"]), directory / f"G{stage['generation']}.obj")
    if response["stages"]:
        save_mesh(mesh_from_data(response["driver"]["mesh"]), directory / "G1_driver.obj")
        write_json_atomic(directory / "driver_field.json", {**response["driver"], "mesh_file": "G1_driver.obj",
                          "alignment": "values/raw_values use the mesh's explicit IDs and OBJ vertex-list order"})
    summary = {"status": response["status"], "reason": response["reason"], "output_directory": str(directory),
               "rhino_execution": "PENDING — this command verifies the real worker, not Rhino host display",
               "runtime_identity": response["runtime_identity"],
               "recipe": response["recipe"],
               "stages": [{key: value for key, value in stage.items() if key not in {"mesh", "lineage", "fields"}}
                          for stage in response["stages"]]}
    write_json_atomic(directory / "experiment_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if response["status"] in ("SUCCESS", "PARTIAL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
