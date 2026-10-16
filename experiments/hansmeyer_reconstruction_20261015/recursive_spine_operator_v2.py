"""Shared-base connected coffer/rib cage and two coupled subdivision generations.

These are new local scaffold generations, unrelated to original G birth IDs.
Source and formed cages share connectivity and source correspondence. Only
their differential is returned; the original cloth is never flattened.
"""
from pathlib import Path
import hashlib
import numpy as np
from scipy.ndimage import gaussian_filter1d


U_KNOTS = np.array([-1., -.75, -.5, -.22, 0., .22, .5, .75, 1.])
NODE_N = np.array([0., .12, .90, .90, .90, .90, .90, .12, 0.])
NECK_N = np.array([0., .12, .65, .20, -.25, .20, .65, .12, 0.])
NODE_B = np.array([0., .10, -.05, .025, 0., -.025, .05, -.10, 0.])
SCHEDULE = ((-.22, .11, .055), (-.14, .07, .035))


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def quintic(value):
    x = np.clip(value, 0., 1.)
    return x*x*x*(10.+x*(-15.+6*x))


def unit(value):
    length = np.linalg.norm(value, axis=1)
    return np.divide(value, length[:, None], out=np.zeros_like(value), where=length[:, None] > 0.)


def incident(values, ids, count):
    degree = np.bincount(ids, minlength=count)
    if np.asarray(values).ndim == 1:
        return np.bincount(ids, weights=values, minlength=count)/degree
    return np.column_stack([np.bincount(ids, weights=values[:, j], minlength=count)/degree
                            for j in range(values.shape[1])])


def topology(q, nv):
    a = q.ravel(); b = np.roll(q, -1, axis=1).ravel()
    edges, inverse, counts = np.unique(np.sort(np.column_stack((a, b)), axis=1),
                                       axis=0, return_inverse=True, return_counts=True)
    if np.any((counts < 1)|(counts > 2)):
        raise ValueError('Local scaffold must have one/two-face edges.')
    face = np.repeat(np.arange(len(q)), 4)
    ef = np.empty((len(edges), 2), np.int64)
    ef[:, 0] = len(q); ef[:, 1] = -1
    np.minimum.at(ef[:, 0], inverse, face); np.maximum.at(ef[:, 1], inverse, face)
    boundary_edges = counts == 1
    boundary_vertices = np.zeros(nv, bool); boundary_vertices[edges[boundary_edges].ravel()] = True
    boundary_degree = np.bincount(edges[boundary_edges].ravel(), minlength=nv)
    if np.any(boundary_degree[boundary_vertices] != 2):
        raise ValueError('Boundary must be closed simple scaffold rim; no repair.')
    return dict(edges=edges, ef=ef, fe=inverse.reshape(-1, 4), edge_counts=counts,
                degree=np.bincount(edges.ravel(), minlength=nv),
                boundary_edges=boundary_edges, boundary_vertices=boundary_vertices)


def coupled(xyz, q, classes, source_chart, logical, activity, weights):
    """Completed F -> E; completed F + original midpoint -> V, open rim CC."""
    nv, nf = len(xyz), len(q); t = topology(q, nv)
    e, ef, degree = t['edges'], t['ef'], t['degree']; ne = len(e)
    p = xyz[q]; c = p.mean(axis=1)
    nfvec = unit(np.cross(p-c[:, None], np.roll(p, -1, axis=1)-c[:, None]).sum(axis=1))
    length = np.linalg.norm(xyz[e[:, 1]]-xyz[e[:, 0]], axis=1)
    sf = length[t['fe']].mean(axis=1)
    se = sf[ef].mean(axis=1)
    sv = incident(np.repeat(sf, 4), q.ravel(), nv)
    nvertex = unit(incident(np.repeat(nfvec, 4, axis=0), q.ravel(), nv))
    nedge = nfvec[ef].mean(axis=1)
    fa = activity[q].mean(axis=1); ea = activity[e].mean(axis=1); va = activity
    wf, we, wp = weights
    base = c.copy()
    cls = classes[q]
    eligible = ((cls == 0).sum(axis=1) == 1)&((cls == 1).sum(axis=1) == 2)&((cls == 2).sum(axis=1) == 1)
    iv, jf = np.argmax(cls == 0, axis=1), np.argmax(cls == 2, axis=1)
    eligible &= (iv+2)%4 == jf
    if np.any(eligible):
        v = xyz[q[np.arange(nf), iv]]; f = xyz[q[np.arange(nf), jf]]
        esum = (p*(cls == 1)[:, :, None]).sum(axis=1)
        w3, w4 = .25*fa[:, None], .25*fa[:, None]
        later = ((v*(1+w3)+f*(1-w3))*(1+w4)+esum*(1-w4))/4.
        base[eligible] = later[eligible]
    face = base+nfvec*(wf*fa*sf)[:, None]
    w1 = -.5*ea[:, None]
    edge = (face[ef].sum(axis=1)*(1+w1)+xyz[e].sum(axis=1)*(1-w1))/4.
    edge += nedge*(we*ea*se)[:, None]
    edge[t['boundary_edges']] = xyz[e[t['boundary_edges']]].mean(axis=1)
    fbar = incident(np.repeat(face, 4, axis=0), q.ravel(), nv)
    mid = xyz[e].mean(axis=1)
    rbar = incident(np.repeat(mid, 2, axis=0), e.ravel(), nv)
    w2 = -2.*va[:, None]
    vertex = (fbar*(1+w2)+rbar*(2-w2)+(degree[:, None]-3)*xyz)/degree[:, None]
    vertex += nvertex*(wp*va*sv)[:, None]
    boundary = t['boundary_vertices']; be = e[t['boundary_edges']]
    for dim in range(3):
        neighbours = np.bincount(be.ravel(), weights=xyz[be[:, ::-1], dim].ravel(), minlength=nv)
        vertex[boundary, dim] = (6*xyz[boundary, dim]+neighbours[boundary])/8.
    out = np.concatenate((vertex, edge, face))
    following = t['fe']; previous = np.roll(following, 1, axis=1)
    child = np.stack((previous+nv, q, following+nv,
                      np.broadcast_to((nv+ne+np.arange(nf))[:, None], q.shape)), axis=-1).reshape(-1, 4)
    def carry(value):
        return np.concatenate((value, value[e].mean(axis=1), value[q].mean(axis=1)))
    outclasses = np.concatenate((np.zeros(nv, np.int8), np.ones(ne, np.int8), np.full(nf, 2, np.int8)))
    if not np.isfinite(out).all():
        raise ValueError('Nonfinite local formation; no fallback.')
    meta = dict(input_vertices=nv, input_quads=nf, output_vertices=len(out), output_quads=len(child),
                wf=wf, we=we, wp=wp, w1=-.5, w2=-2., w3=.25, w4=.25,
                eq4_eligible=int(eligible.sum()), boundary_vertex_count=int(boundary.sum()),
                boundary_rule='Ordinary CC boundary midpoints and (6V+boundary-neighbours)/8 for both paths.',
                fresh_incoming_normals=True, face_scale_quantiles=np.quantile(sf, [0., .1, .5, .9, 1.]).tolist())
    return out, child, outclasses, carry(source_chart), carry(logical), carry(activity), meta


def form(strip, *, periodic=False, cell_count=None, phase_origin=0., total_length=None):
    """Return refined differential mesh, common source-chart correspondence, meta/state.

    strip requires xyz0/chart0 shaped rows x9 x3 sampled at U_KNOTS, and
    normal/across/width/prominence/s per row. Width is FULL physical parent
    shoulder width; xyz0 must already cover only .65 of that width.
    """
    xyz0 = np.asarray(strip['xyz0'], float); chart0 = np.asarray(strip['chart0'], float)
    rows, across_count, dim = xyz0.shape
    if dim != 3 or across_count != len(U_KNOTS) or chart0.shape != xyz0.shape:
        raise ValueError('Nine actual sampled cross-cage stations required.')
    if rows < 8 or not np.isfinite(xyz0).all() or not np.isfinite(chart0).all():
        raise ValueError('Finite adequate confirmed source strip required.')
    width = np.asarray(strip['width'], float)
    depth = np.asarray(strip['prominence'], float)
    s = np.asarray(strip['s'], float)
    n = unit(np.asarray(strip['normal'], float)); b = unit(np.asarray(strip['across'], float))
    if np.any(width <= 0.) or np.any(depth <= 0.) or np.any(np.diff(s) <= 0.):
        raise ValueError('Actual positive shoulder width, prominence and ordered arc required.')
    raw_width, raw_depth = width.copy(), depth.copy()
    sigma = .5*np.median(1.5*.65*width)/np.median(np.diff(s))
    mode = 'wrap' if periodic else 'nearest'
    if not strip.get('guides_prepooled', False):
        width = gaussian_filter1d(width, sigma, mode=mode)
        depth = gaussian_filter1d(depth, sigma, mode=mode)
    n = unit(gaussian_filter1d(n, sigma, axis=0, mode=mode))
    b = gaussian_filter1d(b, sigma, axis=0, mode=mode)
    b = unit(b-n*np.einsum('ij,ij->i', b, n)[:, None])
    if np.any(np.linalg.norm(n, axis=1) < .9) or np.any(np.linalg.norm(b, axis=1) < .9):
        raise ValueError('Pooled actual parent frame is degenerate.')
    requested_base_width = .65*width
    base_width = np.asarray(strip.get('base_width', requested_base_width), float)
    if base_width.shape != width.shape or np.any(base_width <= 0.) or np.any(base_width > requested_base_width+1e-12):
        raise ValueError('Actual sampled usable base must be positive and inside requested .65W.')
    height = np.minimum(.35*base_width, .6*depth)
    pitch = 1.5*requested_base_width
    density = 1./pitch
    chi = np.concatenate(([0.], np.cumsum(np.diff(s)*(density[:-1]+density[1:])/2.)))
    length = float(total_length if total_length is not None else s[-1])
    if periodic:
        closing = max(0., length-s[-1])*(density[-1]+density[0])/2.
        integral = float(chi[-1]+closing)
        count = int(cell_count if cell_count is not None else max(4, 2*round(integral/2)))
        chi *= count/integral
        chi -= np.interp(phase_origin % length, np.r_[s, length], np.r_[chi, count])
    else:
        count = int(cell_count if cell_count is not None else max(3, round(float(chi[-1]))))
        chi *= count/chi[-1]
        chi -= np.interp(phase_origin, s, chi)
    # Even longitudinal node profile; mirror arc reversal can preserve it exactly.
    node = (.5+.5*np.cos(2*np.pi*chi))**2
    end = np.ones(rows) if periodic else quintic(s/(1.5*pitch[0]))*quintic((length-s)/(1.5*pitch[-1]))
    cross_taper = quintic((1.-np.abs(U_KNOTS))/.22)
    crown = NECK_N[None, :]+node[:, None]*(NODE_N-NECK_N)[None, :]
    normal_delta = height[:, None]*crown*end[:, None]*cross_taper[None, :]
    across_delta = base_width[:, None]*node[:, None]*NODE_B[None, :]*end[:, None]*cross_taper[None, :]
    formed = xyz0+normal_delta[:, :, None]*n[:, None]+across_delta[:, :, None]*b[:, None]
    neutral = xyz0.copy()
    logical_first = np.cos(2*np.pi*s/length) if periodic else s/length
    logical_second = np.sin(2*np.pi*s/length) if periodic else np.zeros(rows)
    logical = np.stack((np.broadcast_to(logical_first[:, None], (rows, across_count)),
                        np.broadcast_to(logical_second[:, None], (rows, across_count)),
                        np.broadcast_to(U_KNOTS[None, :], (rows, across_count))), axis=-1)
    activity = end[:, None]*(.15+.85*node[:, None])*quintic((1.-np.abs(U_KNOTS))[None, :]/.3)
    ns = rows if periodic else rows-1
    r, u = np.meshgrid(np.arange(ns), np.arange(across_count-1), indexing='ij')
    following = (r+1)%rows
    q = np.stack((r*across_count+u, following*across_count+u,
                  following*across_count+u+1, r*across_count+u+1), axis=-1).reshape(-1, 4)
    initial = dict(xyz0=xyz0, source_chart0=chart0, formed_cage=formed.copy(),
                   normal_delta=normal_delta, across_delta=across_delta,
                   parent_width=width, actual_parent_depth=depth, node_height=height,
                   raw_parent_width=raw_width, raw_parent_depth=raw_depth,
                   requested_base_width=requested_base_width, usable_base_width=base_width,
                   logical_chi=chi, logical_s=s, node_envelope=node, cell_count=np.array(count))
    formed, neutral, source_chart, logical, activity = (formed.reshape(-1, 3), neutral.reshape(-1, 3),
        chart0.reshape(-1, 3), logical.reshape(-1, 3), activity.ravel())
    classes = np.full(len(formed), -1, np.int8)
    stages = []
    for generation, weights in enumerate(SCHEDULE, 1):
        f, fq, fc, source_next, logical_next, activity_next, fm = coupled(
            formed, q, classes, source_chart, logical, activity, weights)
        z, zq, zc, _, _, _, zm = coupled(neutral, q, classes, source_chart, logical,
                                         np.zeros_like(activity), (0., 0., 0.))
        if not np.array_equal(fq, zq):
            raise ValueError('Formed/neutral local topology differs.')
        stages.append(dict(scaffold_generation=generation, formed=fm, neutral=zm,
                           formed_xyz_sha256=ah(f), neutral_xyz_sha256=ah(z),
                           topology_sha256=ah(fq)))
        formed, neutral, q, classes = f, z, fq, fc
        source_chart, logical, activity = source_next, logical_next, activity_next
    delta = formed-neutral
    # C2 embedding support is applied again at transfer, not a norm clipping step.
    metadata = dict(kind='CONNECTED_BN_COFFER_CAGE_PLUS_TWO_COUPLED_CC_PASSES',
        source='Actual curved source strip; fine carrier is not globally averaged or replaced.',
        scaffold_generations=2, original_G_generation_unchanged=True, periodic=bool(periodic),
        cell_count=count, physical_length=length, phase_origin=phase_origin,
        logical_type='Periodic cos/sin arc and across u' if periodic else 'Open linear normalized arc, zero, across u',
        parent_width_quantiles=np.quantile(width, [0., .1, .5, .9, 1.]).tolist(),
        node_height_quantiles=np.quantile(height, [0., .1, .5, .9, 1.]).tolist(),
        node_pitch_quantiles=np.quantile(pitch, [0., .1, .5, .9, 1.]).tolist(),
        usable_base_width_quantiles=np.quantile(base_width, [0., .1, .5, .9, 1.]).tolist(),
        width_guides_prepooled=bool(strip.get('guides_prepooled', False)),
        guide_pooling='Gaussian on measured widths/depths and frame vectors only, half local node pitch; source XYZ is not filtered.',
        guide_pooling_sigma_samples=float(sigma),
        maximum_scaffold_delta=float(np.linalg.norm(delta, axis=1).max()), stages=stages,
        geometry='Broad transverse node ribs and continuous raised sidewalls enclose recessed interval centres; same signed BN return and causal completed-F E/V subdivision.',
        section_design=dict(node_N=NODE_N.tolist(), neck_N=NECK_N.tolist(), node_B=NODE_B.tolist(), physical_height_budget_unchanged=True),
        limitations='No collision or beauty certificate. Physical source-strip confirmation/injectivity and canonical mirror phase are caller prerequisites.')
    evidence = dict(initial, formed_refined=formed, neutral_refined=neutral,
                    delta_refined=delta, quads_refined=q, source_chart_refined=source_chart,
                    logical_refined=logical, activity_refined=activity)
    return delta, q, source_chart, metadata, evidence


def helper_paths():
    return [Path(__file__).resolve()]


def reconstruct_strip(formation, foundation):
    """Restore the exact certified source cage without remeasuring its surface."""
    curve = foundation['source_curve']
    normal = np.asarray(curve['normal'])
    tangent = np.asarray(curve['tangent']).copy()
    tangent -= normal*np.einsum('ij,ij->i', tangent, normal)[:, None]
    tangent = unit(tangent)
    return dict(xyz0=formation['xyz0'], chart0=formation['source_chart0'],
                normal=normal, across=np.cross(normal, tangent),
                width=formation['parent_width'], prominence=formation['actual_parent_depth'],
                base_width=formation['usable_base_width'], s=formation['logical_s'],
                guides_prepooled=True)


def section_report(strip, formation, metadata):
    """Cached local-frame section gate; no claim of beauty or collision safety."""
    s = formation['logical_s']; length = metadata['physical_length']
    logical = formation['logical_refined']; ss = logical[:, 0]*length
    sigma = .5*np.median(1.5*.65*strip['width'])/np.median(np.diff(s))
    mode = 'wrap' if metadata['periodic'] else 'nearest'
    n = unit(gaussian_filter1d(unit(strip['normal']), sigma, axis=0, mode=mode))
    b = gaussian_filter1d(unit(strip['across']), sigma, axis=0, mode=mode)
    b = unit(b-n*np.einsum('ij,ij->i', b, n)[:, None])
    def interp(values):
        return np.column_stack([np.interp(ss, s, values[:, j]) for j in range(3)])
    nn, bb = unit(interp(n)), unit(interp(b))
    delta = formation['delta_refined']
    dn = np.einsum('ij,ij->i', delta, nn)
    db = np.einsum('ij,ij->i', delta, bb)
    h = np.interp(ss, s, formation['node_height'])
    chi = np.interp(ss, s, formation['logical_chi'])
    pitch = 1.5*formation['requested_base_width']
    end = np.ones(len(ss)) if metadata['periodic'] else quintic(ss/(1.5*pitch[0]))*quintic((length-ss)/(1.5*pitch[-1]))
    core = (end > .99)&(h > .020)
    sections = {}
    for name, u in [('centre', 0.), ('inner', .22), ('sidewall', .5), ('outer', .75)]:
        take = core&(np.abs(np.abs(logical[:, 2])-u) < .035)
        if take.sum() < 20:
            raise ValueError('Insufficient core samples to verify the fixed coffer section.')
        x = np.column_stack((np.ones(take.sum()), np.cos(2*np.pi*chi[take]), np.cos(4*np.pi*chi[take])))
        beta = np.linalg.lstsq(x, dn[take]/h[take], rcond=None)[0]
        sections[name] = dict(samples=int(take.sum()), harmonic_coefficients_N_over_H=beta.tolist(),
            node_N_over_H=float(beta.sum()), neck_N_over_H=float(beta[0]-beta[1]+beta[2]),
            node_minus_neck_N_over_H=float(2*beta[1]),
            N_physical_quantiles=np.quantile(dn[take], [0., .1, .5, .9, 1.]).tolist(),
            absB_physical_quantiles=np.quantile(np.abs(db[take]), [0., .1, .5, .9, 1.]).tolist())
    centre, wall = sections['centre'], sections['sidewall']
    pocket = wall['neck_N_over_H']-centre['neck_N_over_H']
    checks = dict(centre_node_to_interval_contrast_at_least_half_H=centre['node_minus_neck_N_over_H'] >= .50,
                  interval_centre_at_or_below_005H=centre['neck_N_over_H'] <= .05,
                  continuous_sidewall_neck_above_025H=wall['neck_N_over_H'] >= .25,
                  enclosed_interval_depth_above_035H=pocket >= .35,
                  transverse_node_centre_above_045H=centre['node_N_over_H'] >= .45)
    return dict(passed=all(checks.values()), checks=checks, sections=sections,
                enclosed_interval_depth_over_H=float(pocket),
                median_nominal_H=float(np.median(formation['node_height'])),
                fitted_median_centre_node_interval_contrast=float(centre['node_minus_neck_N_over_H']*np.median(formation['node_height'])),
                intended_node_N=NODE_N.tolist(), intended_neck_N=NECK_N.tolist(),
                scope='Numerical forming-frame structure gate on one fixed section after two causal local CC passes; not image beauty, native collision or exact surface-depth certificate.')
