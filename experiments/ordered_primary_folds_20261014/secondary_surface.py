"""Two physically budgeted, nested flank folds on an actual G7 parent.

The caller supplies the fresh ordered PRIMARY carrier and its actual
amplitude envelope. No source XYZ or association is modified. Existing late
LINKED/WIDE deltas and the global micro FLOW are not inputs to this operator.
"""
from pathlib import Path
import hashlib
import importlib.util

import numpy as np

HERE = Path(__file__).resolve().parent
FLOW_PATH = HERE.parent/'flow_fold_finish_20261014/flow_curved_operator.py'
FLOW_SHA = '92248bd60d4d2188f05a7396fc0eec1989ae365644454081e911600e3e5bc844'
CHUNK = 65536


def _file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


if _file_hash(FLOW_PATH) != FLOW_SHA:
    raise ValueError('Frozen normal, transport and averaging adapter changed.')
_spec = importlib.util.spec_from_file_location('parent_nested_frozen_flow', FLOW_PATH)
flow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flow)
field = flow.field


def helper_paths():
    """Every directly imported frozen helper and its imported dependencies."""
    return [FLOW_PATH]+flow.helper_paths()


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _quintic(value):
    s = np.clip(value, 0., 1.)
    return s*s*s*(10.+s*(-15.+6.*s))


def _orbit_min(value, pairs):
    """Conservative scalar budget shared by all actual reflection partners."""
    result = np.minimum(value, value[pairs['X']])
    return np.minimum(result, result[pairs['Y']])


def _metric(xyz, quads, phase, degree, height, pairs):
    """RMS actual-quad intrinsic phase gradient; invalid incidents get zero."""
    gradient_sum = np.zeros(len(xyz), dtype=float)
    invalid_incident = np.zeros(len(xyz), dtype=bool)
    invalid_faces = 0
    minimum_valid_gram_ratio = 1.
    maximum_diagonal_phase_span = 0.
    for start in range(0, len(quads), CHUNK):
        q = quads[start:start+CHUNK]
        p = xyz[q]
        e1, e2 = p[:, 1]-p[:, 3], p[:, 2]-p[:, 0]
        a = np.einsum('ij,ij->i', e1, e1)
        b = np.einsum('ij,ij->i', e1, e2)
        c = np.einsum('ij,ij->i', e2, e2)
        ac = a*c
        determinant = ac-b*b
        d1, d2 = phase[q[:, 1]]-phase[q[:, 3]], phase[q[:, 2]]-phase[q[:, 0]]
        maximum_diagonal_phase_span = max(maximum_diagonal_phase_span,
            float(np.max(np.maximum(np.abs(d1), np.abs(d2)), initial=0.)))
        ratio = np.divide(determinant, ac, out=np.zeros_like(ac), where=ac > 0.)
        valid = (np.isfinite(determinant) & np.isfinite(ratio) &
                 (a > 0.) & (c > 0.) & (determinant > 0.) & (ratio >= 1e-8))
        numerator = c*d1*d1-2.*b*d1*d2+a*d2*d2
        g2 = np.divide(numerator, determinant, out=np.zeros_like(numerator), where=valid)
        valid &= np.isfinite(g2) & (g2 >= 0.)
        invalid_faces += int(np.count_nonzero(~valid))
        if np.any(~valid):
            invalid_incident[q[~valid].ravel()] = True
        if np.any(valid):
            minimum_valid_gram_ratio = min(minimum_valid_gram_ratio, float(ratio[valid].min()))
        g2[~valid] = 0.
        gradient_sum += np.bincount(q.ravel(), weights=np.repeat(g2, 4), minlength=len(xyz))
    gradient = np.sqrt(gradient_sum/degree)
    width = np.divide(1.8, gradient, out=np.full_like(gradient, .08*height), where=gradient > 0.)
    width = np.minimum(width, .08*height)
    width[invalid_incident] = 0.
    width = _orbit_min(width, pairs)
    if not np.isfinite(width).all() or np.any(width < 0.):
        raise ValueError('Nonfinite or negative actual physical flank metric.')
    info = dict(method='Actual incoming quad diagonal Gram solve; incident RMS intrinsic phase gradient.',
        equation='e1=x1-x3; e2=x2-x0; g2=(c*dphi1^2-2*b*dphi1*dphi2+a*dphi2^2)/(a*c-b^2); width=min(1.8/sqrt(mean_incident(g2)),.08H)',
        phase_difference='Direct differences of actual supplied unwrapped inherited phase; no modulo aliasing.',
        gram_relative_threshold=1e-8, invalid_quad_count=invalid_faces,
        invalid_incident_vertex_count=int(np.count_nonzero(invalid_incident)),
        minimum_valid_relative_gram_determinant=minimum_valid_gram_ratio,
        maximum_actual_diagonal_phase_span=maximum_diagonal_phase_span,
        zero_width_vertex_count=int(np.count_nonzero(width == 0.)),
        flank_width_quantiles=np.quantile(width, [0., .1, .25, .5, .75, .9, .99, 1.]).tolist(),
        small_widths_floored=False, maximum_flank_width=.08*height,
        scalar_reflection='Conservative minimum over each actual X/Y reflection orbit.',
        limitation='First-order intrinsic phase spacing, not a geodesic crest-distance or remote-sheet gap/collision certificate.')
    return width, info


def _pass(xyz, quads, degree, signed, amplitude, mask, ids, pairs, label):
    print('PARENT_NESTED '+label+': fresh actual incoming normals', flush=True)
    normals = field._input_normals(xyz, quads)
    normal_sha = _hash(normals)
    raw = normals*signed[:, None]
    del normals
    delta = flow._average_delta(raw, quads, degree)
    del raw
    # Reapply support after averaging so the filter's edge halo does not
    # move the phase-defined parent crest and groove centre lines.
    delta *= mask[:, None]
    cap = amplitude*mask
    norms = np.linalg.norm(delta, axis=1)
    scale = np.divide(cap, norms, out=np.ones_like(cap), where=norms > 0.)
    delta *= np.minimum(1., scale)[:, None]
    delta[cap == 0.] = 0.
    delta = field._transport(delta, ids, pairs)[0]
    norms = np.linalg.norm(delta, axis=1)
    violation = float(np.max(norms-cap, initial=0.))
    protected_error = float(np.max(np.abs(delta[mask == 0.]), initial=0.))
    if violation > 1e-12 or protected_error != 0. or not np.isfinite(delta).all():
        raise ValueError('Actual '+label+' violated its inherited pointwise displacement budget/support.')
    metadata = dict(input_xyz_sha256=_hash(xyz), input_normal_sha256=normal_sha,
        delta_sha256=_hash(delta), maximum_displacement=float(norms.max(initial=0.)),
        displacement_quantiles=np.quantile(norms, [0., .5, .9, .99, 1.]).tolist(),
        amplitude_budget_quantiles=np.quantile(amplitude, [0., .5, .9, .99, 1.]).tolist(),
        maximum_budget_violation=violation, protected_delta_maximum=protected_error,
        nonzero_mask_control_vertices=int(np.count_nonzero(mask)),
        moved_control_vertices=int(np.count_nonzero(norms)), fresh_normal_evaluation=True)
    return delta, metadata


def build(xyz, q, phase, parent_envelope, vx, vy, H):
    """Return output XYZ, JSON-safe metadata and exact two-stage NPZ state."""
    xyz, q, phase = np.asarray(xyz), np.asarray(q), np.asarray(phase)
    envelope = np.asarray(parent_envelope)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or xyz.dtype.kind != 'f' or not len(xyz)
            or not np.isfinite(xyz).all() or q.ndim != 2 or q.shape[1] != 4 or not len(q)
            or q.dtype.kind not in 'iu' or q.min() < 0 or q.max() >= len(xyz)):
        raise ValueError('Actual finite G7 all-quad parent required.')
    count = len(xyz)
    if (phase.shape != (count,) or envelope.shape != (count,)
            or not np.isfinite(phase).all() or not np.isfinite(envelope).all()
            or np.any(envelope < 0.)):
        raise ValueError('Finite inherited phase and nonnegative actual parent envelope required.')
    H = float(H)
    if not np.isfinite(H) or H <= 0.:
        raise ValueError('Positive inherited physical height required.')
    ids, pairs = field._mirror_pairs({'X': vx, 'Y': vy}, count)
    degree = np.bincount(q.ravel(), minlength=count)
    if np.any(degree == 0):
        raise ValueError('Source orphan controls are not repaired.')
    representative = np.minimum(np.minimum(ids, pairs['X']),
        np.minimum(pairs['Y'], pairs['X'][pairs['Y']]))
    sine = np.sin(phase)
    parent_mask = sine*sine
    parent_mask[np.abs(sine) < 1e-14] = 0.  # Exact seam/profile-centre roundoff only.
    parent_mask = parent_mask[representative]
    child_phase = (3.*phase)[representative]
    del sine, representative
    print('PARENT_NESTED: actual physical parent-phase flank widths', flush=True)
    width, metric = _metric(xyz, q, phase, degree, H, pairs)
    inherited_budget = _orbit_min(envelope, pairs)
    child_budget = np.minimum(.28*inherited_budget, .10*width)
    small_budget = np.minimum(.28*child_budget, .075*width/3.)
    profile = np.cos(child_phase)
    small_mask = parent_mask*_quintic((profile-.15)/.65)
    # Masks and caps share the exact canonical reflection orbit, so subsequent
    # vector transport cannot move a protected partner or exceed its budget.
    child_delta, child = _pass(xyz, q, degree, child_budget*parent_mask*profile,
        child_budget, parent_mask, ids, pairs, 'CHILD')
    child_xyz = xyz+child_delta
    small_delta, small = _pass(child_xyz, q, degree,
        small_budget*small_mask*np.cos(3.*child_phase),
        small_budget, small_mask, ids, pairs, 'SMALL')
    output = child_xyz+small_delta
    if not np.isfinite(output).all():
        raise ValueError('Nonfinite actual nested fold output.')
    parent_violation = float(np.max(child_budget-.28*envelope, initial=0.))
    small_violation = float(np.max(small_budget-.28*child_budget, initial=0.))
    mask_violation = float(np.max(small_mask-parent_mask, initial=0.))
    protected = parent_mask == 0.
    protected_motion = float(np.max(np.abs(output[protected]-xyz[protected]), initial=0.))
    if max(parent_violation, small_violation, mask_violation) > 1e-12 or protected_motion != 0.:
        raise ValueError('Actual parent-child hierarchy budget or protected geometry failed.')
    metadata = dict(implementation='ORDERED_PRIMARY_BROAD_FLANK_SECONDARY_V2',
        source_generation=7, output_generation=7, added_CC_passes=0,
        added_topology_events=0, normal_field_passes=2,
        sequence=['CHILD', 'SMALL'], old_LINKED_WIDE_reused=False,
        global_micro_FLOW_added=False, physical_height_reference=H,
        parent_support='W=sin(actual inherited unwrapped primary phase)^2; exact zero enforced only for |sin|<1e-14 profile-centre/seam roundoff',
        child_phase='qchild=3*actual inherited primary phase; no independent axial oscillation',
        child_request='min(.28*actual_parent_envelope,.10*actual_local_flank_width)*W*cos(qchild)',
        small_support='W*quintic(clip((cos(qchild)-.15)/.65,0,1))',
        small_request='min(.28*child_budget,.075*actual_local_flank_width/3)*small_mask*cos(3*qchild)',
        parent_envelope_scope='Fresh actual G6 PRIMARY .009H*PCHIPenvelope*(1-.7*saved_feature_support)*(.825+.175*cos(2*actual_incoming_theta)), transported by the verified neutral CC convex stencil. Phase is defined on actual incoming G6 once and then inherited.',
        displacement_filter='One frozen .5*self+.5*actual_edge_neighbor_mean pass on each new delta only, then support re-mask, pointwise norm cap, and canonical mirror-vector transport.',
        width_metric=metric, child=child, small=small,
        child_budget_max_parent_fraction=.28, small_budget_max_child_fraction=.28,
        actual_child_parent_budget_maximum_violation=parent_violation,
        actual_small_child_budget_maximum_violation=small_violation,
        actual_small_parent_mask_maximum_violation=mask_violation,
        protected_control_vertices=int(np.count_nonzero(protected)),
        protected_output_maximum_motion=protected_motion,
        input_xyz_sha256=_hash(xyz), input_quads_sha256=_hash(q),
        input_parent_phase_sha256=_hash(phase), input_parent_envelope_sha256=_hash(envelope),
        intermediate_child_xyz_sha256=_hash(child_xyz), output_xyz_sha256=_hash(output),
        source_geometry_averaged=False, associations_unchanged=True,
        scalar_reflection='Masks use the minimum-ID orbit representative; physical width/envelope caps use conservative reflection-orbit minima.',
        code_binding={str(path): _file_hash(path) for path in [Path(__file__).resolve()]+helper_paths()},
        support_scope='Counts refer to control vertices, not measured surface area.',
        limitations='Authored dependency on the actual incoming PRIMARY surface phase, not semantic ridge/termination detection or recursive topology. The sin-squared mask preserves primary profile centre lines, not broad crest/groove neighborhoods. Width caps do not prove collision freedom; matched renders determine visual quality.')
    state = dict(delta_child=child_delta, delta_small=small_delta,
        parent_mask=parent_mask, small_mask=small_mask, child_budget=child_budget,
        small_budget=small_budget, local_flank_width=width)
    return output, metadata, state
