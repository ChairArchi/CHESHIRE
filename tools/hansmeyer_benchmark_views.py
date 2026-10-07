"""Flat, depth-correct actual geometry captures; fixed cameras within each set."""
import argparse,sys
from pathlib import Path
from time import perf_counter
import numpy as np
import trimesh,pyrender
from PIL import Image,ImageDraw
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from cross_cell_crease_study import read,write,file_hash
from progressive_gate_views import pose,orthographic_depth,depth_order_check
from hero_design_sprint import guarded


def source(root,name,g):
    if name=='LEAD':return root/'lead'/f'G{g}'
    if name=='TASK27':return Path('E:/CHESHIRE_DATA/task27/stages/R4_PROFILE_DYNAMIC_G5')
    return root/'input/G0' if g==0 else root/'candidates'/name/f'G{g}'


def capture(root,names,generations,tag,resolution,width,views,target,task27_target):
    out=root/'renders'/tag
    if out.exists():raise ValueError('Preserve old captures; use a new tag.')
    out.mkdir(parents=True);records=[];r=pyrender.OffscreenRenderer(resolution,resolution)
    from OpenGL.GL import glGetString,GL_VERSION,GL_RENDERER
    backend=dict(OpenGL=glGetString(GL_VERSION).decode(),GPU=glGetString(GL_RENDERER).decode())
    cameras=dict(front=(0,0),oblique=(28,22),detail=(20,-8),wire=(28,22),top=(12,62))
    try:
        for name in names:
            for g in generations:
                d=source(root,name,g)
                if not (d/'geometry.json.gz').exists():continue
                data=read(d/'geometry.json.gz');ids={v['id']:i for i,v in enumerate(data['vertices'])}
                xyz=np.asarray([v['xyz'] for v in data['vertices']],dtype=np.float64);tri=[]
                for f in data['faces']:
                    q=[ids[v] for v in f['vertices']];tri.append(q[:3])
                    if len(q)==4:tri.append([q[0],q[2],q[3]])
                    elif len(q)!=3:raise ValueError('Only original tri/quads supported.')
                tri=np.asarray(tri,dtype=np.int32)
                model=trimesh.Trimesh(vertices=xyz,faces=tri,process=False)
                mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.73,.73,.70,1.],metallicFactor=0.,roughnessFactor=.86,doubleSided=True)
                pm=pyrender.Mesh.from_trimesh(model,material=mat,smooth=False)
                for view in views:
                    az,el=cameras[view];actual_target=task27_target if name=='TASK27' else target
                    physical_width=width;camera=pose(az,el,actual_target)
                    scene=pyrender.Scene(bg_color=[.96,.96,.95,1.],ambient_light=[.36]*3)
                    scene.add(pm);scene.add(pyrender.OrthographicCamera(xmag=physical_width/2,ymag=physical_width/2,znear=1,zfar=30000),pose=camera)
                    scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=2.4),pose=pose(-35,45,actual_target))
                    scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=.8),pose=pose(65,10,actual_target))
                    t=perf_counter();flags=pyrender.RenderFlags.ALL_WIREFRAME if view=='wire' else pyrender.RenderFlags.NONE
                    color,raw=r.render(scene,flags=flags);depth=orthographic_depth(raw,1,30000)
                    p=out/f'{name}_G{g}_{view}.png';Image.fromarray(color).save(p)
                    projected=(xyz-np.asarray(actual_target))@camera[:3,:2]
                    records.append(dict(name=name,generation=g,view=view,geometry=str(d/'geometry.json.gz'),geometry_sha256=file_hash(d/'geometry.json.gz'),
                        image=str(p),image_sha256=file_hash(p),camera_pose=camera.tolist(),target=actual_target,physical_width=physical_width,resolution=resolution,
                        source_vertices=len(xyz),source_polygons=len(data['faces']),display_triangles=len(tri),
                        derivative='Original XYZ; quads split diagonal0-2 only for display; FLAT normals, no geometry smoothing or displacement.',
                        float32_display_max_error=float(np.abs(xyz-xyz.astype(np.float32).astype(float)).max()),
                        projection_vertices_outside_frame=int((np.abs(projected)>physical_width/2).any(axis=1).sum()),
                        material=dict(clay=[.73,.73,.70],roughness=.86),lighting=dict(ambient=.36,key=[-35,45,2.4],fill=[65,10,.8]),
                        occupied_pixels=int((depth>0).sum()),render_seconds=perf_counter()-t))
                print('Captured',name,'G'+str(g),flush=True)
    finally:r.delete()
    write(out/'camera_manifest.json',dict(backend=backend,source_sha256=file_hash(Path(__file__)),records=records))
    for view in views:
        rows=[x for x in records if x['view']==view];cols=min(4,len(rows));height=(len(rows)+cols-1)//cols
        sheet=Image.new('RGB',(cols*360,height*395),(242,242,240));draw=ImageDraw.Draw(sheet)
        for i,row in enumerate(rows):
            im=Image.open(row['image']).convert('RGB');im.thumbnail((360,360));x=i%cols*360;y=i//cols*395
            sheet.paste(im,(x,y));draw.text((x+10,y+362),row['name']+' G'+str(row['generation']),fill=(25,25,25))
            if row['projection_vertices_outside_frame']:draw.text((x+10,y+378),'CLIPPED: '+str(row['projection_vertices_outside_frame'])+' vertices',fill=(170,25,25))
        sheet.save(out/(view+'_contact_sheet.png'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--names',nargs='+');p.add_argument('--pass-id')
    p.add_argument('--generations',nargs='+',type=int,default=[1]);p.add_argument('--tag',required=True);p.add_argument('--resolution',type=int,default=640)
    p.add_argument('--width',type=float,default=4000);p.add_argument('--target',nargs=3,type=float,default=[0,0,900]);p.add_argument('--views',nargs='+',default=['front','oblique']);p.add_argument('--worker',action='store_true')
    p.add_argument('--task27-target',nargs=3,type=float,default=[-400.036865234375,-18.533447265625,1750])
    a=p.parse_args();names=a.names or read(a.output_root/'definitions'/('pass'+a.pass_id+'.json'))['candidates']
    if a.worker:capture(a.output_root,names,a.generations,a.tag,a.resolution,a.width,a.views,a.target,a.task27_target)
    else:
        args=['--output-root',str(a.output_root),'--names',*names,'--generations',*map(str,a.generations),'--tag',a.tag,'--resolution',str(a.resolution),'--width',str(a.width),'--views',*a.views,'--target',*map(str,a.target),'--task27-target',*map(str,a.task27_target),'--worker']
        logs=a.output_root/'logs'/('capture_'+a.tag)
        if logs.exists():raise ValueError('Preserve prior capture logs.')
        r=guarded(args,logs,worker_script=Path(__file__));print(r,flush=True);sys.exit(r['exit_code'])
