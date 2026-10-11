"""User-requested side symmetry + visibly strong folds. Preserve front half.

This Y reflection is symmetry construction, not the R-family fold mechanism.
S00 copies original A front half, S01 P06 front half. S02 scales authored fold
displacement about the unchanged material carrier, not global object dimensions.
All share source front crease locations. Original candidates stay untouched.
"""
from pathlib import Path
import argparse,copy,shutil,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
base=repair.base
from cheshire.artifact_root import ArtifactRoot

def physical_source(folder):
    g=np.load(folder/'geometry.npz');c=np.load(folder/'checkpoint.npz');ch=c['chart']
    if len(ch)!=len(g['xyz']):ch=np.vstack([ch,ch[c['faces']].mean(1)])
    assert len(ch)==len(g['xyz'])
    return g['xyz'],g['faces'],ch

def front_reflect(xyz,faces,chart):
    # Every source mesh has explicit Y=0 material boundaries already.
    ch=chart.copy();ch[abs(ch[:,2])<1e-11,2]=0
    face=faces[(ch[faces,2]>=0).all(1)]
    ids,inv=np.unique(face,return_inverse=True);f=inv.reshape(-1,3);x=xyz[ids].copy();ch=ch[ids]
    seam=ch[:,2]==0
    seam_correction=float(np.max(abs(x[seam,1])))
    assert seam_correction<1e-10,'Source geometric Y seam is not on reflection plane'
    x[seam,1]=0
    off=~seam;mirror=np.arange(len(x));mirror[off]=len(x)+np.arange(off.sum())
    result=np.vstack([x,x[off]*[1,-1,1]])
    triangles=np.vstack([f,mirror[f[:,[0,2,1]]]])
    all_chart=np.vstack([ch,ch[off]*[1,1,-1]])
    return result,triangles,all_chart,dict(original_front_half_vertices=len(x),front_half_max_movement=seam_correction,
        seam_shared_vertices=int(seam.sum()),symmetry='Copy Y>=0 half to Y<=0; shared seam, reversed reflected triangle winding; X symmetry inherited',
        loss='Original asymmetric front/back event timing replaced by mirrored front events')

def strengthen(xyz,chart,scale):
    theta=np.arctan2(chart[:,2],chart[:,1]);norm=np.linalg.norm(chart[:,1:],axis=1)
    carrier=np.column_stack([.78*chart[:,1],.78*chart[:,2],10*chart[:,0]])
    side=norm>.99;carrier[side,:2]=.78*np.column_stack([np.cos(theta[side]),np.sin(theta[side])])
    return carrier+scale*(xyz-carrier)

def radical_seed(root):
    """One preserved branch, stronger FIRST-generation input, same later events."""
    import conforming_a
    g=np.load(root.resolve('P06_CREASE_MESH/G03/checkpoint.npz'))
    ch,f=g['chart'],g['faces'];original=copy.deepcopy(repair.legacy.EVENTS)
    events=copy.deepcopy(original)
    for generation,items in events.items():
        for item in items:
            for key in ['expansion','reexpansion','constriction','return_depth']:
                multiplier=(1.65 if key in ['expansion','reexpansion'] else 1.35 if key=='constriction' else 1.50) if generation==1 else 1.25
                item[key]*=multiplier
    repair.legacy.EVENTS=events
    try:
        for generation in (1,2,3):
            xyz,_=conforming_a.evaluate(ch,generation)
            out,tri,chart,meta=front_reflect(xyz,f,ch)
            cm=chart.copy();cm[:,2]=abs(cm[:,2]);memory=np.zeros(len(cm))
            for gen in range(1,generation+1):
                for event in events[gen]:memory=np.maximum(memory,repair.line_memory(cm,event)*(1-memory))
            folder=root.resolve('T01_RADICAL_SEED'+f'/G{generation:02}');folder.mkdir(parents=True,exist_ok=True)
            assert not list(folder.iterdir())
            m=trimesh.Trimesh(out,tri,process=False)
            assert np.isfinite(out).all() and m.area_faces.min()>1e-12 and m.is_watertight
            np.savez_compressed(folder/'geometry.npz',xyz=out,faces=tri)
            np.savez_compressed(folder/'checkpoint.npz',xyz=out,faces=tri,chart=chart,memory=memory)
            m.export(folder/'gate.ply')
            base.dump(folder/'generation.json',dict(candidate='T01_RADICAL_SEED',stage=f'G{generation:02}',
                operation='Radical initial seed, subsequent directional folds, front-half mirror construction',
                source='P06 conforming material topology; S02 amplitude convention for later events',events=events,
                G1_multiplier=dict(expansion=1.65,reexpansion=1.65,constriction=1.35,return_depth=1.50),
                later_event_multiplier=1.25,material_fold_positions_and_spans='Unchanged',**meta,
                physical_vertices=len(out),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
                self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',separate_geometric_smoothing=False))
            shutil.copy2(__file__,folder/'side_symmetry_recipe.py')
            print('GENERATED T01_RADICAL_SEED',generation,len(out),len(tri),flush=True)
    finally:repair.legacy.EVENTS=original

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=repair.ROOT);p.add_argument('--radical',action='store_true');args=p.parse_args();root=ArtifactRoot(Path(args.root))
    if args.radical:radical_seed(root);return
    recipes=[('S00_A_FRONT_MIRROR',repair.SOURCE,1.),('S01_P06_FRONT_MIRROR',root.resolve('P06_CREASE_MESH/G03'),1.),
             ('S02_STRONG_FRONT_MIRROR',root.resolve('P06_CREASE_MESH/G03'),1.25)]
    for name,source,scale in recipes:
        xyz,f,ch=physical_source(source)
        if scale!=1:xyz=strengthen(xyz,ch,scale)
        out,tri,chart,meta=front_reflect(xyz,f,ch)
        folder=root.resolve(name+'/G01');folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
        m=trimesh.Trimesh(out,tri,process=False)
        assert np.isfinite(out).all() and m.area_faces.min()>1e-12 and m.is_watertight
        np.savez_compressed(folder/'geometry.npz',xyz=out,faces=tri)
        np.savez_compressed(folder/'checkpoint.npz',xyz=out,faces=tri,chart=chart)
        m.export(folder/'gate.ply')
        base.dump(folder/'generation.json',dict(candidate=name,stage='G01',source=str(source),operation='Front-half Y reflection construction',
            fold_displacement_multiplier=scale,macro_carrier_radius=.78,macro_carrier_height=10.,
            scale_scope='Authored radial/axial fold offsets relative to unchanged carrier; not global size scaling',
            **meta,physical_vertices=len(out),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
            self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',separate_geometric_smoothing=False))
        shutil.copy2(__file__,folder/'side_symmetry_recipe.py');print('GENERATED',name,len(out),len(tri),flush=True)
if __name__=='__main__':main()
