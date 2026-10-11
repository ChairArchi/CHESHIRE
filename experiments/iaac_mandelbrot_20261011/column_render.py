"""Actual column meshes only, identical cameras/material/lights for all cases."""
from pathlib import Path
import sys,json,bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_shared as d
args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]);final='final' in args[1:]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
g=np.load(folder/'geometry.npz');me=bpy.data.meshes.new('Actual generated triangles')
me.from_pydata(g['xyz'].tolist(),[],g['faces'].tolist());me.update()
ob=bpy.data.objects.new(folder.parent.name+'_'+folder.name,me);bpy.context.collection.objects.link(ob)
d.material(ob);d.export(ob,folder,stem='gate_export',obj=final)
scene,cam=d.setup_scene(1200 if final else 800,32 if final else 16)
cam.data.ortho_scale=12.
views={'front':(0,32,5),'oblique':(-18,28,16),'side':(-32,0,5)}
output=folder if final else folder/'preview';output.mkdir(exist_ok=True)
for name,pos in views.items():
    cam.location=pos;cam.rotation_euler=(Vector((0,0,5))-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(output/(name+'.png'));bpy.ops.render.render(write_still=True)
d.dump(output/'render_receipt.json',dict(engine='Blender Cycles',resolution=[scene.render.resolution_x]*2,
    samples=scene.cycles.samples,orthographic_scale=12.,target=[0,0,5],views=views,
    geometry='Actual explicit saved triangles',material='Uniform mineral; flat geometric normals',
    modifiers=[],extra_meshes=[],normal_maps=False))
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'column.blend'))
print('RENDERED',folder,flush=True)
