"""Causal study: face-only versus edge/face differentiated generational stencils.
No appended fin meshes, height bands, or angular placement list.
"""
import argparse,json
import numpy as np
import fluted_generation as common
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.execution import ExecutionBudget

def run(mode,output):
    source=common.ROOT/'fluted_generation_results/g00/mesh.json';j=json.loads(source.read_text());mesh=common.Mesh.from_vertices_and_faces(j['vertices'],j['faces']);origins=None
    output.mkdir(exist_ok=True,parents=True);common.OUT=output
    for generation in range(2):
        areas={f:float(mesh.face_area(f)) for f in mesh.faces()};xyz={v:mesh.vertex_coordinates(v) for v in mesh.vertices()}
        face={};edge={}
        for f in mesh.faces():
            scale=np.sqrt(areas[f]);normal=mesh.face_normal(f)
            cap=abs(normal[2])>.999
            face[f]={'wf':float(0 if cap else scale*(.35 if mode=='face' else (-.10 if generation==0 else .18)))}
        for u,v in mesh.edges():
            incident=[f for f in [mesh.halfedge[u][v],mesh.halfedge[v][u]] if f is not None]
            scale=np.sqrt(min(areas[f] for f in incident))
            cap=all(abs(mesh.face_normal(f)[2])>.999 for f in incident)
            edge[(u,v)]={'we':float(0 if cap or mode in ['face','noedge'] else .48*scale),'w1':-1.}
        weights={'w1':-1.,'w3':.8 if mode!='face' and generation else 0.,'w4':.35 if mode!='face' and generation else 0.}
        result=generational_subdivide_once(mesh,weights,point_weights={'face':face,'edge':edge},origin_lineage=origins,current_generation=generation,budget=ExecutionBudget(150000,150000))
        # Explicit sharp study policy: retain old corners; do not average away parent relief.
        for v,p in xyz.items():result.mesh.vertex_attributes(v,'xyz',p)
        mesh=result.mesh;origins=result.origin_lineage
        common.save(mesh,generation+1,dict(mode=mode,operation='existing CHESHIRE generational stencil with point-class-specific normal displacement',weights=weights,face_multiplier=.35 if mode=='face' else (-.1 if generation==0 else .18),edge_multiplier=0 if mode in ['face','noedge'] else .48,corner_policy='original corner coordinates retained',eligible_ancestral_quads=result.metadata['later_generation_face_stencil']['eligible_faces'],fin_template=False,smoothing=False,claim='controlled hypothesis; not recovered original coefficients'))
        (output/f'g{generation+1:02d}'/'lineage.json').write_text(json.dumps(dict(origins=origins,face_sources=result.metadata['face_sources'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['face','edge','noedge'],required=True);a=p.parse_args();run(a.mode,common.ROOT/f'fin_{a.mode}_results')
