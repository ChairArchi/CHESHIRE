"""Reusable compatibility API for the exact original eight-event fold bank."""
from pathlib import Path
import importlib.util
import json

import numpy as np

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('original_exact_seed_bank',HERE/'seed_fold_bank.py')
bank=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bank)


def helper_paths():
    return [HERE/'seed_fold_bank.py',*bank.helper_paths()]


def load_events():
    """Return flat old-style event dictionaries and exact source metadata.

    The preserved JSON is checked against its construction sources. Original
    event keys retain their scaled source-coordinate meaning; event_height
    performs the exact current-material conversion when initializing rails.
    """
    path=HERE/'actual_seed_fold_events.json'
    data=json.loads(path.read_text(encoding='utf8'))
    for source,checksum in data['source_hashes'].items():
        if bank.sha(source)!=checksum:
            raise ValueError('Original fold bank source changed: '+source)
    events=[]
    for descriptor in data['events']:
        event=dict(descriptor['event'])
        event.update(bank_id=descriptor['bank_id'],coordinate=descriptor['coordinate'],
            amplitude_multiplier=descriptor['amplitude_multiplier'],
            actual_insertion_stage=descriptor['actual_insertion_stage'],
            legacy_recipe_tier=descriptor['legacy_recipe_tier'],descriptor=descriptor)
        events.append(event)
    metadata={key:value for key,value in data.items() if key!='events'}
    metadata.update(bank_file=str(path),bank_file_sha256=bank.sha(path),events=len(events),
        material_conversion='event_height solves exact forward source warp and height-dependent angular sweep. Source height/span values are never approximated by a fitted current span.')
    return events,metadata


def _descriptor(event):
    if 'descriptor' in event:return event['descriptor']
    if isinstance(event.get('event'),dict):return event
    return dict(event={key:event[key] for key in ('id','direction','height','span','expansion',
        'constriction','reexpansion','return_depth','overlap_width','sweep','mirror')},
        coordinate=event.get('coordinate','CURRENT_MATERIAL_T'),
        amplitude_multiplier=event.get('amplitude_multiplier',1.))


def event_height(theta,u,event):
    """Exact current material t at source profile level u for each theta.

    Every native-bank trajectory here is monotone in its material cross
    coordinate. Missing or multiple roots are rejected explicitly. This
    returns a trajectory seed, never a claim of a currently measured trough.
    """
    theta,u=np.broadcast_arrays(np.asarray(theta,dtype=float),np.asarray(u,dtype=float))
    descriptor=_descriptor(event)
    e=descriptor['event']
    bound=.05*1.4*abs(float(e['sweep']))*np.pi/.32/float(e['overlap_width'])
    if not(np.isfinite(theta).all() and np.isfinite(u).all() and np.isfinite(bound)):
        raise ValueError('Finite angular/profile samples and source sweep required.')
    if bound<1.:
        # d(local_height)/ds is bounded in absolute value by bound. Hence
        # source u increases strictly with s; the exact SPAN W also increases.
        # Vector bisection therefore solves the SAME implicit source curve,
        # without per-sample grids, inverse fitting or a local span estimate.
        lo=np.zeros(theta.shape,dtype=float)
        hi=np.ones(theta.shape,dtype=float)
        coordinate=lambda t:bank.event_coordinates(descriptor,t,theta)[1][0][0]
        first,last=coordinate(lo)-u,coordinate(hi)-u
        if np.any(first>1e-12) or np.any(last< -1e-12):
            raise ValueError('Source profile lies outside exact current material domain: '+str(event.get('bank_id',event.get('id'))))
        for _ in range(48):
            mid=(lo+hi)/2.
            below=coordinate(mid)<u
            lo=np.where(below,mid,lo)
            hi=np.where(below,hi,mid)
        result=(lo+hi)/2.
        result=np.where(abs(first)<=1e-13,0.,result)
        result=np.where(abs(last)<=1e-13,1.,result)
        return result
    # A future bank outside the proven monotone domain keeps the original
    # all-roots search and explicitly rejects missing/ambiguous roots.
    result=np.empty(theta.size,dtype=float)
    for index,(angle,level) in enumerate(zip(theta.ravel(),u.ravel())):
        roots=bank.material_roots(descriptor,[float(angle)],float(level))[0]
        if len(roots)!=1:
            raise ValueError('Source profile has '+str(len(roots))+' exact current-material roots: '+str(event.get('bank_id',event.get('id'))))
        result[index]=roots[0]
    return result.reshape(theta.shape)


def event_wave(theta,current_t,event):
    """Actual source angular/terminal support, including bridge multiplier."""
    descriptor=_descriptor(event)
    s,coordinates=bank.event_coordinates(descriptor,current_t,theta)
    wave=sum(item[1] for item in coordinates)
    return wave*bank.legacy.window(s-.5,.40,.49)*descriptor['amplitude_multiplier']


def event_u(theta,current_t,event):
    """Source-profile coordinate on the primary canonical angular centre."""
    return bank.event_coordinates(_descriptor(event),current_t,theta)[1][0][0]
