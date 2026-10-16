"""Render saved native variation meshes without geometry modifiers or LOD."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Vector


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024**2), b''):
            h.update(b)
    return h.hexdigest()


def ah(a):
    return hashlib.sha256(memoryview(np.ascontiguousarray(a)).cast('B')).hexdigest()


def material(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = .66
    if name.startswith(('A ', 'B ')):
        bs.inputs['Alpha'].default_value = .25
    return m


def setup(size, samples):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.cycles.transparent_max_bounces = 24
    prefs = bpy.context.preferences.addons['cycles'].preferences
    gpu = None
    for backend in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            ds = [d for d in prefs.devices if d.type == backend]
            if not ds:
                continue
            for d in prefs.devices:
                d.use = d.type == backend
            s.cycles.device = 'GPU'
            gpu = dict(backend=backend, devices=[d.name for d in ds])
            break
        except Exception:
            continue
    if gpu is None:
        raise RuntimeError('A verified render GPU is required.')
    s.render.resolution_x = size
    s.render.resolution_y = size
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.055,.065,.075,1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    s.view_settings.view_transform = 'AgX'
    s.view_settings.look = 'AgX - Medium High Contrast'
    data = bpy.data.cameras.new('Camera')
    cam = bpy.data.objects.new('Camera', data)
    bpy.context.collection.objects.link(cam)
    data.type = 'ORTHO'
    data.lens = 70
    s.camera = cam
    return s, cam, gpu


def point(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def lights(height, mid):
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)
    for name, pos, energy, size in (
        ('Key', (-.55,-.75,.35), 1100, .45),
        ('Fill', (.65,-.25,.08), 240, .55),
        ('Rim', (.20,.50,.45), 850, .32)):
        data = bpy.data.lights.new(name,'AREA')
        data.energy = energy * height**2 / 100
        data.shape = 'DISK'
        data.size = size*height
        o = bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(o)
        o.location = (pos[0]*height,pos[1]*height,mid+pos[2]*height)
        point(o,(0,0,mid))


def surface(path):
    with np.load(path, allow_pickle=False) as d:
        x = np.asarray(d['xyz'], np.float32)
        t = np.asarray(d['faces'], np.int32)
    if t.shape[1] != 3 or not np.isfinite(x).all():
        raise ValueError('Actual native triangles required.')
    mesh = bpy.data.meshes.new('Saved native surface')
    mesh.vertices.add(len(x))
    mesh.vertices.foreach_set('co',x.ravel())
    mesh.loops.add(t.size)
    mesh.loops.foreach_set('vertex_index',t.ravel())
    mesh.polygons.add(len(t))
    mesh.polygons.foreach_set('loop_start',3*np.arange(len(t),dtype=np.int32))
    mesh.polygons.foreach_set('loop_total',np.full(len(t),3,np.int32))
    mesh.polygons.foreach_set('use_smooth',np.ones(len(t),bool))
    obj = bpy.data.objects.new('Actual generation',mesh)
    bpy.context.collection.objects.link(obj)
    # Read back every displayed coordinate and index before rendering.
    rx = np.empty_like(x)
    rt = np.empty(t.size,np.int32)
    mesh.vertices.foreach_get('co',rx.ravel())
    mesh.loops.foreach_get('vertex_index',rt)
    if ah(rx)!=ah(x) or ah(rt)!=ah(t.ravel()) or len(obj.modifiers):
        raise ValueError('Native render readback differs.')
    return obj, x, dict(vertices=len(x),triangles=len(t),
        display_xyz_sha256=ah(rx),display_triangles_sha256=ah(rt))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--size',type=int,default=850)
    p.add_argument('--samples',type=int,default=24)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    started=time.perf_counter()
    plan=json.loads(a.plan.read_text(encoding='utf8'))
    a.output.mkdir(parents=True,exist_ok=False)
    scene,cam,gpu=setup(a.size,a.samples)
    gray=material('Ivory native geometry',(.70,.68,.63))
    palette=[(.06,.43,.68),(.06,.60,.49),(.78,.41,.075),(.56,.16,.37),(.37,.28,.67),(.69,.65,.14)]
    mats=[material('Structural band '+str(i+1),c) for i,c in enumerate(palette)]
    rows=[]
    for item in plan['items']:
        path=Path(item['geometry'])
        binding=sha(path)
        obj,x,counts=surface(path)
        lo=x.min(0).astype(float);hi=x.max(0).astype(float)
        H=float(hi[2]-lo[2]);mid=float((lo[2]+hi[2])/2)
        lights(H,mid)
        obj.data.materials.append(gray)
        views=item.get('views', ['whole'])
        imgs=[]
        for view in views:
            if view=='whole':
                target=(0,0,mid)
                scale=float(plan.get('common_scale',H*1.12))
                direction=np.array([.17,-1,.06])
            elif view=='oblique':
                target=(0,0,mid)
                scale=H*1.13
                direction=np.array([.72,-1,.10])
            elif view=='crown':
                target=(0,0,float(lo[2]+.80*H))
                scale=max(float(np.ptp(x[:,0]))*1.30,H*.40)
                direction=np.array([.54,-1,.16])
            elif view=='body':
                target=(0,0,float(lo[2]+.53*H))
                scale=max(float(np.ptp(x[:,0]))*1.24,H*.38)
                direction=np.array([.60,-1,.08])
            else:
                spec=item['custom_views'][view]
                target=spec['target'];scale=spec['scale'];direction=np.asarray(spec['direction'])
            cam.location=Vector(target)+Vector(direction/direction.dot(direction)**.5)*(H*2.5)
            point(cam,target)
            cam.data.ortho_scale=scale
            dest=a.output/(item['id']+'_'+view+'.png')
            scene.render.filepath=str(dest)
            bpy.ops.render.render(write_still=True)
            imgs.append(dict(view=view,path=str(dest),sha256=sha(dest),target=list(target),scale=scale,
                camera_position=list(cam.location)))
        if item.get('color',False):
            bands=int(item.get('bands',4))
            active_mats=mats
            if item.get('face_colors'):
                tags=np.load(item['face_colors'],allow_pickle=False)
                if tags.shape!=(len(obj.data.polygons),):
                    raise ValueError('Saved colors must bind every actual native triangle.')
                palette=item['palette']
                active_mats=[material(row['name'],tuple(row['rgb'])) for row in palette]
                meaning=item['color_meaning']
            else:
                cp=Path(item['controls'])
                with np.load(cp,allow_pickle=False) as d:
                    q=d['faces'];chart=d['chart']
                    axial=np.clip(chart[q,0].mean(1),0,1)
                if 4*len(q)!=len(obj.data.polygons):
                    raise ValueError('Color inheritance requires exact quad-centre fans.')
                tags=np.repeat(np.minimum((axial*bands).astype(np.int32),bands-1)%len(mats),4)
                meaning='Inherited early material-t design segments, not measured curvature classes.'
            obj.data.materials.clear()
            for m in active_mats:obj.data.materials.append(m)
            obj.data.polygons.foreach_set('material_index',tags)
            actual=np.empty_like(tags);obj.data.polygons.foreach_get('material_index',actual)
            if ah(tags)!=ah(actual):raise ValueError('Color readback mismatch.')
            target=(0,0,mid);cam.location=Vector(target)+Vector((.17,-1,.06)).normalized()*H*2.5
            point(cam,target);cam.data.ortho_scale=float(plan.get('common_scale',H*1.12))
            color_name=item.get('color_name','bands')
            dest=a.output/(item['id']+'_'+color_name+'.png');scene.render.filepath=str(dest)
            bpy.ops.render.render(write_still=True)
            imgs.append(dict(view=color_name,path=str(dest),sha256=sha(dest),bands=bands,meaning=meaning,
                actual_tags_sha256=ah(tags)))
        if sha(path)!=binding:raise ValueError('Saved source changed while rendering.')
        rows.append(dict(id=item['id'],geometry=str(path),source_sha256=binding,native=counts,
            bounds=[lo.tolist(),hi.tolist()],images=imgs))
        data=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data)
        print('VARIATION_RENDERED',item['id'],flush=True)
    record=dict(kind='ACTUAL_EARLY_GENERATION_NATIVE_VARIATION_RENDER',items=rows,device=gpu,
        size=a.size,samples=a.samples,geometry_modifiers=False,LOD=False,normal_maps=False,
        smooth_normals_display_only=True,renderer_sha256=sha(__file__),plan_sha256=sha(a.plan),
        elapsed_seconds=time.perf_counter()-started)
    (a.output/'RENDER_RECEIPT.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
