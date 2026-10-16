"""Audit preserved CONTINUED G4 arrays; no model generation or rendering.

File hashes are the immutable actual files observed during the 2026-10-15
read-only causal audit. The output is a small C-workspace measurement record.
"""
from pathlib import Path
import hashlib
import json

import numpy as np


HERE=Path(__file__).resolve().parent
ROOT=Path('E:/CHESHIRE_DATA/column_detail_20261012/CONTINUED/G04')
PARENT=Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03/control_quad.npz')
EXPECTED={
    ROOT/'operation_fields.npz':'0205802b69b852b45f2f1afd96a10dcc11cfefa449957665e4ce29203044b1a0',
    ROOT/'control_quad.npz':'7542659440dffa7fd32ed3b71a29a435828da42db3fb6dc5e3d7f7074b7065da',
    ROOT/'generation.json':'0b1b17522e021e5b9335415c0974381bb8ab15ad7b31cf49616c1002b0941d29',
    PARENT:'317b50a76826491a7769276811da1493513ccf9534299a08e868b473bf3681e6',
}
QUANTILES=[0.,.1,.5,.9,.99,1.]


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024**2),b''):
            digest.update(chunk)
    return digest.hexdigest()


def quantile(value):
    return np.quantile(value,QUANTILES).tolist()


def main():
    output=HERE/'diagnosis_continued_saved_results.json'
    if output.exists():
        raise FileExistsError('Existing audit evidence remains preserved: '+str(output))
    for path,expected in EXPECTED.items():
        if sha(path)!=expected:
            raise ValueError('Preserved source file differs: '+str(path))
    metadata=json.loads((ROOT/'generation.json').read_text(encoding='utf8'))
    if (Path(metadata['source']).parent/'control_quad.npz')!=PARENT:
        raise ValueError('Saved G4 parent differs from the actual bound G3.')
    with np.load(PARENT,allow_pickle=False) as saved:
        parent_xyz,parent_faces=saved['xyz'],saved['faces']
        parent_generation=int(saved['generation'])
    with np.load(ROOT/'operation_fields.npz',allow_pickle=False) as saved:
        required=('input_edges','interpolated_xyz','post_task36_xyz',
                  'applied_task36_displacement','field_displacement',
                  'canonical_nearest_outside_target','canonical_vertex',
                  'field_active','face_bend','support_radius',
                  'parent_face_vertices','post_field_xyz')
        op={key:saved[key] for key in required}
    with np.load(ROOT/'control_quad.npz',allow_pickle=False) as saved:
        quads,output_xyz=saved['faces'],saved['xyz']
        generation=int(saved['generation'])
    edges,inter,post=op['input_edges'],op['interpolated_xyz'],op['post_task36_xyz']
    task,field=op['applied_task36_displacement'],op['field_displacement']
    nv,ne,nf=len(parent_xyz),len(edges),len(parent_faces)
    if (parent_generation!=3 or generation!=4 or len(inter)!=nv+ne+nf or
            quads.shape!=(4*nf,4) or
            not np.array_equal(parent_xyz,inter[:nv]) or
            not np.array_equal(parent_faces,op['parent_face_vertices']) or
            not np.array_equal(quads.reshape(nf,4,4)[:,:,1],parent_faces) or
            not np.array_equal(post,inter+task) or
            not np.array_equal(output_xyz,op['post_field_xyz']) or
            not np.array_equal(output_xyz,post+field)):
        raise ValueError('Actual saved parent, V/E/F correspondence or operation replay differs.')
    child_edges=np.concatenate([quads[:,[0,1]],quads[:,[1,2]],
                                quads[:,[2,3]],quads[:,[3,0]]])
    child_edges.sort(axis=1)
    child_edges=np.unique(child_edges,axis=0)
    parent_length=np.linalg.norm(parent_xyz[edges[:,1]]-parent_xyz[edges[:,0]],axis=1)
    child_length=np.linalg.norm(post[child_edges[:,1]]-post[child_edges[:,0]],axis=1)
    if np.any(child_length<=0):
        raise ValueError('Saved post-Task36 child edge has no positive length.')
    field_difference=np.linalg.norm(field[child_edges[:,1]]-field[child_edges[:,0]],axis=1)
    task_difference=np.linalg.norm(task[child_edges[:,1]]-task[child_edges[:,0]],axis=1)
    active=np.asarray(op['field_active'],dtype=bool)
    active_edges=active[child_edges].any(axis=1)
    quarter=np.flatnonzero(np.arange(len(post))==op['canonical_vertex'])
    active_quarter=quarter[active[quarter]]
    birth={}
    for label,first,last in (('old_V',0,nv),('new_E',nv,nv+ne),('new_F',nv+ne,len(post))):
        birth[label]=dict(count=last-first,
            task_norm=quantile(np.linalg.norm(task[first:last],axis=1)),
            field_norm=quantile(np.linalg.norm(field[first:last],axis=1)))
    fine_spacings=sorted({tuple(item['spacing']) for item in metadata['field_step']['local_target_logs']})
    if fine_spacings!=[(.03,.03,.03125)]:
        raise ValueError('Actual saved local target grid differs from the reported factor2 audit.')
    result=dict(kind='READ_ONLY_PRESERVED_CONTINUED_G4_CAUSAL_AUDIT',date='2026-10-15',
        generated_models=0,generated_renders=0,source_arrays_modified=False,
        source_bindings={str(path):expected for path,expected in EXPECTED.items()},
        script_sha256=sha(__file__),
        correspondence=dict(parent_generation=3,output_generation=4,parent_vertices=nv,
            parent_quads=nf,parent_edges=ne,output_vertices=len(post),output_quads=len(quads),
            child_edges=len(child_edges),actual_parent_prefix_exact=True,
            actual_parent_quads_exact=True,actual_child_old_corners_exact=True,
            post_task36_equals_interpolated_plus_saved_task_delta_exact=True,
            actual_output_equals_post_task36_plus_saved_field_delta_exact=True),
        quantile_probabilities=QUANTILES,
        grid=dict(coarse_spacing=[.06,.06,.0625],fine_spacing=list(fine_spacings[0]),
            coarse_spacing_source='experiments/column_development_20261011/target_repeat.py:112',
            fine_spacing_source='Actual CONTINUED G4 generation.json field_step.local_target_logs',
            field_iterations=metadata['field_iterations'],fraction=metadata['field_step']['fraction'],
            field_budget=metadata['field_step']['budget'],
            target_factor=metadata['field_target_refinement'],
            target_resolution_change=metadata['target_resolution_change']),
        input_edge_lengths=quantile(parent_length),
        postTask36_child_edge_lengths=quantile(child_length),
        fraction_child_edges_under_fine_grid03=float(np.mean(child_length<.03)),
        fraction_child_edges_under_coarse_grid06=float(np.mean(child_length<.06)),
        active_field_neighbor_delta=quantile(field_difference[active_edges]),
        active_field_neighbor_delta_over_edge=quantile(field_difference[active_edges]/child_length[active_edges]),
        task_neighbor_delta_over_edge=quantile(task_difference/child_length),
        active_canonical_points=len(active_quarter),
        unique_fine_targets=len(np.unique(np.round(op['canonical_nearest_outside_target'][active_quarter],10),axis=0)),
        target_uniqueness_rounding_decimal_places=10,
        birth=birth,face_bend=quantile(op['face_bend']),support_radius=quantile(op['support_radius']),
        interpretation='Observed fixed target spacing, birth-class contrast and neighbor displacement differences support plausible grid/crust mechanisms. This is not a one-factor causal ablation or an aesthetic score. The prior continuation starts at OVERLAP G3, not the current accepted G6; G3 factor3 changed to coarser G4 factor2. It cannot establish that every later generative continuation fails.')
    for path,expected in EXPECTED.items():
        if sha(path)!=expected:
            raise ValueError('Preserved source changed during read-only audit: '+str(path))
    result['source_file_hashes_unchanged_after_read']=True
    with output.open('x',encoding='utf8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(output),sha256=sha(output),
        input_edge_median=result['input_edge_lengths'][2],
        child_edge_median=result['postTask36_child_edge_lengths'][2],
        fraction_under_fine03=result['fraction_child_edges_under_fine_grid03'],
        old_V_task_max=birth['old_V']['task_norm'][-1],
        new_E_task_median=birth['new_E']['task_norm'][2],
        new_F_task_median=birth['new_F']['task_norm'][2]),indent=2),flush=True)


if __name__=='__main__':main()
