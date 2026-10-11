"""One deep-valley comparison: round authored section curves, not the mesh.

PCHIP passes through the original radial/axial profile control values and
their extrema. An analytic rounded angular cusp broadens the fold line.
No vertex smoothing, CC averaging, or inextensible origami solver is used.
"""
from pathlib import Path
import copy, shutil, sys
import numpy as np
import trimesh
from scipy.interpolate import PchipInterpolator
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a_repair as repair
import conforming_a, side_symmetry, valley_study
base=repair.base;legacy=repair.legacy

KNOTS=np.array([-2.2,-1.4,-.75,-.35,-.15,.15,.35,.75,1.3,2.])

def curve(u,values):
    return np.nan_to_num(PchipInterpolator(KNOTS,values,extrapolate=False)(u))

def smooth_event(chart,event,connected=False,broad=False):
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);h=event['height'];span=event['span']
    centre=event['direction']+event['sweep']*np.sin(np.pi*(s-h)/.32)
    centres=[centre,np.pi-centre] if event['mirror'] else [centre]
    width=event['overlap_width'];e,c,r=event['expansion'],event['constriction'],event['reexpansion']
    rp=[0,.1*e,.62*e,e,.3*e,-c,-.35*c,r,.4*r,0]
    zp=event['return_depth']*np.array([0,0,.2,1,.6,-.6,-1,-.2,0,0])
    result=np.zeros((len(chart),3))
    for a in centres:
        d=legacy.angle_distance(theta,a);q=np.clip(abs(d)/width,0,1)
        # Smooth only the centre cusp; normalize to keep full authored amplitude.
        rounded=(np.sqrt(q*q+.12**2)-.12)/(np.sqrt(1+.12**2)-.12)
        wave=1-1.5*rounded+.5*rounded**3
        local_h=h+.05*np.clip(abs(d)/width,0,1)**1.4;u=(s-local_h)/span
        radial=curve(u,rp)*wave
        result[:,:2]+=radial[:,None]*np.column_stack([np.cos(theta),np.sin(theta)])
        result[:,2]+=curve(u,zp)*wave
    result*=legacy.window(s-.5,.40,.49)[:,None]
    result[np.linalg.norm(chart[:,1:],axis=1)<1e-10]=0
    return result

def smooth_valley(chart):
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);norm=np.linalg.norm(chart[:,1:],axis=1)
    d=np.minimum(abs(legacy.angle_distance(theta,np.pi/2)),abs(legacy.angle_distance(theta,-np.pi/2)))
    q=np.clip(d/.95,0,1);wave=(1-q*q)**2;axial=np.zeros(len(chart))
    for event in legacy.EVENTS[1]:
        centre=event['direction']+event['sweep']*np.sin(np.pi*(s-event['height'])/.32)
        distance=np.minimum(abs(legacy.angle_distance(theta,centre)),abs(legacy.angle_distance(theta,np.pi-centre)))
        local_h=event['height']+.05*np.clip(distance/event['overlap_width'],0,1)**1.4
        axial=np.maximum(axial,curve((s-local_h)/event['span'],[0,.15,.65,1,1,.95,.65,.35,.12,0]))
    activate=np.clip((axial-.2)/.4,0,1);activate=activate**2*(3-2*activate)
    protection=np.maximum(legacy.window(d,.035,.16)*activate,wave*activate)
    offset=np.zeros((len(chart),3));offset[:,1]=-.55*wave*axial*np.sign(np.sin(theta))
    offset[norm<.99]=0;protection[norm<.99]=0
    return offset,protection

def main():
    root=base.ArtifactRoot(Path(repair.ROOT));data=np.load(root.resolve('P06_CREASE_MESH/G03/checkpoint.npz'))
    ch,faces=data['chart'],data['faces'];old_events=legacy.EVENTS;old_function=repair.event
    events=copy.deepcopy(old_events)
    for gen,items in events.items():
        for item in items:
            for key in ('expansion','reexpansion','constriction','return_depth'):
                item[key]*=(1.65 if key in ('expansion','reexpansion') else 1.35 if key=='constriction' else 1.50) if gen==1 else 1.25
    legacy.EVENTS=events;repair.event=smooth_event
    try:
        birth=None
        for gen in (1,2,3):
            x,memory=conforming_a.evaluate(ch,gen);xyz,tri,chart,meta=side_symmetry.front_reflect(x,faces,ch)
            if birth is None:birth=xyz.copy()
            offset,protection=smooth_valley(chart)
            xyz=birth+offset+(xyz-birth)*(1-protection)[:,None]
            folder=root.resolve(f'W01_SMOOTH_DEEP/G{gen:02}');folder.mkdir(parents=True,exist_ok=True);assert not list(folder.iterdir())
            mesh=trimesh.Trimesh(xyz,tri,process=False)
            assert np.isfinite(xyz).all() and mesh.area_faces.min()>1e-12 and mesh.is_watertight
            # Canonical chart memory survives Y reflection without ambiguous KD queries.
            cm=chart.copy();cm[:,2]=abs(cm[:,2]);memory=np.zeros(len(cm))
            for g in range(1,gen+1):
                for e in events[g]:memory=np.maximum(memory,repair.line_memory(cm,e)*(1-memory))
            np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
            np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=tri,chart=chart,memory=memory,valley_protection=protection)
            mesh.export(folder/'gate.ply')
            base.dump(folder/'generation.json',dict(candidate='W01_SMOOTH_DEEP',stage=f'G{gen:02}',
                operation='PCHIP authored fold sections + rounded angular ridge + deep C1 cup section',
                source='Same P06 material mesh, radical T01 event amplitudes, V03 inward depth and width',
                profile_knots=KNOTS.tolist(),authored_valley_depth=.55,angular_cusp_radius=.12,
                unchanged='Event positions/spans, extrema control values, LR/FB symmetry construction',
                separate_geometric_smoothing=False,CC_coordinate_averaging=False,physical_fold_solver=False,
                physical_vertices=len(xyz),physical_triangles=len(tri),minimum_triangle_area=float(mesh.area_faces.min()),
                self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',**meta))
            shutil.copy2(__file__,folder/'smooth_deep_recipe.py');print('GENERATED W01',gen,len(xyz),len(tri),flush=True)
    finally:legacy.EVENTS=old_events;repair.event=old_function
if __name__=='__main__':main()
