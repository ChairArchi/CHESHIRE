"""Regionally choose existing G2 coupled-subdivision placement coefficients.

No source XYZ displacement, primitive, new split topology, normal field or field
target is introduced. The unchanged Task36 function still calls the unchanged
reference subdivider. A scoped adapter supplies only its existing absolute w3,
w4 and w1 arrays, using inherited-material C2 plateau regions. Empty/disabled
regions do not replace the subdivider at all. Every attribute is restored.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import importlib

import numpy as np


_ACTIVE = False
KEYS = ('w3', 'w4', 'w1')


@dataclass
class RegionalRecord:
    evidence: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def _regions(regions):
    out = []
    for region in regions or ():
        if not region.get('enabled', True):
            continue
        value = dict(region)
        for key in ('t_centre', 't_halfwidth', 'theta_centre', 'theta_halfwidth'):
            if key not in value or not np.isfinite(value[key]):
                raise ValueError('Finite material region parameter required: '+key)
        if min(value['t_halfwidth'], value['theta_halfwidth']) <= 0:
            raise ValueError('Positive material region halfwidths required.')
        if not any(key in value for key in KEYS):
            continue
        for key, lo, hi in (('w3', -1., 1.), ('w4', -1., 2.), ('w1', -2., 2.)):
            if key in value and (not np.isfinite(value[key]) or not lo <= value[key] <= hi):
                raise ValueError('Existing Task36 coefficient domain exceeded: '+key)
        out.append(value)
    return out


def _mask(points, region, plateau):
    theta = np.arctan2(np.abs(points[:, 2]), np.abs(points[:, 1]))
    return (plateau((points[:, 0]-region['t_centre'])/region['t_halfwidth'], .60)*
            plateau((theta-region['theta_centre'])/region['theta_halfwidth'], .65))


def _blend(raw, key, masks, regions):
    selected = [(mask, region[key]) for mask, region in zip(masks, regions) if key in region]
    if not selected:
        return raw.copy(), np.zeros(len(raw))
    total = sum(mask for mask, _target in selected)
    numerator = sum(mask*float(target) for mask, target in selected)
    strength = np.minimum(total, 1.)
    target = numerator/np.maximum(total, 1.)
    out = raw*(1-strength)+target
    # Preserve exact no-op samples rather than relying on floating arithmetic.
    out[total == 0] = raw[total == 0]
    return out, strength


@contextmanager
def regional_controls(early, chart, generation, regions, *, enabled=True, refmodule=None):
    """Yield a record while one actual G1->G2 Task36 call is evaluated.

    The first resolved call is the coupled placement. Task36 then computes a
    standard CC baseline without resolved controls and a geometry-only call.
    Its own geometry-only controls already copy the modified coupled arrays;
    the adapter verifies that fact and never applies the blend a second time.
    Normal coefficients and w2 retain their exact incoming arrays.

    Coupling of completed face points to neighboring edge points creates a
    legitimate one-ring halo. No globally unchanged-XYZ claim is made outside
    the material mask. Task36's existing vertex_memory=1 remains responsible
    for old-control retention, not this adapter.
    """
    global _ACTIVE
    regions = _regions(regions) if enabled else []
    record = RegionalRecord(metadata=dict(
        schema='CHESHIRE_EXISTING_G2_REGIONAL_SPLIT_CONTROLS_V1', generation=int(generation),
        applied=False, regions=regions, changed_control_keys=list(KEYS),
        source_XYZ_warp=False, new_operator=False,
        coupled_face_edge_halo='Completed face points influence incident edges; no outside-region XYZ invariance asserted.',
        no_op_reason='Empty/disabled regions or generation is not G2.'))
    if generation != 2 or not regions:
        yield record
        return
    if _ACTIVE:
        raise RuntimeError('Nested regional Task36 adapters are not supported.')
    labels = np.asarray(chart, float)
    if labels.ndim != 2 or labels.shape[1] != 3 or not np.isfinite(labels).all():
        raise ValueError('Finite actual incoming material chart required.')
    ref = refmodule or importlib.import_module('cheshire.reference_subdivision')
    plateau = early.wall.wall_fold.plateau
    original = ref.subdivide
    incoming_id = None
    modified = None
    raw_first = None
    topology = None
    calls = []
    noresolved = 0

    def scoped(mesh, row, *, scale_mode=ref.LOCAL_INCIDENT_SCALE,
               intrinsic=None, resolved_controls=None):
        nonlocal incoming_id, modified, raw_first, topology, noresolved
        if mesh.generation != 1 or len(mesh.xyz) != len(labels):
            return original(mesh, row, scale_mode=scale_mode, intrinsic=intrinsic,
                            resolved_controls=resolved_controls)
        if resolved_controls is None:
            noresolved += 1
            return original(mesh, row, scale_mode=scale_mode, intrinsic=intrinsic,
                            resolved_controls=None)
        if any(key not in resolved_controls for key in KEYS):
            raise ValueError('Expected existing coupled Task36 w3/w4/w1 arrays.')
        raw = {key: np.asarray(value).copy() for key, value in resolved_controls.items()}
        if modified is None:
            incoming_id = id(mesh)
            topology = ref.topology(mesh)
            face_points = labels[mesh.faces].mean(axis=1)
            edge_points = labels[topology['edges']].mean(axis=1)
            face_masks = np.asarray([_mask(face_points, region, plateau) for region in regions])
            edge_masks = np.asarray([_mask(edge_points, region, plateau) for region in regions])
            previous = mesh.classes[mesh.faces]
            eligible = (((previous == 0).sum(axis=1) == 1) &
                        ((previous == 1).sum(axis=1) == 2) &
                        ((previous == 2).sum(axis=1) == 1) &
                        ((np.argmax(previous == 0, axis=1)+2) % 4 ==
                         np.argmax(previous == 2, axis=1)))
            modified = {}
            strengths = {}
            for key in KEYS:
                if raw[key].dtype.kind != 'f':
                    raise ValueError('Existing absolute coefficient arrays must use floating values: '+key)
                modified[key], strengths[key] = _blend(
                    raw[key], key, edge_masks if key == 'w1' else face_masks, regions)
                # In-place is essential: Task36's saved resolved_state aliases
                # these actual coefficient arrays before calling subdivide.
                resolved_controls[key][...] = modified[key]
            raw_first = raw
            record.evidence.update(
                face_region_masks=face_masks, edge_region_masks=edge_masks,
                incoming_face_material_coordinates=face_points,
                incoming_edge_material_coordinates=edge_points,
                input_edges=topology['edges'].copy(), eq4_eligible_mask=eligible,
                **{'raw_resolved_'+key: value.copy() for key, value in raw.items()},
                **{'modified_resolved_'+key: value.copy() for key, value in modified.items()},
                **{'modified_support_'+key: value.copy() for key, value in strengths.items()})
            record.metadata.update(applied=True, no_op_reason=None,
                actual_input_vertices=len(mesh.xyz), actual_input_quads=len(mesh.faces),
                eligible_faces=int(eligible.sum()),
                eligible_modified_faces=int(np.count_nonzero(eligible &
                    ((modified['w3'] != raw['w3']) | (modified['w4'] != raw['w4'])))),
                modified_counts={key: int(np.count_nonzero(modified[key] != raw[key])) for key in KEYS},
                old_point_policy='Unchanged existing Task36 vertex_memory and cap policy.',
                normal_controls_unchanged=True, w2_unchanged=True,
                actual_topology_unchanged_by_adapter=True,
                mask_semantics='Existing C2 plateau in inherited t/absolute-quadrant theta; normalized overlap of coefficient requests, not XYZ displacement.',
                coefficients='Absolute existing resolved w3/w4 face and w1 edge coefficients.')
            if not any(record.metadata['modified_counts'].values()):
                record.metadata.update(applied=False,
                    no_op_reason='Material masks are zero or all requested coefficients equal the incoming values.')
        else:
            if id(mesh) != incoming_id:
                raise ValueError('A regional scope accepts one actual Task36 parent only.')
            for key in KEYS:
                if not np.array_equal(resolved_controls[key], modified[key]):
                    raise ValueError('Geometry-only Task36 did not copy the actual modified coefficient: '+key)
        for key in raw:
            if key not in KEYS and not np.array_equal(raw[key], resolved_controls[key]):
                raise ValueError('Regional adapter changed an undeclared coefficient: '+key)
        call_id = len(calls)
        calls.append(dict(resolved_call=call_id,
            scope='coupled' if call_id == 0 else 'existing_geometry_only_copy',
            blend_applied_once=(call_id == 0),
            regional_arrays_match_first=all(np.array_equal(resolved_controls[key], modified[key]) for key in KEYS)))
        record.evidence.update({'call_'+str(call_id)+'_actual_'+key: np.asarray(resolved_controls[key]).copy()
                                for key in KEYS})
        return original(mesh, row, scale_mode=scale_mode, intrinsic=intrinsic,
                        resolved_controls=resolved_controls)

    _ACTIVE = True
    ref.subdivide = scoped
    try:
        yield record
    finally:
        ref.subdivide = original
        _ACTIVE = False
        record.metadata.update(resolved_calls=calls,
                               standard_noresolved_calls_unchanged=noresolved,
                               subdivide_restored=True)
