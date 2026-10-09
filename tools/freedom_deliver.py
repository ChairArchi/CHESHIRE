"""Exact native exports and world-plane evidence, including labelled invalid studies.

No repair, coordinate normalization, aesthetic pass, or complete solid claim.
Only fresh E:/CHESHIRE_DATA/astra_freedom/deliverables/<tag> is written.
"""
import argparse,datetime,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task29_search import load_mesh
from task36_contacts import contacts
from task32_validation import embedding
from cheshire.astra_validation import embedding_failures
from astra_deliver import exact_symmetry
from astra_evaluate import render,cut_picture
from hero_design_sprint import guarded,windows_memory
ROOT=Path('E:/CHESHIRE_DATA/astra_freedom/deliverables')
EXCLUSIONS='Transverse checker excludes coplanar overlaps, tangency and boundary-only contact. Cap reached is a lower bound, not the total intersections. No 2D section-intersection inspection is performed. Neither zero checked contacts nor closed manifold topology certifies a complete solid. Symmetry is measured, not imposed. Artistic success is not automatically assessed.'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf8')


def verify_sources(root):
    identity=json.loads((root/'source_identity.json').read_text())
    mismatches=[rel for rel,value in identity.items() if sha(REPO/rel)!=value]
    if mismatches:raise RuntimeError('Export validation source changed: '+','.join(mismatches))


def export_obj(mesh,path,status):
    with path.open('w',encoding='ascii',newline='\n') as f:
        f.write('# CHESHIRE FREEDOM STATUS: '+status+'\n')
        f.write('# Exact native coordinates; no repair. '+EXCLUSIONS+'\n')
        for p in mesh.xyz:f.write('v '+' '.join(format(float(v),'.17g') for v in p)+'\n')
        for tri in mesh.faces[:,:3]:f.write('f '+' '.join(str(int(v)+1) for v in tri)+'\n')
    nv=nf=0
    with path.open(encoding='ascii') as f:
        for line in f:
            if line.startswith('v '):
                if nv>=len(mesh.xyz) or not np.array_equal(np.array(list(map(float,line.split()[1:]))),mesh.xyz[nv]):raise ValueError('OBJ vertex roundtrip mismatch')
                nv+=1
            elif line.startswith('f '):
                if nf>=len(mesh.faces) or not np.array_equal(np.array(list(map(int,line.split()[1:])))-1,mesh.faces[nf,:3]):raise ValueError('OBJ face roundtrip mismatch')
                nf+=1
    if (nv,nf)!=(len(mesh.xyz),len(mesh.faces)):raise ValueError('OBJ roundtrip counts differ')
    return dict(vertices=nv,triangles=nf,exact_roundtrip=True,sha256=sha(path))


def world_cuts(mesh,dest,label):
    import trimesh
    model=trimesh.Trimesh(vertices=mesh.xyz,faces=mesh.faces[:,:3],process=False)
    planes=[('Z'+str(z),[0,0,z+.12345],[0,0,1]) for z in range(500,3501,250)]
    planes += [('XZ',[0,0,0],[0,1,0]),('YZ',[0,0,0],[1,0,0]),('DIAGONAL',[0,0,0],[1,-1,0])]
    raw={};records=[]
    for name,origin,normal in planes:
        segments,ids=trimesh.intersections.mesh_plane(model,normal,origin,return_faces=True)
        if not np.isfinite(segments).all():raise ValueError('Nonfinite native world-plane section')
        raw[name]=segments;raw[name+'_triangle_ids']=ids
        records.append(dict(name=name,origin=origin,normal=normal,segments=len(segments),triangle_id_domain='Rows of native_mesh.npz faces, identical to OBJ face order',two_dimensional_intersection_check='NOT_PERFORMED'))
    path=dest/'world_cuts.npz';np.savez_compressed(path,**raw)
    cut_picture(raw,label,dest)
    return dict(path=path.name,sha256=sha(path),planes=records,figure=label+'_cuts.png',plot_axes='Shared fixed XY[-1800,1800]^2; longitudinal horizontal[-2500,2500], Z[-500,4500]. No per-candidate normalization.',limitations='Actual world-plane sections of native triangles, not construction-chart curves. Coplanar triangle and exact boundary conventions follow trimesh.mesh_plane. Raw segments retained without welding or curve reconstruction. No quadratic 2D intersection test.')


def run(root,items):
    import pyrender
    from PIL import Image
    verify_sources(root);renderer=pyrender.OffscreenRenderer(600,600)
    records=[];pictures=[]
    try:
        for item in items:
            start=perf_counter();label=item['id'];stage=Path(item['stage']).resolve()
            dest=root/label;dest.mkdir(exist_ok=False)
            source=stage/'mesh.npz';source_hash=sha(source)
            shutil.copy2(source,dest/'native_mesh.npz')
            if sha(dest/'native_mesh.npz')!=source_hash:raise ValueError('Native copy hash mismatch')
            m=load_mesh(dest/'native_mesh.npz')
            generation=re.search(r'_G([0-9]+)$',label)
            stage_generation=re.match(r'G([0-9]+)(?:_|$)',stage.name)
            if generation is None or int(generation[1])!=m.generation:raise ValueError('ID/native generation mismatch')
            if stage_generation and int(stage_generation[1])!=m.generation:raise ValueError('Stage/native generation mismatch')
            if not np.isfinite(m.xyz).all() or not np.all((m.faces>=0).sum(1)==3):raise ValueError('Finite authoritative native triangles required')
            if np.any(m.faces[:,:3]<0) or np.any(m.faces[:,:3]>=len(m.xyz)):raise ValueError('Invalid triangle vertex index')
            memory=windows_memory();forecast=512*1024**2+len(m.faces)*2400
            if memory['status']!='MEASURED' or forecast>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Measured export reserve insufficient')
            checks=contacts(m,cap=1024,interval=True,include_shared=True)
            try:
                emb=embedding(m);failures=embedding_failures(emb,item.get('expected_euler',2))
            except ValueError as error:
                emb=dict(error=str(error));failures=['EMBEDDING_EXCEPTION']
            symmetry=exact_symmetry(m)
            if checks['transverse_contacts']:failures.append('TRANSVERSE_CONTACTS')
            if not checks['all_triangles_sampled']:failures.append('INCOMPLETE_CONTACT_COVERAGE')
            status='INVALID' if failures else 'TRANSVERSE_AND_EMBEDDING_CHECKS_PASSED'
            suffix='INVALID' if failures else 'CHECKS_PASSED'
            obj=dest/(label+'_'+suffix+'.obj');obj_info=export_obj(m,obj,status)
            cut_info=world_cuts(m,dest,label)
            warning=' INVALID' if failures else ' CHECKS PASSED; NO SOLID CERTIFICATE'
            pictures.extend(render(m,dest,label,renderer,[0,0,2000],5000,warning))
            render(m,dest,label+'_detail',renderer,[0,0,1000],1800,warning)
            lineage={}
            for name in ['completed.json','numerical_failure.json','failed.json']:
                p=stage.parent/name
                if p.exists():lineage[name]=dict(path=str(p),sha256=sha(p),record=json.loads(p.read_text(encoding='utf8')))
            upstream={name:dict(path=str(stage/name),sha256=sha(stage/name)) for name in ['operator_state.npz','operator_mesh.npz','summary.json','validation.json'] if (stage/name).exists()}
            if sha(source)!=source_hash:raise RuntimeError('Original native mesh changed during export')
            report=dict(id=label,stage=str(stage),generation=m.generation,native_sha256=source_hash,status=status,invalid_reasons=failures,obj=dict(path=obj.name,**obj_info),contacts=checks,embedding=emb,symmetry=symmetry,symmetry_policy='Measured only; lack of reflection or quarter-turn symmetry does not reject freedom research.',world_cuts=cut_info,producer_lineage=lineage,upstream=upstream,camera=dict(target=[0,0,2000],width=5000,pixels=600,detail_target=[0,0,1000],detail_width=1800,smooth_shading=False,front=[0,0],oblique=[28,22],side=[90,0]),source_identity_sha256=sha(root/'source_identity.json'),validation_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),forecast_bytes=forecast,available_memory=memory,seconds=perf_counter()-start,limitations=EXCLUSIONS,aesthetic_success='NOT_AUTOMATICALLY_ASSESSED')
            report['artifacts']={p.name:sha(p) for p in dest.iterdir() if p.is_file()}
            write(dest/'exchange.json',report);records.append(report);write(root/'summary.json',records)
            print(label,status,'contacts',checks['transverse_contacts'],'triangles',len(m.faces),'seconds',round(report['seconds'],2),flush=True)
    finally:renderer.delete()
    sheet=Image.new('RGB',(1800,600*len(items)),'white')
    for i,im in enumerate(pictures):sheet.paste(im,((i%3)*600,(i//3)*600))
    sheet.save(root/'comparison.png');verify_sources(root)
    write(root/'completed.json',dict(complete=True,candidates=len(records),invalid=sum(r['status']=='INVALID' for r in records),exact_obj_roundtrips=all(r['obj']['exact_roundtrip'] for r in records),comparison_sha256=sha(root/'comparison.png'),limitations=EXCLUSIONS))


def main():
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.tag.replace('_','').isalnum():raise ValueError('Safe fresh tag required')
    root=ROOT/a.tag
    if a.worker:run(root,json.loads((root/'request.json').read_text()));return
    items=json.loads(sys.stdin.read() if a.request=='-' else Path(a.request).read_text(encoding='utf-8-sig'))
    if not isinstance(items,list) or not items:raise ValueError('Nonempty list of {id,stage} required')
    labels=[i['id'] for i in items]
    if len(set(labels))!=len(labels) or any(not re.fullmatch(r'[A-Za-z0-9_]+_G[0-9]+',label) for label in labels):raise ValueError('Unique safe labels ending _G<n> required')
    estimates=[]
    for item in items:
        path=Path(item['stage'])/'mesh.npz'
        with np.load(path) as z:estimates.append(512*1024**2+len(z['faces'])*2400)
    memory=windows_memory()
    if memory['status']!='MEASURED' or max(estimates)>min(12*1024**3,.55*memory['available_bytes']):raise MemoryError('Measured export preflight reserve insufficient')
    root.mkdir(parents=True,exist_ok=False);write(root/'request.json',items);write(root/'preflight.json',dict(forecast_bytes=max(estimates),memory=memory))
    sourcefiles=['tools/freedom_deliver.py','tools/astra_deliver.py','tools/astra_evaluate.py','tools/task32_validation.py','tools/task36_contacts.py','tools/task36_triangle_interval.py','tools/task33_contacts.py','tools/task36_evidence.py','tools/native/Task36Bounds.cs','src/cheshire/astra_validation.py','src/cheshire/reference_subdivision.py','src/cheshire/task32_morphology.py','examples/task29_search.py','examples/hero_design_sprint.py','tools/progressive_gate_views.py']
    identity={}
    for rel in sourcefiles:
        source=REPO/rel;dest=root/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);identity[rel]=sha(dest)
    write(root/'source_identity.json',identity)
    write(root/'revision.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),python=sys.version,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    result=guarded(['--request',str(root/'request.json'),'--tag',a.tag,'--worker'],root/'logs/run',worker_script=Path(__file__))
    write(root/'execution.json',result)
    if result['exit_code']:raise SystemExit(result['exit_code'])
if __name__=='__main__':main()
