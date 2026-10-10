"""Isolated background Blender worker. Calls upstream Tissue, not a replacement."""
import sys,json,bpy,numpy as np
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];source,target=map(Path,args)
j=json.loads(source.read_text());sys.path.insert(0,j['external_root']);import tissue
tissue.register()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new('CurrentGeneration');mesh.from_pydata(j['vertices'],[],j['faces']);mesh.update()
ob=bpy.data.objects.new('CurrentGeneration',mesh);bpy.context.collection.objects.link(ob);ob.select_set(True);bpy.context.view_layer.objects.active=ob
for name,values in [('cheshire_thickness',j['weights']),('cheshire_selection',j['selection'])]:
    group=ob.vertex_groups.new(name=name)
    for i,v in enumerate(values):group.add([i],float(v),'REPLACE')
status=bpy.ops.object.polyhedral_wireframe(mode='WIREFRAME',thickness=j['thickness'],segments=1,dissolve='NONE',proportional_segments=False)
if status!={'FINISHED'}:raise RuntimeError(str(status))
out=bpy.context.object;props=out.tissue_polyhedra
# Set properties with update lock, then run the actual update once. The create
# operator doesn't copy its vertex-group options into properties upstream.
out.tissue.bool_lock=True
props.vertex_group_thickness='cheshire_thickness';props.vertex_group_thickness_factor=.5
props.selective_wireframe=j.get('selective','NONE');props.vertex_group_selective='cheshire_selection';props.vertex_group_selective_threshold=.45
props.thicken_all=True;out.tissue.bool_lock=False
status=bpy.ops.object.tissue_update_polyhedra()
if status!={'FINISHED'}:raise RuntimeError(str(status))
me=out.data;me.calc_loop_triangles()
result=dict(vertices=[list(v.co) for v in me.vertices],faces=[list(f.vertices) for f in me.polygons],blender=bpy.app.version_string,tissue_version=list(tissue.bl_info['version']),status='FINISHED',operator='object.polyhedral_wireframe + object.tissue_update_polyhedra')
target.write_text(json.dumps(result))
