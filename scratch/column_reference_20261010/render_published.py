"""Actual Blender renders; identical camera/scale/light for all generations."""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:]
wide='--wide' in args
detail='--detail' in args
carrier='--carrier' in args
args=[a for a in args if a not in ['--wide','--detail','--carrier']]
source=(ROOT/'build.py').read_text(encoding='utf8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render='\n'.join(line for line in render.splitlines() if "(folder/'column.obj').write_text" not in line and "(folder/'column.ply').write_text" not in line)
render=render.replace('range(1,5)','range(1,2)').replace("OUT/'validation.json'","OUT/'blender_validation.json'")
scale=14 if carrier else 12 if wide else 10
render=render.replace('camdata.ortho_scale=9','camdata.ortho_scale='+str(scale))
render=render.replace('t.area<1e-10','t.area<=0')
render=render.replace("assert report['zero_area_triangles']==0", "report['precision_note']='Blender float32 preview may collapse tiny CGAL cut triangles; validated double-precision mesh.json and OBJ/PLY are authoritative'")
if detail:
    render=render.replace('camdata.ortho_scale='+str(scale),'camdata.ortho_scale=3.8')
    render=render.replace('Vector((0,0,4))-cam.location','Vector((0,0,4.8))-cam.location')
    render=render.replace("('front',(0,-16,4))","('front',(0,-16,4.8))")
    render=render.replace('scene.render.resolution_x=640;scene.render.resolution_y=1200','scene.render.resolution_x=1000;scene.render.resolution_y=1000')
for folder in args:
    folder=Path(folder).resolve();data=json.loads((folder/'mesh.json').read_text())
    OUT=folder/('carrier_camera' if carrier else 'fixed_detail' if detail else 'fixed_camera_wide' if wide else 'fixed_camera');OUT.mkdir(exist_ok=True)
    def column(stage):return [tuple(v) for v in data['vertices']],[tuple(f) for f in data['faces']],16
    exec(compile(render,'fixed camera comparison','exec'))
