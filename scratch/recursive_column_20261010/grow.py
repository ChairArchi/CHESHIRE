"""Recursive, symmetry-preserving face growth from a fluted straight cage.
No target silhouette or final surface is prescribed. No smooth subdivision.
"""
from pathlib import Path
import argparse,json,math,copy,hashlib
import numpy as np
import trimesh
from scipy.spatial import cKDTree

def initial(fluted=True):
    n=32 if fluted else 8
    levels=[0,1.6,3.2,4.8,6.4,8] if fluted else [0,8]
    vertices=[]
    for z in levels:
        for i in range(n):
            a=2*math.pi*i/n
            r=1.15*(1-.16*(1-math.cos(8*a))/2) if fluted else 1.15
            vertices.append([r*math.cos(a),r*math.sin(a),z])
    faces=[]
    for j in range(len(levels)-1):
        for i in range(n):faces.append(dict(v=[j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i],id=len(faces),born=0,parent=None,role='seed_panel'))
    faces.append(dict(v=list(reversed(range(n))),id=len(faces),born=0,parent=None,role='end'))
    faces.append(dict(v=[(len(levels)-1)*n+i for i in range(n)],id=len(faces),born=0,parent=None,role='end'))
    return dict(vertices=vertices,faces=faces,next_id=len(faces))

def triangles(state):
    tri=[]
    for face in state['faces']:
        f=face['v'];tri.extend([(f[0],f[k],f[k+1]) for k in range(1,len(f)-1)])
    return np.asarray(tri)

def mesh_of(state):return trimesh.Trimesh(np.asarray(state['vertices']),triangles(state),process=False)

def observations(state):
    vertices=np.asarray(state['vertices']);obs=[];edges={}
    for index,face in enumerate(state['faces']):
        p=vertices[face['v']];center=p.mean(0);normal=np.zeros(3);area=0
        for k in range(1,len(p)-1):
            cross=np.cross(p[k]-p[0],p[k+1]-p[0]);normal+=cross;area+=np.linalg.norm(cross)/2
        normal/=max(np.linalg.norm(normal),1e-12)
        obs.append(dict(center=center,normal=normal,area=area,curvature=0.))
        for a,b in zip(face['v'],face['v'][1:]+face['v'][:1]):edges.setdefault(tuple(sorted((a,b))),[]).append(index)
    degree=np.zeros(len(obs))
    for pair in edges.values():
        if len(pair)!=2:continue
        a,b=pair
        if state['faces'][a]['role']=='end' or state['faces'][b]['role']=='end':continue
        bend=1-np.clip(np.dot(obs[a]['normal'],obs[b]['normal']),-1,1)
        obs[a]['curvature']+=bend;obs[b]['curvature']+=bend;degree[a]+=1;degree[b]+=1
    for i,o in enumerate(obs):o['curvature']/=max(degree[i],1)
    return obs

def choose(state,generation,mode,groups):
    obs=observations(state);orbits={}
    for i,(face,o) in enumerate(zip(state['faces'],obs)):
        if face['role']=='end':continue
        if face['born']!=(generation-1 if mode=='recursive' else 0):continue
        if o['area']<.005:continue
        x,y,z=o['center'];a,b=sorted((abs(x),abs(y)))
        key=tuple(round(t,6) for t in (a,b,z,o['area'],abs(o['normal'][2])))+(face['role'],)
        score=o['area']*(.25+abs(o['normal'][2])+.6*o['curvature'])*(.6+.4*math.sin(math.pi*np.clip(z/8,0,1)))
        orbits.setdefault(key,[]).append((i,score))
    ordered=sorted(orbits.values(),key=lambda group:(-np.mean([v[1] for v in group]),min(v[0] for v in group)))
    selected=[];used_vertices=set();seed_heights=[]
    for group in ordered:
        if len(group)!=8:continue
        indices=[i for i,_ in group]
        touched=set(v for i in indices for v in state['faces'][i]['v'])
        if touched & used_vertices:continue
        z=obs[indices[0]]['center'][2]
        if generation==1 and any(abs(z-other)<1.0 for other in seed_heights):continue
        selected.extend(indices);used_vertices|=touched
        seed_heights.append(z)
        if len(selected)>=groups*8:break
    if len(selected)<groups*8:
        # Adjacent orbits are allowed if necessary; all faces still selected before mutation.
        for group in ordered:
            indices=[i for i,_ in group]
            if len(group)==8 and not set(indices)&set(selected):selected.extend(indices)
            if len(selected)>=groups*8:break
    if len(selected)!=groups*8:raise ValueError(f'Insufficient symmetric face groups: {generation}, {mode}, {len(selected)}')
    return selected,obs

def grow(state,generation,mode,groups,strength=1.):
    selected,obs=choose(state,generation,mode,groups);selected=set(selected);new=copy.deepcopy(state);new['faces']=[];events=[]
    for i,face in enumerate(state['faces']):
        if i not in selected:new['faces'].append(copy.deepcopy(face));continue
        p=np.asarray(state['vertices'])[face['v']];o=obs[i];c=o['center'];n=o['normal']
        up=np.array([0.,0.,1.]);tangent=up-n*np.dot(up,n);norm=np.linalg.norm(tangent)
        if norm>1e-8:tangent/=norm
        else:tangent=np.zeros(3)
        direction=1 if n[2]>=0 else -1
        size=math.sqrt(o['area']);distance=strength*.52*size*(.8+.4*o['curvature'])
        # Existing face inclination controls fold direction and displacement.
        rel=(p-c)*.78
        q=c+rel+n*distance+tangent*(direction*.18*distance)
        q+=np.outer(rel@tangent,n)*(direction*.32*strength)
        cap=list(range(len(new['vertices']),len(new['vertices'])+len(q)));new['vertices'].extend(q.tolist())
        created=[]
        def add(vs,role):
            uid=new['next_id'];new['next_id']+=1;new['faces'].append(dict(v=vs,id=uid,born=generation,parent=face['id'],role=role));created.append(uid)
        add(cap,'cap')
        for k,a in enumerate(face['v']):
            j=(k+1)%len(cap);add([a,face['v'][j],cap[j],cap[k]],'side')
        events.append(dict(parent=face['id'],parent_born=face['born'],parent_role=face['role'],children=created,area=o['area'],normal=n.tolist(),curvature=o['curvature'],extrusion=distance))
    return new,events

def crossing_count(mesh):
    # Proper edge/triangle crossings between disjoint triangles; excludes coplanar contact.
    f=np.asarray(mesh.faces);t=np.asarray(mesh.triangles);low=t.min(1);high=t.max(1);count=0
    def hits(edges,tri):
        e1=tri[1]-tri[0];e2=tri[2]-tri[0]
        for a,b in edges:
            d=b-a;p=np.cross(d,e2);det=np.dot(e1,p)
            if abs(det)<1e-10:continue
            s=a-tri[0];u=np.dot(s,p)/det;q=np.cross(s,e1);v=np.dot(d,q)/det;w=np.dot(e2,q)/det
            if 1e-7<u<1-1e-7 and 1e-7<v and u+v<1-1e-7 and 1e-7<w<1-1e-7:return True
        return False
    for i in range(len(t)):
        ids=np.flatnonzero(np.all(high[i]>=low,axis=1)&np.all(high>=low[i],axis=1)&(np.arange(len(t))>i))
        for j in ids:
            if np.intersect1d(f[i],f[j]).size:continue
            if hits(list(zip(t[i],np.roll(t[i],-1,axis=0))),t[j]) or hits(list(zip(t[j],np.roll(t[j],-1,axis=0))),t[i]):count+=1
    return count

def validate(state):
    m=mesh_of(state);v=np.asarray(m.vertices);rot=v.copy();rot[:,0]=-v[:,1];rot[:,1]=v[:,0];mir=v.copy();mir[:,0]*=-1
    tree=cKDTree(v);sym=max(tree.query(rot)[0].max(),tree.query(mir)[0].max())
    assert m.is_watertight and m.is_winding_consistent and len(m.split())==1 and np.isfinite(v).all() and m.area_faces.min()>1e-10 and sym<1e-6
    return m,dict(watertight=True,components=1,symmetry_error=float(sym),volume=float(m.volume),faces=len(state['faces']),vertices=len(v),bounds=m.bounds.tolist(),proper_crossings=crossing_count(m))

def main(output):
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=False);history={}
    def save(folder,state,events,parent_hash=None,extra=None):
        folder.mkdir(parents=True);m,report=validate(state)
        for ext in ('obj','ply'):m.export(folder/('column.'+ext))
        (folder/'mesh.json').write_text(json.dumps(dict(vertices=state['vertices'],faces=[f['v'] for f in state['faces']])))
        (folder/'state.json').write_text(json.dumps(state))
        report.update(events=events,parent_sha256=parent_hash,sha256=hashlib.sha256((folder/'state.json').read_bytes()).hexdigest())
        if extra:report.update(extra)
        (folder/'generation.json').write_text(json.dumps(report,indent=2));return report
    save(root/'00_simple',initial(False),[])
    seed=initial(True);r=save(root/'01_fluted_seed',seed,[]);seed_hash=r['sha256']
    for mode in ('recursive','seed_only'):
        state=copy.deepcopy(seed);parent=seed_hash;history[mode]=[]
        for g,groups in enumerate((2,3,4,4),1):
            for strength in (1.,.75,.5,.3,.18):
                candidate,events=grow(state,g,mode,groups,strength);_,check=validate(candidate)
                if check['proper_crossings']==0:break
            else:raise ValueError('No crossing-free growth step found')
            report=save(root/mode/f'g{g:02d}',candidate,events,parent,dict(strength=strength,selected_faces=len(events),selected_from_previous_generation=sum(e['parent_born']==g-1 for e in events),mode=mode))
            state=candidate;parent=report['sha256'];history[mode].append(report)
            print(mode,g,report['faces'],report['selected_from_previous_generation'],strength,flush=True)
    (root/'run.json').write_text(json.dumps(dict(status='COMPLETE',history=history,scope='recursive coarse face-growth experiment, not a full Hansmeyer reconstruction',self_intersection_check='proper disjoint edge-triangle crossings; not a complete coplanar overlap proof'),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();main(args.output)
