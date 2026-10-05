"""Run the consolidated fixed recipes on an explicit saved original request."""

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
from exchange import VISUAL_MODE, read_json, validate_response, write_json_atomic
from local_settings import remembered_mola_path
from worker_process import worker_launch_options


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-request", type=Path, required=True)
    parser.add_argument("--dll", type=Path)
    args = parser.parse_args()
    dll = str(args.dll.resolve()) if args.dll else remembered_mola_path(ROOT)
    if dll is None:
        parser.error("Configure the existing DLL preference or provide the exact official standalone --dll path.")
    source = read_json(args.input_request)
    request = {"protocol": 1, "mode": VISUAL_MODE, "run_id": str(uuid4()), "source": deepcopy(source["source"]),
               "mesh": deepcopy(source["mesh"]), "mola_dll": dll, "selected_faces": "ALL_ELIGIBLE_PLANAR"}
    directory = ROOT / "output/task12" / request["run_id"]
    directory.mkdir(parents=True, exist_ok=False)
    write_json_atomic(directory / "request.json", request)
    with (directory / "worker_stdout.txt").open("w", encoding="utf-8") as stdout, \
         (directory / "worker_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.run(**worker_launch_options(ROOT, directory / "request.json", directory / "response.json"),
                                 stdout=stdout, stderr=stderr, timeout=60)
    if not (directory / "response.json").exists():
        raise RuntimeError((directory / "worker_stderr.txt").read_text() + "\nNo checkpoint; " + str(directory))
    response = validate_response(read_json(directory / "response.json"), request)
    save_mesh(mesh_from_data(request["mesh"]), directory / "ORIGINAL.obj")
    write_json_atomic(directory / "recipes.json", {"version": response["recipe_version"], "recipes": response["recipes"]})
    for row in response["variants"]:
        save_mesh(mesh_from_data(row["mesh"]), directory / (row["id"] + ".obj"))
        print(row["label"], row["status"], row["vertex_count"], "vertices /", row["face_count"], "faces;",
              f"{row['elapsed_seconds']:.3f}s;", row["reason"] or "completed", "lineage", row["semantic_lineage"])
    print(response["status"], response["reason"] or "Three actual candidates completed.")
    print("ACTUAL VISUAL PROTOTYPE: " + str(directory))
    if process.returncode or response["status"] == "FAILED":
        raise RuntimeError(response["reason"] or f"Worker exited {process.returncode}")


if __name__ == "__main__":
    main()
