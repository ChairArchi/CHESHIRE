import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'branched_column_results';OUT.mkdir(exist_ok=True)
VIEWS=['front','oblique']
if '--' in sys.argv:
    args=sys.argv[sys.argv.index('--')+1:];OUT=Path(args[0]).resolve();OUT.mkdir(exist_ok=True)
    if len(args)>1:VIEWS=args[1].split(',')
def column(stage):
    j=json.loads((OUT/'mesh.json').read_text());return [tuple(v) for v in j['vertices']],[tuple(f) for f in j['faces']],16
_bounds=json.loads((OUT/'mesh.json').read_text())['vertices']
_low=min(v[2] for v in _bounds);_high=max(v[2] for v in _bounds)
VIEW_SCALE=(_high-_low)/8;VIEW_CENTER=(_high+_low)/2
source=(ROOT/'build.py').read_text(encoding='utf-8')
render=source[source.index("bpy.ops.object.select_all(action='SELECT')"):]
render=render.replace('range(1,5)','range(1,2)').replace("OUT/'validation.json'","OUT/'blender_validation.json'")
render=render.replace('        cam.location=pos;', '        if view not in VIEWS:continue\n        cam.location=pos;')
render=render.replace('camdata.ortho_scale=9','camdata.ortho_scale=9*VIEW_SCALE')
render=render.replace('cam.location=pos;cam.rotation_euler=(Vector((0,0,4))-cam.location)', 'cam.location=Vector((pos[0]*VIEW_SCALE,pos[1]*VIEW_SCALE,(pos[2]-4)*VIEW_SCALE+VIEW_CENTER));cam.rotation_euler=(Vector((0,0,VIEW_CENTER))-cam.location)')
exec(compile(render,'shared render/export','exec'))
