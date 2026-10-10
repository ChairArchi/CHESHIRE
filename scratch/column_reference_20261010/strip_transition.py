"""Stage 4 -> 5 study: connected axial flute strips unfold at actual tapers.
Input: aligned closed section rings, followed by cap centers; no smoothing.
Not an inferred historical algorithm. Each new face retains its parent band.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import fluted_generation as common

def evolve(source,output,strength=1.,ridge_power=1.5):
    data=json.loads(source.read_text());v=np.asarray(data['vertices'])
    levels=np.unique(v[:,2]);rings=[]
    for z in levels:
        ring=v[(abs(v[:,2]-z)<1e-7)&(np.linalg.norm(v[:,:2],axis=1)>1e-7)]
        rings.append(ring)
    n=len(rings[0]);assert all(len(r)==n for r in rings),'Requires aligned section rings'
    rings=np.array(rings);r=np.linalg.norm(rings[:,:,:2],axis=2)
    # Actual broad-to-narrow transitions drive selection and direction.
    envelope=r.max(axis=1);height=levels[-1]-levels[0]
    rows=[rings[0]]; ancestry=[];events=[]
    for j in range(len(rings)-1):
        a,b=rings[j:j+2];dz=levels[j+1]-levels[j];dr=envelope[j+1]-envelope[j]
        active=abs(dr)>.025*height and dz>.008*height
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
            rows.append(p);ancestry.append(j)
        if active:events.append(dict(parent_band=j,radial_change=float(dr),height=float(dz),operation='split connected strips; ridge flare; axial tip advance toward neck'))
    vs=np.array(rows).reshape((-1,3)).tolist();faces=[];parents=[]
    for j in range(len(rows)-1):
        for i in range(n):
            faces.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i]);parents.append(ancestry[j]*n+i)
    for j in [0,len(rows)-1]:
        center=len(vs);vs.append([0,0,float(rows[j][0,2])])
        for i in range(n):faces.append([center,j*n+(i+1)%n,j*n+i] if j==0 else [center,j*n+i,j*n+(i+1)%n])
    output.mkdir(parents=True,exist_ok=True);common.OUT=output
    mesh=common.Mesh.from_vertices_and_faces(vs,faces)
    report=dict(source=str(source.resolve()),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),strength=strength,ridge_power=ridge_power,events=events,smoothing=False,subdivision='local axial strip splits only; no Catmull-Clark',scope='aligned section-ring column; not a general arbitrary-mesh operator')
    common.save(mesh,1,report)
    (output/'g01/parent_faces.json').write_text(json.dumps(parents))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=common.ROOT/'fluted_generation_results/g00/mesh.json');p.add_argument('--output',type=Path,default=common.ROOT/'strip_next_results');p.add_argument('--strength',type=float,default=1.);p.add_argument('--ridge-power',type=float,default=1.5);a=p.parse_args();evolve(a.input,a.output,a.strength,a.ridge_power)
