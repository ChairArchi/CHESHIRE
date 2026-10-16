"""Finite Mandelbulb vector volume attached to an actual curved parent sheet.

Only the controller lookup is interpolated/pooled. The input/output carrier
is never replaced by the controller surface. Actual stage XYZ relative to
that curved surface supplies the normal coordinate and therefore feedback.
"""
from pathlib import Path
import importlib.util
from time import perf_counter

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates, spline_filter


HERE = Path(__file__).resolve().parent
FRAME_PATH = HERE/'parent_mandel_formation.py'
_spec = importlib.util.spec_from_file_location('attached_volume_parent_frame', FRAME_PATH)
frame = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(frame)
GRID_SHAPE = (33, 97, 17)
POWER = 8
ITERATIONS = 8


def helper_paths():
    return [FRAME_PATH]


def _array(parent, key, fallback=None):
    if key in parent:
        return np.asarray(parent[key], dtype=float)
    if fallback is not None:
        return np.asarray(fallback, dtype=float)
    raise ValueError('Missing measured parent field: '+key)


def _smooth(value):
    s = np.clip(value, 0., 1.)
    return s*s*s*(10.-15.*s+6.*s*s)


class _ParentGeometry:
    def __init__(self, parent):
        self.parent = parent
        self.family = int(np.asarray(parent.get('family_id', 4)))
        self.parameter = _array(parent, 'parameter')
        if (self.parameter.ndim != 1 or len(self.parameter) < 5
                or not np.all(np.diff(self.parameter) > 0.)):
            raise ValueError('Ordered measured theta stations required.')
        self.cross = _array(parent, 'formation_shoulder_cross')
        self.arc = _array(parent, 'formation_shoulder_arc')
        surface = None
        for name in ('controller_shoulder_xyz', 'actual_shoulder_xyz', 'shoulder_xyz'):
            if name in parent:
                surface = _array(parent, name)
                break
        if surface is None:
            raise ValueError('Actual curved native shoulder XYZ required; no centreline-plane substitute.')
        rows = len(self.parameter)
        if surface.ndim == 3 and surface.shape[0] != rows and surface.shape[1] == rows:
            surface = surface.transpose(1, 0, 2)
        if self.cross.ndim == 2 and self.cross.shape[0] != rows and self.cross.shape[1] == rows:
            self.cross = self.cross.T
        if self.arc.ndim == 2 and self.arc.shape[0] != rows and self.arc.shape[1] == rows:
            self.arc = self.arc.T
        if (self.cross.ndim != 2 or self.cross.shape[0] != rows
                or self.arc.shape != self.cross.shape or surface.shape != (*self.cross.shape, 3)
                or not np.all(np.diff(self.cross, axis=1) > 0.)
                or not np.all(np.diff(self.arc, axis=1) >= 0.)
                or np.any(self.arc[:, -1]-self.arc[:, 0] <= 0.)):
            raise ValueError('Ordered actual shoulder material grid, physical arc and XYZ required.')
        self.surface = surface
        self.width = _array(parent, 'parent_physical_width')
        self.depth = _array(parent, 'parent_observed_chord_depth')
        if (self.width.shape != (rows,) or self.depth.shape != (rows,)
                or np.any(self.width <= 0.) or np.any(self.depth < 0.)):
            raise ValueError('Positive measured width and nonnegative measured depth required.')
        self.curve, self.tangent, self.across, self.normal, self.flow = frame.frames(parent)
        for value in (self.parameter, self.cross, self.arc, self.surface, self.width,
                      self.depth, self.tangent, self.across, self.normal, self.flow):
            if not np.isfinite(value).all():
                raise ValueError('Finite actual parent geometry required.')

    def sample(self, theta, cross):
        """Interpolate actual native reference XYZ, never flatten its profile."""
        p = self.parameter
        lower = np.clip(np.searchsorted(p, theta, side='right')-1, 0, len(p)-2)
        upper = lower+1
        alpha = (theta-p[lower])/(p[upper]-p[lower])
        surface = np.zeros((len(theta), 3))
        fraction = np.zeros(len(theta))
        for row in range(len(p)):
            for index, weight in ((lower, 1.-alpha), (upper, alpha)):
                chosen = np.flatnonzero(index == row)
                if not len(chosen):
                    continue
                query = cross[chosen]
                for axis in range(3):
                    surface[chosen, axis] += weight[chosen]*np.interp(
                        query, self.cross[row], self.surface[row, :, axis])
                arc = np.interp(query, self.cross[row], self.arc[row])-self.arc[row, 0]
                fraction[chosen] += weight[chosen]*arc/(self.arc[row, -1]-self.arc[row, 0])
        tangent = frame.unit(frame.interp_vector(theta, p, self.tangent))
        across = frame.interp_vector(theta, p, self.across)
        across = frame.unit(across-tangent*np.einsum('ij,ij->i', across, tangent)[:, None])
        normal = frame.unit(np.cross(tangent, across))
        width = np.interp(theta, p, self.width)
        depth = np.interp(theta, p, self.depth)
        flow = np.interp(theta, p, self.flow)/self.flow[-1]
        return surface, tangent, across, normal, width, depth, flow, fraction


class ParentAttachedVolume:
    def __init__(self, geometry, events, ownership, axes, coefficients, metadata):
        self.geometry = geometry
        self.events = events
        self.ownership = ownership
        self.axes = axes
        self.coefficients = coefficients
        self.metadata = metadata
        # Caller owns actual SOURCE/attached-root eligibility. The subdivision
        # adapter calls evaluate with three arguments, so root may bind this
        # callback once before running it. Explicit eligible overrides it.
        self.eligibility = None
        self.stage_statistics = metadata['stage_statistics']

    def evaluate(self, xyz, chart, stage, eligible=None):
        """Return an Nx3 physical vector; zero outside owned parent support.

        eligible: boolean array, or callback(xyz,chart,stage)->boolean array.
        It is independent of material ownership and must come from actual
        topology. No nearest-point eligibility inference is performed here.
        """
        xyz, chart = np.asarray(xyz), np.asarray(chart)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or chart.shape != xyz.shape:
            raise ValueError('Matching actual Nx3 stage XYZ and material chart required.')
        output = np.zeros(xyz.shape, dtype=float)
        theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
        cross = chart[:, 0]
        geometry = self.geometry
        p = geometry.parameter
        chosen = ((theta > p[0]) & (theta < p[-1]) & np.isfinite(theta) & np.isfinite(cross))
        eligibility = self.eligibility if eligible is None else eligible
        if eligibility is not None:
            mask = eligibility(xyz, chart, stage) if callable(eligibility) else eligibility
            mask = np.asarray(mask)
            if mask.shape != (len(xyz),) or mask.dtype.kind != 'b':
                raise ValueError('Caller eligibility must be an actual boolean stage-control mask.')
            chosen &= mask
        # This cheap material envelope precedes reference/volume interpolation.
        lo = np.interp(theta, p, geometry.cross[:, 0])
        hi = np.interp(theta, p, geometry.cross[:, -1])
        chosen &= (cross > lo) & (cross < hi)
        ids = np.flatnonzero(chosen)
        record = dict(stage=str(stage), queried_controls=len(xyz), envelope_controls=len(ids),
                      parent_supported_controls=0, volume_supported_controls=0, moved_controls=0,
                      caller_topology_eligibility_bound=eligibility is not None)
        if not len(ids):
            self.stage_statistics.append(record)
            return output
        surface, tangent, across, normal, width, depth, flow, fraction = geometry.sample(theta[ids], cross[ids])
        inside = (fraction > .25) & (fraction < .75)
        ids = ids[inside]
        surface, tangent, across, normal = (v[inside] for v in (surface, tangent, across, normal))
        width, depth, flow, fraction = (v[inside] for v in (width, depth, flow, fraction))
        record['parent_supported_controls'] = len(ids)
        if not len(ids):
            self.stage_statistics.append(record)
            return output
        # Mirror by inherited material identity, not sign(current world XYZ):
        # an intentional folded sheet can cross its reflection plane.
        signs = np.ones((len(ids), 3))
        signs[:, 0] = np.where(chart[ids, 1] < 0., -1., 1.)
        signs[:, 1] = np.where(chart[ids, 2] < 0., -1., 1.)
        current = xyz[ids]*signs
        if not np.isfinite(current).all():
            raise ValueError('Finite eligible actual stage positions required.')
        nscale = np.minimum(np.maximum(.65*depth, .02*width), .20*width)
        cap = np.minimum(.35*depth, .08*width)
        u = (fraction-.25)/.50
        qn = .65+np.einsum('ij,ij->i', current-surface, normal)/nscale
        qt, qb = .8*(flow-.5), 2.2*(u-.5)
        coordinates = np.vstack([qt, qb, qn])
        volume_inside = np.ones(len(ids), bool)
        for axis, values in zip(self.axes, coordinates):
            volume_inside &= (values >= axis[0]) & (values <= axis[-1])
        indices = np.vstack([(values-axis[0])/(axis[1]-axis[0])
                             for axis, values in zip(self.axes, coordinates)])
        normalized = np.zeros((len(ids), 2))
        for component in range(2):
            normalized[volume_inside, component] = map_coordinates(
                self.coefficients[..., component], indices[:, volume_inside],
                order=3, mode='constant', cval=0., prefilter=False)
        weight = (_smooth(flow/.12)*_smooth((1.-flow)/.12)
                  *_smooth(u/.12)*_smooth((1.-u)/.12))
        # Compact C2 fade meets the exact zero beyond the tabulated N slab.
        nlo, nhi = self.axes[2][0], self.axes[2][-1]
        weight *= _smooth((qn-nlo)/(.12*(nhi-nlo)))*_smooth((nhi-qn)/(.12*(nhi-nlo)))
        partitions = self.ownership.partition_weights(theta[ids], cross[ids], self.events)
        if geometry.family >= len(partitions):
            raise ValueError('Actual family index missing from original event ownership bank.')
        weight *= partitions[geometry.family]
        move = (normalized[:, 0, None]*(.25*width[:, None])*across
                +normalized[:, 1, None]*nscale[:, None]*normal)
        norm = np.linalg.norm(move, axis=1)
        ratio = np.divide(norm, cap, out=np.full_like(norm, np.inf), where=cap > 0.)
        move *= np.divide(1., np.sqrt(1.+ratio*ratio), out=np.zeros_like(norm),
                          where=np.isfinite(ratio))[:, None]
        move *= weight[:, None]
        move *= signs
        move[np.abs(chart[ids, 1]) < 1e-12, 0] = 0.
        move[np.abs(chart[ids, 2]) < 1e-12, 1] = 0.
        if not np.isfinite(move).all():
            raise ValueError('Nonfinite parent-attached finite-volume response.')
        output[ids] = move
        magnitude = np.linalg.norm(move, axis=1)
        record.update(volume_supported_controls=int(volume_inside.sum()),
                      moved_controls=int(np.count_nonzero(magnitude > 1e-12)),
                      query_N_quantiles=np.quantile(qn, [0., .1, .5, .9, 1.]).tolist(),
                      maximum_physical_desired_vector=float(magnitude.max(initial=0.)),
                      maximum_nominal_cap=float(cap.max(initial=0.)),
                      maximum_local_T_error=float(np.abs(np.einsum('ij,ij->i', move*signs, tangent)).max(initial=0.)))
        self.stage_statistics.append(record)
        return output

    __call__ = evaluate


def build(parent, events, bulb, ownership):
    """Build one reusable finite vector volume; no source geometry is changed."""
    started = perf_counter()
    geometry = _ParentGeometry(parent)
    axes = (np.linspace(-.4, .4, GRID_SHAPE[0]),
            np.linspace(-1.1, 1.1, GRID_SHAPE[1]),
            np.linspace(.15, 1.15, GRID_SHAPE[2]))
    mesh = np.meshgrid(*axes, indexing='ij')
    queries = np.column_stack([a.ravel() for a in mesh])
    print('PARENT_ATTACHED_VOLUME: finite power8 membership/ray field grid', len(queries), flush=True)
    response, response_metadata = bulb.respond(queries, power=POWER, iterations=ITERATIONS)
    response = np.asarray(response)
    if response.shape != queries.shape or not np.isfinite(response).all():
        raise ValueError('Finite vector-grid response required.')
    if np.any(response[:, 0] != 0.):
        raise ValueError('Parent-longitudinal desired motion must be zero.')
    raw = response[:, 1:].reshape(*GRID_SHAPE, 2)
    median_width = float(np.median(geometry.width))
    nscale = np.minimum(np.maximum(.65*geometry.depth, .02*geometry.width), .20*geometry.width)
    sigma_physical = median_width/(8.*POWER)
    physical_per_q = (float(geometry.flow[-1])/.8, .25*median_width, float(np.median(nscale)))
    sigma = tuple(max(1., sigma_physical/(scale*(axis[1]-axis[0])))
                  for scale, axis in zip(physical_per_q, axes))
    filtered = np.empty_like(raw)
    coefficients = np.empty_like(raw)
    for component in range(2):
        # Exterior grid samples are true zeros before this explicit bandlimit.
        # Gaussian smoothing may spread nonzero response across that finite
        # boundary; no exact inside/outside classification is claimed after it.
        filtered[..., component] = gaussian_filter(raw[..., component], sigma=sigma,
                                                    mode='constant', cval=0.)
        coefficients[..., component] = spline_filter(filtered[..., component], order=3, mode='mirror')
    metadata = dict(
        implementation='CURVED_PARENT_ATTACHED_FINITE_MANDELBULB_C2_VECTOR_VOLUME_V1',
        family_id=geometry.family, power=POWER, iterations=ITERATIONS,
        grid_shape=list(GRID_SHAPE), normalized_grid_bounds=[[float(a[0]), float(a[-1])] for a in axes],
        response=response_metadata,
        normal_coordinate='qN=.65+dot(actual_current_stage_XYZ-reference_actual_curved_parent_surface(theta,material_t),pooled_actual_parent_N)/Nscale',
        tangent_coordinate='qT=.8*(actual parent physical flow arc fraction-.5)',
        across_coordinate='qB=2.2*((actual shoulder arc fraction-.25)/.50-.5); only .25<fraction<.75',
        reference_surface='Interpolate complete actual measured native shoulder XYZ profiles first across material t and then theta. No centreline-plane replacement, world radial profile, or source XYZ fairing.',
        frame='Existing pooled measured actual-parent T/B/N, reorthonormalized at each query; directions are fixed to current input parent, actual stage XYZ supplies N feedback.',
        physical_B_scale='.25*actual shoulder width',
        physical_N_scale='clip(.65*actual observed chord depth,.02*width,.20*width)',
        physical_norm_cap='min(.35*actual observed chord depth,.08*actual shoulder width), smooth norm cap before ownership/support',
        ownership='Original-family actual PCHIP request partition times compact C2 longitudinal/across endpoint guards; caller supplies independent real topology eligibility.',
        sigma_physical=sigma_physical, gaussian_sigma_grid_samples=list(sigma),
        bandlimit='Gaussian on B/N response components including finite exterior zero samples; min one grid sample per axis, then cubic B-spline coefficients and map_coordinates(order3,prefilterFalse).',
        slab_boundary='C2 normal fade to zero over outer12% of tabulated N range; exact zero beyond slab.',
        stage_statistics=[], grid_build_elapsed_seconds=perf_counter()-started,
        source_geometry_modified=False, response_T_component_zero=True,
        limitations='Finite membership and sampled/smoothed restricted-ray response, not an SDF, exact exterior projection or volumetric topology. After bandlimiting the field need not vanish at every finite exterior point. Local continuum mapping/ownership do not prove preserved ridges, collisions or aesthetics; completed F/E/V integration and native validation belong to caller.')
    evidence = dict(volume_T=axes[0], volume_B=axes[1], volume_N=axes[2],
                    raw_normalized_BN_response=raw, bandlimited_normalized_BN_response=filtered,
                    spline_BN_coefficients=coefficients, gaussian_sigma_grid_samples=np.array(sigma),
                    reference_parameter=geometry.parameter, reference_material_cross=geometry.cross,
                    reference_surface_xyz=geometry.surface, reference_shoulder_arc=geometry.arc,
                    reference_T=geometry.tangent, reference_B=geometry.across, reference_N=geometry.normal,
                    reference_width=geometry.width, reference_observed_depth=geometry.depth)
    return ParentAttachedVolume(geometry, events, ownership, axes, coefficients, metadata), metadata, evidence
