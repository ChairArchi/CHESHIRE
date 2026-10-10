"""One actual Catmull-Clark level with dihedral-driven crease preservation."""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'regional_cc_results';OUT.mkdir(exist_ok=True)
sourcefile=ROOT/'regional_children_results/mesh.json'
if '--' in sys.argv:
    args=sys.argv[sys.argv.index('--')+1:];sourcefile=Path(args[0]).resolve();OUT=Path(args[1]).resolve();OUT.mkdir(parents=True,exist_ok=True)
source=json.loads(sourcefile.read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
m=bpy.data.meshes.new('regional');m.from_pydata(source['vertices'],[],source['faces']);m.update()
ob=bpy.data.objects.new('regional',m);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
bm=bmesh.new();bm.from_mesh(m);crease=bm.edges.layers.float.new('crease_edge');protected=0
for e in bm.edges:
    angle=e.calc_face_angle(0)
    value=1.0 if angle>=math.radians(30) else (.8 if angle>=math.radians(12) else 0.)
    e[crease]=value;protected+=value>0
bm.to_mesh(m);bm.free()
mod=ob.modifiers.new('One crease-preserving CC level','SUBSURF');mod.subdivision_type='CATMULL_CLARK';mod.levels=1;mod.render_levels=1;mod.use_limit_surface=False
bpy.ops.object.modifier_apply(modifier=mod.name)
vs=[tuple(v.co) for v in ob.data.vertices];fs=[tuple(p.vertices) for p in ob.data.polygons]
(OUT/'mesh.json').write_text(json.dumps(dict(vertices=vs,faces=fs)))
(OUT/'operation.json').write_text(json.dumps(dict(operation='Blender Catmull-Clark',levels=1,crease_edges=int(protected),input_faces=len(source['faces']),output_faces=len(fs),crease_rule='>=30 degrees: 1; >=12 degrees: .8; otherwise 0',use_limit_surface=False,claim='controlled comparison only, not inferred original algorithm'),indent=2))
def column(stage):return vs,fs,16
render=(ROOT/'build.py').read_text(encoding='utf-8');render=render[render.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('range(1,5)','range(1,2)').replace("'smoothing':False,'subdivision':False","'smoothing':'CC crease constrained','subdivision':True")
exec(compile(render,'shared render/export','exec'))
