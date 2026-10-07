"""Evaluate existing fold point rules on one COMPAS crease topology.

Task25 memory adaptation: the old path materializes crease, sharp and smooth
meshes simultaneously. This path evaluates the same existing equations point
by point using the previous mesh neighborhoods. No cut pieces or new topology.
"""
from collections import Counter
from dataclasses import replace
from hashlib import sha256
import json
from math import hypot,isfinite

from compas.geometry import centroid_points
from .weighted_subdivision import mean,_extrude
from .generational_subdivision import classify_child_quad,later_generation_face_stencil
from .sharp_subdivision import motif_values,equation10,equation11
from .validation import inspect_mesh,validate_mesh


def apply_points(mesh,reference,support,weights,declaration,current_generation,origins):
    output=reference.mesh
    xyz={v:mesh.vertex_coordinates(v) for v in mesh.vertices()}
    centres={f:mean(xyz[v] for v in mesh.face_vertices(f)) for f in mesh.faces()}
    cc_centres={f:list(mesh.face_centroid(f)) for f in mesh.faces()}
    normals={f:list(mesh.face_normal(f)) for f in mesh.faces()}
    edge_sources={r['point']:tuple(r['edge']) for r in reference.metadata['edge_points']}
    edge_ids={tuple(sorted(e)):p for p,e in edge_sources.items()}
    originals=set(xyz);edge_keys=set(edge_sources);face_ids={}
    for r in reference.metadata['face_sources']:
        candidates=set(output.face_vertices(r['id']))-originals-edge_keys
        if len(candidates)!=1:raise ValueError('Ambiguous structural point correspondence.')
        p=candidates.pop();f=r['source_face']
        if f in face_ids and face_ids[f]!=p:raise ValueError('Inconsistent actual face point.')
        face_ids[f]=p
    faces_by_point={p:f for f,p in face_ids.items()}
    u=motif_values(mesh,declaration.get('u_map',{}),declaration.get('unknown_u',0.))
    for v in u:u[v]*=support[v]

    def initial(p):
        if p in xyz:return xyz[p]
        if p in edge_sources:
            a,b=edge_sources[p]
            return [(xyz[a][i]+xyz[b][i])/2 for i in range(3)]
        return cc_centres[faces_by_point[p]]

    # Keep a checksum and a bounded audit sample, rather than duplicate millions
    # of XYZ/weight dictionaries already represented by recipe+input+output.
    audit=sha256();samples=[];active=Counter();fallbacks=Counter();eligible=0
    def place(kind,source,p,parents,sharp,smooth):
        alpha=sum(support[v] for v in parents)/len(parents)
        delta=[alpha*(a-b) for a,b in zip(sharp,smooth)]
        point=[a+b for a,b in zip(output.vertex_coordinates(p),delta)]
        if not all(isfinite(x) for x in point):raise ValueError('Non-finite existing pointwise fold placement.')
        output.vertex_attributes(p,'xyz',point)
        row=dict(point=p,point_class=kind,source=source,route_support=alpha,additional_displacement=delta,result_xyz=point)
        audit.update(json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False).encode());audit.update(b'\n')
        if alpha:active[kind]+=1
        if len(samples)<80 and alpha:samples.append(row)

    for f,p in face_ids.items():
        vertices=mesh.face_vertices(f);alpha=sum(support[v] for v in vertices)/len(vertices)
        if not alpha:continue
        sharp=_extrude(centres[f],normals[f],weights['wf'])
        pattern,reason=classify_child_quad(mesh,f,origins,current_generation)
        if pattern is None:fallbacks[reason]+=1
        else:
            eligible+=1
            if weights['w3'] or weights['w4']:
                sharp=later_generation_face_stencil(*(xyz[pattern[k]] for k in ('V','F','E1','E2')),
                    normals[f],w3=weights['w3'],w4=weights['w4'],wf=weights['wf'])
        sharp=equation10(sharp,[xyz[v] for v in vertices],[u[v] for v in vertices],weights['w6'])
        place('face',f,p,vertices,sharp,cc_centres[f])
    for (a,b),p in edge_ids.items():
        if not (support[a] or support[b]):continue
        f,g=mesh.edge_faces((a,b));w=weights['w1']
        sharp=[((centres[f][i]+centres[g][i])*(1+w)+(xyz[a][i]+xyz[b][i])*(1-w))/4 for i in range(3)]
        sharp=_extrude(sharp,mean(normals[k] for k in (f,g)),weights['we'])
        sharp=equation11(sharp,xyz[a],xyz[b],u[a],u[b],weights['w7'])
        smooth=centroid_points([initial(n) for n in output.halfedge[p]])
        place('edge',[a,b],p,[a,b],sharp,smooth)
    for v in mesh.vertices():
        if not support[v]:continue
        faces=mesh.vertex_faces(v);neighbors=mesh.vertex_neighbors(v);n=len(neighbors);w=weights['w2']
        F=mean(centres[f] for f in faces);E=mean(mean([xyz[v],xyz[z]]) for z in neighbors)
        sharp=[(F[i]*(1+w)+E[i]*(2-w)+xyz[v][i]*(n-3))/n for i in range(3)]
        normal=mean(normals[f] for f in faces);length=hypot(*normal);normal=[x/length for x in normal] if length else [0.,0.,0.]
        sharp=_extrude(sharp,normal,weights['wp'])
        sF=centroid_points([cc_centres[f] for f in faces]);sE=centroid_points([initial(z) for z in output.halfedge[v]])
        smooth=[(sF[i]+2*sE[i]+(n-3.)*xyz[v][i])/n for i in range(3)]
        place('corner',v,v,[v],sharp,smooth)
    if validate_mesh(output) or not output.is_valid() or not output.is_manifold() or not output.is_closed():
        raise ValueError('Pointwise fold produced unusable finite/connectivity state; no repair.')
    nets=tuple(replace(n,path_length=sum(output.edge_length(e.vertices) for e in n.edges)) for n in reference.networks)
    return replace(reference,mesh=output,networks=nets,metadata={**reference.metadata,
        'name':'Existing fold equations evaluated pointwise on COMPAS crease topology',
        'output':inspect_mesh(output),'combined_fold':dict(declaration=declaration,actual_weights=weights,
            execution='POINTWISE_EXISTING_STENCILS',input_route_support={v:a for v,a in support.items() if a},
            zero_support='Omitted support entries are zero; reference crease point retained exactly.',
            active_point_counts=dict(active),placement_audit_sha256=audit.hexdigest(),placement_sample=samples,
            later_face_stencil=dict(eligible_active_faces=eligible,fallback_active_counts=dict(fallbacks)),
            scope='Same parent neighborhoods, Eq4/10/11 functions and weighted formulas; no chunking, remeshing or topology change. Complete origins and face/event/branch state retained separately.')})
