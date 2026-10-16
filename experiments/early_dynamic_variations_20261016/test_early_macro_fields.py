"""Macro-field contracts, plus a read-only test on an actual saved G2 parent."""
from pathlib import Path
import argparse
import hashlib
import json
import unittest

import numpy as np

from early_macro_fields import apply_macro_field
from variation_recipes import catalogue, variant_recipes


def cylinder():
    sectors, rings = 16, 17
    t, angle = np.meshgrid(np.linspace(0, 1, rings),
                          np.arange(sectors)*2*np.pi/sectors, indexing="ij")
    x = np.column_stack((np.cos(angle).ravel(), np.sin(angle).ravel(), 8*t.ravel()))
    x[np.abs(x) < 1e-14] = 0
    chart = np.column_stack((t.ravel(), x[:, 0], x[:, 1]))
    ids = np.arange(rings*sectors).reshape(rings, sectors)
    px = ids[:, (sectors//2-np.arange(sectors)) % sectors].ravel()
    py = ids[:, (-np.arange(sectors)) % sectors].ravel()
    return x, chart, {"X": px, "Y": py}


class MacroTests(unittest.TestCase):
    def test_baseline_is_bit_exact_and_inputs_unchanged(self):
        x, c, pairs = cylinder(); before=x.copy(); chart=c.copy()
        y, evidence, meta = apply_macro_field(x, c, {}, vertex_pairs=pairs)
        self.assertTrue(np.array_equal(y, x))
        self.assertTrue(np.array_equal(x, before) and np.array_equal(c, chart))
        self.assertFalse(meta["active"])
        self.assertFalse(evidence["total_displacement"].any())

    def test_all_families_are_visible_bounded_and_reflection_equivariant(self):
        x, c, pairs = cylinder(); hashes=[]
        for row in variant_recipes()[1:]:
            y, ev, meta = apply_macro_field(x, c, row["macro_fields"], vertex_pairs=pairs)
            self.assertTrue(np.isfinite(y).all())
            self.assertGreater(np.linalg.norm(y-x, axis=1).max(), .08)
            self.assertLessEqual(np.linalg.norm(ev["bounded_macro_displacement"], axis=1).max(),
                                 meta["local_displacement_bound"]*(1+1e-12))
            for label, axis in (("X", 0), ("Y", 1)):
                mirrored=y.copy();mirrored[:, axis]*=-1
                self.assertLess(np.max(np.abs(y[pairs[label]]-mirrored)), 1e-12)
            self.assertTrue(np.array_equal(y[(c[:,0]==0)|(c[:,0]==1)], x[(c[:,0]==0)|(c[:,0]==1)]))
            hashes.append(meta["output_xyz_sha256"])
        self.assertEqual(len(set(hashes)), 18)

    def test_protection_and_single_length_scaling(self):
        x,c,pairs=cylinder();r=dict(family="fan",length_scale=1.5)
        y,ev,meta=apply_macro_field(x,c,r,vertex_pairs=pairs)
        self.assertAlmostEqual(np.ptp(y[:,2]),12.)
        protected=(c[:,0]<.2)|(c[:,0]>.8)
        y,_,_=apply_macro_field(x,c,r,protection=protected,vertex_pairs=pairs)
        self.assertTrue(np.array_equal(y[protected],x[protected]))
        for recipe in variant_recipes()[1:]:
            self.assertEqual(recipe["macro_fields"]["length_scale"],1.)
            source,target=np.asarray(recipe["material_axial_knots"])
            self.assertTrue(np.all(np.diff(source)>0) and np.all(np.diff(target)>0))

    def test_invalid_contracts_fail(self):
        x,c,pairs=cylinder()
        for recipe in ({"nodes":2},{"length_scale":1.8},{"unknown":1}):
            with self.assertRaises(ValueError):apply_macro_field(x,c,recipe)
        with self.assertRaises(ValueError):apply_macro_field(x,c,{"family":"fan"},protection=np.ones(2))
        broken={"X":pairs["X"].copy(),"Y":pairs["Y"]};broken["X"][0]=1
        with self.assertRaises(ValueError):apply_macro_field(x,c,{"family":"fan"},vertex_pairs=broken)


def actual_g2_qa(stage):
    with np.load(stage/"control_quad.npz") as z:x=z["xyz"];q=z["faces"];c=z["chart"]
    before=x.copy();faces=q.copy();chart=c.copy()
    with np.load(stage/"evidence.npz") as z:
        pairs={"X":z["mirror_x_vertex_pairs"],"Y":z["mirror_y_vertex_pairs"]}
    results=[]
    for row in variant_recipes():
        y,ev,meta=apply_macro_field(x,c,row["macro_fields"],stage=2,vertex_pairs=pairs)
        errors=[]
        for label,axis in (("X",0),("Y",1)):
            target=y.copy();target[:,axis]*=-1;errors.append(float(np.max(np.abs(y[pairs[label]]-target))))
        magnitude=np.linalg.norm(y-x,axis=1)
        end=(c[:,0]==0)|(c[:,0]==1)
        assert np.isfinite(y).all() and max(errors)<1e-10
        assert np.array_equal(y[end],x[end])
        if row["id"]=="B00":assert np.array_equal(y,x)
        else:assert magnitude.max()>.01
        results.append(dict(id=row["id"],field_output_sha256=meta["output_xyz_sha256"],
            maximum_displacement=float(magnitude.max()),median_nonzero_displacement=float(np.median(magnitude[magnitude>0])) if np.any(magnitude>0) else 0.,
            changed_vertices=int((magnitude>0).sum()),XY_reflection_max_error=max(errors),
            material_end_vertices_bit_exact=True))
    assert np.array_equal(before,x) and np.array_equal(faces,q) and np.array_equal(chart,c)
    return dict(kind="ACTUAL_G2_READ_ONLY_MACRO_FIELD_QA",passed=True,
        input_control_path=str(stage/"control_quad.npz"),input_sha256=hashlib.sha256((stage/"control_quad.npz").read_bytes()).hexdigest(),
        vertices=len(x),quads=len(q),results=results,
        topology_and_chart_unchanged=True,input_assets_modified=False,
        scope="Tests fields on one actual saved G2 parent; actual replay injects once at G3. Top-level G0 length/remap and downstream operator replay are not tested here.",
        orientation_or_self_intersection_certificate=False)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--actual-g2",type=Path);p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MacroTests))
    if not result.wasSuccessful():raise SystemExit(1)
    if a.actual_g2:
        data=actual_g2_qa(a.actual_g2)
        if a.output:
            if a.output.exists():raise FileExistsError(a.output)
            a.output.write_text(json.dumps(data,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        print("ACTUAL_G2_PASS",data["vertices"],data["quads"],len(data["results"]),flush=True)
