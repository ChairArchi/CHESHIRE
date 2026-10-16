"""Geometry-selected, finite daughter splits in existing parent ribbons.

The event locations come from actual mature radial lobes along material t.
A signed two-daughter cross-section is zero, with zero longitudinal slope,
at both event endpoints.  Balanced V/E/F coupling returns detail only.
"""
from pathlib import Path
import importlib.util

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


FLOW_PATH = Path(__file__).resolve().with_name('coupled_flow_detail.py')
_spec = importlib.util.spec_from_file_location('branch_balanced_flow_helpers', FLOW_PATH)
flow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flow)
CHUNK = 65536


def helper_paths():
    return [FLOW_PATH]


def prepare_events(xyz_parent, phase_parent, longitudinal_parent, body_support,
                   height, *, bins=96):
    """Return ``(JSON_safe_event_list, detection_metadata)`` once on G4.

    Samples are grouped by their inherited parent phase cycle and material t.
    Only the observed radial PROFILE is filtered, never source XYZ.  A radial
    maximum and its adjacent radial minima define each finite branch span.
    No periodic axial locations or random seed are introduced.
    """
    x, phase, t, support = map(np.asarray,
        (xyz_parent, phase_parent, longitudinal_parent, body_support))
    height = float(height)
    if (x.ndim != 2 or x.shape[1] != 3 or not len(x) or
            any(value.shape != (len(x),) for value in (phase, t, support)) or
            not all(np.isfinite(value).all() for value in (x, phase, t, support)) or
            height <= 0. or not np.isfinite(height) or bins < 16):
        raise ValueError('Actual finite parent XYZ/phase/material t/support and height required.')
    available = support > .9
    if np.count_nonzero(available) < 32:
        return [], dict(events=0, reason='Insufficient actual source-body samples.')
    full_lo, full_hi = float(t[available].min()), float(t[available].max())
    full_span = full_hi-full_lo
    if full_span <= 0.:
        raise ValueError('Material longitudinal coordinate has no span.')
    lo, hi = full_lo+.08*full_span, full_hi-.08*full_span
    centres = lo+(np.arange(bins)+.5)*(hi-lo)/bins
    index = np.clip(np.floor((t-lo)/(hi-lo)*bins).astype(np.int64), 0, bins-1)
    cycle = np.floor(phase/(2*np.pi)+.5).astype(np.int64)
    offset = phase-2*np.pi*cycle
    radial = np.linalg.norm(x[:, :2], axis=1)
    available &= (t >= lo) & (t <= hi) & (np.abs(offset) < 2.4)
    events, profiles = [], []
    for parent_cycle in np.unique(cycle[available]):
        selected = available & (cycle == parent_cycle)
        radius_profile, phase_centre = np.full(bins, np.nan), np.full(bins, np.nan)
        counts = np.bincount(index[selected], minlength=bins)
        for row in np.flatnonzero(counts >= 3):
            ids = np.flatnonzero(selected & (index == row))
            rr = radial[ids]
            upper = rr >= np.quantile(rr, .7)
            radius_profile[row] = np.quantile(rr, .8)
            # Follow the actual outward ridge within this inherited cycle;
            # nominal phase only supplies its association, not its position.
            phase_centre[row] = np.clip(np.median(offset[ids[upper]]), -.65, .65)
        measured = np.isfinite(radius_profile)
        if measured.sum() < max(16, bins//3):
            profiles.append(dict(parent_cycle=int(parent_cycle), observed_bins=int(measured.sum()), events=0))
            continue
        first, last = np.flatnonzero(measured)[[0, -1]]
        grid = np.arange(first, last+1)
        signal = gaussian_filter1d(np.interp(grid, np.flatnonzero(measured), radius_profile[measured]),
                                   1.25, mode='nearest')
        centreline = gaussian_filter1d(np.interp(grid, np.flatnonzero(measured), phase_centre[measured]),
                                       1.25, mode='nearest')
        contrast = float(np.quantile(signal, .9)-np.quantile(signal, .1))
        threshold = max(.0015*height, .12*contrast)
        peaks, properties = find_peaks(signal, prominence=threshold, distance=max(4, bins//16))
        minima, _ = find_peaks(-signal)
        minima = np.unique(np.r_[0, minima, len(signal)-1])
        before = len(events)
        prominence_max = float(properties['prominences'].max(initial=0.))
        for peak, prominence in zip(peaks, properties['prominences']):
            left_candidates, right_candidates = minima[minima < peak], minima[minima > peak]
            if not len(left_candidates) or not len(right_candidates):
                continue
            left, right = int(left_candidates[-1]), int(right_candidates[0])
            ta, tb = float(centres[first+left]), float(centres[first+right])
            if tb-ta < .035*full_span or right-left < 5:
                continue
            sample_t = centres[first+left:first+right+1]
            second = np.gradient(np.gradient(signal[left:right+1], sample_t), sample_t)
            events.append(dict(parent_cycle=int(parent_cycle), t_start=ta, t_end=tb,
                t_peak=float(centres[first+peak]), radial_peak=float(signal[peak]),
                radial_prominence=float(prominence),
                strength=float(.4+.6*prominence/max(prominence_max, 1e-30)),
                centre_t=sample_t.tolist(), centre_phase_offset=centreline[left:right+1].tolist(),
                observed_samples=int(counts[first+left:first+right+1].sum()),
                radial_second_derivative_min=float(second.min()),
                endpoint_radii=[float(signal[left]), float(signal[right])]))
        profiles.append(dict(parent_cycle=int(parent_cycle), observed_bins=int(measured.sum()),
            radial_contrast=contrast, prominence_threshold=threshold, events=len(events)-before))
    metadata = dict(implementation='ACTUAL_PARENT_RADIAL_LOBE_BRANCH_EVENTS_V1',
        events=len(events), bins=int(bins), material_domain=[full_lo, full_hi],
        measured_domain=[lo, hi], profiles=profiles,
        detection='Actual outward radial 80th-percentile profile in inherited phase-cycle/material-t bins; scalar Gaussian sigma1.25; radial peak prominence max(.0015H,.12*profile contrast); nearest radial minima delimit spans.',
        ridge_position='Measured upper-radial-quantile median phase offset per material bin, constrained inside its parent cycle; scalar profile interpolation only.',
        no_periodic_axial_seed=True, source_XYZ_changed=False,
        parent_xyz_sha256=flow._hash(x), parent_phase_sha256=flow._hash(phase),
        parent_longitudinal_sha256=flow._hash(t),
        limitation='Radial source-body ridge/lobe detector, not a generic curvature skeleton or a global topology branch operation. Event samples combine reflected quadrants of the same inherited phase family.')
    return events, metadata


def _quintic(value):
    value = np.clip(value, 0., 1.)
    return value**3*(10.-15.*value+6.*value**2)


def branch_field(phase, longitudinal, events, *, separation_phase=1.05,
                 cross_halfwidth_phase=.50):
    """Dimensionless signed profile; exact zero outside each finite event."""
    phase, longitudinal = np.asarray(phase), np.asarray(longitudinal)
    if phase.shape != longitudinal.shape:
        raise ValueError('Matching phase and material t samples required.')
    result = np.zeros_like(phase, dtype=float)
    cycle = np.floor(phase/(2*np.pi)+.5).astype(np.int64)
    for event in events:
        a, b = float(event['t_start']), float(event['t_end'])
        if b <= a:
            raise ValueError('Branch event endpoints must be increasing.')
        selected = ((cycle == int(event['parent_cycle'])) &
                    (longitudinal > a) & (longitudinal < b))
        ids = np.flatnonzero(selected)
        if not len(ids):
            continue
        s = (longitudinal[ids]-a)/(b-a)
        envelope = np.sin(np.pi*s)**2
        separation = separation_phase*envelope
        centre = np.interp(longitudinal[ids], event['centre_t'], event['centre_phase_offset'])
        nominal = phase[ids]-2*np.pi*int(event['parent_cycle'])
        u = nominal-centre
        gaussian = lambda value: np.exp(-.5*(value/cross_halfwidth_phase)**2)
        split = .5*(gaussian(u-separation)+gaussian(u+separation)-2.*gaussian(u))
        transverse = _quintic((np.pi-np.abs(nominal))/.45)
        result[ids] += float(event['strength'])*envelope*transverse*split
    return result


def split_detail(xyz_parent, faces_parent, faces_child, edges, degree,
                 phase_parent, body_support, height, mirror_pairs=None, *,
                 gain=1.0, maximum_height_fraction=.0025,
                 longitudinal_parent=None, events=None, amplitude_fraction=.15,
                 separation_phase=1.05, cross_halfwidth_phase=.50):
    """Return balanced ``(detail_delta_child, metadata)`` on existing IDs.

    ``events`` should be prepared once from the mature G4 source. Material t
    is carried through actual V/E/F IDs along with inherited unwrapped phase.
    Fresh physical phase widths budget the signed split cross-section.
    """
    x, q, child, edges, degree = map(np.asarray,
        (xyz_parent, faces_parent, faces_child, edges, degree))
    phase, support = np.asarray(phase_parent), np.asarray(body_support)
    longitudinal = np.asarray(longitudinal_parent)
    height, gain, maximum_height_fraction, amplitude_fraction = map(float,
        (height, gain, maximum_height_fraction, amplitude_fraction))
    if (x.ndim != 2 or x.shape[1] != 3 or not len(x) or q.ndim != 2 or
            q.shape[1] != 4 or not len(q) or q.dtype.kind not in 'iu' or
            not all(np.isfinite(v).all() for v in (x, phase, support, longitudinal))):
        raise ValueError('Finite actual parent XYZ, quads, phase, support and material t required.')
    nv, nf, ne = len(x), len(q), len(edges)
    if (q.min() < 0 or q.max() >= nv or edges.shape != (ne, 2) or not ne or
            edges.dtype.kind not in 'iu' or edges.min() < 0 or edges.max() >= nv or
            child.shape != (4*nf, 4) or child.dtype.kind not in 'iu' or
            any(v.shape != (nv,) for v in (degree, phase, support, longitudinal)) or
            np.any(degree < 3) or np.any(support < 0.) or np.any(support > 1.)):
        raise ValueError('Matching actual closed-quad V/E/F inputs and support [0,1] required.')
    if (not np.isfinite([height, gain, maximum_height_fraction, amplitude_fraction,
                         separation_phase, cross_halfwidth_phase]).all() or
            min(height, maximum_height_fraction, separation_phase, cross_halfwidth_phase) <= 0. or
            min(gain, amplitude_fraction) < 0.):
        raise ValueError('Finite positive scales and nonnegative relief strength required.')
    detection = None
    if events is None:
        events, detection = prepare_events(x, phase, longitudinal, support, height)
    if not isinstance(events, (list, tuple)):
        raise ValueError('Prepared branch events must be a concrete list.')
    fe = child[:, 2].reshape(nf, 4)-nv
    if (fe.min() < 0 or fe.max() >= ne or
            not np.array_equal(degree, np.bincount(q.ravel(), minlength=nv)) or
            not np.array_equal(degree, np.bincount(edges.ravel(), minlength=nv)) or
            not np.all(np.bincount(fe.ravel(), minlength=ne) == 2)):
        raise ValueError('Actual closed parent incidence differs.')
    normals, g2 = np.empty((nf, 3)), np.zeros(nf)
    invalid = 0
    for start in range(0, nf, CHUNK):
        stop = min(start+CHUNK, nf)
        parent = q[start:stop]
        rows = child[4*start:4*stop].reshape(-1, 4, 4)
        endpoints = np.sort(np.stack((parent, np.roll(parent, -1, axis=1)), axis=-1), axis=-1)
        if (not np.array_equal(rows[:, :, 1], parent) or
                not np.all(rows[:, :, 3] == (nv+ne+np.arange(start, stop))[:, None]) or
                not np.array_equal(rows[:, :, 0]-nv, np.roll(fe[start:stop], 1, axis=1)) or
                not np.array_equal(edges[fe[start:stop]], endpoints)):
            raise ValueError('Saved actual child V/E/F IDs differ.')
        p = x[parent]
        rel = p-p.mean(axis=1)[:, None]
        newell = np.cross(rel, np.roll(rel, -1, axis=1)).sum(axis=1)
        if np.any(np.linalg.norm(newell, axis=1) == 0.):
            raise ValueError('Degenerate actual parent normal; no repair.')
        normals[start:stop] = flow._unit(newell)
        e1, e2 = p[:, 1]-p[:, 3], p[:, 2]-p[:, 0]
        a, b, c = (np.einsum('ij,ij->i', aa, bb) for aa, bb in ((e1,e1),(e1,e2),(e2,e2)))
        determinant = a*c-b*b
        ratio = np.divide(determinant, a*c, out=np.zeros_like(a), where=a*c > 0.)
        valid = (determinant > 0.) & (ratio > 1e-10)
        d1, d2 = phase[parent[:,1]]-phase[parent[:,3]], phase[parent[:,2]]-phase[parent[:,0]]
        block = np.divide(c*d1*d1-2*b*d1*d2+a*d2*d2, determinant,
                          out=np.zeros_like(a), where=valid)
        valid &= np.isfinite(block) & (block >= 0.)
        invalid += int(np.count_nonzero(~valid))
        block[~valid] = 0.
        g2[start:stop] = block
    left, right = np.full(ne, nf, np.int64), np.full(ne, -1, np.int64)
    face_ids = np.arange(nf)
    for corner in range(4):
        np.minimum.at(left, fe[:,corner], face_ids)
        np.maximum.at(right, fe[:,corner], face_ids)
    if np.any(left == right):
        raise ValueError('Parent edge repeats inside one face.')
    mean_normal = flow._sum(normals, q, nv)/degree[:,None]
    nvect = flow._unit(mean_normal)
    variation = np.clip(1.-np.linalg.norm(mean_normal,axis=1),0.,1.)
    gradient = np.sqrt(flow._sum(g2,q,nv)/degree)
    width = np.divide(1.8, gradient, out=np.full(nv,.08*height),where=gradient>0.)
    width = np.minimum(width,.08*height)
    cap = maximum_height_fraction*height
    amplitude = np.minimum(gain*amplitude_fraction*width,cap)/(1.+1.5*variation)
    pe, pf = phase[edges].mean(1), flow._face_mean(phase,q)
    te, tf = longitudinal[edges].mean(1), flow._face_mean(longitudinal,q)
    se, sf = support[edges].mean(1), flow._face_mean(support,q)
    ae, af = amplitude[edges].mean(1), flow._face_mean(amplitude,q)
    field_args=dict(separation_phase=separation_phase,cross_halfwidth_phase=cross_halfwidth_phase)
    vv = amplitude*support*branch_field(phase,longitudinal,events,**field_args)
    ve = ae*se*branch_field(pe,te,events,**field_args)
    vf = af*sf*branch_field(pf,tf,events,**field_args)
    df = normals*vf[:,None]
    de = (df[left]+df[right])/4.+(normals[left]+normals[right])/2.*(.5*ve)[:,None]
    dv = flow._sum(df,q,nv)/(degree*degree)[:,None]+nvect*((1.-1./degree)*vv)[:,None]
    delta = np.concatenate((dv,de,df))
    fcap=af*sf
    limits=np.minimum(cap,np.concatenate((
        flow._sum(fcap,q,nv)/(degree*degree)+(1.-1./degree)*amplitude*support,
        (fcap[left]+fcap[right])/4.+.5*ae*se,fcap)))
    symmetry='Caller responsibility.'
    if mirror_pairs is not None:
        delta,limits=flow._reflection(delta,limits,mirror_pairs)
        symmetry='Canonical actual CHILD X/Y ID transport; conservative orbit bound.'
    norm=np.linalg.norm(delta,axis=1)
    delta*=np.minimum(1.,np.divide(limits,norm,out=np.ones_like(norm),where=norm>0.))[:,None]
    norm=np.linalg.norm(delta,axis=1)
    if not np.isfinite(delta).all() or np.max(norm-limits,initial=0.)>1e-12*height:
        raise ValueError('Invalid new branch relief budget.')
    metadata=dict(implementation='MEASURED_PARENT_FINITE_DAUGHTER_SPLIT_V1',
        gain=gain,amplitude_fraction=amplitude_fraction,maximum_height_fraction=maximum_height_fraction,
        separation_phase=separation_phase,cross_halfwidth_phase=cross_halfwidth_phase,
        events=list(events),event_count=len(events),event_detection=detection,
        parent_vertices=nv,parent_faces=nf,parent_edges=ne,child_vertices=len(delta),
        maximum_displacement=float(norm.max(initial=0.)),displacement_quantiles=flow._quantiles(norm),
        physical_parent_width_quantiles=flow._quantiles(width),invalid_gram_faces=invalid,
        moved_vertices=int(np.count_nonzero(norm)),
        branch_profile='s=(t-start)/(end-start); envelope=sin(pi*s)^2; separation=1.05*envelope; signed=.5*envelope*(G(u-sep)+G(u+sep)-2G(u)); G=exp(-.5*(u/.50)^2); event strength and smooth cycle-edge support multiply it.',
        endpoint_continuity='Both daughter centres coincide with the measured parent trunk at each actual lobe endpoint; separation and its first derivative are zero. Signed split displacement and its first longitudinal derivative are exactly zero outside/at both endpoints.',
        coupling='df=nf*Af; de=(dfL+dfR)/4+mean(nfL,nfR)*(.5*Ae); dv=sum_incident(df)/degree^2+unit(mean_incident(nf))*((1-1/degree)*Av); constant-field balanced.',
        physical_scale='Fresh actual quad intrinsic unwrapped-parent-phase gradient; width=min(1.8/gradient,.08H); new amplitude min(.15*gain*width,.0025H), with fresh continuous normal-dispersion response.',
        source_XYZ_smoothed=False,output_is_detail_delta=True,topology_changed=False,
        added_subdivision_passes=0,symmetry=symmetry,
        parent_xyz_sha256=flow._hash(x),parent_phase_sha256=flow._hash(phase),
        parent_longitudinal_sha256=flow._hash(longitudinal),detail_delta_sha256=flow._hash(delta),
        local_import_dependencies=[str(FLOW_PATH)],
        limitations='A geometric ridge bifurcation on the existing surface, not a new topological genus or separate branch mesh. Radial event detection is source-body specific. No global collision certificate or aesthetic success inferred.')
    return delta,metadata
