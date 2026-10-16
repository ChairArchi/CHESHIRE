"""Stitch bounded triangle replacements into a closed quad carrier.

The helper does not Boolean, smooth, project, or repair geometry. Each incoming
patch must already be a connected oriented surface with one boundary matching
the removed carrier disk. Native quads outside the disks remain exact.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components


def array_hash(a):
    return hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def record(path):
    return dict(path=str(path),sha256=file_hash(path))


def surface_topology(faces,nv):
    """Small bounded patch topology, including oriented edge incidence."""
    f=np.asarray(faces,np.int64)
    if f.ndim!=2 or f.shape[1] not in (3,4) or not len(f):raise ValueError('Triangles or quads required.')
    if f.min()<0 or f.max()>=nv or np.any(np.diff(np.sort(f,axis=1),axis=1)==0):raise ValueError('Invalid face indices.')
    directed=np.stack((f,np.roll(f,-1,axis=1)),axis=-1).reshape(-1,2)
    lo=np.min(directed,axis=1);hi=np.max(directed,axis=1)
    keys=lo*np.int64(nv)+hi;order=np.argsort(keys,kind='stable');sk=keys[order]
    starts=np.r_[0,np.flatnonzero(sk[1:]!=sk[:-1])+1];counts=np.diff(np.r_[starts,len(order)])
    if np.any(counts>2):raise ValueError('Patch has a nonmanifold edge.')
    interior=counts==2
    first=directed[order[starts[interior]]];second=directed[order[starts[interior]+1]]
    if not np.array_equal(first,second[:,::-1]):raise ValueError('Patch oriented edge cycles disagree.')
    boundary=directed[order[starts[counts==1]]]
    used=np.unique(f);edge=directed[order[starts]]
    rows=np.r_[edge[:,0],edge[:,1]];cols=np.r_[edge[:,1],edge[:,0]]
    graph=csr_matrix((np.ones(len(rows),np.uint8),(rows,cols)),shape=(nv,nv))
    _,labels=connected_components(graph,directed=False)
    components=len(np.unique(labels[used]))
    loops=0
    if len(boundary):
        bverts=np.unique(boundary);degree=np.bincount(boundary.ravel(),minlength=nv)
        if np.any(degree[bverts]!=2):raise ValueError('Boundary is not a collection of simple loops.')
        bg=csr_matrix((np.ones(2*len(boundary),np.uint8),
            (np.r_[boundary[:,0],boundary[:,1]],np.r_[boundary[:,1],boundary[:,0]])),shape=(nv,nv))
        _,blabels=connected_components(bg,directed=False);loops=len(np.unique(blabels[bverts]))
    chi=len(used)-len(starts)+len(f)
    return dict(vertices=int(len(used)),edges=int(len(starts)),faces=int(len(f)),
        components=int(components),boundary_edges=int(len(boundary)),boundary_loops=int(loops),
        Euler_characteristic=int(chi)),boundary


def validate_patch(base_xyz,base_quads,patch,*,position_tolerance=1e-9):
    """Check the actual stitch, rather than spatial proximity of two meshes."""
    x=np.asarray(patch['vertices'],np.float64);t=np.asarray(patch['triangles'],np.int64)
    binding=np.asarray(patch['host_vertex_ids'],np.int64)
    removed=np.asarray(patch['removed_host_face_ids'],np.int64)
    if x.shape!=(len(x),3) or binding.shape!=(len(x),) or not len(x) or not np.isfinite(x).all():raise ValueError('Invalid patch XYZ/binding.')
    if removed.ndim!=1 or not len(removed) or np.any(np.diff(removed)<=0) or removed[0]<0 or removed[-1]>=len(base_quads):raise ValueError('Sorted unique removed host quads required.')
    if np.any(binding < -1) or np.any(binding>=len(base_xyz)):raise ValueError('Invalid original host vertex binding.')
    bound=binding>=0
    if len(np.unique(binding[bound]))!=int(bound.sum()):raise ValueError('A host vertex has multiple local bindings.')
    error=float(np.max(abs(x[bound]-base_xyz[binding[bound]]),initial=0))
    if error>position_tolerance:raise ValueError('Bound coordinates differ from the actual carrier.')
    # Compact the source disk solely for its bounded topology audit.
    q=np.asarray(base_quads[removed]);old_ids=np.unique(q);local=np.searchsorted(old_ids,q)
    old,old_boundary=surface_topology(local,len(old_ids));old_boundary=old_ids[old_boundary]
    new,new_boundary=surface_topology(t,len(x))
    if old['components']!=1 or old['boundary_loops']!=1 or old['Euler_characteristic']!=1:raise ValueError('Removed host region must be one topological disk.')
    if new['components']!=1 or new['boundary_loops']!=1:raise ValueError('Replacement must be connected with exactly one boundary.')
    mapped=binding[new_boundary]
    if np.any(mapped<0):raise ValueError('Every replacement boundary vertex must bind to the original carrier.')
    nv=len(base_xyz)
    def ordered(edges):
        return edges[np.argsort(np.min(edges,axis=1)*np.int64(nv)+np.max(edges,axis=1))]
    if not np.array_equal(ordered(mapped),ordered(old_boundary)):raise ValueError('The directed original boundary loop is not exactly preserved.')
    p=x[t];area=.5*np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
    if np.any(area<=0) or not np.isfinite(area).all():raise ValueError('Replacement has degenerate triangles.')
    genus=(1-new['Euler_characteristic'])/2
    if genus<0 or genus!=int(genus):raise ValueError('Invalid orientable one-boundary replacement topology.')
    return dict(source_disk=old,replacement=new,added_handles=int(genus),
        exact_directed_boundary_binding=True,maximum_binding_coordinate_error=error,
        minimum_triangle_area=float(area.min()),bound_vertices=int(bound.sum()),
        new_vertices=int((~bound).sum()),removed_quads=len(removed),new_triangles=len(t))


def assemble_patches(base_xyz,base_quads,patches,folder,*,chunk=65536,progress=print):
    """Out-of-core mixed native surface, preserving quads and exact carrier XYZ.

    Patch dictionaries use vertices, triangles, host_vertex_ids, and
    removed_host_face_ids. Optional triangle_classes is an integer display tag.
    The original carrier must already be a closed connected oriented manifold;
    this input contract is recorded, not silently inferred from vertex count.
    """
    root=Path(folder);root.mkdir(parents=True,exist_ok=False)
    def disk(name,shape,dtype,fill=None):
        result=np.lib.format.open_memmap(root/(name+'.npy'),mode='w+',dtype=dtype,shape=shape)
        if fill is not None:result.fill(fill)
        return result
    nv,nq=len(base_xyz),len(base_quads);keep=np.ones(nq,bool);audits=[];nextra=nt=0
    if not patches:raise ValueError('At least one actual stitched patch is required.')
    for number,patch in enumerate(patches):
        audit=validate_patch(base_xyz,base_quads,patch);removed=patch['removed_host_face_ids']
        if not np.all(keep[removed]):raise ValueError('Replacement disks overlap.')
        keep[removed]=False;audits.append(audit);nextra+=audit['new_vertices'];nt+=audit['new_triangles']
        progress('PATCH_VALIDATED',number,audit['added_handles'],audit['new_triangles'],flush=True)
    nqout=int(keep.sum());temporary=disk('UNCOMPACTED_XYZ',(nv+nextra,3),np.float64)
    for a in range(0,nv,chunk):temporary[a:min(a+chunk,nv)]=base_xyz[a:min(a+chunk,nv)]
    triangles=disk('TRIANGLES',(nt,3),np.int64);tclass=disk('TRIANGLE_CLASSES',(nt,),np.int16,fill=0)
    vpos=nv;tpos=0
    for patch in patches:
        x=np.asarray(patch['vertices']);binding=np.asarray(patch['host_vertex_ids']);fresh=binding<0
        mapping=binding.copy();mapping[fresh]=np.arange(vpos,vpos+int(fresh.sum()),dtype=np.int64)
        temporary[vpos:vpos+int(fresh.sum())]=x[fresh]
        t=np.asarray(patch['triangles']);triangles[tpos:tpos+len(t)]=mapping[t]
        tags=patch.get('triangle_classes',np.zeros(len(t),np.int16))
        if np.asarray(tags).shape!=(len(t),):raise ValueError('Triangle class shape differs.')
        tclass[tpos:tpos+len(t)]=tags;vpos+=int(fresh.sum());tpos+=len(t)
    quads=disk('QUADS',(nqout,4),np.int64);source_face=disk('SOURCE_QUAD_IDS',(nqout,),np.int64)
    pos=0
    for a in range(0,nq,chunk):
        b=min(a+chunk,nq);ids=np.arange(a,b,dtype=np.int64)[keep[a:b]];n=len(ids)
        quads[pos:pos+n]=base_quads[ids];source_face[pos:pos+n]=ids;pos+=n
    used=disk('USED_UNCOMPACTED_VERTICES',(nv+nextra,),np.bool_,fill=False)
    for faces in (quads,triangles):
        for a in range(0,len(faces),chunk):used[faces[a:a+chunk].ravel()]=True
    remap=disk('OLD_TO_NEW',(nv+nextra,),np.int64);np.cumsum(used,dtype=np.int64,out=remap)
    final_nv=int(remap[-1]);remap-=1;remap[~used]=-1
    xyz=disk('XYZ',(final_nv,3),np.float64);pos=0
    for a in range(0,len(temporary),chunk):
        b=min(a+chunk,len(temporary));block=temporary[a:b][used[a:b]];xyz[pos:pos+len(block)]=block;pos+=len(block)
    for faces in (quads,triangles):
        for a in range(0,len(faces),chunk):faces[a:a+chunk]=remap[faces[a:a+chunk]]
    for arr in (temporary,quads,triangles,tclass,source_face,used,remap,xyz):arr.flush()
    result=dict(kind='EXACT_BOUNDARY_STITCHED_MIXED_QUAD_TRIANGLE_ORNAMENT_SURFACE',
        input_contract='Carrier is an independently verified closed connected oriented manifold.',
        counts=dict(vertices=final_nv,quads=nqout,triangles=nt,removed_quads=int((~keep).sum()),
            discarded_unreferenced_vertices=int((~used).sum())),patch_audits=audits,
        added_handles=sum(a['added_handles'] for a in audits),
        native_carrier_quads_preserved=True,all_surviving_carrier_coordinates_exact=True,
        connection_proof='Disjoint carrier disks replaced by oriented connected one-boundary patches with exact directed host-edge loops. Connected closed carrier therefore remains connected and closed.',
        global_self_intersection_checked=False,
        arrays={name:record(root/(name+'.npy')) for name in ('XYZ','QUADS','TRIANGLES','TRIANGLE_CLASSES','SOURCE_QUAD_IDS','OLD_TO_NEW')})
    with (root/'ASSEMBLY_RECEIPT.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    return result
