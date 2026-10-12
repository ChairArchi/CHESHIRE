"""Matched actual-triangle column and three-member gate views, inside Blender."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
COL_VIEWS=dict(front=((0,32,5),(0,0,5),12.),oblique=((-18,28,16),(0,0,5),12.),
    side=((-32,0,5),(0,0,5),12.),front_detail=((0,32,5.6),(0,0,5.6),5.4),
    side_detail=((-32,0,5.6),(0,0,5.6),5.4),
    front_micro=((0,32,7.1),(0,0,7.1),2.6),
    side_micro=((-32,0,7.1),(0,0,7.1),2.6),
    oblique_micro=((-18,28,13),(0,0,7.1),2.6))
GATE_VIEWS=dict(front=((0,12,1.8),(0,0,1.8),5.5),
    oblique=((-7,10,6),(0,0,1.8),5.5),side=((-12,0,1.8),(0,0,1.8),5.5),
    detail=((-3,8,4),(0,0,2.7),3.7))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('folders',type=Path,nargs='+')
    p.add_argument('--kind',choices=('column','gate'),default='column')
    p.add_argument('--views',nargs='+')
    p.add_argument('--resolution',type=int,default=900)
    p.add_argument('--samples',type=int,default=24)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    import bpy
    import numpy as np
    from mathutils import Vector
    spec=importlib.util.spec_from_file_location('visible_render_shared',HERE.parent/'iaac_mandelbrot_20261011/render_shared.py')
    shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
    views=COL_VIEWS if args.kind=='column' else GATE_VIEWS
    names=args.views or list(views)
    if any(name not in views for name in names):
        raise ValueError('Unknown view')
    for folder in args.folders:
        folder=folder.resolve()
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        for old_mesh in list(bpy.data.meshes):
            if old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
        with np.load(folder/'geometry.npz') as data:
            xyz,faces=data['xyz'],data['faces']
            ids=data['face_member'] if 'face_member' in data else np.zeros(len(faces),dtype=int)
            member_names=['LEFT','RIGHT','LINTEL'] if len(np.unique(ids))==3 else ['Actual saved mesh']
            for part in np.unique(ids):
                triangles=faces[ids==part]
                mesh=bpy.data.meshes.new(member_names[int(part)])
                # Bulk arrays preserve triangle order without millions of Python
                # lists/integers during the G06 close-geometry comparison.
                mesh.vertices.add(len(xyz))
                mesh.vertices.foreach_set('co',np.asarray(xyz,dtype=np.float32).ravel())
                mesh.loops.add(3*len(triangles))
                mesh.loops.foreach_set('vertex_index',triangles.ravel())
                mesh.polygons.add(len(triangles))
                mesh.polygons.foreach_set('loop_start',np.arange(0,3*len(triangles),3,dtype=np.int32))
                mesh.polygons.foreach_set('loop_total',np.full(len(triangles),3,dtype=np.int32))
                mesh.update(calc_edges=True)
                obj=bpy.data.objects.new(member_names[int(part)],mesh);bpy.context.collection.objects.link(obj)
                shared.material(obj)
        scene,camera=shared.setup_scene(args.resolution,args.samples)
        output=folder/'views';output.mkdir(parents=True,exist_ok=True)
        for name in names:
            position,target,scale=views[name]
            camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
            camera.data.ortho_scale=scale;scene.render.filepath=str(output/(name+'.png'))
            bpy.ops.render.render(write_still=True)
        (output/'receipt.json').write_text(json.dumps(dict(engine='Blender Cycles',version=bpy.app.version_string,
            resolution=args.resolution,samples=args.samples,views={name:views[name] for name in names},
            objects=member_names,material='Existing uniform mineral; flat geometric normals',
            modifiers=[],normal_maps=False,source=str(folder/'geometry.npz')),indent=2),encoding='utf8')
        print('RENDERED',folder,flush=True)


if __name__=='__main__':
    main()
