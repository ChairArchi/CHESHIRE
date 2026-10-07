"""Explicit mesh-edge networks and finite uniform semi-sharp Catmull-Clark.

Integer geometry is delegated to installed COMPAS. Fractional transitions use
the published OpenSubdiv Uniform mask rules, independently expressed here.
No upstream code, limit evaluation, Chaikin propagation or infinite sentinel.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from math import dist, isfinite

from .execution import ExecutionBudget, check_execution_budget
from .validation import inspect_mesh, validate_mesh


def edge_key(edge):
    if len(edge) != 2 or any(type(v) is not int for v in edge) or edge[0] == edge[1]:
        raise ValueError("An edge requires two distinct integer vertex IDs.")
    return tuple(sorted(edge))


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sharpness(value):
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError("Sharpness must be a finite nonnegative real value.")
    return float(value)


@dataclass(frozen=True)
class CreaseEdge:
    vertices: tuple
    sharpness: float
    parent_edge: tuple | None
    root_edge: tuple
    parent_cells: tuple
    c0_faces: tuple
    motif_ancestry: tuple = ()

    def __post_init__(self):
        if self.vertices != edge_key(self.vertices) or self.root_edge != edge_key(self.root_edge):
            raise ValueError("Canonical edge identity required.")
        object.__setattr__(self,'sharpness',sharpness(self.sharpness))
        if self.parent_edge is not None and self.parent_edge != edge_key(self.parent_edge):
            raise ValueError("Canonical immediate parent edge required.")
        for values in (self.parent_cells, self.c0_faces, self.motif_ancestry):
            if values != tuple(sorted(set(values))):
                raise ValueError("Canonical ancestry sets required.")


@dataclass(frozen=True)
class CreaseNetwork:
    network_id: str
    seed_rule_json: str
    edges: tuple
    generation: int
    path_length: float
    routing_json: str = "{}"

    def __post_init__(self):
        if not self.network_id or type(self.generation) is not int or self.generation < 0:
            raise ValueError("Named network and nonnegative generation required.")
        if not self.edges or tuple(e.vertices for e in self.edges) != tuple(sorted({e.vertices for e in self.edges})):
            raise ValueError("Nonempty sorted unique network edges required.")
        if not isfinite(self.path_length) or self.path_length < 0:
            raise ValueError("Finite geometric path length required.")
        canonical(json.loads(self.seed_rule_json)); canonical(json.loads(self.routing_json))
        adjacency = defaultdict(set)
        for e in self.edges:
            a, b = e.vertices; adjacency[a].add(b); adjacency[b].add(a)
        visited = {min(adjacency)}; stack = list(visited)
        while stack:
            for v in adjacency[stack.pop()] - visited:
                visited.add(v); stack.append(v)
        if visited != set(adjacency):
            raise ValueError("A CreaseNetwork must be one connected mesh-edge graph.")

    @property
    def junction_vertices(self):
        degree = Counter(v for e in self.edges for v in e.vertices)
        return tuple(sorted(v for v, d in degree.items() if d >= 3))

    def to_data(self):
        cells = sorted({c for e in self.edges for c in e.parent_cells})
        coarse = sorted({c for e in self.edges for c in e.c0_faces})
        return dict(network_id=self.network_id, seed_rule=json.loads(self.seed_rule_json),
            generation=self.generation, geometric_path_length=self.path_length,
            junction_vertices=list(self.junction_vertices), parent_cell_ancestry=cells,
            c0_ancestry=coarse, cross_cell=len(cells) >= 3 or len(coarse) >= 2,
            routing=json.loads(self.routing_json), edges=[dict(edge_id=f"{e.vertices[0]}:{e.vertices[1]}",
                vertices=list(e.vertices), sharpness=e.sharpness,
                parent_edge=None if e.parent_edge is None else list(e.parent_edge),
                root_edge=list(e.root_edge), parent_cells=list(e.parent_cells),
                c0_faces=list(e.c0_faces), motif_ancestry=list(e.motif_ancestry)) for e in self.edges])

    @classmethod
    def from_data(cls, data):
        edges = tuple(CreaseEdge(tuple(e['vertices']), sharpness(e['sharpness']),
            None if e['parent_edge'] is None else tuple(e['parent_edge']), tuple(e['root_edge']),
            tuple(e['parent_cells']), tuple(e['c0_faces']), tuple(e.get('motif_ancestry', []))) for e in data['edges'])
        result = cls(data['network_id'], canonical(data['seed_rule']), edges,
            data['generation'], data['geometric_path_length'], canonical(data.get('routing', {})))
        if canonical(result.to_data()) != canonical(data):
            raise ValueError("Serialized network diagnostics/identities do not match its graph.")
        return result

    def digest(self):
        return sha256(canonical(self.to_data()).encode()).hexdigest()

    def __hash__(self):
        return int(self.digest()[:16], 16)


def make_network(mesh, network_id, edges, value, seed_rule, *, cells=None,
                 history=None, motifs=None, routing=None):
    known = {edge_key(e) for e in mesh.edges()}
    edges = sorted({edge_key(e) for e in edges})
    if not set(edges) <= known:
        raise ValueError("Network includes an edge absent from the actual input mesh.")
    rows = []
    for e in edges:
        faces = [f for f in mesh.edge_faces(e) if f is not None]
        s = value[e] if isinstance(value, dict) else value
        rows.append(CreaseEdge(e, sharpness(s), None, e,
            tuple(sorted({c for f in faces for c in (cells or {}).get(f, [])})),
            tuple(sorted({c for f in faces for c, w in (history or {}).get(f, {}).get('source', {}).items() if w > 0})),
            tuple(sorted({m for v in e for m in (motifs or {}).get(v, [])}))))
    return CreaseNetwork(network_id, canonical(seed_rule), tuple(rows), 0,
        sum(mesh.edge_length(e) for e in edges), canonical(routing or {}))


def vertex_rule(neighbors):
    return 'CORNER' if len(neighbors) >= 3 else 'CREASE' if len(neighbors) == 2 else 'DART' if neighbors else 'SMOOTH'


def crease_vertex(v, neighbors, xyz, smooth):
    if len(neighbors) >= 3:
        return xyz[v][:]
    if len(neighbors) == 2:
        a, b = neighbors
        return [(xyz[a][i] + 6 * xyz[v][i] + xyz[b][i]) / 8 for i in range(3)]
    return smooth[:]


def fractional_vertex(v, incident, xyz, smooth):
    """Uniform parent/child rule transition; disappearing-edge average weight."""
    active = [u for u, s in incident if s > 0]
    remaining = [u for u, s in incident if s > 1]
    parent, child = vertex_rule(active), vertex_rule(remaining)
    p = crease_vertex(v, active, xyz, smooth)
    if parent in ('SMOOTH', 'DART') or parent == child:
        return p, dict(parent=parent, child=child, parent_weight=1.)
    disappearing = [s for u, s in incident if 0 < s <= 1]
    t = min(sum(disappearing) / len(disappearing), 1.)
    c = crease_vertex(v, remaining, xyz, smooth)
    if t == 1:
        return p, dict(parent=parent, child=child, parent_weight=t)
    return [t * p[i] + (1 - t) * c[i] for i in range(3)], dict(parent=parent, child=child, parent_weight=t)


@dataclass(frozen=True)
class CreaseResult:
    mesh: object
    networks: tuple
    metadata: dict
    sampling_parents: dict


def crease_subdivide_once(mesh, networks=(), *, mode='INTEGER_COMPAS', fixed=(),
                          budget=None, current_generation=0):
    """One checked closed-manifold refinement, preserving actual edge ancestry."""
    if mode not in ('INTEGER_COMPAS', 'UNIFORM_FRACTIONAL'):
        raise ValueError("Unknown crease mode.")
    budget = budget or ExecutionBudget(50000, 100000, 48)
    before = inspect_mesh(mesh)
    estimate = dict(estimated_output_vertices=mesh.number_of_vertices() + mesh.number_of_edges() + mesh.number_of_faces(),
        estimated_output_faces=sum(len(mesh.face_vertices(f)) for f in mesh.faces()))
    assessment = check_execution_budget(budget, input_vertices=before['vertex_count'], input_faces=before['face_count'],
        current_generation=current_generation, **estimate)
    if assessment['status'] != 'SAFE':
        raise ValueError("Crease refinement blocked: " + ' '.join(assessment['reasons']))
    if validate_mesh(mesh) or not mesh.is_valid() or not mesh.is_manifold() or not mesh.is_closed():
        raise ValueError("Crease study requires finite nonempty closed valid manifold geometry; no repair.")
    if any(mesh.edge_attribute(e, 'crease') for e in mesh.edges()):
        raise ValueError("Use explicit CreaseNetworks; preexisting implicit crease attributes are unsupported.")
    if not set(fixed) <= set(mesh.vertices()):
        raise ValueError("Unknown fixed vertex.")
    if len({n.network_id for n in networks}) != len(networks):
        raise ValueError("Unique network IDs required.")
    known = {edge_key(e) for e in mesh.edges()}; values = {}
    for net in networks:
        for e in net.edges:
            if e.vertices not in known:
                raise ValueError("Stale crease edge identity.")
            values[e.vertices] = max(values.get(e.vertices, 0.), e.sharpness)
    if mode == 'INTEGER_COMPAS' and any(not v.is_integer() for v in values.values()):
        raise ValueError("Integer reference mode rejects fractional sharpness.")
    cage = mesh.copy()
    integer_path = all(v.is_integer() for v in values.values())
    for e in cage.edges():
        cage.edge_attribute(e, 'crease', int(values.get(edge_key(e), 0.)) if integer_path else 0)
    output = cage.subdivided(scheme='catmullclark', k=1, fixed=list(fixed))
    original = set(mesh.vertices()); edge_points = {}
    for e in mesh.edges():
        key = edge_key(e)
        candidates = (set(output.vertex_neighbors(e[0])) & set(output.vertex_neighbors(e[1]))) - original
        if len(candidates) != 1:
            raise ValueError("Ambiguous structural edge-point correspondence.")
        edge_points[key] = candidates.pop()
    signatures = {frozenset(edge_points[edge_key(e)] for e in mesh.face_halfedges(f)): f for f in mesh.faces()}
    if len(signatures) != mesh.number_of_faces():
        raise ValueError("Ambiguous source face edge cycles.")
    face_points = {}
    for v in set(output.vertices()) - original - set(edge_points.values()):
        f = signatures.get(frozenset(output.vertex_neighbors(v)))
        if f is None or f in face_points:
            raise ValueError("Ambiguous structural face-point correspondence.")
        face_points[f] = v
    xyz = {v: mesh.vertex_coordinates(v) for v in mesh.vertices()}; masks = {}
    if not integer_path:
        for e, s in values.items():
            child = edge_points[e]; smooth = output.vertex_coordinates(child)
            midpoint = [(xyz[e[0]][i] + xyz[e[1]][i]) / 2 for i in range(3)]
            t = min(s, 1.)
            output.vertex_attributes(child, 'xyz', midpoint if t == 1 else [t * midpoint[i] + (1 - t) * smooth[i] for i in range(3)])
        for v in mesh.vertices():
            incident = [(u, values.get(edge_key((v, u)), 0.)) for u in mesh.vertex_neighbors(v)]
            p, masks[v] = fractional_vertex(v, incident, xyz, output.vertex_coordinates(v))
            if v not in fixed:
                output.vertex_attributes(v, 'xyz', p)
    else:
        for v in mesh.vertices():
            active = [u for u in mesh.vertex_neighbors(v) if values.get(edge_key((u, v)), 0.) > 0]
            masks[v] = dict(parent=vertex_rule(active), child=vertex_rule([u for u in active if values[edge_key((u, v))] > 1]), parent_weight=1.)
    # Creases are authoritative explicit data, not hidden mutable Mesh attributes.
    for e in output.edges():
        output.edge_attribute(e, 'crease', 0)
    children = []; propagation = []
    for net in networks:
        rows = []
        for e in net.edges:
            middle = edge_points[e.vertices]
            descendants = [edge_key((e.vertices[0], middle)), edge_key((middle, e.vertices[1]))]
            s = max(e.sharpness - 1, 0.)
            for child in descendants:
                rows.append(CreaseEdge(child, s, e.vertices, e.root_edge, e.parent_cells, e.c0_faces, e.motif_ancestry))
            propagation.append(dict(network_id=net.network_id, parent_edge=list(e.vertices), parent_sharpness=e.sharpness,
                child_edges=[list(c) for c in descendants], child_sharpness=s, generation=net.generation + 1))
        rows.sort(key=lambda e: e.vertices)
        children.append(CreaseNetwork(net.network_id, net.seed_rule_json, tuple(rows), net.generation + 1,
            sum(output.edge_length(e.vertices) for e in rows), net.routing_json))
    sampling = {v: [(v, 1.)] for v in original}
    sampling.update({child: [(v, .5) for v in edge] for edge, child in edge_points.items()})
    sampling.update({child: [(v, 1 / len(mesh.face_vertices(f))) for v in mesh.face_vertices(f)] for f, child in face_points.items()})
    reverse = {v: f for f, v in face_points.items()}; face_point_keys = set(reverse); face_sources = []
    for f in output.faces():
        cycle = set(output.face_vertices(f)); parent = cycle & face_point_keys; corner = cycle & original
        if len(parent) != 1 or len(corner) != 1:
            raise ValueError("Unexpected oriented COMPAS child face cycle.")
        face_sources.append(dict(id=f, source_face=reverse[parent.pop()], source_corner=corner.pop()))
    if validate_mesh(output) or not output.is_valid() or not output.is_manifold() or not output.is_closed():
        raise ValueError("Crease output fails finite/closed manifold contract; no repair.")
    after = inspect_mesh(output)
    if after['vertex_count'] != estimate['estimated_output_vertices'] or after['face_count'] != estimate['estimated_output_faces']:
        raise ValueError("Unexpected refinement counts.")
    return CreaseResult(output, tuple(children), dict(name='Explicit persistent semi-sharp CC', mode=mode,
        finite_uniform_decay='max(s-1,0); overlapping network sharpness uses maximum; no infinite sentinel',
        integer_geometry_delegated_to_COMPAS=integer_path, input=before, output=after, budget=assessment,
        face_sources=face_sources, edge_points=[dict(edge=list(e), point=v) for e, v in edge_points.items()],
        vertex_masks=masks, fixed_vertices=list(fixed), crease_lineage=propagation,
        construction_association='Positive original cage association, separate from crease geometry; generic semantic inheritance NOT IMPLEMENTED.'), sampling)
