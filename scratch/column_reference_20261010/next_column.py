"""Local polygon growth on the reference column. No smoothing/subdivision.
Stages: prior proportion, corrected proportion, shoulder growth, cap growth.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'next_column_results';OUT.mkdir(exist_ok=True)
HISTORY=[]

def column(stage):
    n=16
    if stage==1:
        profile=[(0,.95),(.45,.50),(.75,.50),(1.05,1.35),(2.25,1.35),(2.72,.55),(2.9,.27),(3.00,.27),(3.07,.70),(3.37,.70),(3.66,.28),(3.76,.28),(4.02,.56),(4.95,1.40),(7.5,1.40),(8,1.07)]
    else:
        profile=[(0,.95),(.52,.50),(.72,.50),(.90,1.35),(2.02,1.35),(2.50,.48),(2.58,.27),(2.70,.70),(3.06,.70),(3.24,.28),(3.52,.28),(3.68,.56),(4.765,1.40),(7.5,1.40),(8,1.07)]
    octagon=[(math.cos(2*math.pi*i/8+math.pi/8),math.sin(2*math.pi*i/8+math.pi/8)) for i in range(8)]
    poly=[tuple(.84*p[k]+.16*q[k] for k in range(2)) for i,p in enumerate(octagon) for q in (octagon[i-1],octagon[(i+1)%8])]
    vs=[(r*x,r*y,z) for z,r in profile for x,y in poly]
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
    before=len(fs);events=[]
    def grow(face_id, radial, axial, scale, generation):
        face=fs[face_id];points=[Vector(vs[k]) for k in face];center=sum(points,Vector())/len(points)
        outward=Vector((center.x,center.y,0)).normalized()
        cap=[]
        for point in points:
            p=center+(point-center)*scale+outward*radial+Vector((0,0,axial))
            cap.append(len(vs));vs.append(tuple(p))
        fs[face_id]=tuple(cap)
        for k in range(len(face)):
            j=(k+1)%len(face);fs.append((face[k],face[j],cap[j],cap[k]))
        events.append(dict(parent_face=face_id,generation=generation,radial=radial,axial=axial,cap_scale=scale,new_side_faces=len(face)))
    if stage>=3:
        for i in (1,5,9,13):grow(11*n+i,.62,-.42,.60,1)
    if stage>=4:
        # Grow the actual caps made above, rather than reseeding the original body.
        for i in (1,5,9,13):grow(11*n+i,.26,-.24,.52,2)
        # Opposed upward growth on lower shoulder, rotated by half a parent interval.
        for i in (3,7,11,15):grow(4*n+i,.42,.40,.60,1)
    HISTORY.append(dict(stage=stage,base_faces=before,final_faces=len(fs),operations=events,subdivision=False,smoothing=False))
    return vs,fs,n

source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('COLUMN_STUDY_COMPLETE','NEXT_COLUMN_COMPLETE')
exec(compile(render,str(ROOT/'build.py')+' [shared render/export]','exec'))
(OUT/'operation_history.json').write_text(json.dumps(HISTORY,indent=2))
