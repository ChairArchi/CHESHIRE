"""Actual external-worker smoke; provide the official DLL path explicitly."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rhino"))

from compas.datastructures import Mesh
from compas.geometry import Box
from cheshire import save_mesh
from cheshire_worker import mesh_from_data, mesh_to_data
from exchange import read_json, validate_response, write_json_atomic
from worker_process import worker_launch_options


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", required=True, type=Path)
    args = parser.parse_args()
    control = Mesh.from_shape(Box(1, 1, 1))
    run_id = str(uuid4())
    directory = ROOT / "output/task09" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    payload = {"protocol": 1, "mode": "MOLA_TAPER_STUDY", "run_id": run_id,
               "source": {"document_serial": 0, "object_id": "unit-cube-control"},
               "mola_dll": str(args.dll.resolve()), "selected_faces": [next(control.faces())],
               "mesh": mesh_to_data(control)}
    write_json_atomic(directory / "request.json", payload)
    save_mesh(control, directory / "control.obj")
    with (directory / "worker_stdout.txt").open("w", encoding="utf-8") as stdout, \
         (directory / "worker_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.run(**worker_launch_options(ROOT, directory / "request.json", directory / "response.json"),
                                 stdout=stdout, stderr=stderr, timeout=60)
    if process.returncode:
        raise RuntimeError((directory / "worker_stderr.txt").read_text() + "\nWorker failed; logs: " + str(directory))
    response = validate_response(read_json(directory / "response.json"), payload)
    if response["status"] != "SUCCESS":
        raise RuntimeError(response["reason"])
    for variant in response["variants"]:
        save_mesh(mesh_from_data(variant["mesh"]), directory / (variant["name"] + ".obj"))
        print(f"{variant['name']}: {variant['vertex_count']} vertices / {variant['face_count']} faces; "
              f"height ratio {variant['height_ratio']}, fraction {variant['fraction']}")
    backend = response["variants"][0]["backend"]
    print(json.dumps({"runtime": backend["runtime"], "assembly": backend["assembly"], "sha256": backend["sha256"]}))
    print("REAL MOLA WORKER: PASS; " + str(directory))


if __name__ == "__main__":
    main()
