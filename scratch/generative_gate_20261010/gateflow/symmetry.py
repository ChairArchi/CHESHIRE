"""Positive half-space clipping and seam-welded reflection.
Adapted from existing CHESHIRE gate_mirror.cut_reflect: retains convex polygons
so CC/DS are not forced through triangle subdivision at each symmetry boundary.
Locally triangulates polygons with more than two plane crossings.
"""
import numpy as np
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import ArrayMesh

def symmetry_error(m):
    reflected=m.xyz.copy();reflected[:,0]*=-1
    return float(cKDTree(m.xyz).query(reflected)[0].max())

def reflect(m):
    mirrored=m.xyz.copy();mirrored[:,0]*=-1
    distance_to_pair,pair=cKDTree(m.xyz).query(mirrored)
    if distance_to_pair.max()<1e-12 or (distance_to_pair.max()<1e-7 and np.array_equal(pair[pair],np.arange(len(pair)))):
        # Preserve already paired topology; remove floating point drift only.
        xyz=m.xyz.copy() if distance_to_pair.max()<1e-12 else (m.xyz+mirrored[pair])*.5
        out=ArrayMesh(xyz,m.faces.copy(),m.classes.copy(),m.rest.copy(),m.anchors.copy(),m.generation)
        ids=np.arange(len(xyz));faces=np.arange(len(m.faces))
        return out,dict(symmetry_source_edge=np.column_stack([ids,ids]),symmetry_source_alpha=np.zeros(len(ids)),symmetry_parent_face=faces,symmetry_reflected_face=np.zeros(len(faces),bool))
    distance=m.xyz[:,0].copy();distance[np.abs(distance)<1e-10]=0
    vertices=[];rest=[];classes=[];source=[];alpha=[];lookup={};faces=[];parents=[]
    def vertex(a,b=None):
        if b is None or distance[a]==0:b=a
        elif distance[b]==0:a=b
        a,b=sorted((int(a),int(b)));key=(a,b)
        if key not in lookup:
            t=0. if a==b else distance[a]/(distance[a]-distance[b])
            v=(1-t)*m.xyz[a]+t*m.xyz[b]
            if a!=b or distance[a]==0:v[0]=0
            lookup[key]=len(vertices);vertices.append(v);rest.append((1-t)*m.rest[a]+t*m.rest[b]);classes.append(m.classes[a] if a==b else -1);source.append([a,b]);alpha.append(t)
        return lookup[key]
    for fi,q in enumerate(m.faces):
        q=q[q>=0];d=distance[q]
        if np.all(d==0):continue
        cross=sum(distance[a]*distance[b]<0 for a,b in zip(q,np.roll(q,-1)))
        pieces=[q] if cross<=2 else [np.array([q[0],q[j],q[j+1]]) for j in range(1,len(q)-1)]
        for piece in pieces:
            ids=[]
            for a,b in zip(piece,np.roll(piece,-1)):
                if distance[a]>=0:ids.append(vertex(a))
                if distance[a]*distance[b]<0:ids.append(vertex(a,b))
            ids=list(dict.fromkeys(ids))
            if len(ids)>=3:faces.append(ids);parents.append(fi)
    if not faces:raise ValueError('Empty positive half during symmetry')
    v=np.array(vertices);rr=np.array(rest);cl=np.array(classes,dtype=np.int8)
    used=np.unique(np.concatenate(faces));remap=np.full(len(v),-1,int);remap[used]=np.arange(len(used))
    faces=[remap[f].tolist() for f in faces];v=v[used];rr=rr[used];cl=cl[used];source=np.array(source)[used];alpha=np.array(alpha)[used]
    off=np.flatnonzero(v[:,0]!=0);mirror=np.arange(len(v));mirror[off]=len(v)+np.arange(len(off))
    reflected=v[off].copy();reflected[:,0]*=-1
    full=faces+[mirror[f[::-1]].tolist() for f in faces];q=np.full((len(full),max(4,max(map(len,full)))),-1,int)
    for i,f in enumerate(full):q[i,:len(f)]=f
    parent=np.r_[parents,parents]
    out=ArrayMesh(np.r_[v,reflected],q,np.r_[cl,cl[off]],np.r_[rr,rr[off]],m.anchors[parent],m.generation)
    return out,dict(symmetry_source_edge=np.r_[source,source[off]],symmetry_source_alpha=np.r_[alpha,alpha[off]],symmetry_parent_face=parent,symmetry_reflected_face=np.r_[np.zeros(len(faces),bool),np.ones(len(faces),bool)])

def vertex_values(state,values):
    a=state['symmetry_source_edge'];t=state['symmetry_source_alpha']
    return (1-t)*values[a[:,0]]+t*values[a[:,1]]

def symmetric_displacement(m,displacement):
    # Constrain the vector field before deformation, preserving paired topology.
    positive=np.flatnonzero(m.xyz[:,0]>=-1e-10);q=m.xyz.copy();q[:,0]=np.abs(q[:,0])
    ids=positive[cKDTree(m.xyz[positive]).query(q)[1]];result=displacement[ids].copy()
    result[m.xyz[:,0]<0,0]*=-1;result[np.abs(m.xyz[:,0])<1e-10,0]=0
    return result
