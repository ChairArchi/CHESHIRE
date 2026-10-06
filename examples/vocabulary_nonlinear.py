"""Conditional two-cell vertex-alias fixture; no weld/repair engine or gate use."""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from math import dist,fsum
from pathlib import Path
import sys
from compas.datastructures import Mesh

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from ornament_study import digest
from vocabulary_review import STUDY,cases
from cheshire.vocabulary import VocabularyStage,vocabulary_event
from cheshire.ornament import source_history
from cheshire.execution import ExecutionBudget
from cheshire.validation import inspect_mesh,validate_lineage_coverage

THRESHOLD=1e-5
def data(mesh):
    return dict(vertices=[dict(id=v,xyz=mesh.vertex_coordinates(v)) for v in mesh.vertices()],
        faces=[dict(id=f,vertices=mesh.face_vertices(f)) for f in mesh.faces()])

def construct_fixture(dll):
    mesh=Mesh.from_vertices_and_faces([[0,0,0],[1,0,0],[2,0,0],[0,1,0],[1,1,0],[2,1,0]],[[0,1,4,3],[1,2,5,4]])
    original=deepcopy(mesh.__data__)
    stage=VocabularyStage('fixture','DirectionalExtrusion',dict(height_ratio=.2,direction_mode='horizontal',normal_ratio=.6),{})
    result=vocabulary_event(mesh,source_history(mesh),stage,selected_faces=list(mesh.faces()),dll_path=str(dll),budget=ExecutionBudget(64,128,16))
    assert mesh.__data__==original and not validate_lineage_coverage(mesh,result['mesh'],result['lineage'])
    return mesh,result

def alias_proposal(mesh,original_vertices,corner_parents,scale):
    if mesh.number_of_vertices()>32 or mesh.number_of_faces()>16 or scale<=0: raise ValueError('Only the bounded two-cell fixture is supported.')
    original=set(original_vertices); groups=defaultdict(list); aliases={v:v for v in mesh.vertices()}; pairs=[]
    for v in sorted(set(mesh.vertices())-original):
        if corner_parents[v] is not None: groups[corner_parents[v]].append(v)
    for corner,vertices in sorted(groups.items()):
        if len(vertices)>2: raise ValueError('No general clustering; at most two constructive copies of one source corner.')
        if len(vertices)==2:
            a,b=vertices; distance=dist(mesh.vertex_coordinates(a),mesh.vertex_coordinates(b))
            if distance<THRESHOLD*scale:
                aliases[b]=a; pairs.append(dict(vertices=[a,b],source_corner=corner,distance=distance,normalized_distance=distance/scale))
    assert all(aliases[v]==v for v in original)
    faces=[dict(id=f,vertices=[aliases[v] for v in mesh.face_vertices(f)]) for f in mesh.faces()]
    directed=Counter((a,b) for f in faces for a,b in zip(f['vertices'],f['vertices'][1:]+f['vertices'][:1]))
    incident=Counter(tuple(sorted((a,b))) for (a,b),count in directed.items() for _ in range(count))
    bad_edges=[dict(vertices=list(edge),incident_faces=count) for edge,count in sorted(incident.items()) if count>2]
    collapsed=[f['id'] for f in faces if len(set(f['vertices']))!=len(f['vertices'])]
    used={v for f in faces for v in f['vertices']}
    return dict(accepted=False,applied=False,passes_bounded_edge_guard=not(bad_edges or collapsed or any(c>1 for c in directed.values())),
        threshold_normalized=THRESHOLD,characteristic_edge_scale=scale,pairs=pairs,vertex_aliases=aliases,
        before=inspect_mesh(mesh),proposed_topology=dict(vertices=len(used),edges=len(incident),faces=len(faces),
            euler_characteristic=len(used)-len(incident)+len(faces),maximum_edge_face_incidence=max(incident.values(),default=0)),
        rejected_nonmanifold_edges=bad_edges,collapsed_faces=collapsed,repeated_directed_edges=sum(c>1 for c in directed.values()),
        proposed_faces=faces,reason='Conservative quotient guard rejects four-face edges and duplicate directed incidence. Facing interior walls are retained; no hidden deletion or repair.',
        lineage='Constructive pre-join lineage is preserved. No joined lineage or accepted after-mesh is invented.')

def main(dll):
    assessment=read(STUDY/'normal_visual_assessment.json')
    assert assessment['verified_operators_work'] and assessment['strong_cases_still_cell_dominated']
    assert len(cases('F'))>=14 and len(cases('R'))>=18
    out=ROOT/'output/task21/nonlinear'; out.mkdir(parents=True,exist_ok=False)
    source,step=construct_fixture(dll); mesh=step['mesh']; before=deepcopy(mesh.__data__)
    scale=fsum(dist(source.vertex_coordinates(a),source.vertex_coordinates(b)) for a,b in source.edges())/source.number_of_edges()
    a=alias_proposal(mesh,list(source.vertices()),step['corner_parents'],scale)
    b=alias_proposal(mesh,list(source.vertices()),step['corner_parents'],scale)
    assert a==b and mesh.__data__==before and not a['passes_bounded_edge_guard']
    write(out/'source.json',data(source)); write(out/'before_join.json',data(mesh)); write(out/'rejected_vertex_alias_proposal.json',a)
    lineage=step['lineage']
    write(out/'before_join_lineage.json',dict(events=step['events'],history=step['history'],corner_parents=step['corner_parents'],
        vertex_parents={k:[dict(id=p.key,weight=p.weight) for p in rows] for k,rows in lineage.vertex_parents.items()},
        face_parents={k:[dict(id=p.key,weight=p.weight) for p in rows] for k,rows in lineage.face_parents.items()}))
    write(out/'result.json',dict(status='STOPPED_AT_FIXTURE',whole_gate_cases=0,exact_repeat=True,checkpoint_unchanged=True,
        source_immutable=True,before_geometry_sha256=digest(data(mesh)),proposal_applied=False,merge_pairs=len(a['pairs']),
        maximum_proposed_edge_face_incidence=a['proposed_topology']['maximum_edge_face_incidence'],
        conceptual_source='https://archive.bridgesmathart.org/2010/bridges2010-167.pdf',pages='169–170',
        interpretation='A scoped test of near-coincident constructive vertex joining, not a Hansmeyer implementation or a general verdict on nonlinear topology.',
        reason=a['reason']))
    print('Nonlinear fixture stopped:',len(a['pairs']),'join pairs; max edge incidence',a['proposed_topology']['maximum_edge_face_incidence'],'; no gate applied')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--dll',type=Path,required=True); args=p.parse_args(); main(args.dll)
