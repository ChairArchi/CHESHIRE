"""Independent CSG/CC2 ancestry QA and unchanged float64 native-PLY export."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import time

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

HERE=Path(__file__).resolve().parent
PLY_HELPER=HERE.parent/'early_dynamic_variations_20261016/native_export_and_qa_v3.py'
SCHEMA='CHESHIRE_NEW_STRUCTURAL_GRAMMAR_V1'
CHUNK=131072


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def record(path):return dict(path=str(Path(path).resolve()),sha256=sha(path))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def checked(path,digest):
    if sha(path)!=digest:raise ValueError('Bound structural artifact changed: '+str(path))
    return Path(path)
def geometry(path):
    with np.load(path,allow_pickle=False) as z:return z['xyz'],z['faces']


def quality(x,t):
    if x.ndim!=2 or x.shape[1]!=3 or t.ndim!=2 or t.shape[1]!=3 or not len(t):raise ValueError('Actual triangular surface required')
    if not np.isfinite(x).all() or t.min()<0 or t.max()>=len(x):raise ValueError('Invalid structural native coordinates/indices')
    minimum=float('inf');area=0.
    for begin in range(0,len(t),CHUNK):
        p=x[t[begin:begin+CHUNK]];a=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2
        minimum=min(minimum,float(a.min()));area+=float(a.sum())
    a=t.ravel();b=np.roll(t,-1,axis=1).ravel();keys=np.minimum(a,b).astype(np.uint64)*np.uint64(len(x))+np.maximum(a,b).astype(np.uint64)
    order=np.argsort(keys);keys=keys[order];starts=np.r_[0,np.flatnonzero(np.diff(keys))+1];counts=np.diff(np.r_[starts,len(keys)])
    sums=np.add.reduceat((a[order]>b[order]).astype(np.int64),starts);unique=keys[starts]
    graph=csr_matrix((np.ones(len(unique),np.uint8),((unique//len(x)).astype(np.int64),(unique%len(x)).astype(np.int64))),shape=(len(x),len(x)))
    components=int(connected_components(graph,directed=False,return_labels=False));orphan=len(x)-len(np.unique(t));chi=len(x)-len(unique)+len(t)
    passed=bool(components==1 and orphan==0 and chi==2 and np.all(counts==2) and np.all(sums==1) and minimum>0)
    result=dict(passed=passed,vertices=len(x),triangles=len(t),edges=len(unique),components=components,orphan_vertices=orphan,
        Euler_characteristic=int(chi),closed_genus=0 if passed else None,boundary_edges=int((counts==1).sum()),nonmanifold_edges=int((counts>2).sum()),
        inconsistent_oriented_edges=int(((counts==2)&(sums!=1)).sum()),minimum_triangle_area=minimum,surface_area=area,finite=True,
        self_intersection_certified=False,fabrication_certified=False)
    if not passed:raise ValueError('Independent closed genus-zero QA failed: '+str(result))
    return result


def inspect(folder,receipt):
    design=receipt.get('design',{})
    seed_flags=[design[k] for k in ('old_seed_used','original_column_geometry_used') if k in design]
    if receipt.get('old_column_geometry_read') is not False or not seed_flags or any(v is not False for v in seed_flags):raise ValueError('New-grammar/no-old-seed declarations are required')
    if receipt.get('late_ornament_added') is not False:raise ValueError('Initial structure study cannot silently include late ornament')
    sources=[]
    markers=('generation_mirror_hybrid','parent_nested_folds','whole_cc1_prototype','structural_tissue_rebuild','column_synthesis_20261016')
    for original,digest in receipt['source_bindings'].items():
        current=checked(original,digest);snapshot=checked(folder/'source_snapshot'/current.name,digest)
        # A bounded static check of the actual new generator/driver code, not
        # a general filesystem tracing or software-sandbox certificate.
        text=current.read_text(encoding='utf-8-sig')
        hits=[m for m in markers if m in text]
        if current.parent==HERE and hits:raise ValueError('New grammar source references a previous column asset family: '+str(hits))
        sources.append(dict(current=record(current),snapshot=record(snapshot),previous_column_asset_marker_hits=hits))
    components=[]
    for i,row in enumerate(receipt['components']):
        if row['index']!=i:raise ValueError('Component index ordering differs')
        p=checked(row['geometry'],row['sha256']);x,t=geometry(p)
        components.append(dict(index=i,name=row['name'],role=row.get('role'),level=row.get('level'),geometry=record(p),quality=quality(x,t)))
    g0=folder/'G00_CSG';x0,t0=geometry(g0/'geometry.npz');q0=quality(x0,t0);parts=np.load(g0/'triangle_parts.npy',allow_pickle=False)
    if parts.shape!=(len(t0),) or parts.dtype.kind not in 'iu' or parts.min()<0 or parts.max()>=len(components):raise ValueError('Actual CSG source-part lineage differs')
    if receipt['actual_CSG']['actual_output_triangles']!=len(t0) or receipt['actual_CSG']['source_parts']!=len(components):raise ValueError('Actual CSG count binding differs')
    gp=checked(receipt['final_geometry'],receipt['final_geometry_sha256']);cp=checked(receipt['final_controls'],receipt['final_controls_sha256']);x,t=geometry(gp)
    with np.load(cp,allow_pickle=False) as z:v=z['xyz'];q=z['faces'];generation=int(z['generation'])
    if generation!=2 or q.ndim!=2 or q.shape[1]!=4 or len(x)!=len(v)+len(q) or len(t)!=4*len(q):raise ValueError('Actual CC2 mean-native fan dimensions differ')
    if not np.array_equal(x[:len(v)],v):raise ValueError('Native retained controls differ')
    for begin in range(0,len(q),CHUNK):
        end=min(begin+CHUNK,len(q));ids=np.arange(begin,end);quad=q[begin:end]
        centres=v[quad].mean(axis=1)
        if not np.array_equal(x[len(v)+ids],centres):raise ValueError('Actual native face centres differ from exact control means')
        expected=np.stack((quad,np.roll(quad,-1,axis=1),np.broadcast_to((len(v)+ids)[:,None],quad.shape)),axis=2).reshape(-1,3)
        if not np.array_equal(t[4*begin:4*end],expected):raise ValueError('Native triangle order/winding differs from four exact control fans')
    p1=np.load(folder/'G01_actual_parent_face.npy',allow_pickle=False);p2=np.load(folder/'G02_actual_parent_face.npy',allow_pickle=False)
    parent_path=folder/'G02_CC/parent_CSG_face.npy';parent=np.load(parent_path,allow_pickle=False)
    if p1.shape!=(3*len(t0),) or p2.shape!=(len(q),) or parent.shape!=(len(q),):raise ValueError('Actual triangle->CC1->CC2 ancestry counts differ')
    if not np.array_equal(p1,np.repeat(np.arange(len(t0)),3)) or not np.array_equal(p2,np.repeat(np.arange(len(p1)),4)):raise ValueError('Actual recorded CC child-parent ordering differs')
    if not np.array_equal(parent,p1[p2]):raise ValueError('Final CSG parent does not equal the two actual composed parent maps')
    tags_path=checked(receipt['actual_native_color_tags'],receipt['color_tags_sha256']);tags=np.load(tags_path,allow_pickle=False)
    if not np.array_equal(tags,np.repeat(parts[parent],4)):raise ValueError('Native structural colors do not match actual source-part ancestry')
    final_quality=quality(x,t)
    result=dict(id=receipt['id'],source_receipt=record(folder/'RECEIPT.json'),source_bindings=sources,components=components,
        actual_G00_geometry=record(g0/'geometry.npz'),actual_G00_quality=q0,actual_G02_geometry=record(gp),actual_G02_controls=record(cp),quality=final_quality,
        native_four_fans_exact=True,native_controls_and_means_exact=True,actual_CC_parent_composition_exact=True,native_part_colors_exact=True,
        lineage_files=[record(p) for p in (folder/'G01_actual_parent_face.npy',folder/'G02_actual_parent_face.npy',parent_path,g0/'triangle_parts.npy',tags_path)],
        source_component_counts=np.bincount(parts,minlength=len(components)).tolist(),native_component_counts=np.bincount(tags,minlength=len(components)).tolist(),
        physical_extent=np.ptp(x,axis=0).tolist(),old_column_geometry_read=False,old_seed_declaration_verified=True,
        no_old_seed_verification_scope='Actual source/current+snapshot hashes, new primitive components and bounded source-text inspection; not general filesystem instrumentation.',
        late_ornament_added=False,user_adopted=False,aesthetic_success_claimed=False,self_intersection_or_fabrication_certified=False)
    return result,x,t


def main(a):
    start=time.perf_counter();rows={}
    for p in sorted(a.root.rglob('RECEIPT.json')):
        data=read(p)
        if data.get('status')!='PASS':continue
        if data.get('schema')!=SCHEMA:
            if data.get('schema','').startswith('CHESHIRE_NEW_STRUCTURAL_GRAMMAR'):raise ValueError('Unsupported completed structural schema')
            continue
        sid=data['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',sid):raise ValueError('Unsafe grammar identifier')
        if sid in rows:raise ValueError('Multiple completed producers for '+sid)
        rows[sid]=(p,data)
    if not rows:raise ValueError('No completed new structural grammar')
    if a.expected_count is not None and len(rows)!=a.expected_count:raise ValueError('Completed grammar count differs from expected')
    helper=importlib.util.spec_from_file_location('structural_float64_PLY_helper',PLY_HELPER);module=importlib.util.module_from_spec(helper);helper.loader.exec_module(module)
    if not a.inspect_only:
        if a.output is None:raise ValueError('--output is required for export')
        a.output.mkdir(parents=True,exist_ok=False);snap=a.output/'source_snapshot';snap.mkdir()
        for p in (Path(__file__),PLY_HELPER):shutil.copyfile(p,snap/p.name)
    output=[]
    for sid,(path,data) in sorted(rows.items()):
        row,x,t=inspect(path.parent,data)
        if not a.inspect_only:
            target=a.output/sid;target.mkdir();row['model']=module.export_ply(target/(sid+'_CC2_NATIVE_FULL.ply'),x,t)
            write(target/'EXPORT_RECEIPT.json',row)
        output.append(row);print('STRUCTURAL_NATIVE_QA_PASS',sid,len(x),len(t),row['quality']['minimum_triangle_area'],flush=True)
    result=dict(schema='CHESHIRE_NEW_STRUCTURAL_GRAMMAR_EXPORT_QA_V1',passed=True,completed_count=len(output),variants=output,
        source=record(__file__),PLY_export_helper=record(PLY_HELPER),inspection_only=a.inspect_only,
        all_exported_geometry_full_readback_exact=not a.inspect_only,actual_new_macro_CSG_and_CC2=True,previous_26_variants_are_not_this_model=True,
        self_intersection_or_manufacturing_certificate=False,elapsed_seconds=time.perf_counter()-start)
    if not a.inspect_only:write(a.output/'STRUCTURAL_EXPORT_AND_QA.json',result)
    print('STRUCTURAL_QA_AGGREGATE_PASS',len(output),result['elapsed_seconds'],flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--expected-count',type=int);p.add_argument('--inspect-only',action='store_true');main(p.parse_args())
