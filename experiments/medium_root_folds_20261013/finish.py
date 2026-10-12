"""Finish the saved wide-root relief by averaging only its new displacement.

Two actual G7 inputs are required: latest parent_linked trial03 baseline and
medium_root trial01 WIDE_ROOT. Three fixed neighbor averages operate on
raw_xyz-baseline_xyz, never on baseline geometry. No field or CC is rerun.
"""
from pathlib import Path
import argparse
import gc
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = HERE.parent/'parent_linked_folds_20261013'
sys.path.insert(0, str(OLD))
import study as base  # noqa: E402
import smooth_relief as prior  # noqa: E402

PARENT = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial03/PARENT_LINKED/SPAN/G07')
RAW = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial01/WIDE_ROOT/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02')
core, loader, digest, write = base.core, base.loader, base.digest, base.write
field = base.operator.field
FINISH_ITERATIONS = 3


def summary_binding(folder, generation_sha256):
    path = folder.parents[2]/'SUMMARY.json'
    info = base.read(path)
    if info['generation_json_sha256'] != generation_sha256:
        raise ValueError('Actual input generation and preserved summary disagree: '+str(folder))
    return dict(path=str(path), sha256=digest(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'WIDE_ROOT_FINISHED/SPAN/G07'
    if folder.exists() or (root/'SUMMARY.json').exists():
        raise FileExistsError('Earlier output is preserved; no overwrite.')
    for source in (PARENT, RAW):
        if root == source.resolve() or source.resolve() in root.parents:
            raise ValueError('Both actual input checkpoints are read-only.')
    memory_before_load = base.finish.memory_guard()
    print('CHECK latest baseline G7 and actual WIDE_ROOT raw G7 dependencies', flush=True)
    parent, raw = prior.checked_receipt(PARENT), prior.checked_receipt(RAW)
    parent_generation_sha256 = digest(PARENT/'generation.json')
    raw_generation_sha256 = digest(RAW/'generation.json')
    summaries = [summary_binding(PARENT, parent_generation_sha256),
        summary_binding(RAW, raw_generation_sha256)]
    if (parent.get('candidate') != 'PARENT_LINKED' or parent.get('source_generation') != 7 or
            parent.get('added_CC_passes') != 0 or parent.get('added_normal_field_passes') != 2 or
            parent.get('smoothing_passes') != 3 or
            raw.get('candidate') != 'WIDE_ROOT' or raw.get('source_generation') != 7 or
            raw.get('added_CC_passes') != 0 or raw.get('added_normal_field_passes') != 2 or
            raw.get('smoothing_passes') != 4 or
            raw.get('cumulative_normal_field_passes') != parent['cumulative_normal_field_passes']+2 or
            Path(raw['source']).resolve() != PARENT.resolve() or
            Path(raw['parent_stage']).resolve() != PARENT.resolve() or
            raw['source_control_sha256'] != parent['control_file_sha256'] or
            raw['source_generation_json_sha256'] != parent_generation_sha256):
        raise ValueError('Actual WIDE_ROOT must bind the same latest baseline G7 and two prior field passes.')
    if (raw['checks']['control_faces_sha256'] != parent['checks']['control_faces_sha256'] or
            raw['checks']['chart_sha256'] != parent['checks']['chart_sha256'] or
            raw['control_vertices'] != parent['control_vertices'] or
            raw['control_quads'] != parent['control_quads']):
        raise ValueError('Actual baseline/raw topology, chart, or counts differ.')
    print('VERIFY unchanged topology and associations with existing streamed NPZ hashes', flush=True)
    associations = prior.association_hashes(PARENT/'control_quad.npz', RAW/'control_quad.npz')
    data = loader.arrays(PARENT/'control_quad.npz',
        ('xyz', 'faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'))
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    chart = data['chart']
    if (mesh.generation != 7 or mesh.surface != 'mean' or
            mesh.faces.shape != (parent['control_quads'], 4) or len(mesh.xyz) != parent['control_vertices'] or
            prior.array_hash(mesh.xyz) != parent['checks']['control_xyz_sha256']):
        raise ValueError('Actual latest baseline controls disagree with their verified receipt.')
    raw_xyz = loader.arrays(RAW/'control_quad.npz', ('xyz',))['xyz']
    if (raw_xyz.shape != mesh.xyz.shape or not np.isfinite(raw_xyz).all() or
            prior.array_hash(raw_xyz) != raw['checks']['control_xyz_sha256']):
        raise ValueError('Actual WIDE_ROOT raw XYZ differs from its saved verification.')
    pairs = loader.arrays(PARENT/'evidence.npz', ('mirror_x_vertex_pairs',
        'mirror_y_vertex_pairs', 'mirror_x_face_pairs', 'mirror_y_face_pairs'))
    vertex_pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    ids, actual_pairs = field._mirror_pairs(vertex_pairs, len(mesh.xyz))
    unfiltered = raw_xyz-mesh.xyz
    del raw_xyz, data
    degree = np.bincount(mesh.faces.ravel(), minlength=len(mesh.xyz))
    if np.any(degree == 0):
        raise ValueError('Source orphan vertices are not repaired.')
    before = prior.displacement_stats(unfiltered)
    guard = base.finish.memory_guard()
    current = unfiltered
    for iteration in range(FINISH_ITERATIONS):
        print('FINISH only the saved MEDIUM+SMALL delta', iteration+1, '/', FINISH_ITERATIONS, flush=True)
        current = prior.uniform_displacement_pass(current, mesh.faces, degree)
    print('TRANSPORT final delta using actual baseline X/Y IDs', flush=True)
    filtered, representative, fixed_x, fixed_y = field._transport(current, ids, actual_pairs)
    del current, representative, fixed_x, fixed_y, degree, ids
    after = prior.displacement_stats(filtered)
    output_xyz = mesh.xyz+filtered
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite actual finished G7; no fallback.')
    actual_unmoved = int(np.count_nonzero(np.all(output_xyz == mesh.xyz, axis=1)))
    out = core.ArrayMesh(output_xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors, 7)
    out.surface = 'mean'
    state = dict(unfiltered_delta=unfiltered, filtered_delta=filtered, **pairs)
    print('VERIFY actual reflected G7 XYZ and oriented quad cycles once', flush=True)
    symmetry = loader.actual_symmetry(out, state)
    hashes = dict(raw['geometry_code_sha256'])
    hashes[str((HERE/'finish.py').relative_to(REPO))] = digest(HERE/'finish.py')
    smoothing_passes = raw['smoothing_passes']+FINISH_ITERATIONS
    metadata = dict(experiment='MEDIUM_ROOT_DISPLACEMENT_FINISH_20261013',
        schema='CHESHIRE_WIDE_ROOT_SAVED_DELTA_FINISH_V1',
        finish_smoothing_iterations=FINISH_ITERATIONS, finish_smoothing_passes=FINISH_ITERATIONS,
        inherited_raw_smoothing_passes=raw['smoothing_passes'], smoothing_passes=smoothing_passes,
        alpha=.5, baseline_geometry_filtered=False, amplitude_multiplier_applied=False,
        equation='delta_next=.5*delta+.5*uniform_actual_edge_neighbor_mean(delta)',
        neighborhood_scope='Existing verified closed quad graph; the finish may add at most three edge-neighbor steps of halo beyond the raw nonzero delta.',
        reflection_scope='One final source-ID canonical displacement transport; unchanged actual baseline XYZ remains the additive source.',
        before_filter=before, after_filter=after,
        actual_unmoved_vertex_count=actual_unmoved,
        actual_unmoved_vertex_fraction=float(actual_unmoved/len(out.xyz)),
        count_scope='Control-vertex fractions, not surface-area coverage.',
        unchanged_association_npy_sha256=associations,
        input_xyz_sha256=parent['checks']['control_xyz_sha256'],
        raw_xyz_sha256=raw['checks']['control_xyz_sha256'], output_xyz_sha256=prior.array_hash(output_xyz),
        raw_field=raw['operator_metadata'], raw_field_stage=str(RAW),
        normal_field_passes_computed_this_finish=0,
        geometry_scope='Actual latest parent_linked trial03 G7 XYZ plus filtered(raw_WIDE_ROOT_trial01_XYZ-baseline_XYZ); no averaging or rescaling of the baseline geometry.',
        dependency_scope='Two required actual inputs: latest trial03 G7 supplies geometry/topology/associations and WIDE_ROOT trial01 supplies already-computed MEDIUM+SMALL displacement. This finish does not recompute those fields.',
        smoothing_count_scope='Seven displacement averaging passes relative to this baseline: four inherited inside raw MEDIUM/SMALL generation, then three finish passes on their combined saved delta. Earlier baseline smoothing is not counted again.',
        success_scope='Displacement-only finish; preservation of medium folds and reduction of close faceting require actual matched renders. Detail hierarchy is not declared solved.')
    context = dict(input_case='SPAN', candidate='WIDE_ROOT_FINISHED', source=str(PARENT),
        source_generation=7, source_control_sha256=parent['control_file_sha256'],
        source_generation_json_sha256=parent_generation_sha256, parent_stage=str(PARENT),
        parent_control_sha256=parent['control_file_sha256'],
        parent_generation_json_sha256=parent_generation_sha256,
        raw_field_stage=str(RAW), raw_field_control_sha256=raw['control_file_sha256'],
        raw_field_evidence_sha256=raw['evidence_file_sha256'],
        raw_field_generation_json_sha256=raw_generation_sha256, input_summary_bindings=summaries,
        geometry_code_sha256=hashes, added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=2, added_normal_field_passes_this_finish=0,
        cumulative_normal_field_passes=raw['cumulative_normal_field_passes'],
        smoothing_passes=smoothing_passes, finish_smoothing_passes=FINISH_ITERATIONS,
        added_mandelbulb_evaluations=0, operator_metadata=metadata,
        frame_ancestry=raw['frame_ancestry'], symmetry=symmetry,
        memory_guard_before_load=memory_before_load, memory_guard=guard,
        field_count_scope='Two normal passes inherited from the raw WIDE_ROOT dependency relative to the latest baseline; zero new normal passes in this finish.',
        smoothing_scope=metadata['smoothing_count_scope'],
        user_density_baseline='MIDDLE; broad grooves and breathing room remain the design criterion.',
        design_scope='One fixed displacement-only finish of the saved broad MEDIUM folds and dependent SMALL grooves.',
        dependency_scope=metadata['dependency_scope'],
        intermediate_scope='Raw WIDE_ROOT evidence retains delta_medium/delta_small and the actual intermediate reconstruction; this finish stores only combined unfiltered/filtered delta and actual mirror correspondences.',
        porosity_scope='No new perforation or topology-changing branch.',
        validation_scope='Required finite/closed-oriented/connectivity/no-orphan/native-area checks once at save, plus actual reflected XYZ and oriented control quads.',
        exclusions=['Additional subdivision', 'New field parameters', 'Baseline geometry smoothing',
            'Amplitude rescaling', 'Candidate matrix', 'Full independent replay',
            'Native triangle-set sorting', 'Self-intersection repair', 'Fabrication suitability',
            'Aesthetic certification'])
    del mesh, pairs
    gc.collect()
    print('SAVE one actual finished G7 and required existing mesh checks', flush=True)
    record = core.save(folder, out, chart, context, state)
    for source, info, generation_sha256 in ((PARENT, parent, parent_generation_sha256),
            (RAW, raw, raw_generation_sha256)):
        base.checked(source, info, (('control_quad.npz', 'control_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')))
        if digest(source/'generation.json') != generation_sha256:
            raise ValueError('Preserved actual input receipt changed during finish.')
        prior.check_code(info)
    for binding in summaries:
        if digest(binding['path']) != binding['sha256']:
            raise ValueError('Preserved actual input summary changed during finish.')
    write(root/'SUMMARY.json', dict(source=str(PARENT), source_generation=7,
        source_control_sha256=parent['control_file_sha256'], candidate='WIDE_ROOT_FINISHED',
        input_case='SPAN', folder=str(folder), subdivision_generation=7,
        raw_field_stage=str(RAW), raw_field_control_sha256=raw['control_file_sha256'],
        raw_field_generation_json_sha256=raw_generation_sha256,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=2,
        added_normal_field_passes_this_finish=0,
        cumulative_normal_field_passes=raw['cumulative_normal_field_passes'],
        smoothing_passes=smoothing_passes, finish_smoothing_passes=FINISH_ITERATIONS,
        generation_json_sha256=digest(folder/'generation.json'), checks=record['checks'],
        symmetry=symmetry, operator_metadata=metadata, frame_ancestry=raw['frame_ancestry'],
        geometry_code_sha256=hashes, dependency_scope=metadata['dependency_scope'],
        visual_success='PENDING_ACTUAL_WHOLE_BODY_AND_CLOSE_RENDER_REVIEW'))
    print('DONE WIDE_ROOT_FINISHED actual G7; new fields 0; CC 0', flush=True)


if __name__ == '__main__':
    main()
