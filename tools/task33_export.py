"""Explicit mirrored triangulation; original native quads remain untouched.

No position changes, welding, smoothing, or repairs. A first-corner fan on a
nonplanar quad need not reflect its partner, so diagonal choices are paired.
"""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from cheshire.reference_subdivision import ArrayMesh,topology
from task33_preserve import ROOT,sha,write_new
from task29_search import load_mesh
from task33_evidence import canonical,state_at


def triangulate(mesh,state):
    q=mesh.faces
    if q.shape[1]!=4 or np.any(q<0):raise ValueError('Complete native quads required.')
    chart=state['chart'];mirrored=chart.copy();mirrored[:,0]=1-mirrored[:,0]
    distance,pair=cKDTree(chart).query(mirrored)
    if distance.max()>1e-10 or not np.array_equal(pair[pair],np.arange(len(pair))):
        raise ValueError('Reflection correspondence is invalid.')
    a=canonical(q);b=canonical(pair[q[:,::-1]])
    ia=np.lexsort(a.T);ib=np.lexsort(b.T)
    if not np.array_equal(a[ia],b[ib]):raise ValueError('Native face reflection is invalid.')
    face_pair=np.empty(len(q),np.int64);face_pair[ib]=ia
    left=np.flatnonzero(chart[q,0].mean(1)<.5-1e-12)
    if len(left)*2!=len(q) or np.any(face_pair[left]==left):
        raise ValueError('Only paired halves without self-reflecting faces are supported.')
    right=face_pair[left];wanted=np.sort(pair[q[left][:,[0,2]]],axis=1)
    d0=np.sort(q[right][:,[0,2]],axis=1);d1=np.sort(q[right][:,[1,3]],axis=1)
    is0=np.all(wanted==d0,axis=1);is1=np.all(wanted==d1,axis=1)
    if not np.all(is0^is1):raise ValueError('Reflected diagonal cannot be identified.')
    diagonal=np.zeros(len(q),np.int8);diagonal[right]=is1
    first=q[:,[0,1,2]].copy();second=q[:,[0,2,3]].copy()
    selected=diagonal==1
    first[selected]=q[selected][:,[1,2,3]];second[selected]=q[selected][:,[1,3,0]]
    faces=np.concatenate([first,second]);parents=np.tile(np.arange(len(q)),2)
    # Native ArrayMesh helpers use four slots with -1 padding for triangles.
    padded=np.column_stack([faces,np.full(len(faces),-1,np.int64)])
    out=ArrayMesh(mesh.xyz.copy(),padded,mesh.classes.copy(),mesh.rest.copy(),mesh.anchors[parents].copy(),mesh.generation)
    reflected=canonical(pair[faces[:,::-1]]);actual=canonical(faces)
    if not np.array_equal(reflected[np.lexsort(reflected.T)],actual[np.lexsort(actual.T)]):
        raise ValueError('Explicit triangle cycles are not mirrored.')
    topology(out)
    return out,dict(parent_face=parents,quad_diagonal=diagonal,vertex_reflection=pair,source_face_reflection=face_pair)


def export(candidate,tag):
    from task33_research import checkpoint
    job=ROOT/'candidates'/candidate
    stage=Path(json.loads((job/'completed.json').read_text())['final_stage'])
    m=load_mesh(stage);state=state_at(stage);out,op=triangulate(m,state)
    dest=ROOT/'exports'/tag
    checkpoint(dest,out,state,dict(operation='Explicit reflection-paired native quad triangulation; XYZ unchanged.',
        source_mesh_sha256=sha(stage/'mesh.npz'),native_vertices_unchanged=bool(np.array_equal(out.xyz,m.xyz)),
        source_code_sha256=sha(Path(__file__)),warning='Re-test this explicit surface. Original quad contact and nonplanarity diagnostics remain separate.'),op,stage)
    write_new(dest/'producer.json',dict(candidate=candidate,tool_sha256=sha(Path(__file__))))
    print(tag,len(out.xyz),len(out.faces),'exact reflected triangle cycles; no position change',flush=True)
