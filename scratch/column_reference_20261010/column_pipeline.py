"""Progressive column generator: cage -> mass -> facets -> regional cuts -> CC.
Geometry settings are data. Each stage records its actual parent mesh hash.
"""
from flute_column import ROOT,solid,cutter
import numpy as np,trimesh,math,json,hashlib,argparse,subprocess
from pathlib import Path

def cage_mesh(rings):
    rings=np.asarray(rings);n=len(rings[0]);vs=rings.reshape((-1,3));fs=[]
    for j in range(len(rings)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i;fs.extend([(a,b,c),(a,c,d)])
    for i in range(1,n-1):fs.extend([(0,i+1,i),((len(rings)-1)*n,(len(rings)-1)*n+i,(len(rings)-1)*n+i+1)])
    m=trimesh.Trimesh(vs,np.array(fs),process=True);m.fix_normals();return m

def form_mass(rings,profile):
    bottom=np.asarray(rings[0]);top=np.asarray(rings[-1]);formed=[]
    for t,scale in profile:
        ring=(1-t)*bottom+t*top;axis=ring[:,:2].mean(axis=0);ring[:,:2]=axis+(ring[:,:2]-axis)*scale;formed.append(ring)
    return np.array(formed)

def cut_corners(rings,fraction):
    # Explicit edge interpolation, no averaging over neighboring faces.
    return np.array([[(1-fraction)*p+fraction*q for i,p in enumerate(ring) for q in (ring[i-1],ring[(i+1)%len(ring)])] for ring in rings])

def envelope(mesh):
    v=np.asarray(mesh.vertices);lo,hi=mesh.bounds;zs=np.unique(np.round(v[:,2],7));axis=(lo[:2]+hi[:2])/2
    rs=np.array([np.linalg.norm(v[np.isclose(v[:,2],z,atol=(hi[2]-lo[2])*1e-7),:2]-axis,axis=1).max() for z in zs])
    return lo,hi,axis,zs,rs

def regional_cut(current,context,regions):
    lo,hi,axis,zs,rs=context;h=hi[2]-lo[2];result=solid(current)
    for region in regions:
        a=lo[2]+h*region['low'];b=lo[2]+h*region['high'];levels=np.unique(np.r_[np.linspace(a,b,9),zs[(zs>a)&(zs<b)]])
        for k in range(region['count']):
            angle=region['phase']+2*math.pi*k/region['count'];sections=[]
            for z in levels:
                t=(z-a)/(b-a);strength=min(1,t/.16,(1-t)/.16);r=float(np.interp(z,zs,rs));radial=.16*r;center=r*(1.20-region['depth']*strength);tangent=r*region['width']
                sections.append([(axis[0]+(center+radial*math.cos(2*math.pi*j/8))*math.cos(angle)-tangent*math.sin(2*math.pi*j/8)*math.sin(angle),axis[1]+(center+radial*math.cos(2*math.pi*j/8))*math.sin(angle)+tangent*math.sin(2*math.pi*j/8)*math.cos(angle),float(z)) for j in range(8)])
            result=result-cutter(sections)
    data=result.to_mesh64();return trimesh.Trimesh(np.asarray(data.vert_properties)[:,:3],np.asarray(data.tri_verts),process=True)

def run(config,output):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Use a new output directory to preserve checkpoints')
    output.mkdir(parents=True);(output/'config.json').write_text(json.dumps(config,indent=2));history=[];parent=None
    def save(name,mesh,operation):
        nonlocal parent
        assert mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split())==1 and mesh.euler_number==2
        folder=output/name;folder.mkdir(exist_ok=True)
        for ext in ('obj','ply'):mesh.export(folder/('column.'+ext))
        (folder/'mesh.json').write_text(json.dumps(dict(vertices=mesh.vertices.tolist(),faces=mesh.faces.tolist())))
        digest=hashlib.sha256((folder/'column.obj').read_bytes()).hexdigest()
        record=dict(stage=name,operator=operation,parent_sha256=parent,sha256=digest,vertices=len(mesh.vertices),triangles=len(mesh.faces),watertight=True,components=1,genus=0)
        (folder/'stage.json').write_text(json.dumps(record,indent=2));history.append(record);parent=digest
        print(name,len(mesh.faces),flush=True);return folder
    n=config['sides'];h=config['height'];r=config['radius'];angles=np.arange(n)*2*math.pi/n+math.pi/n
    rings=np.array([[(r*math.cos(a),r*math.sin(a),z) for a in angles] for z in (0,h)])
    current=cage_mesh(rings);save('00_simple_mass',current,'polygonal_prism')
    rings=form_mass(rings,config['mass_profile']);current=cage_mesh(rings);save('01_mass_articulation',current,'insert_local_sections_and_radially_transform_previous_cage')
    rings=cut_corners(rings,config['corner_cut']);current=cage_mesh(rings);save('02_planar_corners',current,'explicit_corner_cut')
    context=envelope(current)
    current=regional_cut(current,context,config['regions']);save('03_regional_flutes',current,'regional_boolean_difference')
    current=regional_cut(current,context,config['children']);folder=save('04_transition_children',current,'additional_intermediate_regional_cuts_on_previous_mesh')
    if config.get('cc',False):
        target=output/'05_crease_cc';blender=ROOT.parent/'generative_gate_20261010/external/blender-4.5.4-windows-x64/blender.exe'
        with (output/'cc.log').open('w') as log:
            subprocess.run([str(blender),'-b','-t','4','--python',str(ROOT/'cc_trial.py'),'--',str(folder/'mesh.json'),str(target)],stdout=log,stderr=subprocess.STDOUT,check=True)
        current=trimesh.load(target/'stage_01/column.obj',force='mesh',process=True);save('05_crease_cc',current,'optional_one_level_crease_Catmull_Clark')
    (output/'run.json').write_text(json.dumps(dict(status='COMPLETE',stages=history,scope='progressive straight-column prototype; no ALICE or general gate integration',regional_selection='configured normalized bands; cutter scale derived from mass envelope',subdivision_role='optional refinement, not primary form generation'),indent=2))
    return history

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);args=p.parse_args();run(json.loads(Path(args.config).read_text()),args.output)
