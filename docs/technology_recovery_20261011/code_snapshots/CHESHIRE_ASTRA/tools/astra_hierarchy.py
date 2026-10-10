"""Finite curves on transported construction charts of actual triangle meshes.

Rest-plane endpoints are barycentrically transferred to actual native triangles.
After edge flips this is NOT persistent material-edge ancestry or a continuous
ridge certificate. Fixed rest coordinates label changing reference embeddings.
"""
import argparse,json,sys,hashlib,shutil
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task35_analyze import child_valleys,envelope_retention
from hero_design_sprint import guarded,windows_memory

Z_LEVELS=np.arange(500,3501,250,dtype=float)+.12345
SAMPLES=2048
LIMIT='Finite native-triangle construction-chart curves; changing reference connectivity, not persistent material/edge ancestry or continuous ridges. Radial excess is not intrinsic fold depth.'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8')

def barycentric(points,triangles):
    """Two section endpoints per nondegenerate reference triangle."""
    a=triangles[:,0];v=triangles[:,1]-a;w=triangles[:,2]-a
    vv=np.einsum('ij,ij->i',v,v);ww=np.einsum('ij,ij->i',w,w);vw=np.einsum('ij,ij->i',v,w)
    den=vv*ww-vw*vw
    if np.any(den<=1e-14*np.maximum(vv*ww,1e-300)):raise ValueError('Degenerate or ill-conditioned reference triangle.')
    p=points-a[:,None];pv=np.einsum('ikj,ij->ik',p,v);pw=np.einsum('ikj,ij->ik',p,w)
    b=(pv*ww[:,None]-pw*vw[:,None])/den[:,None];c=(pw*vv[:,None]-pv*vw[:,None])/den[:,None]
    out=np.stack([1-b-c,b,c],axis=-1)
    if not np.isfinite(out).all() or np.min(out)<-1e-7 or np.max(out)>1+1e-7:raise ValueError('Cut endpoint lies outside declared reference triangle.')
    recovered=np.einsum('nij,njk->nik',out,triangles)
    scale=max(float(np.ptp(triangles.reshape(-1,3),axis=0).max()),1.)
    if np.max(np.linalg.norm(recovered-points,axis=2),initial=0)>scale*1e-9:raise ValueError('Barycentric reference reconstruction failed.')
    return out

def sample_segments(rest_lines,actual_lines,endpoint_weights,triangle_ids,triangles,samples=SAMPLES):
    """Only relevant angular intervals are allocated, never Nsegments x Nrays.

    Coincident hits are accepted only if reference radius AND actual XYZ agree.
    Multiple distinct reference radii or multiple actual sheets invalidate a ray.
    """
    theta=(np.arange(samples)+.371)*2*np.pi/samples
    radius=np.full(samples,np.nan);xyz=np.full((samples,3),np.nan);reference=np.full((samples,3),np.nan)
    weights=np.full((samples,3),np.nan);supports=np.full((samples,3),-1,np.int64);ids_out=np.full(samples,-1,np.int64)
    hits=np.zeros(samples,np.int32);ambiguous=np.zeros(samples,bool)
    for j,pair in enumerate(rest_lines):
        a,b=pair[:,:2];d=b-a
        scale=max(float(np.linalg.norm(a)),float(np.linalg.norm(b)),1.)
        if abs(a[0]*b[1]-a[1]*b[0])<=1e-12*scale*scale and np.linalg.norm(d)>1e-10:
            # A segment lying along a sampled positive ray gives an interval
            # of radii, never a unique hit. Do not silently discard it.
            rays=np.column_stack([np.cos(theta),np.sin(theta)])
            on_line=(np.abs(rays[:,0]*a[1]-rays[:,1]*a[0])<=1e-10*scale)&(np.abs(rays[:,0]*d[1]-rays[:,1]*d[0])<=1e-10*scale)
            ambiguous|=on_line&(np.maximum(rays@a,rays@b)>1e-9)
            continue
        aa=np.arctan2(a[1],a[0])%(2*np.pi);bb=aa+(np.arctan2(b[1],b[0])-aa+np.pi)%(2*np.pi)-np.pi
        lo,hi=sorted([aa,bb])
        for shift in [-2*np.pi,0,2*np.pi]:
            first=max(0,int(np.ceil((lo+shift)*samples/(2*np.pi)-.371)))
            last=min(samples,int(np.floor((hi+shift)*samples/(2*np.pi)-.371))+1)
            if last<=first:continue
            chosen=np.arange(first,last);u=np.column_stack([np.cos(theta[chosen]),np.sin(theta[chosen])]);den=u[:,0]*d[1]-u[:,1]*d[0]
            good=np.abs(den)>1e-12;chosen=chosen[good];u=u[good];den=den[good]
            r=(a[0]*d[1]-a[1]*d[0])/den;t=(a[0]*u[:,1]-a[1]*u[:,0])/den
            good=(r>0)&(t>=-1e-9)&(t<=1+1e-9);chosen=chosen[good];r=r[good];t=t[good]
            if not len(chosen):continue
            actual=(1-t[:,None])*actual_lines[j,0]+t[:,None]*actual_lines[j,1]
            ref=(1-t[:,None])*rest_lines[j,0]+t[:,None]*rest_lines[j,1]
            bary=(1-t[:,None])*endpoint_weights[j,0]+t[:,None]*endpoint_weights[j,1]
            prior=hits[chosen]>0
            ambiguous[chosen]|=prior&((np.abs(radius[chosen]-r)>1e-6)|(np.linalg.norm(xyz[chosen]-actual,axis=1)>1e-6))
            new=~prior;take=chosen[new]
            radius[take]=r[new];xyz[take]=actual[new];reference[take]=ref[new];weights[take]=bary[new];supports[take]=triangles[triangle_ids[j]];ids_out[take]=triangle_ids[j]
            hits[chosen]+=1
    missing=hits==0;invalid=missing|ambiguous
    xyz[invalid]=np.nan;reference[invalid]=np.nan;weights[invalid]=np.nan;supports[invalid]=-1;ids_out[invalid]=-1
    excess=np.linalg.norm(xyz[:,:2],axis=1)-radius;excess[invalid]=np.nan
    arrays=dict(theta=theta,sample_rest_radius=radius,sample_actual_xyz=xyz,sample_rest_xyz=reference,sample_weights=weights,sample_support_vertices=supports,sample_triangle_ids=ids_out,sample_hits=hits,ambiguous_rays=ambiguous,radial_excess=excess)
    info=dict(samples=samples,missing_rays=int(missing.sum()),ambiguous_rays=int(ambiguous.sum()),duplicate_agreeing_rays=int(((hits>1)&~ambiguous).sum()),valid=bool(not invalid.any()))
    return arrays,info

def section_curve(mesh,z,samples=SAMPLES):
    import trimesh
    faces=mesh.faces
    if not np.all((faces>=0).sum(1)==3):raise ValueError('Native triangles required; no silent polygon conversion.')
    tri=faces[:,:3]
    if not np.isfinite(mesh.xyz).all() or not np.isfinite(mesh.rest).all():raise ValueError('Finite actual and reference embeddings required.')
    reference=trimesh.Trimesh(vertices=mesh.rest,faces=tri,process=False)
    lines,ids=trimesh.intersections.mesh_plane(reference,[0,0,1],[0,0,z],return_faces=True)
    if not len(lines):
        return dict(rest_segments=lines,actual_segments=lines.copy(),segment_triangle_ids=ids),dict(z=float(z),valid=False,reason='No reference intersection',missing_rays=samples,ambiguous_rays=0)
    weights=barycentric(lines,mesh.rest[tri[ids]])
    actual=np.einsum('nij,njk->nik',weights,mesh.xyz[tri[ids]])
    arrays,info=sample_segments(lines,actual,weights,ids,tri,samples)
    arrays.update(rest_segments=lines,actual_segments=actual,segment_triangle_ids=ids,segment_endpoint_weights=weights)
    valid=arrays['sample_triangle_ids']>=0
    rebuilt=np.einsum('ij,ijk->ik',arrays['sample_weights'][valid],mesh.xyz[arrays['sample_support_vertices'][valid]])
    error=float(np.max(np.linalg.norm(rebuilt-arrays['sample_actual_xyz'][valid],axis=1),initial=0))
    info.update(z=float(z),segments=len(lines),transfer_reconstruction_max=error,limitation=LIMIT)
    return arrays,info

def run(candidate,root,stages):
    results=[];previous=None;comparisons=[]
    for number in stages:
        stage=candidate/f'G{number}';start=perf_counter();mesh=load_mesh(stage)
        if mesh.generation!=number:raise ValueError('Stage/native generation mismatch.')
        forecast=512*1024**2+len(mesh.faces)*500;memory=windows_memory()
        if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Hierarchy read/section forecast exceeds available reserve.')
        dest=root/f'G{number}';dest.mkdir(exist_ok=False);curves=[];rows=[]
        for z in Z_LEVELS:
            try:arrays,info=section_curve(mesh,float(z))
            except ValueError as err:arrays={};info=dict(z=float(z),valid=False,reason=str(err))
            path=dest/f'Z{z:.5f}.npz';np.savez_compressed(path,**arrays);info.update(path=str(path),sha256=sha(path));rows.append(info);curves.append(arrays.get('radial_excess'))
        record=dict(generation=number,mesh_path=str(stage/'mesh.npz'),mesh_sha256=sha(stage/'mesh.npz'),triangles=len(mesh.faces),forecast_bytes=forecast,sections=rows,valid_sections=sum(r['valid'] for r in rows),seconds=perf_counter()-start)
        write(dest/'summary.json',record);results.append(record)
        if previous is not None:
            pn,pr,pc=previous;entries=[]
            for i,z in enumerate(Z_LEVELS):
                valid=pr[i]['valid'] and rows[i]['valid'];child=child_valleys(pc[i],curves[i]) if valid else [];envelope=envelope_retention(pc[i],curves[i]) if valid else []
                entries.append(dict(z=float(z),valid=valid,child_basins=child,parent_envelope=envelope))
            comparisons.append(dict(parent_generation=pn,child_generation=number,adjacent_generations=number==pn+1,valid_sections=sum(e['valid'] for e in entries),sections_with_child_basins=sum(bool(e['child_basins']) for e in entries),finite_basin_records=sum(len(e['child_basins']) for e in entries),sections=entries))
        previous=number,rows,curves
        print(candidate.name,'G'+str(number),'valid',record['valid_sections'],'seconds',round(record['seconds'],2),flush=True)
    summary=dict(candidate=str(candidate),z_levels=Z_LEVELS.tolist(),samples=SAMPLES,prominence=15.,stages=results,comparisons=comparisons,limitation=LIMIT,exclusions='Ambiguous/missing chart rays excluded entirely from basin metrics. Uniqueness is reference-radial, not a 3D embedding certificate. Actual world-plane cuts are separate.')
    write(root/'summary.json',summary)

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--stages',default='3,4,5,6,7,8');p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Fresh safe tag required.')
    stages=[int(v) for v in a.stages.split(',')]
    if not stages or stages!=sorted(set(stages)) or any(g<0 for g in stages):raise ValueError('Distinct increasing generations required.')
    for g in stages:
        if not (a.candidate/f'G{g}/validation.json').exists():raise ValueError('Requested stage lacks completed validation: G'+str(g))
    root=Path('E:/CHESHIRE_DATA/astra_research/hierarchy')/a.tag
    if a.worker:run(a.candidate,root,stages);return
    root.mkdir(parents=True,exist_ok=False)
    write(root/'request.json',dict(candidate=str(a.candidate.resolve()),stages=stages,z_levels=Z_LEVELS.tolist(),samples=SAMPLES,prominence=15.,limitation=LIMIT))
    for rel in ['tools/astra_hierarchy.py','tools/task35_analyze.py','examples/task29_search.py']:
        dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest)
    write(root/'source_identity.json',{str(q.relative_to(root/'source')):sha(q) for q in (root/'source').rglob('*') if q.is_file()})
    args=['--candidate',str(a.candidate),'--tag',a.tag,'--stages',a.stages,'--worker']
    result=guarded(args,root/'logs/run',worker_script=Path(__file__));write(root/'execution.json',result)
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
