"""Small immutable primal comparison; no repairs, failures retained."""
import argparse,json,sys,hashlib,shutil
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.astra_primal import step
from cheshire.task36_growth import carrier,native
from cheshire.reference_subdivision import cube,metrics
from task29_search import save_mesh,load_mesh
from task36_contacts import contacts
from hero_design_sprint import windows_memory


def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--generations',type=int,default=4)
    ap.add_argument('--render',action='store_true');ap.add_argument('--blend',type=float,default=1.)
    ap.add_argument('--shapes',nargs='+',choices=['column','cube'],default=['column','cube'])
    ap.add_argument('--cases',nargs='+');ap.add_argument('--cap-policy',choices=['plane','none'],default='plane')
    ap.add_argument('--w4',type=float,default=.9)
    ap.add_argument('--directional',action='store_true')
    ap.add_argument('--signed-limit',type=float,default=1.4)
    args=ap.parse_args()
    if not 1<=args.generations<=5:raise ValueError('Small G1..5 probe only.')
    root=Path('E:/CHESHIRE_DATA/astra_research/primal_probe')/args.tag;root.mkdir(parents=True,exist_ok=False)
    memory=windows_memory();forecast=4**args.generations*40*1800+512*1024**2
    if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Resource reserve.')
    write(root/'preflight.json',dict(memory=memory,forecast_bytes=forecast))
    sources={}
    for rel in ['src/cheshire/astra_primal.py','src/cheshire/reference_subdivision.py','src/cheshire/task36_growth.py','tools/astra_primal_probe.py','tools/task36_contacts.py','tools/task36_triangle_interval.py','tools/native/Task36Bounds.cs']:
        dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest);sources[rel]=sha(dest)
    write(root/'source_identity.json',sources)
    cases={'P00_CONSTANT':dict(),'P01_INTRINSIC':dict(intrinsic=1.),'P02_SPATIAL':dict(spatial=1.),
        'P03_COMBINED':dict(intrinsic=1.,spatial=1.),'P04_FROZEN':dict(intrinsic=1.,spatial=1.,source='rest')}
    if args.directional:
        cases={'R00_BASE':dict(),'R01_SIGNED':dict(signed_stencil=True),
            'R02_SUPPORT':dict(support_normalization=True),
            'R03_BOTH':dict(signed_stencil=True,support_normalization=True),
            'R04_FROZEN':dict(signed_stencil=True,support_normalization=True,source='rest')}
    if args.cases:
        if set(args.cases)-set(cases):raise ValueError('Unknown case.')
        cases={key:cases[key] for key in args.cases}
    records=[]
    for shape in args.shapes:
        for name,params in cases.items():
            label=shape+'_'+name;job=root/label;job.mkdir();params=dict(params,blend=args.blend,cap_policy=args.cap_policy if shape=='column' else 'none',w4=args.w4,signed_limit=args.signed_limit)
            write(job/'recipe.json',params);mesh=carrier() if shape=='column' else cube();history=[];parent=None
            for g in range(args.generations+1):
                start=perf_counter()
                if g:mesh,meta,state=step(mesh,**params)
                else:meta={};state={}
                stage=job/f'G{g}';physical=native(mesh);save_mesh(stage,physical,meta,state,parent)
                np.savez_compressed(stage/'quad_state.npz',xyz=mesh.xyz,faces=mesh.faces,rest=mesh.rest,classes=mesh.classes,anchors=mesh.anchors,generation=mesh.generation)
                check=contacts(physical,cap=256,interval=True,include_shared=True)
                from scipy.spatial import cKDTree
                tree=cKDTree(physical.xyz);sym={axis:float(tree.query(physical.xyz*np.array(sign))[0].max()) for axis,sign in [('x',[-1,1,1]),('y',[1,-1,1])]}
                rec=dict(generation=g,stage=str(stage),metrics=metrics(physical),contacts=check,symmetry_nearest=sym,seconds=perf_counter()-start)
                if g:
                    rec['features']={key:np.quantile(state[key],[0,.1,.5,.9,1]).tolist() for key in ['feature_aspect','feature_planarity','feature_bend','combined_signal']}
                    rec['w4_counts']=dict(negative=int((state['resolved_w4']<0).sum()),positive=int((state['resolved_w4']>0).sum()),zero=int((state['resolved_w4']==0).sum()))
                    rec['applied_displacement_quantiles']=np.quantile(np.linalg.norm(state['applied_displacement'],axis=1),[0,.1,.5,.9,1]).tolist()
                write(stage/'validation.json',rec);history.append(rec);parent=stage
                print(label,g,'contacts',check['transverse_contacts'],'extent',rec['metrics']['extent'],flush=True)
                if check['transverse_contacts'] or rec['metrics']['zero_area_faces']:break
            write(job/'history.json',history);records.append(dict(candidate=label,shape=shape,history=history))
    write(root/'summary.json',records)
    if args.render:render(root,records)


def render(root,records):
    import pyrender,trimesh
    from PIL import Image,ImageDraw
    from progressive_gate_views import pose
    from cheshire.task32_morphology import triangles
    resolution=520;renderer=pyrender.OffscreenRenderer(resolution,resolution);images=[];manifest=[]
    dest=root/'renders';dest.mkdir()
    try:
        for candidate in records:
            for index in [1,len(candidate['history'])-1]:
                stage=Path(candidate['history'][index]['stage']);mesh=load_mesh(stage)
                for view,angles in [('front',(0,0)),('oblique',(28,22))]:
                    label=candidate['candidate']+'_'+stage.name+'_'+view
                    target=[0,0,2000] if candidate['shape']=='column' else [0,0,0]
                    width=4800 if candidate['shape']=='column' else 2200
                    model=trimesh.Trimesh(vertices=mesh.xyz,faces=triangles(mesh),process=False)
                    mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.65,.65,.63,1],roughnessFactor=.9,metallicFactor=0,doubleSided=True)
                    scene=pyrender.Scene(bg_color=[.96,.96,.95,1],ambient_light=[.08]*3)
                    scene.add(pyrender.Mesh.from_trimesh(model,material=mat,smooth=False))
                    camera=pose(*angles,target);scene.add(pyrender.OrthographicCamera(xmag=width/2,ymag=width/2,znear=1,zfar=30000),pose=camera)
                    for a,b,intensity in [(-65,25,2.),(65,10,.18)]:scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=intensity),pose=pose(a,b,target))
                    color,_=renderer.render(scene);im=Image.fromarray(color);ImageDraw.Draw(im).text((8,8),label,fill=(0,0,0));im.save(dest/(label+'.png'));images.append(im)
                    projected=(mesh.xyz-np.asarray(target))@camera[:3,:2]
                    manifest.append(dict(label=label,stage=str(stage),mesh_sha256=sha(stage/'mesh.npz'),image_sha256=sha(dest/(label+'.png')),camera_width=width,angles=angles,target=target,outside_frame=int((np.abs(projected)>width/2).any(1).sum())))
    finally:renderer.delete()
    sheet=Image.new('RGB',(resolution*4,resolution*len(records)),(255,255,255))
    for i,im in enumerate(images):sheet.paste(im,((i%4)*resolution,(i//4)*resolution))
    sheet.save(dest/'comparison.png');write(dest/'manifest.json',manifest)


if __name__=='__main__':main()
