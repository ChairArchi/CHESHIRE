"""Fixed column cameras on saved actual triangles; no geometry edits.

Blender usage:
  blender --background --factory-startup --python render.py -- FOLDER \
    --views front oblique side front_meso side_meso front_upper side_upper

Whole views match iaac_mandelbrot_20261011/column_render.py. Meso views
match column_detail_20261012/detail_render.py. Upper views use the same
front/side directions and span, with their target moved to z=6.1.
"""
from pathlib import Path
import argparse
import json
import sys

HERE = Path(__file__).resolve().parent
VIEWS = {
    'front': ((0, 32, 5), (0, 0, 5), 12.0),
    'oblique': ((-18, 28, 16), (0, 0, 5), 12.0),
    'side': ((-32, 0, 5), (0, 0, 5), 12.0),
    'front_meso': ((0, 32, 2.8), (0, 0, 2.8), 4.0),
    'side_meso': ((-32, 0, 5), (0, 0, 5), 4.0),
    'front_upper': ((0, 32, 6.1), (0, 0, 6.1), 4.0),
    'side_upper': ((-32, 0, 6.1), (0, 0, 6.1), 4.0),
}
WHOLE = ('front', 'oblique', 'side')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', nargs='+', type=Path)
    parser.add_argument('--views', nargs='+', choices=list(VIEWS), default=list(WHOLE))
    parser.add_argument('--output', type=Path,
                        help='Optional destination root containing preview/detail; requires one source folder.')
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(arguments)
    if args.output is not None and len(args.folders) != 1:
        parser.error('--output requires exactly one source folder to avoid overwriting other sources.')

    # Keep --help available without Blender; actual rendering runs inside Blender.
    import bpy
    import numpy as np
    from mathutils import Vector
    sys.path.insert(0, str(HERE.parent / 'iaac_mandelbrot_20261011'))
    import render_shared as shared

    for folder in args.folders:
        folder = folder.resolve()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        with np.load(folder / 'geometry.npz', allow_pickle=False) as saved:
            mesh = bpy.data.meshes.new('Saved actual column triangles')
            mesh.from_pydata(saved['xyz'].tolist(), [], saved['faces'].tolist())
            mesh.update()
        obj = bpy.data.objects.new(folder.parent.name + '_' + folder.name, mesh)
        bpy.context.collection.objects.link(obj)
        shared.material(obj)
        scene, camera = shared.setup_scene(800, 16)

        for group, resolution, samples in (('preview', 800, 16), ('detail', 1000, 32)):
            names = [name for name in args.views if (name in WHOLE) == (group == 'preview')]
            if not names:
                continue
            output = (args.output.resolve() if args.output is not None else folder) / group
            output.mkdir(parents=True, exist_ok=True)
            scene.render.resolution_x = scene.render.resolution_y = resolution
            scene.cycles.samples = samples
            for name in names:
                position, target, scale = VIEWS[name]
                camera.location = position
                camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
                camera.data.ortho_scale = scale
                scene.render.filepath = str(output / (name + '.png'))
                bpy.ops.render.render(write_still=True)

            receipt = output / 'render_receipt.json'
            previous = json.loads(receipt.read_text(encoding='utf8')).get('views', {}) if receipt.exists() else {}
            previous.update({name: VIEWS[name] for name in names})
            shared.dump(receipt, dict(
                geometry=str(folder / 'geometry.npz'), engine='Blender Cycles',
                version=bpy.app.version_string, resolution=[resolution, resolution],
                samples=samples, views=previous, geometric_modifiers=[],
                normal_maps=False, extra_meshes=[],
                rendered_meshes=[obj.name],
                material='Existing uniform mineral; flat geometric normals',
                source_recipe='iaac_mandelbrot_20261011/render_shared.py',
                scope='Fixed column cameras; actual saved triangles only. No render subdivision, added geometry, maps, retouching or visibility optimization.'))
        print('RENDERED', folder, flush=True)


if __name__ == '__main__':
    main()
