"""Fixed actual-mesh views for the bounded cut/mirror/join study."""
from pathlib import Path
import argparse
import sys
import json
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'iaac_mandelbrot_20261011'))
import render_shared as shared

VIEWS = dict(front=((0,32,5),(0,0,5),14),
    oblique=((-18,28,16),(0,0,5),14), side=((-32,0,5),(0,0,5),14),
    front_meso=((0,32,5),(0,0,5),4), side_meso=((-32,0,5),(0,0,5),4))

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('folders', nargs='+', type=Path)
parser.add_argument('--views', nargs='+', choices=list(VIEWS), default=['front','oblique','side'])
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
for folder in args.folders:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    with np.load(folder/'geometry.npz', allow_pickle=False) as g:
        mesh = bpy.data.meshes.new('Saved actual Boolean result')
        mesh.from_pydata(g['xyz'].tolist(),[],g['faces'].tolist())
        mesh.update()
    obj = bpy.data.objects.new(folder.parent.name+'_'+folder.name,mesh)
    bpy.context.collection.objects.link(obj)
    shared.material(obj)
    scene, camera = shared.setup_scene(800,16)
    output = folder/'preview'
    output.mkdir(exist_ok=True)
    for name in args.views:
        position,target,scale = VIEWS[name]
        camera.location = position
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(output/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    receipt = output/'render_receipt.json'
    previous = json.loads(receipt.read_text(encoding='utf8')).get('views',{}) if receipt.exists() else {}
    previous.update({name:VIEWS[name] for name in args.views})
    shared.dump(receipt,dict(geometry=str(folder/'geometry.npz'),engine='Blender Cycles',
        resolution=[800,800],samples=16,views=previous,geometric_modifiers=[],
        normal_maps=False,extra_meshes=[],material='Uniform mineral, actual flat geometric normals',
        scope='Fixed cameras across all structural candidates; no mesh editing or render detail.'))
    print('RENDERED',folder,flush=True)
