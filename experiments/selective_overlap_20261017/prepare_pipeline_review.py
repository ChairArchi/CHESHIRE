"""Bind completed actual early-pipeline geometry for visual review."""
from pathlib import Path
import hashlib
import json

ROOT = Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')


def main():
    source = ROOT / 'full_pipeline/L08_PRIMARY_193/states/G04_NEUTRAL'
    receipt = json.loads((source / 'generation.json').read_text(encoding='utf8'))
    geometry = source / 'geometry.npz'
    if not receipt['checks']['passed']:
        raise ValueError('Completed actual G4 required.')
    plan = dict(common_scale=11.2, items=[dict(id='L08_G4', geometry=str(geometry),
        controls=str(source / 'control_quad.npz'), views=['whole', 'oblique', 'body', 'crown'])])
    path = ROOT / 'G4_REVIEW_PLAN.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(plan, indent=2), encoding='utf8')
    print(path)


if __name__ == '__main__':
    main()
