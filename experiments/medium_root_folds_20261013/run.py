"""One whole-column medium-root fold sequence continuing the latest saved G7.

The existing MIDDLE ancestry supplies fixed coordinates and associations.
Actual XYZ comes from the latest displacement-finished trial03, not the older
baseline. Two broad/small normal fields preserve topology and subdivision G7.
"""
from pathlib import Path
import argparse
import gc
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREVIOUS_CODE = HERE.parent/'parent_linked_folds_20261013'
sys.path.insert(0, str(PREVIOUS_CODE))
import study as base
import smooth_relief as prior_finish

folds = base.module('medium_root_fixed_operator', HERE/'root_folds.py')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial03/PARENT_LINKED/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial01')
digest, write, core, loader = base.digest, base.write, base.core, base.loader


def load():
    info = prior_finish.checked_receipt(SOURCE)
    if (info.get('candidate') != 'PARENT_LINKED' or info.get('source_generation') != 7
            or info.get('added_CC_passes') != 0 or info.get('added_normal_field_passes') != 2
            or info.get('smoothing_passes') != 3):
        raise ValueError('Latest preserved trial03 G7 required.')
    source_receipt_hash = digest(SOURCE/'generation.json')
    previous_summary_file = SOURCE.parents[2]/'SUMMARY.json'
    previous_summary = base.read(previous_summary_file)
    if previous_summary['generation_json_sha256'] != source_receipt_hash:
        raise ValueError('Latest source summary and generation receipt disagree.')
    mesh, chart, pairs, phase, z, support, height, baseline, ancestry = base.load()
    if (info['checks']['control_faces_sha256'] != baseline['checks']['control_faces_sha256']
            or info['checks']['chart_sha256'] != baseline['checks']['chart_sha256']):
        raise ValueError('Latest source must retain registered baseline associations.')
    associations = prior_finish.association_hashes(base.PARENT/'control_quad.npz', SOURCE/'control_quad.npz')
    source_xyz = loader.arrays(SOURCE/'control_quad.npz', ('xyz',))['xyz']
    if (source_xyz.shape != mesh.xyz.shape or not np.isfinite(source_xyz).all()
            or prior_finish.array_hash(source_xyz) != info['checks']['control_xyz_sha256']):
        raise ValueError('Actual latest source XYZ differs from saved verification.')
    # Unchanged association bytes are proven above. Replace the older XYZ with
    # the actual latest XYZ before any normal or field evaluation.
    mesh.xyz = source_xyz
    ancestry.update(actual_geometry_source=str(SOURCE), actual_geometry_source_generation=7,
        actual_geometry_source_control_sha256=info['control_file_sha256'],
        actual_geometry_source_generation_sha256=source_receipt_hash,
        fixed_frame_baseline=str(base.PARENT),
        unchanged_source_association_npy_sha256=associations,
        source_scope='Latest trial03 G7 XYZ continues directly; older MIDDLE only supplies registered phase/chart/IDs with identical association bytes.')
    return mesh, chart, pairs, phase, z, support, height, info, ancestry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'WIDE_ROOT/SPAN/G07'
    if folder.exists() or (root/'SUMMARY.json').exists():
        raise FileExistsError('Earlier output is preserved; no overwrite.')
    for source in (SOURCE, base.PARENT):
        if root == source.resolve() or source.resolve() in root.parents:
            raise ValueError('Preserved source is read-only.')
    base.finish.memory_guard()
    print('LOAD latest actual trial03 G7 with existing registered MIDDLE coordinates', flush=True)
    mesh, chart, pairs, phase, z, support, height, source, ancestry = load()
    hashes = dict(source['geometry_code_sha256'])
    hashes.update(folds.code_hashes())
    hashes[str((HERE/'run.py').relative_to(REPO))] = digest(HERE/'run.py')
    source_receipt_hash = digest(SOURCE/'generation.json')
    input_xyz_hash = prior_finish.array_hash(mesh.xyz)
    vertex_pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    print('APPLY broad MEDIUM fold then dependent SMALL grooves to the whole G7', flush=True)
    out, metadata, state = folds.build(mesh, chart, vertex_pairs, phase, z, support, height)
    if (out.generation != 7 or not np.array_equal(out.faces, mesh.faces)
            or out.xyz.shape != mesh.xyz.shape or metadata['input_xyz_sha256'] != input_xyz_hash):
        raise ValueError('Actual latest G7 input and unchanged topology required.')
    state.update(mirror_x_face_pairs=pairs['mirror_x_face_pairs'],
        mirror_y_face_pairs=pairs['mirror_y_face_pairs'])
    print('VERIFY actual G7 reflected XYZ and oriented quad cycles', flush=True)
    symmetry = loader.actual_symmetry(out, state)
    context = dict(input_case='SPAN', candidate='WIDE_ROOT', source=str(SOURCE),
        source_generation=7, source_control_sha256=source['control_file_sha256'],
        source_generation_json_sha256=source_receipt_hash,
        parent_stage=str(SOURCE), parent_control_sha256=source['control_file_sha256'],
        parent_generation_json_sha256=source_receipt_hash,
        geometry_code_sha256=hashes, added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=2,
        cumulative_normal_field_passes=source['cumulative_normal_field_passes']+2,
        smoothing_passes=4, smoothing_scope='Only each new displacement vector is averaged twice before actual-ID reflection; existing geometry is not averaged.',
        added_mandelbulb_evaluations=0, operator_metadata=metadata,
        frame_ancestry=ancestry, symmetry=symmetry,
        user_density_baseline='MIDDLE; large grooves and broad-surface breathing room remain the design criterion.',
        design_scope='One whole-column broad panel-flank fold with smaller dependent grooves continuing latest trial03 G7.',
        methodology_scope='Existing normal displacement, registered parent frame, PCHIP envelope, displacement-only averaging and actual-ID reflection; no topology-changing operation.',
        porosity_scope='No new perforations or genus transition. Depth and fold-scale relations are the purpose of this iteration.',
        intermediate_scope='Saved delta_medium reconstructs the actual intermediate; only the final native mesh is saved.',
        validation_scope='Required finite/closed-oriented/connectivity/no-orphan/native-area checks once at save, actual reflected XYZ and oriented control quads, then matched actual renders.',
        exclusions=['Additional subdivision', 'Candidate matrix', 'New perforation algorithms',
            'Full independent replay', 'Native triangle-set sorting', 'Self-intersection repair',
            'Fabrication suitability', 'Aesthetic certification'])
    del mesh, pairs, phase, z, support
    gc.collect()
    print('SAVE one final actual G7 and required existing mesh checks', flush=True)
    record = core.save(folder, out, chart, context, state)
    base.checked(SOURCE, source, (('control_quad.npz', 'control_file_sha256'),
        ('evidence.npz', 'evidence_file_sha256')))
    if digest(SOURCE/'generation.json') != source_receipt_hash:
        raise ValueError('Preserved latest source changed during sequence.')
    prior_finish.check_code(source)
    write(root/'SUMMARY.json', dict(source=str(SOURCE), source_generation=7,
        source_control_sha256=source['control_file_sha256'], candidate='WIDE_ROOT',
        input_case='SPAN', folder=str(folder), subdivision_generation=7,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=2,
        cumulative_normal_field_passes=context['cumulative_normal_field_passes'], smoothing_passes=4,
        generation_json_sha256=digest(folder/'generation.json'), checks=record['checks'],
        symmetry=symmetry, operator_metadata=metadata, frame_ancestry=ancestry,
        geometry_code_sha256=hashes,
        visual_success='PENDING_ACTUAL_WHOLE_BODY_AND_CLOSE_RENDER_REVIEW'))
    print('DONE one whole-column medium-root fold result, actual G7', flush=True)


if __name__ == '__main__':
    main()
