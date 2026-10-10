"""Reference top-row fourth panel, right column: polygonal mass/neck study.
No global subdivision. Local face extrusion creates faces only where needed.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'reference_column_results';OUT.mkdir(exist_ok=True)

def column(stage):
    # Flat cut ends correspond to the column continuing beyond the reference crop.
    n=8
    profiles=[
        [(0,.78),(1.4,.78),(2.65,.78),(2.95,.78),(3.2,.78),(3.9,.78),(8,.78)],
        [(0,.82),(1.4,.82),(2.65,.20),(2.95,.20),(3.2,.30),(3.9,.86),(8,.86)],
        [(0,.82),(1.4,.82),(2.65,.20),(2.95,.20),(3.2,.30),(3.9,.86),(8,.86)],
        [(0,.82),(1.4,.82),(2.65,.20),(2.95,.20),(3.2,.30),(3.9,.86),(8,.86)],
    ]
    vs=[(r*math.cos(2*math.pi*i/n+math.pi/8),r*math.sin(2*math.pi*i/n+math.pi/8),z) for z,r in profiles[stage-1] for i in range(n)]
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(6) for i in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple(6*n+i for i in range(n))])
    def extrude(face_id, distance, dz, shrink):
        old=fs[face_id];ps=[Vector(vs[k]) for k in old];c=sum(ps,Vector())/len(ps)
        normal=Vector((c.x,c.y,0)).normalized()
        new=[]
        for p in ps:
            q=c+(p-c)*shrink+normal*distance+Vector((0,0,dz))
            new.append(len(vs));vs.append(tuple(q))
        fs[face_id]=tuple(new)
        for k in range(len(old)):
            j=(k+1)%len(old);fs.append((old[k],old[j],new[j],new[k]))
        return face_id
    # The base reproduction is stage 2. Further two stages are local alternatives,
    # not claims about the unseen original construction history.
    if stage>=3:
        for i in (0,2,4,6):extrude(8+i,.32,-.18,.58)
    if stage>=4:
        for i in (0,2,4,6):extrude(8+i,.26,.36,.52)
        for i in (1,3,5,7):extrude(32+i,.22,-.26,.52)
    return vs,fs,n

source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('COLUMN_STUDY_COMPLETE','REFERENCE_COLUMN_COMPLETE')
exec(compile(render,str(ROOT/'build.py')+' [shared render/export]','exec'))
