"""Connected face-patch folding by finite rotations, an independent hypothesis.

A dominant current hinge supplies a direction, not a face-ID motif. Exact
midpoint refinement precedes opposite rotations across an interior crease.
Shared-point proposals are area-weighted; intersections are not repaired.
"""
import numpy as np
from .reference_subdivision import ArrayMesh, topology
from .astra_rotating import features


def step(mesh, *, angle=1.1, source='current', direction='parallel', retention=.35, feedback=True):
    if not np.isfinite([angle, retention]).all() or not 0<=angle<=2.5 or not 0<=retention<=1:
        raise ValueError('Invalid finite controls.')
    if source not in ('current','rest') or direction not in ('parallel','transverse'):
        raise ValueError('Unknown geometric observation/direction.')
    t, actual, _ = features(mesh)
    observed = mesh if source=='current' else ArrayMesh(mesh.rest,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    _, obs, feat = features(observed)
    x=mesh.xyz;q=mesh.faces[:,:3];nv=len(x);edges=t['edges'];ne=len(edges);nf=len(q)
    edgeangles=feat['edge_angle'][t['fe'][:,:3]]
    dominant=np.abs(edgeangles)>=np.abs(edgeangles).max(1)[:,None]-1e-12
    # All tied dominant directions contribute, avoiding arbitrary edge IDs.
    strength=np.tanh(2*np.abs(edgeangles)) if feedback else np.ones_like(edgeangles)
    base=np.concatenate([x,x[edges].mean(1)])
    mids=t['fe'][:,:3]+nv
    patch_ids=np.concatenate([q,mids],axis=1)
    patches=base[patch_ids]
    centre=actual['c'];relative=patches-centre[:,None]
    proposal=np.zeros_like(patches)
    resolved=[]
    for slot in range(3):
        axis=x[q[:,(slot+1)%3]]-x[q[:,slot]]
        axis/=np.linalg.norm(axis,axis=1)[:,None]
        if direction=='transverse':axis=np.cross(actual['nf'],axis)
        side=np.cross(actual['nf'],axis)
        distance=np.sum(relative*side[:,None],axis=2)
        support=np.max(np.abs(distance),axis=1)
        # Smooth only the crease angle across its local width; no XYZ smoothing.
        signed=np.tanh(5*distance/np.maximum(support[:,None],1e-12))
        theta=angle*strength[:,slot,None]*signed
        cosine=np.cos(theta)[:,:,None];sine=np.sin(theta)[:,:,None]
        rotated=relative*cosine+np.cross(axis[:,None],relative)*sine+axis[:,None]*np.sum(axis[:,None]*relative,axis=2)[:,:,None]*(1-cosine)
        proposal+=(rotated-relative)*dominant[:,slot,None,None]/dominant.sum(1)[:,None,None]
        resolved.append(theta)
    weights=np.repeat(actual['area'],6)
    ids=patch_ids.ravel();total=np.bincount(ids,weights=weights,minlength=len(base))
    displacement=np.column_stack([np.bincount(ids,weights=weights*proposal[:,:,k].ravel(),minlength=len(base))/total for k in range(3)])
    displacement[:nv]*=retention
    xyz=base+displacement
    a,b,c=q.T;ab,bc,ca=mids.T
    faces=np.stack([np.column_stack([a,ab,ca]),np.column_stack([ab,b,bc]),np.column_stack([ca,bc,c]),np.column_stack([ab,bc,ca])],axis=1).reshape(-1,3)
    parent=np.repeat(np.arange(nf),4)
    out=ArrayMesh(xyz,np.column_stack([faces,np.full(len(faces),-1,np.int64)]),np.r_[np.zeros(nv,np.int8),np.ones(ne,np.int8)],np.concatenate([mesh.rest,mesh.rest[edges].mean(1)]),mesh.anchors[parent],mesh.generation+1)
    if not np.isfinite(xyz).all():raise ValueError('Nonfinite output.')
    topology(out)
    p=xyz[faces];areas=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2
    if np.any(areas<=1e-12):raise ValueError('Degenerate output.')
    state=dict(base_xyz=base,resolved_displacement=displacement,parent_faces=parent,input_edges=edges,new_vertex_parent_faces=t['ef'],input_faces=q.copy(),dominant_hinges=dominant,observed_edge_angles=edgeangles,patch_vertex_ids=patch_ids,patch_rotation_proposals=proposal,resolved_angles=np.stack(resolved,axis=1))
    meta=dict(implementation='FREEDOM_CONNECTED_ROTATING_PATCH',parameters=dict(angle=angle,source=source,direction=direction,retention=retention,feedback=feedback),limitations='Own finite patch-rotation hypothesis. Current placement axes/normals with current or evolving-rest hinge selection. Shared proposals area-averaged. No collision repair. Retention scales all previous-point motion, not fixed boundary conditions.')
    return out,meta,state


def connected_step(mesh, *, angle=1.1, radius=350., source='current', direction='parallel', seed_quantile=.85, seed_length_floor=None):
    """One current geometric hinge rotates a connected multi-cell neighborhood.

    Graph shortest paths from exact edge midpoints bound each patch. Radius is
    in model units. Seeds are current hinge/length quantiles with symmetry ties;
    every seed contribution and its actual affected vertex IDs are recorded.
    """
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    if not np.isfinite([angle,radius,seed_quantile]).all() or not 0<=angle<=2.5 or radius<=0 or not 0<=seed_quantile<=1:
        raise ValueError('Invalid connected-patch controls.')
    if source not in ('current','rest') or direction not in ('parallel','transverse'):
        raise ValueError('Unknown connected-patch mode.')
    t,actual,actualfeat=features(mesh)
    observed=mesh if source=='current' else ArrayMesh(mesh.rest,mesh.faces,mesh.classes,mesh.rest,mesh.anchors,mesh.generation)
    _,obs,feat=features(observed)
    out,_,state=step(mesh,angle=0)
    base=state['base_xyz'];edges=t['edges'];nv=len(mesh.xyz)
    bend=np.abs(feat['edge_angle']);threshold=float(np.quantile(bend,seed_quantile))
    floor=radius*.15 if seed_length_floor is None else float(seed_length_floor)
    if not np.isfinite(floor) or floor<0:raise ValueError('Invalid seed physical length floor.')
    length_threshold=max(float(np.quantile(obs['lengths'],.6)),floor)
    selected=(bend>=max(threshold,1e-8)-1e-12)&(obs['lengths']>=length_threshold-1e-9)
    seeds=np.flatnonzero(selected)
    refined=topology(out);re=refined['edges'];lengths=np.linalg.norm(base[re[:,1]]-base[re[:,0]],axis=1)
    graph=coo_matrix((np.repeat(lengths,2),(re.ravel(),re[:,::-1].ravel())),shape=(len(base),len(base))).tocsr()
    accum=np.zeros_like(base);total=np.zeros(len(base));coverage=np.zeros(len(base),np.int64)
    memberships=[];distances=[];seed_parents=[];contributions=[];axes=[];origins=[]
    for seed in seeds:
        origin=base[nv+seed];axis=mesh.xyz[edges[seed,1]]-mesh.xyz[edges[seed,0]];axis/=np.linalg.norm(axis)
        normal=actual['nf'][t['ef'][seed]].sum(0);normal_norm=np.linalg.norm(normal)
        if normal_norm<=1e-12:continue
        normal/=normal_norm
        if direction=='transverse':axis=np.cross(normal,axis);axis/=np.linalg.norm(axis)
        side=np.cross(normal,axis)
        distance=dijkstra(graph,directed=True,indices=int(nv+seed),limit=radius)
        ids=np.flatnonzero(distance<radius)
        delta=base[ids]-origin
        taper=(1-(distance[ids]/radius)**2)**2
        theta=angle*np.tanh(2*bend[seed])*np.tanh(5*(delta@side)/radius)*taper
        cosine=np.cos(theta)[:,None];sine=np.sin(theta)[:,None]
        rotated=delta*cosine+np.cross(axis,delta)*sine+axis*(delta@axis)[:,None]*(1-cosine)
        move=rotated-delta
        # Seed strength and connected taper, never face IDs, determine overlap.
        weight=taper*bend[seed]
        accum[ids]+=move*weight[:,None];total[ids]+=weight;coverage[ids]+=1
        memberships.append(ids);distances.append(distance[ids]);seed_parents.append(np.full(len(ids),seed,np.int64));contributions.append(move)
        axes.append(axis);origins.append(origin)
    displacement=np.divide(accum,total[:,None],out=np.zeros_like(accum),where=total[:,None]>0)
    out.xyz=base+displacement
    if not np.isfinite(out.xyz).all():raise ValueError('Nonfinite connected patch result.')
    topology(out)
    p=out.xyz[out.faces[:,:3]]
    if np.any(np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)<=2e-12):raise ValueError('Degenerate connected patch result.')
    state.update(resolved_displacement=displacement,seed_edge_ids=seeds,seed_selection_bend=bend,seed_selection_lengths=obs['lengths'],seed_axes=np.asarray(axes),seed_origins=np.asarray(origins),patch_coverage=coverage,patch_vertex_ids_flat=np.concatenate(memberships) if memberships else np.array([],np.int64),patch_geodesic_distance=np.concatenate(distances) if distances else np.array([]),patch_seed_edges=np.concatenate(seed_parents) if seed_parents else np.array([],np.int64),patch_unaveraged_moves=np.concatenate(contributions) if contributions else np.empty((0,3)))
    meta=dict(implementation='FREEDOM_GEODESIC_HINGE_PATCH',parameters=dict(angle=angle,radius=radius,source=source,direction=direction,seed_quantile=seed_quantile,seed_length_floor=seed_length_floor),seed_bend_threshold=threshold,seed_length_threshold=length_threshold,selected_seed_count=len(seeds),covered_vertices=int(np.count_nonzero(coverage)),limitations='Own finite hinge-patch rotation; graph-edge shortest paths approximate geodesic distance. Fixed physical patch radius; current or evolving-rest seed selection, current axes/normals/distance. Overlap weighted by taper and observed bend. No averaging of XYZ except finite rotation proposal overlap. No collision repair or hierarchy certification.')
    return out,meta,state
