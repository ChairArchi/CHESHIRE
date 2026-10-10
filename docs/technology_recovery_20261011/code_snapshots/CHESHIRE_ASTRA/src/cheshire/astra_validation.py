"""Explicit closed single-component policy for the independent primitive study."""
def embedding_failures(value, expected_euler=2):
    failures=[]
    for key in ['finite']:
        if not value.get(key,False):failures.append(key)
    for key in ['zero_area_faces','degenerate_triangles','orphan_vertices']:
        if value.get(key,1)!=0:failures.append(key)
    if value.get('invalid_vertex_links',[None]):failures.append('invalid_vertex_links')
    if value.get('connected_components')!=1:failures.append('connected_components')
    if expected_euler is not None and value.get('Euler')!=expected_euler:failures.append('Euler')
    return failures
