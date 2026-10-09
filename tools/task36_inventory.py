"""Read-only preservation, experiment ledger and render/native identity checks.

Checks the pre-Task36 tracked snapshot and seven selected Task35 assets only;
it does not repeat a full historical external archive audit.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];ROOT=Path('E:/CHESHIRE_DATA/task36')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()


def inventory(tag):
    dest=ROOT/'preservation'/tag;dest.mkdir(parents=True,exist_ok=False)
    baseline=json.loads((ROOT/'preservation/BASELINE.json').read_text());changed=[];missing=[]
    for name,old in baseline['tracked'].items():
        p=REPO/name
        if not p.exists():missing.append(name)
        elif digest(p)!=old:changed.append(name)
    protected=[dict(path=p,sha256=digest(Path(p)),unchanged=digest(Path(p))==h) for p,h in baseline['protected_selected_artifacts'].items()]
    allowed=['README.md','docs/CURRENT_PATHS.md']
    preservation=dict(baseline=baseline['baseline'],tracked_checked=len(baseline['tracked']),missing=missing,changed=changed,
        allowed_current_index_edits=allowed,unexpected_changes=[v for v in changed if v not in allowed],selected_Task35=protected)
    ledger=[];source_checks=state_checks=0
    for job in sorted((ROOT/'candidates').iterdir()):
        if not job.is_dir():continue
        if (job/'completed.json').exists():status='COMPLETED'
        elif (job/'failed.json').exists():status='GEOMETRY_REJECTED'
        elif (job/'interrupted.json').exists():status='INTENTIONALLY_INTERRUPTED'
        else:status='INCOMPLETE_OR_TOOL_ERROR'
        ledger.append(dict(candidate=job.name,status=status,fold_stages=sorted(p.name for p in job.glob('G*_FOLD'))))
        for name,h in json.loads((job/'source_identity.json').read_text()).items():
            if digest(job/'source'/name)!=h:raise ValueError('Producer source identity mismatch: '+job.name+'/'+name)
            source_checks+=1
        for identity in job.glob('G*/identity.json'):
            for name,h in json.loads(identity.read_text()).items():
                if digest(identity.parent/name)!=h:raise ValueError('Native checkpoint mismatch: '+str(identity.parent/name))
                state_checks+=1
    render_checks=[]
    for manifest in sorted((ROOT/'renders').glob('*/manifest.json')):
        for row in json.loads(manifest.read_text())['records']:
            stage=Path(row['stage']);im=Path(row['image'])
            ok=row['label'].startswith(stage.parent.name+'_'+stage.name+'_') and digest(stage/'mesh.npz')==row['mesh_sha256'] and digest(im)==row['image_sha256'] and digest(im.with_suffix('.visibility.npz'))==row['visibility_sha256']
            if not ok:raise ValueError('Render/native identity mismatch: '+row['label'])
            render_checks.append(dict(label=row['label'],physical_width=row['physical_width'],outside_frame=row['outside_frame']))
    result=dict(preservation=preservation,experiments=ledger,producer_source_hash_checks=source_checks,checkpoint_hash_checks=state_checks,render_hash_checks=len(render_checks),renders=render_checks,
        git_head=subprocess.check_output(['git','-c','safe.directory='+REPO.as_posix(),'rev-parse','HEAD'],cwd=REPO,text=True).strip())
    (dest/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    if missing or preservation['unexpected_changes'] or not all(v['unchanged'] for v in protected):raise ValueError('Protected baseline changed.')
    print('Verified',len(protected),'Task35 assets,',source_checks,'producer sources,',state_checks,'checkpoint files,',len(render_checks),'renders; baseline changes',changed,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);a=p.parse_args();inventory(a.tag)
