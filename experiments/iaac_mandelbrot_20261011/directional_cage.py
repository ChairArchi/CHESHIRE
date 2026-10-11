"""Finite feasibility probes for overlapping, direction-dependent macro folds.

Explicit sculpture cages, not a recovered IAAC algorithm or physical origami.
Independent opposing ridge pairs share ONE quad surface and overlapping spans.
Actual neutral CC is retained separately to inspect the raw-to-curved relation.
"""
from pathlib import Path
import sys,shutil,argparse
import numpy as np
from scipy.interpolate import CubicSpline
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import study as base
import column_study as column
import variation_study as v
from cheshire.reference_subdivision import topology,subdivide

K=np.array([0,.08,.18,.29,.40,.51,.62,.73,.84,.93,1.])
CONFIGS={
 'D01_STAGGERED':dict(
    a=[1.05,1.3,.85,.48,1.4,1.0,.48,.82,1.24,.65,.75],
    b=[.72,.65,1.18,1.1,.48,.72,1.12,1.2,.52,.50,.70],
    za=[0,-.08,.08,.45,-.65,-.1,.60,.2,-.50,.05,0],
    zb=[0,.05,-.35,-.15,.60,.15,-.35,-.20,.50,.08,0],gain=.8),
 'D02_INTERLEAVED':dict(
    a=[1.,1.25,.88,.43,1.42,.98,.44,.80,1.25,.60,.72],
    b=[.70,.66,1.22,1.13,.43,.78,1.18,1.22,.48,.52,.68],
    za=[0,-.10,.12,.65,-.85,-.1,.80,.15,-.65,.10,0],
    zb=[0,.05,-.55,-.20,.85,.25,-.50,-.20,.70,.10,0],gain=1.2),
}
CONFIGS['D03_CREASE_DRIFT']=dict(CONFIGS['D02_INTERLEAVED'],drift=.68)
CONFIGS['D04_DEEP_RETURN']=dict(CONFIGS['D02_INTERLEAVED'],gain=1.8)
CONFIGS['D05_CURVED_PATH']=dict(CONFIGS['D02_INTERLEAVED'],drift=.68,physical_drift=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--names',nargs='*');args=parser.parse_args()
    root=base.ArtifactRoot(Path(base.DEFAULT_ROOT))
    for name,cfg in CONFIGS.items():
        if args.names and name not in args.names:continue
        m,ch=v.carrier(v.recipe(name,rings=25,sectors=32));s=ch[:,0]
        material_theta=np.arctan2(ch[:,2],ch[:,1]);theta=material_theta.copy()
        # theta' = theta + beta(s)*cos(theta) commutes with X reflection.
        # beta remains below 1, preserving angular order before the axial return.
        # This is explicit cage modelling, not an inextensible paper simulation.
        beta=cfg.get('drift',0.)*np.sin(np.pi*s)*np.sin(3*np.pi*s+.35)
        theta=theta+beta*np.cos(theta);ca=np.cos(theta);si=np.sin(theta)
        a=CubicSpline(K,cfg['a'])(s);b=CubicSpline(K,cfg['b'])(s)
        za=CubicSpline(K,cfg['za'])(s);zb=CubicSpline(K,cfg['zb'])(s)
        # Axis-specific ridge pairs. Adjacent pairs develop at different heights;
        # neither pair is shut off at a shared circular neck boundary.
        # D03 intentionally preserved: all terms follow the changed angle,
        # which merely reparametrizes the continuous surface. It is NOT a
        # successful fold-path change. D05 transports material ridge/return
        # values into different physical directions, changing the actual shape.
        rc=np.cos(material_theta) if cfg.get('physical_drift') else ca
        rs=np.sin(material_theta) if cfg.get('physical_drift') else si
        x=ca*(.23+a*rc**2);y=si*(.23+b*rs**2)
        z=10*s+cfg['gain']*(za*rc**2+zb*rs**2)
        # Distinguish front/back while preserving the required X reflection.
        y+=.12*np.sin(np.pi*s)**2
        z+=.18*np.sin(3*np.pi*s)*rs*np.sin(np.pi*s)
        cap=np.linalg.norm(ch[:,1:],axis=1)<1e-12;x[cap]=y[cap]=0;z[cap]=10*s[cap]
        m.xyz=np.column_stack([x,y,z]);column.reflect(m,ch);m.rest=m.xyz.copy()
        metadata=dict(operation='Explicit direction-dependent overlapping fold cage',
            knobs=cfg,knots=K.tolist(),field_generated=False,origami_constraints='NOT_ENFORCED',
            IAAC_status='Feasibility model of observed directional behaviour; not recovered source or exact reproduction',
            geometry_logic='Opposing X and Y ridge pairs have offset axial expansion and return profiles, share vertices and overlap in height')
        if name=='D03_CREASE_DRIFT':metadata['design_status']='FAILED: angular reparametrization, no intended continuous-surface change'
        for level in range(3):
            stage='CAGE' if level==0 else f'CC{level}'
            if not root.resolve('directional/'+name+'/'+stage+'/checkpoint.npz').exists():
                base.save(root,'directional/'+name,stage,m,ch,{},dict(metadata,
                    CC_coordinate_averaging=level>0,CC_passes=level,separate_geometric_smoothing=False,
                    fractal_growth_generation=False),mirror_callback=column.reflect)
                shutil.copy2(__file__,root.resolve('directional/'+name+'/'+stage+'/directional_recipe.py'))
            if level<2:
                t=topology(m);m,_,_=subdivide(m,{});ch=base.interpolate_chart(ch,t,len(t['n']))
                column.reflect(m,ch)

if __name__=='__main__':main()
