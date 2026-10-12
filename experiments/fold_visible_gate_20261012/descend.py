"""One measured child generation from saved WALL G3; failed attempts persist."""
from pathlib import Path
import argparse
import json
import shutil

import numpy as np

import study
from child_fold import measure_child


def run(root,case):
    source=root/'WALL'/case/'G03'
    folder=root/'CHILD'/case/'G04'
    attempt=root/'child_attempts'/(case+'.json')
    if folder.exists() or attempt.exists():
        raise FileExistsError('Existing child attempt preserved: '+str(case))
    mesh,chart,tags=study.previous.anchor.t.load(source)
    sampler=study.native_sampler(mesh,chart)
    parent_metadata=json.loads((source/'generation.json').read_text(encoding='utf8'))
    children=[];records=[]
    for i in (0,1):
        with np.load(source/f'rails_{i}.npz') as data:
            parent={key:data[key] for key in data.files}
        try:
            child=measure_child(sampler,parent)
            child['parent_guide_index']=np.array(i)
            children.append(child)
            records.append(dict(parent_guide=i,status='EMITTED',
                actual_parent_detections=int(child['central_parent_detection_count']),
                central_rays=int(child['central_parent_ray_count']),
                interpolated_rays=int(child['interpolated_ray_count']),
                child_depth_range=[float(child['depth'].min()),float(child['depth'].max())],
                maximum_child_parent_depth_ratio=float((child['depth']/child['parent_depth']).max())))
        except ValueError as error:
            records.append(dict(parent_guide=i,status='NOT_EMITTED',reason=str(error)))
    attempt.parent.mkdir(parents=True,exist_ok=True)
    attempt.write_text(json.dumps(dict(case=case,source=str(source),attempts=records),indent=2),encoding='utf8')
    if not children:
        print('CHILD NOT EMITTED',case,records,flush=True)
        return
    out,outchart,outtags,operator=study.previous.anchor.t.memory.refine(mesh,chart,tags)
    reference=out.xyz.copy()
    reference_sampler=study.native_sampler(out,outchart)
    delta,fields=study.wall_fold.apply_wall(reference,outchart,children,mode='WALL')
    existing=study.previous.anchor.t.prior.helpers.existing
    existing.reflect(delta,outchart,existing.symmetry(outchart))
    if case=='GATE_LINTEL':
        import gate_members
        gate_members.reflect_axial_delta(delta,outchart)
    out.xyz=reference+delta
    after=study.native_sampler(out,outchart)
    retention=[]
    for child in children:
        uv=np.column_stack([child['parameter'],child['parent_valley_cross']])
        motion=np.linalg.norm(after.sample(uv)-reference_sampler.sample(uv),axis=1)
        unpaired=np.linalg.norm(after.sample(uv)-sampler.sample(uv),axis=1)
        retention.append(dict(parent_guide=int(child['parent_guide_index']),
            maximum_sampled_parent_valley_motion=float(motion.max()),
            median_sampled_parent_valley_motion=float(np.median(motion)),
            unpaired_g3_to_g4_sample_motion_maximum=float(unpaired.max()),
            scope='Finite matched inactive-G4 parent valley positions; excludes affine chart refinement drift. Not full angle or depth invariance.'))
    study.save(folder,out,outchart,outtags,
        dict(input_case=case,candidate='CHILD',recipe=dict(study.RECIPE,input_generation=3,
            output_generation=4,child_angle_degrees=30.,child_depth_parent_cap=.4,
            child_footprint_physical_arc=[.35,.75]),
            parent=str(source),parent_geometry_sha256=study.digest(source/'geometry.npz'),
            parent_recipe=parent_metadata['recipe'],parent_region_seeds=parent_metadata['parent_region_seeds'],
            input=parent_metadata['input'],added_field_passes=0,emitted_children=records,
            parent_valley_retention=retention,maximum_displacement=float(np.linalg.norm(delta,axis=1).max()),
            axial_role_constraint=parent_metadata.get('axial_role_constraint'),
            scope='One bounded descendant from actual generated walls; not a general recurrence engine.'),
        dict(reference_xyz=reference,delta=delta,chart=outchart,input_edges=operator['input_edges'],
            parent_face=operator['parent_face'],**fields),rails=children)
    shutil.copy2(Path(__file__),folder/'descend.py')
    shutil.copy2(Path(__file__).with_name('child_fold.py'),folder/'child_fold.py')
    print('CHILD RETENTION',case,retention,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--cases',nargs='+',default=['SPAN','COUNTER','GATE_COLUMN','GATE_LINTEL'])
    args=p.parse_args()
    for case in args.cases:
        run(args.root.resolve(),case)
