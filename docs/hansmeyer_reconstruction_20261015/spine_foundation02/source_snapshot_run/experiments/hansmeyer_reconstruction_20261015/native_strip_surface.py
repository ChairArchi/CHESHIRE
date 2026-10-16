"""Exact same-sheet strip measurements on a preserved quad-centre fan.

The saved MIDDLE scalar is a search hint. Connectivity and every returned
sample use actual native fan triangles, never a nearest point on another sheet.
This module does not modify the input geometry or form an ornament.
"""
from pathlib import Path

import numpy as np


def helper_paths():
    return [Path(__file__).resolve()]


def _unit(vector):
    value = np.asarray(vector, dtype=float)
    length = np.linalg.norm(value)
    if not np.isfinite(length) or length <= 1e-15:
        raise ValueError('Undefined direction; no fallback.')
    return value/length


class NativeSurface:
    """SOURCE-only native fan with explicit quad-boundary adjacency.

    Global native triangle ID is 4*quadID+corner. Its vertices are the old
    corner, next corner, and the arithmetic centre of that exact quad.
    """

    def __init__(self, xyz, quads, phi, source_mask, chart):
        self.xyz = np.asarray(xyz)
        self.quads = np.asarray(quads)
        self.phi = np.asarray(phi)
        self.source_mask = np.asarray(source_mask, dtype=bool)
        self.chart = np.asarray(chart)
        self.nv = len(self.xyz)
        self.nq = len(self.quads)
        if (self.xyz.shape != (self.nv, 3) or self.chart.shape != self.xyz.shape or
                self.quads.shape != (self.nq, 4) or self.phi.shape != (self.nv,) or
                self.source_mask.shape != (self.nq,) or not self.source_mask.any()):
            raise ValueError('Actual full control XYZ/chart/phase and quad SOURCE mask required.')
        if self.quads.dtype.kind not in 'iu' or self.quads.min() < 0 or self.quads.max() >= self.nv:
            raise ValueError('Invalid control indices.')
        if not (np.isfinite(self.xyz).all() and np.isfinite(self.chart).all() and np.isfinite(self.phi).all()):
            raise ValueError('Finite preserved arrays required.')
        if 4*self.nq >= np.iinfo(np.int32).max or self.nv*self.nv >= np.iinfo(np.int64).max:
            raise ValueError('Explicit index encoding budget exceeded.')
        self.scale = max(float(np.ptp(self.xyz, axis=0).max()), 1e-12)
        self._boundary_neighbour = np.full((self.nq, 4), -1, np.int32)
        selected = np.flatnonzero(self.source_mask)
        q = self.quads[selected]
        following = np.roll(q, -1, axis=1)
        codes = (np.minimum(q, following)*self.nv + np.maximum(q, following)).ravel()
        order = np.argsort(codes, kind='stable')
        ordered = codes[order]
        begin = np.r_[0, np.flatnonzero(ordered[1:] != ordered[:-1])+1]
        count = np.diff(np.r_[begin, len(ordered)])
        if np.any(count > 2):
            raise ValueError('Nonmanifold SOURCE edge incidence; no repair.')
        paired = begin[count == 2]
        first, second = order[paired], order[paired+1]
        f0, c0 = selected[first//4], first % 4
        f1, c1 = selected[second//4], second % 4
        if np.any(q[first//4, c0] != following[second//4, c1]):
            raise ValueError('SOURCE shared edge has inconsistent winding.')
        self._boundary_neighbour[f0, c0] = 4*f1+c1
        self._boundary_neighbour[f1, c1] = 4*f0+c0
        self.adjacency_metadata = dict(source_quads=len(selected),
            shared_source_quad_edges=len(paired), source_boundary_quad_edges=int(np.count_nonzero(count == 1)),
            native_triangle_id='4*global_quad_id+corner',
            crossing='Intraquad fan spokes directly; quad boundary through exact shared control-edge IDs.',
            source_geometry_modified=False)

    def _triangle(self, triangle_id):
        triangle_id = int(triangle_id)
        if not 0 <= triangle_id < 4*self.nq or not self.source_mask[triangle_id//4]:
            raise ValueError('Triangle is outside SOURCE.')
        face, corner = divmod(triangle_id, 4)
        ids = self.quads[face]
        points = np.stack((self.xyz[ids[corner]], self.xyz[ids[(corner+1) % 4]], self.xyz[ids].mean(axis=0)))
        e1, e2 = points[1]-points[0], points[2]-points[0]
        a, b, c = e1@e1, e1@e2, e2@e2
        determinant = a*c-b*b
        if not determinant > 0. or determinant/max(a*c, 1e-300) < 1e-12:
            raise ValueError('Degenerate or ill-conditioned native triangle.')
        normal = _unit(np.cross(e1, e2))
        return points, normal, (e1, e2, a, b, c, determinant)

    @staticmethod
    def _barycentric(point, data):
        points, _, gram = data
        e1, e2, a, b, c, determinant = gram
        relative = np.asarray(point)-points[0]
        r1, r2 = relative@e1, relative@e2
        u, v = (c*r1-b*r2)/determinant, (a*r2-b*r1)/determinant
        return np.asarray((1-u-v, u, v))

    def sample(self, tri_id, bary):
        ids, weights = np.broadcast_arrays(np.asarray(tri_id, dtype=np.int64)[..., None], np.asarray(bary, dtype=float))
        ids = ids[..., 0]
        shape = ids.shape
        ids, weights = ids.ravel(), weights.reshape(-1, 3)
        valid = (ids >= 0) & (ids < 4*self.nq) & np.isfinite(weights).all(axis=1)
        valid &= (weights.min(axis=1) >= -1e-9) & (weights.max(axis=1) <= 1+1e-9)
        valid &= abs(weights.sum(axis=1)-1.) <= 1e-9
        safe = np.clip(ids, 0, 4*self.nq-1)
        valid &= self.source_mask[safe//4]
        xyz = np.full((len(ids), 3), np.nan)
        chart = np.full_like(xyz, np.nan)
        normal = np.full_like(xyz, np.nan)
        gradient = np.full_like(xyz, np.nan)
        phase = np.full(len(ids), np.nan)
        for i in np.flatnonzero(valid):
            try:
                points, n, gram = self._triangle(ids[i])
            except ValueError:
                valid[i] = False
                continue
            face, corner = divmod(int(ids[i]), 4)
            q = self.quads[face]
            cs = np.stack((self.chart[q[corner]], self.chart[q[(corner+1) % 4]], self.chart[q].mean(axis=0)))
            ps = np.asarray((self.phi[q[corner]], self.phi[q[(corner+1) % 4]], self.phi[q].mean()))
            xyz[i], chart[i], phase[i], normal[i] = weights[i]@points, weights[i]@cs, weights[i]@ps, n
            e1, e2, a, b, c, determinant = gram
            d1, d2 = ps[1]-ps[0], ps[2]-ps[0]
            gradient[i] = ((c*d1-b*d2)*e1 + (a*d2-b*d1)*e2)/determinant
        return dict(xyz=xyz.reshape(*shape, 3), chart=chart.reshape(*shape, 3),
            phi=phase.reshape(shape), normal=normal.reshape(*shape, 3),
            gradient=gradient.reshape(*shape, 3), valid=valid.reshape(shape),
            triangle_ids=ids.reshape(shape), barycentric=weights.reshape(*shape, 3))

    def _neighbour(self, triangle_id, opposite_corner):
        face, corner = divmod(int(triangle_id), 4)
        if opposite_corner == 0:
            return 4*face+(corner+1) % 4
        if opposite_corner == 1:
            return 4*face+(corner-1) % 4
        return int(self._boundary_neighbour[face, corner])

    def _walk(self, state, requested, max_crossings):
        tri, bary, direction, previous = state
        remaining, travelled = float(requested), 0.
        tolerance = 2e-12*self.scale
        for _ in range(max_crossings):
            try:
                data = self._triangle(tri)
            except ValueError:
                return (tri, bary, direction, previous), travelled, 'INVALID_TRIANGLE'
            points, normal, gram = data
            direction = direction-normal*(direction@normal)
            try:
                direction = _unit(direction)
            except ValueError:
                return (tri, bary, direction, previous), travelled, 'INVALID_TANGENT'
            e1, e2, a, b, c, determinant = gram
            r1, r2 = direction@e1, direction@e2
            du, dv = (c*r1-b*r2)/determinant, (a*r2-b*r1)/determinant
            derivative = np.asarray((-du-dv, du, dv))
            hits = np.full(3, np.inf)
            decreasing = derivative < -1e-12/max(np.sqrt(max(a, c)), 1e-15)
            hits[decreasing] = -np.maximum(bary[decreasing], 0.)/derivative[decreasing]
            hit = float(hits.min())
            if not np.isfinite(hit):
                return (tri, bary, direction, previous), travelled, 'NO_FORWARD_EDGE'
            if hit >= remaining-tolerance:
                new_bary = bary+remaining*derivative
                new_bary[abs(new_bary) < 1e-10] = 0.
                if new_bary.min() < -1e-8:
                    return (tri, bary, direction, previous), travelled, 'BARYCENTRIC_EXIT_ERROR'
                new_bary = np.maximum(new_bary, 0.)
                new_bary /= new_bary.sum()
                return (tri, new_bary, direction, previous), travelled+remaining, 'OK'
            tied = np.flatnonzero(abs(hits-hit) <= tolerance)
            if len(tied) != 1:
                return (tri, bary, direction, previous), travelled, 'AMBIGUOUS_VERTEX_HIT'
            opposite = int(tied[0])
            crossing_bary = bary+hit*derivative
            crossing_bary[abs(crossing_bary) < 1e-9] = 0.
            crossing_bary = np.maximum(crossing_bary, 0.)
            crossing_bary /= crossing_bary.sum()
            point = crossing_bary@points
            following = self._neighbour(tri, opposite)
            travelled += hit
            remaining -= hit
            if following < 0:
                return (tri, crossing_bary, direction, previous), travelled, 'SOURCE_BOUNDARY'
            if following == previous and hit <= tolerance:
                return (tri, crossing_bary, direction, previous), travelled, 'EDGE_BOUNCE'
            try:
                next_data = self._triangle(following)
            except ValueError:
                return (tri, crossing_bary, direction, previous), travelled, 'INVALID_NEIGHBOUR'
            next_bary = self._barycentric(point, next_data)
            if next_bary.min() < -1e-8 or np.linalg.norm(next_bary@next_data[0]-point) > 2e-10*self.scale:
                return (tri, crossing_bary, direction, previous), travelled, 'SHARED_EDGE_IDENTITY_ERROR'
            next_bary[abs(next_bary) < 1e-9] = 0.
            next_bary = np.maximum(next_bary, 0.)
            next_bary /= next_bary.sum()
            edge_indices = [j for j in range(3) if j != opposite]
            axis = _unit(points[edge_indices[1]]-points[edge_indices[0]])
            next_normal = next_data[1]
            sine = float(axis@np.cross(normal, next_normal))
            cosine = float(np.clip(normal@next_normal, -1., 1.))
            # Hinge rotation maps old normal to new normal while fixing the
            # shared edge. It is piecewise-flat geodesic parallel transport.
            direction = direction*cosine + np.cross(axis, direction)*sine + axis*(axis@direction)*(1-cosine)
            previous, tri, bary = tri, following, next_bary
        return (tri, bary, direction, previous), travelled, 'CROSSING_BUDGET'

    def trace_across(self, starttri, bary, direction, signed_distances, *, max_crossings=100000):
        distances = np.asarray(signed_distances, dtype=float)
        if distances.ndim != 1 or not np.isfinite(distances).all():
            raise ValueError('Finite one-dimensional signed physical distances required.')
        bary = np.asarray(bary, dtype=float)
        first = self.sample(int(starttri), bary)
        n = len(distances)
        ids = np.full(n, -1, np.int64)
        weights = np.full((n, 3), np.nan)
        valid = np.zeros(n, bool)
        statuses = np.full(n, 'UNREACHED', dtype='<U32')
        travelled = np.zeros(n)
        stops = {}
        if not bool(first['valid']):
            statuses[:] = 'INVALID_START'
        else:
            normal = first['normal']
            projected = np.asarray(direction, dtype=float)-normal*(np.asarray(direction)@normal)
            try:
                projected = _unit(projected)
            except ValueError:
                statuses[:] = 'INVALID_START_TANGENT'
                projected = None
            if projected is not None:
                zero = np.flatnonzero(distances == 0.)
                ids[zero], weights[zero], valid[zero], statuses[zero] = int(starttri), bary, True, 'OK'
                for sign in (-1., 1.):
                    rows = np.flatnonzero(distances*sign > 0.)
                    rows = rows[np.argsort(abs(distances[rows]), kind='stable')]
                    state = (int(starttri), bary.copy(), projected*sign, -1)
                    reached = 0.
                    stopped = None
                    for row in rows:
                        target = abs(float(distances[row]))
                        if stopped is not None:
                            statuses[row], travelled[row] = stopped, sign*reached
                            continue
                        state, actual, status = self._walk(state, target-reached, max_crossings)
                        reached += actual
                        travelled[row], statuses[row] = sign*reached, status
                        if status != 'OK':
                            stopped = status
                            stop_sample = self.sample(state[0], state[1])
                            stops[str(int(sign))] = dict(status=status, physical_distance=sign*reached,
                                triangle_id=int(state[0]), barycentric=state[1].tolist(),
                                xyz=stop_sample['xyz'].tolist())
                        else:
                            ids[row], weights[row], valid[row] = state[0], state[1], True
        observed = self.sample(ids, weights)
        observed.update(valid=valid & observed['valid'], status=statuses,
                        travelled_distance=travelled, requested_distance=distances.copy(), stops=stops)
        return observed

    def resample_curve(self, graph, node_order, count, *, periodic=False):
        order = np.asarray(node_order, dtype=np.int64)
        if len(order) < 2 or count < 3:
            raise ValueError('A genuine connected curve and at least three samples required.')
        pairs = np.column_stack((order, np.roll(order, -1))) if periodic else np.column_stack((order[:-1], order[1:]))
        edge_map = {tuple(pair):i for i, pair in enumerate(np.sort(np.asarray(graph['edges']), axis=1))}
        edge_ids = []
        for pair in np.sort(pairs, axis=1):
            if tuple(pair) not in edge_map:
                raise ValueError('Curve order crosses a nonadjacent graph gap.')
            edge_ids.append(edge_map[tuple(pair)])
        edge_ids = np.asarray(edge_ids)
        lengths = np.asarray(graph['edge_length'])[edge_ids]
        cumulative = np.r_[0., np.cumsum(lengths)]
        targets = np.linspace(0., cumulative[-1], count, endpoint=not periodic)
        segment = np.minimum(np.searchsorted(cumulative, targets, side='right')-1, len(lengths)-1)
        segment = np.maximum(segment, 0)
        triangles = np.asarray(graph['edge_triangle_id'])[edge_ids[segment]]
        bary = np.empty((count, 3))
        tangents = np.empty((count, 3))
        for i, j in enumerate(segment):
            data = self._triangle(triangles[i])
            a, b = np.asarray(graph['node_xyz'])[pairs[j]]
            fraction = (targets[i]-cumulative[j])/lengths[j]
            bary[i] = (1-fraction)*self._barycentric(a, data)+fraction*self._barycentric(b, data)
            tangents[i] = _unit(b-a)
        samples = self.sample(triangles, bary)
        if not samples['valid'].all():
            raise ValueError('Curve resample left its registered native triangles.')
        samples.update(s=targets, tangent=tangents,
                       total_length=float(cumulative[-1]), periodic=bool(periodic))
        return samples

    def measure_strip(self, triangle_ids, barycentrics, *, half_width=None, samples=33,
                      tangents=None, max_half_width=None, curve_s=None, periodic=False):
        centre = self.sample(triangle_ids, barycentrics)
        if not centre['valid'].all() or np.asarray(triangle_ids).ndim != 1 or len(triangle_ids) < 3:
            raise ValueError('At least three actual SOURCE curve samples required.')
        points = centre['xyz']
        s = (np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
             if curve_s is None else np.asarray(curve_s, dtype=float).copy())
        if s.shape != (len(points),) or not np.isfinite(s).all():
            raise ValueError('Actual ordered physical curve arc samples required.')
        if np.any(np.diff(s) <= 0.):
            raise ValueError('Duplicate curve samples cannot define physical arc.')
        if tangents is not None:
            tangent = np.asarray(tangents, dtype=float).copy()
        elif periodic:
            # Direction only; uniform resample_curve arcs close periodically.
            tangent = np.roll(points, -1, axis=0)-np.roll(points, 1, axis=0)
        else:
            tangent = np.gradient(points, s, axis=0)
        normals = centre['normal'].copy()
        across = np.full_like(points, np.nan)
        frame_valid = np.ones(len(points), bool)
        for i in range(len(points)):
            try:
                tangent[i] = _unit(tangent[i]-normals[i]*(tangent[i]@normals[i]))
                across[i] = _unit(np.cross(normals[i], tangent[i]))
            except ValueError:
                frame_valid[i] = False
        gradient = np.linalg.norm(centre['gradient'], axis=1)
        if half_width is None:
            widths = np.divide(1.35*np.pi, gradient, out=np.full_like(gradient, np.nan),
                               where=gradient*self.scale > 1e-10)
        else:
            widths = np.broadcast_to(np.asarray(half_width, dtype=float), gradient.shape).copy()
        requested_widths = widths.copy()
        if max_half_width is not None:
            if not np.isfinite(max_half_width) or max_half_width <= 0.:
                raise ValueError('Positive physical search bound required.')
            widths = np.minimum(widths, float(max_half_width))
        frame_valid &= np.isfinite(widths) & (widths > 1e-12*self.scale)
        shape = (len(points), int(samples))
        if samples < 9 or samples % 2 != 1:
            raise ValueError('An odd actual cross-profile sample count >=9 is required.')
        xyz0 = np.full((*shape, 3), np.nan)
        chart0 = np.full_like(xyz0, np.nan)
        grid_bary = np.full_like(xyz0, np.nan)
        grid_tri = np.full(shape, -1, np.int64)
        grid_phi = np.full(shape, np.nan)
        valid = np.zeros(shape, bool)
        status = np.full(shape, 'INVALID_FRAME', dtype='<U32')
        distances = widths[:, None]*np.linspace(-1., 1., samples)[None, :]
        heights = np.full(shape, np.nan)
        confirmed = np.zeros(len(points), bool)
        prominence = np.zeros(len(points))
        measured_width = np.zeros(len(points))
        peak_index = np.full(len(points), -1, np.int64)
        shoulder_indices = np.full((len(points), 2), -1, np.int64)
        for i in range(len(points)):
            if not frame_valid[i]:
                continue
            measured = self.trace_across(int(np.asarray(triangle_ids)[i]), np.asarray(barycentrics)[i], across[i], distances[i])
            xyz0[i], chart0[i], grid_phi[i] = measured['xyz'], measured['chart'], measured['phi']
            grid_tri[i], grid_bary[i] = measured['triangle_ids'], measured['barycentric']
            valid[i], status[i] = measured['valid'], measured['status']
            if not valid[i].all():
                continue
            fraction = np.linspace(0., 1., samples)
            chord = (1-fraction[:, None])*xyz0[i, 0] + fraction[:, None]*xyz0[i, -1]
            height = (xyz0[i]-chord)@normals[i]
            heights[i] = height
            peaks = np.flatnonzero((height[1:-1] > height[:-2]) & (height[1:-1] >= height[2:]))+1
            peaks = peaks[abs(distances[i, peaks]) <= .5*widths[i]]
            if not len(peaks):
                continue
            peak = int(peaks[np.argmin(abs(distances[i, peaks]))])
            left = int(np.argmin(height[:peak+1]))
            right = peak+int(np.argmin(height[peak:]))
            observed = float(height[peak]-max(height[left], height[right]))
            if left >= peak or right <= peak or observed <= max(1e-10*self.scale, 1e-6*widths[i]):
                continue
            confirmed[i], peak_index[i], shoulder_indices[i] = True, peak, (left, right)
            prominence[i] = observed
            measured_width[i] = distances[i, right]-distances[i, left]
        ridge_tri = np.full(len(points), -1, np.int64)
        ridge_bary = np.full_like(points, np.nan)
        ridge_xyz = np.full_like(points, np.nan)
        for i in np.flatnonzero(confirmed):
            ridge_tri[i], ridge_bary[i], ridge_xyz[i] = grid_tri[i, peak_index[i]], grid_bary[i, peak_index[i]], xyz0[i, peak_index[i]]
        return dict(xyz0=xyz0, chart0=chart0, phi=grid_phi, triangle_ids=grid_tri,
            barycentric=grid_bary, valid=valid, status=status, s=s, across_distances=distances,
            centre_xyz=points, centre_chart=centre['chart'], centre_phi=centre['phi'],
            tangent=tangent, normal=normals, across=across, frame_valid=frame_valid,
            search_half_width=widths, unbounded_search_half_width=requested_widths,
            intrinsic_phase_gradient_norm=gradient, profile_height=heights,
            confirmed=confirmed, width=measured_width, depth=prominence, prominence=prominence,
            geometric_peak_index=peak_index, shoulder_indices=shoulder_indices,
            ridge_xyz=ridge_xyz, ridge_triangle_ids=ridge_tri, ridge_barycentric=ridge_bary,
            metadata=dict(geometry='Exact piecewise-flat geodesic across SOURCE native fan; hinge transport across actual shared edges.',
                phase='Saved registered phase is only a candidate-crest and first-order search-spacing hint.',
                confirmation='Local actual outward normal chord-height maximum nearest nominal centre in central half of the same-sheet cross-profile; positive prominence above flanking actual sampled minima.',
                thresholds='Prominence > max(1e-10*input_extent,1e-6*search_half_width); numerical existence, not a beauty threshold.',
                shoulders='Actual sampled minima in the searched interval; can be interval endpoints and are not guaranteed independent anatomical boundaries.',
                arc='Caller curve_s preserves original native contour polyline arc; without it, chord lengths of supplied samples approximate arc. Periodic tangent uses cyclic adjacent samples.',
                limitations='Measured positive crest may include pre-existing macro curvature. Phase origin does not isolate MIDDLE causal contribution. Native faceted normals, finite cross sampling and arbitrary curve orientation remain explicit. Closed-loop frame/arc phase and mirror transport belong to caller. No model formation, XYZ-nearest lookup, collision or beauty certification.'))
