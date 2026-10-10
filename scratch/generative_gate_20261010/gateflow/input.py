from . import runtime
from pathlib import Path
from dataclasses import dataclass
import json,hashlib
import numpy as np
from cheshire.reference_subdivision import ArrayMesh,topology

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,data):Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def create_neutral(path,width=2.6,height=3.2,depth=.65,opening_width=1.4,opening_height=2.4):
    """Only the INPUT fixture is designed: a plain rectangular connected frame."""
    p=Path(path);p.mkdir(parents=True,exist_ok=False)
    if not (0<opening_width<width and 0<opening_height<height and depth>0):raise ValueError('Invalid plain frame dimensions')
    x=np.unique(np.r_[np.linspace(-width/2,-opening_width/2,3),np.linspace(-opening_width/2,opening_width/2,5),np.linspace(opening_width/2,width/2,3)])
    y=np.linspace(-depth/2,depth/2,3);z=np.r_[np.linspace(0,opening_height,7),np.linspace(opening_height,height,3)[1:]]
    occupied=set()
    for i in range(len(x)-1):
      for j in range(len(y)-1):
       for k in range(len(z)-1):
        if (x[i]+x[i+1])/2<-opening_width/2 or (x[i]+x[i+1])/2>opening_width/2 or (z[k]+z[k+1])/2>opening_height:occupied.add((i,j,k))
    vertices=[];index={};faces=[];roles=[]
    templates=[((-1,0,0),[(0,0,0),(0,0,1),(0,1,1),(0,1,0)]),((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),((0,1,0),[(0,1,0),(0,1,1),(1,1,1),(1,1,0)]),((0,0,-1),[(0,0,0),(0,1,0),(1,1,0),(1,0,0)]),((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)])]
    for i,j,k in sorted(occupied):
      for off,corners in templates:
        if (i+off[0],j+off[1],k+off[2]) in occupied:continue
        f=[]
        for dx,dy,dz in corners:
          key=(i+dx,j+dy,k+dz)
          if key not in index:index[key]=len(vertices);vertices.append([x[key[0]],y[key[1]],z[key[2]]])
          f.append(index[key])
        faces.append(f);roles.append(2 if z[k]>=opening_height-1e-9 else (0 if x[i]<0 else 1))
    with (p/'mesh.obj').open('w') as stream:
      stream.write('# Synthetic neutral development input; NOT ALICE data.\n')
      for v in vertices:stream.write('v '+' '.join(map(str,v))+'\n')
      for f in faces:stream.write('f '+' '.join(str(q+1) for q in f)+'\n')
    write(p/'gate.json',dict(schema='cheshire-neutral-input/1',source_kind='synthetic_neutral_fixture',mesh='mesh.obj',mesh_sha256=sha(p/'mesh.obj'),unit='design_unit',axes='X_RIGHT_Y_FRONT_Z_UP',parameters=dict(width=width,height=height,depth=depth,opening_width=opening_width,opening_height=opening_height),regions={'support_left':[i for i,r in enumerate(roles) if r==0],'support_right':[i for i,r in enumerate(roles) if r==1],'upper':[i for i,r in enumerate(roles) if r==2]},openings=[{'profile_xz':[[-opening_width/2,0],[opening_width/2,0],[opening_width/2,opening_height],[-opening_width/2,opening_height]],'depth_bounds':[-depth,depth]}]))
    return p

@dataclass
class Input:
    mesh:object
    roles:np.ndarray
    openings:list
    manifest:dict
    origin:np.ndarray
    scale:float

def load(path):
    path=Path(path);meta=json.loads((path/'gate.json').read_text(encoding='utf8'))
    if meta['schema']!='cheshire-neutral-input/1':raise ValueError('Unsupported schema; no ALICE integration claimed')
    file=path/meta['mesh']
    if not file.resolve().is_relative_to(path.resolve()):raise ValueError('Mesh outside input directory')
    if sha(file)!=meta['mesh_sha256']:raise ValueError('Input hash mismatch')
    if meta['axes']!='X_RIGHT_Y_FRONT_Z_UP':raise ValueError('Unsupported coordinate frame')
    xyz=[];fs=[]
    for line in file.read_text().splitlines():
      a=line.split()
      if a and a[0]=='v':xyz.append(list(map(float,a[1:4])))
      if a and a[0]=='f':fs.append([int(q.split('/')[0])-1 for q in a[1:]])
    xyz=np.array(xyz);origin=np.array([xyz[:,0].mean(),xyz[:,1].mean(),xyz[:,2].min()]);scale=float(np.ptp(xyz[:,2]))
    if not np.isfinite(xyz).all() or scale<=0:raise ValueError('Invalid input geometry')
    if any(len(f) not in (3,4) for f in fs):raise ValueError('Initial input currently requires triangles/quads')
    q=np.full((len(fs),4),-1,np.int64)
    for i,f in enumerate(fs):q[i,:len(f)]=f
    roles=np.full(len(q),3,np.int8)
    for i,name in enumerate(['support_left','support_right','upper']):
      ids=meta['regions'][name]
      if not ids or min(ids)<0 or max(ids)>=len(q):raise ValueError('Missing/invalid structural region')
      roles[ids]=i
    opening=[]
    for o in meta['openings']:
      prof=(np.array(o['profile_xz'])-origin[[0,2]])/scale
      if not np.isfinite(prof).all() or len(prof)<3:raise ValueError('Invalid opening profile')
      opening.append(prof)
    if len(opening)!=1:raise ValueError('Current development scope: one declared primary opening')
    pos=(xyz-origin)/scale;m=ArrayMesh(pos,q,np.full(len(pos),-1,np.int8),pos.copy(),np.full((len(q),3),-1,np.int64));topology(m)
    return Input(m,roles,opening,meta,origin,scale)
