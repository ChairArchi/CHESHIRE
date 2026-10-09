import numpy as np
from scipy.spatial import cKDTree
from cheshire.reference_subdivision import cube,topology
from cheshire.task36_growth import native,carrier
from cheshire.freedom_patch import step

def test_zero_is_exact_midpoint_surface():
 m=native(carrier());o,_,s=step(m,angle=0)
 np.testing.assert_allclose(o.xyz,s['base_xyz'],atol=1e-12)
 assert len(o.faces)==4*len(m.faces)
 assert len(o.xyz)-len(topology(o)['edges'])+len(o.faces)==2

def test_symmetry_and_actual_parents():
 for direction in ['parallel','transverse']:
  m=native(carrier());o,_,s=step(m,direction=direction)
  for axis in [0,1]:
   x=o.xyz.copy();x[:,axis]*=-1
   assert cKDTree(o.xyz).query(x)[0].max()<1e-9
  assert np.array_equal(o.anchors,m.anchors[s['parent_faces']])

def test_finite_rotation_has_tangential_component_and_feedback():
 m=native(cube());a,_,s=step(m);b,_,r=step(a,source='rest');c,_,v=step(a,source='current')
 assert np.linalg.norm(s['resolved_displacement'])>1
 assert np.max(abs(r['observed_edge_angles']-v['observed_edge_angles']))>1e-3
 assert np.isfinite(b.xyz).all() and np.isfinite(c.xyz).all()

def test_connected_patch_crosses_multiple_parent_faces_and_reflects():
 from cheshire.freedom_patch import connected_step
 m=native(carrier());o,meta,s=connected_step(m,radius=1400.)
 assert len(s['patch_vertex_ids_flat'])>0
 assert s['patch_coverage'].max()>1
 assert np.array_equal(o.faces,step(m,angle=0)[0].faces)
 for axis in [0,1]:
  x=o.xyz.copy();x[:,axis]*=-1
  assert cKDTree(o.xyz).query(x)[0].max()<1e-8
 z,_,zs=connected_step(m,angle=0,radius=1400.)
 np.testing.assert_allclose(z.xyz,zs['base_xyz'],atol=1e-10)
