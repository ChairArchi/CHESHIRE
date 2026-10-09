"""Supplement noncoplanar intersection intervals missed by strict edge hits.

An intersection segment can end on edges of BOTH triangles. Strict interior
barycentric edge tests then reject every endpoint despite interior overlap.
This separately authored test clips both triangles against the other's plane
and checks positive interval overlap along their common line. Both triangles
must straddle the other plane: coplanar and boundary-only contacts stay excluded.
Input coordinates use the existing mesh-span normalization; tol=1e-10.
"""
import numpy as np


def interval_hits(a,b,tol=1e-10):
    a,b=np.broadcast_arrays(np.asarray(a,float),np.asarray(b,float))
    na=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);nb=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
    la=np.linalg.norm(na,axis=1);lb=np.linalg.norm(nb,axis=1)
    na=na/np.maximum(la[:,None],1e-30);nb=nb/np.maximum(lb[:,None],1e-30)
    da=np.sum((a-b[:,0,None])*nb[:,None],axis=2)
    db=np.sum((b-a[:,0,None])*na[:,None],axis=2)
    line=np.cross(na,nb);length=np.linalg.norm(line,axis=1)
    eligible=(la>0)&(lb>0)&(length>tol)&(da.min(1)<-tol)&(da.max(1)>tol)&(db.min(1)<-tol)&(db.max(1)>tol)
    result=np.zeros(len(a),bool);ids=np.flatnonzero(eligible)
    if not len(ids):return result
    axis=line[ids]/length[ids,None]
    def clipped_range(points,distance):
        projection=np.sum(points*axis[:,None],axis=2)
        lo=np.full(len(ids),np.inf);hi=-lo.copy()
        for k in range(3):
            j=(k+1)%3;near=abs(distance[:,k])<=tol
            lo=np.minimum(lo,np.where(near,projection[:,k],np.inf));hi=np.maximum(hi,np.where(near,projection[:,k],-np.inf))
            cross=distance[:,k]*distance[:,j]<0
            denominator=distance[:,k]-distance[:,j]
            fraction=distance[:,k]/np.where(cross,denominator,1.)
            value=projection[:,k]+fraction*(projection[:,j]-projection[:,k])
            lo=np.minimum(lo,np.where(cross,value,np.inf));hi=np.maximum(hi,np.where(cross,value,-np.inf))
        return lo,hi
    alo,ahi=clipped_range(a[ids],da[ids]);blo,bhi=clipped_range(b[ids],db[ids])
    result[ids]=np.minimum(ahi,bhi)-np.maximum(alo,blo)>tol
    return result
