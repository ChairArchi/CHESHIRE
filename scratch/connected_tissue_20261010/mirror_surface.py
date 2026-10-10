"""Shared-edge positive-half clipping, adapted from CHESHIRE gateflow.symmetry.

Works on an open midsurface before thickening, without flattening or remeshing.
"""
import numpy as np
def reflect(vertices,faces):
 v=np.asarray(vertices);d=v[:,0].copy();d[np.abs(d)<1e-10]=0
 points=[];lookup={};polygons=[]
 def add(a,b=None):
  if b is None or d[a]==0:b=a
  elif d[b]==0:a=b
  a,b=sorted((int(a),int(b)));key=(a,b)
  if key not in lookup:
   t=0. if a==b else d[a]/(d[a]-d[b]);p=(1-t)*v[a]+t*v[b]
   if a!=b or d[a]==0:p[0]=0
   lookup[key]=len(points);points.append(p)
  return lookup[key]
 for face in faces:
  q=np.array(face)
  if np.all(d[q]==0):continue
  crossings=sum(d[a]*d[b]<0 for a,b in zip(q,np.roll(q,-1)))
  pieces=[q] if crossings<=2 else [q[[0,i,i+1]] for i in range(1,len(q)-1)]
  for piece in pieces:
   ids=[]
   for a,b in zip(piece,np.roll(piece,-1)):
    if d[a]>=0:ids.append(add(a))
    if d[a]*d[b]<0:ids.append(add(a,b))
   ids=list(dict.fromkeys(ids))
   if len(ids)>=3:polygons.append(ids)
 xyz=np.array(points);off=np.flatnonzero(xyz[:,0]!=0);mapping=np.arange(len(xyz));mapping[off]=len(xyz)+np.arange(len(off))
 mirrored=xyz[off].copy();mirrored[:,0]*=-1
 result=polygons+[mapping[q[::-1]].tolist() for q in polygons]
 partner=np.r_[mapping,off]
 return np.r_[xyz,mirrored].tolist(),result,partner.tolist()
