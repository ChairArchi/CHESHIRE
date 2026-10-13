"""Thin saved-mesh rendering adapter for one distinct G0 input, unchanged recipe."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/distinct_input_transfer_20261013/trial01')
INPUT_CASE = 'CENTRAL_SPINDLE'
FROZEN_RENDER = HERE.parent / 'recipe_transfer_20261013/render.py'
FROZEN_RENDER_SHA256 = '37839ec4f2e6009e8f975e6a93e5af5eb737a9476e9de44e3db38dcea46dc556'
spec = importlib.util.spec_from_file_location('distinct_input_frozen_transfer_renderer', FROZEN_RENDER)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
frozen_code_hashes = prior.code_hashes
digest, read_json, require_close = prior.digest, prior.read_json, prior.require_close
manifest, saved_state, stage_views = prior.manifest, prior.saved_state, prior.stage_views
base, STAGES, FINAL, GENERATIONS = prior.base, prior.STAGES, prior.FINAL, prior.GENERATIONS
VIEWS, PROGRESSION_VIEWS, COMPARISON_VIEWS = prior.VIEWS, prior.PROGRESSION_VIEWS, prior.COMPARISON_VIEWS
COUNT_KEYS = prior.COUNT_KEYS
REFERENCE_STAGE = 'ORIGINAL_G00_INPUT'
ORIGINAL_G0 = Path('E:/CHESHIRE_DATA/fold_band_growth_20261011/inputs/SPAN_SPARSE/G00')
ORIGINAL_G0_SHA256 = {
    'generation.json': '6226ab8043dbd50732da3be842e9a0d2fb3f6fd8a1906dc5d9e1936564a615e1',
    'control_quad.npz': 'cff9089de50aac6019684829cd70303d77e3fceaaabf3f090a06636f4f6cbf55',
    'geometry.npz': '2f5c039ecbd96d0277be51371390a9ff653964d74feb46af155ad960d5337f59'}


def code_hashes():
    if digest(FROZEN_RENDER) != FROZEN_RENDER_SHA256:
        raise ValueError('Preserved transfer renderer changed.')
    return dict(render=digest(__file__), frozen_transfer_renderer=FROZEN_RENDER_SHA256,
                preserved_scene_code_sha256=frozen_code_hashes())


def original_g0_state(root):
    """Read the small stored G0; compute receipt hashes, never rebuild its surface."""
    import numpy as np
    root = Path(root).resolve()
    _, binding = manifest(root)
    for filename, expected in ORIGINAL_G0_SHA256.items():
        if digest(ORIGINAL_G0 / filename) != expected:
            raise ValueError('Original SPAN G0 file changed: ' + filename)
    original = read_json(ORIGINAL_G0 / 'generation.json')
    if (original.get('candidate') != 'SPAN_SPARSE' or original.get('stage') != 'G00' or
        original.get('input_carrier_bilinear_splits') != 0 or
        original.get('watertight') is not True or original.get('winding_consistent') is not True or
        original.get('minimum_area_pass') is not True):
        raise ValueError('Preserved unsplit actual SPAN G0 receipt required.')
    with np.load(ORIGINAL_G0 / 'geometry.npz', allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
        if (xyz.shape != (original['vertices'], 3) or faces.shape != (original['triangles'], 3) or
            not np.isfinite(xyz).all() or not np.issubdtype(faces.dtype, np.integer) or
            faces.min() < 0 or faces.max() >= len(xyz)):
            raise ValueError('Stored original G0 native array dimensions differ.')
        checks = {'native_' + key + '_sha256': hashlib.sha256(
            memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()
            for key, value in (('xyz', xyz), ('faces', faces))}
    # Legacy metadata has no native hashes. This in-memory rendering context
    # supplies hashes read from the frozen geometry, without editing its file.
    info = dict(original, input_case='SPAN', subdivision_generation=0, checks=checks)
    source = dict(source=str(ORIGINAL_G0 / 'geometry.npz'), source_sha256=ORIGINAL_G0_SHA256['geometry.npz'],
        control_source=str(ORIGINAL_G0 / 'control_quad.npz'), control_sha256=ORIGINAL_G0_SHA256['control_quad.npz'],
        generation_source=str(ORIGINAL_G0 / 'generation.json'), generation_sha256=ORIGINAL_G0_SHA256['generation.json'],
        stage_id=REFERENCE_STAGE, legacy_metadata_missing_native_array_hashes=True,
        native_array_hashes_computed_from_saved_geometry=True, **binding)
    return ORIGINAL_G0, info, source


def source_state(root, stage):
    if stage == REFERENCE_STAGE:
        return original_g0_state(root)
    if stage not in STAGES:
        raise ValueError('Selected saved stage required.')
    root = Path(root).resolve()
    index, binding = manifest(root)
    item = index[stage]
    folder = (root / item['folder']).resolve()
    if folder != root / 'states' / stage:
        raise ValueError('Stage must remain in the declared distinct-input trial.')
    info = read_json(folder / 'generation.json')
    if (item.get('generation') != GENERATIONS[stage] or
        info.get('subdivision_generation') != GENERATIONS[stage] or
        info.get('input_case') != INPUT_CASE or not info.get('candidate') or
        item.get('generation_json_sha256') != digest(folder / 'generation.json')):
        raise ValueError('Actual distinct-input stage identity or manifest binding differs.')
    source = saved_state(folder, info)
    source.update(stage_id=stage, **binding)
    return folder, info, source


def render_state(info, source, output, views, hashes):
    # Adapt only the receipt's renderer identity. The frozen saved-native
    # loading, flat material, scene and camera operations execute unchanged.
    old_hash_function = prior.code_hashes
    prior.code_hashes = code_hashes
    try:
        prior.render_state(info, source, output, views, hashes)
    finally:
        prior.code_hashes = old_hash_function


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--stage', choices=(*STAGES, REFERENCE_STAGE), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else None)
    hashes = code_hashes()
    folder, info, source = source_state(args.root, args.stage)
    output = (args.root.resolve() / 'reference_views/G00_INPUT'
              if args.stage == REFERENCE_STAGE else folder / 'views')
    output.parent.mkdir(parents=True, exist_ok=True)
    render_state(info, source, output, stage_views(args.stage), hashes)
    if source_state(args.root, args.stage)[2] != source:
        raise ValueError('Saved distinct input/reference stage changed while rendering.')


if __name__ == '__main__':
    main()
