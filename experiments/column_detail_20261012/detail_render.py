"""Identical actual-geometry close-ups; camera changes only, no mesh edits."""
from pathlib import Path
import argparse
import sys
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'iaac_mandelbrot_20261011'))
import render_shared as shared

VIEWS = {
    'front_meso': ((0, 32, 2.8), (0, 0, 2.8), 4.0),
    'front_micro': ((0, 32, 2.8), (0, 0, 2.8), 1.2),
    'side_meso': ((-32, 0, 5.0), (0, 0, 5.0), 4.0),
    'side_micro': ((-32, 0, 5.0), (0, 0, 5.0), 1.2),
    'front_zone': ((0, 32, 6.2), (0, 0, 6.2), 1.2),
    'side_zone': ((-32, 0, 3.5), (0, 0, 3.5), 1.2),
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('folders', nargs='+', type=Path)
parser.add_argument('--views', nargs='+', choices=list(VIEWS), default=list(VIEWS))
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
folders = args.folders
for folder in folders:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    with np.load(folder / 'geometry.npz', allow_pickle=False) as g:
        mesh = bpy.data.meshes.new('Saved actual triangles')
        mesh.from_pydata(g['xyz'].tolist(), [], g['faces'].tolist())
        mesh.update()
    obj = bpy.data.objects.new(folder.parent.name + '_' + folder.name, mesh)
    bpy.context.collection.objects.link(obj)
    shared.material(obj)
    scene, camera = shared.setup_scene(1000, 32)
    output = folder / 'detail'
    output.mkdir(exist_ok=True)
    for name in args.views:
        position, target, scale = VIEWS[name]
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(output / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    receipt = output / 'render_receipt.json'
    previous = {}
    if receipt.exists():
        import json
        previous = json.loads(receipt.read_text(encoding='utf8')).get('views', {})
    previous.update({name: VIEWS[name] for name in args.views})
    shared.dump(receipt, dict(
        geometry=str(folder / 'geometry.npz'), engine='Blender Cycles',
        resolution=[1000, 1000], samples=32, views=previous,
        geometric_modifiers=[], normal_maps=False, extra_meshes=[],
        material='Existing uniform mineral; flat geometric normals',
        scope='Fixed orthographic close-ups across candidates; no visibility optimization, retouching, or artificial detail.'))
    print('DETAIL_RENDERED', folder, flush=True)
