"""All-role, intrinsic, nominal physical-scale filter on an actual quad mesh.

This removes geometric high frequencies already baked into a saved carrier.
It does not classify semantic folds or guarantee an unchanged silhouette.
Use the actual pre-late-detail G4 as input, then the recorded neutral CC
ancestry to obtain dense controls; do not silently retain late detail deltas.
"""
from time import perf_counter

import numpy as np
import scipy
from scipy.sparse import coo_matrix, diags, eye
from scipy.sparse.linalg import splu


def helper_paths():
    """No project-local helper modules are imported."""
    return []


def _graph(xyz, quads):
    """Positive intrinsic graph stiffness with lumped native-fan area mass."""
    points = xyz[quads]
    relative = points-points.mean(axis=1)[:, None, :]
    area = .5*np.linalg.norm(np.cross(relative, np.roll(relative, -1, axis=1)), axis=2).sum(axis=1)
    if not np.isfinite(area).all() or np.any(area <= 0.):
        raise ValueError('Every actual quad must have positive native-fan area.')
    mass = np.bincount(quads.ravel(), weights=np.repeat(area/4., 4), minlength=len(xyz))
    if np.any(mass <= 0.) or not np.isfinite(mass).all():
        raise ValueError('Positive incident area mass required; orphan controls are not repaired.')
    directed = np.stack([quads, np.roll(quads, -1, axis=1)], axis=-1).reshape(-1, 2)
    directed.sort(axis=1)
    edges, inverse, incidence = np.unique(directed, axis=0, return_inverse=True, return_counts=True)
    if np.any(incidence > 2):
        raise ValueError('Actual manifold quad-edge incidence required.')
    length2 = np.einsum('ij,ij->i', xyz[edges[:, 1]]-xyz[edges[:, 0]],
                        xyz[edges[:, 1]]-xyz[edges[:, 0]])
    if np.any(length2 <= 0.) or not np.isfinite(length2).all():
        raise ValueError('Actual positive edge lengths required; no weld or epsilon clamp.')
    adjacent_area = np.bincount(inverse, weights=np.repeat(area, 4), minlength=len(edges))
    conductance = adjacent_area/(2.*length2)
    if not np.isfinite(conductance).all():
        raise ValueError('Finite positive physical graph conductance required.')
    diagonal = np.bincount(edges.ravel(), weights=np.repeat(conductance, 2), minlength=len(xyz))
    rows = np.concatenate([edges[:, 0], edges[:, 1], np.arange(len(xyz))])
    columns = np.concatenate([edges[:, 1], edges[:, 0], np.arange(len(xyz))])
    values = np.concatenate([-conductance, -conductance, diagonal])
    stiffness = coo_matrix((values, (rows, columns)), shape=(len(xyz), len(xyz))).tocsr()
    return mass, stiffness, edges, conductance, area, incidence


def lowpass(xyz, quads, cutoff=.30):
    """Return ``(filtered_xyz, JSON-safe metadata, NPZ-safe evidence)``.

    ``cutoff`` is a physical length in the input mesh's units. The soft
    continuum transfer is h(lambda)=1/(1+9*(cutoff/lambda)**4), so a mode
    with wavelength equal to cutoff retains 10 percent, while one with five
    times that wavelength retains about 98.58 percent. Discrete graph modes
    only approximate these physical wavelengths on irregular quads.

    No vertex/role/camera mask or authored fold rail is used. Input XYZ and
    quads stay unchanged. Boundary edges, if present, get the natural graph
    boundary treatment. The filter preserves constant translations and the
    input's area-weighted centroid, not volume or exact large crests.
    """
    started = perf_counter()
    xyz, quads = np.asarray(xyz), np.asarray(quads)
    if (xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz)
            or xyz.dtype.kind != 'f' or not np.isfinite(xyz).all()
            or quads.ndim != 2 or quads.shape[1] != 4 or not len(quads)
            or quads.dtype.kind not in 'iu' or quads.min() < 0 or quads.max() >= len(xyz)):
        raise ValueError('Finite actual quad mesh controls required.')
    cutoff = float(cutoff)
    if not np.isfinite(cutoff) or cutoff <= 0.:
        raise ValueError('Positive finite physical cutoff required.')
    mass, stiffness, edges, conductance, area, incidence = _graph(xyz, quads)
    root_mass = np.sqrt(mass)
    inverse_root = 1./root_mass
    scaling = diags(inverse_root, format='csr')
    laplacian = (scaling@stiffness@scaling).tocsr()
    tau = 9.*(cutoff/(2.*np.pi))**4
    centre = np.sum(mass[:, None]*xyz, axis=0)/mass.sum()
    rhs = root_mass[:, None]*(xyz-centre)
    matrix = (eye(len(xyz), format='csc', dtype=np.complex128)
              +1j*np.sqrt(tau)*laplacian.tocsc())
    setup_seconds = perf_counter()-started
    # For real b and real symmetric B,
    # Re[(I+i*sqrt(tau)*B)^-1 b] = (I+tau*B^2)^-1 b.
    # One sparse second-order factorization avoids a dense/filled B^2 matrix
    # and the badly conditioned unpreconditioned fourth-order CG problem.
    factor_started = perf_counter()
    factor = splu(matrix, permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0.,
                  options={'SymmetricMode': True})
    factor_seconds = perf_counter()-factor_started
    solution = factor.solve(rhs.astype(np.complex128))
    complex_residual = matrix@solution-rhs
    rhs_norm = np.linalg.norm(rhs, axis=0)
    relative_complex = np.linalg.norm(complex_residual, axis=0)/np.maximum(rhs_norm, np.finfo(float).tiny)
    filtered_weighted = solution.real
    fourth_residual = filtered_weighted+tau*(laplacian@(laplacian@filtered_weighted))-rhs
    relative_fourth = np.linalg.norm(fourth_residual, axis=0)/np.maximum(rhs_norm, np.finfo(float).tiny)
    output = filtered_weighted*inverse_root[:, None]+centre
    if not np.isfinite(output).all() or np.max(relative_complex) > 1e-8:
        raise ValueError('Physical filter sparse solve failed its finite/residual check.')
    displacement = output-xyz
    norms = np.linalg.norm(displacement, axis=1)
    centroid_error = np.sum(mass[:, None]*(output-xyz), axis=0)/mass.sum()
    quantiles = [0., .1, .5, .9, .99, 1.]
    metadata = dict(
        implementation='ALL_ROLE_INTRINSIC_MASS_STIFFNESS_BIHARMONIC_LOWPASS_V1',
        input_control_count=len(xyz), input_quad_count=len(quads),
        physical_cutoff=cutoff, transition='Soft fourth-order spectral response; no binary semantic fold classification.',
        tau=tau, equation='(M+tau*S*M^-1*S)*x=M*x_input',
        normalized_equation='B=M^-1/2*S*M^-1/2; y=Re[(I+i*sqrt(tau)*B)^-1*sqrt(M)*(x_input-centroid)]; x=M^-1/2*y+centroid',
        nominal_continuum_gain='1/(1+9*(cutoff/wavelength)^4)',
        nominal_gain_at_cutoff=.1, nominal_gain_at_5_times_cutoff=1./(1.+9./625.),
        stiffness='Symmetric positive graph Laplacian, edge conductance=sum(incident actual quad native-fan areas)/(2*actual edge length^2).',
        mass='One quarter of each incident actual quad native-fan area.',
        metric_assumption='Regular square grids reproduce physical finite-difference Laplacian scale. Irregular/nonplanar quads use an intrinsic positive graph approximation, not an exact cotangent FEM Laplace-Beltrami spectrum.',
        role_scope='All controls and all actual quad roles; no SOURCE-only mask.',
        boundary_edge_count=int(np.count_nonzero(incidence == 1)),
        edge_length_quantiles=np.quantile(np.sqrt(np.einsum('ij,ij->i', xyz[edges[:, 1]]-xyz[edges[:, 0]], xyz[edges[:, 1]]-xyz[edges[:, 0]])), quantiles).tolist(),
        conductance_quantiles=np.quantile(conductance, quantiles).tolist(),
        lumped_mass_quantiles=np.quantile(mass, quantiles).tolist(),
        setup_seconds=setup_seconds, factor_seconds=factor_seconds,
        factor_L_nnz=int(factor.L.nnz), factor_U_nnz=int(factor.U.nnz),
        solve_complex_relative_residual_xyz=relative_complex.tolist(),
        fourth_order_relative_residual_xyz=relative_fourth.tolist(),
        area_weighted_centroid_error_xyz=centroid_error.tolist(),
        displacement_quantiles=np.quantile(norms, quantiles).tolist(),
        maximum_displacement=float(norms.max()), elapsed_seconds=perf_counter()-started,
        scipy_version=scipy.__version__, numpy_version=np.__version__,
        source_arrays_modified=False,
        limitations='Nominal physical-scale attenuation, not removal of every semantic fold below a sharp cutoff. Large features are softly attenuated, and volume, silhouette, crests, collision freedom and aesthetics are not guaranteed. The graph is frozen on the actual incoming mesh; later neutral CC transport has its own additional smoothing.')
    evidence = dict(delta=displacement, input_mass=mass,
                    input_edges=edges, edge_conductance=conductance,
                    input_native_fan_quad_area=area,
                    centroid=centre, cutoff=np.array(cutoff), tau=np.array(tau),
                    complex_relative_residual=relative_complex,
                    fourth_order_relative_residual=relative_fourth)
    return output, metadata, evidence
