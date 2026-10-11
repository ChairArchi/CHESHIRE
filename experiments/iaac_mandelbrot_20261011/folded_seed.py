"""Continuous folded column carriers, modelled from the public IAAC silhouette.

The macro folds are explicitly modelled, NOT claimed to emerge from Mandelbulb.
One continuous closed quad surface; CHESHIRE refinement/CC/growth reused intact.
"""
from pathlib import Path
import argparse,shutil,sys
import numpy as np
from scipy.interpolate import CubicSpline,PchipInterpolator
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import study as base
import column_study as column
import variation_study as variants
from cheshire.reference_subdivision import topology,subdivide

KNOTS=np.array([0,.06,.17,.27,.38,.49,.59,.70,.81,.91,1.])
PROFILES={
 'F01_CONTINUOUS':dict(wing=[.95,1.2,1.05,.72,1.38,1.12,.62,1.12,1.28,.69,.70],
     core=[.30,.29,.30,.28,.31,.30,.28,.30,.31,.29,.28],return_gain=.45,turn=0.,front_bias=.10),
 'F02_RETURN':dict(wing=[.95,1.2,1.08,.66,1.48,1.15,.55,1.18,1.37,.66,.72],
     core=[.27,.27,.28,.24,.28,.26,.24,.26,.28,.26,.25],return_gain=1.,turn=0.,front_bias=.13),
 'F03_TURN':dict(wing=[.88,1.14,1.04,.70,1.38,1.05,.63,1.16,1.30,.75,.72],
     core=[.29,.28,.29,.27,.30,.29,.26,.28,.30,.27,.27],return_gain=.70,turn=.62,front_bias=.12),
 'F04_FAN':dict(wing=[.88,1.08,.94,.64,1.18,1.02,.57,1.02,1.10,.68,.62],
     core=[.27,.38,.29,.18,.62,.22,.17,.63,.24,.18,.27],return_gain=.75,turn=0.,front_bias=.14,
     fan=[0,-.12,.12,.35,-.28,-.08,.40,-.30,.10,.18,0],curl=0.,sectors=64),
 'F05_CURL':dict(wing=[.88,1.08,.94,.64,1.18,1.02,.57,1.02,1.10,.68,.62],
     core=[.27,.38,.29,.18,.62,.22,.17,.63,.24,.18,.27],return_gain=.90,turn=.16,front_bias=.14,
     fan=[0,-.12,.12,.35,-.28,-.08,.40,-.30,.10,.18,0],curl=1.5,sectors=64),
 'F06_CUP_CURL':dict(wing=[.95,1.12,.90,.59,1.24,.94,.52,.98,1.18,.57,.68],
     core=[.27,.42,.25,.16,.72,.19,.15,.70,.20,.16,.24],return_gain=1.15,turn=.32,front_bias=.18,
     fan=[0,-.12,.18,.42,-.34,-.08,.45,-.34,.20,.22,0],curl=2.4,sectors=64),
}

def carrier(name):
    p=PROFILES[name];cfg=variants.recipe(name,rings=41,sectors=p.get('sectors',32));m,ch=variants.carrier(cfg)
    s=ch[:,0];theta=np.arctan2(ch[:,2],ch[:,1])
    wing=PchipInterpolator(KNOTS,p['wing'])(s);core=PchipInterpolator(KNOTS,p['core'])(s)
    turn=p['turn']*np.sin(2*np.pi*(s-.08))*np.sin(np.pi*s)
    # cos(theta) reverses under X reflection, so both winding flows are mirrors.
    phase=theta-turn*np.cos(theta)
    lobe=(.5-.5*np.cos(4*phase))**.8
    radius=core+wing*lobe*(1+p['front_bias']*np.sin(theta))
    fan=PchipInterpolator(KNOTS,p.get('fan',[0]*len(KNOTS)))(s)
    curl=p.get('curl',0)*(.3+.7*np.sin(np.pi*s)**2)
    mapped=theta+fan*np.sin(2*theta)+curl*np.sin(4*theta)/4
    x=radius*np.cos(mapped);y=radius*np.sin(mapped)
    # A continuous ridge never drops to a circular neck. Individual crest paths
    # fold back vertically while valleys remain through-going axial channels.
    returned=CubicSpline(KNOTS,[0,-.10,.05,.32,-.60,-.14,.56,.18,-.65,.14,0])(s)
    zz=10*s+p['return_gain']*returned*lobe
    cap=(ch[:,1]**2+ch[:,2]**2)<1e-12
    x[cap]=0;y[cap]=0;zz[cap]=10*s[cap]
    m.xyz=np.column_stack([x,y,zz]);column.reflect(m,ch);m.rest=m.xyz.copy()
    return m,ch,dict(name=name,profiles=p,knots=KNOTS.tolist(),rings=41,sectors=cfg['sectors'],
        construction='One continuous four-pleat section family, nonzero wing depth through necks, axial crest returns',
        reference='IAAC initial CC silhouette; explicit parametric modelling, not recovered IAAC initial cage',
        field_generated_macro=False)

def save_cc(root,name,stage,mesh,ch):
    t=topology(mesh);cc,_,_=subdivide(mesh,{});chart=base.interpolate_chart(ch,t,len(mesh.faces))
    base.save(root,'folded/'+name,stage+'_CC',cc,chart,{},dict(
        parent='folded/'+name+'/'+stage,operation='One actual neutral Catmull-Clark presentation subdivision',
        fractal_growth_generation=False,separate_geometric_smoothing=False,CC_coordinate_averaging=True),mirror_callback=column.reflect)
    shutil.copy2(__file__,root.resolve('folded/'+name+'/'+stage+'_CC/folded_recipe.py'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default=base.DEFAULT_ROOT)
    p.add_argument('--names',nargs='*',default=list(PROFILES));p.add_argument('--mode',choices=['seed','field','growth'],default='seed')
    p.add_argument('--last',type=int,default=2);p.add_argument('--cc',action='store_true');args=p.parse_args()
    root=base.ArtifactRoot(Path(args.root))
    for name in args.names:
        folder=root.resolve('folded/'+name+'/G00')
        if not (folder/'checkpoint.npz').exists():
            m,ch,meta=carrier(name);base.save(root,'folded/'+name,'G00',m,ch,{},dict(meta,operation='Explicit continuous folded seed'),mirror_callback=column.reflect)
            shutil.copy2(__file__,folder/'folded_recipe.py')
        else:m,ch=base.load(folder)
        if args.mode=='seed':
            if args.cc and not root.resolve('folded/'+name+'/G00_CC/checkpoint.npz').exists():save_cc(root,name,'G00',m,ch)
            continue
        stem=name+('_FIELD' if args.mode=='field' else '_GROWTH')
        cfg=variants.recipe(stem,eligibility='new',fraction=.50,axial=3.6)
        trees,path=variants.grid(cfg,root) if args.mode=='field' else (None,None)
        for g in range(1,args.last+1):
            stage=f'G{g:02}';target=root.resolve('folded/'+stem+'/'+stage)
            if (target/'checkpoint.npz').exists():m,ch=base.load(target);continue
            if args.mode=='field':
                m,ch,record,meta=variants.advance(m,ch,cfg,g,trees)
                meta['parent']='folded/'+name+'/G00' if g==1 else f'folded/{stem}/G{g-1:02}'
                meta['field_path']=path
            else:
                old=len(m.xyz);t=topology(m);m,op=base.growth.step(m,
                    face_gain=.58,edge_gain=.16,feedback=1.4,inherited_bias=.5,vertex_memory=1,
                    mode='interpolating',surface='mean')
                ch=base.interpolate_chart(ch,t,len(t['n']));column.reflect(m,ch)
                record={k:op[k] for k in ('face_vector','edge_vector','support_radius','face_bend')}
                meta=dict(parent='folded/'+name+'/G00' if g==1 else f'folded/{stem}/G{g-1:02}',
                    operation='Unchanged Task36 interpolating support/bend growth on explicit folded seed',
                    controls=dict(face_gain=.58,edge_gain=.16,feedback=1.4,inherited_bias=.5,vertex_memory=1),
                    old_vertex_max_movement=0.,separate_geometric_smoothing=False,CC_coordinate_averaging=False)
            base.save(root,'folded/'+stem,stage,m,ch,record,meta,mirror_callback=column.reflect)
            shutil.copy2(__file__,target/'folded_recipe.py')
        if args.cc and not root.resolve('folded/'+stem+f'/G{args.last:02}_CC/checkpoint.npz').exists():
            save_cc(root,stem,f'G{args.last:02}',m,ch)

if __name__=='__main__':main()
