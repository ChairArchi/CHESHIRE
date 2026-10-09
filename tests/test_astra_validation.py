from cheshire.astra_validation import embedding_failures

def valid():
    return dict(finite=True,zero_area_faces=0,degenerate_triangles=0,orphan_vertices=0,invalid_vertex_links=[],connected_components=1,Euler=2)

def test_disconnected_and_pinched_cannot_pass_export_policy():
    for key,value in [('connected_components',2),('invalid_vertex_links',[3]),('orphan_vertices',1),('finite',False),('degenerate_triangles',1)]:
        data=valid();data[key]=value
        assert key in embedding_failures(data)

def test_genus_policy_is_explicit_not_universal_ban():
    data=valid();data['Euler']=0
    assert 'Euler' in embedding_failures(data)
    assert not embedding_failures(data,expected_euler=0)
