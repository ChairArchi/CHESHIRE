"""Finish one actual new G5 with existing finite Mandel and actual Tissue relief.

Only the two immutable source assets are reused. Host geometry, normals,
one-ring shape evidence, physical material metrics, guards and recovery are
evaluated on this input. No historical column XYZ/atlas is loaded, no host
smoothing is performed, and the existing Tissue plugin is not invoked anew.
The Tissue adapter is a single-valued height graph, not a full-XYZ graft.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gc
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
from scipy.interpolate import RectBivariateSpline

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'src'))
from cheshire import adaptive_ornament as ornament
from cheshire.ornament_analysis import smooth01

SCHEMA = 'CHESHIRE_SELECTIVE_ACTUAL_HOST_MANDEL_TISSUE_FINISH_V1'
DEFAULT_PROFILE = Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/'
                       'trial12c_all_small_mandel_replacement/MANDELBULB_PROFILE.json')
DEFAULT_TISSUE = Path('E:/CHESHIRE_DATA/experiments/generation_mirror_hybrid_20261016/'
                      'paper_tissue/ACTUAL_TISSUE_RECEIPT.json')


@dataclass(frozen=True)
class FinishRecipe:
    mandel_period: float = .48
    class_amplitudes: tuple = (.020, .022, .010, .023, .026)
    tissue_priorities: tuple = (.15, .30, .18, .72, .86)
    tissue_longitudinal_period: float = .70
    tissue_transverse_period: float = .70
    tissue_amplitude: float = .055
    shape_radius: float = .20
    waist_feather_t: float = .012
    cap_feather_t: float = .025
    normal_safety_ratio: float = .35
    chunk_size: int = 65536
    max_faces: int = 3_500_000
    max_recovery_passes: int = 32

    def validate(self):
        positive = (self.mandel_period, self.tissue_longitudinal_period,
                    self.tissue_transverse_period, self.shape_radius,
                    self.waist_feather_t, self.cap_feather_t, self.normal_safety_ratio)
        if min(positive) <= 0 or not np.isfinite(positive).all():
            raise ValueError('Finite positive physical periods and guard widths required.')
        if len(self.class_amplitudes) != 5 or len(self.tissue_priorities) != 5:
            raise ValueError('Five shape-class coefficients required.')
        if min(self.class_amplitudes) < 0 or self.tissue_amplitude < 0:
            raise ValueError('Relief amplitudes must be nonnegative.')
        if min(self.tissue_priorities) < 0 or max(self.tissue_priorities) > 1:
            raise ValueError('Tissue priorities must be in [0,1].')
        if min(self.chunk_size, self.max_faces, self.max_recovery_passes) < 1:
            raise ValueError('Positive execution budgets required.')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False)+'\n', encoding='utf8')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def ah(value):
    value = np.asarray(value)
    digest = hashlib.sha256()
    # All arrays here are C-contiguous NPY or NPZ arrays; hash in bounded rows.
    if not value.flags.c_contiguous:
        value = np.ascontiguousarray(value)
    view = memoryview(value).cast('B')
    for first in range(0, len(view), 8*1024**2):
        digest.update(view[first:first+8*1024**2])
    return digest.hexdigest()


def file_record(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def load_assets(profile_receipt, tissue_receipt):
    pinfo, tinfo = read(profile_receipt), read(tissue_receipt)
    pfile, tfile = Path(pinfo['array_file']), Path(tinfo['height_grid'])
    if sha(pfile) != pinfo['array_file_sha256']:
        raise ValueError('Finite Mandel profile array binding changed.')
    boundary = {}
    with np.load(pfile, allow_pickle=False) as stored:
        for key in ('theta', 'phi', 'radius'):
            item = pinfo['tree'][key]
            value = stored[item['npz_key']]
            if list(value.shape) != item['shape'] or ah(value) != item['sha256']:
                raise ValueError('Finite Mandel boundary changed: '+key)
            boundary[key] = value
    profile = ornament.MandelRadialProfile(**boundary)
    if not tinfo.get('actual_Tissue_call_succeeded') or sha(tfile) != tinfo['height_grid_sha256']:
        raise ValueError('Existing actual Tissue component is not hash verified.')
    with np.load(tfile, allow_pickle=False) as stored:
        uv, height = stored['uv'], stored['height']
    if (uv.ndim != 1 or height.shape != (len(uv), len(uv)) or
            not np.isfinite(height).all() or height.min() < 0 or height.max() > 1+1e-12 or
            not np.all(np.diff(uv) > 0) or uv[0] != 0 or uv[-1] != 1 or
            np.max(np.abs(np.r_[height[0], height[-1], height[:, 0], height[:, -1]])) > 1e-12):
        raise ValueError('Actual normalized Tissue grid must have a zero outer edge.')
    # Also bind the existing source component and exact top-ray provenance.
    extra = {}
    for key in ('source_closed_component', 'exact_top_ray_adapter', 'source_paper_receipt'):
        if key in tinfo:
            entry = tinfo[key]
            if sha(entry['path']) != entry['sha256']:
                raise ValueError('Tissue source provenance changed: '+key)
            extra[key] = entry
    info = dict(
        mandel=dict(receipt=file_record(profile_receipt), arrays=file_record(pfile),
                    profile_sampling_sha256=profile.sha256,
                    evaluated_kernel='cheshire.adaptive_ornament.MandelRadialProfile.sample',
                    finite_boundary_reused=True, new_volumetric_classification=False),
        tissue=dict(receipt=file_record(tissue_receipt), height_grid=file_record(tfile),
                    original_operator=tinfo['actual_operator'], source_provenance=extra,
                    historical_actual_Tissue_call=True, new_Tissue_invocations=0,
                    adapter='Actual component topmost-ray height graph, cubic interpolation, zero outer taper.',
                    full_XYZ_graft=False, source_handles_transferred=False))
    return profile, RectBivariateSpline(uv, uv, height, s=0), info


def load_host(source, max_faces):
    info = read(source/'generation.json')
    for name, key in (('control_quad.npz', 'control_file_sha256'),
                      ('evidence.npz', 'evidence_file_sha256')):
        if sha(source/name) != info[key]:
            raise ValueError('Actual G5 file binding changed: '+name)
    if not info['checks']['passed'] or info['subdivision_generation'] != 5:
        raise ValueError('Verified actual G5 input required.')
    with np.load(source/'control_quad.npz', allow_pickle=False) as stored:
        host = {key: stored[key] for key in ('xyz', 'faces', 'chart', 'classes')}
        if int(stored['generation']) != 5:
            raise ValueError('Actual saved generation differs.')
    x, q, c = (host[key] for key in ('xyz', 'faces', 'chart'))
    if (x.shape != c.shape or x.ndim != 2 or x.shape[1] != 3 or
            q.ndim != 2 or q.shape[1] != 4 or q.dtype.kind not in 'iu' or
            not len(q) or len(q) > max_faces or q.min() < 0 or q.max() >= len(x) or
            not np.isfinite(x).all() or not np.isfinite(c).all()):
        raise ValueError('Finite valid G5 quads/chart within face budget required.')
    for key, value in (('control_xyz_sha256', x), ('control_faces_sha256', q), ('chart_sha256', c)):
        if key in info['checks'] and ah(value) != info['checks'][key]:
            raise ValueError('Actual saved array differs: '+key)
    with np.load(source/'evidence.npz', allow_pickle=False) as stored:
        pairs = {axis: stored['mirror_'+axis+'_vertex_pairs'] for axis in ('x', 'y')}
    ids = np.arange(len(x))
    for axis, pair in pairs.items():
        if pair.shape != ids.shape or pair.dtype.kind not in 'iu' or not np.array_equal(pair[pair], ids):
            raise ValueError('Actual reflection involution required: '+axis)
    if not np.array_equal(pairs['x'][pairs['y']], pairs['y'][pairs['x']]):
        raise ValueError('Actual X/Y reflection involutions must commute.')
    rep = np.minimum(np.minimum(ids, pairs['x']), np.minimum(pairs['y'], pairs['x'][pairs['y']]))
    return host, info, pairs, rep


def current_shape(x, q, chart, normals, recipe):
    """One-ring measured normal shape operator and material gradients.

    All incident directed face edges are fitted in actual tangent planes.
    Shared edges occur twice, uniformly on this verified closed quad host.
    This local diagnostic is not the older fixed-radius historical classifier.
    """
    n = len(x)
    e = np.zeros_like(x); e[:, 2] = 1
    e -= normals*normals[:, 2, None]
    small = np.linalg.norm(e, axis=1) < .15
    e[small] = np.array([1., 0., 0.])-normals[small]*normals[small, 0, None]
    e /= np.linalg.norm(e, axis=1)[:, None]
    v = np.cross(normals, e)
    A = np.zeros((n, 3)); B = np.zeros((n, 4)); G = np.zeros((n, 4))
    theta = np.arctan2(chart[:, 2], chart[:, 1])
    for first in range(0, len(q), recipe.chunk_size):
        faces = q[first:first+recipe.chunk_size]
        aa, bb = faces.ravel(), np.roll(faces, -1, axis=1).ravel()
        for a, b in ((aa, bb), (bb, aa)):
            dp, dn = x[b]-x[a], normals[b]-normals[a]
            p0, p1 = np.einsum('ij,ij->i', dp, e[a]), np.einsum('ij,ij->i', dp, v[a])
            y0, y1 = -np.einsum('ij,ij->i', dn, e[a]), -np.einsum('ij,ij->i', dn, v[a])
            w = 1/np.maximum(np.einsum('ij,ij->i', dp, dp), 1e-24)
            dt = chart[b, 0]-chart[a, 0]
            da = np.arctan2(np.sin(theta[b]-theta[a]), np.cos(theta[b]-theta[a]))
            for j, value in enumerate((p0*p0*w, p0*p1*w, p1*p1*w)):
                np.add.at(A[:, j], a, value)
            for j, value in enumerate((p0*y0*w, p0*y1*w, p1*y0*w, p1*y1*w)):
                np.add.at(B[:, j], a, value)
            for j, value in enumerate((p0*dt*w, p1*dt*w, p0*da*w, p1*da*w)):
                np.add.at(G[:, j], a, value)
    det = A[:, 0]*A[:, 2]-A[:, 1]**2
    valid = det > 1e-8*np.maximum((A[:, 0]+A[:, 2])**2, 1e-30)
    inv = np.zeros_like(A)
    inv[valid, 0] = A[valid, 2]/det[valid]
    inv[valid, 1] = -A[valid, 1]/det[valid]
    inv[valid, 2] = A[valid, 0]/det[valid]
    s00 = inv[:, 0]*B[:, 0]+inv[:, 1]*B[:, 2]
    s01 = .5*(inv[:, 0]*B[:, 1]+inv[:, 1]*B[:, 3]+inv[:, 1]*B[:, 0]+inv[:, 2]*B[:, 2])
    s11 = inv[:, 1]*B[:, 1]+inv[:, 2]*B[:, 3]
    middle, rad = .5*(s00+s11), np.sqrt((.5*(s00-s11))**2+s01*s01)
    kappa = np.column_stack((middle-rad, middle+rad))
    absk = np.abs(kappa)
    strength = recipe.shape_radius*np.linalg.norm(kappa, axis=1)
    anisotropy = (absk.max(1)-absk.min(1))/np.maximum(absk.sum(1), 1e-12)
    grad_t = np.column_stack((inv[:, 0]*G[:, 0]+inv[:, 1]*G[:, 1],
                              inv[:, 1]*G[:, 0]+inv[:, 2]*G[:, 1]))
    grad_theta = np.column_stack((inv[:, 0]*G[:, 2]+inv[:, 1]*G[:, 3],
                                  inv[:, 1]*G[:, 2]+inv[:, 2]*G[:, 3]))
    gsize = np.linalg.norm(grad_t, axis=1)
    flow_axis = e*(grad_t[:, 0]/np.maximum(gsize, 1e-20))[:, None]+v*(grad_t[:, 1]/np.maximum(gsize, 1e-20))[:, None]
    # Principal directions of the symmetric 2x2 normal shape tensor.
    angle = .5*np.arctan2(2*s01, s00-s11)
    low_angle = angle+np.where(np.abs(middle+rad) > np.abs(middle-rad), np.pi/2, 0.)
    alignment = ((grad_t[:, 0]*np.cos(low_angle)+grad_t[:, 1]*np.sin(low_angle))/np.maximum(gsize, 1e-20))**2
    coherence = np.clip(anisotropy*alignment, 0, 1)*valid
    busy = smooth01((strength-.18)/.95)
    weights = np.column_stack((1-smooth01((strength-.06)/.32),
                               .12+(1-busy)*smooth01((strength-.025)/.25),
                               busy*anisotropy,
                               smooth01((strength-.10)/.65)*(1-anisotropy)*(kappa.prod(1)>0),
                               busy*(1-.55*anisotropy)))
    weights /= weights.sum(1)[:, None]
    del A, B, G, inv, e, v
    gc.collect()
    return dict(weights=weights, kappa=kappa, strength=strength,
                anisotropy=anisotropy, coherence=coherence, flow_axis=flow_axis,
                grad_t_size=gsize, grad_theta_size=np.linalg.norm(grad_theta, axis=1),
                fit_valid=valid)


def physical_material_coordinates(x, chart, shape):
    """Build new physical material metrics from this host's measured gradients."""
    t = chart[:, 0]; lo, hi = float(t.min()), float(t.max())
    edges = np.linspace(lo, hi, 97); centres = .5*(edges[:-1]+edges[1:])
    # Deterministic bounded sample, including the complete range of actual IDs.
    take = np.arange(0, len(t), max(1, len(t)//400_000))
    bins = np.clip(np.searchsorted(edges, t[take], side='right')-1, 0, len(centres)-1)
    long, transverse = np.full(len(centres), np.nan), np.full(len(centres), np.nan)
    height = float(np.ptp(x[:, 2])); median_radius = float(np.median(np.linalg.norm(x[:, :2], axis=1)))
    for j in range(len(centres)):
        ids = take[(bins == j)&shape['fit_valid'][take]]
        if not len(ids):
            continue
        good = shape['grad_t_size'][ids] > 1e-8
        if good.any(): long[j] = np.median(1/shape['grad_t_size'][ids[good]])
        good = shape['grad_theta_size'][ids] > 1e-8
        if good.any(): transverse[j] = np.median(1/shape['grad_theta_size'][ids[good]])
    for a, fallback, lower, upper in ((long, height/(hi-lo), .25*height/(hi-lo), 6*height/(hi-lo)),
                                      (transverse, median_radius, .1*median_radius, 4*median_radius)):
        finite = np.isfinite(a)&(a>0)
        a[:] = np.interp(centres, centres[finite], a[finite]) if finite.any() else fallback
        np.clip(a, max(lower, 1e-5), max(upper, lower), out=a)
    nodes = np.r_[lo, centres, hi]
    metric = np.r_[long[0], long, long[-1]]
    arc = np.r_[0., np.cumsum(.5*(metric[:-1]+metric[1:])*np.diff(nodes))]
    u = np.interp(t, nodes, arc)
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    # A single measured mean circumferential metric avoids phase shear at tiers.
    radius = float(np.median(transverse))
    return np.column_stack((u, theta*radius)), dict(
        material_t_nodes=nodes.tolist(), longitudinal_metric=metric.tolist(),
        integrated_material_arc=arc.tolist(), transverse_metric_by_t=transverse.tolist(),
        transverse_radius=radius, physical_Z_height=height,
        current_geometry_measured=True, historical_atlas_read=False,
        scope='One-ring current material gradients, robust axial-bin medians. Reflected quadrant material coordinates; no geometry warp.')


def protection(chart, guards, recipe):
    t = chart[:, 0]; lo, hi = float(t.min()), float(t.max())
    caps = np.isclose(t, lo, atol=1e-12, rtol=0)|np.isclose(t, hi, atol=1e-12, rtol=0)
    waist = np.zeros(len(t), bool); fade = np.zeros(len(t))
    for guard in guards:
        a, b = map(float, guard['interval'])
        waist |= (t >= a)&(t <= b)
        d = np.maximum(np.maximum(a-t, t-b), 0.)
        fade = np.maximum(fade, 1-smooth01(d/recipe.waist_feather_t))
    end_distance = np.minimum(t-lo, hi-t)
    fade = np.maximum(fade, 1-smooth01(end_distance/recipe.cap_feather_t))
    fade[caps|waist] = 1.
    return caps, waist, fade


def mirror_scalar(value, rep):
    return np.asarray(value)[rep]


def mirror_recovery(x, q, pairs, rep, result, recipe):
    """Canonicalize only new normal increments using actual new reflection IDs."""
    normals = result['normals'][rep].copy()
    ids = np.arange(len(x))
    # The commuting involutions identify each representative's reflection word.
    mx = pairs['x'][rep]; my = pairs['y'][rep]; mxy = pairs['x'][my]
    flipx = ((ids == mx)|(ids == mxy))&(ids != rep)&(ids != my)
    flipy = ((ids == my)|(ids == mxy))&(ids != rep)&(ids != mx)
    normals[flipx, 0] *= -1; normals[flipy, 1] *= -1
    # At reflection-fixed planes the corresponding normal component is zero.
    normals[pairs['x'] == ids, 0] = 0.; normals[pairs['y'] == ids, 1] = 0.
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-30)
    height = result['actual_height'][rep]
    fixed = result['fixed_mask']|result['fixed_mask'][rep]
    delta = normals*height[:, None]; delta[fixed] = 0.
    gain = np.ones(len(x)); counts = []
    for _iteration in range(recipe.max_recovery_passes):
        out = x+delta*gain[:, None]; out[fixed] = x[fixed]
        bad = ornament._bad_faces(out, q, x, recipe.chunk_size)
        counts.append(int(bad.sum()))
        if not bad.any():
            return out, normals, height*gain, gain, counts
        hit = np.zeros(len(x), bool); hit[q[bad].ravel()] = True
        hit |= hit[pairs['x']]|hit[pairs['y']]|hit[pairs['x'][pairs['y']]]
        gain[hit] *= .5
    raise ValueError('Post-reflection decoration-only orientation recovery exhausted.')


def save_array(folder, name, value, records, chunk=65536):
    value = np.asarray(value); path = folder/(name+'.npy')
    arr = np.lib.format.open_memmap(path, mode='w+', dtype=value.dtype, shape=value.shape)
    if value.ndim == 0:
        arr[...] = value
    else:
        for first in range(0, len(value), chunk): arr[first:first+chunk] = value[first:first+chunk]
    arr.flush(); del arr
    records[name] = dict(**file_record(path), shape=list(value.shape), dtype=value.dtype.str,
                         array_sha256=ah(value))
    return np.load(path, mmap_mode='r', allow_pickle=False)


def native_fans(folder, x, q, records, chunk):
    nv, nf = len(x), len(q)
    xp, fp = folder/'NATIVE_XYZ.npy', folder/'NATIVE_FACES.npy'
    xx = np.lib.format.open_memmap(xp, mode='w+', dtype=np.float64, shape=(nv+nf, 3))
    ff = np.lib.format.open_memmap(fp, mode='w+', dtype=np.int64, shape=(4*nf, 3))
    xx[:nv] = x; minimum_area = np.inf; volume = 0.
    for first in range(0, nf, chunk):
        end = min(first+chunk, nf); ids = q[first:end]; p = x[ids]; c = p.mean(1)
        xx[nv+first:nv+end] = c
        tri = np.empty((len(ids), 4, 3), np.int64)
        tri[:, :, 0] = ids; tri[:, :, 1] = np.roll(ids, -1, axis=1)
        tri[:, :, 2] = nv+np.arange(first, end)[:, None]
        ff[4*first:4*end] = tri.reshape(-1, 3)
        b = np.roll(p, -1, axis=1)
        area = .5*np.linalg.norm(np.cross(p-c[:, None], b-c[:, None]), axis=2)
        minimum_area = min(minimum_area, float(area.min()))
        volume += float(np.einsum('fi,fki->fk', c, np.cross(p, b)).sum()/6.)
    xx.flush(); ff.flush()
    for name, path, arr in (('NATIVE_XYZ', xp, xx), ('NATIVE_FACES', fp, ff)):
        records[name] = dict(**file_record(path), shape=list(arr.shape), dtype=arr.dtype.str,
                             array_sha256=ah(arr))
    if minimum_area <= 0 or not np.isfinite(minimum_area) or volume <= 0:
        raise ValueError('Nonpositive native fan area or signed volume.')
    return dict(vertices=nv+nf, triangles=4*nf, minimum_triangle_area=minimum_area,
                signed_volume=volume, native='Actual arithmetic quad-centroid fan',
                closed_topology_inherited_unchanged=True, self_intersection_checked=False)


def run(args):
    started = time.perf_counter(); source, output = args.source_g5.resolve(), args.output.resolve()
    if output.exists(): raise FileExistsError('Preserve existing final output: '+str(output))
    recipe = FinishRecipe(mandel_period=args.mandel_period, tissue_amplitude=args.tissue_amplitude,
                          normal_safety_ratio=args.normal_safety_ratio,
                          max_faces=args.max_faces); recipe.validate()
    host, parent_info, pairs, rep = load_host(source, recipe.max_faces)
    x, q, chart = (host[key] for key in ('xyz', 'faces', 'chart'))
    profile, tissue, assets = load_assets(args.profile.resolve(), args.tissue.resolve())
    source_receipt = args.source_g0.resolve()
    source_info = read(source_receipt); guards = source_info['waist_guards']
    if source_info.get('candidate') != args.id or not source_info['checks']['passed']:
        raise ValueError('Matching verified selected G0 waist receipt required.')
    # Bind the selected source receipt to the actual current pipeline contract.
    pipeline = source.parent.parent/'RECIPE.json'
    if pipeline.exists() and read(pipeline)['recipe']['source_G0_receipt'] != str(source_receipt).replace('\\', '/'):
        actual_path = Path(read(pipeline)['recipe']['source_G0_receipt']).resolve()
        if actual_path != source_receipt: raise ValueError('G5 pipeline belongs to another G0 source.')
    print('MEASURE actual G5', len(x), 'V', len(q), 'Q', flush=True)
    normals = ornament.host_normals(x, q, chunk_size=recipe.chunk_size)
    shape = current_shape(x, q, chart, normals, recipe)
    uv, metric = physical_material_coordinates(x, chart, shape)
    weights = mirror_scalar(shape['weights'], rep)
    coherence = mirror_scalar(shape['coherence'], rep)
    uv = mirror_scalar(uv, rep)
    caps, waist, protected = protection(chart, guards, recipe)
    caps, waist, protected = (mirror_scalar(a, rep) for a in (caps, waist, protected))
    flow = np.maximum(protected, np.clip(.45*weights[:, 2]*coherence+.12*weights[:, 2], 0, .60))
    tissue_height = np.clip(tissue.ev(np.mod(uv[:, 0]/recipe.tissue_longitudinal_period, 1.),
                                     np.mod(uv[:, 1]/recipe.tissue_transverse_period, 1.)), 0., 1.)
    priority = np.clip(weights@np.asarray(recipe.tissue_priorities), 0., .9)
    measured = dict(shape_method='Actual host one-ring tangent normal tensor; five continuous local shape weights, no historical classification cache.',
                    valid_shape_fit_fraction=float(shape['fit_valid'].mean()),
                    shape_weight_mean=weights.mean(0).tolist(),
                    curvature_abs_quantiles=np.quantile(np.abs(shape['kappa']), [0, .5, .9, .99, 1]).tolist(),
                    material_metrics=metric)
    # Keep compact measured diagnostics; discard fitting matrices before topology/recovery.
    compact = {key: shape[key] for key in ('kappa', 'strength', 'anisotropy', 'coherence', 'flow_axis', 'fit_valid')}
    del shape, normals; gc.collect()
    op_recipe = ornament.OrnamentRecipe(mandel_period=recipe.mandel_period,
        class_amplitudes=recipe.class_amplitudes, class_tissue_priorities=recipe.tissue_priorities,
        tissue_amplitude=recipe.tissue_amplitude, valley_amplitude=.004,
        normal_safety_ratio=recipe.normal_safety_ratio, chunk_size=recipe.chunk_size,
        max_faces=recipe.max_faces, max_recovery_passes=recipe.max_recovery_passes)
    print('DEPOSIT existing finite Mandel + actual paper Tissue height on new G5', flush=True)
    result = ornament.apply_adaptive_ornament(x, q, shape_weights=weights, pattern_coordinates=uv,
        profile=profile, recipe=op_recipe, tissue_height=tissue_height, tissue_priority=priority,
        flow_protection=flow, cap_mask=caps)
    budget = weights@np.asarray(recipe.class_amplitudes)
    eligible = ~(caps|waist|(flow == 1))
    safety_diagnostics = dict(
        safety_cap_quantiles=np.quantile(result['safety_cap'], [0, .1, .5, .9, .99, 1]).tolist(),
        intended_Mandel_amplitude_quantiles=np.quantile(budget[eligible], [0, .1, .5, .9, .99, 1]).tolist(),
        actual_desired_height_abs_quantiles=np.quantile(np.abs(result['desired_height'][eligible]), [0, .1, .5, .9, .99, 1]).tolist(),
        eligible_controls=int(eligible.sum()),
        Mandel_amplitude_safety_clamped_fraction=float(np.mean(result['safety_cap'][eligible] < budget[eligible])),
        Tissue_amplitude_safety_clamped_fraction=float(np.mean(result['safety_cap'][eligible] < recipe.tissue_amplitude)),
        explanation='Existing adaptive_ornament shortest-edge / maximum-normal-variation safety formula, unchanged. Only recipe.normal_safety_ratio is configurable.')
    print('SAFETY', json.dumps(safety_diagnostics, allow_nan=False), flush=True)
    raw = x+result['normals']*result['desired_height'][:, None]
    final, used_normals, height, post_gain, post_counts = mirror_recovery(x, q, pairs, rep, result, recipe)
    fixed = caps|waist|(flow == 1)
    if not np.array_equal(final[fixed], x[fixed]): raise ValueError('Protected original XYZ changed.')
    output.mkdir(parents=True); arrays_dir = output/'working_arrays'; arrays_dir.mkdir()
    snapshots = output/'source_snapshot'; snapshots.mkdir()
    code = {}
    for path in (Path(__file__).resolve(), REPO/'src/cheshire/adaptive_ornament.py', REPO/'src/cheshire/ornament_analysis.py'):
        target = snapshots/path.name; shutil.copyfile(path, target)
        code[str(path)] = dict(**file_record(path), snapshot=str(target.resolve()))
    records = {}
    for name, value in (
        ('CONTROL_XYZ', final), ('CONTROL_QUADS', q), ('CHART', chart), ('CONTROL_CLASSES', host['classes']),
        ('RAW_CONTROL_XYZ', raw), ('ACTUAL_HOST_NORMALS', used_normals),
        ('CAP_MASK', caps), ('WAIST_GUARD_MASK', waist), ('FIXED_MASK', fixed),
        ('FLOW_PROTECTION', flow), ('PATTERN_COORDINATES', uv), ('SHAPE_WEIGHTS', weights),
        ('TISSUE_HEIGHT', tissue_height), ('TISSUE_PRIORITY', priority),
        ('MANDEL_SOURCE_HEIGHT', result['source_height']), ('DESIRED_HEIGHT', result['desired_height']),
        ('ACTUAL_HEIGHT', height), ('LOCAL_GAIN', result['local_gain']), ('POST_MIRROR_GAIN', post_gain),
        ('NORMAL_SAFETY_CAP', result['safety_cap']),
        ('MIRROR_X_VERTEX_PAIRS', pairs['x']), ('MIRROR_Y_VERTEX_PAIRS', pairs['y'])):
        save_array(arrays_dir, name, value, records, recipe.chunk_size)
    for key, value in compact.items(): save_array(arrays_dir, 'MEASURED_'+key.upper(), value, records)
    tags = np.empty(len(q), np.int32); shape_tags = np.empty(len(q), np.uint8)
    for first in range(0, len(q), recipe.chunk_size):
        faces = q[first:first+recipe.chunk_size]
        mandel = np.abs(result['source_height'][faces]*(1-priority[faces]))
        tissue_part = np.minimum(recipe.tissue_amplitude, result['safety_cap'][faces])*tissue_height[faces]*priority[faces]
        actual = np.abs(height[faces]).mean(1)
        tag = np.where(tissue_part.mean(1)>mandel.mean(1), 2, 1).astype(np.uint8)
        tag[actual < .001] = 0; tag[fixed[faces].mean(1) >= .5] = 3
        tags[first:first+len(faces)] = tag
        shape_tags[first:first+len(faces)] = np.argmax(weights[faces].mean(1), axis=1)
    save_array(arrays_dir, 'QUAD_EFFECT_CLASSES', tags, records)
    save_array(arrays_dir, 'QUAD_SHAPE_LABELS', shape_tags, records)
    native = native_fans(arrays_dir, final, q, records, recipe.chunk_size)
    displacement = np.linalg.norm(final-x, axis=1)
    receipt = dict(schema=SCHEMA, status='PASS', candidate=args.id, actual_generation=5,
        recipe=asdict(recipe), existing_ornament_recipe=op_recipe.to_dict(), arrays=records,
        source_G5={name:file_record(source/name) for name in ('control_quad.npz', 'evidence.npz', 'generation.json')},
        selected_source_G0_receipt=file_record(source_receipt), source_assets=assets, geometry_code=code,
        measured_shape=measured, normal_safety_diagnostics=safety_diagnostics,
        waist_guard_intervals=guards, native=native,
        checks=dict(all_finite=bool(np.isfinite(final).all()), reversed_native_fan_faces=0,
                    fixed_coordinates_exact=True, cap_coordinates_exact=True, waist_coordinates_exact=True,
                    unchanged_control_topology=True, unchanged_material_chart=True,
                    normal_only_new_increment=True),
        recovery_bad_face_counts=result['recovery_bad_face_counts'], post_mirror_recovery_bad_face_counts=post_counts,
        actual_displacement_quantiles=np.quantile(displacement, [0, .5, .9, .99, 1]).tolist(),
        changed_control_vertices=int(np.count_nonzero(displacement)),
        cap_frozen_controls=int(caps.sum()), waist_frozen_controls=int(waist.sum()),
        effect_label_meaning={'0':'Original host / sub-threshold relief', '1':'New finite Mandel relief dominates',
                              '2':'Actual paper Tissue height dominates', '3':'Protected original waist or cap'},
        effect_quad_counts={str(k):int((tags == k).sum()) for k in range(4)},
        native_effect_labels='Repeat each QUAD_EFFECT_CLASSES entry four times in arithmetic fan order; these are dominant-effect labels, not topological ownership.',
        baseline_geometry_smoothed=False, added_subdivision_passes=0, added_topology_events=0,
        new_Tissue_invocations=0, single_valued_Tissue_height_relief=True, full_XYZ_Tissue_graft=False,
        historical_G7_XYZ_or_atlas_read=False, added_through_holes=0,
        self_intersection='NOT_CHECKED_EXPLORATORY', fabrication='NOT_CHECKED',
        elapsed_seconds=time.perf_counter()-started)
    write(output/'RECEIPT.json', receipt)
    print('FINISH PASS', len(q), 'Q', native['triangles'], 'T', 'seconds', round(receipt['elapsed_seconds'], 3), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-g5', type=Path, required=True)
    parser.add_argument('--source-g0', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--id', default='L08_PRIMARY_193')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--tissue', type=Path, default=DEFAULT_TISSUE)
    parser.add_argument('--mandel-period', type=float, default=.48)
    parser.add_argument('--tissue-amplitude', type=float, default=.055)
    parser.add_argument('--normal-safety-ratio', type=float, default=.35)
    parser.add_argument('--max-faces', type=int, default=3_500_000)
    args = parser.parse_args(); run(args)


if __name__ == '__main__': main()
