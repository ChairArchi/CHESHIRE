"""Two attached scales of oblique ribs on the existing broad-shoulder ridge.

This is a pure scalar geometry operator: the caller applies the height along
normals measured on its actual incoming G06 surface. The source mesh, topology,
generation and trunk are not changed here. Six authored, nonuniform branches
start on folds.centre(q); one smaller branch starts on each primary curve.
These are connected curve families, not a fractal grammar, grid or noise field.
Widths are fractions of the measured G03 transverse surface arc, not exact
geodesic distances perpendicular to the oblique curves.
"""
from pathlib import Path
import importlib.util
import json

import numpy as np


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('rooted_fans_broad_operator', HERE/'folds.py')
folds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(folds)
measure, bulb = folds.measure, folds.bulb
quintic = folds.previous.guidance._quintic

RECIPE = dict(output_generation=6, additional_field_passes=1,
    root_centre_arc=float(folds.RECIPE['centre_arc']),
    root_centre_sweep_arc=float(folds.RECIPE['centre_sweep_arc']),
    primary_start_q=[-.74, -.51, -.22, .045, .31, .46],
    primary_duration_q=[.60, .56, .53, .49, .43, .37],
    primary_side=[-1., 1., -1., 1., -1., 1.],
    primary_reach_arc=[.27, .25, .30, .28, .25, .24],
    primary_halfwidth_arc=.055, primary_height_cap=.040,
    primary_height_width_ratio=.060,
    child_attachment_fraction=[.48, .56, .44, .53, .49, .57],
    child_end_extension_q=[.07, .05, .08, .06, .05, .07],
    child_reach_arc=[.10, .09, .11, .095, .10, .085],
    child_halfwidth_arc=.028, child_height_cap=.016,
    child_height_width_ratio=.025,
    root_turn_fraction=.20, root_height_fade_fraction=.12,
    tip_height_fade_fraction=.24, groove_root_fade_fraction=.28,
    groove_ratio=.42, groove_offset_in_halfwidths=1.45,
    groove_halfwidth_ratio=.65,
    trunk_groove_protection_halfwidth_arc=.075,
    trunk_groove_protection_fade_arc=.055,
    end_limits=[.10, .90],
    scope='Two authored connected curve scales on one shared measured broad shoulder; same recipe on both inputs',
    lineage='Additional scalar pass on actual incoming BROAD_ACTIVE G06; no refinement and generation remains 6',
    amplitude_scope='Fine-pass amplitude is an explicit comparison condition; no legacy .65 total-shift design requirement',
    normal_scope='Caller applies height along actual incoming G06 pooled normals and performs constructive material X/Y geometry reflection',
    width_scope='Halfwidth is a fraction of measured G03 transverse surface arc, not an exact perpendicular geodesic distance')


def _recipe(recipe):
    result = dict(RECIPE)
    if recipe is not None:
        result.update(recipe)
    keys = ('primary_start_q', 'primary_duration_q', 'primary_side',
            'primary_reach_arc', 'child_attachment_fraction',
            'child_end_extension_q', 'child_reach_arc')
    arrays = [np.asarray(result[key], float) for key in keys]
    if not all(value.ndim == 1 and len(value) == len(arrays[0]) for value in arrays):
        raise ValueError('Primary and child recipe arrays must have the same one-dimensional length.')
    if len(arrays[0]) == 0 or not all(np.isfinite(value).all() for value in arrays):
        raise ValueError('A finite nonempty connected curve family is required.')
    start, duration, sides, reach, attachment, extension, child_reach = arrays
    if (np.any(duration <= 0.) or np.any(start <= -1.) or
            np.any(start+duration+extension >= 1.) or np.any(extension < 0.) or
            np.any(np.abs(sides) != 1.) or np.any(reach <= 0.) or
            np.any(child_reach <= 0.) or np.any(attachment <= 0.) or np.any(attachment >= 1.)):
        raise ValueError('Curve roots, tips and child attachment must lie inside the shared patch.')
    for key in ('primary_halfwidth_arc', 'child_halfwidth_arc',
                'primary_height_cap', 'child_height_cap',
                'primary_height_width_ratio', 'child_height_width_ratio',
                'root_turn_fraction', 'root_height_fade_fraction',
                'tip_height_fade_fraction', 'groove_root_fade_fraction',
                'groove_offset_in_halfwidths', 'groove_halfwidth_ratio',
                'trunk_groove_protection_fade_arc'):
        if not np.isfinite(result[key]) or float(result[key]) <= 0.:
            raise ValueError('Positive finite fold scale/fade required: '+key)
    if not 0. <= float(result['groove_ratio']) <= 1.:
        raise ValueError('Groove ratio must be in [0,1].')
    if result['output_generation'] != 6 or result['additional_field_passes'] != 1:
        raise ValueError('This operator declares generation 6 with one field-only pass.')
    return result


def root_centre(q, recipe=RECIPE):
    """Use exactly the existing broad fold centre with recorded coefficients."""
    return folds.centre(q, dict(centre_arc=recipe['root_centre_arc'],
                               centre_sweep_arc=recipe['root_centre_sweep_arc']))


def definitions(recipe=RECIPE):
    """Small serializable curve bank; child IDs explicitly name their parent."""
    selected = _recipe(recipe)
    result = []
    for index, (start, duration, side, reach) in enumerate(zip(
            selected['primary_start_q'], selected['primary_duration_q'],
            selected['primary_side'], selected['primary_reach_arc'])):
        result.append(dict(curve_id=index, level=0, parent_id=-1,
            start_q=float(start), end_q=float(start+duration),
            side=float(side), reach_arc=float(reach)))
    count = len(result)
    for index in range(count):
        parent = result[index]
        start = parent['start_q']+selected['child_attachment_fraction'][index]*(parent['end_q']-parent['start_q'])
        result.append(dict(curve_id=count+index, level=1, parent_id=index,
            start_q=float(start),
            end_q=float(parent['end_q']+selected['child_end_extension_q'][index]),
            side=parent['side'], reach_arc=float(selected['child_reach_arc'][index])))
    return result


def curve(q, definition, recipe=RECIPE, bank=None):
    """Evaluate one attached centreline and its root/tip height envelope.

    At a primary root the centreline equals the long trunk. A child equals its
    actual primary curve at its root. The initial turn has zero transverse
    derivative, while quintic height fades join both ends to the existing body.
    """
    q = np.asarray(q, float)
    if not np.isfinite(q).all():
        raise ValueError('Finite curve parameters required.')
    bank = definitions(recipe) if bank is None else bank
    progress = (q-definition['start_q'])/(definition['end_q']-definition['start_q'])
    clipped = np.clip(progress, 0., 1.)
    bend = clipped*quintic(clipped/recipe['root_turn_fraction'])
    if definition['level'] == 0:
        inherited = root_centre(q, recipe)
    else:
        inherited = curve(q, bank[definition['parent_id']], recipe, bank)[0]
    centre = inherited+definition['side']*definition['reach_arc']*bend
    gate = quintic(progress/recipe['root_height_fade_fraction'])*quintic(
        (1.-progress)/recipe['tip_height_fade_fraction'])
    return centre, progress, gate


def height(chart, patch, recipe=RECIPE):
    """Return signed scalar fine relief and replayable per-control fields.

    Curves are evaluated sequentially, avoiding a curves-by-G06-control array.
    Positive crowns combine by maximum; groove suppression protects every crown
    and the centre of the original trunk. There is no accumulation at crossings.
    """
    selected = _recipe(recipe)
    chart = np.asarray(chart, float)
    owned = measure.coordinates(chart, patch)
    q, u = owned['q'], owned['u']
    weight = owned['envelope'].copy()
    lower, upper = selected['end_limits']
    ends = (chart[:, 0] <= lower) | (chart[:, 0] >= upper)
    weight[ends] = 0.
    width = np.interp(chart[:, 0], patch['parameter'], patch['physical_width'])
    if not np.isfinite(width).all() or np.any(width <= 0.):
        raise ValueError('Actual measured positive shoulder width required; no synthetic fallback.')
    primary_amplitude = np.minimum(selected['primary_height_cap'], selected['primary_height_width_ratio']*width)
    child_amplitude = np.minimum(selected['child_height_cap'], selected['child_height_width_ratio']*width)
    primary_positive = np.zeros_like(q)
    child_positive = np.zeros_like(q)
    positive_strength = np.zeros_like(q)
    negative_raw = np.zeros_like(q)
    owner = np.full(q.shape, -1, dtype=np.int16)
    bank = definitions(selected)
    for item in bank:
        middle, progress, gate = curve(q, item, selected, bank)
        if item['level'] == 0:
            halfwidth, amplitude = selected['primary_halfwidth_arc'], primary_amplitude
            target = primary_positive
        else:
            halfwidth, amplitude = selected['child_halfwidth_arc'], child_amplitude
            target = child_positive
        positive = gate*bulb.compact((u-middle)/halfwidth)
        candidate = amplitude*positive
        previous_positive = np.maximum(primary_positive, child_positive)
        owner[candidate > previous_positive] = item['curve_id']
        np.maximum(target, candidate, out=target)
        np.maximum(positive_strength, positive, out=positive_strength)
        groove = np.maximum(
            bulb.compact((u-middle-selected['groove_offset_in_halfwidths']*halfwidth)/
                         (selected['groove_halfwidth_ratio']*halfwidth)),
            bulb.compact((u-middle+selected['groove_offset_in_halfwidths']*halfwidth)/
                         (selected['groove_halfwidth_ratio']*halfwidth)))
        groove *= gate*quintic(progress/selected['groove_root_fade_fraction'])
        np.maximum(negative_raw, amplitude*selected['groove_ratio']*groove, out=negative_raw)
    positive_height = np.maximum(primary_positive, child_positive)
    trunk_release = quintic((np.abs(u-root_centre(q, selected))-
        selected['trunk_groove_protection_halfwidth_arc'])/
        selected['trunk_groove_protection_fade_arc'])
    negative_height = negative_raw*(1.-positive_strength)**2*trunk_release
    result = weight*(positive_height-negative_height)
    owner[weight == 0.] = -1
    return result, dict(height=result, primary_positive_height=primary_positive,
        child_positive_height=child_positive, positive_height=positive_height,
        negative_height=negative_height, q=q, u=u, patch_weight=weight,
        fixed_ends=ends, positive_curve_owner=owner,
        actual_shoulder_width=width, output_generation=np.array(6),
        additional_field_passes=np.array(1),
        curve_definitions_json=np.array(json.dumps(bank, sort_keys=True)),
        recipe_json=np.array(json.dumps(selected, sort_keys=True)))


def curve_evidence(patch, recipe=RECIPE, samples=97):
    """Small material-UV evidence for the caller to sample on actual G06.

    This helper does not invent XYZ/frame provenance. The caller must save
    actual native triangle IDs and barycentric coordinates when sampling it.
    All primary roots and child attachments are retained explicitly.
    """
    selected = _recipe(recipe)
    if int(samples) < 3:
        raise ValueError('At least three evidence samples per curve required.')
    bank = definitions(selected)
    parameters = np.asarray(patch['parameter'])
    all_q, all_u, all_gate, all_uv = [], [], [], []
    root_q, root_u, parent_root_u = [], [], []
    for item in bank:
        q = np.linspace(item['start_q'], item['end_q'], int(samples))
        u, _, gate = curve(q, item, selected, bank)
        if np.any(u <= 0.) or np.any(u >= 1.):
            raise ValueError('Authored curve evidence leaves the measured physical shoulder.')
        parameter = parameters[0]+(q+1.)*.5*np.ptp(parameters)
        all_q.append(q); all_u.append(u); all_gate.append(gate)
        all_uv.append(measure.uv_at_fraction(parameter, u, patch))
        root_q.append(q[0]); root_u.append(u[0])
        parent_root_u.append(float(root_centre(q[0], selected)) if item['level'] == 0 else
            float(curve(q[0], bank[item['parent_id']], selected, bank)[0]))
    return dict(q=np.asarray(all_q), u=np.asarray(all_u), height_gate=np.asarray(all_gate),
        surface_uv=np.asarray(all_uv), root_q=np.asarray(root_q), root_u=np.asarray(root_u),
        inherited_root_u=np.asarray(parent_root_u),
        root_attachment_max_error=np.array(np.max(np.abs(np.asarray(root_u)-parent_root_u))),
        curve_ids=np.array([item['curve_id'] for item in bank]),
        levels=np.array([item['level'] for item in bank]),
        parent_ids=np.array([item['parent_id'] for item in bank]),
        curve_definitions_json=np.array(json.dumps(bank, sort_keys=True)),
        coordinate_scope=np.array('Measured G03 arc map; caller must resample these UV on actual incoming G06 for XYZ and native provenance'))
