"""Exact native AABB broad phase; original Task33 NumPy narrow phase unchanged.

Candidate pairs remain ascending (a,b), with the same sphere/AABB/shared-vertex
filters. No sampling, triangle merging, tolerance changes or predicate ports.
"""
import json,subprocess,tempfile,sys,os
from pathlib import Path
from time import perf_counter
import numpy as np
REPO=Path(__file__).resolve().parents[1];sys.path[:0]=[str(REPO/'tools'),str(REPO/'examples')]
from task33_contacts import batch_hits
from cheshire.task32_morphology import triangles
from task33_preserve import sha
BUILD=Path('C:/Users/Public/Documents/ESTsoft/CreatorTemp/task36_bvh')


def helper():
    source=REPO/'tools/native/Task36Bounds.cs';digest=sha(source);dest=BUILD/digest[:16];exe=dest/'Task36Bounds.exe'
    if not exe.exists():
        dest.mkdir(parents=True,exist_ok=True)
        result=subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/optimize+','/out:'+str(exe),str(source)],capture_output=True,text=True)
        (dest/'compile.json').write_text(json.dumps(dict(code=result.returncode,stdout=result.stdout,stderr=result.stderr,source_sha256=digest),indent=2))
        if result.returncode:raise RuntimeError('Local AABB helper compilation failed: '+result.stdout)
    return exe


def read_exact(stream,n):
    chunks=[];left=n
    while left:
        block=stream.read(left)
        if not block:raise EOFError('AABB helper ended inside a binary batch.')
        chunks.append(block);left-=len(block)
    return b''.join(chunks)


def contacts(mesh,cap=256,interval=False):
    start=perf_counter();tri=triangles(mesh);span=float(np.ptp(mesh.xyz,axis=0).max())
    if span<=0:raise ValueError('Nonzero extent required.')
    p=(mesh.xyz[tri]-mesh.xyz.min(0))/span;centre=p.mean(1);radius=np.linalg.norm(p-centre[:,None],axis=2).max(1)
    bounds=np.column_stack([p.min(1),p.max(1)]);exe=helper();pairs=[];checked=0;raw=0
    fd,name=tempfile.mkstemp(prefix='task36_bounds_',suffix='.bin',dir=BUILD);os.close(fd);temporary=Path(name)
    try:
        with temporary.open('wb') as out:
            out.write(np.array([len(tri)],'<i4').tobytes());out.write(bounds.astype('<f8',copy=False).tobytes());out.write(tri.astype('<i4',copy=False).tobytes())
        process=subprocess.Popen([str(exe),str(temporary)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while True:
                count=int(np.frombuffer(read_exact(process.stdout,4),dtype='<i4')[0])
                if count==0:break
                ab=np.frombuffer(read_exact(process.stdout,count*8),dtype='<i4').reshape(-1,2);a,b=ab.T;raw+=len(a)
                eligible=np.linalg.norm(centre[a]-centre[b],axis=1)<=radius[a]+radius[b]+1e-10
                a=a[eligible];b=b[eligible];checked+=len(a)
                hit=batch_hits(p[a],p[b])
                if interval:
                    from task36_triangle_interval import interval_hits
                    remaining=~hit
                    hit[remaining]|=interval_hits(p[a[remaining]],p[b[remaining]])
                pairs.extend(np.column_stack([a[hit],b[hit]]).tolist())
                if len(pairs)>=cap:pairs=pairs[:cap];break
        finally:
            if process.poll() is None and len(pairs)>=cap:process.terminate()
            process.wait();error=process.stderr.read().decode(errors='replace')
            process.stdout.close();process.stderr.close()
        if process.returncode and len(pairs)<cap:raise RuntimeError('AABB helper failed: '+error)
    finally:
        if not temporary.resolve().is_relative_to(BUILD.resolve()):raise ValueError('Unexpected temporary payload path.')
        temporary.unlink(missing_ok=True)
    return dict(transverse_contacts=len(pairs),pairs=pairs,sample_triangles=len(tri),total_triangles=len(tri),all_triangles_sampled=True,
        cap_reached=len(pairs)==cap,cap=cap,checked_nonadjacent_AABB_pairs=checked,raw_AABB_pairs=raw,seconds=perf_counter()-start,
        broad_phase='Exact native AABB BVH, ascending pairs; same bounding-sphere filter; unchanged Task33 batch_hits.',
        helper_source_sha256=sha(REPO/'tools/native/Task36Bounds.cs'),helper_binary_sha256=sha(exe),
        narrow_phase='Task33 strict edge hits UNION Task36 positive noncoplanar interior interval overlap' if interval else 'Unchanged Task33 strict edge hits',
        exclusions='Shared vertices, coplanar, boundary/tangent contacts excluded; no sampling or triangle merging. Zero does not certify solid geometry.')
