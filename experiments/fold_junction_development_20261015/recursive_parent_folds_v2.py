"""Topology-aware SOURCE-strip segmentation for measured-parent recurrence.

This changes ownership coverage, not the geometric RETURN rule. Actual holes
in the SOURCE material chart split an inherited family into valid longitudinal
pieces. No piece bridges a hole, no world-nearest point substitutes geometry,
and every accepted sample has an actual native triangle/barycentric record.
"""
from pathlib import Path
import importlib.util
import types

import numpy as np


CORE_PATH=Path(__file__).resolve().with_name('recursive_parent_folds.py')
_spec=importlib.util.spec_from_file_location('source_segmented_recurrence_core',CORE_PATH)
core=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)
initialize=core.initialize


def helper_paths():
    return [CORE_PATH]+core.helper_paths()


class CoverageSampler:
    """Existing UV native lookup with explicit validity and exact completion."""
    def __init__(self,recorded_sampler):
        self.base=recorded_sampler.sampler
        self.native_triangle_ids=recorded_sampler.native_triangle_ids
        self.lower=self.base.p.min(axis=1)
        self.upper=self.base.p.max(axis=1)
        self.complete_bbox_queries=0
        self.complete_bbox_resolved=0

    def coverage(self,uv):
        uv=np.asarray(uv,dtype=float)
        shape=uv.shape[:-1]
        query=uv.reshape(-1,2)
        if not np.isfinite(query).all():
            raise ValueError('Finite actual material sample coordinates required.')
        chosen=np.full(len(query),-1,dtype=np.int64)
        bary=np.full((len(query),3),np.nan)
        for count in (24,128,512):
            unresolved=np.flatnonzero(chosen<0)
            if not len(unresolved):
                break
            _,candidates=self.base.tree.query(query[unresolved],k=min(count,len(self.base.p)))
            candidates=np.asarray(candidates).reshape(len(unresolved),-1)
            bb=np.einsum('nkij,nkj->nki',self.base.inv[candidates],
                query[unresolved,None,:]-self.base.p[candidates,0])
            weights=np.concatenate((1.-bb.sum(axis=2,keepdims=True),bb),axis=2)
            valid=(weights>=-1e-9).all(axis=2)&(weights<=1.+1e-9).all(axis=2)
            found=valid.any(axis=1)
            rows=np.flatnonzero(found);cols=np.argmax(valid,axis=1)[found]
            chosen[unresolved[rows]]=candidates[rows,cols]
            bary[unresolved[rows]]=weights[rows,cols]
        # A KD-centroid miss is not proof of a chart hole. Test ALL possible
        # UV containing triangles by complete bounding-box inclusion, then
        # the same barycentric rule. This is not nearest-world fallback.
        for index in np.flatnonzero(chosen<0):
            self.complete_bbox_queries+=1
            point=query[index]
            candidates=np.flatnonzero(((self.lower<=point+1e-10)&
                                       (self.upper>=point-1e-10)).all(axis=1))
            if not len(candidates):
                continue
            bb=np.einsum('nij,nj->ni',self.base.inv[candidates],point-self.base.p[candidates,0])
            weights=np.column_stack((1.-bb.sum(axis=1),bb))
            valid=(weights>=-1e-9).all(axis=1)&(weights<=1.+1e-9).all(axis=1)
            if valid.any():
                row=int(np.flatnonzero(valid)[0])
                chosen[index]=candidates[row];bary[index]=weights[row]
                self.complete_bbox_resolved+=1
        valid=chosen>=0
        xyz=np.full((len(query),3),np.nan)
        ids=np.full(len(query),-1,dtype=np.int64)
        xyz[valid]=np.einsum('ni,nij->nj',bary[valid],self.base.xyz[chosen[valid]])
        ids[valid]=self.native_triangle_ids[self.base.ids[chosen[valid]]]
        return xyz.reshape(*shape,3),valid.reshape(shape),ids.reshape(shape),bary.reshape(*shape,3)

    def sample(self,uv,*,records=False):
        xyz,valid,ids,bary=self.coverage(uv)
        if not valid.all():
            raise ValueError(f'{int(np.count_nonzero(~valid))} guide samples outside native chart.')
        return (xyz,ids,bary) if records else xyz


def _rail(parent):
    if 'rail' in parent:
        return parent['rail']
    excluded={'family_id','piece_id','tier','longitudinal_extent','actual_bracketed_extent'}
    return {key:value for key,value in parent.items() if key not in excluded}


def _slice_rail(rail,start,stop):
    n=len(rail['parameter'])
    result={}
    for key,value in rail.items():
        value=np.asarray(value)
        # Only material ownership is used by fresh wall measurement. Preserve
        # exact per-ray associations; old XYZ/fit targets never place a fold.
        if key in ('axis','parameter','lower_cross','guide_cross','upper_cross'):
            result[key]=value[start:stop].copy() if value.ndim and value.shape[0]==n else value.copy()
    return result


def _partition(mesh,chart,state,body_face_mask):
    recorded,sampler_info=core.native_body_sampler(mesh,chart,body_face_mask)
    sampler=CoverageSampler(recorded)
    parents,records,evidence=[],[],{}
    for number,parent in enumerate(state['parents']):
        rail=_rail(parent)
        p=np.asarray(rail['parameter'],dtype=float)
        lo,mid,hi=(np.asarray(rail[key],dtype=float) for key in ('lower_cross','guide_cross','upper_cross'))
        if (len(p)<5 or not np.all(np.diff(p)>0.) or
                not np.all((lo<mid)&(mid<hi))):
            raise ValueError('Inherited ordered strip with at least5rays required.')
        full=lo[:,None]+(hi-lo)[:,None]*np.linspace(0.,1.,257)
        fractions=np.linspace(0.,1.,17)
        wall=np.concatenate((lo[:,None]+(mid-lo)[:,None]*fractions,
            mid[:,None]+(hi-mid)[:,None]*fractions[1:]),axis=1)
        corridor=.2*(hi-lo)
        a,b=np.maximum(lo,mid-corridor),np.minimum(hi,mid+corridor)
        basin=a[:,None]+(b-a)[:,None]*np.linspace(0.,1.,257)
        cross=np.concatenate((full,wall,basin),axis=1)
        uv=np.stack((np.broadcast_to(p[:,None],cross.shape),cross),axis=2)
        xyz,valid,ids,bary=sampler.coverage(uv)
        valid_ray=valid.all(axis=1)
        bounds=np.flatnonzero(np.diff(np.r_[False,valid_ray,False]))
        family_id=int(parent['family_id'])
        old_piece=str(np.asarray(parent.get('piece_id','0')))
        runs=[]
        for run_index,(first,last) in enumerate(zip(bounds[::2],bounds[1::2])):
            if last-first<5:
                runs.append(dict(first_ray=int(first),last_ray_exclusive=int(last),accepted=False,
                    reason='Actual valid SOURCE run has fewer than5longitudinal rays.'))
                continue
            piece_id=old_piece if first==0 and last==len(p) else old_piece+'.'+str(run_index)
            parents.append(dict(rail=_slice_rail(rail,first,last),family_id=family_id,
                piece_id=piece_id,tier=int(parent.get('tier',0)),
                longitudinal_extent=np.asarray(parent['longitudinal_extent']).tolist()))
            runs.append(dict(first_ray=int(first),last_ray_exclusive=int(last),accepted=True,
                piece_id=piece_id,material_extent=[float(p[first]),float(p[last-1])],rays=int(last-first)))
        records.append(dict(family_id=family_id,input_piece_id=old_piece,
            original_longitudinal_extent=np.asarray(parent['longitudinal_extent']).tolist(),
            actual_input_rail_extent=[float(p[0]),float(p[-1])],
            total_rays=int(len(p)),fully_covered_rays=int(np.count_nonzero(valid_ray)),
            missing_SOURCE_samples=int(np.count_nonzero(~valid)),
            invalid_ray_indices=np.flatnonzero(~valid_ray).tolist(),runs=runs))
        prefix=f'coverage_{number:03}_'
        evidence.update({prefix+'uv':uv,prefix+'xyz':xyz,prefix+'valid':valid,
            prefix+'native_triangle_ids':ids,prefix+'barycentric':bary,
            prefix+'valid_longitudinal_ray':valid_ray})
    segmented=dict(state,parents=parents,active=bool(parents))
    metadata=dict(implementation='TOPOLOGY_AWARE_SOURCE_STRIP_SEGMENTATION_V1',
        input_parent_records=len(state['parents']),accepted_owned_pieces=len(parents),
        original_family_count=len({int(p['family_id']) for p in state['parents']}),
        accepted_family_count=len({int(p['family_id']) for p in parents}),coverage=records,
        complete_bbox_queries=sampler.complete_bbox_queries,
        complete_bbox_resolved=sampler.complete_bbox_resolved,
        coverage_rule='Per original longitudinal ray:257full-strip+33wall+257basin-corridor exact native-chart samples; a ray containing any actual SOURCE hole cannot belong to a piece. Maximal contiguous valid runs>=5rays only.',
        hole_policy='No bridge, no XYZ interpolation across unresolved UV holes, no whole-family discard when other valid pieces exist.',
        lookup='Existing barycentric native lookup followed, for every unresolved sample, by complete UVtrianglebbox inclusion and exact barycentric containment. Missing samples are NaN withvalidFalse/nativeID-1.',
        sampler=sampler_info,
        limitation='Coverage is explicitly sampled on original longitudinal rays; it is not an analytic proof of every point of the continuous strip between rays.')
    return segmented,metadata,evidence,sampler,sampler_info


def measure_only(mesh,chart,fold_state,body_face_mask):
    """Measure actual current pieces without CC or deformation.

    Returns ``(segmented_input_state,JSON_safe_metadata,flat_NPZ_evidence)``.
    The state still describes incoming owned parents; no formation is claimed.
    """
    segmented,coverage,evidence,sampler,_=_partition(mesh,chart,fold_state,body_face_mask)
    records=[]
    for number,parent in enumerate(segmented['parents']):
        record=dict(family_id=int(parent['family_id']),piece_id=str(parent['piece_id']))
        try:
            child,measured=core._measure_owned_child(sampler,_rail(parent))
        except (core.AbsentParentFold,ValueError) as error:
            record.update(status='NO_MEASURABLE_PARENT_PIECE',reason=str(error))
        else:
            points=np.asarray(child['centre_xyz'])
            record.update(status='MEASURED_PARENT_PIECE',material_extent=np.asarray(child['parameter'])[[0,-1]].tolist(),
                child_centres_bounds_min=points.min(axis=0).tolist(),
                child_centres_bounds_max=points.max(axis=0).tolist(),
                actual_parent_chord_depth_quantiles=np.quantile(child['parent_observed_chord_depth'],[0.,.5,1.]).tolist(),
                requested_child_groove_depth_quantiles=np.quantile(child['depth'],[0.,.5,1.]).tolist())
            prefix=f'measurement_{number:03}_'
            for key,value in measured.items():
                evidence[prefix+key]=np.asarray(value)
            for key,value in child.items():
                evidence[prefix+'child_rail_'+key]=np.asarray(value)
        records.append(record)
    metadata=dict(status='MEASUREMENT_ONLY',input_generation=int(mesh.generation),
        output_generation=int(mesh.generation),added_CC_passes=0,added_formation_cycles=0,
        coverage=coverage,pieces=records,
        measurable_pieces=sum(p['status']=='MEASURED_PARENT_PIECE' for p in records),
        measurable_family_ids=sorted({p['family_id'] for p in records if p['status']=='MEASURED_PARENT_PIECE'}),
        source_xyz_sha256=core._hash(np.asarray(mesh.xyz)),source_geometry_changed=False)
    return segmented,metadata,evidence


def step(mesh,chart,fold_state,body_face_mask,vertex_pairs=None,*,
         subdivide=True,angle=.65,depth_ratio=.28,strength=1.):
    """Same recurrence API; segment topology-owned parents before measurement."""
    segmented,coverage,coverage_evidence,sampler,sampler_info=_partition(mesh,chart,fold_state,body_face_mask)
    mapping={}
    internal=[]
    for number,parent in enumerate(segmented['parents']):
        mapping[number]=(int(parent['family_id']),str(parent['piece_id']))
        internal.append(dict(parent,family_id=number))
    run_state=dict(segmented,parents=internal)
    namespace=dict(vars(core))
    namespace['native_body_sampler']=lambda unused_mesh,unused_chart,unused_mask:(sampler,sampler_info)
    run=types.FunctionType(core.step.__code__,namespace,name='segmented_source_recurrence',argdefs=core.step.__defaults__)
    run.__kwdefaults__=dict(core.step.__kwdefaults__)
    out,outchart,next_state,metadata,evidence=run(mesh,chart,run_state,body_face_mask,
        vertex_pairs,subdivide=subdivide,angle=angle,depth_ratio=depth_ratio,strength=strength)
    for parent in next_state['parents']:
        family,piece=mapping[int(parent['family_id'])]
        parent['family_id']=np.array(family);parent['piece_id']=np.array(piece)
    for record in metadata.get('terminated',[]):
        family,piece=mapping[record['family_id']]
        record['family_id']=family;record['piece_id']=piece
    metadata.update(implementation='SEGMENTED_MEASURED_PARENT_RETURN_RECURRENCE_V2',
        source_ownership_coverage=coverage,formed_pieces=len(next_state['parents']),
        formed_family_ids=sorted({int(p['family_id']) for p in next_state['parents']}),
        all_current_parent_pieces_measured_independently=True)
    next_state['last_step']=metadata
    evidence.update(coverage_evidence)
    return out,outchart,next_state,metadata,evidence
