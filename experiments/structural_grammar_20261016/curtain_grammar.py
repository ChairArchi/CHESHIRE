"""Long folded membranes with continuous back-webs and unequal branch lengths."""
import numpy as np
from scipy.interpolate import PchipInterpolator
import grammar_kernel as k


def folded_web(phase,lo,hi,radii,turn,*,width_samples=13,long_samples=25,thickness=.13,
               radial_knots=None):
    s=np.linspace(0,1,long_samples);v=np.linspace(0,1,width_samples)
    knots=np.asarray(radial_knots if radial_knots is not None else
        [0.,.09,.23,.59,.72,.80,.93,1.] if len(radii)==8 else
        [0.,.16,.55,.82,1.],float)
    outer=PchipInterpolator(knots,radii)(s)
    base=phase+turn*np.sin(np.pi*(s-.12))
    # One large radial membrane is continuously attached to the core.
    radius=.23+v[None,:]*(outer[:,None]-.23)
    theta=base[:,None]+(.48+.22*np.sin(np.pi*s))[:,None]*v[None,:]**2
    z=lo+(hi-lo)*s[:,None]+.52*np.sin(np.pi*v)[None,:]*np.sin(2*np.pi*s)[:,None]
    z=z+.24*v[None,:]**2*np.sin(np.pi*s)[:,None]
    surface=np.stack([radius*np.cos(theta),radius*np.sin(theta),np.broadcast_to(z,radius.shape)],axis=-1)
    return k.closed_sheet(surface,thickness)


def build_components():
    z=np.linspace(0,10,24)
    centre=np.column_stack([.10*np.sin(z*.45),.05*np.sin(z*.73),z])
    core=k.loft_closed_tube(centre,PchipInterpolator([0,1.2,4.0,7.5,10],[.62,.43,.39,.46,.56])(z),20)
    parts=[dict(name='continuous narrow spine',xyz=core[0],faces=core[1],role='spine',level=0)]
    profiles=[(.10,.55,9.65,[.52,1.10,2.65,1.90,1.10,2.28,1.65,.52],.62),
              (2.20,.70,9.35,[.52,1.65,2.20,.85,1.30,2.80,1.42,.52],-.42),
              (4.30,.90,9.55,[.52,.90,1.90,2.65,1.00,1.75,2.40,.52],.38)]
    for i,(phase,lo,hi,r,turn) in enumerate(profiles):
        x,t=folded_web(phase,lo,hi,r,turn)
        parts.append(dict(name=f'long continuous fold {i+1}',xyz=x,faces=t,role='primary_long_fold',level=1))
    # These smaller branches occupy different extents and follow one large fold.
    for i,(phase,lo,hi,r,turn) in enumerate([
        (.46,6.40,9.10,[.48,1.12,1.56,1.23,.47],.30),
        (2.90,1.10,2.70,[.47,.94,1.48,1.10,.47],-.24)]):
        x,t=folded_web(phase,lo,hi,r,turn,width_samples=10,long_samples=17,thickness=.11)
        parts.append(dict(name=f'partial nested fold {i+1}',xyz=x,faces=t,role='secondary_fold',level=2))
    return parts,dict(id='S03_CURTAIN',label_ko='긴 접힘이 갈라지는 연속 겹막',
        grammar='Three long radial membranes, two shorter unequal nested branches and a continuous central back-web; no previous column seed.',
        operations=['Actual different parameterized closed sheets','Continuous core attachment along every primary fold','Solid Boolean union','Actual descendant Catmull-Clark'],
        primary_units=3,secondary_units=2,local_axes='Different smoothly curved planes; no imposed global X/Y mirror.',
        segmentation='Unequal axial bend intervals; long primary membranes, a short lower branch 1.1-2.7 and an upper branch 6.4-9.1. No uniform node grid.',
        apparent_recesses='Each folded membrane is a closed thick volume attached by a continuous inner web.',
        old_seed_used=False,ornament_added=False)
