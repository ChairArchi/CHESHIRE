"""Proportion review using two unchanged copies of the actual current column.

The saved SPAN WALL G03 geometry is uniformly scaled to a 3 m bbox height and
translated, then duplicated. No column vertex is redesigned, no anisotropic
scale is used, and no primitive substitutes for the actual column. The plain
box lintel is a layout placeholder; its ornament and physical joints are out
of scope. Every candidate retains three independently indexed closed parts.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
DEFAULT_COLUMN = HERE.parents[1]/'output/fold_visible_gate_20261012/WALL/SPAN/G03/geometry.npz'
OPTIONS = (
    dict(id='A_NARROW_LOW', opening_in_widths=1.8, beam_height_in_heights=.12, overhang_in_widths=.15),
    dict(id='B_WIDE_LOW', opening_in_widths=2.6, beam_height_in_heights=.12, overhang_in_widths=.15),
    dict(id='C_NARROW_HIGH', opening_in_widths=1.8, beam_height_in_heights=.22, overhang_in_widths=.15),
    dict(id='D_WIDE_HIGH', opening_in_widths=2.6, beam_height_in_heights=.22, overhang_in_widths=.15),
    dict(id='E_WIDE_LOW_OVERHANG', opening_in_widths=2.6, beam_height_in_heights=.12, overhang_in_widths=.35),
)


def box(length, depth, height, bottom):
    """Plain outward-oriented closed triangular box in world coordinates."""
    xyz = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
    xyz *= np.array([length, depth, height])/2
    xyz[:, 2] += bottom+height/2
    quads = np.array([[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4],
        [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]], np.int64)
    triangles = np.stack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]], axis=1).reshape(-1, 3)
    return xyz, triangles


def uniform_column_transform(source_bbox, height, center_x):
    low, high = np.asarray(source_bbox)
    scale = height/(high[2]-low[2])
    centre = (low+high)/2
    transform = np.eye(4)
    transform[:3, :3] *= scale
    transform[:3, 3] = [center_x-scale*centre[0], -scale*centre[1], -scale*low[2]]
    return transform


def apply_transform(xyz, transform):
    return xyz @ transform[:3, :3].T+transform[:3, 3]


def create_layout(source_xyz, source_faces, option, *, column_height=3., seat_gap=.04):
    """Assemble fixed actual triangles with only uniform scaling/translation."""
    source_bbox = np.array([source_xyz.min(0), source_xyz.max(0)])
    size = source_bbox[1]-source_bbox[0]
    scale = column_height/size[2]
    width, depth = size[:2]*scale
    opening = option['opening_in_widths']*width
    centre_distance = opening+width
    overhang = option['overhang_in_widths']*width
    outer_column_span = opening+2*width
    beam_length = outer_column_span+2*overhang
    beam_height = option['beam_height_in_heights']*column_height
    transforms = {name: uniform_column_transform(source_bbox, column_height, x)
        for name, x in [('LEFT', -centre_distance/2), ('RIGHT', centre_distance/2)]}
    columns = {name: apply_transform(source_xyz, transform) for name, transform in transforms.items()}
    beam_xyz, beam_faces = box(beam_length, depth, beam_height, column_height+seat_gap)
    n = len(source_xyz)
    xyz = np.vstack([columns['LEFT'], columns['RIGHT'], beam_xyz])
    faces = np.vstack([source_faces, source_faces+n, beam_faces+2*n])
    face_member = np.r_[np.zeros(len(source_faces), np.int8), np.ones(len(source_faces), np.int8),
        np.full(len(beam_faces), 2, np.int8)]
    physical = trimesh.Trimesh(xyz, faces, process=False)
    # Compare stored world columns against the direct source transformation;
    # this is exact at the saved floating-point precision and retains ordering.
    forward_errors = {name: float(np.max(np.abs(columns[name]-apply_transform(source_xyz, transform))))
        for name, transform in transforms.items()}
    inverse_errors = {name: float(np.max(np.abs(
        (columns[name]-transform[:3, 3])/scale-source_xyz)))
        for name, transform in transforms.items()}
    difference = columns['RIGHT']-columns['LEFT']
    duplication_error = float(np.max(np.abs(difference-[centre_distance, 0., 0.])))
    left_bbox = np.array([columns['LEFT'].min(0), columns['LEFT'].max(0)])
    right_bbox = np.array([columns['RIGHT'].min(0), columns['RIGHT'].max(0)])
    bbox_opening = float(right_bbox[0, 0]-left_bbox[1, 0])
    bbox_seat_gap = float(beam_xyz[:, 2].min()-max(left_bbox[1, 2], right_bbox[1, 2]))
    checks = dict(finite=bool(np.isfinite(xyz).all()), components=int(physical.body_count),
        watertight=bool(physical.is_watertight), winding_consistent=bool(physical.is_winding_consistent),
        minimum_triangle_area=float(physical.area_faces.min()),
        source_triangle_arrays_identical=bool(np.array_equal(faces[:len(source_faces)], source_faces) and
            np.array_equal(faces[len(source_faces):2*len(source_faces)]-n, source_faces)),
        direct_source_transform_max_errors=forward_errors,
        inverse_uniform_transform_max_errors=inverse_errors,
        duplicate_translation_max_error=duplication_error,
        column_linear_transforms_are_uniform=bool(all(np.array_equal(m[:3, :3], np.eye(3)*scale)
            for m in transforms.values())),
        bbox_opening_width=bbox_opening, bbox_vertical_seat_gap=bbox_seat_gap)
    passed = bool(checks['finite'] and checks['components'] == 3 and checks['watertight'] and
        checks['winding_consistent'] and checks['minimum_triangle_area'] > 1e-12 and
        checks['source_triangle_arrays_identical'] and checks['column_linear_transforms_are_uniform'] and
        max(forward_errors.values()) == 0. and max(inverse_errors.values()) < 1e-12 and
        duplication_error < 1e-12 and abs(bbox_opening-opening) < 1e-12 and
        abs(bbox_seat_gap-seat_gap) < 1e-12)
    metadata = dict(candidate=option['id'], scope='Actual unchanged current column duplication and plain lintel proportion review',
        units='metres', coefficients=dict(option), column_display_height=column_height,
        column_uniform_scale=scale, actual_scaled_column_width=float(width), actual_scaled_column_depth=float(depth),
        opening_width=float(opening), column_center_distance=float(centre_distance),
        outer_column_span=float(outer_column_span), lintel_length=float(beam_length),
        lintel_height=float(beam_height), lintel_depth=float(depth), overhang_each_side=float(overhang),
        nominal_seat_gap=seat_gap, world_bbox=[xyz.min(0).tolist(), xyz.max(0).tolist()],
        source_bbox=source_bbox.tolist(), column_transforms={key: value.tolist() for key, value in transforms.items()},
        source_column_vertices=n, source_column_triangles=len(source_faces),
        part_names=['LEFT', 'RIGHT', 'LINTEL'],
        part_vertex_ranges=dict(LEFT=[0, n], RIGHT=[n, 2*n], LINTEL=[2*n, 2*n+8]),
        columns='Exact source XYZ under saved common uniform scale and translations; no deformation or anisotropic scaling',
        lintel='New plain rectangular box placeholder only; no ornament operator applied',
        seating='Bounding-box grounding and vertical gap only; actual column end caps remain unchanged and are not certified flat bearing faces',
        self_intersection='NOT_CHECKED; source geometry preserved', structural_connections='NOT_IMPLEMENTED',
        fabrication='NOT_CHECKED', checks=checks, quick_integrity='PASS' if passed else 'FAILED_PRESERVED')
    return dict(xyz=xyz, faces=faces, face_member=face_member, metadata=metadata)


def generate(root, column=DEFAULT_COLUMN, *, export_obj=False):
    root, column = Path(root).resolve(), Path(column).resolve()
    if root.exists():
        raise FileExistsError('Existing layout review preserved: '+str(root))
    with np.load(column, allow_pickle=False) as data:
        source_xyz, source_faces = data['xyz'].copy(), data['faces'].copy()
    if source_xyz.ndim != 2 or source_xyz.shape[1] != 3 or not np.isfinite(source_xyz).all():
        raise ValueError('Finite actual source XYZ required.')
    if source_faces.ndim != 2 or source_faces.shape[1] != 3 or not np.issubdtype(source_faces.dtype, np.integer):
        raise ValueError('Actual explicit integer source triangles required.')
    if source_faces.min() < 0 or source_faces.max() >= len(source_xyz) or np.ptp(source_xyz[:, 2]) <= 0:
        raise ValueError('Valid source indices and positive column height required.')
    source_hash = hashlib.sha256(column.read_bytes()).hexdigest()
    records = []
    for option in OPTIONS:
        result = create_layout(source_xyz, source_faces, option)
        folder = root/option['id']; folder.mkdir(parents=True)
        np.savez_compressed(folder/'geometry.npz', xyz=result['xyz'], faces=result['faces'],
            face_member=result['face_member'])
        metadata = dict(result['metadata'], source_column=str(column), source_geometry_sha256=source_hash)
        (folder/'assembly.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
        if export_obj:
            trimesh.Trimesh(result['xyz'], result['faces'], process=False).export(folder/'gate.obj')
        records.append(dict(candidate=option['id'], path=str(folder),
            opening_width=metadata['opening_width'], lintel_height=metadata['lintel_height'],
            lintel_length=metadata['lintel_length'], overhang_each_side=metadata['overhang_each_side'],
            actual_scaled_column_width=metadata['actual_scaled_column_width'],
            coefficients=metadata['coefficients'], quick_integrity=metadata['quick_integrity']))
        print(option['id'], metadata['quick_integrity'], 'opening', round(metadata['opening_width'], 4),
            'beam_height', round(metadata['lintel_height'], 4), 'beam_length', round(metadata['lintel_length'], 4), flush=True)
        if metadata['quick_integrity'] != 'PASS':
            raise ValueError('Layout quick-check failure preserved: '+str(folder))
    summary = dict(scope='Five proportion alternatives; identical actual columns under one uniform display scale',
        source_column=str(column), source_geometry_sha256=source_hash,
        source_column_vertices=len(source_xyz), source_column_triangles=len(source_faces),
        column_display_height=3., nominal_seat_gap=.04, options=records,
        controlled_comparisons=dict(opening=['A_NARROW_LOW versus B_WIDE_LOW', 'C_NARROW_HIGH versus D_WIDE_HIGH'],
            lintel_height=['A_NARROW_LOW versus C_NARROW_HIGH', 'B_WIDE_LOW versus D_WIDE_HIGH'],
            overhang='B_WIDE_LOW versus E_WIDE_LOW_OVERHANG'),
        no_column_optimization=True, lintel_ornament_applied=False,
        seating_and_structural_connections='NOT_VALIDATED')
    (root/'SUMMARY.json').write_text(json.dumps(summary, indent=2), encoding='utf8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--column', type=Path, default=DEFAULT_COLUMN)
    parser.add_argument('--obj', action='store_true', help='Also export each actual layout as gate.obj')
    args = parser.parse_args()
    generate(args.root, args.column, export_obj=args.obj)
