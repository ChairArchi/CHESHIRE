"""Stage 4 -> 5 study: connected axial flute strips unfold at actual tapers.
Input: aligned closed section rings, followed by cap centers; no smoothing.
Not an inferred historical algorithm. Each new face retains its parent band.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import fluted_generation as common

def evolve(source,output,strength=1.,ridge_power=1.5,generation=1,interstitial=False,child_gain=.55):
    data=json.loads(source.read_text());v=np.asarray(data['vertices'])
    statefile=source.parent/'strip_state.json'
    if statefile.exists():
        state=json.loads(statefile.read_text());rings=v[np.array(state['rings'])];prior_birth=state['band_birth']
    else:
        levels=np.unique(v[:,2]);rings=[]
        for z in levels:
            ring=v[(abs(v[:,2]-z)<1e-7)&(np.linalg.norm(v[:,:2],axis=1)>1e-7)]
            rings.append(ring)
        prior_birth=[0]*(len(rings)-1)
    n=len(rings[0]);assert all(len(r)==n for r in rings),'Requires aligned section rings'
    rings=np.array(rings);r=np.linalg.norm(rings[:,:,:2],axis=2)
    # Actual broad-to-narrow transitions drive selection and direction.
    height=np.ptp(v[:,2])
    rows=[rings[0]]; ancestry=[];events=[];birth=[]
    for j in range(len(rings)-1):
        a,b=rings[j:j+2];dz=b[:,2]-a[:,2];dr=r[j+1]-r[j]
        span=np.linalg.norm(b-a,axis=1)
        active=float(np.max(abs(dr)))>.012*height and float(np.max(span))>.018*height
        fractions=[.22,.5,.78,1.] if active else [1.]
        for t in fractions:
            p=(1-t)*a+t*b
            if active and t<1:
                radius=np.linalg.norm(p[:,:2],axis=1);radial=p[:,:2]/radius[:,None]
                # Existing flute ridges, not independent decorations, become folds.
                ridge=(radius-radius.min())/max(np.ptp(radius),1e-12)
                lobe=ridge**ridge_power
                theta=np.arctan2(p[:,1],p[:,0])
                hierarchy=.8+.2*np.cos(4*theta)
                shape=1-abs(2*t-1)
                outward=strength*abs(dr)*.8*shape*lobe*hierarchy
                p[:,:2]+=radial*outward[:,None]
                # Advance ridge tips into the narrower adjoining region.
                p[:,2]+=-np.sign(dr)*strength*dz*.55*shape*lobe*hierarchy
            rows.append(p);ancestry.append(j);birth.append(generation if active else prior_birth[j])
        if active:events.append(dict(parent_band=j,parent_birth=prior_birth[j],max_radial_change=float(max(abs(dr))),operation='split current connected strips; ridge flare; axial tip advance toward neck'))
    child_count=0
    if interstitial:
        old=np.array(rows);expanded=[]
        for k,ring in enumerate(old):
            nxt=np.roll(ring,-1,axis=0);mid=(ring+nxt)/2
            edge=nxt[:,:2]-ring[:,:2];width=np.linalg.norm(edge,axis=1)
            normal=np.column_stack([edge[:,1],-edge[:,0]])/np.maximum(width[:,None],1e-12)
            lo=old[max(k-1,0)];hi=old[min(k+1,len(old)-1)]
            radial_change=np.abs(np.linalg.norm(hi[:,:2],axis=1)-np.linalg.norm(lo[:,:2],axis=1))
            travel=np.linalg.norm(hi-lo,axis=1)
            activation=np.clip(radial_change/np.maximum(travel,1e-12),0,1)
            activation=(activation+np.roll(activation,-1))/2
            amount=child_gain*width*activation*(width>.65*width.max())
            if k in [0,len(old)-1]:amount[:]=0
            mid[:,:2]+=normal*amount[:,None]
            # Original ridge vertices remain; new points lie on their connecting faces.
            row=np.empty((n*2,3));row[::2]=ring;row[1::2]=mid;expanded.append(row)
            child_count+=int(np.count_nonzero(amount>1e-8))
        rows=expanded;n*=2
    vs=np.array(rows).reshape((-1,3)).tolist();faces=[];parents=[]
    for j in range(len(rows)-1):
        for i in range(n):
            faces.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i]);parents.append(ancestry[j]*(n//2 if interstitial else n)+(i//2 if interstitial else i))
    for j in [0,len(rows)-1]:
        center=len(vs);vs.append([0,0,float(rows[j][0,2])])
        for i in range(n):faces.append([center,j*n+(i+1)%n,j*n+i] if j==0 else [center,j*n+i,j*n+(i+1)%n])
    output.mkdir(parents=True,exist_ok=True);common.OUT=output
    mesh=common.Mesh.from_vertices_and_faces(vs,faces)
    report=dict(source=str(source.resolve()),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),strength=strength,ridge_power=ridge_power,events=events,smoothing=False,subdivision='local axial strip splits only; no Catmull-Clark',scope='aligned section-ring column; not a general arbitrary-mesh operator')
    report.update(generation=generation,child_gain=child_gain,interstitial_new_fold_vertices=child_count,selected_new_parent_bands=sum(e['parent_birth']==generation-1 for e in events),scope='persistent ring topology; warped rings supported; no coordinate-height regrouping after initialization')
    common.save(mesh,generation,report)
    dest=output/f'g{generation:02d}'
    (dest/'parent_faces.json').write_text(json.dumps(parents))
    (dest/'strip_state.json').write_text(json.dumps(dict(rings=np.arange(len(rows)*n).reshape((-1,n)).tolist(),band_birth=birth,generation=generation)))
    return dest/'mesh.json'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=common.ROOT/'fluted_generation_results/g00/mesh.json');p.add_argument('--output',type=Path,default=common.ROOT/'recursive_strip_results');p.add_argument('--strength',type=float,default=.8);p.add_argument('--ridge-power',type=float,default=8.);p.add_argument('--generations',type=int,default=2);p.add_argument('--interstitial',action='store_true');p.add_argument('--child-gain',type=float,default=.55);a=p.parse_args()
    source=a.input
    start=json.loads((source.parent/'strip_state.json').read_text())['generation'] if (source.parent/'strip_state.json').exists() else 0
    for g in range(start+1,start+a.generations+1):source=evolve(source,a.output,a.strength,a.ridge_power,g,a.interstitial,a.child_gain)
