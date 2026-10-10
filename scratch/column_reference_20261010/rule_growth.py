"""Geometry-driven independent root/child growth on connected face patches.
Study hypothesis, not Hansmeyer's original implementation. D4 column symmetry.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import generation_rules as rules
import fluted_generation as common

def grow(source,output,gain=.65,orbits=6):
    data=json.loads(source.read_text());v=np.array(data['vertices']);faces=data['faces'];analysis=rules.analyze(data);d=analysis['faces']
    centers=np.array([d[i]['center'] for i in range(len(faces))]);tree=cKDTree(centers)
    rotations=[np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]) for a in np.arange(4)*np.pi/2]
    maps=[]
    for R in rotations:
        error,ids=tree.query(centers@R.T)
        assert error.max()<1e-6,'Input must have D4 face correspondence'
        maps.append(ids)
    blocked=set();patches=[];selected=0
    for seed in analysis['candidates']:
        orbit=[sorted(set(int(m[k]) for k in d[seed]['support_patch'])) for m in maps]
        union=set(k for patch in orbit for k in patch)
        if len(union)!=sum(len(p) for p in orbit) or union&blocked:continue
        patches.extend(orbit);selected+=1
        blocked.update(union)
        for k in union:blocked.update(d[k]['neighbors'])
        if selected>=orbits:break
    verts=v.tolist();removed=set();added=[];lineage=[];events=[]
    for patch in patches:
        keys=sorted(set(k for f in patch for k in faces[f]));p=v[keys]
        area=sum(d[f]['area'] for f in patch);center=np.average([d[f]['center'] for f in patch],axis=0,weights=[d[f]['area'] for f in patch])
        normal=np.sum([np.array(d[f]['normal'])*d[f]['area'] for f in patch],axis=0);normal/=np.linalg.norm(normal)
        tangent=np.array([0.,0.,1.])-normal*normal[2];tangent/=max(np.linalg.norm(tangent),1e-12)
        tangent*=np.sign(normal[2])
        size=np.sqrt(area)*gain;bend=float(np.mean([d[f]['max_dihedral'] for f in patch]))
        base_height=size*(.18+.1*min(bend,1.));tip_height=size
        cap_scale=float(np.clip(.55-.12*bend,.3,.55))
        boundary={}
        for f in patch:
            face=faces[f]
            for a,b in zip(face,face[1:]+face[:1]):
                if (b,a) in boundary:del boundary[b,a]
                else:boundary[a,b]=True
        base={};tip={}
        for key,point in zip(keys,p):
            base[key]=len(verts);verts.append((center+(point-center)*.92+normal*base_height).tolist())
            tip[key]=len(verts);verts.append((center+(point-center)*cap_scale+normal*tip_height+tangent*size*.12).tolist())
        for f in patch:added.append([tip[k] for k in faces[f]]);lineage.append(dict(role='child_cap',parents=patch))
        for a,b in boundary:
            added.append([a,b,base[b],base[a]]);lineage.append(dict(role='root',parents=patch))
            added.append([base[a],base[b],tip[b],tip[a]]);lineage.append(dict(role='child_side',parents=patch))
        removed.update(patch);events.append(dict(parents=patch,support_area=area,normal=normal.tolist(),flow=tangent.tolist(),base_height=base_height,tip_height=tip_height,cap_scale=cap_scale))
    retained=[(i,f) for i,f in enumerate(faces) if i not in removed]
    allfaces=[f for _,f in retained]+added
    # Interior source patch vertices may become unused after replacement.
    used=sorted(set(k for f in allfaces for k in f));remap={k:i for i,k in enumerate(used)}
    mesh=common.Mesh.from_vertices_and_faces([verts[k] for k in used],[[remap[k] for k in f] for f in allfaces])
    output.mkdir(parents=True,exist_ok=True);common.OUT=output
    common.save(mesh,1,dict(operation='current-geometry patch selection -> inherited-footprint root -> child extrusion',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),gain=gain,patch_count=len(patches),events=events,smoothing=False,claim='implemented hypothesis; no manual height bands or fixed circumferential sector count'))
    rows=[dict(role='parent',parents=[i]) for i,_ in retained]+lineage
    (output/'g01/face_lineage.json').write_text(json.dumps(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=common.ROOT/'independent_extrusion_results/g01/mesh.json');p.add_argument('--output',type=Path,default=common.ROOT/'rule_growth_results');p.add_argument('--gain',type=float,default=.65);p.add_argument('--orbits',type=int,default=6);a=p.parse_args();grow(a.input,a.output,a.gain,a.orbits)
