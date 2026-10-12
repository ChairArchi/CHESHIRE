"""Replay the two accepted column inputs without requiring rejected gate pilots."""
from pathlib import Path
import argparse
import json

import verify


def run(root, modes):
    records, metadata = [], []
    for case in ('SPAN', 'COUNTER'):
        for mode in modes:
            record, saved = verify.verify_parent(root, case, mode)
            records.append(record)
            metadata.append(saved)
    recipes = [verify.recipe_without_candidate(item) for item in metadata]
    common_recipe = bool(recipes and all(item == recipes[0] for item in recipes))
    passed = bool(len(records) == 2*len(modes) and common_recipe and
                  all(record['passed'] for record in records))
    return dict(passed=passed, expected_cases=['SPAN', 'COUNTER'], modes=list(modes),
                expected_states=2*len(modes), verified_states=len(records),
                common_recipe=common_recipe, records=records,
                scope='Explicit expected-case saved G3 operations and native reconstruction. '
                      'No gate, self-intersection, fabrication or aesthetic certification.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--modes', nargs='+', choices=verify.MODES,
                        default=list(verify.MODES))
    args = parser.parse_args()
    result = run(args.root.resolve(), tuple(dict.fromkeys(args.modes)))
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps({key: result[key] for key in
                     ('passed', 'expected_states', 'verified_states', 'common_recipe')}))
    raise SystemExit(0 if result['passed'] else 1)
