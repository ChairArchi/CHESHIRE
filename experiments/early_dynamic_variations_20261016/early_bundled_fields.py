"""Coherent large fluted bundles on actual G2, before WALL is remeasured.

Only inherited material t/theta specify the field. Primary longitudinal folds
and smaller folds use one shared curved phase. Broad crown/lower returns vary
the silhouette. X/Y vector transport uses actual supplied reflection IDs;
source XYZ are never averaged. No microdetail or topology is added.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator


def _smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*x*(10.+x*(-15.+6.*x))


def _bump(t, centre, width):
    d = (t-centre)/width
    return np.maximum(0., 1.-d*d)**3


def apply_bundled_field(xyz, chart, recipe, *, vertex_pairs, stage=2):
    x, labels = np.asarray(xyz, float), np.asarray(chart, float)
    if (stage != 2 or x.ndim != 2 or x.shape[1] != 3 or labels.shape != x.shape or
            not np.isfinite(x).all() or not np.isfinite(labels).all()):
        raise ValueError('Finite actual G2 XYZ and inherited material chart required.')
    t = labels[:, 0]
    if t.min() < -1e-12 or t.max() > 1.+1e-12:
        raise ValueError('Inherited unit material height required.')
    n = len(x)
    ids = np.arange(n, dtype=np.int64)
    px, py = (np.asarray(vertex_pairs[k], np.int64) for k in ('X', 'Y'))
    if (px.shape != (n,) or py.shape != (n,) or
            not np.array_equal(px[px], ids) or not np.array_equal(py[py], ids) or
            not np.array_equal(px[py], py[px])):
        raise ValueError('Actual commuting X/Y reflection involutions required.')
    theta = np.arctan2(np.abs(labels[:, 2]), np.abs(labels[:, 1]))
    order = int(recipe.get('order', 2))
    strength = float(recipe.get('strength', .38))
    curvature = float(recipe.get('curvature', .20))
    secondary = float(recipe.get('secondary', .26))
    crown_strength = float(recipe.get('crown_strength', .38))
    crown_return = float(recipe.get('crown_return', .22))
    crown_centre = float(recipe.get('crown_centre', .75))
    crown_width = float(recipe.get('crown_width', .17))
    lower_strength = float(recipe.get('lower_strength', .22))
    tangent_strength = float(recipe.get('tangent_strength', .10))
    bound_fraction = float(recipe.get('bound_radius_fraction', .70))
    if (order not in (2, 3) or not np.isfinite([strength, curvature, secondary,
            crown_strength, crown_return, crown_centre, crown_width,
            lower_strength, tangent_strength, bound_fraction]).all() or
            min(strength, secondary, crown_strength, crown_return, lower_strength) < 0 or
            crown_width <= 0 or not 0 < bound_fraction <= .70):
        raise ValueError('Bounded declared coarse bundle parameters required.')
    radial_size = np.linalg.norm(x[:, :2], axis=1)
    valid = (t > .08)&(t < .92)&(radial_size > 1e-8)
    radius = float(np.median(radial_size[valid]))
    if not np.isfinite(radius) or radius <= 0:
        raise ValueError('Positive actual G2 median body radius required.')
    # Phase bends smoothly with height while its angular derivative vanishes
    # at actual reflection seams. Secondary folds follow the primary phase.
    phase_bend = curvature*np.sin(2*np.pi*(t-.10)/1.15)*np.sin(2*theta)
    phase = 2*order*(theta+phase_bend)
    profile = (np.cos(phase)+secondary*np.cos(2*phase))/(1+secondary)
    env_knots = recipe.get('envelope_knots', [0., .06, .18, .38, .55, .73, .88, .96, 1.])
    env_values = recipe.get('envelope_values', [0., .18, .86, 1., .85, 1., .72, .12, 0.])
    env = PchipInterpolator(env_knots, env_values)(t)
    cap_fade = _smooth((t-.035)/.055)*_smooth((.965-t)/.055)
    crown = _bump(t, crown_centre, crown_width)
    lower_centre = float(recipe.get('lower_centre', .23))
    lower_width = float(recipe.get('lower_width', .17))
    lower = _bump(t, lower_centre, lower_width)
    middle = _bump(t, float(recipe.get('middle_centre', .47)),
                   float(recipe.get('middle_width', .06)))
    middle_strength = float(recipe.get('middle_strength', 0.))
    radial_request = radius*(strength*env*profile +
        crown_strength*crown*(.70+.30*np.cos(phase)) +
        lower_strength*lower*(.72+.28*np.cos(phase)) +
        middle_strength*middle*(.75+.25*np.cos(phase)))
    # A broad radial/axial return, rather than an independent jitter field.
    axial_request = radius*(crown_return*crown*np.sin(np.pi*(t-crown_centre)/crown_width) +
                            .16*lower_strength*lower*np.sin(np.pi*(t-lower_centre)/lower_width))
    radial = np.zeros_like(x)
    radial[:, :2] = np.divide(x[:, :2], radial_size[:, None],
                             out=np.zeros_like(x[:, :2]), where=radial_size[:, None] > 1e-12)
    tangent = np.column_stack((-radial[:, 1], radial[:, 0], np.zeros(n)))
    signed_xy = 2*labels[:, 1]*labels[:, 2]/np.maximum(
        labels[:, 1]**2+labels[:, 2]**2, 1e-30)
    tangential_request = radius*tangent_strength*env*signed_xy*np.sin(phase)
    delta = radial*radial_request[:, None]+tangent*tangential_request[:, None]
    delta[:, 2] = axial_request
    delta *= cap_fade[:, None]
    norm = np.linalg.norm(delta, axis=1)
    bound = bound_fraction*radius
    factor = np.divide(bound*np.tanh(norm/bound), norm,
                       out=np.ones_like(norm), where=norm > 0)
    delta *= factor[:, None]
    # Exact vector orbits, without source-coordinate averaging or inferred IDs.
    pxy = px[py]
    rep = np.minimum(np.minimum(ids, px), np.minimum(py, pxy))
    delta[px == ids, 0] = 0.
    delta[py == ids, 1] = 0.
    transported = delta[rep].copy()
    transported[(ids == px[rep])|(ids == pxy[rep]), 0] *= -1.
    transported[(ids == py[rep])|(ids == pxy[rep]), 1] *= -1.
    transported[px == ids, 0] = 0.
    transported[py == ids, 1] = 0.
    caps = (t <= .035)|(t >= .965)
    transported[caps] = 0.
    out = x+transported
    out[caps] = x[caps]
    if not np.isfinite(out).all() or not np.array_equal(out[caps], x[caps]):
        raise ValueError('Nonfinite field or changed protected source ends.')
    evidence = dict(before_xyz=x.copy(), actual_displacement=transported,
                    phase=phase, primary_profile=np.cos(phase),
                    secondary_profile=np.cos(2*phase), envelope=env,
                    crown_envelope=crown, lower_envelope=lower, middle_envelope=middle,
                    cap_fade=cap_fade, fixed_cap_mask=caps,
                    actual_body_radius=np.array(radius),
                    displacement_bound=np.array(bound))
    metadata = dict(applied=True, source_generation=2,
        injection='Actual G02_OVERLAP parent before WALL rail measurement and all G3 constructive events.',
        recipe=dict(recipe), actual_body_radius=radius, displacement_bound=bound,
        maximum_displacement=float(np.linalg.norm(transported, axis=1).max()),
        changed_controls=int(np.count_nonzero(np.linalg.norm(transported, axis=1))),
        fixed_end_controls=int(caps.sum()), fixed_ends_bitwise_exact=True,
        phase_scope='One material phase supplies large curved longitudinal flutes and same-direction smaller secondary folds.',
        reflection='Actual X/Y ID vector transport; seam normal components zero; no XYZ averaging.',
        topology_unchanged=True, microscopic_noise=False,
        self_intersection='NOT_CHECKED_VISUAL_PROTOTYPE', fabrication='NOT_CHECKED')
    return out, evidence, metadata


def candidate_recipes():
    rows = [
        ('C01', '긴 주름 다발', 1.15, 2, .34, .16, .22, .32, .16, .18, .06,
         [1., 1.02, 1.08, .94, .94, 1.32, 1.16, 1.]),
        ('C02', '굽은 부채와 귀환', 1.25, 2, .42, .30, .28, .46, .28, .24, .12,
         [1., 1.04, 1.12, .92, .96, 1.44, 1.24, 1.]),
        ('C03', '세 갈래 다발', 1.30, 3, .38, .20, .24, .38, .22, .26, .10,
         [1., 1.02, 1.10, .96, .94, 1.38, 1.20, 1.]),
        ('C04', '긴 줄기와 겹친 주두', 1.40, 2, .48, .34, .32, .50, .34, .28, .14,
         [1., 1.04, 1.14, .90, .94, 1.50, 1.30, 1.])]
    recipes = []
    for cid, label, length, order, strength, curvature, secondary, crown, ret, lower, tangent, radial in rows:
        recipes.append(dict(id=cid, label_ko=label, family='coherent_G2_bundle',
            length_scale=length, radius_scale_profile=radial,
            macro_fields={}, global_XY_reflection=True,
            bundled_fields=dict(order=order, strength=strength, curvature=curvature,
                secondary=secondary, crown_strength=crown, crown_return=ret,
                crown_centre=.75, crown_width=.17, lower_strength=lower,
                tangent_strength=tangent, bound_radius_fraction=.70),
            macro_injection_stage='G02_OVERLAP_BEFORE_WALL',
            genuine_early_replay=True, detail_added=False, fabrication_certified=False))
    # Different spatial extents deliberately replace a matrix of equal-size
    # repeated units. C04 also starts from an actual newly profiled G0 carrier.
    overrides = [
        dict(label_ko='거대 주두와 가는 줄기 · 상부 40%',
            radius_scale_profile=[1., .64, .62, .62, .70, 1.60, 1.40, 1.],
            spatial_scale_scope='One giant upper crown over approximately 40% of the height; long quiet slender stem.',
            bundled=dict(envelope_knots=[0., .06, .25, .45, .60, .72, .85, .95, 1.],
                envelope_values=[0., 0., .06, .12, .70, 1., 1., .30, 0.],
                crown_width=.25, crown_centre=.74, crown_strength=.58,
                crown_return=.18, lower_strength=.02, strength=.30)),
        dict(label_ko='길게 굽은 주름 다발 · 길이 70%', length_scale=1.35,
            radius_scale_profile=[1., .90, .92, .95, .92, 1.15, 1.08, 1.],
            spatial_scale_scope='Continuous large curved flutes over 70% height; secondary folds follow the same phase at a smaller scale.',
            bundled=dict(envelope_knots=[0., .06, .16, .30, .52, .70, .86, .96, 1.],
                envelope_values=[0., .10, .85, 1., 1., 1., .85, .10, 0.],
                strength=.48, curvature=.38, secondary=.34,
                crown_strength=.18, crown_width=.16, lower_strength=.10)),
        dict(label_ko='불균등 군집 · 큰 위 / 중간 아래 / 작은 중앙', length_scale=1.25,
            radius_scale_profile=[1., 1.10, 1.20, .60, .85, 1.50, 1.20, 1.],
            spatial_scale_scope='Three unequal clusters: broad/large upper, medium lower, narrow/small middle. No equal node widths.',
            bundled=dict(envelope_knots=[0., .06, .18, .28, .42, .49, .56, .67, .76, .90, 1.],
                envelope_values=[0., .10, .65, .50, .05, .40, .10, .60, 1., .30, 0.],
                crown_width=.22, crown_centre=.75, crown_strength=.50,
                lower_width=.12, lower_centre=.22, lower_strength=.32,
                middle_width=.05, middle_centre=.47, middle_strength=.14)),
        dict(label_ko='새 초기 캐리어 · 한 구간의 큰 귀환과 긴 줄기',
            seed_mode='fresh_profile_carrier',
            fresh_radius_profile=dict(knots=[0., .05, .20, .42, .58, .68, .78, .90, .97, 1.],
                values=[.62, .65, .55, .50, .55, 1.10, 1.55, 1.45, 1.05, 1.00]),
            radius_scale_profile=[1.]*8,
            spatial_scale_scope='New G0 profile removes the inherited two-bulb massing. One localized large crown return; long quiet lower context.',
            bundled=dict(envelope_knots=[0., .06, .25, .45, .60, .70, .80, .90, 1.],
                envelope_values=[0., 0., .02, .08, .20, 1., 1., .30, 0.],
                order=2, strength=.22, secondary=.20, crown_width=.11,
                crown_centre=.79, crown_strength=.65, crown_return=.65,
                lower_strength=.02))]
    for row, override in zip(recipes, overrides):
        values = dict(override)
        row['bundled_fields'].update(values.pop('bundled'))
        row.update(values)
        row['unchanged_branch_grammar'] = 'One canonical root and three canonical sidewalls; spatial extent and early carrier/folds differ, not the branch count.'
    return recipes
