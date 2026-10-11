"""Geometry-responsive meso folds on the existing closed column material chart.

Declared parent event bands locate the search, not the new fold coordinates.
Native triangle samples measure a parent ridge/valley, its shoulder arc length, and a
shared curved guide. No origami mechanics or arbitrary-mesh support is implied.
"""
import numpy as np
from scipy.spatial import cKDTree


def unit(vectors):
    vectors = np.asarray(vectors, dtype=float)
    lengths = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if np.any(lengths < 1e-12):
        raise ValueError('Degenerate measured guide frame.')
    return vectors / lengths


def window(q):
    """Compact C1 guide envelope; this does not smooth mesh coordinates."""
    q = np.clip(np.abs(q), 0., 1.)
    return (1. - q*q)**2


def region_frame(centres,parameter,across_vectors):
    """Pool only the guide directions over a region; leave source XYZ intact."""
    t=(parameter-parameter.mean())/(np.ptp(parameter)/2)
    coefficient=np.polyfit(t,centres,3)
    tangent=unit(np.column_stack([np.polyval(np.polyder(coefficient[:,i]),t) for i in range(3)]))
    across=np.column_stack([np.polyval(np.polyfit(t,across_vectors[:,i],2),t) for i in range(3)])
    across=unit(across-tangent*np.sum(across*tangent,axis=1)[:,None])
    normal=unit(np.cross(tangent,across))
    radial=np.column_stack([centres[:,:2],np.zeros(len(centres))])
    sign=1. if np.median(np.sum(normal*radial,axis=1))>=0 else -1.
    return tangent*sign,normal*sign


class NativeChartSampler:
    """Barycentric points on actual native triangles in the first quadrant.

    UV uses affine (material height, atan2 at each native triangle vertex).
    This is an explicit chart interpolant, not a world-space planar section.
    Candidate lookup never substitutes nearest points for missing triangles.
    """
    def __init__(self, xyz, triangles, chart):
        xyz, triangles, chart = np.asarray(xyz), np.asarray(triangles), np.asarray(chart)
        if xyz.shape != chart.shape or xyz.ndim != 2 or xyz.shape[1] != 3:
            raise ValueError('Matching finite native XYZ and material chart required.')
        if not np.isfinite(xyz).all() or not np.isfinite(chart).all():
            raise ValueError('Finite native coordinates required.')
        if triangles.ndim != 2 or triangles.shape[1] != 3:
            raise ValueError('Explicit native triangles required.')
        theta = np.arctan2(chart[:, 2], chart[:, 1])
        uv = np.column_stack([chart[:, 0], theta])
        body = np.linalg.norm(chart[:, 1:], axis=1) > .2
        quarter = (chart[:, 1] >= -1e-10) & (chart[:, 2] >= -1e-10) & body
        ids = np.flatnonzero(quarter[triangles].all(axis=1))
        p = uv[triangles[ids]]
        basis = np.stack([p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]], axis=2)
        good = np.abs(np.linalg.det(basis)) > 1e-14
        self.ids, self.p, self.basis = ids[good], p[good], basis[good]
        self.inv = np.linalg.inv(self.basis)
        self.xyz = xyz[triangles[self.ids]]
        self.tree = cKDTree(self.p.mean(axis=1))

    def sample(self, uv, *, records=False):
        uv = np.asarray(uv, dtype=float)
        shape = uv.shape[:-1]
        uv = uv.reshape(-1, 2)
        if not np.isfinite(uv).all():
            raise ValueError('Finite material sample coordinates required.')
        chosen = np.full(len(uv), -1, dtype=int)
        bary = np.zeros((len(uv), 3))
        for count in (24, 128, 512):
            unresolved = np.flatnonzero(chosen < 0)
            if not len(unresolved):
                break
            _, cand = self.tree.query(uv[unresolved], k=min(count, len(self.p)))
            cand = np.asarray(cand).reshape(len(unresolved), -1)
            b = np.einsum('nkij,nkj->nki', self.inv[cand],
                uv[unresolved, None, :]-self.p[cand, 0])
            weights = np.concatenate([1.-b.sum(axis=2, keepdims=True), b], axis=2)
            valid = (weights >= -1e-9).all(axis=2) & (weights <= 1.+1e-9).all(axis=2)
            found = valid.any(axis=1)
            row, col = np.flatnonzero(found), np.argmax(valid, axis=1)[found]
            chosen[unresolved[row]] = cand[row, col]
            bary[unresolved[row]] = weights[row, col]
        if (chosen < 0).any():
            raise ValueError(f'{int((chosen < 0).sum())} guide samples outside native chart.')
        points = np.einsum('ni,nij->nj', bary, self.xyz[chosen]).reshape(*shape, 3)
        if records:
            return points, self.ids[chosen].reshape(shape), bary.reshape(*shape, 3)
        return points


def parent_height(theta, u, parent):
    """Only a search trajectory, inherited from the declared parent profile."""
    h, span, width = [parent[k] for k in ('height', 'span', 'overlap_width')]
    s = np.broadcast_to(h+span*np.asarray(u), np.broadcast_shapes(np.shape(theta), np.shape(u))).copy()
    for _ in range(8):
        centre = parent['direction']+parent['sweep']*np.sin(np.pi*(s-h)/.32)
        q = np.clip(np.abs(np.asarray(theta)-centre)/width, 0, 1)
        s = h+.05*q**1.4+span*np.asarray(u)
    return s


def measure_parent(sampler, parent, *, shoulder_fraction=.55,frame_mode='native'):
    """One smooth guide fitted to a measured shoulder across multiple cells.

    Per-ray deepest radial chord deficit locates the basin within the declared
    parent band. Arc distance toward its upper lip locates the child. A quadratic
    fit pools those measured locations, preventing per-cell guide jitter.
    """
    lo = max(.025, parent['direction']-.82*parent['overlap_width'])
    hi = min(np.pi/2-.025, parent['direction']+.82*parent['overlap_width'])
    if hi-lo < .10:
        raise ValueError('Parent band too narrow on the canonical quadrant.')
    theta = np.linspace(lo, hi, 41)
    u = np.linspace(-.35, .75, 65)
    height = parent_height(theta[:, None], u[None, :], parent)
    uv = np.stack([height, np.broadcast_to(theta[:, None], height.shape)], axis=2)
    xyz, triangle_ids, bary = sampler.sample(uv, records=True)
    radial = np.linalg.norm(xyz[:, :, :2], axis=2)
    chord = radial[:, :1]+(radial[:, -1:]-radial[:, :1])*np.linspace(0, 1, len(u))
    deficits = chord-radial
    interior = (u >= -.05) & (u <= .50)
    trough = np.argmax(np.where(interior, deficits, -np.inf), axis=1)
    arc = np.concatenate([np.zeros((len(theta), 1)),
        np.cumsum(np.linalg.norm(np.diff(xyz, axis=1), axis=2), axis=1)], axis=1)
    child_s, shoulder_length, trough_s = [], [], []
    for row, index in enumerate(trough):
        length = arc[row, -1]-arc[row, index]
        if length <= 1e-9:
            raise ValueError('Measured parent shoulder has no positive arc length.')
        child_s.append(np.interp(arc[row, index]+shoulder_fraction*length, arc[row], height[row]))
        shoulder_length.append(length)
        trough_s.append(height[row, index])
    t = (theta-(lo+hi)/2)/((hi-lo)/2)
    fit = np.polyfit(t, child_s, 2)
    guide_s = np.polyval(fit, t)
    lower_fit = np.polyfit(t, trough_s, 2)
    lower_s = np.polyval(lower_fit, t)
    upper_s = height[:, -1]
    if not np.all((guide_s > lower_s) & (guide_s < upper_s)):
        raise ValueError('Pooled guide escaped the measured shoulder.')
    centres, centre_triangles, centre_bary = sampler.sample(
        np.column_stack([guide_s, theta]), records=True)
    tangent = unit(np.gradient(centres, theta, axis=0))
    epsilon = .001*parent['span']
    across = (sampler.sample(np.column_stack([guide_s+epsilon, theta]))
        -sampler.sample(np.column_stack([guide_s-epsilon, theta])))
    across = unit(across-tangent*np.sum(across*tangent, axis=1)[:, None])
    normal = unit(np.cross(tangent, across))
    radial_direction = np.column_stack([centres[:, :2], np.zeros(len(theta))])
    signs = np.where(np.sum(normal*radial_direction, axis=1) >= 0, 1., -1.)
    normal *= signs[:, None]
    # An unoriented tangent is enough for grooves. RETURN needs a consistent
    # right-handed T/B/N frame; choose T so T cross across equals outward N.
    tangent *= signs[:, None]
    if frame_mode=='region':
        tangent,normal=region_frame(centres,theta,xyz[:,-1]-xyz[np.arange(len(theta)),trough])
    elif frame_mode!='native':
        raise ValueError('Explicit native or region guide frame required.')
    length_fit = np.polyfit(t, shoulder_length, 2)
    lengths = np.polyval(length_fit, t)
    if np.any(lengths <= 0):
        raise ValueError('Invalid pooled physical shoulder scale.')
    basin_deficit = deficits[np.arange(len(theta)), trough]
    if np.median(basin_deficit)/np.median(lengths) < .02:
        raise ValueError('No measured parent basin in the declared search band.')
    return dict(theta=theta, guide_s=guide_s, lower_s=lower_s, upper_s=upper_s,
        parameter=theta, guide_cross=guide_s, lower_cross=lower_s, upper_cross=upper_s,
        axis=np.array('theta'),frame_mode=np.array(frame_mode),
        centres=centres, tangent=tangent, normal=normal, shoulder_length=lengths,
        measured_child_s=np.asarray(child_s), measured_shoulder_length=np.asarray(shoulder_length),
        parent_basin_deficit=basin_deficit,
        source_sample_uv=uv, source_sample_xyz=xyz, source_triangle_ids=triangle_ids,
        source_barycentric=bary, centre_triangle_ids=centre_triangles,
        centre_barycentric=centre_bary, guide_fit=fit)


def measure_longitudinal(sampler, parent, *, shoulder_fraction=.55,frame_mode='native'):
    """Track measured ridge OR valley shoulders along height instead of across it.

    Absolute angular chord relief selects the actual strongest parent feature.
    The seed confines the search. Its sign is recorded; a ridge is never relabeled
    a basin. Physical arc distance locates a child on the adjacent shoulder.
    """
    s=np.linspace(parent['height']-.9*parent['span'],parent['height']+1.2*parent['span'],41)
    centre=parent['direction']+parent['sweep']*np.sin(np.pi*(s-parent['height'])/.32)
    lo=np.maximum(.025,centre-.85*parent['overlap_width'])
    hi=np.minimum(np.pi/2-.025,centre+.85*parent['overlap_width'])
    if np.any(hi-lo<.10):
        raise ValueError('Longitudinal parent band too narrow.')
    fractions=np.linspace(0,1,65)
    theta=lo[:,None]+fractions[None,:]*(hi-lo)[:,None]
    uv=np.stack([np.broadcast_to(s[:,None],theta.shape),theta],axis=2)
    xyz,ids,bary=sampler.sample(uv,records=True)
    radial=np.linalg.norm(xyz[:,:,:2],axis=2)
    chord=radial[:,:1]+(radial[:,-1:]-radial[:,:1])*fractions
    deficit=chord-radial
    interior=(fractions>=.18)&(fractions<=.75)
    feature=np.argmax(np.where(interior,np.abs(deficit),-np.inf),axis=1)
    arc=np.concatenate([np.zeros((len(s),1)),
        np.cumsum(np.linalg.norm(np.diff(xyz,axis=1),axis=2),axis=1)],axis=1)
    child,lower,lengths=[],[],[]
    for row,index in enumerate(feature):
        length=arc[row,-1]-arc[row,index]
        if length<=1e-9:
            raise ValueError('Measured longitudinal shoulder has no arc length.')
        child.append(np.interp(arc[row,index]+shoulder_fraction*length,arc[row],theta[row]))
        lower.append(theta[row,index]);lengths.append(length)
    t=(s-s.mean())/(np.ptp(s)/2)
    fit=np.polyfit(t,child,2);guide=np.polyval(fit,t)
    lower=np.polyval(np.polyfit(t,lower,2),t)
    # Keep the pooled guide within its measured shoulder. If fitting cannot
    # describe that shoulder, fail rather than add a discontinuous clamp.
    if not np.all((guide>lower)&(guide<hi)):
        raise ValueError('Pooled longitudinal guide escaped its shoulder.')
    centres,centre_ids,centre_bary=sampler.sample(np.column_stack([s,guide]),records=True)
    tangent=unit(np.gradient(centres,s,axis=0))
    epsilon=.001*parent['overlap_width']
    across=sampler.sample(np.column_stack([s,guide+epsilon]))-sampler.sample(np.column_stack([s,guide-epsilon]))
    across=unit(across-tangent*np.sum(across*tangent,axis=1)[:,None])
    normal=unit(np.cross(tangent,across))
    outward=np.column_stack([centres[:,:2],np.zeros(len(s))])
    sign=np.where(np.sum(normal*outward,axis=1)>=0,1.,-1.)
    normal*=sign[:,None];tangent*=sign[:,None]
    if frame_mode=='region':
        tangent,normal=region_frame(centres,s,xyz[:,-1]-xyz[np.arange(len(s)),feature])
    elif frame_mode!='native':
        raise ValueError('Explicit native or region guide frame required.')
    lengths_fit=np.polyval(np.polyfit(t,lengths,2),t)
    relief=deficit[np.arange(len(s)),feature]
    if np.any(lengths_fit<=0) or np.median(np.abs(relief))/np.median(lengths_fit)<.02:
        raise ValueError('No measured parent relief for longitudinal growth.')
    return dict(axis=np.array('height'),frame_mode=np.array(frame_mode),parameter=s,guide_cross=guide,
        lower_cross=lower,upper_cross=hi,centres=centres,tangent=tangent,normal=normal,
        shoulder_length=lengths_fit,measured_child_cross=np.asarray(child),
        measured_shoulder_length=np.asarray(lengths),parent_signed_chord_relief=relief,
        source_sample_uv=uv,source_sample_xyz=xyz,source_triangle_ids=ids,
        source_barycentric=bary,centre_triangle_ids=centre_ids,
        centre_barycentric=centre_bary,guide_fit=fit)


def proposal(xyz, chart, guides, *, mode='GROOVE', depth_ratio=.28, angle=.65):
    """A connected V groove, or that groove plus paired shoulder rotations.

    All points in a strip share the measured curve frame at their guide parameter.
    Width/depth depend on the actual shoulder, not the mesh edge length. X/Y
    symmetry is constructed from one canonical quadrant. No old-point lock or
    Mandelbulb pass is applied. Parent band's lower/upper boundaries have zero
    displacement; complete old fold preservation is not guaranteed.
    """
    xyz, chart = np.asarray(xyz, dtype=float), np.asarray(chart, dtype=float)
    if mode not in ('GROOVE', 'RETURN') or depth_ratio < 0 or not np.isfinite([depth_ratio, angle]).all():
        raise ValueError('Declared finite region-fold controls required.')
    canonical = xyz.copy()
    canonical[:, :2] *= np.where(chart[:, 1:] < 0, -1., 1.)
    theta = np.arctan2(np.abs(chart[:, 2]), np.abs(chart[:, 1]))
    delta = np.zeros_like(xyz)
    weights = []
    for g in guides:
        th = g['parameter'] if 'parameter' in g else g['theta']
        longitudinal=str(g.get('axis','theta'))=='height'
        parameter=chart[:,0] if longitudinal else theta
        cross=theta if longitudinal else chart[:,0]
        inside = (parameter >= th[0]) & (parameter <= th[-1])
        interp = lambda values: (np.interp(parameter, th, values) if values.ndim == 1 else
            np.column_stack([np.interp(parameter, th, values[:, i]) for i in range(3)]))
        cross_keys=(('guide_cross','lower_cross','upper_cross') if 'guide_cross' in g else
            ('guide_s','lower_s','upper_s'))
        middle, lower, upper = [interp(g[key]) for key in cross_keys]
        dist = cross-middle
        extent = np.where(dist < 0, middle-lower, upper-middle)
        v = dist/np.maximum(extent, 1e-12)
        along = window((parameter-(th[0]+th[-1])/2)/((th[-1]-th[0])/2))
        # Piecewise-linear cusp makes a new groove; C1 terminal taper confines
        # the patch. This is a coordinate deformation, not a shell/origami solve.
        profile = np.maximum(0., 1.-np.abs(v))*along*inside
        centre, normal, tangent = [interp(g[key]) for key in ('centres', 'normal', 'tangent')]
        normal, tangent = unit(normal), unit(tangent)
        depth = depth_ratio*interp(g['shoulder_length'])
        move = -depth[:, None]*profile[:, None]*normal
        if mode == 'RETURN':
            r = canonical-centre
            phi = angle*np.sign(v)*window(v)*along*inside
            cosine, sine = np.cos(phi)[:, None], np.sin(phi)[:, None]
            rotated = r*cosine+np.cross(tangent, r)*sine+tangent*np.sum(tangent*r, axis=1)[:, None]*(1-cosine)
            move += rotated-r
        delta += move
        weights.append(profile)
    delta[:, :2] *= np.where(chart[:, 1:] < 0, -1., 1.)
    # Points on symmetry planes may only move within their own plane.
    delta[np.abs(chart[:, 1]) < 1e-10, 0] = 0
    delta[np.abs(chart[:, 2]) < 1e-10, 1] = 0
    poles = np.linalg.norm(chart[:, 1:], axis=1) < 1e-10
    delta[poles] = 0
    return delta, np.asarray(weights)
