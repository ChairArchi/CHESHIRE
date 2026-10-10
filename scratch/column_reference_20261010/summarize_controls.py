"""Measure saved controls and verify exports; no shape generation."""
import json, ast
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;O=R.parents[1]/'outputs/expansion_control_20261010'
result=json.loads((O/'measurements.json').read_text());exports={}
# Earlier completed export checks are retained; avoid repeating four expensive reloads.
logbytes=(O/'export_check.log').read_bytes()
logtext=logbytes.decode('utf-16' if logbytes.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8',errors='replace')
for line in logtext.splitlines():
 if line.startswith(tuple(result)):
  label,record=line.split(' ',1);exports[label]=ast.literal_eval(record)
folders={k:O/k for k in result};folders['hierarchy_G1_G8']=R/'published_column_hierarchy8_results/g08'
folders['regional_G5_G8']=R/'published_column_regional8_results/g08'
for name,p in folders.items():
 if name in exports:continue
 data=json.loads((p/'mesh.json').read_text());v=np.array(data['vertices']);tri=np.array([[f[0],f[j],f[j+1]] for f in data['faces'] for j in range(1,len(f)-1)])
 if name in ['hierarchy_G1_G8','regional_G5_G8']:
  im=Image.new('1',(600,1000));draw=ImageDraw.Draw(im);uv=np.column_stack([(v[:,0]+4.5)*600/9,(11-v[:,2])*1000/14])
  for f in tri:draw.polygon([tuple(t) for t in uv[f]],fill=1)
  im.save(O/(name+'_silhouette.png'))
  result[name]=dict(extents=np.ptp(v,axis=0).tolist(),silhouette_pixels=dict(front=int(np.asarray(im).sum())),config=str(R/('paper075_hierarchy_control_8.json' if name=='hierarchy_G1_G8' else 'paper075_regional_control_8.json')))
 checks={}
 for ext in ['obj','ply']:
  m=trimesh.load(p/('column.'+ext),force='mesh',process=False)
  check=dict(vertices=len(m.vertices),triangles=len(m.faces),finite=bool(np.isfinite(m.vertices).all()),watertight=bool(m.is_watertight),winding=bool(m.is_winding_consistent),zero_area_triangles=int((m.area_faces<=0).sum()),max_vertex_roundtrip_error=float(np.max(np.linalg.norm(m.vertices-v,axis=1))),faces_equal=bool(np.array_equal(m.faces,tri)))
  assert check['finite'] and check['watertight'] and check['winding'] and check['faces_equal'],check
  checks[ext]=check
 # Original float32 PLY is preserved; an explicit double-coordinate delivery is separate.
 exact=p/'column_double.ply'
 with exact.open('w') as fp:
  fp.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty double x\nproperty double y\nproperty double z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n'%(len(v),len(tri)))
  np.savetxt(fp,v,fmt='%.17g');np.savetxt(fp,np.column_stack([np.full(len(tri),3),tri]),fmt='%d')
 # Trimesh's ASCII loader creates millions of tiny arrays; use bounded NumPy parsing.
 with exact.open() as fp:
  while fp.readline().strip()!='end_header':pass
  rv=np.loadtxt(fp,max_rows=len(v));rf=np.loadtxt(fp,dtype=np.int64)[:,1:]
 m=trimesh.Trimesh(rv,rf,process=False)
 checks['double_ply']=dict(max_vertex_roundtrip_error=float(np.max(np.linalg.norm(m.vertices-v,axis=1))),zero_area_triangles=int((m.area_faces<=0).sum()),watertight=bool(m.is_watertight),winding=bool(m.is_winding_consistent))
 assert checks['double_ply']['zero_area_triangles']==0 and checks['double_ply']['max_vertex_roundtrip_error']==0
 exports[name]=checks;print(name,checks,flush=True)
for name,r in result.items():
 r['front_area_change_pct']=100*(r['silhouette_pixels']['front']/result['baseline']['silhouette_pixels']['front']-1)
 r['width_change_pct']=100*(r['extents'][0]/result['baseline']['extents'][0]-1)
(O/'final_measurements.json').write_text(json.dumps(result,indent=2));(O/'export_checks.json').write_text(json.dumps(exports,indent=2))
