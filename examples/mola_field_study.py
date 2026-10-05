"""Real isolated-worker study; replay an explicit ORIGINAL request or a small control."""

import argparse
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rhino"))

from compas.datastructures import Mesh
from cheshire import save_mesh
from cheshire_worker import mesh_from_data, mesh_to_data
from exchange import read_json, validate_response, write_json_atomic
from local_settings import remembered_mola_path, remember_mola_path
from worker_process import worker_launch_options


def control_mesh():
    # Deterministic vertical planar control; no random variation/test download.
    return Mesh.from_vertices_and_faces([[x-1.5, 0, z] for z in range(7) for x in range(4)],
        [[z*4+x, z*4+x+1, (z+1)*4+x+1, (z+1)*4+x] for z in range(6) for x in range(3)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, help="Exact external official DLL; otherwise reuse the ignored preference.")
    parser.add_argument("--input-request", type=Path, help="Explicit saved request containing the ORIGINAL mesh, not a response.")
    args = parser.parse_args()
    dll = str(args.dll.resolve()) if args.dll else remembered_mola_path(ROOT)
    if dll is None:
        parser.error("Provide --dll once or configure output/local_settings.json through Rhino.")
    dll = remember_mola_path(ROOT, dll)
    original = read_json(args.input_request)["mesh"] if args.input_request else mesh_to_data(control_mesh())
    run_id = str(uuid4())
    directory = ROOT / "output/task10" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    request = {"protocol": 1, "mode": "MOLA_FIELD_STUDY", "run_id": run_id,
               "source": {"document_serial": 0, "object_id": "original-request-replay" if args.input_request else "vertical-control"},
               "mola_dll": dll, "selected_faces": "ALL_ELIGIBLE_PLANAR", "mesh": deepcopy(original)}
    write_json_atomic(directory / "request.json", request)
    save_mesh(mesh_from_data(original), directory / "G0.obj")
    with (directory / "worker_stdout.txt").open("w", encoding="utf-8") as stdout, \
         (directory / "worker_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.run(**worker_launch_options(ROOT, directory / "request.json", directory / "response.json"),
                                 stdout=stdout, stderr=stderr, timeout=60)
    if not (directory / "response.json").is_file():
        raise RuntimeError((directory / "worker_stderr.txt").read_text() + "\nNo response; " + str(directory))
    response = validate_response(read_json(directory / "response.json"), request)
    write_json_atomic(directory / "drivers.json", response["drivers"])
    for stage in response["stages"]:
        save_mesh(mesh_from_data(stage["mesh"]), directory / f"G{stage['generation']}.obj")
        print(f"G{stage['generation']}: {stage['vertex_count']} vertices / {stage['face_count']} faces; "
              f"processed {stage['processed_face_count']}; height {stage['height_range']}; "
              f"fraction {stage['fraction_range']}; {stage['elapsed_seconds']:.3f}s; {stage['budget']['status']}")
    print(response["status"] + ": " + (response["reason"] or "G1/G2/G3 cap recursion completed"))
    print(response["variation_assessment"])
    print("ACTUAL MOLA FIELD STUDY: " + str(directory))
    if process.returncode or response["status"] == "FAILED":
        raise RuntimeError(response["reason"] or "Worker exited " + str(process.returncode))


if __name__ == "__main__":
    main()
