"""Headless topology experiment; all operations use copies of the frozen target."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np

j=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());out=Path(j['output']);out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def obj(name,vertices,faces):
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def serial(ob):return dict(vertices=[list(v.co) for v in ob.data.vertices],faces=[list(f.vertices) for f in ob.data.polygons])
def save(ob,name):
 d=serial(ob);(out/(name+'.json')).write_text(json.dumps(d));active(ob)
 with (out/(name+'.obj')).open('w') as stream:
  stream.write('# Shared-index geometry; Z up, Y front; no shading-induced vertex splits\n')
  for v in d['vertices']:stream.write('v '+' '.join(format(x,'.17g') for x in v)+'\n')
  for q in d['faces']:stream.write('f '+' '.join(str(x+1) for x in q)+'\n')
 return d
def apply(ob,mod):active(ob);bpy.ops.object.modifier_apply(modifier=mod.name)
target=json.loads(Path(j['target']).read_text());high=obj('FrozenTargetCopy',target['vertices'],target['faces'])
if j.get('method')=='frozen':save(high,'result');sys.exit(0)
if j['action']=='prepare':
 mod=high.modifiers.new('TopologyScale','DECIMATE');mod.decimate_type='UNSUBDIV';mod.iterations=j['unsubdivide_iterations'];apply(high,mod)
 d=save(high,'coarse');(out/'prepare.json').write_text(json.dumps(dict(operator='Blender DECIMATE / UNSUBDIV',iterations=j['unsubdivide_iterations'],source_faces=len(target['faces']),result_faces=len(d['faces']),face_sizes=sorted(set(map(len,d['faces'])))),indent=2))
else:
 bvh=BVHTree.FromPolygons([Vector(v) for v in target['vertices']],target['faces'],all_triangles=False)
 if j['action']=='audit':
  report={}
  for file in j['meshes']:
   data=json.loads(Path(file).read_text());vertices=data['vertices'];ids=np.linspace(0,len(vertices)-1,min(20000,len(vertices)),dtype=int)
   distances=[bvh.find_nearest(Vector(vertices[i]))[3] for i in ids]
   face_ids=np.linspace(0,len(data['faces'])-1,min(20000,len(data['faces'])),dtype=int)
   interior=[];edge=[]
   for idx in face_ids:
    q=data['faces'][idx];points=[Vector(vertices[k]) for k in q]
    for k in range(1,len(points)-1):
     interior.append(bvh.find_nearest((points[0]+points[k]+points[k+1])/3)[3])
    edge.append(bvh.find_nearest((points[0]+points[1])/2)[3])
   report[file]=dict(samples=len(ids),distance_quantiles=np.quantile(distances,[0,.5,.95,1]).tolist(),triangle_interior_distance_quantiles=np.quantile(interior,[0,.5,.95,1]).tolist(),edge_midpoint_distance_quantiles=np.quantile(edge,[0,.5,.95,1]).tolist(),scope='Deterministic samples against frozen target triangles, before solidify offsets. Interior distances detect bridging missed by vertex-only checks; nearest distance does not certify feature correspondence.')
  (out/'surface_audit.json').write_text(json.dumps(report,indent=2));sys.exit(0)
 data=json.loads(Path(j['patch']).read_text());base=obj('ConnectedPatch',data['vertices'],data['faces'])
 if j['method']=='target':save(base,'result');sys.exit(0)
 variable=j['method']=='tissue_variable'
 if j['method'] in ('tissue','tissue_round','tissue_collar','tissue_variable'):
  sys.path.insert(0,j['external']);import tissue;tissue.register()
  # A simple open square frame can share its outer edges with its neighbors.
  # A closed cube cell cannot acquire that interface merely through overlap.
  a=.19;outer=[(0,0,0),(1,0,0),(1,1,0),(0,1,0)];inner=[(a,a,0),(1-a,a,0),(1-a,1-a,0),(a,1-a,0)]
  rings=[[i,(i+1)%4,4+(i+1)%4,4+i] for i in range(4)]
  cell=obj('SimpleOpenFrame',outer+inner,rings)
  if variable:
   # Current normal variation controls the INNER shape only; shared ports stay fixed.
   normals=np.array([list(p.normal) for p in base.data.polygons]);acc=np.zeros((len(base.data.vertices),3));count=np.zeros(len(acc))
   for face,n in zip(data['faces'],normals):
    for vertex in face:acc[vertex]+=n;count[vertex]+=1
   variation=1-np.linalg.norm(acc,axis=1)/np.maximum(count,1)
   feature=np.clip(variation/max(float(np.quantile(variation,.9)),1e-9),0,1)
   dense=.2+.75*(1-feature)
   group=base.vertex_groups.new(name='Dense')
   for idx,weight in enumerate(dense):group.add([idx],float(weight),'REPLACE')
   cell.shape_key_add(name='Basis');key=cell.shape_key_add(name='Dense');key.value=1.
   for idx,(x,y) in enumerate([(.43,.43),(.57,.43),(.57,.57),(.43,.57)],start=4):key.data[idx].co=(x,y,0)
   (out/'density_field.json').write_text(json.dumps(dict(weights=dense.tolist(),normal_variation=variation.tolist(),rule='Quiet regions tighten the input window; high normal variation keeps stronger separation; outer seam ports remain fixed')))
  (out/'input_component.json').write_text(json.dumps(dict(vertices=outer+inner,faces=rings),indent=2))
  collar=j['method']=='tissue_collar'
  collar_count=0
  if collar:
   counts={}
   for q in data['faces']:
    for k in range(len(q)):
     key=tuple(sorted((q[k],q[(k+1)%len(q)])));counts[key]=counts.get(key,0)+1
   for face,q in zip(base.data.polygons,data['faces']):face.select=not any(counts[tuple(sorted((q[k],q[(k+1)%len(q)])))]==1 for k in range(len(q)))
   collar_count=sum(not face.select for face in base.data.polygons)
  active(base);cell.select_set(True)
  status=bpy.ops.object.tissue_tessellate(generator=base.name,component=cell.name,component_mode='OBJECT',mode='LOCAL',fill_mode='QUAD',combine_mode='UNUSED' if collar else 'LAST',iterations=1,scale_mode='CONSTANT',zscale=1.,merge=True,merge_thres=1e-6,merge_open_edges_only=True,gen_modifiers=False,com_modifiers=False,bool_selection=collar,bool_shapekeys=variable,bool_vertex_group=variable,rotation_mode='DEFAULT',normals_mode='VERTS')
  if status!={'FINISHED'}:raise RuntimeError(status)
  network=bpy.context.object;operation='Actual Tissue QUAD / '+('UNUSED, one-ring target collar' if collar else 'LAST')+' / boundary merge'
  if variable:
   active(network);bpy.ops.object.convert(target='MESH');network=bpy.context.object;operation+=' / Dense shape key driven by current normal-variation vertex group'
 elif j['method']=='frame_strips':
  sys.path.insert(0,str(Path(__file__).resolve().parent));from strip_network import build
  vertices,faces,relief,lengths=build(data)
  network=obj('ConnectedFaceStrips',vertices,faces);attr=network.data.attributes.new('bundle_relief','FLOAT','POINT')
  for item,value in zip(attr.data,relief):item.value=value
  (out/'strip_groups.json').write_text(json.dumps(dict(face_chain_lengths=lengths,rule='Up to three edge-adjacent quads, actual long-axis alignment and normal agreement. Shared boundary vertices preserved.')))
  operation='Adjacent-face strip aggregation, shared Frame/Window and raised rail crowns; not Tissue tessellation'
 else:
  # Shared outer vertex indices guarantee edge adjacency across neighboring faces.
  vertices=[list(v) for v in data['vertices']];faces=[];relief=[0.]*len(vertices)
  for q in data['faces']:
   if len(q)!=4:raise ValueError('Quad topology required for frame comparison')
   if j.get('seam_collar',0)>0 and min(abs(vertices[k][0]) for k in q)<j['seam_collar']:
    faces.append(q);continue
   p=np.array([vertices[v] for v in q]);lu=(np.linalg.norm(p[1]-p[0])+np.linalg.norm(p[2]-p[3]))/2;lv=(np.linalg.norm(p[3]-p[0])+np.linalg.norm(p[2]-p[1]))/2
   ratio=max(lu,lv)/max(min(lu,lv),1e-9);strong=.19+.075*min(max(ratio-1,0),1)
   bundle=j['method']=='frame_bundle'
   u,v=((.12,.43) if lu>lv else (.43,.12)) if bundle else ((.12,strong) if lu>lv else (strong,.12))
   if bundle:
    crest=len(vertices)
    for x,y in [(u*.5,v*.5),(1-u*.5,v*.5),(1-u*.5,1-v*.5),(u*.5,1-v*.5)]:
     vertices.append(((1-x)*(1-y)*p[0]+x*(1-y)*p[1]+x*y*p[2]+(1-x)*y*p[3]).tolist());relief.append(min(.004,max(.0015,min(lu,lv)*.35)))
    faces.extend([[q[i],q[(i+1)%4],crest+(i+1)%4,crest+i] for i in range(4)])
   start=len(vertices)
   for x,y in [(u,v),(1-u,v),(1-u,1-v),(u,1-v)]:
    vertices.append(((1-x)*(1-y)*p[0]+x*(1-y)*p[1]+x*y*p[2]+(1-x)*y*p[3]).tolist());relief.append(0.)
   rim=[crest+i for i in range(4)] if bundle else q
   faces.extend([[rim[i],rim[(i+1)%4],start+(i+1)%4,start+i] for i in range(4)])
  network=obj('SharedTopologyFrame',vertices,faces);operation='Quad Frame/Window with shared indices; aspect-aligned rails'
  if j['method']=='frame_bundle':
   attr=network.data.attributes.new('bundle_relief','FLOAT','POINT')
   for item,value in zip(attr.data,relief):item.value=value
   operation+='; elongated windows and raised rail crowns with interpolated normal relief'
 # Refine the network only; never smooth the target itself. Reproject the new
 # samples onto the actual frozen target before giving the connected sheet depth.
 rounded=j['method'] in ('frame_round','frame_bundle','frame_strips','tissue_round','tissue_collar','tissue_variable')
 crease_count=0
 if rounded and j.get('protect_folds',False):
  bm=bmesh.new();bm.from_mesh(network.data);bm.normal_update();bm.edges.ensure_lookup_table()
  weights={tuple(sorted(v.index for v in edge.verts)):max(0.,min(1.,(math.degrees(edge.calc_face_angle(0.))-12.)/26.)) if len(edge.link_faces)==2 else 0. for edge in bm.edges}
  bm.free();attribute=network.data.attributes.new('crease_edge','FLOAT','EDGE')
  for edge in network.data.edges:
   weight=weights[tuple(sorted(edge.vertices))];attribute.data[edge.index].value=weight;crease_count+=weight>0
 mod=network.modifiers.new('NetworkSampling','SUBSURF');mod.subdivision_type='CATMULL_CLARK' if rounded else 'SIMPLE';mod.levels=j.get('refinement',1);mod.render_levels=mod.levels;mod.use_limit_surface=False;apply(network,mod)
 errors=[]
 for vertex in network.data.vertices:
  point,normal,index,distance=bvh.find_nearest(vertex.co)
  if point is None:raise ValueError('Surface projection failed')
  errors.append(distance);vertex.co=point
  if j['method'] in ('frame_bundle','frame_strips'):vertex.co+=normal*network.data.attributes['bundle_relief'].data[vertex.index].value
 network.data.update()
 if j.get('bilateral',False):
  sys.path.insert(0,str(Path(__file__).resolve().parent));from mirror_surface import reflect
  raw=serial(network);vertices,faces,partners=reflect(raw['vertices'],raw['faces']);network=obj('BilateralNetwork',vertices,faces)
 save(network,'midsurface')
 thickness=j.get('thickness',.0012)
 mod=network.modifiers.new('NetworkThicken','SOLIDIFY');mod.thickness=thickness;mod.offset=0.;mod.use_even_offset=False;mod.use_quality_normals=True;apply(network,mod)
 if j.get('bilateral',False):
  # SOLIDIFY's quality-normal weighting on non-planar quads can produce small
  # left/right offset differences. Constrain corresponding layers, not topology.
  n=len(partners)
  if len(network.data.vertices)!=2*n:raise ValueError('Unexpected Solidify vertex correspondence')
  for layer in [0,n]:
   for i,k in enumerate(partners):
    if i>k:continue
    a=network.data.vertices[layer+i].co.copy();b=network.data.vertices[layer+k].co.copy();b.x*=-1;p=(a+b)*.5
    if i==k:p.x=0
    network.data.vertices[layer+i].co=p;p.x*=-1;network.data.vertices[layer+k].co=p
  network.data.update()
 save(network,'result')
 (out/'operations.json').write_text(json.dumps(dict(operator=operation,subdivision=('CATMULL_CLARK' if rounded else 'SIMPLE')+', then closest-point projection to frozen target',refinement=j.get('refinement',1),projection_displacement_quantiles=np.quantile(errors,[0,.5,.95,1]).tolist(),thicken='Blender SOLIDIFY; centered normal offsets; even-offset disabled',thickness=thickness,source_target_in_output=False,original_target_modified=False,target_boundary='Geometric contact at projected midsurface only; not welded to original target',blender=bpy.app.version_string),indent=2))
 metadata=json.loads((out/'operations.json').read_text());metadata.update(fold_protection=j.get('protect_folds',False),creased_edges=crease_count,bilateral=j.get('bilateral',False));(out/'operations.json').write_text(json.dumps(metadata,indent=2))
 if j['method']=='frame_bundle':
  metadata.update(intentional_normal_relief=True,seam_collar_width=j.get('seam_collar',0),relief_rule='Shared outer seams remain at zero relief; rail crowns use min(0.004,max(0.0015,0.35*short_face_edge_length)), interpolated through subdivision and applied after projection.',subdivision=metadata['subdivision']+', then interpolated crown relief along target normals')
  (out/'operations.json').write_text(json.dumps(metadata,indent=2))
 if j['method']=='tissue_collar':
  meta=json.loads((out/'operations.json').read_text());meta.update(retained_collar_faces=collar_count,target_boundary='Network is welded to one ring of retained coarse target faces, then subdivided and reprojected together. No weld to the separate full original TARGET object.');(out/'operations.json').write_text(json.dumps(meta,indent=2))
