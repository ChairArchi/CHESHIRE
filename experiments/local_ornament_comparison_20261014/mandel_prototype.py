"""One real finite power-8 Mandelbulb surface for local ornament placement.

Reuse the preserved spherical-power escape count, then extract a complete
three-dimensional finite escape-time isosurface with Lewiner marching cubes.
This is not a height atlas, signed distance estimate, infinite-set boundary,
body deformation, smoothing pass, or an automatic attachment operation.
Only the largest connected extracted component is retained. A uniform affine
normalization preserves its shape while setting root Z=0 and maximum Z=1.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import platform
import shutil
import sys
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/local_ornament_comparison_20261014/trial01')
PACKAGE_ROOT = Path('E:/CHESHIRE_DATA/python_packages/local_ornament_20261014')
ESCAPE_SOURCE = REPO/'experiments/iaac_mandelbrot_20261011/study.py'
RECIPE = dict(
    schema='CHESHIRE_LOCAL_ORNAMENT_MANDELBULB_PROTOTYPE_20261014',
    power=8, iterations=10, bailout=4.,
    grid_resolution=193, grid_bounds=[[-1.35, 1.35]]*3,
    grid_axis_order=['X', 'Y', 'Z'], grid_chunk_points=180000,
    field='Preserved escape_field returns continuous escape count nu and finite unescaped membership; nu is the isosurface scalar.',
    formula='z0=0; z(k+1)=r^8*(sin(8*polar)*cos(8*azimuth), sin(8*polar)*sin(8*azimuth), cos(8*polar))+c, polar=acos(z.z/r), azimuth=atan2(z.y,z.x). Stop each point at norm(z)>4 or after 10 updates.',
    escaped_count='nu=step+2-log(log(norm(z)))/log(8) at first escape; finite unescaped points receive nu=10.',
    isolevel=9.5,
    finite_set_distinction='The superlevel nu>=9.5 includes some late-escaping points. It is explicitly a finite escape-time isosurface, not the exact 10-step occupancy boundary, signed distance, or infinite Mandelbulb set.',
    extraction='scikit-image.measure.marching_cubes, Lewiner method, gradient_direction=descent, step_size=1, allow_degenerate=False.',
    component_policy='Retain only the largest extracted vertex-edge connected component; discard every other component and compact vertex IDs.',
    normalization='Subtract bounding-box XY centre and raw minimum Z; divide all XYZ by the same raw Z extent. No anisotropic scale or smoothing.',
    normalized_contract='Minimum Z=0, maximum Z=1, XY radial maximum<=1; actual radial maximum is recorded for later footprint sizing.',
    source_body_modified=False, attachment_executed=False,
    smoothing_passes=0, subdivision_passes=0, remesh_passes=0,
    scope='One fixed standalone local ornament prototype. Placement, root embedding, body connection, motif reflection, self-intersection and visual suitability are not certified here.'
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def array_hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def load_escape():
    spec = importlib.util.spec_from_file_location('local_ornament_preserved_escape', ESCAPE_SOURCE)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result.escape_field


def extraction_dependency():
    if not PACKAGE_ROOT.is_dir():
        raise FileNotFoundError('Task-owned E-drive scikit-image package directory is required.')
    sys.path.insert(0, str(PACKAGE_ROOT))
    from skimage.measure import marching_cubes
    records = {}
    for name in ('skimage', 'skimage.measure._marching_cubes_lewiner',
                 'skimage.measure._marching_cubes_lewiner_cy',
                 'skimage.measure._marching_cubes_lewiner_luts', 'lazy_loader'):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        if not path.is_relative_to(PACKAGE_ROOT.resolve()):
            raise ValueError('Extraction dependency escaped task-owned E package root: '+str(path))
        records[name] = dict(path=str(path), sha256=digest(path))
    return marching_cubes, dict(package_root=str(PACKAGE_ROOT),
        scikit_image_version=importlib.metadata.version('scikit-image'),
        lazy_loader_version=importlib.metadata.version('lazy_loader'),
        numpy_version=np.__version__, scipy_version=importlib.metadata.version('scipy'),
        python=platform.python_version(), python_executable=sys.executable,
        implementation_files=records)


def sample_field(escape):
    n = RECIPE['grid_resolution']
    axis = np.linspace(-1.35, 1.35, n, dtype=float)
    scalar = np.empty(n*n*n, np.float32)
    finite_inside = np.empty(n*n*n, bool)
    for start in range(0, len(scalar), RECIPE['grid_chunk_points']):
        stop = min(start+RECIPE['grid_chunk_points'], len(scalar))
        indices = np.arange(start, stop, dtype=np.int64)
        ix, remainder = np.divmod(indices, n*n)
        iy, iz = np.divmod(remainder, n)
        points = np.column_stack([axis[ix], axis[iy], axis[iz]])
        _, nu, inside = escape(points, power=RECIPE['power'],
            iterations=RECIPE['iterations'], bailout=RECIPE['bailout'])
        if not np.isfinite(nu).all():
            raise ValueError('Preserved escape function returned nonfinite counts.')
        scalar[start:stop] = nu
        finite_inside[start:stop] = inside
        if start == 0 or stop == len(scalar) or (start//RECIPE['grid_chunk_points']) % 8 == 0:
            print('MANDELBULB_FIELD', stop, '/', len(scalar), flush=True)
    scalar, finite_inside = scalar.reshape(n, n, n), finite_inside.reshape(n, n, n)
    level = RECIPE['isolevel']
    boundary_maximum = max(float(scalar[0].max()), float(scalar[-1].max()),
        float(scalar[:, 0].max()), float(scalar[:, -1].max()),
        float(scalar[:, :, 0].max()), float(scalar[:, :, -1].max()))
    if boundary_maximum >= level:
        raise ValueError('Finite isosurface reaches the fixed sampling boundary; no automatic grid enlargement.')
    positive = scalar >= level
    return scalar, dict(shape=list(scalar.shape), dtype=str(scalar.dtype),
        scalar_sha256=array_hash(scalar), finite_membership_sha256=array_hash(finite_inside),
        scalar_minimum=float(scalar.min()), scalar_maximum=float(scalar.max()),
        boundary_scalar_maximum=boundary_maximum, sampled_points=int(scalar.size),
        finite_unescaped_points=int(finite_inside.sum()), isosurface_positive_points=int(positive.sum()),
        late_escaped_points_in_superlevel=int(np.count_nonzero(positive & ~finite_inside)),
        finite_unescaped_points_outside_superlevel=int(np.count_nonzero(finite_inside & ~positive)),
        all_sampling_boundary_values_below_isolevel=True)


def keep_main_component(xyz, faces):
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    graph = coo_matrix((np.ones(len(edges), np.uint8), (edges[:, 0], edges[:, 1])),
                      shape=(len(xyz), len(xyz))).tocsr()
    count, labels = connected_components(graph, directed=False)
    sizes = np.bincount(labels)
    main = int(np.argmax(sizes))
    selected = labels == main
    keep = np.all(selected[faces], axis=1)
    ids = np.flatnonzero(selected)
    index = np.full(len(xyz), -1, np.int64)
    index[ids] = np.arange(len(ids))
    result = index[faces[keep]]
    if result.min() < 0:
        raise ValueError('Largest component compaction lost an actual face vertex.')
    return xyz[ids].astype(float), result.astype(np.int32), dict(
        extracted_components=int(count), extracted_component_sizes_descending=sorted(sizes.tolist(), reverse=True),
        extracted_vertex_count=len(xyz), extracted_triangle_count=len(faces),
        kept_component_vertices=len(ids), kept_component_triangles=len(result),
        discarded_vertices=int(len(xyz)-len(ids)), discarded_triangles=int(np.count_nonzero(~keep)),
        selected_original_vertex_ids_sha256=array_hash(ids))


def verify_mesh(xyz, faces):
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3 or
            not len(xyz) or not len(faces) or not np.isfinite(xyz).all() or
            faces.min() < 0 or faces.max() >= len(xyz)):
        raise ValueError('Invalid actual standalone prototype arrays.')
    a, b, c = xyz[faces[:, 0]], xyz[faces[:, 1]], xyz[faces[:, 2]]
    crosses = np.cross(b-a, c-a)
    area = np.linalg.norm(crosses, axis=1)*.5
    signed_volume = float(np.einsum('ij,ij->i', a, np.cross(b, c)).sum()/6.)
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    signs = np.where(directed[:, 0] < directed[:, 1], 1., -1.)
    edges = np.sort(directed, axis=1)
    unique, inverse, incidence = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    balance = np.bincount(inverse, weights=signs)
    graph = coo_matrix((np.ones(len(unique), np.uint8), (unique[:, 0], unique[:, 1])),
                      shape=(len(xyz), len(xyz))).tocsr()
    components, labels = connected_components(graph, directed=False)
    orphans = int(np.count_nonzero(np.bincount(faces.ravel(), minlength=len(xyz)) == 0))
    checks = dict(finite=True, indexed_triangles=True,
        positive_triangle_area=bool(area.min() > 0.), minimum_triangle_area=float(area.min()),
        closed_two_face_edges=bool(np.all(incidence == 2)),
        consistently_oriented_edges=bool(np.all(balance == 0.)),
        boundary_edges=int(np.count_nonzero(incidence == 1)),
        nonmanifold_edges=int(np.count_nonzero(incidence > 2)),
        single_connected_component=bool(components == 1), connected_components=int(components),
        no_orphan_vertices=bool(orphans == 0), orphan_vertices=orphans,
        positive_signed_volume=bool(signed_volume > 0.), signed_volume=signed_volume,
        vertices=len(xyz), triangles=len(faces), unique_edges=len(unique),
        Euler_characteristic=int(len(xyz)-len(unique)+len(faces)))
    passed = all(checks[key] for key in ('finite', 'indexed_triangles', 'positive_triangle_area',
        'closed_two_face_edges', 'consistently_oriented_edges', 'single_connected_component',
        'no_orphan_vertices', 'positive_signed_volume'))
    checks['all_required_checks_pass'] = bool(passed)
    if not passed:
        raise ValueError('Actual prototype integrity failure: '+json.dumps(checks))
    return checks


def root_axis_evidence(xyz, faces, raw_origin, raw_height, escape):
    """Inspect actual saved-surface axis intersections around 22% embedding.

    A closed-mesh vertical ray parity test is independent of the analytic
    finite escape-count probe. This is standalone root geometry evidence,
    not a claim that any column attachment has already been performed.
    """
    a, b, c = xyz[faces[:, 0]], xyz[faces[:, 1]], xyz[faces[:, 2]]
    ab, ac = b[:, :2]-a[:, :2], c[:, :2]-a[:, :2]
    q = -a[:, :2]  # Actual nominal normalized XY=(0,0) axis.
    cross2 = lambda x, y: x[:, 0]*y[:, 1]-x[:, 1]*y[:, 0]
    denominator = cross2(ab, ac)
    nonparallel = np.abs(denominator) > 1e-18
    u = np.divide(cross2(q, ac), denominator, out=np.zeros(len(faces)), where=nonparallel)
    v = np.divide(cross2(ab, q), denominator, out=np.zeros(len(faces)), where=nonparallel)
    hit = nonparallel & (u >= -1e-10) & (v >= -1e-10) & (u+v <= 1.+1e-10)
    intersections = np.sort(a[hit, 2]+u[hit]*(b[hit, 2]-a[hit, 2])+v[hit]*(c[hit, 2]-a[hit, 2]))
    intersections = intersections[np.r_[True, np.diff(intersections) > 1e-9]] if len(intersections) else intersections
    probes = np.array([[0., 0., .21], [0., 0., .22], [0., 0., .23]])
    raw_probes = probes*raw_height+raw_origin
    _, nu, finite_inside = escape(raw_probes, power=RECIPE['power'],
        iterations=RECIPE['iterations'], bailout=RECIPE['bailout'])
    rows = []
    for point, raw, count, inside in zip(probes, raw_probes, nu, finite_inside):
        above = int(np.count_nonzero(intersections > point[2]+1e-9))
        on_surface = bool(np.any(np.abs(intersections-point[2]) <= 1e-9))
        rows.append(dict(normalized_point=point.tolist(), raw_field_point=raw.tolist(),
            finite_escape_count=float(count), finite_unescaped=bool(inside),
            analytic_superlevel=bool(count >= RECIPE['isolevel']),
            actual_mesh_ray_hits_above=above, actual_mesh_axis_inside_by_ray_parity=bool(above % 2 == 1 and not on_surface),
            on_axis_surface=on_surface))
    return dict(nominal_root_axis_XY=[0., 0.], proposed_embedding_height_fraction=.22,
        minimum_Z_surface_vertex=xyz[int(np.argmin(xyz[:, 2]))].tolist(),
        actual_mesh_vertical_axis_intersection_Z=intersections.tolist(),
        probes=rows,
        root_axis_crosses_inside_neighborhood=bool(all(row['actual_mesh_axis_inside_by_ray_parity'] for row in rows)),
        scope='Actual prototype triangles, unique vertical-axis surface hits deduplicated at 1e-9, and independent finite escape probes. No column intersection or final attachment has been executed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    folder = root/'prototypes'
    output = folder/'MANDELBULB.npz'
    receipt_path = folder/'MANDELBULB_PROTOTYPE_RECEIPT.json'
    failure_path = folder/'MANDELBULB_PROTOTYPE_FAILURE.json'
    if any(path.exists() for path in (output, receipt_path, failure_path)):
        raise FileExistsError('Earlier prototype/checkpoint preserved; use a new root.')
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = folder/'MANDELBULB_source_snapshot'
    snapshot.mkdir(exist_ok=False)
    code_hashes = {str(p.relative_to(REPO)).replace('\\', '/'): digest(p)
                   for p in (Path(__file__), ESCAPE_SOURCE)}
    for path in (Path(__file__), ESCAPE_SOURCE):
        shutil.copyfile(path, snapshot/path.name)
    started = time.perf_counter()
    phase = 'LOAD_EXTRACTION_DEPENDENCY'
    try:
        marching_cubes, dependencies = extraction_dependency()
        escape = load_escape()
        phase = 'SAMPLE_ONE_FIXED_FINITE_ESCAPE_FIELD'
        scalar, field_record = sample_field(escape)
        phase = 'EXTRACT_ACTUAL_3D_ISOSURFACE'
        spacing = 2.70/(RECIPE['grid_resolution']-1)
        xyz, faces, _, _ = marching_cubes(scalar, level=RECIPE['isolevel'],
            spacing=(spacing, spacing, spacing), gradient_direction='descent',
            step_size=1, allow_degenerate=False, method='lewiner')
        xyz = xyz.astype(float)-1.35
        del scalar
        gc.collect()
        phase = 'RETAIN_LARGEST_ACTUAL_CONNECTED_COMPONENT'
        xyz, faces, components = keep_main_component(xyz, faces)
        raw_min, raw_max = xyz.min(axis=0), xyz.max(axis=0)
        height = float(raw_max[2]-raw_min[2])
        if not np.isfinite(height) or height <= 0.:
            raise ValueError('Extracted prototype has no positive Z extent.')
        origin = np.array([(raw_min[0]+raw_max[0])*.5, (raw_min[1]+raw_max[1])*.5, raw_min[2]])
        xyz = (xyz-origin)/height
        # Retain its complete geometry; only global face orientation may reverse.
        signed_volume = np.einsum('ij,ij->i', xyz[faces[:, 0]],
            np.cross(xyz[faces[:, 1]], xyz[faces[:, 2]])).sum()/6.
        reversed_winding = bool(signed_volume < 0.)
        if reversed_winding:
            faces = faces[:, [0, 2, 1]].copy()
        radial = np.linalg.norm(xyz[:, :2], axis=1)
        if xyz[:, 2].min() != 0. or xyz[:, 2].max() != 1. or radial.max() > 1.:
            raise ValueError('Uniform prototype normalization does not meet the fixed interface.')
        phase = 'VERIFY_ACTUAL_COMPLETE_PROTOTYPE'
        checks = verify_mesh(xyz, faces)
        root_evidence = root_axis_evidence(xyz, faces, origin, height, escape)
        phase = 'SAVE_STANDALONE_PROTOTYPE'
        np.savez_compressed(output, xyz=xyz, faces=faces)
        record = dict(date='2026-10-14', timezone='Asia/Seoul', prototype='MANDELBULB',
            recipe=RECIPE, geometry=str(output), geometry_sha256=digest(output),
            xyz_sha256=array_hash(xyz), faces_sha256=array_hash(faces),
            xyz_dtype=str(xyz.dtype), faces_dtype=str(faces.dtype),
            grid_field=field_record, component_extraction=components,
            normalization=dict(raw_bounds=[raw_min.tolist(), raw_max.tolist()],
                raw_translation_origin=origin.tolist(), uniform_scale=1./height,
                normalized_bounds=[xyz.min(axis=0).tolist(), xyz.max(axis=0).tolist()],
                normalized_radial_maximum=float(radial.max()), normalized_z_minimum=0., normalized_z_maximum=1.),
            global_winding_reversed=reversed_winding, checks=checks,
            root_axis_evidence=root_evidence,
            dependencies=dependencies, geometry_code_sha256=code_hashes,
            elapsed_seconds=time.perf_counter()-started,
            source_body_loaded=False, source_body_modified=False,
            smoothing_passes=0, subdivision_passes=0, remesh_passes=0,
            actual_root_attachment='NOT_EXECUTED_STANDALONE_PROTOTYPE',
            exact_XY_motif_reflection='NOT_EXECUTED_BY_PROTOTYPE_BUILDER',
            self_intersection='NOT_CERTIFIED', fabrication='NOT_CHECKED', visual_success='PENDING_ACTUAL_RENDER')
        if any(digest(REPO/rel) != expected for rel, expected in code_hashes.items()):
            raise ValueError('Frozen prototype/escape source changed during execution.')
        write(receipt_path, record)
        print('MANDELBULB_PROTOTYPE_SAVED', len(xyz), len(faces), radial.max(), flush=True)
    except Exception as error:
        write(failure_path, dict(date='2026-10-14', phase=phase,
            error_type=type(error).__name__, error=str(error), recipe=RECIPE,
            geometry_code_sha256=code_hashes, elapsed_seconds=time.perf_counter()-started,
            source_body_loaded=False, source_body_modified=False))
        raise


if __name__ == '__main__':
    main()
