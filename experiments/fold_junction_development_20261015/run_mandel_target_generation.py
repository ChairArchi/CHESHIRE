"""Actual G6 -> G7 ordered finite-Mandelbulb boundary target formation.

The paired CONTROL is the actual saved neutral G7 from identical G6 input.
This runner does not erase fine source geometry or coat a completed mesh.
"""
from pathlib import Path
import argparse,gc,importlib.util,json,shutil,sys,time
import numpy as np
from scipy.signal import find_peaks

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'src'))
from cheshire.reference_subdivision import ArrayMesh


def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def compact_stages(evidence,neutral,nv,ne,util):
    records={};stats={}
    for stage,start,stop in (('face',nv+ne,len(neutral)),('edge',nv,nv+ne),('vertex',0,nv)):
        desired=evidence[stage+'_desired_field'];carrier=evidence[stage+'_carrier'];base=neutral[start:stop]
        ids=np.flatnonzero((np.linalg.norm(desired,axis=1)>1e-12)|(np.linalg.norm(carrier-base,axis=1)>1e-12))
        records[stage+'_active_ids']=ids
        for key in ('carrier','chart','desired_field','added_offset'):
            a=evidence[stage+'_'+key];records[stage+'_'+key]=a[ids]
            stats[stage+'_'+key+'_complete_sha256']=util.ah(a)
        complete=evidence['completed_'+stage];records[stage+'_completed']=complete[ids]
        stats[stage+'_completed_complete_sha256']=util.ah(complete)
        stats[stage+'_total']=len(carrier);stats[stage+'_active']=len(ids)
    return records,stats


def measure_new_child(parent,neutral_mesh,out_xyz,chart,body,measure,util):
    """Actual native output/CONTROL comparison; emitted rails require new relief."""
    recorded,info=measure.core.native_body_sampler(neutral_mesh,chart,body)
    sampler=measure.v3.CoverageSampler(recorded)
    p=parent['parameter'];cross=parent['formation_shoulder_cross']
    uv=measure._uv(p[:,None],cross,'theta')
    baseline,valid,ids,bary=sampler.coverage(uv)
    nverts=len(out_xyz);face_id=ids//4;corner=ids%4
    current=np.full_like(baseline,np.nan)
    flat_valid=np.flatnonzero(valid.ravel());fq=face_id.ravel()[flat_valid];fc=corner.ravel()[flat_valid]
    q=neutral_mesh.faces[fq]
    points=np.stack((out_xyz[q[np.arange(len(q)),fc]],out_xyz[q[np.arange(len(q)),(fc+1)%4]],out_xyz[q].mean(1)),axis=1)
    current.reshape(-1,3)[flat_valid]=np.einsum('ij,ijk->ik',bary.reshape(-1,3)[flat_valid],points)
    frame=module('coupled_measure_parent_frames',HERE/'parent_mandel_formation.py')
    _,t,b,n,_=frame.frames(parent)
    delta=current-baseline
    normal_delta=np.einsum('nkj,nj->nk',delta,n)
    new_profile=np.einsum('nkj,nj->nk',current,n)
    old_profile=np.einsum('nkj,nj->nk',baseline,n)
    fractions=parent['formation_shoulder_arc']/parent['formation_shoulder_arc'][:,-1,None]
    choices=[]
    for row in range(len(p)):
        allowed=valid[row]&(fractions[row]>.25)&(fractions[row]<.75)
        prominence=max(.002,.003*float(parent['parent_physical_width'][row]))
        signal=np.where(allowed,-np.nan_to_num(normal_delta[row]),-1e6)
        peaks,props=find_peaks(signal,prominence=prominence)
        peaks=[j for j in peaks if allowed[j] and normal_delta[row,j]<-.001]
        choices.append(max(peaks,key=lambda j:-normal_delta[row,j]) if peaks else -1)
    chosen=np.asarray(choices);observed=chosen>=0
    # An actual newly depressed rail is recorded only on the observed rows;
    # no interpolation invents a parent across absent new geometry.
    rows=np.flatnonzero(observed);rail={}
    if len(rows):
        cols=chosen[rows]
        rail=dict(parameter=p[rows],material_cross=cross[rows,cols],XYZ=current[rows,cols],
            native_triangle_ids=ids[rows,cols],native_barycentric=bary[rows,cols],
            new_normal_depression=normal_delta[rows,cols])
    metadata=dict(status='NEW_NORMAL_GROOVE_OBSERVED' if observed.sum()>len(p)/2 else 'NO_MAJORITY_NEW_GROOVE',
        observed_rows=int(observed.sum()),total_rows=len(p),threshold='Per row prominence=max(.002,.003*parentwidth) and negative new normal displacement < -.001 within 25–75% shoulder.',
        matched_native_triangle_queries=int(valid.sum()),missing_queries=int((~valid).sum()),
        maximum_normal_relief=float(np.nanmax(np.abs(normal_delta))),
        actual_output_xyz_sha256=util.ah(out_xyz),sampler=info,
        limits='A newly depressed output rail versus the neutral CONTROL is evidence of new local relief, not proof of bifurcation, recursive continuation, global topology or beauty. No future parent is fabricated on unobserved rows.')
    evidence=dict(native_query_uv=uv,native_query_triangle_ids=ids,native_query_barycentric=bary,valid=valid,
        control_native_XYZ=baseline,formed_native_XYZ=current,normal_delta=normal_delta,
        control_normal_profile=old_profile,formed_normal_profile=new_profile,observed_row=observed,rail=rail)
    return metadata,evidence


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);args=ap.parse_args()
    root=args.root.resolve()
    if root.exists():raise FileExistsError('Previous trial preserved; choose a fresh root.')
    started=time.perf_counter()
    util=module('coupled_generation_utils',HERE/'run_recursive.py');native=module('coupled_generation_native',HERE/'run_final.py')
    measure=module('coupled_generation_actual_parent_measure',HERE/'recursive_fold_formation_v2.py')
    bank=module('coupled_generation_bank',HERE/'original_fold_events.py')
    ownership=module('coupled_generation_ownership',HERE/'parent_ownership.py')
    bulb=module('coupled_generation_orbits',HERE/'parent_local_mandelbulb.py')
    volume=module('coupled_generation_attached_volume',HERE/'parent_mandel_target_surface.py')
    operator=module('coupled_generation_operator',HERE/'target_projected_subdivision.py')
    contract=module('target_contract_check',HERE/'check_target_projection_contract.py').check()
    sources={};folder6,_=util.bound_stage('G06_MIDDLE',sources);folder7,_=util.bound_stage('G07_SURFACE',sources)
    folder3,_=util.bound_stage('G03_SIDEWALL',sources)
    x6=util.arrays(folder6/'control_quad.npz');x7=util.arrays(folder7/'control_quad.npz')
    mesh=ArrayMesh(x6['xyz'],x6['faces'],x6['classes'],x6['rest'],x6['anchors'],6);mesh.surface='mean'
    chart=x6['chart'];q6=mesh.faces;q7=x7['faces']
    with np.load(folder3/'control_quad.npz',allow_pickle=False) as a:q3=a['faces']
    recovered=q6
    for _ in range(3):recovered=recovered.reshape(-1,4,4)[:,:,1]
    if not np.array_equal(recovered,q3):raise ValueError('Actual G6 SOURCE ancestry differs.')
    with np.load(folder3/'evidence.npz',allow_pickle=False) as a:body=np.repeat(a['face_event_ids']==0,64)
    edges,following,degree=native.recover(q6,q7);nv=len(mesh.xyz);ne=len(edges)
    free=np.ones(nv,bool);free[np.unique(q6[~body])]=False
    edge_body=np.bincount(following.ravel(),weights=np.repeat(body.astype(int),4),minlength=ne)==2
    eligibility={'FACE':body & free[q6].all(axis=1),'EDGE':edge_body & free[edges].all(axis=1),'VERTEX':free}
    events,bank_metadata=bank.load_events();state=measure.initialize_events(events)
    state['parents']=[p for p in state['parents'] if p['family_id']==4]
    print('MEASURE actual G6 theta-flow macro parent family4; no G7 rail reuse',flush=True)
    segmented,coverage,sampler,info,source_evidence=measure._resolve_and_partition(mesh,chart,state,body)
    measured=[]
    for piece in segmented['parents']:
        parent,ev=measure._measure_child(sampler,piece['rail'])
        parent.update(family_id=np.array(4),piece_id=np.array(piece['piece_id']),tier=np.array(0))
        parent['controller_shoulder_xyz']=ev['actual_shoulder_xyz']
        measured.append((parent,ev))
    if not measured:raise ValueError('Actual owned macro shoulder absent; no decorative substitute.')
    parent,parent_evidence=max(measured,key=lambda pair:float(np.ptp(pair[0]['parameter'])))
    del sampler;gc.collect()
    root.mkdir(parents=True);snapshots={}
    code=[Path(__file__).resolve(),HERE/'run_recursive.py',HERE/'run_final.py',HERE/'recursive_fold_formation_v2.py',
          HERE/'original_fold_events.py',HERE/'actual_seed_fold_events.json',HERE/'parent_ownership.py',
          HERE/'parent_local_mandelbulb.py',HERE/'parent_mandel_target_surface.py',HERE/'target_projected_subdivision.py',
          HERE/'parent_mandel_formation.py',HERE/'render_generation_pair.py',HERE/'check_target_projection_contract.py',
          *measure.helper_paths(),*bank.helper_paths(),*ownership.helper_paths(),*volume.helper_paths()]
    for file in dict.fromkeys(Path(x).resolve() for x in code):
        target=root/'source_snapshot_run'/file.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        snapshots[file.relative_to(REPO).as_posix()]=dict(source=str(file),snapshot=str(target),sha256=util.digest(file))
    parent_record=util.save_tree(root,'ACTUAL_G6_PARENT',dict(parent=parent,measurement=parent_evidence,source_coverage=source_evidence))
    field,field_meta,field_evidence=volume.build(parent,events,bulb,ownership)
    field.eligibility=lambda xyz,material,stage:eligibility[stage.split('_')[0]]
    field_record=util.save_tree(root,'ACTUAL_TARGET_SURFACE',field_evidence)
    print('FORM actual G6 -> G7: completed F then changed-carrier E and V',flush=True)
    out,outchart,operator_meta,stage_evidence=operator.subdivide(mesh.xyz,q6,chart,edges,following,degree,q7,field)
    if not np.array_equal(outchart,x7['chart']):raise ValueError('Actual G7 material transport differs from saved neutral chart.')
    neutral=native.neutral_delta(mesh.xyz,q6,edges,following,degree)
    zero_error=float(np.max(np.abs(neutral-x7['xyz'])))
    if zero_error>2e-13:raise ValueError('Actual same-G6 neutral control differs from preserved neutral G7.')
    compact,stage_hashes=compact_stages(stage_evidence,x7['xyz'],nv,ne,util)
    feedback={}
    for label,lower,upper in (('EDGE',nv,nv+ne),('VERTEX',0,nv)):
        old_stage=x7['xyz'][lower:upper];material=outchart[lower:upper]
        baseline_request=field.evaluate(old_stage,material,label+'_COUNTERFACTUAL')
        difference=stage_evidence[label.lower()+'_desired_field']-baseline_request
        active=np.flatnonzero(np.linalg.norm(difference,axis=1)>1e-12)
        feedback[label]=dict(changed_query_results=len(active),maximum_query_feedback=float(np.linalg.norm(difference,axis=1).max(initial=0.)))
        compact[label.lower()+'_feedback_ids']=active;compact[label.lower()+'_feedback_delta']=difference[active]
    stage_record=util.save_tree(root,'CAUSAL_STAGE_EVIDENCE',compact)
    del stage_evidence,compact,neutral;gc.collect()
    with np.load(folder7/'evidence.npz',allow_pickle=False) as a:px=a['mirror_x_vertex_pairs'];py=a['mirror_y_vertex_pairs']
    # Numerical symmetry restoration only; the actual stage fields already
    # use inherited material reflection. Record its magnitude transparently.
    symmetric=native.reflect_delta(out,px,py);symmetry_correction=float(np.max(np.abs(symmetric-out)))
    if symmetry_correction>2e-12:raise ValueError('Causal stages have a substantive mirror inconsistency.')
    out=symmetric
    difference=out-x7['xyz'];norm=np.linalg.norm(difference,axis=1)
    if not np.isfinite(out).all() or norm.max()<1e-10:raise ValueError('No finite actual new formation.')
    parent7=ArrayMesh(x7['xyz'],q7,x7['classes'],x7['rest'],x7['anchors'],7);parent7.surface='mean'
    print('MEASURE formed native output against actual neutral child',flush=True)
    child_meta,child_evidence=measure_new_child(parent,parent7,out,outchart,np.repeat(body,4),measure,util)
    child_record=util.save_tree(root,'ACTUAL_NEW_CHILD_MEASUREMENT',child_evidence)
    formation=dict(algorithm='CURVED_PARENT_ORDERED_FINITE_MANDELBULB_BOUNDARY_TARGET_GENERATION',
        input_generation=6,output_generation=7,added_subdivision_passes=1,new_G8=False,projection_contract_check=contract,
        same_input_neutral_control_error=zero_error,operator=operator_meta,field=field_meta,feedback=feedback,
        parent_coverage=coverage,parent_sampler=info,parent_record=parent_record,
        measured_current_family=4,selected_piece=str(parent['piece_id']),measured_pieces=len(measured),
        maximum_formation_vs_neutral=float(norm.max()),moved_controls=int((norm>1e-12).sum()),
        symmetry_correction_maximum=symmetry_correction,actual_new_child=child_meta,
        claim='Completed F/E/V use full residuals to one measured-parent curved target carrying an actual finite Mandelbulb boundary. Visual quality, recursive continuation and global intersections remain unproven; this is actual G7.')
    util.write(root/'FORMATION.json',formation)
    old_receipt=Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial08_recursive_generation/RECEIPT.json')
    old=json.loads(old_receipt.read_text(encoding='utf8'));control=dict(old['variants']['REFERENCE_G7']);old_native=Path(control['geometry'])
    if util.digest(old_native)!=control['geometry_sha256']:raise ValueError('Preserved actual neutral native changed.')
    sources[str(old_receipt)]=util.digest(old_receipt);sources[str(old_native)]=control['geometry_sha256']
    control_dir=root/'CONTROL';control_dir.mkdir();control_file=control_dir/'geometry.npz';shutil.copyfile(old_native,control_file)
    if util.digest(control_file)!=control['geometry_sha256']:raise ValueError('Exact neutral native copy differs.')
    control['geometry']=str(control_file)
    print('SAVE complete actual formed G7 native and next-step controls',flush=True)
    formed=native.save(root,'FORMED',out,q7,dict(formation=formation,global_self_intersection_checked=False))
    x7['xyz']=out;control_path=root/'FORMED/control_quad.npz';np.savez_compressed(control_path,**x7)
    formed.update(control_quad=str(control_path),control_quad_sha256=util.digest(control_path))
    for item in snapshots.values():
        if util.digest(item['source'])!=item['sha256'] or util.digest(item['snapshot'])!=item['sha256']:raise ValueError('Generation source changed.')
    for path,h in sources.items():
        if util.digest(path)!=h:raise ValueError('Actual preserved input changed.')
    util.write(root/'RECEIPT.json',dict(kind='ACTUAL_G6_G7_ORDERED_MANDELBULB_TARGET_GENERATION',date='2026-10-15',
        variants={'CONTROL':control,'FORMED':formed},source_snapshots=snapshots,sources=sources,
        source_control=str(folder6/'control_quad.npz'),source_control_sha256=sources[str(folder6/'control_quad.npz')],
        neutral_control=str(folder7/'control_quad.npz'),neutral_control_sha256=sources[str(folder7/'control_quad.npz')],
        source_xyz_sha256=util.ah(mesh.xyz),formation=formation,parent_measurement=parent_record,
        target_surface=field_record,stage_evidence=stage_record,stage_complete_hashes=stage_hashes,new_child_measurement=child_record,
        original_event_bank=bank_metadata,elapsed_seconds=time.perf_counter()-started,
        baseline='CONTROL is the exact neutral G7 from the same actual G6; accepted NESTED02 is a separate design reference, not this causal control.',
        source_geometry_unchanged=True,generation=7,added_subdivision_passes=1,new_G8=False,
        visual_status='Pending actual matched CONTROL/FORMED native render.'))
    print('MANDELBULB_TARGET_GENERATION_COMPLETE',time.perf_counter()-started,flush=True)


if __name__=='__main__':main()
