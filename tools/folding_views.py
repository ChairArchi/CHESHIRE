"""Registered whole-gate and lintel views through the existing projection route."""
import argparse
from pathlib import Path
import shutil
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from cross_cell_crease_study import read,write,file_hash
from hero_design_views import matrix,rotated


CAMERAS={
    'front':(0,0,[-400,0,2000],8600),
    'oblique':(32,16,[-400,0,2000],8600),
    'underside':(0,-30,[-400,0,2000],8600),
    'detail':(0,-12,[-400,0,2450],1800),
    'detail_angle':(18,-25,[-400,0,2450],1800),
    'close':(0,-12,[-400,0,2390],800),
}


def prepare(root,names,tag,views=None,reuse_tags=()):
    cameras={k:v for k,v in CAMERAS.items() if views is None or k in views}
    out=root/'renders'/tag;out.mkdir(parents=True,exist_ok=True);frames=[];records=[]
    reusable={}
    renderer_hash=file_hash(REPO/'tools/crease_projection.ps1')
    for previous in reuse_tags:
        folder=root/'renders'/previous
        manifest=read(folder/'camera_manifest.json')
        if manifest['renderer_sha256']!=renderer_hash:continue
        for row in manifest['records']:reusable[(row['id'],row['view'])]=(folder,row)
    for name in names:
        if name in ('H1','H2_R1','H3_R3'):
            directory=root/'inputs'/name;path=directory/'terminal.json.gz'
        else:
            directory=sorted((root/'designs'/name).glob('attempt_*'))[-1];path=directory/'geometry.json.gz'
            if read(directory/'summary.json')['status']!='SUCCESS':raise ValueError('No completed real mesh.')
        data=None;input_hash=file_hash(path)
        for view,(azimuth,elevation,target,width) in cameras.items():
            m=matrix(azimuth,elevation);t=[sum(a*b for a,b in zip(row,target)) for row in m]
            filename=name+'_'+view+'.json'
            bounds=[t[0]-width/2,t[0]+width/2,t[2]-width/2,t[2]+width/2]
            frame=dict(mesh=filename,file=name+'_'+view+'.png',label=name+' / '+view+' / actual polygons',
                camera='front',width=800,height=800,bounds=bounds)
            prior=reusable.get((name,view));reused=None
            if prior:
                folder,row=prior
                if row['input_sha256']==input_hash and row['matrix']==m and row['target']==target and row['world_frame_width']==width:
                    images=[frame['file']]+([name+'_wire.png'] if view=='close' else [])
                    if all((folder/n).exists() for n in images):
                        reused={n:dict(source=str(folder/n),sha256=file_hash(folder/n)) for n in images}
                        for n in images:shutil.copyfile(folder/n,out/n)
            if not reused:
                if data is None:data=read(path)
                write(out/filename,rotated(data,m));frames.append(frame)
                if view=='close':frames.append({**frame,'file':name+'_wire.png','label':name+' / actual wire / unculled','wireframe':True})
            records.append(dict(id=name,view=view,input=str(path),input_sha256=input_hash,
                matrix=m,target=target,world_frame_width=width,bounds=bounds,
                reused_actual_image=reused,
                projection='Orthographic; same fixed region in original model coordinates.',
                processing='Display camera rotation only; original geometry and coordinates preserved.'))
            print(name,view,'reuse' if reused else 'prepared',flush=True)
    sheets=[dict(file='comparison_'+view+'.png',title='Task25 / '+view+' / FIXED REGION AND MODEL SCALE / painter occlusion approximate',
        images=[n+'_'+view+'.png' for n in names],width=800,height=800,columns=len(names)) for view in cameras]
    if 'close' in cameras:
        sheets.append(dict(file='comparison_wire.png',title='Task25 / actual geometric edges / unculled',
            images=[n+'_wire.png' for n in names],width=800,height=800,columns=len(names)))
    write(out/'camera_manifest.json',dict(records=records,renderer='Existing tools/crease_projection.ps1 / System.Drawing painter projection',
        renderer_sha256=renderer_hash,
        limitation='Flat polygon normals, no ray tracing, pixel z buffer or AO; crossing occlusion approximate. Not a DCC viewport or beauty render.'))
    write(out/'projection_plan.json',dict(frames=frames,sheets=sheets));return out/'projection_plan.json'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--names',nargs='+',required=True);p.add_argument('--tag',required=True)
    p.add_argument('--views',nargs='+',choices=list(CAMERAS))
    p.add_argument('--reuse-tags',nargs='+',default=[])
    a=p.parse_args();print(prepare(a.output_root,a.names,a.tag,a.views,a.reuse_tags),flush=True)
