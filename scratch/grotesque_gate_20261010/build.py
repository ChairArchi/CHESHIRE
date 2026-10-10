import sys,json,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'deps'))
sys.path.insert(0,str(ROOT.parents[1]/'src'))
import numpy as np,trimesh
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
import manifold3d as md
from PIL import Image,ImageDraw,ImageFont
import OpenGL
OpenGL.USE_ACCELERATE=False
import pyrender
from cheshire.reference_subdivision import ArrayMesh,subdivide
OUT=ROOT/'artifacts';OUT.mkdir(exist_ok=True)

def save(m,name,route):
    m.remove_unreferenced_vertices();m.fix_normals()
    m.export(OUT/(name+'.obj'));m.export(OUT/(name+'.ply'))
    edges=np.sort(m.edges,axis=1);_,cnt=np.unique(edges,axis=0,return_counts=True)
    info=dict(name=name,route=route,vertices=len(m.vertices),triangles=len(m.faces),finite=bool(np.isfinite(m.vertices).all()),watertight=bool(m.is_watertight),winding_consistent=bool(m.is_winding_consistent),positive_volume=bool(m.volume>0),volume=float(m.volume),boundary_edges=int((cnt==1).sum()),nonmanifold_edges=int((cnt>2).sum()),zero_area_faces=int((m.area_faces==0).sum()),near_zero_area_faces_under_1e_12=int((m.area_faces<1e-12).sum()),components=len(m.split(only_watertight=False)),bounds=m.bounds.tolist(),units='metres (design scale; not structural certification)',self_intersection='No exhaustive triangle-pair test; basic topology checks only')
    (OUT/(name+'.json')).write_text(json.dumps(info,indent=2)); print(json.dumps(info),flush=True)
    return m

def folded():
    # Closed U-shaped swept surface, then actual CHESHIRE Catmull-Clark.
    n=76
    left=np.column_stack([np.full(n,-1.95),np.zeros(n),np.linspace(.12,3.55,n)])
    t=np.linspace(np.pi,0,110)[1:-1]
    arch=np.column_stack([1.95*np.cos(t),np.zeros(len(t)),3.55+1.95*np.sin(t)])
    right=np.column_stack([np.full(n,1.95),np.zeros(n),np.linspace(3.55,.12,n)])
    path=np.vstack([left,arch,right]);N=len(path);K=40
    tan=np.gradient(path,axis=0);tan/=np.linalg.norm(tan,axis=1)[:,None]
    normal=np.column_stack([-tan[:,2],np.zeros(N),tan[:,0]])
    verts=[]
    for i,c in enumerate(path):
      h=c[2];s=i/(N-1);ph=.8*h+.7*np.sin(h*1.3)
      for a in np.arange(K)*2*np.pi/K:
        # Broad asymmetric fluting with nested folds, real silhouette depth.
        lobe=(.5+.5*np.cos(6*a+ph))**2
        r=.48+.26*lobe+.12*np.sin(3*a-ph)+.07*np.cos(13*a+2*ph)
        r*=1+.17*np.cos(h*2.4)+.15*np.exp(-((h-4.9)/.65)**2)
        v=c+normal[i]*r*np.cos(a)+np.array([0,1,0])*r*(1.05+.12*np.sin(h))*np.sin(a)
        v[1]+=.12*np.sin(h*1.9)*np.sin(np.pi*s)
        verts.append(v)
    faces=[]
    for i in range(N-1):
      for j in range(K):faces.append([i*K+j,i*K+(j+1)%K,(i+1)*K+(j+1)%K,(i+1)*K+j])
    # quad fan caps, meeting at midpoint pair with triangle slots
    for i,reverse in [(0,True),(N-1,False)]:
      ci=len(verts);verts.append(path[i])
      for j in range(K):
        q=[ci,i*K+(j+1)%K,i*K+j] if reverse else [ci,i*K+j,i*K+(j+1)%K]
        faces.append(q+[-1])
    xyz=np.array(verts);q=np.array(faces)
    # normalize input orientation through triangles before preserving polygon order
    m=ArrayMesh(xyz,q,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(q),3),-1,np.int64))
    m,meta,states=subdivide(m,{'weights':{'wf':.035,'we':-.015}})
    f=np.vstack([m.faces[:,:3],m.faces[:,[0,2,3]]]);mesh=trimesh.Trimesh(m.xyz,f,process=True)
    mesh.vertices[:,2]-=mesh.bounds[0,2]
    np.savez_compressed(OUT/'A_folded_state.npz',xyz=m.xyz,faces=m.faces,classes=m.classes,rest=m.rest,anchors=m.anchors)
    return save(mesh,'A_FOLDED_RELIQUARY','Twisted fluted U carrier + actual CHESHIRE reference_subdivision.subdivide')

def ell(c,r,rot=(0,0,0),seg=32):return md.Manifold.sphere(1,seg).scale(tuple(r)).rotate(rot).translate(tuple(c))
def union(items):return md.Manifold.batch_boolean(items,md.OpType.Add)
def carved():
    parts=[md.Manifold.cube((1.6,1.65,4.2),True).translate((s*2.0,0,2.1)) for s in [-1,1]]
    parts += [ell((0,0,4.45),(2.8,.9,1.6),seg=48)]
    for s in [-1,1]:
      parts.append(ell((s*2.05,0,.3),(1.02,1.0,.4)))
      for k in range(3):
        parts.append(md.Manifold.cylinder(1.1-k*.18,.34-k*.04,0,20).rotate((s*8,s*(20+10*k),0)).translate((s*(1.0+k*.62),.07,5.3-k*.27)))
    body=union(parts)
    cut=[md.Manifold.cube((2.55,5,3.5),True).translate((0,0,1.5)),ell((0,0,3.2),(1.275,3,1.65),seg=48)]
    for s in [-1,1]:
      # deep hollowing, not microtexture
      for k in range(5):
        z=.65+k*.86
        cut.append(ell((s*(2+.18*np.sin(k*1.8)),-.80,z),(.42,.59,.62),rot=(0,s*(18+12*np.sin(k)),0)))
        cut.append(ell((s*2.64,.06,z+.23),(.39,.53,.45)))
      for k in range(4):
        cut.append(ell((s*(.35+.5*k),-.85,5.35-.13*k),(.19,.51,.59),rot=(0,s*28,0)))
    body=md.Manifold.batch_boolean([body]+cut,md.OpType.Subtract)
    if str(body.status())!='Error.NoError':print('BOOLEAN',body.status(),flush=True)
    raw=body.to_mesh();m=trimesh.Trimesh(np.asarray(raw.vert_properties)[:,:3],np.asarray(raw.tri_verts),process=True)
    return save(m,'B_CARVED_BASTION','Manifold solid union + through opening + deep ellipsoid Boolean subtraction + horn solids')

class Field:
  def __init__(self,h=.036):
    self.h=h;self.lo=np.array([-3.55,-1.7,-.3]);self.hi=np.array([3.55,1.7,7.7]);self.axes=[np.arange(a,b+h,h,dtype=np.float32) for a,b in zip(self.lo,self.hi)];self.f=np.full(tuple(map(len,self.axes)),3,dtype=np.float32)
  def tube(self,pts,rads,k=.10):
    pts=np.array(pts);rads=np.broadcast_to(rads,(len(pts),))
    for a,b,ra,rb in zip(pts[:-1],pts[1:],rads[:-1],rads[1:]):
      pad=max(ra,rb)+k+.06;low=np.maximum(0,np.floor((np.minimum(a,b)-pad-self.lo)/self.h).astype(int));high=np.minimum(self.f.shape,np.ceil((np.maximum(a,b)+pad-self.lo)/self.h).astype(int)+1)
      if np.any(high<=low):continue
      sl=tuple(slice(i,j) for i,j in zip(low,high));x,y,z=np.ogrid[tuple(slice(i,j) for i,j in zip(low,high))];p=[x*self.h+self.lo[0]-a[0],y*self.h+self.lo[1]-a[1],z*self.h+self.lo[2]-a[2]];v=b-a
      t=np.clip(sum(p[i]*v[i] for i in range(3))/max(v@v,1e-12),0,1)
      d=np.sqrt(sum((p[i]-t*v[i])**2 for i in range(3)))-(ra+(rb-ra)*t)
      old=self.f[sl];blend=np.maximum(k-np.abs(old-d),0)/k
      self.f[sl]=np.minimum(old,d)-blend*blend*k*.25
  def mesh(self):
    # Cut at z=0 to produce a flat, closed standing footprint.
    z=self.axes[2][None,None,:];self.f=np.maximum(self.f,-z)
    v,f,_,_=marching_cubes(self.f,0,spacing=(self.h,)*3,allow_degenerate=False)
    v+=self.lo
    return trimesh.Trimesh(v,f,process=True)

def organic(final=False):
    field=Field(.027 if final else .042)
    for s in [-1,1]:
      # Three macroscopic intertwined load-like roots, not a texture displacement.
      for j in range(3):
        t=np.linspace(0,1,80);z=-.06+4.55*t;phase=2*np.pi*j/3+(2.05 if final else 1.8)*z
        x=s*(1.98+(.43 if final else .25)*np.cos(phase)+.12*np.sin(z*1.35));y=(.57 if final else .39)*np.sin(phase)
        pts=np.column_stack([x,y,z]);r=(.17 if final else .20)+.08*(1-t)+.08*np.exp(-((t-.72)/.17)**2)
        field.tube(pts,r,.13)
        # buttress roots, wider foot attached to each strand
        foot=np.array([[s*(2.0+.7*np.cos(j*2)),.64*np.sin(j*2),-.08],pts[7],pts[18]])
        field.tube(foot,[.28,.24,.24],.14)
      # several deeply separated arch ribs, fuse at shoulder and keystone
      for j in range(4):
        t=np.linspace(0,np.pi/2,65)
        x=s*(2.0*np.cos(t));z=3.75+(1.8+.22*j)*np.sin(t)
        y=((-1.00+.64*j) if final else (-.72+.46*j))*np.sin(t*.9)+.10*np.cos(t*4+j)
        pts=np.column_stack([x,y,z]);r=.18+.07*np.cos(t)**2+.045*np.sin(t*3+j)**2
        field.tube(pts,r,.10)
      # hooked shoulder horns, growing out then curling toward center
      t=np.linspace(0,1,65)
      pts=np.column_stack([s*(2.10+.64*np.sin(np.pi*t)-.34*t),.10+.18*np.sin(t*4),4.0+2.52*t])
      field.tube(pts,.30*(1-t)**.85+.028,.10)
      # large curled scroll: cavity framed by a tapering continuous tube
      t=np.linspace(0,1,90);a=-1.25+5.7*t;r=.64*(1-.74*t)
      pts=np.column_stack([s*(2.12+r*np.cos(a)),-.66-.09*np.sin(t*3),4.18+r*np.sin(a)])
      field.tube(pts,.21*(1-.65*t),.10)
      if final:
        # Hierarchical openwork: five unequal outward loops linked into the roots.
        for k in range(5):
          t=np.linspace(0,1,55);hh=.52+k*.79+.09*s*np.sin(k*2)
          bulge=(.46+.12*np.sin(k*1.7+s))*np.sin(np.pi*t)
          pts=np.column_stack([s*(2.04+bulge+.13*np.sin(t*6+k)), -.38-.34*np.sin(np.pi*t),hh+1.05*t])
          field.tube(pts,.135+.04*np.sin(np.pi*t),.08)
          # Tapered hooked spur grows out of each second loop, at architectural scale.
          if k%2==0:
            t=np.linspace(0,1,40)
            pts=np.column_stack([s*(2.30+.62*np.sin(t*1.9)), -.48+.17*t, hh+.5+.68*t])
            field.tube(pts,.18*(1-t)**1.1+.023,.08)
        # Irregular crown crest: distinct curved branches anchored in arch ribs.
        for k in range(4):
          u=.22+k*.31;t=np.linspace(0,1,46);base_x=s*(2*np.cos(u));base_z=3.75+2.15*np.sin(u)
          pts=np.column_stack([base_x+s*(.35*np.sin(t*2.9)-.26*t), -.06+.30*np.sin(k*1.7)+.22*np.sin(t*3),base_z+(.80+.26*np.sin(k*2+s))*t])
          field.tube(pts,.17*(1-t)**.85+.022,.08)
        # Smaller shoulder scroll retains a real central void.
        t=np.linspace(0,1,65);a=-1.0+5.3*t;rr=.33*(1-.55*t)
        pts=np.column_stack([s*(2.27+rr*np.cos(a)),-.79-.13*np.sin(t*3),3.18+rr*np.sin(a)])
        field.tube(pts,.09*(1-.5*t),.065)
        # Reinforce arch-to-pier web; branching cusp spurs with controlled asymmetry.
        for k in range(3):
          t=np.linspace(0,1,28)
          pts=np.column_stack([s*(2.10-.42*np.sin(t*np.pi/2)),.35*np.cos(k*2)-.16*t,(1.35+k*.92)+.67*t])
          field.tube(pts,.15*(1-t)+.065,.09)
        t=np.linspace(0,1,45)
        pts=np.column_stack([s*(.18+.53*t+.13*np.sin(t*np.pi)), -.03-.20*np.sin(t*np.pi),5.71+(.9 if s<0 else 1.16)*t])
        field.tube(pts,.20*(1-t)+.024,.1)
    # branching crown joins both halves with a pendulous central boss
    t=np.linspace(0,1,45)
    field.tube(np.column_stack([.09*np.sin(t*6),-.26-.15*t,5.82-.75*t]),.25*(1-t)+.08,.13)
    m=field.mesh()
    if final:
      # Discard three sub-voxel isolated bubbles; retain the actual main gate.
      pieces=m.split(only_watertight=False);m=max(pieces,key=lambda a:abs(a.volume))
      solid=md.Manifold(md.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
      if str(solid.status())!='Error.NoError':raise RuntimeError(str(solid.status()))
      cutters=[]
      for side in [-1,1]:
        for k in range(4):
          cutters.append(ell((side*(2.00+.10*np.sin(k*2)), -.67, .94+k*.89),(.20,.34,.40),rot=(0,side*(20-9*k),0),seg=32))
      solid=md.Manifold.batch_boolean([solid]+cutters,md.OpType.Subtract).simplify(.0015)
      if str(solid.status())!='Error.NoError':raise RuntimeError(str(solid.status()))
      raw=solid.to_mesh64();m=trimesh.Trimesh(np.asarray(raw.vert_properties)[:,:3],np.asarray(raw.tri_verts),process=True)
      m=max(m.split(only_watertight=False),key=lambda a:abs(a.volume))
      m.vertices[:,2]-=m.bounds[0,2]
    return save(m,'FINAL_THORN_CATHEDRAL' if final else 'C_ROOT_CATHEDRAL','Smooth implicit union of tapered branching roots, separated arch ribs and curled horns; marching cubes'+('; reinforced shoulders, asymmetric bifid crown, Boolean recesses, sub-voxel islands removed and 0.0015m simplification' if final else ''))

def pose(eye,target):
    eye=np.array(eye);target=np.array(target);z=eye-target;z/=np.linalg.norm(z);x=np.cross([0,0,1],z);x/=np.linalg.norm(x);y=np.cross(z,x);p=np.eye(4);p[:3,:3]=np.column_stack([x,y,z]);p[:3,3]=eye;return p

def render(m,name,res=1050):
    renderer=pyrender.OffscreenRenderer(res,res)
    mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.57,.52,.43,1],metallicFactor=.1,roughnessFactor=.8)
    for label,eye in [('front',[0,-17,3.7]),('oblique',[9,-16,8.2])]:
      scene=pyrender.Scene(bg_color=[.055,.064,.072,1],ambient_light=[.24,.24,.25])
      scene.add(pyrender.Mesh.from_trimesh(m,material=mat,smooth=True))
      floor=trimesh.creation.box(extents=[200,200,.10]);floor.apply_translation([0,0,-.07])
      scene.add(pyrender.Mesh.from_trimesh(floor,material=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.11,.12,.13,1],roughnessFactor=1)))
      scene.add(pyrender.OrthographicCamera(xmag=4.3,ymag=4.3,znear=.1,zfar=200),pose=pose(eye,[0,0,3.35]))
      for e,c,intensity in [([-5,-8,11],[1,.86,.68],3.0),([6,-3,6],[.62,.77,1],1.7),([0,5,10],[1,.86,.63],2.4)]:
        scene.add(pyrender.DirectionalLight(color=c,intensity=intensity),pose=pose(e,[0,0,3.4]))
      col,depth=renderer.render(scene,flags=pyrender.RenderFlags.NONE)
      Image.fromarray(col).save(OUT/f'{name}_{label}.png')
      print('render',name,label,flush=True)
    renderer.delete()

def sheet(names):
    w=620;cap=70;im=Image.new('RGB',(w*len(names),(w+cap)*2),(20,23,27));d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    for i,name in enumerate(names):
      for row,view in enumerate(['front','oblique']):
        pic=Image.open(OUT/f'{name}_{view}.png').resize((w,w));im.paste(pic,(i*w,row*(w+cap)));d.text((i*w+14,row*(w+cap)+w+12),name.replace('_',' '),font=font,fill=(225,220,206))
    im.save(OUT/'candidate_comparison.png')

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'all'
    if mode=='all':
      for fn in [folded,carved,organic]:
        m=fn();name=['A_FOLDED_RELIQUARY','B_CARVED_BASTION','C_ROOT_CATHEDRAL'][[folded,carved,organic].index(fn)];render(m,name)
      sheet(['A_FOLDED_RELIQUARY','B_CARVED_BASTION','C_ROOT_CATHEDRAL'])
    elif mode=='final':
      m=organic(True);render(m,'FINAL_THORN_CATHEDRAL',1500)
