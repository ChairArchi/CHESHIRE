"""Image-inferred panel 4 -> panel 5, rightmost column only.
Operations are axial section editing and selective angular folding, not smoothing.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'reference_next_panel_results';OUT.mkdir(exist_ok=True)

def tent(z,low,peak,high):
    if z<=low or z>=high:return 0.
    return (z-low)/(peak-low) if z<peak else (high-z)/(high-peak)

def angular_fold(radius,angle,z,low,peak,high,depth,lobes=4,phase=0):
    # The current section supplies its radius; recesses alternate with parent ridges.
    sector=(angle-phase)*lobes/(2*math.pi)
    triangular=abs(2*(sector-math.floor(sector)) - 1)
    return radius-depth*tent(z,low,peak,high)*(1-triangular)

def column(stage):
    n=16
    if stage==1:
        profile=[(0,.95),(.52,.50),(.72,.50),(.90,1.35),(2.02,1.35),(2.50,.48),(2.58,.27),(2.70,.70),(3.06,.70),(3.24,.28),(3.52,.28),(3.68,.56),(4.765,1.40),(7.5,1.40),(8,1.07)]
    else:
        # New cuts are concentrated in the neck, canopy and lower body.
        profile=[(0,.95),(.52,.50),(.72,.50),(.90,.55),(1.18,1.00),(1.62,1.35),(2.08,1.28),(2.50,.66),(2.66,.40),(2.72,1.40),(3.38,.30),(3.52,.25),(4.04,.25),(4.24,.48),(4.88,1.40),(7.5,1.40),(8,1.07)]
    vs=[]
    for z,r in profile:
        for i in range(n):
            a=2*math.pi*i/n
            rr=r
            if stage==2:
                # Selected lower mass becomes four thick longitudinal lobes.
                rr=angular_fold(rr,a,z,.90,1.62,2.66,.83,4,math.pi/4)
                # Fine axial ribs at the narrow stem, driven by the same section angles.
                rr+=.065*tent(z,3.38,3.52,4.24)*max(0,math.cos(4*a))
                # Restrained longitudinal faceting on the long upper body.
                rr-=.045*tent(z,4.24,4.88,8)*max(0,math.cos(8*a))
            vs.append((rr*math.cos(a),rr*math.sin(a),z))
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
    return vs,fs,n

source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('range(1,5)','range(1,3)').replace('COLUMN_STUDY_COMPLETE','REFERENCE_NEXT_PANEL_COMPLETE')
exec(compile(render,str(ROOT/'build.py')+' [shared render/export]','exec'))
(OUT/'interpretation.json').write_text(json.dumps(dict(reference='hansmeyer_reference.png',panels=[4,5],column='rightmost',observations=['upper mass retained','neck develops longitudinal ribs','collar spreads into canopy','lower mass develops deep axial valleys'],operations=['local axial cuts and radius remap','triangular angular folding of lower mass','small radial ribs on stem'],subdivision=False,smoothing=False,limitations=['backside inferred by symmetry','no original algorithm recovery','band locations currently configured for this column','no through-holes inferred']),indent=2))
