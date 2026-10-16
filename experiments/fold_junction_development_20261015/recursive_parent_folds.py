"""A reusable measured-parent shoulder RETURN recurrence on column charts.

Existing lineage strips seed ownership, not target positions. Every call reads
the actual incoming SOURCE surface, detects its basin, measures a smaller
physical-arc shoulder, optionally performs one genuine neutral CC step, and
applies the same measured-frame RETURN there. No phase decoration, new artist
coordinates, finite-field replay, or blanket source fairing is introduced.

Scope is explicit: the established column material (t,polar-cross) chart and
its canonical X/Y reflections. This is not an arbitrary-mesh parameterizer.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import numpy as np


HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
VISIBLE=HERE.parent/'fold_visible_gate_20261012'
REGION=HERE.parent/'fold_region_growth_20261012'
for path in (REPO/'src',REGION,VISIBLE):
    if str(path) not in sys.path:
        sys.path.insert(0,str(path))
from cheshire.reference_subdivision import ArrayMesh,subdivide as cc_subdivide
import region_fold
import wall_fold
import child_fold

VERIFY_PATH=HERE.parent/'connected_fold_growth_20261012/verify.py'
_spec=importlib.util.spec_from_file_location('recursive_parent_actual_mirror_ids',VERIFY_PATH)
mirror=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mirror)


class AbsentParentFold(ValueError):
    """Actual owned parent has no sufficient measured basin; no replacement."""


def helper_paths():
    import cheshire.reference_subdivision as reference
    return [Path(region_fold.__file__),Path(wall_fold.__file__),
            Path(child_fold.__file__),VERIFY_PATH,Path(reference.__file__)]


def _hash(value):
    return hashlib.sha256(memoryview(np.ascontiguousarray(value)).cast('B')).hexdigest()


def _copy_rail(rail):
    return {key:np.asarray(value).copy() for key,value in rail.items()}


def initialize(rails_list):
    """Seed from saved lineage rails. No generation3 or file-path assumption."""
    parents=[]
    for index,rail in enumerate(rails_list):
        if str(rail.get('axis',''))!='height':
            raise ValueError('Adapter requires existing longitudinal column-chart lineage rails.')
        p=np.asarray(rail['parameter'],dtype=float)
        if p.ndim!=1 or len(p)<5 or not np.all(np.diff(p)>0.):
            raise ValueError('Existing parent parameter must have at least5ordered samples.')
        parents.append(dict(rail=_copy_rail(rail),family_id=int(index),tier=0,
            longitudinal_extent=[float(p[0]),float(p[-1])]))
    if not parents:
        raise ValueError('At least one existing lineage-owned parent is required.')
    return dict(schema='MEASURED_PARENT_RETURN_RECURRENCE_V1',parents=parents,
                formation_cycles=0,active=True)


class _RecordedSampler:
    def __init__(self,sampler,native_triangle_ids):
        self.sampler,self.native_triangle_ids=sampler,native_triangle_ids

    def sample(self,uv,*,records=False):
        result=self.sampler.sample(uv,records=records)
        if not records:
            return result
        xyz,ids,bary=result
        return xyz,self.native_triangle_ids[ids],bary


def native_body_sampler(mesh,chart,body_face_mask):
    """Actual SOURCE canonical-quarter native fans only; no fullnative copy."""
    x,q,chart=np.asarray(mesh.xyz),np.asarray(mesh.faces),np.asarray(chart)
    mask=np.asarray(body_face_mask,dtype=bool)
    if chart.shape!=x.shape or q.ndim!=2 or q.shape[1]!=4 or mask.shape!=(len(q),):
        raise ValueError('Matching actual quad mesh/chart/SOURCE-face mask required.')
    if not np.isfinite(x).all() or not np.isfinite(chart).all():
        raise ValueError('Finite actual incoming surface and chart required.')
    if str(getattr(mesh,'surface','mean'))!='mean':
        raise ValueError('This adapter measures actual arithmetic-mean native fans only.')
    eligible=(chart[:,1]>=-1e-10)&(chart[:,2]>=-1e-10)&(np.linalg.norm(chart[:,1:],axis=1)>.2)
    ids=np.flatnonzero(mask&eligible[q].all(axis=1))
    if not len(ids):
        raise AbsentParentFold('No actual SOURCE triangles in canonical material quadrant.')
    selected=q[ids]
    centres=x[selected].mean(axis=1)
    centre_chart=chart[selected].mean(axis=1)
    native_xyz=np.concatenate((x,centres))
    native_chart=np.concatenate((chart,centre_chart))
    triangles=np.stack((selected,np.roll(selected,-1,axis=1),
        np.broadcast_to((len(x)+np.arange(len(ids)))[:,None],selected.shape)),axis=-1).reshape(-1,3)
    original_native_triangle_ids=(4*ids[:,None]+np.arange(4)).ravel()
    sampler=region_fold.NativeChartSampler(native_xyz,triangles,native_chart)
    return _RecordedSampler(sampler,original_native_triangle_ids),dict(
        selected_source_quads=int(len(ids)),selected_native_triangles=int(len(triangles)),
        native_surface='Actual arithmetic quad-centre fans on SOURCE faces only.',
        canonical_quadrant=True,attachment_chart_aliases_excluded=True,
        source_triangle_id_convention='4*actual_parent_quad_id+fan_corner')


def _measure_owned_child(sampler,parent_rail):
    """Use legacy basin evidence, then reconstruct all-ray ownership untrimmed."""
    fresh=wall_fold.measure_rails(sampler,parent_rail,angle_degrees=30.)
    try:
        detected=child_fold.measure_child(sampler,fresh)
    except ValueError as error:
        message=str(error)
        if ('trough absent' in message or 'Too little bracketed' in message or
                'no physical arc' in message):
            raise AbsentParentFold(message) from error
        raise
    # Existing measure_child returns full search evidence but restricts its
    # constructed child to q<=.6. Reuse the actual full-range detections,
    # not that recursively shortening output. No new detection is invented.
    parameter=np.asarray(detected['parent_search_parameter'])
    valid=np.asarray(detected['parent_search_valid'],dtype=bool)
    indices=np.asarray(detected['parent_search_trough_indices'])
    uv=np.asarray(detected['parent_search_uv'])
    if valid.sum()<=len(valid)/2:
        raise AbsentParentFold('Actual parent basin absent on majority of full owned longitudinal rays.')
    measured_ids=np.flatnonzero(valid)
    first,last=int(measured_ids[0]),int(measured_ids[-1])
    if last-first<4:
        raise AbsentParentFold('Actual parent full-range basin has too few bracketed rays.')
    take=np.arange(first,last+1)
    p=parameter[take]
    trough=np.asarray([uv[row,indices[row],1] for row in measured_ids])
    valley=np.interp(p,parameter[measured_ids],trough)
    lower=np.interp(p,fresh['parameter'],fresh['lower_cross'])
    upper=np.interp(p,fresh['parameter'],fresh['upper_cross'])
    fractions=np.linspace(0.,1.,129)
    shoulder_cross=valley[:,None]+(upper-valley)[:,None]*fractions
    shoulder_uv=np.stack((np.broadcast_to(p[:,None],shoulder_cross.shape),shoulder_cross),axis=2)
    shoulder_xyz,shoulder_ids,shoulder_bary=sampler.sample(shoulder_uv,records=True)
    arc=np.concatenate((np.zeros((len(p),1)),np.cumsum(np.linalg.norm(np.diff(shoulder_xyz,axis=1),axis=2),axis=1)),axis=1)
    if np.any(arc[:,-1]<=1e-10):
        raise AbsentParentFold('Actual parent outward shoulder has no positive physical arc.')
    owned=np.asarray([[np.interp(f*arc[row,-1],arc[row],shoulder_cross[row])
                       for f in (.35,.55,.75)] for row in range(len(p))])
    if not np.all((valley<owned[:,0])&(owned[:,0]<owned[:,1])&
                  (owned[:,1]<owned[:,2])&(owned[:,2]<upper)):
        raise ValueError('Actual physical-arc child ownership escaped parent shoulder.')
    guide=dict(axis=np.array('height'),parameter=p,lower_cross=owned[:,0],
               guide_cross=owned[:,1],upper_cross=owned[:,2])
    child=wall_fold.measure_rails(sampler,guide,angle_degrees=30.)
    # Observe actual trough depth under its own lower/upper shoulder chord.
    # Legacy depth is a width*tan(angle) request, not a measured basin depth.
    chord_uv=np.stack((np.broadcast_to(p[:,None],(len(p),3)),
                       np.column_stack((lower,valley,upper))),axis=2)
    chord_xyz,chord_ids,chord_bary=sampler.sample(chord_uv,records=True)
    normal=region_fold.unit(np.column_stack([np.interp(p,fresh['parameter'],fresh['normal'][:,k]) for k in range(3)]))
    left,centre,right=chord_xyz[:,0],chord_xyz[:,1],chord_xyz[:,2]
    vector=right-left
    alpha=np.clip(np.einsum('ij,ij->i',centre-left,vector)/np.maximum(np.einsum('ij,ij->i',vector,vector),1e-30),0.,1.)
    actual_depth=np.maximum(0.,np.einsum('ij,ij->i',left+alpha[:,None]*vector-centre,normal))
    if np.count_nonzero(actual_depth>1e-10)<=len(actual_depth)/2:
        raise AbsentParentFold('Actual detected trough has no positive shoulder-chord depth on majority of rays.')
    cap=.4*actual_depth
    uncapped=np.asarray(child['depth_uncapped']).copy()
    own_cap=np.asarray(child['depth_cap']).copy()
    child['depth_cap']=np.minimum(own_cap,cap)
    child['depth']=np.minimum(uncapped,child['depth_cap'])
    child['depth_capped']=uncapped>child['depth_cap']
    child['valley_fit']=child['centre_fit']-child['depth'][:,None]*child['normal']
    child['parent_observed_chord_depth']=actual_depth
    child['parent_expected_detection_depth']=np.interp(p,fresh['parameter'],fresh['depth'])
    child['parent_depth_ratio_cap']=np.array(.4)
    evidence=dict(parent_full_search_parameter=parameter,parent_full_search_valid=valid,
        parent_full_search_prominence=np.asarray(detected['parent_search_prominence']),
        parent_full_search_uv=uv,parent_full_search_xyz=np.asarray(detected['parent_search_xyz']),
        parent_full_search_triangle_ids=np.asarray(detected['parent_search_triangle_ids']),
        parent_full_search_barycentric=np.asarray(detected['parent_search_barycentric']),
        legacy_central_child_extent=np.asarray(detected['parameter'])[[0,-1]],
        all_ray_bracketed_child_extent=p[[0,-1]],child_measured_basin_mask=valid[take],
        shoulder_uv=shoulder_uv,shoulder_xyz=shoulder_xyz,shoulder_arc=arc,
        shoulder_triangle_ids=shoulder_ids,shoulder_barycentric=shoulder_bary,
        child_owned_cross=owned,child_owned_arc_fraction=np.tile([.35,.55,.75],(len(p),1)),
        parent_chord_xyz=chord_xyz,parent_chord_triangle_ids=chord_ids,
        parent_chord_barycentric=chord_bary,parent_actual_chord_depth=actual_depth,
        parent_expected_detection_depth=child['parent_expected_detection_depth'],
        child_depth=child['depth'],child_depth_cap=child['depth_cap'])
    return child,evidence


def _return_delta(xyz,chart,children,angle,depth_ratio,strength):
    guides=[]
    for child in children:
        guides.append(dict(axis=np.array('height'),parameter=child['parameter'],
            lower_cross=child['lower_cross'],guide_cross=child['guide_cross'],
            upper_cross=child['upper_cross'],centres=child['centre_fit'],
            normal=child['normal'],tangent=child['tangent'],
            shoulder_length=child['measured_left_arc']+child['measured_right_arc']))
    # Existing measured-T Rodrigues return, unchanged. Its normal groove is
    # added below using actual per-ray parent-depth caps instead of radius.
    delta,weights=region_fold.proposal(xyz,chart,guides,mode='RETURN',depth_ratio=0.,angle=angle)
    cross=np.arctan2(np.abs(chart[:,2]),np.abs(chart[:,1]))
    t=chart[:,0]
    signs=np.where(chart[:,1:]<0.,-1.,1.)
    depths=[]
    for child,g in zip(children,guides):
        p=child['parameter']
        interp=lambda a:np.interp(t,p,a)
        lo,mid,hi=(interp(child[key]) for key in ('lower_cross','guide_cross','upper_cross'))
        v=(cross-mid)/np.where(cross<mid,mid-lo,hi-mid)
        along=region_fold.window((t-(p[0]+p[-1])/2)/((p[-1]-p[0])/2))
        profile=np.maximum(0.,1.-np.abs(v))*along*((t>=p[0])&(t<=p[-1]))
        measured_width=.5*(child['measured_left_arc']+child['measured_right_arc'])
        depth=np.minimum(child['depth'],depth_ratio*measured_width)
        normal=region_fold.unit(np.column_stack([interp(child['normal'][:,k]) for k in range(3)]))
        groove=-interp(depth)[:,None]*profile[:,None]*normal
        groove[:,:2]*=signs
        delta+=groove
        depths.append(depth)
    denominator=np.maximum(1.,weights.sum(axis=0))
    return strength*delta/denominator[:,None],dict(
        return_weights=weights,overlap_denominator=denominator,
        actual_child_groove_depths=depths)


def _reflect(delta,pairs):
    n=len(delta);ids=np.arange(n)
    px,py=(mirror.involution(np.asarray(pairs[key]),n,key+' sourceID') for key in ('X','Y'))
    if not np.array_equal(px[py],py[px]):
        raise ValueError('SourceID reflection involutions must commute.')
    both=px[py];rep=np.minimum(np.minimum(ids,px),np.minimum(py,both))
    out=delta[rep].copy()
    out[(ids==px[rep])|(ids==both[rep]),0]*=-1.
    out[(ids==py[rep])|(ids==both[rep]),1]*=-1.
    out[px==ids,0]=0.;out[py==ids,1]=0.
    return out,px,py


def _clone(mesh,xyz):
    result=ArrayMesh(xyz,np.asarray(mesh.faces).copy(),np.asarray(mesh.classes).copy(),
        np.asarray(mesh.rest).copy(),np.asarray(mesh.anchors).copy(),int(mesh.generation))
    result.surface=str(getattr(mesh,'surface','mean'))
    return result


def step(mesh,chart,fold_state,body_face_mask,vertex_pairs=None,*,
         subdivide=True,angle=.65,depth_ratio=.28,strength=1.):
    """Return ``(out_mesh,out_chart,next_state,metadata,evidence)``.

    ``subdivide=True`` performs ONE true current-parent CC generation before
    the same dimensionless measured RETURN rule. False is a same-topology
    formation cycle and is recorded separately. New ownership is returned as
    a guide/expected-depth state; the next call measures the ACTUAL new mesh.
    """
    chart=np.asarray(chart);body=np.asarray(body_face_mask,dtype=bool)
    if (fold_state.get('schema')!='MEASURED_PARENT_RETURN_RECURRENCE_V1' or
            not np.isfinite([angle,depth_ratio,strength]).all() or
            angle<0. or depth_ratio<0. or not 0.<=strength<=1.):
        raise ValueError('Initialized recurrence state and finite dimensionless RETURN controls required.')
    sampler,sampler_info=native_body_sampler(mesh,chart,body)
    children,records,terminated=[],[],[]
    for parent in fold_state['parents']:
        rail=parent['rail'] if 'rail' in parent else {key:value for key,value in parent.items()
            if key not in ('family_id','tier','longitudinal_extent','actual_bracketed_extent')}
        try:
            child,record=_measure_owned_child(sampler,rail)
        except AbsentParentFold as error:
            terminated.append(dict(family_id=int(parent['family_id']),reason=str(error)))
            continue
        except ValueError as error:
            if 'guide samples outside native chart' not in str(error):
                raise
            terminated.append(dict(family_id=int(parent['family_id']),
                reason='Inherited owned strip leaves the actual SOURCE chart: '+str(error)))
            continue
        children.append(child)
        records.append(dict(parent=parent,evidence=record))
    del sampler
    cycles=int(fold_state.get('formation_cycles',0))
    if not children:
        meta=dict(status='NO_ACTIVE_PARENT_BASIN',input_generation=int(mesh.generation),
            output_generation=int(mesh.generation),added_CC_passes=0,added_formation_cycles=0,
            terminated=terminated,sampler=sampler_info,forced_ornament_added=False)
        state=dict(fold_state,parents=[],active=False,last_step=meta)
        return _clone(mesh,np.asarray(mesh.xyz).copy()),chart.copy(),state,meta,dict()
    if subdivide:
        out,cc_meta,op=cc_subdivide(mesh,{})
        edges=op['input_edges']
        outchart=np.concatenate((chart,chart[edges].mean(axis=1),chart[mesh.faces].mean(axis=1)))
        outbody=np.repeat(body,4)
        outpairs=None if vertex_pairs is None else {key:mirror.refine_mirror_pairs(
            mesh.faces,edges,np.asarray(vertex_pairs[key])) for key in ('X','Y')}
    else:
        out=_clone(mesh,np.asarray(mesh.xyz).copy());outchart=chart.copy()
        outbody=body.copy();outpairs=vertex_pairs;cc_meta=None;op={}
    reference=out.xyz.copy()
    delta,formation=_return_delta(reference,outchart,children,angle,depth_ratio,strength)
    # Shared SOURCE/attachment interface controls remain exactly at the
    # current refined carrier. Parent/root ownership cannot cross that seam.
    forbidden=np.bincount(out.faces[~outbody].ravel(),minlength=len(reference))>0
    movable=~forbidden
    if outpairs is not None:
        delta,px,py=_reflect(delta,outpairs)
        movable&=movable[px]&movable[py]&movable[px[py]]
    else:
        delta[np.abs(outchart[:,1])<1e-10,0]=0.
        delta[np.abs(outchart[:,2])<1e-10,1]=0.
    delta[~movable]=0.
    out.xyz=reference+delta
    out.surface='mean'
    if not np.isfinite(out.xyz).all() or np.any(delta[~movable]!=0.):
        raise ValueError('New RETURN violates finite SOURCE-boundary preservation.')
    next_parents=[]
    for child,record in zip(children,records):
        parent=record['parent']
        next_parent=_copy_rail(child)
        next_parent.update(family_id=np.array(int(parent['family_id'])),
            tier=np.array(int(parent.get('tier',0))+1),
            longitudinal_extent=np.asarray(parent['longitudinal_extent'],dtype=float),
            actual_bracketed_extent=np.asarray(child['parameter'])[[0,-1]])
        next_parents.append(next_parent)
    metadata=dict(status='FORMED_FROM_ACTUAL_PARENT',implementation='MEASURED_PARENT_RETURN_RECURRENCE_V1',
        input_generation=int(mesh.generation),output_generation=int(out.generation),
        added_CC_passes=int(bool(subdivide)),added_formation_cycles=1,
        total_formation_cycles=cycles+1,formed_parent_families=len(children),terminated=terminated,
        angle=float(angle),depth_ratio=float(depth_ratio),strength=float(strength),
        maximum_displacement=float(np.linalg.norm(delta,axis=1).max(initial=0.)),
        moved_controls=int(np.count_nonzero(np.linalg.norm(delta,axis=1))),
        protected_SOURCE_attachment_controls=int(np.count_nonzero(~movable)),
        source_boundary_return_displacement=0.,sampler=sampler_info,
        source_xyz_sha256=_hash(np.asarray(mesh.xyz)),output_xyz_sha256=_hash(out.xyz),
        current_parent_remeasured=True,source_XYZ_globally_faired=False,
        parent_detection='Unchanged child_fold.measure_child actual native trough detector;4%of width-derived expected depth remains its detection threshold. Its full all-ray evidence reconstructs35–75%physical-arc ownership without the fixedcentral.6longitudinal trim.',
        actual_depth='Actual lower/upper shoulder-chord normal deficit at detected trough caps the child normal V-groove depth at.4;expectedwidth*tan30depth is retained separately,never called observeddepth. Rodrigues shoulder rotation is separately controlled by angle and is NOT bounded by this groove-depth cap.',
        geometry='Existing measured-T Rodrigues shoulder RETURN plus a bounded normal V-groove; the same dimensionless angle/depth ratios at every tier.',
        longitudinal_policy='Inherited original longitudinal_extent remains unchanged; only real full-range detected endpoints bracket active ownership. No automatic.6trim at every tier.',
        next_state_scope='New emitted child ownership/expecteddepth is not claimed to be an already measured next-generation basin; every following step reads the actual new native SOURCE again.',
        symmetry='Actual sourceID involutions when supplied; otherwise established canonical column-chart vector construction.',
        limitations='Column-chart longitudinal SOURCE folds only. Legacy radial orientation and member-radius intermediate cap are explicit adapters; actual parent chord depth additionally limits the normal V-groove only. The separate Rodrigues rotation is not depth-capped. No forced absent basin, global collision certificate or aesthetic success claim.')
    next_state=dict(schema=fold_state['schema'],parents=next_parents,formation_cycles=cycles+1,
        active=True,last_step=metadata,output_generation=int(out.generation),
        body_ownership_rule='Repeat each incoming SOURCE face flag four times for each actual CC step; unchanged on a same-topology formation cycle.')
    evidence=dict(return_delta=delta,output_body_face_mask=outbody,
        return_weights=formation['return_weights'],
        overlap_denominator=formation['overlap_denominator'],
        neutral_CC_metadata_json=np.array(json.dumps(cc_meta,allow_nan=False)))
    for key,value in op.items():
        evidence['refinement_'+key]=np.asarray(value)
    if outpairs is not None:
        for key,value in outpairs.items():
            evidence['output_mirror_'+key.lower()+'_vertex_pairs']=np.asarray(value)
    for index,(child,record) in enumerate(zip(children,records)):
        prefix=f'child_{index:03}_'
        for key,value in record['evidence'].items():
            evidence[prefix+key]=np.asarray(value)
        for key,value in child.items():
            evidence[prefix+'rail_'+key]=np.asarray(value)
        evidence[prefix+'applied_groove_depth']=formation['actual_child_groove_depths'][index]
    return out,outchart,next_state,metadata,evidence
