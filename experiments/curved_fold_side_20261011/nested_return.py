"""One final composition: existing return sections beside retained fold fans.

No new operator: reuse smooth_deep's existing expansion/constriction/return
profile. Canonical quarter generates both reflections without averaging.
Legacy macro lines, deep valley cores and preceding fan cores attenuate this
new movement. This is a finite design refinement, not stationary growth.
"""
from pathlib import Path
import shutil,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair,smooth_deep
base=repair.base
EVENTS=[
 dict(id='LOW_NESTED_RETURN',direction=0.,height=.285,span=.040,expansion=.24,constriction=.10,reexpansion=.17,return_depth=.16,overlap_width=.78,sweep=-.13,mirror=True),
 dict(id='MID_INNER_RETURN',direction=np.pi/2,height=.485,span=.035,expansion=.19,constriction=.08,reexpansion=.16,return_depth=.15,overlap_width=.70,sweep=0.,mirror=False),
 dict(id='UPPER_NESTED_RETURN',direction=0.,height=.770,span=.032,expansion=.20,constriction=.09,reexpansion=.19,return_depth=.15,overlap_width=.72,sweep=.10,mirror=True),
]

def main():
    root=Path(repair.ROOT);g=np.load(root/'GEO01_FAN_MEMORY/G03/checkpoint.npz');ch=g['chart'];x=g['xyz'];tri=g['faces']
    source=np.load(root/'W06_SYMMETRIC_SMOOTH/G01/checkpoint.npz')
    # Transfer existing source feature tags through the exact midpoint adapter.
    _,_,tags=trimesh.remesh.subdivide(source['xyz'],source['faces'],vertex_attributes={
        'memory':source['memory'][:,None],'valley':source['valley_protection'][:,None]})
    protection=np.maximum(g['memory'],np.maximum(tags['memory'][:,0],tags['valley'][:,0]))
    canonical=ch.copy();canonical[:,1:]=abs(canonical[:,1:])
    move=sum(smooth_deep.smooth_event(canonical,e) for e in EVENTS)*(1-protection)[:,None]
    move[:,:2]*=np.where(ch[:,1:]<0,-1,1)
    xyz=x+move;folder=root/'GEO03_NESTED_RETURN/G01';folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
    m=trimesh.Trimesh(xyz,tri,process=False);assert np.isfinite(xyz).all() and m.is_watertight
    np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
    np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=ch,memory=protection)
    np.savez_compressed(folder/'operation_fields.npz',actual_displacement=move,protection=protection)
    m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'nested_return_recipe.py')
    core=protection>=1-1e-12
    base.dump(folder/'generation.json',dict(candidate='GEO03_NESTED_RETURN',stage='G01',source='GEO01_FAN_MEMORY/G03',
        operation='Existing rounded return-section events beside protected macro creases and fold fans',events=EVENTS,
        protected_core_vertices=int(core.sum()),protected_core_max_movement=float(np.linalg.norm(move[core],axis=1).max()),
        actual_displacement_maximum=float(np.linalg.norm(move,axis=1).max()),
        physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
        minimum_area_threshold=1e-12,minimum_area_pass=bool(m.area_faces.min()>1e-12),
        separate_geometric_smoothing=False,CC_coordinate_averaging=False,physical_fold_solver=False,
        self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
    print('GENERATED GEO03',np.linalg.norm(move,axis=1).max(),flush=True)
if __name__=='__main__':main()
