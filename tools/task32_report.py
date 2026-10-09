"""Summarize actual retained trials, not an automatic aesthetic ranking."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from task32_research import ROOT,read,write_new,sha


def summarize():
    geometry={};full={}
    for path in sorted((ROOT/'validation').glob('*/summary.json')):
        records=read(path)
        if not isinstance(records,list):continue
        for r in records:
            if 'embedding' in r:geometry[r['id']]=r
            if r.get('contacts',{}).get('all_triangles_sampled'):full[r['id']]=r
    rows=[]
    for path in sorted((ROOT/'candidates').glob('*/request.json')):
        dest=path.parent;request=read(path);stages=sorted(dest.glob('S[0-9][0-9]'))
        latest=read(stages[-1]/'summary.json');completed=(dest/'completed.json').exists()
        logs=[read(p) for p in sorted((ROOT/'logs'/dest.name).glob('attempt_*/process.json'))]
        proof_run=any(s in dest.name for s in ['REPLAY','PREFIX_RESUME','RECOVERY'])
        state=geometry.get(dest.name)
        screens=[]
        for stage in stages:
            meta=read(stage/'summary.json')['metadata']
            if 'contacts' in meta:screens.append(dict(stage=stage.name,contacts=meta['contacts']))
        row=dict(id=dest.name,proof_run=proof_run,completed=completed,
            status='completed' if completed else 'rejected_contact_screen' if latest['metadata'].get('continuation_rejected') else 'failed_recovery_probe',
            definition_sha256=request['definition_sha256'],source_snapshot=hashlib.sha256(json.dumps(request['sources'],sort_keys=True).encode()).hexdigest(),
            vertices=latest['vertices'],faces=latest['faces'],generation=latest['generation'],
            final_stage=str(stages[-1]),mesh_sha256=sha(stages[-1]/'mesh.npz'),
            guard_seconds=sum(r['seconds'] for r in logs),
            sampled_peak_MiB=max([r['sampled_peak_tree_plus_driver_bytes']/1024**2 for r in logs] or [0]),
            resource_stops=[r['resource_stop'] for r in logs if r['resource_stop']],
            screened_stages=screens,final_audit=state,full_audit=full.get(dest.name+'_final_full'),
            creation_UTC=datetime.fromtimestamp(path.stat().st_ctime,timezone.utc).isoformat(),
            note='Native metadata, numerical status and geometric flags are not an aesthetic verdict. Full checked triangles still exclude tangency/coplanar/adjacent cases.')
        rows.append(row)
    out=ROOT/'analysis';out.mkdir(exist_ok=True)
    write_new(out/'experiment_summary.json',dict(UTC=datetime.now(timezone.utc).isoformat(),records=rows,
        total_runs=len(rows),research_trials=sum(not r['proof_run'] for r in rows),
        proof_runs=sum(r['proof_run'] for r in rows),
        completed_research=sum(r['completed'] and not r['proof_run'] for r in rows),
        rejected_research=sum(not r['completed'] and not r['proof_run'] for r in rows)))
    columns=['id','proof_run','status','vertices','faces','generation','guard_seconds','sampled_peak_MiB','mesh_sha256','source_snapshot']
    with (out/'experiment_summary.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print('Research trials',sum(not r['proof_run'] for r in rows),'proof runs',sum(r['proof_run'] for r in rows))


if __name__=='__main__':summarize()
