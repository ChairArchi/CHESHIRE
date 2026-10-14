"""Bind one already-saved full replay for viewing; no geometry generation or copying."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('end_replay_binding_renderer', HERE/'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
STORED = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states/G07_FINAL')
GENERATION_SHA = 'd9f23217bb65c48f77a3039670d19cf9c22a74c888242ff08293bb9a276e80ff'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.ROOT)
    args = parser.parse_args()
    path = args.root/'RECEIPT.json'
    if path.exists():
        raise FileExistsError('Earlier focused receipt preserved.')
    generation = STORED/'generation.json'
    if render.digest(generation) != GENERATION_SHA:
        raise ValueError('Actual stored replay generation record changed.')
    g = render.read_json(generation)
    geometry = STORED/'geometry.npz'
    if render.digest(geometry) != g['geometry_file_sha256']:
        raise ValueError('Actual preserved replay geometry changed.')
    binding = render.source_binding()
    expected = dict(geometry=str(geometry), geometry_sha256=g['geometry_file_sha256'],
        xyz_sha256=g['checks']['native_xyz_sha256'], faces_sha256=g['checks']['native_faces_sha256'],
        vertices=g['native_vertices'], triangles=g['native_triangles'],
        stored_generation_json=str(generation), stored_generation_json_sha256=GENERATION_SHA,
        validation=g['checks'], source_geometry_regenerated=False, original_saved_native_mesh=True,
        scope='Unmasked actual saved G07_FINAL replay from the prior end-rule study. It is not the later mask-spliced REVISED body and does not include subsequent FLOW finish.')
    receipt = dict(kind='EXISTING_SAVED_FULL_REPLAY_VISUAL_DIAGNOSTIC', date='2026-10-14',
        source_native_path=binding['source_native_path'], source_native_geometry_sha256=binding['source_native_geometry_sha256'],
        variants={'COHERENT_REPLAY':expected}, geometry_generation=False, geometry_copy=False,
        preparation_code_sha256=render.digest(__file__), source_baseline=binding,
        scope='Read-only viewing of one existing full replay against actual current FLOW03. No new model, algorithm, blending, smoothing or geometry operation.')
    render.write(path, receipt)
    render.variants(args.root, binding)
    print('EXISTING_REPLAY_BOUND', expected['vertices'], expected['triangles'], flush=True)


if __name__ == '__main__':
    main()
