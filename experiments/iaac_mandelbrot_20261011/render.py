"""Uniform actual-mesh rendering; camera/light recipe reused without changes."""
from pathlib import Path
import sys,bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_shared as d
args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]);final='final' in args[1:]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
g=np.load(folder/'geometry.npz');me=bpy.data.meshes.new('Actual generated triangles')
me.from_pydata(g['xyz'].tolist(),[],g['faces'].tolist());me.update()
ob=bpy.data.objects.new(folder.parent.name+'_'+folder.name,me);bpy.context.collection.objects.link(ob)
d.material(ob)
# gate.ply written by the study is the validation input; preserve it unchanged.
d.export(ob,folder,stem='gate_export',obj=final)
d.render(folder if final else folder/'preview',['front','oblique','side'],resolution=1200 if final else 800,samples=32 if final else 16)
cam=bpy.context.scene.camera;cam.location=d.VIEWS['oblique']
cam.rotation_euler=(Vector((0,0,6.5))-cam.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'gate.blend'))
print('RENDERED',folder,flush=True)
