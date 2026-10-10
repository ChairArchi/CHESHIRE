"""Simple rocket-column study: straight body plus literal triangular fins.
Blender -b --python rocket_build.py. Reuses the previous study's render/export setup.
"""
import bpy, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def make_mesh(name, vertices, faces):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    return obj

def fin(angle, root_low, root_high, tip_z, reach, half_thickness=.065):
    # A triangular prism: an actual fin, with its root embedded in the body.
    section=[(.46,root_low),(.46,root_high),(reach,tip_z)]
    vertices=[]
    for side in (-half_thickness,half_thickness):
        for radius,z in section:
            vertices.append((radius*math.cos(angle)-side*math.sin(angle),radius*math.sin(angle)+side*math.cos(angle),z))
    return make_mesh('triangular_fin',vertices,[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)])

def column(stage):
    n=8 if stage<3 else 16
    # Straight shaft and one low-poly nose. No repeated necks or ornaments.
    rings=[(0,.62),(6.8,.62),(7.85,.10),(8,.10)]
    vs=[(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for z,r in rings for i in range(n)]
    fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(rings)-1) for i in range(n)]
    fs+=[tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))]
    body=make_mesh('rocket_body',vs,fs)
    if stage>=2:
        specs=[(i*math.pi/2,.75,3.1,.50,1.75) for i in range(4)]
        if stage>=3:specs += [(math.pi/4+i*math.pi/2,1.8,3.8,1.45,1.25) for i in range(4)]
        for spec in specs:
            wing=fin(*spec)
            bpy.context.view_layer.objects.active=body
            mod=body.modifiers.new('Union attached fin','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=wing
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(wing,do_unlink=True)
    vs=[tuple(v.co) for v in body.data.vertices];fs=[tuple(p.vertices) for p in body.data.polygons]
    bpy.data.objects.remove(body,do_unlink=True)
    return vs,fs,n

# Keep the same material, camera, export and validation as the previous study.
source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('range(1,5)','range(1,4)').replace('COLUMN_STUDY_COMPLETE','ROCKET_STUDY_COMPLETE')
OUT=ROOT/'rocket_results';OUT.mkdir(exist_ok=True)
import bmesh,json
from mathutils import Vector
exec(compile(render,str(ROOT/'build.py')+' [shared render/export]','exec'))
