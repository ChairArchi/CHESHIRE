"""Image-inferred column study, not a reconstruction of Hansmeyer's source code.
Run with Blender --background --python build.py. No subdivision or smoothing.
"""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results_v2'; OUT.mkdir(exist_ok=True)

def chamfer(poly, t):
    return [tuple((1-t)*p[k]+t*q[k] for k in range(2))
            for i,p in enumerate(poly) for q in (poly[i-1],poly[(i+1)%len(poly)])]

square=[(-.62,-.62),(.62,-.62),(.62,.62),(-.62,.62)]
octagon=chamfer(square,.24)
hexadecagon=chamfer(octagon,.22)

def interp(z,knots):
    for (a,x),(b,y) in zip(knots,knots[1:]):
        if a<=z<=b:return x+(y-x)*(z-a)/(b-a)
    return knots[-1][1]

def column(stage):
    poly=[square,octagon,hexadecagon,hexadecagon][stage-1]
    n=len(poly)
    # Shared axial stations retain long planar shafts between localized ornaments.
    zs=[0,.45,1.05,1.32,1.63,2.08,2.45,3.12,3.5,3.82,4.05,4.35,4.72,5.1,5.75,6.15,6.52,6.85,7.3,8]
    profile=[(0,1),(.45,1),(1.05,1),(1.32,.78),(1.63,.49),(2.08,.82),(2.45,1),(3.12,1),(3.5,.68),(3.82,.38),(4.05,.38),(4.35,.74),(4.72,1.08),(5.1,1.08),(5.75,1),(6.15,.77),(6.52,.51),(6.85,.85),(7.3,1),(8,1)]
    verts=[]
    for z in zs:
        for i,(x,y) in enumerate(poly):
            a=math.atan2(y,x)
            r=math.hypot(x,y)
            scale=1 if stage==1 else (1+{2:.13,3:.32,4:1.0}[stage]*(interp(z,profile)-1))
            extra=0; lift=0
            if stage>=3:
                # Eight alternating polygon vertices become eight explicit wing ridges.
                parent=1.0 if i%2==0 else 0.0
                alternate=parent
                for center,width,amount,family,sign in [(1.32,.55,.90,parent,1),(4.35,.56,.80,alternate,-1),(6.85,.55,.75,parent,-1)]:
                    w=max(0,1-abs(z-center)/width)
                    extra+=amount*w*family;lift+=sign*.22*w*family
            if stage==4:
                # Children occupy intermediate sectors, retaining the parent wing field.
                child=1.0 if i%2==1 else 0.0
                for center,width,amount,sign in [(2.08,.4,.62,-1),(3.5,.38,.60,1),(6.15,.4,.62,1)]:
                    w=max(0,1-abs(z-center)/width)
                    extra+=amount*w*child;lift+=sign*.17*w*child
            rr=r*scale+extra
            verts.append((rr*math.cos(a),rr*math.sin(a),z+lift))
    faces=[]
    for j in range(len(zs)-1):
        for i in range(n):
            faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple((len(zs)-1)*n+i for i in range(n))])
    return verts,faces,n

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=640;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.12,.12,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.view_transform='AgX'
mat=bpy.data.materials.new('Matte neutral');mat.diffuse_color=(.65,.65,.65,1);mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.65,.65,.65,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.85
for name,loc,power,size in [('Key',(-4,-6,10),1400,5),('Fill',(5,-2,6),400,4),('Rim',(2,4,9),900,3)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size
    ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,4))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=9
reports=[]
for stage in range(1,5):
    vs,fs,n=column(stage)
    mesh=bpy.data.meshes.new('Column');mesh.from_pydata(vs,[],fs);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh)
    report={'stage':stage,'circumferential_vertices':n,'vertices':len(vs),'faces':len(fs),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume':bm.calc_volume(signed=True),'smoothing':False,'subdivision':False}
    assert report['nonmanifold_edges']==0 and report['volume']>0
    bm.free();mesh.calc_loop_triangles()
    tris=[tuple(t.vertices) for t in mesh.loop_triangles]
    report['zero_area_triangles']=sum(t.area<1e-10 for t in mesh.loop_triangles)
    assert report['zero_area_triangles']==0
    folder=OUT/f'stage_{stage:02d}';folder.mkdir(exist_ok=True)
    # Triangulation makes nonplanar wing facets unambiguous in all viewers.
    (folder/'column.obj').write_text(''.join('v %.9f %.9f %.9f\n'%v for v in vs)+''.join('f %d %d %d\n'%tuple(i+1 for i in t) for t in tris))
    (folder/'column.ply').write_text('ply\nformat ascii 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\nelement face %d\nproperty list uchar int vertex_indices\nend_header\n'%(len(vs),len(tris))+''.join('%.9f %.9f %.9f\n'%v for v in vs)+''.join('3 %d %d %d\n'%t for t in tris))
    ob=bpy.data.objects.new('Column',mesh);scene.collection.objects.link(ob);mesh.materials.append(mat)
    for view,pos in [('front',(0,-16,4)),('oblique',(10,-16,6.5))]:
        cam.location=pos;cam.rotation_euler=(Vector((0,0,4))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(ob,do_unlink=True);reports.append(report)
(OUT/'validation.json').write_text(json.dumps(reports,indent=2))
print('COLUMN_STUDY_COMPLETE',flush=True)
