"""Render actual exported mesh with Cycles; no image generation or geometry edits."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];meshfile=Path(args[0]).resolve();out=Path(args[1]).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.obj_import(filepath=str(meshfile),forward_axis='Y',up_axis='Z');obj=bpy.context.selected_objects[0]
bounds=[obj.matrix_world@Vector(v) for v in obj.bound_box];lo=Vector(tuple(min(v[i] for v in bounds) for i in range(3)));hi=Vector(tuple(max(v[i] for v in bounds) for i in range(3)));center=(lo+hi)/2;span=max(hi-lo)
focus=json.loads(Path(args[3]).read_text()) if len(args)>3 else None
if focus: center=Vector(focus['center']);span=float(focus['span'])
# Scale whole scene into normalized coordinates; geometry itself is not modified.
obj.location-=center;obj.scale/=span;obj.location/=span
mat=bpy.data.materials.new('Warm mineral');mat.diffuse_color=(.54,.49,.40,1);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.54,.49,.40,1);bs.inputs['Roughness'].default_value=.85;obj.data.materials.clear();obj.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.color=(.055,.055,.055);scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.06,.07,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35
for name,loc,power,size in [('Key',(-1.5,2.5,2.8),260,1.6),('Fill',(2.,1.2,1.),55,1.8),('Rim',(0.,-2.,2.5),170,1.2)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=loc;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=1.3
for name,pos in [('front',(0,4,0)),('oblique',(-2.5,4,1.55)),('detail',(-1.4,3,.8)),('micro',(-1.4,3,.8)),('column',(0,4,0))]:
 if name=='micro' and not focus:continue
 if len(args)>2 and name not in args[2].split(','):continue
 target=Vector((0,0,0));camdata.ortho_scale=1.3
 scene.render.resolution_x=1200;scene.render.resolution_y=1200
 if name=='column':target=Vector((.3125,0,-.125));camdata.ortho_scale=.9;scene.render.resolution_x=600
 if name=='detail':target=Vector((.2,0,.17));camdata.ortho_scale=.62
 if name=='micro':target=Vector(focus['target']);camdata.ortho_scale=float(focus['ortho_scale'])
 cam.location=Vector(pos)+target;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
(out/('render_micro.json' if focus else 'render.json')).write_text(json.dumps(dict(source=str(meshfile),engine='Blender Cycles',samples=40,geometry_changes=False,version=bpy.app.version_string,shared_camera=focus),indent=2))
