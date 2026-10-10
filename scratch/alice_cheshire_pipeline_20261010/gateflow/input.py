"""Read actual ALICE geometry and observations; no culture-specific geometry rules."""
from . import runtime
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
import numpy as np,trimesh
from scipy.spatial import cKDTree
ROLES=['support_left','support_right','overhead','upper_context','other']
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
@dataclass
class GateInput:
    mesh: object
    labels: np.ndarray
    profiles: list
    provenance: dict
    unit: str
    origin: np.ndarray
    scale: float
    def __post_init__(self):
        self.tree=cKDTree(self.mesh.triangles_center)
    def roles_at(self,points):
        distance,idx=self.tree.query(points)
        return self.labels[idx],distance,idx

def load_atlas(path):
    path=Path(path).resolve();a=read(path);source=read(path.with_name('source.json'))
    mp=Path(source['mesh']);mp=mp if mp.is_absolute() else path.parent/mp
    if digest(mp)!=source['mesh_sha256']:raise ValueError('ALICE source mesh hash mismatch')
    scene=trimesh.load(mp,process=False);m=scene.to_mesh() if isinstance(scene,trimesh.Scene) else scene
    if len(m.faces)>1500000:raise ValueError('Input face budget exceeded')
    if not np.isfinite(m.vertices).all():raise ValueError('Non-finite input')
    labels=np.full(len(m.faces),4,np.int8);assigned=np.zeros(len(m.faces),bool)
    primary=[p for p in a['passages'] if p['primary']]
    if len(primary)!=1:raise ValueError('Exactly one primary passage is currently required')
    slots={r['side']:r['target'] for r in a['relationships'] if r['source']==primary[0]['identifier'] and r['relation']=='bounded_by'}
    if set(slots)!={'left','right','overhead'}:raise ValueError('Closed gate relations missing')
    rolemap={slots['left']:0,slots['right']:1,slots['overhead']:2,'upper_mass':3}
    counts={}
    for cell in a['cells']:
        idx=np.array(cell['face_indices'],int)
        if len(idx) and (idx.min()<0 or idx.max()>=len(m.faces)):raise ValueError('Atlas face reference outside original mesh')
        if assigned[idx].any():raise ValueError('Overlapping atlas cells are unsupported')
        labels[idx]=rolemap.get(cell['identifier'],4);assigned[idx]=True;counts[cell['identifier']]=len(idx)
    if any(not np.any(labels==j) for j in range(3)):raise ValueError('Missing support or overhead observations')
    # Proper ALICE -> CHESHIRE frame rotation; one UNIFORM normalization, never a template warp.
    xyz=m.vertices[:,[0,2,1]].copy();xyz[:,1]*=-1
    scale=float(np.ptp(xyz[:,2]));origin=np.array([a['transform']['center_x'],0,xyz[:,2].min()])
    xyz=(xyz-origin)/scale
    mesh=trimesh.Trimesh(xyz,m.faces.copy(),process=False)
    profiles=[]
    for p in a['passages']:
        profile=np.array([[r['left'],r['right'],r['y']] for r in p['profile']],float)
        if len(profile)<2:raise ValueError('Measured passage profile missing')
        profile[:,:2]=(profile[:,:2]-origin[0])/scale;profile[:,2]=(profile[:,2]-origin[2])/scale
        if not np.isfinite(profile).all() or np.any(profile[:,0]>=profile[:,1]):raise ValueError('Invalid measured profile')
        profiles.append(dict(id=p['identifier'],primary=p['primary'],confidence=p['confidence'],samples=profile.tolist(),bottom=(p['physical']['bottom']-origin[2])/scale,top=(p['physical']['top']-origin[2])/scale))
    return GateInput(mesh,labels,profiles,dict(kind='actual_ALICE_atlas',identifier=a['identifier'],family=source.get('family'),atlas=str(path),atlas_sha256=digest(path),source_json_sha256=digest(path.with_name('source.json')),source_mesh=str(mp),source_mesh_sha256=digest(mp),source_face_counts=counts,source_topology=a['diagnostics'].get('source_topology'),geometry='Full original source vertices/connectivity after proper rotation and uniform normalization; no template geometry'), 'design_unit',origin,scale)

def load_exchange(path):
    from cheshire.gate_exchange import load_gate_input
    mesh,manifest=load_gate_input(path);v,f=mesh.to_vertices_and_faces()
    if any(len(q)!=3 for q in f):raise ValueError('Exchange adapter currently requires triangles')
    sem=manifest['semantics']
    if any(sem[k] is None or not sem[k] for k in ('support_left','support_right','upper','openings')):raise ValueError('Exchange has unknown/empty structural observations; supply an actual ALICE atlas instead')
    xyz=np.asarray(v);scale=float(np.ptp(xyz[:,2]));origin=xyz.mean(0);origin[2]=xyz[:,2].min();xyz=(xyz-origin)/scale
    labels=np.full(len(f),4,np.int8)
    for key,role in [('support_left',0),('support_right',1),('upper',2)]:labels[sem[key]]=role
    profiles=[]
    for j,op in enumerate(sem['openings']):
        lo,hi=(np.array(op['bounds'])-origin)/scale
        profiles.append(dict(id=f'opening_{j}',primary=j==0,confidence=None,bottom=lo[2],top=hi[2],samples=[[lo[0],hi[0],lo[2]],[lo[0],hi[0],hi[2]]]))
    return GateInput(trimesh.Trimesh(xyz,f,process=False),labels,profiles,dict(kind='ALICE_gate_exchange_v1',manifest=manifest,input_path=str(Path(path).resolve())),manifest['unit'],origin,scale)

def load(path):
    p=Path(path)
    return load_atlas(p) if p.is_file() else load_exchange(p)
