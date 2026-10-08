"""Task32 evidence capture. Never edits prior studies or experimental stages."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from task32_research import ROOT,REPO,read,write_new,sha


def git(*args):
    return subprocess.check_output(['git','-c','safe.directory=C:/Users/USER/CHESHIRE',*args],cwd=REPO)


def sources():
    commits=git('rev-list','--reverse','17c0415..HEAD').decode().splitlines()
    groups={};records=[]
    for path in sorted((ROOT/'candidates').glob('*/request.json')):
        request=read(path);identity=request['sources']
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        groups[key]=identity
        records.append(dict(id=path.parent.name,source_snapshot=key,
                            definition_sha256=request['definition_sha256']))
    snapshots=[]
    for key,identity in groups.items():
        output=ROOT/'source_snapshots'/key;output.mkdir(parents=True,exist_ok=True)
        matching_revisions=set(commits);proof=[]
        for name,expected in identity.items():
            data=(REPO/name).read_bytes();matches=[]
            for commit in commits:
                result=subprocess.run(['git','-c','safe.directory=C:/Users/USER/CHESHIRE','show',commit+':'+name],
                                      cwd=REPO,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                if result.returncode:continue
                blob=result.stdout
                for option in (blob,blob.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')):
                    if hashlib.sha256(option).hexdigest()==expected:
                        data=option;matches.append(commit);break
            matching_revisions.intersection_update(matches)
            if hashlib.sha256(data).hexdigest()!=expected:
                raise ValueError('Exact historical source bytes unavailable: '+name)
            target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():
                with target.open('xb') as stream:stream.write(data)
            if sha(target)!=expected:raise ValueError('Source copy verification failed.')
            proof.append(dict(path=name,sha256=expected,matching_revisions=matches))
        snapshot=dict(key=key,files=proof,matching_source_revisions=sorted(matching_revisions),
                      note='Exact declared source bytes including line endings. Full imports/history retained in Git bundle; overlay these bytes in an isolated checkout to resume this batch.')
        if not matching_revisions:raise ValueError('No committed producer source set.')
        if not (output/'manifest.json').exists():write_new(output/'manifest.json',snapshot)
        snapshots.append(snapshot)
    dest=ROOT/'preservation/source_snapshots.json';number=2
    while dest.exists():
        dest=ROOT/f'preservation/source_snapshots_{number:03}.json';number+=1
    write_new(dest,dict(snapshots=snapshots,experiments=records))
    print('Preserved source sets',len(snapshots),'experiments',len(records))


def checkpoints():
    rows=[];total_files=0
    for path in sorted((ROOT/'candidates').glob('*/request.json')):
        request=read(path);dest=path.parent;stages=[]
        for stage in sorted(dest.glob('S[0-9][0-9]')):
            identity=read(stage/'task32_identity.json');index=int(stage.name[1:])
            expected_step=dict(kind='input') if index==0 else request['definition']['steps'][index-1]
            if identity['sources']!=request['sources'] or identity['step']!=expected_step:
                raise ValueError('Source/step identity mismatch: '+str(stage))
            for name,expected in identity['files'].items():
                if sha(stage/name)!=expected:raise ValueError('State hash mismatch: '+str(stage/name))
                total_files+=1
            parent=None if index==0 else sha(dest/f'S{index-1:02}'/'mesh.npz')
            if parent!=identity['parent_mesh_sha256']:raise ValueError('Parent hash mismatch.')
            stages.append(dict(stage=stage.name,mesh_sha256=sha(stage/'mesh.npz'),
                               files_verified=len(identity['files']),identity_sha256=sha(stage/'task32_identity.json')))
        completed=read(dest/'completed.json') if (dest/'completed.json').exists() else None
        if completed and len(stages)!=len(request['definition']['steps'])+1:raise ValueError('Incomplete declared run.')
        rows.append(dict(id=dest.name,completed=completed is not None,stages=stages,
                         request_sha256=sha(path),producer_sources=request['sources']))
    write_new(ROOT/'preservation/checkpoints_verified.json',dict(UTC=datetime.now(timezone.utc).isoformat(),
        experiments=rows,stage_files_verified=total_files,total_stages=sum(len(r['stages']) for r in rows)))
    print('Checkpoint files verified',total_files)


def protect():
    original=read(ROOT/'preservation/task31_before.json');rows=[]
    for row in original['files']:
        path=Path(original['root'])/row['path']
        if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:
            raise ValueError('Protected Task31 changed: '+str(path))
        rows.append(row)
    write_new(ROOT/'preservation/task31_after.json',dict(UTC=datetime.now(timezone.utc).isoformat(),
        root=original['root'],verified_files=len(rows),all_unchanged=True,files=rows))
    print('Protected Task31 files unchanged',len(rows))


def visibility():
    rows=[]
    # Fixed main portal interior, not an enclosed-hole counter for a U-shaped gate.
    corners=np.array([[-900.036865234375,-18.533447265625,800],
                      [99.963134765625,-18.533447265625,2000]])
    for manifest in sorted((ROOT/'renders').glob('*/manifest.json')):
        for record in read(manifest)['records']:
            if record.get('angles')!=[0,0] or record.get('width')!=5400:continue
            path=Path(record['image']).with_suffix('.visibility.npz')
            with np.load(path) as state:hit=state['hit']
            camera=np.array(record['camera_pose']);target=np.array(record['target'])
            projected=(corners-target)@camera[:3,:2];height,width=hit.shape
            xs=np.sort(np.clip(np.rint((projected[:,0]/5400+.5)*width).astype(int),0,width))
            ys=np.sort(np.clip(np.rint((.5-projected[:,1]/5400)*height).astype(int),0,height))
            roi=hit[ys[0]:ys[1],xs[0]:xs[1]]
            rows.append(dict(label=record['label'],mesh_sha256=record['mesh_sha256'],
                ROI_pixel_bounds=[xs.tolist(),ys.tolist()],samples=roi.size,
                occupied_pixels=int(roi.sum()),front_background_fraction=float(1-roi.mean()),
                outside_frame=record['outside_frame'],visibility_sha256=sha(path)))
    write_new(ROOT/'validation/portal_visibility.json',dict(world_ROI_corners=corners.tolist(),records=rows,
        caveat='Actual orthographic depth mask at fixed main portal interior. Background fraction is not 3D passage clearance, not a topology hole/genus metric, and not an aesthetic score.'))
    print('Portal front visibility records',len(rows))


def inventory():
    rows=[]
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and not path.name.startswith('FINAL_ARTIFACTS'):
            rows.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)))
    write_new(ROOT/'FINAL_ARTIFACTS.json',dict(UTC=datetime.now(timezone.utc).isoformat(),root=str(ROOT),
        files=rows,bytes=sum(r['bytes'] for r in rows),note='Payload manifest excludes itself. Includes failures, checkpoints, states, definitions, exact source overlays, papers and image/visibility evidence.'))
    print('Indexed',len(rows),'files',sum(r['bytes'] for r in rows),'bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['sources','checkpoints','protect','visibility','inventory'])
    a=p.parse_args();dict(sources=sources,checkpoints=checkpoints,protect=protect,visibility=visibility,inventory=inventory)[a.action]()
