"""Two bounded IAAC-public-flow-inspired passes on retained folded inputs.

Reuse the existing finite Mandelbulb classifier and cached outside-point grid.
One surface-exact triangle midpoint subdivision, then nearest-outside movement.
G2 repeats field growth at fixed resolution; it is not a second subdivision.
Authored crease/valley tags attenuate movement. No CC or extra smoothing.
The IAAC equations and exact sequence are not published executable source.
"""
from pathlib import Path
import argparse,shutil,sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
base=repair.base;variation=repair.variation

def symmetry(chart):
    tree=cKDTree(chart);pairs=[]
    for sign in ([1,-1,1],[1,1,-1]):
        distance,ids=tree.query(chart*sign)
        assert distance.max()<1e-9 and np.array_equal(ids[ids],np.arange(len(chart)))
        pairs.append(ids)
    return pairs

def reflect(xyz,chart,pairs):
    for axis,coordinate,ids in [(0,1,pairs[0]),(1,2,pairs[1])]:
        negative=chart[:,coordinate]<-1e-12;sign=np.ones(3);sign[axis]=-1
        xyz[negative]=xyz[ids[negative]]*sign
        xyz[abs(chart[:,coordinate])<=1e-12,axis]=0

def load_source(root,name):
    path=root/name/'G01';g=np.load(path/'checkpoint.npz');chart=g['chart']
    if 'memory' in g.files:memory=g['memory']
    else:
        old=np.load(root/'T01_RADICAL_SEED/G03/checkpoint.npz')
        target=chart.copy();target[:,2]=abs(target[:,2]);dist,ids=cKDTree(old['chart']).query(target)
        assert dist.max()<1e-9;memory=old['memory'][ids]
    return g['xyz'],g['faces'],chart,np.maximum(memory,g['valley_protection'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--names',nargs='+',default=['V04_SYMMETRIC_CUP','W06_SYMMETRIC_SMOOTH'])
    args=parser.parse_args();root=Path(repair.ROOT);artifact=base.ArtifactRoot(root)
    cfg=variation.recipe('FOLD_RETENTION',fraction=.55,powers=[5,6],centres=[2.5,7.5],axial=2.8,scales=[1.6,1.6])
    _,fieldpath=variation.grid(cfg,artifact);points=np.load(Path(fieldpath)/'outside_grid.npz')['points']
    points=points[(points[:,0]>=0)&(points[:,1]>=-1e-12)].copy();points[abs(points[:,1])<1e-12,1]=0
    trees=[]
    for px,py in [(False,False),(True,False),(False,True),(True,True)]:
        choose=np.ones(len(points),bool)
        if px:choose &= points[:,0]==0
        if py:choose &= points[:,1]==0
        subset=points[choose];trees.append((px,py,cKDTree(subset),subset))
    for name in args.names:
        birth,tri,chart,protect=load_source(root,name);nv=len(birth)
        xyz,tri,attributes=trimesh.remesh.subdivide(birth,tri,vertex_attributes={'chart':chart,'protection':protect[:,None]})
        chart=attributes['chart'];protection=attributes['protection'][:,0];pairs=symmetry(chart)
        initial=xyz.copy();protected=protect>=1-1e-12
        assert np.array_equal(xyz[:nv],birth)
        for gen in (1,2):
            incoming=xyz.copy();p=incoming.copy();p[:,:2]=abs(p[:,:2])
            inside=variation.classify(p,cfg);active=inside & (np.linalg.norm(p[:,:2],axis=1)>1e-10)
            active &= (chart[:,0]>.025)&(chart[:,0]<.975)
            xp=abs(chart[:,1])<1e-12;yp=abs(chart[:,2])<1e-12;move=np.zeros_like(xyz)
            fraction,budget=(.55,.18) if gen==1 else (.35,.10)
            for px,py,tree,subset in trees:
                ids=np.flatnonzero(active&(xp==px)&(yp==py))
                if not len(ids):continue
                _,where=tree.query(p[ids]);target=subset[where];assert not variation.classify(target,cfg).any()
                move[ids]=fraction*(target-p[ids])
            length=np.linalg.norm(move,axis=1);move*=np.minimum(1,budget/np.maximum(length,1e-15))[:,None]
            move*=(1-protection)[:,None];move[:,:2]*=np.where(incoming[:,:2]<0,-1,1)
            xyz=incoming+move;reflect(xyz,chart,pairs)
            folder=root/('F_'+name)/f'G{gen:02}';folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
            m=trimesh.Trimesh(xyz,tri,process=False);assert np.isfinite(xyz).all() and m.is_watertight
            delta=np.linalg.norm(xyz[:nv]-birth,axis=1)
            np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
            np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=chart,protection=protection)
            np.savez_compressed(folder/'operation_fields.npz',finite_inside=inside,active=active,displacement=xyz-incoming)
            m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'growth_follow_recipe.py')
            base.dump(folder/'generation.json',dict(candidate='F_'+name,stage=f'G{gen:02}',input=name+'/G01',
                operation='Triangle midpoint subdivision once; protected nearest finite-outside attraction',
                field_recipe=cfg,field_cache=fieldpath,subdivision_passes_total=1,field_passes_total=gen,
                G2_resolution='Fixed G1 topology; no second subdivision',displacement_fraction=fraction,maximum_requested_step=budget,
                active_fraction=float(active.mean()),moved_vertices=int((np.linalg.norm(xyz-incoming,axis=1)>1e-12).sum()),
                maximum_actual_step=float(np.linalg.norm(xyz-incoming,axis=1).max()),
                source_legacy_core_vertices=int(protected.sum()),source_legacy_core_max_movement=float(delta[protected].max()),
                source_vertex_RMS_movement=float(np.sqrt(np.mean(delta**2))),
                initial_midpoint_surface_max_displacement=float(np.linalg.norm(xyz-initial,axis=1).max()),
                physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
                minimum_area_threshold=1e-12,minimum_area_pass=bool(m.area_faces.min()>1e-12),
                symmetry='Canonical X>=0/Y>=0 outside-grid queries and explicit mirrored coordinates; no averaging',
                separate_geometric_smoothing=False,CC_coordinate_averaging=False,
                source_status='CHESHIRE finite Mandelbulb reconstruction; not IAAC original code',
                self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
            print('GENERATED F',name,gen,len(xyz),len(tri),'active',active.mean(),'step',np.linalg.norm(xyz-incoming,axis=1).max(),flush=True)
if __name__=='__main__':main()
