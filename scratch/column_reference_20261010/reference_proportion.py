"""Refine the specific reference column's coarse masses, no subdivision."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'reference_proportion_results';OUT.mkdir(exist_ok=True)

def column(stage):
    n=8 if stage<3 else 16
    if stage==1:
        profile=[(0,.82),(1.4,.82),(2.65,.20),(2.95,.20),(3.2,.30),(3.9,.86),(8,.86)]
    else:
        profile=[(0,.95),(.45,.50),(.75,.50),(1.05,1.35),(2.25,1.35),(2.72,.55),(2.9,.27),(3.12,.27),(3.48,.27),(3.76,.27),(4.02,.56),(4.95,1.40),(7.5,1.40),(8,1.07)]
        if stage==3:
            # Only the short neck interval acquires the collar's extra axial faces.
            profile=[(0,.95),(.45,.50),(.75,.50),(1.05,1.35),(2.25,1.35),(2.72,.55),(2.9,.27),(3.00,.27),(3.07,.70),(3.37,.70),(3.66,.28),(3.76,.28),(4.02,.56),(4.95,1.40),(7.5,1.40),(8,1.07)]
    # Octagon corner cuts create extra flat longitudinal planes, not smooth subdivision.
    poly=[(math.cos(2*math.pi*i/8+math.pi/8),math.sin(2*math.pi*i/8+math.pi/8)) for i in range(8)]
    if stage==3:
        poly=[tuple(.84*p[k]+.16*q[k] for k in range(2)) for i,p in enumerate(poly) for q in (poly[i-1],poly[(i+1)%8])]
    vs=[(r*x,r*y,z) for z,r in profile for x,y in poly]
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
    return vs,fs,n

source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('range(1,5)','range(1,4)').replace('COLUMN_STUDY_COMPLETE','REFERENCE_PROPORTION_COMPLETE')
exec(compile(render,str(ROOT/'build.py')+' [shared render/export]','exec'))
