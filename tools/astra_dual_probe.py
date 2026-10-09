"""Small immutable DS competition probe; actual native geometry, no smoothing."""
import argparse,json,sys,hashlib,shutil
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.astra_dual import step,native,refine_fan
from cheshire.task36_growth import carrier
from cheshire.reference_subdivision import metrics
from cheshire.reference_subdivision import subdivide
from cheshire.dual_subdivision import doo_sabin
from task29_search import save_mesh
from task36_contacts import contacts
from hero_design_sprint import windows_memory


def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--generations',type=int,default=4)
    ap.add_argument('--render',action='store_true');ap.add_argument('--hybrid',action='store_true')
    ap.add_argument('--published-mix',action='store_true');ap.add_argument('--double-primal',action='store_true')
    ap.add_argument('--roles',action='store_true');ap.add_argument('--role-gain',type=float,default=.3);args=ap.parse_args()
    if args.double_primal and not args.published_mix:raise ValueError('Double-primal is an explicitly published mixed control.')
    if not 1<=args.generations<=6:raise ValueError('This is explicitly a small prototype.')
    root=Path('E:/CHESHIRE_DATA/astra_research/dual_probe')/args.tag;root.mkdir(parents=True,exist_ok=False)
    memory=windows_memory();forecast=(4**args.generations)*40*1800+512*1024**2
    if forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Resource forecast exceeds existing reserve.')
    write(root/'preflight.json',dict(memory=memory,forecast_bytes=forecast))
    sources={}
    for rel in ['src/cheshire/astra_dual.py','src/cheshire/dual_subdivision.py','src/cheshire/reference_subdivision.py','tools/astra_dual_probe.py']:
        dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest);sources[rel]=sha(dest)
    write(root/'source_identity.json',sources)
    cases={
      'D00_REFERENCE':dict(tension=.65,fold_gain=0,feedback=0),
      'D01_WIDTH':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=0),
      'D02_CORNERS':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5),
      'D03_REST':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5,source='rest'),
      'D04_STRONG':dict(tension=.7,fold_gain=.4,feedback=.8,corner_gain=.6),
      'D05_RETENTION':dict(tension=.85,fold_gain=.2,feedback=.6,corner_gain=.5),
    }
    if args.hybrid:
        cases={
          'H00_REFERENCE':dict(tension=.65,fold_gain=0,feedback=0),
          'H01_CURRENT':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5),
          'H02_REST':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5,source='rest'),
          'H03_STRONG':dict(tension=.7,fold_gain=.4,feedback=.8,corner_gain=.6),
        }
    if args.published_mix:
        cases={
          'C00_CC_ONLY':{},
          'C01_PUBLISHED_DS_CC':dict(w1=.6,wf=.03),
          'C02_CURRENT_DS_CC':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5),
          'C03_REST_DS_CC':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5,source='rest'),
          'C04_STRONG_DS_CC':dict(tension=.7,fold_gain=.4,feedback=.8,corner_gain=.6),
        }
        if args.double_primal:cases={k:v for k,v in cases.items() if k in ['C01_PUBLISHED_DS_CC','C02_CURRENT_DS_CC','C03_REST_DS_CC']}
    if args.roles:
        cases={
          'R00_SCALAR_ONLY':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5),
          'R01_ORIGIN_ONLY':dict(tension=.65,fold_gain=0,feedback=0,role_gain=args.role_gain),
          'R02_ORIGIN_CURRENT':dict(tension=.65,fold_gain=.2,feedback=.6,corner_gain=.5,role_gain=args.role_gain),
        }
        if args.role_gain!=.3:cases.pop('R00_SCALAR_ONLY')
    records=[]
    for name,params in cases.items():
        job=root/name;job.mkdir();write(job/'recipe.json',dict(dual=params,primal=dict(w1=-.18,w2=-.3,w3=-.9,w4=.5),
            schedule='CC only' if name=='C00_CC_ONLY' else ('DS/CC/CC repeat' if args.double_primal else 'odd DS, even published coupled CC')) if args.published_mix else params)
        mesh=carrier();roles=None;parent=None;history=[]
        for g in range(args.generations+1):
            start=perf_counter()
            if g and args.published_mix and ((g%3!=1 if args.double_primal else g%2==0) or name=='C00_CC_ONLY'):
                mesh,meta,state=subdivide(mesh,dict(w1=-.18,w2=-.3,w3=-.9,w4=.5));roles=None
            elif g and args.published_mix and name=='C01_PUBLISHED_DS_CC':
                mesh,roles,meta,state=doo_sabin(mesh,params,face_roles=roles)
            elif g and args.hybrid and g%2==0:
                mesh,state=refine_fan(mesh);roles=None;meta=dict(operation='surface_preserving_split')
            elif g:mesh,roles,meta,state=step(mesh,roles,**params)
            else:meta={};state={}
            stage=job/f'G{g}';physical=native(mesh);save_mesh(stage,physical,meta,state,parent)
            np.savez_compressed(stage/'quad_state.npz',xyz=mesh.xyz,faces=mesh.faces,rest=mesh.rest,classes=mesh.classes,
                anchors=mesh.anchors,generation=mesh.generation,roles=np.array([]) if roles is None else roles,surface=getattr(mesh,'surface','mean'))
            check=contacts(physical,cap=256,interval=True,include_shared=True)
            from scipy.spatial import cKDTree
            tree=cKDTree(physical.xyz)
            sym={axis:float(tree.query(physical.xyz*np.array(sign))[0].max()) for axis,sign in [('x',[-1,1,1]),('y',[1,-1,1])]}
            rec=dict(generation=g,stage=str(stage),metrics=metrics(physical),contacts=check,symmetry_nearest=sym,seconds=perf_counter()-start)
            if g and 'feature_width_contrast' in state:
                rec['width_contrast_quantiles']=np.quantile(state['feature_width_contrast'],[0,.1,.5,.9,1]).tolist()
                rec['normal_offset_quantiles']=np.quantile(state['resolved_corner_offset'],[0,.1,.5,.9,1]).tolist()
            write(stage/'validation.json',rec);history.append(rec);parent=stage
            print(name,g,'contacts',check['transverse_contacts'],'extent',rec['metrics']['extent'],flush=True)
            if check['transverse_contacts'] or rec['metrics']['zero_area_faces']:break
        write(job/'history.json',history);records.append(dict(candidate=name,history=history))
    write(root/'summary.json',records)
    if args.render:render(root,records)


def render(root,records,directory='renders'):
    import pyrender,trimesh
    from PIL import Image,ImageDraw
    from progressive_gate_views import pose
    from task29_search import load_mesh
    from cheshire.task32_morphology import triangles
    resolution=600;renderer=pyrender.OffscreenRenderer(resolution,resolution);images=[];manifest=[]
    dest=root/directory;dest.mkdir()
    try:
        for candidate in records:
            for index in [1,len(candidate['history'])-1]:
                stage=Path(candidate['history'][index]['stage']);mesh=load_mesh(stage)
                for view,angles in [('front',(0,0)),('oblique',(28,22))]:
                    label=candidate['candidate']+'_'+stage.name+'_'+view;target=[0,0,2000];width=6000
                    model=trimesh.Trimesh(vertices=mesh.xyz,faces=triangles(mesh),process=False)
                    mat=pyrender.MetallicRoughnessMaterial(baseColorFactor=[.65,.65,.63,1],roughnessFactor=.9,doubleSided=True)
                    scene=pyrender.Scene(bg_color=[.96,.96,.95,1],ambient_light=[.08]*3)
                    scene.add(pyrender.Mesh.from_trimesh(model,material=mat,smooth=False))
                    scene.add(pyrender.OrthographicCamera(xmag=width/2,ymag=width/2,znear=1,zfar=30000),pose=pose(*angles,target))
                    for a,b,intensity in [(-65,25,2.),(65,10,.18)]:scene.add(pyrender.DirectionalLight(color=np.ones(3),intensity=intensity),pose=pose(a,b,target))
                    color,_=renderer.render(scene);im=Image.fromarray(color);im.save(dest/(label+'.png'))
                    invalid=candidate['history'][index]['contacts']['transverse_contacts']>0
                    ImageDraw.Draw(im).text((8,8),label+(' INVALID CROSSINGS' if invalid else ''),fill=(0,0,0));images.append(im)
                    projected=(mesh.xyz-np.array(target))@pose(*angles,target)[:3,:2]
                    manifest.append(dict(label=label,stage=str(stage),mesh_sha256=sha(stage/'mesh.npz'),image_sha256=sha(dest/(label+'.png')),camera_width=width,angles=angles,target=target,
                        outside_frame=int((np.abs(projected)>width/2).any(1).sum()),invalid_crossings=invalid,producer_sha256=sha(Path(__file__))))
    finally:renderer.delete()
    sheet=Image.new('RGB',(resolution*4,resolution*len(records)),(255,255,255))
    for i,im in enumerate(images):sheet.paste(im,((i%4)*resolution,(i//4)*resolution))
    sheet.save(dest/'comparison.png');write(dest/'manifest.json',manifest)


if __name__=='__main__':main()
