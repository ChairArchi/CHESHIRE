"""One bounded actual NESTED02 parent measurement; no deformation/export."""
from pathlib import Path
import importlib.util
import json
import time
import numpy as np

HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value

started=time.perf_counter()
util=module('macro_measure_receipt',HERE/'run_recursive.py')
op=module('macro_measure_operator',HERE/'recursive_fold_formation.py')
receipt=json.loads((util.ACCEPTED/'RECEIPT.json').read_text(encoding='utf8'))
source=Path(receipt['variants']['NESTED']['control_quad'])
print('LOAD actual accepted NESTED02 G7',flush=True)
control=util.arrays(source)
mesh=op.core.ArrayMesh(control['xyz'],control['faces'],control['classes'],control['rest'],control['anchors'],int(control['generation']))
mesh.surface=str(control['surface']);chart=control['chart']
with np.load(util.STATES/'G03_SIDEWALL/evidence.npz',allow_pickle=False) as data:owners=data['face_event_ids']
with np.load(util.STATES/'G03_SIDEWALL/control_quad.npz',allow_pickle=False) as data:q3=data['faces']
ancestor=mesh.faces
for _ in range(4):ancestor=ancestor.reshape(-1,4,4)[:,:,1]
assert np.array_equal(ancestor,q3)
body=np.repeat(owners==0,4**4)
events,bank=op.original_events.load_events()
print('MEASURE exact SOURCE components and actual macro shoulders',flush=True)
segmented,coverage,sampler,info,evidence=op._resolve_and_partition(mesh,chart,op.initialize_events(events),body)
records=[]
for parent in segmented['parents']:
    record=dict(family_id=int(parent['family_id']),piece_id=str(parent['piece_id']))
    try:child,_=op._measure_safe(sampler,parent['rail'])
    except ValueError as error:record.update(status='ABSENT_ACTUAL_PARENT',reason=str(error))
    else:
        record.update(status='MEASURED_ACTUAL_PARENT',axis=str(child['axis']),
            parameter=child['parameter'].tolist(),lower_cross=child['lower_cross'].tolist(),
            guide_cross=child['guide_cross'].tolist(),upper_cross=child['upper_cross'].tolist(),
            centre_bounds_min=child['centre_xyz'].min(axis=0).tolist(),
            centre_bounds_max=child['centre_xyz'].max(axis=0).tolist(),
            parent_shoulder_side=str(child['parent_shoulder_side']),
            actual_parent_depth_quantiles=np.quantile(child['parent_observed_chord_depth'],[0,.5,1]).tolist(),
            physical_child_width_quantiles=np.quantile(child['child_physical_width'],[0,.5,1]).tolist(),
            normal_amplitude_quantiles=np.quantile(child['formation_normal_amplitude'],[0,.5,1]).tolist(),
            return_amplitude_quantiles=np.quantile(child['formation_return_amplitude'],[0,.5,1]).tolist())
    records.append(record);print(record['family_id'],record['piece_id'],record['status'],record.get('normal_amplitude_quantiles',record.get('reason')),flush=True)
report=dict(status='MEASUREMENT_ONLY',source=str(source),expected_source_file_sha256=receipt['variants']['NESTED']['control_quad_sha256'],
    source_xyz_sha256=op.core._hash(mesh.xyz),source_geometry_changed=False,added_CC_passes=0,
    source_component_records=coverage,pieces=records,sampler=info,elapsed_seconds=time.perf_counter()-started,
    limitation='Actual measured ownership and physical budget are not a beauty result or a next-tier closure proof.')
target=HERE/'macro_parent_measurement.json'
target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
print('MEASUREMENT_COMPLETE',target,report['elapsed_seconds'],flush=True)
