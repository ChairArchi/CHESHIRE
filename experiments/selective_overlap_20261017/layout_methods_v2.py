"""One stronger parameter-only major-fold overlap proposal on measured source lobes."""
from __future__ import annotations
import copy
import numpy as np
from scipy.signal import find_peaks
from layout_methods import measure_sections,compare_sections

def guards_at_same_material_scale(profile,prominence=.15,minimum_separation=4/48):
    p=np.asarray(profile);dt=float(np.median(np.diff(p[:,0])))
    ix,meta=find_peaks(-p[:,1],prominence=prominence,distance=max(1,int(round(minimum_separation/dt))))
    result=[]
    for i,pr in zip(ix,meta["prominences"]):
        if not .18<p[i,0]<.86:continue
        lo=hi=int(i);limit=p[i,1]+.15*pr
        while lo>0 and p[lo-1,1]<=limit:lo-=1
        while hi+1<len(p) and p[hi+1,1]<=limit:hi+=1
        result.append(dict(index=int(i),t=float(p[i,0]),radius=float(p[i,1]),prominence=float(pr),
                           interval=[float(p[lo,0]-.5*dt),float(p[hi,0]+.5*dt)]))
    return result

def append_six_major_lobe_events(original,guards,warp):
    intervals=[];left=float(warp(.15))
    for g in guards:
        lo,hi=[float(warp(t)) for t in g["interval"]]
        if lo>left:intervals.append((left,lo))
        left=max(left,hi)
    if left<float(warp(.96)):intervals.append((left,float(warp(.96))))
    lobes=sorted(sorted(intervals,key=lambda p:p[1]-p[0],reverse=True)[:3])
    if len(lobes)!=3:raise ValueError("Three measured lobes are required.")
    events=copy.deepcopy(original);records=[]
    for j,(lo,hi) in enumerate(lobes):
        span=min(.03,(hi-lo-.058)/4.2)
        if span<=0:raise ValueError("No compact support fits measured lobe.")
        a=lo+2.2*span+.004;b=hi-.05-2*span-.004
        for k in (0,1):
            height=a+(b-a)*(.30 if k==0 else .70)
            template=k;event=copy.deepcopy(original[1][template])
            event.update(id="SELECTED_LOBE_%d_MAJOR_%d"%(j+1,k+1),height=float(height),span=float(span),
                         direction=(.39269908169872414 if k==0 else .7853981633974483),
                         overlap_width=(.32 if k==0 else .36),sweep=(.18 if k==0 else -.20))
            events[1].append(event)
            support=[float(height-2.2*span),float(height+.05+2*span)]
            separated=all(support[1]<=float(warp(g["interval"][0])) or support[0]>=float(warp(g["interval"][1])) for g in guards)
            if not separated:raise ValueError("Extra support crosses a measured waist core.")
            records.append(dict(lobe=j+1,template_index=template,lobe_warped_interval=[lo,hi],support_warped_interval=support,
                                conservative_support_outside_guards=separated,
                                span_below_preferred_point02=bool(span<.02),
                                axial_samples_across_full_support_at193=float(4.2*span*192)))
    return events,dict(strategy="All original events retained; six original major templates appended only inside three measured lobe intervals",
                       placements=records,original_primary_two_retained=True,original_ancillary_three_retained=True,
                       primary_event_count=len(events[1]),total_event_count=sum(map(len,events.values())),
                       crown_scope_material_t=.96,waist_geometry_projected_or_masked=False)

