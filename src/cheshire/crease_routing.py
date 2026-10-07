"""CHESHIRE design routing on actual mesh edges, separate from crease rules."""
from collections import defaultdict
import heapq
from math import acos, degrees, dist, sqrt

from .creases import edge_key, make_network


def unit(vector):
    length = sqrt(sum(v*v for v in vector))
    return [v/length for v in vector] if length else [0., 0., 0.]


def dot(a, b):
    return max(-1., min(1., sum(x*y for x, y in zip(a, b))))


class CreaseRouter:
    def __init__(self, mesh, source, history, cells, events=(), motifs=None):
        self.mesh = mesh; self.source = source; self.history = history; self.cells = cells; self.events = events
        self.motifs = motifs
        self.xyz = {v: mesh.vertex_coordinates(v) for v in mesh.vertices()}
        p = [source.vertex_coordinates(v) for v in source.vertices()]
        self.low = [min(q[a] for q in p) for a in range(3)]
        self.high = [max(q[a] for q in p) for a in range(3)]
        self.center = [(a+b)/2 for a, b in zip(self.low, self.high)]
        self.size = [b-a for a, b in zip(self.low, self.high)]
        self.source_lintel = {f for f in source.faces() if source.face_centroid(f)[2] >= self.low[2]+.74*self.size[2]}
        self.source_front = {f for f in source.faces() if source.face_normal(f)[1] < -.25}
        normals = {f: mesh.face_normal(f) for f in mesh.faces()}
        self.edge_data = {}
        self.adjacency = {v: sorted(mesh.vertex_neighbors(v)) for v in mesh.vertices()}
        self.support = {}
        for v in mesh.vertices():
            faces = mesh.vertex_faces(v)
            self.support[v] = sum(sum(w for f0, w in history[f]['source'].items() if f0 in self.source_lintel) for f in faces)/len(faces)
        for e in mesh.edges():
            e = edge_key(e); faces = mesh.edge_faces(e)
            a, b = faces
            angle = degrees(acos(dot(normals[a], normals[b]))) if all(sum(x*x for x in normals[f]) > .5 for f in faces) else None
            self.edge_data[e] = dict(length=mesh.edge_length(e), angle=angle,
                crosses_cell=set(cells.get(a, ())) != set(cells.get(b, ())),
                front=sum(sum(w for c, w in history[f]['source'].items() if c in self.source_front) for f in faces)/2)

    def target(self, x, z, y=-.65):
        return [self.center[0]+x*self.size[0], self.center[1]+y*self.size[1], self.low[2]+z*self.size[2]]

    def nearest(self, point, *, min_degree=0, minimum_support=0.):
        eligible = [v for v in self.xyz if self.mesh.vertex_degree(v) >= min_degree and self.support[v] >= minimum_support]
        if not eligible:
            raise ValueError('No eligible semantic routing seed; no edge-ID fallback.')
        return min(eligible, key=lambda v: (dist(self.xyz[v], point), v))

    def path(self, start, goal, specification, *, first_neighbor=None):
        """Shortest positive-cost directed-edge states, including tangent history."""
        if start == goal:
            return [start]
        previous = start if first_neighbor is not None else -1
        current = first_neighbor if first_neighbor is not None else start
        initial = (previous, current); heap = [(0., previous, current)]
        costs = {initial: 0.}; parents = {}; reached = None
        while heap:
            cost, previous, current = heapq.heappop(heap)
            state = (previous, current)
            if cost != costs[state]:
                continue
            if current == goal:
                reached = state; break
            for nxt in self.adjacency[current]:
                if nxt == previous or nxt == start:
                    continue
                if self.xyz[nxt][2] < self.low[2]+specification.get('quiet_below', .5)*self.size[2]:
                    continue
                data = self.edge_data[edge_key((current, nxt))]
                direction = unit([self.xyz[nxt][a]-self.xyz[current][a] for a in range(3)])
                tangent = unit([self.xyz[current][a]-self.xyz[previous][a] for a in range(3)]) if previous >= 0 else direction
                turn = (1-dot(direction, tangent))/2
                support = (self.support[current]+self.support[nxt])/2
                angle = (data['angle'] or 0.)/180
                factor = (1 + specification.get('turn_cost', 1.4)*turn
                    + specification.get('source_cost', .8)*(1-support)
                    + specification.get('front_cost', .8)*(1-data['front'])
                    + specification.get('dihedral_cost', .25)*(1-angle)
                    - specification.get('cell_reward', .15)*data['crosses_cell'])
                if factor <= 0 or data['length'] <= 0:
                    raise ValueError('Routing requires positive edge length and cost.')
                candidate = cost+data['length']*factor; target = (current, nxt)
                if candidate < costs.get(target, float('inf')):
                    costs[target] = candidate; parents[target] = state
                    heapq.heappush(heap, (candidate, current, nxt))
        if reached is None:
            raise ValueError('Semantic route endpoints are disconnected under declared eligibility.')
        path = [reached[1]]; state = reached
        while state != initial:
            state = parents[state]; path.append(state[1])
        path.reverse()
        if first_neighbor is not None:
            path.insert(0, start)
        if len(path) != len(set(path)):
            raise ValueError('Directed route revisits a vertex; loop rejected without repair.')
        return path

    def trace(self, seed, direction, specification):
        """Bidirectional greedy continuity walk, avoiding all return vertices."""
        visited = set(seed); result = list(seed)
        maximum = specification.get('max_steps', 80)
        target_length = specification.get('length_ratio', .85)*self.size[0]
        for side in (1, 0):
            previous, current = (seed[0], seed[1]) if side else (seed[1], seed[0])
            preferred = direction if side else [-v for v in direction]
            length = 0.
            for _ in range(maximum):
                candidates = []
                tangent = unit([self.xyz[current][a]-self.xyz[previous][a] for a in range(3)])
                for nxt in self.adjacency[current]:
                    if nxt in visited or self.xyz[nxt][2] < self.low[2]+specification.get('quiet_below', .55)*self.size[2]:
                        continue
                    data = self.edge_data[edge_key((current, nxt))]
                    d = unit([self.xyz[nxt][a]-self.xyz[current][a] for a in range(3)])
                    turn = (1-dot(d, tangent))/2
                    if turn > specification.get('max_turn', .85):
                        continue
                    score = (specification.get('turn_cost', 1.4)*turn + .8*(1-dot(d, preferred))/2
                        + specification.get('source_cost', .8)*(1-self.support[nxt]) + .5*(1-data['front'])
                        - specification.get('cell_reward', .15)*data['crosses_cell']
                        - specification.get('dihedral_cost', .25)*(data['angle'] or 0.)/180)
                    candidates.append((score, nxt))
                if not candidates:
                    break
                _, nxt = min(candidates); visited.add(nxt)
                length += self.edge_data[edge_key((current, nxt))]['length']
                if side:
                    result.append(nxt)
                else:
                    result.insert(0, nxt)
                previous, current = current, nxt
                if length >= target_length/2:
                    break
        return result

    def generate(self, specification, network_id='N'):
        kind = specification['generator']; variant = specification.get('relation', 'outer_lintel')
        def point(x,z): return self.target(x,z,specification.get('target_y_ratio',-.65))
        paths = []; seeds = []; seed_events = []
        if kind == 'N1':
            relations = {
                'outer_lintel': [(-.46, .98), (0, 1.0), (.46, .98)],
                'opening_rim': [(-.28, .72), (0, .78), (.28, .72)],
                'support_shoulder_lintel': [(-.40, .60), (-.36, .90), (0, .98), (.36, .90), (.40, .60)]}
            if variant not in relations:
                raise ValueError('Undeclared architectural source relation.')
            seeds = [self.nearest(point(x, z), minimum_support=specification.get('minimum_seed_support', .05)) for x, z in relations[variant]]
            joined = []
            for a, b in zip(seeds, seeds[1:]):
                segment = self.path(a, b, specification)
                joined.extend(segment if not joined else segment[1:])
            paths = [joined]
        elif kind in ('N2', 'N3', 'N4'):
            cue = point(*specification.get('seed_xz', [-.32, .91]))
            eligible = [e for e in self.edge_data if (self.support[e[0]]+self.support[e[1]])/2 >= .3]
            preferred = unit(specification.get('direction', [1., 0., 0.]))
            if kind == 'N4':
                candidates = []
                for event in self.events:
                    if event.get('operator') != 'Roof':
                        continue
                    sides = [c['id'] for c in event['children'] if c['role'] == 'RIDGE_SIDE' and self.mesh.has_face(c['id'])]
                    if len(sides) != 2:
                        continue
                    shared = set(self.mesh.face_vertices(sides[0])) & set(self.mesh.face_vertices(sides[1]))
                    if len(shared) != 2 or edge_key(tuple(shared)) not in self.edge_data:
                        continue
                    e = edge_key(tuple(shared)); mid = [(self.xyz[e[0]][i]+self.xyz[e[1]][i])/2 for i in range(3)]
                    candidates.append((dist(mid, cue), event['id'], e, event['direction_details']['actual_ridge_axis']))
                if not candidates:
                    raise ValueError('No surviving recorded Roof ridge edge; no invented transfer.')
                _, event_id, seed, preferred = min(candidates); seed_events = [event_id]
                preferred = unit(preferred)
            else:
                if not eligible:
                    raise ValueError('No eligible trace seed.')
                def score(e):
                    mid = [(self.xyz[e[0]][i]+self.xyz[e[1]][i])/2 for i in range(3)]
                    d = unit([self.xyz[e[1]][i]-self.xyz[e[0]][i] for i in range(3)])
                    return (dist(mid, cue)/self.size[0]+.3*(1-abs(dot(d, preferred)))
                        - (.65*(self.edge_data[e]['angle'] or 0.)/180 if kind == 'N3' else 0), e)
                seed = min(eligible, key=score)
            if dot(unit([self.xyz[seed[1]][i]-self.xyz[seed[0]][i] for i in range(3)]), preferred) < 0:
                seed = tuple(reversed(seed))
            paths = [self.trace(seed, preferred, specification)]; seeds = list(seed)
        elif kind in ('N5', 'N6'):
            side = specification.get('side', 'left')
            if kind == 'N5':
                sign = -1 if side == 'left' else 1
                cue = point(*specification.get('seed_xz',[sign*.36,.87]))
                targets = [(0, .96), (sign*.47, .98), (sign*.39, .56)]
            else:
                cue = point(*specification.get('junction_xz', [0, .91]))
                junction = specification.get('junction', 'T')
                targets = {'T': [(-.45, .90), (.45, .90), (0, 1.04)],
                    'X': [(-.45, .90), (.45, .90), (0, 1.04), (0, .76)],
                    'Y': [(-.40, .98), (.40, .98), (0, .76)]}.get(junction)
                if targets is None:
                    raise ValueError('Undeclared junction.')
                targets = specification.get('arm_targets', targets)
            center = self.nearest(cue, min_degree=len(targets), minimum_support=specification.get('minimum_seed_support', .3)); seeds = [center]
            used = set()
            for x, z in targets:
                goal = self.nearest(point(x, z), minimum_support=specification.get('minimum_target_support', .05))
                if goal == center:
                    raise ValueError('Junction arm snaps to its seed under source eligibility; empty arm rejected.')
                direction = unit([self.xyz[goal][a]-self.xyz[center][a] for a in range(3)])
                candidates = [u for u in self.adjacency[center] if u not in used]
                first = min(candidates, key=lambda u: (-dot(unit([self.xyz[u][a]-self.xyz[center][a] for a in range(3)]), direction), u))
                used.add(first); seeds.append(goal)
                paths.append(self.path(center, goal, specification, first_neighbor=first))
        else:
            raise ValueError('Undeclared network generator.')
        edges = {edge_key((a, b)) for path in paths for a, b in zip(path, path[1:])}
        profile = specification.get('profile', 'CONSTANT'); base = specification.get('sharpness', 4.)
        adjacency = defaultdict(list)
        for a, b in edges:
            length = self.edge_data[(a, b)]['length']; adjacency[a].append((b, length)); adjacency[b].append((a, length))
        degrees0 = {v: len(n) for v, n in adjacency.items()}
        start = paths[0][0]
        if profile == 'JUNCTION_SOFT_ENDS':
            junctions = [v for v, degree in degrees0.items() if degree >= 3]
            start = min(junctions or adjacency, key=lambda v: (dist(self.xyz[v], point(0, .92)), v))
        distances = {start: 0.}; heap = [(0., start)]
        while heap:
            d, v = heapq.heappop(heap)
            if d != distances[v]:
                continue
            for u, length in adjacency[v]:
                if d+length < distances.get(u, float('inf')):
                    distances[u] = d+length; heapq.heappush(heap, (d+length, u))
        maximum = max(distances.values()); values = {}
        for e in edges:
            t = (distances[e[0]]+distances[e[1]])/(2*maximum) if maximum else 0.
            if profile == 'CONSTANT': s = base
            elif profile == 'SHOULDER_TO_CENTER': s = .5+(base-.5)*abs(2*t-1)
            elif profile == 'JUNCTION_SOFT_ENDS': s = .25+(base-.25)*(1-t)
            elif profile == 'CENTER_SOFT_TAILS': s = .25+(base-.25)*(1-abs(2*t-1))
            elif profile == 'TWO_PEAKS': s = .5+(base-.5)*max(0., 1-4*abs(t-.25), 1-4*abs(t-.75))
            else: raise ValueError('Undeclared sharpness profile.')
            values[e] = s
        routing = dict(paths=paths, semantic_seed_vertices=seeds, seed_events=seed_events,
            profile=profile, profile_distance_origin=start, profile_maximum_graph_length=maximum,
            source_lintel_faces=sorted(self.source_lintel), source_front_faces=sorted(self.source_front),
            seed_policy='World targets derive from C0 architecture; deterministic nearest eligible vertex/edge. No manually picked generated edge IDs.',
            propagation='Finite Uniform max(s-1,0), no Chaikin neighbor averaging.')
        return make_network(self.mesh, network_id, edges, values, specification, cells=self.cells,
            history=self.history, motifs=self.motifs, routing=routing)
