"""Supplementary matched raking light; native flat normals, no geometry edits."""
import gc,json,sys
from pathlib import Path
import numpy as np
import trimesh,pyrender
from PIL import Image
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import ROOT,sha,write_new
from task29_search import load_mesh
from task30_views import sheet
from progressive_gate_views import pose,orthographic_depth
from cheshire.task32_morphology import triangles
from hero_design_sprint import windows_memory


def raking(request,tag):
    request=Path(request);definition=json.loads(request.read_text());dest=ROOT/'renders'/tag
    dest.mkdir(parents=True,exist_ok=False)
    write_new(dest/'request.json',definition);records=[]
    resolution=definition.get('resolution',1400)
    renderer=pyrender.OffscreenRenderer(resolution,resolution)
    from OpenGL.GL import glGetString,GL_RENDERER
    backend=glGetString(GL_RENDERER).decode()
    try:
        for i,item in enumerate(definition['items']):
            stage=Path(item['stage']);summary=json.loads((stage/'summary.json').read_text())
            forecast=512*1024**2+summary['faces']*1200
            memory=windows_memory()
            if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):
                raise MemoryError('Render forecast exceeds measured reserve.')
            mesh=load_mesh(stage);tri=triangles(mesh)
            model=trimesh.Trimesh(vertices=mesh.xyz,faces=tri,process=False)
            mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.65,.65,.63,1],roughnessFactor=.9,metallicFactor=0,doubleSided=True)
            target=item.get('target',definition['target']);width=item.get('width',definition['width'])
            camera=pose(*item['angles'],target)
            scene=pyrender.Scene(bg_color=[.96,.96,.95,1],ambient_light=[.08]*3)
            scene.add(pyrender.Mesh.from_trimesh(model,material=mat,smooth=False))
            scene.add(pyrender.OrthographicCamera(xmag=width/2,ymag=width/2,znear=1,zfar=30000),pose=camera)
            scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=2.0),pose=pose(-65,25,target))
            scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=.18),pose=pose(65,10,target))
            colour,raw=renderer.render(scene)
            path=dest/f'{i:03}_{item["label"]}.png';Image.fromarray(colour).save(path)
            depth=orthographic_depth(raw,1,30000)
            np.savez_compressed(path.with_suffix('.visibility.npz'),depth=depth.astype(np.float32),hit=depth>0)
            projected=(mesh.xyz-np.asarray(target))@camera[:3,:2]
            records.append(dict(**item,image=str(path),mesh_sha256=sha(stage/'mesh.npz'),image_sha256=sha(path),
                visibility_sha256=sha(path.with_suffix('.visibility.npz')),camera_pose=camera.tolist(),physical_width=width,
                vertices=len(mesh.xyz),triangles=len(tri),flat_normals=True,geometric_smoothing=False,
                outside_frame=int((np.abs(projected)>width/2).any(1).sum()),
                display_float32_max_error=float(np.abs(mesh.xyz-mesh.xyz.astype(np.float32).astype(float)).max()),
                forecast_working_bytes=forecast,available_before=memory))
            del model,mesh,tri,scene,colour,raw,depth,projected;gc.collect()
    finally:renderer.delete()
    write_new(dest/'manifest.json',dict(records=records,backend=backend,request_sha256=sha(request),producer_sha256=sha(Path(__file__)),
        light='All rows: key -65/25 intensity2.0, fill65/10 intensity0.18, ambient0.08; no shadow maps; same clay0.65/0.65/0.63.',
        limitations='Supplement to original standard-light evidence, not a new geometry or validity proof. No smooth normals, per-row framing/lighting adjustment or defect removal.'))
    sheet(records,ROOT/'renders'/definition['sheet_name'],definition.get('cols',3),definition.get('size',520))
