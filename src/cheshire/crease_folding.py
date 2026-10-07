"""Experimental route-local composition of verified point placement and creases.

The additional placement is CHESHIRE composition, not a DeRose crease mask.
The reference crease implementation remains independently unchanged.
"""
from collections import deque
from dataclasses import replace
from math import isfinite

from .creases import crease_subdivide_once, edge_key
from .sharp_subdivision import sharp_subdivide_once, WEIGHTS, finite
from .validation import inspect_mesh, validate_mesh


def route_support(mesh,networks,hops):
    if type(hops) is not int or hops<1:
        raise ValueError('Positive explicit route-band radius required.')
    seeds={v for n in networks for e in n.edges for v in e.vertices}
    if not seeds or not seeds<=set(mesh.vertices()):
        raise ValueError('Actual current crease vertices required for fold support.')
    distances={v:0 for v in seeds};queue=deque(sorted(seeds))
    while queue:
        v=queue.popleft()
        if distances[v]>=hops:continue
        for u in sorted(mesh.vertex_neighbors(v)):
            if u not in distances:distances[u]=distances[v]+1;queue.append(u)
    return {v:max(0.,1-distances.get(v,hops)/hops) for v in mesh.vertices()}


def folded_crease_once(mesh,networks,declaration,*,mode='INTEGER_COMPAS',budget=None,current_generation=0):
    """P = reference crease point + route support*(sharp-weighted - smooth).

    Sharp-weighted uses existing literal Eq10/11 and Extended CC. Points are
    matched only by original corner, edge or face identity, never coordinates.
    Normal-extrusion weights are absolute model units, not dimensionless ratios.
    """
    requested=declaration.get('weights',{})
    if set(requested)-set(WEIGHTS):raise ValueError('Unknown combined fold weight.')
    weights={k:finite(requested.get(k,0.)) for k in WEIGHTS}
    reference=crease_subdivide_once(mesh,networks,mode=mode,budget=budget,current_generation=current_generation)
    if all(w==0 for w in weights.values()):
        return reference
    if weights['w3'] or weights['w4']:
        raise ValueError('This composition does not invent later point-origin stencils; w3/w4 must be zero.')
    support=route_support(mesh,networks,declaration['band_hops'])
    overrides={'face':{},'edge':{},'corner':{}}
    # Do not request an unused normal extrusion in a zero-support quiet zone.
    for f in mesh.faces():
        if not any(support[v] for v in mesh.face_vertices(f)):overrides['face'][f]={'wf':0.}
    for e in mesh.edges():
        if not any(support[v] for v in e):overrides['edge'][e]={'we':0.}
    for v in mesh.vertices():
        if not support[v]:overrides['corner'][v]={'wp':0.}
    # A separate verified sharp operator computes its exact literal equations.
    # The caller's original mesh and implicit crease attributes stay untouched.
    sharp=sharp_subdivide_once(mesh,weights,u_map=declaration.get('u_map',{}),
        unknown_u=declaration.get('unknown_u',0.),vertex_u_scale=support,
        point_weights=overrides,budget=budget,current_generation=current_generation)
    smooth=crease_subdivide_once(mesh,(),budget=budget,current_generation=current_generation)
    output=reference.mesh
    corners=set(mesh.vertices());edge_ids={edge_key(r['edge']):r['point'] for r in reference.metadata['edge_points']}
    edge_points=set(edge_ids.values());face_ids={}
    for r in reference.metadata['face_sources']:
        candidates=set(output.face_vertices(r['id']))-corners-edge_points
        if len(candidates)!=1:raise ValueError('Ambiguous actual face-point correspondence in fold composition.')
        child=candidates.pop();parent=r['source_face']
        if parent in face_ids and face_ids[parent]!=child:raise ValueError('Inconsistent face-point correspondence.')
        face_ids[parent]=child
    mappings=[];seen=set()
    for r in sharp.metadata['points']:
        kind=r['point_class'];source=r['source']
        child=source if kind=='corner' else edge_ids[edge_key(source)] if kind=='edge' else face_ids[source]
        if child in seen:raise ValueError('Duplicate point placement; no topology reinterpretation.')
        seen.add(child)
        parents=[source] if kind=='corner' else source if kind=='edge' else mesh.face_vertices(source)
        alpha=sum(support[v] for v in parents)/len(parents)
        delta=[alpha*(a-b) for a,b in zip(sharp.mesh.vertex_coordinates(r['id']),smooth.mesh.vertex_coordinates(child))]
        xyz=[a+b for a,b in zip(output.vertex_coordinates(child),delta)]
        if not all(isfinite(x) for x in xyz):raise ValueError('Nonfinite combined fold placement.')
        output.vertex_attributes(child,'xyz',xyz)
        mappings.append(dict(point=child,sharp_point=r['id'],point_class=kind,source=source,
            route_support=alpha,additional_displacement=delta,result_xyz=xyz))
    if seen!=set(output.vertices()):raise ValueError('Incomplete structural point placement coverage.')
    if validate_mesh(output) or not output.is_valid() or not output.is_manifold() or not output.is_closed():
        raise ValueError('Combined fold output is not finite/closed/topologically usable; no repair.')
    nets=tuple(replace(n,path_length=sum(output.edge_length(e.vertices) for e in n.edges)) for n in reference.networks)
    metadata={**reference.metadata,'output':inspect_mesh(output),'name':'Route-local sharp placement plus persistent crease CC',
        'combined_fold':dict(declaration=declaration,actual_weights=weights,input_route_support=support,
            placement=mappings,verified_sharp_operator=sharp.metadata,
            equation='P_crease + alpha*(P_existing_sharp_weighted - P_standard_smooth)',
            scope='Experimental additive CHESHIRE composition; reference stencil before this displacement remains independent. Positive construction association unchanged; no generic semantic inheritance.' )}
    return replace(reference,mesh=output,networks=nets,metadata=metadata)
