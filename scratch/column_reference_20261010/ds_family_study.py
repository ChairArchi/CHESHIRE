"""Current topology generates parent/edge/vertex face families; then families diverge.
No fin primitive or circumferential placement list. Experimental weighted DS.
"""
import json
import numpy as np
import fluted_generation as common
from cheshire.weighted_doosabin import weighted_doosabin_once
from cheshire.execution import ExecutionBudget

source=common.ROOT/'fluted_generation_results/g00/mesh.json';data=json.loads(source.read_text())
mesh=common.Mesh.from_vertices_and_faces(data['vertices'],data['faces']);families=None
common.OUT=common.ROOT/'ds_family_results';common.OUT.mkdir(exist_ok=True)
for generation in range(2):
    overrides={}
    for f in mesh.faces():
        area=float(mesh.face_area(f));p=np.array(mesh.face_coordinates(f));normal=mesh.face_normal(f)
        family=families[f]['class'] if families else 'SOURCE_FACE'
        scale=np.sqrt(area)
        if family in ['SOURCE_FACE','FACE_DERIVED']:
            w1=.35;distance=-.035*scale
        elif family=='EDGE_DERIVED':
            w1=.25;distance=.42*scale
        else:w1=.3;distance=.12*scale
        if abs(normal[2])>.999:distance=0.
        overrides[f]={'w1':float(w1),'w10':float(distance)}
    result=weighted_doosabin_once(mesh,face_families=families,face_weights=overrides,current_generation=generation,budget=ExecutionBudget(150000,150000))
    mesh=result.mesh;families=result.face_families
    common.save(mesh,generation+1,dict(operation='weighted Doo-Sabin using existing CHESHIRE / COMPAS',family_counts=result.metadata['family_counts'],input_families=result.metadata['input_family_counts'],fallback_faces=result.metadata['fallback_faces'],placement='parent face contraction; independently weighted generated edge/vertex faces',fin_primitive=False,standard_smoothing_pass=False,uses_affine_corner_interpolation=True,claim='mechanism test, not original Hansmeyer settings'))
    (common.OUT/f'g{generation+1:02d}'/'families.json').write_text(json.dumps(families))
