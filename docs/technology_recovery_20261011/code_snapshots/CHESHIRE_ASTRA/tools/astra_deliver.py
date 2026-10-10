"""Verified exchange artifact; geometric checks are not aesthetic approval."""
import argparse,json,sys,hashlib,datetime,subprocess
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task36_contacts import contacts
from task32_validation import embedding
from cheshire.astra_validation import embedding_failures
from task36_evidence import cycles

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def exact_symmetry(mesh):
    tree=cKDTree(mesh.xyz);original=cycles(mesh.faces[:,:3]);out={}
    transforms=[('X',np.diag([-1,1,1])),('Y',np.diag([1,-1,1])),('QUARTER_TURN',np.array([[0,-1,0],[1,0,0],[0,0,1]]))]
    for name,matrix in transforms:
        distance,ids=tree.query(mesh.xyz@matrix.T);mapped=ids[mesh.faces[:,:3]]
        if np.linalg.det(matrix)<0:mapped=mapped[:,[0,2,1]]
        out[name]=dict(max_distance=float(distance.max()),bijective=len(np.unique(ids))==len(ids),oriented_cycle_failures=int(np.any(cycles(mapped)!=original,axis=1).sum()))
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--tag',required=True);a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required.')
    root=Path('E:/CHESHIRE_DATA/astra_research/deliverables')/a.tag;root.mkdir(parents=True,exist_ok=False)
    m=load_mesh(a.stage)
    if not np.isfinite(m.xyz).all() or not np.all((m.faces>=0).sum(1)==3):raise ValueError('Finite authoritative triangles required.')
    check=contacts(m,cap=1024,interval=True,include_shared=True);embed=embedding(m);sym=exact_symmetry(m)
    producer=a.stage.parent
    lineage={name:json.loads((producer/name).read_text()) for name in ['completed.json','failed.json'] if (producer/name).exists()}
    validator_sources={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),REPO/'src/cheshire/astra_validation.py',REPO/'tools/task32_validation.py',REPO/'tools/task36_contacts.py',REPO/'tools/task36_triangle_interval.py',REPO/'tools/native/Task36Bounds.cs']}
    report=dict(validation_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),validator_sources=validator_sources,producer_lineage=lineage,stage=str(a.stage.resolve()),native_sha256=sha(a.stage/'mesh.npz'),contacts=check,embedding=embed,symmetry=sym,exclusions='Coplanar/tangent/boundary-only contacts excluded; zero is not complete solid certification. No artistic success implied.')
    (root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    if check['transverse_contacts'] or not check['all_triangles_sampled'] or any(v['max_distance']>1e-8 or not v['bijective'] or v['oriented_cycle_failures'] for v in sym.values()):raise ValueError('Validation failed; no OBJ.')
    failures=embedding_failures(embed)
    if failures:raise ValueError('Embedding policy failed; no OBJ: '+','.join(failures))
    dest=root/(a.tag+'.obj')
    with dest.open('w',encoding='ascii',newline='\n') as f:
        f.write('# CHESHIRE independent research; geometry checks passed within documented exclusions\n')
        for xyz in m.xyz:f.write('v '+' '.join(format(float(v),'.17g') for v in xyz)+'\n')
        for tri in m.faces[:,:3]:f.write('f '+' '.join(str(int(v)+1) for v in tri)+'\n')
    nv=nf=0
    with dest.open(encoding='ascii') as f:
        for line in f:
            if line.startswith('v '):
                if not np.array_equal(np.array(list(map(float,line.split()[1:]))),m.xyz[nv]):raise ValueError('Vertex roundtrip failed.')
                nv+=1
            elif line.startswith('f '):
                if not np.array_equal(np.array(list(map(int,line.split()[1:])))-1,m.faces[nf,:3]):raise ValueError('Face roundtrip failed.')
                nf+=1
    if (nv,nf)!=(len(m.xyz),len(m.faces)):raise ValueError('OBJ counts differ.')
    report.update(obj=str(dest),obj_sha256=sha(dest),vertices=nv,triangles=nf,exact_roundtrip=True)
    (root/'exchange.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(dest)
if __name__=='__main__':main()
