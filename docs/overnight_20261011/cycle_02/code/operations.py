"""Exact finite modelling functions from the preserved KNOT R02 recipe.
Requires local TORQUE geometry, material chart and mirror pairs; no standalone engine.
"""
import numpy as np

def g(t,c,w):return np.exp(-((t-c)/w)**2)

def smooth(a,b,t):v=np.clip((t-a)/(b-a),0,1);return v*v*(3-2*v)

def edit(v,chart,key,rev):
    q=np.round(chart[:,0],12);unique,index=np.unique(q,return_inverse=True)
    counts=np.bincount(index)
    # Pivots from the preserved actual material rings; the neighbouring rings
    # remain connected by original polygons. These are not separate modules.
    centers=np.column_stack([np.bincount(index,weights=v[:,k])/counts for k in range(3)])[index]
    w=v.copy();x,y,z=v.T
    support=1-smooth(.245,.315,q)
    if key=='D_SPLAY':
        width=1-.16*g(q,.19,.075)*support
        outward=.95*g(q,.20,.115)*support
        arch_x=1+.20*smooth(.19,.35,q)
        turn=-.48*g(q,.34,.075)+.25*g(q,.49,.06)
        yz_scale=1-.40*g(q,.50,.11)
        lift=.65*g(q,.33,.065)-1.65*g(q,.50,.095)
        depth=.50*g(q,.35,.08)-.20*g(q,.50,.08)
    elif key=='D_CROOK':
        width=1-.12*g(q,.20,.08)*support
        outward=.70*g(q,.20,.115)*support
        arch_x=1+.27*g(q,.325,.095)
        turn=-.85*g(q,.33,.065)+.80*g(q,.445,.065)
        yz_scale=1+.14*g(q,.32,.055)-.54*g(q,.50,.09)
        lift=.90*g(q,.335,.060)-.30*g(q,.44,.07)
        depth=.65*g(q,.33,.06)-.45*g(q,.435,.06)
    else:
        width=1-.10*g(q,.20,.085)*support
        outward=.65*g(q,.20,.115)*support
        arch_x=1+.12*g(q,.32,.10)
        turn=.95*g(q,.405,.09)-.40*g(q,.50,.045)
        yz_scale=1-.50*g(q,.50,.105)
        lift=.50*g(q,.37,.085)-.70*g(q,.50,.075)
        depth=-.60*g(q,.365,.07)+1.15*g(q,.485,.08)
        if rev==2:
            # After viewing R01: let the support expansion move farther out,
            # extend the haunch into a rolled arm, and give the middle knot
            # a fuller reverse turn instead of a shallow hanging saddle.
            width=1-.16*g(q,.20,.085)*support
            outward=1.10*g(q,.20,.115)*support
            arch_x=1+.22*g(q,.32,.10)
            turn=1.18*g(q,.385,.075)-.62*g(q,.50,.055)
            yz_scale=1+.13*g(q,.32,.05)-.38*g(q,.50,.10)
            lift=.65*g(q,.36,.075)-.45*g(q,.50,.075)
            depth=-.70*g(q,.365,.07)+.70*g(q,.485,.08)
    w[:,0]=(centers[:,0]+(x-centers[:,0])*width-outward)*arch_x
    # The existing finite return in YZ is applied to the complete section,
    # including its core and flutes, around that section's actual centroid.
    dy=(y-centers[:,1])*yz_scale;dz=(z-centers[:,2])*yz_scale
    upper=smooth(.245,.31,q)
    angle=turn*upper
    w[:,1]=centers[:,1]+dy*np.cos(angle)-dz*np.sin(angle)+depth*upper
    w[:,2]=centers[:,2]+dy*np.sin(angle)+dz*np.cos(angle)+lift*upper
    return w,dict(material_arc=q,section_return_angle=angle,section_yz_scale=yz_scale,
                  support_width_scale=width,support_outward_offset=outward,arch_span_scale=arch_x,
                  arch_lift=lift*upper,arch_depth_offset=depth*upper)
