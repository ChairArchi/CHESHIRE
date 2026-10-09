"""Read-only exchange check and optional bounded neutral subdivision probe."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cheshire.gate_exchange import describe_gate_input, load_gate_input


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--probe-subdivision", action="store_true")
    args = parser.parse_args()
    report = describe_gate_input(args.directory)
    if args.probe_subdivision:
        from cheshire import ExecutionBudget, subdivide_quad_once
        mesh, _ = load_gate_input(args.directory)
        result = subdivide_quad_once(
            mesh, budget=ExecutionBudget(max_faces=50000, max_vertices=50000, max_generation=1),
            current_generation=0, nonplanar_policy="bilinear")
        report["neutral_probe"] = dict(vertices=result.mesh.number_of_vertices(),
                                       faces=result.mesh.number_of_faces(), generations=1)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
