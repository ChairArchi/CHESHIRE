"""Actual stitched column synthesis; earlier experiments are immutable inputs."""
from pathlib import Path
import sys,json,argparse,shutil,time,importlib.util
sys.dont_write_bytecode=True
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'src'))
from cheshire.ornament_assembly import assemble_patches,record,file_hash
BASE=Path(r'E:\CHESHIRE_DATA\experiments\whole_cc1_prototype_20261016')
ROOT=Path(r'E:\CHESHIRE_DATA\experiments\column_synthesis_20261016')
PRIOR=Path(r'E:\CHESHIRE_DATA\experiments\generation_mirror_hybrid_20261016')
OLD=Path(r'E:\CHESHIRE_DATA\experiments\fold_aligned_mandel_20261015')
CHUNK=65536

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main(index_path,out):
    started=time.perf_counter();index=read(index_path);patches=[]
    source=read(BASE/'RECOVERY_RECEIPT.json')
    x_path=BASE/'working_arrays/RECOVERED_CC1_XYZ.npy';q_path=BASE/'working_arrays/CHILD_QUADS.npy'
    x=np.load(x_path,mmap_mode='r');q=np.load(q_path,mmap_mode='r')
    host_input=read(Path(r'E:\CHESHIRE_DATA\handoffs\CHESHIRE_20261016_WHOLE_CC1_PROTOTYPE.json'))
    for key,path in [('xyz',x_path),('quads',q_path)]:
        if file_hash(path)!=host_input['source_arrays'][key]['sha256']:raise ValueError('Selected actual CC1 carrier changed.')
    classifier=np.load(PRIOR/'history_classification/SOURCE5_WEIGHTS_G3.npz')
    source_body=classifier['source_body']
    W=np.load(PRIOR/'history_classification/SOURCE5_G7.npy',mmap_mode='r')
    sr=read(OLD/'variant16_whole_hybrid_20261016/SOURCE_FIELD_RECEIPT.json')
    caps=np.load(sr['protected_cap_mask']['path'],mmap_mode='r')
    flowmeta=read(OLD/'variant22_flow_corrected_visible_relief_whole_hybrid_20261016/CLASSIFICATION.json')
    flow=np.load(flowmeta['display_flow_protection']['path'],mmap_mode='r')
    helpers=module('synthesis_readonly_host_arrays',OLD/'run_whole_hybrid_20261016.py')
    q7=helpers.m.mapped(Path(r'E:\CHESHIRE_DATA\experiments\parent_nested_folds_20261014\trial02\NESTED\control_quad.npz'),'faces')
    if len(q)!=27352*1024:raise ValueError('Actual saved G3-to-G8 face lineage differs.')
    def classify(fids):
        fids=np.asarray(fids,np.int64);parent=fids//4;corner=fids%4;ids=q7[parent]
        # Mean of the actual V/E/F bilinear attributes on each child quad.
        coef=np.full((len(fids),4),.0625);r=np.arange(len(fids))
        coef[r,corner]=.5625;coef[r,(corner-1)%4]=.1875;coef[r,(corner+1)%4]=.1875
        weights=np.einsum('nk,nkc->nc',coef,W[ids]);labels=1+np.argmax(weights,axis=1)
        labels[~source_body[fids//1024]]=0
        labels[np.einsum('nk,nk->n',coef,flow[ids])>=.5]=6
        labels[np.any(caps[ids],axis=1)]=0
        return labels.astype(np.int16)
    for row in index['patches']:
        p=Path(row['path'])
        if file_hash(p)!=row['sha256']:raise ValueError('Actual local stitched patch changed.')
        with np.load(p,allow_pickle=False) as z:patch={k:z[k] for k in z.files}
        if 'triangle_host_face_ids' in patch:
            ids=patch['triangle_host_face_ids'];labels=np.full(len(ids),{'A':7,'B':8,'C':9}[row['part_type']],np.int16)
            host=ids>=0
            for a in range(0,len(ids),CHUNK):
                b=min(a+CHUNK,len(ids));valid=host[a:b];labels[a:b][valid]=classify(ids[a:b][valid])
            patch['triangle_classes']=labels
        else:
            raise ValueError('Actual host-top versus component face provenance required for truthful color material.')
        patches.append(patch)
    result=assemble_patches(x,q,patches,out,chunk=CHUNK)
    if result['added_handles']!=0:raise ValueError('Final blind-pocket surface must introduce no through handles.')
    remap=np.load(result['arrays']['OLD_TO_NEW']['path'],mmap_mode='r')
    material=np.lib.format.open_memmap(out/'MATERIAL_G8_TO_FINAL.npy',mode='w+',shape=(len(x),),dtype=np.int64)
    material[:]=remap[:len(x)];vpos=len(x)
    for patch in patches:
        fresh=np.asarray(patch['host_vertex_ids'])<0;n=int(fresh.sum())
        if 'material_host_vertex_ids' not in patch:raise ValueError('Logical carrier vertex lineage required for geometry-nearest-free profile QA.')
        logical=np.asarray(patch['material_host_vertex_ids'])[fresh];new=remap[vpos:vpos+n]
        valid=logical>=0
        old=material[logical[valid]]
        if np.any((old>=0)&(old!=new[valid])):raise ValueError('One material carrier vertex has two final surface coordinates.')
        material[logical[valid]]=new[valid];vpos+=n
    if np.any(material<0):raise ValueError('Every original material vertex must remain represented after closed relief replacement.')
    material.flush();result['arrays']['MATERIAL_G8_TO_FINAL']=record(out/'MATERIAL_G8_TO_FINAL.npy')
    quad_ids=np.load(result['arrays']['SOURCE_QUAD_IDS']['path'],mmap_mode='r')
    color=np.lib.format.open_memmap(out/'QUAD_CLASSES.npy',mode='w+',shape=(len(quad_ids),),dtype=np.int16)
    for a in range(0,len(quad_ids),CHUNK):color[a:a+CHUNK]=classify(quad_ids[a:a+CHUNK])
    color.flush();result['arrays']['QUAD_CLASSES']=record(out/'QUAD_CLASSES.npy')
    snap=out/'source_snapshot';snap.mkdir()
    snapshots={}
    for path in (Path(__file__).resolve(),REPO/'src/cheshire/ornament_assembly.py'):
        target=snap/path.name;shutil.copyfile(path,target);snapshots[str(path)]=dict(source=str(path),snapshot=str(target),sha256=file_hash(path))
    synthesis=dict(kind='COLUMN_CLOSED_BLIND_RECESS_TISSUE_SYNTHESIS',prototype=True,
        actual_blind_recess_geometry=True,continuous_host_backskin=True,
        through_ornament_handles_intentionally_omitted=True,
        actual_added_handles=result['added_handles'],
        prior_results_preserved=True,base=host_input['source_arrays'],base_recovery=record(BASE/'RECOVERY_RECEIPT.json'),
        patches=record(index_path),selection_history=record(PRIOR/'history_classification/CLASSIFICATION_RECEIPT.json'),
        assembly=result,source_snapshots=snapshots,
        color=dict(quad_classes=record(out/'QUAD_CLASSES.npy'),triangle_classes=result['arrays']['TRIANGLE_CLASSES'],
            palette=['structural carrier','calm SOURCE','weak SOURCE','strong SOURCE','rounded SOURCE','complex SOURCE',
                'protected established flow','paper-derived closed relief','deep blind recesses','closed folded membrane']),
        formulation='Actual smooth CC1 carrier + deep closed-backed Tissue/paper recesses on bounded native disks, exact boundary stitched. Through-hole studies are preserved separately; original results unchanged.',
        global_self_intersection_checked=False,elapsed_seconds=time.perf_counter()-started)
    with (out/'SYNTHESIS_RECEIPT.json').open('x',encoding='utf-8') as f:json.dump(synthesis,f,indent=2)
    print('WHOLE_BLIND_RECESS_SYNTHESIS_ASSEMBLED',result['counts'],result['added_handles'],time.perf_counter()-started,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--patch-index',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();main(args.patch_index,args.out)
