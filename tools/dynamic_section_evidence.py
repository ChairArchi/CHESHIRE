"""Actual geometry comparisons, parameter feedback and full-file resume checks."""
import argparse,sys
from pathlib import Path
from math import acos,degrees
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from dynamic_section_gates import directory
from cross_cell_crease_study import read,write,gz_write,file_hash,raw_mesh
from generational_folding import verify_obj
import progressive_gate_evidence as matched
from cheshire.dynamic_sections import restore,measure,map_rules
from cheshire.fold_continuation import load_state
from cheshire.progressive_gates import symmetry,cycle_key,PLANE_Y


def front_rear_diagnostics(root,revision,generation):
    data=read(directory(root,'G0_PROFILE')/'geometry.json.gz')
    xyz={r['id']:r['xyz'] for r in data['vertices']};faces={r['id']:r['vertices'] for r in data['faces']}
    lookup={tuple(round(x,10) for x in p):v for v,p in xyz.items()}
    vp={v:lookup[tuple(round(x,10) for x in [p[0],2*PLANE_Y-p[1],p[2]])] for v,p in xyz.items()}
    face_lookup={cycle_key(c):f for f,c in faces.items()}
    fp={f:face_lookup[cycle_key([vp[v] for v in reversed(c)])] for f,c in faces.items()};rows=[]
    for g in range(1,generation+1):
        name=f'{revision}_PROFILE_DYNAMIC_G{g}';d=directory(root,name);op=read(d/'operator.json.gz')
        edge={tuple(sorted(r['source'])):r['id'] for r in op['points'] if r['point_class']=='edge'}
        fpoints={r['source']:r['id'] for r in op['points'] if r['point_class']=='face'}
        newvp={v:vp[v] for v in vp}
        newvp.update({point:edge[tuple(sorted(vp[v] for v in e))] for e,point in edge.items()})
        newvp.update({point:fpoints[fp[f]] for f,point in fpoints.items()})
        child={(r['source_face'],r['source_corner']):r['id'] for r in op['face_sources']}
        newfp={f:child[fp[parent],vp[corner]] for (parent,corner),f in child.items()}
        vp,fp=newvp,newfp;data=read(d/'geometry.json.gz')
        xyz={r['id']:r['xyz'] for r in data['vertices']};faces={r['id']:r['vertices'] for r in data['faces']}
        maximum=max(float(np.linalg.norm(np.subtract([p[0],2*PLANE_Y-p[1],p[2]],xyz[vp[v]]))) for v,p in xyz.items())
        failures=sum(cycle_key([vp[v] for v in reversed(c)])!=cycle_key(faces[fp[f]]) for f,c in faces.items())
        rows.append(dict(stage=name,plane_Y=PLANE_Y,max_coordinate_residual=maximum,oriented_face_failures=failures,
            method='Independent constructive reflection from declared G0 registry and actual saved CC corner/edge/face parent relations; no nearest-point pairing.'))
    return rows


def analyze(root,revision,generation,comparison_generation=None):
    cg=generation if comparison_generation is None else comparison_generation
    matched.parent_directory=directory
    pairs=[('R1_CONTROL_CC_G'+str(cg),'R1_PROFILE_CC_G'+str(cg))]
    for g in range(1,cg+1):pairs.append((f'{revision}_PROFILE_STATIC_G{g}',f'{revision}_PROFILE_DYNAMIC_G{g}'))
    pairs.append(('R1_PROFILE_CC_G'+str(cg),f'{revision}_PROFILE_DYNAMIC_G{cg}'))
    comparisons=[matched.geometry_comparison(root,*pair) for pair in pairs]
    table=[];feedback=[];rule_symmetry=[]
    coarse=restore(load_state(directory(root,'G0_PROFILE')/'state.json.gz'))['gate']['face_pair']
    for g in range(1,generation+1):
        name=f'{revision}_PROFILE_DYNAMIC_G{g}';d=directory(root,name);summary=read(d/'summary.json');request=read(d/'request.json')
        descriptor=read(d/'descriptors.json.gz');rules=read(d/'rules.json.gz')['faces'];parent=Path(request['parent']['path'])
        if file_hash(parent/'geometry.json.gz')!=request['parent']['geometry_sha256']:raise ValueError('Measured parent geometry identity changed.')
        if file_hash(parent/'state.json.gz')!=request['parent']['state_sha256']:raise ValueError('Measured parent state identity changed.')
        if descriptor['generation']!=g-1:raise ValueError('Descriptor generation mismatch.')
        old_observation=read(parent/('descriptors.json.gz' if g==1 else 'observations.json.gz'))
        if descriptor['sections']!=old_observation['sections']:raise ValueError('Fresh reread disagrees with actual saved preceding geometry observation.')
        parent_state=restore(load_state(parent/'state.json.gz'));pair=parent_state['gate']['face_pair']
        deltas={key:max(abs(r[key]-rules[str(pair[int(f)])][key]) for f,r in rules.items()) for key in next(iter(rules.values()))}
        if max(deltas.values())>1e-8:raise ValueError('Current local rules fail mirrored numeric correspondence.')
        swaps={'COLUMN_L':'COLUMN_R','COLUMN_R':'COLUMN_L','BASE_L':'BASE_R','BASE_R':'BASE_L','LINTEL':'LINTEL'}
        for f,drow in descriptor['faces'].items():
            other=descriptor['faces'][str(pair[int(f)])]
            if swaps[drow['part']]!=other['part'] or drow['generation']!=other['generation']:
                raise ValueError('Semantic/generation reflection mismatch.')
            if {coarse[int(k)] for k in drow['coarse']}!=set(map(int,other['coarse'])):
                raise ValueError('Coarse ancestry reflection mismatch.')
            if parent_state['section']['bands'][int(f)]!=parent_state['section']['bands'][pair[int(f)]] and drow['part']!='LINTEL':
                raise ValueError('Column section band reflection mismatch.')
        rule_symmetry.append(dict(stage=name,input_generation=g-1,max_abs_parameter_residual=deltas,
            semantic_parts_coarse_ancestry_generation_and_column_bands='PASS',selection=parent_state['gate']['selection_policy']))
        del parent_state,pair
        neck=descriptor['sections']['COLUMN_L'][5];body=descriptor['sections']['COLUMN_L'][2]
        table.append(dict(name=name,input_generation=g-1,output_generation=g,
            input_body_width=body['width'],input_neck_width=neck['width'],input_neck_depth=neck['depth'],
            vertices=summary['statistics']['vertex_count'],faces=summary['statistics']['face_count'],
            parameters=summary['rule_statistics'],process=read(root/'logs'/name/'process.json'),times=summary['times'],
            OBJ_bytes=(d/(name+'.obj')).stat().st_size))
        if g>1:
            old_rules=read(parent/'rules.json.gz')['faces'];op=read(parent/'operator.json.gz')
            ancestry={str(r['id']):str(r['source_face']) for r in op['face_sources']}
            changes={}
            for key in ('wf','w1','w2','w3','w4'):
                delta=np.asarray([abs(r[key]-old_rules[ancestry[f]][key]) for f,r in rules.items()])
                changes[key]=dict(changed_faces=int((delta>1e-10).sum()),max_abs=float(delta.max()),median_abs=float(np.median(delta)))
            feedback.append(dict(stage=name,parent_geometry_sha256=request['parent']['geometry_sha256'],
                actual_descriptors_sha256=file_hash(d/'descriptors.json.gz'),input_generation=descriptor['generation'],
                actual_sections_equal_saved_parent_observation=True,rule_changes_vs_inherited_previous_input=changes,
                statement='w3/w4/w1/w2 changes also prove geometry feedback beyond shrinking h-based offsets; no generation strength schedule.'))
    lead=f'{revision}_PROFILE_DYNAMIC_G{generation}';d=directory(root,lead)
    mesh=raw_mesh(read(d/'geometry.json.gz'));state=restore(load_state(d/'state.json.gz'))
    for field in ('history','source_cells','signatures'):
        if set(state[field])!=set(mesh.faces()):raise ValueError('Incomplete saved face state.')
    for field in ('origins',):
        if set(state[field])!=set(mesh.vertices()):raise ValueError('Incomplete saved point state.')
    if set(state['gate']['material'])!=set(mesh.vertices()):raise ValueError('Incomplete saved material coordinates.')
    if set(state['section']['bands'])!=set(mesh.faces()):raise ValueError('Incomplete section ancestry.')
    remeasured=measure(mesh,state);observation=read(d/'observations.json.gz')
    if remeasured['sections']!=observation['sections']:raise ValueError('Actual full checkpoint remeasurement differs.')
    config=read(root/'configuration.json')['configs'][revision]
    next_rules=map_rules(remeasured,config);next_summary={}
    for key in ('wf','w1','w2','w3','w4'):
        values=[r[key] for r in next_rules.values()];next_summary[key]=dict(min=min(values),max=max(values),median=float(np.median(values)))
    normals={f:mesh.face_normal(f) for f in mesh.faces()};dihedral={}
    for part in sorted(set(state['gate']['parts'].values())):
        angles=[]
        for e in mesh.edges():
            a,b=mesh.edge_faces(e)
            if a is not None and b is not None and state['gate']['parts'][a]==part and state['gate']['parts'][b]==part:
                dot=sum(x*y for x,y in zip(normals[a],normals[b]));angles.append(degrees(acos(max(-1.,min(1.,dot)))))
        if angles:dihedral[part]=dict(median=float(np.median(angles)),p90=float(np.quantile(angles,.9)),max=max(angles))
    report=dict(status='PASS',lead=lead,actual_full_checkpoint_reload=True,OBJ=verify_obj(mesh,d/(lead+'.obj')),
        geometry_sha256=file_hash(d/'geometry.json.gz'),state_sha256=file_hash(d/'state.json.gz'),
        symmetry=symmetry(mesh,state),sections_equal_actual_saved_observation=True,next_rule_statistics=next_summary,
        continued_geometry_not_allocated='Actual next rule mapping reconstructed; exact small save/reload next-generation equality is separately tested.',
        next_action=state['section']['next'],completed=state['section']['completed'],dihedral_degrees=dihedral,
        dihedral_caution='Actual geometry orientation diagnostic; normal variation or count growth alone does not prove hierarchy.')
    del mesh,state,observation,remeasured,next_rules,normals
    front_rear=front_rear_diagnostics(root,revision,generation)
    tolerance=1e-8
    for row in table:
        stage_diag=read(directory(root,row['name'])/'summary.json')['symmetry']
        if stage_diag['max_coordinate_residual']>tolerance or stage_diag['oriented_face_failures']:
            raise ValueError('Primary lineage fails numeric left/right symmetry: '+row['name'])
    for a,b in pairs:
        for name in (a,b):
            diag=read(directory(root,name)/'summary.json')['symmetry']
            if diag['max_coordinate_residual']>tolerance or diag['oriented_face_failures']:
                raise ValueError('Comparison stage fails numeric left/right symmetry: '+name)
    if report['symmetry']['max_coordinate_residual']>tolerance or report['symmetry']['oriented_face_failures']:
        raise ValueError('Lead fails numeric left/right symmetry.')
    if any(r['max_coordinate_residual']>tolerance or r['oriented_face_failures'] for r in front_rear):
        raise ValueError('Claimed front/rear symmetry fails numeric verification.')
    report['symmetry_tolerance']=tolerance
    write(root/'analysis'/(revision+'_G'+str(generation)+'_evidence.json'),dict(comparison_generation=cg,lead_generation=generation,
        comparisons=comparisons,parameter_table=table,feedback=feedback,lead_checkpoint=report,front_rear=front_rear,rule_symmetry=rule_symmetry))
    print('Actual comparisons, feedback and full checkpoint/OBJ reread PASS',lead,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--revision',default='R2');p.add_argument('--generation',type=int,default=4)
    p.add_argument('--comparison-generation',type=int)
    a=p.parse_args();analyze(a.output_root,a.revision,a.generation,a.comparison_generation)
