"""Render the saved stitched mixed surface once; no geometry modifiers or LOD."""
from pathlib import Path
import sys,json,argparse,importlib.util,time,shutil
sys.dont_write_bytecode=True
import bpy,numpy as np
BASE=Path(r'E:\CHESHIRE_DATA\experiments\fold_aligned_mandel_20261015')
spec=importlib.util.spec_from_file_location('synthesis_preserved_studio',BASE/'render_spine_review_v2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
render,fast,digest,write=m.render,m.fast,m.digest,m.write
ah=render.scaffold.array_hash
PALETTE=[('기존 구조',(.30,.32,.35,1)),('완만한 SOURCE',(.20,.55,.90,1)),
 ('약한 주름',(.025,.48,.40,1)),('강한 주름',(.015,.09,.30,1)),('둥근 융기',(.75,.46,.035,1)),
 ('복합 SOURCE',(.55,.07,.34,1)),('주요 흐름 보호',(.08,.65,.12,1)),
 ('반사 원형의 막힌 요철',(.73,.12,.42,1)),('깊은 막힌 홈',(.02,.70,.68,1)),('겹친 막과 접힘',(.95,.29,.035,1))]

def disk(root,name,shape,dtype):return np.lib.format.open_memmap(root/(name+'.npy'),mode='w+',shape=shape,dtype=dtype)
def get(record):
 if digest(record['path'])!=record['sha256']:raise ValueError('Saved native array changed.')
 return np.load(record['path'],mmap_mode='r',allow_pickle=False)
def signature(obj,work,prefix,expected):
 mesh=obj.data;x=disk(work,prefix+'_xyz',(len(mesh.vertices),3),np.float32)
 loops=disk(work,prefix+'_loops',(len(mesh.loops),),np.int32)
 mesh.vertices.foreach_get('co',x.ravel());mesh.loops.foreach_get('vertex_index',loops)
 if ah(x)!=expected['xyz_float32_sha256'] or ah(loops)!=expected['loops_int32_sha256']:raise ValueError('Every displayed coordinate/index must match the saved mixed surface.')
 if len(mesh.edges) or len(obj.modifiers):raise ValueError('Unexpected edge graph or modifier.')
 return dict(vertices=len(mesh.vertices),polygons=len(mesh.polygons),loops=len(mesh.loops),
  xyz_float32_sha256=ah(x),loops_int32_sha256=ah(loops),edges=0,modifiers=0)
def gpu(scene):
 prefs=bpy.context.preferences.addons['cycles'].preferences
 for backend in ('OPTIX','CUDA'):
  try:prefs.compute_device_type=backend;prefs.get_devices()
  except Exception:continue
  found=[d for d in prefs.devices if d.type==backend]
  if found:
   for d in prefs.devices:d.use=d.type==backend
   scene.cycles.device='GPU';return dict(backend=backend,devices=[d.name for d in found])
 raise RuntimeError('No verified render GPU available.')
def shading(obj,smooth):
 mesh=obj.data;mesh.polygons.foreach_set('use_smooth',np.full(len(mesh.polygons),smooth,bool))
 mesh.update_tag();obj.update_tag(refresh={'DATA'});bpy.context.view_layer.update()
def color_materials(obj,tags):
 obj.data.materials.clear()
 for i,(name,color) in enumerate(PALETTE):
  mat=bpy.data.materials.new(str(i)+': '+name);mat.use_nodes=True;n=mat.node_tree.nodes;n.clear();l=mat.node_tree.links
  out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.8
  em=n.new('ShaderNodeEmission');em.inputs['Color'].default_value=color;em.inputs['Strength'].default_value=.8
  mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=.20;l.new(bs.outputs['BSDF'],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs[0]);obj.data.materials.append(mat)
 obj.data.polygons.foreach_set('material_index',tags)

def main(root,device_mode='auto',review_name='REVIEW',detail_view=None):
 started=time.perf_counter();meta_path=root/'SYNTHESIS_RECEIPT.json';checksum=digest(meta_path)
 meta=json.loads(meta_path.read_text(encoding='utf-8'));arrays=meta['assembly']['arrays']
 detail_binding=None;detail=None
 if detail_view is not None:
  detail=json.loads(detail_view.read_text(encoding='utf-8'))
  if Path(detail['master_receipt']['path']).resolve()!=meta_path.resolve() or detail['master_receipt']['sha256']!=checksum:
   raise ValueError('Detail camera must bind this actual final master receipt.')
  if detail['patch_index']['sha256']!=meta['patches']['sha256'] or detail['master_xyz']!=arrays['XYZ']:
   raise ValueError('Detail camera uses another patch selection or master geometry.')
  if digest(detail['patch_index']['path'])!=detail['patch_index']['sha256'] or digest(detail['accepted_patch']['path'])!=detail['accepted_patch']['sha256']:
   raise ValueError('Detail camera accepted source patch changed.')
  index=json.loads(Path(detail['patch_index']['path']).read_text(encoding='utf-8'))
  if not any(row['sha256']==detail['accepted_patch']['sha256'] and row['site_id']==detail['site_id'] for row in index['patches']):
   raise ValueError('Detail camera must show an actual accepted final patch.')
  detail_binding=dict(path=str(detail_view),sha256=digest(detail_view),record=detail)
 if Path(review_name).name!=review_name or review_name in ('.','..'):raise ValueError('Review name must be one folder name.')
 work=root/('render_cache' if review_name=='REVIEW' else review_name+'_cache');work.mkdir();out=root/review_name;out.mkdir()
 snapshot=out/'source_snapshot';snapshot.mkdir();shutil.copyfile(__file__,snapshot/Path(__file__).name)
 if detail_view is not None:shutil.copyfile(detail_view,snapshot/detail_view.name)
 xyz=get(arrays['XYZ']);q=get(arrays['QUADS']);t=get(arrays['TRIANGLES'])
 nq,nt,nv=len(q),len(t),len(xyz);nf=nq+nt;nl=4*nq+3*nt
 dx=disk(work,'display_xyz',xyz.shape,np.float32);loops=disk(work,'display_loops',(nl,),np.int32)
 starts=disk(work,'loop_starts',(nf,),np.int32);totals=disk(work,'loop_totals',(nf,),np.int32)
 for a in range(0,nv,131072):dx[a:a+131072]=xyz[a:a+131072]
 for a in range(0,nq,131072):
  b=min(a+131072,nq);loops[4*a:4*b]=q[a:b].ravel();starts[a:b]=4*np.arange(a,b,dtype=np.int32);totals[a:b]=4
 for a in range(0,nt,131072):
  b=min(a+131072,nt);loops[4*nq+3*a:4*nq+3*b]=t[a:b].ravel();starts[nq+a:nq+b]=4*nq+3*np.arange(a,b,dtype=np.int32);totals[nq+a:nq+b]=3
 expected=dict(xyz_float32_sha256=ah(dx),loops_int32_sha256=ah(loops))
 binding=render.source_binding();shared=render.scaffold.setup_scene()
 print('LOAD_SAVED_STITCHED_MIXED_SURFACE',nv,nq,nt,flush=True)
 mesh=bpy.data.meshes.new('Original quads and closed-backed deep recess triangles')
 mesh.vertices.add(nv);mesh.vertices.foreach_set('co',dx.ravel());mesh.loops.add(nl);mesh.loops.foreach_set('vertex_index',loops)
 mesh.polygons.add(nf);mesh.polygons.foreach_set('loop_start',starts);mesh.polygons.foreach_set('loop_total',totals)
 obj=bpy.data.objects.new('CHESHIRE blind recess synthesis',mesh);bpy.context.collection.objects.link(obj)
 fast.assign_original_material(obj,shared);fast.set_flat_flags(obj)
 scene,camera=shared.setup_scene(900,24)
 if device_mode=='cpu':
  scene.cycles.device='CPU';device=dict(backend='CPU',devices=['CPU'],explicit_fallback=True)
 else:device=gpu(scene)
 before=signature(obj,work,'before',expected)
 stages={};views=dict(binding['views'])
 if detail is not None:views[detail['view_name']]=(detail['position'],detail['target'],detail['scale'])
 studio_views=['front','body_oblique','close_oblique']
 color_views=['front','body_oblique']
 if detail is not None:studio_views.append(detail['view_name']);color_views.append(detail['view_name'])
 av,imgs=render.scaffold.render_views(scene,camera,{'close_oblique':views['close_oblique']},out/'flat_geometry_check')
 stages['flat_geometry_check']=dict(actual_views=av,images=imgs,all_flat=True)
 print('FLAT_ACTUAL_GEOMETRY_READY',flush=True)
 # Display normal interpolation alone is changed for the final studio views.
 # The source geometry, connectivity, relief and topology remain identical.
 shading(obj,True)
 scene.render.resolution_x=1800;scene.render.resolution_y=1800;scene.cycles.samples=48
 scene.render.use_persistent_data=True
 bs=next(n for n in obj.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(.72,.70,.66,1);bs.inputs['Roughness'].default_value=.62
 av,imgs=render.scaffold.render_views(scene,camera,{v:views[v] for v in studio_views},out/'studio')
 stages['studio']=dict(actual_views=av,images=imgs,resolution=[1800,1800],samples=48,smooth_normal_interpolation=True,geometry_changed=False)
 print('WHOLE_STUDIO_VIEWS_READY',flush=True)
 tags=disk(work,'material_indices',(nf,),np.int32);qc=get(meta['color']['quad_classes']);tc=get(meta['color']['triangle_classes'])
 tags[:nq]=qc;tags[nq:]=tc
 if tags.min()<0 or tags.max()>=len(PALETTE):raise ValueError('Unexpected material category.')
 color_materials(obj,tags);shading(obj,False)
 scene.cycles.samples=16;scene.view_settings.exposure=-.4
 scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25
 for name,power in (('Key',16000),('Fill',3000),('Rim',6000)):bpy.data.lights[name].energy=power
 av,imgs=render.scaffold.render_views(scene,camera,{v:views[v] for v in color_views},out/'color')
 stages['color']=dict(actual_views=av,images=imgs,resolution=[1800,1800],samples=16,all_flat=True,
  palette=[dict(index=i,label_ko=name,rgba=color) for i,(name,color) in enumerate(PALETTE)],category_polygon_counts=np.bincount(tags,minlength=len(PALETTE)).tolist())
 after=signature(obj,work,'after',expected)
 if after!=before or digest(meta_path)!=checksum:raise ValueError('Saved/display geometry changed during rendering.')
 if detail_binding is not None and digest(detail_view)!=detail_binding['sha256']:raise ValueError('Detail camera input changed during rendering.')
 flags=np.empty(nf,np.int32);mesh.polygons.foreach_get('material_index',flags)
 if ah(flags)!=ah(tags):raise ValueError('Actual color indices changed.')
 write(out/'RENDER_RECEIPT.json',dict(kind='SAME_SAVED_FULL_MIXED_NATIVE_BLIND_RECESS_SYNTHESIS_RENDER',
  source_receipt=dict(path=str(meta_path),sha256=checksum),stages=stages,native_counts=meta['assembly']['counts'],
  accepted_feature_detail_camera=detail_binding,all_views_use_same_whole_saved_geometry=True,
  display_before=before,display_after=after,render_device=device,geometry_changed=False,
  native_loaded_once=True,decimation=False,geometry_modifiers=False,normal_maps=False,
  studio_normal_interpolation_is_display_only=True,deep_recesses_are_saved_3D_geometry=True,
  apparent_holes_have_continuous_closed_backskin=True,through_ornament_handles=False,
  renderer_sha256=digest(__file__),version=bpy.app.version_string,elapsed_seconds=time.perf_counter()-started))
 print('SYNTHESIS_RENDER_COMPLETE',time.perf_counter()-started,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
 p.add_argument('--device',choices=('auto','cpu'),default='auto');p.add_argument('--review-name',default='REVIEW')
 p.add_argument('--detail-view',type=Path)
 a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);main(a.root,a.device,a.review_name,a.detail_view)
