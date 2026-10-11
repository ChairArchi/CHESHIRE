"""One applied Catmull-Clark pass for two saved closed solids, not new growth."""
from pathlib import Path
import argparse
import json
import shutil
import sys
import bpy
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('parents', nargs='+', type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
for parent in args.parents:
    output = parent.with_name(parent.name+'_CC1')
    if output.exists():
        raise FileExistsError('Existing result preserved: '+str(output))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    with np.load(parent/'geometry.npz', allow_pickle=False) as data:
        mesh = bpy.data.meshes.new('Actual triangular Boolean surface')
        mesh.from_pydata(data['xyz'].tolist(), [], data['faces'].tolist())
        mesh.update()
    obj = bpy.data.objects.new('Applied CC1', mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new('One actual CC finish', 'SUBSURF')
    modifier.subdivision_type = 'CATMULL_CLARK'
    modifier.levels = modifier.render_levels = 1
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = obj.data
    mesh.calc_loop_triangles()
    xyz = np.array([v.co[:] for v in mesh.vertices], dtype=np.float64)
    faces = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64)
    output.mkdir(parents=True)
    np.savez_compressed(output/'geometry.npz', xyz=xyz, faces=faces)
    record = dict(parent=str(parent), candidate=parent.parent.name,
        label=output.name, operation='One applied Blender Catmull-Clark pass on saved triangular solid; resulting quads triangulated for export',
        subdivision_passes=1, separate_geometric_smoothing=False,
        triangle_input=True, crease_weights_added=False,
        warning='Finishing diagnostic only. Irregular Boolean triangle stencils can introduce uneven curvature; no remeshing or tag transfer.',
        quick_integrity='NOT_CHECKED', self_intersection='NOT_CHECKED',
        thickness_structure_fabrication='NOT_CHECKED', blender_version=bpy.app.version_string)
    (output/'generation.json').write_text(json.dumps(record, indent=2), encoding='utf8')
    shutil.copy2(__file__, output/'cc_finish.py')
    print('APPLIED_CC1', output, len(xyz), len(faces), flush=True)
