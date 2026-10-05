"""Real isolated-worker G1/G3 comparison, using an explicit original request."""

import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rhino"))

from cheshire import save_mesh
from cheshire_worker import mesh_from_data
from exchange import MOLA_SURFACE_MODE, read_json, validate_response, write_json_atomic
from local_settings import remembered_mola_path
from worker_process import worker_launch_options


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-request", type=Path, required=True, help="Saved ORIGINAL request; not a generated response.")
    parser.add_argument("--dll", type=Path, help="Official external DLL, otherwise reuse the ignored preference.")
    args = parser.parse_args()
    dll = str(args.dll.resolve()) if args.dll else remembered_mola_path(ROOT)
    if dll is None:
        parser.error("Configure the existing local DLL preference or supply --dll.")
    source = read_json(args.input_request)
    request = {"protocol": 1, "mode": MOLA_SURFACE_MODE, "run_id": str(uuid4()),
               "source": deepcopy(source["source"]), "mesh": deepcopy(source["mesh"]),
               "mola_dll": dll, "selected_faces": "ALL_ELIGIBLE_PLANAR"}
    directory = ROOT / "output/task11" / request["run_id"]
    directory.mkdir(parents=True, exist_ok=False)
    write_json_atomic(directory / "request.json", request)
    with (directory / "worker_stdout.txt").open("w", encoding="utf-8") as stdout, \
         (directory / "worker_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.run(**worker_launch_options(ROOT, directory / "request.json", directory / "response.json"),
                                 stdout=stdout, stderr=stderr, timeout=60)
    if not (directory / "response.json").is_file():
        raise RuntimeError((directory / "worker_stderr.txt").read_text() + "\nNo response; " + str(directory))
    response = validate_response(read_json(directory / "response.json"), request)
    save_mesh(mesh_from_data(request["mesh"]), directory / "G0.obj")
    for stage in response["stages"]:
        save_mesh(mesh_from_data(stage["mesh"]), directory / f"G{stage['generation']}_RAW.obj")
    for row in response["derivatives"]:
        label = f"G{row['source_generation']}_CC1"
        if row["status"] == "SUCCESS":
            save_mesh(mesh_from_data(row["mesh"]), directory / (label + ".obj"))
            print(label, row["output"]["vertex_count"], "vertices /", row["output"]["face_count"], "faces;",
                  row["elapsed_seconds"], "s; boundary", row["boundary_preservation"],
                  "displacement", row["retained_vertex_displacement"])
        else:
            print(label, row["status"], row["reason"])
    print(response["status"], response["reason"] or "Both comparisons complete.")
    print("ACTUAL MOLA SURFACE STUDY: " + str(directory))
    if process.returncode or response["status"] == "FAILED":
        raise RuntimeError(response["reason"] or f"Worker exited {process.returncode}")


if __name__ == "__main__":
    main()
