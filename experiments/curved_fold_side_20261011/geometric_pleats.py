"""Three selected fold fans, added sequentially without smoothing the body.

The signed section is zero at ridge lines and recesses between them. Fan width
couples the creases to local convergence; a small axial return is paired with
the recession. This is authored fold geometry, not a mechanical origami solve.
"""
from pathlib import Path
import shutil,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
base=repair.base;legacy=repair.legacy

EVENTS=[
    dict(id='LOW_VALLEY_FAN',axis='Y',centre=.43,span=.105,width0=.42,width1=.58,cycles=10,depth=.070),
    dict(id='UPPER_SHOULDER_FAN',axis='Y',centre=.80,span=.090,width0=.30,width1=.56,cycles=8,depth=.055),
    dict(id='SIDE_BINDING_FAN',axis='X',centre=.60,span=.115,width0=.62,width1=.38,cycles=6,depth=.060),
]

def event(chart,cfg,chevron=False):
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);v=(s-cfg['centre'])/cfg['span']
    axis=1 if cfg['axis']=='Y' else 0;coordinate=chart[:,2] if axis==1 else chart[:,1]
    sign=np.where(coordinate<0,-1,1);centre=sign*np.pi/2 if axis==1 else np.where(sign<0,np.pi,0.)
    d=legacy.angle_distance(theta,centre)
    width=cfg['width0']+(cfg['width1']-cfg['width0'])*np.clip((v+1)/2,0,1)
    q=d/width;envelope=legacy.window(q,.72,1.)*legacy.window(v,.43,1.)
    envelope[np.linalg.norm(chart[:,1:],axis=1)<.99]=0
    if chevron:
        # Side chevrons open away from an unchanged deep central valley line.
        phase=np.pi*cfg['cycles']*(abs(q)+.16*v*(1-abs(q)))
        envelope*=1-legacy.window(q,.05,.18)
    else:phase=np.pi*cfg['cycles']*q
    profile=(1-np.cos(phase))/2
    move=np.zeros((len(chart),3));move[:,axis]=-sign*cfg['depth']*profile*envelope
    move[:,2]=-.30*cfg['depth']*profile*envelope*np.sin(np.pi*np.clip(v,-1,1))
    return move,envelope

def main():
    root=Path(repair.ROOT);g=np.load(root/'W03_PLEAT_CONTROL/G01/checkpoint.npz')
    source,tri,chart=g['xyz'],g['faces'],g['chart']
    for name,chevron in [('GEO01_FAN_MEMORY',False),('GEO02_CHEVRON_MEMORY',True)]:
        xyz=source.copy();memory=np.zeros(len(xyz));landmarks=[];history=[]
        for gen,cfg in enumerate(EVENTS,1):
            move,zone=event(chart,cfg,chevron);xyz+=move*(1-memory)[:,None]
            previous=max([float(np.linalg.norm(xyz[ids]-saved,axis=1).max()) for ids,saved in landmarks],default=0.)
            history.append(dict(generation=gen,prior_feature_core_max_movement=previous))
            core=np.flatnonzero(zone>=1-1e-12)
            if len(core):landmarks.append((core,xyz[core].copy()))
            memory=np.maximum(memory,zone)
            # Both reflections are generated analytically: cos is even, chevron uses |q|.
            folder=root/name/f'G{gen:02}';folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
            m=trimesh.Trimesh(xyz,tri,process=False);assert np.isfinite(xyz).all() and m.is_watertight
            np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
            np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=chart,memory=memory)
            np.savez_compressed(folder/'operation_fields.npz',zone=zone,requested_displacement=move)
            m.export(folder/'gate.ply');shutil.copy2(__file__,folder/'geometric_pleats_recipe.py')
            base.dump(folder/'generation.json',dict(candidate=name,stage=f'G{gen:02}',source='W03_PLEAT_CONTROL/G01',
                operation='Selected converging recessed fold sections + paired axial return + previous-zone memory',
                events=EVENTS[:gen],chevron=chevron,prior_feature_history=history,
                physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(m.area_faces.min()),
                minimum_area_threshold=1e-12,minimum_area_pass=bool(m.area_faces.min()>1e-12),
                separate_geometric_smoothing=False,CC_coordinate_averaging=False,random_noise=False,
                physical_fold_solver=False,self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED'))
            print('GENERATED',name,gen,'prior core',previous,flush=True)
if __name__=='__main__':main()
