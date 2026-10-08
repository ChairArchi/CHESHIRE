"""Compare existing full Task31 renders with newly matched Task32 actual renders."""
import sys
import numpy as np
from PIL import Image
from task32_research import ROOT,read,write_new,sha
from task31_views import sheet


def main():
    old=read('E:/CHESHIRE_DATA/task31/renders/gate_compare/manifest.json')
    detail=read('E:/CHESHIRE_DATA/task31/renders/gate_detail/manifest.json')
    current=read(ROOT/'renders/G8_CAMERA_1400/manifest.json')
    for field in ['backend','material','light']:
        if current[field]!=old[field] or current[field]!=detail[field]:raise ValueError('Render condition changed: '+field)
    prior=[old['records'][2],old['records'][3],detail['records'][8]]
    records=[dict(r,label='TASK31 FOLD_OPEN_85 G8 '+label) for r,label in zip(prior,['front','oblique','lintel'])]
    proof=[]
    for i,r in enumerate(current['records']):
        p=prior[i%3]
        for field in ['angles','width','target','flat_normals','smoothing','camera_pose']:
            if r[field]!=p[field]:raise ValueError('Camera/shading mismatch: '+field)
        if Image.open(r['image']).size!=Image.open(p['image']).size:raise ValueError('Pixel resolution mismatch.')
        for image_record in [p,r]:
            if sha(image_record['image'])!=image_record['image_sha256']:raise ValueError('Image hash mismatch.')
        proof.append(dict(current=r['label'],prior=p['label'],camera_and_shading_equal=True,
            original_mesh_sha256=p['mesh_sha256'],original_image_sha256=p['image_sha256'],
            current_mesh_sha256=r['mesh_sha256'],current_image_sha256=r['image_sha256'],
            original_polygons=p['polygons'],current_polygons=r['polygons']))
        records.append(r)
    output=ROOT/'renders/TASK31_G8_VS_TASK32.png'
    if output.exists():raise ValueError('Fresh comparison output required.')
    sheet(records,output,cols=3,size=700)
    write_new(ROOT/'validation/frozen_G8_comparison.json',dict(records=records,proof=proof,
        image_sha256=sha(output),script_sha256=sha(__file__),
        note='Original Task31 G8 images reused byte-unmodified; no GPU reload of 5,021,696 polygons. Current actual native meshes rendered with identical camera, 1400px resolution, flat normals, clay, light and backend. Mesh resolutions differ explicitly; no claim of equal detail density.'))


if __name__=='__main__':main()
