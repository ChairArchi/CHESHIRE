"""Apply Blender's existing Simple Deform; no smoothing or topology changes."""
import bpy,sys,json
from pathlib import Path
source,target=map(Path,sys.argv[sys.argv.index('--')+1:]);j=json.loads(source.read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
me=bpy.data.meshes.new('CurrentTarget');me.from_pydata(j['vertices'],[],j['faces']);me.update()
ob=bpy.data.objects.new('CurrentTarget',me);bpy.context.collection.objects.link(ob)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
origin=bpy.data.objects.new('MeasuredSupportAxis',None);bpy.context.collection.objects.link(origin);origin.location=j['origin']
vg=ob.vertex_groups.new(name='SupportTransitionWeight')
for i,w in enumerate(j['weights']):vg.add([i],float(w),'REPLACE')
modifier=ob.modifiers.new('MeasuredSupportTwist','SIMPLE_DEFORM')
modifier.deform_method='TWIST';modifier.deform_axis='Z';modifier.angle=j['angle'];modifier.origin=origin;modifier.vertex_group=vg.name
bpy.ops.object.modifier_apply(modifier=modifier.name)
target.write_text(json.dumps(dict(vertices=[list(v.co) for v in ob.data.vertices],faces=[list(f.vertices) for f in ob.data.polygons],operator='Blender Simple Deform / TWIST',blender=bpy.app.version_string,topology_changed=False,smoothing=False)))
