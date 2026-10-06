"""Source-graph scalar activity, separate from weights and geometry.

Positive sampling parents are control-cage associations. They do not claim
to explain signed experimental geometry or supply architectural semantics.
"""
from collections import deque
from dataclasses import dataclass
from math import fsum, isfinite, log
from types import MappingProxyType


def unit(value):
    if type(value) not in (int, float) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Activity must be a finite real number in [0, 1].")
    return float(value)


def source_graph(mesh):
    return {v: tuple(sorted(mesh.vertex_neighbors(v))) for v in sorted(mesh.vertices())}


def distances(graph, seeds):
    seeds = tuple(sorted(set(seeds)))
    if not seeds or set(seeds)-set(graph):
        raise ValueError("Seeds must be nonempty existing source IDs.")
    result = {v: None for v in graph}
    queue = deque(seeds)
    for v in seeds:
        result[v] = 0
    while queue:
        v = queue.popleft()
        for n in graph[v]:
            if result[n] is None:
                result[n] = result[v]+1
                queue.append(n)
    return result


def distance_values(graph, seeds, *, radius=3.0):
    if type(radius) not in (int, float) or not isfinite(radius) or radius <= 0:
        raise ValueError("Distance radius must be finite and positive.")
    return {v: None if d is None else max(0.0, 1-d/radius)
            for v, d in distances(graph, seeds).items()}


def diffuse(graph, initial, *, rate=0.5, iterations=1):
    rate = unit(rate)
    if type(iterations) is not int or iterations < 0 or set(initial) != set(graph):
        raise ValueError("Diffusion needs full source coverage and nonnegative integer iterations.")
    values = {v: unit(initial[v]) for v in sorted(graph)}
    for _ in range(iterations):
        values = {v: (1-rate)*values[v]+rate*fsum(values[n] for n in graph[v])/len(graph[v])
                  if graph[v] else values[v] for v in values}
    return values


def peak_normalize(values):
    maximum = max(values.values(), default=0)
    return {v: value/maximum if maximum else 0.0 for v, value in values.items()}


def field_statistics(values, seed_distances=None):
    present = [value for value in values.values() if value is not None]
    if not present:
        return dict(available=0, unavailable=len(values))
    total = fsum(present); average = total/len(present)
    return dict(available=len(present), unavailable=len(values)-len(present),
        min=min(present), max=max(present), mean=average,
        variance=fsum((v-average)**2 for v in present)/len(present),
        entropy_normalized=(-fsum(v/total*log(v/total) for v in present if v > 0)/log(len(present)))
            if total and len(present)>1 else 0.0,
        effective_fraction=(total*total/(len(present)*fsum(v*v for v in present))) if total else 0.0,
        distance_weighted_spread=(fsum(value*seed_distances[v] for v, value in values.items()
            if value is not None and seed_distances[v] is not None)/total)
            if total and seed_distances is not None else None)


def inherit_values(values, parents):
    """Existing positive parents only; missing source values remain None."""
    result = {}
    for child, refs in parents.items():
        pairs = [(ref.key, ref.weight) if hasattr(ref, "key") else ref for ref in refs]
        if not pairs or any(type(w) not in (int, float) or not isfinite(w) or w < 0 for _, w in pairs) or abs(fsum(w for _, w in pairs)-1)>1e-9:
            raise ValueError("Activity inheritance requires normalized nonnegative parents.")
        if any(p not in values or values[p] is None for p, w in pairs if w > 0):
            result[child] = None
        else:
            value = fsum(w*unit(values[p]) for p, w in pairs if w > 0)
            # Only floating point roundoff of a validated convex combination.
            result[child] = min(1.0, max(0.0, value))
    return result


def lerp_weight(quiet, active, phi):
    phi = unit(phi)
    if any(type(w) not in (int, float) or not isfinite(w) for w in (quiet, active)):
        raise ValueError("Weights must be finite real numbers.")
    if phi == 1:
        return active  # Exact original arithmetic path, without cancellation.
    if phi == 0:
        return quiet
    return quiet+(active-quiet)*phi


def scale_at(strategy, generation):
    if type(generation) is not int or generation < 1:
        raise ValueError("Activity is assigned to positive integer generations.")
    phase = 0 if generation == 1 else 1 if generation <= 3 else 2
    schedules = {"U": ("UNIFORM",)*3, "S": ("MEDIUM",)*3,
        "M": ("BROAD", "MEDIUM", "FINE"), "R": ("FINE", "MEDIUM", "BROAD"),
        "P": ("MEDIUM", "FINE", "BROAD"), "D": ("DISTANCE",)*3}
    if strategy not in schedules:
        raise ValueError("Unknown activity control.")
    return schedules[strategy][phase]


@dataclass(frozen=True)
class ActivityField:
    name: str
    values: dict

    def __post_init__(self):
        object.__setattr__(self, "values", MappingProxyType({v: None if x is None else unit(x) for v, x in self.values.items()}))

    def vertex(self, key):
        return self.values.get(key)

    def face(self, mesh, key):
        values = [self.vertex(v) for v in mesh.face_vertices(key)]
        return None if any(v is None for v in values) else fsum(values)/len(values)

    def edge(self, edge):
        values = [self.vertex(v) for v in edge]
        return None if any(v is None for v in values) else fsum(values)/2

    def inherited(self, parents):
        return ActivityField(self.name, inherit_values(self.values, parents))
