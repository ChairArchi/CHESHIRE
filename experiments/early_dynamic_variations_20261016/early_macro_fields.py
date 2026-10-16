"""Material-coordinate macro deformations for an actual early column parent.

This module changes coordinates, never topology or the inherited chart. Inputs
are Z-up, centred on the X/Y reflection planes, with chart columns [t, X, Y].
It neither imports project states nor evaluates a late ornament/height texture.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from hashlib import sha256
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class MacroRecipe:
    family: str = "overlap"
    nodes: int = 4
    node_centres: tuple[float, ...] = ()
    node_width: float = 0.16
    node_strengths: tuple[float, ...] = ()
    phase: float = 0.0
    phase_advance: float = 0.65
    angular_order: int = 2
    radial_strength: float = 0.30
    axial_strength: float = 0.30
    tangent_strength: float = 0.08
    hierarchy: float = 0.35
    turns: float = 0.8
    return_bias: float = 0.15
    cap_fade: float = 0.075
    displacement_bound: float = 0.60
    length_scale: float = 1.0
    enabled: bool = True


def _digest(a):
    return sha256(np.ascontiguousarray(a).view(np.uint8)).hexdigest()


def _smooth(a):
    x = np.clip(a, 0.0, 1.0)
    return x*x*x*(10.0 + x*(-15.0 + 6.0*x))


def _recipe(recipe):
    if isinstance(recipe, MacroRecipe):
        result = recipe
    elif isinstance(recipe, Mapping):
        unknown = set(recipe) - {f.name for f in fields(MacroRecipe)}
        if unknown:
            raise ValueError("Unknown macro recipe keys: " + ", ".join(sorted(unknown)))
        result = MacroRecipe(**recipe)
    else:
        raise TypeError("recipe must be a mapping or MacroRecipe")
    if result.family not in ("overlap", "fan", "mirrored_twist"):
        raise ValueError("Unknown macro family")
    if result.nodes not in (3, 4, 5, 6):
        raise ValueError("Macro envelopes require 3 to 6 nodes")
    if not 1 <= result.angular_order <= 5:
        raise ValueError("angular_order must be 1..5")
    if not 0.02 <= result.node_width <= 0.40:
        raise ValueError("node_width is a material-t halfwidth, 0.02..0.40")
    if not 0.01 <= result.cap_fade <= 0.25:
        raise ValueError("cap_fade must be 0.01..0.25")
    if not 1.0 <= result.length_scale <= 1.5:
        raise ValueError("length_scale must be 1..1.5")
    if not 0 < result.displacement_bound <= 1.0:
        raise ValueError("displacement_bound must be a positive radius fraction <=1")
    for name in ("radial_strength", "axial_strength", "tangent_strength"):
        if not 0 <= getattr(result, name) <= 1:
            raise ValueError(name + " must be a radius fraction in [0,1]")
    scalars = [v for v in asdict(result).values() if isinstance(v, (float, int))]
    if not np.isfinite(scalars).all():
        raise ValueError("Nonfinite macro configuration")
    return result


def _transport(delta, pairs):
    """Transport displacements only; never average or repair the parent XYZ."""
    if pairs is None:
        return delta, {"mode": "analytic_reflection_equivariant_field"}
    n = len(delta)
    if isinstance(pairs, Mapping):
        px = pairs.get("mirror_x_vertex_pairs", pairs.get("X"))
        py = pairs.get("mirror_y_vertex_pairs", pairs.get("Y"))
    else:
        px, py = pairs
    px, py = np.asarray(px, np.int64), np.asarray(py, np.int64)
    ids = np.arange(n)
    if (px.shape != (n,) or py.shape != (n,) or
            np.any(px < 0) or np.any(py < 0) or
            np.any(px >= n) or np.any(py >= n)):
        raise ValueError("Reflection maps must contain one valid ID per input vertex")
    if not (np.array_equal(px[px], ids) and np.array_equal(py[py], ids)
            and np.array_equal(px[py], py[px])):
        raise ValueError("Reflection maps must be commuting involutions")
    xy = px[py]
    rep = np.minimum.reduce((ids, px, py, xy))
    out = delta[rep].copy()
    flip_x = (px[rep] == ids) | (xy[rep] == ids)
    flip_y = (py[rep] == ids) | (xy[rep] == ids)
    # Fixed-plane duplicates have ambiguous signs; their normal component is 0.
    out[flip_x, 0] *= -1
    out[flip_y, 1] *= -1
    out[px == ids, 0] = 0
    out[py == ids, 1] = 0
    return out, dict(mode="canonical_orbit_displacement_transport",
        representative_sha256=_digest(rep), X_sha256=_digest(px), Y_sha256=_digest(py),
        parent_coordinates_averaged=False)


def apply_macro_field(xyz, chart, recipe, *, roles=None, stage=3,
                      protection=None, vertex_pairs=None):
    """Return (new_xyz, evidence, metadata), with caller arrays unchanged.

    radius fractions are measured from this actual parent's median radius.
    ``protection`` is an optional vertex-aligned [0,1] immobility weight; it
    suppresses *both* standalone stretching and macro displacement. ``roles``
    may provide a smooth ``vertex_gain`` or descriptive ``face_role_counts``.
    Face-aligned integer labels are descriptive, never reinterpreted as vertex
    masks. Empty recipe and enabled=False are bit-exact coordinate no-ops.

    Length scaling is available for standalone use. Replay recipes put length
    scaling at G0 and leave this module's length_scale at 1 to apply it once.
    """
    x = np.asarray(xyz)
    c = np.asarray(chart)
    if x.ndim != 2 or x.shape[1] != 3 or c.shape != x.shape:
        raise ValueError("xyz and chart must both have shape (N,3)")
    if x.dtype.kind != "f" or not np.isfinite(x).all() or not np.isfinite(c).all():
        raise ValueError("Finite floating XYZ and finite chart are required")
    if not len(x):
        raise ValueError("Empty early parent")
    if stage not in (1, 2, 3, "G01_ANCESTRY", "G02_OVERLAP", "G03_SIDEWALL"):
        raise ValueError("Only actual early G1/G2/G3 parents are supported")
    disabled = recipe is None or (isinstance(recipe, Mapping) and not recipe)
    cfg = _recipe({"enabled": False} if disabled else recipe)
    zeros = np.zeros_like(x, dtype=np.float64)
    if disabled or not cfg.enabled:
        return x.copy(), {"total_displacement": zeros}, dict(
            active=False, exact_coordinate_noop=True, stage=stage,
            input_xyz_sha256=_digest(x), output_xyz_sha256=_digest(x),
            topology_changed=False, chart_changed=False)
    t = np.asarray(c[:, 0], np.float64)
    if t.min() < -1e-10 or t.max() > 1+1e-10:
        raise ValueError("Inherited material t must already be normalized to [0,1]")
    t = np.clip(t, 0, 1)
    centres = np.asarray(cfg.node_centres or np.linspace(0.14, 0.86, cfg.nodes), float)
    strength = np.asarray(cfg.node_strengths or np.ones(cfg.nodes), float)
    if (centres.shape != (cfg.nodes,) or strength.shape != (cfg.nodes,)
            or not np.isfinite(centres).all() or not np.isfinite(strength).all()
            or np.any(np.diff(centres) <= 0) or centres[0] <= 0 or centres[-1] >= 1
            or np.any(strength <= 0) or np.any(strength > 2)):
        raise ValueError("Ordered interior node centres and positive finite strengths required")
    radius = np.hypot(x[:, 0], x[:, 1])
    positive = radius[radius > max(float(radius.max()), 1)*1e-12]
    if not len(positive):
        raise ValueError("The early parent has no nonzero transverse radius")
    R = float(np.median(positive))
    height = float(np.ptp(x[:, 2]))
    if height <= 0:
        raise ValueError("The early parent must have nonzero axial extent")
    theta = np.arctan2(np.abs(c[:, 2]), np.abs(c[:, 1]))
    # Compact degree-six pulses and quintic end fades have zero first/second
    # derivatives where they join zero. No random field or geometric hashing.
    u = (t[:, None]-centres[None, :])/cfg.node_width
    pulse = np.maximum(0.0, 1-u*u)**3 * strength[None, :]
    pulse /= max(float(pulse.sum(axis=1).max()), 1.0)
    fade = _smooth(t/cfg.cap_fade)*_smooth((1-t)/cfg.cap_fade)
    seam = np.sin(2*theta)**4
    radial, tangent, axial = (np.zeros(len(x)) for _ in range(3))
    for i in range(cfg.nodes):
        phase = cfg.phase + i*cfg.phase_advance
        order = min(5, cfg.angular_order + (i % 2 if cfg.family == "fan" else 0))
        angle = 2*order*theta
        if cfg.family == "mirrored_twist":
            phase = phase + 2*np.pi*cfg.turns*(t-centres[i])
        # Phase is confined to the canonical material quadrant. This is not
        # a global chiral rotation; reflection creates counter-handed sectors.
        angular = np.cos(angle)*np.cos(phase) + seam*np.sin(angle)*np.sin(phase)
        p = pulse[:, i]
        if cfg.family == "overlap":
            radial += p*(0.22 + angular)
            axial += p*np.sin(np.pi*np.clip(u[:, i], -1, 1))*(0.65+0.35*angular)
            axial += cfg.return_bias*p*((-1.0)**i)*angular
            tangent += p*seam*np.sin(phase+2*theta)
        elif cfg.family == "fan":
            tier = 1+cfg.hierarchy*(2*i/max(cfg.nodes-1, 1)-1)
            radial += p*tier*(0.65*angular+0.35*np.cos(2*theta))
            axial += p*((-1.0)**i)*(0.4+0.6*angular)
            tangent += p*tier*seam*np.sin(2*theta)*np.cos(phase)
        else:
            radial += p*angular
            tangent += p*seam*np.sin(angle-phase)
            axial += p*np.sin(np.pi*np.clip(u[:, i], -1, 1)+phase)*0.65
    denom = np.maximum(radius, R*1e-12)
    rx, ry = x[:, 0]/denom, x[:, 1]/denom
    tx = -np.sign(x[:, 0])*np.abs(x[:, 1])/denom
    ty = np.sign(x[:, 1])*np.abs(x[:, 0])/denom
    raw = np.column_stack((cfg.radial_strength*radial*rx + cfg.tangent_strength*tangent*tx,
                           cfg.radial_strength*radial*ry + cfg.tangent_strength*tangent*ty,
                           cfg.axial_strength*axial))*R*fade[:, None]
    gain = np.ones(len(x))
    role_description = {}
    if isinstance(roles, Mapping):
        role_description = {k: v for k, v in roles.items() if k != "vertex_gain"}
        if "vertex_gain" in roles:
            gain = np.asarray(roles["vertex_gain"], float)
    elif roles is not None:
        labels, counts = np.unique(np.asarray(roles), return_counts=True)
        role_description = {"descriptive_role_counts": {str(k): int(v) for k, v in zip(labels, counts)}}
    if gain.shape != (len(x),) or not np.isfinite(gain).all() or np.any(gain < 0) or np.any(gain > 1):
        raise ValueError("vertex_gain must have one finite [0,1] weight per vertex")
    protect = np.zeros(len(x)) if protection is None else np.asarray(protection, float)
    if protect.shape != (len(x),) or not np.isfinite(protect).all() or np.any(protect < 0) or np.any(protect > 1):
        raise ValueError("protection must have one finite [0,1] weight per vertex")
    raw *= (gain*(1-protect))[:, None]
    magnitude = np.linalg.norm(raw, axis=1)
    bound = cfg.displacement_bound*R
    ratio = magnitude/bound
    limiter = np.ones(len(x));nonzero = ratio > 0
    limiter[nonzero] = np.tanh(ratio[nonzero])/ratio[nonzero]
    macro = raw*limiter[:, None]
    stretch = zeros.copy()
    stretch[:, 2] = (cfg.length_scale-1)*(x[:, 2]-float(x[:, 2].min()))*(1-protect)
    delta, transport = _transport(macro+stretch, vertex_pairs)
    # Protection is a declared input contract. It must itself be reflection-
    # invariant if orbit transport is requested; never silently unprotect it.
    if np.any(delta[protect == 1] != 0):
        raise ValueError("Reflection transport conflicts with the protection mask")
    output = x.astype(np.float64, copy=True)+delta
    if not np.isfinite(output).all():
        raise ValueError("Nonfinite deformed early coordinates")
    ev = dict(total_displacement=delta, raw_macro_displacement=raw,
        bounded_macro_displacement=macro, standalone_length_displacement=stretch,
        material_t=t, canonical_material_theta=theta, node_weights=pulse,
        cap_fade=fade, displacement_limiter=limiter, protection=protect)
    meta = dict(active=True, exact_coordinate_noop=False, stage=stage, recipe=asdict(cfg),
        material_chart_scope="Inherited t and angular ancestry; chart unchanged",
        actual_parent_radius=R, actual_parent_height=height,
        radius_measure="median of nonaxis actual input XY radii", model_units="input XYZ units",
        local_displacement_bound=bound, maximum_raw_macro_displacement=float(magnitude.max()),
        maximum_bounded_macro_displacement=float(np.linalg.norm(macro, axis=1).max()),
        maximum_total_displacement=float(np.linalg.norm(delta, axis=1).max()),
        requested_length_scale=cfg.length_scale,
        output_axial_extent=float(np.ptp(output[:, 2])),
        standalone_length_is_exempt_from_local_macro_bound=True,
        replay_length_should_be_applied_at_G0_once=True,
        changed_vertices=int(np.any(delta != 0, axis=1).sum()),
        zero_macro_end_vertices=int((fade == 0).sum()),
        cap_policy="C2 local macro fade at material ends; standalone length changes axial span",
        global_XY_reflection_equivariant=True, global_chiral_twist=False,
        twist_semantics="Mirrored canonical-quadrant countertwist", reflection_transport=transport,
        roles=role_description, topology_changed=False, chart_changed=False,
        late_surface_ornament=False, random_noise=False,
        input_xyz_sha256=_digest(x), output_xyz_sha256=_digest(output),
        displacement_sha256=_digest(delta), self_intersections_checked=False,
        replay_and_geometry_QA_required=True)
    return output, ev, meta


def apply_early_macro_fields(xyz, chart, recipe, **kwargs):
    """Compatibility wrapper with explicit (xyz, metadata, evidence) order."""
    output, evidence, metadata = apply_macro_field(xyz, chart, recipe, **kwargs)
    return output, metadata, evidence
