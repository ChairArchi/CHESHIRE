"""A-specific follow-up after user steering: retain strong fold positions/depth.

P00-P03 isolate authored memory bands and angular panel transitions in a
continuous reconstruction of the original event sequence. NOT bitwise A replay.
P04/P05 instead use the actual saved A control mesh; selected full meridians
remain exactly fixed. Intervening polar panels are rebuilt by linear r/z
interpolation. No point averaging, smoothing, origami or developability claim.
"""
from pathlib import Path
import argparse,importlib.util,shutil,sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'iaac_mandelbrot_20261011'))
import study as base
import column_study as column
import variation_study as variation
from cheshire.artifact_root import ArtifactRoot

spec=importlib.util.spec_from_file_location('legacy_memory',HERE.parent/'directional_fold_memory_20261011/study.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
ROOT='E:/CHESHIRE_DATA/curved_fold_side_20261011'
SOURCE=Path('E:/CHESHIRE_DATA/directional_fold_memory_20261011/A_FOLD/G03')

def event(chart,event,connected=False,broad=False):
    if not connected:return legacy.folded_event_values(chart,event)[0]
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);h=event['height'];span=event['span']
    centre=event['direction']+event['sweep']*np.sin(np.pi*(s-h)/.32)
    centres=[centre,np.pi-centre] if event['mirror'] else [centre]
    width=event['overlap_width']*(1.22 if broad else 1.)
    e,c,r=event['expansion'],event['constriction'],event['reexpansion']
    knots=np.array([-2.2,-1.4,-.75,-.35,-.15,.15,.35,.75,1.3,2.])
    rp=[0,.1*e,.62*e,e,.3*e,-c,-.35*c,r,.4*r,0]
    zp=event['return_depth']*np.array([0,0,.2,1,.6,-.6,-1,-.2,0,0])
    result=np.zeros((len(chart),3))
    for a in centres:
        d=legacy.angle_distance(theta,a);q=np.clip(abs(d)/width,0,1)
        # C1 at outer boundary, nonzero one-sided centre slope retains ridge.
        wave=1-1.5*q+.5*q**3
        local_h=h+.05*np.clip(abs(d)/event['overlap_width'],0,1)**1.4
        u=(s-local_h)/span
        radial=np.interp(u,knots,rp,left=0,right=0)*wave
        result[:,:2]+=radial[:,None]*np.column_stack([np.cos(theta),np.sin(theta)])
        result[:,2]+=np.interp(u,knots,zp,left=0,right=0)*wave
    result*=legacy.window(s-.5,.40,.49)[:,None]
    result[np.linalg.norm(chart[:,1:],axis=1)<1e-10]=0
    return result

def line_memory(chart,event):
    s=chart[:,0];theta=np.arctan2(chart[:,2],chart[:,1]);h=event['height'];span=event['span'];width=event['overlap_width']
    a=event['direction']+event['sweep']*np.sin(np.pi*(s-h)/.32)
    centres=[a,np.pi-a] if event['mirror'] else [a];mask=np.zeros(len(s))
    for centre in centres:
        d=legacy.angle_distance(theta,centre);local_h=h+.05*np.clip(abs(d)/width,0,1)**1.4
        u=(s-local_h)/span
        # Preserve narrow ridge meridian plus two authored axial return edges.
        ridge=legacy.window(d,.015,.10)*legacy.window(u,1.25,1.95)
        lips=np.maximum(legacy.window(u+.35,.025,.11),legacy.window(u-.35,.025,.11))
        lips*=legacy.window(d,width*.45,width*.85)
        mask=np.maximum(mask,np.maximum(ridge,lips))
    mask[np.linalg.norm(chart[:,1:],axis=1)<1e-10]=0
    return mask

def analytic(root,name,policy,connected=False,broad=False):
    m,ch=variation.carrier(dict(rings=193,sectors=256,radius=.78))
    memory=np.zeros(len(ch));landmarks=[];metrics=[]
    for gen in (1,2,3):
        previous=m.xyz.copy();proposed=np.sum([event(ch,e,connected,broad) for e in legacy.EVENTS[gen]],axis=0)
        m.xyz+=proposed*(1-memory)[:,None];column.reflect(m,ch)
        maxmove=max([float(np.max(np.linalg.norm(m.xyz[ids]-positions,axis=1))) for ids,positions in landmarks],default=0.)
        metrics.append(dict(generation=gen,existing_line_landmark_max_movement=maxmove))
        for e in legacy.EVENTS[gen]:
            tag=(legacy.folded_event_values(ch,e)[1] if policy=='broad_legacy' else line_memory(ch,e))*(1-memory)
            ids=np.flatnonzero(tag>=1-1e-12)
            if len(ids):landmarks.append((ids,m.xyz[ids].copy()))
            memory=np.maximum(memory,tag)
        base.save(root,name,f'G{gen:02}',m,ch,dict(memory=memory),dict(
            operation='Original A event locations/amplitudes, rebuilt angular transitions and selected line memory',
            policy=policy,connected_angular_panel=connected,broader_direction_overlap=broad,
            original_event_parameters=legacy.EVENTS,legacy_landmark_movement=metrics,
            separate_geometric_smoothing=False,CC_coordinate_averaging=False,
            comparison_scope='Continuous re-evaluation of authored recipe; differs from historical bilinear tag interpolation and cap tessellation. Not a bitwise reconstruction.'),mirror_callback=column.reflect)
        folder=root.resolve(name+f'/G{gen:02}')
        shutil.copy2(__file__,folder/'a_repair_recipe.py')

def guide_repair(root,name,count):
    m,ch=base.load(SOURCE);old=m.xyz.copy()
    use=np.linalg.norm(ch[:,1:],axis=1)>.995-1e-9
    ids=np.flatnonzero(use);s=np.round(ch[ids,0],12);theta=np.mod(np.arctan2(ch[ids,2],ch[ids,1]),2*np.pi)
    order=np.lexsort((theta,s));grid=ids[order].reshape(193,256)
    a=np.mod(np.arctan2(ch[grid[0],2],ch[grid[0],1]),2*np.pi)
    guides=np.arange(0,256,256//count)
    assert len(guides)==count
    for j in range(count):
        start,end=int(guides[j]),int(guides[(j+1)%count]);stop=end if end>start else end+256
        index=np.arange(start,stop+1);angles=np.r_[a,a+2*np.pi][index]
        t=(angles-angles[0])/(angles[-1]-angles[0])
        va,vb=old[grid[:,start]],old[grid[:,end]]
        ra,rb=np.linalg.norm(va[:,:2],axis=1),np.linalg.norm(vb[:,:2],axis=1)
        radius=(1-t)*ra[:,None]+t*rb[:,None]
        z=(1-t)*va[:,2,None]+t*vb[:,2,None]
        rebuilt=np.stack([radius*np.cos(angles),radius*np.sin(angles),z],-1)
        # Endpoints assigned exactly below, not approximated by polar conversion.
        m.xyz[grid[:,index%256]]=rebuilt
    m.xyz[grid[:,guides]]=old[grid[:,guides]]
    # Cap interiors stay original; circular rim endpoints are unchanged.
    column.reflect(m,ch)
    guide_error=float(np.max(np.linalg.norm(m.xyz[grid[:,guides]]-old[grid[:,guides]],axis=-1)))
    assert guide_error<1e-12
    movement=np.linalg.norm(m.xyz-old,axis=1)
    base.save(root,name,'G01',m,ch,dict(guide_vertex_ids=grid[:,guides],actual_displacement=m.xyz-old),dict(
        operation='Preserve actual A meridian curves; rebuild intervening polar r/z panels',source=str(SOURCE),
        guide_curves=count,guide_vertices=int(grid[:,guides].size),guide_vertex_max_movement=guide_error,
        maximum_vertex_movement=float(movement.max()),rms_vertex_movement=float(np.sqrt((movement**2).mean())),
        preserved='All 193 axial samples on each guide; front/back ridges and X-extreme folded profiles included',
        changed='Intervening angular surface, including old wide-mask boundary artifacts',
        developability='NOT_ENFORCED; polar interpolation is not a developable or inextensible fold solver',
        separate_geometric_smoothing=False,CC_coordinate_averaging=False),mirror_callback=column.reflect)
    shutil.copy2(__file__,root.resolve(name+'/G01/a_repair_recipe.py'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=ROOT);p.add_argument('--mode',choices=['ALL','analytic','guides'],default='ALL');args=p.parse_args()
    root=ArtifactRoot(Path(args.root));root.path.mkdir(parents=True,exist_ok=True)
    if args.mode in ('ALL','analytic'):
        analytic(root,'P00_BROAD_MEMORY','broad_legacy')
        analytic(root,'P01_LINE_MEMORY','narrow_lines')
        analytic(root,'P02_CONNECTED_PANELS','narrow_lines',True)
        analytic(root,'P03_OVERLAP','narrow_lines',True,True)
    if args.mode in ('ALL','guides'):
        guide_repair(root,'P04_EIGHT_GUIDES',8)
        guide_repair(root,'P05_SIXTEEN_GUIDES',16)
if __name__=='__main__':main()
