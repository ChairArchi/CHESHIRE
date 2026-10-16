"""Exact actual-G7 FORMED PLYs and an offline neutral CONTROL/FORMED slider.

Only run after visual review. research_probe is the default and is labelled as
a test artifact, not an adopted design. Both images come from the completed
generation pair; NESTED02 supplies camera/scene provenance only.
"""
from pathlib import Path
import argparse
import copy
import importlib.util
import shutil
import time
import types

import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
GENERATION_RENDERER=HERE/'render_generation_pair.py'
GENERATION_RENDERER_SHA='6f4ae79198bd740e0161a989b2caac9001de76df2eb35f1b64db5d34f1df6964'
PLY_CODE=HERE/'package.py'
PLY_SHA='4ada4bcb1a772ffccec3f0e5281b8e4cb067695e8ac3213060dbf94d95f97321'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pair_renderer=module('generation_export_verified_renderer',GENERATION_RENDERER)
preserved=module('generation_export_frozen_exact_PLY',PLY_CODE)
render,digest=pair_renderer.render,pair_renderer.digest


def code_hashes():
    if digest(GENERATION_RENDERER)!=GENERATION_RENDERER_SHA or digest(PLY_CODE)!=PLY_SHA:
        raise ValueError('Frozen actual-pair renderer or exact PLY exporter changed.')
    return dict(export_adapter=digest(__file__),actual_generation_pair_renderer=pair_renderer.code_hashes(),
                preserved_PLY_exporter_sha256=PLY_SHA)


def checked_pair(root):
    root=Path(root).resolve()
    pair_path=root/'GENERATION_PAIR_RECEIPT.json'
    pair=render.read_json(pair_path)
    names=(pair['control_variant'],pair['formed_variant'])
    receipt,expected,generation=pair_renderer.generation_state(root,*names)
    if (pair['kind']!='ACTUAL_NEUTRAL_CONTROL_VERSUS_FORMED_GENERATION_PAIR' or
            pair['generation_receipt']!=generation or set(pair['variants'])!=set(names) or
            pair['causal_geometry_control']!=expected[names[0]] or
            pair['camera_reference_is_geometry_control'] is not False or
            pair['all_flat'] is not True or pair['modifiers']!=[] or pair['normal_maps'] is not False or
            pair['mesh_edges']!=0 or pair['native_triangle_mesh_constructed_once'] is not True or
            pair['coordinate_only_variant_update'] is not True or
            pair['complete_formed_faces_verified_by_streaming'] is not True or
            pair['executed_code_sha256']!=pair_renderer.code_hashes()):
        raise ValueError('Actual completed neutral-CONTROL/formed pair provenance differs.')
    identity=pair['neutral_control_identity']
    if (identity['xyz_sha256']!=pair_renderer.NEUTRAL_XYZ_SHA or
            identity['faces_sha256']!=pair_renderer.NEUTRAL_FACES_SHA or
            identity['vertices']!=14004226 or identity['triangles']!=28008448):
        raise ValueError('Actual paired geometry control is not the original neutral G7.')
    snapshots=pair['source_snapshots']
    dependencies={'render_generation_pair.py':GENERATION_RENDERER,'render_parent_probe.py':pair_renderer.SHARED,
        'fast_render.py':pair_renderer.shared_probe.FAST_PATH,'render.py':pair_renderer.shared_probe.fast.PRESERVED}
    if set(snapshots)!=set(dependencies):
        raise ValueError('All actual renderer/helper snapshots required.')
    for name,path in dependencies.items():
        record=snapshots[name]
        render.verify_snapshot(record)
        if Path(record['source']).resolve()!=path.resolve() or record['sha256']!=digest(path):
            raise ValueError('Actual executed renderer/helper source binding differs.')
    camera_reference=render.source_binding()
    if pair['camera_reference_binding']!=camera_reference:
        raise ValueError('Actual preserved camera/material/light reference changed.')
    records={}
    for name in names:
        bound=pair['variants'][name]
        path=root/(name+'_FLAT')/'review'/'receipt.json'
        if Path(bound['receipt']).resolve()!=path.resolve() or digest(path)!=bound['receipt_sha256']:
            raise ValueError('Actual variant render receipt changed.')
        actual=render.read_json(path)
        source=expected[name]
        counts,display=actual['geometry_counts'],actual['display_readback']
        if (actual['state']!=name or actual['phase']!='review' or actual['saved_geometry']!=source or
                actual['generation_receipt']!=generation or actual['causal_geometry_control']!=expected[names[0]] or
                actual['camera_reference_binding']!=camera_reference or
                actual['executed_code_sha256']!=pair_renderer.code_hashes() or actual['source_snapshots']!=snapshots or
                actual['source_snapshot']!=snapshots['render_generation_pair.py'] or
                actual['geometry_unchanged_during_render'] is not True or actual['native_faces_unchanged'] is not True or
                actual['all_flat'] is not True or actual['modifiers']!=[] or actual['normal_maps'] is not False or
                actual['mesh_edges']!=0 or actual['shared_native_object'] is not True or
                actual['resolution_matched_to_camera_reference'] is not True or
                actual['version']!=camera_reference['Blender_version'] or
                counts['vertices']!=source['vertices'] or counts['triangles']!=source['triangles'] or
                counts['source_arrays']!={key:source[key] for key in ('xyz_sha256','faces_sha256')} or
                display['geometry']!=counts['expected_display_arrays'] or display['polygons']!=source['triangles'] or
                display['smooth_polygons']!=0 or display['all_use_smooth'] is not False or
                display['geometry_unchanged'] is not True or display['modifiers']!=[] or
                display['custom_normal_map'] is not False or bound['saved_geometry']!=source or
                bound['display_readback']!=display):
            raise ValueError('Actual full native array/display/flat-shading provenance differs.')
        render.require_close(actual['conditions'],camera_reference['conditions'])
        render.require_close(actual['conditions'],bound['conditions'])
        render.require_close(actual['actual_views'],bound['actual_views'])
        if (not actual['images'] or set(actual['actual_views'])!={item['view'] for item in actual['images']} or
                len(actual['images'])!=len(actual['actual_views'])):
            raise ValueError('Actual unique matched-camera image inventory required.')
        for image in actual['images']:
            view=image['view']
            if view not in render.VIEWS or image['filename']!=view+'.png':
                raise ValueError('Actual local PNG filename required.')
            render.require_close(actual['actual_views'][view],camera_reference['actual_views'][view])
            png=path.parent/image['filename']
            if digest(png)!=image['sha256'] or Path(bound['images'][view]).resolve()!=png.resolve():
                raise ValueError('Actual source PNG changed.')
            with Image.open(png) as opened:
                if opened.format!='PNG' or opened.size!=(900,900):
                    raise ValueError('Actual matched900px PNG required.')
                opened.verify()
        if digest(source['geometry'])!=source['geometry_sha256']:
            raise ValueError('Actual saved native source file changed.')
        if source.get('control_quad'):
            if digest(source['control_quad'])!=source['control_quad_sha256']:
                raise ValueError('Actual saved control state for continuation changed.')
        records[name]=actual
    render.require_close(records[names[0]]['actual_views'],records[names[1]]['actual_views'])
    return dict(receipt=receipt,expected=expected,generation_receipt=generation,pair=pair,names=names,
        pair_receipt=dict(path=str(pair_path),sha256=digest(pair_path)),records=records,
        camera_reference=camera_reference,renderer_snapshots=snapshots)


def write_viewer(output,state,status,full,detail):
    control,formed=state['names']
    maps={name:{item['view']:item for item in record['images']} for name,record in state['records'].items()}
    images=[]
    for view in state['records'][control]['actual_views']:
        item=dict(view=view)
        for side,name in (('reference',control),('candidate',formed)):
            image=maps[name][view]
            item[side]=str(Path(state['pair']['variants'][name]['receipt']).parent/image['filename'])
            item[side+'_sha256']=image['sha256']
        images.append(item)
    namespace=dict(preserved.__dict__)
    namespace['BASE_EXPORT']=output/'NO_UNRELATED_NESTED02_MODEL_LINKS'
    writer=types.FunctionType(preserved.write_viewer.__code__,namespace,'actual_generation_pair_viewer')
    result=writer(output,formed,images,state['expected'][formed],True,full,detail)
    path=Path(result['path'])
    document=path.read_text(encoding='utf8').replace('NESTED02',control).replace('개발 모델',formed)
    status_label='연구 시험 · 채택 결과 아님' if status=='research_probe' else '검토 후 선택한 결과'
    document=document.replace('<h1>','<p>'+status_label+' · '+control+' = 원래 neutral G7</p><h1>',1)
    path.write_text(document,encoding='utf8')
    result.update(sha256=digest(path),status=status,actual_control_variant=control,actual_formed_variant=formed,
        paired_geometry_control='Actual original neutral G7; NESTED02 is camera/scene provenance only.',
        baseline_model_links_are_external=False,source_PNG_pixels_modified=False,labels_adapted_only=True)
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
        raise FileExistsError('Earlier actual native-generation package is preserved.')
    if not np.isfinite(args.detail_radius) or args.detail_radius<=0:
        parser.error('Positive finite detail radius required.')
    started=time.perf_counter()
    hashes=code_hashes()
    state=checked_pair(root)
    control,formed=state['names']
    expected=state['expected'][formed]
    print('GENERATION_EXPORT load complete actual saved formed native',flush=True)
    xyz,faces=render.load_arrays(expected)
    output.mkdir(parents=True)
    snapshots={}
    dependencies=(Path(__file__).resolve(),GENERATION_RENDERER,PLY_CODE,pair_renderer.SHARED,
                  pair_renderer.shared_probe.FAST_PATH,pair_renderer.shared_probe.fast.PRESERVED)
    for source in dependencies:
        target=output/('SOURCE_SNAPSHOT_'+source.name)
        shutil.copyfile(source,target)
        if digest(source)!=digest(target):
            raise ValueError('Actual export source snapshot differs.')
        snapshots[source.name]=dict(source=str(source),snapshot=str(target),sha256=digest(source))
    for name in ('RECEIPT.json','GENERATION_PAIR_RECEIPT.json'):
        shutil.copyfile(root/name,output/('SOURCE_'+name))
    for name in (control,formed):
        shutil.copyfile(state['pair']['variants'][name]['receipt'],output/('SOURCE_'+name+'_RENDER_RECEIPT.json'))
    prefix='CHESHIRE_GENERATION_'+formed
    full=preserved.write_ply(output/(prefix+'_FULL.ply'),xyz,faces,expected['geometry_sha256'])
    target=np.asarray(state['records'][formed]['actual_views'].get('close_oblique',
        {'target':preserved.TARGET.tolist()})['target'],dtype=float)
    chosen=[]
    for start in range(0,len(faces),131072):
        centres=xyz[faces[start:start+131072]].mean(axis=1)
        chosen.append(start+np.flatnonzero(np.sum((centres-target)**2,axis=1)<=args.detail_radius**2))
    face_ids=np.concatenate(chosen)
    if not len(face_ids):
        raise ValueError('Exact stored near-detail triangle subset is empty.')
    vertex_ids,inverse=np.unique(faces[face_ids].ravel(),return_inverse=True)
    detail=preserved.write_ply(output/(prefix+'_DETAIL.ply'),xyz[vertex_ids],inverse.reshape(-1,3),expected['geometry_sha256'])
    detail.update(scope='Exact original stored native triangle subset; open cut boundary, no caps.',
                  selection='Native triangle centroid sphere at the actual preserved close-camera target.',
                  target=target.tolist(),radius=args.detail_radius)
    ids_path=output/'DETAIL_SOURCE_IDS.npz'
    np.savez_compressed(ids_path,source_vertex_ids=vertex_ids,source_face_ids=face_ids)
    comparison,images=write_viewer(output,state,args.status,full,detail)
    final=checked_pair(root)
    if code_hashes()!=hashes or final['pair_receipt']!=state['pair_receipt'] or final['generation_receipt']!=state['generation_receipt']:
        raise ValueError('Actual native sources/PNGs/receipts or executed export code changed.')
    manifest=dict(kind='EXACT_ACTUAL_NEUTRAL_CONTROL_FORMED_GENERATION_PACKAGE',date='2026-10-15',
        status=args.status,research_probe_not_adopted=args.status=='research_probe',
        generation_receipt=state['generation_receipt'],generation_pair_receipt=state['pair_receipt'],
        control_variant=control,formed_variant=formed,causal_geometry_control=state['expected'][control],
        actual_formed_geometry=expected,camera_reference_is_geometry_control=False,
        full=full,detail=detail,detail_source_ids=dict(path=str(ids_path),sha256=digest(ids_path)),
        comparison=comparison,actual_compared_PNGs=images,source_snapshots=snapshots,
        actual_render_source_snapshots=state['renderer_snapshots'],executed_code_sha256=hashes,
        actual_saved_control_for_continuation=(None if not expected.get('control_quad') else
            dict(path=expected['control_quad'],sha256=expected['control_quad_sha256'])),
        source_geometry_modified_by_exporter=False,simplification=False,
        units='Unchanged original axes/model units; no scale conversion.',
        acceptance='Caller-selected visual-review status; no aesthetic or collision success inferred from finite coordinates.',
        seconds=time.perf_counter()-started)
    preserved.write_json(output/'MANIFEST.json',manifest)
    with open(output/'README.txt','x',encoding='utf8') as stream:
        stream.write('CHESHIRE actual neutral-G7 CONTROL / formed-G7 native test\nStatus: '+args.status+'\n\n'
            'comparison.html: actual paired900px PNGs, offline; all rendered views included.\n'
            'CONTROL is actual saved neutral G7. NESTED02 supplies camera/material/light provenance only.\n'
            'FULL PLY: complete actual saved formed native, float64 coordinates and unchanged stored triangles.\n'
            'DETAIL PLY: exact original triangle subset; open cut boundary, no caps or new surface.\n'
            'Complete PLY coordinate/index roundtrip is verified. Original axes/model units retained.\n'
            'The saved formed control-quad state stays in its source trial for genuine later continuation.\n'
            'Research-test status does not imply adoption or a collision certificate.\n')
    print('ACTUAL_GENERATION_PAIR_PACKAGE_DONE '+str(output),flush=True)


if __name__=='__main__':
    main()
