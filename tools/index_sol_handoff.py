"""Index existing experiments without replaying or modifying them."""
import json,hashlib,sys,os
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'outputs/sol_handoff_20261010';O.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
entries=[]
for branch in ['column_reference_20261010','generative_gate_20261010','connected_tissue_20261010','grotesque_gate_20261010','alice_cheshire_pipeline_20261010','recursive_column_20261010']:
 root=R/'scratch'/branch
 if not root.exists():entries.append(dict(root=str(root),missing=True));continue
 files=[]
 for parent,dirs,names in os.walk(root):
  dirs[:]=[d for d in dirs if d not in ['deps','external','__pycache__','worker_temp','test_runs']]
  for name in names:
   p=Path(parent)/name
   if p.suffix.lower() in ['.py','.ps1','.obj','.ply','.png','.json','.npz','.npy','.txt','.html']:
    files.append(dict(path=p.relative_to(R).as_posix(),bytes=p.stat().st_size))
 entries.append(dict(root=root.relative_to(R).as_posix(),files=files))
(R/'docs/SOL_EXPERIMENT_INDEX_20261010.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf8')
frozen=json.loads((R/'scratch/connected_tissue_20261010/sources.json').read_text());checks=[]
for path,expected in frozen.items():
 p=Path(path);actual=sha(p) if p.exists() else None;checks.append(dict(path=path,exists=p.exists(),matches=actual==expected,sha256=actual))
assert all(x['matches'] for x in checks)
(O/'frozen_target_hash_check.json').write_text(json.dumps(checks,indent=2))
sources=[]
for branch in entries:
 for rec in branch.get('files',[]):
  p=R/rec['path']
  if p.suffix=='.py':
   try:compile(p.read_text(encoding='utf8-sig'),str(p),'exec');status='syntax OK; not executed'
   except Exception as e:status=str(e)
   sources.append(dict(path=rec['path'],status=status,sha256=sha(p)))
(O/'source_syntax_check.json').write_text(json.dumps(sources,indent=2))
print('indexed',sum(len(x.get('files',[])) for x in entries),'files; frozen hashes verified',len(checks),'source files',len(sources))
