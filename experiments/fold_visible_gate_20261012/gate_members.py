"""Portable, explicitly authored three-member gate pilot, in metres.

Each member starts as its own closed rectangular ring prism. Two real inactive
Task36 refinements and two declared PCHIP macro returns prepare a G2 input; no
finished historical column, field cache, or hidden fractal pass is imported.
The subsequent measured wall operator is deliberately outside this module.

``build_source(kind)`` returns (G2 ArrayMesh, material chart, scalar tags, JSON
metadata). ``write_source(root, kind)`` saves actual G0/G1/G2 and returns its G2
folder. ``assemble(parts)`` accepts local (xyz, triangles) tuples or mappings
with those keys, keyed LEFT/RIGHT/LINTEL, or shared COLUMN plus LINTEL. It returns
a dictionary containing XYZ, triangles, integer face_parts, and JSON metadata.
The assembly keeps the three index ranges separate and never welds parts.
"""
from pathlib import Path
import copy
import importlib.util
import json
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
from cheshire import task36_growth
from cheshire.reference_subdivision import ArrayMesh, topology

_spec = importlib.util.spec_from_file_location('gate_pilot_existing_memory',
    HERE.parent / 'fold_transfer_20261012/memory.py')
_memory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_memory)

PARENTS = [
    dict(id='LOWER_DIAGONAL_RETURN', direction=.35, height=.39, span=.12,
         expansion=.48, constriction=.28, reexpansion=.38, return_depth=.72,
         overlap_width=.46, sweep=.28, mirror=False),
    dict(id='UPPER_CROSSING_RETURN', direction=1.18, height=.61, span=.12,
         expansion=.46, constriction=.26, reexpansion=.36, return_depth=.68,
         overlap_width=.46, sweep=.28, mirror=False),
]
DIMENSIONS = dict(COLUMN=dict(half_x=.45, half_y=.25, length=2.6),
                  LINTEL=dict(half_x=.45, half_y=.25, length=4.0))
KNOTS = np.array([-2.2, -1.4, -.75, -.35, -.15, .15, .35, .75, 1.3, 2.])


def build_carrier(kind='COLUMN', *, rings=20, sectors=24):
    """New rectangular G0 with the established (s, cos theta, sin theta) chart."""
    if kind not in DIMENSIONS:
        raise ValueError('Choose COLUMN or LINTEL.')
    if type(rings) is not int or rings < 3 or type(sectors) is not int or sectors < 8 or sectors % 8:
        raise ValueError('At least three rings and a sector count divisible by eight required to sample every rectangular corner.')
    d = DIMENSIONS[kind]
    theta = np.arange(sectors) * 2*np.pi/sectors
    c, s = np.cos(theta), np.sin(theta)
    c[np.abs(c) < 1e-14] = 0.; s[np.abs(s) < 1e-14] = 0.
    divisor = np.maximum(np.abs(c), np.abs(s))
    longitudinal = np.linspace(0., 1., rings)
    xyz = np.stack(np.broadcast_arrays(d['half_x']*c[None, :]/divisor,
        d['half_y']*s[None, :]/divisor, d['length']*longitudinal[:, None]), -1).reshape(-1, 3)
    chart = np.stack(np.broadcast_arrays(longitudinal[:, None], c[None, :], s[None, :]), -1).reshape(-1, 3)
    ids = np.arange(rings*sectors).reshape(rings, sectors)
    side = np.stack([ids[:-1], np.roll(ids[:-1], -1, 1),
        np.roll(ids[1:], -1, 1), ids[1:]], -1).reshape(-1, 4)
    bottom, top = len(xyz), len(xyz)+1
    caps = [[bottom, ids[0, (j+2) % sectors], ids[0, j+1], ids[0, j]]
        for j in range(0, sectors, 2)]
    caps += [[top, ids[-1, j], ids[-1, j+1], ids[-1, (j+2) % sectors]]
        for j in range(0, sectors, 2)]
    xyz = np.vstack([xyz, [0, 0, 0], [0, 0, d['length']]])
    chart = np.vstack([chart, [0, 0, 0], [1, 0, 0]])
    faces = np.vstack([side, caps]).astype(np.int64)
    mesh = ArrayMesh(xyz, faces, np.full(len(xyz), -1, np.int8), xyz.copy(),
        np.full((len(faces), 3), -1, np.int64), 0)
    mesh.surface = 'mean'
    topology(mesh)
    return mesh, chart


def macro_displacement(chart, event, kind):
    """Same legacy PCHIP profile coefficients, now in declared member scales.

    This is explicit authored seeding, based on smooth_deep.smooth_event, not
    emergent discovery. Radial components use each physical half-section;
    axial return uses the smaller half-section, independently of member length.
    """
    d = DIMENSIONS[kind]
    c = np.asarray(chart, float).copy(); c[:, 1:] = np.abs(c[:, 1:])
    s = c[:, 0]; theta = np.arctan2(c[:, 2], c[:, 1])
    centre = event['direction'] + event['sweep']*np.sin(np.pi*(s-event['height'])/.32)
    angle = np.arctan2(np.sin(theta-centre), np.cos(theta-centre))
    q = np.clip(np.abs(angle)/event['overlap_width'], 0., 1.)
    rounded = (np.sqrt(q*q+.12**2)-.12)/(np.sqrt(1+.12**2)-.12)
    wave = 1.-1.5*rounded+.5*rounded**3
    local_h = event['height'] + .05*q**1.4
    u = (s-local_h)/event['span']
    e, constriction, r = [event[key] for key in ('expansion', 'constriction', 'reexpansion')]
    radial_values = [0, .1*e, .62*e, e, .3*e, -constriction, -.35*constriction, r, .4*r, 0]
    axial_values = event['return_depth']*np.array([0, 0, .2, 1, .6, -.6, -1, -.2, 0, 0])
    radial = np.nan_to_num(PchipInterpolator(KNOTS, radial_values, extrapolate=False)(u))*wave
    axial = np.nan_to_num(PchipInterpolator(KNOTS, axial_values, extrapolate=False)(u))*wave
    # Declared smooth endpoint window; the two cap planes stay unchanged.
    a = np.clip((np.abs(s-.5)-.40)/.09, 0., 1.)
    end_window = 1.-a*a*(3.-2.*a)
    delta = np.column_stack([d['half_x']*radial*np.cos(theta),
        d['half_y']*radial*np.sin(theta), min(d['half_x'], d['half_y'])*axial])
    delta *= end_window[:, None]
    delta[:, :2] *= np.where(chart[:, 1:] < 0., -1., 1.)
    delta[np.abs(chart[:, 1]) < 1e-12, 0] = 0.
    delta[np.abs(chart[:, 2]) < 1e-12, 1] = 0.
    delta[np.linalg.norm(chart[:, 1:], axis=1) < 1e-10] = 0.
    return delta


def axial_correspondence(chart):
    """Exact discrete material reflection s -> 1-s; no world-space nearest fit."""
    reflected = np.asarray(chart, float).copy(); reflected[:, 0] = 1.-reflected[:, 0]
    distance, ids = cKDTree(chart).query(reflected)
    if distance.max() > 1e-10 or not np.array_equal(ids[ids], np.arange(len(ids))):
        raise ValueError('Material chart lacks an exact axial reflection correspondence.')
    return ids


def reflect_lintel(values, chart, *, positions=False):
    """Constructively copy the local first half onto the second beam half.

    Use this on later lintel displacement fields too, before world assembly,
    to retain gate left-right symmetry. It does not average paired coordinates.
    """
    values = np.asarray(values)
    if values.shape != np.asarray(chart).shape:
        raise ValueError('One local XYZ triple per material control required.')
    ids = axial_correspondence(chart)
    second = chart[:, 0] > .5+1e-12
    values[second] = values[ids[second]] * np.array([1., 1., -1.])
    if positions:
        values[second, 2] += DIMENSIONS['LINTEL']['length']
    centre = np.abs(chart[:, 0]-.5) <= 1e-12
    values[centre, 2] = DIMENSIONS['LINTEL']['length']/2 if positions else 0.
    return values


def reflect_axial_delta(delta, chart):
    """Root runner adapter for the lintel's declared axial role constraint."""
    return reflect_lintel(delta, chart, positions=False)


def _stages(kind):
    mesh, chart = build_carrier(kind)
    tags = np.zeros(len(chart))
    yield mesh, chart, tags, dict(stage='G00', operation='New rectangular ring prism', authored_event=None)
    for index, event in enumerate(PARENTS, 1):
        mesh, chart, tags, _ = _memory.refine(mesh, chart, tags)
        mesh.xyz += macro_displacement(chart, event, kind)
        if kind == 'LINTEL':
            reflect_lintel(mesh.xyz, chart, positions=True)
        tags = np.maximum(tags, _memory.feature_mask(chart, [event]))
        if kind == 'LINTEL':
            ids = axial_correspondence(chart)
            tags[chart[:, 0] > .5+1e-12] = tags[ids[chart[:, 0] > .5+1e-12]]
        yield mesh, chart, tags, dict(stage=f'G{index:02}',
            operation='Existing inactive Task36 refinement then one authored PCHIP macro return', authored_event=event['id'])


def _metadata(kind, history):
    return dict(candidate='NEW_SEPARATE_'+kind+'_PILOT', member_kind=kind, units='metres',
        source_identity='New authored member-local rectangular carrier; not a transformed finished historical column',
        nominal_dimensions_local=dict(DIMENSIONS[kind]),
        material_chart='s along member local Z; cos(theta), sin(theta) around rectangular section',
        local_generation=2, source_generation=2,
        parent_region_seeds=copy.deepcopy(PARENTS), event_bank=copy.deepcopy(PARENTS),
        macro_seed_provenance='Same two declared coefficients as directional_growth_20261012/overlap_probe.py; PCHIP expression reused in normalized member cross-section units',
        macro_scaling=dict(radial='local half_x / half_y', axial='min(local half_x,local half_y)'),
        generation_history=history, field_passes_inherited=0, field_passes_total=0,
        added_field_passes=0, source_endpoint_planes='Planar untouched G0 caps; no structural joint validation',
        lintel_axial_reflection=(kind == 'LINTEL'),
        lintel_reflection_method='Exact material s->1-s correspondence; copy first half, reverse local Z, no averaging',
        self_intersection='NOT_CHECKED_EXPLORATION', fabrication='NOT_CHECKED')


def build_source(kind='COLUMN'):
    history = []
    for mesh, chart, tags, stage in _stages(kind):
        history.append(dict(stage, control_vertices=len(mesh.xyz), control_quads=len(mesh.faces)))
    return mesh, chart, tags, _metadata(kind, history)


def write_source(root, kind='COLUMN'):
    """Save all actual source stages into a fresh root/kind/G00..G02 tree."""
    destination = Path(root).resolve()/kind
    if destination.exists():
        raise FileExistsError('Existing source preserved: '+str(destination))
    history = []
    for mesh, chart, tags, stage in _stages(kind):
        folder = destination/stage['stage']; folder.mkdir(parents=True)
        history.append(dict(stage, control_vertices=len(mesh.xyz), control_quads=len(mesh.faces)))
        physical = task36_growth.native(mesh)
        np.savez_compressed(folder/'control_quad.npz', xyz=mesh.xyz, faces=mesh.faces,
            classes=mesh.classes, rest=mesh.rest, anchors=mesh.anchors,
            generation=np.array(mesh.generation), surface=np.array(mesh.surface), chart=chart, memory=tags)
        np.savez_compressed(folder/'geometry.npz', xyz=physical.xyz, faces=physical.faces[:, :3])
        metadata = _metadata(kind, history)
        metadata.update(stage=stage['stage'], local_generation=mesh.generation, source_generation=mesh.generation,
                        actual_control_vertices=len(mesh.xyz), actual_control_quads=len(mesh.faces))
        (folder/'generation.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
    return destination/'G02'


def member_transforms():
    transforms = {}
    for name, x in [('LEFT', -1.55), ('RIGHT', 1.55)]:
        m = np.eye(4); m[:3, 3] = [x, 0., 0.]; transforms[name] = m
    beam = np.eye(4)
    # local Z -> global X, local X -> global Z, local Y -> global -Y.
    beam[:3, :3] = [[0, 0, 1], [0, -1, 0], [1, 0, 0]]
    beam[:3, 3] = [-2., 0., 3.09]
    transforms['LINTEL'] = beam
    return transforms


def assemble(parts):
    parts = dict(parts)
    if 'COLUMN' in parts:
        parts.setdefault('LEFT', parts['COLUMN']); parts.setdefault('RIGHT', parts['COLUMN'])
        del parts['COLUMN']
    if set(parts) != {'LEFT', 'RIGHT', 'LINTEL'}:
        raise ValueError('Supply LEFT/RIGHT/LINTEL, or shared COLUMN plus LINTEL.')
    transforms = member_transforms(); xyzs, triangles, labels, records = [], [], [], []
    offset = 0
    for index, name in enumerate(('LEFT', 'RIGHT', 'LINTEL')):
        part = parts[name]
        xyz, faces = (part['xyz'], part['faces']) if isinstance(part, dict) else part
        xyz, faces = np.asarray(xyz, float), np.asarray(faces)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
            raise ValueError('Finite local XYZ required.')
        if faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer):
            raise ValueError('Explicit integer native triangles required.')
        if faces.min() < 0 or faces.max() >= len(xyz):
            raise ValueError('Triangle vertex index outside local member.')
        m = transforms[name]
        world = xyz @ m[:3, :3].T + m[:3, 3]
        xyzs.append(world); triangles.append(faces+offset); labels.append(np.full(len(faces), index, np.int8))
        records.append(dict(name=name, part_id=index, vertex_start=offset, vertices=len(xyz),
            triangles=len(faces), world_bbox=[world.min(0).tolist(), world.max(0).tolist()]))
        offset += len(xyz)
    return dict(xyz=np.vstack(xyzs), faces=np.vstack(triangles), face_parts=np.concatenate(labels),
        metadata=dict(units='metres', parts=records, transforms={k:v.tolist() for k,v in transforms.items()},
            topology='Three separately indexed closed parts; no welding or connection construction',
            nominal_seat_gap=.04, nominal_rectangular_opening=[2.2, 2.6],
            nominal_box_extent=[4., .5, 3.54],
            clearance='40mm nominal seat gap only; deformed closest separation and intersections unverified',
            structural_connections='NOT_IMPLEMENTED'))
