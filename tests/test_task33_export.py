import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from task33_export import triangulate
from task33_evidence import canonical
from test_task33_folds import gate
from cheshire.task33_folds import initial_chart,refine,evaluate
from cheshire.reference_subdivision import topology


def test_explicit_triangle_surface_reflects_without_changing_native_positions():
    m=gate();state=initial_chart(m)
    for _ in range(2):m,state,_,_=refine(m,state,carrier_smoothing=True)
    m,_=evaluate(m,state,dict(twist=.35,paired_controls=True),2)
    out,op=triangulate(m,state)
    np.testing.assert_array_equal(out.xyz,m.xyz)
    np.testing.assert_array_equal(out.rest,m.rest)
    np.testing.assert_array_equal(out.classes,m.classes)
    assert len(out.faces)==2*len(m.faces)
    reflected=canonical(op['vertex_reflection'][out.faces[:,:3][:,::-1]])
    actual=canonical(out.faces[:,:3])
    np.testing.assert_array_equal(actual[np.lexsort(actual.T)],reflected[np.lexsort(reflected.T)])
    t=topology(out)
    assert len(out.xyz)-len(t['edges'])+len(out.faces)==2
    np.testing.assert_array_equal(out.anchors,m.anchors[op['parent_face']])
