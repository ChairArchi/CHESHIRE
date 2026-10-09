"""Small orthographic triangle z-buffer renderer of actual mesh coordinates."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',size)

def render(v,faces,path,title,scale=125,size=(600,760),color=(177,187,196)):
    w,h=size; image=np.full((h,w,3),246.,dtype=float); depth=np.full((h,w),-np.inf)
    right=np.array([.83,.47,0]); right/=np.linalg.norm(right)
    toward=np.array([.47,-.83,.29]); toward/=np.linalg.norm(toward)
    up=np.cross(toward,right); up/=np.linalg.norm(up)
    cam=np.column_stack((v@right,v@up,v@toward))
    screen=np.column_stack((w/2+cam[:,0]*scale,h/2+28-cam[:,1]*scale))
    light=np.array([-.35,-.65,.68]); light/=np.linalg.norm(light)
    for f in faces:
        p=v[f]; normal=np.cross(p,np.roll(p,-1,axis=0)).sum(axis=0)
        normal/=max(np.linalg.norm(normal),1e-12)
        shade=.42+.58*max(0,float(normal@light))
        fill=np.array(color)*shade
        for k in range(1,len(f)-1):
            ids=[f[0],f[k],f[k+1]]; tri=screen[ids]; z=cam[ids,2]
            x0=max(0,int(np.floor(tri[:,0].min()))); x1=min(w-1,int(np.ceil(tri[:,0].max())))
            y0=max(70,int(np.floor(tri[:,1].min()))); y1=min(h-35,int(np.ceil(tri[:,1].max())))
            if x0>x1 or y0>y1: continue
            xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
            a,b,c=tri; den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-10: continue
            u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            t=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
            s=1-u-t; zz=u*z[0]+t*z[1]+s*z[2]
            region=depth[y0:y1+1,x0:x1+1]; mask=(u>=-1e-9)&(t>=-1e-9)&(s>=-1e-9)&(zz>region)
            region[mask]=zz[mask]; image[y0:y1+1,x0:x1+1][mask]=fill
    im=Image.fromarray(np.uint8(np.clip(image,0,255))); d=ImageDraw.Draw(im)
    d.text((24,18),title,font=font(23),fill=(28,37,49))
    d.text((24,h-30),f'{len(v)} vertices / {len(faces)} faces',font=font(15),fill=(70,80,90))
    im.save(path); return im

def sheet(rows,path,subtitle):
    tw,th=360,456; out=Image.new('RGB',(tw*len(rows[0]),86+th*len(rows)),(255,255,255))
    d=ImageDraw.Draw(out); d.text((18,12),subtitle,font=font(25),fill=(25,35,45))
    d.text((18,49),'Same camera and scale | each object centered for display | single mapping',font=font(18),fill=(75,85,95))
    for j,row in enumerate(rows):
        for i,im in enumerate(row): out.paste(im.resize((tw,th),Image.Resampling.LANCZOS),(i*tw,86+j*th))
    out.save(path)
