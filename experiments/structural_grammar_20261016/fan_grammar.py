"""New coarse layered-calyx grammar, independent of all previous column seeds.

Closed thick membranes grow out of a continuous solid core. Their large
centreline bends outward/upward and returns inward/downward. Smaller nested
membranes follow the same direction. Three unequal tiers use independent local
axes and 3/5/4-fold rotational arrangements. This is macro geometry, not surface
ornament, noise, old mesh displacement, or an imitation of a cited algorithm.

``build_components()`` returns (components, metadata). Each component dictionary
contains name, xyz, faces, role, level and recipe. A common CSG runner should
union the actual closed components before Catmull--Clark refinement. Component
closure alone does not certify the union's embedding or fabrication suitability.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from math import comb
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator


RECIPE = dict(
    schema='CHESHIRE_NEW_LAYERED_CALYX_MACRO_GRAMMAR_V1',
    core_height=10.35, core_segments=32, core_rings=49,
    core_radius_knots=[0., .06, .16, .28, .40, .54, .68, .78, .90, 1.],
    core_radius_values=[.70, .66, .58, .53, .62, .57, .53, .62, .58, .55],
    longitudinal_segments=16, across_segments=8,
    levels=[
        dict(name='lower_small_calyx', z=1.10, radius=1.00, height=.90,
             petals=3, phase_degrees=0., tilt_x_degrees=0., tilt_y_degrees=4.,
             width=.72, thickness=.12, cup=.24, sweep=.08,
             nested_scales=[1.], nested_height_scales=[1.]),
        dict(name='middle_fivefold_fan', z=6.15, radius=1.85, height=2.20,
             petals=5, phase_degrees=18., tilt_x_degrees=8., tilt_y_degrees=-7.,
             width=1.24, thickness=.13, cup=.26, sweep=.14,
             nested_scales=[1., .64], nested_height_scales=[1., .65]),
        dict(name='upper_fourfold_crown', z=8.70, radius=2.80, height=2.30,
             petals=4, phase_degrees=45., tilt_x_degrees=-9., tilt_y_degrees=12.,
             width=1.62, thickness=.15, cup=.29, sweep=-.16,
             nested_scales=[1., .70, .43], nested_height_scales=[1., .84, .66])],
    spatial_hierarchy='Compact low calyx, a long quiet stem, then two overlapping upper crown clusters of sharply unequal radii/heights. Large membranes contain smaller same-flow membranes. Local axes and 3/5/4 rotational counts differ.',
    original_column_geometry_used=False, detail_ornament_added=False,
    union_required=True, self_intersection='NOT_CERTIFIED', fabrication='NOT_CERTIFIED')


def _unit(v):
    size = np.linalg.norm(v, axis=-1, keepdims=True)
    if np.any(size <= 1e-12):
        raise ValueError('Degenerate coarse loft frame.')
    return v/size


def _rotation(ax, ay):
    ax, ay = np.deg2rad([ax, ay])
    rx = np.array([[1., 0., 0.], [0., np.cos(ax), -np.sin(ax)],
                   [0., np.sin(ax), np.cos(ax)]])
    ry = np.array([[np.cos(ay), 0., np.sin(ay)], [0., 1., 0.],
                   [-np.sin(ay), 0., np.cos(ay)]])
    return ry@rx


def _bezier(points, t):
    degree = len(points)-1
    return sum(comb(degree, k)*(1-t)[:, None]**(degree-k)*t[:, None]**k*p
               for k, p in enumerate(np.asarray(points, float)))


def thick_membrane(centreline, lateral, width, thickness, cup, across_segments):
    """Closed double-surface sheet with actual finite-thickness capped edges."""
    c, lateral = np.asarray(centreline, float), np.asarray(lateral, float)
    tangent = _unit(np.gradient(c, axis=0))
    lateral = _unit(lateral-tangent*np.sum(lateral*tangent, axis=1)[:, None])
    normal = _unit(np.cross(lateral, tangent))
    width, thick = np.broadcast_arrays(np.asarray(width, float),
                                       np.asarray(thickness, float))
    if width.shape != (len(c),) or np.any(width <= 0) or np.any(thick <= 0):
        raise ValueError('Positive width and nonzero thickness at every end required.')
    v = np.linspace(-1., 1., across_segments+1)
    mid = (c[:, None]+lateral[:, None]*(.5*width[:, None]*v[None])[:, :, None] +
           normal[:, None]*(cup*width[:, None]*(v[None]**2-1.))[:, :, None])
    offset = normal[:, None]*(.5*thick)[:, None, None]
    front, back = (mid+offset).reshape(-1, 3), (mid-offset).reshape(-1, 3)
    nrow, ncol, count = len(c), len(v), len(front)
    tri = []
    for i in range(nrow-1):
        for j in range(ncol-1):
            a = i*ncol+j
            b, cc, d = a+1, a+ncol, a+ncol+1
            tri.extend(((a, b, cc), (b, d, cc)))
    tri = np.asarray(tri, np.int64)
    directed = np.concatenate((tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]))
    keys = np.sort(directed, axis=1)
    _edges, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    boundary = directed[counts[inverse] == 1]
    sides = np.array([face for a, b in boundary for face in
                      ((b, a, a+count), (b, a+count, b+count))], np.int64)
    faces = np.concatenate((tri, tri[:, ::-1]+count, sides))
    return np.concatenate((front, back)), faces


def petal(level, layer, index, recipe=RECIPE):
    scale = level['nested_scales'][layer]
    hs = level['nested_height_scales'][layer]
    radius, height = level['radius']*scale, level['height']*hs
    n = int(recipe['longitudinal_segments'])
    t = np.linspace(0., 1., n+1)
    # The last point is inward and lower than the penultimate control point:
    # the actual material tip returns rather than merely tapering straight up.
    rz = _bezier([[.18, -.10], [.52*radius, .10*height],
                  [1.28*radius, .58*height], [1.08*radius, 1.23*height],
                  [max(.64*radius, .95), .91*height]], t)
    theta0 = np.deg2rad(level['phase_degrees'])+2*np.pi*index/level['petals']
    theta = theta0+level['sweep']*np.sin(np.pi*t)
    c = np.column_stack((rz[:, 0]*np.cos(theta), rz[:, 0]*np.sin(theta), rz[:, 1]))
    lateral = np.column_stack((-np.sin(theta), np.cos(theta), np.zeros(len(t))))
    width = level['width']*scale*(.22+.78*np.sin(np.pi*t)**.85)
    thickness = level['thickness']*max(.65, scale)*(.85+.15*np.sin(np.pi*t))
    xyz, faces = thick_membrane(c, lateral, width, thickness,
                                level['cup'], int(recipe['across_segments']))
    rot = _rotation(level['tilt_x_degrees'], level['tilt_y_degrees'])
    xyz = xyz@rot.T+np.array([0., 0., level['z']+.10*layer])
    return dict(name=level['name']+'_layer'+str(layer)+'_petal'+str(index),
                xyz=xyz, faces=faces, role='outer_membrane' if layer == 0 else 'nested_membrane',
                level=level['name'], recipe=dict(level=deepcopy(level), layer=layer,
                    angular_index=index, layer_radius=radius, layer_height=height))


def solid_core(recipe=RECIPE):
    nr, ns = int(recipe['core_rings']), int(recipe['core_segments'])
    t = np.linspace(0., 1., nr)
    radius = PchipInterpolator(recipe['core_radius_knots'], recipe['core_radius_values'])(t)
    angle = np.arange(ns)*2*np.pi/ns
    xyz = np.stack((radius[:, None]*np.cos(angle), radius[:, None]*np.sin(angle),
                    np.broadcast_to((recipe['core_height']*t)[:, None], (nr, ns))), axis=2).reshape(-1, 3)
    xyz = np.concatenate((xyz, [[0., 0., 0.], [0., 0., recipe['core_height']]]))
    tri = []
    for i in range(nr-1):
        for j in range(ns):
            a, b = i*ns+j, i*ns+(j+1)%ns
            cc, d = a+ns, b+ns
            tri.extend(((a, b, cc), (b, d, cc)))
    for j in range(ns):
        tri.append((j, nr*ns, (j+1)%ns))
        a, b = (nr-1)*ns+j, (nr-1)*ns+(j+1)%ns
        tri.append((a, b, nr*ns+1))
    return dict(name='continuous_solid_backing_core', xyz=xyz,
                faces=np.asarray(tri, np.int64), role='solid_backing_core', level='all',
                recipe=dict(height=recipe['core_height'], radius_knots=recipe['core_radius_knots'],
                            radius_values=recipe['core_radius_values']))


def component_checks(component):
    x, f = component['xyz'], component['faces']
    edges = np.concatenate((f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]))
    keys = np.sort(edges, axis=1)
    unique, inverse, count = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    sign = np.sign(edges[:, 1]-edges[:, 0])
    balanced = np.bincount(inverse, weights=sign)
    area = .5*np.linalg.norm(np.cross(x[f[:, 1]]-x[f[:, 0]], x[f[:, 2]]-x[f[:, 0]]), axis=1)
    volume = float(np.einsum('ij,ij->i', x[f[:, 0]],
                              np.cross(x[f[:, 1]], x[f[:, 2]])).sum()/6.)
    result = dict(vertices=len(x), triangles=len(f),
        finite=bool(np.isfinite(x).all()), closed_two_face_edges=bool(np.all(count == 2)),
        oriented_edge_pairs=bool(np.all(balanced == 0)),
        Euler=int(len(x)-len(unique)+len(f)), minimum_triangle_area=float(area.min()),
        signed_volume=volume, self_intersection='NOT_CHECKED')
    result['passed'] = bool(result['finite'] and result['closed_two_face_edges'] and
        result['oriented_edge_pairs'] and result['Euler'] == 2 and
        result['minimum_triangle_area'] > 1e-12 and volume > 0)
    return result


def build_components(recipe=None):
    recipe = deepcopy(RECIPE if recipe is None else recipe)
    components = [solid_core(recipe)]
    for level in recipe['levels']:
        if len(level['nested_scales']) != len(level['nested_height_scales']):
            raise ValueError('Each nested membrane needs an explicit height scale.')
        for layer in range(len(level['nested_scales'])):
            for index in range(level['petals']):
                components.append(petal(level, layer, index, recipe))
    checks = {part['name']: component_checks(part) for part in components}
    if not all(item['passed'] for item in checks.values()):
        raise ValueError('Closed coarse component failed: '+str(checks))
    total = sum(len(part['faces']) for part in components)
    if total > 30_000:
        raise ValueError('Explicit coarse input triangle budget exceeded.')
    level_bounds = {}
    for level in recipe['levels']:
        points = np.concatenate([part['xyz'] for part in components if part['level'] == level['name']])
        level_bounds[level['name']] = dict(
            actual_bbox_min=points.min(axis=0).tolist(),
            actual_bbox_max=points.max(axis=0).tolist(),
            actual_z_bounds=[float(points[:, 2].min()), float(points[:, 2].max())],
            declared_root_height=level['z'], declared_membrane_height=level['height'],
            declared_major_radius=level['radius'])
    meta = dict(schema=recipe['schema'], recipe=recipe,
        component_count=len(components), membrane_count=len(components)-1,
        coarse_input_triangles=total, component_checks=checks,
        actual_level_bounds=level_bounds,
        closed_individual_components=True,
        connected_whole='REQUIRES_ACTUAL_CSG_UNION',
        original_column_geometry_used=False, added_surface_detail=False,
        topology_scope='Each finite-thickness sheet is a closed genus-zero solid and its root overlaps the continuous core. Actual CSG and later CC are the runner responsibility.',
        self_intersection='NOT_CERTIFIED', fabrication='NOT_CERTIFIED')
    return components, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Preserve the previous coarse grammar output.')
    components, meta = build_components()
    output.mkdir(parents=True)
    for index, part in enumerate(components):
        path = output/(format(index, '02d')+'_'+part['name']+'.npz')
        np.savez_compressed(path, xyz=part['xyz'], faces=part['faces'])
        meta['component_checks'][part['name']]['file'] = str(path)
    (output/'COMPONENTS.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2,
                                                   allow_nan=False), encoding='utf8')
    print(json.dumps(dict(output=str(output), components=meta['component_count'],
                         triangles=meta['coarse_input_triangles'])))


if __name__ == '__main__':
    main()
