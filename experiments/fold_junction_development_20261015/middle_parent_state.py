"""Initialize current G6 body-ribbon ownership from its actual scalar field.

Registered MIDDLE phase seeds ownership only. Every phase observation is an
actual barycentric SOURCE-native sample; the subsequent RETURN operator must
remeasure current geometry, normals, widths and basin depths independently.
No camera coordinates, authored ornament placements or geometry edits occur.
"""
from pathlib import Path
import importlib.util
import itertools

import numpy as np

HERE=Path(__file__).resolve().parent
BRANCH_PATH=HERE/'branch_detail.py'
_spec=importlib.util.spec_from_file_location('middle_seed_measured_lobes',BRANCH_PATH)
branch=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(branch)


def helper_paths():
    return [BRANCH_PATH,*branch.helper_paths()]


def _observe(sampler,uv,phase,quads):
    """Actual native fan phase, never a chart-nearest XYZ approximation."""
    xyz,valid,triangle,bary=sampler.coverage(uv)
    valid=np.asarray(valid,dtype=bool).copy()
    triangle,bary=np.asarray(triangle),np.asarray(bary)
    scalar=np.full(valid.shape,np.nan)
    if np.any(valid):
        tri=triangle[valid]
        face,corner=tri//4,tri%4
        if np.any(face<0) or np.any(face>=len(quads)):
            raise ValueError('Coverage sampler must return original global quad-fan triangle IDs.')
        q=quads[face]
        p0=phase[q[np.arange(len(q)),corner]]
        p1=phase[q[np.arange(len(q)),(corner+1)%4]]
        pc=phase[q].mean(axis=1)
        scalar[valid]=(bary[valid]*np.column_stack((p0,p1,pc))).sum(axis=1)
    valid&=np.isfinite(scalar)&np.isfinite(xyz).all(axis=-1)&np.isfinite(bary).all(axis=-1)
    return scalar,valid,np.asarray(xyz),triangle,bary


def _brackets(values,valid,target,theta):
    found=[]
    for i in range(len(theta)-1):
        if not(valid[i] and valid[i+1]):continue
        left,right=values[i]-target,values[i+1]-target
        if left*right>0 or abs(values[i+1]-values[i])<1e-13:continue
        estimate=theta[i]+(target-values[i])*(theta[i+1]-theta[i])/(values[i+1]-values[i])
        if found and abs(estimate-found[-1]['estimate'])<1e-8:continue
        found.append(dict(lo=float(theta[i]),hi=float(theta[i+1]),
            vlo=float(values[i]),vhi=float(values[i+1]),estimate=float(estimate)))
    return found


def _ordered_triplets(values,valid,levels,theta):
    candidates=[_brackets(values,valid,target,theta) for target in levels]
    triples=[]
    for triple in itertools.product(*candidates):
        cross=np.asarray([item['estimate'] for item in triple])
        if np.all(np.diff(cross)>1e-7):triples.append((cross,triple))
        if len(triples)>128:
            return [],True
    return triples,False


def _track(all_candidates,theta_step):
    """Anchor a unique actual triplet; continue across measured stations."""
    count=len(all_candidates)
    chosen=[None]*count
    reasons=['NO_ORDERED_PHASE_TRIPLET']*count
    unique=[i for i,c in enumerate(all_candidates) if len(c)==1]
    if not unique:
        return chosen,['AMBIGUOUS_WITHOUT_UNIQUE_ANCHOR' if c else r
                       for c,r in zip(all_candidates,reasons)]
    anchor=min(unique,key=lambda i:abs(i-(count-1)/2))
    chosen[anchor]=all_candidates[anchor][0]
    reasons[anchor]='UNIQUE_ACTUAL_TRIPLET'
    for sequence in (range(anchor+1,count),range(anchor-1,-1,-1)):
        previous=chosen[anchor][0]
        for i in sequence:
            candidates=all_candidates[i]
            if not candidates:continue
            distance=np.asarray([np.linalg.norm(item[0]-previous) for item in candidates])
            order=np.argsort(distance)
            best=int(order[0])
            limit=max(4*theta_step,.65*(previous[2]-previous[0]))
            if np.max(abs(candidates[best][0]-previous))>limit:
                reasons[i]='DISCONTINUOUS_PHASE_BRANCH';continue
            if len(order)>1 and distance[order[1]]-distance[best]<.5*theta_step:
                reasons[i]='AMBIGUOUS_CONTINUATION';continue
            chosen[i]=candidates[best]
            reasons[i]='UNIQUE_ACTUAL_TRIPLET' if len(candidates)==1 else 'MULTICROSSING_RESOLVED_BY_CONTINUITY'
            previous=candidates[best][0]
    return chosen,reasons


def _refine(sampler,parameter,chosen,levels,phase,quads):
    rows=np.asarray([i for i,item in enumerate(chosen) if item is not None],dtype=np.int64)
    cross=np.full((len(parameter),3),np.nan)
    valid=np.zeros(len(parameter),dtype=bool)
    if not len(rows):return cross,valid,{}
    bracket=[[item for item in chosen[row][1]] for row in rows]
    lo=np.asarray([[item['lo'] for item in triple] for triple in bracket])
    hi=np.asarray([[item['hi'] for item in triple] for triple in bracket])
    vlo=np.asarray([[item['vlo'] for item in triple] for triple in bracket])
    target=np.broadcast_to(levels,lo.shape)
    live=np.ones(lo.shape,dtype=bool)
    t=np.broadcast_to(parameter[rows,None],lo.shape)
    for _ in range(14):
        mid=(lo+hi)/2.
        value,covered,_,_,_=_observe(sampler,np.stack((t,mid),axis=-1),phase,quads)
        live&=covered
        same=(vlo-target)*(value-target)>0
        lo=np.where(live&same,mid,lo)
        vlo=np.where(live&same,value,vlo)
        hi=np.where(live&~same,mid,hi)
    root=(lo+hi)/2.
    uv=np.stack((t,root),axis=-1)
    value,covered,xyz,triangle,bary=_observe(sampler,uv,phase,quads)
    live&=covered&(abs(value-target)<2e-4)
    good=live.all(axis=1)&(np.diff(root,axis=1)>1e-7).all(axis=1)
    cross[rows[good]]=root[good]
    valid[rows[good]]=True
    return cross,valid,dict(station_indices=rows,root_uv=uv,root_xyz=xyz,
        root_native_triangle_ids=triangle,root_barycentric=bary,
        root_observed_phase=value,root_target_phase=target,root_valid=live)


def initialize_middle(mesh,chart,phase,body_mask,sampler,*,bins=96):
    """Return ``(fold_state,metadata,evidence)`` for measured RETURN recurrence.

    ``sampler.coverage(uv)`` supplies (XYZ,valid,global fan triangle IDs,bary).
    A scalar lobe detector on current old-G4 samples sets finite longitudinal
    episodes. For phase cycle k, actual native level sets 2pi*k,(2k+1)pi,
    2pi*(k+1) seed lower crest, valley and upper crest ownership. Future calls
    consume the emitted state and remeasure geometry; phase is not reapplied.
    """
    x,q,chart,phase=map(np.asarray,(mesh.xyz,mesh.faces,chart,phase))
    body=np.asarray(body_mask,dtype=bool)
    if (x.ndim!=2 or x.shape[1]!=3 or chart.shape!=x.shape or phase.shape!=(len(x),) or
            q.ndim!=2 or q.shape[1]!=4 or body.shape!=(len(q),) or
            not all(np.isfinite(v).all() for v in (x,chart,phase))):
        raise ValueError('Actual current mesh/chart/phase/SOURCE face ownership required.')
    if not hasattr(sampler,'coverage'):
        raise ValueError('Exact coverage-aware SOURCE native sampler required.')
    coarse=q
    levels_back=max(0,int(mesh.generation)-4)
    for _ in range(levels_back):
        if len(coarse)%4:raise ValueError('Actual old-G4 ancestry does not have four-child layout.')
        coarse=coarse.reshape(-1,4,4)[:,:,1]
    coarse_count=int(coarse.max())+1
    group=body.reshape(len(coarse),4**levels_back)
    if not np.all(group==group[:,:1]):
        raise ValueError('SOURCE ownership changes inside an ancestral G4 face.')
    coarse_body=group[:,0]
    degree=np.bincount(coarse.ravel(),minlength=coarse_count)
    if np.any(degree==0):raise ValueError('Old-G4 ancestry has orphan IDs.')
    support=np.bincount(coarse.ravel(),weights=np.repeat(coarse_body.astype(float),4),
                        minlength=coarse_count)/degree
    height=float(np.ptp(x[:,2]))
    events,detection=branch.prepare_events(x[:coarse_count],phase[:coarse_count],
        chart[:coarse_count,0],support,height,bins=bins)
    theta=np.linspace(0.,np.pi/2.,257)
    phase_bounds=(float(phase.min()),float(phase.max()))
    parents,episodes=[],[]
    evidence=dict(theta_search_grid=theta,episodes=[])
    domain_span=float(np.ptp(chart[:coarse_count,0]))
    for event_index,event in enumerate(events):
        parameter=np.linspace(float(event['t_start']),float(event['t_end']),33)
        cycle=int(event['parent_cycle'])
        targets=np.asarray([2*np.pi*cycle,(2*cycle+1)*np.pi,2*np.pi*(cycle+1)])
        if targets[0]<phase_bounds[0]-1e-8 or targets[-1]>phase_bounds[1]+1e-8:
            episodes.append(dict(event_index=event_index,phase_cycle=cycle,
                longitudinal_extent=[float(parameter[0]),float(parameter[-1])],
                formed_parent_pieces=0,status='CREST_PAIR_OUTSIDE_ACTUAL_PHASE_RANGE'))
            continue
        uv=np.stack((np.broadcast_to(parameter[:,None],(33,len(theta))),
                     np.broadcast_to(theta[None,:],(33,len(theta)))),axis=-1)
        observed,covered,_,_,_=_observe(sampler,uv,phase,q)
        candidate_rows,overflow=[],[]
        for row in range(len(parameter)):
            candidates,many=_ordered_triplets(observed[row],covered[row],targets,theta)
            candidate_rows.append(candidates);overflow.append(many)
        chosen,reasons=_track(candidate_rows,theta[1]-theta[0])
        cross,valid,root_evidence=_refine(sampler,parameter,chosen,targets,phase,q)
        reasons=['EXACT_NATIVE_ROOT_FAILED_OR_COVERAGE_HOLE' if chosen[i] is not None and not valid[i]
                 else reason for i,reason in enumerate(reasons)]
        runs=np.flatnonzero(np.diff(np.r_[False,valid,False]))
        formed=0
        for part,(first,last) in enumerate(zip(runs[::2],runs[1::2])):
            if last-first<5 or parameter[last-1]-parameter[first]<.035*domain_span:
                continue
            p=parameter[first:last].copy()
            owned=cross[first:last].copy()
            rail=dict(axis=np.array('height'),parameter=p,lower_cross=owned[:,0],
                      guide_cross=owned[:,1],upper_cross=owned[:,2])
            parents.append(dict(rail=rail,family_id=int(event_index*100+part),tier=0,
                longitudinal_extent=[float(p[0]),float(p[-1])],
                source_phase_cycle=cycle,source_lobe_event_index=event_index))
            formed+=1
        episodes.append(dict(event_index=event_index,phase_cycle=cycle,
            longitudinal_extent=[float(parameter[0]),float(parameter[-1])],
            stations=len(parameter),coverage_valid_samples=int(covered.sum()),
            phase_root_valid_stations=int(valid.sum()),formed_parent_pieces=formed,
            candidate_triplet_counts=[len(row) for row in candidate_rows],
            excessive_crossing_stations=int(np.count_nonzero(overflow)),station_status=reasons))
        evidence['episodes'].append(dict(event_index=event_index,parameter=parameter,
            targets=targets,observed_phase_grid=observed,source_coverage_mask=covered,
            selected_cross=cross,selected_station_valid=valid,roots=root_evidence))
    state=dict(schema='MEASURED_PARENT_RETURN_RECURRENCE_V1',parents=parents,
        formation_cycles=0,active=bool(parents),
        initialization='Actual registered G6 phase level sets seed SOURCE ownership only; subsequent formation remeasures actual geometry.')
    metadata=dict(implementation='ACTUAL_MIDDLE_PHASE_NATIVE_LEVELSET_INITIALIZATION_V1',
        current_generation=int(mesh.generation),old_G4_measurement_samples=coarse_count,
        radial_lobe_detection=detection,detected_lobe_episodes=len(events),
        initialized_parent_pieces=len(parents),stations_per_episode=33,
        angular_search_samples=len(theta),root_bisection_iterations=14,
        actual_vertex_phase_range=list(phase_bounds),episodes=episodes,
        scalar_sampling='Barycentric scalar on actual original global quad-centre fan triangle IDs: old corner, next corner, mean phase of current quad.',
        ownership='Ordered actual phase crest 2*pi*k, valley (2*k+1)*pi and crest2*pi*(k+1); missing/ambiguous/discontinuous or hole-crossing stations do not seed a parent.',
        recurrence='Phase is used once for ownership initialization. The next RETURN step and later calls measure actual native basin, physical shoulder arc, tangent and observed depth.',
        source_geometry_changed=False,artist_coordinates_used=False,
        limitations='This is registered G6-field ownership on established column charts, not a semantic macro-ribbon skeleton or proof that phase valleys coincide with every inherited geometric trough. Actual positive-width/basin-depth validation remains the subsequent reusable geometry operator responsibility.')
    return state,metadata,evidence
