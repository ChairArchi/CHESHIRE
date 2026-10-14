"""Integral short diagonal ridges inside existing fine G7 quad boundaries."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import shutil
import time
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path('E:/CHESHIRE_DATA/experiments/comb_relief_20261014/trial01')
SOURCE = Path('E:/CHESHIRE_DATA/experiments/end_rule_revision_20261014/trial01/REVISED')
ORIGINAL = Path('E:/CHESHIRE_DATA/experiments/medium_root_folds_20261013/trial02/WIDE_ROOT_FINISHED/SPAN/G07')
EXPECTED = {'geometry.npz':'952386874740ca35a26dcb0a5a42cda4fb91eaa8f814f7668550d839a2b688ce',
            'control_quad.npz':'0915ac8f56509768c6329a7d848793c6936b903d4d9316e01b1076a76aba8e27'}
MASK_SHA = 'db4b3b8f0bebd4907f25e3316cdd3a918e987bf99d941811586c365fdbf8a88a'
H = 9.735842284057451
PATTERN = np.array([[0,1,4],[1,5,4],[1,2,5],[2,3,5],[3,4,5],[3,0,4]], np.int64)

def digest(path):
    h = hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()

def ah(array):
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast('B')).hexdigest()

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def unit(value):
    return value/np.maximum(np.linalg.norm(value,axis=-1,keepdims=True),1e-30)

def template_check():
    edges = {}
    for triangle in PATTERN:
        for a,b in zip(triangle,np.roll(triangle,-1)):
            key = tuple(sorted((int(a),int(b))))
            edges.setdefault(key,[]).append((int(a),int(b)))
    boundary = []
    for pair in edges.values():
        if len(pair)==1:boundary.extend(pair)
        elif len(pair)!=2 or pair[0] != pair[1][::-1]:raise ValueError('Invalid local roof disk.')
    if set(boundary)!={(0,1),(1,2),(2,3),(3,0)} or len(edges)!=11:
        raise ValueError('Roof changes original oriented boundary.')
    return dict(vertices=6,edges=11,triangles=6,Euler_disk=1,oriented_boundary=boundary,
        internal_edge_incidence='Each interior edge occurs twice with opposite direction.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();root=args.root.resolve()
    if (root/'RELIEF').exists() or (root/'RECEIPT.json').exists():raise FileExistsError('One existing relief preserved.')
    started=time.perf_counter();code_sha=digest(__file__)
    snapshot=root/'source_snapshot/experiments/comb_relief_20261014/run.py'
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    if snapshot.exists():raise FileExistsError('Earlier source snapshot preserved.')
    shutil.copyfile(__file__,snapshot)
    for name,checksum in EXPECTED.items():
        if digest(SOURCE/name)!=checksum:raise ValueError('Saved study source changed.')
    if digest(root/'MASK.npz')!=MASK_SHA:raise ValueError('Frozen broad fine-cell mask changed.')
    with np.load(SOURCE/'control_quad.npz',allow_pickle=False) as saved:
        xyz,q=saved['xyz'],saved['faces']
    nc,nq=len(xyz),len(q)
    with np.load(root/'MASK.npz',allow_pickle=False) as saved:weight=saved['quad_weight']
    if weight.shape!=(nq,) or not np.isfinite(weight).all() or weight.min()<0 or weight.max()>1:
        raise ValueError('Finite source-bound weight in [0,1] required.')
    with np.load(ORIGINAL/'evidence.npz',allow_pickle=False) as saved:
        px,py=saved['mirror_x_face_pairs'],saved['mirror_y_face_pairs']
        vx,vy=saved['mirror_x_vertex_pairs'],saved['mirror_y_vertex_pairs']
    ids=np.arange(nq,dtype=np.int64)
    for pair,count in ((px,nq),(py,nq),(vx,nc),(vy,nc)):
        if pair.shape!=(count,) or not np.array_equal(pair[pair],np.arange(count)):
            raise ValueError('Actual source mirror involutions required.')
    if not np.array_equal(px[py],py[px]) or not np.array_equal(vx[vy],vy[vx]):
        raise ValueError('Actual source mirrors must commute.')
    if not np.array_equal(weight,weight[px]) or not np.array_equal(weight,weight[py]):
        raise ValueError('Fine-cell mask lost actual symmetry.')
    pxy=px[py];rep=np.minimum(np.minimum(ids,px),np.minimum(py,pxy))
    fixed=(px==ids)|(py==ids)|(pxy==ids)
    selected=np.flatnonzero((weight>0)&~fixed)
    rank=np.full(nq,-1,np.int64);rank[selected]=np.arange(len(selected))
    canonical=selected[rep[selected]==selected]
    if len(selected)!=4*len(canonical):raise ValueError('Four-face source orbits required; fixed faces untouched.')
    r0=np.empty((len(selected),3),float);r1=np.empty_like(r0)
    corners=np.empty((len(selected),4),np.int64);odd=np.empty(len(selected),bool)
    heights=np.empty(len(selected),float);bad=np.zeros(nq,bool)
    print('BUILD',len(selected),'integral short ridges over broad fine-cell support',flush=True)
    for start in range(0,len(canonical),32768):
        f=canonical[start:start+32768];base_ids=q[f];p=xyz[base_ids];o=p.mean(1)
        edge=np.roll(p,-1,axis=1)-p
        source_cross=np.cross(edge,o[:,None,:]-p)
        n=unit(source_cross.sum(1))
        alt=(np.einsum('nki,ni->nk',source_cross,n)/np.maximum(np.linalg.norm(edge,axis=2),1e-30)).min(1)
        # Higher of the existing two diagonal midpoints determines direction.
        d=(p[:,0]+p[:,2])*.5-o
        rotate=(np.einsum('ni,ni->n',d,n)<0).astype(np.int64)
        order=(np.arange(4)[None,:]+rotate[:,None])%4
        oriented=np.take_along_axis(base_ids,order,axis=1)
        p=xyz[oriented]
        h=np.minimum(.65*weight[f]*alt,H*.0006)
        a=.4*p[:,0]+.6*o+h[:,None]*n
        c=.4*p[:,2]+.6*o+h[:,None]*n
        points=np.concatenate([p,a[:,None,:],c[:,None,:]],axis=1)
        tri=points[:,PATTERN]
        cross=np.cross(tri[:,:,1]-tri[:,:,0],tri[:,:,2]-tri[:,:,0])
        signed=np.einsum('nki,ni->nk',cross,n)
        safe=(signed>0).all(1)&np.isfinite(cross).all(axis=(1,2))&(alt>0)
        for mx,my in ((False,False),(True,False),(False,True),(True,True)):
            faces=f.copy();mapped=oriented.copy();aa=a.copy();cc=c.copy()
            if mx:faces=px[faces];mapped=vx[mapped];aa[:,0]*=-1;cc[:,0]*=-1
            if my:faces=py[faces];mapped=vy[mapped];aa[:,1]*=-1;cc[:,1]*=-1
            if not np.array_equal(np.sort(mapped,axis=1),np.sort(q[faces],axis=1)):
                raise ValueError('Canonical reflected corner IDs do not match actual paired source quad.')
            outward=mapped[:,[0,3,2,1]] if mx!=my else mapped
            cycle_ok=np.zeros(len(faces),bool)
            for shift in range(4):cycle_ok|=np.all(np.roll(outward,shift,axis=1)==q[faces],axis=1)
            if not cycle_ok.all():raise ValueError('Actual oriented quad boundary cycle differs after reflection.')
            ix=rank[faces]
            if (ix<0).any():raise ValueError('Incomplete symmetric source selection.')
            r0[ix],r1[ix],corners[ix],odd[ix],heights[ix]=aa,cc,mapped,mx!=my,h
            bad[faces]=~safe
    # One safety exclusion; no threshold or amplitude retry.
    valid=~bad[selected]
    selected,r0,r1,corners,odd,heights=(a[valid] for a in (selected,r0,r1,corners,odd,heights))
    rank.fill(-1);rank[selected]=np.arange(len(selected))
    if not len(selected):raise ValueError('No valid diagonal roof survived.')
    for label,axis,pair in (('x',0,px),('y',1,py)):
        for points in (r0,r1):
            reflected=points[rank[pair[selected]]].copy();reflected[:,axis]*=-1
            if not np.array_equal(points,reflected):raise ValueError('Actual ridge coordinate symmetry failed: '+label)
    minimum_area=float('inf');maxpitch=0.;wing=[];source_pitch=[]
    for start in range(0,len(selected),32768):
        end=min(len(selected),start+32768);p=xyz[corners[start:end]];o=p.mean(1)
        n=unit(np.cross(np.roll(p,-1,axis=1)-p,o[:,None,:]-p).sum(1))
        n[odd[start:end]]*=-1
        # n above comes from canonical-oriented mirrored cycles, so odd mirrors
        # need the same winding reversal as their six actual roof triangles.
        points=np.concatenate([p,r0[start:end,None,:],r1[start:end,None,:]],axis=1)
        tri=points[:,PATTERN]
        cross=np.cross(tri[:,:,1]-tri[:,:,0],tri[:,:,2]-tri[:,:,0])
        cross[odd[start:end]]*=-1
        signed=np.einsum('nki,ni->nk',cross,n)
        area=np.linalg.norm(cross,axis=2)*.5
        if (signed<=0).any() or not np.isfinite(area).all():raise ValueError('Actual reflected roof orientation failed.')
        minimum_area=min(minimum_area,float(area.min()))
        pitch=np.rad2deg(np.arccos(np.clip(np.einsum('nki,ni->nk',unit(cross),n),-1,1)))
        maxpitch=max(maxpitch,float(pitch.max()))
        wing.append(pitch[:,[1,4]].ravel().astype(np.float32))
        oldp=xyz[q[selected[start:end]]];oldc=oldp.mean(1)
        oldcross=np.cross(np.roll(oldp,-1,axis=1)-oldp,oldc[:,None,:]-oldp)
        oldn=unit(oldcross.sum(1))
        oldangle=np.rad2deg(np.arccos(np.clip(np.einsum('nki,ni->nk',unit(oldcross),oldn),-1,1)))
        source_pitch.append(oldangle.ravel().astype(np.float32))
    wing=np.concatenate(wing);source_pitch=np.concatenate(source_pitch)
    source_template=template_check()
    folder=root/'RELIEF';folder.mkdir()
    np.savez_compressed(folder/'ridge_state.npz',quad_ids=selected,oriented_corners=corners,
        ridge0=r0,ridge1=r1,odd_reflection=odd,height=heights,weight=weight[selected])
    print('SAVE',len(selected),'roofs; load actual source native boundary fans',flush=True)
    with np.load(SOURCE/'geometry.npz',allow_pickle=False) as saved:
        oldxyz,oldfaces=saved['xyz'],saved['faces']
    if not np.array_equal(oldxyz[:nc],xyz) or oldfaces.shape!=(4*nq,3) or len(oldxyz)!=nc+nq:
        raise ValueError('Actual source native/control association mismatch.')
    for start in range(0,nq,65536):
        end=min(nq,start+65536);fq=q[start:end];center=np.arange(start,end)+nc
        expected=np.stack([fq,np.roll(fq,-1,axis=1),np.broadcast_to(center[:,None],fq.shape)],axis=-1)
        if not np.array_equal(oldfaces[4*start:4*end].reshape(-1,4,3),expected):
            raise ValueError('Actual saved fan indices/oriented boundary differ.')
        if not np.array_equal(oldxyz[nc+start:nc+end],xyz[fq].mean(1)):
            raise ValueError('Source native centers are not recorded arithmetic fans.')
    nold=len(oldxyz);nnew=nold+len(selected)
    outxyz=np.empty((nnew,3),oldxyz.dtype);outxyz[:nold]=oldxyz
    outxyz[nc+selected]=r0;outxyz[nold:]=r1
    outfaces=np.empty((len(oldfaces)+2*len(selected),3),oldfaces.dtype);outfaces[:len(oldfaces)]=oldfaces
    for start in range(0,len(selected),65536):
        end=min(len(selected),start+65536);ix=np.arange(start,end)
        vertex_ids=np.column_stack([corners[start:end],nc+selected[start:end],nold+ix])
        tri=vertex_ids[:,PATTERN]
        tri[odd[start:end]]=tri[odd[start:end]][:,:,[0,2,1]]
        outfaces[(4*selected[start:end,None]+np.arange(4)).ravel()]=tri[:,:4].reshape(-1,3)
        outfaces[len(oldfaces)+2*start:len(oldfaces)+2*end]=tri[:,4:].reshape(-1,3)
    if not np.array_equal(outxyz[:nc],xyz) or not np.isfinite(outxyz).all():
        raise ValueError('Original controls changed or nonfinite output.')
    untouched=rank<0
    if not np.array_equal(outxyz[nc:nold][untouched],oldxyz[nc:nold][untouched]):
        raise ValueError('Unselected centers changed.')
    for start in range(0,nq,65536):
        end=min(nq,start+65536);keep=untouched[start:end]
        if not np.array_equal(outfaces[4*start:4*end].reshape(-1,4,3)[keep],oldfaces[4*start:4*end].reshape(-1,4,3)[keep]):
            raise ValueError('Unselected source fan indices changed.')
    xhash,fhash=ah(outxyz),ah(outfaces)
    nativepath=folder/'geometry.npz';np.savez_compressed(nativepath,xyz=outxyz,faces=outfaces)
    stats=dict(source_control_corners=nc,unchanged_control_corners=nc,changed_control_corners=0,
        source_native_vertices=nold,source_native_triangles=len(oldfaces),
        roof_quads=len(selected),source_quad_fraction=len(selected)/nq,
        added_native_vertices=len(selected),added_native_triangles=2*len(selected),
        source_fixed_face_orbits_left_untouched=int(np.count_nonzero(fixed&(weight>0))),
        unsafe_roof_quads_excluded=int(bad.sum()),minimum_new_triangle_area=minimum_area,
        minimum_roof_height=float(heights.min()),maximum_roof_height=float(heights.max()),
        height_quantiles=np.quantile(heights,[.1,.5,.9,.99]).tolist(),
        source_fan_pitch_quantiles_degrees=np.quantile(source_pitch,[.1,.5,.9,.99]).tolist(),
        roof_wing_pitch_quantiles_degrees=np.quantile(wing,[.1,.5,.9,.99]).tolist(),
        roof_wing_fraction_pitch_over15_degrees=float(np.mean(wing>15)),
        maximum_roof_pitch_degrees=maxpitch,exact_ridge_XY_coordinate_symmetry=True)
    validation=dict(control_corners_byte_identical=True,unselected_centers_and_faces_byte_identical=True,
        actual_source_fourfan_indices_checked=True,actual_mirror_corner_associations_checked=True,
        actual_oriented_boundary_cycles_checked=True,
        actual_roof_XY_coordinate_symmetry=True,all_new_roof_projected_signed_areas_positive=True,
        local_template=source_template,
        topology_scope='Each selected source disk replaced with same oriented outer boundary. Inherited closed one-component source connectivity; +1V,+3E,+2F per disk, no isolated ornaments. No global edge sort repeated.',
        limits='No global self-intersection or fabrication certificate. Native finish is not a control subdivision and is not automatically carried by future control refinement.')
    recipe=dict(stage='INTEGRAL_DIAGONAL_NATIVE_RELIEF_G7',source_growth_generation=7,added_G8=False,
        input='Same REVISED body as user-liked reference; original design baseline retained.',
        selection='Frozen broad fine warped-cell weight, no aspect or world-axis gates; no selective shading.',
        ridge='Choose actual higher source diagonal. R0=.4*A+.6*O+h*N; R1=.4*C+.6*O+h*N.',
        height='h=min(.65*weight*minimum_positive_source_fan_projected_altitude,H*.0006)',
        construction='Replace four fan triangles by six-triangle integral ridge disk. Reuse original center for R0, append one R1 per selected quad.',
        feather_scope='Weight feathers ridge height; discrete diagonal re-triangulation also changes the source nonplanar fan surface even as height approaches zero.',
        symmetry='Canonical actual face orbit, reflected original corner IDs and ridge coordinates, odd-reflection winding reversal. Fixed-face orbits unchanged.',
        changes='Native surface/topology only. All control corners and oriented quad boundaries unchanged. No Mandelbulb, external ornaments, Boolean or remesh.')
    after={name:digest(SOURCE/name) for name in EXPECTED}
    if after!=EXPECTED or digest(__file__)!=code_sha or digest(snapshot)!=code_sha:
        raise ValueError('Source data or executing code changed.')
    variant=dict(geometry=str(nativepath),geometry_sha256=digest(nativepath),xyz_sha256=xhash,faces_sha256=fhash,
        vertices=len(outxyz),triangles=len(outfaces),ridge_state=str(folder/'ridge_state.npz'),
        ridge_state_sha256=digest(folder/'ridge_state.npz'),validation=validation)
    write(root/'RECEIPT.json',dict(date='2026-10-14',timezone='Asia/Seoul',
        source_native_path=str(SOURCE/'geometry.npz'),source_native_geometry_sha256=EXPECTED['geometry.npz'],
        source_control_path=str(SOURCE/'control_quad.npz'),source_control_sha256=EXPECTED['control_quad.npz'],
        source_hashes_after=after,mask_path=str(root/'MASK.npz'),mask_sha256=MASK_SHA,
        measurement_path=str(root/'MEASUREMENT.json'),measurement_sha256=digest(root/'MEASUREMENT.json'),
        geometry_code_sha256={'experiments/comb_relief_20261014/run.py':code_sha},
        variants={'RELIEF':variant},statistics=stats,recipe=recipe,seconds=time.perf_counter()-started,
        visual_success='PENDING_MATCHED_ACTUAL_RENDERS'))
    print(json.dumps(stats),flush=True)

if __name__=='__main__':main()
