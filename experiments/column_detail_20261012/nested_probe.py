"""Selected smaller-scale E/F relief on the preserved OVERLAP G3 column.

Existing role_growth.edge_face uses input-cell support scale, held old V,
shared midpoint/face-centre refinement and normal offsets. No Mandelbulb
pass, new authored macro fold, global absolute-depth growth or XYZ smoothing.
Local detail pass 1/2 corresponds to global generation G4/G5, respectively.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]/'src'))
sys.path.insert(0, str(HERE.parent/'fold_band_growth_20261011'))
sys.path.insert(0, str(HERE.parent/'directional_growth_20261012'))
import role_growth as roles
import overlap_probe as overlap
from cheshire.reference_subdivision import ArrayMesh

prior = roles.prior
ancestry = overlap.ancestry
SOURCE = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
ALGORITHM = 'EXISTING_EDGE_FACE_LOCAL_NESTED_DETAIL_V1'
GUIDE_SPECS = [
    dict(name='LOWER_RETURN_LIP', height=.39, axial_halfwidth=.105, direction=.35, sweep=.28),
    dict(name='UPPER_RETURN_SHOULDER', height=.61, axial_halfwidth=.105, direction=1.18, sweep=.28),
]
RANGES = (.34, .24)
BUDGETS = (.04, .025)
STRONG_BUDGETS = (.09, .06)
CORE_INNER = .018
CORE_OUTER = .06


def smoothstep(t):
    t = np.clip(t, 0., 1.)
    return t*t*(3.-2.*t)


def legacy_guides(mesh, chart):
    canonical = chart.copy()
    canonical[:, 1:] = np.abs(canonical[:, 1:])
    theta = np.arctan2(canonical[:, 2], canonical[:, 1])
    tree = cKDTree(np.column_stack([canonical[:, 0], theta/(np.pi/2)]))
    guides=[]
    for spec in GUIDE_SPECS:
        height = np.linspace(spec['height']-spec['axial_halfwidth'], spec['height']+spec['axial_halfwidth'], 65)
        angle = spec['direction']+spec['sweep']*np.sin(np.pi*(height-spec['height'])/.32)
        _, indices=tree.query(np.column_stack([height,angle/(np.pi/2)]))
        keep=np.r_[True,indices[1:]!=indices[:-1]]
        indices=indices[keep]
        points=mesh.xyz[indices].copy()
        points[:,:2]=np.abs(points[:,:2])
        keep=np.r_[True,np.linalg.norm(np.diff(points,axis=0),axis=1)>1e-12]
        points,indices=points[keep],indices[keep]
        if len(points)<2:
            raise ValueError('Legacy guide must contain actual nonzero surface segments.')
        segments=np.column_stack([np.arange(len(points)-1),np.arange(1,len(points))])
        guides.append(dict(spec=spec,points=points,segments=segments,source_indices=indices))
    return guides


def activation(xyz, chart, guides, local_pass):
    query=xyz.copy()
    query[:,:2]=np.abs(query[:,:2])
    height=chart[:,0]
    angle=np.arctan2(np.abs(chart[:,2]),np.abs(chart[:,1]))
    support=np.zeros(len(xyz))
    core=np.zeros(len(xyz))
    payload={}
    for number,guide in enumerate(guides):
        spec=guide['spec']
        t=(height-spec['height'])/spec['axial_halfwidth']
        centre=spec['direction']+spec['sweep']*np.sin(np.pi*(height-spec['height'])/.32)
        height_gate=1.-smoothstep((np.abs(t)-.65)/.35)
        direction_gate=1.-smoothstep(np.abs(angle-centre)/.45)
        zone=height_gate*direction_gate
        distance=ancestry.loop.curves.closest_segment_distance(query,guide['points'],guide['segments'])
        side_support=1.-smoothstep(distance/RANGES[local_pass-1])
        protected_core=1.-smoothstep((distance-CORE_INNER)/(CORE_OUTER-CORE_INNER))
        support=np.maximum(support,zone*side_support)
        core=np.maximum(core,zone*protected_core)
        payload[f'guide_{number}_distance']=distance
        payload[f'guide_{number}_zone']=zone
    factor=1.-.95*core
    factor[core>=1.-1e-12]=0.
    weights=support*factor
    payload.update(detail_zone=support,legacy_core_weight=core,legacy_factor=factor,actual_activation=weights)
    return weights,payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('E:/CHESHIRE_DATA/column_detail_20261012'))
    parser.add_argument('--detail-pass',type=int,choices=(1,2),default=1)
    parser.add_argument('--name',default='NESTED')
    parser.add_argument('--strength',type=float,choices=(1.,3.),default=1.,
        help='Multiply the existing support-relative E/F coefficients; no absolute-depth replacement.')
    args=parser.parse_args()
    local=args.detail_pass
    global_stage=3+local
    root=args.root.resolve()
    family=Path(args.name)
    if family.is_absolute() or len(family.parts)!=1 or '..' in family.parts:
        raise ValueError('--name must be one family folder beneath --root.')
    source=SOURCE if local==1 else root/family/'G04'
    folder=root/family/f'G{global_stage:02}'
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError('Existing output preserved: '+str(folder))
    mesh,chart=ancestry.load_control(source/'control_quad.npz')
    legacy,legacy_chart=ancestry.load_control(SOURCE/'control_quad.npz')
    if mesh.generation!=global_stage-1:
        raise ValueError('Actual parent control generation differs from the declared global stage.')
    guides=legacy_guides(legacy,legacy_chart)
    measured={}
    def activate(refined_xyz,refined_chart,generation):
        weights,fields=activation(refined_xyz,refined_chart,guides,local)
        measured.update(fields)
        return weights
    nv=len(mesh.xyz)
    # Registration is only in this process-local imported dictionary. The
    # original role_growth source and existing NESTED output stay unchanged.
    variant='edge_face'
    budget=BUDGETS[local-1]
    if args.strength!=1.:
        variant='edge_face_nested_scaled'
        roles.VARIANTS[variant]={key:float(value*args.strength)
            for key,value in roles.VARIANTS['edge_face'].copy().items()}
        budget=STRONG_BUDGETS[local-1]
    xyz,quads,chart_out,operation,role_log=roles.role_step(mesh.xyz,mesh.faces,chart,
        local,variant,budget,absolute_depth=None,activation_fn=activate)
    if not np.array_equal(xyz[:nv],mesh.xyz):
        raise ValueError('Old control vertices must remain exactly held in this E/F-only detail pass.')
    edges=operation['input_edges']
    rest=np.concatenate([mesh.rest,mesh.rest[edges].mean(1),mesh.rest[mesh.faces].mean(1)])
    anchors=np.repeat(mesh.anchors,4,axis=0)
    out=ArrayMesh(xyz,quads,operation['birth_class'].copy(),rest,anchors,global_stage)
    out.surface='mean'
    physical=ancestry.task36_growth.native(out)
    triangles=physical.faces[:,:3]
    physical_chart=np.concatenate([chart_out,chart_out[quads].mean(1)])
    _,errors,matches=prior.reflection_state(physical.xyz,triangles,physical_chart)
    actual=trimesh.Trimesh(physical.xyz,triangles,process=False)
    area=float(actual.area_faces.min())
    checks=dict(finite=bool(np.isfinite(physical.xyz).all()),watertight=bool(actual.is_watertight),
        winding_consistent=bool(actual.is_winding_consistent),components=int(actual.body_count),
        minimum_triangle_area=area,minimum_area_threshold=1e-12,minimum_area_pass=area>1e-12,
        geometric_reflection_error=errors,reflected_triangle_sets_identical=matches)
    passed=checks['finite'] and checks['watertight'] and checks['winding_consistent'] and checks['minimum_area_pass']
    folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/'geometry.npz',xyz=physical.xyz,faces=triangles)
    np.savez_compressed(folder/'checkpoint.npz',xyz=physical.xyz,faces=triangles,chart=physical_chart,
        classes=physical.classes,rest=physical.rest,anchors=physical.anchors,generation=np.array(global_stage))
    np.savez_compressed(folder/'control_quad.npz',xyz=xyz,faces=quads,chart=chart_out,
        classes=out.classes,rest=rest,anchors=anchors,generation=np.array(global_stage))
    np.savez_compressed(folder/'operation_fields.npz',**operation,**measured,incoming_point_classes=mesh.classes)
    np.savez_compressed(folder/'legacy_guides.npz',
        **{f'guide_{i}_{key}':g[key] for i,g in enumerate(guides) for key in ('points','segments','source_indices')})
    actual.export(folder/'gate.ply')
    shutil.copy2(__file__,folder/'nested_recipe.py')
    role_log['guide_floor']=0.
    lengths=np.linalg.norm(operation['displacement'],axis=1)
    active=operation['guide_activation']>0.
    metadata=dict(candidate=str(family),stage=f'G{global_stage:02}',algorithm=ALGORITHM,
        source=str(source/'checkpoint.npz'),parent=str(source/'checkpoint.npz'),legacy_source=str(SOURCE/'control_quad.npz'),
        operation='One existing quad split and E-positive/F-negative support-scaled local normal relief; all inherited controls held, no field pass',
        role_variant=variant,role_offset=role_log,support_coefficient_gain=args.strength,
        declared_normal_offset_budget=budget,detail_pass_local=local,global_geometry_generation=global_stage,
        inherited_global_growth_cycles=3,new_detail_cycles_total=local,growth_cycles_total=global_stage,
        subdivision_passes_total=global_stage,role_offset_passes_total=local,field_passes_total=3,new_field_passes=0,
        counting_rule='G4/G5 label total geometry cycles; local role pass1/2 is a detail-only split, not another Task36+field cycle.',
        guide_specs=GUIDE_SPECS,guide_range=RANGES[local-1],protected_core_inner=CORE_INNER,protected_core_outer=CORE_OUTER,
        activation_floor=0.,activation_fraction=float(active.mean()),
        legacy_protection='Fixed actual G3 surface guide core attenuates new births; all inherited control XYZ stay exact. No automatic crease detection or dihedral/developability guarantee.',
        scale_policy='Existing minimum centre-to-supporting-edge radius; no constant world-depth amplification. G5 also keeps existing local role decay .72.',
        original_ancestry_preservation='rest interpolated in the same V/E/F order; original face anchors repeated to four children. Input classes stored separately; output classes use the existing last-birth V/E/F convention.',
        inactive_surface_limit='Old controls stay exact, but mean fan interpolation of nonplanar child quads may alter the physical surface even where role activation is zero.',
        source_control_vertices=nv,source_control_quads=len(mesh.faces),control_vertices=len(xyz),control_quads=len(quads),
        physical_vertices=len(physical.xyz),physical_triangles=len(triangles),
        old_controls_region_active=int(active[:nv].sum()),old_controls_region_inactive=int((~active[:nv]).sum()),
        old_controls_moved=0,old_controls_exactly_held=nv,new_controls_moved=int((lengths[nv:]>1e-12).sum()),
        maximum_actual_step=float(lengths.max()),minimum_triangle_area=area,
        separate_geometric_smoothing=False,CC_coordinate_averaging=False,field_used=False,new_authored_fold=False,
        quick_integrity='PASS' if passed else 'FAILED_PRESERVED_NO_REPAIR',
        provenance='Existing CHESHIRE role-growth normal placement with explicit selected-guide detail activation; not IAAC original code or physical folding.',
        self_intersection='NOT_CHECKED_INTERMEDIATE',fabrication_thickness_structure='NOT_CHECKED',
        **{key:value for key,value in checks.items() if key!='minimum_triangle_area'})
    prior.base.dump(folder/'generation.json',metadata)
    print('GENERATED',str(family),f'G{global_stage:02}','local role',local,'actual',len(physical.xyz),len(triangles),
        'activation',metadata['activation_fraction'],'step',metadata['maximum_actual_step'],'quick',metadata['quick_integrity'],flush=True)
    if not passed:
        raise ValueError('Failed candidate and record preserved; no repair or threshold change.')


if __name__=='__main__':
    main()
