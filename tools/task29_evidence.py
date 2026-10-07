"""Saved lineage, exact regeneration, exports and ancestry diagnostics."""
import argparse,json,shutil,sys,gc
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from task29_search import ROOT,load_mesh,cube,subdivide
from cheshire.reference_subdivision import topology,fields
from cross_cell_crease_study import read,write,file_hash


def lineage(final):
    result=[];p=Path(final)
    while p:
        result.append(p);parent=read(p/'summary.json').get('parent');p=Path(parent) if parent else None
    result.reverse()
    if [load_mesh(p).generation for p in result]!=list(range(len(result))):raise ValueError('Broken actual lineage.')
    return result


def select(final,definition):
    stages=lineage(final);manifest=[]
    for g,p in enumerate(stages):
        d=ROOT/'lead'/f'G{g}'
        if d.exists():raise ValueError('Preserve selected real stages.')
        shutil.copytree(p,d)
        manifest.append(dict(generation=g,actual_source=str(p),source_mesh_sha256=file_hash(p/'mesh.npz'),lead_mesh_sha256=file_hash(d/'mesh.npz')))
    write(ROOT/'lead/lineage_manifest.json',dict(stages=manifest,selection='Actual saved geometry copied without substitution or reconstruction. Parent chains retain their original source paths.'))
    write(ROOT/'definitions/selected_nonstationary_schedule.json',read(definition))
    print('Selected actual lead',final,flush=True)


def obj_save_verify(m,path):
    with path.open('w',encoding='ascii',newline='\n') as out:
        out.write('# Task29 actual double precision checkpoint; unresolved units\n')
        for p in m.xyz:out.write('v '+' '.join(format(float(v),'.17g') for v in p)+'\n')
        for q in m.faces:out.write('f '+' '.join(str(int(v)+1) for v in q if v>=0)+'\n')
    vcount=fcount=0
    with path.open() as src:
        for line in src:
            s=line.split()
            if not s:continue
            if s[0]=='v':
                if not np.array_equal(np.array(list(map(float,s[1:]))),m.xyz[vcount]):raise ValueError('OBJ XYZ changed.')
                vcount+=1
            if s[0]=='f':
                if [int(v)-1 for v in s[1:]]!=[int(v) for v in m.faces[fcount] if v>=0]:raise ValueError('OBJ oriented face changed.')
                fcount+=1
    if (vcount,fcount)!=(len(m.xyz),len(m.faces)):raise ValueError('OBJ count changed.')
    return dict(path=str(path),vertices=vcount,faces=fcount,exact_XYZ=True,exact_oriented_faces=True,sha256=file_hash(path))


def verify_export():
    definition=read(ROOT/'definitions/selected_nonstationary_schedule.json');m=cube();records=[];start=perf_counter()
    for g in range(len(definition['rows'])+1):
        d=ROOT/'lead'/f'G{g}';saved=load_mesh(d)
        if g:
            m,meta,state=subdivide(m,definition['rows'][g-1],scale_mode=definition['scale'],intrinsic=definition.get('intrinsic'))
            if definition.get('topology') and g==definition['topology']['generation']:
                from task29_topology import weld
                m,log=weld(m,definition['topology'])
                if log!=read(d/'summary.json')['metadata']['topology']:raise ValueError('Topology log replay changed.')
            with np.load(d/'operator_state.npz') as actual:
                for k,v in state.items():
                    if not np.array_equal(v,actual[k]):raise ValueError('Resolved operator/intrinsic state changed: '+k)
        for k in ['xyz','faces','classes','rest','anchors']:
            if not np.array_equal(getattr(m,k),getattr(saved,k)):raise ValueError(f'Exact deterministic {k} replay changed G{g}')
        obj=obj_save_verify(saved,d/f'G{g}.obj')
        records.append(dict(generation=g,exact_geometry=True,exact_faces=True,exact_origins_rest_ancestry=True,exact_resolved_operator_state=True,OBJ=obj))
        print('Exact full regeneration and OBJ G'+str(g),'PASS',flush=True);del saved;gc.collect()
    g=len(definition['rows']);ROOT.joinpath('dcc').mkdir(exist_ok=True)
    shutil.copy2(ROOT/f'lead/G{g}/G{g}.obj',ROOT/'dcc/TASK29_LEAD.obj')
    # Actual reload of penultimate checkpoint independently exercises continuation.
    prior=load_mesh(ROOT/f'lead/G{g-1}');continued,_,_=subdivide(prior,definition['rows'][-1],scale_mode=definition['scale'],intrinsic=definition.get('intrinsic'))
    if definition.get('topology') and g==definition['topology']['generation']:
        from task29_topology import weld
        continued,_=weld(continued,definition['topology'])
    assert np.array_equal(continued.xyz,m.xyz) and np.array_equal(continued.faces,m.faces)
    write(ROOT/'analysis/geometry_validation.json',dict(records=records,exact_G0_to_final_regeneration=True,actual_checkpoint_continuation=True,seconds=perf_counter()-start,definition_sha256=file_hash(ROOT/'definitions/selected_nonstationary_schedule.json')))


def retention(paths,out):
    result=[]
    for final in paths:
        stages=lineage(final);ms={load_mesh(p).generation:load_mesh(p) for p in stages}
        curves=[];cached={g:fields(m) for g,m in ms.items()}
        for birth in [1,2,3]:
            ref=ms[birth];rf=cached[birth];t=topology(ref)
            # Diagnostic patches selected by actual normal disagreement of incident
            # faces, with ties by ID for reproducibility, never generation drivers.
            normals=rf['nf'];scores=1-np.linalg.norm(normals[t['ef']].mean(1),axis=1)
            face_scores=np.zeros(len(ref.faces));np.maximum.at(face_scores,t['ef'].ravel(),np.repeat(scores,2))
            chosen=np.argsort(-face_scores,kind='stable')[:3]
            for anchor in chosen:
                normal=normals[anchor];center=rf['c'][anchor];samples=[]
                for g in range(birth,max(ms)+1):
                    m=ms[g];mask=m.anchors[:,birth-1]==anchor
                    if not mask.any():raise ValueError('Diagnostic ancestry disappeared.')
                    ids=np.unique(m.faces[mask]);ids=ids[ids>=0];p=m.xyz[ids]
                    depth=(p-center)@normal;nf=cached[g]['nf'][mask]
                    samples.append(dict(generation=g,descendant_faces=int(mask.sum()),depth_range=float(np.ptp(depth)),depth_RMS=float(np.sqrt((depth**2).mean())),
                        normal_variation=float(1-np.linalg.norm(nf.mean(0))),patch_extent=np.ptp(p,axis=0).tolist()))
                curves.append(dict(birth=birth,ancestor_face=int(anchor),reference_normal=normal.tolist(),reference_center=center.tolist(),samples=samples))
        result.append(dict(final=str(final),curves=curves,macro_extent_curve=[dict(generation=g,extent=np.ptp(m.xyz,axis=0).tolist()) for g,m in ms.items()]))
        print('Retention',final,flush=True)
    write(out,dict(results=result,definition='Three actual high-normal-disagreement face patches per G1/G2/G3. Descendants identified by saved anchors. Depth range/RMS measured along fixed birth face normal about birth centroid; normal variation of descendant normals. Diagnostic proxies, not proof of named ridge identity. Visual progression is decisive.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--select',type=Path);p.add_argument('--definition',type=Path);p.add_argument('--verify-export',action='store_true');p.add_argument('--retention',nargs='+',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    if a.select:select(a.select,a.definition)
    if a.verify_export:verify_export()
    if a.retention:retention(a.retention,a.out)
