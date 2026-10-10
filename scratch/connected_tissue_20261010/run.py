"""Reusable connected-patch extraction and topology/tessellation experiment."""
from pathlib import Path
import argparse,json,subprocess,sys,hashlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra,connected_components
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'generative_gate_20261010'
sys.path.insert(0,str(OLD));from gateflow import runtime
import trimesh
from scipy.spatial import cKDTree
BLENDER=OLD/'external/blender-4.5.4-windows-x64/blender.exe'
def write(p,d):p.write_text(json.dumps(d,indent=2))
def call(j):
 p=Path(j['output']);p.mkdir(parents=True,exist_ok=True);write(p/'job.json',j)
 with (p/'blender.log').open('w',encoding='utf8') as log:
  subprocess.run([str(BLENDER),'--background','--factory-startup','--threads','8','--python-exit-code','1','--python',str(ROOT/'worker.py'),'--',str(p/'job.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
def mesh(data):
 vertices=np.array(data['vertices']);tri=[]
 for q in data['faces']:
  for i in range(1,len(q)-1):tri.append([q[0],q[i],q[i+1]])
 return trimesh.Trimesh(vertices,np.array(tri),process=False)
def inspect(folder):
 data=json.loads((folder/'result.json').read_text());tm=mesh(data)
 counts=np.bincount(tm.edges_unique_inverse);components=trimesh.graph.connected_components(tm.face_adjacency,nodes=np.arange(len(tm.faces)))
 report=dict(vertices=len(tm.vertices),triangles=len(tm.faces),components=len(components),boundary_edges=int((counts==1).sum()),nonmanifold_edges=int((counts>2).sum()),zero_area_faces=int((tm.area_faces==0).sum()),finite=bool(np.isfinite(tm.vertices).all()),watertight=bool(tm.is_watertight),winding_consistent=bool(tm.is_winding_consistent))
 tm.export(folder/'result.ply');write(folder/'checks.json',report);print(folder.name,report,flush=True)
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--target',type=Path,default=ROOT/'target.json');p.add_argument('--scale',type=int,default=4);p.add_argument('--radius',type=float,default=.16);p.add_argument('--wide',action='store_true');p.add_argument('--protect-folds',action='store_true');p.add_argument('--seam-collar',type=float,default=0.);p.add_argument('--methods',default='target,tissue,frame,frame_round');p.add_argument('--refinement',type=int,default=1);p.add_argument('--thickness',type=float,default=.0012);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output).resolve()
 if out.exists():raise FileExistsError(out)
 target=Path(a.target).resolve();target_hash=hashlib.sha256(target.read_bytes()).hexdigest()
 out.mkdir(parents=True);coarse=ROOT/(f'scale_{a.scale}' if target==ROOT/'target.json' else f'scale_{a.scale}_{target_hash[:12]}')
 if not (coarse/'coarse.json').is_file():call(dict(action='prepare',target=str(target),output=str(coarse),unsubdivide_iterations=a.scale))
 d=json.loads((coarse/'coarse.json').read_text());v=np.array(d['vertices'])
 if set(map(len,d['faces']))!={4}:raise ValueError('Requested unsubdivision scale has non-quad faces; use scale 2 or 4 for this TARGET')
 f=np.array(d['faces']);centers=v[f].mean(1)
 if f.shape[1]!=4:raise ValueError('Unsubdivision did not produce quad scale')
 edges=np.sort(np.stack([f,np.roll(f,-1,axis=1)],axis=2).reshape(-1,2),axis=1);_,inverse,count=np.unique(edges,axis=0,return_inverse=True,return_counts=True)
 order=np.argsort(inverse,kind='stable');pairs=order.reshape(-1,2)//4
 if not np.all(count==2):raise ValueError('Closed coarse target expected')
 length=np.linalg.norm(centers[pairs[:,0]]-centers[pairs[:,1]],axis=1)
 graph=coo_matrix((np.r_[length,length],(np.r_[pairs[:,0],pairs[:,1]],np.r_[pairs[:,1],pairs[:,0]])),shape=(len(f),len(f))).tocsr()
 desired=np.array([.22,.10,.73]);seed=int(np.argmin(np.linalg.norm(centers-desired,axis=1)))
 if a.wide:
  eligible=(centers[:,1]>0)&(centers[:,2]>.06)
  ids=np.flatnonzero(eligible);nc,label=connected_components(graph[ids][:,ids],directed=False)
  selected=ids[label==np.argmax(np.bincount(label))]
 else:selected=np.flatnonzero(dijkstra(graph,directed=False,indices=seed,limit=a.radius)<a.radius)
 # Store actual selected coarse face IDs and the exact shared vertices.
 used,remap=np.unique(f[selected],return_inverse=True);patch=dict(vertices=v[used].tolist(),faces=remap.reshape(-1,4).tolist())
 write(out/'patch.json',patch);np.save(out/'selected_face_ids.npy',selected)
 graph_components=connected_components(graph[selected][:,selected],directed=False,return_labels=False)
 if graph_components!=1:raise ValueError('Patch must be edge connected')
 center=v[used].mean(0);extent=float(np.max(np.ptp(v[used],axis=0)))
 write(out/'camera.json',dict(center=[0,0,.5],span=1.,target=(center-np.array([0,0,.5])).tolist(),ortho_scale=extent*1.2))
 record=dict(status='RUNNING',target=str(target),target_sha256=target_hash,scale_iterations=a.scale,source_faces=len(json.loads(target.read_text())['faces']),coarse_faces=len(f),selected_faces=len(selected),edge_connected_components=graph_components,seed_face=seed,radius=a.radius,wide=a.wide,variants={})
 write(out/'run.json',record)
 for method in a.methods.split(','):
  if method not in ('target','tissue','tissue_round','tissue_collar','tissue_variable','frame','frame_round','frame_bundle','frame_strips'):raise ValueError('Unknown method')
  folder=out/method;call(dict(action='make',target=str(target),patch=str(out/'patch.json'),output=str(folder),method=method,refinement=a.refinement,thickness=a.thickness,bilateral=a.wide,protect_folds=a.protect_folds,seam_collar=a.seam_collar,external=str(OLD/'external')))
  record['variants'][method]=inspect(folder);write(out/'run.json',record)
  ck=record['variants'][method]
  if method!='target' and (ck['components']!=1 or not ck['watertight'] or ck['nonmanifold_edges'] or ck['zero_area_faces'] or not ck['finite'] or not ck['winding_consistent']):raise ValueError('Connected solid-shell checks failed: '+method)
 record['status']='COMPLETE';record['source_preserved']={k:hashlib.sha256(Path(k).read_bytes()).hexdigest()==s for k,s in json.loads((ROOT/'sources.json').read_text()).items()};write(out/'run.json',record)
if __name__=='__main__':
 try:main()
 except Exception as error:
  output=Path(sys.argv[sys.argv.index('--output')+1]);manifest=output/'run.json'
  record=json.loads(manifest.read_text()) if manifest.exists() else {}
  if output.exists():write(manifest,dict(record,status='FAILED',error=str(error)))
  raise
