"""Exact diagnostic rays through actual saved G6 control quad-centre fans."""
from pathlib import Path
import hashlib
import json
import numpy as np

HERE=Path(__file__).resolve().parent
STATES=Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/replay/states')
CAMERA=Path('E:/CHESHIRE_DATA/experiments/parent_nested_folds_20261014/trial02/NESTED_FLAT/review/receipt.json')
RAYS=np.asarray([[.30,.25],[.28,.4],[.32,.55],[.45,.35],[.5,.5],[.65,.5],[.8,.5],[.4,.7]])
EXPECTED={STATES/'G06_MIDDLE/control_quad.npz':'38998220e63e9b9bd98f3d63870db444c681b9531d761581083c554021b8528d',
          STATES/'G06_MIDDLE/evidence.npz':'1f1984a368ea03cc780d5ca72429837cbf6215ac3f7113c7ef4b1fee96a2685e',
          STATES/'G03_SIDEWALL/evidence.npz':'59a74daaaa2defe02b071d59530d95f66e38978d8330d0a0a1e057e51ddbba51'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()

def main():
    output=HERE/'diagnosis_visible_face_owners_results.json'
    if output.exists():raise FileExistsError(output)
    bindings={str(p):sha(p) for p in EXPECTED}
    if any(bindings[str(p)]!=value for p,value in EXPECTED.items()):
        raise ValueError('Actual preserved G6/ownership source hash differs.')
    bindings[str(CAMERA)]=sha(CAMERA)
    view=json.loads(CAMERA.read_text(encoding='utf8'))['actual_views']['close_oblique']
    position,target=np.asarray(view['position']),np.asarray(view['target'])
    if not(np.allclose(position,[-18,28,12],rtol=0,atol=1e-9) and
           np.allclose(target,[-.6,.72,6.6],rtol=0,atol=1e-9) and abs(view['scale']-1.25)<1e-9):
        raise ValueError('Actual close camera differs.')
    forward=target-position;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    screen=np.column_stack(((RAYS[:,0]-.5)*view['scale'],(.5-RAYS[:,1])*view['scale']))
    with np.load(STATES/'G06_MIDDLE/control_quad.npz',allow_pickle=False) as data:
        xyz,quads,chart=data['xyz'],data['faces'],data['chart']
        if int(data['generation'])!=6 or str(data['surface'])!='mean':
            raise ValueError('Actual G6 arithmetic-fan source required.')
    with np.load(STATES/'G06_MIDDLE/evidence.npz',allow_pickle=False) as data:phase=data['directional_phase']
    with np.load(STATES/'G03_SIDEWALL/evidence.npz',allow_pickle=False) as data:
        owners,roles=data['face_event_ids'],data['face_roles']
    if len(quads)!=len(owners)*64:raise ValueError('Actual G6 to G3 face ancestry count differs.')
    depths=np.full(len(RAYS),np.inf)
    hits=[None]*len(RAYS)
    for start in range(0,len(quads),65536):
        q=quads[start:start+65536]
        world=xyz[q];centre=world.mean(axis=1)
        relative=world-target
        projected=np.stack((relative@right,relative@up),axis=-1)
        c=projected.mean(axis=1)
        for corner in range(4):
            a,b=projected[:,corner],projected[:,(corner+1)%4]
            minimum=np.minimum(np.minimum(a,b),c)-1e-12
            maximum=np.maximum(np.maximum(a,b),c)+1e-12
            for ray,p in enumerate(screen):
                candidate=np.flatnonzero((minimum[:,0]<=p[0])&(maximum[:,0]>=p[0])&
                                         (minimum[:,1]<=p[1])&(maximum[:,1]>=p[1]))
                if not len(candidate):continue
                aa,bb,cc=a[candidate],b[candidate],c[candidate]
                denominator=(bb[:,1]-cc[:,1])*(aa[:,0]-cc[:,0])+(cc[:,0]-bb[:,0])*(aa[:,1]-cc[:,1])
                stable=abs(denominator)>1e-18
                candidate=candidate[stable];aa,bb,cc=aa[stable],bb[stable],cc[stable]
                denominator=denominator[stable]
                if not len(candidate):continue
                w0=((bb[:,1]-cc[:,1])*(p[0]-cc[:,0])+(cc[:,0]-bb[:,0])*(p[1]-cc[:,1]))/denominator
                w1=((cc[:,1]-aa[:,1])*(p[0]-cc[:,0])+(aa[:,0]-cc[:,0])*(p[1]-cc[:,1]))/denominator
                weights=np.column_stack((w0,w1,1-w0-w1))
                inside=(weights>=-1e-9).all(axis=1)&(weights<=1+1e-9).all(axis=1)
                candidate,weights=candidate[inside],weights[inside]
                if not len(candidate):continue
                vertices=np.stack((world[candidate,corner],world[candidate,(corner+1)%4],centre[candidate]),axis=1)
                points=(vertices*weights[:,:,None]).sum(axis=1)
                ray_depth=(points-position)@forward
                ray_depth[ray_depth<=0]=np.inf
                pick=int(np.argmin(ray_depth))
                if ray_depth[pick]>=depths[ray]:continue
                local=int(candidate[pick]);face=start+local;ancestor=face//64
                bary=weights[pick];ids=q[local]
                normal=np.cross(vertices[pick,1]-vertices[pick,0],vertices[pick,2]-vertices[pick,0])
                normal/=np.linalg.norm(normal)
                phi=float(np.dot(bary,[phase[ids[corner]],phase[ids[(corner+1)%4]],phase[ids].mean()]))
                material=(chart[ids[corner]]*bary[0]+chart[ids[(corner+1)%4]]*bary[1]+chart[ids].mean(axis=0)*bary[2])
                depths[ray]=float(ray_depth[pick])
                hits[ray]=dict(normalized_image_xy=RAYS[ray].tolist(),hit_xyz=points[pick].tolist(),
                    G6_quad_id=int(face),native_fan_corner=corner,global_native_triangle_id=int(4*face+corner),
                    barycentric=bary.tolist(),G3_face_id=int(ancestor),event_owner=int(owners[ancestor]),
                    face_role=int(roles[ancestor]),role_name={0:'SOURCE',1:'WALL',2:'CAP'}[int(roles[ancestor])],
                    source_only_operator_eligible=bool(owners[ancestor]==0),phase=phi,
                    phase_cycle=int(np.floor(phi/(2*np.pi)+.5)),material_t=float(material[0]),
                    face_normal=normal.tolist(),camera_depth=float(ray_depth[pick]))
    valid=[hit for hit in hits if hit is not None]
    source=sum(hit['event_owner']==0 for hit in valid)
    result=dict(kind='EXACT_ACTUAL_G6_VISIBLE_FACE_OWNERSHIP_RAYS',date='2026-10-15',
        camera=view,source_bindings=bindings,source_generation=6,control_vertices=len(xyz),control_quads=len(quads),
        tested_native_fan_triangles=4*len(quads),rays=hits,hit_rays=len(valid),
        SOURCE_ray_count=source,event_owned_ray_count=len(valid)-source,
        SOURCE_percentage=100*source/len(valid) if valid else None,
        event_owned_percentage=100*(len(valid)-source)/len(valid) if valid else None,
        algorithm='Every actual G6 quad-centre fan triangle is considered in chunks. Projected AABB culling plus exact 2D barycentric containment and minimum positive orthographic depth. No nearest-point fallback or coarse ancestry sampling.',
        ownership='G6 face index // 64 identifies the actual G3_SIDEWALL ancestor; G3 face_event_ids and face_roles are read unchanged.',
        source_surface='Declared arithmetic quad-centre fan of actual preserved G06_MIDDLE controls. Original intermediate native was not stored; this diagnostic evaluates its declared actual control surface.',
        geometry_generated=False,render_generated=False,
        limitation='Eight authored diagnostic rays, not surface-area percentages or a complete visible-image segmentation. SOURCE eligibility here is face ownership; incident nonSOURCE vertices can still be pinned by the formation operator.')
    for path,checksum in bindings.items():
        if sha(path)!=checksum:raise ValueError('Actual source changed during diagnostic.')
    result['source_hashes_verified_after_read']=True
    with output.open('x',encoding='utf8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(output=str(output),hits=hits,SOURCE_ray_count=source,
                         event_owned_ray_count=len(valid)-source),indent=2),flush=True)

if __name__=='__main__':main()
