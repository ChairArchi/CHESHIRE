"""Curate a sparse foliate composition from measured NESTED02 ribbon lobes.

Selection never edits measured event spans or centreline samples. Six broad
leaves are preferred across the canonical phase families, with a close-view
S-ribbon anchor, separated lower/upper accents and quiet intervening panels.
This is explicit art direction, not an aesthetic score or an automated proof
of beauty. Only Python standard-library helpers are imported.
"""
from copy import deepcopy
import math


def select_events(events, detection_metadata=None):
    """Return ``(selected_events, JSON_safe_selection_info)``.

    Each selected copy gains ``source_event_index``, ``art_role``,
    ``art_weight`` and ``leaf_side_count``. Existing geometry measurements,
    strength, t_start/t_end and centre_t/centre_phase_offset remain unchanged.
    ``leaf_side_count`` is the number of primary side-vein attachment stations
    for the relief grammar; it lies between three and five.
    """
    if not isinstance(events, (list, tuple)):
        raise ValueError('Concrete measured event list required.')
    rows=[]
    for index,event in enumerate(events):
        if not isinstance(event,dict):
            raise ValueError('Each measured event must be a dictionary.')
        a,b,p=(float(event[key]) for key in ('t_start','t_end','t_peak'))
        prominence=float(event.get('radial_prominence',0.))
        curvature=abs(float(event.get('radial_second_derivative_min',0.)))
        if (not all(math.isfinite(v) for v in (a,b,p,prominence,curvature)) or
                not a<p<b or prominence<0):
            raise ValueError('Finite ordered measured lobe and nonnegative prominence required.')
        if b-a < .11 or prominence <= 0:
            continue
        rows.append(dict(index=index,event=event,a=a,b=b,p=p,span=b-a,
                         prominence=prominence,curvature=curvature,
                         cycle=int(event['parent_cycle'])))
    if not rows:
        return [],dict(implementation='SPARSE_MEASURED_FOLIATE_ART_SELECTION_V1',
                       selected=0,reason='No broad measured parent lobe; no tiny ornament forced.',
                       source_event_count=len(events),source_events_modified=False)
    maximum_curvature=max(row['curvature'] for row in rows) or 1.
    for row in rows:
        # Span and actual radial prominence dominate. Curvature has only a
        # modest tie-breaking role so sharp, short noise cannot become a hero.
        turn=.8+.2*math.sqrt(min(1.,row['curvature']/maximum_curvature))
        row['rank']=row['span']*row['prominence']*turn
    chosen=[]
    used_cycles=set()

    def choose(pool,role,weight,*,rank=None):
        pool=[r for r in pool if r['index'] not in {c['index'] for c in chosen}]
        if not pool:return None
        selected=max(pool,key=rank or (lambda r:(r['rank'],-r['index'])))
        record=dict(selected,role=role,weight=weight)
        chosen.append(record)
        used_cycles.add(selected['cycle'])
        return selected

    # Original source projection through the actual close camera finds the
    # central visible surface mostly in phase families2/3/4 around t=.67.
    # Family3's large measured S lobe extends into t=.60-.67; retain the full
    # lobe rather than manufacturing a tiny close-camera patch.
    hero=[r for r in rows if r['cycle']==3 and r['a']<=.64<=r['b'] and r['span']>=.13]
    if not hero:
        hero=[r for r in rows if r['a']<.72 and r['b']>.60 and r['span']>=.13]
    anchor=choose(hero or rows,'CLOSE_S_RIBBON',1.10)
    choose([r for r in rows if r['cycle'] not in used_cycles and .20<=r['p']<=.38],
           'LOWER_FOCAL_LEAF',1.00)
    choose([r for r in rows if r['cycle'] not in used_cycles and .78<=r['p']<=.88],
           'UPPER_SECONDARY_LEAF',.86)
    # One neighboring upper leaf supports the close-view anchor, while other
    # nearby families retain quiet fields. Prefer its canonical lower neighbor.
    if anchor is not None:
        neighbor=[r for r in rows if r['cycle']==anchor['cycle']-1 and
                  r['cycle'] not in used_cycles and .60<=r['p']<=.75]
        choose(neighbor,'CLOSE_UPPER_COMPANION',.90)
        # The broad S anchor ends near the projected view centre. A second
        # measured lobe on its other side crosses t=.68, so the image centre
        # receives a living midrib instead of only the first leaf's faded tip.
        centre=[r for r in rows if r['cycle']==anchor['cycle']+1 and
                r['cycle'] not in used_cycles and r['a']<=.68<=r['b'] and
                .65<=r['p']<=.76 and r['span']>=.13]
        choose(centre,'CLOSE_CENTRAL_CARVING',.98)

    def quiet_rank(row):
        penalty=1.
        for other in chosen:
            # Adjacent phase families carrying the same longitudinal carpet
            # are discouraged; gaps between separate foliate accents remain.
            if abs(row['cycle']-other['cycle'])==1:
                overlap=max(0.,min(row['b'],other['b'])-max(row['a'],other['a']))
                fraction=overlap/min(row['span'],other['span'])
                penalty*=1.-.82*fraction
        middle=.92 if .45<=row['p']<=.75 else 1.
        return (row['rank']*penalty*middle,-row['index'])

    target=min(6,len({row['cycle'] for row in rows}))
    while len(chosen)<target:
        pool=[r for r in rows if r['cycle'] not in used_cycles]
        if not pool:break
        choose(pool,'SPACED_OUTER_ACCENT',.76,rank=quiet_rank)

    chosen.sort(key=lambda r:(r['cycle'],r['a'],r['index']))
    selected,preview=[],[]
    for row in chosen:
        event=deepcopy(row['event'])
        side_count=5 if row['span']>=.19 else 4 if row['span']>=.145 else 3
        event.update(source_event_index=int(row['index']),art_role=row['role'],
                     art_weight=float(row['weight']),leaf_side_count=side_count)
        selected.append(event)
        preview.append(dict(source_event_index=row['index'],parent_cycle=row['cycle'],
            t_start=row['a'],t_peak=row['p'],t_end=row['b'],art_role=row['role'],
            art_weight=row['weight'],leaf_side_count=side_count))
    info=dict(implementation='SPARSE_MEASURED_FOLIATE_ART_SELECTION_V1',
        source_event_count=len(events),broad_candidates=len(rows),selected=len(selected),
        selected_source_event_indices=[row['index'] for row in chosen],selected_preview=preview,
        minimum_measured_span=.11,maximum_selected_per_cycle=1,
        source_events_modified=False,measured_spans_and_centrelines_preserved=True,
        composition='A broad lower close-view S ribbon and a measured central carving that crosses t=.68, with one upper close companion, a strong lower leaf, a quieter upper leaf and a separated outer accent. Other adjacent phase families avoid covering the same longitudinal panels.',
        selection_basis='Measured lobe span and radial prominence, modest measured-curvature tie break, explicit art-directed focal domains and quiet spacing; no random placement or periodic axial seeding.',
        detection_implementation=(detection_metadata or {}).get('implementation'),
        limitation='Sparse compositional curation on this actual column. Selection scores do not certify beauty or geometric fit; final sculpture and actual renders decide the result.')
    return selected,info
