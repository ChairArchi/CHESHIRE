"""Subdivision Beyond Smoothness, equations 1-6: executable parameter study.

Published operators are reused, parameters below are OUR hypotheses, not the
parameters of Hansmeyer's column. No fin primitives or restored old corners.
"""
import argparse, json, hashlib
import numpy as np
import fluted_generation as common
from cheshire.weighted_doosabin import weighted_doosabin_once
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.execution import ExecutionBudget

def run(args):
    source=common.ROOT/'fluted_generation_results/g00/mesh.json'
    data=json.loads(source.read_text())
    mesh=common.Mesh.from_vertices_and_faces(data['vertices'],data['faces'])
    if args.coarse:
        # This input adapter is explicitly limited to the preserved 72-corner,
        # 16-ring column. Keep crest pair + deepest valley of each real flute.
        # It is a control-cage approximation, NOT an identical surface.
        v=np.array(data['vertices']); assert len(v)==1154
        keep=sorted(set([9*k+i for k in range(8) for i in (0,4,8)]))
        vertices=[v[72*j+i].tolist() for j in range(16) for i in keep]
        n=len(keep);faces=[[j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i] for j in range(15) for i in range(n)]
        for j in (0,15):
            c=len(vertices);vertices.append([0.,0.,float(v[72*j,2])])
            faces.extend([[c,j*n+(i+1)%n,j*n+i] if j==0 else [c,j*n+i,j*n+(i+1)%n] for i in range(n)])
        mesh=common.Mesh.from_vertices_and_faces(vertices,faces)
    common.OUT=common.ROOT/args.output; common.OUT.mkdir(exist_ok=True)
    common.save(mesh,0,dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
    families=None;origins=None;previous_input=None
    for g in range(args.generations):
        per={}; act={}
        for f in mesh.faces():
            p=np.array(mesh.face_coordinates(f))
            per[f]=float(np.linalg.norm(p-np.roll(p,1,axis=0),axis=1).sum())
            n=np.array(mesh.face_normal(f))
            act[f]=.15+.85*abs(float(n[2]))
            if np.ptp(p[:,2])<1e-8 and abs(n[2])>.999:act[f]=0.
        if args.mode=='ds':
            local={}
            for f in mesh.faces():
                family=families[f]['class'] if families else 'SOURCE_FACE'
                if g==0: w1=-.6 if args.coarse else -.15; amount=0. if args.coarse else .015
                elif family=='FACE_DERIVED':w1=.15;amount=-.008
                elif family=='EDGE_DERIVED':
                    w1=.05;amount=.11
                    if args.axial_fins:
                        u,v=families[f]['source']
                        tangent=np.array(previous_input.vertex_coordinates(u))-np.array(previous_input.vertex_coordinates(v))
                        horizontal=abs(tangent[2])<.2*np.linalg.norm(tangent)
                        amount=args.fin_gain if horizontal else .008
                else:w1=.1;amount=.035
                local[f]=dict(w1=w1,w10=args.strength*amount*per[f]*act[f])
            result=weighted_doosabin_once(mesh,face_families=families,face_weights=local,current_generation=g,budget=ExecutionBudget(350000,350000))
            families=result.face_families
            participation=result.metadata['input_family_counts']
            lineage={str(f):[dict(parent=p.key,weight=p.weight) for p in rows] for f,rows in result.lineage.face_parents.items()}
        else:
            pw={'face':{},'edge':{},'corner':{}}
            for f in mesh.faces():pw['face'][f]={'wf':args.strength*(.025 if g%2==0 else -.015)*per[f]*act[f]}
            for u,v in mesh.edges():
                fs=[mesh.halfedge[u][v],mesh.halfedge[v][u]]
                length=sum(per[f]*act[f] for f in fs)/2
                pw['edge'][(u,v)]={'w1':-.6 if g%2==0 else .15,'we':args.strength*(-.006 if g%2==0 else .055)*length}
            for v in mesh.vertices():
                fs=mesh.vertex_faces(v);length=sum(per[f]*act[f] for f in fs)/len(fs)
                pw['corner'][v]={'w2':-.5,'wp':args.strength*(.004 if g%2==0 else .012)*length}
            fw={f:dict(w3=.5,w4=.25) for f in mesh.faces()} if g else None
            result=generational_subdivide_once(mesh,point_weights=pw,face_weights=fw,origin_lineage=origins,current_generation=g,budget=ExecutionBudget(350000,350000))
            origins=result.origin_lineage
            participation=result.metadata.get('later_generation_face_stencil',{})
            lineage=result.metadata.get('face_sources',[])
        previous_input=mesh
        mesh=result.mesh
        info=dict(operation=args.mode,strength=args.strength,paper='Hansmeyer 2010 Subdivision Beyond Smoothness',scaling='current face perimeter',parameters='experimental, not published column coefficients',old_vertices_restored=False,participation=participation)
        common.save(mesh,g+1,info)
        folder=common.OUT/f'g{g+1:02d}'
        (folder/'lineage.json').write_text(json.dumps(lineage))
        (folder/'operator_metadata.json').write_text(json.dumps(result.metadata))
    (common.OUT/'config.json').write_text(json.dumps(vars(args),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['ds','cc'],default='ds');p.add_argument('--coarse',action='store_true');p.add_argument('--axial-fins',action='store_true');p.add_argument('--fin-gain',type=float,default=.4);p.add_argument('--strength',type=float,default=1.);p.add_argument('--generations',type=int,default=2);p.add_argument('--output',default='paper075_ds_results');run(p.parse_args())
