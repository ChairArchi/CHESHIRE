# B: one parallel projection, two separate geometries

- Orphan branch `research/input-target-poc`.
- Worktree `C:/Users/USER/CHESHIRE/cleanroom/input-target`.
- Generation: `src/projection.py`; execution: `run_checkpoint.py`.
- No CC, DS, extrusion or recursive symmetry operations.

## Exact geometries

INPUT: planar rectangular frame at y=-2.5. Outer x in [-1.1,1.1],
z in [-1.8,1.8]. Central opening x in [-0.55,0.55], z in [-0.9,0.9].
17x17 regular grid before unused interior points are removed: 240 retained
vertices and 192 quads. This is only sampling for projection, not recursive
subdivision. One connected annular surface; two boundary loops.

TARGET: independent capped 32-sided elliptical prism. Vertex coordinates
(1.4*cos(2*pi*k/32),0.9*sin(2*pi*k/32),z), k=0..31, z=-2.2 or 2.2.
64 vertices, 32 side quads and two polygon caps; solid boundary, no opening.
Neither object is built by modifying the other.

## Operation stated before implementation

For each input point p, cast a ray p+t*d, d=(0,1,0). Select the nearest
nonnegative intersection with the actual triangulated TARGET mesh.
Set OUTPUT vertex to that intersection; retain INPUT face connectivity.
Missing intersections are errors. The target is not used merely as a
bounding box: actual target triangle coordinates determine every hit.
Moller-Trumbore intersection is implemented directly in `project()`.

The output is an open frame-shaped surface on the target's front side.
Every vertex is on a target triangle; faces linearly connect the samples
and approximate the piecewise planar target where a sampling strip crosses
a target crease. This is not a Boolean perforation of the solid.

## Relationship to supplied papers

Bader/Oxman, attached `C:/Users/USER/Downloads/mirror.pdf`, section 2,
describes recursive cut/mirror/union and a distinct target-envelope fitting
example in Fig. 6. This deliberately smaller ray-projection POC is the
requested independent interpretation, **not** a replication of that method
or its target optimization. No such claim is made. Hansmeyer rules are not
part of B. Other attached architecture/material papers supply no projection
equation used here.
