"""Actual inherited-route overlay and native-file analytical sections.

Uses the existing projection tool and Rhino-produced intersection polylines.
No shader, sculpting, topology repair or replacement renderer is introduced.
"""
import argparse
import gc
from html import escape
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'examples'))
from cross_cell_crease_study import read,write,file_hash


def overlay(root,lead,attempt,view_tag):
    checkpoint=root/'designs'/lead/attempt
    state=read(checkpoint/'state.json.gz')['state']
    networks=state['networks'];del state;gc.collect()
    operator=read(checkpoint/'operator.json.gz')
    combined=operator['combined_fold']
    counts={k:combined[k] for k in ['active_point_counts','later_face_stencil','placement_audit_sha256']}
    counts['nonzero_input_support_vertices']=len(combined['input_route_support'])
    del operator,combined;gc.collect()
    edges=[];junctions=[];directions=[]
    for net in networks:
        central=net['network_id']=='lintel_convergence_support'
        for edge in net['edges']:
            edges.append(dict(vertices=edge['vertices'],sharpness=edge['sharpness'],code=5 if central else -1))
        if central:
            junctions.extend(net.get('junction_vertices',[]))
    out=root/'renders/geometry_evidence';out.mkdir(parents=True,exist_ok=True)
    write(out/'edges.json',dict(edges=edges,junctions=junctions,directions=directions,
        legend='CYAN: actual zero-sharpness central support descendants; GRAY: inherited crease paths. Unculled overlay; graph band extends beyond the lines.'))
    cameras=read(root/'renders'/view_tag/'camera_manifest.json')['records']
    frames=[]
    for view in ['close','detail_angle']:
        camera=next(row for row in cameras if row['id']==lead and row['view']==view)
        frames.append(dict(mesh='../'+view_tag+'/'+lead+'_'+view+'.json',
            file=lead+'_'+view+'_overlay.png',label=lead+' / actual path descendants / unculled overlay',
            camera='front',bounds=camera['bounds'],width=1000,height=1000,edgefile='edges.json'))
    write(out/'projection_plan.json',dict(frames=frames,sheets=[]))
    write(root/'analysis/folding_support.json',dict(lead=lead,attempt=attempt,
        actual_state=str(checkpoint/'state.json.gz'),state_sha256=file_hash(checkpoint/'state.json.gz'),
        operator_sha256=file_hash(checkpoint/'operator.json.gz'),counts=counts,
        camera_manifest_sha256=file_hash(root/'renders'/view_tag/'camera_manifest.json'),
        networks=networks,
        interpretation='Support selects where existing weighted placement acts, not a new crease ridge/valley classifier. Cyan paths have sharpness zero; original crease constraints remain active separately.',
        band='Linear graph-hop alpha, zero outside explicit recipe band. Face/edge alpha is the average of its actual parent vertices.',
        overlay='Actual current mesh IDs. All path lines drawn without visibility culling; crossings cannot prove a hole.'))
    print(out/'projection_plan.json',flush=True)


def sections(root,lead):
    names=['H1_BASELINE',lead];rows=[read(root/'analysis/sections'/(n+'.json')) for n in names]
    # Identical original-coordinate frames for each actual native-file section.
    panels=[('X=-392 / YZ',(1,2),(-1500,500,1800,3000)),
            ('Y=-350 / XZ',(0,2),(-1100,300,1800,3000)),
            ('Z=2450 / XY',(0,1),(-1100,300,-1600,500))]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1640" height="1720" viewBox="0 0 1640 1720">',
        '<rect width="1640" height="1720" fill="white"/>',
        '<text x="20" y="25" font-family="sans-serif" font-size="18">Task25: actual native-file mesh/plane intersections. Fixed coordinates; no shading or volume inference.</text>']
    for j,(label,axes,bounds) in enumerate(panels):
        for i,(name,row) in enumerate(zip(names,rows)):
            x=20+i*810;y=60+j*550;w=790;h=480
            svg.append('<defs><clipPath id="c%d%d"><rect x="%d" y="%d" width="%d" height="%d"/></clipPath></defs>'%(i,j,x,y+30,w,h))
            svg.append('<text x="%d" y="%d" font-family="sans-serif" font-size="17">%s / %s</text>'%(x,y+20,escape(name),escape(label)))
            svg.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#f8f9fa" stroke="#999"/>'%(x,y+30,w,h))
            # Equal horizontal/vertical scale within each section panel.
            a,b,c,d=bounds;scale=min(w/(b-a),h/(d-c));ox=x+(w-(b-a)*scale)/2;oy=y+30+(h-(d-c)*scale)/2
            section=next(s for s in row['sections'] if s['plane']==label)
            svg.append('<g clip-path="url(#c%d%d)" fill="none" stroke="#304c66" stroke-width="0.7">'%(i,j))
            for line in section['polylines']:
                points=' '.join('%.3f,%.3f'%(ox+(p[axes[0]]-a)*scale,oy+(d-p[axes[1]])*scale) for p in line)
                svg.append('<polyline points="'+points+'"/>')
            svg.append('</g>')
    svg.append('</svg>');(root/'analysis/native_sections.svg').write_text('\n'.join(svg),encoding='utf-8')
    write(root/'analysis/native_sections_manifest.json',dict(names=names,planes=panels,
        inputs={n:file_hash(root/'analysis/sections'/(n+'.json')) for n in names},
        semantics='Polygon-plane intersection coordinates from actual reread native files; sampled planes do not establish watertight physical volume, new handles or self-intersection freedom.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,required=True);p.add_argument('--lead',required=True)
    p.add_argument('--attempt',default='attempt_001');p.add_argument('--sections',action='store_true')
    p.add_argument('--view-tag',default='curvature_comparison')
    a=p.parse_args()
    if a.sections:sections(a.output_root,a.lead)
    else:overlay(a.output_root,a.lead,a.attempt,a.view_tag)
