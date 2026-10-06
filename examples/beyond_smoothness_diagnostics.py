"""Separate sharpness, ancestry and validity observations; no aesthetic score."""
from collections import Counter,defaultdict,deque
from math import acos,degrees,fsum
from cheshire.sharp_subdivision import topology_motifs,normal_variation_values
from carrier_scale_study import extra_diagnostics
from ornament_study import distributions

def stats(values):
    values=sorted(v for v in values if v is not None); n=len(values)
    return dict(min=values[0],p10=values[int(.1*(n-1))],median=values[(n-1)//2],p90=values[int(.9*(n-1))],max=values[-1],mean=fsum(values)/n) if n else None

def observe(mesh,cells=None,threshold=45.,source_history=None):
    normals={f:mesh.face_normal(f) for f in mesh.faces()}; angles=[]; sharp=[]; undefined=0
    for u,v in mesh.edges():
        a,b=mesh.halfedge[u][v],mesh.halfedge[v][u]
        if a is None or b is None: continue
        if any(fsum(x*x for x in normals[f])<.5 for f in (a,b)):
            undefined+=1; continue
        angle=degrees(acos(max(-1,min(1,fsum(x*y for x,y in zip(normals[a],normals[b]))))))
        angles.append(angle)
        if angle>=threshold: sharp.append((u,v,a,b,angle))
    graph=defaultdict(set); byvertex=defaultdict(set)
    for index,(u,v,*_) in enumerate(sharp): byvertex[u].add(index); byvertex[v].add(index)
    for indices in byvertex.values():
        for i in indices: graph[i].update(indices-{i})
    remaining=set(range(len(sharp))); components=[]
    while remaining:
        seed=min(remaining); found={seed}; queue=deque([seed]); remaining.remove(seed)
        while queue:
            i=queue.popleft(); new=graph[i]&remaining; remaining.difference_update(new); found.update(new); queue.extend(sorted(new))
        ancestral=set(); macro=set()
        if cells:
            for i in found:
                ancestral.update(cells.get(sharp[i][2],())); ancestral.update(cells.get(sharp[i][3],()))
                if source_history:
                    macro.update(source_history[sharp[i][2]]['source']); macro.update(source_history[sharp[i][3]]['source'])
        components.append(dict(edges=len(found),source_cells=sorted(ancestral),source_cell_count=len(ancestral),
            crosses_ancestry_boundary=len(ancestral)>1,source_C0_face_ids=sorted(macro),source_C0_face_count=len(macro)))
    components.sort(key=lambda r:(-r['edges'],r['source_cells']))
    d=extra_diagnostics(mesh)
    variation=normal_variation_values(mesh)
    d.update(distributions=distributions(mesh),dihedral_degrees=stats(angles),high_dihedral_threshold_degrees=threshold,
        high_dihedral_edge_count=len(sharp),high_dihedral_edge_fraction=len(sharp)/len(angles) if angles else 0,undefined_adjacent_normal_edges=undefined,
        local_normal_variation=stats(variation.values()),local_normal_variation_undefined_vertices=sum(v is None for v in variation.values()),
        motif_histogram=dict(Counter(s.key() for s in topology_motifs(mesh).values())),
        cross_cell_sharp_components=dict(total=len(components),confined=sum(c['source_cell_count']==1 for c in components),
            multiple_neighboring_cells=sum(c['source_cell_count']>1 for c in components),largest_components=components[:80],
            multiple_C0_source_faces=sum(c['source_C0_face_count']>1 for c in components),
            high_edges_crossing_frozen_cell_boundaries=sum(set(cells.get(a,()))!=set(cells.get(b,())) for _,_,a,b,_ in sharp) if cells else None,
            high_edges_crossing_C0_source_face_boundaries=sum(set(source_history[a]['source'])!=set(source_history[b]['source']) for _,_,a,b,_ in sharp) if source_history else None,
            note='Connected edges with >=45 degree adjacent-face-normal contrast. Source cells are frozen prefix faces; connectivity is geometric adjacency, not evidence of visual hierarchy.'),
        high_dihedral_faces=sorted({f for _,_,a,b,_ in sharp for f in (a,b)}))
    return d

def geometry_state(d,crossings):
    if d['degenerate_fan_faces'] or d['distributions']['face_area']['min']<=0 or d['components']!=1 or not d['is_manifold'] or not d['is_closed'] or crossings.get('sample_limit_reached'):
        return 'UNSTABLE'
    if d['opposed_fan_normals'] or d['bilinear_admissibility_warning_faces'] or crossings.get('sampled_transverse_crossings',0):
        return 'BOUNDARY_SHARP'
    return 'VALID_SHARP'
