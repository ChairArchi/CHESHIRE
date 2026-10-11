"""Finite side-view fold study. Two constructions, no paper mechanics solver.

C: explicit 3D crease curves joined by straight or analytically bent panels.
   Aligned and unaligned meshes sample the SAME continuous panel surface.
   Ruled does not imply developable. Old crease curves are copied, not averaged.
R: split triangles at ordered planes, then apply cumulative plane reflections.
   Every material patch is rigidly isometric; the initial shape may not be
   developable and the resulting closed surface may self intersect.
"""
from pathlib import Path
import argparse, json, shutil, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'iaac_mandelbrot_20261011'))
import study as base
import column_study as column
import variation_study as variation
from cheshire.reference_subdivision import ArrayMesh
from cheshire.artifact_root import ArtifactRoot

DEFAULT_ROOT='E:/CHESHIRE_DATA/curved_fold_side_20261011'
NT=128
G1=np.array([0,.10,.155,.205,.235,.265,.325,.365,.675,.72,.745,.775,.825,.87,.94,1.])
NEW=np.array([.40,.44,.47,.505,.54,.57,.60,.635])
RECIPES=[
 dict(name='C00_UNALIGNED',sampling='uniform'),
 dict(name='C01_ALIGNED'),
 dict(name='C02_BENT_PANEL',bend=-.075),
 dict(name='C03_SHALLOW_RETURN',depth=.65,expansion=.90),
 dict(name='C04_OBLIQUE_CREASE',warp=.055,phase=.44),
 dict(name='C05_ALTERNATE_RETURN',back_sign=-1.,front_sign=-1.),
 dict(name='C06_DEEP_RETURN',depth=1.35,expansion=1.10),
 dict(name='C07_BROAD_DIRECTION',width=1.40,phase=-.25,bend=-.045),
]

def cfg_for(item):
    cfg=dict(sampling='aligned',depth=1.,expansion=1.,warp=.025,phase=.12,
             width=1.14,bend=0.,front_sign=1.,back_sign=1.)
    cfg.update(item);return cfg

def weight(theta,centre,width):
    d=np.arctan2(np.sin(theta-centre),np.cos(theta-centre))
    return np.where(np.abs(d)<width,.5+.5*np.cos(np.pi*np.clip(d/width,-1,1)),0.)

def mirror_curves(curves):
    # theta -> pi-theta. Assign canonical half, never average crease positions.
    ids=(NT//2-np.arange(NT))%NT
    theta=np.arange(NT)*2*np.pi/NT;left=np.cos(theta)<-1e-12
    curves[:,left]=curves[:,ids[left]]*[-1,1,1]
    curves[:,np.abs(np.cos(theta))<1e-12,0]=0.
    return curves

def material(stations,cfg):
    theta=np.arange(NT)*2*np.pi/NT
    s=stations[:,None]
    return s+cfg['warp']*np.sin(np.pi*s)**2*(np.cos(2*theta)[None,:]+.45*np.sin(theta)[None,:])

def initial_curves(cfg):
    theta=np.arange(NT)*2*np.pi/NT
    phase=cfg['phase']*np.sin(2*np.pi*G1)
    angle=theta[None,:]+phase[:,None]*np.cos(theta)[None,:]
    radius=np.full((len(G1),NT),.78)
    z=10*material(G1,cfg)
    for start,e,c,re,d in [(2,.70,.28,.38,.48),(9,.49,.24,.64,.42)]:
        # Continuous panels connect non-monotonic axial crease positions.
        rp=np.array([0,.50*e,e,-c,re,0])*cfg['expansion']
        zp=np.array([0,.65*d,d,-d,-.10*d,0])*cfg['depth']
        for k in range(6):
            a=phase[start+k]
            w=np.maximum(weight(theta,a,cfg['width']),weight(theta,np.pi-a,cfg['width']))
            radius[start+k]+=rp[k]*w;z[start+k]+=zp[k]*w
    curves=np.stack([radius*np.cos(angle),radius*np.sin(angle),z],-1)
    return G1.copy(),mirror_curves(curves)

def add_central(stations,curves,cfg):
    all_s=np.sort(np.r_[stations,NEW]);result=[]
    theta=np.arange(NT)*2*np.pi/NT
    for s in all_s:
        old=np.flatnonzero(np.isclose(stations,s,atol=1e-12))
        if len(old):result.append(curves[old[0]].copy());continue
        j=np.searchsorted(stations,s)-1;v=(s-stations[j])/(stations[j+1]-stations[j])
        p=(1-v)*curves[j]+v*curves[j+1]
        if s<=.505:
            k=int(np.argmin(abs(NEW[:4]-s)))
            rp=[0,.58,-.22,.38][k]*cfg['expansion']
            zp=[0,.43,-.43,0][k]*cfg['depth']*cfg['front_sign']
            w=weight(theta,np.pi/2,1.10)
        else:
            k=int(np.argmin(abs(NEW[4:]-s)))
            rp=[0,.45,-.20,.51][k]*cfg['expansion']
            zp=[0,.36,-.36,0][k]*cfg['depth']*cfg['back_sign']
            w=weight(theta,-np.pi/2,1.04)
        # Independent return displacement; this is not radial inflation alone.
        p[:,:2]+=rp*w[:,None]*np.column_stack([np.cos(theta),np.sin(theta)])
        p[:,2]+=zp*w
        result.append(p)
    return all_s,mirror_curves(np.array(result))

def add_inner(stations,curves,cfg):
    """One selected follow-up: insert narrow crease inside panels, old lines fixed."""
    theta=np.arange(NT)*2*np.pi/NT;inserts=[.222,.457,.758]
    all_s=np.sort(np.r_[stations,inserts]);result=[]
    for s in all_s:
        old=np.flatnonzero(abs(stations-s)<1e-10)
        if len(old):result.append(curves[old[0]].copy());continue
        j=np.searchsorted(stations,s)-1;v=(s-stations[j])/(stations[j+1]-stations[j])
        p=(1-v)*curves[j]+v*curves[j+1]
        centre=np.pi/2 if s==.457 else (.27 if s<.5 else -.27)
        w=weight(theta,centre,.65)
        if s!=.457:w=np.maximum(w,weight(theta,np.pi-centre,.65))
        p[:,:2]+=.16*w[:,None]*np.column_stack([np.cos(theta),np.sin(theta)])
        p[:,2]-=.12*w
        result.append(p)
    return all_s,mirror_curves(np.array(result))

def evaluate(stations,curves,mat,cfg):
    """mat is nr by nt material s. Same continuous function for both samplers."""
    knots=material(stations,cfg);nt=mat.shape[1]
    j=np.maximum(0,np.minimum((knots[None,:,:]<=mat[:,None,:]).sum(1)-1,len(stations)-2))
    theta_ids=np.broadcast_to(np.arange(nt),mat.shape)
    lo=knots[j,theta_ids];hi=knots[j+1,theta_ids]
    v=np.clip((mat-lo)/(hi-lo),0,1)
    a=curves[j,theta_ids];b=curves[j+1,theta_ids]
    p=(1-v[:,:,None])*a+v[:,:,None]*b
    if cfg['bend']:
        radial=np.stack([np.cos(np.arange(nt)*2*np.pi/nt),np.sin(np.arange(nt)*2*np.pi/nt),np.zeros(nt)],-1)
        # Endpoint-zero analytic bend; no iterative smoothing or coordinate mean.
        length=np.linalg.norm(b-a,axis=-1)
        p+=cfg['bend']*(4*v*(1-v)*np.minimum(length,1.1))[:,:,None]*radial[None,:,:]
    return p

def quad_mesh(stations,curves,cfg,rows_per_panel=6):
    nr=(len(stations)-1)*rows_per_panel+1
    if cfg['sampling']=='uniform':mat=np.broadcast_to(np.linspace(0,1,nr)[:,None],(nr,NT))
    else:
        knots=material(stations,cfg)
        mat=np.vstack([(1-v)*knots[j]+v*knots[j+1]
                       for j in range(len(stations)-1) for v in np.arange(rows_per_panel)/rows_per_panel]+[knots[-1]])
    grid=evaluate(stations,curves,mat,cfg);ids=np.arange(nr*NT).reshape(nr,NT)
    faces=np.stack([ids[:-1],np.roll(ids[:-1],-1,1),np.roll(ids[1:],-1,1),ids[1:]],-1).reshape(-1,4)
    a,b=nr*NT,nr*NT+1
    caps=[[a,ids[0,(j+2)%NT],ids[0,j+1],ids[0,j]] for j in range(0,NT,2)]
    caps += [[b,ids[-1,j],ids[-1,j+1],ids[-1,(j+2)%NT]] for j in range(0,NT,2)]
    xyz=np.vstack([grid.reshape(-1,3),curves[0].mean(0),curves[-1].mean(0)])
    chart=np.stack(np.broadcast_arrays(mat,np.cos(np.arange(NT)*2*np.pi/NT)[None,:],np.sin(np.arange(NT)*2*np.pi/NT)[None,:]),-1).reshape(-1,3)
    chart=np.vstack([chart,[0,0,0],[1,0,0]])
    m=ArrayMesh(xyz,np.vstack([faces,caps]),np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(faces)+len(caps),3),-1,np.int64),0)
    column.reflect(m,chart);m.rest=m.xyz.copy();return m,chart

def torsal_diagnostic(curves):
    d=curves[1:]-curves[:-1]
    cprime=(np.roll(curves[:-1],-1,axis=1)-np.roll(curves[:-1],1,axis=1))/2
    dprime=(np.roll(d,-1,axis=1)-np.roll(d,1,axis=1))/2
    denominator=np.linalg.norm(cprime,axis=-1)*np.linalg.norm(d,axis=-1)*np.linalg.norm(dprime,axis=-1)
    test=np.divide(np.abs(np.einsum('ijk,ijk->ij',np.cross(cprime,d),dprime)),denominator,out=np.zeros_like(denominator),where=denominator>1e-14)
    return dict(normalized_scalar_triple_product_p50=float(np.median(test)),p95=float(np.percentile(test,95)),maximum=float(test.max()),
        meaning='Nonzero disproves developability of corresponding straight-ruled patches; bent-panel variant is not ruled.')

def save_c(root,cfg,stage,stations,curves,previous=None):
    m,ch=quad_mesh(stations,curves,cfg)
    movement=None
    if previous is not None:
        ss,cc=previous
        movement=max(float(np.max(np.linalg.norm(curves[np.argmin(abs(stations-s))]-c,axis=1))) for s,c in zip(ss,cc))
        assert movement<1e-12
    base.save(root,cfg['name'],stage,m,ch,{},dict(operation='Explicit crease boundaries and panel interpolation',parameters=cfg,
        old_crease_curve_max_movement=movement,crease_curve_positions_preserved_not_fold_angles=True,
        separate_geometric_smoothing=False,CC_coordinate_averaging=False,developability=torsal_diagnostic(curves)),mirror_callback=column.reflect)
    folder=root.resolve(cfg['name']+'/'+stage)
    np.savez_compressed(folder/'crease_curves.npz',stations=stations,curves=curves,material=material(stations,cfg))
    shutil.copy2(__file__,folder/'side_fold_recipe.py')

def split_plane(xyz,faces,normal,offset):
    """Conforming exact triangle split. Edge intersection vertices are shared."""
    signed=xyz@normal-offset;eps=1e-11
    edges=np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    edges=np.unique(edges,axis=0);cross=edges[(signed[edges[:,0]]>eps)&(signed[edges[:,1]]<-eps)|(signed[edges[:,0]]<-eps)&(signed[edges[:,1]]>eps)]
    ratio=signed[cross[:,0]]/(signed[cross[:,0]]-signed[cross[:,1]])
    new=xyz[cross[:,0]]+ratio[:,None]*(xyz[cross[:,1]]-xyz[cross[:,0]])
    lookup={tuple(e):len(xyz)+i for i,e in enumerate(cross)}
    result=[]
    for tri in faces:
        ds=signed[tri]
        if ds.min()>=-eps or ds.max()<=eps:result.append(tri.tolist());continue
        for sign in (1,-1):
            poly=[]
            for k in range(3):
                a,b=int(tri[k]),int(tri[(k+1)%3]);da,db=sign*signed[a],sign*signed[b]
                if da>=-eps:poly.append(a)
                if (da>eps and db<-eps) or (da<-eps and db>eps):poly.append(lookup[tuple(sorted([a,b]))])
            poly=list(dict.fromkeys(poly))
            for k in range(1,len(poly)-1):result.append([poly[0],poly[k],poly[k+1]])
    return np.vstack([xyz,new]),np.array(result,dtype=np.int64)

def reflection_geometry(xyz,faces,planes):
    rest=xyz.copy();f=faces.copy()
    for n,d in planes:rest,f=split_plane(rest,f,n,d)
    signed=np.array([rest@n-d for n,d in planes]).T
    # Plane ordering must cut each material generator without interleaved parts.
    assert not np.any((signed[:,:-1]<-1e-9)&(signed[:,1:]>1e-9)), 'Intersecting material cut planes'
    count=(signed>1e-10).sum(1);out=rest.copy();A=np.eye(3);b=np.zeros(3)
    for i in range(len(planes)+1):
        use=count==i;out[use]=rest[use]@A.T+b
        if i<len(planes):
            n,d=planes[i];R=np.eye(3)-2*np.outer(n,n);t=2*d*n
            b=A@t+b;A=A@R
    # All points on cut planes must agree under the two adjacent transforms.
    # Edge length preservation covers both within patches and their boundary.
    e=np.unique(np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1),axis=0)
    l0=np.linalg.norm(rest[e[:,0]]-rest[e[:,1]],axis=1);l1=np.linalg.norm(out[e[:,0]]-out[e[:,1]],axis=1)
    error=np.max(np.abs(l1-l0)/np.maximum(l0,1e-12))
    assert error<1e-8,(error,'Reflection broke patch isometry')
    return out,f,rest,dict(maximum_relative_edge_length_change=float(error),material_patches=len(planes)+1)

def save_tri(root,name,xyz,faces,rest,meta):
    folder=root.resolve(name+'/G01');folder.mkdir(parents=True,exist_ok=True)
    assert not list(folder.iterdir()),'Never overwrite checkpoint'
    area=np.linalg.norm(np.cross(xyz[faces[:,1]]-xyz[faces[:,0]],xyz[faces[:,2]]-xyz[faces[:,0]]),axis=1)/2
    assert np.isfinite(xyz).all() and area.min()>1e-12
    np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=faces)
    np.savez_compressed(folder/'checkpoint.npz',xyz=xyz,faces=faces,rest=rest)
    trimesh.Trimesh(xyz,faces,process=False).export(folder/'gate.ply')
    base.dump(folder/'generation.json',dict(candidate=name,stage='G01',operation='Conforming cuts followed by cumulative exact plane reflection',
        **meta,physical_vertices=len(xyz),physical_triangles=len(faces),bounds=[xyz.min(0).tolist(),xyz.max(0).tolist()],
        minimum_triangle_area=float(area.min()),self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',
        separate_geometric_smoothing=False,physical_surface='Stored float64 triangles; identical checking and rendering input'))
    shutil.copy2(__file__,folder/'side_fold_recipe.py');print('GENERATED',name,len(xyz),len(faces),flush=True)

def run_reflections(root):
    for name,kind,slope,gap in [('R01_ROUND','round',.85,.55),('R02_CORRUGATED','corrugated',.85,.55),
                                  ('R03_SCULPTED','sculpted',.80,.65),('R04_CONE','cone',.60,.75)]:
        if kind=='sculpted':
            path=Path('E:/CHESHIRE_DATA/iaac_mandelbrot_20261011/directional/D02_INTERLEAVED/CC2/geometry.npz')
            g=np.load(path);xyz=g['xyz'];faces=g['faces'];source=str(path)
        else:
            m,ch=variation.carrier(dict(rings=41,sectors=128,radius=.78))
            theta=np.arctan2(m.xyz[:,1],m.xyz[:,0]);cap=np.linalg.norm(m.xyz[:,:2],axis=1)<1e-9
            if kind=='corrugated':m.xyz[:,:2]*=(1+.14*np.cos(4*theta))[:,None]
            if kind=='cone':m.xyz[:,:2]*=(.80+.04*m.xyz[:,2])[:,None]
            native=base.growth.native(m);xyz=native.xyz;faces=native.faces[:,:3];source='Developable generalized cylinder side' if kind!='cone' else 'Developable cone side'
        # Paired parallel cuts return the outgoing axis to its original direction.
        planes=[]
        for h,k in [(2.45,slope),(2.45+gap,slope),(7.25,-slope),(7.25+gap,-slope)]:
            n=np.array([0.,-k,1.]);norm=np.linalg.norm(n);planes.append((n/norm,h/norm))
        out,f,rest,meta=reflection_geometry(xyz,faces,planes)
        save_tri(root,name,out,f,rest,dict(**meta,source=source,input_side_developable=kind!='sculpted',
            closed_caps_are_not_claimed_as_single_sheet_origami=True,planes=[dict(normal=n.tolist(),offset=d) for n,d in planes],
            reflection_planes_preserve_X_symmetry=True,developability_claim='Only round/corrugated cylinder and cone SIDE patches have developable input. Sculpted input is not developable.'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=DEFAULT_ROOT);p.add_argument('--follow',nargs='*');p.add_argument('--family',choices=['C','R','ALL'],default='ALL');args=p.parse_args()
    root=ArtifactRoot(Path(args.root));root.path.mkdir(parents=True,exist_ok=True)
    if args.follow:
        for name in args.follow:
            cfg=cfg_for(next(r for r in RECIPES if r['name']==name));g=np.load(root.resolve(name+'/G02/crease_curves.npz'))
            previous=(g['stations'],g['curves']);ss,cc=add_inner(*previous,cfg)
            save_c(root,cfg,'G03',ss,cc,previous)
        return
    if args.family in ('C','ALL'):
        for item in RECIPES:
            cfg=cfg_for(item);s1,c1=initial_curves(cfg);s2,c2=add_central(s1,c1,cfg)
            save_c(root,cfg,'G01',s1,c1)
            save_c(root,cfg,'G02',s2,c2,(s1,c1))
    if args.family in ('R','ALL'):run_reflections(root)
    base.dump(root.resolve('recipes.json'),dict(curve_panel_recipes=[cfg_for(r) for r in RECIPES],reflection_recipes=['R01_ROUND','R02_CORRUGATED','R03_SCULPTED','R04_CONE'],sources_in='experiments/curved_fold_side_20261011/RESEARCH.md'))

if __name__=='__main__':main()
