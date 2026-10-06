"""Independent audit of serialized constructor frames and routing evidence."""
from math import fsum,isclose,isfinite,sqrt
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read,write
from vocabulary_review import STUDY,cases,gz_read

def dot(a,b): return fsum(x*y for x,y in zip(a,b))

def inspect(case):
    events=gz_read(case/'terminal_lineage.json.gz')['events']; count=0; alignments=[]
    patches={}
    for e in events:
        if e['operator'] not in ('DirectionalExtrusion','Roof'): continue
        count+=1; frame=e['local_frame']; n,t,u=(frame[k] for k in ('N','T1','T2'))
        assert all(isfinite(x) for v in (n,t,u) for x in v)
        assert all(isclose(dot(v,v),1,abs_tol=2e-12) for v in (n,t,u))
        assert all(abs(dot(a,b))<2e-12 for a,b in ((n,t),(n,u),(t,u)))
        assert all(w>0 for w in e['source_C0_ancestry'].values()) and isclose(fsum(e['source_C0_ancestry'].values()),1,abs_tol=1e-9)
        if e['operator']=='DirectionalExtrusion':
            d=e['direction_details']; q=d['unit_direction']; ratio=d['normal_ratio']; tangent=d['tangent_component']
            assert isclose(dot(q,q),1,abs_tol=2e-12)
            expected=[ratio*n[a]+tangent*t[a] for a in range(3)]
            assert all(isclose(x,y,abs_tol=2e-12) for x,y in zip(q,expected))
            assert [c['role'] for c in e['children']]==['DIRECTIONAL_EXTRUSION_SIDE']*len(frame['ordered_corner_ids'])+['DIRECTIONAL_EXTRUSION_CAP']
            assert all(isclose(d['normal_tangent_offset'][a],e['height_world']*q[a],abs_tol=1e-10) for a in range(3))
        else:
            assert len(frame['ordered_corner_ids'])==4
            assert [c['role'] for c in e['children']]==['RIDGE_END','RIDGE_SIDE','RIDGE_END','RIDGE_SIDE']
            # Constructor normal is recomputed after an orientation-preserving
            # cyclic quad rotation. A warped quad can therefore differ from N.
            assert isclose(dot(e['direction_details']['constructor_normal'],e['direction_details']['constructor_normal']),1,abs_tol=2e-12)
            d=e['direction_details']
            if 'actual_ridge_axis' in d:
                assert isclose(dot(d['actual_ridge_axis'],d['actual_ridge_axis']),1,abs_tol=2e-12)
                assert isclose(abs(dot(d['actual_ridge_axis'],t)),d['ridge_alignment_abs_dot_T1'],abs_tol=2e-12)
                alignments.append(d['ridge_alignment_abs_dot_T1'])
        p=e['routing_patch']
        if p:
            key=e['stage']+':'+p['id']
            if key in patches: assert patches[key]==p
            patches[key]=p
    result=dict(id=case.parent.name,new_event_count=count,unit_orthogonal_frames=True,direction_formula=True,
        exact_constructor_roles=True,positive_source_mass=True,shared_patch_metadata_consistent=True,
        patch_count=len(patches),actual_ridge_axis_records=len(alignments),
        ridge_alignment_abs_dot_T1_mean=fsum(alignments)/len(alignments) if alignments else None,
        ridge_alignment_abs_dot_T1_min=min(alignments,default=None),
        scope='Serialized constructive evidence, not a geometric intersection certificate or visual assembly score. Earlier runs without actual ridge-axis records remain unavailable, not inferred.')
    write(case/'direction_verification.json',result)
    return result

if __name__=='__main__':
    phases=sys.argv[1:] or ['A','B','C','F','R','HERO','REPLAY']; rows=[]
    for phase in phases:
        for case in cases(phase):
            if (case/'terminal_lineage.json.gz').exists(): rows.append(dict(phase=phase,**inspect(case)))
    write(STUDY/'direction_verification.json',rows); print('verified',len(rows),'actual cases; events',sum(r['new_event_count'] for r in rows))
