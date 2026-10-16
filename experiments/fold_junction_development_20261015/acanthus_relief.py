"""Sparse carved acanthus relief integrated into the actual mature ribbons.

Art direction: a strong sinuous midrib supports a few broad, calm leaf lobes;
upward-curving, narrow channels separate them.  Smaller veins belong to those
lobes.  There is no global periodic ornament and no separate pasted leaf mesh.
The stable branch operator supplies fresh physical metrics and balanced V/E/F
coupling, with an isolated field binding rather than module mutation.
"""
from pathlib import Path
import importlib.util
import types

import numpy as np


BRANCH_PATH = Path(__file__).resolve().with_name('branch_detail.py')
_spec = importlib.util.spec_from_file_location('acanthus_stable_branch_core', BRANCH_PATH)
branch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(branch)
prepare_events = branch.prepare_events


def helper_paths():
    return [BRANCH_PATH]+branch.helper_paths()


def _quintic(value):
    value = np.clip(value, 0., 1.)
    return value**3*(10.-15.*value+6.*value**2)


def _bevel(distance, shoulder=.55):
    """C2 compact crown with a calm central plane and a decisive bevel."""
    return _quintic((1.-np.abs(distance))/shoulder)


def _outline(s):
    return 2.25*np.sin(np.pi*s)**2


def _event_coords(phase, longitudinal, event):
    a, b = float(event['t_start']), float(event['t_end'])
    if b <= a:
        raise ValueError('Leaf event endpoints must increase.')
    cycle = int(event['parent_cycle'])
    raw = phase-2*np.pi*cycle
    selected = ((longitudinal > a)&(longitudinal < b)&(np.abs(raw) < np.pi))
    ids = np.flatnonzero(selected)
    s = (longitudinal[ids]-a)/(b-a)
    centre = np.interp(longitudinal[ids],event['centre_t'],event['centre_phase_offset'])
    # A small directional sweep joins the measured, already sinuous trunk.
    # It changes once over the finite leaf rather than introducing a repeat.
    handedness = -1. if int(event.get('source_event_index',cycle))%2 else 1.
    centre += handedness*.16*np.sin(np.pi*s)**2*(2*s-1.)
    u = raw[ids]-centre
    axial = 64.*s**3*(1.-s)**3
    width = _outline(s)
    margin = _bevel(np.divide(u,width,out=np.full_like(u,np.inf),where=width>0.),.28)
    cycle_edge = _quintic((np.pi-np.abs(raw[ids]))/.32)
    mask = axial*margin*cycle_edge
    return ids,s,u,width,mask


def leaf_mask(phase,longitudinal,events):
    """Continuous [0,1] C2 support on only the selected finite leaf planes."""
    phase,longitudinal=np.asarray(phase),np.asarray(longitudinal)
    if phase.shape!=longitudinal.shape:
        raise ValueError('Matching inherited phase and material t samples required.')
    result=np.zeros_like(phase,dtype=float)
    for event in events:
        ids,_,_,_,mask=_event_coords(phase,longitudinal,event)
        result[ids]=np.maximum(result[ids],mask)
    return result


def _vein_layout(count):
    if count==3:
        return [( .16,.43),( .38,.65),( .62,.86)]
    if count==5:
        return [( .10,.34),( .22,.48),( .36,.63),( .51,.77),( .66,.88)]
    return [( .12,.37),( .28,.55),( .45,.71),( .62,.86)]


def _bezier_rail(s,start,finish,reach,side):
    parameter=np.linspace(0.,1.,65)
    v=1.-parameter
    ts=v**3*start+3*v*v*parameter*(start+.05)+3*v*parameter**2*(finish-.035)+parameter**3*finish
    us=side*reach*(3*v*v*parameter*.12+3*v*parameter**2*.78+parameter**3)
    return np.interp(s,ts,us),np.interp(s,ts,parameter)


def carved_field(phase,longitudinal,events,*,tier=0):
    """Dimensionless carved leaf; tier1 inhabits tier0's explicit lobe rails."""
    phase,longitudinal=np.asarray(phase),np.asarray(longitudinal)
    if phase.shape!=longitudinal.shape or tier not in (0,1):
        raise ValueError('Matching leaf coordinates and tier0/tier1 required.')
    result=np.zeros_like(phase,dtype=float)
    for event in events:
        ids,s,u,width,mask=_event_coords(phase,longitudinal,event)
        if not len(ids):
            continue
        stem_width=.14+.075*np.sin(np.pi*s)**2
        stem_core=_bevel(u/stem_width,.55)
        # A calm broad blade carries the ribs; max orchestration prevents
        # additive bulges at their common roots and at overlapping crowns.
        positive=np.maximum(.20*_bevel(np.divide(u,width,
            out=np.full_like(u,np.inf),where=width>0.),.35),stem_core)
        negative=np.zeros_like(s)
        subordinate_positive,subordinate_negative=np.zeros_like(s),np.zeros_like(s)
        count=int(event.get('leaf_side_count',4))
        if count not in (3,4,5):
            raise ValueError('Curated leaf_side_count must be3,4or5.')
        variation=.9+.05*(int(event.get('source_event_index',0))%3)
        for index,(start,finish) in enumerate(_vein_layout(count)):
            reach=.89*float(_outline(finish))*variation
            for side in (-1.,1.):
                # Slightly different reaches are deliberate sculptural
                # balance, never randomness or another periodic field.
                local_reach=reach*(1. if side<0 else .94+.015*index)
                rail,v=_bezier_rail(s,start,finish,local_reach,side)
                inside=(s>start)&(s<finish)
                gate=np.zeros_like(s)
                gate[inside]=64.*v[inside]**3*(1.-v[inside])**3
                lobe_width=.31+.20*np.sin(np.pi*v)**2
                crown=.64*gate*_bevel((u-rail)/lobe_width,.45)
                positive=np.maximum(positive,crown)
                # The channel curves along the inner edge of its thick lobe.
                # It releases smoothly before the shared central midrib.
                channel_rail=rail-side*.34*np.sin(np.pi*v)**2
                channel=gate*_bevel((u-channel_rail)/(.095+.025*np.sin(np.pi*v)**2),.65)
                negative=np.maximum(negative,channel)
                if tier==1:
                    # Two finite veins grow from each particular primary
                    # rail. Their locations vary with its own local length.
                    for child_start,child_finish in ((.23,.59),(.51,.84)):
                        local=(v-child_start)/(child_finish-child_start)
                        child_inside=inside&(local>0.)&(local<1.)
                        cgate=np.zeros_like(s)
                        cgate[child_inside]=64.*local[child_inside]**3*(1.-local[child_inside])**3
                        child_rail=rail+side*.24*np.sin(np.pi*np.clip(local,0.,1.))**2
                        target=.30*cgate*gate*_bevel((u-child_rail)/.075,.6)
                        subordinate_positive=np.maximum(subordinate_positive,target)
                        groove=.16*cgate*gate*_bevel((u-child_rail+side*.085)/.045,.65)
                        subordinate_negative=np.maximum(subordinate_negative,groove)
        # A restrained channel defines the leaf margin, with no raised lip.
        margin_channel=_bevel((np.abs(u)-.90*width)/np.maximum(.065*width,.015),.7)
        negative=np.maximum(negative,.38*margin_channel)
        protect_stem=(1.-stem_core)**2
        if tier==0:
            field=positive-.52*negative*protect_stem
        else:
            field=subordinate_positive-subordinate_negative*protect_stem
        field*=mask*float(event.get('art_weight',1.))
        # Selected events can overlap slightly on the same mature ribbon.
        # Retain the stronger sculptural gesture rather than summing bumps.
        use=np.abs(field)>np.abs(result[ids])
        result[ids[use]]=field[use]
    return result


def split_detail(xyz_parent,faces_parent,faces_child,edges,degree,
                 phase_parent,body_support,height,mirror_pairs=None,*,
                 longitudinal_parent=None,events=None,tier=0,gain=1.,
                 maximum_height_fraction=.006):
    """Return actual child detail delta and an honest sculptural receipt.

    The existing fresh quad phase-gradient metric budgets amplitude by
    min(.45*actual_parent_width*gain,.006H). Isolated function globals bind
    only its scalar field to this leaf; imported module state is unchanged.
    """
    if tier not in (0,1):
        raise ValueError('Only an explicit main leaf and subordinate vein tier exist.')
    if longitudinal_parent is None or events is None:
        raise ValueError('Actual material t and curated leaf events are required.')
    def bound_field(phase,longitudinal,selected_events,**unused):
        return carved_field(phase,longitudinal,selected_events,tier=tier)
    namespace=dict(vars(branch))
    namespace['branch_field']=bound_field
    core=types.FunctionType(branch.split_detail.__code__,namespace,
        name='isolated_acanthus_metric_and_coupling',argdefs=branch.split_detail.__defaults__)
    core.__kwdefaults__=dict(branch.split_detail.__kwdefaults__)
    delta,metadata=core(xyz_parent,faces_parent,faces_child,edges,degree,
        phase_parent,body_support,height,mirror_pairs,gain=gain,
        maximum_height_fraction=maximum_height_fraction,longitudinal_parent=longitudinal_parent,
        events=events,amplitude_fraction=.45)
    mask=leaf_mask(np.asarray(phase_parent),np.asarray(longitudinal_parent),events)
    metadata.update(implementation='SPARSE_CARVED_ACANTHUS_RELIEF_V1',tier=int(tier),
        artwork_intent='A few thick, upward-unfurling stone leaves integrated into mature flowing ribbons; a strong sinuous midrib, broad quiet lobes, decisive bevels and deep curving channels. Subordinate veins belong to the primary lobe rails.',
        event_count=len(events),events=list(events),
        branch_profile='Replaced entirely by a C2 finite acanthus blade, beveled midrib,3–5curved broad side-lobes and narrow inner channels; no split Gaussian and no global axial periodic field.',
        endpoint_continuity='64*s^3*(1-s)^3 axial envelope and compact C2 margins; displacement and its first two longitudinal derivatives vanish at the selected leaf endpoints.',
        physical_scale='Fresh actual quad intrinsic parent-phase gradient; width=min(1.8/gradient,.08H); amplitude min(.45*gain*width,H*maximum_height_fraction)/(1+1.5*actual normal dispersion). Tier1 scalar crown is at most .30 of the primary before art weighting.',
        leaf_mask_quantiles=branch.flow._quantiles(mask),
        selected_parent_controls=int(np.count_nonzero(mask)),
        global_periodic_ornament=False,separate_leaf_mesh_added=False,
        imported_module_mutated=False,
        local_import_dependencies=[str(path) for path in helper_paths()],
        limitations='A source-specific integrated relief, not botanical reconstruction or a new topological branch. Existing malformed source ends outside the selected leaf support remain. Fresh local width budgets do not certify global self-intersection freedom. Aesthetic quality requires actual rendered review.')
    return delta,metadata
