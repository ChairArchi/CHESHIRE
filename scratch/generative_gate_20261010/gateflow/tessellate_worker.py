"""Tissue component-to-target mapping, executed in headless Blender."""
import bpy,sys,json
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:];source,target=map(Path,args);j=json.loads(source.read_text());sys.path.insert(0,j['external_root']);import tissue;tissue.register()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mesh_object(name,vertices,faces):
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
base=mesh_object('GateTarget',j['vertices'],j['faces']);cell=mesh_object('PorousInput',j['component']['vertices'],j['component']['faces'])
coords=[v.co.copy() for v in cell.data.vertices];low=[min(v[k] for v in coords) for k in range(3)];high=[max(v[k] for v in coords) for k in range(3)]
for v in cell.data.vertices:
    for k in range(2):v.co[k]=.5+j['overlap']*j['mapping'].get('xy_scale',[1.,1.])[k]*((v.co[k]-low[k])/(high[k]-low[k])-.5)
    v.co.z=j['mapping'].get('z_factor',1.)*(v.co.z-(high[2]+low[2])*.5+j.get('offset',0.)*.5*(high[2]-low[2]))/max(high[0]-low[0],high[1]-low[1])
cell.data.update()
vg=base.vertex_groups.new(name='CurrentGeometryDepth')
for i,value in enumerate(j['weights']):vg.add([i],float(value),'REPLACE')
rotation=base.vertex_groups.new(name='OpeningFlow')
for i,value in enumerate(j.get('rotation_weights',j['weights'])):rotation.add([i],float(value),'REPLACE')
for face,selected in zip(base.data.polygons,j['selected']):face.select=selected
base.select_set(True);cell.select_set(True);bpy.context.view_layer.objects.active=base
combine=j.get('combine_mode','LAST')
if combine not in ('LAST','UNUSED','ALL'):raise ValueError('Unsupported Tissue combine mode')
if j['keep_target'] and combine!='LAST':raise ValueError('Appending full target requires LAST, to avoid double inclusion')
status=bpy.ops.object.tissue_tessellate(generator=base.name,component=cell.name,component_mode='OBJECT',mode='LOCAL',fill_mode='QUAD',combine_mode=combine,iterations=1,scale_mode='ADAPTIVE',zscale=j['depth'],offset=j.get('offset',0.),rotation_shift=j.get('rotation_shift',0),merge=False,gen_modifiers=False,com_modifiers=False,bool_selection=True,rotation_mode='WEIGHT',vertex_group_rotation='OpeningFlow',bool_vertex_group=True,vertex_group_thickness='CurrentGeometryDepth',vertex_group_thickness_factor=.5,normals_mode='VERTS')
if status!={'FINISHED'}:raise RuntimeError(str(status))
out=bpy.context.object;me=out.data;me.calc_loop_triangles()
result=dict(vertices=[list(v.co) for v in me.vertices],faces=[list(f.vertices) for f in me.polygons],operator='object.tissue_tessellate',blender=bpy.app.version_string,tissue_version=list(tissue.bl_info['version']),target_faces=len(base.data.polygons),component_faces=len(cell.data.polygons),scale_mode='ADAPTIVE',depth_group='CurrentGeometryDepth',merge=False)
result.update(combine_mode=combine,fill_mode='QUAD',iterations=1)
if j['keep_target']:
 n=len(result['vertices']);result['vertices']+=j['vertices'];result['faces']+=[[int(v)+n for v in face] for face in j['faces']]
 result['retained_target_vertex_offset']=n
 result['retained_target_faces']=len(j['faces'])
 result['assembly']='Full target plus projected component shells; no Boolean union claimed'
target.write_text(json.dumps(result))
