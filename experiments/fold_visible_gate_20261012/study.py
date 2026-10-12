"""Visible wall redevelopment versus depth alone, on two saved column inputs.

The default cases are the two saved actual column inputs. GATE_COLUMN and
GATE_LINTEL are the earlier primitive-input diagnostic only, retained for replay;
they are not the accepted fixed-column gate. Use symmetric_lintel.py for that
gate: two unchanged current columns and one newly symmetric lintel.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
spec=importlib.util.spec_from_file_location('visible_previous_region_study',
    HERE.parent/'fold_region_growth_20261012/study.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
sys.path.insert(0,str(HERE))
from region_fold import NativeChartSampler,measure_longitudinal,proposal
import wall_fold

RECIPE=dict(name='measured_three_rail_wall_v1',angle_degrees=40.,
    shoulder_fraction=.55,axial_plateau_fraction=.60,
    input_generation=2,output_generation=3,
    note='Same coefficients across inputs. WALL deliberately rebuilds the interior surface; DEPTH only displaces along the same pooled normal. No field pass or fabrication audit.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_sampler(mesh,chart):
    t=previous.anchor.t
    native=t.growth.native(mesh)
    pchart=np.concatenate([chart,t.face_values(mesh,chart)])
    return NativeChartSampler(native.xyz,native.faces[:,:3],pchart)


def save(folder,mesh,chart,tags,metadata,arrays,guides=(),rails=()):
    if folder.exists():
        raise FileExistsError('Existing result preserved: '+str(folder))
    t=previous.anchor.t
    native=t.growth.native(mesh);faces=native.faces[:,:3]
    actual=trimesh.Trimesh(native.xyz,faces,process=False)
    pchart=np.concatenate([chart,t.face_values(mesh,chart)])
    _,errors,matches=t.prior.reflection_state(native.xyz,faces,pchart)
    checks=dict(finite=bool(np.isfinite(native.xyz).all()),watertight=bool(actual.is_watertight),
        winding_consistent=bool(actual.is_winding_consistent),components=int(actual.body_count),
        minimum_triangle_area=float(actual.area_faces.min()),reflection_error=errors,
        reflected_triangle_sets_identical=matches)
    passed=checks['finite'] and checks['watertight'] and checks['winding_consistent']
    passed &= checks['components']==1 and checks['minimum_triangle_area']>1e-12 and max(errors)<1e-9 and all(matches)
    metadata=dict(metadata,**checks,quick_integrity='PASS' if passed else 'FAILED_PRESERVED',
        control_vertices=len(mesh.xyz),physical_vertices=len(native.xyz),physical_triangles=len(faces),
        source_revision='055c42f',self_intersection='NOT_CHECKED',fabrication='NOT_CHECKED')
    folder.mkdir(parents=True)
    np.savez_compressed(folder/'control_quad.npz',xyz=mesh.xyz,faces=mesh.faces,chart=chart,
        classes=mesh.classes,rest=mesh.rest,anchors=mesh.anchors,generation=np.array(mesh.generation),
        surface=np.array(mesh.surface),memory=tags)
    np.savez_compressed(folder/'geometry.npz',xyz=native.xyz,faces=faces)
    np.savez_compressed(folder/'operation_fields.npz',**arrays)
    for prefix,records in (('guide',guides),('rails',rails)):
        for i,record in enumerate(records):
            np.savez_compressed(folder/f'{prefix}_{i}.npz',**record)
    (folder/'generation.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
    for path in (Path(__file__),HERE/'wall_fold.py'):
        shutil.copy2(path,folder/path.name)
    actual.export(folder/'member.ply')
    print(metadata['input_case'],metadata['candidate'],metadata['quick_integrity'],
        len(faces),'max',metadata.get('maximum_displacement',0),flush=True)
    if not passed:
        raise ValueError('Quick integrity failure preserved; no repair.')
    return metadata


def prepared_input(case):
    if case in previous.SOURCES:
        source=previous.SOURCES[case]
        mesh,chart,tags=previous.anchor.t.load(source)
        metadata=json.loads((source/'generation.json').read_text(encoding='utf8'))
        parents=metadata.get('event_bank',metadata.get('authored_return_events'))
        return mesh,chart,tags,dict(source=str(source),source_control_sha256=digest(source/'control_quad.npz'),
            field_passes_inherited=metadata['field_passes_total'],parent_region_seeds=parents)
    import gate_members
    mesh,chart,tags,metadata=gate_members.build_source(case.removeprefix('GATE_'))
    return mesh,chart,tags,metadata


def run(root,case,mode):
    mesh,chart,tags,source=prepared_input(case)
    parents=source['parent_region_seeds']
    if mesh.generation!=2 or len(parents)!=2:
        raise ValueError('Two declared G2 parent seeds required.')
    sampler=native_sampler(mesh,chart)
    guides=[measure_longitudinal(sampler,parent,shoulder_fraction=.55,frame_mode='region') for parent in parents]
    rails=[wall_fold.measure_rails(sampler,guide,angle_degrees=40.) for guide in guides]
    out,outchart,outtags,operator=previous.anchor.t.memory.refine(mesh,chart,tags)
    reference=out.xyz.copy()
    if mode=='CONTROL':
        delta=np.zeros_like(reference);fields={}
    elif mode=='PREVIOUS':
        delta,weights=proposal(reference,outchart,guides,mode='GROOVE',depth_ratio=.28)
        fields=dict(region_weights=weights)
    else:
        delta,fields=wall_fold.apply_wall(reference,outchart,rails,mode=mode)
    existing=previous.anchor.t.prior.helpers.existing
    existing.reflect(delta,outchart,existing.symmetry(outchart))
    if case=='GATE_LINTEL':
        import gate_members
        gate_members.reflect_axial_delta(delta,outchart)
    out.xyz=reference+delta
    recipe=dict(RECIPE,candidate=mode)
    return save(root/mode/case/'G03',out,outchart,outtags,
        dict(input_case=case,candidate=mode,recipe=recipe,input=source,
            parent_region_seeds=parents,added_field_passes=0,
            maximum_displacement=float(np.linalg.norm(delta,axis=1).max()),
            moved_controls=int((np.linalg.norm(delta,axis=1)>1e-12).sum()),
            axial_role_constraint='Constructive first-half material reflection for lintel' if case=='GATE_LINTEL' else None,
            geometry_operation='Interior ruled-wall redevelopment' if mode=='WALL' else mode),
        dict(reference_xyz=reference,delta=delta,chart=outchart,
            input_edges=operator['input_edges'],parent_face=operator['parent_face'],**fields),guides,rails)


def assemble(root,mode,stage='G03'):
    import gate_members
    folder=root/'assemblies'/mode
    if folder.exists():
        raise FileExistsError(str(folder))
    parts={}
    sources={}
    for kind in ('COLUMN','LINTEL'):
        source=root/mode/('GATE_'+kind)/stage
        with np.load(source/'geometry.npz') as data:
            parts[kind]=(data['xyz'],data['faces'])
        sources[kind]=dict(path=str(source),sha256=digest(source/'geometry.npz'))
    assembly=gate_members.assemble(parts)
    actual=trimesh.Trimesh(assembly['xyz'],assembly['faces'],process=False)
    checks=dict(components=int(actual.body_count),watertight=bool(actual.is_watertight),
        winding_consistent=bool(actual.is_winding_consistent),finite=bool(np.isfinite(assembly['xyz']).all()),
        minimum_triangle_area=float(actual.area_faces.min()))
    assert checks['components']==3 and checks['watertight'] and checks['winding_consistent'] and checks['minimum_triangle_area']>1e-12
    folder.mkdir(parents=True)
    np.savez_compressed(folder/'geometry.npz',xyz=assembly['xyz'],faces=assembly['faces'],face_member=assembly['face_parts'])
    metadata=dict(assembly['metadata'],candidate=mode,sources=sources,recipe=RECIPE,**checks)
    (folder/'assembly.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
    actual.export(folder/'gate.ply')
    print('ASSEMBLED',mode,len(assembly['faces']),'triangles; 3 separate parts',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--action',choices=('generate','assemble','gate-sources'),default='generate')
    p.add_argument('--cases',nargs='+',choices=('SPAN','COUNTER','GATE_COLUMN','GATE_LINTEL'),default=['SPAN','COUNTER'])
    p.add_argument('--modes',nargs='+',choices=('CONTROL','PREVIOUS','DEPTH','WALL'),default=['CONTROL','PREVIOUS','DEPTH','WALL'])
    args=p.parse_args()
    if args.action=='gate-sources':
        import gate_members
        for kind in ('COLUMN','LINTEL'):
            print('SOURCE',gate_members.write_source(args.root/'sources',kind),flush=True)
    elif args.action=='assemble':
        for mode in args.modes:
            assemble(args.root.resolve(),mode)
    else:
        for case in args.cases:
            for mode in args.modes:
                run(args.root.resolve(),case,mode)
