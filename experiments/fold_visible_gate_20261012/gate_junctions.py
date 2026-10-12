"""Thicken and lower lintel seats until sampled actual column-head intervals overlap.

The two accepted current columns and their transforms are unchanged. The lintel
keeps all axial stations and its topology; overlap is permitted and no Boolean,
weld, physical bearing or structural-joint claim is made.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np

import symmetric_lintel as lintel
from wall_fold import plateau


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(array):
    a = np.ascontiguousarray(array)
    return dict(shape=list(a.shape), dtype=a.dtype.str,
        sha256=hashlib.sha256(a.tobytes()).hexdigest())


def read_arrays(path):
    return lintel.arrays(path)


class VerticalTriangles:
    """Exact barycentric vertical intersections of actual triangles, no rtree."""
    def __init__(self, xyz, faces):
        self.tri = np.asarray(xyz)[np.asarray(faces)]
        self.lo = self.tri[:, :, :2].min(axis=1)
        self.hi = self.tri[:, :, :2].max(axis=1)

    def hits(self, xy):
        xy = np.asarray(xy)
        keep = np.all((xy >= self.lo-1e-12) & (xy <= self.hi+1e-12), axis=1)
        t = self.tri[keep]
        a, b = t[:, 1, :2]-t[:, 0, :2], t[:, 2, :2]-t[:, 0, :2]
        determinant = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
        good = np.abs(determinant) > 1e-14
        t, a, b, determinant = t[good], a[good], b[good], determinant[good]
        d = xy-t[:, 0, :2]
        u = (d[:, 0]*b[:, 1]-d[:, 1]*b[:, 0])/determinant
        v = (a[:, 0]*d[:, 1]-a[:, 1]*d[:, 0])/determinant
        inside = (u >= -1e-10) & (v >= -1e-10) & (u+v <= 1+1e-10)
        z = t[:, 0, 2]+u*(t[:, 1, 2]-t[:, 0, 2])+v*(t[:, 2, 2]-t[:, 0, 2])
        z = np.sort(z[inside])
        return z[np.r_[True, np.diff(z) > 1e-9]] if len(z) else z


def intervals(hits):
    if len(hits) < 2 or len(hits) % 2:
        return None
    return np.asarray(hits).reshape(-1, 2)


def section_extent(xyz, faces, station):
    """Extent of actual triangle/constant-local-Z intersection segments."""
    tri = xyz[faces]
    tri = tri[(tri[:, :, 2].min(1) <= station) & (tri[:, :, 2].max(1) >= station)]
    points = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        difference = tri[:, j, 2]-tri[:, i, 2]
        good = (np.abs(difference) > 1e-14) & ((tri[:, i, 2]-station)*(tri[:, j, 2]-station) <= 0)
        fraction = (station-tri[good, i, 2])/difference[good]
        points.append(tri[good, i]+fraction[:, None]*(tri[good, j]-tri[good, i]))
    points = np.vstack(points)
    if not len(points):
        raise ValueError('No actual lintel cross section at requested seat.')
    return np.ptp(points[:, :2], axis=0)


def contact_records(beam_xyz, beam_faces, column_surfaces, rays, required_overlap):
    beam = VerticalTriangles(beam_xyz, beam_faces)
    records = []
    for name, xy, central in rays:
        column_hits = column_surfaces[name].hits(xy)
        beam_hits = beam.hits(xy)
        ci, bi = intervals(column_hits), intervals(beam_hits)
        overlap = 0.
        if ci is not None and bi is not None:
            # Only the topmost actual column interval counts as a head join.
            head = ci[-1]
            overlap = float(np.maximum(0., np.minimum(head[1], bi[:, 1])-
                np.maximum(head[0], bi[:, 0])).max(initial=0.))
        records.append(dict(seat=name, world_xy=np.asarray(xy).tolist(), central=central,
            column_hits=column_hits.tolist(), beam_hits=beam_hits.tolist(),
            parity_valid=ci is not None and bi is not None,
            topmost_column_interval_overlap=overlap, passes=overlap >= required_overlap))
    return records


def contact_passes(records):
    for name in ('LEFT', 'RIGHT'):
        rows = [r for r in records if r['seat'] == name]
        if sum(r['passes'] for r in rows) < 5 or not any(r['central'] and r['passes'] for r in rows):
            return False
    return True


def deform(reference, weights, factor, drop):
    result = reference.copy()
    scale = 1.+(factor-1.)*weights
    result[:, :2] *= scale[:, None]
    result[:, 0] -= drop*weights
    return result


def generate(source, column, root):
    source, column, root = source.resolve(), column.resolve(), root.resolve()
    if root.exists():
        raise FileExistsError('Existing joined gate result preserved: '+str(root))
    source_beam = source/'lintel/WALL/G03'
    metadata = json.loads((source/'WALL/assembly.json').read_text(encoding='utf8'))
    if sha(column) != metadata['source_column_sha256']:
        raise ValueError('The exact accepted existing column geometry is required.')
    columns = read_arrays(column)
    source_control = read_arrays(source_beam/'control_quad.npz')
    original_beam = read_arrays(source_beam/'geometry.npz')
    mesh, chart, _ = lintel.study.previous.anchor.t.load(source_beam)
    reference = mesh.xyz.copy()
    transform = np.asarray(metadata['lintel_transform'])
    transforms = {name: np.asarray(t) for name, t in metadata['column_transforms'].items()}
    # Fixed accepted transform: beam local Z is world X and local X is world Z.
    if not np.array_equal(transform[:3, :3], [[0, 0, 1], [0, -1, 0], [1, 0, 0]]):
        raise ValueError('Expected the accepted proper lintel orientation.')
    world_columns = {name: lintel.gate_layout.apply_transform(columns['xyz'], t)
        for name, t in transforms.items()}
    width = float(metadata['target_lintel_vertical_section'])
    depth = float(metadata['target_lintel_depth'])
    seats = np.array([transforms[name][0, 3]-transform[0, 3] for name in ('LEFT', 'RIGHT')])
    halfwidth = .65*width
    seat_weights = np.array([plateau((reference[:, 2]-seat)/halfwidth, .45) for seat in seats])
    weights = seat_weights.max(axis=0)
    source_sections = np.array([section_extent(original_beam['xyz'], original_beam['faces'], s) for s in seats])
    # 1.65 is the nominal visible enlargement. The actual section must also be
    # thicker than the original member's largest transverse envelope.
    original_envelope = np.ptp(original_beam['xyz'][:, :2], axis=0)
    factor = max(1.65, float(np.max(1.15*original_envelope/source_sections.min(axis=0))))
    if factor > 2.75:
        raise ValueError('Required joint thickening exceeds declared bounded experiment.')
    column_surfaces = {name: VerticalTriangles(xyz, columns['faces']) for name, xyz in world_columns.items()}
    rays = []
    for name in ('LEFT', 'RIGHT'):
        centre = transforms[name][0, 3]
        for dx in (-.18*width, 0., .18*width):
            for y in (-.12*depth, 0., .12*depth):
                rays.append((name, [centre+dx, y], dx == 0 and y == 0))
    required_overlap = .035*width
    before_world = lintel.gate_layout.apply_transform(original_beam['xyz'], transform)
    before = contact_records(before_world, original_beam['faces'], column_surfaces, rays, required_overlap)
    history = []
    drop = 0.
    final = None
    # Actual triangle feedback, not a bbox seating assumption. A common drop
    # preserves left/right symmetry even if individual ray estimates differ.
    for attempt in range(21):
        mesh.xyz = deform(reference, weights, factor, drop)
        native = lintel.study.previous.anchor.t.growth.native(mesh)
        world = lintel.gate_layout.apply_transform(native.xyz, transform)
        records = contact_records(world, native.faces[:, :3], column_surfaces, rays, required_overlap)
        passed = contact_passes(records)
        history.append(dict(attempt=attempt, common_seat_drop=drop,
            passing_rays={name: sum(r['passes'] for r in records if r['seat'] == name) for name in ('LEFT', 'RIGHT')},
            central_overlap={name: next(r['topmost_column_interval_overlap'] for r in records
                if r['seat'] == name and r['central']) for name in ('LEFT', 'RIGHT')}, passed=passed))
        if passed:
            final = native, world, records
            break
        needed = []
        for record in records:
            if record['parity_valid']:
                needed.append(max(0., record['beam_hits'][0]-record['column_hits'][-1]+1.5*required_overlap))
        increment = max(.025*width, float(np.percentile(needed, 75)) if needed else .05*width)
        drop += increment
        if drop > .75*width:
            break
    if final is None:
        raise ValueError('Actual head overlap not obtained within bounded drop: '+json.dumps(history))
    native, world_beam, after = final
    faces = native.faces[:, :3]
    local_checks = lintel.geometry_checks(native.xyz, faces, components=1)
    axial = lintel.reflection(native.xyz, faces, axis=2, plane=metadata['target_lintel_length']/2)
    axial_station_error = float(np.max(np.abs(mesh.xyz[:, 2]-reference[:, 2])))
    actual_sections = np.array([section_extent(native.xyz, faces, s) for s in seats])
    relative_sections = actual_sections/source_sections
    enlarged_vs_original_envelope = actual_sections/original_envelope
    if not local_checks['passed'] or not axial['passed'] or axial_station_error != 0:
        raise ValueError('Joined lintel basic integrity or axial station failure.')
    if np.any(enlarged_vs_original_envelope < 1.1):
        raise ValueError('Actual joint cross sections are not thicker than the original member.')
    count = len(columns['xyz'])
    assembly_xyz = np.vstack([world_columns['LEFT'], world_columns['RIGHT'], world_beam])
    assembly_faces = np.vstack([columns['faces'], columns['faces']+count, faces+2*count])
    labels = np.r_[np.zeros(len(columns['faces']), np.int8), np.ones(len(columns['faces']), np.int8),
        np.full(len(faces), 2, np.int8)]
    checks = lintel.geometry_checks(assembly_xyz, assembly_faces, components=3)
    checks['global_left_right'] = lintel.reflection(assembly_xyz, assembly_faces, axis=0)
    original_assembly = read_arrays(source/'WALL/geometry.npz')
    column_error = float(np.max(np.abs(assembly_xyz[:2*count]-original_assembly['xyz'][:2*count])))
    columns_faces_equal = np.array_equal(assembly_faces[:2*len(columns['faces'])],
        original_assembly['faces'][:2*len(columns['faces'])])
    if not checks['passed'] or not checks['global_left_right']['passed'] or column_error != 0 or not columns_faces_equal:
        raise ValueError('Joined assembly did not preserve exact current columns/basic geometry.')
    root.mkdir(parents=True)
    before_folder = root/'beam/CONTROL/G03'; before_folder.mkdir(parents=True)
    for name in ('control_quad.npz', 'geometry.npz', 'generation.json'):
        shutil.copyfile(source_beam/name, before_folder/name)
    after_folder = root/'beam/JOINED/G03'; after_folder.mkdir(parents=True)
    control_after = dict(source_control, xyz=mesh.xyz)
    np.savez_compressed(after_folder/'control_quad.npz', **control_after)
    np.savez_compressed(after_folder/'geometry.npz', xyz=native.xyz, faces=faces)
    operation = dict(reference_xyz=reference, delta=mesh.xyz-reference, weights=weights,
        seat_weights=seat_weights, section_factor=np.array(factor), common_drop=np.array(drop),
        seat_local_z=seats, support_halfwidth=np.array(halfwidth), chart=chart,
        beam_transform=transform, column_left_transform=transforms['LEFT'], column_right_transform=transforms['RIGHT'])
    np.savez_compressed(after_folder/'operation_fields.npz', **operation)
    generation = dict(candidate='JOINED', source=str(source_beam), source_control_sha256=sha(source_beam/'control_quad.npz'),
        actual_cross_section_factors=relative_sections.tolist(), nominal_section_factor=factor,
        common_downward_seat_shift=drop, axial_station_max_error=axial_station_error,
        target_overlap_per_ray=required_overlap, local_geometry_checks=local_checks, local_axial_reflection=axial,
        operation='Continuous control deformation; native fan surface regenerated; no new subdivision or Boolean',
        structural_joint='NOT_IMPLEMENTED', fabrication='NOT_CHECKED', self_intersection='NOT_CHECKED')
    (after_folder/'generation.json').write_text(json.dumps(generation, indent=2), encoding='utf8')
    for mode in ('CONTROL', 'JOINED'):
        folder = root/mode; folder.mkdir(parents=True)
        if mode == 'CONTROL':
            shutil.copyfile(source/'WALL/geometry.npz', folder/'geometry.npz')
            item = dict(metadata, candidate=mode, original_fixed_gate_candidate='WALL',
                comparison='Existing accepted gate with its original gap', source=str(source/'WALL'))
        else:
            np.savez_compressed(folder/'geometry.npz', xyz=assembly_xyz, faces=assembly_faces, face_member=labels)
            item = dict(metadata, candidate=mode, checks=checks, column_array_max_error=column_error,
                column_triangle_arrays_identical=bool(columns_faces_equal),
                lintel_operation='Thickened local seat regions, actual triangle feedback fitted downward shift, deliberate overlap',
                nominal_section_factor=factor, common_seat_drop=drop,
                seating='Positive actual sampled head/beam vertical parity intervals; no welded or structural bearing claim',
                actual_bbox_vertical_gap=float(world_beam[:, 2].min()-max(v[:, 2].max() for v in world_columns.values())),
                intersections='Beam/column overlap deliberately permitted; self-intersections untested',
                source=str(source/'WALL'))
        (folder/'assembly.json').write_text(json.dumps(item, indent=2), encoding='utf8')
    replay_xyz = deform(reference, weights, factor, drop)
    replay_error = float(np.max(np.abs(replay_xyz-mesh.xyz)))
    receipt = dict(status='PASS', source_fixed_gate=str(source), source_existing_column_sha256=sha(column),
        source_fixed_assembly_sha256=sha(source/'WALL/geometry.npz'),
        source_control_arrays={key: array_sha(a) for key, a in source_control.items()},
        column_array_max_error=column_error, column_triangle_arrays_identical=bool(columns_faces_equal),
        operation_replay_max_error=replay_error, beam_axial_station_max_error=axial_station_error,
        section_factor=factor, common_seat_drop=drop, joint_support_halfwidth=halfwidth,
        actual_seat_sections_before=source_sections.tolist(), actual_seat_sections_after=actual_sections.tolist(),
        actual_seat_section_factors=relative_sections.tolist(),
        joint_section_vs_original_global_envelope=enlarged_vs_original_envelope.tolist(),
        required_overlap=required_overlap, actual_contact_before=before, actual_contact_after=after,
        autofit_history=history, local_geometry=local_checks, global_geometry=checks,
        contact_scope='18 actual native-triangle vertical ray sections, nine per seat. Positive overlap is measured against the topmost parity interval of the actual column head. Closed self-intersecting sources can have ambiguous physical interiors; this is finite geometric overlap evidence, not volume/structural certification.',
        excluded=['Boolean union', 'welded mesh', 'load path', 'bearing area', 'self-intersection validity', 'fabrication'])
    (root/'verification.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    (root/'SUMMARY.json').write_text(json.dumps(dict(candidate='JOINED', column_geometry_unchanged=True,
        section_factor=factor, common_drop=drop, section_factors=relative_sections.tolist(),
        passing_contact_rays={name: sum(r['passes'] for r in after if r['seat'] == name) for name in ('LEFT', 'RIGHT')},
        verification='verification.json', geometry='JOINED/geometry.npz'), indent=2), encoding='utf8')
    shutil.copyfile(__file__, root/'gate_junctions.py')
    print(json.dumps(dict(status='PASS', root=str(root), section_factor=factor, common_drop=drop,
        actual_section_factors=relative_sections.tolist(), column_error=column_error,
        passing_contact_rays={name: sum(r['passes'] for r in after if r['seat'] == name) for name in ('LEFT', 'RIGHT')},
        central_overlap={name: next(r['topmost_column_interval_overlap'] for r in after
            if r['seat'] == name and r['central']) for name in ('LEFT', 'RIGHT')}), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--column', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    generate(args.source, args.column, args.root)
