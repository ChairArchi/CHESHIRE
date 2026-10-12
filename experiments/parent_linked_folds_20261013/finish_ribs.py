"""One correction of visibly faceted narrow parent-linked relief on saved G7.

The first result is preserved. Registered parent bands and amplitudes remain
fixed; broader cosine profiles replace the visibly faceted narrow profiles.
This is one whole-column correction, not an amplitude or method search.
"""
from pathlib import Path
import argparse
import gc

import numpy as np

import study as base

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ribs = base.module('parent_linked_connected_ribs', HERE/'connected_ribs.py')
PARENT, digest, write, core = base.PARENT, base.digest, base.write, base.core
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial02')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'PARENT_LINKED/SPAN/G07'
    if folder.exists() or (root/'SUMMARY.json').exists():
        raise FileExistsError('Earlier whole-column correction is preserved; no overwrite.')
    if root == PARENT.resolve() or PARENT.resolve() in root.parents:
        raise ValueError('Selected source is read-only.')
    base.finish.memory_guard()
    print('LOAD same selected MIDDLE SURFACE G7 and registered parent frame', flush=True)
    mesh, chart, pairs, phase, z, support, height, parent, ancestry = base.load()
    hashes = dict(parent['geometry_code_sha256'])
    for path in (HERE/'study.py', HERE/'parent_folds.py', HERE/'finish_ribs.py', HERE/'connected_ribs.py'):
        hashes[str(path.relative_to(REPO))] = digest(path)
    source_generation_sha256 = digest(PARENT/'generation.json')
    vertex_pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    print('APPLY one wider cosine CHILD -> GRANDCHILD correction, same G7', flush=True)
    out, metadata, state = ribs.build(mesh, chart, vertex_pairs, phase, z, support, height)
    if (out.generation != 7 or not np.array_equal(out.faces, mesh.faces)
            or out.xyz.shape != mesh.xyz.shape):
        raise ValueError('Same actual G7 topology required.')
    state.update(mirror_x_face_pairs=pairs['mirror_x_face_pairs'],
        mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    print('VERIFY actual reflected G7 XYZ and oriented control quads', flush=True)
    symmetry = base.loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='PARENT_LINKED',
        source=str(PARENT), source_generation=7, source_control_sha256=parent['control_file_sha256'],
        source_generation_json_sha256=source_generation_sha256, parent_stage=str(PARENT),
        parent_control_sha256=parent['control_file_sha256'],
        parent_generation_json_sha256=source_generation_sha256, geometry_code_sha256=hashes,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=2,
        cumulative_normal_field_passes=parent['cumulative_normal_field_passes']+2,
        added_mandelbulb_evaluations=0, operator_metadata=metadata, frame_ancestry=ancestry,
        symmetry=symmetry, user_density_baseline='MIDDLE; preserve large grooves and broad-surface breathing room.',
        correction_scope='One wider-profile correction after trial01 close renders showed serrated facets; same source, bands, amplitudes and two-pass dependency.',
        preceding_result='E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial01',
        design_scope='Whole selected MIDDLE G7 with compact parent-linked cosine ribs; global FINE was not applied.',
        methodology_scope='Existing actual-input incident-normal displacement with two fixed dependent cosine profiles; no topological branching claim.',
        intermediate_scope='Saved delta_child reconstructs actual intermediate; no separately saved CHILD native mesh.',
        validation_scope='Finite/closed-oriented/connectivity/no-orphan/native-area checks once at save plus actual G7 reflected XYZ and oriented control quads.',
        exclusions=['Additional subdivision', 'Parameter alternatives', 'Independent full geometry replay',
            'Native triangle-set sorting', 'Self-intersection repair', 'Fabrication suitability', 'Aesthetic certification'])
    del mesh, pairs, phase, z, support
    gc.collect()
    print('SAVE corrected actual G7 and required mesh checks', flush=True)
    record = core.save(folder, out, chart, context, state)
    if (digest(PARENT/'control_quad.npz') != parent['control_file_sha256']
            or digest(PARENT/'generation.json') != source_generation_sha256):
        raise ValueError('Preserved selected source changed during correction.')
    write(root/'SUMMARY.json', dict(source=str(PARENT), source_generation=7, candidate='PARENT_LINKED',
        input_case='SPAN', folder=str(folder), subdivision_generation=7, added_CC_passes=0,
        added_topology_events=0, added_normal_field_passes=2,
        generation_json_sha256=digest(folder/'generation.json'), checks=record['checks'],
        symmetry=symmetry, operator_metadata=metadata, frame_ancestry=ancestry,
        geometry_code_sha256=hashes, correction_scope=context['correction_scope'],
        visual_success='PENDING_ACTUAL_WHOLE_AND_CLOSE_RENDER_REVIEW'))
    print('DONE one corrected whole-column G7; no added CC', flush=True)


if __name__ == '__main__':
    main()
