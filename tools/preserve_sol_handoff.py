"""Read-only source inventory and non-destructive verified archival copy.
Only cache/.git directories are excluded. Git history is preserved separately as bundle.
Existing E research stays in place and is inventoried, not claimed as duplicated.
"""
import argparse,os,json,hashlib,shutil,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--external-inventory',action='store_true');a=p.parse_args()
R=Path('C:/Users/USER/CHESHIRE');A=Path(a.archive);A.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
errors=[];excluded=[];count=0;total=0
roots=[(R,'workspace'),(Path('C:/Users/USER/CHESHIRE_ASTRA'),'dependencies/CHESHIRE_ASTRA'),(Path('C:/Users/USER/Libraries/HDMola'),'dependencies/HDMola')]
tasks=[]
for root,label in roots:
 if not root.exists():errors.append(dict(path=str(root),error='Missing dependency root'));continue
 for parent,dirs,files in os.walk(root,onerror=lambda e:errors.append(dict(path=e.filename,error=str(e)))):
  for d in list(dirs):
   if d in ['.git','__pycache__','.pytest_cache']:
    excluded.append(str(Path(parent)/d));dirs.remove(d)
  for name in files:
   src=Path(parent)/name
   if src==R/'outputs/sol_preservation.log':continue
   tasks.append((src,A/label/src.relative_to(root)))
def copy_one(pair):
 src,dst=pair
 try:
  st=src.stat();dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists() or dst.stat().st_size!=st.st_size or dst.stat().st_mtime_ns!=st.st_mtime_ns:shutil.copy2(src,dst)
  x=sha(src);y=sha(dst)
  if x!=y:raise ValueError('SHA256 mismatch')
  return dict(source=str(src),archive=str(dst),bytes=st.st_size,sha256=x)
 except Exception as e:return dict(path=str(src),error=str(e))
with (A/'files_verified.jsonl').open('w',encoding='utf8') as manifest:
 with ThreadPoolExecutor(max_workers=12) as pool:
  for item in pool.map(copy_one,tasks):
   if 'error' in item:errors.append(item);continue
   manifest.write(json.dumps(item,ensure_ascii=False)+'\n');count+=1;total+=item['bytes']
   if count%3000==0:print(count,total,flush=True)
 # References supplied by user; do not substitute unidentified web copies.
 for name in ['075-081 (1).pdf','mirror.pdf','User attachment.png']:
  src=Path('C:/Users/USER/Downloads')/name;dst=A/'references'/name
  try:
   dst.parent.mkdir(exist_ok=True);shutil.copy2(src,dst);x=sha(src);assert x==sha(dst)
   manifest.write(json.dumps(dict(source=str(src),archive=str(dst),bytes=src.stat().st_size,sha256=x))+'\n')
  except Exception as e:errors.append(dict(path=str(src),error=str(e)))
if a.external_inventory:
 with (A/'external_inventory.jsonl').open('w',encoding='utf8') as out:
  for parent,dirs,files in os.walk('E:/CHESHIRE_DATA',onerror=lambda e:errors.append(dict(path=e.filename,error=str(e)))):
   dirs[:]=[d for d in dirs if (Path(parent)/d).resolve()!=A.resolve() and d not in ['.git','__pycache__','.venv']]
   for name in files:
    q=Path(parent)/name
    try:s=q.stat();out.write(json.dumps(dict(path=str(q),bytes=s.st_size,mtime_ns=s.st_mtime_ns,status='existing in place; not copied by this archive'))+'\n')
    except Exception as e:errors.append(dict(path=str(q),error=str(e)))
report=dict(verified_files=count,verified_bytes=total,errors=errors,excluded_cache_and_git=excluded,external_policy='Existing E research inventoried in place. Git bundle separate. Virtualenv copied as local recovery aid; not portable.',completed=time.strftime('%Y-%m-%dT%H:%M:%S'))
(A/'preservation_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['errors','excluded_cache_and_git']}),flush=True)
print('errors',len(errors),flush=True)
