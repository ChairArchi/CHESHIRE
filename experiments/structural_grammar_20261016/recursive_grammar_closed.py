"""Five irregularly clustered free-tip cut-reflected returns, with blind webs.

This bounded fork preserves recursive_grammar.py's diagnostic. No daughter
connectors or returning-tip-to-stem bridges are used. Every local reflection
is backed continuously along its actual cut plane before the column union.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE=Path(__file__).resolve().parent


def _load(name,path):
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _backed_unit(kernel, base, plane_normal):
    curve,lateral,width,thickness=base
    n=np.asarray(plane_normal,float);n/=np.linalg.norm(n)
    tangent=kernel.unit(np.gradient(curve,axis=0))
    lat=lateral-(lateral*tangent).sum(1)[:,None]*tangent
    lat=kernel.unit(lat);normal=kernel.unit(np.cross(tangent,lat))
    # Find each exact cross-section/plane intersection on the sheet interior.
    # The web follows the actual folded middle surface, not a height projection.
    roots=[]
    for c,L,N,w in zip(curve,lat,normal,width):
        a=.13*np.dot(N,n);b=w*np.dot(L,n);d=np.dot(c,n)
        candidates=np.roots([a,b,d]) if abs(a)>1e-13 else [-d/b]
        valid=[float(np.real(u)) for u in candidates
               if abs(np.imag(u))<1e-9 and abs(np.real(u))<=1.+1e-9]
        if not valid:raise ValueError("Reflection plane leaves the folded strip interior.")
        roots.append(min(valid,key=abs))
    u=np.asarray(roots)
    intersection=curve+u[:,None]*width[:,None]*lat+.13*u[:,None]**2*normal
    raw=kernel.loft_closed_ribbon(curve,width,thickness,lateral,
                                  across_curvature=.13,samples_across=8)
    reflected=kernel.cut_reflect_union(raw,n,point=(0.,0.,0.))
    web=kernel.loft_closed_tube(intersection,.071,sides=10)
    md=kernel.manifold_module();x,t=reflected
    solid=md.Manifold(md.Mesh64(np.ascontiguousarray(x),np.ascontiguousarray(t,dtype=np.uint64)))
    solid=solid+kernel.to_manifold(*web)
    volume=solid.volume();solid=solid.simplify(1e-8)
    if len(solid.decompose())!=1 or solid.genus()!=0:
        raise ValueError("A backed reflection unit must be one genus-zero solid.")
    mesh=kernel.from_manifold(solid);kernel.orient(*mesh)
    return mesh,dict(normal=n.tolist(),point=[0.,0.,0.],
        actual_positive_trim_and_reflect=True,backing="Continuous actual cross-section/plane web",
        backing_radius=.071,unit_components=1,unit_genus=0,
        cleanup_tolerance=1e-8,cleanup_volume_delta=float(solid.volume()-volume),
        free_tip_not_reattached=True)


def build_components(recipe=None):
    cfg=dict(height=10.,samples=21,
        origins=[1.12,1.93,3.68,8.25,9.12],
        angles_degrees=[24.,129.,-37.,72.,226.],
        local_scales=[[.58,.65,.64],[.48,.60,.56],[1.30,1.05,3.15],
                      [.35,.45,.48],[.28,.40,.40]],
        planes=[[0.,1.,0.],[.08,1.,.06],[-.03,1.,.08]])
    cfg.update(recipe or {})
    if not (len(cfg["origins"])==len(cfg["angles_degrees"])==len(cfg["local_scales"])==5):
        raise ValueError("This bounded grammar declares two low, one giant middle and two high returns.")
    previous=_load("recursive_grammar_preserved_helpers",HERE/"recursive_grammar.py")
    k=previous._kernel()
    base=previous._return_curve(int(cfg["samples"]))
    units=[_backed_unit(k,base,n) for n in cfg["planes"]]
    t=np.linspace(0.,1.,45)
    spine=np.column_stack((.13*np.sin(1.4*np.pi*t),.09*np.sin(2*np.pi*t),cfg["height"]*t))
    sx,st=k.loft_closed_tube(spine,.30+.045*np.sin(np.pi*t)**2,sides=14)
    parts=[dict(name="continuous_new_spine",xyz=sx,faces=st,role="core",level=0)]
    events=[]
    for i,(height,angle,scale) in enumerate(zip(cfg["origins"],cfg["angles_degrees"],cfg["local_scales"])):
        level=0 if i<2 else 1 if i==2 else 2
        frame=previous._basis(np.deg2rad(angle),0.)
        origin=np.array([.13*np.sin(1.4*np.pi*height/cfg["height"]),
                         .09*np.sin(2*np.pi*height/cfg["height"]),height])
        unit,operator=units[level];x,f=unit
        points=previous._map(x,frame,origin,np.asarray(scale))
        parts.append(dict(name=f"closed_return_{i+1}",xyz=points,faces=f,
                          role="primary_return",level=level+1))
        events.append(dict(event=i+1,origin=origin.tolist(),frame=frame.tolist(),
            positive_affine_scale=scale,operator=operator,
            actual_height_range=[float(points[:,2].min()),float(points[:,2].max())]))
    return parts,dict(schema="CHESHIRE_CLOSED_IRREGULAR_MULTI_PLANE_RETURN_GRAMMAR_V1",
        recipe=cfg,events=events,source_parts=len(parts),
        input_triangles=sum(len(p["faces"]) for p in parts),
        historical_column_or_chart_used=False,global_XY_symmetry_imposed=False,
        actual_cut_reflection=True,unit_genus_zero_verified=True,
        final_union_genus_zero_must_be_verified_by_caller=True,
        late_ornament_added=False,visual_success="PENDING_ACTUAL_RENDER",
        fabrication_certified=False)


build=build_components
