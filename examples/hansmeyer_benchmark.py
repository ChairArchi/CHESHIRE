"""Task28 simple specimen and saved nonstationary calls to existing sharp CC."""
import argparse,gc,sys,shutil,json,hashlib
from pathlib import Path
from math import cos,sin,pi,dist
from time import perf_counter
import numpy as np
from compas.datastructures import Mesh

REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'examples'),str(REPO/'tools')]
from cross_cell_crease_study import read,write,gz_write,file_hash,raw_mesh,mesh_to_data
from hero_design_sprint import guarded
from generational_folding import verify_obj
from cheshire import save_mesh,inspect_mesh
from cheshire.sharp_subdivision import sharp_subdivide_once,WEIGHTS
from cheshire.execution import ExecutionBudget

BASELINE='a9974d39f8e92c01c454e455399ca038fb8513cc'
SOURCES=['examples/hansmeyer_benchmark.py','src/cheshire/weighted_subdivision.py',
         'src/cheshire/generational_subdivision.py','src/cheshire/sharp_subdivision.py']


def specimen_definition():
    return dict(schema='TASK28_SIMPLE_COLUMN_V1',sections=[dict(z=z,width=900,depth=500,center=[0,0,z]) for z in [0,650,1800]],
        perimeter=8,angular_offset=pi/8,frame=dict(T=[0,0,1],U=[1,0,0],V=[0,1,0]),
        caps='Four coplanar quads per end: center, ring[2j], ring[2j+1], ring[2j+2]. Bottom reversed.',
        units='Same unresolved coordinate units as old experiments; no rescaling',
        input_variation='Unequal two longitudinal band lengths only; constant ellipse, straight centerline, no ornament or desired final silhouette.')


def specimen(definition):
    points=[];faces=[];rings=[]
    for s in definition['sections']:
        ring=[]
        for j in range(8):
            a=j*pi/4+definition['angular_offset'];ring.append(len(points))
            points.append([s['width']/2*cos(a),s['depth']/2*sin(a),s['z']])
        rings.append(ring)
    for lo,hi in zip(rings,rings[1:]):
        for j in range(8):faces.append([lo[j],lo[(j+1)%8],hi[(j+1)%8],hi[j]])
    for ring,z,reverse in [(rings[0],0,True),(rings[-1],1800,False)]:
        c=len(points);points.append([0,0,z])
        for j in range(0,8,2):
            q=[c,ring[j],ring[(j+1)%8],ring[(j+2)%8]];faces.append(q[::-1] if reverse else q)
    m=Mesh.from_vertices_and_faces(points,faces)
    assert m.is_valid() and m.is_closed() and m.is_connected() and m.is_manifold()
    return m


def directory(root,name,generation):
    return root/'candidates'/name/f'G{generation}'


def restore_state(data):
    for k in ['origins','face_ancestry']:data[k]={int(f):r for f,r in data[k].items()}
    return data


def phase(weights,units='RATIO',u_map=None,source=None):
    return dict(weights={k:float(weights.get(k,0)) for k in WEIGHTS},offset_units=units,
        u_map=u_map or {},unknown_u=.5 if u_map and '(6,6)' in u_map else 0.,source=source)


def recovered():
    inv=read(Path('E:/CHESHIRE_DATA/task28/analysis/previous_success_inventory.json'))['items']
    find=lambda name:next(r for r in inv if r['name']==name)
    b=find('C11 macro prefix / C07')['exact_subdivision_weights']
    c=find('C26_column');h=find('H1 mantle_macro / cleft_articulation')
    return dict(C11A=phase(b[0],source='Task20/21 C11 macro_CC_1'),C11B=phase(b[1],source='Task20/21 C11 macro_CC_2'),
        C26=phase(c['exact_subdivision_weights'][0],u_map=c['u_map'],source='Task22 C26'),
        H1=phase(h['exact_subdivision_weights'][0],'ABSOLUTE',h['u_map'],'Task24 H1 mantle_macro'),
        H1B=phase(h['exact_subdivision_weights'][1],'ABSOLUTE',h['u_map'],'Task24 H1 cleft_articulation'),
        CURVE=phase(find('H1_CURVATURE_G2')['exact_subdivision_weights'][0],'ABSOLUTE',source='Task25 H1_CURVATURE_G2'),
        AMP=phase(find('H1_AMPLIFIED_G2')['exact_subdivision_weights'][0],'ABSOLUTE',source='Task25 H1_AMPLIFIED_G2'),
        GENTLE=phase(find('H1_CONVERGENCE_G2')['exact_subdivision_weights'][0],'ABSOLUTE',source='Task25 H1_CONVERGENCE_G2'),
        ZERO=phase({},source='Existing all-zero backend; control or zero-valued later phase, no external smoothing modifier'))


def prepare(root):
    if (root/'definitions/specimen_definition.json').exists():raise ValueError('Preserve prepared input.')
    d=specimen_definition();m=specimen(d);write(root/'definitions/specimen_definition.json',d)
    g0=root/'input/G0';g0.mkdir(parents=True)
    state=dict(schema='TASK28_BENCHMARK_STATE_V1',generation=0,origins={},face_ancestry={f:f for f in m.faces()},completed=[],next=None)
    gz_write(g0/'geometry.json.gz',mesh_to_data(m));gz_write(g0/'state.json.gz',state);save_mesh(m,g0/'G0.obj')
    write(g0/'summary.json',dict(statistics=inspect_mesh(m),OBJ=verify_obj(m,g0/'G0.obj')))
    seeds=recovered();write(root/'definitions/recovered_subdivision_seeds.json',seeds)
    defs=[]
    def add(name,rows,hypothesis):defs.append(dict(id=name,pass_id='PASS1',rows=rows,hypothesis=hypothesis))
    for key in ['C11A','C11B','C26','H1','CURVE','AMP']:
        add('P1_'+key+'_REPEAT',[seeds[key]]*3,'Direct exact numeric seed replay, no Mola or spatial route; repeated forcing control.')
    add('P1_C11_PREFIX',[seeds['C11A'],seeds['C11B'],seeds['ZERO']],'Actual old first two macro rows and later zero CC phase, with Mola events omitted explicitly.')
    add('P1_CURVE_AFTER_CC',[seeds['ZERO'],seeds['CURVE'],seeds['CURVE']],'Exact Task25 relative G2 weight row after an actual prior split; no inherited gate geometry.')
    add('P1_AMP_AFTER_CC',[seeds['ZERO'],seeds['AMP'],seeds['AMP']],'Same matched relative G2 test with the recovered angular Eq4 row.')
    add('P1_OLD_ONLY',[phase(dict(w1=-.7,w2=-2.8))]*3,'Matched C26 with Eq10/11 absent.')
    add('P1_STANDARD',[seeds['ZERO']]*3,'True standard closed CC numeric control.')
    for n in [3,4,5]:add('P1_H1_AT_G'+str(n),[seeds['ZERO']]*(n-1)+[seeds['H1']],f'Exact old H1 macro coefficients at absolute CC{n}; old first H1 macro was CC4. Prior simple CC parents, not copied gate.')
    for r in defs:write(root/'definitions/candidates'/(r['id']+'.json'),r)
    write(root/'definitions/pass1.json',dict(candidates=[r['id'] for r in defs],hypothesis='Recover exact working ranges before new combinations',generation_roles='Repeated or direct historical prefix; selected diagnostic generations preserved.'))
    print('Prepared actual simple column',m.number_of_vertices(),m.number_of_faces(),len(defs),'replay definitions',flush=True)


def diagnostics(mesh,before=None,result=None):
    xyz=np.asarray([mesh.vertex_coordinates(v) for v in mesh.vertices()]);angles=[]
    normals={f:np.asarray(mesh.face_normal(f)) for f in mesh.faces()}
    for e in mesh.edges():
        a,b=mesh.edge_faces(e);angles.append(float(np.degrees(np.arccos(np.clip(normals[a]@normals[b],-1,1)))))
    areas=[]
    for f in mesh.faces():
        p=np.asarray(mesh.face_coordinates(f));c=p.mean(axis=0)
        areas.append(float(.5*np.linalg.norm(np.cross(p-c,np.roll(p,-1,axis=0)-c),axis=1).sum()))
    report=dict(statistics=inspect_mesh(mesh),bounds_min=xyz.min(axis=0).tolist(),bounds_max=xyz.max(axis=0).tolist(),
        coordinates_finite=bool(np.isfinite(xyz).all()),zero_unsigned_fan_faces=sum(a<1e-12 for a in areas),
        dihedral=dict(median=float(np.median(angles)),p90=float(np.quantile(angles,.9)),max=max(angles),fraction_over_45=float(np.mean(np.asarray(angles)>45))))
    if before is not None:
        from cheshire.creases import crease_subdivide_once
        plain=crease_subdivide_once(before,(),budget=ExecutionBudget(400000,400000,None)).mesh
        delta=np.asarray([dist(mesh.vertex_coordinates(v),plain.vertex_coordinates(v)) for v in mesh.vertices()])
        report['vs_same_parent_standard_CC']=dict(RMS=float(np.sqrt(np.mean(delta**2))),maximum=float(delta.max()),changed_vertices=int((delta>1e-9).sum()))
        report['eq4']=dict(eligible=result.metadata['later_generation_face_stencil']['eligible_faces'],fallback=result.metadata['later_generation_face_stencil']['fallback_faces'])
    return report


def run_stage(root,name,g):
    definition=read(root/'definitions/candidates'/(name+'.json'));d=directory(root,name,g)
    if d.exists():raise ValueError('Stage already exists; preserve outputs and use a new ID.')
    parent=root/'input/G0' if g==1 else directory(root,name,g-1)
    mesh=raw_mesh(read(parent/'geometry.json.gz'));state=restore_state(read(parent/'state.json.gz'));row=definition['rows'][g-1]
    if state['generation']!=g-1:raise ValueError('Wrong actual parent generation.')
    d.mkdir(parents=True);code={p:file_hash(REPO/p) for p in SOURCES}
    for p,h in code.items():
        q=root/'source_snapshots'/h/p
        if not q.exists():q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/p,q)
    write(d/'request.json',dict(candidate=definition,generation=g,parent=str(parent),parent_geometry_sha256=file_hash(parent/'geometry.json.gz'),parent_state_sha256=file_hash(parent/'state.json.gz'),source_hashes=code,baseline=BASELINE))
    t=perf_counter();lengths=[mesh.edge_length(e) for e in mesh.edges()];scale=float(np.mean(lengths)) if row['offset_units']=='RATIO' else 1.
    weights={k:v*(scale if k in ['wf','we','wp'] else 1) for k,v in row['weights'].items()}
    result=sharp_subdivide_once(mesh,weights,u_map=row['u_map'],unknown_u=row['unknown_u'],origin_lineage=state['origins'],budget=ExecutionBudget(200000,200000,None),current_generation=g-1)
    new_state=dict(schema=state['schema'],generation=g,origins=result.origin_lineage,
        face_ancestry={r['id']:state['face_ancestry'][r['source_face']] for r in result.metadata['face_sources']},
        completed=state['completed']+[dict(generation=g,declared=row,resolved_weights=weights,normal_offset_scale=scale)],
        next=definition['rows'][g] if g<len(definition['rows']) else None)
    summary=diagnostics(result.mesh,mesh,result);summary.update(status='COMPUTED',candidate=name,generation=g,parent=str(parent),declared=row,resolved_weights=weights,normal_offset_scale=scale)
    gz_write(d/'geometry.json.gz',mesh_to_data(result.mesh));gz_write(d/'state.json.gz',new_state);gz_write(d/'operator.json.gz',result.metadata)
    save_mesh(result.mesh,d/f'G{g}.obj');summary['OBJ']=verify_obj(result.mesh,d/f'G{g}.obj');summary['seconds']=perf_counter()-t
    summary['OBJ_bytes']=(d/f'G{g}.obj').stat().st_size;summary['geometry_sha256']=file_hash(d/'geometry.json.gz')
    summary['ordered_geometry_sha256']=hashlib.sha256(json.dumps(mesh_to_data(result.mesh),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    write(d/'summary.json',summary)
    print(name,'G'+str(g),summary['statistics']['face_count'],round(summary['seconds'],3),'s',flush=True)
    del mesh,result,state,new_state;gc.collect()


def worker(root,names,g):
    for name in names:
        definition=read(root/'definitions/candidates'/(name+'.json'))
        if g<=len(definition['rows']) and not directory(root,name,g).exists():run_stage(root,name,g)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--prepare',action='store_true')
    p.add_argument('--names',nargs='+');p.add_argument('--pass-id');p.add_argument('--generation',type=int,default=1);p.add_argument('--worker',action='store_true');p.add_argument('--tag')
    a=p.parse_args();root=a.output_root.resolve()
    if a.prepare:prepare(root)
    names=a.names or (read(root/'definitions'/('pass'+a.pass_id+'.json'))['candidates'] if a.pass_id else [])
    if names:
        if a.worker:worker(root,names,a.generation)
        else:
            tag=a.tag or ('G'+str(a.generation)+'_'+(a.pass_id or names[0]));logs=root/'logs'/tag
            if logs.exists():raise ValueError('Preserve previous logs; use a new tag.')
            r=guarded(['--output-root',str(root),'--names',*names,'--generation',str(a.generation),'--worker'],logs,worker_script=Path(__file__))
            print(r,flush=True);sys.exit(r['exit_code'])
