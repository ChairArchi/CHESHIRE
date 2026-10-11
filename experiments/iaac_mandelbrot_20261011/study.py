"""Bounded IAAC-inspired gate POC. No existing CHESHIRE operator is modified.

Three comparable paths from one rounded, sparsely folded carrier:
Task36 control, radial escape-field response, Task36 field modulation.
The finite Mandelbulb test is neither an exact signed distance nor IAAC code.
"""
from pathlib import Path
import argparse, json, sys, shutil
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree
import trimesh

HERE = Path(__file__).resolve().parent
TREE = HERE.parents[1]
sys.path.insert(0, str(TREE / 'src'))
from cheshire.reference_subdivision import ArrayMesh, topology, fields, mean_incident, unit
from cheshire import task36_growth as growth, task33_folds as folds
from cheshire.artifact_root import ArtifactRoot

DEFAULT_ROOT = 'E:/CHESHIRE_DATA/iaac_mandelbrot_20261011'
KNOTS = np.array([0, .08, .18, .30, .42, .5, .58, .70, .82, .92, 1.])
CENTRES = np.array([[-5.25,0,0],[-5.18,.04,1.9],[-5.05,.08,4.7],[-4.4,.16,7.7],
    [-2.4,.12,9.7],[0,.05,10.4],[2.4,.12,9.7],[4.4,.16,7.7],[5.05,.08,4.7],[5.18,.04,1.9],[5.25,0,0]])
CURVE = CubicSpline(KNOTS, CENTRES, bc_type=((1,[0,0,24]),(1,[0,0,-24])))

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def frame(s):
    c = CURVE(s)
    d = CURVE(s, 1)
    a = unit(np.column_stack([d[:,2], np.zeros(len(s)), -d[:,0]]))
    return c, a

def reflect(mesh, chart):
    # Construct from the canonical half. Never average opposite folds.
    target = chart.copy(); target[:,0] = 1-target[:,0]
    distance, ids = cKDTree(chart).query(target)
    assert distance.max() < 1e-10
    assert np.array_equal(ids[ids], np.arange(len(ids))), 'Ambiguous mirror chart'
    right = chart[:,0] > .5+1e-12
    mesh.xyz[right] = mesh.xyz[ids[right]] * np.array([-1,1,1])
    mesh.xyz[np.abs(chart[:,0]-.5)<1e-12,0] = 0
    return ids

def carrier():
    # Curved samples BEFORE subdivision; an octagon is not frozen by retention.
    s = np.linspace(0,1,33); angle = np.arange(16)*2*np.pi/16
    q = np.minimum(s,1-s)
    c,a = frame(s)
    width = np.interp(q, [0,.10,.23,.35,.44,.5], [1.22,1.01,.96,1.28,1.02,.85])
    depth = np.interp(q, [0,.12,.25,.37,.5], [.97,.99,1.02,1.13,.90])
    phase = 1.2*np.sin(2*np.pi*q)
    seed = 1+.11*np.cos(3*(angle[None,:]-phase[:,None]))+.055*np.sin(2*(angle[None,:]-phase[:,None]))
    grid = c[:,None,:]+a[:,None,:]*(width[:,None]*seed*np.cos(angle)[None,:])[:,:,None]
    grid[:,:,1] += depth[:,None]*seed*np.sin(angle)[None,:]
    ids = np.arange(33*16).reshape(33,16)
    side = np.stack([ids[:-1],np.roll(ids[:-1],-1,1),np.roll(ids[1:],-1,1),ids[1:]],-1).reshape(-1,4)
    cap0,cap1 = len(grid.reshape(-1,3)),len(grid.reshape(-1,3))+1
    caps = [[cap0,ids[0,(j+2)%16],ids[0,j+1],ids[0,j]] for j in range(0,16,2)]
    caps += [[cap1,ids[-1,j],ids[-1,j+1],ids[-1,(j+2)%16]] for j in range(0,16,2)]
    xyz = np.concatenate([grid.reshape(-1,3),c[[0,-1]]])
    faces = np.concatenate([side,np.array(caps)])
    chart = np.stack(np.broadcast_arrays(s[:,None],np.cos(angle)[None,:],np.sin(angle)[None,:]),-1).reshape(-1,3)
    chart = np.concatenate([chart,[[0,0,0],[1,0,0]]])
    mesh = ArrayMesh(xyz,faces,np.full(len(xyz),-1,np.int8),xyz.copy(),np.full((len(faces),3),-1,np.int64),0)
    reflect(mesh,chart);mesh.rest = mesh.xyz.copy()
    topology(mesh)
    return mesh,chart

def escape_field(c, power=5, iterations=18, bailout=4.):
    """z <- spherical_power(z,p)+c, z0=0; finite escape, no random noise.

    The continuous escape count smooths the SCALAR classification transition;
    it does not filter or average any mesh coordinates. Unescaped is only a
    finite-iteration classification, not proof of membership in an infinite set.
    """
    z = np.zeros_like(c); alive = np.ones(len(c),bool)
    nu = np.full(len(c),float(iterations)); escaped = np.zeros(len(c),bool)
    for step in range(iterations):
        idx = np.flatnonzero(alive)
        if not len(idx): break
        zz = z[idx]; r = np.linalg.norm(zz,axis=1)
        polar = np.arccos(np.divide(zz[:,2],r,out=np.ones_like(r),where=r>1e-14).clip(-1,1))
        azimuth = np.arctan2(zz[:,1],zz[:,0])
        rp = r**power
        z[idx] = rp[:,None]*np.column_stack([np.sin(power*polar)*np.cos(power*azimuth),
            np.sin(power*polar)*np.sin(power*azimuth),np.cos(power*polar)])+c[idx]
        rr = np.linalg.norm(z[idx],axis=1); outside = rr>bailout
        hit = idx[outside]
        nu[hit] = step+2-np.log(np.log(rr[outside]))/np.log(power)
        alive[hit] = False; escaped[hit] = True
    return np.tanh((nu-3.)/1.25), nu, ~escaped

def field_at(xyz, chart):
    s = chart[:,0]; q = np.minimum(s,1-s)
    c,a = frame(s); offset = xyz-c
    u = (offset*a).sum(1); v = offset[:,1]
    phase = .3+2.1*np.sin(2*np.pi*q)
    # One bent domain per support-to-crown half, mirrored geometrically.
    # No repeated independent bulb meshes and no stacked column modules.
    domain = np.column_stack([(u*np.cos(phase)-v*np.sin(phase))/1.35,
        (u*np.sin(phase)+v*np.cos(phase))/1.35,
        3.7*(q-.25)+.13*v])
    h,nu,inside = escape_field(domain)
    foot = np.clip(q/.045,0,1);foot = foot*foot*(3-2*foot)
    return h,dict(domain=domain,escape_count=nu,finite_inside=inside,foot_envelope=foot)

def interpolate_chart(chart, t, nf):
    return np.concatenate([chart,chart[t['edges']].mean(1),mean_incident(chart[t['a']],t['fi'],nf)])

def advance(mesh, chart, mode, generation):
    t = topology(mesh); nv = len(mesh.xyz); ne = len(t['edges']); nf = len(mesh.faces)
    newchart = interpolate_chart(chart,t,nf)
    if mode=='DIRECT':
        out,_,_,_ = folds.refine(mesh,dict(carrier=mesh.rest,chart=chart),carrier_smoothing=False,smooth_geometry=False)
        incoming = out.xyz.copy()
        h,record = field_at(incoming,newchart)
        c,a = frame(newchart[:,0]); off = incoming-c
        radial = unit(a*(off*a).sum(1)[:,None]+np.column_stack([np.zeros(len(off)),off[:,1],np.zeros(len(off))]))
        amplitude = {1:.26,2:.14,3:.075,4:.045}[generation]
        displacement = amplitude*h*record['foot_envelope']
        out.xyz += radial*displacement[:,None]
        record.update(signed_field=h,requested_radial_displacement=displacement)
        description = 'Existing bilinear quad refinement; all vertices move radially by current-point escape field'
    else:
        # Task36's column end selector receives material arc for this call;
        # this fixes the two feet, rather than treating the crown as a top cap.
        adapted_rest = mesh.rest.copy();adapted_rest[:,2] = chart[:,0]
        adapted = ArrayMesh(mesh.xyz,mesh.faces,mesh.classes,adapted_rest,mesh.anchors,mesh.generation)
        adapted.surface = getattr(mesh,'surface','mean')
        out,op = growth.step(adapted,face_gain=.35,edge_gain=.10,feedback=.85,
            inherited_bias=.35,vertex_memory=1,mode='interpolating',surface='mean')
        out.rest = np.concatenate([mesh.rest,mesh.rest[t['edges']].mean(1),mesh.rest[mesh.faces].mean(1)])
        record = dict(support_radius=op['support_radius'],face_bend=op['face_bend'])
        if mode=='HYBRID':
            fc = newchart[nv+ne:];ec = newchart[nv:nv+ne]
            hf,rf = field_at(op['face_base'],fc);he,_ = field_at(op['edge_base'],ec)
            face_factor = .25+1.25*hf
            edge_factor = .55+.40*he
            out.xyz[nv+ne:] = op['face_base']+op['face_vector']*face_factor[:,None]
            out.xyz[nv:nv+ne] = op['edge_base']+op['edge_vector']*edge_factor[:,None]
            record.update(face_field=hf,face_multiplier=face_factor,edge_multiplier=edge_factor,
                face_domain=rf['domain'],face_escape_count=rf['escape_count'])
            description = 'Existing Task36 current-geometry support/bend growth; field reverses/modulates newborn face offsets and modulates edge offsets'
        else:
            description = 'Unmodified Task36 interpolating current-geometry growth; no fractal field'
        assert np.array_equal(out.xyz[:nv],mesh.xyz), 'Unexpected old-vertex movement'
    reflect(out,newchart)
    old_delta = float(np.max(np.linalg.norm(out.xyz[:nv]-mesh.xyz,axis=1)))
    return out,newchart,record,dict(operation=description,old_vertex_max_movement=old_delta,
        separate_geometric_smoothing=False,CC_coordinate_averaging=False,
        cap_policy='Two feet fixed by material arc; crown free',
        field_power=5 if mode!='CONTROL' else None,field_iterations=18 if mode!='CONTROL' else None)

def save(root,mode,stage,mesh,chart,record,metadata,mirror_callback=None):
    folder = root.resolve(mode+'/'+stage)
    folder.mkdir(parents=True,exist_ok=True)
    assert not list(folder.iterdir()), 'Checkpoint already exists; never overwrite'
    mirror = (mirror_callback or reflect)(mesh,chart)
    t = topology(mesh); f = fields(mesh,t)
    native = growth.native(mesh);xyz = native.xyz;tri = native.faces[:,:3]
    area = np.linalg.norm(np.cross(xyz[tri[:,1]]-xyz[tri[:,0]],xyz[tri[:,2]]-xyz[tri[:,0]]),axis=1)/2
    assert np.isfinite(xyz).all(), 'Non-finite physical coordinates'
    assert area.min()>1e-12, 'Degenerate physical triangle area <= 1e-12'
    np.savez_compressed(folder/'checkpoint.npz',xyz=mesh.xyz,faces=mesh.faces,classes=mesh.classes,
        rest=mesh.rest,anchors=mesh.anchors,generation=mesh.generation,chart=chart)
    np.savez_compressed(folder/'geometry.npz',xyz=xyz,faces=tri)
    np.save(folder/'mirror_pairs.npy',mirror)
    if record:np.savez_compressed(folder/'operation_fields.npz',**record)
    trimesh.Trimesh(xyz,tri,process=False).export(folder/'gate.ply')
    dump(folder/'generation.json',dict(candidate=mode,stage=stage,**metadata,
        control_vertices=len(mesh.xyz),control_quads=len(mesh.faces),physical_vertices=len(xyz),physical_triangles=len(tri),
        bounds=[xyz.min(0).tolist(),xyz.max(0).tolist()],minimum_triangle_area=float(area.min()),
        control_dihedral_median_degrees=float(np.median(f['angles'])),
        control_nearly_flat_edge_fraction=float((f['angles']<1).mean()),
        interpretation='Dihedral fraction is a diagnostic, not an aesthetic pass criterion',
        self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication='NOT_CHECKED',
        physical_surface='Explicit Task36 quad-centre fans, identical for checking/render/export'))
    shutil.copy2(__file__,folder/'recipe.py')
    print('GENERATED',mode,stage,len(xyz),len(tri),'old_delta',metadata.get('old_vertex_max_movement'),flush=True)

def load(folder):
    g = np.load(folder/'checkpoint.npz')
    m = ArrayMesh(*[g[k] for k in ('xyz','faces','classes','rest','anchors')],int(g['generation']))
    m.surface = 'mean'
    return m,g['chart']

def main():
    parser = argparse.ArgumentParser();parser.add_argument('--output-root',default=DEFAULT_ROOT)
    parser.add_argument('--mode',choices=['CONTROL','DIRECT','HYBRID','ALL'],default='ALL')
    parser.add_argument('--last',type=int,default=3);parser.add_argument('--resume',type=int,default=0)
    args = parser.parse_args();assert 1<=args.last<=4 and 0<=args.resume<args.last
    root = ArtifactRoot(Path(args.output_root));root.path.mkdir(parents=True,exist_ok=True)
    # Minimal verification of the new field, not a repository regression suite.
    h,_,inside = escape_field(np.array([[0.,0,0],[3.,0,0]]))
    assert inside.tolist()==[True,False] and h[0]>h[1]
    if not root.resolve('COMMON/G00/checkpoint.npz').exists():
        m,ch = carrier();save(root,'COMMON','G00',m,ch,{},dict(operation='Rounded continuous gate, sparse broad twisting fold seeds; no ornament input'))
    for mode in (['CONTROL','DIRECT','HYBRID'] if args.mode=='ALL' else [args.mode]):
        mesh,chart = load(root.resolve(('COMMON/G00' if args.resume==0 else mode+f'/G{args.resume:02}')))
        for generation in range(args.resume+1,args.last+1):
            mesh,chart,record,meta = advance(mesh,chart,mode,generation)
            save(root,mode,f'G{generation:02}',mesh,chart,record,meta)

if __name__=='__main__':main()
