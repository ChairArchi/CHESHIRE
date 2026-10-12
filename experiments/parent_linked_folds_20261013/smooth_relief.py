"""Filter only the saved broad-rib displacement on unchanged selected G7.

This finish has two actual inputs: the selected MIDDLE_SURFACE baseline G7
and the frozen trial02 broad-rib G7. It performs three fixed uniform-neighbor
averages of their displacement difference, never of the baseline geometry.
It adds neither a subdivision pass nor a new normal-field evaluation.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import zipfile

import numpy as np

import study as base

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PARENT = base.PARENT
RAW = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial02/PARENT_LINKED/SPAN/G07')
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/parent_linked_folds_20261013/trial03')
core, loader, digest, write = base.core, base.loader, base.digest, base.write
field = base.operator.field
ITERATIONS, ALPHA = 3, .5


def array_hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def check_code(info):
    for name, checksum in info['geometry_code_sha256'].items():
        if digest(REPO/Path(name.replace('\\', '/'))) != checksum:
            raise ValueError('Frozen source code changed: '+name)


def checked_receipt(folder):
    info = base.read(folder/'generation.json')
    if (info.get('subdivision_generation') != 7 or info.get('input_case') != 'SPAN' or
            not info['checks']['passed'] or not info['symmetry']['passed']):
        raise ValueError('Saved verified actual SPAN G7 required: '+str(folder))
    base.checked(folder, info, (('control_quad.npz', 'control_file_sha256'),
        ('evidence.npz', 'evidence_file_sha256')))
    check_code(info)
    return info


def member_hash(archive, name):
    """Compare unchanged associations without loading duplicate dense arrays."""
    hasher = hashlib.sha256()
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def association_hashes(baseline_file, raw_file):
    result = {}
    with zipfile.ZipFile(baseline_file) as baseline, zipfile.ZipFile(raw_file) as raw:
        for key in ('faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'):
            name = key+'.npy'
            expected, actual = member_hash(baseline, name), member_hash(raw, name)
            if actual != expected:
                raise ValueError('Raw/baseline association differs: '+key)
            result[key] = expected
    return result


def uniform_displacement_pass(delta, faces, degree, chunk_faces=131072):
    """Apply .5*delta + .5*uniform-neighbor-mean on the closed quad graph.

    Each incident quad contributes .5*(previous+next) corner displacement.
    An undirected edge occurs twice in the verified closed quad manifold;
    dividing the accumulated contribution by incident face degree therefore
    equals the uniform mean over the vertex's actual edge neighbors.
    The source XYZ is never an operand of this averaging operation.
    """
    mean = np.zeros_like(delta)
    for start in range(0, len(faces), chunk_faces):
        quad = faces[start:start+chunk_faces]
        ids = quad.ravel()
        for component in range(3):
            values = delta[:, component][quad]
            contribution = .5*(np.roll(values, 1, axis=1)+np.roll(values, -1, axis=1))
            mean[:, component] += np.bincount(ids, weights=contribution.ravel(),
                minlength=len(delta))
    mean /= degree[:, None]
    mean += delta
    mean *= .5
    return mean


def displacement_stats(delta):
    norms = np.linalg.norm(delta, axis=1)
    unmoved = int(np.count_nonzero(np.all(delta == 0., axis=1)))
    return dict(maximum_displacement_norm=float(norms.max(initial=0.)),
        displacement_norm_quantiles=np.quantile(norms, [0, .5, .9, .99, 1]).tolist(),
        zero_displacement_vertex_count=unmoved,
        zero_displacement_vertex_fraction=float(unmoved/len(delta)),
        displacement_vector_sha256=array_hash(delta))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'PARENT_LINKED/SPAN/G07'
    if folder.exists() or (root/'SUMMARY.json').exists():
        raise FileExistsError('Earlier displacement finish is preserved; no overwrite.')
    for source in (PARENT, RAW):
        if root == source.resolve() or source.resolve() in root.parents:
            raise ValueError('Both saved inputs are read-only.')
    memory_before_load = base.finish.memory_guard()
    print('CHECK actual selected MIDDLE_SURFACE and frozen broad-rib G7 dependencies', flush=True)
    parent, raw = checked_receipt(PARENT), checked_receipt(RAW)
    parent_generation_sha256 = digest(PARENT/'generation.json')
    raw_generation_sha256 = digest(RAW/'generation.json')
    raw_summary_file = RAW.parents[2]/'SUMMARY.json'
    raw_summary = base.read(raw_summary_file)
    raw_summary_sha256 = digest(raw_summary_file)
    if (parent.get('candidate') != 'MIDDLE_SURFACE' or parent.get('selected_stage') != 'MIDDLE' or
            raw.get('candidate') != 'PARENT_LINKED' or raw.get('source_generation') != 7 or
            raw.get('added_CC_passes') != 0 or raw.get('added_normal_field_passes') != 2 or
            Path(raw['source']).resolve() != PARENT.resolve() or
            Path(raw['parent_stage']).resolve() != PARENT.resolve() or
            raw['source_control_sha256'] != parent['control_file_sha256'] or
            raw['source_generation_json_sha256'] != parent_generation_sha256 or
            raw_summary['generation_json_sha256'] != raw_generation_sha256):
        raise ValueError('Actual trial02 must bind the same selected baseline G7 and two prior field passes.')
    if (raw['checks']['control_faces_sha256'] != parent['checks']['control_faces_sha256'] or
            raw['checks']['chart_sha256'] != parent['checks']['chart_sha256']):
        raise ValueError('Baseline/raw actual topology or chart hashes differ.')
    print('VERIFY identical topology and associations by streamed NPZ member hashes', flush=True)
    associations = association_hashes(PARENT/'control_quad.npz', RAW/'control_quad.npz')
    data = loader.arrays(PARENT/'control_quad.npz',
        ('xyz', 'faces', 'classes', 'rest', 'anchors', 'chart', 'generation', 'surface'))
    mesh = core.ArrayMesh(data['xyz'], data['faces'], data['classes'], data['rest'],
        data['anchors'], int(data['generation']))
    mesh.surface = str(data['surface'])
    chart = data['chart']
    if (mesh.generation != 7 or mesh.surface != 'mean' or
            mesh.faces.shape != (parent['control_quads'], 4) or len(mesh.xyz) != parent['control_vertices']):
        raise ValueError('Actual baseline G7 controls disagree with their receipt.')
    raw_xyz = loader.arrays(RAW/'control_quad.npz', ('xyz',))['xyz']
    if raw_xyz.shape != mesh.xyz.shape or not np.isfinite(raw_xyz).all():
        raise ValueError('Finite matching actual raw XYZ required.')
    if array_hash(raw_xyz) != raw['checks']['control_xyz_sha256']:
        raise ValueError('Actual raw XYZ hash differs from saved verification.')
    pairs = loader.arrays(PARENT/'evidence.npz', ('mirror_x_vertex_pairs',
        'mirror_y_vertex_pairs', 'mirror_x_face_pairs', 'mirror_y_face_pairs'))
    vertex_pairs = dict(X=pairs['mirror_x_vertex_pairs'], Y=pairs['mirror_y_vertex_pairs'])
    ids, actual_pairs = field._mirror_pairs(vertex_pairs, len(mesh.xyz))
    unfiltered = raw_xyz-mesh.xyz
    del raw_xyz, data
    degree = np.bincount(mesh.faces.ravel(), minlength=len(mesh.xyz))
    if np.any(degree == 0):
        raise ValueError('Orphan baseline vertices are not repaired.')
    before = displacement_stats(unfiltered)
    guard = base.finish.memory_guard()
    current = unfiltered
    for iteration in range(ITERATIONS):
        print('FILTER saved displacement only', iteration+1, '/', ITERATIONS, flush=True)
        current = uniform_displacement_pass(current, mesh.faces, degree)
    print('TRANSPORT final filtered displacement with actual source mirror IDs', flush=True)
    filtered, representative, fixed_x, fixed_y = field._transport(current, ids, actual_pairs)
    del current, representative, fixed_x, fixed_y, degree, ids
    after = displacement_stats(filtered)
    output_xyz = mesh.xyz+filtered
    if not np.isfinite(output_xyz).all():
        raise ValueError('Nonfinite filtered displacement result; no fallback.')
    actual_unmoved = int(np.count_nonzero(np.all(output_xyz == mesh.xyz, axis=1)))
    # Reuse the verified unchanged baseline association arrays; only XYZ is new.
    out = core.ArrayMesh(output_xyz, mesh.faces, mesh.classes, mesh.rest, mesh.anchors, 7)
    out.surface = 'mean'
    state = dict(unfiltered_delta=unfiltered, filtered_delta=filtered, **pairs)
    print('VERIFY actual reflected G7 XYZ and oriented quad cycles', flush=True)
    symmetry = loader.actual_symmetry(out, state)
    hashes = dict(raw['geometry_code_sha256'])
    hashes[str((HERE/'smooth_relief.py').relative_to(REPO))] = digest(HERE/'smooth_relief.py')
    metadata = dict(experiment='PARENT_LINKED_DISPLACEMENT_FINISH_20261013',
        schema='CHESHIRE_SAVED_RELIEF_UNIFORM_FILTER_V1', smoothing_iterations=ITERATIONS,
        alpha=ALPHA, baseline_geometry_filtered=False,
        equation='delta_next=.5*delta+.5*uniform_actual_edge_neighbor_mean(delta)',
        neighborhood_scope='Verified closed quad edge-neighbor graph; at most three edges of halo beyond initially nonzero relief.',
        reflection_scope='One final minimum-ID orbit displacement transport using existing source X/Y IDs; source coordinates are retained.',
        before_filter=before, after_filter=after,
        actual_unmoved_vertex_count=actual_unmoved,
        actual_unmoved_vertex_fraction=float(actual_unmoved/len(out.xyz)),
        count_scope='Control-vertex fractions, not surface area.',
        unchanged_association_npy_sha256=associations,
        raw_field=raw['operator_metadata'], raw_field_stage=str(RAW),
        normal_field_passes_computed_this_finish=0,
        geometry_scope='Actual unchanged selected MIDDLE_SURFACE G7 XYZ plus filtered(raw_trial02_XYZ-baseline_XYZ); no averaging of baseline XYZ.',
        dependency_scope='Two required actual inputs: baseline G7 supplies geometry/topology/associations, while frozen trial02 supplies the already-computed CHILD+GRANDCHILD displacement. This finish does not recompute those two fields.',
        success_scope='Displacement smoothing only; no claim that detail hierarchy, branch structure, or visual quality is solved.')
    context = dict(input_case='SPAN', candidate='PARENT_LINKED', source=str(PARENT),
        source_generation=7, source_control_sha256=parent['control_file_sha256'],
        source_generation_json_sha256=parent_generation_sha256, parent_stage=str(PARENT),
        parent_control_sha256=parent['control_file_sha256'],
        parent_generation_json_sha256=parent_generation_sha256,
        raw_field_stage=str(RAW), raw_field_control_sha256=raw['control_file_sha256'],
        raw_field_evidence_sha256=raw['evidence_file_sha256'],
        raw_field_generation_json_sha256=raw_generation_sha256,
        raw_field_summary_sha256=raw_summary_sha256,
        geometry_code_sha256=hashes, added_CC_passes=0, added_topology_events=0,
        added_normal_field_passes=2, added_normal_field_passes_this_finish=0,
        cumulative_normal_field_passes=raw['cumulative_normal_field_passes'],
        smoothing_passes=ITERATIONS, added_mandelbulb_evaluations=0,
        operator_metadata=metadata, frame_ancestry=raw['frame_ancestry'], symmetry=symmetry,
        memory_guard_before_load=memory_before_load, memory_guard=guard,
        field_count_scope='Two normal passes inherited from the actual raw dependency relative to the baseline source; zero normal passes evaluated in this smoothing finish.',
        user_density_baseline='Selected MIDDLE; global FINE remains unapplied.',
        design_scope='One fixed three-pass smoothing finish of broad connected-rib displacement; baseline large grooves and geometry are not averaged.',
        dependency_scope=metadata['dependency_scope'],
        intermediate_scope='Raw trial02 evidence preserves CHILD/GRANDCHILD intermediate deltas; new evidence stores only the unfiltered and filtered combined relief plus actual mirror correspondences.',
        validation_scope='Saved finite/closed-oriented/connectivity/no-orphan/native-area checks once, plus actual G7 reflected XYZ and oriented control cycles.',
        exclusions=['Additional subdivision', 'New field parameters', 'Baseline geometry smoothing',
            'Independent full geometry replay', 'Native triangle-set sorting',
            'Self-intersection repair', 'Fabrication suitability', 'Aesthetic certification'])
    del mesh, pairs
    gc.collect()
    print('SAVE one filtered actual G7 and required existing mesh checks', flush=True)
    record = core.save(folder, out, chart, context, state)
    for source, info, generation_sha256 in ((PARENT, parent, parent_generation_sha256),
            (RAW, raw, raw_generation_sha256)):
        base.checked(source, info, (('control_quad.npz', 'control_file_sha256'),
            ('evidence.npz', 'evidence_file_sha256')))
        if digest(source/'generation.json') != generation_sha256:
            raise ValueError('Preserved input generation receipt changed during finish.')
        check_code(info)
    if digest(raw_summary_file) != raw_summary_sha256:
        raise ValueError('Preserved raw dependency summary changed during finish.')
    write(root/'SUMMARY.json', dict(source=str(PARENT), source_generation=7,
        source_control_sha256=parent['control_file_sha256'], candidate='PARENT_LINKED',
        input_case='SPAN', folder=str(folder), subdivision_generation=7,
        raw_field_stage=str(RAW), raw_field_control_sha256=raw['control_file_sha256'],
        raw_field_generation_json_sha256=raw_generation_sha256,
        added_CC_passes=0, added_topology_events=0, added_normal_field_passes=2,
        added_normal_field_passes_this_finish=0, smoothing_passes=ITERATIONS,
        generation_json_sha256=digest(folder/'generation.json'), checks=record['checks'],
        symmetry=symmetry, operator_metadata=metadata, frame_ancestry=raw['frame_ancestry'],
        geometry_code_sha256=hashes, dependency_scope=metadata['dependency_scope'],
        visual_success='PENDING_ACTUAL_WHOLE_AND_CLOSE_RENDER_REVIEW'))
    print('DONE saved displacement finish only, actual G7, no new field or CC', flush=True)


if __name__ == '__main__':
    main()
