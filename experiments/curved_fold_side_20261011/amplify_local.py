"""Amplify existing later-generation folding in legacy-feature collars.

No noise or new periodic ridges: the vector is the already generated W01
G1->G3 change. Exact G1 feature cores and deep valley cores remain fixed.
The extra gain is largest beside protected creases, not over the full body.
"""
from pathlib import Path
import shutil,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
base=repair.base

def main():
    root=base.ArtifactRoot(Path(repair.ROOT));a=np.load(root.resolve('W01_SMOOTH_DEEP/G01/checkpoint.npz'))
    b=np.load(root.resolve('W01_SMOOTH_DEEP/G03/checkpoint.npz'))
    assert np.array_equal(a['faces'],b['faces']) and np.array_equal(a['chart'],b['chart'])
    w=a['memory'];collar=4*w*(1-w);extra=.85*collar[:,None]*(b['xyz']-a['xyz'])
    xyz=b['xyz']+extra;tri=b['faces'];folder=root.resolve('W02_AMPLIFIED/G01')
    folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
    m=trimesh.Trimesh(xyz,tri,process=False)
    assert np.isfinite(xyz).all() and m.area_faces.min()>1e-12 and m.is_watertight
    np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
    np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=b['chart'],memory=b['memory'],valley_protection=b['valley_protection'])
    np.savez_compressed(folder/'operation_fields.npz',feature_collar=collar,extra_displacement=extra)
    m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'amplification_recipe.py')
    base.dump(folder/'generation.json',dict(candidate='W02_AMPLIFIED',stage='G01',
        operation='Existing W01 G1->G3 folding amplified only beside protected legacy creases',
        source='W01_SMOOTH_DEEP/G03',comparison='W01_SMOOTH_DEEP/G03',maximum_additional_gain=.85,
        maximum_additional_displacement=float(np.linalg.norm(extra,axis=1).max()),
        legacy_core_max_extra_movement=float(np.linalg.norm(extra[w>=1-1e-12],axis=1).max()),
        valley_core_max_extra_movement=float(np.linalg.norm(extra[b['valley_protection']>=1-1e-12],axis=1).max()),
        physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
        separate_geometric_smoothing=False,random_noise=False,physical_fold_solver=False,
        self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
    print('GENERATED W02',len(xyz),len(tri),'extra',np.linalg.norm(extra,axis=1).max(),flush=True)
if __name__=='__main__':main()
