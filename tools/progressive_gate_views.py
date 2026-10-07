"""Small capture adapter for existing pyrender OpenGL depth rendering.

Exact original polygons are preserved in checkpoint/OBJ/3DM. Rendering uses a
separately declared triangle index stream with the original vertex positions.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
import numpy as np
from PIL import Image,ImageDraw
import pyrender
import trimesh

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from progressive_gates import parent_directory
from cross_cell_crease_study import read,write,file_hash

CAMERAS=dict(front=(0,0,[-400.036865234375,-18.533447265625,1750],4800),
             oblique=(30,18,[-400.036865234375,-18.533447265625,1750],4800),
             underside=(15,-30,[-400.036865234375,-18.533447265625,1750],4800),
             detail=(0,-8,[-1950.036865234375,-18.533447265625,2550],1500),
             detail_angle=(32,-22,[-1950.036865234375,-18.533447265625,2550],1500),
             mantle=(0,-12,[-400.036865234375,-18.533447265625,3050],1900),
             column=(0,0,[-1950.036865234375,-18.533447265625,1300],3200))


def depth_order_check(path):
    """Concrete z-occlusion check independent of polygon insertion order."""
    r=pyrender.OffscreenRenderer(64,64);outputs=[]
    try:
        for order in [(0,1),(1,0)]:
            scene=pyrender.Scene(ambient_light=[1,1,1],bg_color=[1,1,1,1])
            for i in order:
                v=np.array([[-400,-i*200,-300],[400,-i*200,-300],[0,-i*200,400]])
                model=trimesh.Trimesh(vertices=v,faces=[[0,1,2]],process=False)
                mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=([.8,.1,.1,1] if i else [.1,.1,.8,1]),doubleSided=True)
                scene.add(pyrender.Mesh.from_trimesh(model,material=mat))
            scene.add(pyrender.OrthographicCamera(xmag=500,ymag=500,znear=1,zfar=20000),pose=pose(0,0,[0,0,0]))
            color,raw=r.render(scene)
            outputs.append((color,orthographic_depth(raw,1,20000)))
        equal=bool(np.array_equal(outputs[0][0],outputs[1][0]) and np.array_equal(outputs[0][1],outputs[1][1]))
        center=float(outputs[0][1][32,32])
        if not equal or abs(center-9800)>2:raise ValueError('Depth-order fixture failed.')
        write(path,dict(status='PASS',insertion_order_invariant=equal,center_depth=center,expected_depth=9800,
            pyrender_raw_center=float(raw[32,32]),depth_correction='pyrender 0.1.45 applies perspective linearization even to orthographic cameras; adapter inverses it, then applies orthographic linearization.',
            method='Two coincident projected triangles at Y=0 and Y=-200, actual camera at Y=-10000. Near surface wins in both insertion orders.'))
    finally:r.delete()


def orthographic_depth(raw,near,far):
    mask=raw>0;depth=np.zeros(raw.shape,dtype=np.float64)
    depth[mask]=near+far-near*far/raw[mask].astype(np.float64)
    return depth


def pose(azimuth,elevation,target,distance=10000):
    az,el=np.radians([azimuth,elevation]);z=np.array([np.sin(az)*np.cos(el),-np.cos(az)*np.cos(el),np.sin(el)])
    x=np.cross([0,0,1],z);x/=np.linalg.norm(x);y=np.cross(z,x)
    m=np.eye(4);m[:3,:3]=np.column_stack([x,y,z]);m[:3,3]=np.array(target)+z*distance
    return m


def capture(root,names,tag,views,resolution=1200):
    out=root/'renders'/tag;out.mkdir(parents=True,exist_ok=True)
    records=[];r=pyrender.OffscreenRenderer(resolution,resolution)
    from OpenGL.GL import glGetString,GL_VERSION,GL_RENDERER
    backend=dict(OpenGL=glGetString(GL_VERSION).decode(),GPU=glGetString(GL_RENDERER).decode())
    try:
        for name in names:
            source=parent_directory(root,name);path=source/'geometry.json.gz';data=read(path)
            ids={v['id']:i for i,v in enumerate(data['vertices'])};v=np.asarray([v['xyz'] for v in data['vertices']],dtype=np.float64)
            tris=[]
            for f in data['faces']:
                q=[ids[i] for i in f['vertices']]
                if len(q) not in (3,4):raise ValueError('No unrecorded render polygon conversion.')
                tris.append(q[:3])
                if len(q)==4:tris.append([q[0],q[2],q[3]])
            tri=np.asarray(tris,dtype=np.int32);del tris,data
            material=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.73,.73,.70,1.],metallicFactor=0.,roughnessFactor=.86,doubleSided=True)
            model=trimesh.Trimesh(vertices=v,faces=tri,process=False)
            pm=pyrender.Mesh.from_trimesh(model,material=material,smooth=True)
            derivative=out/(name+'_render_indices.npz')
            # Index stream only; XYZ remains the hash-linked full-resolution source.
            if not derivative.exists():np.savez_compressed(derivative,vertex_ids=np.asarray(list(ids)),triangles=tri)
            for view in views:
                az,el,target,width=CAMERAS[view.removesuffix('_wire')];m=pose(az,el,target)
                scene=pyrender.Scene(bg_color=[.96,.96,.95,1.],ambient_light=[.36,.36,.36])
                scene.add(pm);scene.add(pyrender.OrthographicCamera(xmag=width/2,ymag=width/2,znear=1,zfar=30000),pose=m)
                scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=2.4),pose=pose(-35,45,target))
                scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=.8),pose=pose(65,10,target))
                flags=pyrender.RenderFlags.ALL_WIREFRAME if view.endswith('_wire') else pyrender.RenderFlags.NONE
                t=perf_counter();color,raw=r.render(scene,flags=flags);depth=orthographic_depth(raw,1,30000);seconds=perf_counter()-t
                filename=name+'_'+view+'.png';Image.fromarray(color).save(out/filename)
                np.savez_compressed(out/(name+'_'+view+'_depth.npz'),depth=depth)
                occupied=depth[depth>0]
                records.append(dict(id=name,view=view,geometry=str(path),geometry_sha256=file_hash(path),
                    input_polygons=read(source/'summary.json')['statistics']['face_count'],render_triangles=len(tri),
                    derivative_indices=str(derivative),derivative_sha256=file_hash(derivative),
                    conversion='Quads split 0-2 for display only, same original XYZ; shared vertex smooth display normals, no displacement or remeshing.',
                    camera_pose=m.tolist(),target=target,physical_width=width,resolution=[resolution,resolution],
                    capture_type='pyrender OpenGL depth-buffer render',material=dict(clay=[.73,.73,.70],roughness=.86),
                    depth_conversion='Undo perspective depth linearization in pyrender 0.1.45, then orthographic linearization: near+far-near*far/raw_depth; empty=0. GPU occlusion/color unchanged.',
                    lighting=dict(ambient=.36,key=[-35,45,2.4],fill=[65,10,.8]),
                    image=str(out/filename),image_sha256=file_hash(out/filename),depth_file=str(out/(name+'_'+view+'_depth.npz')),
                    occupied_pixels=int(len(occupied)),depth_min=float(occupied.min()) if len(occupied) else None,
                    depth_max=float(occupied.max()) if len(occupied) else None,render_seconds=seconds,
                    float32_display_max_coordinate_error=float(np.abs(v-v.astype(np.float32).astype(float)).max()),backend=backend))
                print(name,view,round(seconds,2),'s',flush=True)
            del model,pm,v,tri
    finally:r.delete()
    write(out/'camera_manifest.json',dict(renderer='pyrender '+pyrender.__version__,backend=backend,
        source_sha256=file_hash(Path(__file__)),records=records))
    for view in views:
        files=[out/(name+'_'+view+'.png') for name in names];cols=min(3,len(files));rows=(len(files)+cols-1)//cols
        sheet=Image.new('RGB',(cols*460,rows*490),(242,242,240));draw=ImageDraw.Draw(sheet)
        for i,(name,p) in enumerate(zip(names,files)):
            im=Image.open(p).convert('RGB');im.thumbnail((460,460));x=i%cols*460;y=i//cols*490
            sheet.paste(im,(x,y));draw.text((x+12,y+463),name,fill=(30,30,30))
        sheet.save(out/(view+'_sheet.png'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--names',nargs='+',required=True);p.add_argument('--tag',required=True)
    p.add_argument('--views',nargs='+',default=['front','detail']);p.add_argument('--resolution',type=int,default=1200)
    a=p.parse_args();capture(a.output_root,a.names,a.tag,a.views,a.resolution)
