"""Keep the liked front geometry, restore exact front/back valley symmetry.

The added valley's axial mapping used signed theta against swept G1 events;
this introduced a small Y reflection discrepancy. Preserve those trials, then
construct a new front-half mirrored mesh. No averaging of opposite folds.
"""
from pathlib import Path
import shutil,sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair,side_symmetry
base=repair.base

def main():
    root=Path(repair.ROOT)
    for source,name in [('V03_WIDE_CUP/G03','V04_SYMMETRIC_CUP'),('W01_SMOOTH_DEEP/G03','W06_SYMMETRIC_SMOOTH')]:
        g=np.load(root/source/'checkpoint.npz');xyz,tri,ch,meta=side_symmetry.front_reflect(g['xyz'],g['faces'],g['chart'])
        original_error=float(cKDTree(g['xyz']).query(g['xyz']*[1,-1,1])[0].max())
        target=ch.copy();target[:,2]=abs(target[:,2]);dist,ids=cKDTree(g['chart']).query(target);assert dist.max()<1e-10
        fields={k:g[k][ids] for k in ('memory','valley_protection') if k in g.files}
        folder=root/name/'G01';folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
        m=trimesh.Trimesh(xyz,tri,process=False);assert m.is_watertight and m.area_faces.min()>1e-12
        np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
        np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=ch,**fields)
        m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'symmetry_repair_recipe.py')
        base.dump(folder/'generation.json',dict(candidate=name,stage='G01',source=source,
            operation='Preserve source front half and reflect real vertices/faces across Y=0',
            source_front_back_nearest_vertex_error=original_error,
            physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
            failure_cause='Valley axial map used signed theta relative to a swept G1 event, unlike the preceding mirrored seed.',
            self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',**meta))
        base.dump(root/source/'valley_symmetry_issue.json',dict(front_back_nearest_vertex_error=original_error,
            status='FAIL: added valley is not exactly Y symmetric',preserved=True,repair_branch=name,
            correction='Front-half reflection construction, not point averaging.'))
        print('REPAIRED',name,'previous Y error',original_error,flush=True)
if __name__=='__main__':main()
