"""Actual checkpoint flat-normal rendering, with auditable fixed framing."""
import argparse,json,re,sys,textwrap,gc
from pathlib import Path
from time import perf_counter
import numpy as np
import trimesh,pyrender
from PIL import Image,ImageDraw,ImageFont
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from task29_search import load_mesh
from task31_study import ROOT
from cross_cell_crease_study import read,write,file_hash
from progressive_gate_views import pose,orthographic_depth
from hero_design_sprint import guarded


def sheet(records,path,cols=4,size=460):
    rows=(len(records)+cols-1)//cols
    out=Image.new('RGB',(cols*size,rows*(size+32)),(245,245,242));d=ImageDraw.Draw(out)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    for i,r in enumerate(records):
        im=Image.open(r['image']).convert('RGB');im=im.resize((size,size))
        x=i%cols*size;y=i//cols*(size+32);out.paste(im,(x,y))
        d.text((x+8,y+size+4),r['label'],font=font,fill=(25,25,25))
    path.parent.mkdir(parents=True,exist_ok=True);out.save(path)


def render(request,tag):
    requests=read(request);resolution=requests.get('resolution',640);width=requests.get('width',4000.)
    target=requests.get('target',[0,0,0]);out=ROOT/'renders'/tag;out.mkdir(parents=True,exist_ok=False)
    renderer=pyrender.OffscreenRenderer(resolution,resolution);records=[]
    from OpenGL.GL import glGetString,GL_RENDERER
    backend=glGetString(GL_RENDERER).decode()
    try:
        for j,r in enumerate(requests['items']):
            if 'rejection' in r:
                card=Image.new('RGB',(resolution,resolution),(248,240,236));draw=ImageDraw.Draw(card)
                font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',max(16,resolution//32))
                text='REJECTED TOPOLOGY PROPOSAL\n\n'+r['label']+'\n\n'+r['rejection']+'\n\nNo invalid continuation generated.\nActual pre-weld geometry retained.'
                draw.multiline_text((30,60),'\n'.join(line if len(line)<48 else textwrap.fill(line,48) for line in text.splitlines()),font=font,fill=(90,35,25),spacing=10)
                path=out/f'{j:04}_REJECTED.png';card.save(path)
                records.append(dict(**r,image=str(path),rendered_geometry=False));continue
            stage=Path(r['stage']);m=load_mesh(stage);xyz=m.xyz
            q=m.faces
            tri=np.concatenate([q[q[:,k]>=0][:,[0,k-1,k]] for k in range(2,q.shape[1])]).astype(np.int32)
            model=trimesh.Trimesh(vertices=xyz,faces=tri,process=False)
            mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.73,.73,.70,1],metallicFactor=0,roughnessFactor=.86,doubleSided=True)
            pm=pyrender.Mesh.from_trimesh(model,material=mat,smooth=False)
            camera=pose(*r.get('angles',[28,22]),r.get('target',target));physical_width=r.get('width',width)
            scene=pyrender.Scene(bg_color=[.96,.96,.95,1],ambient_light=[.36]*3)
            scene.add(pm);scene.add(pyrender.OrthographicCamera(xmag=physical_width/2,ymag=physical_width/2,znear=1,zfar=30000),pose=camera)
            scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=2.4),pose=pose(-35,45,r.get('target',target)))
            scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=.8),pose=pose(65,10,r.get('target',target)))
            start=perf_counter();color,raw=renderer.render(scene);depth=orthographic_depth(raw,1,30000)
            filename=re.sub(r'[^A-Za-z0-9_.-]+','_',r['label'])
            path=out/f'{j:04}_{filename}.png';Image.fromarray(color).save(path)
            # Actual orthographic visibility, separately saved from shaded clay.
            hit=depth>0
            from scipy.ndimage import binary_fill_holes,label
            holes=binary_fill_holes(hit)&~hit
            components,count=label(holes)
            sizes=np.bincount(components.ravel())[1:]
            np.savez_compressed(path.with_suffix('.visibility.npz'),hit=hit,depth=depth.astype(np.float32))
            projected=(xyz-np.asarray(r.get('target',target)))@camera[:3,:2]
            record=dict(**r,image=str(path),mesh_sha256=file_hash(stage if stage.suffix=='.npz' else stage/'mesh.npz'),image_sha256=file_hash(path),camera_pose=camera.tolist(),physical_width=physical_width,
                flat_normals=True,smoothing=False,display_float32_max_error=float(np.abs(xyz-xyz.astype(np.float32).astype(float)).max()),
                vertices=len(xyz),polygons=len(q),triangles=len(tri),occupied_pixels=int((depth>0).sum()),
                outside_frame=int((np.abs(projected)>physical_width/2).any(1).sum()),seconds=perf_counter()-start,
                enclosed_background_pixels=int(holes.sum()),largest_background_component=int(sizes.max()) if len(sizes) else 0,
                enclosed_background_area=float(holes.sum()*(physical_width/resolution)**2),
                visibility_sha256=file_hash(path.with_suffix('.visibility.npz')))
            records.append(record)
            del scene,pm,model,tri,q,m,xyz,projected,color,raw,depth
            gc.collect()
            if (j+1)%16==0:print('Rendered',tag,j+1,'/',len(requests['items']),flush=True)
    finally:renderer.delete()
    write(out/'manifest.json',dict(backend=backend,records=records,request_sha256=file_hash(request),material='Same clay .73/.73/.70',light='Same key -35/45/2.4 fill65/10/.8 ambient.36',camera='Same orthographic physical units; explicit targets/crops in each record.'))
    pages=requests.get('pages',64)
    for i in range(0,len(records),pages):sheet(records[i:i+pages],out/f'page_{i//pages:02}.png',requests.get('cols',4),requests.get('size',460))
    if requests.get('sheet_name'):sheet(records,ROOT/'renders'/requests['sheet_name'],requests.get('cols',4),requests.get('size',460))


from task30_views import sheet

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:render(a.request,a.tag)
    else:
        r=guarded(['--request',str(a.request),'--tag',a.tag,'--worker'],ROOT/'logs'/('render_'+a.tag),worker_script=Path(__file__));print(r,flush=True);sys.exit(r['exit_code'])
