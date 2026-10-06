"""Bounded transverse-crossing audit using COMPAS's line/triangle query.

Quads split only for this diagnostic approximation, never in delivered meshes.
Coplanar overlaps, adjacent faces and the full collision problem are excluded.
"""
import argparse
from itertools import combinations, product
import json
from math import floor, dist
from pathlib import Path
from time import perf_counter
from compas.geometry import intersection_line_triangle, is_point_on_segment, closest_point_on_segment

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
args = parser.parse_args()
response = json.loads((args.run / "response.json").read_text())
request = json.loads((args.run / "request.json").read_text())
source = [row["xyz"] for row in request["mesh"]["vertices"]]
scale = max(max(p[a] for p in source) - min(p[a] for p in source) for a in range(3))
cell, epsilon = scale / 24, scale * 1e-8
report = {"method": "COMPAS intersection_line_triangle with segment bounds; diagnostic-only fan triangulation of quads",
          "scope": "Up to 30 non-adjacent transverse crossings per candidate; excludes adjacent/coplanar contacts. NOT a global collision certificate.", "candidates": []}
for variant in response["variants"]:
    start = perf_counter()
    xyz = {row["id"]: row["xyz"] for row in variant["mesh"]["vertices"]}
    faces, cells, pairs = {}, {}, set()
    for face in variant["mesh"]["faces"]:
        points = [xyz[k] for k in face["vertices"]]
        low = [min(p[a] for p in points) for a in range(3)]
        high = [max(p[a] for p in points) for a in range(3)]
        faces[face["id"]] = (set(face["vertices"]), points, low, high)
        for index in product(*(range(floor(low[a] / cell), floor(high[a] / cell) + 1) for a in range(3))):
            cells.setdefault(index, []).append(face["id"])
    for keys in cells.values():
        pairs.update(tuple(sorted(pair)) for pair in combinations(keys, 2))
    contacts, checked = [], 0
    for a, b in sorted(pairs):
        keys_a, points_a, low_a, high_a = faces[a]
        keys_b, points_b, low_b, high_b = faces[b]
        if keys_a & keys_b or any(high_a[i] < low_b[i] - epsilon or high_b[i] < low_a[i] - epsilon for i in range(3)):
            continue
        checked += 1
        hit = None
        for p, q in ((points_a, points_b), (points_b, points_a)):
            for u, v in zip(p, p[1:] + p[:1]):
                for index in range(1, len(q) - 1):
                    triangle = [q[0], q[index], q[index + 1]]
                    contact = intersection_line_triangle([u, v], triangle)
                    if contact is not None and is_point_on_segment(contact, [u, v], tol=epsilon) and min(dist(contact, u), dist(contact, v)) > epsilon and all(dist(contact, closest_point_on_segment(contact, [a, b])) > epsilon for a, b in zip(triangle, triangle[1:] + triangle[:1])):
                        hit = list(contact)
                        break
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is not None:
            contacts.append({"faces": [a, b], "point": hit})
        if len(contacts) == 30:
            break
    record = {"id": variant["id"], "sampled_transverse_crossings": len(contacts), "sample_limit_reached": len(contacts) == 30,
              "checked_nonadjacent_pairs": checked, "contacts": contacts, "elapsed_seconds": perf_counter() - start}
    report["candidates"].append(record)
    print(record["id"], "sample crossings", len(contacts), "checked pairs", checked, "seconds", record["elapsed_seconds"])
(args.run / "crossing_audit.json").write_text(json.dumps(report, indent=2) + "\n")
