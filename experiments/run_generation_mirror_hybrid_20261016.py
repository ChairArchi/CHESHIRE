"""Whole-column prototype: history classification, true interleaved CC, paper-origin actual Tissue.

The column underlay is never smoothed. A paired neutral CC transports only a new
coarse Mandel displacement. Paper Boolean topology is retained in its standalone
asset; its actual Tissue top-height pullback is an explicitly single-valued adapter.
"""
from pathlib import Path
import sys, json, argparse, importlib.util, time, gc, shutil
sys.dont_write_bytecode=True
import numpy as np
from scipy.sparse import csr_matrix

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
from cheshire.ornament_subdivision import prepare_cc1
BASE=Path(r'E:\CHESHIRE_DATA\experiments\fold_aligned_mandel_20261015')
ROOT=Path(r'E:\CHESHIRE_DATA\experiments\generation_mirror_hybrid_20261016')
HISTORY=ROOT/'history_classification'
SAFE22=BASE/'variant22_flow_corrected_visible_relief_whole_hybrid_20261016'
SOURCE16=BASE/'variant16_whole_hybrid_20261016'
CHUNK=65536

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj);return obj
legacy=module('frozen_orientation_and_original_host_helpers',BASE/'run_visible_organic_flow_whole_hybrid_20261016.py')
base,m,core=legacy.base,legacy.m,legacy.core
read,bound,smooth=legacy.read,legacy.bound,legacy.smooth
WORK=ROOT/'working_arrays'

def disk(name,shape,dtype=np.float64,fill=0):
    WORK.mkdir(exist_ok=True,parents=True);path=WORK/(name+'.npy')
    if path.exists():raise FileExistsError(str(path))
    arr=np.lib.format.open_memmap(path,mode='w+',dtype=dtype,shape=shape)
    if fill is not None:arr.fill(fill)
    return arr
def record(path):return dict(path=str(path),sha256=core.sha(path))
def rec_array(name):return record(WORK/(name+'.npy'))
def load(name):return np.load(WORK/(name+'.npy'),mmap_mode='r',allow_pickle=False)
def write(name,value):core.write(ROOT/name,value)
def flush(*arrays):
    for arr in arrays:
        if hasattr(arr,'flush'):arr.flush()

def execution_snapshots():
    folder=ROOT/'source_snapshot_run';folder.mkdir(exist_ok=True)
    paths=[Path(__file__).resolve(),REPO/'src/cheshire/ornament_subdivision.py',
        Path(legacy.__file__),Path(base.__file__),Path(base.c.__file__),Path(m.__file__),Path(core.__file__),
        Path(base.c.mandel.__file__),HISTORY/'run_history_classification.py',HISTORY/'history_classifier.py']
    records={}
    for path in paths:
        target=folder/path.name
        if target.exists():
            if core.sha(target)!=core.sha(path):raise ValueError('Executed source changed after coarse stage: '+str(path))
        else:shutil.copyfile(path,target)
        records[str(path)]=dict(source=str(path),snapshot=str(target),sha256=core.sha(path))
    return records

def context():
    sources={};baseline,control,px,py,cached=base.load_host(sources)
    sr=read(SOURCE16/'SOURCE_FIELD_RECEIPT.json',sources)
    f={k:bound(sr[k],sources) for k in ('original_normals','normal_safety_cap','source_weights',
        'source_eligibility','protected_cap_mask','flow_core_guard','source_valley_guard')}
    safe=read(SAFE22/'RECEIPT.json',sources);cp=Path(safe['variants']['MANDEL']['control_quad'])
    if core.sha(cp)!=safe['variants']['MANDEL']['control_quad_sha256']:raise ValueError('Safe22 binding changed.')
    sources[str(cp)]=core.sha(cp);prior=m.mapped(cp,'xyz')
    display_meta=read(SAFE22/'CLASSIFICATION.json',sources)
    display=bound(display_meta['display_flow_protection'],sources)
    if prior.shape!=control['xyz'].shape:raise ValueError('Safe22 topology contract differs.')
    return sources,baseline,control,px,py,cached,f,prior,display

def profile_source(xyz,normal,weights,eligible,classes,valley,rep,px,py,period,amplitudes,name,sources):
    """Evaluate finite power8/iteration8 boundary anew on the actual supplied surface."""
    n=len(xyz);raw=disk(name+'_CANONICAL_RAW',xyz.shape);height=disk(name+'_PROFILE_HEIGHT',(n,))
    amplitude=disk(name+'_AMPLITUDE',(n,))
    boundary=core.load_tree(base.c.PROFILE/'MANDELBULB_PROFILE.json',sources)
    profile=base.c.mandel.BoundaryProfile(boundary['theta'],boundary['phi'],boundary['radius'],{})
    k=2*np.pi/period;epsilon=.01*(period/4)
    def evaluate(q0,q1):
        theta=np.arccos(np.clip(np.cos(q0),-1,1))
        phi=np.mod(q1+np.where(np.sin(q0)<0,np.pi,0),2*np.pi)
        return np.clip((profile._spline.ev(theta,phi)-profile.centre)/profile.scale,-1,1)
    for a in range(0,n,CHUNK):
        b=min(a+CHUNK,n);cw=np.maximum(np.asarray(classes[a:b]),0)
        missing=cw.sum(1)<=1e-15;cw[missing,1]=1;cw/=cw.sum(1)[:,None]
        cw=smooth(cw);cw/=cw.sum(1)[:,None]
        amp=cw@np.asarray(amplitudes);amp=amp*(1-valley[a:b])+min(amplitudes)*.4*valley[a:b]
        amplitude[a:b]=amp*eligible[a:b]
        ids=np.arange(a,b);ids=ids[(rep[a:b]==ids)&eligible[a:b]&(weights[a:b]>0)]
        p=np.sqrt(xyz[ids]**2+epsilon**2)
        h=evaluate(k*(p@base.c.mandel.AXIS_A),k*(p@base.c.mandel.AXIS_B))
        height[ids]=h;raw[ids]=(h*amplitude[ids]*weights[ids])[:,None]*normal[ids]
    field=BASE/'trial02_continuous/FIELD_DELTA.npz';sources[str(field)]=core.sha(field)
    old_ids=m.mapped(field,'ids');old_can=np.asarray(old_ids[old_ids<len(rep)])
    old_can=old_can[rep[old_can]==old_can]
    # Atlas rows use full G7 canonical ordering even for the retained G6 subset.
    full_ids=m.mapped(field,'ids');rep7=np.load(BASE/'trial03b_refined/working_arrays/4_representatives.npy',mmap_mode='r')
    full_can=np.asarray(full_ids[rep7[full_ids]==full_ids]);indices=np.flatnonzero(full_can<n)
    cache=BASE/'trial06_density_low_20261016/working_arrays'
    ap=list(cache.glob('*_shared_exact_density_attributes.npy'));wp=list(cache.glob('*_shared_exact_density_weight.npy'))
    if len(ap)!=1 or len(wp)!=1:raise ValueError('Unique certified physical atlas required.')
    attrs=bound(record(ap[0]),sources);atlasw=bound(record(wp[0]),sources)
    if attrs.shape!=(len(full_can),9):raise ValueError('Physical atlas row identity differs.')
    for a in range(0,len(indices),CHUNK):
        rows=indices[a:a+CHUNK];ids=full_can[rows];data=attrs[rows];w=atlasw[rows]
        h=evaluate(np.pi/2+k*data[:,1],k*data[:,0])
        aligned=(h*amplitude[ids]*weights[ids])[:,None]*normal[ids]
        raw[ids]=raw[ids]*(1-w[:,None])+aligned*w[:,None];height[ids]=height[ids]*(1-w)+h*w
    full=disk(name+'_DELTA',xyz.shape,fill=None)
    for a in range(0,n,CHUNK):
        b=min(a+CHUNK,n);full[a:b]=base.reflected_block(raw,a,b,px,py,rep)
    flush(raw,height,amplitude,full)
    return full,dict(period=period,primary_lobe_spacing=period/8,class_amplitudes=list(amplitudes),
        actual_surface_coordinates_used=True,actual_surface_normals_used=True,
        finite_boundary_sha256=core.ah(boundary['radius']),raw=rec_array(name+'_DELTA'),
        height=rec_array(name+'_PROFILE_HEIGHT'),amplitudes=rec_array(name+'_AMPLITUDE'),
        physical_atlas='Certified physical arc and transverse coordinates; same atlas, newly evaluated profile.')

def coarse():
    start=time.perf_counter();sources,baseline,control,px,py,cached,f,prior,display=context()
    hrec=read(HISTORY/'CLASSIFICATION_RECEIPT.json',sources)
    snapshots=execution_snapshots()
    classes6=bound(hrec['outputs']['SOURCE5_G6'],sources)
    path=core.STATES/'G06_MIDDLE/control_quad.npz';sources[str(path)]=core.sha(path)
    x6=m.mapped(path,'xyz');q6=m.mapped(path,'faces');n6=len(x6);rep=cached['rep'][:n6]
    evidence=core.STATES/'G06_MIDDLE/evidence.npz'
    # G7 retained vertex IDs preserve the G6 reflection involutions.
    if np.max(rep)>=n6 or np.max(px[:n6])>=n6 or np.max(py[:n6])>=n6:raise ValueError('Retained G6 reflection order differs.')
    if classes6.shape!=(n6,5):raise ValueError('Actual new G6 SOURCE5 required.')
    normals6=disk('ACTUAL_G6_NORMALS',x6.shape,fill=None);normals6[:]=base.c.normals(x6,q6);normals6.flush()
    delta,profile=profile_source(x6,normals6,f['source_weights'][:n6],f['source_eligibility'][:n6],classes6,
        f['source_valley_guard'][:n6],rep,px[:n6],py[:n6],.90,[.025,.025,.012,.020,.022],'NEW_COARSE_G6',sources)
    deformed=disk('ACTUAL_COARSE_G6_XYZ',x6.shape,fill=None)
    for a in range(0,n6,CHUNK):
        b=min(a+CHUNK,n6);deformed[a:b]=x6[a:b]+delta[a:b]
    deformed.flush();print('ACTUAL_PAIRED_CC_BEGIN',flush=True)
    old,oldinfo=prepare_cc1(x6,q6,ROOT/'paired_cc_original',chunk=CHUNK)
    new,newinfo=prepare_cc1(deformed,q6,ROOT/'paired_cc_coarse_mandel',chunk=CHUNK)
    q7=control['faces'];nv=len(control['xyz'])
    if oldinfo['output_counts']!=newinfo['output_counts'] or len(old['RAW_CC_XYZ'])!=nv:raise ValueError('Paired actual CC count differs.')
    for a in range(0,len(q7),CHUNK):
        b=min(a+CHUNK,len(q7))
        if not np.array_equal(old['CHILD_QUADS'][a:b],q7[a:b]) or not np.array_equal(new['CHILD_QUADS'][a:b],q7[a:b]):raise ValueError('Actual saved G7 CC lineage differs.')
    raw=disk('CC_COARSE_G7_RAW_DIFFERENCE',(nv,3),fill=None)
    projected=disk('CC_COARSE_G7_DELTA',(nv,3),fill=None)
    tangent_max=0.
    for a in range(0,nv,CHUNK):
        b=min(a+CHUNK,nv);d=new['RAW_CC_XYZ'][a:b]-old['RAW_CC_XYZ'][a:b];raw[a:b]=d
        normal=f['original_normals'][a:b];h=np.einsum('ij,ij->i',d,normal)
        p=h[:,None]*normal;tangent_max=max(tangent_max,float(np.linalg.norm(d-p,axis=1).max(initial=0)))
        projected[a:b]=p
    # Canonical reflection removes only numerical transport roundoff.
    canonical=disk('CC_COARSE_G7_CANONICAL',(nv,3),fill=None);canonical[:]=projected;canonical.flush()
    for a in range(0,nv,CHUNK):
        b=min(a+CHUNK,nv);projected[a:b]=base.reflected_block(canonical,a,b,px,py,cached['rep'])
    flush(raw,projected)
    proof=dict(kind='ACTUAL_G6_MANDELBULB_THEN_PAIRED_NEUTRAL_CATMULL_CLARK_TO_G7',
        coarse_profile=profile,base_CC=oldinfo,decorated_CC=newinfo,
        differential='CC(G6+fresh coarse Mandel)-CC(G6); exact whole G7 child quad identity.',
        raw_difference=rec_array('CC_COARSE_G7_RAW_DIFFERENCE'),normal_projected_difference=rec_array('CC_COARSE_G7_DELTA'),
        maximum_removed_tangent_component=tangent_max,column_underlay_smoothed=False,
        adapter='Project only transported decoration differential onto original G7 normals; original NESTED XYZ retained.',
        classification=record(HISTORY/'CLASSIFICATION_RECEIPT.json'),sources=sources,elapsed_seconds=time.perf_counter()-start)
    proof['source_snapshots']=snapshots
    write('INTERLEAVED_COARSE_RECEIPT.json',proof);print('COARSE_READY',proof['elapsed_seconds'],flush=True)

def graph(q,nv):
    return csr_matrix((np.ones(q.size,np.float32),(q.ravel(),np.roll(q,-1,axis=1).ravel())),shape=(nv,nv))

def guarded_target(original,prior,components,normal,safety,allow,protected,name):
    nv=len(original);target=disk(name+'_DESIRED_XYZ',original.shape,fill=None)
    increment=disk(name+'_MINUS_SAFE22',original.shape,fill=None);scale=disk(name+'_CAP_SCALE',(nv,),fill=None)
    for a in range(0,nv,CHUNK):
        b=min(a+CHUNK,nv);d=sum(np.asarray(c[a:b]) for c in components)
        h=np.abs(np.einsum('ij,ij->i',d,normal[a:b]));s=np.minimum(1,np.divide(safety[a:b],h,out=np.ones_like(h),where=h>0))
        scale[a:b]=s;t=original[a:b]+d*s[:,None];target[a:b]=t
        inc=(t-prior[a:b])*allow[a:b,None];inc[protected[a:b]]=0.;increment[a:b]=inc
    flush(target,increment,scale);return target,increment,scale

def recover(original,prior,increment,q,rep,g,protected,name):
    nv=len(original);gain=disk(name+'_LOCAL_GAIN',(nv,),fill=1.);out=disk(name+'_RECOVERED_XYZ',original.shape,fill=None)
    passes=[];minimum=np.ones(nv)
    for iteration in range(25):
        legacy.write_output(prior,increment,gain,out,protected)
        bad,audit=legacy.orientation_audit(original,out,q);audit['iteration']=iteration;passes.append(audit)
        write(name+'_RECOVERY_PROGRESS.json',dict(passes=passes));print(name,'RECOVERY',iteration,audit['bad_triangles'],flush=True)
        if not audit['bad_triangles']:break
        if iteration==24:raise ValueError('Local safe22 recovery did not remove every original-native reversal.')
        canonical=np.zeros(nv,bool);np.logical_or.at(canonical,rep,bad);bad=canonical[rep]
        ring1=(g.dot(bad.astype(np.float32))>0)&~bad
        ring2=(g.dot((bad|ring1).astype(np.float32))>0)&~bad&~ring1
        factor=np.ones(nv);factor[bad]=.5;factor[ring1]=.5+.5*float(smooth(1/3));factor[ring2]=.5+.5*float(smooth(2/3))
        minimum.fill(1.);np.minimum.at(minimum,rep,np.asarray(gain)*factor)
        for a in range(0,nv,CHUNK):
            b=min(a+CHUNK,nv);gain[a:b]=minimum[rep[a:b]]
        del bad,canonical,ring1,ring2,factor;gc.collect()
    flush(gain,out)
    receipt=dict(kind='ONLY_NEW_INCREMENT_RECOVERY_TOWARD_ACTUAL_SAFE22',passes=passes,
        gain=rec_array(name+'_LOCAL_GAIN'),output=rec_array(name+'_RECOVERED_XYZ'),
        orientation_reference='Actual original NESTED complete native centroid fan, not only safe22.',
        exact_protected_safe22=True,zero_gain_limit='Actual safe22 coordinates',locally_attenuated_controls=int(np.count_nonzero(gain<1)))
    write(name+'_RECOVERY.json',receipt);return out,gain,receipt

def assemble(tissue_raw_receipt):
    started=time.perf_counter()
    if (ROOT/'RECEIPT.json').exists():raise FileExistsError('Completed new whole result preserved.')
    sources,baseline,control,px,py,cached,f,prior,display=context()
    coarsemeta=read(ROOT/'INTERLEAVED_COARSE_RECEIPT.json',sources)
    history=read(HISTORY/'CLASSIFICATION_RECEIPT.json',sources)
    classes=bound(history['outputs']['SOURCE5_G7'],sources)
    tr=read(tissue_raw_receipt,sources)
    # Adapter schema: full native-control scalar arrays; semantic weight applied once, no flow/cap guards yet.
    rawh=bound(tr['height'],sources);raww=bound(tr['priority'],sources)
    original,q=control['xyz'],control['faces'];nv=len(original);rep=cached['rep'];normal=f['original_normals']
    if rawh.shape!=(nv,) or raww.shape!=(nv,) or classes.shape!=(nv,5):raise ValueError('New whole field dimensions differ.')
    cap=f['protected_cap_mask'];full=(display>=1-1e-12)|cap
    allow=disk('INCREMENT_ALLOW',(nv,),fill=None);safety=disk('COMBINED_NORMAL_SAFETY_CAP',(nv,),fill=None)
    tissue=disk('PAPER_TISSUE_G7_DELTA',original.shape);tw=disk('TISSUE_PRIORITY_WEIGHT',(nv,))
    coarsefield=load('CC_COARSE_G7_DELTA');coarseweighted=disk('COARSE_AFTER_TISSUE_PRIORITY',original.shape,fill=None)
    for a in range(0,nv,CHUNK):
        b=min(a+CHUNK,nv);flow=np.clip(f['flow_core_guard'][a:b],0,1);flow[flow>=1-1e-12]=1
        w=np.clip(raww[a:b],0,1)*(1-flow);h=rawh[a:b]*(1-flow)*(1-.75*f['source_valley_guard'][a:b])
        h[cap[a:b]]=0.;w[cap[a:b]]=0.;tw[a:b]=w;tissue[a:b]=h[:,None]*normal[a:b]
        coarseweighted[a:b]=coarsefield[a:b]*(1-w[:,None])
        safety[a:b]=1.75*f['normal_safety_cap'][a:b]
        allow[a:b]=1-np.clip(display[a:b],0,1);allow[a:b][full[a:b]]=0.
    flush(allow,safety,tissue,tw,coarseweighted)
    g=graph(q,nv)
    ct,ci,cs=guarded_target(original,prior,[coarseweighted,tissue],normal,safety,allow,full,'COARSE_STAGE')
    coarseactual,cgain,crecovery=recover(original,prior,ci,q,rep,g,full,'COARSE_STAGE')
    actualnormal=disk('ACTUAL_COARSE_STAGE_NORMALS',original.shape,fill=None)
    actualnormal[:]=base.c.normals(coarseactual,q);actualnormal.flush()
    fine,finemeta=profile_source(coarseactual,actualnormal,f['source_weights'],f['source_eligibility'],classes,
        f['source_valley_guard'],rep,px,py,.42,[.008,.006,.003,.005,.005],'NEW_FINE_G7',sources)
    fineweighted=disk('FINE_AFTER_TISSUE_PRIORITY',original.shape,fill=None)
    for a in range(0,nv,CHUNK):
        b=min(a+CHUNK,nv);fineweighted[a:b]=fine[a:b]*(1-tw[a:b,None])
    fineweighted.flush()
    desired,increment,scale=guarded_target(original,prior,[coarseweighted,fineweighted,tissue],normal,safety,allow,full,'FINAL')
    output,gain,recovery=recover(original,prior,increment,q,rep,g,full,'FINAL')
    del g;gc.collect()
    moved=0;maxnormal=maxtangent=symmetry=0.;samples=[]
    for a in range(0,nv,CHUNK):
        b=min(a+CHUNK,nv);d=output[a:b]-original[a:b];h=np.einsum('ij,ij->i',d,normal[a:b])
        if np.any(np.abs(h)>safety[a:b]+3e-12):raise ValueError('Combined cap violated.')
        if not np.array_equal(output[a:b][full[a:b]],prior[a:b][full[a:b]]):raise ValueError('Protected22 coordinates changed.')
        if not np.array_equal(output[a:b][cap[a:b]],original[a:b][cap[a:b]]):raise ValueError('Original structural caps changed.')
        moved+=int(np.any(output[a:b]!=prior[a:b],axis=1).sum())
        maxnormal=max(maxnormal,float(np.abs(h).max(initial=0)))
        maxtangent=max(maxtangent,float(np.linalg.norm(d-h[:,None]*normal[a:b],axis=1).max(initial=0)))
        for axis,pair in enumerate((px,py)):
            mirrored=np.asarray(output[pair[a:b]]).copy();mirrored[:,axis]*=-1
            symmetry=max(symmetry,float(np.abs(output[a:b]-mirrored).max(initial=0)))
        ids=np.arange(a,b,64);effective=(gain[ids]*allow[ids]*scale[ids])[:,None]
        samples.append(np.column_stack((ids,gain[ids],allow[ids],scale[ids],tw[ids],
            np.linalg.norm(coarseweighted[ids]*effective,axis=1),np.linalg.norm(fineweighted[ids]*effective,axis=1),
            np.linalg.norm(tissue[ids]*effective,axis=1),np.linalg.norm(output[ids]-prior[ids],axis=1))))
    if symmetry>2e-12:raise ValueError('Whole XY reflection symmetry changed: '+str(symmetry))
    sample=np.concatenate(samples);samplepath=ROOT/'FINAL_METHOD_CONTRIBUTION_SAMPLES.npz'
    np.savez(samplepath,values=sample,columns=np.array(['control_id','increment_gain','increment_allow','combined_cap_scale','Tissue_priority','effective_coarse','effective_fine','effective_paper_Tissue','change_from22']))
    contribution={name:dict(nonzero_sample_controls=int(np.count_nonzero(sample[:,col]>1e-12)),
        effective_norm_quantiles=np.quantile(sample[sample[:,col]>1e-12,col],[0,.1,.5,.9,1]).tolist()) for name,col in [('coarse_actual_CC',5),('fresh_fine',6),('paper_actual_Tissue',7)]}
    if any(v['nonzero_sample_controls']==0 for v in contribution.values()):raise ValueError('Required new method has zero effective contribution.')
    nf=len(q);vertices=disk('NATIVE_XYZ',(nv+nf,3),fill=None);triangles=disk('NATIVE_FACES',(4*nf,3),np.int64,fill=None)
    vertices[:nv]=output;minarea=mindot=float('inf');diagbad=0;diagbaseline_degenerate=0
    for a in range(0,nf,CHUNK):
        b=min(a+CHUNK,nf);iq=q[a:b];o=original[iq];p=output[iq];oc=o.mean(1);pc=p.mean(1)
        vertices[nv+a:nv+b]=pc;tri=triangles[4*a:4*b].reshape(-1,4,3)
        tri[:,:,0]=iq;tri[:,:,1]=np.roll(iq,-1,axis=1);tri[:,:,2]=(nv+np.arange(a,b))[:,None]
        aa=np.cross(o-oc[:,None],np.roll(o,-1,axis=1)-oc[:,None]);bb=np.cross(p-pc[:,None],np.roll(p,-1,axis=1)-pc[:,None])
        area=.5*np.linalg.norm(bb,axis=2);dot=np.einsum('nki,nki->nk',aa,bb)
        if np.any(dot<=0) or np.any(area<=0) or not np.isfinite(area).all():raise ValueError('Complete native orientation failure.')
        minarea=min(minarea,float(area.min()));mindot=min(mindot,float(dot.min()))
        for corners in ((0,1,2),(0,2,3),(0,1,3),(1,2,3)):
            u,v,w=corners;ad=np.cross(o[:,v]-o[:,u],o[:,w]-o[:,u]);bd=np.cross(p[:,v]-p[:,u],p[:,w]-p[:,u])
            valid=np.linalg.norm(ad,axis=1)>0;diagbaseline_degenerate+=int(np.count_nonzero(~valid))
            diagbad+=int(np.count_nonzero(valid&(np.einsum('ij,ij->i',ad,bd)<=0)))
    flush(vertices,triangles)
    facehash=core.ah(triangles)
    if facehash!=baseline['faces_sha256']:raise ValueError('Native topology differs.')
    quality=dict(all_finite=True,degenerate_triangles=0,original_to_output_orientation_reversals=0,
        minimum_triangle_area=minarea,minimum_original_to_output_triangle_cross_dot=mindot,
        both_quad_diagonal_orientation_reversals=diagbad,baseline_degenerate_diagonal_triangles=diagbaseline_degenerate,
        diagonal_check_is_auxiliary_native_fan_is_rendered=True,maximum_normal_displacement=maxnormal,
        maximum_tangent_displacement=maxtangent,XY_symmetry_error=symmetry,global_self_intersection_checked=False)
    classmeta=dict(shape_vertex_fields=record(HISTORY/'SOURCE5_G7.npy'),protected_cap_mask=record(f_path('protected_cap_mask')),
        display_flow_protection=record(Path(read(SAFE22/'CLASSIFICATION.json')['display_flow_protection']['path'])),
        tissue_host_faces=record(HISTORY/'TISSUE_HOSTS.npz'),
        lineage_receipt=record(Path(r'E:\CHESHIRE_DATA\experiments\whole_tissue_relief_20261016\UV_LINEAGE_RECEIPT.json')),
        classification_receipt=record(HISTORY/'CLASSIFICATION_RECEIPT.json'),tissue_host_receipt=record(tissue_raw_receipt),
        SOURCE=history,Tissue=tr,priority='Constructive structure, protected established flow, generation-responsive SOURCE5, actual paper-origin Tissue.')
    formation=dict(kind='GENERATION_HISTORY_ACTUAL_CC_AND_PAPER_TISSUE_WHOLE_PROTOTYPE',date='2026-10-16',
        classification=classmeta,coarse=coarsemeta,fresh_fine=finemeta,paper_Tissue=tr,
        interleaving='fresh G6 Mandel → actual paired neutral CC → original G7 normal pullback → protected coarse stage → fresh fine Mandel evaluated on that actual stage',
        paper_application='Actual cut/mirror/Boolean union 3D component → top-ray height adapter → actual Tissue → G3/G7 exact UV lineage. Column receives relief, not solid Boolean union.',
        large_column_underlay_smoothed=False,original_NESTED_underlay_retained=True,
        coarse_stage_recovery=crecovery,LOCAL_HEIGHT_RECOVERY=recovery,method_contributions=contribution,
        method_contribution_samples=record(samplepath),moved_from22_controls=moved,control_vertices=nv,
        geometry_quality=quality,flow_core22_changed_controls=0,original_structural_caps_exact=True,
        combined_cap=rec_array('FINAL_CAP_SCALE'),increment_allow=rec_array('INCREMENT_ALLOW'))
    for name,value in [('CLASSIFICATION.json',classmeta),('FORMATION.json',formation),('GEOMETRY_QUALITY.json',quality),
        ('LOCAL_HEIGHT_RECOVERY.json',recovery),('PRESERVATION_AUDIT.json',dict(geometry_quality=quality,flow_core22_changed_controls=0,original_structural_caps_exact=True))]:write(name,value)
    folder=ROOT/'MANDEL';folder.mkdir();gp=folder/'geometry.npz';np.savez(gp,xyz=vertices,faces=triangles)
    cp=folder/'control_quad.npz';control['xyz']=output;np.savez(cp,**control)
    native=dict(geometry=str(gp),geometry_sha256=core.sha(gp),xyz_sha256=core.ah(vertices),faces_sha256=facehash,
        vertices=len(vertices),triangles=len(triangles),control_quad=str(cp),control_quad_sha256=core.sha(cp),validation=dict(formation,mesh=quality))
    for path,digest in sources.items():
        if core.sha(path)!=digest:raise ValueError('Executed formation source changed: '+path)
    write('RECEIPT.json',dict(kind=formation['kind'],date='2026-10-16',variants=dict(MANDEL=native,REFERENCE_NESTED=baseline,REFERENCE_TIP_FINISH=baseline),
        comparison_source_native_path=baseline['geometry'],comparison_source_native_geometry_sha256=baseline['geometry_sha256'],formation=formation,
        native_arrays=dict(xyz=rec_array('NATIVE_XYZ'),faces=rec_array('NATIVE_FACES')),sources=sources,
        source_snapshots=execution_snapshots(),elapsed_seconds=time.perf_counter()-started))
    print('NEW_WHOLE_COMPLETE',moved,quality,contribution,time.perf_counter()-started,flush=True)

def f_path(key):return Path(read(SOURCE16/'SOURCE_FIELD_RECEIPT.json')[key]['path'])
if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--coarse',action='store_true');group.add_argument('--tissue-raw-receipt',type=Path)
    args=parser.parse_args();coarse() if args.coarse else assemble(args.tissue_raw_receipt)
