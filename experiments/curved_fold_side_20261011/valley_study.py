"""Two inward valley sections on the retained radical fold seed.

Preserve X-extreme fold profiles. Recess front/back material into a sharp V or
broader cup; protect the new narrow valley line against subsequent filling.
No normal shading trick, noise, global depth scaling or inextensible solver.
"""
from pathlib import Path
import argparse,shutil,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
base=repair.base;legacy=repair.legacy
from cheshire.artifact_root import ArtifactRoot

def valley(chart,kind,depth,width):
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);norm=np.linalg.norm(chart[:,1:],axis=1)
    d=np.minimum(abs(legacy.angle_distance(theta,np.pi/2)),abs(legacy.angle_distance(theta,-np.pi/2)))
    q=np.clip(d/width,0,1)
    wave=1-1.5*q+.5*q**3 if kind=='V' else (1-q*q)**2
    axial=np.zeros(len(chart));protection=np.zeros(len(chart))
    knots=np.array([-2.2,-1.4,-.75,-.35,-.15,.15,.35,.75,1.3,2.])
    values=[0,.15,.65,1,1,.95,.65,.35,.12,0]
    for event in legacy.EVENTS[1]:
        centre=event['direction']+event['sweep']*np.sin(np.pi*(s-event['height'])/.32)
        distance=np.minimum(abs(legacy.angle_distance(theta,centre)),abs(legacy.angle_distance(theta,np.pi-centre)))
        local_h=event['height']+.05*np.clip(distance/event['overlap_width'],0,1)**1.4
        u=(s-local_h)/event['span'];profile=np.interp(u,knots,values,left=0,right=0)
        axial=np.maximum(axial,profile)
    activate=np.clip((axial-.2)/.4,0,1);activate=activate*activate*(3-2*activate)
    protection=legacy.window(d,.035,.16)*activate
    offset=np.column_stack([np.cos(theta),np.sin(theta),np.zeros(len(theta))])*(-depth*wave*axial)[:,None]
    if kind=='Y_CUP':
        # Preserve the mouth's X width; recess only along front/back depth.
        offset[:,0]=0;offset[:,1]=-depth*wave*axial*np.sign(np.sin(theta))
        protection=np.maximum(protection,wave*activate)
    offset[norm<.99]=0;protection[norm<.99]=0
    return offset,protection

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=repair.ROOT);p.add_argument('--wide-only',action='store_true');args=p.parse_args();root=ArtifactRoot(Path(args.root))
    seed=np.load(root.resolve('T01_RADICAL_SEED/G01/checkpoint.npz'));birth=seed['xyz'];chart=seed['chart'];tri=seed['faces']
    recipes=[('V03_WIDE_CUP','Y_CUP',.55,.95)] if args.wide_only else [('V01_SHARP_VALLEY','V',.42,.65),('V02_CUP_VALLEY','U',.55,.80)]
    for name,kind,depth,width in recipes:
        offset,protection=valley(chart,kind,depth,width)
        for gen in (1,2,3):
            source=np.load(root.resolve('T01_RADICAL_SEED'+f'/G{gen:02}/checkpoint.npz'))
            assert np.array_equal(tri,source['faces']) and np.array_equal(chart,source['chart'])
            xyz=birth+offset+(source['xyz']-birth)*(1-protection)[:,None]
            folder=root.resolve(name+f'/G{gen:02}');folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
            m=trimesh.Trimesh(xyz,tri,process=False)
            assert np.isfinite(xyz).all() and m.area_faces.min()>1e-12 and m.is_watertight
            np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
            np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=chart,valley_protection=protection)
            np.savez_compressed(folder/'operation_fields.npz',valley_offset=offset,valley_protection=protection,attenuated_later_growth=(source['xyz']-birth)*protection[:,None])
            m.export(folder/'gate.ply')
            base.dump(folder/'generation.json',dict(candidate=name,stage=f'G{gen:02}',source='T01_RADICAL_SEED',
                operation='Inward angular valley section + narrow valley-line position memory',valley_section=kind,
                maximum_authored_inward_depth=depth,angular_half_width=width,actual_offset_maximum=float(np.linalg.norm(offset,axis=1).max()),
                carrier_radius=.78,carrier_height=10,original_outer_X_fold_events='Unchanged',
                protected_valley_vertices=int((protection>=1-1e-12).sum()),
                self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',
                physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
                separate_geometric_smoothing=False,physical_fold_solver=False))
            shutil.copy2(__file__,folder/'valley_recipe.py');print('GENERATED',name,gen,len(xyz),len(tri),flush=True)
if __name__=='__main__':main()
