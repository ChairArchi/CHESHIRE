"""Render actual neutral-G7 CONTROL versus actual formed-G7 native geometry.

One Blender triangle mesh is constructed; only its complete coordinates change
between the two renders. The preserved NESTED02 receipt supplies cameras and
render conditions only. The causal geometry baseline is the actual neutral G7
CONTROL, explicitly checked against its saved native-array identity.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import shutil
import sys
import time
import zipfile

import numpy as np

HERE = Path(__file__).resolve().parent
SHARED = HERE/'render_parent_probe.py'
SHARED_SHA = '393ed485f3bad277167f3174d23bf08df772210395304c9d84f2d4b822eff561'
spec=importlib.util.spec_from_file_location('generation_pair_verified_native_helpers',SHARED)
shared_probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared_probe)
render,digest,write=shared_probe.render,shared_probe.digest,shared_probe.write
NEUTRAL_XYZ_SHA='01739daf00df22ae7e765ea94cdd1699c7fa95796e585e27b7fb4476f1892429'
NEUTRAL_FACES_SHA='67109d7c7378b6cdfe82a713c74a860c98cdd53adcdce311f8612b3e6565a9ee'


def code_hashes():
    if digest(SHARED)!=SHARED_SHA:
        raise ValueError('Verified native construction/coordinate-update helper changed.')
    return dict(generation_pair_renderer=digest(__file__),verified_native_helpers=shared_probe.code_hashes())


def generation_state(root,control_name,formed_name):
    root=Path(root).resolve()
    path=root/'RECEIPT.json'
    receipt=render.read_json(path)
    if control_name==formed_name:
        raise ValueError('Distinct control and formed variant names required.')
    variants=receipt.get('variants',{})
    expected={}
    for name in (control_name,formed_name):
        render.checked_name(name)
        if name not in variants:
            raise ValueError('Actual saved native variant absent: '+name)
        record=copy.deepcopy(variants[name])
        if any(key not in record for key in ('geometry','geometry_sha256','xyz_sha256','faces_sha256','vertices','triangles')):
            raise ValueError('Actual complete native file/array/count record required: '+name)
        geometry=Path(record['geometry'])
        geometry=geometry.resolve() if geometry.is_absolute() else (root/geometry).resolve()
        if not geometry.is_relative_to(root):
            raise ValueError('Actual generation native geometry must be stored inside this trial.')
        if any(not isinstance(record[key],int) or record[key]<=0 for key in ('vertices','triangles')):
            raise ValueError('Positive actual native counts required.')
        record['geometry']=str(geometry)
        expected[name]=record
    control,formed=expected[control_name],expected[formed_name]
    if (control['xyz_sha256']!=NEUTRAL_XYZ_SHA or control['faces_sha256']!=NEUTRAL_FACES_SHA or
            control['vertices']!=14004226 or control['triangles']!=28008448):
        raise ValueError('CONTROL must be the actual saved neutral G7, not NESTED02 late-field geometry.')
    if any(formed[key]!=control[key] for key in ('faces_sha256','vertices','triangles')):
        raise ValueError('Actual CONTROL/formed variants must have identical complete native triangle connectivity/counts.')
    snapshots=receipt.get('source_snapshots')
    if not isinstance(snapshots,dict) or not snapshots:
        raise ValueError('Actual executed generation source snapshots required.')
    for record in snapshots.values():
        render.verify_snapshot(record)
    for source,checksum in receipt.get('sources',{}).items():
        if digest(source)!=checksum:
            raise ValueError('Actual immutable generation source changed: '+source)
    return receipt,expected,dict(path=str(path),sha256=digest(path))


def load_verified_coordinates(expected,face_dtype):
    """Verify second file's full faces by streaming; load only its XYZ array."""
    path=Path(expected['geometry'])
    if digest(path)!=expected['geometry_sha256']:
        raise ValueError('Actual formed native file changed.')
    with zipfile.ZipFile(path) as archive:
        if archive.namelist().count('faces.npy')!=1:
            raise ValueError('Exactly one stored native faces array required.')
        with archive.open('faces.npy') as stream:
            version=np.lib.format.read_magic(stream)
            if version==(1,0):
                shape,fortran,dtype=np.lib.format.read_array_header_1_0(stream)
            elif version==(2,0):
                shape,fortran,dtype=np.lib.format.read_array_header_2_0(stream)
            else:
                raise ValueError('Supported original non-pickled native NPY header required.')
            if shape!=(expected['triangles'],3) or fortran or dtype!=np.dtype(face_dtype):
                raise ValueError('Actual formed native face shape/storage/dtype differs.')
            checksum=hashlib.sha256()
            byte_count=0
            for block in iter(lambda:stream.read(8*1024**2),b''):
                checksum.update(block)
                byte_count+=len(block)
            if (byte_count!=expected['triangles']*3*dtype.itemsize or
                    checksum.hexdigest()!=expected['faces_sha256']):
                raise ValueError('Complete actual formed native connectivity differs.')
    with np.load(path,allow_pickle=False) as saved:
        xyz=saved['xyz']
    if (xyz.dtype!=np.dtype('float64') or xyz.shape!=(expected['vertices'],3) or
            not np.isfinite(xyz).all() or shared_probe.array_hash(xyz)!=expected['xyz_sha256']):
        raise ValueError('Complete actual formed float64 native coordinates differ.')
    return xyz


def main():
    import bpy
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--control',default='CONTROL')
    parser.add_argument('--variant',default='FORMED')
    parser.add_argument('--views',nargs='+',choices=render.VIEWS,default=['close_oblique'])
    parser.add_argument('--resolution',type=int,default=900)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if len(set(args.views))!=len(args.views) or not 64<=args.resolution<=4096:
        parser.error('Unique preserved views and resolution64..4096 required.')
    root=args.root.resolve()
    phase='review' if args.resolution==900 else f'preview_{args.resolution}'
    names=(render.checked_name(args.control),render.checked_name(args.variant))
    pair_path=root/'GENERATION_PAIR_RECEIPT.json'
    snapshot_folder=root/'source_snapshot_render'/'generation_pair'/phase
    if (pair_path.exists() or snapshot_folder.exists() or
            any((root/(name+'_FLAT')/phase).exists() for name in names)):
        raise FileExistsError('Earlier native generation-pair render/receipt/snapshots are preserved.')
    receipt,expected,generation=generation_state(root,*names)
    # This binding supplies frozen camera/scene provenance, NOT the geometry control.
    camera_reference=render.source_binding()
    hashes=code_hashes()
    started=time.perf_counter()
    print('GENERATION_PAIR_LOAD exact neutral-G7 CONTROL native once',flush=True)
    control_xyz,faces=render.load_arrays(expected[names[0]])
    face_dtype=faces.dtype
    shared_scene=render.scaffold.setup_scene()
    obj,baseline_counts=shared_probe.add_arrays_once(control_xyz,faces,expected[names[0]],shared_scene)
    del control_xyz,faces
    print('GENERATION_PAIR_VERIFY full formed file/connectivity; load coordinates only',flush=True)
    formed_xyz=load_verified_coordinates(expected[names[1]],face_dtype)
    snapshot_folder.mkdir(parents=True)
    snapshots={}
    for source in (Path(__file__).resolve(),SHARED,shared_probe.FAST_PATH,shared_probe.fast.PRESERVED):
        target=snapshot_folder/source.name
        shutil.copyfile(source,target)
        record=dict(source=str(source),snapshot=str(target),sha256=digest(source))
        render.verify_snapshot(record)
        snapshots[source.name]=record
    shutil.copyfile(generation['path'],snapshot_folder/'SOURCE_GENERATION_RECEIPT.json')
    scene,camera=shared_scene.setup_scene(args.resolution,24)
    preparation_seconds=time.perf_counter()-started
    results={}
    for name in names:
        counts=(baseline_counts if name==names[0] else
            shared_probe.set_saved_coordinates(obj,formed_xyz,expected[name]['xyz_sha256'],baseline_counts))
        conditions=render.base.actual_conditions(bpy,scene,camera,obj)
        expected_conditions=copy.deepcopy(camera_reference['conditions'])
        expected_conditions['resolution']=[args.resolution,args.resolution]
        render.require_close(conditions,expected_conditions)
        if bpy.app.version_string!=camera_reference['Blender_version']:
            raise ValueError('Actual original scene and generation-pair Blender versions differ.')
        before=render.scaffold.geometry_signature(obj,counts,False)
        print('GENERATION_PAIR_RENDER '+name+'; neutral CONTROL is the causal geometry baseline',flush=True)
        output=root/(name+'_FLAT')/phase
        actual_views,images=render.scaffold.render_views(scene,camera,
            {view:camera_reference['views'][view] for view in args.views},output)
        after=render.scaffold.geometry_signature(obj,counts,False)
        if before!=after or len(obj.data.edges):
            raise ValueError('Native coordinates/connectivity/flat flags changed during rendering.')
        for view in args.views:
            render.require_close(actual_views[view],camera_reference['actual_views'][view],'matched-camera.'+view)
        result=dict(state=name,phase=phase,saved_geometry=expected[name],generation_receipt=generation,
            causal_geometry_control=expected[names[0]],camera_reference_binding=camera_reference,
            camera_reference_scope='Preserved camera/material/lights/conditions only; NESTED02 is not the paired geometry baseline.',
            geometry_counts=counts,display_readback=after,conditions=conditions,actual_views=actual_views,images=images,
            geometry_unchanged_during_render=True,native_faces_unchanged=True,all_flat=True,
            modifiers=[],normal_maps=False,mesh_edges=0,shared_native_object=True,
            resolution_matched_to_camera_reference=args.resolution==900,version=bpy.app.version_string,
            executed_code_sha256=hashes,source_snapshots=snapshots,
            source_snapshot=snapshots['render_generation_pair.py'])
        write(output/'receipt.json',result)
        results[name]=dict(receipt=str(output/'receipt.json'),receipt_sha256=digest(output/'receipt.json'),
            saved_geometry=expected[name],images={item['view']:str(output/item['filename']) for item in images},
            display_readback=after,actual_views=actual_views,conditions=conditions)
    render.require_close(results[names[0]]['actual_views'],results[names[1]]['actual_views'])
    render.require_close(results[names[0]]['conditions'],results[names[1]]['conditions'])
    if (generation_state(root,*names)!=(receipt,expected,generation) or code_hashes()!=hashes or
            render.source_binding()!=camera_reference or
            any(digest(record['geometry'])!=record['geometry_sha256'] for record in expected.values())):
        raise ValueError('Actual generation files, snapshots, scene reference or executed renderer changed.')
    for record in snapshots.values():
        render.verify_snapshot(record)
    write(pair_path,dict(kind='ACTUAL_NEUTRAL_CONTROL_VERSUS_FORMED_GENERATION_PAIR',
        generation_receipt=generation,control_variant=names[0],formed_variant=names[1],variants=results,
        causal_geometry_control=expected[names[0]],
        neutral_control_identity=dict(xyz_sha256=NEUTRAL_XYZ_SHA,faces_sha256=NEUTRAL_FACES_SHA,
            vertices=14004226,triangles=28008448,source='Exact saved neutral G07_SURFACE arithmetic-centre fan native arrays.'),
        camera_reference_binding=camera_reference,camera_reference_is_geometry_control=False,
        views=args.views,resolution=[args.resolution,args.resolution],samples=24,
        all_flat=True,modifiers=[],normal_maps=False,mesh_edges=0,
        native_triangle_mesh_constructed_once=True,coordinate_only_variant_update=True,
        complete_formed_faces_verified_by_streaming=True,preparation_seconds=preparation_seconds,
        executed_code_sha256=hashes,source_snapshots=snapshots,version=bpy.app.version_string,
        scope='Actual neutral G7 versus actual formed G7 from the selected generation receipt, '
            'identical saved native faces, original preserved cameras/material/lights/24samples/flat flags. '
            'NESTED02 late fields are not used as the causal geometry baseline. No image retouching or geometry repair.'))
    print('ACTUAL_GENERATION_PAIR_DONE '+str(root),flush=True)


if __name__=='__main__':
    main()
