"""Subordinate volumetric field response in measured native parent frames.

The actual incoming sheet is retained as the carrier. Measured ownership and
physical width/depth control each response. No ruled-sheet replacement,
additional normal profile, manual patch, or subdivision is performed here.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d


def unit(a):
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-30)


def smooth(x):
    x=np.clip(x,0.,1.)
    return x*x*x*(10.-15.*x+6.*x*x)


def frames(parent):
    p=np.asarray(parent['parameter'],float)
    curve=gaussian_filter1d(parent['centre_xyz'],3.,axis=0,mode='nearest')
    t=unit(np.gradient(curve,p,axis=0))
    b=gaussian_filter1d(parent['across'],3.,axis=0,mode='nearest')
    b=unit(b-t*np.einsum('ij,ij->i',b,t)[:,None])
    n=unit(np.cross(t,b))
    if np.median(np.einsum('ij,ij->i',n,parent['normal']))<0.:
        t=-t;n=-n
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))]
    if arc[-1]<=1e-10:raise ValueError('No positive parent flow arc.')
    return curve,t,b,n,arc


def interp_vector(q,p,a):
    return np.column_stack([np.interp(q,p,a[:,k]) for k in range(3)])


def cross_fraction(q,cross,parent):
    p=parent['parameter'];grid=parent['formation_shoulder_cross'];arc=parent['formation_shoulder_arc']
    low=np.clip(np.searchsorted(p,q,side='right')-1,0,len(p)-2);high=low+1
    alpha=(q-p[low])/(p[high]-p[low]);value=np.zeros(len(q))
    for row in range(len(p)):
        for index,weight in ((low,1.-alpha),(high,alpha)):
            chosen=index==row
            if chosen.any():value[chosen]+=weight[chosen]*np.interp(cross[chosen],grid[row],arc[row])
    return value/np.maximum(np.interp(q,p,arc[:,-1]),1e-30)


def controller_height(q,cross,parent,curve,normal):
    # Pool only the measured controller lookup. Actual output XYZ retains all
    # original residuals, rather than projecting the sheet to this guide.
    p=parent['parameter'];grid=parent['formation_shoulder_cross']
    height=np.einsum('nkj,nj->nk',parent['controller_shoulder_xyz']-curve[:,None,:],normal)
    height=gaussian_filter1d(height,3.,axis=1,mode='nearest')
    height=gaussian_filter1d(height,1.,axis=0,mode='nearest')
    low=np.clip(np.searchsorted(p,q,side='right')-1,0,len(p)-2);high=low+1
    alpha=(q-p[low])/(p[high]-p[low]);value=np.zeros(len(q))
    for row in range(len(p)):
        for index,weight in ((low,1.-alpha),(high,alpha)):
            chosen=index==row
            if chosen.any():value[chosen]+=weight[chosen]*np.interp(cross[chosen],grid[row],height[row])
    return value


def form(xyz,chart,parents,events,free,pairs,family_ids,bulb,ownership,*,block=1024):
    theta=np.arctan2(np.abs(chart[:,2]),np.abs(chart[:,1]));height=chart[:,0]
    canonical=(chart[:,1]>=-1e-12)&(chart[:,2]>=-1e-12)&free
    accum=np.zeros_like(xyz);records=[];evidence={};canon_moved=[]
    for parent in parents:
        family=int(parent['family_id'])
        if family not in family_ids:continue
        if str(parent['axis'])!='theta':raise ValueError('Measured theta-flow parent required.')
        p=np.asarray(parent['parameter']);lo=parent['formation_shoulder_cross'][:,0];hi=parent['formation_shoulder_cross'][:,-1]
        ids=np.flatnonzero(canonical&(theta>p[0])&(theta<p[-1])&
            (height>np.interp(theta,p,lo))&(height<np.interp(theta,p,hi)))
        fraction=cross_fraction(theta[ids],height[ids],parent)
        keep=(fraction>.25)&(fraction<.75);ids=ids[keep];fraction=fraction[keep]
        if not len(ids):continue
        curve,t,b,n,flow=frames(parent)
        parameter=theta[ids]
        tangent=unit(interp_vector(parameter,p,t));across=interp_vector(parameter,p,b)
        across=unit(across-tangent*np.einsum('ij,ij->i',across,tangent)[:,None])
        normal=unit(np.cross(tangent,across))
        centre=interp_vector(parameter,p,curve)
        width=np.interp(parameter,p,parent['parent_physical_width'])
        depth=np.interp(parameter,p,parent['parent_observed_chord_depth'])
        if np.any(width<=0.) or np.any(depth<0.):raise ValueError('Invalid measured physical parent scale.')
        nscale=np.minimum(np.maximum(.65*depth,.02*width),.20*width)
        physical_cap=np.minimum(.28*depth,.06*width)
        s=np.interp(parameter,p,flow)/flow[-1];u=(fraction-.25)/.50
        weight=smooth(s/.12)*smooth((1.-s)/.12)*smooth(u/.12)*smooth((1.-u)/.12)
        partitions=ownership.partition_weights(parameter,height[ids],events)
        weight*=partitions[family]
        measured_height=controller_height(parameter,height[ids],parent,curve,n)
        local=np.column_stack(((s-.5)*.8,(u-.5)*2.2,
            .65+measured_height/np.maximum(nscale,1e-12)))
        move=np.zeros((len(ids),3));inside=0;maximum_normalized=0.;first_meta=None
        print('PARENT_FIELD family',family,'canonical queries',len(ids),flush=True)
        for start in range(0,len(ids),block):
            end=min(start+block,len(ids));d,meta=bulb.respond(local[start:end])
            if first_meta is None:first_meta=meta
            inside+=int(meta['finite_inside_queries'])
            maximum_normalized=max(maximum_normalized,float(np.linalg.norm(d,axis=1).max(initial=0.)))
            move[start:end]=d[:,1,None]*(.25*width[start:end,None])*across[start:end]+d[:,2,None]*nscale[start:end,None]*normal[start:end]
            if start%(20*block)==0:print('PARENT_FIELD progress',family,end,'/',len(ids),flush=True)
        requested=np.linalg.norm(move,axis=1)
        ratio=requested/np.maximum(physical_cap,1e-30)
        move/=np.sqrt(1.+ratio*ratio)[:,None]
        move*=weight[:,None]
        tangent_error=float(np.max(np.abs(np.einsum('ij,ij->i',move,tangent)),initial=0.))
        move[np.abs(chart[ids,1])<1e-12,0]=0.
        move[np.abs(chart[ids,2])<1e-12,1]=0.
        accum[ids]+=move;canon_moved.append(ids)
        key='parent_'+str(family)+'_'
        evidence.update({key+'ids':ids,key+'local_query':local,key+'physical_cap':physical_cap,
            key+'ancestry_weight':partitions[family],key+'support_weight':weight,
            key+'tangent':tangent,key+'canonical_delta':move,key+'cross_arc_fraction':fraction})
        records.append(dict(family_id=family,bank_id=events[family]['bank_id'],canonical_queries=len(ids),
            query_N_quantiles=np.quantile(local[:,2],[0,.1,.5,.9,1]).tolist(),
            query_B_quantiles=np.quantile(local[:,1],[0,.1,.5,.9,1]).tolist(),
            nonzero_canonical_queries=int((np.linalg.norm(move,axis=1)>1e-12).sum()),
            finite_inside_queries=inside,finite_inside_fraction=inside/len(ids),
            maximum_normalized_response=maximum_normalized,maximum_physical_delta=float(np.linalg.norm(move,axis=1).max(initial=0.)),
            local_T_delta_error=tangent_error,field_algorithm=first_meta,
            carrier='Exact actual incoming coordinates; no carrier replacement or XYZ filtering.',
            support='Central 25–75% of actual measured shoulder arc; smooth boundary/endpoint support times original-family request partition.',
            field_coordinates='T=.8*(physical flow arc fraction-.5); B=2.2*(child arc fraction-.5); N=.65+pooled measured source normal-height lookup / measured depth scale. Controller lookup pooled sigma3 across and sigma1 along; actual source XYZ is never filtered.',
            physical_budget='Smooth norm bound min(.28*actual parent depth,.06*actual shoulder width). B scale=.25*shoulder width; N scale=clip(.65*depth,.02*width,.20*width).'))
    if not canon_moved:raise ValueError('No selected actual parent SOURCE queries.')
    canonical_ids=np.unique(np.concatenate(canon_moved));base_delta=accum[canonical_ids].copy()
    full=np.zeros_like(xyz)
    for mx,my in ((False,False),(True,False),(False,True),(True,True)):
        target=canonical_ids.copy();d=base_delta.copy()
        if mx:target=pairs['X'][target];d[:,0]*=-1.
        if my:target=pairs['Y'][target];d[:,1]*=-1.
        full[target]=d
    if np.any(np.linalg.norm(full[~free],axis=1)>1e-12):raise ValueError('Attached root boundary moved.')
    ids=np.flatnonzero(np.linalg.norm(full,axis=1)>1e-12);delta=full[ids]
    if not len(ids) or not np.isfinite(delta).all():raise ValueError('No finite nonzero actual response.')
    out=xyz+full
    symmetry=0.
    for axis,key in enumerate(('X','Y')):
        reflected=out[pairs[key][ids]].copy();reflected[:,axis]*=-1.
        symmetry=max(symmetry,float(np.max(np.abs(out[ids]-reflected),initial=0.)))
    if symmetry>2e-12:raise ValueError('Lost actual XY symmetry.')
    return ids,delta,dict(algorithm='PARENT_OWNED_FINITE_3D_MANDELBULB_RESPONSE_V1',parents=records,
        moved_controls=len(ids),maximum_delta=float(np.linalg.norm(delta,axis=1).max()),
        XY_symmetry_error=symmetry,generation=7,added_subdivision=0,source_outside_support_exact=True,
        actual_parent_carrier_retained=True,global_self_intersection_checked=False,
        aesthetic_success='Pending matched actual native renders; not a mathematical quality claim.'),evidence


def helper_paths():
    return [Path(__file__).resolve()]
