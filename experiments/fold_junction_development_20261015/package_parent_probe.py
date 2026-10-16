"""Exact reconstructed FIELD PLYs and an offline CONTROL/FIELD image slider.

This command exports only when explicitly run after review. Default status is
research_probe, which is visibly labelled as an unadopted research artifact.
No intermediate full native NPZ is required. The frozen PLY writer verifies
every float64 coordinate and triangle by complete binary readback.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import json
import shutil
import time
import types

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PROBE_CODE = HERE/'render_parent_probe.py'
PROBE_SHA = '393ed485f3bad277167f3174d23bf08df772210395304c9d84f2d4b822eff561'
PLY_CODE = HERE/'package.py'
PLY_SHA = '4ada4bcb1a772ffccec3f0e5281b8e4cb067695e8ac3213060dbf94d95f97321'


def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe=module('exact_parent_probe_export_reconstruction',PROBE_CODE)
preserved=module('exact_parent_probe_preserved_PLY',PLY_CODE)
render,digest=probe.render,probe.digest


def code_hashes():
    if digest(PROBE_CODE)!=PROBE_SHA or digest(PLY_CODE)!=PLY_SHA:
        raise ValueError('Frozen reconstruction or exact PLY workflow changed.')
    return dict(export_adapter=digest(__file__),probe_renderer=probe.code_hashes(),
                preserved_PLY_exporter_sha256=PLY_SHA)


def checked_pair(root):
    root=Path(root).resolve()
    probe_path,pair_path=root/'PROBE_RECEIPT.json',root/'PAIR_RECEIPT.json'
    prepared,pair=render.read_json(probe_path),render.read_json(pair_path)
    reference=dict(path=str(probe_path),sha256=digest(probe_path))
    if (pair['kind']!='ACTUAL_PARENT_CONTROL_DELTA_MATCHED_NATIVE_PAIR' or
            pair['probe_receipt']!=reference or pair['executed_code_sha256']!=probe.code_hashes() or
            set(pair['variants'])!={'CONTROL','FIELD'} or pair['all_flat'] is not True or
            pair['modifiers']!=[] or pair['normal_maps'] is not False or
            pair['native_triangles_loaded_once'] is not True or pair['shared_native_object'] is not True or
            pair['saved_native_faces_unchanged'] is not True or pair['mesh_edges']!=0):
        raise ValueError('Actual completed native CONTROL/FIELD pair provenance differs.')
    snapshots=pair['source_snapshots']
    sources={'render_parent_probe.py':PROBE_CODE,'fast_render.py':probe.FAST_PATH,'render.py':probe.fast.PRESERVED}
    if set(snapshots)!=set(sources):
        raise ValueError('All actual parent-pair renderer snapshots are required.')
    for filename,path in sources.items():
        record=snapshots[filename]
        render.verify_snapshot(record)
        if Path(record['source']).resolve()!=path.resolve() or record['sha256']!=digest(path):
            raise ValueError('Actual parent-pair executed source/snapshot binding differs.')
    for record in prepared.get('source_snapshots',{}).values():
        render.verify_snapshot(record)
    binding=render.source_binding()
    if pair['source_binding']!=binding:
        raise ValueError('Preserved actual camera/material source binding differs.')
    expected=copy.deepcopy(prepared['baseline_record'])
    native,native_sha=probe.file_binding(prepared,'baseline_native',root,expected['geometry_sha256'])
    control,control_sha=probe.file_binding(prepared,'baseline_control_quad',root)
    expected['geometry']=str(native)
    field=prepared['variants']['FIELD']
    delta=Path(field['control_delta'])
    delta=delta.resolve() if delta.is_absolute() else (root/delta).resolve()
    if (pair['baseline_native']!=expected or pair['baseline_control_quad']!={'path':str(control),'sha256':control_sha} or
            pair['control_delta']!={'path':str(delta),'sha256':field['control_delta_sha256']} or
            native_sha!=expected['geometry_sha256'] or digest(control)!=control_sha or
            digest(delta)!=field['control_delta_sha256']):
        raise ValueError('Actual baseline/control/sparse-delta bindings differ.')
    records={}
    for name in ('CONTROL','FIELD'):
        path=root/(name+'_FLAT')/'review'/'receipt.json'
        bound=pair['variants'][name]
        if Path(bound['receipt']).resolve()!=path.resolve() or digest(path)!=bound['receipt_sha256']:
            raise ValueError('Actual variant render receipt changed.')
        record=render.read_json(path)
        xyz_sha=expected['xyz_sha256'] if name=='CONTROL' else field['xyz_sha256']
        counts,display=record['geometry_counts'],record['display_readback']
        if (record['state']!=name or record['phase']!='review' or record['probe_receipt']!=reference or
                record['baseline_native']!=expected or record['coordinate_source']!=prepared['variants'][name] or
                record['actual_native_xyz_sha256']!=xyz_sha or
                record['actual_native_faces_sha256']!=expected['faces_sha256'] or
                record['code_sha256']!=probe.code_hashes() or record['source_snapshots']!=snapshots or
                record['source_snapshot']!=snapshots['render_parent_probe.py'] or record['source_binding']!=binding or
                record['geometry_unchanged_during_render'] is not True or record['native_faces_unchanged'] is not True or
                record['all_flat'] is not True or record['modifiers']!=[] or record['normal_maps'] is not False or
                record['mesh_edges']!=0 or record['shared_native_object'] is not True or
                record['resolution_matched_to_source'] is not True or record['version']!=binding['Blender_version'] or
                counts['vertices']!=expected['vertices'] or counts['triangles']!=expected['triangles'] or
                counts['source_arrays']!={'xyz_sha256':xyz_sha,'faces_sha256':expected['faces_sha256']} or
                display['geometry']!=counts['expected_display_arrays'] or display['polygons']!=expected['triangles'] or
                display['smooth_polygons']!=0 or display['all_use_smooth'] is not False or
                display['geometry_unchanged'] is not True or display['modifiers']!=[] or
                display['custom_normal_map'] is not False or bound['display_readback']!=display or
                bound['actual_native_xyz_sha256']!=xyz_sha):
            raise ValueError('Actual complete native array/display/flat-shading readbacks differ.')
        render.require_close(record['conditions'],binding['conditions'])
        render.require_close(record['actual_views'],bound['actual_views'])
        render.require_close(record['conditions'],bound['conditions'])
        if (not record['images'] or set(record['actual_views'])!={item['view'] for item in record['images']} or
                len(record['images'])!=len(record['actual_views'])):
            raise ValueError('Actual unique pair image/view inventory required.')
        for image in record['images']:
            view=image['view']
            if view not in render.VIEWS or image['filename']!=view+'.png':
                raise ValueError('Unknown or nonlocal actual pair image.')
            render.require_close(record['actual_views'][view],binding['actual_views'][view])
            png=path.parent/image['filename']
            if digest(png)!=image['sha256'] or Path(bound['images'][view]).resolve()!=png.resolve():
                raise ValueError('Actual pair PNG changed.')
            with Image.open(png) as opened:
                if opened.format!='PNG' or opened.size!=(900,900):
                    raise ValueError('Original 900px pair PNG required.')
                opened.verify()
        records[name]=record
    if set(records['CONTROL']['actual_views'])!=set(records['FIELD']['actual_views']):
        raise ValueError('CONTROL and FIELD must contain the same actual camera views.')
    render.require_close(records['CONTROL']['actual_views'],records['FIELD']['actual_views'])
    if records['FIELD']['reconstruction']!=pair['reconstruction']:
        raise ValueError('Actual FIELD reconstruction proof differs.')
    return dict(prepared=prepared,pair=pair,records=records,binding=binding,baseline=expected,
        native=native,native_sha=native_sha,control=control,control_sha=control_sha,delta=delta,
        probe_receipt=reference,pair_receipt=dict(path=str(pair_path),sha256=digest(pair_path)))


def viewer(output,state,status,full,detail):
    images=[]
    maps={name:{item['view']:item for item in data['images']} for name,data in state['records'].items()}
    for view in state['records']['CONTROL']['actual_views']:
        row=dict(view=view)
        for side,name in (('reference','CONTROL'),('candidate','FIELD')):
            item=maps[name][view]
            row[side]=str(Path(state['pair']['variants'][name]['receipt']).parent/item['filename'])
            row[side+'_sha256']=item['sha256']
        images.append(row)
    namespace=dict(preserved.__dict__)
    namespace['BASE_EXPORT']=output/'NO_UNRELATED_CONTROL_MODEL_LINKS'
    writer=types.FunctionType(preserved.write_viewer.__code__,namespace,'actual_probe_image_viewer')
    result=writer(output,'FIELD',images,state['baseline'],True,full,detail)
    path=Path(result['path'])
    document=path.read_text(encoding='utf8').replace('NESTED02','CONTROL').replace('개발 모델','FIELD')
    label='연구 프로브 · 채택 결과 아님' if status=='research_probe' else '검토 후 선택한 결과'
    document=document.replace('<h1>','<p>'+label+'</p><h1>',1)
    path.write_text(document,encoding='utf8')
    result.update(sha256=digest(path),comparison='Actual newly rendered CONTROL versus FIELD PNGs.',
                  status=status,labels_adapted_only=True,PNG_pixels_modified=False,
                  baseline_model_links_are_external=False)
    return result,images


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--status',choices=('research_probe','accepted'),default='research_probe')
    parser.add_argument('--detail-radius',type=float,default=preserved.RADIUS)
    args=parser.parse_args()
    root,output=args.root.resolve(),args.output.resolve()
    if output.exists():
        raise FileExistsError('Earlier actual probe package is preserved.')
    if not np.isfinite(args.detail_radius) or args.detail_radius<=0:
        parser.error('Finite positive detail radius required.')
    started=time.perf_counter()
    hashes=code_hashes()
    state=checked_pair(root)
    print('PROBE_EXPORT reconstruct exact native FIELD once',flush=True)
    baseline,faces=render.load_arrays(state['baseline'])
    with np.load(state['control'],allow_pickle=False) as saved:
        control,quads=saved['xyz'],saved['faces']
    probe.verify_native_fan_faces(faces,quads,len(control))
    with np.load(state['delta'],allow_pickle=False) as saved:
        ids,delta,nv=saved['ids'],saved['delta'],saved['control_vertices']
    if np.asarray(nv).shape!=() or np.asarray(nv).dtype.kind not in 'iu' or int(nv)!=len(control):
        raise ValueError('Sparse control count differs.')
    field,proof=probe.apply_sparse_control_delta(baseline,control,quads,ids,delta)
    if proof!=state['pair']['reconstruction'] or proof['complete_native_xyz_sha256']!=state['prepared']['variants']['FIELD']['xyz_sha256']:
        raise ValueError('Exported full float64 native FIELD differs from the actual rendered reconstruction.')
    del baseline,control,quads,ids,delta
    output.mkdir(parents=True)
    snapshots={}
    for path in (Path(__file__).resolve(),PROBE_CODE,PLY_CODE,probe.FAST_PATH,probe.fast.PRESERVED):
        target=output/('SOURCE_SNAPSHOT_'+path.name)
        shutil.copyfile(path,target)
        if digest(path)!=digest(target):
            raise ValueError('Exact export source snapshot differs.')
        snapshots[path.name]=dict(source=str(path),snapshot=str(target),sha256=digest(path))
    for name in ('PROBE_RECEIPT.json','PAIR_RECEIPT.json'):
        shutil.copyfile(root/name,output/('SOURCE_'+name))
    for name in ('CONTROL','FIELD'):
        shutil.copyfile(state['pair']['variants'][name]['receipt'],output/('SOURCE_'+name+'_RENDER_RECEIPT.json'))
    shutil.copyfile(state['delta'],output/'SOURCE_SPARSE_CONTROL_DELTA.npz')
    xyz_sha=proof['complete_native_xyz_sha256']
    full=preserved.write_ply(output/'CHESHIRE_PARENT_PROBE_FIELD_FULL.ply',field,faces,xyz_sha)
    chosen=[]
    for start in range(0,len(faces),131072):
        centres=field[faces[start:start+131072]].mean(axis=1)
        chosen.append(start+np.flatnonzero(np.sum((centres-preserved.TARGET)**2,axis=1)<=args.detail_radius**2))
    face_ids=np.concatenate(chosen)
    if not len(face_ids):
        raise ValueError('Exact actual near-detail triangle subset is empty.')
    vertex_ids,inverse=np.unique(faces[face_ids].ravel(),return_inverse=True)
    detail=preserved.write_ply(output/'CHESHIRE_PARENT_PROBE_FIELD_DETAIL.ply',field[vertex_ids],inverse.reshape(-1,3),xyz_sha)
    detail.update(scope='Exact reconstructed native triangle subset; open cut boundary, no added caps.',
                  target=preserved.TARGET.tolist(),radius=args.detail_radius)
    ids_path=output/'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path,source_vertex_ids=vertex_ids,source_face_ids=face_ids)
    comparison,images=viewer(output,state,args.status,full,detail)
    if (digest(state['native'])!=state['native_sha'] or code_hashes()!=hashes or
            checked_pair(root)['pair_receipt']!=state['pair_receipt']):
        raise ValueError('Actual export inputs, PNGs or executed code changed.')
    manifest=dict(kind='EXACT_PARENT_CONTROL_FIELD_PROBE_PACKAGE',date='2026-10-15',status=args.status,
        research_probe_not_adopted=args.status=='research_probe',probe_receipt=state['probe_receipt'],
        pair_receipt=state['pair_receipt'],baseline_native=state['baseline'],reconstruction=proof,
        full=full,detail=detail,detail_source_ids=dict(path=str(ids_path),sha256=digest(ids_path)),
        comparison=comparison,actual_compared_PNGs=images,source_snapshots=snapshots,
        sparse_delta_copy=dict(path=str(output/'SOURCE_SPARSE_CONTROL_DELTA.npz'),sha256=digest(output/'SOURCE_SPARSE_CONTROL_DELTA.npz')),
        executed_code_sha256=hashes,source_geometry_modified_by_exporter=False,simplification=False,
        source_geometry_SHA_comment=dict(kind='COMPLETE_RECONSTRUCTED_NATIVE_FLOAT64_XYZ_ARRAY_SHA256',value=xyz_sha),
        native_faces_sha256=state['baseline']['faces_sha256'],units='Original axes/model units retained; no scaling.',
        quality=state['prepared'].get('quality'),acceptance='Explicit export status supplied by the reviewing caller; not inferred from finite geometry.',
        self_intersection_certificate=False,seconds=time.perf_counter()-started)
    preserved.write_json(output/'MANIFEST.json',manifest)
    with open(output/'README.txt','x',encoding='utf8') as stream:
        stream.write('CHESHIRE actual CONTROL/FIELD parent probe\nStatus: '+args.status+'\n\n'
            'comparison.html: actual same-camera900px CONTROL/FIELD PNGs, offline.\n'
            'FIELD FULL: complete reconstructed native float64 coordinates and unchanged original triangles.\n'
            'FIELD DETAIL: exact native triangle subset; open boundary, no caps.\n'
            'PLY Source geometry SHA256 comment identifies the complete native XYZ ARRAY, not an NPZ file.\n'
            'No intermediate full native NPZ was needed; see MANIFEST.json and SOURCE receipts.\n'
            'Research probe status does not indicate adoption or geometric safety certification.\n')
    print('ACTUAL_PARENT_PROBE_PACKAGE_DONE '+str(output),flush=True)


if __name__=='__main__':
    main()
