"""One isolated study candidate, using the existing validated prototype."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rhino"))
from cheshire_worker import RUNTIME_IDENTITY  # Checks interpreter, stdlib and checkout.
from exchange import read_json, write_json_atomic, validate_response
from visual_prototype import run_visual_prototype


def main():
    request_path, response_path, recipe_path = map(Path, sys.argv[1:])
    request, candidate = read_json(request_path), read_json(recipe_path)
    if candidate["recipe"]["id"] not in ("A", "B", "C"):
        raise ValueError("Keep recipe family IDs A/B/C; candidate_id is separate.")
    response = run_visual_prototype(request, recipes=[candidate["recipe"]],
        publish=lambda value: write_json_atomic(response_path, value))
    validate_response(response, request)
    print("Worker Python:", RUNTIME_IDENTITY["version"])
    print("Worker stdlib:", RUNTIME_IDENTITY["re_file"])
    print("CHESHIRE package:", RUNTIME_IDENTITY["cheshire_file"])
    print(candidate["candidate_id"], response["status"], response["reason"])
    return 0 if response["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
