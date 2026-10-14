"""One early field-direction revision, exact replay, bounded original-G7 output."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_ROOT = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
SELECTION = Path('E:/CHESHIRE_DATA/experiments/volume_junction_target_20261014/trial01/selection.npz')
SELECTION_SHA = '7bbfb7cdb50b3fad320451dc096b23f8f662c7a09a425324949cba39396584ab'
SOURCE_HASHES = {'generation.json':'c7452dc63998c61783215f0bb23434ea5e9b223d89fcd836d1a4081907ab2cf5',
    'control_quad.npz':'0d966671a028cd56f49d0c5d1e626207652e789d281a9fa69475c3492f95fdc6',
    'geometry.npz':'98a88c6727045e0a5aad67df6cd6295de6c14655a78ac0ca95812a5f37841e91'}
STAGES = ('early','G05_DIRECTIONAL','G06_DEPTH08','G06_MIDDLE','G07_SURFACE',
    'G07_LINKED_RAW','G07_LINKED_FINISHED','G07_WIDE_RAW','G07_FINAL')


def digest(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):
            h.update(block)
    return h.hexdigest()


def ah(a):
    return hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def splice(root):
    incoming = root/'replay/states/G07_FINAL'
    replay_info = read(incoming/'generation.json')
    if not replay_info['checks']['passed']:
        raise ValueError('Actual revised source replay failed.')
    print('CHECK original/replayed actual G7 topology and associations',flush=True)
    with np.load(SOURCE/'control_quad.npz',allow_pickle=False) as original:
        data = {k:original[k] for k in ('xyz','faces','chart','classes','rest','anchors','generation','surface')}
    with np.load(incoming/'control_quad.npz',allow_pickle=False) as revised:
        xyz_replay = revised['xyz']
        for key in ('faces','chart','classes','rest','anchors','generation','surface'):
            if not np.array_equal(revised[key],data[key]):
                raise ValueError('Exact original/replay association differs: '+key)
    if xyz_replay.shape != data['xyz'].shape or not np.isfinite(xyz_replay).all():
        raise ValueError('Finite same-topology revised G7 required.')
    if digest(SELECTION) != SELECTION_SHA:
        raise ValueError('Original user-marked mask changed.')
    with np.load(SELECTION,allow_pickle=False) as selection:
        mask = selection['full_mask']
    if mask.shape != (len(data['xyz']),) or mask.min()<0 or mask.max()>1:
        raise ValueError('Original source-bound mask required.')
    before = data['xyz']
    delta = (xyz_replay-before)*mask[:,None]
    output = before+delta
    if not np.array_equal(output[mask==0],before[mask==0]):
        raise ValueError('Out-of-mask geometry changed.')
    faces = data['faces']
    affected = np.flatnonzero(np.any(mask[faces]>0,axis=1))
    minimum, normal_reversed, maximum_angle, all_nonfinite = float('inf'),0,0.,0
    for start in range(0,len(affected),32768):
        ids = affected[start:start+32768]
        qold, qnew = before[faces[ids]],output[faces[ids]]
        cold,cnew = qold.mean(1),qnew.mean(1)
        for k in range(4):
            no = np.cross(qold[:,(k+1)%4]-qold[:,k],cold-qold[:,k])
            nn = np.cross(qnew[:,(k+1)%4]-qnew[:,k],cnew-qnew[:,k])
            area = np.linalg.norm(nn,axis=1)
            minimum = min(minimum,float(area.min())*.5)
            all_nonfinite += int(np.count_nonzero(~np.isfinite(area)))
            cosine = np.einsum('ij,ij->i',no,nn)/np.maximum(np.linalg.norm(no,axis=1)*area,1e-30)
            normal_reversed += int(np.count_nonzero(cosine<0))
            maximum_angle=max(maximum_angle,float(np.rad2deg(np.arccos(np.clip(cosine,-1,1))).max()))
    if minimum<=0 or all_nonfinite or not np.isfinite(output).all():
        raise ValueError('Affected native triangle degeneration or nonfinite result.')
    pairs_path = SOURCE/'evidence.npz'
    symmetry={}
    with np.load(pairs_path,allow_pickle=False) as evidence:
        for label,coordinate in (('x',0),('y',1)):
            pair=evidence['mirror_'+label+'_vertex_pairs']
            reflected=output[pair].copy();reflected[:,coordinate]*=-1
            error=float(np.linalg.norm(output-reflected,axis=1).max())
            if error>1e-9:raise ValueError('Actual candidate symmetry changed.')
            symmetry[label]=error
    region = mask>0
    stats=dict(selected_controls=int(region.sum()),changed_controls=int(np.count_nonzero(np.any(delta!=0,axis=1))),
        unchanged_outside_controls=int(np.count_nonzero(~region)),changed_outside_controls=0,
        maximum_delta=float(np.linalg.norm(delta,axis=1).max()),
        rms_selected_delta=float(np.sqrt(np.mean(np.sum(delta[region]**2,axis=1)))),
        actual_source_region_max_radius=float(np.linalg.norm(before[region,:2],axis=1).max()),
        actual_candidate_region_max_radius=float(np.linalg.norm(output[region,:2],axis=1).max()),
        original_selected_z_range=[float(before[region,2].min()),float(before[region,2].max())],
        candidate_selected_z_range=[float(output[region,2].min()),float(output[region,2].max())],
        affected_quads=len(affected),checked_affected_native_triangles=4*len(affected),
        minimum_affected_native_triangle_area=minimum,old_new_normal_dot_negative_triangles=normal_reversed,
        maximum_old_new_triangle_normal_angle_degrees=maximum_angle,
        normal_scope='Old/new normal angle is a deformation diagnostic, not a self-intersection or invariant orientation certificate.',
        actual_XY_reflection_max_error=symmetry)
    folder=root/'REVISED';folder.mkdir(exist_ok=False)
    data['xyz']=output
    control=folder/'control_quad.npz'
    np.savez_compressed(control,**data)
    np.savez_compressed(folder/'delta.npz',delta=delta,mask=mask)
    del xyz_replay,delta,mask,data,before
    gc.collect()
    print('SAVE actual revised native G7; no added topology',flush=True)
    centres=output[faces].mean(axis=1)
    native_xyz=np.concatenate([output,centres]);del centres
    with np.load(SOURCE/'geometry.npz',allow_pickle=False) as native:
        native_faces=native['faces']
    if len(native_xyz)!=14004226 or len(native_faces)!=28008448:
        raise ValueError('Expected immutable original native topology.')
    geometry=folder/'geometry.npz'
    np.savez_compressed(geometry,xyz=native_xyz,faces=native_faces)
    return dict(geometry=str(geometry),geometry_sha256=digest(geometry),xyz_sha256=ah(native_xyz),
        faces_sha256=ah(native_faces),vertices=len(native_xyz),triangles=len(native_faces),
        control=str(control),control_sha256=digest(control),statistics=stats,
        topology_scope='Exact original control topology/associations and native triangle indices; inherited original one-component closed oriented topology, no added components.',
        replay_final=str(incoming),replay_final_generation_sha256=digest(incoming/'generation.json'),
        mask=str(SELECTION),mask_sha256=SELECTION_SHA,
        combination='Xfinal=Xoriginal+saved_original_mask*(Xexact_revised_replay−Xoriginal). Exact replay interior with feathered transition; outside mask original XYZ is byte-identical.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    args=parser.parse_args();root=args.root.resolve()
    if (root/'RECEIPT.json').exists() or (root/'replay').exists():
        raise FileExistsError('Existing trial/replay preserved; no parameter retuning or overwrite.')
    root.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    for name,h in SOURCE_HASHES.items():
        if digest(SOURCE/name)!=h:raise ValueError('Original source changed: '+name)
    hashes={str((HERE/n).relative_to(REPO)).replace('\\','/'):digest(HERE/n) for n in ('run.py','replay.py')}
    for rel,h in hashes.items():
        target=root/'source_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/rel,target)
    write(root/'RUN_REQUEST.json',dict(date='2026-10-14',basis_commit='34063f2cb424f3896bdd4114862321611b8dd5f0',
        input_case='SPAN',one_candidate=True,source=str(SOURCE),source_hashes=SOURCE_HASHES,
        changed_rule='G1/G2 finite-field applied Z component only: axial_gain=1−.75*material_mask. XY, Task36 and authored returns unchanged.',
        exact_replay_stages=STAGES,final_output='Source-bound feathered original G7 end mask; no extra ornaments or G8.',
        geometry_code_sha256=hashes))
    temp=root/'temp';temp.mkdir(exist_ok=True)
    env=os.environ.copy();env.update(TEMP=str(temp),TMP=str(temp),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    for stage in STAGES:
        print('REPLAY one revised source rule /',stage,flush=True)
        logfile=root/(stage+'.log')
        with open(logfile,'w',encoding='utf8') as log:
            result=subprocess.run([sys.executable,'-X','utf8','-B','-u',str(HERE/'replay.py'),
                '--root',str(root/'replay'),'--stage',stage],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError('Revised replay stopped; preserved log '+str(logfile))
    variant=splice(root)
    for name,h in SOURCE_HASHES.items():
        if digest(SOURCE/name)!=h:raise ValueError('Preserved original source changed.')
    for rel,h in hashes.items():
        if digest(REPO/rel)!=h or digest(root/'source_snapshot'/rel)!=h:raise ValueError('Executed source changed.')
    write(root/'RECEIPT.json',dict(date='2026-10-14',timezone='Asia/Seoul',input_case='SPAN',
        source_native_path=str(SOURCE/'geometry.npz'),source_native_geometry_sha256=SOURCE_HASHES['geometry.npz'],
        source_hashes_after=SOURCE_HASHES,source_growth_generation=7,added_G8=False,added_ornaments=0,
        one_rule_revision=True,variants={'REVISED':variant},geometry_code_sha256=hashes,
        seconds=time.perf_counter()-started,visual_success='PENDING_MATCHED_FLAT_AND_SMOOTH_REVIEW',
        scope='One modified early field-direction rule with actual downstream regeneration. Final candidate is restricted to original marked ends; all original data and prior candidates remain untouched.'))
    print('SAVED one source-rule revision; original G7 preserved',flush=True)


if __name__=='__main__':
    main()
