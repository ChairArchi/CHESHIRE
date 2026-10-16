"""Matched actual-parent finite Mandelbulb probe on the exact accepted G7."""
from pathlib import Path
import argparse,gc,importlib.util,json,shutil,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'src'))


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def restore(path,util):
    record=json.loads(path.read_text(encoding='utf8'));npz=Path(record['array_file'])
    if util.digest(npz)!=record['array_file_sha256']:raise ValueError('Measured-state array binding changed.')
    with np.load(npz,allow_pickle=False) as a:
        def decode(v):
            if isinstance(v,dict):
                if 'npz_key' in v:
                    value=a[v['npz_key']]
                    if util.ah(value)!=v['sha256']:raise ValueError('Measured-state array changed.')
                    return value
                return {k:decode(x) for k,x in v.items()}
            if isinstance(v,list):return [decode(x) for x in v]
            return v
        return decode(record['tree'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--families',type=int,nargs='+',default=[4]);args=p.parse_args();root=args.root.resolve()
    if root.exists():raise FileExistsError('Immutable earlier trial; choose fresh root.')
    started=time.perf_counter()
    util=module('parent_mandel_utils',HERE/'run_recursive.py');native=module('parent_mandel_native',HERE/'run_final.py')
    bank=module('parent_mandel_bank',HERE/'original_fold_events.py')
    ownership=module('parent_mandel_ownership',HERE/'parent_ownership.py')
    bulb=module('parent_mandel_volume',HERE/'parent_local_mandelbulb.py')
    formation=module('parent_mandel_form',HERE/'parent_mandel_formation.py')
    renderer=module('parent_mandel_display',HERE/'render_parent_probe.py')
    accepted_path=util.ACCEPTED/'RECEIPT.json'
    if util.digest(accepted_path)!=native.BASE_RECEIPT_SHA:raise ValueError('Accepted receipt changed.')
    accepted=json.loads(accepted_path.read_text(encoding='utf8'));base=accepted['variants']['NESTED']
    source=Path(base['control_quad']);geometry=Path(base['geometry'])
    if util.digest(source)!=base['control_quad_sha256'] or util.digest(geometry)!=base['geometry_sha256']:
        raise ValueError('Accepted actual geometry changed.')
    sources={str(accepted_path):native.BASE_RECEIPT_SHA,str(source):base['control_quad_sha256'],str(geometry):base['geometry_sha256']}
    previous=Path('E:/CHESHIRE_DATA/experiments/fold_junction_development_20261015/trial10_macro_cross_folds')
    prior_receipt_path=previous/'RECEIPT.json';prior=json.loads(prior_receipt_path.read_text(encoding='utf8'))
    if prior['source_control_sha256']!=base['control_quad_sha256'] or prior['formation']['source_xyz_sha256']!=base.get('control_xyz_sha256',prior['formation']['source_xyz_sha256']):
        raise ValueError('Measurement source differs from accepted carrier.')
    state_path=previous/'NEXT_FOLD_STATE.json'
    if Path(prior['next_fold_state']['description']).resolve()!=state_path.resolve():
        raise ValueError('Measured parent description changed.')
    sources[str(prior_receipt_path)]=util.digest(prior_receipt_path)
    sources[str(state_path)]=util.digest(state_path)
    state_meta=json.loads(state_path.read_text(encoding='utf8'));sources[state_meta['array_file']]=state_meta['array_file_sha256']
    parents=restore(state_path,util)['parents']
    evidence_path=previous/'FORMATION_EVIDENCE.json'
    evidence_meta=json.loads(evidence_path.read_text(encoding='utf8'))
    if evidence_meta['array_file_sha256']!=prior['formation_evidence']['array_file_sha256'] or util.digest(evidence_meta['array_file'])!=evidence_meta['array_file_sha256']:
        raise ValueError('Saved actual shoulder measurement changed.')
    sources[str(evidence_path)]=util.digest(evidence_path)
    sources[evidence_meta['array_file']]=evidence_meta['array_file_sha256']
    with np.load(evidence_meta['array_file'],allow_pickle=False) as a:
        for index,parent in enumerate(parents):
            record=evidence_meta['tree']['child_'+format(index,'03')+'_actual_shoulder_xyz']
            value=a[record['npz_key']]
            if util.ah(value)!=record['sha256']:raise ValueError('Measured shoulder XYZ changed.')
            parent['controller_shoulder_xyz']=value
    print('LOAD exact accepted G7 carrier and already measured parent native rails',flush=True)
    control=util.arrays(source);xyz=control['xyz'];quads=control['faces'];chart=control['chart']
    if util.ah(xyz)!=prior['formation']['source_xyz_sha256']:raise ValueError('Rails were measured on another surface.')
    owners_folder,_=util.bound_stage('G03_SIDEWALL',sources)
    with np.load(owners_folder/'control_quad.npz',allow_pickle=False) as a:q3=a['faces']
    recovered=quads
    for _ in range(4):recovered=recovered.reshape(-1,4,4)[:,:,1]
    if not np.array_equal(recovered,q3):raise ValueError('Actual SOURCE ancestry mismatch.')
    with np.load(owners_folder/'evidence.npz',allow_pickle=False) as a:body=np.repeat(a['face_event_ids']==0,256)
    free=np.ones(len(xyz),bool);free[np.unique(quads[~body])]=False
    surface=util.STATES/'G07_SURFACE';surface_meta=json.loads((surface/'generation.json').read_text(encoding='utf8'))
    pair_path=surface/'evidence.npz'
    if util.digest(pair_path)!=surface_meta['evidence_file_sha256']:raise ValueError('Actual G7 mirror evidence changed.')
    sources[str(pair_path)]=surface_meta['evidence_file_sha256']
    with np.load(pair_path,allow_pickle=False) as a:pairs={k:a['mirror_'+k.lower()+'_vertex_pairs'] for k in ('X','Y')}
    events,bank_metadata=bank.load_events()
    root.mkdir(parents=True);snapshots={}
    code=[Path(__file__).resolve(),HERE/'parent_mandel_formation.py',HERE/'parent_local_mandelbulb.py',HERE/'parent_ownership.py',
          HERE/'render_parent_probe.py',HERE/'run_recursive.py',HERE/'run_final.py',HERE/'original_fold_events.py',HERE/'actual_seed_fold_events.json',*bank.helper_paths(),*ownership.helper_paths()]
    for file in dict.fromkeys(Path(x).resolve() for x in code):
        target=root/'source_snapshot_run'/file.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        snapshots[file.relative_to(REPO).as_posix()]=dict(source=str(file),snapshot=str(target),sha256=util.digest(file))
    ids,delta,formation_meta,evidence=formation.form(xyz,chart,parents,events,free,pairs,args.families,bulb,ownership)
    util.write(root/'FORMATION.json',formation_meta);evidence_record=util.save_tree(root,'FIELD_EVIDENCE',evidence)
    delta_path=root/'FIELD_DELTA.npz';np.savez_compressed(delta_path,ids=ids,delta=delta,control_vertices=np.array(len(xyz)))
    print('VERIFY full unchanged native topology and exact new fan-centre coordinates',flush=True)
    with np.load(geometry,allow_pickle=False) as a:full=a['xyz'];faces=a['faces']
    if util.ah(full)!=base['xyz_sha256'] or util.ah(faces)!=base['faces_sha256']:raise ValueError('Actual native arrays changed.')
    full,reconstruction=renderer.apply_sparse_control_delta(full,xyz,quads,ids,delta)
    expected_sha=util.ah(full)
    changed=quads[np.any(np.isin(quads,ids),axis=1)]
    out=xyz.copy();out[ids]+=delta
    minarea=float('inf');flipped=0;triangles=0
    for start in range(0,len(changed),131072):
        q=changed[start:start+131072];old=xyz[q];new=out[q];oc=old.mean(1);nc=new.mean(1)
        for corner in range(4):
            a0=np.cross(old[:,corner]-oc,old[:,(corner+1)%4]-oc);a1=np.cross(new[:,corner]-nc,new[:,(corner+1)%4]-nc)
            area=.5*np.linalg.norm(a1,axis=1);minarea=min(minarea,float(area.min(initial=float('inf'))))
            flipped+=int((np.einsum('ij,ij->i',a0,a1)<0.).sum());triangles+=len(q)
    if minarea<=0. or not np.isfinite(full).all():raise ValueError('Nonfinite or degenerate actual changed triangles.')
    quality=dict(changed_native_triangles=triangles,minimum_changed_triangle_area=minarea,orientation_reversals_vs_source=flipped,
        orientation_reversal_fraction=flipped/max(triangles,1),self_intersections_checked=False)
    util.write(root/'QUALITY.json',quality)
    for s in snapshots.values():
        if util.digest(s['source'])!=s['sha256'] or util.digest(s['snapshot'])!=s['sha256']:raise ValueError('Code changed during probe.')
    for path,h in sources.items():
        if util.digest(path)!=h:raise ValueError('Read-only source changed during probe.')
    util.write(root/'PROBE_RECEIPT.json',dict(kind='MATCHED_ACTUAL_PARENT_MANDELBULB_PROBE',date='2026-10-15',
        baseline_native=str(geometry),baseline_native_sha256=base['geometry_sha256'],
        baseline_control_quad=str(source),baseline_control_quad_sha256=base['control_quad_sha256'],baseline_record=base,
        variants={'CONTROL':dict(kind='BASELINE',xyz_sha256=base['xyz_sha256']),
                  'FIELD':dict(kind='CONTROL_DELTA',control_delta=str(delta_path),control_delta_sha256=util.digest(delta_path),xyz_sha256=expected_sha)},
        source_snapshots=snapshots,sources=sources,formation=formation_meta,field_evidence=evidence_record,
        reconstruction=reconstruction,quality=quality,selected_families=args.families,original_event_bank=bank_metadata,
        elapsed_seconds=time.perf_counter()-started,
        scope='Same accepted actual G7 native mesh and unchanged topology. CONTROL is exact accepted carrier; FIELD differs only by one parent-owned finite 3D field response. No omitted source fields, extra subdivision, topology growth, camera-defined sculpture, or SDF claim.'))
    print('PARENT_MANDEL_PROBE_COMPLETE',time.perf_counter()-started,flush=True)


if __name__=='__main__':main()
