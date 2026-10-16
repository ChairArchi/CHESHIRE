"""Reusable normal-relief deposition, independent of a particular column.

The Mandel input is a sampled finite radial boundary, not volumetric topology.
Physical material coordinates, measured shape weights, actual Tissue component
heights and flow protection are inputs; vertex/face IDs and project paths are
never part of a recipe. NumPy/SciPy are the existing ``task32`` extra.
"""
from dataclasses import asdict, dataclass
import hashlib

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.sparse import csr_matrix


CLASS_NAMES = ("calm", "weak_fold", "strong_fold", "bulge", "complex_candidate")


@dataclass(frozen=True)
class OrnamentRecipe:
    """Lengths are multiplied by length_scale, in the host's physical units."""

    length_scale: float = 1.0
    mandel_period: float = .60
    class_amplitudes: tuple = (.025, .025, .012, .020, .022)
    class_tissue_priorities: tuple = (.10, .25, .12, .65, .85)
    tissue_amplitude: float = .050
    valley_amplitude: float = .004
    normal_safety_ratio: float = .35
    orientation_decay: float = .5
    orientation_halo_decay: float = .9
    max_recovery_passes: int = 32
    freeze_boundary: bool = True
    chunk_size: int = 65536
    max_faces: int = 1_000_000

    def __post_init__(self):
        object.__setattr__(self, 'class_amplitudes', tuple(self.class_amplitudes))
        object.__setattr__(self, 'class_tissue_priorities', tuple(self.class_tissue_priorities))
        positive = (self.length_scale, self.mandel_period, self.normal_safety_ratio)
        nonnegative = (*self.class_amplitudes, self.tissue_amplitude, self.valley_amplitude)
        if len(self.class_amplitudes) != 5 or not np.isfinite((*positive, *nonnegative)).all():
            raise ValueError("Five finite class amplitudes and finite recipe lengths required.")
        if min(positive) <= 0 or min(nonnegative) < 0:
            raise ValueError("Positive scale/period/safety ratio and nonnegative amplitudes required.")
        if len(self.class_tissue_priorities) != 5 or not np.isfinite(self.class_tissue_priorities).all() or any(
                k < 0 or k > 1 for k in self.class_tissue_priorities):
            raise ValueError("Five Tissue class preferences in [0,1] required.")
        if not 0 < self.orientation_decay < 1 or not 0 < self.orientation_halo_decay <= 1:
            raise ValueError("Recovery decay must contract the desired increment.")
        if min(self.max_recovery_passes, self.chunk_size, self.max_faces) < 1:
            raise ValueError("Positive execution limits required.")
        if any(not isinstance(k, int) or isinstance(k, bool) for k in
               (self.max_recovery_passes, self.chunk_size, self.max_faces)):
            raise ValueError("Execution limits must be integers.")

    def to_dict(self):
        return asdict(self)


class MandelRadialProfile:
    """Periodic cubic interpolation of a caller-supplied finite bulb boundary.

    theta/phi/radius can be loaded from the existing MANDELBULB_PROFILE.npz.
    This class does not silently regenerate or filter that evidence.
    """

    def __init__(self, theta, phi, radius, *, provenance=None):
        theta, phi, radius = (np.asarray(a, dtype=float) for a in (theta, phi, radius))
        if theta.ndim != 1 or phi.ndim != 1 or radius.shape != (len(theta), len(phi)):
            raise ValueError("Matching angular axes and radial grid required.")
        if min(len(theta), len(phi)) < 4 or not all(np.isfinite(a).all() for a in (theta, phi, radius)):
            raise ValueError("Finite angular samples required.")
        if np.any(np.diff(theta) <= 0) or np.any(np.diff(phi) <= 0) or radius.min() <= 0:
            raise ValueError("Strictly increasing axes and positive radii required.")
        if not np.isclose(theta[0], 0) or not np.isclose(theta[-1], np.pi):
            raise ValueError("Latitude must span the two poles.")
        if phi[0] < 0 or phi[-1] >= 2 * np.pi:
            raise ValueError("Longitude must represent one period without a repeated endpoint.")
        if np.ptp(radius[0]) > 1e-10 or np.ptp(radius[-1]) > 1e-10:
            raise ValueError("Each pole must have a single radius.")
        self.centre = float((radius.min() + radius.max()) / 2)
        self.scale = float(np.ptp(radius) / 2)
        if self.scale <= 1e-10:
            raise ValueError("Constant radial profile has no ornament relief.")
        extended = np.concatenate((phi - 2 * np.pi, phi, phi + 2 * np.pi))
        self._spline = RectBivariateSpline(theta, extended, np.tile(radius, (1, 3)), s=0)
        digest = hashlib.sha256()
        for name, array in (("theta", theta), ("phi", phi), ("radius", radius)):
            canonical = np.ascontiguousarray(array, dtype='<f8')
            digest.update(f'{name}:{canonical.dtype.str}:{canonical.shape}'.encode('ascii'))
            digest.update(canonical.tobytes())
        self.sha256 = digest.hexdigest()
        self.radius_sha256 = hashlib.sha256(np.ascontiguousarray(radius).tobytes()).hexdigest()
        self.provenance = dict(provenance or {})

    def sample(self, coordinates, period):
        """coordinates[:,0:2] are continuous physical material/flow distances."""
        uv = np.asarray(coordinates, dtype=float)
        if uv.ndim != 2 or uv.shape[1] != 2 or not np.isfinite(uv).all() or not np.isfinite(period) or period <= 0:
            raise ValueError("Finite Nx2 physical coordinates and positive period required.")
        a, b = (2 * np.pi / period * uv).T
        theta = np.arccos(np.clip(np.cos(a), -1, 1))
        phi = np.mod(b + np.where(np.sin(a) < 0, np.pi, 0), 2 * np.pi)
        return np.clip((self._spline.ev(theta, phi) - self.centre) / self.scale, -1, 1)


def _weight(value, n, name):
    a = np.asarray(value, dtype=float)
    if a.shape != (n,) or not np.isfinite(a).all() or np.any((a < 0) | (a > 1)):
        raise ValueError(f"{name} must be a finite N-vector in [0,1].")
    return a


def _mesh(xyz, quads, recipe):
    x = np.asarray(xyz, dtype=float)
    q0 = np.asarray(quads)
    if x.ndim != 2 or x.shape[1] != 3 or not np.isfinite(x).all():
        raise ValueError("Finite Nx3 host geometry required.")
    if q0.ndim != 2 or q0.shape[1] != 4 or q0.dtype.kind not in "iu" or not len(q0):
        raise ValueError("Nonempty integer Mx4 quad topology required.")
    if len(q0) > recipe.max_faces:
        raise ValueError("Host exceeds the explicit face budget.")
    q = q0.astype(np.int64, copy=False)
    if q.min() < 0 or q.max() >= len(x) or np.any(np.diff(np.sort(q, axis=1), axis=1) == 0):
        raise ValueError("Quad references must be valid and distinct.")
    return x, q


def host_normals(xyz, quads, *, chunk_size=65536):
    """Area-weighted normals of the actual quad-centroid fan geometry."""
    acc = np.zeros_like(xyz, dtype=float)
    for first in range(0, len(quads), chunk_size):
        q = quads[first:first + chunk_size]
        p = xyz[q]
        c = p.mean(axis=1)
        fan = np.cross(p - c[:, None], np.roll(p, -1, axis=1) - c[:, None])
        if np.any(np.linalg.norm(fan, axis=2) <= 1e-30):
            raise ValueError("Degenerate native host fan.")
        face = fan.sum(axis=1)
        np.add.at(acc, q.ravel(), np.repeat(face, 4, axis=0))
    length = np.linalg.norm(acc, axis=1)
    if np.any(length <= 1e-30):
        raise ValueError("Unused vertex or degenerate incident host normal.")
    return acc / length[:, None]


def _topology(x, q, normals):
    edges = np.sort(np.stack((q, np.roll(q, -1, axis=1)), axis=2).reshape(-1, 2), axis=1)
    edges, count = np.unique(edges, axis=0, return_counts=True)
    if np.any(count > 2):
        raise ValueError("Nonmanifold host edge.")
    edge_length = np.linalg.norm(x[edges[:, 1]] - x[edges[:, 0]], axis=1)
    change = np.linalg.norm(normals[edges[:, 1]] - normals[edges[:, 0]], axis=1)
    shortest = np.full(len(x), np.inf)
    variation = np.zeros(len(x))
    for k in range(2):
        np.minimum.at(shortest, edges[:, k], edge_length)
        np.maximum.at(variation, edges[:, k], change)
    rows = np.r_[edges[:, 0], edges[:, 1]]
    cols = np.r_[edges[:, 1], edges[:, 0]]
    graph = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(len(x), len(x)))
    boundary = np.zeros(len(x), dtype=bool)
    boundary[edges[count == 1].ravel()] = True
    return shortest, variation, graph, boundary


def _bad_faces(x, q, reference, chunk):
    bad = np.zeros(len(q), dtype=bool)
    for first in range(0, len(q), chunk):
        ids = q[first:first + chunk]
        p, r = x[ids], reference[ids]
        pc, rc = p.mean(axis=1), r.mean(axis=1)
        a = np.cross(p - pc[:, None], np.roll(p, -1, axis=1) - pc[:, None])
        b = np.cross(r - rc[:, None], np.roll(r, -1, axis=1) - rc[:, None])
        dot = np.einsum("fki,fki->fk", a, b)
        bad[first:first + len(ids)] = np.any((dot <= 0) | ~np.isfinite(dot), axis=1)
    return bad


def apply_adaptive_ornament(xyz, quads, *, shape_weights, pattern_coordinates,
                            profile, recipe=None, tissue_height=None,
                            tissue_priority=None, flow_protection=None,
                            cap_mask=None, valley_weight=None):
    """Return a new mesh's vertices and reproducible fields, without mutation.

    shape_weights: Nx5 normalized continuous SOURCE class weights.
    tissue_height: UNWEIGHTED normalized [0,1] actual Tissue component height.
    tissue_priority: blend [0,1], applied exactly once. If height is provided
      and priority omitted, derive it from measured shape weights and recipe.
      An already weighted
      Tissue delta must be converted by its adapter, never silently weighted twice.
    flow_protection: [0,1], where 1 preserves incoming XYZ bit for bit.
    caps/boundaries also preserve incoming XYZ. Recovery only contracts this
    new increment. No blur, mesh joining, holes or physical inflation is implied.
    """
    recipe = recipe or OrnamentRecipe()
    x, q = _mesh(xyz, quads, recipe)
    n = len(x)
    weights = np.asarray(shape_weights, dtype=float)
    if weights.shape != (n, 5) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("Finite nonnegative Nx5 shape weights required.")
    if not np.allclose(weights.sum(axis=1), 1, atol=1e-9, rtol=0):
        raise ValueError("Each shape-weight row must sum to one.")
    uv = np.asarray(pattern_coordinates, dtype=float)
    if uv.shape != (n, 2) or not np.isfinite(uv).all():
        raise ValueError("Physical material coordinates must match the host.")
    automatic_tw = (weights @ np.asarray(recipe.class_tissue_priorities)
                    if tissue_height is not None else np.zeros(n))
    tw = _weight(automatic_tw if tissue_priority is None else tissue_priority, n, "Tissue priority")
    th = _weight(np.zeros(n) if tissue_height is None else tissue_height, n, "Tissue height")
    if tissue_height is None and np.any(tw):
        raise ValueError("Nonzero Tissue priority requires actual Tissue component heights.")
    flow = _weight(np.zeros(n) if flow_protection is None else flow_protection, n, "Flow protection")
    valley = _weight(np.zeros(n) if valley_weight is None else valley_weight, n, "Valley weight")
    caps = np.zeros(n, dtype=bool) if cap_mask is None else np.asarray(cap_mask, dtype=bool)
    if caps.shape != (n,):
        raise ValueError("Cap mask must match host vertices.")
    normals = host_normals(x, q, chunk_size=recipe.chunk_size)
    shortest, variation, graph, boundary = _topology(x, q, normals)
    safety = recipe.normal_safety_ratio * shortest / np.maximum(variation, 1e-12)
    amplitude = weights @ (np.asarray(recipe.class_amplitudes) * recipe.length_scale)
    amplitude = amplitude * (1 - valley) + recipe.valley_amplitude * recipe.length_scale * valley
    amplitude = np.minimum(amplitude, safety)
    tissue_amp = np.minimum(recipe.tissue_amplitude * recipe.length_scale, safety)
    raw = profile.sample(uv, recipe.mandel_period * recipe.length_scale)
    source_height = amplitude * raw
    height = (source_height * (1 - tw) + tissue_amp * th * tw) * (1 - flow)
    fixed = caps | (flow == 1)
    if recipe.freeze_boundary:
        fixed |= boundary
    height[fixed] = 0
    increment = normals * height[:, None]
    gain = np.ones(n)
    recovery = []
    for iteration in range(recipe.max_recovery_passes):
        output = x + increment * gain[:, None]
        output[fixed] = x[fixed]
        bad = _bad_faces(output, q, x, recipe.chunk_size)
        recovery.append(int(bad.sum()))
        if not bad.any():
            break
        hit = np.zeros(n, dtype=bool)
        hit[q[bad].ravel()] = True
        halo = (graph @ hit.astype(np.float32) > 0) & ~hit
        gain[hit] *= recipe.orientation_decay
        gain[halo] *= recipe.orientation_halo_decay
    else:
        raise ValueError("Local orientation recovery exhausted; no result accepted.")
    return dict(xyz=output, normals=normals, source_height=source_height,
                desired_height=height, actual_height=height * gain,
                local_gain=gain, safety_cap=safety, fixed_mask=fixed,
                shape_weights=weights.copy(), tissue_priority=tw.copy(),
                recipe=recipe.to_dict(), profile_sha256=profile.sha256,
                recovery_bad_face_counts=recovery,
                quality=dict(all_finite=bool(np.isfinite(output).all()),
                             reversed_native_fan_faces=0,
                             fixed_coordinates_exact=bool(np.array_equal(output[fixed], x[fixed])),
                             unchanged_quad_topology=True,
                             self_intersection_checked=False))
