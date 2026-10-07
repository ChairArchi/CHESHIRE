"""Task27 hash-linked stage index and actually reread review/model archives."""
import argparse,sys,subprocess
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from dynamic_section_gates import directory,SOURCES,BASELINE
from cross_cell_crease_study import read,write,file_hash
from progressive_gate_package import archive

TASK_SOURCES=['src/cheshire/dynamic_sections.py','examples/dynamic_section_gates.py','tests/test_dynamic_sections.py',
    'tools/dynamic_section_views.py','tools/dynamic_section_native.ps1','tools/dynamic_section_jobs.py',
    'tools/dynamic_section_evidence.py','tools/dynamic_section_package.py','docs/TASK27_RESULTS.md','docs/TASK27_HANDOFF.md']


def package(root,revision,generation):
    lead=f'{revision}_PROFILE_DYNAMIC_G{generation}';stages=[]
    for d in sorted((root/'stages').iterdir()):
        if not (d/'summary.json').exists():continue
        row=read(d/'summary.json')
        row['files']={p.name:dict(path=str(p),bytes=p.stat().st_size,sha256=file_hash(p)) for p in d.iterdir() if p.is_file()}
        if (d/'request.json').exists():
            for name,h in read(d/'request.json')['source_hashes'].items():
                candidates=[REPO/name,*list((root/'source_snapshots').glob('*/'+name))]
                if not any(p.is_file() and file_hash(p)==h for p in candidates):raise ValueError('Executed source hash missing: '+name)
        stages.append(row)
    captures=[]
    for p in sorted((root/'renders').glob('*/camera_manifest.json')):
        m=read(p)
        for row in m['records']:
            if file_hash(Path(row['geometry']))!=row['geometry_sha256']:raise ValueError('Captured geometry identity changed.')
            if file_hash(Path(row['image']))!=row['image_sha256']:raise ValueError('Actual captured PNG identity changed.')
        captures.append(dict(path=str(p),sha256=file_hash(p),records=m['records']))
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=REPO).strip()
    status=subprocess.check_output(['git','status','--porcelain'],text=True,cwd=REPO)
    write(root/'stage_manifest.json',dict(lead=lead,baseline=BASELINE,stages=stages,captures=captures,
        lineage=['G0_PROFILE',*[f'{revision}_PROFILE_DYNAMIC_G{g}' for g in range(1,generation+1)]],
        policy='Every stage is an actual saved parent-child generation. Original polygons retained; neutral OpenGL capture derivatives are declared separately.'))
    write(root/'release.json',dict(baseline=BASELINE,final_local_commit=sha,branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
        working_tree=status,clean=not bool(status),lead=lead,source_hashes={n:file_hash(REPO/n) for n in TASK_SOURCES},
        OBJ=str(directory(root,lead)/(lead+'.obj')),native=str(root/'dcc'/(lead+'.3dm'))))
    review={};model={}
    def add(target,p):
        if p.is_file():target[p.relative_to(root).as_posix()]=p
    for name in ['FINAL_REPORT.md','TASK27_HANDOFF.md','configuration.json','stage_manifest.json','release.json']:
        add(review,root/name);add(model,root/name)
    for folder in ['definitions','recipes','analysis','test_logs','brief']:
        for p in (root/folder).rglob('*'):
            add(review,p)
            if folder in ('definitions','recipes'):add(model,p)
    for p in (root/'source_snapshots').rglob('*'):add(review,p);add(model,p)
    for p in (root/'logs').glob('*/process.json'):add(review,p)
    for row in stages:
        d=root/'stages'/row['name']
        for name in ['summary.json','request.json','resource_preflight.json']:add(review,d/name)
    # Preserve every capture externally; keep the upload packet focused on
    # the accepted lineage, its matched controls and representative trials.
    for p in (root/'renders').glob('*/**/*manifest.json'):add(review,p)
    for p in (root/('renders/'+revision+'_G4_comparison')).glob('*_four_path_comparison.png'):add(review,p)
    for p in (root/('renders/progression_'+revision)).glob('*_sheet.png'):add(review,p)
    for p in (root/'renders/coarse').glob('*_sheet.png'):add(review,p)
    for tag in ['R1_comparison','R2_G4_comparison','R3_G4_comparison','revision_comparison']:
        p=root/'renders'/tag/'front_sheet.png';add(review,p)
    for p in (root/('renders/lead_'+revision)).glob('*.png'):
        if not p.name.endswith('_sheet.png'):add(review,p)
    add(review,root/'renders/geometry/section_comparison.png')
    for p in (root/'dcc').glob('*_import_evidence.json'):add(review,p);add(model,p)
    for g in range(1,generation+1):
        d=directory(root,f'{revision}_PROFILE_DYNAMIC_G{g}')
        for name in ['descriptors.json.gz','rules.json.gz']:add(review,d/name)
    for p in directory(root,lead).iterdir():add(model,p)
    for p in directory(root,'G0_PROFILE').iterdir():add(model,p)
    add(model,root/'dcc'/(lead+'.3dm'))
    for name in TASK_SOURCES:
        review['source/'+name]=REPO/name;model['source/'+name]=REPO/name
    a=archive(root/'CHESHIRE_TASK27_REVIEW.zip',review)
    b=archive(root/'CHESHIRE_TASK27_MODEL.zip',model)
    write(root/'deliverables.json',dict(review=a,model=b,lead=lead,final_local_commit=sha,working_tree_clean=not bool(status)))
    print('Actual ZIP reread CRC/payload SHA256 passed',a['bytes'],b['bytes'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--revision',default='R3');p.add_argument('--generation',type=int,default=4)
    a=p.parse_args();package(a.output_root,a.revision,a.generation)
