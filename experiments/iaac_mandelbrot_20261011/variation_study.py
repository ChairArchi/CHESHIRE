"""Expanded, finite IAAC reconstruction catalogue. Existing operators untouched.

Not a general growth engine: explicit column recipes compare unresolved public
parameters and two clearly labelled supplemental coordinate interpretations.
"""
from pathlib import Path
import argparse, json, shutil, sys, time
import numpy as np
from scipy.spatial import cKDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import study as base
import column_study as column
from cheshire import task33_folds as folds
from cheshire.reference_subdivision import ArrayMesh, topology, subdivide

def recipe(name, **overrides):
    cfg=dict(name=name, powers=[5,6], centres=[2.5,7.5], axial=2.8,
        scales=[1.6,1.6], orientation='Z', roll=0., offset_y=0., radius=.78,
        rings=11, sectors=16, fraction=.85, eligibility='all', refinement='bilinear',
        response='nearest', local_step=None, convention='polar', iterations=18,
        family='public-flow reconstruction')
    cfg.update(overrides);return cfg

RECIPES=[
    recipe('V01_P4',powers=[4,4]),
    recipe('V02_P6',powers=[6,6]),
    recipe('V03_P8',powers=[8,8]),
    recipe('V04_P2',powers=[2,2]),
    recipe('V05_P3',powers=[3,3]),
    recipe('V06_THREE',powers=[4,6,8],centres=[5/3,5,25/3],axial=2.),
    recipe('V07_FOUR',powers=[4,6,7,8],centres=[1.25,3.75,6.25,8.75],axial=1.55),
    recipe('V08_FIVE',powers=[4,6,7,8,8],centres=[1,3,5,7,9],axial=1.25),
    recipe('V09_THIN',radius=.42),
    recipe('V10_WIDE',radius=1.12),
    recipe('V11_OVERLAP',axial=3.6),
    recipe('V12_LATITUDE',orientation='Y'),
    recipe('V13_OFFSET',offset_y=.30,scales=[1.9,1.4]),
    recipe('V14_RESOLUTION',rings=21,sectors=32),
    recipe('V15_GENTLE',fraction=.45),
    recipe('V16_FULL',fraction=1.),
    recipe('V17_NEW_ONLY',eligibility='new'),
    recipe('V18_FACE_ONLY',eligibility='face'),
    recipe('V19_CC_LOOP',refinement='CC'),
    recipe('V20_LOCAL_STEP',local_step=.45,family='supplement: local edge travel limit'),
    recipe('V21_RADIAL',response='radial',family='supplement: first outside point along radial ray'),
    recipe('V22_THIN_RADIAL',response='radial',radius=.42,
        family='supplement: first outside point along radial ray'),
    recipe('V23_FIVE_RADIAL',response='radial',powers=[4,6,7,8,8],
        centres=[1,3,5,7,9],axial=1.25,radius=.42,
        family='supplement: first outside point along radial ray'),
    recipe('V24_TURN',orientation='Y',roll=1.15,axial=3.5,radius=.58,
        family='supplement: rotating fractal domain'),
    recipe('V25_LAT_P4',convention='latitude',powers=[4,4]),
    recipe('V26_LAT_P8',convention='latitude',powers=[8,8]),
    recipe('V27_LAT_P2_I4',convention='latitude',powers=[2,2],iterations=4),
    recipe('V28_LAT_P2_I8',convention='latitude',powers=[2,2],iterations=8),
    recipe('V29_POLAR_P2_I4',powers=[2,2],iterations=4),
    recipe('V30_POLAR_P8_I4',powers=[8,8],iterations=4),
    recipe('V31_FIVE_LAT',convention='latitude',powers=[4,6,7,8,8],
        centres=[1,3,5,7,9],axial=1.25,radius=.42),
    recipe('V32_DENSE_THIN',rings=21,sectors=32,radius=.42),
    recipe('V33_EIGHT_SIDES',sectors=8,radius=.42),
    recipe('V34_THIN_NEW',radius=.42,eligibility='new'),
    recipe('V35_CC_NEW',refinement='CC',eligibility='new'),
    recipe('V36_FIVE_OVERLAP',powers=[4,6,7,8,8],centres=[1,3,5,7,9],
        axial=1.7,radius=.42),
]

def finite_inside(domain,power,iterations,convention):
    if convention=='polar':return base.escape_field(domain,power=power,iterations=iterations,bailout=4.)[2]
    # Alternative documented by Mandelbulber: latitude asin(z/r) instead of
    # polar acos(z/r). Reconstructed formula, no external source code copied.
    z=np.zeros_like(domain);alive=np.ones(len(z),bool)
    for _ in range(iterations):
        ids=np.flatnonzero(alive)
        if not len(ids):break
        q=z[ids];r=np.linalg.norm(q,axis=1)
        latitude=np.arcsin(np.divide(q[:,2],r,out=np.zeros_like(r),where=r>1e-14).clip(-1,1))
        phi=np.arctan2(q[:,1],q[:,0]);rp=r**power
        z[ids]=rp[:,None]*np.column_stack([np.cos(power*latitude)*np.cos(power*phi),
            np.cos(power*latitude)*np.sin(power*phi),np.sin(power*latitude)])+domain[ids]
        alive[ids[np.linalg.norm(z[ids],axis=1)>4]]=False
    return alive

def carrier(cfg):
    nr,nt=cfg['rings'],cfg['sectors'];angle=np.arange(nt)*2*np.pi/nt
    z=np.linspace(0,10,nr);radius=cfg['radius']
    xyz=np.stack(np.broadcast_arrays(radius*np.cos(angle)[None,:],
        radius*np.sin(angle)[None,:],z[:,None]),-1).reshape(-1,3)
    ids=np.arange(nr*nt).reshape(nr,nt);a,b=nr*nt,nr*nt+1
    faces=np.stack([ids[:-1],np.roll(ids[:-1],-1,1),np.roll(ids[1:],-1,1),ids[1:]],-1).reshape(-1,4)
    caps=[[a,ids[0,(j+2)%nt],ids[0,j+1],ids[0,j]] for j in range(0,nt,2)]
    caps += [[b,ids[-1,j],ids[-1,j+1],ids[-1,(j+2)%nt]] for j in range(0,nt,2)]
    xyz=np.vstack([xyz,[0,0,0],[0,0,10]])
    chart=np.stack(np.broadcast_arrays(z[:,None]/10,np.cos(angle)[None,:],
        np.sin(angle)[None,:]),-1).reshape(-1,3)
    chart=np.vstack([chart,[0,0,0],[1,0,0]])
    m=ArrayMesh(xyz,np.vstack([faces,caps]),np.full(len(xyz),-1,np.int8),
        xyz.copy(),np.full((len(faces)+len(caps),3),-1,np.int64),0)
    column.reflect(m,chart);m.rest=m.xyz.copy();return m,chart

def classify(xyz,cfg):
    p=xyz.copy();p[:,0]=np.abs(p[:,0]);inside=np.zeros(len(p),bool)
    for centre,power in zip(cfg['centres'],cfg['powers']):
        x=p[:,0]/cfg['scales'][0];y=(p[:,1]-cfg['offset_y'])/cfg['scales'][1]
        z=(p[:,2]-centre)/cfg['axial']
        if cfg['roll']:
            angle=cfg['roll']*(p[:,2]-5)/5
            y,z=y*np.cos(angle)-z*np.sin(angle),y*np.sin(angle)+z*np.cos(angle)
        domain=np.column_stack([x,y,z] if cfg['orientation']=='Z' else [x,z,y])
        inside |= finite_inside(domain,power,cfg['iterations'],cfg['convention'])
    return inside

def grid(cfg,root):
    # Cache by actual field parameters, not mesh recipe. Local experiment only.
    key={k:cfg[k] for k in ('powers','centres','axial','scales','orientation','roll','offset_y','iterations','convention')}
    cache=root.resolve('variations/fields');cache.mkdir(parents=True,exist_ok=True)
    entry=None
    for p in cache.glob('*/field.json'):
        if json.loads(p.read_text())['parameters']==key:entry=p.parent;break
    if entry is None:
        entry=cache/('F%02d'%(len(list(cache.glob('F*')))+1));entry.mkdir()
        axis=np.linspace(-2.4,2.4,81);zz=np.linspace(0,10,161)
        sample=np.stack(np.meshgrid(axis,axis,zz,indexing='ij'),-1).reshape(-1,3)
        sample=sample[sample[:,0]>=-1e-12];sample[np.abs(sample[:,0])<1e-12,0]=0
        points=sample[~classify(sample,cfg)]
        np.savez_compressed(entry/'outside_grid.npz',points=points)
        base.dump(entry/'field.json',dict(parameters=key,dimensions=[81,81,161],
            spacing=[.06,.06,.0625],points=len(points),domain=[[-2.4,-2.4,0],[2.4,2.4,10]],
            semantics='Finite-iteration union complement, X>=0 canonical half'))
    points=np.load(entry/'outside_grid.npz')['points'];plane=points[points[:,0]==0]
    return [(cKDTree(points),points),(cKDTree(plane),plane)],str(entry)

def radial_targets(p,active,cfg):
    """First finite outside sample on each outward ray, then bracket refinement.
    This is an explicit restriction of the search, NOT global nearest-point.
    No random field, distance-estimator substitute, or coordinate averaging.
    """
    ids=np.flatnonzero(active);q=p[ids];r=np.linalg.norm(q[:,:2],axis=1)
    direction=np.divide(q[:,:2],r[:,None],out=np.zeros((len(q),2)),where=r[:,None]>1e-12)
    lo=np.zeros(len(q));hi=np.zeros(len(q));pending=np.ones(len(q),bool)
    for step in np.linspace(.025,3.2,128):
        k=np.flatnonzero(pending)
        if not len(k):break
        test=q[k].copy();test[:,:2]+=direction[k]*step
        outside=~classify(test,cfg);hit=k[outside]
        hi[hit]=step;pending[hit]=False;lo[k[~outside]]=step
    assert not pending.any(),'Radial search domain insufficient'
    for _ in range(10):
        mid=(lo+hi)/2;test=q.copy();test[:,:2]+=direction*mid[:,None]
        inside=classify(test,cfg);lo[inside]=mid[inside];hi[~inside]=mid[~inside]
    target=q.copy();target[:,:2]+=direction*hi[:,None]
    assert not classify(target,cfg).any()
    return ids,target

def advance(mesh,ch,cfg,generation,trees):
    t=topology(mesh);nv=len(mesh.xyz);ne=len(t['edges'])
    if cfg['refinement']=='CC':
        out,_,_=subdivide(mesh,{});newch=base.interpolate_chart(ch,t,len(mesh.faces))
    else:
        out,state,_,_=folds.refine(mesh,dict(carrier=mesh.rest,chart=ch),
            carrier_smoothing=False,smooth_geometry=False);newch=state['chart']
    incoming=out.xyz.copy();p=incoming.copy();p[:,0]=np.abs(p[:,0]);p[:,2]=p[:,2].clip(0,10)
    inside=classify(p,cfg);active=inside.copy()
    if cfg['eligibility']=='new':active[:nv]=False
    if cfg['eligibility']=='face':active[:nv+ne]=False
    active &= (np.linalg.norm(p[:,:2],axis=1)>1e-10) # cap centres stay on axis
    plane=np.abs(newch[:,1])<1e-12;move=np.zeros_like(p)
    if cfg['response']=='radial':
        ids,target=radial_targets(p,active,cfg);move[ids]=cfg['fraction']*(target-p[ids])
    else:
        for mask,(tree,points) in zip([active&~plane,active&plane],trees):
            ids=np.flatnonzero(mask)
            if not len(ids):continue
            _,where=tree.query(p[ids]);target=points[where]
            assert not classify(target,cfg).any();move[ids]=cfg['fraction']*(target-p[ids])
    if cfg['local_step'] is not None:
        ot=topology(out);e=ot['edges'];length=np.linalg.norm(incoming[e[:,1]]-incoming[e[:,0]],axis=1)
        shortest=np.full(len(p),np.inf);np.minimum.at(shortest,e[:,0],length);np.minimum.at(shortest,e[:,1],length)
        mag=np.linalg.norm(move,axis=1);factor=np.minimum(1,cfg['local_step']*shortest/np.maximum(mag,1e-15))
        move*=factor[:,None]
    move[:,0]*=np.where(incoming[:,0]<0,-1,1);out.xyz=incoming+move
    out.xyz[:,2]=out.xyz[:,2].clip(0,10);column.reflect(out,newch)
    return out,newch,dict(finite_inside=inside,active=active,displacement=out.xyz-incoming),dict(
        recipe=cfg,parent=f'variations/{cfg["name"]}/G{generation-1:02}',
        operation='Refine, finite inside test, outside-point attraction, faces; canonical mirrored field',
        old_vertex_max_movement=float(np.linalg.norm(out.xyz[:nv]-mesh.xyz,axis=1).max()),
        active_fraction=float(active.mean()),separate_geometric_smoothing=False,
        CC_coordinate_averaging=cfg['refinement']=='CC',
        source_status=cfg['family'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-root',default=base.DEFAULT_ROOT)
    p.add_argument('--names',nargs='*');p.add_argument('--resume',type=int,default=0)
    p.add_argument('--last',type=int,default=2);args=p.parse_args()
    root=base.ArtifactRoot(Path(args.output_root));results=[]
    for cfg in RECIPES:
        if args.names and cfg['name'] not in args.names:continue
        start=time.time();name=cfg['name'];target=root.resolve('variations/'+name)
        target.mkdir(parents=True,exist_ok=True);base.dump(target/'parameters.json',cfg)
        source=target/f'G{args.resume:02}'
        if not source.exists():
            assert args.resume==0;m,ch=carrier(cfg)
            base.save(root,'variations/'+name,'G00',m,ch,{},dict(operation='Plain closed polygonal cylinder',recipe=cfg),mirror_callback=column.reflect)
        mesh,ch=base.load(source)
        trees,field_path=grid(cfg,root) if cfg['response']=='nearest' else (None,'Analytic finite classification along radial ray')
        try:
            for generation in range(args.resume+1,args.last+1):
                stage=f'G{generation:02}'
                if (target/stage/'checkpoint.npz').exists():
                    mesh,ch=base.load(target/stage);continue
                mesh,ch,record,meta=advance(mesh,ch,cfg,generation,trees)
                base.save(root,'variations/'+name,stage,mesh,ch,record,dict(meta,field_path=field_path),mirror_callback=column.reflect)
                shutil.copy2(__file__,target/stage/'variation_recipe.py')
            status='GENERATED'
        except (AssertionError,ValueError) as exc:
            status=type(exc).__name__+': '+str(exc)
            failed=target/f'FAILED_G{mesh.generation:02}';failed.mkdir(exist_ok=True)
            actual=base.growth.native(mesh)
            np.savez_compressed(failed/'geometry.npz',xyz=actual.xyz,faces=actual.faces[:,:3])
            np.savez_compressed(failed/'failed_control.npz',xyz=mesh.xyz,faces=mesh.faces,chart=ch)
            base.trimesh.Trimesh(actual.xyz,actual.faces[:,:3],process=False).export(failed/'failed_mesh.ply')
            base.dump(failed/'failure.json',dict(status=status,recipe=cfg,
                classification='FAILED_CHECKPOINT; preserved for visual diagnosis, not a valid saved generation'))
            shutil.copy2(__file__,failed/'variation_recipe.py')
            print('FAILED',name,status,flush=True)
        results.append(dict(name=name,status=status,elapsed_seconds=time.time()-start))
        base.dump(root.resolve('variations/last_run.json'),results)
    base.dump(root.resolve('variations/catalogue.json'),RECIPES)

if __name__=='__main__':main()
