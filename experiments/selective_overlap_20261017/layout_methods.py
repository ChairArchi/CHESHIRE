"""Measured axial waist guards and parameter-only proposals for existing fold kernels."""
from __future__ import annotations
import copy
import numpy as np
from scipy.signal import find_peaks

def measure_sections(xyz,chart):
    x=np.asarray(xyz);c=np.asarray(chart);rows=[]
    for t in np.unique(c[:,0]):
        ids=np.flatnonzero((abs(c[:,0]-t)<1e-10)&(np.linalg.norm(c[:,1:],axis=1)>.99))
        if len(ids)<8:continue
        ids=ids[np.argsort(np.arctan2(c[ids,2],c[ids,1]))]
        p=x[ids,:2];area=.5*abs(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))
        radius=np.linalg.norm(p,axis=1)
        rows.append((t,np.sqrt(area/np.pi),radius.max(),area,np.median(x[ids,2])))
    return np.asarray(rows)

def waist_guards(profile,prominence=.15):
    p=np.asarray(profile);ix,meta=find_peaks(-p[:,1],prominence=prominence,distance=4)
    dt=float(np.median(np.diff(p[:,0])));guards=[]
    for i,pr in zip(ix,meta["prominences"]):
        if not .18<p[i,0]<.86:continue
        lo=hi=int(i);limit=p[i,1]+.15*pr
        while lo>0 and p[lo-1,1]<=limit:lo-=1
        while hi+1<len(p) and p[hi+1,1]<=limit:hi+=1
        guards.append(dict(index=int(i),t=float(p[i,0]),radius=float(p[i,1]),
                           prominence=float(pr),interval=[float(p[lo,0]-.5*dt),float(p[hi,0]+.5*dt)]))
    return guards

def compact_events(original,guards,warp,secondary_count):
    if secondary_count not in (4,6):raise ValueError("Bounded comparison uses four or six secondary events.")
    intervals=[];left=float(warp(.15))
    for g in guards:
        lo,hi=map(lambda v:float(warp(v)),g["interval"])
        if lo>left:intervals.append((left,lo))
        left=max(left,hi)
    if left<float(warp(.9)):intervals.append((left,float(warp(.9))))
    usable=sorted([v for v in intervals if v[1]-v[0]>.14],key=lambda v:v[1]-v[0],reverse=True)[:2]
    if len(usable)<2:raise ValueError("Two broad lobes with conservative support do not fit.")
    usable=sorted(usable)
    resolved={1:copy.deepcopy(original[1]),2:[],3:[]};records=[]
    each=secondary_count//2
    for gen in (2,3):
        for i in range(each):
            lo,hi=usable[i%2];span=min(.032,(hi-lo-.058)/4.2)
            if span<.018:raise ValueError("Insufficient physical source sampling for secondary support.")
            a=lo+2.2*span+.004;b=hi-.05-2*span-.004
            height=(a+b)/2+(i//2-.25)*.35*(b-a)
            template=i%len(original[gen]);event=copy.deepcopy(original[gen][template])
            lanes=(np.pi/8,3*np.pi/8,np.pi/4) if gen==2 else (np.pi/4,np.pi/8,.95)
            event.update(id="LOBED_G%d_%d"%(gen,i+1),height=float(height),span=float(span),
                         direction=float(lanes[i]),overlap_width=.40,sweep=(.14 if i%2==0 else -.16))
            resolved[gen].append(event)
            support=[float(height-2.2*span),float(height+.05+2*span)]
            records.append(dict(generation=gen,template_index=template,lobe_interval=[lo,hi],
                                support_interval=support,conservative_support_outside_waists=all(
                                support[1]<=float(warp(g["interval"][0])) or support[0]>=float(warp(g["interval"][1])) for g in guards)))
    return resolved,dict(strategy="Conservative full original support contained in selected broad lobes",placements=records)

def phase_events(original,guards,warp):
    resolved={1:copy.deepcopy(original[1]),2:[],3:[]};records=[]
    major_targets=[original[1][0]["height"]+.15*original[1][0]["span"],
                   float(warp(guards[len(guards)//2]["t"])),
                   original[1][1]["height"]+.15*original[1][1]["span"]]
    for gen,spans,lanes in ((2,(.045,.04,.05),(np.pi/8,np.pi/4,3*np.pi/8)),
                           (3,(.028,.03,.032),(3*np.pi/8,np.pi/8,np.pi/4))):
        for i,(target,span,direction) in enumerate(zip(major_targets,spans,lanes)):
            template=i%len(original[gen]);event=copy.deepcopy(original[gen][template])
            event.update(id="PHASE_G%d_%d"%(gen,i+1),height=float(target-.15*span),span=span,
                         direction=float(direction),overlap_width=.30,sweep=0.)
            resolved[gen].append(event)
            records.append(dict(generation=gen,template_index=template,
                                contraction_warped_t=float(target),selected_meridian=float(direction),
                                offset_rule="h = target - .15*span; local_h angular offset is zero at selected meridian"))
    return resolved,dict(strategy="Secondary contraction phase aligned with existing narrow sections",placements=records,
                         exact_guard_invariance_claimed=False)

def compare_sections(reference,candidate,guards):
    a=np.asarray(reference);b=np.asarray(candidate)
    if not np.array_equal(a[:,0],b[:,0]):raise ValueError("Matching material sections required.")
    rows=[]
    for g in guards:
        i=g["index"]
        mask=(a[:,0]>=g["interval"][0])&(a[:,0]<=g["interval"][1])
        rows.append(dict(t=g["t"],reference_radius=float(a[i,1]),candidate_radius=float(b[i,1]),
                         centre_radius_ratio=float(b[i,1]/a[i,1]),
                         maximum_guard_area_ratio=float(np.max(b[mask,3]/a[mask,3])),
                         maximum_guard_outer_radius_ratio=float(np.max(b[mask,2]/a[mask,2]))))
    return rows

