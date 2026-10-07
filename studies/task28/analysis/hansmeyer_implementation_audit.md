# Task28 implementation audit

Audit before new parameters: existing weighted_subdivision, generational_subdivision, sharp_subdivision, creases, crease_folding, fold_continuation, prior Mola compatibility and Task20–27 studies. No equation is rewritten for the initial benchmark.

Reference check: Hansmeyer, Design by Subdivision (Bridges2010), primary text pp168–170: https://archive.bridgesmathart.org/2010/bridges2010-167.pdf . It identifies weighted point interpolation, normal extrusion, previous point classes, nonstationary/nonuniform parameters and motif attraction. Primary text was accessible; screenshots were unavailable. Subdivision Beyond Smoothness publisher fetch failed. Existing local equation notes remain distinguished from complete source algorithm reconstruction.

## Confirmed current machinery

* Topology: COMPAS 2.15.1 Catmull-Clark, k children per input k-gon; triangle/quad input. Weighted operator preserves its connectivity. Pure zero-weight closed outputs match standard CC.
* Eq1 face centroid plus wf*unit face normal.
* Eq2 edge: ((C1+C2)*(1+w1)+(P1+P2)*(1-w1))/4 + we*mean incident unit normals. Current code uses ORIGINAL input face centroids, not the already displaced same-generation face points.
* Eq3 corner: (F*(1+w2)+E*(2-w2)+P*(valence-3))/valence + wp*normalized incident normal mean. Current code uses input face centers and input edge midpoints. Same-generation face/edge extrusion is deliberately isolated rather than propagated into Eq2/Eq3. This is a documented CHESHIRE subset convention; the benchmark must not claim complete reproduction of every published processing interpretation.
* Eq4 later face: ((V*(1+w3)+F*(1-w3))*(1+w4)+(E1+E2)*(1-w4))/4 + wf*n. Only actual preceding CC corner/face/edge/edge origins, checked for parent-edge incidence and generation. G1 falls back to Eq1. Negative geometric coefficients are allowed; semantic ancestry remains positive and separate.
* Point classes: VERTEX_DERIVED, EDGE_DERIVED, FACE_DERIVED are actually implemented, regenerated each call and serializable.
* Literal Eq10: face_base + w6*SUM[(input_corner-face_base)*u(corner)]. Eq11: edge_base + w7*SUM[(input_endpoint-edge_base)*u(endpoint)]. Unnormalized sums; actual motif signature (valence, incident_faces). Inputs are original current mesh points. Tagging corner locks, intrinsic source distance and current normal-variation interpolation also exist.
* Nonstationary schedules: existing compile_schedule supports explicit finite DISCRETE rows and Eq7 a+b*(i-1)^q. No noise is needed. Each call already accepts global and local point-class numeric overrides. Weight schedules and scalar interpolation are CHESHIRE experiments, not published reference recipes.
* Creases: genuine finite integer COMPAS crease masks and separately reconstructed fractional Uniform masks, plus explicit ordered graph correspondence. Weighted/sharp subset rejects nonzero interior creases; a separate crease_folding wrapper composes reference crease geometry with the relative sharp operator displacement. This wrapper is a CHESHIRE addition. Initial Task28 global benchmark uses no crease network or route.
* Boundary: fixed naked corners, exact naked-edge midpoints and zero boundary extrusion are the existing CHESHIRE policy. Lead benchmark will use a closed specimen.
* Mola: installed optional official HDMola CatmullClark compatibility and verified Taper/Frame/Roof events exist. Events are distinct topology operators; they are not Hansmeyer modified CC. They contributed to prior C07/H1, but will not be used to rescue the initial subdivision-only benchmark.
* Missing scope: no exact complete Digital Grotesque algorithm, general geometric collision repair, general motif merging / threshold welding, adaptive topology or generic ornament grammar. Current motif classes mostly become valence4; extreme signed placement can produce intersections without changing graph validity.

## Recovered causes worth testing

C11's first two global rows, retained by Task20/21 and traced by Task25, are aggressive relative normal displacement plus edge/corner weighting, followed by prior-class Eq4. Task22 C26's w2=-2.8 with w6=.25/w7=.65 and u3=1/u4=-.2 retains angular structure. Task24 H1 macro uses absolute wf/we/wp=-280/320/520, w1=.8, w2=-2.8, w6=-.9, w7=.8. Task25 zero-offset -0.18/-0.3/-0.9/.5 is a later-curvature seed; simply amplifying -3/1.5 was not sufficient. Test exact numbers first, then a bounded nonstationary combination on one simple input.
