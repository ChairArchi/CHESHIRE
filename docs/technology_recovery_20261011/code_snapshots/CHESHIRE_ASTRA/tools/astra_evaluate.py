"""Fixed-camera and actual triangle-cut evidence for independent experiments.

Input JSON is an ordered list {id,stage}; no automatic candidate selection.
All source meshes remain immutable. Current geometry, not shading, is cut.
"""
import argparse,json,sys,hashlib,shutil,re
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task36_contacts import contacts
from task32_validation import embedding
from task33_planar import inspect_segments
from task35_analyze import radial_cut,longitudinal_profile,child_valleys,open_valleys
from hero_design_sprint import guarded,windows_memory
from scipy.spatial import cKDTree

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')

def render(mesh,dest,label,renderer,target,width,warning=""):
    import pyrender,trimesh
    from PIL import Image,ImageDraw
    from progressive_gate_views import pose
    model=trimesh.Trimesh(vertices=mesh.xyz,faces=mesh.faces[:,:3],process=False)
    material=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.65,.65,.63,1],roughnessFactor=.9,metallicFactor=0,doubleSided=True)
    pictures=[]
    for view,angles in [('front',(0,0)),('oblique',(28,22)),('side',(90,0))]:
        scene=pyrender.Scene(bg_color=[.96,.96,.95,1],ambient_light=[.08]*3)
        scene.add(pyrender.Mesh.from_trimesh(model,material=material,smooth=False))
        scene.add(pyrender.OrthographicCamera(xmag=width/2,ymag=width/2,znear=1,zfar=30000),pose=pose(*angles,target))
        for a,b,intensity in [(-65,25,2.),(65,10,.18)]:scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=intensity),pose=pose(a,b,target))
        rgb,_=renderer.render(scene);im=Image.fromarray(rgb)
        ImageDraw.Draw(im).text((10,10),label+' '+view+warning,fill=(0,0,0));name=label+'_'+view+'.png';im.save(dest/name)
        pictures.append(im)
    return pictures

def cut_picture(raw,label,dest):
    from PIL import Image,ImageDraw
    size=500;names=[k for k in raw if not k.endswith(('_profile','_triangle_ids'))];sheet=Image.new('RGB',(size*4,size*4),'white');draw=ImageDraw.Draw(sheet)
    for i,name in enumerate(names):
        lines=raw[name];x=(i%4)*size;y=(i//4)*size
        if name.startswith('Z'):uv=lines[:,:,[0,1]];lo=np.array([-1800.,-1800.]);span=np.array([3600.,3600.])
        else:
            uv=lines[:,:,[0,2]] if name=='XZ' else lines[:,:,[1,2]] if name=='YZ' else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
            lo=np.array([-2500.,-500.]);span=np.array([5000.,5000.])
        pixels=(uv-lo)/span*(size-40)
        for line in pixels:draw.line([(x+20+float(p[0]),y+size-20-float(p[1])) for p in line],fill=(35,45,60),width=1)
        draw.text((x+10,y+8),label+' '+name,fill=(0,0,0))
    sheet.save(dest/(label+'_cuts.png'))

def evaluate(items,root,rendering=True):
    import trimesh
    from PIL import Image
    renderer=None;rows=[];pictures=[]
    if rendering:
        import pyrender
        renderer=pyrender.OffscreenRenderer(600,600)
    try:
        for item in items:
            start=perf_counter();stage=Path(item['stage']);label=item['id']
            if not label.replace('_','').isalnum():raise ValueError('Safe unique label required.')
            dest=root/label;dest.mkdir(exist_ok=False)
            m=load_mesh(stage)
            if not np.all((m.faces>=0).sum(1)==3):raise ValueError('Authoritative native triangle surface required; no implicit truncation.')
            if not np.isfinite(m.xyz).all():raise ValueError('Nonfinite input.')
            match=re.search(r'_G([0-9]+)$',label)
            if match is None or int(match.group(1))!=m.generation:raise ValueError('Label must end in exact native _G<generation>.')
            stage_match=re.match(r'G([0-9]+)(?:_|$)',stage.name)
            if stage_match and int(stage_match.group(1))!=m.generation:raise ValueError('Stage directory/native generation mismatch.')
            forecast=512*1024**2+len(m.faces)*1800;memory=windows_memory()
            if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Forecast exceeds available reserve.')
            check=contacts(m,cap=512,interval=True,include_shared=True)
            tree=cKDTree(m.xyz)
            sym={name:float(tree.query(m.xyz*np.array(sign))[0].max()) for name,sign in [('X',[-1,1,1]),('Y',[1,-1,1])]}
            row=dict(**item,sha256=sha(stage/'mesh.npz'),generation=m.generation,vertices=len(m.xyz),triangles=len(m.faces),extent=np.ptp(m.xyz,axis=0).tolist(),embedding=embedding(m),contacts=check,symmetry_nearest=sym,symmetry_limit='Nearest geometric match only; does not prove bijection or oriented topology.',forecast_bytes=forecast)
            model=trimesh.Trimesh(vertices=m.xyz,faces=m.faces[:,:3],process=False);raw={};cuts=[]
            # Longitudinal profiles are fixed world Z=0..4000; raw cuts have no such restriction.
            planes=[('Z'+str(z),[0,0,z+.12345],[0,0,1],[0,1]) for z in item.get('section_z',list(range(500,3501,250)))]
            planes += [('XZ',[0,0,0],[0,1,0],[0,2]),('YZ',[0,0,0],[1,0,0],[1,2]),('DIAGONAL',[0,0,0],[1,-1,0],None)]
            for name,origin,normal,axes in planes:
                lines,face_ids=trimesh.intersections.mesh_plane(model,normal,origin,return_faces=True);raw[name]=lines;raw[name+'_triangle_ids']=face_ids
                uv=lines[:,:,axes] if axes else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
                info=dict(name=name,**inspect_segments(uv))
                if len(lines):
                    signal,coverage=radial_cut(lines) if name.startswith('Z') else longitudinal_profile(lines,name)
                    raw[name+'_profile']=signal;info['coverage']=coverage
                cuts.append(info)
            np.savez_compressed(dest/'cuts.npz',**raw);cut_picture(raw,label,dest)
            row['cuts']=cuts;row['seconds']=perf_counter()-start
            row['longitudinal_profile_domain']=[0,4000]
            row['limitations']='Longitudinal profile uses fixed Z=0..4000; arbitrary inputs should use raw cuts. Zero transverse contacts excludes coplanar overlap and boundary-only tangency. Finite cuts are not continuous ridge certification. Current labels are bound to SHA/native generation.'
            if renderer:
                pictures.extend(render(m,dest,label,renderer,item.get('target',[0,0,2000]),item.get('camera_width',5000),' INVALID' if check['transverse_contacts'] else ''))
                render(m,dest,label+'_detail',renderer,item.get('detail_target',[0,0,1000]),1800,' INVALID' if check['transverse_contacts'] else '')
                row['camera']=dict(target=item.get('target',[0,0,2000]),width=item.get('camera_width',5000),views={'front':[0,0],'oblique':[28,22],'side':[90,0]},smooth_shading=False,metallic_factor=0,roughness=.9,base_color=[.65,.65,.63])
            row['artifact_sha256']={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
            write(dest/'audit.json',row);rows.append(row);print(label,'contacts',check['transverse_contacts'],'seconds',round(row['seconds'],2),flush=True)
    finally:
        if renderer:renderer.delete()
    if pictures:
        sheet=Image.new('RGB',(1800,600*len(items)),'white')
        for i,im in enumerate(pictures):sheet.paste(im,((i%3)*600,(i//3)*600))
        sheet.save(root/'comparison.png')
    write(root/'summary.json',rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');p.add_argument('--no-render',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required.')
    root=Path('E:/CHESHIRE_DATA/astra_research/evaluation')/a.tag
    if a.worker:evaluate(json.loads((root/'request.json').read_text()),root,not a.no_render);return
    root.mkdir(parents=True,exist_ok=False);shutil.copy2(a.request,root/'request.json');shutil.copy2(Path(__file__),root/'source.py')
    args=['--request',str(root/'request.json'),'--tag',a.tag,'--worker']+(['--no-render'] if a.no_render else [])
    result=guarded(args,root/'logs/run',worker_script=Path(__file__));write(root/'execution.json',result)
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
