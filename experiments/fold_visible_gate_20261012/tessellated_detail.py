"""One finite branched-component preview on the unchanged actual WALL column.

This tests three-dimensional motifs against scalar surface-height relief. It
uses no Tissue installation, recovered IAAC code, random displacement, mesh
smoothing, or boolean union. Deterministically varied closed branch pieces
overlap one another and the exact source surface. Their real gaps and returning
branches are geometry, but attachment, intersection and fabrication are not
validated. Only this one preview state is generated.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import study

DEFAULT_SOURCE = HERE.parents[1]/'output/fold_visible_gate_20261012/WALL/SPAN/G03'
RECIPE = dict(name='actual_surface_branched_components_v1',
    canonical_colonies=72, constructive_quadrant_copies=4,
    primary_branches=[3, 5], branchlets_per_primary=2,
    primary_branch_circle_diameter=[.24, .38], complete_footprint_maximum=.40,
    normal_protrusion_maximum=.25,
    primary_tube_radius=[.014, .024], secondary_tube_radius=[.007, .011],
    anchor_spacing_minimum=.155, source_geometry='Unchanged actual WALL/SPAN/G03 native triangles',
    placement='Low-discrepancy material candidates; actual native triangle points and pooled local frames',
    symmetry='Constructive XY copies of complete canonical colony meshes; reverse winding for odd reflection',
    operation='Closed overlapping branch components only; no source vertex moved or removed',
    purpose='Finite comparison of actual volumetric detail against Mandelbulb height relief; not a general component engine')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def h01(index, key=0):
    """Stable integer mixing for motif variation, never for vertex noise."""
    v = (int(index)+1)*0x9e3779b1 ^ (int(key)+1)*0x85ebca77
    v &= 0xffffffff
    v ^= v >> 16
    v = (v*0x7feb352d) & 0xffffffff
    v ^= v >> 15
    return v/4294967296.


def unit(vector):
    return np.asarray(vector, float)/np.linalg.norm(vector)


def closed_tube(points, radii, sectors=8, phase=0.):
    """Faceted closed swept tube, capped at both ends; no rendered curves."""
    points, radii = np.asarray(points, float), np.asarray(radii, float)
    tangent = np.gradient(points, axis=0)
    theta = phase+np.arange(sectors)*2*np.pi/sectors
    rings = []
    for p, t, r in zip(points, tangent, radii):
        t = unit(t)
        guide = np.array([0., 0., 1.]) if abs(t[2]) < .85 else np.array([1., 0., 0.])
        a = unit(np.cross(t, guide)); b = np.cross(t, a)
        rings.append(p+r*(np.cos(theta)[:, None]*a+np.sin(theta)[:, None]*b))
    xyz = np.vstack([*rings, points[0], points[-1]])
    ids = np.arange(len(points)*sectors).reshape(len(points), sectors)
    faces = []
    for k in range(len(points)-1):
        for j in range(sectors):
            a, b = ids[k, j], ids[k, (j+1) % sectors]
            c, d = ids[k+1, (j+1) % sectors], ids[k+1, j]
            faces.extend([[a, b, c], [a, c, d]])
    cap0, cap1 = len(xyz)-2, len(xyz)-1
    for j in range(sectors):
        faces.extend([[cap0, ids[0, (j+1) % sectors], ids[0, j]],
            [cap1, ids[-1, j], ids[-1, (j+1) % sectors]]])
    faces = np.asarray(faces, np.int64)
    actual = trimesh.Trimesh(xyz, faces, process=False)
    if actual.volume < 0:
        faces = faces[:, [0, 2, 1]]
    return xyz, faces


def lobed_knob(centre, radius, phase, *, sectors=10, rings=5):
    """Closed anisotropic radial bud with an intentionally faceted silhouette."""
    angle = np.arange(sectors)*2*np.pi/sectors
    polar = np.linspace(np.pi/(rings+1), np.pi*rings/(rings+1), rings)
    xyz = []
    for a in polar:
        lobes = 1.+.17*np.cos(5*angle+phase)*np.sin(a)**2
        xyz.extend(np.column_stack([radius*lobes*np.sin(a)*np.cos(angle),
            radius*lobes*np.sin(a)*np.sin(angle),
            np.full(sectors, .78*radius*np.cos(a))]))
    xyz = np.vstack([xyz, [0, 0, .78*radius], [0, 0, -.78*radius]])+centre
    ids = np.arange(rings*sectors).reshape(rings, sectors)
    faces = []
    for k in range(rings-1):
        for j in range(sectors):
            a, b = ids[k, j], ids[k, (j+1) % sectors]
            c, d = ids[k+1, (j+1) % sectors], ids[k+1, j]
            faces.extend([[a, c, b], [a, d, c]])
    north, south = len(xyz)-2, len(xyz)-1
    for j in range(sectors):
        faces.extend([[north, ids[0, j], ids[0, (j+1) % sectors]],
            [south, ids[-1, (j+1) % sectors], ids[-1, j]]])
    faces = np.asarray(faces, np.int64)
    if trimesh.Trimesh(xyz, faces, process=False).volume < 0:
        faces = faces[:, [0, 2, 1]]
    return xyz, faces


def motif(index):
    """Related primary arches and secondary returning branchlets in local XYZ.

    Local Z is the pooled outward surface normal. All dimensions refer to the
    original saved column units. Variation changes whole branches and buds;
    there is no independent high-frequency perturbation of mesh vertices.
    """
    diameter = .24+.14*h01(index, 1)
    radius = diameter/2
    height = .14+.065*h01(index, 2)
    count = 3+int(3*h01(index, 3))
    phase = 2*np.pi*h01(index, 4)
    pieces = []
    stem = np.array([[0, 0, -.038], [0, 0, .015], [0, 0, .055], [0, 0, .085]])
    pieces.append(closed_tube(stem, [.030, .033, .024, .017], sectors=10, phase=phase))
    for branch in range(count):
        angle = phase+2*np.pi*branch/count+.22*(h01(index, 10+branch)-.5)
        curl = (.22+.42*h01(index, 20+branch))*(-1 if branch % 2 else 1)
        t = np.linspace(0., 1., 7)
        reach = radius*(.78+.18*h01(index, 30+branch))
        r = reach*np.sin(t*np.pi*.6)
        a = angle+curl*t*t
        z = .036+(height-.036)*np.sin(t*np.pi*.72)
        # Return the tip toward the surface to create a real open underside.
        z -= (.025+.035*h01(index, 40+branch))*t**3
        points = np.column_stack([r*np.cos(a), r*np.sin(a), z])
        tube_radius = .014+.010*h01(index, 50+branch)
        pieces.append(closed_tube(points, np.linspace(tube_radius, .65*tube_radius, len(t)),
            sectors=8, phase=angle))
        knob_radius = .029+.017*h01(index, 60+branch)
        pieces.append(lobed_knob(points[-1], knob_radius, phase+branch))
        for child in range(2):
            start = points[3+child]
            child_angle = a[3+child]+(-1 if child == 0 else 1)*(.85+.35*h01(index, 70+branch*2+child))
            length = .048+.026*h01(index, 90+branch*2+child)
            offset = np.array([np.cos(child_angle), np.sin(child_angle), .45])*length
            child_points = np.array([start, start+.4*offset+[0, 0, .012],
                start+.8*offset+[0, 0, .008], start+offset-[0, 0, .010]])
            small_radius = .007+.004*h01(index, 110+branch*2+child)
            pieces.append(closed_tube(child_points, [small_radius, small_radius, .8*small_radius, .6*small_radius],
                sectors=6, phase=child_angle))
            pieces.append(lobed_knob(child_points[-1], .013+.008*h01(index, 130+branch*2+child),
                phase+child, sectors=8, rings=4))
    xyz, faces, piece_id, cursor = [], [], [], 0
    for part, (p, f) in enumerate(pieces):
        xyz.append(p); faces.append(f+cursor)
        piece_id.append(np.full(len(f), part, np.int16)); cursor += len(p)
    xyz, faces = np.vstack(xyz), np.vstack(faces)
    # One whole-motif scale bounds its footprint and protrusion without
    # changing individual vertices independently or touching source geometry.
    footprint = np.ptp(xyz[:, :2], axis=0).max()
    normal_max = xyz[:, 2].max()
    scale = min(1., .40/footprint, RECIPE['normal_protrusion_maximum']/normal_max)
    xyz *= scale
    return xyz, faces, np.concatenate(piece_id), dict(primary_branches=count,
        closed_component_pieces=len(pieces), motif_uniform_scale=float(scale),
        local_normal_minimum=float(xyz[:, 2].min()), local_normal_maximum=float(xyz[:, 2].max()),
        local_footprint=np.ptp(xyz[:, :2], axis=0).tolist())


def anchors(mesh, chart, count):
    """Select actual surface points with finite native-triangle provenance."""
    native = study.previous.anchor.t.growth.native(mesh)
    physical_chart = np.concatenate([chart, study.previous.anchor.t.face_values(mesh, chart)])
    sampler = study.NativeChartSampler(native.xyz, native.faces[:, :3], physical_chart)
    records = []
    for band, (u0, u1) in enumerate(((.61, .83), (.40, .62))):
        candidates = np.arange(2800)
        u = u0+(u1-u0)*np.mod((candidates+1)*.6180339887498949+.173*band, 1.)
        angle = .10+1.37*np.mod((candidates+1)*.7548776662466927+.317*band, 1.)
        uv = np.column_stack([u, angle])
        xyz, ids, bary = sampler.sample(uv, records=True)
        # Pool directions from actual points over a finite patch, not the
        # high-frequency normals of individual fan triangles.
        tangent = sampler.sample(uv+[.008, 0])-sampler.sample(uv-[.008, 0])
        across = sampler.sample(uv+[0, .045])-sampler.sample(uv-[0, .045])
        raw_normals = np.cross(native.xyz[native.faces[ids, 1]]-native.xyz[native.faces[ids, 0]],
            native.xyz[native.faces[ids, 2]]-native.xyz[native.faces[ids, 0]])
        per_band = []
        for index in range(len(uv)):
            t = unit(tangent[index]); a = across[index]-np.dot(across[index], t)*t
            if np.linalg.norm(a) < 1e-10:
                continue
            n = unit(np.cross(t, a))
            if np.dot(n, raw_normals[index]) < 0:
                n *= -1
            a = unit(np.cross(n, t))
            radial = np.r_[xyz[index, :2], 0.]
            if np.dot(n, radial)/np.linalg.norm(radial) < .25:
                continue
            if records and np.min(np.linalg.norm(np.array([r['xyz'] for r in records])-xyz[index], axis=1)) < RECIPE['anchor_spacing_minimum']:
                continue
            frame = np.column_stack([t, a, n])
            record = dict(xyz=xyz[index], uv=uv[index], triangle_id=ids[index], barycentric=bary[index],
                frame=frame, raw_native_face_normal=unit(raw_normals[index]), band=band,
                candidate_index=int(index))
            records.append(record); per_band.append(record)
            if len(per_band) == count//2:
                break
        if len(per_band) != count//2:
            raise ValueError('Too few separated actual exposed surface anchors for finite preview.')
    return records, native


def generate(root, source=DEFAULT_SOURCE):
    root, source = Path(root).resolve(), Path(source).resolve()
    if root.exists():
        raise FileExistsError('Existing component preview preserved: '+str(root))
    mesh, chart, _ = study.previous.anchor.t.load(source)
    records, native = anchors(mesh, chart, RECIPE['canonical_colonies'])
    source_faces = native.faces[:, :3]
    with np.load(source/'geometry.npz', allow_pickle=False) as saved:
        if not np.array_equal(saved['xyz'], native.xyz) or not np.array_equal(saved['faces'], source_faces):
            raise ValueError('Source native reconstruction differs from the actual saved WALL geometry.')
    xyz_parts, face_parts = [native.xyz.copy()], [source_faces.copy()]
    vertex_colony, face_colony = [np.full(len(native.xyz), -1, np.int16)], [np.full(len(source_faces), -1, np.int16)]
    face_piece = [np.full(len(source_faces), -1, np.int16)]
    notes = []; cursor = len(native.xyz); colony = 0
    transforms = [np.diag(sign) for sign in ([1., 1., 1.], [-1., 1., 1.], [1., -1., 1.], [-1., -1., 1.])]
    for index, record in enumerate(records):
        local_xyz, local_faces, pieces, note = motif(index)
        canonical = local_xyz@record['frame'].T+record['xyz']
        for transform in transforms:
            p = canonical@transform.T
            f = local_faces if np.linalg.det(transform) > 0 else local_faces[:, [0, 2, 1]]
            xyz_parts.append(p); face_parts.append(f+cursor)
            vertex_colony.append(np.full(len(p), colony, np.int16))
            face_colony.append(np.full(len(f), colony, np.int16)); face_piece.append(pieces)
            notes.append(dict(colony=colony, canonical_motif=index, band=int(record['band']),
                reflected_axes=np.diag(transform).tolist(), **note))
            cursor += len(p); colony += 1
    xyz, faces = np.vstack(xyz_parts), np.vstack(face_parts)
    actual = trimesh.Trimesh(xyz, faces, process=False)
    source_xyz_error = float(np.max(np.abs(xyz[:len(native.xyz)]-native.xyz)))
    source_faces_equal = bool(np.array_equal(faces[:len(source_faces)], source_faces))
    # Check identical template regeneration independently of output composition.
    deterministic = all(np.array_equal(motif(i)[0], motif(i)[0]) for i in (0, 17, 53))
    reconstruction_error = []
    for r in records:
        reconstructed = np.asarray(r['barycentric'])@native.xyz[source_faces[r['triangle_id']]]
        reconstruction_error.append(np.linalg.norm(reconstructed-r['xyz']))
    checks = dict(finite=bool(np.isfinite(xyz).all()), watertight=bool(actual.is_watertight),
        winding_consistent=bool(actual.is_winding_consistent), minimum_triangle_area=float(actual.area_faces.min()),
        source_xyz_max_error=source_xyz_error, source_triangle_arrays_identical=source_faces_equal,
        anchor_barycentric_reconstruction_max_error=float(max(reconstruction_error)),
        all_colony_protrusions_within_declared_bound=bool(max(n['local_normal_maximum'] for n in notes) <= .25+1e-12),
        maximum_colony_normal_protrusion=float(max(n['local_normal_maximum'] for n in notes)),
        minimum_colony_embedding=float(min(n['local_normal_minimum'] for n in notes)),
        template_regeneration_deterministic=deterministic,
        source_and_detail_are_separate_closed_overlapping_components=True)
    passed = bool(checks['finite'] and checks['watertight'] and checks['winding_consistent'] and
        checks['minimum_triangle_area'] > 1e-12 and checks['source_xyz_max_error'] == 0. and
        checks['source_triangle_arrays_identical'] and checks['anchor_barycentric_reconstruction_max_error'] < 1e-12 and
        checks['all_colony_protrusions_within_declared_bound'] and deterministic)
    root.mkdir(parents=True)
    np.savez_compressed(root/'geometry.npz', xyz=xyz, faces=faces,
        vertex_colony=np.concatenate(vertex_colony), face_colony=np.concatenate(face_colony),
        face_piece=np.concatenate(face_piece))
    np.savez_compressed(root/'placement.npz', anchor_xyz=np.array([r['xyz'] for r in records]),
        anchor_uv=np.array([r['uv'] for r in records]), source_triangle_ids=np.array([r['triangle_id'] for r in records]),
        source_barycentric=np.array([r['barycentric'] for r in records]),
        pooled_local_frames=np.array([r['frame'] for r in records]),
        raw_native_face_normals=np.array([r['raw_native_face_normal'] for r in records]),
        band=np.array([r['band'] for r in records]), candidate_index=np.array([r['candidate_index'] for r in records]),
        quadrant_transforms=np.array(transforms))
    metadata = dict(candidate='BRANCHED_COMPONENT_PREVIEW', source=str(source),
        source_geometry_sha256=digest(source/'geometry.npz'), source_control_sha256=digest(source/'control_quad.npz'),
        recipe=RECIPE, canonical_anchors=len(records), complete_colonies=colony,
        closed_detail_pieces=sum(n['closed_component_pieces'] for n in notes),
        source_vertices=len(native.xyz), source_triangles=len(source_faces),
        complete_vertices=len(xyz), complete_triangles=len(faces), checks=checks,
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED',
        limitations=['No Tissue addon used', 'Authored volumetric branch motifs, not an emergent fractal boundary',
            'Closed overlapping parts; no boolean union, physical attachment or intersection check',
            'Normal protrusion is relative to each saved pooled anchor frame, not a global signed-distance bound',
            'Only SPAN finite preview; no generalization or aesthetic success claim'],
        colony_notes=notes)
    (root/'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    print(json.dumps({k:metadata[k] for k in ('candidate','quick_integrity','canonical_anchors',
        'complete_colonies','closed_detail_pieces','complete_vertices','complete_triangles','checks')}, indent=2), flush=True)
    if not passed:
        raise ValueError('Component preview failed; actual evidence preserved.')
    return metadata


def cycles(triangles):
    """Canonical oriented triangle rows, preserving winding under comparison."""
    first = np.argmin(triangles, axis=1)
    rows = triangles[np.arange(len(triangles))[:, None], (first[:, None]+np.arange(3)) % 3]
    return rows[np.lexsort((rows[:, 2], rows[:, 1], rows[:, 0]))]


def verify(root, source=DEFAULT_SOURCE):
    """Rebuild every saved motif and use explicit reflective correspondence.

    Repeated cap-centre coordinates in overlapping pieces make nearest-point
    pairing ambiguous. The construction's known component correspondence
    checks actual oriented triangles without merging those separate vertices.
    """
    root, source = Path(root).resolve(), Path(source).resolve()
    with np.load(root/'geometry.npz', allow_pickle=False) as data:
        xyz, faces = data['xyz'], data['faces']
    with np.load(root/'placement.npz', allow_pickle=False) as data:
        saved_placement = {key:data[key] for key in data.files}
    mesh, chart, _ = study.previous.anchor.t.load(source)
    records, native = anchors(mesh, chart, RECIPE['canonical_colonies'])
    physical_chart = np.concatenate([chart, study.previous.anchor.t.face_values(mesh, chart)])
    base_pairs = study.previous.anchor.t.prior.helpers.existing.symmetry(physical_chart)
    pair_maps = [np.empty(len(xyz), np.int64), np.empty(len(xyz), np.int64)]
    for axis in (0, 1):
        pair_maps[axis][:len(native.xyz)] = base_pairs[axis]
    assert np.array_equal(xyz[:len(native.xyz)], native.xyz)
    assert np.array_equal(faces[:len(native.faces)], native.faces[:, :3])
    placement_error = max(float(np.max(np.abs(saved_placement[key]-value))) for key,value in
        dict(anchor_xyz=np.array([r['xyz'] for r in records]),
            anchor_uv=np.array([r['uv'] for r in records]),
            pooled_local_frames=np.array([r['frame'] for r in records])).items())
    assert placement_error == 0.
    cursor, face_cursor = len(native.xyz), len(native.faces)
    replay_error = 0.
    faces_equal = True
    for index, record in enumerate(records):
        local_xyz, local_faces, _, _ = motif(index)
        count, nfaces = len(local_xyz), len(local_faces)
        canonical = local_xyz@record['frame'].T+record['xyz']
        for quarter, transform in enumerate(saved_placement['quadrant_transforms']):
            expected_xyz = canonical@transform.T
            expected_faces = local_faces if np.linalg.det(transform) > 0 else local_faces[:, [0, 2, 1]]
            replay_error = max(replay_error, float(np.max(np.abs(xyz[cursor:cursor+count]-expected_xyz))))
            faces_equal &= np.array_equal(faces[face_cursor:face_cursor+nfaces]-cursor, expected_faces)
            # Quarter order is ++, -+, +-, --. Bit0 changes X and bit1 Y.
            motif_start = cursor-quarter*count
            for axis in (0, 1):
                partner = quarter ^ (1 << axis)
                pair_maps[axis][cursor:cursor+count] = motif_start+partner*count+np.arange(count)
            cursor += count; face_cursor += nfaces
    assert cursor == len(xyz) and face_cursor == len(faces)
    assert replay_error == 0. and faces_equal
    original_cycles = cycles(faces)
    reflections = []
    for axis, ids in enumerate(pair_maps):
        sign = np.ones(3); sign[axis] = -1
        point_error = float(np.max(np.abs(xyz-xyz[ids]*sign)))
        involutive = bool(np.array_equal(ids[ids], np.arange(len(ids))))
        face_match = bool(np.array_equal(original_cycles, cycles(ids[faces][:, [0, 2, 1]])))
        assert point_error < 1e-12 and involutive and face_match
        reflections.append(dict(axis=axis, maximum_xyz_error=point_error,
            explicit_pair_map_involutive=involutive, oriented_triangle_sets_identical=face_match))
    result = dict(status='PASS', scope='Regenerated actual anchors and every complete motif; exact source prefix and oriented X/Y construction reflection',
        full_detail_xyz_replay_max_error=replay_error, full_detail_triangle_arrays_identical=bool(faces_equal),
        anchor_and_pooled_frame_regeneration_max_error=placement_error, reflections=reflections,
        excluded=['Intersections', 'Boolean union', 'Physical attachment', 'Aesthetic success'])
    (root/'verification.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    p.add_argument('--verify', action='store_true', help='Replay an existing preview; write verification.json only')
    args = p.parse_args()
    if args.verify:
        verify(args.root, args.source)
    else:
        generate(args.root, args.source)
