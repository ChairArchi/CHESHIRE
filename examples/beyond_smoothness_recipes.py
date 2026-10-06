"""Hypothesis-led declarations, not a Cartesian parameter grid."""
from copy import deepcopy
from cheshire.sharp_subdivision import compile_schedule

def recipe(name,family,fixture,hypothesis,weights,u=None,locks=0,generations=5,modulation=None,finish=None,scope='ALL'):
    specifications={}
    for k,v in weights.items():
        specifications[k]=v if isinstance(v,dict) else dict(mode='DISCRETE',values=list(v) if isinstance(v,(list,tuple)) else [v]*generations)
    return dict(id=name,family=family,input=fixture,hypothesis=hypothesis,schedule=compile_schedule(specifications,generations),
        u_map=u or {},unknown_u=0.,locks=dict(mode='SOURCE_EDGE_ENDPOINT_CORNERS',iterations=locks),scope=scope,
        modulation=modulation,finish=finish or [],equation_mode='LITERAL_EQ10_EQ11_UNNORMALIZED',terminal_smoothing=False)

def controls():
    sparse={'(3,3)':1.,'(4,4)':0.}; bipolar={'(3,3)':1.,'(4,4)':-.25}
    definitions=[
        ('S0','Standard CC: retain smooth weak baseline',{},{} ,0),
        ('S0','Existing interpolation creates the comparison fold without new attraction',dict(w1=-.7,w2=-.5,w3=-.6,w4=.35),{},0),
        ('S1','Uniform u and positive edge attraction pull edge points toward source segments',dict(w7=.35),{'(3,3)':1.,'(4,4)':1.},0),
        ('S1','Negative u reverses uniform edge attraction',dict(w7=.35),{'(3,3)':-1.,'(4,4)':-1.},0),
        ('S1','Only valence-three vertices attract their adjacent face points',dict(w6=.3),sparse,0),
        ('S1','Valence-three face deflection reverses corner-local compression',dict(w6=-.3),sparse,0),
        ('S2','Mixed motif face attraction only',dict(w6=.25),bipolar,0),
        ('S2','Matched mixed motif edge attraction only',dict(w7=.25),bipolar,0),
        ('S2','Mixed motif face and edge terms together',dict(w6=.25,w7=.25),bipolar,0),
        ('S2','Edge points near interpolation cancellation may preserve straight ridges',dict(w7=.5),{'(3,3)':1.,'(4,4)':1.},0),
        ('S2','Past cancellation tests genuine folding and its stability boundary',dict(w7=.75),{'(3,3)':1.,'(4,4)':1.},0),
        ('S3','Edge contrast grows linearly through the finite horizon',dict(w7=dict(mode='EQ7_TREND',a=.12,b=.065,q=1)),bipolar,0),
        ('S3','Strong early edge attraction attenuates quadratically',dict(w7=dict(mode='EQ7_TREND',a=.5,b=-.025,q=2)),bipolar,0),
        ('S3','Edge grows quadratically while face attraction attenuates',dict(w7=dict(mode='EQ7_TREND',a=.08,b=.018,q=2),w6=dict(mode='EQ7_TREND',a=.2,b=-.03,q=1)),bipolar,0),
        ('S3','Discrete pulse separates early macro and later meso compression',dict(w6=[0,.28,.15,.04,0],w7=[.1,.35,.28,.1,.03]),bipolar,0),
        ('S4','Restrained old interpolation plus sparse face deflection',dict(w1=-.3,w2=-.25,w3=-.4,w4=.2,w6=-.12,w7=.2),sparse,0),
        ('S4','Expanded edge interpolation and motif displacement test panel angles',dict(w1=.35,w2=-.2,w6=.2,w7=.25),bipolar,0),
        ('S4','Fold-oriented old point classes with restrained motif offsets',dict(w1=-.8,w2=-.6,w3=-.7,w4=.4,w6=.08,w7=.14),bipolar,0),
        ('S5','One-iteration literal source-edge endpoint lock',dict(w7=.35),sparse,1),
        ('S5','Three-iteration literal source-edge endpoint lock',dict(w7=.35),sparse,3),
        ('S5','Six-iteration literal source-edge endpoint lock',dict(w7=.35),sparse,6),
        ('S6','Small normal depth on sparse edge repositioning',dict(w7=.3,wf=.015,we=-.005,wp=.005),sparse,0),
        ('S6','Small face depth with attenuated motif compression',dict(w6=.12,w7=.2,wf=[.02,.01,.005,0,0]),bipolar,0),
        ('S4','Deliberate near-collapse exposure: excessive opposite-class repositioning',dict(w6=1.2,w7=1.,w1=-.7,w2=-.6),{'(3,3)':1.,'(4,4)':-1.},0),
    ]
    result=[]
    for i,(family,hypothesis,weights,u,locks) in enumerate(definitions,1):
        for fixture in ('cube','column'):
            result.append(recipe(f'C{i:02d}_{fixture}',family,fixture,hypothesis,weights,u,locks))
    return result

def lock_sanity():
    return [recipe(f'LOCK_L{l}','LOCK_SANITY','cube','Literal fixed endpoint descendants compared at equal six-generation depth',{},locks=l,generations=6) for l in (0,1,3,6)]

def boundary_controls():
    """Five targeted followups to the observed smoothing of weak motif terms."""
    definitions=[
        ('S0','Strong existing interpolation control preserves source planes; no motif contribution',dict(w1=-1.,w2=-4.),{},0),
        ('S4','Reduce corner smoothing, then distinguish valence3 attraction from valence4 deflection',dict(w1=-.7,w2=-2.8,w6=.25,w7=.65),{'(3,3)':1.,'(4,4)':-.2},0),
        ('S5','Corner-preserving neighborhood plus face deflection and finite endpoint locks',dict(w1=-.7,w2=-3.4,w3=-.75,w4=.4,w6=-.12,w7=.25),{'(3,3)':1.,'(4,4)':-.2},3),
        ('S3','Less corner smoothing; quadratically rising edge term approaches folding boundary',dict(w1=-.6,w2=-2.5,w6=dict(mode='EQ7_TREND',a=.1,b=.025,q=1),w7=dict(mode='EQ7_TREND',a=.2,b=.025,q=2)),{'(3,3)':1.,'(4,4)':.15},0),
        ('S4','Expose the contact boundary with stronger face/edge compression on both point classes',dict(w1=-.4,w2=-2.5,w6=.4,w7=.75),{'(3,3)':1.,'(4,4)':.5},0)]
    return [recipe(f'C{i+25:02d}_{fixture}',family,fixture,hypothesis,weights,u,locks)
        for i,(family,hypothesis,weights,u,locks) in enumerate(definitions) for fixture in ('cube','column')]

def mechanism_controls():
    """Matched term ablations and finite trends after C26 showed real creases."""
    base=dict(w1=-.7,w2=-2.8); u={'(3,3)':1.,'(4,4)':-.2}
    data=[
        ('S0','Same strong interpolation without attraction isolates motif contribution',{},u,0),
        ('S2','Strong-neighborhood face term only',dict(w6=.25),u,0),
        ('S2','Strong-neighborhood edge term only',dict(w7=.65),u,0),
        ('S1','Same face/edge settings with sparse valence3 map',dict(w6=.25,w7=.65),{'(3,3)':1.},0),
        ('S1','Reverse both motif signs in the matched strong neighborhood',dict(w6=.25,w7=.65),{'(3,3)':-1.,'(4,4)':.2},0),
        ('S3','Quadratic attenuation preserves the early corner crease without continuous forcing',dict(w6=dict(mode='EQ7_TREND',a=.25,b=-.0125,q=2),w7=dict(mode='EQ7_TREND',a=.65,b=-.025,q=2)),u,0),
        ('S3','Discrete early fold followed by decreasing interpolation and weak late attraction',dict(w2=[-3.,-2.8,-2.4,-2.,-1.6],w6=[.3,.25,.12,.04,0],w7=[.6,.5,.25,.12,.04]),u,0),
        ('S5','Matched strong motif control with one sharp-stage lock',dict(w6=.25,w7=.65),u,1),
        ('S5','Matched strong motif control with three sharp-stage locks',dict(w6=.25,w7=.65),u,3),
        ('S5','Matched strong motif control with six sharp-stage locks',dict(w6=.25,w7=.65),u,6),
        ('S4','Alternate verified V/F/E face-stencil emphasis while corner smoothing stays low',dict(w3=[0,-.6,.2,-.3,0],w4=[0,.25,-.1,.15,0],w6=.15,w7=.4),u,0),
        ('S4','More face-center edge interpolation distinguishes corner preservation from edge placement',dict(w1=-.2,w6=.18,w7=.55),u,0),
        ('S6','Tiny normal extrusion gives depth to an already sharp motif substrate',dict(w6=.25,w7=.65,wf=.005,we=-.003,wp=.002),u,0)]
    return [recipe(f'C{i+30:02d}_column',family,'column',hypothesis,{**base,**weights},mapping,locks)
        for i,(family,hypothesis,weights,mapping,locks) in enumerate(data)]

def secondary(base,mode):
    """Eight finite, paired interpolation hypotheses; no new geometry operator."""
    pairs=[{'w1':[-1.,-.3]},{'w1':[-.3,-1.]},{'w2':[-3.4,-1.5]},{'w2':[-1.5,-3.4]},
           {'w3':[-.6,0.],'w4':[.4,0.]},{'w3':[0.,-.6],'w4':[0.,.4]},
           {'wf':[0.,.02]},{'wf':[.02,0.]}]
    out=[]
    for i,controls in enumerate(pairs,1):
        r=deepcopy(base); r['id']=('D' if mode=='SOURCE_GRAPH_DISTANCE' else 'P')+f'{i:02d}'
        r['family']=mode; r['hypothesis']=f'{mode}: min/max interpolation of {controls} on the fixed source cage / existing incident-normal proxy.'
        r['modulation']=dict(mode=mode,controls=controls); out.append(r)
    return out
