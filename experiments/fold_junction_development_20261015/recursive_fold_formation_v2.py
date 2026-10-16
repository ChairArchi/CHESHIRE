"""Original PCHIP fold-section family in freshly measured parent N/B frames.

Original event descriptors seed transverse macro-parent ownership. A parent
flows along theta and is sampled across material t; emitted child ownership
is measured anew on every next actual mesh. The same expansion/constriction/
re-expansion and signed back-return section is formed at each physical scale.
No phase harmonic, camera coordinate or manually selected patch is introduced.
"""
from pathlib import Path
import importlib.util
import types

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d


HERE=Path(__file__).resolve().parent
V3_PATH=HERE/'recursive_parent_folds_v3.py'
_spec=importlib.util.spec_from_file_location('physical_parent_formation_source_lookup',V3_PATH)
v3=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(v3)
core=v3.core
EVENT_PATH=HERE/'original_fold_events.py'
_event_spec=importlib.util.spec_from_file_location('physical_parent_exact_original_events',EVENT_PATH)
original_events=importlib.util.module_from_spec(_event_spec);_event_spec.loader.exec_module(original_events)
PROFILE_SOURCE=HERE.parent/'curved_fold_side_20261011/smooth_deep.py'
# Exact published-in-repository smooth_deep section abscissae and value
# arrangement; amplitudes below are newly parent-relative, not copied units.
KNOTS=np.array([-2.2,-1.4,-.75,-.35,-.15,.15,.35,.75,1.3,2.])
NORMAL_PROFILE=np.array([0.,.1,.62,1.,.3,-.65,-.35*.65,.75,.4*.75,0.])
RETURN_PROFILE=np.array([0.,0.,.2,1.,.6,-.6,-1.,-.2,0.,0.])
_NORMAL=PchipInterpolator(KNOTS,NORMAL_PROFILE,extrapolate=False)
_RETURN=PchipInterpolator(KNOTS,RETURN_PROFILE,extrapolate=False)


def helper_paths():
    return list(dict.fromkeys([V3_PATH,PROFILE_SOURCE,EVENT_PATH,HERE/'actual_seed_fold_events.json']+
        v3.helper_paths()+original_events.helper_paths()))


def initialize_events(events):
    """Existing generative event provenance only; no new event placement."""
    parents=[]
    for index,event in enumerate(events):
        required=('height','span','direction','sweep','overlap_width')
        if not all(key in event for key in required):
            raise ValueError('Original return event descriptor is missing its ownership fields.')
        parents.append(dict(seed_event=dict(event),family_id=index,piece_id='0',tier=0))
    if not parents:
        raise ValueError('Existing source return event provenance is required.')
    return dict(schema='MEASURED_PARENT_RETURN_RECURRENCE_V1',parents=parents,
                formation_cycles=0,active=True,formation_family='PCHIP_N_B_CROSS_SECTION')


def initialize(rails_list):
    parents=[]
    for index,rail in enumerate(rails_list):
        if str(rail.get('axis','')) not in ('theta','height'):
            raise ValueError('Actual transverse or longitudinal parent ownership required.')
        p=np.asarray(rail['parameter'])
        parents.append(dict(rail=core._copy_rail(rail),family_id=index,piece_id='0',tier=0,
            longitudinal_extent=[float(p[0]),float(p[-1])]))
    return dict(schema='MEASURED_PARENT_RETURN_RECURRENCE_V1',parents=parents,
                formation_cycles=0,active=bool(parents),formation_family='PCHIP_N_B_CROSS_SECTION')


def _uv(parameter,cross,axis):
    parameter,cross=np.broadcast_arrays(parameter,cross)
    return np.stack((cross,parameter) if axis=='theta' else (parameter,cross),axis=-1)


def _quintic(x):
    x=np.clip(x,0.,1.)
    return x*x*x*(10.-15.*x+6.*x*x)


def _frames(centres,parameter,left,right):
    # Pool guide geometry only at the daughter forming scale. The incoming
    # mesh and its normals outside these owned guides are never filtered.
    centres=gaussian_filter1d(np.asarray(centres),3.,axis=0,mode='nearest')
    tangent=core.region_fold.unit(np.gradient(centres,parameter,axis=0))
    across=gaussian_filter1d(np.asarray(right)-np.asarray(left),3.,axis=0,mode='nearest')
    across=core.region_fold.unit(across-tangent*np.einsum('ij,ij->i',across,tangent)[:,None])
    normal=core.region_fold.unit(np.cross(tangent,across))
    radial=np.column_stack((centres[:,:2],np.zeros(len(centres))))
    # One orientation per connected guide: an overhanging ray must not flip
    # its frame merely because its outward radial dot changes sign locally.
    sign=1. if np.median(np.einsum('ij,ij->i',normal,radial))>=0. else -1.
    return tangent*sign,across,normal*sign


def _measure_child(sampler,parent):
    axis=str(parent['axis']);p=np.asarray(parent['parameter'],dtype=float)
    lo,mid,hi=(np.asarray(parent[key],dtype=float) for key in ('lower_cross','guide_cross','upper_cross'))
    f=np.linspace(0.,1.,257)
    cross=lo[:,None]+(hi-lo)[:,None]*f
    xyz,ids,bary=sampler.sample(_uv(p[:,None],cross,axis),records=True)
    centre=sampler.sample(_uv(p,mid,axis))
    tangent,across,normal=_frames(centre,p,xyz[:,0],xyz[:,-1])
    profile=np.einsum('nkj,nj->nk',xyz,normal)
    left_width=np.linalg.norm(centre-xyz[:,0],axis=1)
    right_width=np.linalg.norm(xyz[:,-1]-centre,axis=1)
    expected_depth=np.minimum(left_width,right_width)*np.tan(np.deg2rad(30.))
    valid=np.zeros(len(p),bool);valley=np.full(len(p),np.nan);prominence=np.zeros(len(p))
    for row in range(len(p)):
        peaks,properties=find_peaks(-profile[row],prominence=.04*expected_depth[row])
        if len(peaks):
            near=np.abs(cross[row,peaks]-mid[row])<=.30*(hi[row]-lo[row])
            peaks=peaks[near];properties_prom=properties['prominences'][near]
            if len(peaks):
                take=int(np.argmin(np.abs(cross[row,peaks]-mid[row])))
                valley[row]=cross[row,peaks[take]];prominence[row]=properties_prom[take];valid[row]=True
    if valid.sum()<=len(valid)/2:
        raise core.AbsentParentFold('Actual macro-parent basin absent on majority of complete owned rays.')
    observed=np.flatnonzero(valid);take=np.arange(observed[0],observed[-1]+1)
    if len(take)<5:
        raise core.AbsentParentFold('Too few bracketed macro-parent basin rays.')
    parameter=p[take];trough=np.interp(parameter,p[valid],valley[valid])
    # Both shoulders are actual geometry. Choose one family-wide side by
    # measured physical arc, rather than always taking increasing material t.
    left_cross=lo[take,None]+(trough-lo[take])[:,None]*np.linspace(0.,1.,129)
    right_cross=trough[:,None]+(hi[take]-trough)[:,None]*np.linspace(0.,1.,129)
    left_xyz=sampler.sample(_uv(parameter[:,None],left_cross,axis))
    right_xyz=sampler.sample(_uv(parameter[:,None],right_cross,axis))
    left_arc=np.linalg.norm(np.diff(left_xyz,axis=1),axis=2).sum(axis=1)
    right_arc=np.linalg.norm(np.diff(right_xyz,axis=1),axis=2).sum(axis=1)
    side='LOWER' if np.median(left_arc)>np.median(right_arc) else 'UPPER'
    wall_cross=left_cross if side=='LOWER' else right_cross
    wall_uv=_uv(parameter[:,None],wall_cross,axis)
    wall_xyz,wall_ids,wall_bary=sampler.sample(wall_uv,records=True)
    arc=np.concatenate((np.zeros((len(take),1)),np.cumsum(np.linalg.norm(np.diff(wall_xyz,axis=1),axis=2),axis=1)),axis=1)
    if np.any(arc[:,-1]<=1e-10):
        raise core.AbsentParentFold('Measured macro-parent shoulder has no positive physical arc.')
    # Half of the actual whole shoulder forms the daughter. The
    # centre guide follows the exact PCHIP constriction abscissa within it.
    constriction_fraction=(.15-KNOTS[0])/(KNOTS[-1]-KNOTS[0])
    fractions=(.25,.25+.50*constriction_fraction,.75)
    owned=np.asarray([[np.interp(frac*arc[row,-1],arc[row],wall_cross[row])
                       for frac in fractions] for row in range(len(parameter))])
    rails_uv=_uv(parameter[:,None],owned,axis)
    rails_xyz,rail_ids,rail_bary=sampler.sample(rails_uv,records=True)
    t,b,n=_frames(rails_xyz[:,1],parameter,rails_xyz[:,0],rails_xyz[:,2])
    chord_uv=_uv(parameter[:,None],np.column_stack((lo[take],trough,hi[take])),axis)
    chord_xyz,chord_ids,chord_bary=sampler.sample(chord_uv,records=True)
    vector=chord_xyz[:,2]-chord_xyz[:,0]
    alpha=np.clip(np.einsum('ij,ij->i',chord_xyz[:,1]-chord_xyz[:,0],vector)/
        np.maximum(np.einsum('ij,ij->i',vector,vector),1e-30),0.,1.)
    depth=np.maximum(0.,np.einsum('ij,ij->i',chord_xyz[:,0]+alpha[:,None]*vector-chord_xyz[:,1],normal[take]))
    if np.count_nonzero(depth>1e-10)<=len(depth)/2:
        raise core.AbsentParentFold('Actual macro-parent shoulder-chord depth is absent on majority of rays.')
    full_width=arc[:,-1]
    child_width=.50*full_width
    length=float(np.linalg.norm(np.diff(rails_xyz[:,1],axis=0),axis=1).sum())
    normal_amp=np.minimum(.35*depth,.25*child_width)
    confidence=np.clip(depth/np.maximum(.15*full_width,1e-12),0.,1.)
    return_amp=np.minimum(.08*child_width,.12*length)*confidence
    normal_amp=np.minimum(normal_amp,gaussian_filter1d(normal_amp,3.,mode='nearest'))
    return_amp=np.minimum(return_amp,gaussian_filter1d(return_amp,3.,mode='nearest'))
    child=dict(axis=np.array(axis),parameter=parameter,lower_cross=owned[:,0],
        guide_cross=owned[:,1],upper_cross=owned[:,2],centre_xyz=rails_xyz[:,1],
        centre_fit=gaussian_filter1d(rails_xyz[:,1],3.,axis=0,mode='nearest'),tangent=t,across=b,normal=n,
        depth=normal_amp,depth_cap=normal_amp,parent_observed_chord_depth=depth,
        parent_expected_detection_depth=expected_depth[take],parent_physical_width=full_width,
        parent_physical_longitudinal_length=np.array(length),
        parent_shoulder_side=np.array(side),child_physical_width=child_width,
        formation_normal_amplitude=normal_amp,formation_return_amplitude=return_amp,
        formation_carrier_lower=gaussian_filter1d(rails_xyz[:,0],3.,axis=0,mode='nearest'),
        formation_carrier_upper=gaussian_filter1d(rails_xyz[:,2],3.,axis=0,mode='nearest'),
        formation_shoulder_cross=wall_cross,formation_shoulder_arc=arc,
        formation_owned_arc_fraction=np.asarray(fractions),
        measured_left_arc=arc[:,-1]*(fractions[1]-fractions[0]),
        measured_right_arc=arc[:,-1]*(fractions[2]-fractions[1]))
    evidence=dict(parent_search_parameter=p,parent_search_valid=valid,
        parent_search_profile=profile,parent_search_prominence=prominence,
        parent_search_xyz=xyz,parent_search_triangle_ids=ids,parent_search_barycentric=bary,
        actual_parent_chord_depth=depth,expected_detection_depth=expected_depth[take],
        actual_shoulder_uv=wall_uv,actual_shoulder_xyz=wall_xyz,actual_shoulder_arc=arc,
        actual_shoulder_triangle_ids=wall_ids,actual_shoulder_barycentric=wall_bary,
        child_rail_uv=rails_uv,child_rail_xyz=rails_xyz,child_rail_triangle_ids=rail_ids,
        child_rail_barycentric=rail_bary,parent_chord_uv=chord_uv,parent_chord_xyz=chord_xyz,
        parent_chord_triangle_ids=chord_ids,parent_chord_barycentric=chord_bary)
    return child,evidence


def _physical_across(parameter,cross,child):
    p=child['parameter'];samples=child['formation_shoulder_cross'];arc=child['formation_shoulder_arc']
    low=np.clip(np.searchsorted(p,parameter,side='right')-1,0,len(p)-2);high=low+1
    alpha=(parameter-p[low])/(p[high]-p[low])
    value=np.zeros(len(parameter))
    for row in range(len(p)):
        for query,weight in ((low,1.-alpha),(high,alpha)):
            choose=query==row
            if choose.any(): value[choose]+=weight[choose]*np.interp(cross[choose],samples[row],arc[row])
    total=np.interp(parameter,p,arc[:,-1])
    return np.divide(value/np.maximum(total,1e-30)-.25,.50)


def _formation_delta(xyz,chart,children,angle,depth_ratio,strength):
    # angle/depth_ratio remain in the common runner signature for compatibility;
    # the PCHIP family uses its declared physical dimensionless ratios instead.
    parameter_height=chart[:,0]
    theta=np.arctan2(np.abs(chart[:,2]),np.abs(chart[:,1]))
    signs=np.where(chart[:,1:]<0.,-1.,1.)
    delta=np.zeros_like(xyz);total_weight=np.zeros(len(xyz));unoccupied=np.ones(len(xyz));weights=[]
    applied_depths=[]
    for child in children:
        axis=str(child['axis']);parameter=theta if axis=='theta' else parameter_height
        cross=parameter_height if axis=='theta' else theta
        p=child['parameter']
        lo=np.interp(parameter,p,child['lower_cross']);hi=np.interp(parameter,p,child['upper_cross'])
        selected=(parameter>p[0])&(parameter<p[-1])&(cross>lo)&(cross<hi)
        ids=np.flatnonzero(selected)
        weight=np.zeros(len(xyz))
        if not len(ids):
            weights.append(weight);applied_depths.append(child['formation_normal_amplitude']);continue
        s=(parameter[ids]-p[0])/(p[-1]-p[0])
        across=_physical_across(parameter[ids],cross[ids],child)
        transverse=2.*across-1.
        q=np.clip(np.abs(transverse),0.,1.)
        rounded=(np.sqrt(q*q+.12**2)-.12)/(np.sqrt(1+.12**2)-.12)
        wave=(1.-1.5*rounded+.5*rounded**3)*_quintic((1.-q)/.20)
        along=64.*s**3*(1.-s)**3
        weight[ids]=along*wave
        # Same original section family, now across a measured parent shoulder.
        u=KNOTS[0]+(KNOTS[-1]-KNOTS[0])*across
        nr=np.nan_to_num(_NORMAL(u));br=np.nan_to_num(_RETURN(u))
        n=core.region_fold.unit(np.column_stack([np.interp(parameter[ids],p,child['normal'][:,k]) for k in range(3)]))
        b=core.region_fold.unit(np.column_stack([np.interp(parameter[ids],p,child['across'][:,k]) for k in range(3)]))
        b=core.region_fold.unit(b-n*np.einsum('ij,ij->i',b,n)[:,None])
        normal_amp=np.interp(parameter[ids],p,child['formation_normal_amplitude'])
        return_amp=np.interp(parameter[ids],p,child['formation_return_amplitude'])
        left=np.column_stack([np.interp(parameter[ids],p,child['formation_carrier_lower'][:,k]) for k in range(3)])
        right=np.column_stack([np.interp(parameter[ids],p,child['formation_carrier_upper'][:,k]) for k in range(3)])
        carrier=(1.-across[:,None])*left+across[:,None]*right
        target=carrier+(normal_amp*nr)[:,None]*n+(return_amp*br)[:,None]*b
        source=xyz[ids].copy();source[:,:2]*=signs[ids]
        move=(target-source)*weight[ids,None]
        move[:,:2]*=signs[ids]
        delta[ids]+=move;total_weight+=weight;unoccupied*=1.-weight;weights.append(weight)
        applied_depths.append(child['formation_normal_amplitude'])
    # A smooth partition blends overlapping target sheets; it does not pile
    # several independently formed daughters on the same incoming surface.
    occupancy=1.-unoccupied
    denominator=np.divide(total_weight,occupancy,out=np.ones_like(total_weight),where=occupancy>1e-15)
    return strength*delta/denominator[:,None],dict(return_weights=np.asarray(weights),
        overlap_denominator=denominator,actual_child_groove_depths=applied_depths)


def _seed_rail(event):
    lo=max(.025,float(event['direction'])-.82*float(event['overlap_width']))
    hi=min(np.pi/2-.025,float(event['direction'])+.82*float(event['overlap_width']))
    if hi-lo<.10:
        raise core.AbsentParentFold('Original event has no substantial canonical angular support.')
    p=np.linspace(lo,hi,65)
    # Exact legacy source warp and swept local-height inversion, not a fitted
    # current-height span. This bracket includes both expansion shoulders.
    lower=original_events.event_height(p,-.75,event)
    guide=original_events.event_height(p,.15,event)
    upper=original_events.event_height(p,1.3,event)
    return dict(axis=np.array('theta'),parameter=p,lower_cross=lower,
        guide_cross=guide,upper_cross=upper)


def _clip_components(sampler,rail):
    """Keep the actual cross-component containing the inherited macro basin.

    An upper attachment hole clips a shoulder; it does not discard the whole
    angular ray. If the nominal valley itself is absent, only a genuinely
    detected radial basin in another connected SOURCE interval can qualify.
    """
    axis=str(rail['axis']);p=np.asarray(rail['parameter'])
    low,mid,high=(np.asarray(rail[key],float) for key in ('lower_cross','guide_cross','upper_cross'))
    fractions=np.linspace(0.,1.,257)
    cross=low[:,None]+(high-low)[:,None]*fractions
    uv=_uv(p[:,None],cross,axis)
    xyz,valid,ids,bary=sampler.coverage(uv)
    _,guide_valid,_,_=sampler.coverage(_uv(p,mid,axis))
    new_lo=low.copy();new_hi=high.copy();new_mid=mid.copy()
    accepted=np.zeros(len(p),bool);reason=[]
    for row in range(len(p)):
        bounds=np.flatnonzero(np.diff(np.r_[False,valid[row],False]))
        runs=[(int(a),int(b)) for a,b in zip(bounds[::2],bounds[1::2]) if b-a>=9]
        containing=[(a,b) for a,b in runs if cross[row,a]<=mid[row]<=cross[row,b-1]]
        if guide_valid[row] and containing:
            a,b=containing[0];reason.append('NOMINAL_VALLEY_ACTUAL_SOURCE_COMPONENT')
        else:
            candidates=[]
            for a,b in runs:
                radial=np.linalg.norm(xyz[row,a:b,:2],axis=1)
                arc=np.linalg.norm(np.diff(xyz[row,a:b],axis=0),axis=1).sum()
                if arc<=1e-10:continue
                peaks,prop=find_peaks(-radial,prominence=.02*arc)
                for peak in peaks:
                    j=a+int(peak)
                    if abs(cross[row,j]-mid[row])<=.35*(high[row]-low[row]):
                        candidates.append((abs(cross[row,j]-mid[row]),a,b,j))
            if not candidates:
                reason.append('NO_SOURCE_COMPONENT_CONTAINING_ACTUAL_OR_NOMINAL_BASIN');continue
            _,a,b,j=min(candidates)
            new_mid[row]=cross[row,j];reason.append('ACTUAL_DETECTED_BASIN_SOURCE_COMPONENT')
        # Stay inside the last verified containing triangles. No invented XYZ
        # is used at clipped endpoints; all subsequent points are resampled.
        inset=.02*(cross[row,1]-cross[row,0])
        new_lo[row]=cross[row,a]+inset;new_hi[row]=cross[row,b-1]-inset
        accepted[row]=new_lo[row]<new_mid[row]<new_hi[row]
    result=dict(rail,lower_cross=new_lo,guide_cross=new_mid,upper_cross=new_hi)
    evidence=dict(uv=uv,xyz=xyz,valid=valid,native_triangle_ids=ids,barycentric=bary,
        nominal_guide_valid=guide_valid,accepted_longitudinal_ray=accepted,
        clipped_lower_cross=new_lo,clipped_upper_cross=new_hi,actual_or_nominal_guide=new_mid)
    return result,accepted,reason,evidence


def _measure_safe(sampler,parent):
    try:
        return _measure_child(sampler,parent)
    except ValueError as error:
        if 'Degenerate measured guide frame' in str(error):
            raise core.AbsentParentFold(str(error)) from error
        raise


def _resolve_and_partition(mesh,chart,state,body):
    recorded,info=core.native_body_sampler(mesh,chart,body);sampler=v3.CoverageSampler(recorded)
    parents,records,evidence=[],[],{}
    for old in state['parents']:
        family=int(old['family_id']);piece=str(np.asarray(old.get('piece_id','0')))
        try:
            if 'seed_event' in old:
                rail=_seed_rail(old['seed_event'])
                extent=np.asarray(rail['parameter'])[[0,-1]].tolist()
            else:
                rail=v3._rail(old);extent=np.asarray(old['longitudinal_extent']).tolist()
            axis=str(rail['axis']);p=np.asarray(rail['parameter'])
            rail,valid_ray,reasons,source_evidence=_clip_components(sampler,rail)
            for key,value in source_evidence.items():
                evidence[f'source_component_{family}_{piece}_{key}']=value
            bounds=np.flatnonzero(np.diff(np.r_[False,valid_ray,False]))
            accepted=0
            for number,(first,last) in enumerate(zip(bounds[::2],bounds[1::2])):
                if last-first<5:continue
                pid=piece if first==0 and last==len(p) else piece+'.'+str(number)
                parents.append(dict(rail=v3._slice_rail(rail,first,last),family_id=family,
                    piece_id=pid,tier=int(old.get('tier',0)),longitudinal_extent=extent))
                accepted+=1
            records.append(dict(family_id=family,piece_id=piece,axis=axis,
                bank_id=old.get('seed_event',{}).get('bank_id'),
                valid_rays=int(valid_ray.sum()),total_rays=len(p),accepted_pieces=accepted,
                source_component_reasons=reasons,
                clipped_lower_cross=np.asarray(rail['lower_cross']).tolist(),
                clipped_upper_cross=np.asarray(rail['upper_cross']).tolist()))
        except ValueError as error:
            records.append(dict(family_id=family,piece_id=piece,status='NO_ACTUAL_SOURCE_PARENT',reason=str(error)))
    return dict(state,parents=parents,active=bool(parents)),records,sampler,info,evidence


def step(mesh,chart,fold_state,body_face_mask,vertex_pairs=None,*,
         subdivide=False,angle=.65,depth_ratio=.28,strength=1.):
    """Same five-return API; parent measured fresh, one CC, N/B forming."""
    segmented,coverage,sampler,info,source_evidence=_resolve_and_partition(mesh,chart,fold_state,body_face_mask)
    mapping={};internal=[]
    for number,parent in enumerate(segmented['parents']):
        mapping[number]=(int(parent['family_id']),str(parent['piece_id']))
        internal.append(dict(parent,family_id=number))
    namespace=dict(vars(core));namespace['native_body_sampler']=lambda unused_mesh,unused_chart,unused_mask:(sampler,info)
    namespace['_measure_owned_child']=_measure_safe;namespace['_return_delta']=_formation_delta
    run=types.FunctionType(core.step.__code__,namespace,name='parent_PCHIP_section_recurrence',argdefs=core.step.__defaults__)
    run.__kwdefaults__=dict(core.step.__kwdefaults__)
    out,outchart,next_state,metadata,evidence=run(mesh,chart,dict(segmented,parents=internal),
        body_face_mask,vertex_pairs,subdivide=subdivide,angle=angle,depth_ratio=depth_ratio,strength=strength)
    for parent in next_state['parents']:
        family,piece=mapping[int(parent['family_id'])]
        parent['family_id']=np.array(family);parent['piece_id']=np.array(piece)
    for terminated in metadata.get('terminated',[]):
        family,piece=mapping[terminated['family_id']]
        terminated.update(family_id=family,piece_id=piece)
    metadata.update(implementation='RECURSIVE_MEASURED_PARENT_PCHIP_N_B_FORMATION_V2',
        source_event_coverage=coverage,formed_pieces=len(next_state['parents']),
        formed_family_ids=sorted({int(parent['family_id']) for parent in next_state['parents']}),
        geometry='Original smooth_deep PCHIP expansion/constriction/re-expansion and signed back-return profile forms a daughter target on a local pooled boundary-rail ruled carrier in actual parent N/B frames. Compact C2 support blends this target with the actual source; overlapping targets use smooth partition weights.',
        geometry_profile_source=str(PROFILE_SOURCE),profile_knots=KNOTS.tolist(),
        normal_profile=NORMAL_PROFILE.tolist(),signed_return_profile=RETURN_PROFILE.tolist(),
        child_footprint='25 to 75 percent of the physically larger actual trough shoulder; 50 percent physical forming footprint. Constriction guide follows the original PCHIP minimum abscissa.',
        amplitude_budget='Normal=min(.35*actual parent chord depth,.25*physical child width). Back-return=min(.08*physical child width,.12*actual parent flow length)*actual depth confidence. Child width=.50*actual shoulder arc. Amplitudes are guide-pooled and bounded by their original per-ray budgets. These profile amplitudes do not bound the separate local carrier correction.',
        parent_detection='Fresh actual native source profiles and frame,4%width-derived expecteddepth prominence threshold, nearest detected basin within the inherited owned corridor, actual chord depth checked on majority of rays.',
        endpoint_continuity='Compact cubic axial envelope and rounded transverse support with quintic edge gate; roots and owned boundaries have zero displacement/firsttwo derivatives.',
        actual_depth='Actual parent chord depth caps the normal expansion; signed transverse back-return has a separate measured-width/length budget. The old groove-depth/Rodrigues descriptions do not apply.',
        source_component_policy='Dense 257-point actual native SOURCE coverage per longitudinal ray. Clip to the connected cross-component containing the nominal or actually detected macro basin, then split only missing longitudinal runs. No nearest world fallback or hole bridging.',
        frame_orientation='Gaussian sigma 3 rays pools only measured guide curves/across vectors before fresh orthonormal frames; one pooled radial sign per connected guide prevents local overhang sign flips.',
        formation_angle_parameter_used=False,formation_depth_ratio_parameter_used=False,
        limitations='Existing column material chart and original event provenance only; not an arbitrarymesh solver. Actual absent parent basins terminate. Fullprofileformation can create overhangs and is not a global intersection or beauty certificate.')
    next_state['last_step']=metadata;next_state['formation_family']='PCHIP_N_B_CROSS_SECTION'
    evidence.update(source_evidence)
    return out,outchart,next_state,metadata,evidence
