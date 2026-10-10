"""G8-only controlled DS extrusion ablation. Reuses verified topology, not smoothing.
Run from repository root with .venv/Scripts/python.exe -B this_file.py.
"""
import json, sys, gc, argparse
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageDraw
R=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=R.parents[1]/'outputs/expansion_control_20261010');args=parser.parse_args()
O=args.output.resolve()
if (O/'measurements.json').exists():raise FileExistsError('Use a fresh --output directory; completed comparison is preserved')
O.mkdir(exist_ok=True)
def read(p): return json.loads(p.read_text())
p=read(R/'published_column_vertex7_results/g07/mesh.json')
b=read(R/'published_column_vertex8_results/g08/mesh.json')
v=np.asarray(p['vertices']); bv=np.asarray(b['vertices']); faces=b['faces']
meta=read(R/'published_column_vertex8_results/g08/operator_metadata.json')
records=meta['points']
assert len(records)==len(bv)
effective=np.array([[r['effective']['w1'],r['effective']['w10']] for r in records])
assert all(r['weighted_supported'] for r in records)
del records,meta;gc.collect()
lengths=np.array([len(f) for f in p['faces']]); assert set(lengths)<={3,4}
offset=np.r_[0,np.cumsum(lengths)]
normals=np.empty_like(bv); base=np.empty_like(bv); per=np.zeros(len(lengths)); area=per.copy()
for n in (3,4):
    ids=np.where(lengths==n)[0]; indices=np.array([p['faces'][i] for i in ids]); q=v[indices]
    nxt=np.roll(q,-1,axis=1); prv=np.roll(q,1,axis=1)
    normal=np.cross(q,nxt).sum(axis=1); normal/=np.linalg.norm(normal,axis=1)[:,None]
    out=offset[ids,None]+np.arange(n); w=effective[out,0,None]
    if n==4: xyz=(q*(2.25+2*w)+(nxt+prv)*(.75-w)+.25*np.roll(q,2,axis=1))/4
    else: xyz=(2/3)*q*(1+w/2)+(1/6)*(nxt+prv)*(1-w)
    base[out]=xyz; normals[out]=normal[:,None,:]
    per[ids]=np.linalg.norm(nxt-q,axis=2).sum(axis=1)
    area[ids]=sum(np.linalg.norm(np.cross(q[:,j]-q[:,0],q[:,j+1]-q[:,0]),axis=1)/2 for j in range(1,n-1))
err=float(np.max(np.linalg.norm(base+normals*effective[:,1,None]-bv,axis=1)))
assert err<1e-10,err
tri=np.array([[f[0],f[j],f[j+1]] for f in faces for j in range(1,len(f)-1)])
old=effective[offset[:-1],1]; budget=area*np.abs(old)
raw=1/(1+(per/np.median(per))**2)
lo,hi=0.,100.
for _ in range(70):
    mid=(lo+hi)/2
    if np.average(np.minimum(.5,raw*mid),weights=budget)<.25:lo=mid
    else:hi=mid
regional=np.minimum(.5,raw*(lo+hi)/2)
results={}
for name,factor in [('baseline',np.ones(len(per))),('decay_025',np.full(len(per),.25)),('reprocess_only',np.zeros(len(per))),('local_decay',regional)]:
    dst=O/name;dst.mkdir(exist_ok=True)
    xyz=base+normals*(effective[:,1]*np.repeat(factor,lengths))[:,None]
    mesh=trimesh.Trimesh(xyz,tri,process=False)
    valid=dict(finite=bool(np.isfinite(xyz).all()),watertight=bool(mesh.is_watertight),winding=bool(mesh.is_winding_consistent),min_triangle_area=float(mesh.area_faces.min()))
    assert valid['finite'] and valid['watertight'] and valid['winding'] and valid['min_triangle_area']>0
    (dst/'mesh.json').write_text(json.dumps(dict(vertices=xyz.tolist(),faces=faces)))
    mesh.export(dst/'column.obj',digits=17)
    # Explicit double coordinates: Blender previews are not the master geometry.
    with (dst/'column.ply').open('w') as fp:
        fp.write('ply\nformat ascii 1.0\nelement vertex %d\nproperty double x\nproperty double y\nproperty double z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n'%(len(xyz),len(tri)))
        np.savetxt(fp,xyz,fmt='%.17g');np.savetxt(fp,np.column_stack([np.full(len(tri),3),tri]),fmt='%d')
    pixels={}
    for axis,label in [(0,'front'),(1,'side')]:
        im=Image.new('1',(600,1000));draw=ImageDraw.Draw(im)
        uv=np.column_stack([(xyz[:,axis]+4.5)*600/9,(11-xyz[:,2])*1000/14])
        for f in tri:draw.polygon([tuple(t) for t in uv[f]],fill=1)
        pixels[label]=int(np.asarray(im).sum());im.save(dst/(label+'_silhouette.png'))
    result=dict(**valid,vertices=len(xyz),faces=len(faces),triangles=len(tri),extents=np.ptp(xyz,axis=0).tolist(),silhouette_pixels=pixels,normal_growth_budget_multiplier=float(np.average(factor,weights=budget)),factor_range=[float(factor.min()),float(factor.max())],baseline_reconstruction_error=err,self_intersections='Raw experimental mesh; not repaired, not certified intersection-free',source_parent=str(R/'published_column_vertex7_results/g07/mesh.json'),source_template=str(R/'published_column_vertex8_results/g08/mesh.json'),control='G8 only: unchanged DS placement weights and topology; normal extrusion multiplier',local_rule='min(0.5,k/(1+(face_perimeter/median_perimeter)^2)); k balances area*abs(w10) budget to 0.25' if name=='local_decay' else name)
    np.save(dst/'face_growth_multiplier.npy',factor)
    (dst/'validation.json').write_text(json.dumps(result,indent=2));results[name]=result
    print(name,result,flush=True)
(O/'measurements.json').write_text(json.dumps(results,indent=2))
