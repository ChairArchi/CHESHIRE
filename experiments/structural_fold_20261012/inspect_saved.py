"""Reuse the structural trial's unchanged quick checks on applied CC outputs."""
import argparse
import json
from pathlib import Path
from study import load, solid, inspect

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('folders', nargs='+', type=Path)
args = parser.parse_args()
for folder in args.folders:
    mesh = load(folder)
    checks, passed = inspect(mesh, solid(mesh))
    record = json.loads((folder/'generation.json').read_text(encoding='utf8'))
    record.update(checks=checks, quick_integrity='PASS' if passed else 'FAIL',
        area_failure_threshold=1e-12, all_components_retained=True)
    (folder/'generation.json').write_text(json.dumps(record, indent=2), encoding='utf8')
    mesh.export(folder/'column.ply')
    print(json.dumps(dict(output=str(folder), quick_integrity=record['quick_integrity'], checks=checks)), flush=True)
