"""Refresh changed/new files after the full SHA-verified preservation pass.
Unchanged size+mtime files retain the prior pass SHA record, explicitly labelled.
Does not delete any archived or source file.
"""
import os,json,hashlib,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
R=Path(__file__).resolve().parents[1];A=Path('E:/CHESHIRE_DATA/archives/SOL_HANDOFF_20261010')
old={}
for line in (A/'files_verified.jsonl').read_text(encoding='utf8').splitlines():
 try:r=json.loads(line);old[r['source']]=r
 except (ValueError,KeyError):pass
previous=json.loads((A/'preservation_status.json').read_text(encoding='utf8'))
errors=[];tasks=[]
for root,label in [(R,'workspace'),(Path('C:/Users/USER/CHESHIRE_ASTRA'),'dependencies/CHESHIRE_ASTRA'),(Path('C:/Users/USER/Libraries/HDMola'),'dependencies/HDMola')]:
 for parent,dirs,files in os.walk(root,onerror=lambda e:errors.append(dict(path=e.filename,error=str(e)))):
  dirs[:]=[x for x in dirs if x not in ['.git','__pycache__','.pytest_cache']]
  for name in files:
   src=Path(parent)/name
   if name in ['sol_preservation.log','archive_finalize.log']:continue
   tasks.append((src,A/label/src.relative_to(root)))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as fp:
  for c in iter(lambda:fp.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def refresh(pair):
 src,dst=pair
 try:
  s=src.stat();prior=old.get(str(src))
  if prior and dst.exists() and dst.stat().st_size==s.st_size==prior['bytes'] and dst.stat().st_mtime_ns==s.st_mtime_ns:
   return {**prior,'verification':'prior full SHA256 pass; source/archive size and mtime unchanged'}
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);x=sha(src);assert x==sha(dst)
  return dict(source=str(src),archive=str(dst),bytes=s.st_size,sha256=x,verification='new full SHA256 check')
 except Exception as e:return dict(path=str(src),error=str(e))
rows=[]
with ThreadPoolExecutor(max_workers=12) as pool:
 for rec in pool.map(refresh,tasks):
  if 'error' in rec:errors.append(rec)
  else:rows.append(rec)
# References from first pass remain independently preserved.
present={x['source'] for x in rows}
rows.extend(x for k,x in old.items() if k not in present and '/Downloads/' in k.replace('\\','/'))
with (A/'files_verified_final.jsonl').open('w',encoding='utf8') as fp:
 for rec in rows:fp.write(json.dumps(rec,ensure_ascii=False)+'\n')
status=dict(verified_files=len(rows),verified_bytes=sum(x['bytes'] for x in rows),new_full_hash_checks=sum(x.get('verification')=='new full SHA256 check' for x in rows),errors=errors,previous_pass_errors=previous['errors'],policy='Base pass SHA256 plus metadata-unchanged retention; new/changed files SHA256 verified. E research indexed in place, not duplicated.')
(A/'preservation_final_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in status.items() if k not in ['errors','previous_pass_errors']}),flush=True);print('errors',len(errors),flush=True)
