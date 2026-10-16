"""Replace exactly the authored G7 CHILD/SMALL layers, preserving their parent."""
from pathlib import Path
import argparse,gc,importlib.util,json,shutil,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    root=parser.parse_args().root.resolve()
    if root.exists():raise FileExistsError('Previous experiment preserved; choose a fresh root.')
    started=time.perf_counter()
    util=module('g7_detail_utils',HERE/'run_recursive.py')
    native=module('g7_detail_native',HERE/'run_final.py')
    renderer=module('g7_detail_renderer',HERE/'render_parent_probe.py')
    mandel=module('g7_detail_boundary',HERE/'mandelbulb_surface_replacement.py')
    operator=module('g7_detail_replacement',HERE/'g7_detail_mandel_rounded.py')
    accepted=util.ACCEPTED
    receipt_path=accepted/'RECEIPT.json'
    if util.digest(receipt_path)!=native.BASE_RECEIPT_SHA:raise ValueError('Accepted receipt changed.')
    receipt=json.loads(receipt_path.read_text(encoding='utf8'));base=receipt['variants']['NESTED']
    source=Path(base['control_quad']);geometry=Path(base['geometry'])
    if util.digest(source)!=base['control_quad_sha256'] or util.digest(geometry)!=base['geometry_sha256']:
        raise ValueError('Preserved accepted geometry changed.')
    sources={str(receipt_path):native.BASE_RECEIPT_SHA,str(source):base['control_quad_sha256'],str(geometry):base['geometry_sha256']}
    folder6,meta6=util.bound_stage('G06_MIDDLE',sources)
    folder7,_=util.bound_stage('G07_SURFACE',sources)
    for name in ('PARENT_STATE.npz','NESTED_STATE.npz'):
        path=accepted/name;sources[str(path)]=util.digest(path)
    print('G7_ONLY: load exact authored CHILD/SMALL contributions',flush=True)
    control=util.arrays(source);original=control['xyz'];quads=control['faces']
    with np.load(accepted/'PARENT_STATE.npz',allow_pickle=False) as a:primary=a['primary_delta']
    with np.load(accepted/'NESTED_STATE.npz',allow_pickle=False) as a:
        child=a['delta_child'];small=a['delta_small'];mask=a['parent_mask'];budget=a['child_budget'];width=a['local_flank_width']
    with np.load(folder7/'control_quad.npz',allow_pickle=False) as a:
        carrier=a['xyz']+primary
        if not np.array_equal(quads,a['faces']):raise ValueError('Accepted topology differs from preserved G7.')
    if util.ah(child)!=receipt['nested']['child']['delta_sha256'] or util.ah(small)!=receipt['nested']['small']['delta_sha256']:
        raise ValueError('Recorded original G7 detail array hashes differ.')
    if util.ah(carrier)!=receipt['nested']['child']['input_xyz_sha256']:
        raise ValueError('Exact original G7 detail input carrier hash differs.')
    rebuilt=(carrier+child)+small
    reconstruction_error=float(np.max(np.abs(rebuilt-original)))
    if reconstruction_error>1e-13:raise ValueError('Exact G7 component identity failed.')
    active=(mask>0.)&(budget>0.)
    mask=np.where(active,mask,0.)
    print('G7_ONLY: carrier+CHILD+SMALL identity error',reconstruction_error,'replacement controls',int(active.sum()),flush=True)
    del rebuilt,primary,child,small;gc.collect()
    with np.load(folder6/'evidence.npz',allow_pickle=False) as a:phase6=a['directional_phase']
    with np.load(folder6/'control_quad.npz',allow_pickle=False) as a:q6=a['faces']
    with np.load(folder7/'evidence.npz',allow_pickle=False) as a:
        edges=a['input_edges'];px=a['mirror_x_vertex_pairs'];py=a['mirror_y_vertex_pairs']
    phase=np.concatenate((phase6,phase6[edges].mean(1),phase6[q6].mean(1)))
    if util.ah(phase)!=receipt['parent_frame_proof']['lifted_phase_sha256']:
        raise ValueError('Actual inherited G7 detail phase differs.')
    del phase6,q6,edges;gc.collect()
    longitudinal=np.arctan2(np.abs(control['chart'][:,2]),np.abs(control['chart'][:,1]))/(np.pi/2.)
    height=float(meta6['operator_metadata']['physical_height'])
    root.mkdir(parents=True);snapshots={}
    files=[Path(__file__).resolve(),HERE/'g7_detail_mandel_rounded.py',HERE/'mandelbulb_surface_replacement.py',
           HERE/'run_recursive.py',HERE/'run_final.py',HERE/'render_parent_probe.py',*mandel.helper_paths(),*operator.helper_paths()]
    for file in dict.fromkeys(Path(p).resolve() for p in files):
        target=root/'source_snapshot_run'/file.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        snapshots[file.relative_to(REPO).as_posix()]=dict(source=str(file),snapshot=str(target),sha256=util.digest(file))
    print('G7_ONLY: finite power8 boundary, inherited phase/support, no whole-surface filter',flush=True)
    profile,profile_meta,profile_evidence=mandel.build_profile(power=8,iterations=8)
    profile_record=util.save_tree(root,'ACTUAL_MANDELBULB_BOUNDARY',profile_evidence)
    candidate,formation,state=operator.build(carrier,quads,phase,mask,budget,width,px,py,height,
                                             longitudinal=longitudinal,profile=profile)
    candidate[~active]=original[~active]
    outside_error=float(np.max(np.abs(candidate[~active]-original[~active]),initial=0.))
    if outside_error!=0.:raise ValueError('Outside original G7-detail footprint moved.')
    total=candidate-original;ids=np.flatnonzero(np.any(total!=0.,axis=1)).astype(np.int64);delta=total[ids]
    candidate=original.copy();candidate[ids]+=delta
    symmetry=0.
    for axis,pair in enumerate((px,py)):
        for first in range(0,len(ids),131072):
            chosen=ids[first:first+131072];reflected=candidate[pair[chosen]].copy();reflected[:,axis]*=-1.
            symmetry=max(symmetry,float(np.max(np.abs(candidate[chosen]-reflected),initial=0.)))
    if symmetry>2e-12:raise ValueError('Replacement lost inherited position symmetry.')
    state_record=util.save_tree(root,'G7_DETAIL_REPLACEMENT_STATE',state)
    formation.update(component_identity_error=reconstruction_error,original_G7_detail_support_controls=int(active.sum()),
        unchanged_outside_G7_detail_bit_exact=True,outside_G7_detail_error=outside_error,XY_symmetry_error=symmetry,
        removed_layers=['G7 CHILD','G7 SMALL'],preserved_layers='Full replay G07_SURFACE from actual G6 plus accepted primary_delta.',
        point_birth_mask_used=False,source_roles='All roles in the original authored G7 detail footprint.',
        maximum_total_change=float(np.linalg.norm(delta,axis=1).max()),moved_controls=len(ids),new_G8=False)
    util.write(root/'FORMATION.json',formation)
    delta_path=root/'FIELD_DELTA.npz'
    np.savez_compressed(delta_path,ids=ids,delta=delta,control_vertices=np.array(len(original),dtype=np.int64))
    del state,carrier,phase,longitudinal,px,py,width,budget,mask,active,total;gc.collect()
    print('G7_ONLY: exact full native reconstruction and quality',flush=True)
    with np.load(geometry,allow_pickle=False) as a:full=a['xyz'];faces=a['faces']
    if util.ah(full)!=base['xyz_sha256'] or util.ah(faces)!=base['faces_sha256']:raise ValueError('Native source hash failed.')
    full,reconstruction=renderer.apply_sparse_control_delta(full,original,quads,ids,delta)
    minimum=float('inf');reversed_count=0
    for first in range(0,len(quads),65536):
        q=quads[first:first+65536];a=original[q];b=candidate[q];ac=a.mean(1);bc=b.mean(1)
        for corner in range(4):
            na=np.cross(a[:,corner]-ac,a[:,(corner+1)%4]-ac);nb=np.cross(b[:,corner]-bc,b[:,(corner+1)%4]-bc)
            area=.5*np.linalg.norm(nb,axis=1)
            if not np.isfinite(area).all():raise ValueError('Nonfinite triangles')
            minimum=min(minimum,float(area.min()));reversed_count+=int((np.einsum('ij,ij->i',na,nb)<0.).sum())
    if minimum<=0.:raise ValueError('Degenerate native triangle')
    quality=dict(minimum_native_triangle_area=minimum,orientation_reversals_vs_original=reversed_count,
        orientation_reversal_fraction=reversed_count/(4*len(quads)),global_self_intersection_checked=False)
    util.write(root/'QUALITY.json',quality)
    for item in snapshots.values():
        if util.digest(item['source'])!=item['sha256'] or util.digest(item['snapshot'])!=item['sha256']:raise ValueError('Executed source changed.')
    for path,h in sources.items():
        if util.digest(path)!=h:raise ValueError('Preserved input changed.')
    util.write(root/'PROBE_RECEIPT.json',dict(kind='EXACT_G7_CHILD_SMALL_STRONG_ROUNDED_MANDELBULB_REPLACEMENT',date='2026-10-15',
        baseline_native=str(geometry),baseline_native_sha256=base['geometry_sha256'],
        baseline_control_quad=str(source),baseline_control_quad_sha256=base['control_quad_sha256'],baseline_record=base,
        variants={'CONTROL':dict(kind='BASELINE',xyz_sha256=base['xyz_sha256']),
                  'FIELD':dict(kind='CONTROL_DELTA',control_delta=str(delta_path),control_delta_sha256=util.digest(delta_path),xyz_sha256=reconstruction['complete_native_xyz_sha256'])},
        source_snapshots=snapshots,sources=sources,formation=formation,profile_evidence=profile_record,
        replacement_evidence=state_record,reconstruction=reconstruction,quality=quality,
        reconstruction_code_sha256=util.digest(HERE/'render_parent_probe.py'),elapsed_seconds=time.perf_counter()-started,
        scope='Only original authored G7 CHILD/SMALL are replaced; all earlier carrier/primary contributions retained. Outside their footprint coordinates are bit-exact. Visual review pending.'))
    print('G7_DETAIL_ROUNDED_COMPLETE',time.perf_counter()-started,flush=True)

if __name__=='__main__':main()
