"""Strict pre-study gate and frozen inputs. Heavy files require --output-root."""
import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
for folder in ('rhino','examples','tools'): sys.path.insert(0,str(ROOT/folder))
from compas.datastructures import Mesh
from compas.geometry import Box
from cheshire.artifact_root import ArtifactRoot
from cheshire.generational_subdivision import generational_subdivide_once
from cheshire.sharp_subdivision import sharp_subdivide_once,topology_motifs,equation7,equation10,equation11
from cheshire_worker import mesh_from_data,mesh_to_data
from ornament_study import digest,file_hash,gz_write

BASELINE='0090fc816c8d7a1bcb755114a859c295047c7b0b'

def read(path):
    with gzip.open(path,'rt',encoding='utf-8') if str(path).endswith('.gz') else Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)

def write(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)

def verify(root):
    root=ArtifactRoot(root); target=root.resolve('inputs'); target.mkdir(parents=True,exist_ok=True)
    report=dict(baseline=BASELINE,regressions=[],reference_inputs={},ordering_differences=[],motifs={})
    for name,mesh in [('cube',Mesh.from_shape(Box(2,2,2))),('column',Mesh.from_shape(Box(1,1,6))),
                      ('C0',mesh_from_data(read(ROOT/'studies/task19/C0.json')))]:
        write(target/(name+'.json'),mesh_to_data(mesh))
        report['motifs'][name]=dict(__import__('collections').Counter(s.key() for s in topology_motifs(mesh).values()))
        original=deepcopy(mesh.__data__); weights=dict(wf=.03,w1=-.6,we=-.01,w2=-.4,wp=.02,w3=-.7,w4=.4)
        old=generational_subdivide_once(mesh,weights)
        new=sharp_subdivide_once(mesh,{**weights,'w6':0,'w7':0},u_map={'(3,3)':1},lock_groups={'OFF':dict(vertices=[next(mesh.vertices())],iterations=0)})
        assert old.mesh.__data__==new.mesh.__data__ and old.sampling_parents==new.sampling_parents
        assert old.origin_lineage==new.origin_lineage and mesh.__data__==original
        report['regressions'].append(dict(fixture=name,exact_mesh_data=True,exact_positive_sampling=True,source_immutable=True,geometry_sha256=digest(mesh_to_data(new.mesh))))
    frozen=read(ROOT/'studies/task20/backbone.json'); write(target/'backbone.json',frozen)
    prior=ROOT/'output/task21/study'
    for i in range(1,6):
        name=f'BACKBONE_S{i:02d}.json.gz'; actual=read(prior/'references'/name)
        assert digest(actual)==frozen['geometry_sha256'][str(i)]
        for suffix in ('.json.gz','_lineage.json.gz','_signatures.json.gz'):
            source=prior/'references'/f'BACKBONE_S{i:02d}{suffix}'; dest=target/source.name
            if not dest.exists(): shutil.copyfile(source,dest)
            assert file_hash(dest)==file_hash(source)
            report['reference_inputs'][root.reference(dest)]=file_hash(dest)
    # Replay the actual first weighted C11 stage using the saved source and parameters.
    mesh=mesh_from_data(read(target/'C0.json')); row=frozen['recipe']['stages'][0]['parameters']['ratios']
    from math import dist,fsum
    scale=fsum(dist(mesh.vertex_coordinates(a),mesh.vertex_coordinates(b)) for a,b in mesh.edges())/mesh.number_of_edges()
    weights={k:v*scale if k in ('wf','we','wp') else v for k,v in row.items()}
    old=generational_subdivide_once(mesh,weights); new=sharp_subdivide_once(mesh,{**weights,'w6':0,'w7':0})
    assert old.mesh.__data__==new.mesh.__data__
    assert digest(mesh_to_data(new.mesh))==frozen['geometry_sha256']['1']
    report['regressions'].append(dict(fixture='Saved Task21 C11 weighted stage 1',exact_mesh_data=True,
        exact_saved_ordered_polygon_json=True,geometry_sha256=digest(mesh_to_data(new.mesh))))
    # Recover the real last CC point origins from its actual input; do not infer them from XYZ.
    cc3=generational_subdivide_once(mesh_from_data(read(target/'BACKBONE_S03.json.gz')),current_generation=2)
    assert digest(mesh_to_data(cc3.mesh))==frozen['geometry_sha256']['4']
    gz_write(target/'CC3_origins.json.gz',cc3.origin_lineage)
    current=mesh_from_data(read(target/'BACKBONE_S05.json.gz'))
    weights=dict(w1=-.4,w2=-.8,w3=-.6,w4=.3)
    old=generational_subdivide_once(current,weights,origin_lineage=cc3.origin_lineage,current_generation=3)
    new=sharp_subdivide_once(current,weights,origin_lineage=cc3.origin_lineage,current_generation=3)
    assert old.mesh.__data__==new.mesh.__data__ and old.origin_lineage==new.origin_lineage
    report['regressions'].append(dict(fixture='C07 continuation with restored verified CC3 origins',exact_mesh_data=True,
        eligible_eq4_faces=old.metadata['later_generation_face_stencil']['eligible_faces'],geometry_sha256=digest(mesh_to_data(new.mesh))))
    report['restored_point_origins']=dict(method='Replayed unchanged standard CC on exact saved S03; S04 ordered polygon hash exactly matched. Post-CC Mola-created vertices have no invented CC point class.',
        generations=3,artifact=root.reference(target/'CC3_origins.json.gz'),sha256=file_hash(target/'CC3_origins.json.gz'))
    ordered=prior/'HERO/HERO_ORDERED_RIDGES/attempt_001'
    for i in range(6,13):
        source=ordered/f'S{i:02d}_lineage.json.gz'; dest=target/f'ORDERED_S{i:02d}_lineage.json.gz'
        if not dest.exists(): shutil.copyfile(source,dest)
        assert file_hash(dest)==file_hash(source)
        report['reference_inputs'][root.reference(dest)]=file_hash(dest)
    for source,rename in [(ordered/'S10.json.gz','ORDERED_CORE.json.gz'),(ordered/'S10_lineage.json.gz','ORDERED_CORE_lineage.json.gz'),
                           (ordered/'S10_signatures.json.gz','ORDERED_CORE_signatures.json.gz'),
                           (ordered/'terminal.json','TASK21_ORDERED.json'),(ordered/'terminal_lineage.json.gz','TASK21_ORDERED_lineage.json.gz')]:
        dest=target/rename
        if not dest.exists(): shutil.copyfile(source,dest)
        assert file_hash(source)==file_hash(dest)
        report['reference_inputs'][root.reference(dest)]=file_hash(dest)
    hero=next(r for r in read(ROOT/'studies/task21/recipes.json')['recipes'] if r['id']=='HERO_ORDERED_RIDGES')
    write(target/'ORDERED_recipe.json',hero)
    # Decode only the existing verified constructive corner contract, then
    # independently compare the recovered clouds with Task21's actual monitor.
    from cheshire.vocabulary import VocabularyRecipe
    from cheshire.gate_integrity import GateIntegrityMonitor
    stages=VocabularyRecipe.from_data(hero).compile().stages
    anchors={v:v for v in mesh_from_data(read(target/'C0.json')).vertices()}
    checks=[]; prior_summary=read(ordered/'summary.json')
    monitor=GateIntegrityMonitor(mesh_from_data(read(target/'C0.json')))
    for i,stage in enumerate(stages,1):
        lineage=read(target/(f'BACKBONE_S{i:02d}_lineage.json.gz' if i<=5 else f'ORDERED_S{i:02d}_lineage.json.gz'))
        next_anchors={}
        for child,refs in lineage['vertex_parents'].items():
            if len(refs)==1 and refs[0]['weight']==1.:
                next_anchors[int(child)]=anchors.get(refs[0]['id'])
            elif stage.operator=='TaperedExtrusion':
                fraction=stage.parameters['fraction']; n=len(refs)
                candidates=[p for p in refs if abs(p['weight']-(1-fraction+fraction/n))<1e-12]
                assert len(candidates)==1 and all(abs(p['weight']-fraction/n)<1e-12 for p in refs if p is not candidates[0])
                next_anchors[int(child)]=anchors.get(candidates[0]['id'])
            else:
                # CC edge/face points and Roof ridge points are not old corner anchors.
                next_anchors[int(child)]=None
        anchors=next_anchors
        if i in (5,10,12):
            label={5:'C07',10:'ORDERED_CORE',12:'TASK21_ORDERED'}[i]
            geometry=read(target/({5:'BACKBONE_S05.json.gz',10:'ORDERED_CORE.json.gz',12:'TASK21_ORDERED.json'}[i]))
            observed=monitor.evaluate(mesh_from_data(geometry),anchors,generation=i)
            expected=next(s['monitor'] for s in prior_summary['stages'] if s['stage_index']==i)
            assert observed==expected, 'Recovered old corner cloud differs from actual Task21 monitor.'
            write(target/(label+'_anchors.json'),anchors)
            checks.append(dict(input=label,tracked_vertices=observed['tracked_vertex_count'],exact_old_monitor=True))
    report['restored_corner_anchors']=checks
    for name in ('C0','BACKBONE_S05','ORDERED_CORE','TASK21_ORDERED'):
        path=target/(name+'.json' if name in ('C0','TASK21_ORDERED') else name+'.json.gz')
        mesh=mesh_from_data(read(path))
        report['motifs'][name]=dict(__import__('collections').Counter(s.key() for s in topology_motifs(mesh).values()))
    report['equation7_oracles']=[dict(a=a,b=b,q=q,values=[equation7(i,a,b,q) for i in (1,2,3)]) for a,b,q in [(.3,.2,1),(.1,-.05,2),(-1,.125,3)]]
    corners=[[0,0,0],[4,0,0],[4,2,0],[0,2,0]]
    report['equation10_oracles']=dict(base=[2,1,1],input=corners,weight=.25,positive=equation10([2,1,1],corners,[1,0,0,0],.25),negative=equation10([2,1,1],corners,[-1,0,0,0],.25),two_positive=equation10([2,1,1],corners,[1,1,0,0],.25))
    report['equation11_oracle']=dict(base=[1,.5,.25],endpoints=[[0,0,0],[2,0,0]],u=[.5,-1],weight=.4,result=equation11([1,.5,.25],[0,0,0],[2,0,0],.5,-1,.4))
    report['status']='PASS'; write(root.resolve('study/verification.json'),report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output-root',required=True,type=Path)
    verify(parser.parse_args().output_root)
