"""Visible meso-scale chevron pleats inside broad mature ribbon flanks.

This is a different directional morphology from the earlier inherited-phase
harmonics and daughter-lobe split.  Axial pleat crests sweep across each broad
flank in a V/fan pattern, with raised crowns and deep signed troughs.  Parent
crest/groove lines have zero requested relief.  Source XYZ is never averaged.
"""
from pathlib import Path
import importlib.util

import numpy as np


FLOW_PATH = Path(__file__).resolve().with_name('coupled_flow_detail.py')
_spec = importlib.util.spec_from_file_location('visible_pleat_balanced_helpers', FLOW_PATH)
flow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flow)
CHUNK = 65536


def helper_paths():
    return [FLOW_PATH]


def pleat_field(phase, longitudinal, *, wavelength_height_fraction=.020,
                chevron_gain=2.2, secondary_fraction=.30, chevron_rounding=.12):
    """Dimensionless continuous signed relief and its broad flank envelope."""
    phase, longitudinal = np.asarray(phase), np.asarray(longitudinal)
    if phase.shape != longitudinal.shape:
        raise ValueError('Matching inherited phase and longitudinal samples required.')
    wrapped = np.arctan2(np.sin(phase), np.cos(phase))
    across = np.sqrt(wrapped*wrapped+chevron_rounding**2)-chevron_rounding
    psi = (2*np.pi/wavelength_height_fraction)*longitudinal+chevron_gain*across
    primary = np.cos(psi)
    # The smaller fold inhabits the crown of the wider pleat.  The primary
    # negative trough keeps its full depth instead of becoming surface noise.
    crown = (.5+.5*primary)**2
    secondary = np.cos(2*psi+.2*np.sin(psi))*crown
    profile = (primary+secondary_fraction*secondary)/(1.+secondary_fraction)
    flank = np.sin(phase)**2
    return flank*profile, flank


def split_detail(xyz_parent, faces_parent, faces_child, edges, degree,
                 phase_parent, body_support, height, mirror_pairs=None, *,
                 longitudinal_parent=None, gain=1.0,
                 maximum_height_fraction=.0035, wavelength_height_fraction=.020,
                 chevron_gain=2.2, secondary_fraction=.30, chevron_rounding=.12):
    """Return ``(child_detail_delta, metadata)`` in actual V/E/F ID order.

    Material t is dimensionless in the established column chart; its physical
    gradient is measured on the incoming mature surface.  H*t therefore
    defines the nominal axial distance and wavelength is ``fraction*H``.
    The physical cap allows a wave slope of order one: .5 times 1.8/|grad psi|.
    It is intentionally large enough to form actual meso-scale folds.
    """
    x, q, child, edges, degree = map(np.asarray,
        (xyz_parent, faces_parent, faces_child, edges, degree))
    phase, support = np.asarray(phase_parent), np.asarray(body_support)
    if longitudinal_parent is None:
        raise ValueError('Actual inherited material longitudinal_parent is required.')
    longitudinal = np.asarray(longitudinal_parent)
    height, gain, maximum_height_fraction, wavelength_height_fraction = map(float,
        (height, gain, maximum_height_fraction, wavelength_height_fraction))
    chevron_gain, secondary_fraction, chevron_rounding = map(float,
        (chevron_gain, secondary_fraction, chevron_rounding))
    if (x.ndim != 2 or x.shape[1] != 3 or x.dtype.kind != 'f' or not len(x) or
            q.ndim != 2 or q.shape[1] != 4 or not len(q) or q.dtype.kind not in 'iu' or
            not all(np.isfinite(v).all() for v in (x, phase, support, longitudinal))):
        raise ValueError('Finite actual parent XYZ/quads/phase/material t/support required.')
    nv, nf, ne = len(x), len(q), len(edges)
    if (q.min() < 0 or q.max() >= nv or edges.shape != (ne, 2) or not ne or
            edges.dtype.kind not in 'iu' or edges.min() < 0 or edges.max() >= nv or
            np.any(edges[:,0] >= edges[:,1]) or child.shape != (4*nf,4) or
            child.dtype.kind not in 'iu' or
            any(value.shape != (nv,) for value in (phase,support,longitudinal,degree)) or
            np.any(degree < 3) or np.any(support < 0.) or np.any(support > 1.)):
        raise ValueError('Actual closed-quad parent/child incidence and support [0,1] required.')
    if (not np.isfinite([height,gain,maximum_height_fraction,wavelength_height_fraction,
                         chevron_gain,secondary_fraction,chevron_rounding]).all() or
            min(height,maximum_height_fraction,wavelength_height_fraction,chevron_rounding) <= 0. or
            min(gain,chevron_gain,secondary_fraction) < 0.):
        raise ValueError('Finite positive physical scales and nonnegative field strengths required.')
    fe = child[:,2].reshape(nf,4)-nv
    if (fe.min() < 0 or fe.max() >= ne or
            not np.array_equal(degree,np.bincount(q.ravel(),minlength=nv)) or
            not np.array_equal(degree,np.bincount(edges.ravel(),minlength=nv)) or
            not np.all(np.bincount(fe.ravel(),minlength=ne)==2)):
        raise ValueError('Supplied actual closed parent valences/edge incidences differ.')
    normals = np.empty((nf,3))
    phase_g2, pleat_g2, axial_g2 = (np.zeros(nf) for _ in range(3))
    invalid = 0
    axial_frequency = 2*np.pi/wavelength_height_fraction
    for start in range(0,nf,CHUNK):
        stop=min(start+CHUNK,nf)
        parent=q[start:stop]
        rows=child[4*start:4*stop].reshape(-1,4,4)
        endpoints=np.sort(np.stack((parent,np.roll(parent,-1,axis=1)),axis=-1),axis=-1)
        if (not np.array_equal(rows[:,:,1],parent) or
                not np.all(rows[:,:,3]==(nv+ne+np.arange(start,stop))[:,None]) or
                not np.array_equal(rows[:,:,0]-nv,np.roll(fe[start:stop],1,axis=1)) or
                not np.array_equal(edges[fe[start:stop]],endpoints)):
            raise ValueError('Actual saved child V/E/F birth correspondence differs.')
        p=x[parent]
        relative=p-p.mean(axis=1)[:,None]
        newell=np.cross(relative,np.roll(relative,-1,axis=1)).sum(axis=1)
        if np.any(np.linalg.norm(newell,axis=1)==0.):
            raise ValueError('Degenerate actual parent polygon normal; no fallback.')
        normals[start:stop]=flow._unit(newell)
        e1,e2=p[:,1]-p[:,3],p[:,2]-p[:,0]
        a,b,c=(np.einsum('ij,ij->i',aa,bb) for aa,bb in ((e1,e1),(e1,e2),(e2,e2)))
        determinant,ac=a*c-b*b,a*c
        ratio=np.divide(determinant,ac,out=np.zeros_like(a),where=ac>0.)
        valid=(determinant>0.)&(ratio>=1e-10)
        def gradient(value):
            d1=value[parent[:,1]]-value[parent[:,3]]
            d2=value[parent[:,2]]-value[parent[:,0]]
            aa=np.divide(c*d1-b*d2,determinant,out=np.zeros_like(a),where=valid)
            bb=np.divide(a*d2-b*d1,determinant,out=np.zeros_like(a),where=valid)
            return aa[:,None]*e1+bb[:,None]*e2
        gp,gt=gradient(phase),gradient(longitudinal)
        wrapped=np.arctan2(np.sin(phase[parent].mean(axis=1)),np.cos(phase[parent].mean(axis=1)))
        transverse_derivative=chevron_gain*wrapped/np.sqrt(wrapped*wrapped+chevron_rounding**2)
        gpsi=axial_frequency*gt+transverse_derivative[:,None]*gp
        valid&=np.isfinite(gp).all(axis=1)&np.isfinite(gt).all(axis=1)&np.isfinite(gpsi).all(axis=1)
        invalid+=int(np.count_nonzero(~valid))
        gp[~valid]=0.;gt[~valid]=0.;gpsi[~valid]=0.
        phase_g2[start:stop]=np.einsum('ij,ij->i',gp,gp)
        pleat_g2[start:stop]=np.einsum('ij,ij->i',gpsi,gpsi)
        axial_g2[start:stop]=np.einsum('ij,ij->i',gt,gt)
    left,right=np.full(ne,nf,np.int64),np.full(ne,-1,np.int64)
    ids=np.arange(nf)
    for corner in range(4):
        np.minimum.at(left,fe[:,corner],ids)
        np.maximum.at(right,fe[:,corner],ids)
    if np.any(left==right):
        raise ValueError('Parent edge repeats inside a single face.')
    normal_mean=flow._sum(normals,q,nv)/degree[:,None]
    vertex_normals=flow._unit(normal_mean)
    dispersion=np.clip(1.-np.linalg.norm(normal_mean,axis=1),0.,1.)
    grad_phase=np.sqrt(flow._sum(phase_g2,q,nv)/degree)
    grad_pleat=np.sqrt(flow._sum(pleat_g2,q,nv)/degree)
    grad_t=np.sqrt(flow._sum(axial_g2,q,nv)/degree)
    width_pleat=np.divide(1.8,grad_pleat,out=np.full(nv,.08*height),where=grad_pleat>0.)
    width_parent=np.divide(1.8,grad_phase,out=np.full(nv,.08*height),where=grad_phase>0.)
    width_pleat=np.minimum(width_pleat,.08*height)
    width_parent=np.minimum(width_parent,.08*height)
    cap=height*maximum_height_fraction
    amplitude=np.minimum(np.minimum(gain*cap,.5*width_pleat),.22*width_parent)
    amplitude/=1.+.5*dispersion
    pe,pf=phase[edges].mean(1),flow._face_mean(phase,q)
    te,tf=longitudinal[edges].mean(1),flow._face_mean(longitudinal,q)
    se,sf=support[edges].mean(1),flow._face_mean(support,q)
    ae,af=amplitude[edges].mean(1),flow._face_mean(amplitude,q)
    field_args=dict(wavelength_height_fraction=wavelength_height_fraction,
        chevron_gain=chevron_gain,secondary_fraction=secondary_fraction,chevron_rounding=chevron_rounding)
    fv,flank=pleat_field(phase,longitudinal,**field_args)
    fedge,_=pleat_field(pe,te,**field_args)
    fface,_=pleat_field(pf,tf,**field_args)
    av,aredge,arface=amplitude*support*fv,ae*se*fedge,af*sf*fface
    df=normals*arface[:,None]
    de=(df[left]+df[right])/4.+(normals[left]+normals[right])/2.*(.5*aredge)[:,None]
    dv=flow._sum(df,q,nv)/(degree*degree)[:,None]
    dv+=vertex_normals*((1.-1./degree)*av)[:,None]
    delta=np.concatenate((dv,de,df))
    fcap=af*sf
    limits=np.minimum(cap*max(1.,gain),np.concatenate((
        flow._sum(fcap,q,nv)/(degree*degree)+(1.-1./degree)*amplitude*support,
        (fcap[left]+fcap[right])/4.+.5*ae*se,fcap)))
    symmetry='Caller responsibility.'
    if mirror_pairs is not None:
        delta,limits=flow._reflection(delta,limits,mirror_pairs)
        symmetry='Canonical actual CHILD X/Y ID vector transport and conservative orbit bound.'
    norm=np.linalg.norm(delta,axis=1)
    delta*=np.minimum(1.,np.divide(limits,norm,out=np.ones_like(norm),where=norm>0.))[:,None]
    norm=np.linalg.norm(delta,axis=1)
    if not np.isfinite(delta).all() or np.max(norm-limits,initial=0.)>1e-12*height:
        raise ValueError('Nonfinite or over-budget visible pleat relief.')
    broad=(support>.9)&(flank>.75)&(dispersion<.15)
    metadata=dict(implementation='VISIBLE_MESO_CHEVRON_FLANK_PLEATS_V1',
        gain=gain,height=height,maximum_height_fraction=maximum_height_fraction,
        wavelength_height_fraction=wavelength_height_fraction,nominal_physical_wavelength=wavelength_height_fraction*height,
        chevron_gain=chevron_gain,secondary_fraction=secondary_fraction,chevron_rounding=chevron_rounding,
        requested_height_cap=cap,maximum_displacement=float(norm.max(initial=0.)),
        displacement_quantiles=flow._quantiles(norm),parent_amplitude_quantiles=flow._quantiles(amplitude),
        broad_flank_controls=int(np.count_nonzero(broad)),
        broad_flank_amplitude_quantiles=flow._quantiles(amplitude[broad]) if np.any(broad) else [],
        broad_flank_requested_relief_quantiles=flow._quantiles(np.abs(av[broad])) if np.any(broad) else [],
        actual_pleat_width_quantiles=flow._quantiles(width_pleat),
        actual_parent_width_quantiles=flow._quantiles(width_parent),
        material_t_gradient_quantiles=flow._quantiles(grad_t),
        invalid_gram_faces=invalid,moved_vertices=int(np.count_nonzero(norm)),
        parent_vertices=nv,parent_edges=ne,parent_faces=nf,child_vertices=len(delta),
        field='psi=(2*pi/wavelength_height_fraction)*material_t+chevron_gain*(sqrt(wrapped_parent_phase^2+rounding^2)-rounding); flank=sin(parent_phase)^2; primary=cos(psi); secondary=cos(2psi+.2sin(psi))*(.5+.5cos(psi))^2; signed=flank*(primary+secondary_fraction*secondary)/(1+secondary_fraction).',
        physical_metric='Actual parent quad Gram solve for vector grad(material_t) and grad(parent_phase); grad(psi)=axial_frequency*grad(t)+chevron_gain*wrapped/sqrt(wrapped^2+rounding^2)*grad(phi). Incident RMS gradient sets width=1.8/gradient.',
        amplitude_budget='min(gain*H*maximum_height_fraction,.5*actual_pleat_width,.22*actual_parent_width)/(1+.5*normal_dispersion); deliberately permits wave slopes of order one for visible folding.',
        coupling='df=nf*Af; de=(dfL+dfR)/4+mean(nfL,nfR)*(.5*Ae); dv=sum_incident(df)/degree^2+unit(mean_incident(nf))*((1-1/degree)*Av); constant signed field has no V/E/F cell-centre contrast.',
        source_XYZ_smoothed=False,fresh_normals=True,output_is_detail_delta=True,
        topology_changed=False,added_subdivision_passes=0,symmetry=symmetry,
        parent_xyz_sha256=flow._hash(x),parent_phase_sha256=flow._hash(phase),
        parent_longitudinal_sha256=flow._hash(longitudinal),detail_delta_sha256=flow._hash(delta),
        local_import_dependencies=[str(FLOW_PATH)],
        limitations='Large signed local surface folds; local first-order phase width does not certify global self-intersection freedom or semantic end/root repair. Broad-flank amplitudes are control-sample statistics, not surface-area statistics. Visual visibility and regressions require the actual matched render.')
    return delta,metadata
