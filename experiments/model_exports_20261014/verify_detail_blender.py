"""Open the small exported original-detail PLY in the installed Blender."""
from pathlib import Path
import json
import bpy
import numpy as np

ROOT=Path('E:/CHESHIRE_DATA/exports/20261014/LATEST_COLUMN_SCALE_REFINED')
manifest=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf8'))
info=manifest['detail'];path=Path(info['path'])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.ply_import(filepath=str(path))
obj=bpy.context.active_object;mesh=obj.data
if len(mesh.vertices)!=info['vertices'] or len(mesh.polygons)!=info['triangles']:
    raise ValueError('Actual Blender import counts differ.')
with open(path,'rb') as stream:
    while stream.readline()!=b'end_header\n':pass
    expected=np.fromfile(stream,dtype='<f8',count=3*len(mesh.vertices)).astype(np.float32)
    faces=np.fromfile(stream,dtype=np.dtype([('n','u1'),('f','<i4',(3,))]),count=len(mesh.polygons))
actual=np.empty(3*len(mesh.vertices),np.float32)
mesh.vertices.foreach_get('co',actual)
indices=np.empty(len(mesh.loops),np.int32)
mesh.loops.foreach_get('vertex_index',indices)
if not np.array_equal(actual,expected) or not np.array_equal(indices,faces['f'].ravel()):
    raise ValueError('Actual Blender imported coordinates or indices differ.')
if not np.allclose(np.array(obj.matrix_world),np.eye(4),atol=1e-12):
    raise ValueError('Unexpected import axis transform.')
receipt=dict(passed=True,Blender_version=bpy.app.version_string,file=str(path),
    vertices=len(mesh.vertices),triangles=len(mesh.polygons),
    positions_equal_PLY_float32=True,triangle_indices_equal=True,axis_transform='identity',
    scope='Actual near-detail PLY imported in Blender. Full PLY was stream-verified against every native source coordinate and triangle, not fully reimported here.')
(ROOT/'BLENDER_IMPORT_VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(json.dumps(receipt))
