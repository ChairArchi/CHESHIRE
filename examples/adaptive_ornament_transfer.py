"""Run the reusable analyzer/deposition on a new column without fixture IDs.

python examples/adaptive_ornament_transfer.py --host new_host.npz \
    --profile mandel_profile.npz --radius .30 --output NEW_DIRECTORY

Requires the existing task32 NumPy/SciPy extra. The output must not exist.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cheshire.adaptive_ornament import MandelRadialProfile, OrnamentRecipe, apply_adaptive_ornament
from cheshire.ornament_analysis import EvidenceConfig, analyze_ornament_shape


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--recipe', type=Path)
    parser.add_argument('--radius', type=float, required=True, help='Physical analysis radius in host units.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Output exists; previous models are preserved.')
    recipe = OrnamentRecipe(**json.loads(args.recipe.read_text(encoding='utf-8'))) if args.recipe else OrnamentRecipe()
    with np.load(args.host, allow_pickle=False) as host, np.load(args.profile, allow_pickle=False) as boundary:
        x, q, uv = host['xyz'], host['faces'], host['pattern_coordinates']
        profile = MandelRadialProfile(boundary['theta'], boundary['phi'], boundary['radius'],
                                     provenance={'input_file_sha256': sha(args.profile)})
        analysis = analyze_ornament_shape(x, q, config=EvidenceConfig(radius=args.radius),
            fallback_face_weights=host['fallback_face_weights'] if 'fallback_face_weights' in host else None)
        optional = {k: host[k] for k in ('tissue_height', 'tissue_priority', 'flow_protection', 'cap_mask', 'valley_weight') if k in host}
        result = apply_adaptive_ornament(x, q, shape_weights=analysis['shape_weights'],
            pattern_coordinates=uv, profile=profile, recipe=recipe, **optional)
    args.output.mkdir(parents=True)
    np.savez(args.output / 'geometry.npz', xyz=result['xyz'], faces=q,
             pattern_coordinates=uv, shape_weights=result['shape_weights'],
             normals=result['normals'], desired_height=result['desired_height'],
             actual_height=result['actual_height'], local_gain=result['local_gain'],
             fixed_mask=result['fixed_mask'], tissue_priority=result['tissue_priority'],
             face_shape_weights=analysis['face_shape_weights'],
             **analysis['vertex_fields'])
    manifest = dict(kind='REUSABLE_ADAPTIVE_ORNAMENT_TRANSFER',
        source_host=str(args.host.resolve()), source_host_sha256=sha(args.host),
        boundary_file=str(args.profile.resolve()), boundary_file_sha256=sha(args.profile),
        profile_sampling_sha256=profile.sha256, profile_radius_sha256=profile.radius_sha256,
        recipe=recipe.to_dict(), analysis=analysis['metadata'], quality=result['quality'],
        recovery_bad_face_counts=result['recovery_bad_face_counts'],
        geometry_sha256=sha(args.output / 'geometry.npz'),
        core_source_hashes={name: sha(Path(__file__).resolve().parents[1] / 'src/cheshire' / name)
            for name in ('adaptive_ornament.py', 'ornament_analysis.py')},
        limitations=['Physical material coordinates and actual Tissue heights are adapter inputs.',
                     'Flow candidates are not automatically certified protected ridges.',
                     'This is a new transfer result, not an exact replay of completed column22.'])
    (args.output / 'RECEIPT.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(output=str(args.output), vertices=len(x), quads=len(q), quality=result['quality'])))


if __name__ == '__main__':
    main()
