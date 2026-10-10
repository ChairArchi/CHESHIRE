"""Preserved fluted parent + existing CHESHIRE generational stencils.
Run from repository: .venv/Scripts/python.exe -B scratch/column_reference_20261010/fluted_generation.py
Experimental column study; not a reconstruction of Hansmeyer's algorithm.
"""
import sys,json,hashlib,argparse
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'src'))
from compas.datastructures import Mesh
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.execution import ExecutionBudget
OUT=ROOT/'fluted_generation_results'
MACRO=0.
MACRO_LIMIT=.22
FOLD=.48

def triangles(v,f):
    tri=[]
    for face in f:
        tri.extend([[face[0],face[i],face[i+1]] for i in range(1,len(face)-1)])
    return trimesh.Trimesh(v,tri,process=False)

def save(mesh,g,info):
    v,f=mesh.to_vertices_and_faces(); t=triangles(v,f)
    p=OUT/f'g{g:02d}';p.mkdir(exist_ok=True)
    (p/'mesh.json').write_text(json.dumps(dict(vertices=v,faces=f)))
    for ext in ['obj','ply']:t.export(p/f'column.{ext}')
    rotated=np.array(v)[:,[1,0,2]]*[-1,1,1]
    info.update(vertices=len(v),faces=len(f),triangles=len(t.faces),watertight=bool(t.is_watertight),winding=bool(t.is_winding_consistent),components=len(t.split()),volume=float(t.volume),min_triangle_area=float(t.area_faces.min()),d4_error=float(cKDTree(v).query(rotated)[0].max()),self_intersections='not exhaustively checked')
    assert info['watertight'] and info['winding'] and info['components']==1 and info['min_triangle_area']>1e-12
    (p/'validation.json').write_text(json.dumps(info,indent=2))
    print(g,{k:info[k] for k in ['vertices','faces','watertight','d4_error']},flush=True)

def parent():
    src=ROOT/'fluted_column_results/column.obj'
    original=trimesh.load(src,force='mesh',process=True)
    config=json.loads((ROOT/'fluted_column_results/validation.json').read_text())
    # Extract the actual polygonal flute contour. Remove only collinear Boolean vertices.
    section=original.section(plane_origin=[0,0,6],plane_normal=[0,0,1])
    contour=max(section.discrete,key=len)[:-1,:2]
    # Keep true contour adjacency, including groove undercuts (not polar sorting).
    signed=np.sum(contour[:,0]*np.roll(contour[:,1],-1)-contour[:,1]*np.roll(contour[:,0],-1))
    if signed<0:contour=contour[::-1]
    while True:
        a=contour-np.roll(contour,1,axis=0);b=np.roll(contour,-1,axis=0)-contour
        cross=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])
        keep=cross>1e-5*np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
        if keep.all():break
        contour=contour[keep]
    n=len(contour); levels=config['input_levels']; radii=config['input_radii']
    vs=[[*xy,float(z)] for z,r in zip(levels,radii) for xy in contour*(r/radii[-2])]
    fs=[[j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i] for j in range(len(levels)-1) for i in range(n)]
    for j in [0,len(levels)-1]:
        center=len(vs);vs.append([0,0,levels[j]])
        for i in range(n):fs.append([center,j*n+(i+1)%n,j*n+i] if j==0 else [center,j*n+i,j*n+(i+1)%n])
    t=triangles(vs,fs)
    # Deterministic vertices+triangle centroids test in both directions.
    errors=[];worst=[]
    for a,b in [(original,t),(t,original)]:
        points=np.vstack([a.vertices,a.triangles_center])
        for chunk in np.array_split(points,20):
            distance=trimesh.proximity.closest_point_naive(b,chunk)[1];errors.extend(distance)
            worst.append((float(max(distance)),chunk[np.argmax(distance)].tolist()))
    report=dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),operation='actual section contour loft; collinear vertices removed; no smoothing',surface_sample_max_error=float(max(errors)),section_corners=n)
    if max(errors)>=1e-5:print(sorted(worst,reverse=True)[:5],flush=True)
    assert max(errors)<1e-5,report
    return Mesh.from_vertices_and_faces(vs,fs),report

def step(mesh,origins,g):
    xyz={v:np.array(mesh.vertex_coordinates(v)) for v in mesh.vertices()}
    normals={f:np.array(mesh.face_normal(f)) for f in mesh.faces()}
    pw={};fw={}; shifts={}
    for f in mesh.faces():
        poly=np.array([xyz[v] for v in mesh.face_vertices(f)])
        area=mesh.face_area(f);normal=normals[f]
        bend=max([1-float(np.dot(normal,normals[k])) for k in mesh.face_neighbors(f)] or [0])
        # Geometry-based activation; broad vertical flute walls remain legible.
        activation=min(1.,abs(normal[2])*1.1+bend*.3)
        scale=min(np.sqrt(area),.6)
        end=np.allclose(poly[:,2],0) or np.allclose(poly[:,2],8)
        amount=0 if end else scale*(.035+FOLD*activation)
        pw[f]={'wf':float(amount)}
        fw[f]={'w3':float(.45*activation) if g else 0.,'w4':float(.18*activation) if g else 0.}
    for v,p in xyz.items():
        faces=mesh.vertex_faces(v);normal=np.mean([normals[f] for f in faces],axis=0)
        length=np.linalg.norm(normal);normal=normal/max(length,1e-12)
        local=min(np.linalg.norm(xyz[k]-p) for k in mesh.vertex_neighbors(v))
        # Existing parent corners also participate, but never undergo CC averaging.
        shifts[v]=normal*min(local,.35)*.15*abs(normal[2]) if 1e-6<p[2]<8-1e-6 else np.zeros(3)
        if MACRO and 1e-6<p[2]<8-1e-6:
            # Axial neighbours of the CURRENT mesh, not a pre-scripted radius profile.
            axial=[xyz[k] for k in mesh.vertex_neighbors(v) if abs(xyz[k][2]-p[2])>1e-7]
            if len(axial)>=2:
                delta=p-np.mean(axial,axis=0)
                radial=p.copy();radial[2]=0;radius=np.linalg.norm(radial);radial/=max(radius,1e-12)
                radial_delta=float(np.dot(delta,radial))*radial
                change=MACRO*(radial_delta+np.array([0,0,.35*delta[2]]))
                limit=MACRO_LIMIT*radius
                change*=min(1.,limit/max(np.linalg.norm(change),1e-12))
                shifts[v]+=change
    result=generational_subdivide_once(mesh,{'w1':-1.},point_weights={'face':pw},face_weights=fw,origin_lineage=origins,current_generation=g,budget=ExecutionBudget(150000,150000))
    for v,p in xyz.items():result.mesh.vertex_attributes(v,'xyz',p.tolist())
    # Transfer the coherent coarse displacement to descendants as well as corners.
    for v,parents in result.sampling_parents.items():
        shift=sum((shifts[k]*weight for k,weight in parents),np.zeros(3))
        result.mesh.vertex_attributes(v,'xyz',(np.array(result.mesh.vertex_coordinates(v))+shift).tolist())
    report=dict(operation='COMPAS split topology + existing CHESHIRE weighted extrusion / later-generation stencil',corner_policy='retain prior geometry plus local normal displacement and optional axial-neighbour anti-Laplacian; no CC corner averaging',macro_gain=MACRO,macro_limit=MACRO_LIMIT,fold_strength=FOLD,edge_policy='exact parent edge midpoint plus inherited coarse displacement',generation=g+1,eligible_previous_generation_faces=result.metadata['later_generation_face_stencil']['eligible_faces'],mean_face_extrusion=float(np.mean([x['wf'] for x in pw.values()])),max_parent_corner_displacement=float(max(np.linalg.norm(s) for s in shifts.values())),smoothing=False)
    p=OUT/f'g{g+1:02d}';p.mkdir(exist_ok=True)
    (p/'lineage.json').write_text(json.dumps(dict(origins=result.origin_lineage,face_sources=result.metadata['face_sources'])))
    return result.mesh,result.origin_lineage,report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT);ap.add_argument('--macro',type=float,default=0.);ap.add_argument('--macro-limit',type=float,default=.22);ap.add_argument('--fold',type=float,default=.48);args=ap.parse_args()
    OUT=args.output.resolve();OUT.mkdir(exist_ok=True,parents=True);MACRO=args.macro;MACRO_LIMIT=args.macro_limit;FOLD=args.fold
    mesh,report=parent();save(mesh,0,report);origins=None
    for g in range(2):
        mesh,origins,report=step(mesh,origins,g);save(mesh,g+1,report)
