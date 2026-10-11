"""Unchanged shared CHESHIRE rendering recipe, copied for portability."""

import bpy,json

from pathlib import Path

from mathutils import Vector

def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')

def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob

def export(ob,folder,stem='body',obj=False):
 active(ob)
 bpy.ops.wm.ply_export(filepath=str(folder/(stem+'.ply')),export_selected_objects=True,apply_modifiers=False,export_normals=False,export_uv=False,export_colors='NONE',forward_axis='Y',up_axis='Z')
 if obj:
  bpy.ops.wm.obj_export(filepath=str(folder/(stem+'.obj')),export_selected_objects=True,apply_modifiers=False,export_normals=False,export_uv=False,export_materials=False,forward_axis='Y',up_axis='Z')

def material(ob):
 mat=bpy.data.materials.get('Untextured mineral')
 if not mat:
  mat=bpy.data.materials.new('Untextured mineral');mat.use_nodes=True
  bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.50,.47,.41,1);bs.inputs['Roughness'].default_value=.84
 ob.data.materials.clear();ob.data.materials.append(mat)
 # Flat geometric normals consistently. No displacement/bump/normal maps.
 for p in ob.data.polygons:p.use_smooth=False

def setup_scene(resolution=1000,samples=24):
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=samples;scene.cycles.use_denoising=True
 scene.render.resolution_x=resolution;scene.render.resolution_y=resolution;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
 scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.055,.063,.075,1);bg.inputs[1].default_value=.4
 focus=Vector((0,0,6.5))
 for name,loc,power,size in [('Key',(-20,25,32),36000,17),('Fill',(24,13,15),8500,18),('Rim',(0,-23,29),26000,13)]:
  data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
  light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=loc;light.rotation_euler=(focus-light.location).to_track_quat('-Z','Y').to_euler()
 data=bpy.data.cameras.new('Shared orthographic camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.ortho_scale=17.5
 return scene,cam

VIEWS={'front':(0,38,6.5),'oblique':(-25,36,21),'side':(-38,0,6.5),'rear':(0,-38,6.5)}

def render(folder,views,resolution=1000,samples=24):
 scene,cam=setup_scene(resolution,samples)
 for name in views:
  cam.location=VIEWS[name];target=Vector((0,0,6.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  scene.render.filepath=str(folder/(name+'.png'));bpy.ops.render.render(write_still=True)
 dump(folder/'render_receipt.json',dict(engine='Blender Cycles',version=bpy.app.version_string,samples=samples,resolution=[resolution,resolution],camera_target=[0,0,6.5],orthographic_scale=17.5,positions={v:VIEWS[v] for v in views},geometry_modifiers=[],material='Uniform untextured mineral; flat geometric normals',rendered_objects=[o.name for o in scene.objects if o.type=='MESH'],source='Actual exported/saved mesh only; no AI generated imagery, added decoration, ground, or image retouching'))
