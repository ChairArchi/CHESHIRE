"""Source-following straight-column test after user removed the arch constraint.

IAAC: plain cylinder, two Mandelbrot volumes, midpoint subdivision, two
published coordinate-response loops. Raw and actual CC presentation separated.
Numerics/formula interpretation are reconstructed, not recovered IAAC code.
"""
from pathlib import Path
import argparse,sys,shutil
import numpy as np
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import study as base
from cheshire import task33_folds as folds,task36_growth as growth
from cheshire.reference_subdivision import ArrayMesh,topology,subdivide

HEIGHT=10.
FIELD_Z=np.array([2.5,7.5])
FIELD_POWER=np.array([5,6])
FIELD_RADIAL_SCALE=1.6
FIELD_AXIAL_SCALE=2.8

def reflect(mesh,chart):
    target=chart.copy();target[:,1]*=-1
    dist,ids=cKDTree(chart).query(target)
    assert dist.max()<1e-10 and np.array_equal(ids[ids],np.arange(len(ids)))
    left=chart[:,1]<-1e-12
    mesh.xyz[left]=mesh.xyz[ids[left]]*[-1,1,1]
    mesh.xyz[np.abs(chart[:,1])<1e-12,0]=0
    return ids

def carrier():
    # Public slides expose cylinder divisions but not executable definitions.
    # Use 10 axial spans, 16 circular samples: a finite, closed quad cylinder.
    nr,nt=11,16;angle=np.arange(nt)*2*np.pi/nt
    z=np.linspace(0,HEIGHT,nr)
    grid=np.stack(np.broadcast_arrays(.78*np.cos(angle)[None,:],.78*np.sin(angle)[None,:],z[:,None]),-1)
    ids=np.arange(nr*nt).reshape(nr,nt)
    quads=np.stack([ids[:-1],np.roll(ids[:-1],-1,1),np.roll(ids[1:],-1,1),ids[1:]],-1).reshape(-1,4)
    cap0,cap1=nr*nt,nr*nt+1
    caps=[[cap0,ids[0,(j+2)%nt],ids[0,j+1],ids[0,j]] for j in range(0,nt,2)]
    caps+=[[cap1,ids[-1,j],ids[-1,j+1],ids[-1,(j+2)%nt]] for j in range(0,nt,2)]
    xyz=np.concatenate([grid.reshape(-1,3),[[0,0,0],[0,0,HEIGHT]]])
    faces=np.concatenate([quads,np.array(caps)])
    chart=np.stack(np.broadcast_arrays(z[:,None]/HEIGHT,np.cos(angle)[None,:],np.sin(angle)[None,:]),-1).reshape(-1,3)
    chart=np.concatenate([chart,[[0,0,0],[1,0,0]]])
    m=ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(faces),3),-1,np.int64),0)
    reflect(m,chart);m.rest=m.xyz.copy();topology(m)
    return m,chart

def classify(xyz):
    # Mirrored design domain, not averaging of opposite displacements.
    sample=xyz.copy();sample[:,0]=np.abs(sample[:,0]);sample[:,2]=sample[:,2].clip(0,HEIGHT)
    in_each=[]
    for centre,power in zip(FIELD_Z,FIELD_POWER):
        domain=sample/np.array([FIELD_RADIAL_SCALE,FIELD_RADIAL_SCALE,FIELD_AXIAL_SCALE])
        domain[:,2]-=centre/FIELD_AXIAL_SCALE
        _,_,inside=base.escape_field(domain,power=int(power),iterations=18,bailout=4.)
        in_each.append(inside)
    return np.stack(in_each,axis=1).any(1)

def grid(root):
    folder=root.resolve('columns/fields');path=folder/'outside_grid.npz'
    if path.exists():points=np.load(path)['outside_points']
    else:
        # Actual complement of the UNION, not independent nearest targets that
        # might still lie inside the other fractal volume.
        axis=np.linspace(-2,2,65);zz=np.linspace(0,HEIGHT,161)
        samples=np.stack(np.meshgrid(axis,axis,zz,indexing='ij'),-1).reshape(-1,3)
        points=samples[(samples[:,0]>=0)&~classify(samples)]
        folder.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(path,outside_points=points,axis=axis,z_axis=zz)
        base.dump(folder/'field.json',dict(volumes=2,powers=FIELD_POWER.tolist(),iterations=18,bailout=4.,
            radial_scale=FIELD_RADIAL_SCALE,axial_scale=FIELD_AXIAL_SCALE,centres_z=FIELD_Z.tolist(),
            grid_dimensions=[65,65,161],grid_spacing=[.0625,.0625,.0625],outside_points=len(points),
            symmetry='Canonical X >= 0 field mirrored',semantics='Finite occupancy union, not exact distance',
            n_interpretation='Per-volume spherical exponent; IAAC does not publish the formula or parameter semantics'))
    plane=points[np.abs(points[:,0])<1e-12]
    return (cKDTree(points),points),(cKDTree(plane),plane)

def advance(mesh,chart,mode,generation,trees):
    if mode=='CONTROL':
        t=topology(mesh);nv=len(mesh.xyz)
        out,op=growth.step(mesh,face_gain=.35,edge_gain=.10,feedback=.85,inherited_bias=.35,
            vertex_memory=1,mode='interpolating',surface='mean')
        ch=base.interpolate_chart(chart,t,len(mesh.faces));reflect(out,ch)
        assert np.array_equal(out.xyz[:nv],mesh.xyz)
        return out,ch,dict(support_radius=op['support_radius'],face_bend=op['face_bend']),dict(
            operation='Unmodified CHESHIRE Task36 normal/support/bend growth',old_vertex_max_movement=0.,
            separate_geometric_smoothing=False,CC_coordinate_averaging=False)
    out,state,_,_=folds.refine(mesh,dict(carrier=mesh.rest,chart=chart),
        carrier_smoothing=False,smooth_geometry=False)
    ch=state['chart'];incoming=out.xyz.copy();sample=incoming.copy();sample[:,0]=np.abs(sample[:,0])
    old_z=sample[:,2].copy();sample[:,2]=sample[:,2].clip(0,HEIGHT)
    inside=classify(sample);movement=np.zeros_like(sample)
    if mode=='NEAREST':
        plane=np.abs(ch[:,1])<1e-12
        for mask,(tree,points) in zip([inside&~plane,inside&plane],trees):
            ids=np.flatnonzero(mask)
            if not len(ids):continue
            _,target=tree.query(sample[ids]);target_points=points[target]
            assert not classify(target_points).any()
            movement[ids]=.85*(target_points-sample[ids])
        operation='IAAC flowchart: midpoint subdivision -> inside test -> closest outside UNION grid point -> move inside vertices -> faces'
    else:
        radial=np.column_stack([sample[:,:2],np.zeros(len(sample))])
        length=np.linalg.norm(radial,axis=1)
        radial=np.divide(radial,length[:,None],out=np.zeros_like(radial),where=length[:,None]>0)
        amplitude={1:.36,2:.20,3:.11,4:.065}[generation]
        movement=radial*(np.where(inside,1.,-1.)*amplitude)[:,None]
        operation='IAAC flowchart: midpoint subdivision -> inside away from cylinder axis, outside toward axis -> faces'
    # Restore the full mesh from one calculated half; centre-plane points use
    # their own plane-restricted nearest search. Feet/crown are not gate locks.
    movement[:,0]*=np.where(incoming[:,0]<0,-1.,1.)
    out.xyz=incoming+movement
    out.xyz[:,2]=out.xyz[:,2].clip(0,HEIGHT)
    reflect(out,ch)
    meta=dict(operation=operation,reference='Published IAAC flowchart reconstruction',
        parent='columns/COMMON/G00' if generation==1 else f'columns/{mode}/G{generation-1:02}',
        volumes=2,powers=FIELD_POWER.tolist(),finite_iterations=18,
        nearest_approach_fraction=.85 if mode=='NEAREST' else None,
        radial_step=None if mode=='NEAREST' else amplitude,
        inside_fraction=float(inside.mean()),z_adjustments=int((old_z!=sample[:,2]).sum()),
        old_vertex_max_movement=float(np.linalg.norm(out.xyz[:len(mesh.xyz)]-mesh.xyz,axis=1).max()),
        separate_geometric_smoothing=False,CC_coordinate_averaging=False,
        claim='Public-order reconstruction with explicit substitute constants, not recovered IAAC source')
    record=dict(incoming_finite_inside=inside,requested_displacement=movement,actual_displacement=out.xyz-incoming)
    return out,ch,record,meta

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',default=base.DEFAULT_ROOT)
    p.add_argument('--mode',choices=['ALL','CONTROL','NEAREST','SIGN'],default='ALL')
    p.add_argument('--resume',type=int,default=0);p.add_argument('--last',type=int,default=1)
    p.add_argument('--cc-view',action='store_true');args=p.parse_args()
    root=base.ArtifactRoot(Path(args.output_root))
    if not root.resolve('columns/COMMON/G00/checkpoint.npz').exists():
        mesh,ch=carrier();base.save(root,'columns/COMMON','G00',mesh,ch,{},dict(
            operation='Plain closed cylinder; no gate arch or ornament profile',height=HEIGHT,radius=.78,
            axial_spans=10,circular_samples=16),mirror_callback=reflect)
    trees=grid(root) if args.mode in ('ALL','NEAREST') else None
    for mode in (['CONTROL','NEAREST','SIGN'] if args.mode=='ALL' else [args.mode]):
        source='columns/COMMON/G00' if not args.resume else f'columns/{mode}/G{args.resume:02}'
        mesh,ch=base.load(root.resolve(source))
        for generation in range(args.resume+1,args.last+1):
            mesh,ch,record,meta=advance(mesh,ch,mode,generation,trees)
            folder=f'columns/{mode}/G{generation:02}'
            base.save(root,'columns/'+mode,f'G{generation:02}',mesh,ch,record,meta,mirror_callback=reflect)
            shutil.copy2(__file__,root.resolve(folder+'/column_recipe.py'))
        if args.cc_view:
            # IAAC explicitly publishes a separate Catmull-Clark-smoothed row.
            # One actual neutral CC subdivision is preserved as a separate mesh;
            # it is NOT another claimed fractal-growth generation.
            t=topology(mesh);newchart=base.interpolate_chart(ch,t,len(mesh.faces))
            cc,_,_=subdivide(mesh,{})
            base.save(root,'columns/'+mode,f'G{args.last:02}_CC_VIEW',cc,newchart,{},dict(
                operation='One actual neutral Catmull-Clark subdivision for the separate IAAC-style smoothed comparison row',
                parent=f'columns/{mode}/G{args.last:02}',fractal_growth_generation=False,
                CC_coordinate_averaging=True,separate_geometric_smoothing=False,
                old_vertex_max_movement=float(np.linalg.norm(cc.xyz[:len(mesh.xyz)]-mesh.xyz,axis=1).max())),mirror_callback=reflect)
            shutil.copy2(__file__,root.resolve(f'columns/{mode}/G{args.last:02}_CC_VIEW/column_recipe.py'))

if __name__=='__main__':main()
