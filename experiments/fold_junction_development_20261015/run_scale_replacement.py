"""User-directed TEST: replace sub-cutoff folds over the entire column.

Remove the late detail recipe, filter remaining fine geometry intrinsically
on the real G4 all-role mesh, then prolong the macro carrier to native G7 and
cover it with a finite Mandelbulb-boundary-derived geometric response.
"""
from pathlib import Path
import argparse,gc,importlib.util,json,shutil,sys,time
import numpy as np

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'src'))


def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def normals(xyz,q,chunk=131072):
    nf=len(q);fn=np.empty((nf,3),float)
    for start in range(0,nf,chunk):
        stop=min(start+chunk,nf);p=xyz[q[start:stop]];centre=p.mean(1)
        fn[start:stop]=np.cross(p-centre[:,None],np.roll(p,-1,axis=1)-centre[:,None]).sum(1)
    result=np.column_stack([np.bincount(q.ravel(),weights=np.repeat(fn[:,k],4),minlength=len(xyz)) for k in range(3)])
    length=np.linalg.norm(result,axis=1)
    if np.any(length<=1e-20):raise ValueError('Carrier contains a vertex without a normal.')
    return result/length[:,None]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--cutoff',type=float,default=.30);args=p.parse_args();root=args.root.resolve()
    if root.exists():raise FileExistsError('Previous trial preserved; select fresh root.')
    if not 0.<args.cutoff<1.:raise ValueError('Expected physical sub-column cutoff.')
    started=time.perf_counter();util=module('scale_replace_utils',HERE/'run_recursive.py')
    native=module('scale_replace_native',HERE/'run_final.py')
    coarse=module('scale_replace_filter',HERE/'physical_scale_carrier.py')
    mandel=module('scale_replace_mandel',HERE/'mandelbulb_surface_replacement.py')
    renderer=module('scale_replace_reconstruction',HERE/'render_parent_probe.py')
    source_receipt=util.ACCEPTED/'RECEIPT.json'
    if util.digest(source_receipt)!=native.BASE_RECEIPT_SHA:raise ValueError('Accepted source receipt changed.')
    accepted=json.loads(source_receipt.read_text(encoding='utf8'));base=accepted['variants']['NESTED']
    source=Path(base['control_quad']);geometry=Path(base['geometry'])
    if util.digest(source)!=base['control_quad_sha256'] or util.digest(geometry)!=base['geometry_sha256']:
        raise ValueError('Accepted preserved arrays changed.')
    sources={str(source_receipt):native.BASE_RECEIPT_SHA,str(source):base['control_quad_sha256'],str(geometry):base['geometry_sha256']}
    folder,_=util.bound_stage('G04_NEUTRAL',sources)
    g4=util.arrays(folder/'control_quad.npz')
    with np.load(source,allow_pickle=False) as a:original=a['xyz'];q7=a['faces']
    topology={7:q7}
    for g in (6,5,4):topology[g]=topology[g+1].reshape(-1,4,4)[:,:,1].copy()
    if not np.array_equal(topology[4],g4['faces']):raise ValueError('Accepted G7->actual G4 ancestry differs.')
    root.mkdir(parents=True);snapshots={}
    code=[Path(__file__).resolve(),HERE/'physical_scale_carrier.py',HERE/'mandelbulb_surface_replacement.py',
          HERE/'run_recursive.py',HERE/'run_final.py',HERE/'render_parent_probe.py',*coarse.helper_paths(),*mandel.helper_paths()]
    for file in dict.fromkeys(Path(x).resolve() for x in code):
        target=root/'source_snapshot_run'/file.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        snapshots[file.relative_to(REPO).as_posix()]=dict(source=str(file),snapshot=str(target),sha256=util.digest(file))
    print('REPLACE_FINE: physical all-role lowpass on real G4, cutoff',args.cutoff,flush=True)
    carrier,filter_meta,filter_evidence=coarse.lowpass(g4['xyz'],g4['faces'],cutoff=args.cutoff)
    filter_record=util.save_tree(root,'PHYSICAL_FILTER_EVIDENCE',filter_evidence)
    np.savez_compressed(root/'MACRO_CARRIER_G4.npz',xyz=carrier,faces=g4['faces'])
    refinement=[]
    for g in (4,5,6):
        print('REPLACE_FINE: exact neutral CC macro carrier',g,'->',g+1,flush=True)
        edges,following,degree=native.recover(topology[g],topology[g+1])
        carrier=native.neutral_delta(carrier,topology[g],edges,following,degree)
        refinement.append(dict(input_generation=g,output_generation=g+1,vertices=len(carrier),quads=len(topology[g+1])))
        del edges,following,degree;gc.collect()
    surface=util.STATES/'G07_SURFACE';meta=json.loads((surface/'generation.json').read_text(encoding='utf8'))
    pair_path=surface/'evidence.npz'
    if util.digest(pair_path)!=meta['evidence_file_sha256']:raise ValueError('Actual symmetry-ID evidence changed.')
    sources[str(pair_path)]=meta['evidence_file_sha256']
    with np.load(pair_path,allow_pickle=False) as a:px=a['mirror_x_vertex_pairs'];py=a['mirror_y_vertex_pairs']
    carrier=native.reflect_delta(carrier,px,py)
    print('REPLACE_FINE: calculate actual smooth macro normals and finite Mandelbulb profile',flush=True)
    n=normals(carrier,q7)
    profile,profile_meta,profile_evidence=mandel.build_profile(power=8,iterations=8)
    profile_record=util.save_tree(root,'MANDELBULB_PROFILE',profile_evidence)
    response,response_meta=mandel.displace(carrier,n,profile=profile,cutoff=args.cutoff,amplitude=.035)
    response=native.reflect_delta(response,px,py)
    candidate=carrier+response
    total=candidate-original;ids=np.flatnonzero(np.linalg.norm(total,axis=1)>1e-14);delta=total[ids]
    if not len(ids) or not np.isfinite(candidate).all():raise ValueError('No finite actual replacement.')
    symmetry=0.
    for axis,pair in enumerate((px,py)):
        for start in range(0,len(ids),262144):
            chosen=ids[start:start+262144];mirror=candidate[pair[chosen]].copy();mirror[:,axis]*=-1.
            symmetry=max(symmetry,float(np.max(np.abs(candidate[chosen]-mirror))))
    if symmetry>2e-12:raise ValueError('Replacement lost actual symmetry.')
    height=float(np.ptp(g4['xyz'][:,2]));change=np.linalg.norm(carrier-original,axis=1)
    formation=dict(algorithm='ALL_ROLE_PHYSICAL_SCALE_FINE_FOLD_REPLACEMENT_TEST_V1',
        input='Accepted NESTED02 actual G7',carrier_source='Actual preserved G04_NEUTRAL, all SOURCE/WALL/CAP roles.',
        cutoff=args.cutoff,cutoff_fraction_of_height=args.cutoff/height,physical_height=height,
        filter=filter_meta,refinement=refinement,profile=profile_meta,response=response_meta,
        removed_recipe_layers=['G5 directional detail','G6 directional detail','G6 MIDDLE','G7 primary gain','G7 CHILD','G7 SMALL'],
        carrier_change_norm_quantiles=np.quantile(change,[0,.25,.5,.75,.9,.99,1]).tolist(),
        maximum_new_mandelbulb_response=float(np.linalg.norm(response,axis=1).max()),
        maximum_total_change=float(np.linalg.norm(total,axis=1).max()),moved_controls=len(ids),XY_symmetry_error=symmetry,
        scope='Explicit user-directed whole-column TEST. Existing fine geometry is removed before the new response. Physical cutoff is a smooth intrinsic spectral transition, not an exact semantic feature classifier. Macro flow approximately retained; exact silhouette unchanged is not claimed. No role masks, one-parent restriction, camera sculpture, or extra decoration mesh.',
        generation=7,added_generation_above_original=0,full_volumetric_mandelbulb_topology=False,
        visual_status='Requested research test; actual matched rendering pending, not accepted final design.')
    util.write(root/'FORMATION.json',formation)
    print('REPLACE_FINE: save complete replacement as exact dense control delta',flush=True)
    delta_path=root/'FIELD_DELTA.npz';np.savez_compressed(delta_path,ids=ids,delta=delta,control_vertices=np.array(len(original)))
    del n,response,carrier,total,change,px,py;gc.collect()
    print('REPLACE_FINE: verify complete actual native fan coordinates',flush=True)
    with np.load(geometry,allow_pickle=False) as a:full=a['xyz'];faces=a['faces']
    if util.ah(full)!=base['xyz_sha256'] or util.ah(faces)!=base['faces_sha256']:raise ValueError('Accepted native hashes differ.')
    full,reconstruction=renderer.apply_sparse_control_delta(full,original,q7,ids,delta)
    expected_sha=util.ah(full)
    minimum=float('inf');reversed_count=0;total_triangles=4*len(q7)
    for start in range(0,len(q7),131072):
        q=q7[start:start+131072];a=original[q];b=candidate[q];ac=a.mean(1);bc=b.mean(1)
        for corner in range(4):
            na=np.cross(a[:,corner]-ac,a[:,(corner+1)%4]-ac);nb=np.cross(b[:,corner]-bc,b[:,(corner+1)%4]-bc)
            area=.5*np.linalg.norm(nb,axis=1);minimum=min(minimum,float(area.min()))
            reversed_count+=int((np.einsum('ij,ij->i',na,nb)<0.).sum())
    if minimum<=0.:raise ValueError('Degenerate actual replacement triangles.')
    quality=dict(minimum_native_triangle_area=minimum,triangles=total_triangles,orientation_reversals_vs_original=reversed_count,
        orientation_reversal_fraction=reversed_count/total_triangles,global_self_intersection_checked=False)
    util.write(root/'QUALITY.json',quality)
    for item in snapshots.values():
        if util.digest(item['source'])!=item['sha256'] or util.digest(item['snapshot'])!=item['sha256']:raise ValueError('Executed code changed.')
    for path,h in sources.items():
        if util.digest(path)!=h:raise ValueError('Preserved source changed.')
    util.write(root/'PROBE_RECEIPT.json',dict(kind='WHOLE_COLUMN_SUBCUTOFF_MANDELBULB_REPLACEMENT_TEST',date='2026-10-15',
        baseline_native=str(geometry),baseline_native_sha256=base['geometry_sha256'],
        baseline_control_quad=str(source),baseline_control_quad_sha256=base['control_quad_sha256'],baseline_record=base,
        variants={'CONTROL':dict(kind='BASELINE',xyz_sha256=base['xyz_sha256']),
                  'FIELD':dict(kind='CONTROL_DELTA',control_delta=str(delta_path),control_delta_sha256=util.digest(delta_path),xyz_sha256=expected_sha)},
        source_snapshots=snapshots,sources=sources,formation=formation,physical_filter_evidence=filter_record,
        profile_evidence=profile_record,reconstruction=reconstruction,quality=quality,
        reconstruction_code_sha256=util.digest(HERE/'render_parent_probe.py'),elapsed_seconds=time.perf_counter()-started,
        scope='Requested whole-column replacement TEST, not a design adoption. Exact same original native connectivity, physically filtered macro carrier plus finite 3D Mandelbulb-boundary relief, original fine recipe removed.'))
    print('WHOLE_COLUMN_REPLACEMENT_COMPLETE',time.perf_counter()-started,flush=True)


if __name__=='__main__':main()
