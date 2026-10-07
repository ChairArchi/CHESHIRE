"""Measured high-angle components and annotated graph views, no geometry edits."""
from collections import defaultdict
from math import acos, degrees
from cross_cell_crease_study import raw_mesh, dot, read, write


def high_angle_components(geometry, cells, history, threshold=20.):
    mesh = raw_mesh(geometry); normals = {f: mesh.face_normal(f) for f in mesh.faces()}
    edges = {}
    for e in mesh.edges():
        e=tuple(sorted(e)); a,b=mesh.edge_faces(e)
        if a is None or b is None: continue
        if any(sum(x*x for x in normals[f]) < .5 for f in (a,b)): continue
        angle=degrees(acos(dot(normals[a],normals[b])))
        if angle >= threshold: edges[e]=(mesh.edge_length(e),angle,(a,b))
    adjacency=defaultdict(set)
    for e in edges:
        for v in e: adjacency[v].add(e)
    remaining=set(edges); components=[]
    while remaining:
        stack=[min(remaining)]; members=[]
        while stack:
            e=stack.pop()
            if e not in remaining: continue
            remaining.remove(e); members.append(e)
            for v in e: stack.extend(sorted(adjacency[v]&remaining))
        parent_cells=sorted({c for e in members for f in edges[e][2] for c in cells.get(str(f),cells.get(f,[]))})
        coarse=sorted({int(c) for e in members for f in edges[e][2] for c,w in history.get(str(f),history.get(f,{}))['source'].items() if w>0})
        components.append(dict(edge_count=len(members), length=sum(edges[e][0] for e in members),
            maximum_angle=max(edges[e][1] for e in members), parent_cells=parent_cells,C0_faces=coarse,
            cross_cell=len(parent_cells)>=3 or len(coarse)>=2))
    components.sort(key=lambda r:-r['length'])
    return dict(threshold_degrees=threshold,high_angle_edge_count=len(edges),component_count=len(components),
        cross_cell_component_count=sum(r['cross_cell'] for r in components),components=components,
        scope='Current whole-mesh adjacent-normal contrast, with actual positive face ancestry. No occlusion test or aesthetic score.'), edges


def annotated_views(directory, geometry, networks, output, key, generation0=False):
    lineage=read(directory/((key.split('_')[-1])+'_lineage.json.gz'))
    mesh=raw_mesh(geometry); cells=lineage['source_cells']; history=lineage['history']
    metrics, angles=high_angle_components(geometry,cells,history)
    write(output/(key+'_high_angle_metrics.json'),metrics)
    # Dominant positive ancestry and actual ornament depth remain distinct views.
    ancestry={int(f): int(max(r['source'],key=lambda c:(r['source'][c],-int(c)))) for f,r in history.items()}
    depth={int(f):r['depth'] for f,r in history.items()}
    write(output/(key+'_ancestry.json'),ancestry); write(output/(key+'_depth.json'),depth)
    allsharp=[e['sharpness'] for n in networks for e in n['edges']]; maximum=max(allsharp,default=1.) or 1.
    sharp=dict(edges=[dict(vertices=e['vertices'],sharpness=e['sharpness'],code=min(8,int(8*e['sharpness']/maximum))) for n in networks for e in n['edges']],
        junctions=sorted({v for n in networks for v in n['junction_vertices']}),directions=[],legend='Initial/remaining sharpness 0 gray -> 8; declared edges incl. hidden')
    write(output/(key+'_sharpness.json'),sharp)
    high=dict(edges=[dict(vertices=list(e),sharpness=1,code=6) for e in angles],junctions=[],directions=[],
        legend='ACTUAL adjacent-normal contrast >=20 degrees; projected incl. hidden edges')
    write(output/(key+'_high.json'),high)
    if generation0:
        boundaries=[]
        for e in mesh.edges():
            a,b=mesh.edge_faces(e)
            if a is not None and b is not None and set(cells[str(a)]) != set(cells[str(b)]):
                boundaries.append(dict(vertices=list(e),sharpness=0,code=-1))
        write(output/(key+'_cell_boundaries.json'),dict(edges=boundaries,junctions=[],directions=[],
            legend='Frozen parent-cell boundaries, incl. hidden; separate from crease graph'))
    return metrics
