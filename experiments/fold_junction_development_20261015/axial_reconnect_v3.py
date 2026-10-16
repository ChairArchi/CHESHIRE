"""Coherent transverse axial redistribution, followed by monotone projection.

This diffuses only a new Z displacement on actual equal-material-height mesh
edges. The source XYZ and radial envelope are never averaged. Positive-slope
projection follows every diffusion pass so lateral organization cannot simply
restore the original folded-over cup return.
"""
from pathlib import Path
import importlib.util

import numpy as np

_spec = importlib.util.spec_from_file_location('axial_v2_preserved_v1',
    Path(__file__).with_name('axial_reconnect.py'))
_v1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v1)


def _source_runs(chart, allowed, minimum_radius):
    key = np.rint(chart[:,1:]*1e10).astype(np.int64)
    order = np.lexsort((chart[:,0],key[:,1],key[:,0]))
    bounds = np.r_[0, np.flatnonzero(np.any(key[order][1:] != key[order][:-1],axis=1))+1, len(chart)]
    result=[]
    for a,b in zip(bounds[:-1],bounds[1:]):
        v=order[a:b]
        if len(v)<7 or np.max(np.linalg.norm(chart[v,1:],axis=1)) <= minimum_radius:
            continue
        t=chart[v,0]
        dup=np.r_[False,np.diff(t)<=1e-10] | np.r_[np.diff(t)<=1e-10,False]
        usable=allowed[v]&~dup
        breaks=np.flatnonzero(np.diff(np.r_[False,usable,False]))
        for first,last in zip(breaks[::2],breaks[1::2]):
            if last-first>=7:
                result.append(v[first:last])
    return result


def _project(z, d, t, runs, height, floor_fraction):
    result=d.copy()
    skipped=0
    for run in runs:
        # Retain the original first tangent if it already points upward.
        # An originally inverted boundary tangent cannot be both retained
        # and unfolded, so that side pins only the exact SOURCE endpoint.
        left_pin=2 if (z[run[1]]-z[run[0]])/(t[run[1]]-t[run[0]])>0 else 1
        right_pin=2 if (z[run[-1]]-z[run[-2]])/(t[run[-1]]-t[run[-2]])>0 else 1
        v=run[left_pin-1:len(run)-right_pin+1]
        local_t, original=t[v], z[v]
        secant=(original[-1]-original[0])/(local_t[-1]-local_t[0])
        if secant <= .02*height:
            skipped+=1
            continue
        floor=min(floor_fraction*height,.65*secant)
        baseline=floor*(local_t-local_t[0])
        lower,upper=original[0],original[-1]-baseline[-1]
        shifted=original+result[v]-baseline
        monotone=np.r_[lower,np.clip(_v1._pava(shifted[1:-1]),lower,upper),upper]
        result[v]=baseline+monotone-original
        result[run[:left_pin]]=0.
        result[run[-right_pin:]]=0.
    return result,skipped


def _roughness(d,edges):
    if not len(edges):return dict(edges=0)
    difference=abs(d[edges[:,1]]-d[edges[:,0]])
    return dict(edges=int(len(edges)),mean_abs=float(difference.mean()),
                rms=float(np.sqrt(np.mean(difference*difference))),
                quantiles=np.quantile(difference,[0,.5,.9,.99,1]).tolist())


def build(xyz, quads, chart, body_face_mask, vertex_pairs, *, strength=1.,
          interior=(.12,.90), minimum_chart_radius=.97,
          floor_height_fraction=.30, trigger_height_fraction=.12,
          interval_padding=.032, monotone_smoothing_sigma=2.,
          transverse_passes=8, transverse_strength=.36,
          projection_floor_height_fraction=.12):
    """Return ``(Z-only displacement, JSON-safe stats)`` on the actual G4 cage.

    The full-strength v1 reconnection supplies a localized target. Eight low
    strength passes communicate that displacement across existing SOURCE
    circumferential edges. Each pass combines 12% fidelity to the target,
    transverse averaging, and positive-slope meridian projection. Exact SOURCE
    borders, valid two-row endpoint tangents and terminal exclusions stay fixed.
    Partial ``strength`` is applied at the end and may retain axial inversions.
    """
    if not 0 <= strength <= 1 or not 0 <= transverse_strength <= 1 or transverse_passes<0:
        raise ValueError('Strengths in [0,1] and nonnegative pass count required.')
    xyz,quads,chart=map(np.asarray,(xyz,quads,chart))
    body=np.asarray(body_face_mask,dtype=bool)
    initial,meta=_v1.build(xyz,quads,chart,body,vertex_pairs,strength=1.,
        interior=interior,minimum_chart_radius=minimum_chart_radius,
        floor_height_fraction=floor_height_fraction,trigger_height_fraction=trigger_height_fraction,
        interval_padding=interval_padding,monotone_smoothing_sigma=monotone_smoothing_sigma)
    nv=len(xyz)
    height=float(np.ptp(xyz[:,2]))
    degree=np.bincount(quads.ravel(),minlength=nv)
    owned=np.bincount(quads[~body].ravel(),minlength=nv)
    allowed=(degree>0)&(owned==0)&(np.linalg.norm(chart[:,1:],axis=1)>minimum_chart_radius)
    allowed&=(chart[:,0]>=interior[0])&(chart[:,0]<=interior[1])
    px=np.asarray(vertex_pairs['X'] if 'X' in vertex_pairs else vertex_pairs['mirror_x_vertex_pairs'])
    py=np.asarray(vertex_pairs['Y'] if 'Y' in vertex_pairs else vertex_pairs['mirror_y_vertex_pairs'])
    allowed&=allowed[px]&allowed[py]&allowed[px[py]]
    runs=_source_runs(chart,allowed,minimum_chart_radius)
    for run in runs:
        t=chart[run,0]
        z=xyz[run,2]
        left_pin=2 if (z[1]-z[0])/(t[1]-t[0])>0 else 1
        right_pin=2 if (z[-1]-z[-2])/(t[-1]-t[-2])>0 else 1
        allowed[run[:left_pin]]=False
        allowed[run[-right_pin:]]=False
    edge=np.concatenate([quads[:,[0,1]],quads[:,[1,2]],quads[:,[2,3]],quads[:,[3,0]]])
    edge.sort(axis=1)
    edge=np.unique(edge,axis=0)
    same_t=abs(chart[edge[:,1],0]-chart[edge[:,0],0])<1e-10
    cross_length=np.linalg.norm(chart[edge[:,1],1:]-chart[edge[:,0],1:],axis=1)
    cross=same_t&(cross_length>1e-10)&(cross_length<.1)
    # Keep fixed source boundary samples as zero-valued neighbors; they taper
    # the displacement laterally without moving attached root interfaces.
    source=(degree>0)&(owned==0)
    cross&=source[edge[:,0]]&source[edge[:,1]]
    edges=edge[cross]
    a,b=edges[:,0],edges[:,1]
    transverse_degree=np.bincount(edges.ravel(),minlength=nv)
    target=initial[:,2].copy()
    d=target.copy()
    before=_roughness(d,edges)
    skipped=0
    ids=np.arange(nv)
    rep=np.minimum(np.minimum(ids,px),np.minimum(py,px[py]))
    for _ in range(int(transverse_passes)):
        total=np.bincount(a,weights=d[b],minlength=nv)+np.bincount(b,weights=d[a],minlength=nv)
        average=np.divide(total,transverse_degree,out=d.copy(),where=transverse_degree>0)
        proposal=(1.-transverse_strength)*d+transverse_strength*average
        proposal=.88*proposal+.12*target
        proposal[~allowed]=0.
        d,skipped=_project(xyz[:,2],proposal,chart[:,0],runs,height,projection_floor_height_fraction)
        d=d[rep]
        d[~allowed]=0.
    delta=np.zeros_like(xyz)
    delta[:,2]=float(strength)*d
    if (not np.isfinite(delta).all() or np.any(delta[:,:2]) or
            not np.array_equal(delta[:,2],delta[px,2]) or
            not np.array_equal(delta[:,2],delta[py,2])):
        raise ValueError('Finite axial-only exact-reflection invariant failed.')
    axial_edges=np.concatenate([np.column_stack([v[:-1],v[1:]]) for v in runs])
    t=chart[:,0]
    slopes0=(xyz[axial_edges[:,1],2]-xyz[axial_edges[:,0],2])/(t[axial_edges[:,1]]-t[axial_edges[:,0]])
    slopes1=((xyz[:,2]+delta[:,2])[axial_edges[:,1]]-(xyz[:,2]+delta[:,2])[axial_edges[:,0]])/(t[axial_edges[:,1]]-t[axial_edges[:,0]])
    stats=dict(meta)
    stats.update(operator='COHERENT_TRANSVERSE_AXIAL_RECONNECTION_V2',
        inherited_v1_maximum_abs_z_displacement=meta['maximum_abs_z_displacement'],
        inherited_v1_meridian_slopes_after=meta['material_meridian_slopes_after'],
        strength=float(strength),transverse_passes=int(transverse_passes),
        transverse_strength=float(transverse_strength),
        projection_floor_height_fraction=float(projection_floor_height_fraction),
        transverse_displacement_roughness_before=before,
        transverse_displacement_roughness_after=_roughness(delta[:,2],edges),
        material_meridian_slopes_before=_v1._slope_summary(slopes0,height),
        material_meridian_slopes_after=_v1._slope_summary(slopes1,height),
        changed_vertices=int(np.count_nonzero(delta[:,2])),
        maximum_abs_z_displacement=float(abs(delta[:,2]).max()),
        displacement_quantiles=np.quantile(abs(delta[:,2]),[0,.5,.9,.99,1]).tolist(),
        projection_skipped_runs=int(skipped),
        source_border_endpoints_fixed=True,
        endpoint_tangent_scope='Two exact original rows retain each original upward SOURCE-boundary tangent. An already-inverted boundary tangent pins only its exact endpoint so it can unfold. Analytic C1 is not claimed.',
        local_dependencies=['axial_reconnect.py'],
        scope='Only new axial displacement is averaged across actual equal-material-height SOURCE edges. Source XYZ is never averaged. Every pass projects eligible meridians to positive slope with fixed endpoint rows. XY/radius, attached-root borders and terminal exclusions remain exact; no collision or aesthetic certificate.')
    return delta,stats


reconnect=build
