"""Analytical plane intersections of actual saved polygons, image evidence.

Triangulation is for section sampling only; checkpoint polygons are unchanged.
Segments are not falsely labelled closed loops or fabricated solid validation.
"""
import argparse,gc,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from task31_study import ROOT,read,write,file_hash,load_mesh
from hero_design_sprint import guarded


def section(mesh,axis,position):
    segments=[]
    for start in range(0,len(mesh.faces),50000):
        q=mesh.faces[start:start+50000]
        tri=np.concatenate([q[q[:,k]>=0][:,[0,k-1,k]] for k in range(2,q.shape[1])])
        p=mesh.xyz[tri];d=p[:,:,axis]-position
        nxt=np.roll(p,-1,axis=1);dn=np.roll(d,-1,axis=1)
        cross=(d<0)!=(dn<0);valid=cross.sum(1)==2
        t=np.divide(d,d-dn,out=np.zeros_like(d),where=d!=dn)
        hits=p+t[:,:,None]*(nxt-p)
        segments.append(hits[valid][cross[valid]].reshape(-1,2,3))
    return np.concatenate(segments)


def make(kind):
    lead=read(ROOT/'definitions/task31_lead_pipeline.json')[kind]
    names=['TASK30','OPEN_85',lead['id'],'AXIS_DEPTH'] if kind=='cube' else ['TASK30_GATE',lead['id']]
    paths=[ROOT/'controls/cube/G8',ROOT/'candidates/cube/OPEN_85/G8',ROOT/'candidates/cube'/lead['id']/'G8',ROOT/'candidates/cube/AXIS_DEPTH/G8'] if kind=='cube' else [ROOT/'candidates/gate'/name/'G8' for name in names]
    axes=[0,2] if kind=='cube' else [1]
    position=-57.63561231649889+.1 if kind=='cube' else -18.533447265625+.1
    if kind=='cube':
        response=read(ROOT/'analysis/regional_response_cube.json')
        channel=next(r for row in response if row['id']=='AXIS_DEPTH' for r in row['regions'] if r['mode']=='CHANNEL')
        position=float(channel['weighted_centroid'][0])+.1
    target=ROOT/'analysis/sections';target.mkdir(exist_ok=True)
    if kind=='cube' and (target/'cube_manifest.json').exists():
        backup=target/'prior_G2_plane';backup.mkdir(exist_ok=False)
        for p in target.glob('cube_*'):shutil.copy2(p,backup/p.name)
        shutil.copy2(ROOT/'renders/TASK31_cube_sections.png',backup/'TASK31_cube_sections.png')
    out=Image.new('RGB',(1600*len(axes),900*len(names)),(245,245,242));draw=ImageDraw.Draw(out)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',28);records=[]
    for row,(name,path) in enumerate(zip(names,paths)):
        m=load_mesh(path)
        for col,axis in enumerate(axes):
            lines=section(m,axis,position);xy=[j for j in range(3) if j!=axis]
            frame=[[-650,650],[-650,650]] if kind=='cube' else [[-3100,2300],[-500,4200]]
            sx=1440/(frame[0][1]-frame[0][0]);sy=740/(frame[1][1]-frame[1][0]);scale=min(sx,sy)
            center=np.mean(frame,axis=1);uv=(lines[:,:,xy]-center)*scale
            uv[:,:,0]+=col*1600+800;uv[:,:,1]=row*900+420-uv[:,:,1]
            for pair in uv:draw.line([tuple(pair[0]),tuple(pair[1])],fill=(42,53,55),width=1)
            label=f'{name} | {"XYZ"[axis]}={position:.3f} | actual G8 section'
            draw.text((col*1600+30,row*900+835),label,font=font,fill=(25,25,25))
            saved=target/(kind+'_'+name+f'_axis{axis}.npz');np.savez_compressed(saved,segments=lines,axis=axis,position=position)
            records.append(dict(name=name,checkpoint=str(path),mesh_sha256=file_hash(path/'mesh.npz'),axis=axis,position=position,
                segment_count=len(lines),section_sha256=file_hash(saved),frame=frame))
        del m;gc.collect()
    saved=ROOT/'renders'/('TASK31_'+kind+'_sections.png');out.save(saved)
    write(target/(kind+'_manifest.json'),dict(records=records,image_sha256=file_hash(saved),
        caveat='Actual triangle-plane segments; no Boolean solid claim. Same physical frame/plane in comparisons; .1-unit offset avoids coplanar sample degeneracy.',
        plane_selection='Cube final AXIS_DEPTH CHANNEL centroid X + .1, same scalar plane for X/Z and all comparisons; earlier G2 mouth-plane comparison retained separately. Gate original Y frame + .1.'))
    print('Saved actual',kind,'analytical section comparisons.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['cube','gate']);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:make(a.kind)
    else:
        result=guarded([a.kind,'--worker'],ROOT/'logs'/('sections_'+a.kind),worker_script=__file__);print(result,flush=True);raise SystemExit(result['exit_code'])
