"""Compare Tissue surface composition on an immutable CHESHIRE checkpoint.

UNUSED intentionally produces an open surface at replacement boundaries. This
export path does not pretend it is a solid, cap it, or apply a solid Boolean.
"""
from pathlib import Path
import json,time
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import ArrayMesh
from .engine import tessellate,surface,from_tri
from .symmetry import reflect,symmetry_error
from .input import load,sha,write
from .render import render


def metrics(tm):
    count=np.bincount(tm.edges_unique_inverse,minlength=len(tm.edges_unique))
    report=dict(vertices=len(tm.vertices),triangles=len(tm.faces),finite=bool(np.isfinite(tm.vertices).all()),
                zero_area_faces=int(np.count_nonzero(tm.area_faces==0)),boundary_edges=int(np.count_nonzero(count==1)),
                nonmanifold_edges=int(np.count_nonzero(count>2)),watertight=bool(tm.is_watertight),
                winding_consistent=bool(tm.is_winding_consistent),components=len(trimesh.graph.connected_components(tm.face_adjacency,nodes=np.arange(len(tm.faces)))))
    if not report['finite'] or report['zero_area_faces'] or report['nonmanifold_edges'] or not report['winding_consistent']:
        raise ValueError('Invalid surface: '+str(report))
    return report


def retained_faces(original,result,selected):
    """Identify original quads by all four corners, not just nearby centroids."""
    distance,nearest=cKDTree(original.xyz).query(result.xyz)
    q=result.faces
    candidates=(q>=0).sum(1)==4
    indices=nearest[np.maximum(q[candidates],0)][:,:4]
    good=np.max(distance[np.maximum(q[candidates],0)][:,:4],axis=1)<1e-7
    indices=np.ascontiguousarray(np.sort(indices[good],axis=1),dtype=np.int64)
    keytype=np.dtype((np.void,32))
    keys=indices.view(keytype).ravel()
    source=np.ascontiguousarray(np.sort(original.faces,axis=1),dtype=np.int64).view(keytype).ravel()
    retained=np.isin(source,keys)
    return dict(selected_original_faces_remaining=int(np.count_nonzero(retained&selected)),
                unused_original_faces_remaining=int(np.count_nonzero(retained&~selected)),
                comparison_tolerance=1e-7)


def run(target_stage,mapping_stage,input_path,output):
    target_stage=Path(target_stage).resolve();mapping_stage=Path(mapping_stage).resolve();out=Path(output).resolve()
    if out.exists():raise FileExistsError(out)
    g=load(input_path)
    parent=json.loads((target_stage.parent/'run.json').read_text())
    if parent['status']!='COMPLETE' or parent['input_sha256']!=g.manifest['mesh_sha256']:raise ValueError('Completed matching target required')
    st=np.load(target_stage/'state.npz');m=ArrayMesh(st['xyz'],st['faces'],st['classes'],st['rest'],st['anchors'],int(st['generation']))
    old=np.load(mapping_stage/'observations.npz')
    if not np.array_equal(old['positions'],m.xyz):raise ValueError('Mapping checkpoint does not refer to this TARGET')
    selected=np.load(mapping_stage/'operator_state.npz')['selected_target_faces'].astype(bool)
    original_spec=json.loads((mapping_stage/'stage.json').read_text())['parameters']
    obs=dict(field=old['field'],openings=g.openings,projection_selection=selected)
    out.mkdir(parents=True)
    protected=[target_stage/'state.npz',mapping_stage/'state.npz',Path(original_spec['component'])]
    protected[-1]=protected[-1] if protected[-1].is_absolute() else Path(__file__).resolve().parents[1]/protected[-1]
    hashes={str(p):sha(p) for p in protected}
    record=dict(status='RUNNING',target_stage=str(target_stage),mapping_stage=str(mapping_stage),source_sha256=hashes,
                fixed_mapping=original_spec,selected_target_faces=int(selected.sum()),total_target_faces=len(m.faces),
                selection_fraction=float(selected.mean()),variants={},
                limits=['UNUSED can have open replacement boundaries; no capping, welding or solid Boolean is applied.',
                        'LAST contains the same selected patches only, not the whole gate surface.',
                        'No self-intersection/fabrication certification.'])
    write(out/'comparison.json',record)
    framing=np.array([g.mesh.xyz.min(0)-.16,g.mesh.xyz.max(0)+.16])
    reference_cells=None
    for name,combine,keep in [('03_tissue_only','LAST',False),('02_replace_selected','UNUSED',False),('01_overlay','LAST',True)]:
        start=time.perf_counter();folder=out/name;folder.mkdir()
        spec=dict(original_spec,combine_mode=combine,keep_target=keep)
        result,meta,state=tessellate(m,obs,spec,1.,3000000)
        expected_cells=int(selected.sum())*meta['component_faces']
        expected_original=len(m.faces) if keep else (int((~selected).sum()) if combine=='UNUSED' else 0)
        if len(result.faces)!=expected_cells+expected_original:raise ValueError('Unexpected Tissue face composition')
        remaining=retained_faces(m,result,selected)
        if remaining['selected_original_faces_remaining']!=(int(selected.sum()) if keep else 0):raise ValueError('Selected target faces were not removed as requested')
        if remaining['unused_original_faces_remaining']!=(int((~selected).sum()) if (keep or combine=='UNUSED') else 0):raise ValueError('Unexpected unused target face retention')
        if reference_cells is None:reference_cells=result.xyz.copy()
        cell_error=float(cKDTree(result.xyz).query(reference_cells)[0].max())
        if cell_error>1e-7:raise ValueError('Cell geometry changed between combine modes')
        result,_=reflect(result)
        tm=surface(result);checks=metrics(tm);checks['symmetry_max_error']=symmetry_error(result)
        checks.update(remaining);checks['cell_geometry_max_distance_from_LAST']=cell_error
        np.savez_compressed(folder/'state.npz',xyz=result.xyz,faces=result.faces)
        world=tm.copy();world.vertices=world.vertices*g.scale+g.origin
        world.export(folder/'result.obj',digits=16);world.export(folder/'result.ply')
        checks['obj_reload']=metrics(trimesh.load(folder/'result.obj',force='mesh',process=False))
        checks['ply_reload']=metrics(trimesh.load(folder/'result.ply',force='mesh',process=False))
        render(tm,folder/'views',1000,framing)
        entry=dict(status='COMPLETE',parameters=spec,operator=meta,checks=checks,elapsed_seconds=time.perf_counter()-start)
        write(folder/'run.json',entry);record['variants'][name]=entry;write(out/'comparison.json',record)
        print(json.dumps(dict(variant=name,checks=checks,seconds=entry['elapsed_seconds'])),flush=True)
    record['sources_unchanged']={p:sha(p)==digest for p,digest in hashes.items()}
    if not all(record['sources_unchanged'].values()):raise ValueError('Source changed during comparison')
    record['status']='COMPLETE';write(out/'comparison.json',record)
    return record
