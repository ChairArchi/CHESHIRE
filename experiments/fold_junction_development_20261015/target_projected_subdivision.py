"""Completed-face Catmull-Clark refinement constrained to one fixed target patch.

Completed faces feed the edge and old-vertex carriers. The field is queried
again at each causally changed carrier, not once on a neutral child mesh.
Original edge midpoints are retained in the vertex equation. Topology and
material transport come from the caller's verified actual q6/q7 lineage.
"""
from pathlib import Path

import numpy as np


def helper_paths():
    return [Path(__file__).resolve()]


def _unit_free_incident_mean(values,ids,counts):
    """Arithmetic incidence mean; physical vectors are not normalized."""
    return np.column_stack([np.bincount(ids,weights=values[:,axis],
        minlength=len(counts))/counts for axis in range(3)])


def _repeat_incident_mean(values,ids,repetitions,counts):
    return np.column_stack([np.bincount(ids,
        weights=np.repeat(values[:,axis],repetitions),minlength=len(counts))/counts
        for axis in range(3)])


def _request(field,carrier,chart,stage):
    callback=getattr(field,'evaluate',field)
    if not callable(callback):raise ValueError('A callable actual-carrier 3D field required.')
    positions=carrier.view();positions.flags.writeable=False
    material=chart.view();material.flags.writeable=False
    desired=np.asarray(callback(positions,material,stage),dtype=float)
    if desired.shape!=carrier.shape or not np.isfinite(desired).all():
        raise ValueError('Field must return a finite physical Nx3 vector at stage '+stage)
    return desired


def _peak(values):
    return float(np.linalg.norm(values,axis=1).max(initial=0.))


def subdivide(xyz,q6,chart,edges,following,degree,q7,field):
    """Return ``(outXYZ, outChart, JSON_safe_meta, flat_NPZ_evidence)``.

    ``following`` is (nf,4) face-corner -> following input edge ID. ``q7``
    must use the exact actual [old V, new E, new F] global point ordering and
    [previous E, old corner V, following E, parent F] child quad ordering.
    Callback signature: evaluate(currentXYZ, materialChart, stage)->full target residual P(currentXYZ)-currentXYZ.
    Stages are FACE, EDGE, VERTEX. Caller owns parent/rail/SOURCE eligibility.
    """
    xyz=np.asarray(xyz,dtype=float);chart=np.asarray(chart,dtype=float)
    q6=np.asarray(q6);edges=np.asarray(edges);following=np.asarray(following)
    degree=np.asarray(degree);q7=np.asarray(q7)
    nv=len(xyz);nf=len(q6);ne=len(edges)
    if xyz.shape!=(nv,3) or chart.shape!=xyz.shape or not np.isfinite(xyz).all() or not np.isfinite(chart).all():
        raise ValueError('Matching finite Nx3 actual positions/material chart required.')
    if (q6.shape!=(nf,4) or edges.shape!=(ne,2) or following.shape!=(nf,4) or
            degree.shape!=(nv,) or q7.shape!=(4*nf,4) or
            any(a.dtype.kind not in 'iu' for a in (q6,edges,following,degree,q7))):
        raise ValueError('Actual quad, edge, face-edge, degree and child topology arrays required.')
    if (not nv or not nf or not ne or q6.min()<0 or q6.max()>=nv or
            edges.min()<0 or edges.max()>=nv or following.min()<0 or following.max()>=ne or
            np.any(degree<=0) or q7.min()<0 or q7.max()>=nv+ne+nf):
        raise ValueError('In-range closed actual refinement topology required.')
    face_incidence=np.bincount(q6.ravel(),minlength=nv)
    edge_incidence=np.bincount(edges.ravel(),minlength=nv)
    edge_face_count=np.bincount(following.ravel(),minlength=ne)
    if (not np.array_equal(face_incidence,degree) or not np.array_equal(edge_incidence,degree) or
            not np.all(edge_face_count==2)):
        raise ValueError('Closed quad incidence/degree differs from supplied actual topology.')
    # Bounded validation of exact supplied child ancestry, without resorting
    # edges or inventing an alternative child point order.
    for first in range(0,nf,131072):
        last=min(first+131072,nf);q=q6[first:last];fe=following[first:last]
        child=q7[4*first:4*last].reshape(-1,4,4)
        if (not np.array_equal(child[:,:,1],q) or
                not np.array_equal(child[:,:,2],nv+fe) or
                not np.array_equal(child[:,:,0],nv+np.roll(fe,1,axis=1)) or
                not np.array_equal(child[:,:,3],np.broadcast_to((nv+ne+np.arange(first,last))[:,None],q.shape))):
            raise ValueError('Supplied child topology has a different V/E/F ancestry/order.')
        pair=edges[fe];next_vertex=np.roll(q,-1,axis=1)
        match=((pair[:,:,0]==q)&(pair[:,:,1]==next_vertex))|((pair[:,:,1]==q)&(pair[:,:,0]==next_vertex))
        if not match.all():raise ValueError('Following input edge does not match its actual face side.')
    face_chart=chart[q6].mean(axis=1)
    edge_chart=chart[edges].mean(axis=1)
    face_carrier=xyz[q6].mean(axis=1)
    face_desired=_request(field,face_carrier,face_chart,'FACE')
    completed_face=face_carrier+face_desired
    # Two incident COMPLETED face positions plus ORIGINAL endpoints, Eq2.
    face_sum_at_edge=np.column_stack([np.bincount(following.ravel(),
        weights=np.repeat(completed_face[:,axis],4),minlength=ne) for axis in range(3)])
    original_midpoints=xyz[edges].mean(axis=1)
    edge_carrier=(face_sum_at_edge+2.*original_midpoints)/4.
    edge_desired=_request(field,edge_carrier,edge_chart,'EDGE')
    edge_offset=edge_desired
    completed_edge=edge_carrier+edge_offset
    # Completed face mean plus ORIGINAL edge-midpoint mean, Eq3. The completed
    # edge points above are intentionally not substituted into this equation.
    completed_face_mean=_repeat_incident_mean(completed_face,q6.ravel(),4,degree)
    original_midpoint_mean=_repeat_incident_mean(original_midpoints,edges.ravel(),2,degree)
    vertex_carrier=(completed_face_mean+2.*original_midpoint_mean+
        (degree-3)[:,None]*xyz)/degree[:,None]
    vertex_desired=_request(field,vertex_carrier,chart,'VERTEX')
    vertex_offset=vertex_desired
    completed_vertex=vertex_carrier+vertex_offset
    out=np.concatenate((completed_vertex,completed_edge,completed_face))
    outchart=np.concatenate((chart,edge_chart,face_chart))
    if not np.isfinite(out).all():raise ValueError('Nonfinite causal vector refinement.')
    metadata=dict(implementation='FIXED_TARGET_FULL_RESIDUAL_CC_V1',
        input_vertices=nv,input_edges=ne,input_quads=nf,
        output_vertices=len(out),output_quads=len(q7),added_subdivision_passes=1,
        field_stage_order=['FACE','EDGE','VERTEX'],
        maximum_face_desired_physical_vector=_peak(face_desired),
        maximum_edge_desired_physical_vector=_peak(edge_desired),
        maximum_vertex_desired_physical_vector=_peak(vertex_desired),
        maximum_face_added_offset=_peak(face_desired),
        maximum_edge_added_offset=_peak(edge_offset),
        maximum_vertex_added_offset=_peak(vertex_offset),
        face_equation='F=mean(original quad positions)+A(actual face carrier,face chart,FACE).',
        edge_equation='Ecarrier=(sum(two completed F)+sum(two original endpoints))/4; E=Ecarrier+R(Ecarrier,edge chart,EDGE).',
        vertex_equation='Vcarrier=(mean(incident completed F)+2*mean(ORIGINAL incident edge midpoints)+(degree-3)*oldV)/degree; V=Vcarrier+R(Vcarrier,old chart,VERTEX).',
        original_midpoints_retained=True,completed_edges_used_in_vertex_equation=False,
        physical_vector_units=True,mesh_edge_length_amplitude_scaling=False,
        old_vertices_pinned=False,scalar_normal_only_field=False,target_full_residual=True,
        material_transport='Old V chart unchanged; E original endpoint chart mean; F original quad chart mean.',
        target_contract='R=P(actual carrier)-actual carrier at every class; no extrusion balance factors. A fixed plane projector puts every class on the same plane.',
        control_scope='w1/w2/w3/w4/w6/w7 remain zero. Only physical3D A and its causal stage queries modify the standard carrier.',
        topology_scope='Caller supplied actual q6/q7 edge order, closed incidences and exact child ancestry verified; no edge sorting/remeshing.',
        parent_protection='Caller callback must supply compact zero field on all protected rails/source interfaces for all stages. No automatic pin or global flow guarantee.',
        causality_scope='Actual formed face points change subsequent field query positions. A callback ignoring XYZ may algebraically reduce to a sampled coating; vector coupling alone does not guarantee branching.',
        global_self_intersection_checked=False,aesthetic_success='Unverified until actual matched render.')
    evidence=dict(face_carrier=face_carrier,face_chart=face_chart,
        face_desired_field=face_desired,face_added_offset=face_desired,completed_face=completed_face,
        edge_carrier=edge_carrier,edge_chart=edge_chart,edge_desired_field=edge_desired,
        edge_added_offset=edge_offset,completed_edge=completed_edge,
        vertex_carrier=vertex_carrier,vertex_chart=chart,vertex_desired_field=vertex_desired,
        vertex_added_offset=vertex_offset,completed_vertex=completed_vertex,
        original_edge_midpoints=original_midpoints)
    return out,outchart,metadata,evidence
