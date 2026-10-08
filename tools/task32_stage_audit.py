"""Explicit checkpoint audits, including complete low-resolution contact checks."""
import argparse
from pathlib import Path
from time import perf_counter
import numpy as np
from task32_research import ROOT,read,write_new,sha
from task32_validation import embedding,transverse_contacts,section_segments
from task29_search import load_mesh
from hero_design_sprint import guarded


def audit(request,tag):
    output=ROOT/'validation'/tag;output.mkdir(parents=True,exist_ok=False);rows=[]
    for item in read(request)['items']:
        path=Path(item['stage']).resolve()
        if not any(path.is_relative_to(root.resolve()) for root in [ROOT/'candidates',Path('E:/CHESHIRE_DATA/task31/lead/gate')]):
            raise ValueError('Only protected/current native checkpoint reads allowed.')
        m=load_mesh(path);start=perf_counter()
        row=dict(**item,mesh_sha256=sha(path/'mesh.npz'),embedding=embedding(m),contacts=transverse_contacts(m))
        sections,segments=section_segments(m)
        np.savez_compressed(output/(item['id']+'_sections.npz'),**segments)
        row.update(sections=sections,seconds=perf_counter()-start)
        write_new(output/(item['id']+'.json'),row);rows.append(row)
        print(item['id'],row['contacts']['transverse_contacts'],row['embedding']['opposed_quad_fan_normals'],flush=True)
    write_new(output/'summary.json',rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in a.tag):raise ValueError('Safe tag required.')
    if a.worker:audit(a.request,a.tag)
    else:
        result=guarded(['--request',str(a.request),'--tag',a.tag,'--worker'],ROOT/'logs'/('stage_audit_'+a.tag),worker_script=Path(__file__))
        print(result)
        if result['exit_code']:raise SystemExit(result['exit_code'])
