"""Conforming material-domain cuts for the SAME P02 continuous fold recipe.

Uses actual authored axial profile break curves, root-solving intersections
on shared edges. Clipped quads get centre fans (no asymmetric diagonals).
Then evaluate the unchanged continuous event/memory formula. No smoothing.
"""
from pathlib import Path
import argparse,sys,shutil
import numpy as np
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
base=repair.base;column=repair.column;variation=repair.variation;legacy=repair.legacy
from cheshire.artifact_root import ArtifactRoot

def cut(chart,faces,field):
    signed=field(chart);eps=1e-11
    edges=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),1),axis=0)
    da,db=signed[edges[:,0]],signed[edges[:,1]]
    cross=edges[((da>eps)&(db<-eps))|((da<-eps)&(db>eps))]
    a,b=chart[cross[:,0]],chart[cross[:,1]]
    lo=np.zeros(len(cross));hi=np.ones(len(cross));sa=field(a)
    for _ in range(38):
        mid=(lo+hi)/2;sm=field((1-mid[:,None])*a+mid[:,None]*b)
        same=sa*sm>0;lo=np.where(same,mid,lo);hi=np.where(same,hi,mid)
    t=(lo+hi)/2;points=(1-t[:,None])*a+t[:,None]*b
    lookup={tuple(e):len(chart)+i for i,e in enumerate(cross)}
    expanded=np.vstack([chart,points]);centres=[];out=[]
    values=signed[faces];hit=(values.min(1)<-eps)&(values.max(1)>eps)
    unchanged=faces[~hit]
    for tri in faces[hit]:
        for sign in (1,-1):
            poly=[]
            for k in range(3):
                aa,bb=int(tri[k]),int(tri[(k+1)%3]);va,vb=sign*signed[aa],sign*signed[bb]
                if va>=-eps:poly.append(aa)
                if (va>eps and vb<-eps) or (va<-eps and vb>eps):poly.append(lookup[tuple(sorted([aa,bb]))])
            poly=list(dict.fromkeys(poly))
            if len(poly)==3:out.append(poly)
            elif len(poly)==4:
                idx=len(expanded)+len(centres);centres.append(expanded[poly].mean(0))
                out.extend([[poly[k],poly[(k+1)%4],idx] for k in range(4)])
            else:raise AssertionError(('Unexpected clipped polygon',poly))
    if centres:expanded=np.vstack([expanded,centres])
    return expanded,np.vstack([unchanged,np.array(out,dtype=np.int64)])

def crease_field(event,centre_id,knot):
    def field(chart):
        s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);h=event['height'];w=event['overlap_width']
        centre=event['direction']+event['sweep']*np.sin(np.pi*(s-h)/.32)
        if centre_id:centre=np.pi-centre
        d=legacy.angle_distance(theta,centre)
        return s-h-.05*np.clip(abs(d)/w,0,1)**1.4-event['span']*knot
    return field

def evaluate(chart,last):
    theta=np.arctan2(chart[:,2],chart[:,1]);norm=np.linalg.norm(chart[:,1:],axis=1)
    # Source material chart includes cap interior. Match its radius, not a new cylinder cap.
    xyz=np.column_stack([.78*chart[:,1],.78*chart[:,2],10*chart[:,0]])
    # Side ring and inserted points lie on the conceptual circular input, not chords.
    side=norm>.99;xyz[side,:2]=.78*np.column_stack([np.cos(theta[side]),np.sin(theta[side])])
    memory=np.zeros(len(chart))
    for gen in range(1,last+1):
        move=np.sum([repair.event(chart,e,connected=True) for e in legacy.EVENTS[gen]],axis=0)
        xyz+=move*(1-memory)[:,None]
        for e in legacy.EVENTS[gen]:memory=np.maximum(memory,repair.line_memory(chart,e)*(1-memory))
    target=chart* [1,-1,1];dist,pairs=cKDTree(chart).query(target)
    assert dist.max()<1e-8 and np.array_equal(pairs[pairs],np.arange(len(chart))),float(dist.max())
    left=chart[:,1]<-1e-12;xyz[left]=xyz[pairs[left]]*[-1,1,1];xyz[abs(chart[:,1])<=1e-12,0]=0
    return xyz,memory

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=repair.ROOT);args=p.parse_args()
    root=ArtifactRoot(Path(args.root));m,ch=variation.carrier(dict(rings=49,sectors=128,radius=.78))
    f=m.faces;chart=np.vstack([ch,ch[f].mean(1)])
    ids=np.arange(len(f))+len(ch)
    faces=np.stack([f,np.roll(f,-1,1),np.broadcast_to(ids[:,None],f.shape)],-1).reshape(-1,3)
    # Sequential clipping on two halves can choose different tessellations at
    # curve crossings. Construct only X>=0, then mirror topology and positions.
    # This preserves folds; there is no after-the-fact vertex averaging.
    chart[abs(chart[:,1])<1e-12,1]=0
    faces=faces[(chart[faces,1]>=0).all(1)]
    used,inv=np.unique(faces,return_inverse=True);chart=chart[used];faces=inv.reshape(-1,3)
    operations=[];knots=[-2.2,-1.4,-.75,-.35,-.15,.15,.35,.75,1.3,2.]
    for gen in (1,2,3):
        for e in legacy.EVENTS[gen]:
            for mirror in range(2 if e['mirror'] else 1):
                for k in knots:
                    chart,faces=cut(chart,faces,crease_field(e,mirror,k))
                    operations.append(dict(event=e['id'],mirror=mirror,knot=k,vertices=len(chart),triangles=len(faces)))
        print('CUTS',gen,len(chart),len(faces),flush=True)
    chart[abs(chart[:,1])<1e-12,1]=0
    off=chart[:,1]>0;other=np.arange(len(chart))
    other[off]=len(chart)+np.arange(off.sum())
    faces=np.vstack([faces,other[faces[:,[0,2,1]]]])
    chart=np.vstack([chart,chart[off]*[1,-1,1]])
    # Same topology at all stages so this records growth, not changing sampling.
    import importlib.util
    spec=importlib.util.spec_from_file_location('panel_study',HERE/'study.py');study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)
    for gen in (1,2,3):
        xyz,memory=evaluate(chart,gen)
        name='P06_CREASE_MESH';folder=root.resolve(name+f'/G{gen:02}');folder.mkdir(parents=True,exist_ok=True)
        assert not list(folder.iterdir()),'Never overwrite'
        area=np.linalg.norm(np.cross(xyz[faces[:,1]]-xyz[faces[:,0]],xyz[faces[:,2]]-xyz[faces[:,0]]),axis=1)/2
        # Keep the existing study's area threshold. Report small crease-crossing slivers.
        assert np.isfinite(xyz).all() and area.min()>1e-12
        np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=faces)
        np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=faces,chart=chart,memory=memory)
        import trimesh
        trimesh.Trimesh(xyz,faces,process=False).export(folder/'gate.ply')
        base.dump(folder/'generation.json',dict(candidate=name,stage=f'G{gen:02}',physical_vertices=len(xyz),physical_triangles=len(faces),
            operation='Material crease-conforming cuts, identical P02 continuous event and memory formula',
            generation=gen,initial_sampling=dict(rings=49,sectors=128),minimum_triangle_area=float(area.min()),
            separate_geometric_smoothing=False,CC_coordinate_averaging=False,developability='NOT_ENFORCED',
            comparison='Same conceptual continuous side surface as P02; cap parameterization differs. Much lower initial grid plus conforming cuts.',
            symmetry_construction='Only canonical X>=0 half cut, then reflect vertices and reverse reflected triangle winding; seam vertices shared',
            self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
        shutil.copy2(__file__,folder/'conforming_recipe.py');shutil.copy2(HERE/'a_repair.py',folder/'a_repair_recipe.py')
        print('GENERATED',name,gen,len(xyz),len(faces),'minarea',area.min(),flush=True)
    base.dump(root.resolve('P06_CREASE_MESH/cut_log.json'),operations)
if __name__=='__main__':main()
