"""Read-only real local geometry/residual comparison, no model formation."""
from pathlib import Path
import argparse
import json
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
import run_spine_reconstruction_v7 as run
import recursive_spine_operator_v2 as op


def quant(a):
    a = np.asarray(a)
    return dict(count=len(a), values=np.quantile(a, [0., .1, .5, .9, .99, 1.]).tolist()) if len(a) else dict(count=0, values=[])


def frames(strip):
    s = strip['s']; sigma = .5*np.median(1.5*.65*strip['width'])/np.median(np.diff(s))
    n = op.unit(gaussian_filter1d(op.unit(strip['normal']), sigma, axis=0, mode='nearest'))
    b = gaussian_filter1d(op.unit(strip['across']), sigma, axis=0, mode='nearest')
    b = op.unit(b-n*np.einsum('ij,ij->i', b, n)[:, None])
    return n, b


def at(s, vector, target):
    return op.unit(np.column_stack([np.interp(target, s, vector[:, j]) for j in range(3)]))


def choose_window(f):
    chi, h, base = f['logical_chi'], f['node_height'], f['usable_base_width']
    s = f['logical_s']; pitch = 1.5*f['requested_base_width']
    end = op.quintic(s/(1.5*pitch[0]))*op.quintic((s[-1]-s)/(1.5*pitch[-1]))
    good = (end > .99)&(h > .020)&(base > .04)
    hm, bm = np.median(h[good]), np.median(base[good])
    choices = []
    for first in range(1, int(f['cell_count'])-3):
        take = (chi >= first)&(chi <= first+3)
        if take.sum() < 8 or good[take].mean() < .75:
            continue
        distance = abs(np.median(h[take])-hm)/hm+abs(np.median(base[take])-bm)/bm
        choices.append((distance, first))
    if not choices:
        raise ValueError('No representative core three-cell window, no forced selection.')
    first = min(choices)[1]
    return first, first+3


class NativeFanSampler:
    """Exact (t, atan2(chart_y,chart_x)) inverse on existing native fan triangles."""
    def __init__(self, xyz, q, chart, face_ids, sparse_ids, sparse_delta, angle_reference):
        self.face_ids = face_ids; self.q = q[face_ids]; self.angle = angle_reference
        p = xyz[self.q]; c = p.mean(axis=1)
        m = chart[self.q]; mc = m.mean(axis=1)
        delta = np.zeros_like(p); flat = self.q.ravel()
        pos = np.searchsorted(sparse_ids, flat); inside = pos < len(sparse_ids)
        hit = np.zeros(len(flat), bool); hit[inside] = sparse_ids[pos[inside]] == flat[inside]
        delta.reshape(-1, 3)[hit] = sparse_delta[pos[hit]]
        dc = delta.mean(axis=1)
        self.points = np.stack([np.stack((p[:, k], p[:, (k+1)%4], c), axis=1) for k in range(4)], axis=1).reshape(-1, 3, 3)
        self.deltas = np.stack([np.stack((delta[:, k], delta[:, (k+1)%4], dc), axis=1) for k in range(4)], axis=1).reshape(-1, 3, 3)
        self.charts = np.stack([np.stack((m[:, k], m[:, (k+1)%4], mc), axis=1) for k in range(4)], axis=1).reshape(-1, 3, 3)
        theta = np.arctan2(self.charts[:, :, 2], self.charts[:, :, 1])
        theta = angle_reference+np.arctan2(np.sin(theta-angle_reference), np.cos(theta-angle_reference))
        uv = np.stack((self.charts[:, :, 0], theta), axis=-1)
        self.low, self.high = uv.min(axis=1), uv.max(axis=1)
        centres = (self.low+self.high)/2
        radius = np.linalg.norm(self.high-self.low, axis=1)/2
        self.buckets = []
        groups = np.floor(np.log2(radius/radius.min())).astype(int)
        for group in np.unique(groups):
            take = np.flatnonzero(groups == group)
            self.buckets.append((take, cKDTree(centres[take]), float(radius[take].max())))

    def sample(self, uv):
        valid = np.zeros(len(uv), bool); tri_id = np.full(len(uv), -1, np.int64)
        bary = np.zeros((len(uv), 3)); points = np.zeros_like(bary); delta = np.zeros_like(bary)
        normal = np.zeros_like(bary)
        for lookup, tree, radius in self.buckets:
            lists = tree.query_ball_point(uv, radius+1e-12)
            counts = np.fromiter(map(len, lists), dtype=np.int64, count=len(lists))
            if not counts.sum(): continue
            qi = np.repeat(np.arange(len(uv)), counts); ti = lookup[np.concatenate(lists).astype(int)]
            take = (~valid[qi])&np.all((uv[qi] >= self.low[ti]-1e-12)&(uv[qi] <= self.high[ti]+1e-12), axis=1)
            qi, ti = qi[take], ti[take]
            if not len(qi): continue
            ch = self.charts[ti]
            line = ch[:, :, 2]*np.cos(uv[qi, 1, None])-ch[:, :, 1]*np.sin(uv[qi, 1, None])
            matrix = np.stack((np.ones_like(line), ch[:, :, 0], line), axis=1)
            rhs = np.column_stack((np.ones(len(qi)), uv[qi, 0], np.zeros(len(qi))))
            bb = np.linalg.solve(matrix, rhs[:, :, None])[:, :, 0]
            inside = np.all(bb >= -1e-8, axis=1)&np.all(bb <= 1+1e-8, axis=1)
            qi, ti, bb = qi[inside], ti[inside], bb[inside]
            if not len(qi): continue
            _, first = np.unique(qi, return_index=True); qi, ti, bb = qi[first], ti[first], bb[first]
            valid[qi] = True; bary[qi] = bb
            tri_id[qi] = 4*self.face_ids[ti//4]+ti%4
            points[qi] = np.einsum('nj,nji->ni', bb, self.points[ti])
            delta[qi] = np.einsum('nj,nji->ni', bb, self.deltas[ti])
            normal[qi] = op.unit(np.cross(self.points[ti, 1]-self.points[ti, 0], self.points[ti, 2]-self.points[ti, 0]))
        return dict(valid=valid, triangle_ids=tri_id, barycentric=bary, carrier=points, delivered=points+delta, normal=normal)


def save_mesh(root, name, xyz, quads, extra=None):
    centres = xyz[quads].mean(axis=1); nv = len(xyz)
    faces = np.stack((quads, np.roll(quads, -1, axis=1), np.broadcast_to((nv+np.arange(len(quads)))[:, None], quads.shape)), axis=-1).reshape(-1, 3)
    native = np.concatenate((xyz, centres))
    path = root/(name+'.npz')
    np.savez_compressed(path, xyz=native, faces=faces, **(extra or {}))
    return dict(geometry=str(path.resolve()), geometry_sha256=run.sha(path), xyz_sha256=run.ah(native), faces_sha256=run.ah(faces), vertices=len(native), triangles=len(faces), source_quad_count=len(quads))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); out = args.output.resolve()
    if out.exists(): raise FileExistsError(out)
    receipt_path = args.root/'RECEIPT.json'; receipt = json.loads(receipt_path.read_text())
    preflight = json.loads((args.root/'PREFLIGHT.json').read_text())
    sources = {str(receipt_path.resolve()):run.sha(receipt_path)}
    contexts = []
    for info in preflight['selected']:
        if info['component'] not in (25, 40): continue
        state = run.load_tree(info['evidence']['description'], sources); f = state['formation']
        strip = op.reconstruct_strip(f, state['foundation']); n, b = frames(strip)
        first, last = choose_window(f); logical = f['logical_refined']; ss = logical[:, 0]*info['total_length']
        chi = np.interp(ss, f['logical_s'], f['logical_chi'])
        quad_chi = chi[f['quads_refined']].mean(axis=1)
        selected_q = f['quads_refined'][(quad_chi >= first)&(quad_chi <= last)]
        ids = np.unique(selected_q); uv = f['source_uv_refined'][ids]
        contexts.append(dict(info=info, state=state, f=f, strip=strip, n=n, b=b, first=first, last=last, ids=ids, quads=selected_q, uv=uv, low=uv.min(axis=0), high=uv.max(axis=0), candidate_faces=[]))
    control_path = Path(receipt['variants']['REFERENCE_NESTED']['control_quad'])
    with np.load(control_path, allow_pickle=False) as z: xyz, q7, chart7 = z['xyz'], z['faces'], z['chart']
    with np.load(args.root/'SPARSE_DELTA.npz', allow_pickle=False) as z: sparse_ids, sparse_delta = z['ids'], z['delta']
    with np.load(run.STATES/'G03_SIDEWALL/control_quad.npz', allow_pickle=False) as z: q3, c3 = z['faces'], z['chart']
    with np.load(run.STATES/'G03_SIDEWALL/evidence.npz', allow_pickle=False) as z: owner = z['face_event_ids']
    ancestor = q7
    for _ in range(4): ancestor = ancestor.reshape(-1, 4, 4)[:, :, 1]
    if not np.array_equal(ancestor, q3): raise ValueError('G7 body ancestry mismatch.')
    cap = np.all(c3[q3, 0] == 0., axis=1)|np.all(c3[q3, 0] == 1., axis=1)
    body = np.repeat((owner == 0)&~cap, 256)
    for start in range(0, len(q7), 65536):
        face_ids = np.flatnonzero(body[start:start+65536])+start
        ch = chart7[q7[face_ids]]
        for c in contexts:
            reference = float((c['low'][1]+c['high'][1])/2)
            theta = np.arctan2(ch[:, :, 2], ch[:, :, 1]); theta = reference+np.arctan2(np.sin(theta-reference), np.cos(theta-reference))
            uv = np.stack((ch[:, :, 0], theta), axis=-1)
            hit = np.all((uv.max(axis=1) >= c['low']-1e-10)&(uv.min(axis=1) <= c['high']+1e-10), axis=1)
            c['candidate_faces'].append(face_ids[hit])
    out.mkdir(parents=True)
    results = []; numerical = {}
    for c in contexts:
        info, f, ids = c['info'], c['f'], c['ids']; ci = info['component']
        face_ids = np.concatenate(c['candidate_faces']); reference = float((c['low'][1]+c['high'][1])/2)
        sampler = NativeFanSampler(xyz, q7, chart7, face_ids, sparse_ids, sparse_delta, reference)
        sampled = sampler.sample(c['uv'])
        if not sampled['valid'].all(): raise ValueError(f'Actual common-UV native coverage failed {ci}: {sampled["valid"].sum()}/{len(ids)}')
        ss = f['logical_refined'][ids, 0]*info['total_length']; uu = f['logical_refined'][ids, 2]
        nn, bb = at(f['logical_s'], c['n'], ss), at(f['logical_s'], c['b'], ss)
        hh = np.interp(ss, f['logical_s'], f['node_height']); chi = np.interp(ss, f['logical_s'], f['logical_chi'])
        formed, neutral = f['formed_refined'][ids], f['neutral_refined'][ids]
        residual = sampled['carrier']-neutral
        actual_difference = sampled['delivered']-(sampled['carrier']+formed-neutral)
        result = dict(component=ci, selected_cell_interval=[c['first'], c['last']], source_uv_bounds=[c['low'].tolist(), c['high'].tolist()], points=len(ids), actual_native_candidate_quads=len(face_ids), residual_norm=quant(np.linalg.norm(residual, axis=1)), actual_native_interpolation_difference=quant(np.linalg.norm(actual_difference, axis=1)), median_nominal_H=float(np.median(hh)), median_predicted_coffer_depth=float(np.median(hh)*info['local_section_gate']['enclosed_interval_depth_over_H']), sections={})
        for name, u in [('centre', 0.), ('inner', .22), ('sidewall', .5), ('outer', .75)]:
            take = np.abs(np.abs(uu)-u) < .035
            rn = np.einsum('ij,ij->i', residual[take], nn[take]); rb = np.einsum('ij,ij->i', residual[take], bb[take])
            angle = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', sampled['normal'][take], nn[take]), -1, 1)))
            xchi = chi[take]; xchi -= xchi.mean()
            design = np.column_stack((np.ones(len(xchi)), xchi, xchi*xchi, xchi**3, np.cos(2*np.pi*xchi), np.sin(2*np.pi*xchi), np.cos(4*np.pi*xchi), np.sin(4*np.pi*xchi)))
            beta = np.linalg.lstsq(design, rn, rcond=None)[0]; unexplained = rn-design@beta
            result['sections'][name] = dict(samples=int(take.sum()), residual_N=quant(rn), residual_B=quant(rb), residual_N_RMS=float(np.sqrt(np.mean(rn*rn))), residual_N_over_H=quant(rn/hh[take]), unexplained_residual_N_RMS=float(np.sqrt(np.mean(unexplained**2))), actual_carrier_normal_vs_forming_N_angle_degrees=quant(angle), two_cell_harmonic_residual_N_amplitudes=[float(np.hypot(beta[4], beta[5])), float(np.hypot(beta[6], beta[7]))])
        numerical[f'parent_{ci}_local_vertex_ids'] = ids
        numerical[f'parent_{ci}_source_uv'] = c['uv']
        for name, a in sampled.items(): numerical[f'parent_{ci}_{name}'] = a
        numerical[f'parent_{ci}_formed'] = formed; numerical[f'parent_{ci}_neutral'] = neutral
        results.append(result)
        if ci != 40: continue
        local_q = np.searchsorted(ids, c['quads'])
        meshes = dict(NEUTRAL=save_mesh(out, 'NEUTRAL', neutral, local_q, dict(local_refined_vertex_ids=ids)), FORMED=save_mesh(out, 'FORMED', formed, local_q, dict(local_refined_vertex_ids=ids)))
        atlas = run.BucketAtlas(f['source_chart_transfer'], f['quads_refined'], f['delta_refined'], f['logical_refined'], verify_global=False)
        native_chart = np.concatenate((chart7[q7[face_ids]].reshape(-1, 3), chart7[q7[face_ids]].mean(axis=1)))
        _, logical, valid = atlas.evaluate(native_chart)
        nquad = len(face_ids); logic_chi = np.interp(logical[:, 0]*info['total_length'], f['logical_s'], f['logical_chi'])
        inside = valid&(logic_chi >= c['first'])&(logic_chi <= c['last'])
        keep = inside[:4*nquad].reshape(-1, 4).any(axis=1)|inside[4*nquad:]
        exact_faces = face_ids[keep]; native_q = q7[exact_faces]; native_ids = np.unique(native_q); native_q_local = np.searchsorted(native_ids, native_q)
        delivered = xyz[native_ids].copy(); pos = np.searchsorted(sparse_ids, native_ids); inrange = pos < len(sparse_ids)
        hit = np.zeros(len(pos), bool); hit[inrange] = sparse_ids[pos[inrange]] == native_ids[inrange]
        delivered[hit] += sparse_delta[pos[hit]]
        extra = dict(original_control_vertex_ids=native_ids, original_quad_ids=exact_faces, original_native_triangle_ids=(4*exact_faces[:, None]+np.arange(4)).ravel())
        meshes['CARRIER'] = save_mesh(out, 'CARRIER', xyz[native_ids], native_q_local, extra)
        meshes['DELIVERED'] = save_mesh(out, 'DELIVERED', delivered, native_q_local, extra)
        mid = .5*(c['first']+c['last']); arc = float(np.interp(mid, f['logical_chi'], f['logical_s']))
        normal = at(f['logical_s'], c['n'], np.array([arc]))[0]; across = at(f['logical_s'], c['b'], np.array([arc]))[0]
        center = np.array([np.interp(arc, f['logical_s'], c['strip']['xyz0'][:, 4, j]) for j in range(3)])
        tangent = np.cross(across, normal); tangent /= np.linalg.norm(tangent)
        manifest = dict(schema='CHESHIRE_LOCAL_FORMATION_DIAGNOSTIC_V1', meshes=meshes, frame=dict(center=center.tolist(), normal=normal.tolist(), tangent=tangent.tolist(), across=across.tolist()), sources=sources, component=ci, selected_cell_interval=[c['first'], c['last']], selection='Three-cell core window nearest parent median nominal height and usable base; no camera or visually attractive-region selection.', correspondence='FORMED/NEUTRAL are actual cached local2CC quads reconstructed as arithmetic native fans. CARRIER/DELIVERED are true original G7 native fan subsets with unchanged original control and face IDs, not resampled proxies. Different topology is intentional; same source corridor and world camera.', visual_success=False)
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    np.savez_compressed(out/'CORRESPONDENCE.npz', **numerical)
    result = dict(kind='ACTUAL_LOCAL_FORMED_NEUTRAL_CARRIER_DELIVERED_DIAGNOSTIC', sources=sources, source_control=str(control_path), source_control_sha256=receipt['variants']['REFERENCE_NESTED']['control_quad_sha256'], sparse_delta_sha256=run.sha(args.root/'SPARSE_DELTA.npz'), diagnostic_source_sha256=run.sha(Path(__file__)), no_new_mesh_formation=True, source_inverse='Existing SOURCE BODY fan: complete UV AABB-centre radius bound, exact sum/t/angular-line barycentric solve; no nearest-world lookup.', residual_definition='R=actual G7 carrier sampled at common source UV minus actual cached local neutral geometry. Actual delivered sampled independently from original native control deltas.', parents=results)
    (out/'RESULT.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(out/'manifest.json', flush=True)
    for r in results:
        print('PARENT', r['component'], 'cells', r['selected_cell_interval'], 'RnormMed', r['residual_norm']['values'][2], 'cofferDepth', r['median_predicted_coffer_depth'], 'deliveryErrorMax', r['actual_native_interpolation_difference']['values'][-1], flush=True)


if __name__ == '__main__': main()
