"""Finite actual-triangle sections and material-edge ancestry, without shading.

Raw 15-unit prominence threshold retained from Task34; no analysis filtering.
World planes measure distribution. Native material edges measure ancestry;
they are distinct, particularly after axial redistribution.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_preserve import sha,write_new
from task29_search import load_mesh
from cheshire.task35_columns import native
ROOT=Path('E:/CHESHIRE_DATA/task35')
SAMPLES=2048
THETA=(np.arange(SAMPLES)+.371)*2*np.pi/SAMPLES
AXIAL_Z=(np.arange(SAMPLES)+.371)*4000/SAMPLES
REGIONS=[('body',400,1800),('contraction',1800,2000),('neck',2000,2240),('flare_collar',2240,2600),('upper',2600,3600)]


def region(z):
    for name,a,b in REGIONS:
        if a<=z<(b if b!=3600 else b+1e-6):return name
    return 'end_transition'


def radial_cut(lines):
    """Intersect each angular ray with actual triangle-cut segments.

    No angular interpolation of vertex radii. A multiple positive hit is
    retained as invalid for radial peak counting, never replaced by outermost.
    """
    radius=np.full(SAMPLES,np.nan);hits=np.zeros(SAMPLES,np.int32);multi=np.zeros(SAMPLES,bool)
    for pair in lines:
        a,b=pair[:,:2];d=b-a
        aa=np.arctan2(a[1],a[0])%(2*np.pi);bb=aa+(np.arctan2(b[1],b[0])-aa+np.pi)%(2*np.pi)-np.pi
        lo,hi=sorted([aa,bb])
        for shift in [-2*np.pi,0,2*np.pi]:
            j0=max(0,int(np.ceil((lo+shift)*SAMPLES/(2*np.pi)-.371)))
            j1=min(SAMPLES,int(np.floor((hi+shift)*SAMPLES/(2*np.pi)-.371))+1)
            if j1<=j0:continue
            ids=np.arange(j0,j1);u=np.column_stack([np.cos(THETA[ids]),np.sin(THETA[ids])]);den=u[:,0]*d[1]-u[:,1]*d[0]
            good=np.abs(den)>1e-12;ids=ids[good];u=u[good];den=den[good]
            r=(a[0]*d[1]-a[1]*d[0])/den;t=(a[0]*u[:,1]-a[1]*u[:,0])/den
            good=(r>0)&(t>=-1e-9)&(t<=1+1e-9);ids=ids[good];r=r[good]
            multi[ids]|=(hits[ids]>0)&(np.abs(radius[ids]-r)>1e-6)
            radius[ids]=r;hits[ids]+=1
    return radius,dict(missing_rays=int((hits==0).sum()),multiple_distinct_rays=int(multi.sum()))


def peaks(values,threshold=15.):
    if not np.isfinite(values).all():return []
    n=len(values);p,_=find_peaks(np.tile(values,3),prominence=threshold);p=p[(p>=n)&(p<2*n)]-n;out=[]
    if len(p)<2:return out
    for j,i in enumerate(p):
        prev=p[j-1];nxt=p[(j+1)%len(p)]
        left=np.arange(prev,i+n*(i<=prev)+1)%n;right=np.arange(i,nxt+n*(nxt<=i)+1)%n
        lv=int(left[np.argmin(values[left])]);rv=int(right[np.argmin(values[right])]);prom=float(values[i]-max(values[lv],values[rv]))
        if prom>=threshold:out.append(dict(peak=int(i),left_valley=lv,right_valley=rv,prominence=prom,angle=float(THETA[i])))
    return out


def child_valleys(parent,child):
    """Internal valleys with flanking crests inside a finite parent basin.

    Parent material angle intervals, not nearest spatial vertices. This is
    finite evidence, not a certification of continuous surface ridge curves.
    """
    n=len(parent);rows=[]
    for p in peaks(parent):
        a=p['left_valley'];b=p['right_valley'];ids=np.arange(a,b+n*(b<=a)+1)%n;v=child[ids]
        minima,_=find_peaks(-v,prominence=15.);maxima,_=find_peaks(v,prominence=15.)
        for m in minima:
            left=maxima[maxima<m];right=maxima[maxima>m]
            if not len(left) or not len(right):continue
            l=int(left[-1]);r=int(right[0]);depth=float(min(v[l],v[r])-v[m])
            if depth>=15:rows.append(dict(parent_peak=p['peak'],parent_left=a,parent_right=b,valley=int(ids[m]),left_crest=int(ids[l]),right_crest=int(ids[r]),depth=depth))
    return rows


def envelope_retention(parent,child):
    rows=[];n=len(parent)
    for p in peaks(parent):
        a=p['left_valley'];b=p['right_valley'];ids=np.arange(a,b+n*(b<=a)+1)%n
        depth=float(np.max(child[ids])-max(child[a],child[b]))
        rows.append(dict(parent_peak=p['peak'],initial_depth=p['prominence'],final_outer_depth=depth,ratio=depth/p['prominence']))
    return rows


def material_edge(state,row):
    # Piecewise linear interpolation along actual native material edges.
    g=state['grid'][row];rest=state['rest'][row];theta=state['theta']
    xyz=np.column_stack([np.interp(THETA,theta,g[:,k],period=2*np.pi) for k in range(3)])
    base=np.column_stack([np.interp(THETA,theta,rest[:,k],period=2*np.pi) for k in range(3)])
    return xyz,np.linalg.norm(xyz[:,:2],axis=1)-np.linalg.norm(base[:,:2],axis=1)


def longitudinal_profile(lines,name):
    uv=lines[:,:,[0,2]] if name=='XZ' else lines[:,:,[1,2]] if name=='YZ' else np.stack([(lines[:,:,0]+lines[:,:,1])/2**.5,lines[:,:,2]],axis=-1)
    radius=np.full(SAMPLES,np.nan);multiple=np.zeros(SAMPLES,bool)
    for pair in uv:
        a,b=pair
        if abs(b[1]-a[1])<1e-10:continue
        lo,hi=sorted([a[1],b[1]]);ids=np.flatnonzero((AXIAL_Z>=lo)&(AXIAL_Z<hi))
        r=a[0]+(b[0]-a[0])*(AXIAL_Z[ids]-a[1])/(b[1]-a[1]);good=r>0;ids=ids[good];r=r[good]
        multiple[ids]|=np.isfinite(radius[ids])&(abs(radius[ids]-r)>1e-6);radius[ids]=r
    return radius,dict(missing_samples=int((~np.isfinite(radius)).sum()),multiple_positive_hits=int(multiple.sum()))


def open_valleys(parent,child):
    if not np.isfinite(parent).all() or not np.isfinite(child).all():return []
    pp,_=find_peaks(parent,prominence=15);rows=[]
    for j,p in enumerate(pp):
        previous=int(pp[j-1]) if j else 0;nxt=int(pp[j+1]) if j+1<len(pp) else len(parent)-1
        a=previous+int(np.argmin(parent[previous:p+1]));b=p+int(np.argmin(parent[p:nxt+1]));v=child[a:b+1]
        valleys,_=find_peaks(-v,prominence=15);crests,_=find_peaks(v,prominence=15)
        for valley in valleys:
            left=crests[crests<valley];right=crests[crests>valley]
            if not len(left) or not len(right):continue
            l=int(left[-1]);r=int(right[0]);depth=float(min(v[l],v[r])-v[valley])
            if depth>=15:rows.append(dict(parent_world_z=float(AXIAL_Z[p]),valley_world_z=float(AXIAL_Z[a+valley]),depth=depth))
    return rows


def measure(candidate,validation,tag,audit_id=None):
    import trimesh
    job=ROOT/'candidates'/candidate;dest=ROOT/'measurements'/tag;dest.mkdir(parents=True,exist_ok=False)
    stage=Path(json.loads((job/'completed.json').read_text())['final_stage']);state=dict(np.load(stage/'formation_state.npz'))
    audit_id=audit_id or candidate;audit_path=ROOT/'validation'/validation/(audit_id+'.json')
    audit=json.loads(audit_path.read_text())
    if audit['mesh_sha256']!=sha(stage/'mesh.npz'):raise ValueError('Section certificate belongs to a different native mesh.')
    cuts_path=ROOT/'validation'/validation/(audit_id+'_cuts.npz');cuts=dict(np.load(cuts_path))
    rest_mesh,_,_=native(dict(state,grid=state['rest']),7)
    rest=trimesh.Trimesh(vertices=rest_mesh.xyz,faces=rest_mesh.faces[:,:3],process=False)
    curves={};world=[];named=[];earlier={};named_heights=[900,1500,1900,2120,2380,2520,3000]
    final_mesh=load_mesh(stage);final_model=trimesh.Trimesh(vertices=final_mesh.xyz,faces=final_mesh.faces[:,:3],process=False)
    for name in ['G3_FORM','G4_FOLD']:
        m=load_mesh(job/name);earlier[name]=trimesh.Trimesh(vertices=m.xyz,faces=m.faces[:,:3],process=False)
    longitudinal=[]
    for name,normal in [('XZ',[0,1,0]),('YZ',[1,0,0]),('DIAGONAL',[1,-1,0])]:
        profiles={};validations={}
        for stage_name,model in list(earlier.items())+[('G7_FOLD',final_model),('REST',rest)]:
            lines=trimesh.intersections.mesh_plane(model,normal,[0,0,0]);curves['LONG_'+stage_name+'_'+name+'_segments']=lines
            profiles[stage_name],validations[stage_name]=longitudinal_profile(lines,name);curves['LONG_'+stage_name+'_'+name+'_radius']=profiles[stage_name]
        valid=not any(any(v.values()) for v in validations.values())
        longitudinal.append(dict(plane=name,ray_validation=validations,
            raw_middle_inside_large=open_valleys(profiles['G3_FORM'],profiles['G4_FOLD']) if valid else [],
            raw_small_inside_middle=open_valleys(profiles['G4_FOLD'],profiles['G7_FOLD']) if valid else [],
            limits='Fixed-world actual triangle cuts; axial redistribution prevents interpreting these world-Z basins as exact material ancestry.'))
    for z in sorted(set(range(400,3601,100))|set(named_heights)):
        name=f'Z{z}';lines=cuts[name] if name in cuts else trimesh.intersections.mesh_plane(final_model,[0,0,1],[0,0,z+.12345])
        curves[name+'_segments']=lines;r,valid=radial_cut(lines);base_lines=trimesh.intersections.mesh_plane(rest,[0,0,1],[0,0,z+.12345]);base,base_valid=radial_cut(base_lines)
        curves[name+'_radius']=r;curves[name+'_base_radius']=base;excess=r-base
        invalid=any(valid.values()) or any(base_valid.values());p=[] if invalid else peaks(excess)
        before={};before_valid={}
        for stage_name,model in earlier.items():
            lines=trimesh.intersections.mesh_plane(model,[0,0,1],[0,0,z+.12345]);rr,vv=radial_cut(lines)
            curves[stage_name+'_'+name+'_radius']=rr;curves[stage_name+'_'+name+'_segments']=lines;before[stage_name]=rr-base;before_valid[stage_name]=vv
        entry=dict(z=z+.12345,region=region(z),ray_validation=valid,base_ray_validation=base_valid,earlier_ray_validation=before_valid,
            ornament_peaks=p,raw_radius_peaks=[] if invalid else peaks(r),radius_range=[float(np.nanmin(r)),float(np.nanmax(r))])
        entry['large_to_middle']=[] if any(before_valid['G3_FORM'].values()) or any(before_valid['G4_FOLD'].values()) else child_valleys(before['G3_FORM'],before['G4_FOLD'])
        entry['middle_to_final']=[] if invalid or any(before_valid['G4_FOLD'].values()) else child_valleys(before['G4_FOLD'],excess)
        if z%100==0:world.append(entry)
        if z in named_heights:named.append(entry)
    stages=['G3_FORM','G4_PRE','G4_FOLD','G7_PRE','G7_FOLD'];states={k:dict(np.load(job/k/'formation_state.npz')) for k in stages}
    # Every inherited G3 body ring, not selected after seeing good details.
    original=states['G3_FORM']['s']*4000;tracks=[]
    for index,z in enumerate(original):
        if not 400<=z<=3600:continue
        row=dict(original_z=float(z),region=region(z),observations={});signals={}
        for name,s in states.items():
            matches=np.flatnonzero(np.isclose(s['s'],z/4000,rtol=0,atol=1e-14))
            if len(matches)!=1:raise ValueError('Lost unique material ring identity.')
            ring=int(matches[0]);xyz,value=material_edge(s,ring);signals[name]=value;curves[f'M{index}_{name}_xyz']=xyz;curves[f'M{index}_{name}_excess']=value
            row['observations'][name]=dict(ring_index=ring,mean_actual_z=float(xyz[:,2].mean()),peaks=peaks(value))
        row['middle_inside_large']=child_valleys(signals['G3_FORM'],signals['G4_FOLD'])
        row['small_inside_middle']=child_valleys(signals['G4_FOLD'],signals['G7_FOLD'])
        row['large_envelope_retention']=envelope_retention(signals['G3_FORM'],signals['G7_FOLD'])
        row['middle_envelope_retention']=envelope_retention(signals['G4_FOLD'],signals['G7_FOLD'])
        row['large_final_min_depth']=min([x['prominence'] for x in peaks(signals['G7_FOLD'])],default=0.)
        tracks.append(row)
    np.savez_compressed(dest/'actual_curves.npz',theta=THETA,axial_z=AXIAL_Z,**curves)
    controls={};provenance=[]
    for name in ['G3_FORM','G4_FOLD','G7_FOLD']:
        s=states[name];c=dict(np.load(job/name/'control_state.npz'));original=s['s']*4000;rs=[]
        for area,a,b in REGIONS:
            take=(original>=a)&(original<b);distance=c['total_applied_distance'][take]
            if not len(distance):continue
            angular_edges=np.linalg.norm(np.roll(s['grid'][take],-1,axis=1)-s['grid'][take],axis=2)
            axial_edges=np.linalg.norm(np.diff(s['grid'],axis=0),axis=2)
            entry=dict(region=area,mean_move=float(distance.mean()),max_move=float(distance.max()),active_fraction=float((distance>1e-9).mean()),
                median_angular_edge=float(np.median(angular_edges)),median_axial_edge=float(np.median(axial_edges)),
                broadness_range=[float(c['read_broadness'][take].min()),float(c['read_broadness'][take].max())],
                slope_range=[float(c['read_slope'][take].min()),float(c['read_slope'][take].max())])
            if 'axial_redistribution' in c:entry.update(axial_move_range=[float(c['axial_redistribution'][take].min()),float(c['axial_redistribution'][take].max())],
                angular_move_range=[float(c['angular_displacement'][take].min()),float(c['angular_displacement'][take].max())])
            rs.append(entry)
        controls[name]=rs
        if name!='G3_FORM':
            source=json.loads((job/name/'features.json').read_text());source_stage=Path(source['source_stage']);m=load_mesh(source_stage)
            errors=[]
            for feature in source['features']:
                reconstructed=(m.xyz[np.asarray(feature['source_edge_vertices'])]*np.asarray(feature['source_edge_weights'])[:,None]).sum(0)
                errors.append(float(np.linalg.norm(reconstructed-feature['xyz'])))
            before=job/name.replace('FOLD','PRE');pre=dict(np.load(before/'formation_state.npz'))
            provenance.append(dict(stage=name,source_stage=str(source_stage),source_sha_matches=sha(source_stage/'mesh.npz')==source['source_mesh_sha256'],
                actual_feature_edge_count=len(errors),feature_xyz_reconstruction_max=max(errors,default=0),
                applied_vector_reconstruction_max=float(abs(s['grid']-pre['grid']-c['applied_displacement']).max()),
                note='feature_owner uses the canonical X/Y representative; reflected controls share that owner. Material-domain ancestry is not a certified spatial ridge.'))
    summary=dict(candidate=candidate,mesh_sha256=sha(stage/'mesh.npz'),source_cut_sha256=sha(cuts_path),producer_sha256=sha(Path(__file__)),
        source_audit_sha256=sha(audit_path),analysis='2048 fixed rays intersect actual native triangle cuts; 15-unit unfiltered radial-excess prominence. Material tracks interpolate actual native edges, not fixed-world sections.',
        limitations='Radial excess relative to unwarped rest at same world Z is a distribution descriptor, not ancestry. Native material-edge tracking uses material theta, not spatial polar angle. Finite samples do not certify continuous ridges. Coarse facet kinks can be peaks; counts alone are not ornament success.',
        world_sections=world,named_sections=named,longitudinal_sections=longitudinal,material_tracks=tracks,controls=controls,provenance=provenance,
        middle_coverage=sum(bool(t['middle_inside_large']) for t in tracks),small_coverage=sum(bool(t['small_inside_middle']) for t in tracks),material_denominator=len(tracks),
        world_middle_coverage=sum(bool(t['large_to_middle']) for t in world),world_small_coverage=sum(bool(t['middle_to_final']) for t in world),
        fine_depths=[v['depth'] for t in tracks for v in t['small_inside_middle']])
    write_new(dest/'result.json',summary)
    print(candidate,'material',summary['middle_coverage'],summary['small_coverage'],'/',len(tracks),'fine',len(summary['fine_depths']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--validation',required=True);p.add_argument('--tag',required=True);p.add_argument('--audit-id');a=p.parse_args();measure(a.candidate,a.validation,a.tag,a.audit_id)
