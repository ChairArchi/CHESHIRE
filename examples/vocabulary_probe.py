"""Task-21 live reflection and bounded raw fixtures, never third-party source."""
import argparse
import json
from pathlib import Path

from cheshire.mola import _load_backend
from cheshire.ornament import local_polygon
from compas.datastructures import Mesh
from math import dist,isfinite
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]

def reference_path(label):
    """Prefer this study's exact saved references, including review archives."""
    saved=ROOT/'output/task21/study/references'/(label+'.json')
    if saved.is_file(): return saved
    fallback={'C07':'references/C07.json','HERO':'B/HERO_ROLE_ASSEMBLY/attempt_001/terminal.json'}
    return ROOT/'output/task20/study'/fallback[label]

def reflection(dll):
    _,metadata=_load_backend(str(dll))
    import clr
    assembly=clr.AddReference(str(dll))
    methods=[m for m in assembly.GetType('FaceSubdivision',True).GetMethods() if m.IsPublic and m.IsStatic]
    metadata['face_subdivision_api']=[dict(name=str(m.Name),signature=str(m),return_type=str(m.ReturnType.FullName),
        parameters=[dict(name=str(p.Name),type=str(p.ParameterType.FullName),default=str(p.DefaultValue) if p.HasDefaultValue else None) for p in m.GetParameters()]) for m in methods]
    return assembly,methods,metadata

def probes(dll):
    assembly,methods,metadata=reflection(dll)
    from System import Array,Object,Single,Int32,Boolean
    vec=assembly.GetType('Mola.Vec3',True)
    ctor=next(c for c in vec.GetConstructors() if [str(p.ParameterType.FullName) for p in c.GetParameters()]==['System.Single']*3)
    def vector(p): return ctor.Invoke(Array[Object]([Single(x) for x in p]))
    def call(name,xyz,parameters):
        vectors=Array.CreateInstance(vec,len(xyz))
        for i,p in enumerate(xyz): vectors.SetValue(vector(p),i)
        if name=='Extrude': types=['Mola.Vec3[]','Mola.Vec3','System.Single','System.Boolean']; values=[vectors,vector(parameters[0]),Single(parameters[1]),Boolean(True)]
        elif name in ('LinearSplitQuad','LinearSplitQuadBorder'):
            methods_for=[m for m in methods if m.Name==name and len(m.GetParameters())==len(parameters)+1]
            method=methods_for[0]; values=[vectors,*[Int32(v) if str(p.ParameterType.FullName)=='System.Int32' else Single(v) for p,v in zip(list(method.GetParameters())[1:],parameters)]]
            types=None
        elif name=='ExtrudeToPoint': types=['Mola.Vec3[]','Mola.Vec3']; values=[vectors,vector(parameters[0])]
        else: types=['Mola.Vec3[]']+['System.Single']*len(parameters); values=[vectors,*map(Single,parameters)]
        if types: method=next(m for m in methods if str(m.Name)==name and [str(p.ParameterType.FullName) for p in m.GetParameters()]==types)
        raw=method.Invoke(None,Array[Object](values))
        return [[[float(vec.GetField(a).GetValue(p)) for a in ('x','y','z')] for p in face] for face in raw]
    fixtures={'unit_quad':[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],'elongated_quad':[[0,0,0],[3,0,0],[3,.6,0],[0,.6,0]],
        'warped_quad':[[0,0,0],[1,0,.12],[1,1,0],[0,1,-.08]],'triangle':[[0,0,0],[1,0,0],[0,1,0]]}
    for label in ('C07','HERO'):
        path=reference_path(label)
        geometry=json.loads(path.read_text(encoding='utf-8')); mesh=Mesh()
        for v in geometry['vertices']: mesh.add_vertex(key=v['id'],x=v['xyz'][0],y=v['xyz'][1],z=v['xyz'][2])
        for f in geometry['faces']: mesh.add_face(f['vertices'],fkey=f['id'])
        eligible=[]
        for f in mesh.faces():
            try: data=local_polygon(mesh,f)
            except ValueError: continue
            if len(data[0])==4: eligible.append((mesh.face_area(f),f,data))
        eligible.sort(reverse=True)
        for i in (0,len(eligible)//2,-1):
            _,f,data=eligible[i]; fixtures[f'{label}_area_rank_{i}_face_{f}']=data[3]
    choices=[('Extrude',[[0,0,1],.18]),('Extrude',[[.8,0,.6],.24]),('Extrude',[[0,.8,.6],.24]),('Extrude',[[1,0,0],.2]),
        ('LinearSplitQuad',[.3,0]),('LinearSplitQuad',[.3,1]),('LinearSplitQuad',[.22,.22,0]),('LinearSplitQuad',[.15,.35,0]),
        ('LinearSplitQuadBorder',[.18,.18,0]),('LinearSplitQuadBorder',[.18,.18,1]),('Roof',[.2,.2]),('Roof',[.2,0]),('Roof',[.12,.35])]
    result=[]
    for label,xyz in fixtures.items():
        for name,parameters in choices:
            row=dict(fixture=label,operator=name,parameters=parameters,input=xyz)
            try:
                raw=call(name,xyz,parameters); row['output']=raw
                repeats=[call(name,xyz,parameters) for _ in range(4)]
                row['repeat_count']=len(repeats)
                row['repeat_identical']=all(r==raw for r in repeats)
                if not row['repeat_identical']: row['first_different_repeat']=next(r for r in repeats if r!=raw)
                row['finite']=all(isfinite(x) for face in raw for p in face for x in p)
                row['face_sizes']=list(map(len,raw))
                def key(p): return tuple(round(x,6) for x in p)
                directed=Counter((key(a),key(b)) for face in raw for a,b in zip(face,face[1:]+face[:1]))
                boundary=[(a,b) for (a,b),count in directed.items() if directed[(b,a)]==0]
                expected={(key(a),key(b)) for a,b in zip(xyz,xyz[1:]+xyz[:1])}
                row['exact_unsplit_boundary']=set(boundary)==expected
                # Float32 can straddle a decimal rounding bucket. Check the
                # constructor boundary with the same explicit local tolerance,
                # then retain original XYZ; this is not welding geometry.
                new_nodes={}
                def node(p):
                    existing=[i for i,q in enumerate(xyz) if dist(p,q)<3e-6]
                    if existing: return existing[0]
                    value=tuple(p)
                    if value not in new_nodes: new_nodes[value]=len(xyz)+len(new_nodes)
                    return new_nodes[value]
                cycles=[[node(p) for p in face] for face in raw]
                edges=Counter((a,b) for face in cycles for a,b in zip(face,face[1:]+face[:1]))
                open_edges={(a,b) for a,b in edges if not edges[b,a]}
                row['boundary_contract_with_float32_tolerance']=open_edges=={(i,(i+1)%len(xyz)) for i in range(len(xyz))}
                if name=='Roof' and len(xyz)==4:
                    from cheshire.mola import _cross,_subtract,_dot
                    from math import hypot
                    normal=_cross(_subtract(xyz[1],xyz[0]),_subtract(xyz[2],xyz[0])); normal=[v/hypot(*normal) for v in normal]
                    m0=[(xyz[0][a]+xyz[1][a])/2 for a in range(3)]; m1=[(xyz[2][a]+xyz[3][a])/2 for a in range(3)]
                    h,g=parameters
                    expected_ridges=[[(1-g)*m0[a]+g*m1[a]+h*normal[a] for a in range(3)],[g*m0[a]+(1-g)*m1[a]+h*normal[a] for a in range(3)]]
                    row['ridge_oracle_matches']=all(dist(p,q)<3e-6 for p,q in zip((raw[0][-1],raw[2][-1]),expected_ridges))
                row['boundary_edges']=len(boundary); row['repeated_directed_edges']=sum(n>1 for n in directed.values())
                row['original_corner_occurrences']=[sum(dist(p,q)<3e-6 for face in raw for p in face) for q in xyz]
            except Exception as error: row['error']=str(error)
            result.append(row)
    metadata['probes']=result
    path=ROOT/'output/task21/operator_probes.json'
    initial=path.with_name('operator_probes_initial.json')
    if path.exists() and not initial.exists(): initial.write_bytes(path.read_bytes())
    path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    for row in result:
        if row['fixture']=='unit_quad' or row.get('error'): print(row['fixture'],row['operator'],row['parameters'],{k:row.get(k) for k in ('repeat_identical','face_sizes','exact_unsplit_boundary','error')})
    print('raw unit Roof',next(r['output'] for r in result if r['fixture']=='unit_quad' and r['operator']=='Roof'))
    print('raw unit Extrude',next(r['output'] for r in result if r['fixture']=='unit_quad' and r['operator']=='Extrude'))
    print('probes',len(result))

def wrapper_probes(dll):
    from cheshire.vocabulary import VocabularyStage,vocabulary_event
    from cheshire.ornament import source_history
    from cheshire.execution import ExecutionBudget
    from cheshire.validation import validate_lineage_coverage,inspect_mesh
    records=[]
    for label in ('C07','HERO'):
        path=reference_path(label)
        d=json.loads(path.read_text(encoding='utf-8')); mesh=Mesh()
        for v in d['vertices']: mesh.add_vertex(key=v['id'],x=v['xyz'][0],y=v['xyz'][1],z=v['xyz'][2])
        for f in d['faces']: mesh.add_face(f['vertices'],fkey=f['id'])
        eligible=[]
        for f in mesh.faces():
            try: data=local_polygon(mesh,f)
            except ValueError: continue
            if len(data[0])==4: eligible.append((mesh.face_area(f),f))
        eligible.sort(reverse=True)
        for rank in (0,len(eligible)//2,-1):
            _,f=eligible[rank]
            for op,p in [('DirectionalExtrusion',dict(height_ratio=.2,direction_mode='horizontal',normal_ratio=.45)),('Roof',dict(height_ratio=.2,gable_inset=.2,direction_mode='vertical'))]:
                stage=VocabularyStage('probe',op,p,{})
                row=dict(source=label,area_rank=rank,parent_face=f,operator=op,parameters=p)
                try:
                    from copy import deepcopy
                    input_snapshot=deepcopy(mesh.__data__)
                    a=vocabulary_event(mesh,source_history(mesh),stage,selected_faces=[f],dll_path=str(dll),budget=ExecutionBudget(150000,300000))
                    b=vocabulary_event(mesh,source_history(mesh),stage,selected_faces=[f],dll_path=str(dll),budget=ExecutionBudget(150000,300000))
                    row.update(success=True,repeat_identical=a['mesh'].__data__==b['mesh'].__data__,inspection=inspect_mesh(a['mesh']),
                        lineage_problems=validate_lineage_coverage(mesh,a['mesh'],a['lineage']),event=a['events'][0],input_immutable=mesh.__data__==input_snapshot)
                except Exception as error: row.update(success=False,error=str(error))
                records.append(row); print(label,rank,f,op,row.get('success'),row.get('error'))
    path=ROOT/'output/task21/operator_acceptance.json'
    path.write_text(json.dumps(dict(wrapper_probes=records,accepted=['DirectionalExtrusion','Roof'] if all(r['success'] and r['repeat_identical'] and not r['lineage_problems'] for r in records) else [],
        rejected={'LinearSplitQuad':'Boundary segmentation breaks an unchanged neighbor on a closed gate; variable min/max call is nondeterministic.',
        'LinearSplitQuadBorder':'Boundary segmentation needs neighbor stitching/refinement, outside the face-local contract.'},
        not_selected={'ExtrudeToPoint':'Present in reflection; not probed or integrated after accepting two complementary types.',
        'Grid/GridAbs':'Present in reflection; lower priority because of regular tiling risk; not probed.'}),indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--dll',type=Path,required=True)
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--wrappers',action='store_true')
    args=parser.parse_args()
    if args.wrappers: wrapper_probes(args.dll.resolve()); raise SystemExit(0)
    if args.probe: probes(args.dll.resolve()); raise SystemExit(0)
    assembly,methods,metadata=reflection(args.dll.resolve())
    path=ROOT/'output/task21/operator_reflection.json'; path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    for m in metadata['face_subdivision_api']: print(m['signature'],[(p['name'],p['type']) for p in m['parameters']])
