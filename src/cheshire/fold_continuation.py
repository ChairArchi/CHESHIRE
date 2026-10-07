"""Stateful continuation of existing crease folding, including real CC origins.

The state table interns equal face records without removing ancestry. Origins
describe the previous actual split; they are never inferred from coordinates.
"""
import gzip
import json

from .creases import CreaseNetwork,edge_key
from .crease_folding import folded_crease_once


def cc_origins(before,result,generation):
    origins={v:dict(class_='VERTEX_DERIVED',generation=generation,source=v) for v in before.vertices()}
    for r in origins.values():r['class']=r.pop('class_')
    edges={r['point'] for r in result.metadata['edge_points']}
    for r in result.metadata['edge_points']:
        origins[r['point']]=dict(class_='EDGE_DERIVED',generation=generation,source=r['edge'])
        origins[r['point']]['class']=origins[r['point']].pop('class_')
    originals=set(before.vertices());faces={}
    for r in result.metadata['face_sources']:
        point=set(result.mesh.face_vertices(r['id']))-originals-edges
        if len(point)!=1:raise ValueError('Ambiguous actual CC face origin.')
        v=point.pop();f=r['source_face']
        if v in faces and faces[v]!=f:raise ValueError('Conflicting CC face origins.')
        faces[v]=f
    for v,f in faces.items():
        origins[v]=dict(class_='FACE_DERIVED',generation=generation,source=f,source_vertices=before.face_vertices(f))
        origins[v]['class']=origins[v].pop('class_')
    if set(origins)!=set(result.mesh.vertices()):raise ValueError('Incomplete generated point state.')
    return origins


def fold_state(mesh,state,declaration,*,budget,mode='INTEGER_COMPAS'):
    if set(state['history'])!=set(mesh.faces()) or set(state['source_cells'])!=set(mesh.faces()) or set(state['signatures'])!=set(mesh.faces()):
        raise ValueError('Geometry/state IDs differ; resume from the keyed checkpoint, not an OBJ alone.')
    generation=state['generation']['absolute_cc']
    networks=tuple(CreaseNetwork.from_data(n) for n in state['networks'])
    origins=state.get('origins',{})
    result=folded_crease_once(mesh,networks,declaration,mode=mode,budget=budget,
        current_generation=generation,origin_lineage=origins)
    next_generation=generation+1
    next_origins=cc_origins(mesh,result,next_generation)
    # A CC child has exactly one face parent with positive mass one. This
    # special case has identical history/signature semantics to the existing
    # propagate_history / BranchSignatures.advance, without redundant mixtures.
    history={};cells={};signatures={};cache={}
    for row in result.metadata['face_sources']:
        f,p=row['id'],row['source_face']
        if p not in cache:
            h=state['history'][p]
            cache[p]={**h,'operator_depth':h['operator_depth']+1}
        history[f]=cache[p];cells[f]=state['source_cells'][p];signatures[f]=state['signatures'][p]
    next_state={**state,'history':history,'source_cells':cells,'signatures':signatures,
        'origins':next_origins,'networks':[n.to_data() for n in result.networks],
        'anchors':{v:p for v,p in state['anchors'].items() if result.mesh.has_vertex(v)},
        'generation':{**state['generation'],'absolute_cc':next_generation,
            'continuation_depth':state['generation']['continuation_depth']+1},
        'completed_step':declaration,'next_step':None}
    return result,next_state


def packed(state):
    tables=[];lookup={};object_cache={};ids=[];indices=[]
    for f in sorted(state['history']):
        h=state['history'][f];c=state['source_cells'][f];s=state['signatures'][f]
        key=(id(h),id(c),id(s))
        if key not in object_cache:
            row=dict(history=h,source_cells=c,signatures=[[list(p),w] for p,w in sorted(s.items())])
            signature=json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)
            if signature not in lookup:lookup[signature]=len(tables);tables.append(row)
            object_cache[key]=lookup[signature]
        ids.append(f);indices.append(object_cache[key])
    rest={k:v for k,v in state.items() if k not in ('history','source_cells','signatures')}
    return dict(schema='CHESHIRE_CC_CONTINUATION_V1',state=rest,
        face_ids=ids,face_records=indices,records=tables,
        encoding='Lossless equal face-state interning; complete ancestry/signature/depth retained.')


def unpacked(data):
    if data['schema']!='CHESHIRE_CC_CONTINUATION_V1':raise ValueError('Unknown continuation state.')
    state=dict(data['state']);rows=[]
    for row in data['records']:
        h=row['history'];h={**h,'source':{int(k):w for k,w in h['source'].items()},
            'events':tuple(h['events']),'roles':tuple(tuple(r) for r in h['roles'])}
        rows.append((h,row['source_cells'],{tuple(p):w for p,w in row['signatures']}))
    if len(data['face_ids'])!=len(data['face_records']) or len(set(data['face_ids']))!=len(data['face_ids']):
        raise ValueError('Face-state coverage changed.')
    history={};cells={};signatures={}
    for f,i in zip(data['face_ids'],data['face_records']):
        h,c,s=rows[i];history[f]=h;cells[f]=c;signatures[f]=s
    state.update(history=history,source_cells=cells,signatures=signatures,
        anchors={int(v):p for v,p in state['anchors'].items()},
        origins={int(v):r for v,r in state['origins'].items()})
    return state


def save_state(path,state):
    with gzip.open(path,'wt',encoding='utf-8',compresslevel=1) as f:
        json.dump(packed(state),f,separators=(',',':'),allow_nan=False)


def load_state(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:return unpacked(json.load(f))
