"""Blender subdivision with measured edge creases, applied headlessly."""
import bpy,sys,json
from pathlib import Path
source,target=map(Path,sys.argv[sys.argv.index('--')+1:]);j=json.loads(source.read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
me=bpy.data.meshes.new('CurrentFoldedTarget');me.from_pydata(j['vertices'],[],j['faces']);me.update()
ob=bpy.data.objects.new('CurrentFoldedTarget',me);bpy.context.collection.objects.link(ob)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
weights={tuple(sorted(e)):w for e,w in zip(j['edges'],j['creases'])}
attribute=me.attributes.new('crease_edge','FLOAT','EDGE')
for edge in me.edges:attribute.data[edge.index].value=weights[tuple(sorted(edge.vertices))]
modifier=ob.modifiers.new('PreserveMeasuredCreases','SUBSURF');modifier.subdivision_type=j.get('sampling','CATMULL_CLARK')
modifier.levels=1;modifier.render_levels=1;modifier.quality=4;modifier.use_limit_surface=False
bpy.ops.object.modifier_apply(modifier=modifier.name)
target.write_text(json.dumps(dict(vertices=[list(v.co) for v in ob.data.vertices],faces=[list(f.vertices) for f in ob.data.polygons],operator='Blender Subdivision Surface / '+j.get('sampling','CATMULL_CLARK'),blender=bpy.app.version_string,levels=1,use_limit_surface=False)))
