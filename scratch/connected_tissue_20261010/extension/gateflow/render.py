from . import runtime
import numpy as np,trimesh
import OpenGL
OpenGL.USE_ACCELERATE=False
import pyrender
from PIL import Image,ImageDraw,ImageFont

def pose(eye,target):
    z=np.asarray(eye,float)-target;z/=np.linalg.norm(z);x=np.cross([0,0,1],z);x/=np.linalg.norm(x);y=np.cross(z,x)
    p=np.eye(4);p[:3,:3]=np.column_stack([x,y,z]);p[:3,3]=eye;return p

def render(m,out,resolution=900,framing=None,use_vertex_colors=False):
    out.mkdir(exist_ok=True)
    box=m.bounds if framing is None else np.array(framing);center=box.mean(0);span=np.ptp(box,axis=0).max()*1.32
    material=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.58,.55,.48,1],roughnessFactor=.9,metallicFactor=.04)
    renderer=pyrender.OffscreenRenderer(resolution,resolution)
    try:
      for name,eye in [('front',center+[0,4*span,0]),('oblique',center+[-2.7*span,4*span,1.7*span])]:
        scene=pyrender.Scene(bg_color=[.075,.08,.09,1],ambient_light=[.24]*3)
        scene.add(pyrender.Mesh.from_trimesh(m,material=None if use_vertex_colors else material,smooth=False))
        scene.add(pyrender.OrthographicCamera(xmag=span/2,ymag=span/2,znear=.001,zfar=30*span),pose=pose(eye,center))
        for xyz,intensity in [([-2,3,4],2.4),([2,2,1],.9),([0,-3,3],1.6)]:
            scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=intensity),pose=pose(center+np.array(xyz)*span,center))
        color,depth=renderer.render(scene);Image.fromarray(color).save(out/(name+'.png'))
    finally:renderer.delete()

def sheet(items,path,size=450,columns=3):
    rows=(len(items)+columns-1)//columns;im=Image.new('RGB',(columns*size,rows*(size+54)),(24,25,28));d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    for i,(p,label) in enumerate(items):
        x=(i%columns)*size;y=(i//columns)*(size+54);im.paste(Image.open(p).resize((size,size)),(x,y));d.text((x+12,y+size+12),label,font=font,fill=(230,228,220))
    im.save(path)
