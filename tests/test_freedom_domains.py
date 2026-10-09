"""Geometry invariants for the deliberately symmetry-unconstrained domain study."""
import copy
import numpy as np
import pytest
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from cheshire.reference_subdivision import topology
from cheshire.task36_growth import native,carrier
from cheshire.freedom_domains import step


def irregular_column():
    # Break equal-score numerical ties only in the test fixture. No random input.
    m=native(carrier())
    i=np.arange(len(m.xyz),dtype=float)
    m.xyz += np.column_stack([17*np.sin(i*.713),23*np.cos(i*.491),11*np.sin(i*.337)])
    m.rest=m.xyz.copy()
    return m


def graph_for(base,faces):
    class Geometry:pass
    m=Geometry();m.xyz=base;m.faces=faces
    e=topology(m)['edges'];length=np.linalg.norm(base[e[:,1]]-base[e[:,0]],axis=1)
    return coo_matrix((np.repeat(length,2),(e.ravel(),e[:,::-1].ravel())),shape=(len(base),len(base))).tocsr()


def test_zero_angle_exact_surface_and_closed_topology():
    m=irregular_column();o,meta,s=step(m,angle=0,radius=1400.)
    np.testing.assert_array_equal(o.xyz,s['base_xyz'])
    np.testing.assert_array_equal(o.xyz[:len(m.xyz)],m.xyz)
    np.testing.assert_array_equal(o.xyz[len(m.xyz):],m.xyz[s['input_edges']].mean(1))
    tri=o.xyz[o.faces[:,:3]];areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    p=m.xyz[m.faces[:,:3]];parent_area=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)/2
    np.testing.assert_allclose(areas.reshape(-1,4).sum(1),parent_area)
    assert len(o.xyz)-len(topology(o)['edges'])+len(o.faces)==2
    assert meta['degenerate_triangles']==0


def test_coordinate_and_radius_similarity_equivariance():
    m=irregular_column();scaled=copy.deepcopy(m);scaled.xyz*=3;scaled.rest*=3
    a,_,sa=step(m,radius=1400.,angle=1.1)
    b,_,sb=step(scaled,radius=4200.,angle=1.1)
    np.testing.assert_array_equal(sa['candidate_seed_edges'],sb['candidate_seed_edges'])
    np.testing.assert_array_equal(sa['selected_seed_edges'],sb['selected_seed_edges'])
    np.testing.assert_array_equal(sa['suppressed_by_seed'],sb['suppressed_by_seed'])
    np.testing.assert_allclose(b.xyz,3*a.xyz,rtol=1e-12,atol=1e-9)
    np.testing.assert_allclose(sb['domain_distances'],3*sa['domain_distances'],rtol=1e-12,atol=1e-9)
    np.testing.assert_allclose(sb['domain_weights'],sa['domain_weights'],rtol=1e-10,atol=1e-12)


def test_seed_spacing_is_actual_graph_distance_and_suppression_is_true():
    m=irregular_column();radius=1400.;spacing=.7
    out,_,s=step(m,radius=radius,spacing=spacing)
    seeds=s['selected_seed_edges'];assert len(seeds)>1
    graph=graph_for(s['base_xyz'],out.faces);nv=len(m.xyz)
    for seed in seeds:
        distance=dijkstra(graph,indices=int(nv+seed),directed=True)
        others=seeds[seeds!=seed]
        assert np.all(distance[nv+others]>=spacing*radius-1e-8)
        suppressed=np.flatnonzero(s['suppressed_by_seed']==seed)
        assert np.all(distance[nv+suppressed]<spacing*radius+1e-8)
        chosen=s['domain_seed_edges']==seed
        np.testing.assert_allclose(s['domain_distances'][chosen],distance[s['domain_vertex_ids'][chosen]])
        assert np.all(s['domain_distances'][chosen]<radius)


def test_current_geometry_reinterprets_hinges_vs_evolving_rest():
    m=irregular_column();first,_,_=step(m,radius=1400.,angle=1.3)
    current,_,sc=step(first,radius=1100.,source='current')
    rest,_,sr=step(first,radius=1100.,source='rest')
    assert np.max(abs(sc['seed_observed_bend']-sr['seed_observed_bend']))>1e-3
    assert np.max(abs(current.xyz-rest.xyz))>1e-3
    assert not np.array_equal(sc['selected_seed_edges'],sr['selected_seed_edges'])


def test_coherent_weights_reconstruct_applied_motion_without_nan():
    m=irregular_column();out,_,s=step(m,radius=1800.,spacing=.3,power=4.)
    ids=s['domain_vertex_ids'];weights=s['domain_weights'];moves=s['domain_moves'];n=len(out.xyz)
    assert len(ids)>0 and s['patch_coverage'].max()>1
    assert np.isfinite(weights).all() and np.all(weights>=0)
    total=np.bincount(ids,weights=weights,minlength=n)
    accum=np.column_stack([np.bincount(ids,weights=weights*moves[:,k],minlength=n) for k in range(3)])
    applied=np.divide(accum,total[:,None],out=np.zeros_like(accum),where=total[:,None]>0)
    np.testing.assert_allclose(applied,s['resolved_displacement'],rtol=1e-12,atol=1e-12)
    np.testing.assert_array_equal(np.bincount(ids,minlength=n),s['patch_coverage'])
    np.testing.assert_allclose(out.xyz,s['base_xyz']+applied)
    assert np.isfinite(s['proposal_attenuation']).all()
    assert np.all(s['proposal_attenuation']>=-1e-12)
    assert np.all(s['proposal_attenuation']<=1+1e-12)
    for vertex in np.flatnonzero(total>0):
        assert s['winning_seed'][vertex] in s['domain_seed_edges'][ids==vertex]


def test_explicit_control_guards():
    m=native(carrier())
    for kw in ({'angle':np.nan},{'radius':0},{'spacing':-1},{'power':0},{'polarity':0},{'source':'unknown'}):
        with pytest.raises(ValueError):step(m,**kw)
