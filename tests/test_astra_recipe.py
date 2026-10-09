import importlib.util
from pathlib import Path
import numpy as np
import pytest
from cheshire.task36_growth import carrier
spec=importlib.util.spec_from_file_location('astra_recipe',Path(__file__).resolve().parents[1]/'tools/astra_recipe.py')
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)

def test_dual_to_primal_does_not_fabricate_vfe_ancestry():
    m=carrier();m,roles,meta,state=recipe.operate(m,None,dict(operator='dual',parameters=dict(fold_gain=0,feedback=0)))
    out,roles,meta,state=recipe.operate(m,roles,dict(operator='reference',parameters={}))
    assert meta['eq4_eligible']==0
    assert roles is None
    assert np.isfinite(out.xyz).all()

def test_triangle_rotation_uses_complete_quad_native_surface():
    m=carrier();out,_,meta,state=recipe.operate(m,None,dict(operator='rotating',parameters=dict(fold=0)))
    assert len(out.faces)==len(m.faces)*4*3
    assert out.generation==1
    assert state['parent_faces'].max()<len(m.faces)*4

def test_unknown_operator_is_not_silent_fallback():
    with pytest.raises(ValueError,match='Unknown'):recipe.operate(carrier(),None,dict(operator='unknown'))
