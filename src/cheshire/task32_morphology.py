"""Opt-in Task32 experiments, independent of all Task01--31 operators.

Metric growth below is a graph-spring variational surrogate, NOT ARCSim or
an implementation of Gingras/Kry's shell mechanics. Swept hierarchy is our
own carrier-space application of hierarchical/field-guided modelling.
"""
from dataclasses import replace
import numpy as np
from scipy.sparse import coo_matrix, diags, eye
from scipy.optimize import minimize
from .reference_subdivision import topology, fields, unit
from .progressive_gates import PLANE_X, PLANE_Y


def triangles(mesh):
    q = mesh.faces
    return np.concatenate([q[q[:, k] >= 0][:, [0, k-1, k]]
                           for k in range(2, q.shape[1])])


def carrier_coordinates(rest):
    """Nearest segment of the existing RECT U's centreline, in input units.

    This is a declared carrier-specific approximation, not a general surface
    parameterization or exact geodesic. Positive CC material samples retained.
    """
    path = np.array([[-1550, 0], [-1550, 1300], [-1550, 2600],
                     [-1550, 3050], [0, 3050], [1550, 3050],
                     [1550, 2600], [1550, 1300], [1550, 0]], float)
    p = rest[:, [0, 2]] - [PLANE_X, 0]
    delta = np.diff(path, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    t = np.clip(((p[:, None]-path[:-1])*delta).sum(2)/lengths**2, 0, 1)
    candidates = path[:-1] + t[:, :, None]*delta
    pick = np.argmin(((p[:, None]-candidates)**2).sum(2), axis=1)
    chosen = candidates[np.arange(len(p)), pick]
    tangent = delta[pick]/lengths[pick, None]
    cross = np.column_stack([tangent[:, 1], -tangent[:, 0]])
    radial = ((p-chosen)*cross).sum(1)/450
    depth = (rest[:, 1]-PLANE_Y)/250
    theta = np.arctan2(depth, radial)
    arc = np.r_[0, np.cumsum(lengths)][pick]+t[np.arange(len(p)), pick]*lengths[pick]
    return arc, theta, float(lengths.sum()), tangent


def hierarchy_field(rest, spec, level=0):
    """Parent envelope gates smaller, phase-coupled children (no random noise).

    No branching connectivity is claimed: 'children' here are field lobes.
    Turning off coupling retains the same frequencies and envelope bandwidths.
    """
    arc, theta, total, _ = carrier_coordinates(rest)
    s = arc/total
    count = float(spec.get('lobes', 5))
    parent_phase = 2*np.pi*count*s + float(spec.get('phase', 0))
    parent = .5+.5*np.cos(parent_phase)
    twist = float(spec.get('twist', 1.5))*2*np.pi*s
    theta_phase = float(spec.get('angular', 3))*theta+twist
    if level == 0:
        f = parent*np.cos(theta_phase)
    else:
        envelope = parent**float(spec.get('envelope_power', 1.5))
        coupling = float(spec.get('coupling', 1))*np.sin(parent_phase)
        f = envelope*np.cos((2**level)*theta_phase + coupling*(level+1))
        f *= .5+.5*np.cos((2**level)*parent_phase+coupling)
    # Suppression at original feet is explicit and shared by all conditions.
    f *= np.clip(np.minimum(s, 1-s)/.07, 0, 1)
    return f


def displace_hierarchy(mesh, spec, level=0):
    scalar = hierarchy_field(mesh.rest, spec, level)
    normals = fields(mesh)['nv']
    amplitude = float(spec['amplitude'])*(float(spec.get('decay', .38))**level)
    if not np.isfinite(amplitude):
        raise ValueError('Finite displacement amplitude required.')
    xyz = mesh.xyz + amplitude*scalar[:, None]*normals
    out = replace(mesh, xyz=xyz)
    return out, dict(mechanism='swept parent/child normal displacement', level=level,
                     amplitude=amplitude, spec=spec, topology_changed=False,
                     caveat='Applied field geometry; neither physical folding nor topological branching.'), \
        dict(field=scalar, applied_normals=normals, vertex_displacement=xyz-mesh.xyz)


def spring_system(mesh):
    tri = triangles(mesh)
    edges = np.unique(np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]],
                                              tri[:, [2, 0]]]), axis=1), axis=0)
    i, j = edges.T
    weights = np.ones(2*len(i))
    adjacency = coo_matrix((weights, (np.r_[i, j], np.r_[j, i])),
                           shape=(len(mesh.xyz),)*2).tocsr()
    laplacian = eye(len(mesh.xyz), format='csr')-diags(1/np.asarray(adjacency.sum(1)).ravel())@adjacency
    scale = float(np.linalg.norm(mesh.xyz[i]-mesh.xyz[j], axis=1).mean())
    if not scale > 0:
        raise ValueError('Positive spring scale required.')
    return edges, laplacian, scale


def growth_energy(x, base, edges, lengths, laplacian, bending, anchors):
    """Analytic gradient of a stated spring + displacement-Laplacian energy.

    A positive regularizer in lengths only prevents division by zero in the
    gradient; collapsed edges are separately reported, never repaired.
    """
    x = np.asarray(x).reshape(base.shape)
    i, j = edges.T
    difference = x[i]-x[j]
    current = np.linalg.norm(difference, axis=1)
    error = current-lengths
    value = .5*np.sum(error**2)
    force = (error/np.maximum(current, 1e-14))[:, None]*difference
    gradient = np.column_stack([np.bincount(i, weights=force[:, k], minlength=len(x))-
                                np.bincount(j, weights=force[:, k], minlength=len(x)) for k in range(3)])
    dx = x-base
    bend = laplacian@dx
    value += .5*bending*np.sum(bend**2) + .5*np.sum(anchors[:, None]*dx**2)
    gradient += bending*(laplacian.T@bend) + anchors[:, None]*dx
    return float(value/len(x)), (gradient/len(x)).ravel()


def metric_growth(mesh, spec):
    edges, lap, scale = spring_system(mesh)
    base = mesh.xyz/scale
    arc, theta, total, tangent = carrier_coordinates(mesh.rest)
    parent = hierarchy_field(mesh.rest, spec)
    # Growth is nonnegative, with anisotropy along the actual swept tangent.
    signal = .5+.5*parent
    if spec.get('field') == 'bands':
        signal = (.5+.5*np.cos(2*np.pi*spec.get('lobes', 5)*arc/total))**2
    signal *= np.clip(np.minimum(arc, total-arc)/(total*.07), 0, 1)
    i, j = edges.T
    direction = unit(mesh.xyz[j]-mesh.xyz[i])
    vector = np.column_stack([tangent[:, 0], np.zeros(len(base)), tangent[:, 1]])
    alignment = ((direction*unit(vector[i]+vector[j])).sum(1))**2
    anisotropy = float(spec.get('anisotropy', 0))
    growth = 1+float(spec.get('growth', .3))*signal[edges].mean(1)*((1-anisotropy)+anisotropy*alignment)
    target = np.linalg.norm(base[j]-base[i], axis=1)*growth
    anchors = np.full(len(base), float(spec.get('anchor', .002)))
    anchors[mesh.rest[:, 2] < 50] = float(spec.get('foot_anchor', 10))
    bending = float(spec.get('bending', .02))
    if np.any(growth <= 0) or not np.isfinite(growth).all() or bending < 0 or np.any(anchors < 0):
        raise ValueError('Invalid metric growth energy.')
    # Infinitesimal, reproducible symmetry breaking, NOT a sculpted fold shape.
    seed = float(spec.get('seed', .001))*parent[:, None]*fields(mesh)['nv']
    history = []
    def objective(x):
        return growth_energy(x, base, edges, target, lap, bending, anchors)
    initial = objective((base+seed).ravel())[0]
    def callback(x):
        if len(history) % 25 == 0:
            history.append(dict(energy=objective(x)[0]))
        else:
            history.append(None)
    result = minimize(objective, (base+seed).ravel(), jac=True, method='L-BFGS-B',
                      callback=callback, options=dict(maxiter=int(spec.get('maxiter', 2000)),
                      ftol=1e-11, gtol=1e-6, maxls=40))
    xyz = result.x.reshape(base.shape)*scale
    if not np.isfinite(xyz).all():
        raise ValueError('Nonfinite growth result; no fallback.')
    actual = np.linalg.norm(xyz[j]-xyz[i], axis=1)/scale
    meta = dict(mechanism='anisotropic rest-edge growth variational surrogate', spec=spec,
                topology_changed=False, converged=bool(result.success), termination=str(result.message),
                iterations=int(result.nit), evaluations=int(result.nfev), initial_energy=initial,
                final_energy=float(result.fun), gradient_inf=float(np.abs(result.jac).max()),
                relative_metric_error_RMS=float(np.sqrt(np.mean(((actual-target)/target)**2))),
                scale=scale, bending=bending, caveat='No physical shell bending, collision response, or manufacturing guarantee.')
    state = dict(spring_edges=edges, target_lengths=target*scale, growth_signal=signal,
                 base_xyz=mesh.xyz, anchors=anchors, energy_history=np.array([h['energy'] if h else np.nan for h in history]),
                 optimizer_xyz=xyz, terminal_gradient=result.jac.reshape(base.shape))
    return replace(mesh, xyz=xyz), meta, state
