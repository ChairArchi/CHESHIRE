"""Individually inspectable comparative diagnostics, without an aesthetic score."""
from itertools import combinations
from math import acos, dist, fsum, pi
from statistics import median

from .activity import field_statistics
from .attributes import _curvature, _face_normal


def distribution(values):
    values = sorted(values)
    if not values:
        return dict(available=0)
    average = fsum(values)/len(values); total = fsum(values)
    count = max(1, (len(values)+9)//10)
    return dict(available=len(values), mean=average, median=median(values), max=max(values),
        variance=fsum((v-average)**2 for v in values)/len(values),
        top_decile_mass_fraction=fsum(values[-count:])/total if total else 0.0,
        percentile_80=values[int(.8*(len(values)-1))],
        percentile_95=values[int(.95*(len(values)-1))])


def hierarchy_diagnostics(previous, mesh, parents, seed_channels, *, previous_active=None, sample_limit=1024):
    # This is movement from the documented positive sampling cage, rather
    # than distance from an assumed corresponding vertex across topology.
    movement = {}
    for v, refs in parents.items():
        pairs = [(r.key, r.weight) if hasattr(r, "key") else r for r in refs]
        reference = [fsum(previous.vertex_coordinates(p)[axis]*w for p, w in pairs) for axis in range(3)]
        movement[v] = dist(mesh.vertex_coordinates(v), reference)
    face_activity = {f: fsum(movement[v] for v in mesh.face_vertices(f))/len(mesh.face_vertices(f)) for f in mesh.faces()}
    ordered = sorted(face_activity.values()); threshold = ordered[int(.8*(len(ordered)-1))]
    active = {f for f, value in face_activity.items() if value >= threshold and value > 0}
    remaining = set(active); patches = []
    while remaining:
        todo = [min(remaining)]; remaining.remove(todo[0]); count = 0
        while todo:
            f = todo.pop(); count += 1
            for n in mesh.face_neighbors(f):
                if n in remaining:
                    remaining.remove(n); todo.append(n)
        patches.append(count)
    source_support = {channel: fsum(fsum(values[v] for v in mesh.face_vertices(f))/len(mesh.face_vertices(f)) for f in active)/len(active)
                      if active else None for channel, values in seed_channels.items()}
    # Seed indicator channels inherited through the same positive parents
    # make source-region persistence identifiable without geometric guessing.
    present = sorted(k for k, value in source_support.items() if value is not None and value > .01)
    normal = {f: _face_normal(mesh, f) for f in mesh.faces()}
    vertices = list(mesh.vertices()); sampled = vertices if len(vertices) <= sample_limit else [vertices[i*len(vertices)//sample_limit] for i in range(sample_limit)]
    variation = {1: [], 2: []}; missing = {1: 0, 2: 0}
    for v in sampled:
        first = _curvature(mesh, v, mesh.vertex_neighbors(v), mesh.is_vertex_on_boundary(v), normal)
        if first is None:
            missing[1] += 1
        else:
            variation[1].append(first)
        neighborhood = {f for vertex in [v, *mesh.vertex_neighbors(v)] for f in mesh.vertex_faces(vertex)}
        if len(neighborhood) < 2 or any(normal[f] is None for f in neighborhood):
            missing[2] += 1
        else:
            angles = [acos(min(1.0, max(-1.0, fsum(a*b for a, b in zip(normal[f], normal[g])))))/pi
                      for f, g in combinations(sorted(neighborhood), 2)]
            variation[2].append(fsum(angles)/len(angles))
    record = dict(displacement=distribution(movement.values()),
        displacement_reference="Positive immediate control-cage sampling position; not excess over standard subdivision or a curvature spectrum",
        spatial_concentration=field_statistics(face_activity),
        active_patches=dict(percentile=80, threshold=threshold, count=len(patches),
            face_counts=sorted(patches, reverse=True), active_face_count=len(active),
            active_face_fraction=len(active)/len(face_activity),
            largest_patch_fraction=max(patches, default=0)/len(face_activity),
            ties_included=True),
        normal_variation={f"radius_{r}": {**distribution(variation[r]), "unavailable": missing[r]} for r in (1, 2)},
        normal_variation_scope="Fixed evenly spaced vertex sample up to 1024; existing mean pairwise incident-normal angle/pi, then incident faces of one vertex-neighbor ring",
        persistence=dict(source_seed_support=source_support, represented_source_regions=present,
            previous_source_regions=previous_active,
            retained_previous_regions=sorted(set(previous_active or []) & set(present)),
            note="Coarse source-seed support in top-displacement faces, not proof of geometrically nested patches"))
    return record, present
