"""New closed macro grammar: nested returns across changing local planes.

No historical column coordinates, material chart or fixed X/Y mirror maps are
used. Each tier creates folded ribbon solids, actually cuts and reflects them,
then grows smaller returns from their retained positive-side interior. The
caller performs the final union and true subdivision generations.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent


def _kernel():
    path = HERE / "grammar_kernel.py"
    name = "recursive_grammar_actual_csg_kernel"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _basis(angle, tilt=0.):
    """Proper local frame; local Z leans in the radial U direction."""
    u = np.array([np.cos(angle), np.sin(angle), 0.])
    v = np.array([-np.sin(angle), np.cos(angle), 0.])
    z = np.array([0., 0., 1.])
    return np.column_stack((np.cos(tilt)*u-np.sin(tilt)*z,
                            v, np.sin(tilt)*u+np.cos(tilt)*z))


def _return_curve(samples=25):
    """A broad curved leaf returns down/out; it is not a straight extrusion."""
    t = np.linspace(0., 1., samples)
    angle=2.40*t
    # Elliptic arc has no vanishing-speed hairpin. Its radius exceeds the
    # finite sheet thickness; the tip still returns downward after pi/2.
    curve = np.column_stack((1.02*(1.-np.cos(angle)),
                             .14*np.sin(1.4*np.pi*t),
                             .96*np.sin(angle)))
    lateral = np.column_stack((-.08*np.sin(np.pi*t), np.ones_like(t),
                               .16*np.sin(1.5*np.pi*t)))
    lateral /= np.linalg.norm(lateral,axis=1)[:,None]
    width = .58*(.68+.44*np.sin(np.pi*t))*(1.-.48*t**3)
    thickness = .12*(1.-.42*t)
    return curve, lateral, width, thickness


def _map(xyz, frame, origin, scale):
    return (np.asarray(xyz)*np.asarray(scale)) @ frame.T + np.asarray(origin)


def _clean_csg_numerics(kernel, mesh, tolerance=1e-8):
    """Simplify own valid CSG output's coplanar slivers at explicit tolerance."""
    md = kernel.manifold_module()
    xyz,tri = mesh
    solid = md.Manifold(md.Mesh64(np.ascontiguousarray(xyz,dtype=np.float64),
                                 np.ascontiguousarray(tri,dtype=np.uint64)))
    if str(solid.status()) != "Error.NoError":
        raise ValueError("Cut-reflection did not produce a valid solid.")
    cleaned = solid.simplify(float(tolerance))
    out = kernel.from_manifold(cleaned)
    kernel.orient(*out)  # Keep the original strict positive-area threshold.
    if cleaned.genus()!=solid.genus():
        raise ValueError("Numerical cleanup changed source topology.")
    return out,dict(operation="Manifold.simplify on valid actual CSG result",
        tolerance=float(tolerance),input_triangles=len(tri),output_triangles=len(out[1]),
        genus_before=int(solid.genus()),genus_after=int(cleaned.genus()),
        volume_change=float(cleaned.volume()-solid.volume()),
        strict_input_area_gate_retained=True)


def build(recipe=None):
    """Return (closed CSG input parts, explicit constructive metadata).

    The default 2/3/5 tier grammar has a slender continuous spine. Main and
    daughter return solids are connected geometrically by actual joint solids.
    There is no late ornament or mature-column displacement in this model.
    """
    cfg = dict(tier_counts=[2,3,5], tier_heights=[1.55,5.15,8.7],
               tier_angles_degrees=[18.,-43.,79.],
               tier_scales=[.68,1.35,.44], spine_height=10.,
               branch_heights=[[1.25,1.85],[3.75,5.15,6.5],
                               [8.15,8.35,8.75,8.85,9.1]],
               branch_scale_factors=[[1.,.82],[1.,.72,.56],[.85,1.,.70,.88,.62]],
               branch_angle_offsets_degrees=[[0.,74.],[0.,117.,242.],
                                             [0.,57.,131.,216.,278.]],
               tier_axis_stretch=[[1.,.90,1.],[1.,1.,2.1],[.90,1.,.90]],
               primary_samples=21, daughter_scale=.46)
    cfg.update(recipe or {})
    if not (len(cfg["tier_counts"]) == len(cfg["tier_heights"]) ==
            len(cfg["tier_angles_degrees"]) == len(cfg["tier_scales"])):
        raise ValueError("Each grammar tier needs count, height, axis and scale.")
    if any(int(n)!=n or not 1<=n<=6 for n in cfg["tier_counts"]):
        raise ValueError("One to six explicit macro returns per tier required.")
    for key in ("branch_heights","branch_scale_factors","branch_angle_offsets_degrees"):
        if len(cfg[key])!=len(cfg["tier_counts"]) or any(
                len(row)!=int(n) for row,n in zip(cfg[key],cfg["tier_counts"])):
            raise ValueError("Explicit irregular per-branch values must match each tier count: "+key)
    k = _kernel()
    parts, operations = [], []

    def add(name, mesh, role, **formation):
        xyz, tri = map(np.asarray, mesh)
        if xyz.ndim!=2 or xyz.shape[1]!=3 or tri.ndim!=2 or tri.shape[1]!=3:
            raise ValueError("Closed actual triangle solids required.")
        if not np.isfinite(xyz).all():
            raise ValueError("Nonfinite actual grammar coordinates.")
        parts.append(dict(name=name,xyz=xyz,faces=tri,role=role,
                          level=int(formation.get("tier",0))))
        operations.append(dict(name=name,role=role,vertices=len(xyz),
                               triangles=len(tri),**formation))

    t = np.linspace(0.,1.,45)
    spine = np.column_stack((.14*np.sin(1.7*np.pi*t),
                              .10*np.sin(2.1*np.pi*t+.2)-.10*np.sin(.2),
                              cfg["spine_height"]*t))
    radii = .30+.10*np.sin(np.pi*t)**2+.025*np.cos(5*np.pi*t)
    add("continuous_spine", k.loft_closed_tube(spine,radii,sides=14),
        "core", construction="New gently curved closed spine; no historical seed")

    curve,lateral,width,thickness = _return_curve(int(cfg["primary_samples"]))
    unit = k.loft_closed_ribbon(curve,width,thickness,lateral,
                               across_curvature=.13,samples_across=8)
    primary_normal = np.array([1.,.19,.12])
    primary_point = np.array([.10,0.,.16])
    folded = k.cut_reflect_union(unit,primary_normal,point=primary_point)
    # A second actual cut/reflection gives daughters a different fold axis.
    daughter_normal = np.array([.25,1.,.16])
    daughter_point = np.array([.44,0.,.42])
    daughter,cleanup = _clean_csg_numerics(k,
        k.cut_reflect_union(unit,daughter_normal,point=daughter_point))
    positive_anchor = curve[int(.57*(len(curve)-1))]
    for tier,(count,height,phase,scale) in enumerate(zip(cfg["tier_counts"],
            cfg["tier_heights"],cfg["tier_angles_degrees"],cfg["tier_scales"])):
        for branch in range(int(count)):
            actual_height=float(cfg["branch_heights"][tier][branch])
            centre=np.array([.14*np.sin(1.7*np.pi*actual_height/cfg["spine_height"]),
                .10*np.sin(2.1*np.pi*actual_height/cfg["spine_height"]+.2)-.10*np.sin(.2),actual_height])
            angle = np.deg2rad(phase+cfg["branch_angle_offsets_degrees"][tier][branch])
            branch_scale=scale*cfg["branch_scale_factors"][tier][branch]
            stretch=np.asarray(cfg["tier_axis_stretch"][tier],float)
            # Changing tilt, handedness and tier count changes connectivity
            # and fold origins; it is not the old unit with a larger amplitude.
            tilt = np.deg2rad((12 if branch%2==0 else -9)+6*tier)
            frame = _basis(angle,tilt)
            origin = centre + .06*frame[:,0]
            x,f = folded
            world_n=frame@(primary_normal/stretch)
            world_n/=np.linalg.norm(world_n)
            add(f"tier_{tier+1}_return_{branch+1}",(_map(x,frame,origin,branch_scale*stretch),f),
                "primary_return",tier=tier+1,parent="continuous_spine",
                local_axis_frame=frame.tolist(),origin=origin.tolist(),scale=branch_scale,
                local_axis_stretch=stretch.tolist(),
                actual_cut_reflect_plane=dict(normal=primary_normal.tolist(),point=primary_point.tolist(),
                    world_normal=world_n.tolist(),world_point=_map(primary_point,frame,origin,branch_scale*stretch).tolist()))
            anchor = _map(positive_anchor,frame,origin,branch_scale*stretch)
            child_frame = _basis(angle+(-.63 if branch%2 else .73),tilt+.22)
            child_scale = branch_scale*float(cfg["daughter_scale"])
            child_stretch=np.sqrt(stretch)
            x,f = daughter
            world_n=child_frame@(daughter_normal/child_stretch)
            world_n/=np.linalg.norm(world_n)
            add(f"tier_{tier+1}_daughter_{branch+1}",
                (_map(x,child_frame,anchor,child_scale*child_stretch),f),"nested_return",
                tier=tier+1,parent=f"tier_{tier+1}_return_{branch+1}",
                local_axis_frame=child_frame.tolist(),origin=anchor.tolist(),scale=child_scale,
                local_axis_stretch=child_stretch.tolist(),
                actual_cut_reflect_plane=dict(normal=daughter_normal.tolist(),point=daughter_point.tolist(),
                    world_normal=world_n.tolist(),world_point=_map(daughter_point,child_frame,anchor,child_scale*child_stretch).tolist()))
            # The joint overlaps both retained ribbons; it is explicit CSG,
            # not an assertion based only on a touching point.
            # End inside the known retained positive-half ribbon, rather than
            # at the clipping plane where a zero-area touch can disconnect.
            connection=np.stack((anchor,
                _map(curve[int(.30*(len(curve)-1))],child_frame,anchor,child_scale*child_stretch),
                _map(positive_anchor,child_frame,anchor,child_scale*child_stretch)))
            add(f"tier_{tier+1}_joint_{branch+1}",
                k.loft_closed_tube(connection,.065*branch_scale,sides=10),"structural_joint",
                parent=f"tier_{tier+1}_return_{branch+1}")
    total=sum(len(p["faces"]) for p in parts)
    if total>30000:
        raise ValueError("Bounded coarse grammar input budget exceeded.")
    return parts,dict(schema="CHESHIRE_RECURSIVE_MULTI_PLANE_MACRO_GRAMMAR_V1",
        recipe=cfg,operations=operations,input_triangles=total,
        actual_local_cut_reflection=True,global_XY_symmetry_imposed=False,
        historical_column_or_chart_used=False,late_ornament_added=False,
        requested_primary_returns=sum(cfg["tier_counts"]),
        requested_nested_returns=sum(cfg["tier_counts"]),
        daughter_CSG_numerical_cleanup=cleanup,
        final_union_and_subdivision_owned_by_caller=True,
        prototype_scope="Initial macro grammar comparison; not a final printable closed-blind-pocket model.",
        zero_handle_guarantee=False,
        global_union_genus_must_be_measured=True,
        visual_success="PENDING_ACTUAL_RENDER",fabrication_certified=False)


build_components = build
