"""Task34 actual triangle cuts, finite feature tracking and causal comparisons.

Material-ring edges are explicitly distinguished from world-plane cuts.
No ridge-continuity or between-plane solid certification is implied.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
import trimesh
from scipy.signal import find_peaks
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from task29_search import load_mesh
from task33_planar import inspect_segments
from cheshire.task32_morphology import triangles
from cheshire.task34_refolding import read_features,frame,refine,native,refold
from hero_design_sprint import guarded
ROOT=Path('E:/CHESHIRE_DATA/task34')


def state_at(stage):
    with np.load(Path(stage)/'formation_state.npz') as data:return dict(data)


def measure(request,tag):
    dest=ROOT/'analysis'/tag;dest.mkdir(parents=True,exist_ok=False)
    write_new(dest/'request.json',request);rows=[]
    planes=[(f'Z{z}',[0,0,z],[0,0,1],[1,0,0],[0,1,0]) for z in (650,1300,2200,2750,3050)]
    planes += [('MID_Y',[0,-18.533447265625,0],[0,1,0],[1,0,0],[0,0,1]),
               ('PIER_X',[-1950.036865234375,0,0],[1,0,0],[0,1,0],[0,0,1]),
               ('JOINT',[-1800,-18.533447265625,2900],[2**-.5,0,2**-.5],[2**-.5,0,-2**-.5],[0,1,0])]
    for item in request['items']:
        stage=Path(item['stage']);mesh=load_mesh(stage)
        model=trimesh.Trimesh(vertices=mesh.xyz,faces=triangles(mesh),process=False)
        cuts={};cutinfo=[]
        for name,origin,normal,u,v in planes:
            segments=trimesh.intersections.mesh_plane(model,normal,origin)
            uv=np.stack([(segments-np.asarray(origin))@u,(segments-np.asarray(origin))@v],axis=-1)
            cuts[name]=segments;cuts[name+'_UV']=uv
            check=inspect_segments(uv) if len(uv) else dict(segments=0)
            cutinfo.append(dict(name=name,origin=origin,normal=normal,u=u,v=v,**check))
        np.savez_compressed(dest/(item['id']+'_cuts.npz'),**cuts)
        row=dict(**item,mesh_sha256=sha(stage/'mesh.npz'),bounds=[mesh.xyz.min(0).tolist(),mesh.xyz.max(0).tolist()],
                 vertices=len(mesh.xyz),triangles=len(triangles(mesh)),cuts=cutinfo)
        if (stage/'formation_state.npz').exists():
            state=state_at(stage);records,signal,geometries=read_features(state);c,a,_=frame(state)
            profiles={};sections=[]
            # These material s values belong to the FIRST formation sampling.
            for label,s in request.get('material_samples',{}).items():
                r=int(np.argmin(abs(state['s']-s)));g=state['grid'][r];rest=state['rest'][r]
                theta=np.arange(512)*2*np.pi/512
                xyz=np.column_stack([np.interp(theta,state['theta'],g[:,k],period=2*np.pi) for k in range(3)])
                rr=np.column_stack([np.interp(theta,state['theta'],rest[:,k],period=2*np.pi) for k in range(3)])
                def projection(p):
                    o=p-c[r];return np.stack([o[:,[0,2]]@a[r],o[:,1]],axis=-1)
                xy=projection(xyz);raw=np.linalg.norm(xy,axis=1)-np.linalg.norm(projection(rr),axis=1)
                profiles[label+'_xyz']=xyz;profiles[label+'_excess']=raw;profiles[label+'_xy']=xy
                peaks,_=find_peaks(np.tile(raw,3),prominence=15.)
                peaks=peaks[(peaks>=512)&(peaks<1024)]-512;raw_features=[]
                for j,peak in enumerate(peaks):
                    previous=int(peaks[j-1]);following=int(peaks[(j+1)%len(peaks)])
                    left=np.arange(previous,int(peak)+512*(peak<=previous)+1)%512
                    right=np.arange(int(peak),following+512*(following<=peak)+1)%512
                    lv=int(left[np.argmin(raw[left])]);rv=int(right[np.argmin(raw[right])])
                    position=peak*len(g)/512;edge=int(np.floor(position))%len(g);weight=float(position-np.floor(position))
                    raw_features.append(dict(peak=int(peak),left_valley=lv,right_valley=rv,xyz=xyz[peak].tolist(),
                        prominence=float(raw[peak]-max(raw[lv],raw[rv])),source_edge_vertices=[r*len(g)+edge,r*len(g)+(edge+1)%len(g)],
                        source_edge_weights=[1-weight,weight]))
                sections.append(dict(label=label,row=r,material_s=float(state['s'][r]),raw_excess_min=float(raw.min()),
                    raw_excess_max=float(raw.max()),features=records[r],raw_analysis_features=raw_features))
            np.savez_compressed(dest/(item['id']+'_material_edges.npz'),**profiles)
            row['material_sections']=sections
        rows.append(row);print(item['id'],'actual cuts and edges measured',flush=True)
    # A child match is an observed peak inside its previous parent's angular basin.
    # It is not a topology ancestor or a continuous curve certificate.
    tracks=[]
    selected=[r for r in rows if 'material_sections' in r]
    for previous,current in zip(selected,selected[1:]):
        oldprof=np.load(dest/(previous['id']+'_material_edges.npz'))
        newprof=np.load(dest/(current['id']+'_material_edges.npz'))
        for psection,csection in zip(previous['material_sections'],current['material_sections']):
            label=psection['label'];raw=newprof[label+'_excess'];xyz=newprof[label+'_xyz']
            for parent in psection['raw_analysis_features']:
                start=parent['left_valley'];length=(parent['right_valley']-start)%512
                children=[f for f in csection['raw_analysis_features'] if (f['peak']-start)%512<=length]
                children.sort(key=lambda f:(f['peak']-start)%512)
                valleys=[]
                for one,two in zip(children,children[1:]):
                    ids=np.arange(one['peak'],two['peak']+512*(two['peak']<one['peak'])+1)%512
                    at=int(ids[np.argmin(raw[ids])]);depth=float(min(raw[one['peak']],raw[two['peak']])-raw[at])
                    valleys.append(dict(peak_pair=[one['peak'],two['peak']],valley=at,raw_radial_depth=depth,
                        peak_valley_chords=[float(np.linalg.norm(xyz[f['peak']]-xyz[at])) for f in (one,two)],valley_xyz=xyz[at].tolist()))
                tracks.append(dict(from_stage=previous['id'],to_stage=current['id'],section=label,
                    material_s=psection['material_s'],parent=parent,children=children,internal_valleys=valleys))
    write_new(dest/'measurements.json',dict(stages=rows,finite_feature_tracks=tracks,
        caveats=['Raw cuts intersect the explicit native triangular surface; material edges are native edges but generally not planar after longitudinal displacement.',
                 'Feature identification uses a fixed 512-angle scalar filter. Raw depths and XYZ chords are recorded separately.',
                 'Control features retain the original sigma=.035. Separate descriptive raw extrema use no filter and prominence15, so fine folds hidden by the control filter can be inspected; this is not a relaxed validity criterion.',
                 'Matching inside sampled parent angular basins is not continuous ridge certification or native face ancestry.',
                 'Finite planar cut checks do not certify all coplanar/tangent or between-plane solid contacts.'],
        producer_sha256=sha(Path(__file__))))


def causality(request,tag):
    dest=ROOT/'analysis'/tag;dest.mkdir(parents=True,exist_ok=False);rows=[]
    left=ROOT/'candidates'/request['current'];right=ROOT/'candidates'/request['frozen']
    a=json.loads((left/'request.json').read_text());b=json.loads((right/'request.json').read_text())
    aa=dict(a);bb=dict(b);aa.pop('criterion');bb.pop('criterion')
    if aa!=bb:raise ValueError('Only geometry criterion may differ in this causal pair.')
    for name in ['G3_FORM','G4_PRE','G4_FOLD','G5_PRE','G5_FOLD']:
        x=load_mesh(left/name);y=load_mesh(right/name);d=np.linalg.norm(x.xyz-y.xyz,axis=1)
        row=dict(stage=name,byte_identical_mesh=sha(left/name/'mesh.npz')==sha(right/name/'mesh.npz'),
            coordinate_max=float(d.max()),coordinate_rms=float(np.sqrt(np.mean(d*d))))
        if (left/name/'features.json').exists():
            ca=np.load(left/name/'control_state.npz');cb=np.load(right/name/'control_state.npz')
            # Early Task34 snapshots use the historical radial field name;
            # both denote the signed fold component, not total XYZ distance.
            key='requested_signed_fold_distance' if 'requested_signed_fold_distance' in ca.files else 'requested_radial'
            row['signed_control_max_difference']=float(abs(ca[key]-cb[key]).max())
            row['active_vertices_current']=int(np.count_nonzero(ca[key]))
            row['active_vertices_frozen']=int(np.count_nonzero(cb[key]))
            for key,job in [('current',left),('frozen',right)]:
                features=json.loads((job/name/'features.json').read_text());row[key+'_source']=features['source']
                row[key+'_source_sha256']=features['source_mesh_sha256'];row[key+'_features']=len(features['features'])
        rows.append(row)
    if not all(r['byte_identical_mesh'] for r in rows[:-1]) or rows[-1]['coordinate_max']<=1e-6:
        raise ValueError('Causal comparison did not isolate a response to generated geometry.')
    write_new(dest/'comparison.json',dict(request=request,identical_rule_and_parameters=aa,rows=rows,
        generation_is_not_an_input_to_refold=True,source_sha256=sha(REPO/'src/cheshire/task34_refolding.py'),producer_sha256=sha(Path(__file__))))
    print(rows[-1],flush=True)


def lineage(request,tag):
    job=ROOT/'candidates'/request['candidate'];dest=ROOT/'analysis'/tag;dest.mkdir(parents=True,exist_ok=False);rows=[]
    previous=job/'G0_CARRIER'
    for generation in range(1,request.get('final_generation',6)+1):
        before=job/f'G{generation}_PRE';state=state_at(before);op=np.load(before/'operator_state.npz');parent=load_mesh(previous)
        ids=op['grid_parent_vertices'];weights=op['grid_parent_weights']
        reconstructed=(parent.xyz[np.maximum(ids,0)]*weights[:,:,:,None]).sum(2)
        error=float(abs(reconstructed-state['grid']).max())
        if error>1e-11:raise ValueError('Actual vertex stencils do not reconstruct PRE geometry.')
        row=dict(generation=generation,parent_stage=str(previous),stencil_max_error=error,
            genuine_parent_face_contributors=op['parent_native_triangle_contributors'].shape[-1])
        after=job/f'G{generation}_FOLD'
        if after.exists():
            metadata=json.loads((after/'features.json').read_text());source=load_mesh(metadata['source']);features=metadata['features']
            errors=[np.linalg.norm(np.asarray(f['source_edge_weights'])@source.xyz[f['source_edge_vertices']]-f['xyz']) for f in features]
            row['feature_source_edge_max_error']=float(max(errors,default=0));row['feature_count']=len(features)
        actual=after if after.exists() else job/f'G{generation}_FORM'
        previous=actual if actual.exists() else before;rows.append(row)
    write_new(dest/'lineage.json',dict(candidate=request['candidate'],rows=rows,producer_sha256=sha(Path(__file__)),
        caveat='Native vertex stencils and two triangle contributors describe mesh refinement. Sampled geometric crest matching is a separate relation.'))
    print(rows,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--action',choices=['measure','causality','lineage'],required=True)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--worker',action='store_true');args=p.parse_args()
    if not args.tag.replace('_','').isalnum():raise ValueError('Fresh safe tag required.')
    if args.worker:globals()[args.action](json.loads(args.request.read_text()),args.tag)
    else:
        logs=ROOT/'logs'/('analysis_'+args.tag)
        if logs.exists():raise FileExistsError(logs)
        result=guarded(['--action',args.action,'--request',str(args.request),'--tag',args.tag,'--worker'],logs,worker_script=Path(__file__))
        write_new(ROOT/'resources'/('analysis_'+args.tag+'.json'),result);print(json.dumps(result),flush=True)
        if result['exit_code']:raise SystemExit(result['exit_code'])
