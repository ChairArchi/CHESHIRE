"""Follow IAAC's TWO published flowcharts, not an invented noise substitute.

Unknown IAAC numerics are explicit experimental choices. The formula is the
public White/Nylander spherical-power map, also demonstrated by Coding Train.
No code is copied from third-party renderers. Only CHESHIRE mesh refinement is
reused. Output meshes are gates at every generation, not bent finished columns.
"""
from pathlib import Path
import argparse, sys, json
import numpy as np
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import study as base
from cheshire import task33_folds as folds
from cheshire.reference_subdivision import topology,unit

CENTRES=np.array([.075,.245,.425])
SPANS=np.array([.085,.090,.085])
POWERS=np.array([4,6,8])
RADIAL_SCALE=1.65

def outside_grid(root,power):
    path=root.resolve(f'fields/power_{power:02}_grid65.npz')
    if path.exists():
        a=np.load(path);points=a['outside_points']
    else:
        v=np.linspace(-1.3,1.3,65)
        grid=np.stack(np.meshgrid(v,v,v,indexing='ij'),-1).reshape(-1,3)
        _,_,inside=base.escape_field(grid,power=int(power),iterations=18,bailout=4.)
        points=grid[~inside]
        path.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(path,outside_points=points,axis_samples=v,power=power,iterations=18,bailout=4.)
        base.dump(path.with_suffix('.json'),dict(formula='spherical-power Mandelbulb',power=int(power),
            finite_iterations=18,bailout=4,grid_resolution=[65,65,65],range=[-1.3,1.3],
            outside_points=len(points),grid_spacing=float(v[1]-v[0]),
            classification='Finite-iteration outside set; not exact infinite-set distance'))
    return cKDTree(points),points

def measure(xyz,chart):
    s=chart[:,0];q=np.minimum(s,1-s)
    centre,a=base.frame(s);d=base.CURVE(s,1)
    speed=np.linalg.norm(d,axis=1);t=unit(d)
    canonical_t=t*np.where(s<=.5,1.,-1.)[:,None]
    off=xyz-centre;u=np.sum(off*a,axis=1);v=off[:,1]
    # Actual incoming axial movement participates in the next classification.
    projected_q=q+np.sum(off*canonical_t,axis=1)/speed
    effective_q=projected_q.clip(0,.5)
    volume=np.argmin(np.abs((effective_q[:,None]-CENTRES)/SPANS),axis=1)
    local_z=(effective_q-CENTRES[volume])/SPANS[volume]
    # Explicit equivalent of the flowchart's out-of-range Z adjustment.
    z=local_z.clip(-1,1)
    domain=np.column_stack([u/RADIAL_SCALE,v/RADIAL_SCALE,z])
    return domain,volume,dict(a=a,t=canonical_t,speed=speed,u=u,v=v,q=q,
        z_clamped=(local_z!=z),arc_clamped=(projected_q!=effective_q))

def advance(mesh,chart,mode,generation,grids):
    out,state,_,_=folds.refine(mesh,dict(carrier=mesh.rest,chart=chart),
        carrier_smoothing=False,smooth_geometry=False)
    incoming=out.xyz.copy();ch=state['chart']
    domain,volume,frame=measure(incoming,ch)
    inside=np.zeros(len(domain),bool);delta=np.zeros_like(domain)
    distances=np.zeros(len(domain))
    for i,power in enumerate(POWERS):
        ids=np.flatnonzero(volume==i)
        _,_,isin=base.escape_field(domain[ids],power=int(power),iterations=18,bailout=4.)
        inside[ids]=isin
        if mode=='IAAC_NEAREST':
            active=ids[isin]
            if not len(active):continue
            tree,points=grids[int(power)]
            dist,idx=tree.query(domain[active])
            target=points[idx]
            # Verify the named target class, not a signed-distance assumption.
            _,_,check=base.escape_field(target,power=int(power),iterations=18,bailout=4.)
            assert not check.any()
            delta[active]=target-domain[active]
            distances[active]=dist
    fade=np.clip(frame['q']/.045,0,1);fade=fade*fade*(3-2*fade)
    if mode=='IAAC_NEAREST':
        # Closest point is in a finite 3-D grid. Transport its complete vector,
        # including axial movement, to the bent gate's local frame.
        world=frame['a']*(RADIAL_SCALE*delta[:,0])[:,None]
        world[:,1]+=RADIAL_SCALE*delta[:,1]
        world+=frame['t']*(SPANS[volume]*frame['speed']*delta[:,2])[:,None]
        length=np.linalg.norm(world,axis=1)
        budget={1:.50,2:.28,3:.15,4:.085}[generation]
        # Partial approach prevents different vertices being assigned the same
        # voxel point in one step; this is a declared approximation to IAAC.
        factor=np.minimum(.72,np.divide(budget,length,out=np.full_like(length,.72),where=length>0))
        movement=world*(factor*fade)[:,None]
        description='Quad midpoint subdivision -> finite membership -> nearest outside grid point -> partial full-vector transport -> faces'
    else:
        radial=unit(frame['a']*frame['u'][:,None]+np.column_stack([np.zeros(len(domain)),frame['v'],np.zeros(len(domain))]))
        amplitude={1:.24,2:.135,3:.075,4:.045}[generation]
        movement=radial*(amplitude*np.where(inside,1.,-1.)*fade)[:,None]
        budget=amplitude
        description='Quad midpoint subdivision -> finite membership -> inside away from centre, outside toward centre -> faces'
    out.xyz=incoming+movement
    base.reflect(out,ch)
    meta=dict(operation=description,reference='IAAC published flowchart; unknown constants reconstructed',
        parent=f'{mode}/G{generation-1:02}' if generation>1 else 'COMMON/G00',
        fractal_volumes_per_half=3,powers=POWERS.tolist(),finite_iterations=18,
        radial_scale=RADIAL_SCALE,volume_centres=CENTRES.tolist(),volume_spans=SPANS.tolist(),
        movement_budget=budget,active_inside_fraction=float(inside.mean()),
        z_adjustment_count=int(frame['z_clamped'].sum()),arc_adjustment_count=int(frame['arc_clamped'].sum()),
        old_vertex_max_movement=float(np.linalg.norm(out.xyz[:len(mesh.xyz)]-mesh.xyz,axis=1).max()),
        separate_geometric_smoothing=False,CC_coordinate_averaging=False,
        gate_adaptation='Bent local frame, mirror construction, fixed feet, centre-plane boundary constraint',
        uncontrolled_claims=['Exact IAAC code','Exact IAAC n values','Infinite set membership','True closest point to infinite fractal'])
    record=dict(field_domain=domain,volume=volume,finite_inside=inside,nearest_grid_distance=distances,
        requested_displacement=movement,actual_displacement=out.xyz-incoming,
        field_z_adjustment=frame['z_clamped'],field_arc_adjustment=frame['arc_clamped'])
    return out,ch,record,meta

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',default=base.DEFAULT_ROOT)
    p.add_argument('--mode',choices=['IAAC_NEAREST','IAAC_SIGN','BOTH'],default='BOTH')
    p.add_argument('--resume',type=int,default=0);p.add_argument('--last',type=int,default=1)
    args=p.parse_args();assert 0<=args.resume<args.last<=4
    root=base.ArtifactRoot(Path(args.output_root))
    grids={}
    if args.mode in ('BOTH','IAAC_NEAREST'):
        grids={int(n):outside_grid(root,int(n)) for n in POWERS}
    for mode in (['IAAC_NEAREST','IAAC_SIGN'] if args.mode=='BOTH' else [args.mode]):
        source='COMMON/G00' if not args.resume else f'{mode}/G{args.resume:02}'
        mesh,chart=base.load(root.resolve(source))
        for generation in range(args.resume+1,args.last+1):
            mesh,chart,record,meta=advance(mesh,chart,mode,generation,grids)
            base.save(root,mode,f'G{generation:02}',mesh,chart,record,meta)
            # Preserve the actual flowchart recipe as well as shared exporter.
            import shutil
            shutil.copy2(__file__,root.resolve(f'{mode}/G{generation:02}/iaac_recipe.py'))

if __name__=='__main__':main()
