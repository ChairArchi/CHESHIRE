"""Out-of-core exact neutral Catmull-Clark on quad arrays; no project IDs."""
from pathlib import Path
import numpy as np

def allocate(folder,name,shape,dtype):
    path=Path(folder)/(name+'.npy')
    if path.exists():raise FileExistsError(str(path))
    return np.lib.format.open_memmap(path,mode='w+',dtype=dtype,shape=shape)

def ranges(n,chunk):
    for start in range(0,n,chunk):yield start,min(n,start+chunk)

def prepare_cc1(xyz,quads,folder,*,float_attributes=None,bool_attributes=None,chunk=65536,allow_boundary=False,progress=print):
    """Real CC geometry, exact V/E/F lineage and bilinear attribute transport.

    Boundary support exists for small COMPAS verification only: naked old
    vertices fixed and naked edge midpoints retained, matching crease2/k1.
    Main whole-column call requires every edge to have two opposite incidences.
    """
    root=Path(folder);root.mkdir(parents=True,exist_ok=False)
    x=xyz;q=quads;nv=len(x);nf=len(q);nh=4*nf
    if q.shape!=(nf,4) or x.shape!=(nv,3) or chunk<1:raise ValueError('Quad xyz input required.')
    for a,b in ranges(nv,chunk):
        if not np.isfinite(x[a:b]).all():raise ValueError('Nonfinite source coordinates.')
    keys=allocate(root,'HALFEDGE_KEYS',(nh,),np.int64)
    for a,b in ranges(nf,chunk):
        f=np.asarray(q[a:b]);nxt=np.roll(f,-1,axis=1)
        if np.any(f<0) or np.any(f>=nv):raise ValueError('Invalid source face index.')
        keys[4*a:4*b]=(np.minimum(f,nxt)*np.int64(nv)+np.maximum(f,nxt)).ravel()
    keys.flush();progress('CC1_EDGE_SORT_BEGIN',nh,flush=True)
    order=np.argsort(keys,kind='stable');sk=np.asarray(keys)[order]
    starts=np.r_[0,np.flatnonzero(sk[1:]!=sk[:-1])+1]
    counts=np.diff(np.r_[starts,nh]);ne=len(starts)
    if np.any((counts<1)|(counts>2)) or (not allow_boundary and np.any(counts!=2)):
        raise ValueError('Require manifold edge incidence; whole-column input must be closed.')
    edgekeys=allocate(root,'INPUT_EDGE_KEYS',(ne,),np.int64);edgekeys[:]=sk[starts]
    edges=allocate(root,'INPUT_EDGES',(ne,2),np.int64)
    ef=allocate(root,'INPUT_EDGE_FACES',(ne,2),np.int64)
    fe=allocate(root,'INPUT_FACE_EDGE_IDS',(nf,4),np.int64)
    boundary=np.zeros(nv,bool);orientation_checks=0
    for a,b in ranges(ne,chunk):
        unique=np.asarray(edgekeys[a:b]);edges[a:b,0]=unique//nv;edges[a:b,1]=unique%nv
        first=order[starts[a:b]];second=order[starts[a:b]+counts[a:b]-1]
        ef[a:b,0]=first//4;ef[a:b,1]=np.where(counts[a:b]==2,second//4,-1)
        aa=q[first//4,first%4];ab=q[first//4,(first%4+1)%4]
        ba=q[second//4,second%4];bb=q[second//4,(second%4+1)%4]
        closed=counts[a:b]==2
        if np.any(closed&((aa!=bb)|(ab!=ba))):raise ValueError('Input oriented edge cycles disagree.')
        orientation_checks+=int(closed.sum())
        if np.any(~closed):boundary[np.asarray(edges[a:b])[~closed].ravel()]=True
        h0=int(starts[a]);h1=int(starts[b]) if b<ne else nh
        fe.reshape(-1)[order[h0:h1]]=np.repeat(np.arange(a,b,dtype=np.int64),counts[a:b])
    for arr in (edgekeys,edges,ef,fe):arr.flush()
    del order,sk,starts,keys
    progress('CC1_EDGE_TOPOLOGY_READY',ne,'boundary_vertices',int(boundary.sum()),flush=True)
    nout=nv+ne+nf;nqout=4*nf
    raw=allocate(root,'RAW_CC_XYZ',(nout,3),np.float64)
    reference=allocate(root,'BILINEAR_REFERENCE_XYZ',(nout,3),np.float64)
    child=allocate(root,'CHILD_QUADS',(nqout,4),np.int64)
    parent=allocate(root,'PARENT_FACE',(nqout,),np.int64)
    face_sum=np.zeros((nv,3),float);face_count=np.zeros(nv,np.int64)
    for a,b in ranges(nf,chunk):
        f=np.asarray(q[a:b]);point=np.asarray(x[f]).mean(1)
        raw[nv+ne+a:nv+ne+b]=point;reference[nv+ne+a:nv+ne+b]=point
        for k in range(4):np.add.at(face_sum,f[:,k],point);np.add.at(face_count,f[:,k],1)
        eid=np.asarray(fe[a:b]);fid=np.arange(a,b,dtype=np.int64)
        child[4*a:4*b]=np.stack((np.roll(eid,1,axis=1)+nv,f,eid+nv,np.broadcast_to((fid+nv+ne)[:,None],f.shape)),axis=2).reshape(-1,4)
        parent[4*a:4*b]=np.repeat(fid,4)
    midpoint_sum=np.zeros((nv,3),float);degree=np.zeros(nv,np.int64)
    for a,b in ranges(ne,chunk):
        e=np.asarray(edges[a:b]);mid=np.asarray(x[e]).mean(1);adj=np.asarray(ef[a:b])
        reference[nv+a:nv+b]=mid
        point=mid.copy();interior=adj[:,1]>=0
        point[interior]=(np.asarray(x[e[interior]]).sum(1)+np.asarray(raw[nv+ne+adj[interior]]).sum(1))/4.
        raw[nv+a:nv+b]=point
        for k in range(2):np.add.at(midpoint_sum,e[:,k],mid);np.add.at(degree,e[:,k],1)
    if np.any(degree<2) or np.any(face_count<1):raise ValueError('Isolated/invalid vertex incidence.')
    if not allow_boundary and np.any(face_count!=degree):raise ValueError('Closed quad vertex face/edge incidence differs.')
    for a,b in ranges(nv,chunk):
        d=degree[a:b,None];old=np.asarray(x[a:b]);reference[a:b]=old
        value=(face_sum[a:b]/face_count[a:b,None]+2*midpoint_sum[a:b]/d+(d-3)*old)/d
        value[boundary[a:b]]=old[boundary[a:b]];raw[a:b]=value
    del face_sum,midpoint_sum,face_count
    for arr in (raw,reference,child,parent):arr.flush()
    progress('CC1_VEF_COORDINATES_READY',nout,nqout,flush=True)
    arrays=dict(RAW_CC_XYZ=raw,BILINEAR_REFERENCE_XYZ=reference,CHILD_QUADS=child,PARENT_FACE=parent,
        INPUT_EDGES=edges,INPUT_EDGE_KEYS=edgekeys,INPUT_EDGE_FACES=ef,INPUT_FACE_EDGE_IDS=fe)
    for name,source in (float_attributes or {}).items():
        if len(source)!=nv:raise ValueError('Attribute source vertex count mismatch: '+name)
        tail=source.shape[1:];target=allocate(root,name,(nout,)+tail,np.float64)
        for a,b in ranges(nv,chunk):target[a:b]=source[a:b]
        for a,b in ranges(ne,chunk):target[nv+a:nv+b]=np.asarray(source[np.asarray(edges[a:b])]).mean(1)
        for a,b in ranges(nf,chunk):target[nv+ne+a:nv+ne+b]=np.asarray(source[np.asarray(q[a:b])]).mean(1)
        target.flush();arrays[name]=target
        progress('CC1_FLOAT_ATTRIBUTE_READY',name,flush=True)
    for name,source in (bool_attributes or {}).items():
        if source.shape!=(nv,):raise ValueError('Boolean attribute source mismatch.')
        target=allocate(root,name,(nout,),np.bool_)
        for a,b in ranges(nv,chunk):target[a:b]=source[a:b]
        for a,b in ranges(ne,chunk):target[nv+a:nv+b]=np.any(source[np.asarray(edges[a:b])],axis=1)
        for a,b in ranges(nf,chunk):target[nv+ne+a:nv+ne+b]=np.any(source[np.asarray(q[a:b])],axis=1)
        target.flush();arrays[name]=target
    info=dict(input_counts=dict(vertices=nv,edges=ne,quads=nf),output_counts=dict(vertices=nout,quads=nqout,
        native_fan_vertices=nout+nqout,native_fan_triangles=4*nqout),
        closed_input=bool(not boundary.any()),boundary_vertices=int(boundary.sum()),opposite_edge_incidence_checks=orientation_checks,
        input_Euler_characteristic=nv-ne+nf,output_Euler_characteristic=nout-(2*ne+4*nf)+nqout,
        degree_quantiles=np.quantile(degree,[0,.5,.9,.99,1]).tolist(),
        vertex_order="old V, sorted undirected E, original F",child_order="[previous_E, original_corner_V, next_E, original_F]",
        parent_face="PARENT_FACE; equivalently child_face//4",parent_corner_ordinal="child_face%4",parent_corner_vertex="CHILD_QUADS[:,1]",
        geometry="Neutral true Catmull-Clark: F=mean original corners; E=(original endpoints+two completed F)/4; V=(mean incident F+2*mean ORIGINAL edge midpoints+(degree-3)*original V)/degree.",
        scalar_attributes="V unchanged, E endpoint mean, F corner mean; cap masks any endpoint/corner. Attributes do not use CC geometry averaging.",
        maximum_expected_RAM_GiB=8.0,chunk=chunk)
    return arrays,info
