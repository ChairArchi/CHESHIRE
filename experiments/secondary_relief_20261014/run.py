"""One low-amplitude existing FINE phase on the accepted triangle-native finish.

No old source chart, quad ancestry or feature-memory support is invented.
Incident triangle normals and actual clean ID reflection bind displacement.
This is G7-derived finish relief, not another source subdivision generation.
"""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import sys
import time

import numpy as np
from scipy.interpolate import PchipInterpolator

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SOURCE=Path('E:/CHESHIRE_DATA/experiments/volume_junction_target_20261014/trial01/volume_finish_clean')
SOURCE_GEOMETRY_SHA='74db70348be271c24f6284a94680c3d9136cb2c25a339b563c89e30b91a16122'
DEFAULT_ROOT=Path('E:/CHESHIRE_DATA/experiments/secondary_relief_20261014/trial01')
FIELD=HERE.parent/'whole_column_detail_20261013/whole_field.py'
spec=importlib.util.spec_from_file_location('secondary_relief_preserved_phase',FIELD)
old=importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

RECIPE=dict(schema='CHESHIRE_TRIANGLE_NATIVE_SECONDARY_RELIEF_20261014',
    source='G7-derived cleaned volumetric finish accepted by user',
    phase='Reuse exact whole_field.py FINE analytic phase, profile, modulation and PCHIP envelope; no new MIDDLE geometry.',
    amplitude_height_fraction=.0006, old_FINE_amplitude_height_fraction=.0018,
    actual_source_normal='Unit mean of actual incident triangle unit normals; no normal/shading map.',
    current_feature_policy='No inherited feature_support exists on remesh; do not substitute or claim old support. Instead attenuate where incident normals disagree.',
    normal_coherence='norm(mean(incident triangle unit normals)), in [0,1].',
    coherence_attenuation='smoothstep(clip((coherence-.75)/.20,0,1)); hard or folded-back junctions attenuated, smooth faces retain amplitude.',
    displacement='actual_source_XYZ + transported_actual_normal * signed_amplitude',
    reflection='Actual clean mirror_x/y_vertex_pairs; frozen _transport; exact source ID topology retained.',
    added_source_subdivision_passes=0, added_topology_events=0, added_voxel_passes=0,
    added_mandelbulb_evaluations=0, added_normal_displacement_passes=1,
    source_geometry_averaged=False, original_growth_G8=False,
    scope='One authored low-amplitude whole-column relief. Analytic theta/height phase gives mostly longitudinal direction; it does not track every actual material fold, restore old chart/feature ancestry, or add branching ornament.')


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):result.update(block)
    return result.hexdigest()


def array_hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def triangle_normals(xyz,faces):
    """Triangle-native adaptation of the preserved incident unit-normal rule."""
    nv,nf=len(xyz),len(faces)
    face_normals=np.empty((nf,3),np.float32)
    for start in range(0,nf,262144):
        triangle=xyz[faces[start:start+262144]].astype(float)
        cross=np.cross(triangle[:,1]-triangle[:,0],triangle[:,2]-triangle[:,0])
        length=np.linalg.norm(cross,axis=1)
        if np.any(length<=1e-16):raise ValueError('Degenerate actual source triangle.')
        face_normals[start:start+len(triangle)]=cross/length[:,None]
    degree=np.bincount(faces.ravel(),minlength=nv)
    if np.any(degree==0):raise ValueError('Actual source has orphan vertices.')
    mean=np.empty((nv,3),float)
    for component in range(3):
        mean[:,component]=np.bincount(faces.ravel(),weights=np.repeat(face_normals[:,component],3),minlength=nv)/degree
    coherence=np.linalg.norm(mean,axis=1)
    if np.any(coherence<=1e-12):raise ValueError('Zero incident mean source normal; no fallback.')
    mean/=coherence[:,None]
    return mean,np.clip(coherence,0.,1.)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    root=parser.parse_args().root.resolve()
    if root.exists() and any(root.iterdir()):raise FileExistsError('Earlier output preserved.')
    root.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    source_info=json.loads((SOURCE/'FINISH_RECEIPT.json').read_text(encoding='utf-8'))
    source_checks=json.loads((SOURCE/'VERIFICATION.json').read_text(encoding='utf-8'))
    if digest(SOURCE/'geometry.npz')!=SOURCE_GEOMETRY_SHA or not source_checks['all_required_checks_pass']:
        raise ValueError('Actual accepted source/checkpoint changed.')
    if digest(SOURCE/'cleanup_evidence.npz')!=source_info['cleanup_evidence_sha256']:
        raise ValueError('Actual clean ID reflection evidence changed.')
    hashes={path.relative_to(REPO).as_posix():digest(path) for path in [Path(__file__),FIELD,REPO/'src/cheshire/reference_subdivision.py']}
    snapshot=root/'source_snapshot'
    for rel,sha in hashes.items():
        target=snapshot/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/rel,target)
    write(root/'RUN_REQUEST.json',dict(date='2026-10-14',recipe=RECIPE,source=str(SOURCE),
        source_geometry_sha256=SOURCE_GEOMETRY_SHA,source_finish_receipt_sha256=digest(SOURCE/'FINISH_RECEIPT.json'),
        source_verification_sha256=digest(SOURCE/'VERIFICATION.json'),source_cleanup_evidence_sha256=source_info['cleanup_evidence_sha256'],geometry_code_sha256=hashes,
        user_direction='Previous finish is sufficiently acceptable; stop fixating on irregular rolled ends and move to next scale.'))
    print('LOAD accepted full-column finish and actual ID involutions',flush=True)
    with np.load(SOURCE/'geometry.npz',allow_pickle=False) as data:xyz,faces=data['xyz'],data['faces']
    with np.load(SOURCE/'cleanup_evidence.npz',allow_pickle=False) as data:
        pairs=dict(X=data['mirror_x_vertex_pairs'],Y=data['mirror_y_vertex_pairs'])
    ids,pairs=old._mirror_pairs(pairs,len(xyz))
    print('ACTUAL triangle incident normals',flush=True)
    normals,coherence=triangle_normals(xyz,faces)
    zmin,zmax=float(xyz[:,2].min()),float(xyz[:,2].max());height=zmax-zmin
    z=(xyz[:,2].astype(float)-zmin)/height
    theta=np.arctan2(np.abs(xyz[:,1].astype(float)),np.abs(xyz[:,0].astype(float)))
    middle=old._middle_phase(theta,z)
    phase=72*theta+3.5*np.sin(2*theta)*np.sin(2*np.pi*z/.023)+.9*np.sin(6*theta)*np.sin(2*np.pi*z/.049)+1.2*np.sin(4*theta)*np.sin(middle)
    env=PchipInterpolator(old.RECIPE['envelope']['knots'],old.RECIPE['envelope']['values'],extrapolate=False)(z)
    attenuation=np.clip((coherence-.75)/.20,0.,1.);attenuation=attenuation*attenuation*(3.-2.*attenuation)
    signed=height*.0006*env*(.7+.3*np.cos(middle)**2)*attenuation*old._profile(phase)
    delta,representative,fixed_x,fixed_y=old._transport(normals*signed[:,None],ids,pairs)
    output=xyz.astype(float)+delta
    bound=height*.0006
    motion=np.linalg.norm(delta,axis=1)
    if not np.isfinite(output).all() or motion.max()>bound*(1+1e-12):raise ValueError('Actual displacement violates fixed amplitude.')
    for axis,sign in [('X',[-1.,1.,1.]),('Y',[1.,-1.,1.])]:
        for start in range(0,len(output),262144):
            stop=min(start+262144,len(output))
            if not np.array_equal(output[pairs[axis][start:stop]],output[start:stop]*sign):raise ValueError('Actual exact output symmetry failed: '+axis)
    # Check every actual triangle against source orientation and area once.
    min_area=np.inf;flipped=0;minimum_normal_dot=1.
    for start in range(0,len(faces),262144):
        f=faces[start:start+262144];p=xyz[f].astype(float);q=output[f]
        a=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);b=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
        la,lb=np.linalg.norm(a,axis=1),np.linalg.norm(b,axis=1)
        dot=np.einsum('ij,ij->i',a,b)/(la*lb)
        min_area=min(min_area,float(lb.min()*.5));flipped+=int(np.count_nonzero(dot<=0.));minimum_normal_dot=min(minimum_normal_dot,float(dot.min()))
    if min_area<=1e-14 or flipped:raise ValueError('New displacement has collapsed or reversed source triangles: '+str((min_area,flipped)))
    # Invariant topology inherits proven source edge closure/connectivity; no redundant rebuild.
    path=root/'geometry.npz';np.savez(path,xyz=output,faces=faces)
    evidence=root/'displacement.npz';np.savez(evidence,displacement=delta,normal_coherence=coherence,attenuation=attenuation)
    record=dict(date='2026-10-14',candidate='SECONDARY_RELIEF',source=str(SOURCE),
        source_geometry_sha256=SOURCE_GEOMETRY_SHA,geometry=str(path),geometry_sha256=digest(path),
        xyz_sha256=array_hash(output),faces_sha256=array_hash(faces),vertices=len(output),triangles=len(faces),
        recipe=RECIPE,physical_height=height,amplitude_bound=bound,maximum_actual_displacement=float(motion.max()),
        displacement_quantiles=np.quantile(motion,[0,.5,.9,.99,1]).tolist(),
        normal_coherence_quantiles=np.quantile(coherence,[0,.01,.1,.5,1]).tolist(),
        attenuated_vertex_count=int(np.count_nonzero(attenuation<1.)),
        normal_displacement_passes=1,added_topology_events=0,added_subdivision_passes=0,
        exact_XY_vertex_ID_symmetry=True,source_triangle_indices_unchanged=True,
        minimum_output_triangle_area=min_area,source_orientation_reversed_triangles=flipped,minimum_source_output_normal_dot=minimum_normal_dot,
        inherited_topology_checks=source_checks['checks'],inherited_topology_verification_sha256=digest(SOURCE/'VERIFICATION.json'),
        topology_check_scope='Exact unchanged triangle array inherits proven closed connected oriented edge graph and no orphans; all current output positions/triangle areas and relative orientation checked.',
        displacement_file_sha256=digest(evidence),geometry_code_sha256=hashes,elapsed_seconds=time.perf_counter()-started,
        source_unchanged=digest(SOURCE/'geometry.npz')==SOURCE_GEOMETRY_SHA,
        visual_status='PENDING_ACTUAL_MATCHED_RENDER',self_intersection='NOT_CHECKED',G1_continuity='NOT_CERTIFIED')
    if not record['source_unchanged'] or any(digest(REPO/rel)!=sha for rel,sha in hashes.items()):raise ValueError('Actual source/code changed during generation.')
    write(root/'RECEIPT.json',record)
    print('SECONDARY_RELIEF_SAVED',len(output),len(faces),motion.max(),flush=True)


if __name__=='__main__':main()
