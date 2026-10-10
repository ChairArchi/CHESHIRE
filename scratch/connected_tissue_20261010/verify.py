"""Verify actual artifacts, shared topology, projection, and immutable inputs."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
from scipy.spatial import cKDTree
import run
ROOT=run.ROOT
report={'runs':{},'limitations':['No global self-intersection proof. Closed topology alone is not fabrication certification.','Wide surface replaces the front region as a separate connected shell; not welded to the full original gate.']}
requested=set(sys.argv[1:])
if requested and (ROOT/'verification.json').exists():report=json.loads((ROOT/'verification.json').read_text())
audit_groups={}
for folder in sorted((ROOT/'runs').glob('*')):
 if requested and folder.name not in requested:continue
 manifest=folder/'run.json'
 if not manifest.exists():continue
 r=json.loads(manifest.read_text())
 if r.get('status')!='COMPLETE':continue
 if 'target_sha256' in r:assert hashlib.sha256(Path(r['target']).read_bytes()).hexdigest()==r['target_sha256']
 result={}
 for method in r['variants']:
  p=folder/method;d=json.loads((p/'result.json').read_text())
  # Write full-precision shared-index OBJ, avoiding split vertices from per-face normals.
  with (p/'result.obj').open('w') as stream:
   stream.write('# Shared-index geometry; Z up, Y front\n')
   for v in d['vertices']:stream.write('v '+' '.join(format(x,'.17g') for x in v)+'\n')
   for q in d['faces']:stream.write('f '+' '.join(str(x+1) for x in q)+'\n')
  checks={}
  for extension in ['obj','ply']:
   tm=run.trimesh.load(p/('result.'+extension),force='mesh',process=False)
   edge_count=np.bincount(tm.edges_unique_inverse)
   ncomp=len(run.trimesh.graph.connected_components(tm.face_adjacency,nodes=np.arange(len(tm.faces))))
   checks[extension]=dict(components=ncomp,watertight=bool(tm.is_watertight),zero_area_faces=int(np.count_nonzero(tm.area_faces==0)),nonmanifold_edges=int(np.count_nonzero(edge_count>2)),winding_consistent=bool(tm.is_winding_consistent))
   if method!='target':assert ncomp==1 and tm.is_watertight and checks[extension]['zero_area_faces']==0 and checks[extension]['nonmanifold_edges']==0 and tm.is_winding_consistent,(p,extension,checks)
  if (p/'midsurface.json').exists():
   mid=run.mesh(json.loads((p/'midsurface.json').read_text()))
   checks['midsurface_components']=len(run.trimesh.graph.connected_components(mid.face_adjacency,nodes=np.arange(len(mid.faces))))
   assert checks['midsurface_components']==1
   target=r.get('target',str(ROOT/'target.json'))
   audit_groups.setdefault(target,[]).append(str(p/'midsurface.json'))
  if r['wide']:
   v=np.array(d['vertices']);mirrored=v.copy();mirrored[:,0]*=-1;checks['symmetry_max_error']=float(cKDTree(v).query(mirrored)[0].max())
  result[method]=checks
 report['runs'][folder.name]=result
report['sources_unchanged']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in json.loads((ROOT/'sources.json').read_text()).items()}
assert all(report['sources_unchanged'].values())
run.write(ROOT/'verification.json',report)
for target,files in audit_groups.items():
 name='audit' if Path(target)==ROOT/'target.json' else 'audit_'+hashlib.sha256(Path(target).read_bytes()).hexdigest()[:12]
 if requested:name+='_subset'
 run.call(dict(action='audit',target=target,output=str(ROOT/name),meshes=files))
print(json.dumps(report,indent=2))
