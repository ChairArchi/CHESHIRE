"""Matched real-mesh renders, writing only this pilot's output directory."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
VIEWS = dict(front=((0, 32, 5), (0, 0, 5), 12.),
    shoulder_front=((0, 32, 8.05), (0, 0, 8.05), 3.2),
    shoulder_oblique=((-18, 28, 15), (0, 0, 8.05), 3.2),
    shoulder_side=((-32, 0, 8.05), (0, 0, 8.05), 3.2))
MODES = ('BASELINE', 'CLEAR_ONLY', 'BROAD_ACTIVE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--parent-root', type=Path, required=True)
    parser.add_argument('--case', nargs='+', choices=('SPAN', 'COUNTER'), default=['SPAN', 'COUNTER'])
    parser.add_argument('--resolution', type=int, default=900)
    parser.add_argument('--samples', type=int, default=24)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    import bpy
    import numpy as np
    from mathutils import Vector
    spec = importlib.util.spec_from_file_location('broad_render_shared',
        HERE.parent/'iaac_mandelbrot_20261011/render_shared.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    for case in args.case:
        for mode in MODES:
            folder = (args.parent_root if mode == 'BASELINE' else args.root)/mode/case/'G06'
            source = (folder/'geometry.npz').resolve()
            output = args.root/mode/case/'G06/views'
            if output.exists():
                raise FileExistsError('Earlier pilot renders preserved: '+str(output))
            output.mkdir(parents=True)
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)
            for old_mesh in list(bpy.data.meshes):
                if old_mesh.users == 0:
                    bpy.data.meshes.remove(old_mesh)
            with np.load(source, allow_pickle=False) as data:
                xyz, triangles = data['xyz'], data['faces']
                mesh = bpy.data.meshes.new('Actual saved G6 mesh')
                mesh.vertices.add(len(xyz))
                mesh.vertices.foreach_set('co', np.asarray(xyz, np.float32).ravel())
                mesh.loops.add(3*len(triangles))
                mesh.loops.foreach_set('vertex_index', triangles.ravel())
                mesh.polygons.add(len(triangles))
                mesh.polygons.foreach_set('loop_start', np.arange(0, 3*len(triangles), 3, dtype=np.int32))
                mesh.polygons.foreach_set('loop_total', np.full(len(triangles), 3, dtype=np.int32))
                mesh.update(calc_edges=True)
                obj = bpy.data.objects.new('Actual saved G6 mesh', mesh)
                bpy.context.collection.objects.link(obj)
                shared.material(obj)
            scene, camera = shared.setup_scene(args.resolution, args.samples)
            for name, (position, target, scale) in VIEWS.items():
                camera.location = position
                camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
                camera.data.ortho_scale = scale
                scene.render.filepath = str(output/f'{name}.png')
                bpy.ops.render.render(write_still=True)
            receipt = dict(input_case=case, candidate=mode, engine='Blender Cycles', version=bpy.app.version_string,
                resolution=args.resolution, samples=args.samples, views=VIEWS,
                material='Existing uniform mineral; flat geometric normals', modifiers=[], normal_maps=False,
                source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                render_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Actual saved native geometry; new shoulder cameras are identical between all three states')
            (output/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
            print('RENDERED', case, mode, flush=True)


if __name__ == '__main__':
    main()
