"""Flat-ended column; chunky polygon-corner wings, not literal rocket fins."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'wedge_results';OUT.mkdir(exist_ok=True)

def column(stage):
    n=16
    zs=[0,.6,1.1,1.5,1.85,2.35,3.6,4.1,4.5,4.85,5.35,6.4,8]
    vertices=[]
    for z in zs:
        for i in range(n):
            a=2*math.pi*i/n
            r=.65;dz=0
            if stage>=2:
                # Broad roots occupy adjacent corner sectors; no separate fin plates.
                weight=max(0,1-min(i%4,4-i%4)/2)
                envelope=max(0,1-abs(z-1.5)/.85)
                r+=.78*weight*envelope
                dz-=.22*weight*envelope
            if stage>=3:
                # Same transformation rotated half a parent interval at another height.
                q=(i-2)%4;weight=max(0,1-min(q,4-q)/2)
                envelope=max(0,1-abs(z-4.5)/.85)
                r+=.67*weight*envelope
                dz+=.22*weight*envelope
            vertices.append((r*math.cos(a),r*math.sin(a),z+dz))
    faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(zs)-1) for i in range(n)]
    faces.extend([tuple(reversed(range(n))),tuple((len(zs)-1)*n+i for i in range(n))])
    return vertices,faces,n

source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('range(1,5)','range(1,4)').replace('COLUMN_STUDY_COMPLETE','WEDGE_STUDY_COMPLETE')
exec(compile(render,str(ROOT/'build.py')+' [shared render/export]','exec'))
