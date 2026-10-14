"""One physical G4-distance collar, lifted through actual G5/G6/G7 IDs.

Only scalar support is generated. Original geometry and all previous masks
remain unchanged. Graph edge lengths use the original final G7's actual old
G4 prefix, not an earlier smoothed cage or spatial nearest-neighbour links.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import shutil
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/end_continuity_20261014/trial01')
E = Path('E:/CHESHIRE_DATA/experiments')
SOURCE = E/'medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07'
REPLAY = E/'end_rule_revision_20261014/trial01/replay/states/G07_FINAL'
OLD_MASK = E/'volume_junction_target_20261014/trial01/selection.npz'
G4 = E/'sidewall_fan_growth_20261013/trial01/SIDEWALL_FAN/SPAN/G04'
G5 = E/'coherent_fold_detail_20261013/trial01/DIRECTIONAL/SPAN/G05'
G6 = E/'directional_g6_20261013/trial01/DEPTH_08/SPAN/G06'
G7 = E/'whole_column_detail_20261013/trial01/SURFACE/MIDDLE/SPAN/G07'
H = 9.735842284057451
WIDTH = .08*H
EXPECTED = {
    SOURCE/'control_quad.npz': '0d966671a028cd56f49d0c5d1e626207652e789d281a9fa69475c3492f95fdc6',
    SOURCE/'evidence.npz': '226c22ca83f9c71e69059d817e42140483d19a46228d66c6710170bc1ac17e21',
    REPLAY/'control_quad.npz': '09be1bf0ad67f718f110bc9de1d2ba108998b53ca00edfc8fc2ad046c2916f23',
    OLD_MASK: '7bbfb7cdb50b3fad320451dc096b23f8f662c7a09a425324949cba39396584ab',
    G4/'control_quad.npz': 'a8ff83f00582c489867414a2540ec62bd30c7a79cb785f2c2e3e8a0111aee43a',
    G5/'control_quad.npz': 'f164ef1c25bd08c1119d57c5388d624d733adc3b6d6142d6f670dca2f254e357',
    G6/'control_quad.npz': '215f6e3c929a500043e70eee4984245874d719bc9a6c20ef1bb92389b6217c50',
    G7/'control_quad.npz': '373663eae5b7685e2b833de6e4704eab1af8e345d890a72b37384dbe98a23ceb',
    G5/'evidence.npz': 'abe38b477bc1c452549465aa86b206ad1b96e1cd19e44d3392450ee801ecab01',
    G6/'evidence.npz': '0c3af89f8901329daac8f2f2e83e4af39b373f60f4f92eba93c8af23f984e1d5',
    G7/'evidence.npz': 'ca08819a3a44aa6b7f73b398c7d32bef7b28e8ccd2051ae0c0ec755165401a8c',
}
REPRESENTATIVE_EDGES = np.array([[52332,1959852],[3932787,5959763],[2838143,809144]], np.int64)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def ah(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
        allow_nan=False)+'\n', encoding='utf8')


def smooth(value):
    x = np.clip(value, 0., 1.)
    return x*x*x*(10+x*(-15+6*x))


def canonical(value, px, py):
    ids = np.arange(len(value))
    if (px.shape != ids.shape or py.shape != ids.shape or
            not np.array_equal(px[px], ids) or not np.array_equal(py[py], ids) or
            not np.array_equal(px[py], py[px])):
        raise ValueError('Actual commuting scalar mirror IDs required.')
    rep = np.minimum(np.minimum(ids, px), np.minimum(py, px[py]))
    error = max(float(np.max(np.abs(value-value[px]))),
                float(np.max(np.abs(value-value[py]))))
    if error > 1e-10:
        raise ValueError('Actual scalar before canonical transport lost symmetry.')
    return value[rep].copy(), error


def verified_lift(value, incoming, outgoing):
    with np.load(incoming/'control_quad.npz', allow_pickle=False) as data:
        faces = data['faces']
        if len(data['xyz']) != len(value):
            raise ValueError('Actual incoming scalar/control size differs.')
    with np.load(outgoing/'evidence.npz', allow_pickle=False) as data:
        edges = data['input_edges']
    with np.load(outgoing/'control_quad.npz', allow_pickle=False) as data:
        children = data['faces']
        output_count = len(data['xyz'])
    nv, ne, nf = len(value), len(edges), len(faces)
    if output_count != nv+ne+nf or children.shape != (4*nf, 4):
        raise ValueError('Actual V/E/F birth count differs.')
    child = children.reshape(nf,4,4)
    if not np.array_equal(child[:,:,1],faces) or not np.all(child[:,:,3] == (nv+ne+np.arange(nf))[:,None]):
        raise ValueError('Actual child corner/face-centre IDs differ.')
    following = child[:,:,2]-nv
    if following.min()<0 or following.max()>=ne or not np.array_equal(child[:,:,0]-nv,np.roll(following,1,axis=1)):
        raise ValueError('Actual preceding/following edge IDs differ.')
    for start in range(0,nf,65536):
        q=faces[start:start+65536];b=np.roll(q,-1,axis=1)
        e=edges[following[start:start+65536]]
        if not (np.array_equal(e[:,:,0],np.minimum(q,b)) and np.array_equal(e[:,:,1],np.maximum(q,b))):
            raise ValueError('Actual source edge endpoints differ.')
    if not np.all(np.bincount(following.ravel(),minlength=ne)==2):
        raise ValueError('Actual closed quad edge incidence differs.')
    lifted = np.concatenate([value,value[edges].mean(axis=1),value[faces].mean(axis=1)])
    report = dict(input=str(incoming),output=str(outgoing),input_count=nv,
        input_edges=ne,input_faces=nf,output_count=output_count,
        actual_input_edges_sha256=ah(edges),actual_input_faces_sha256=ah(faces),
        actual_output_faces_sha256=ah(children),actual_child_ID_layout_verified=True,
        scalar_transport='Old values + actual edge means + actual face means; scalar association, not a geometry subdivision.')
    return lifted,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    root=parser.parse_args().root.resolve()
    if (root/'PHYSICAL_MASK.npz').exists() or (root/'MASK_RECEIPT.json').exists():
        raise FileExistsError('Previous scalar preparation remains immutable.')
    started=time.perf_counter()
    for path,expected in EXPECTED.items():
        if sha(path)!=expected:raise ValueError('Frozen actual source changed: '+str(path))
    root.mkdir(parents=True,exist_ok=True)
    snapshot=root/'source_snapshot/physical_mask_prepare.py'
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(__file__,snapshot)
    with np.load(OLD_MASK,allow_pickle=False) as data:
        old_coarse,old_full=data['coarse_mask'],data['full_mask']
    nc=len(old_coarse)
    if nc!=109410 or old_full.shape!=(7002114,):raise ValueError('Actual selected G4/G7 sizes differ.')
    promoted=smooth(old_coarse/.30)
    core=promoted>=.9
    if int(core.sum())!=1988:raise ValueError('Actual frozen core selection differs.')
    with np.load(SOURCE/'control_quad.npz',allow_pickle=False) as data:
        source_xyz=data['xyz']; source_faces_sha=ah(data['faces'])
    with np.load(SOURCE/'evidence.npz',allow_pickle=False) as data:
        px,py=data['mirror_x_vertex_pairs'],data['mirror_y_vertex_pairs']
    if max(px[:nc].max(),py[:nc].max())>=nc:raise ValueError('Actual G4 prefix lacks closed mirror orbits.')
    if not np.array_equal(core,core[px[:nc]]) or not np.array_equal(core,core[py[:nc]]):
        raise ValueError('Frozen core lost actual reflection.')
    with np.load(G5/'evidence.npz',allow_pickle=False) as data:edges=data['input_edges']
    xyz=source_xyz[:nc]
    lengths=np.linalg.norm(xyz[edges[:,0]]-xyz[edges[:,1]],axis=1)
    if not np.isfinite(lengths).all() or lengths.min()<=0:raise ValueError('Positive physical edge weights required.')
    graph=coo_matrix((np.tile(lengths,2),(np.concatenate([edges[:,0],edges[:,1]]),
        np.concatenate([edges[:,1],edges[:,0]]))),shape=(nc,nc)).tocsr()
    print('ONE physical source-prefix multi-source Dijkstra',nc,len(edges),'width',WIDTH,flush=True)
    distance=dijkstra(graph,indices=np.flatnonzero(core),directed=False,min_only=True,limit=WIDTH)
    coarse,coarse_error=canonical(smooth(1-distance/WIDTH),px[:nc],py[:nc])
    if not np.all(coarse[core]==1):raise ValueError('Fixed core plateau is not retained.')
    full=coarse.copy();lifts=[]
    for incoming,outgoing in ((G4,G5),(G5,G6),(G6,G7)):
        print('LIFT actual scalar association',incoming.name,'to',outgoing.name,flush=True)
        full,proof=verified_lift(full,incoming,outgoing);lifts.append(proof)
    if len(full)!=len(source_xyz) or lifts[-1]['actual_output_faces_sha256']!=source_faces_sha:
        raise ValueError('Actual final G7 source association differs.')
    full,full_error=canonical(full,px,py)
    if not np.isfinite(full).all() or full.min()<0 or full.max()>1:raise ValueError('Finite bounded full scalar required.')
    probe_ids=REPRESENTATIVE_EDGES.ravel()
    source_probe=source_xyz[probe_ids]
    with np.load(REPLAY/'control_quad.npz',allow_pickle=False) as data:
        replay_probe=data['xyz'][probe_ids]
        if ah(data['faces'])!=source_faces_sha:raise ValueError('Actual replay/source G7 ordered faces differ.')
    D=(replay_probe-source_probe).reshape(-1,2,3)
    probe_source=source_probe.reshape(-1,2,3)
    probes=[]
    for i,(a,b) in enumerate(REPRESENTATIVE_EDGES):
        edge=float(np.linalg.norm(probe_source[i,0]-probe_source[i,1]))
        item=dict(vertex_ids=[int(a),int(b)],original_edge_length=edge)
        for label,mask in (('old',old_full),('physical',full)):
            ma,mb=float(mask[a]),float(mask[b]);da,db=D[i]
            maskterm=(ma-mb)*.5*(da+db);replayterm=.5*(ma+mb)*(da-db)
            item[label]=dict(weights=[ma,mb],mask_gradient_term_norm=float(np.linalg.norm(maskterm)),
                replay_gradient_term_norm=float(np.linalg.norm(replayterm)),
                total_displacement_difference_norm=float(np.linalg.norm(maskterm+replayterm)),
                mask_term_per_original_edge_length=float(np.linalg.norm(maskterm)/edge))
        probes.append(item)
    support=coarse>0
    spatial=dict(source_G7_prefix_support_z_bounds=[float(xyz[support,2].min()),float(xyz[support,2].max())],
        graph_edge_length_quantiles=np.quantile(lengths,[0,.1,.5,.9,1]).tolist())
    result=root/'PHYSICAL_MASK.npz'
    print('SAVE scalar masks only; no geometry',flush=True)
    np.savez_compressed(result,full_mask=full,coarse_mask=coarse,
        coarse_distance=distance,core_mask=core)
    del graph,source_xyz,source_probe,replay_probe
    gc.collect()
    for path,expected in EXPECTED.items():
        if sha(path)!=expected:raise ValueError('Frozen source changed during scalar preparation.')
    write(root/'MASK_RECEIPT.json',dict(date='2026-10-14',timezone='Asia/Seoul',
        schema='CHESHIRE_PHYSICAL_G4_GEODESIC_MASK_V1',candidate_geometry_generated=False,
        sources={str(path):expected for path,expected in EXPECTED.items()},
        recipe=dict(core='quintic(clip(saved_old_coarse_mask/.30,0,1))>=.9',
            core_vertices=int(core.sum()),reference_height=H,physical_collar_width=WIDTH,
            physical_collar_height_fraction=.08,graph='Actual G4 input_edges, weighted by Euclidean lengths of original final G7 old-G4-prefix coordinates. No spatial-nearest-neighbour cross-sheet edges.',
            solve='One multi-source sparse weighted Dijkstra, limit=L',
            mask='C2 quintic(clip(1-geodesic_distance/L,0,1)); exact plateau1 on core, exact0 beyond collar',
            geometry_scope='Only scalar mask. No averaging/rebuilding of geometry, normals or original replay deltas.',
            physical_bound_scope='Coarse graph distance is 1-Lipschitz on its weighted edges; quintic derivative <=1.875/L. Fine lifted values require their actual G7 displacement-gradient check; no fine-geometry guarantee inferred solely from coarse distance.'),
        old_mask=dict(nonzero_coarse=int(np.count_nonzero(old_coarse)),
            promoted_exact_one_vertices=int(np.count_nonzero(promoted==1)),
            promoted_nonzero_min=float(promoted[promoted>0].min()),
            nonzero_full=int(np.count_nonzero(old_full))),
        output=dict(path=str(result),sha256=sha(result),bytes=result.stat().st_size,
            full_count=len(full),nonzero_full=int(np.count_nonzero(full)),
            full_mask_array_sha256=ah(full),nonzero_coarse=int(np.count_nonzero(coarse)),
            coarse_mask_array_sha256=ah(coarse),coarse_distance_outside_limit='Infinity; diagnostic only. Mask is exactly zero there.'),
        actual_scalar_mirror_transport=dict(coarse_precopy_max_error=coarse_error,
            final_precopy_max_error=full_error,canonical_minimum_ID_orbit_copy=True,
            final_XY_scalar_equal=True),lifts=lifts,spatial=spatial,
        representative_edge_decomposition=probes,
        executed_source_sha256=sha(snapshot),elapsed_seconds=time.perf_counter()-started,
        limits='Physical scalar collar does not itself establish improved endings, full replay quality, no foldover/intersection, or an adopted design. Root constructs and reviews any candidate separately.'))
    if sha(HERE/'physical_mask_prepare.py')!=sha(snapshot):raise ValueError('Executed source/snapshot changed.')
    print(json.dumps(dict(prepared=str(result),nonzero_full=int(np.count_nonzero(full)),
        nonzero_coarse=int(np.count_nonzero(coarse)),representative_edges=probes),indent=2),flush=True)


if __name__=='__main__':
    main()
