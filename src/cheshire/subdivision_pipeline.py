"""Small explicit reference pipeline, independent of research artifact roots.

Task29 CC behavior stays in reference_subdivision unchanged. Dual subdivision
is opt-in. Persistent face roles are distinct from CC vertex stencil classes.
"""
from dataclasses import dataclass
from pathlib import Path
import copy
import numpy as np
from .reference_subdivision import ArrayMesh,subdivide,REFERENCE_COUPLED
from .dual_subdivision import doo_sabin,REFERENCE_DOO_SABIN


@dataclass
class SubdivisionState:
    mesh: ArrayMesh
    face_roles: np.ndarray

    def __post_init__(self):
        self.face_roles=np.asarray(self.face_roles)
        if self.face_roles.shape!=(len(self.mesh.faces),) or not np.isin(self.face_roles,[-1,0,1,2]).all():
            raise ValueError('Face roles must correspond to actual mesh faces.')
        self.face_roles=self.face_roles.astype(np.int8,copy=False)


def step(current,spec):
    """One declared step; return state, metadata, exact resolved operator arrays."""
    m=current.mesh;roles=current.face_roles
    if spec['generation']!=m.generation+1:raise ValueError('Step generation does not match checkpoint.')
    if spec['scheme']==REFERENCE_DOO_SABIN:
        out,r,meta,arrays=doo_sabin(m,spec['weights'],face_roles=roles,groups=spec.get('groups'),scale_mode=spec['scale'])
    elif spec['scheme']==REFERENCE_COUPLED:
        rule=copy.deepcopy(spec.get('intrinsic'))
        if rule and spec['generation']>spec.get('lock_end',100):rule.pop('lock_threshold',None)
        out,meta,arrays=subdivide(m,spec['row'],scale_mode=spec['scale'],intrinsic=rule)
        r=roles[arrays['parent_face']]
        parents=np.full((len(out.faces),4),-1,np.int64);parents[:,0]=arrays['parent_face']
        arrays.update(parent_faces=parents,input_face_roles=roles,output_face_roles=r)
    else:raise ValueError('Undeclared subdivision scheme.')
    return SubdivisionState(out,r),meta,arrays


def save_checkpoint(path,current,operator_state=None):
    """Refuse overwrites; store double geometry and the actual structural state."""
    path=Path(path);path.mkdir(parents=True,exist_ok=False);m=current.mesh
    np.savez_compressed(path/'mesh.npz',xyz=m.xyz,faces=m.faces,classes=m.classes,rest=m.rest,
        anchors=m.anchors,generation=m.generation,face_roles=current.face_roles)
    if operator_state is not None:np.savez_compressed(path/'operator_state.npz',**operator_state)


def load_checkpoint(path):
    """Read canonical files, or Task29/30 split-role research checkpoints."""
    path=Path(path)
    with np.load(path/'mesh.npz',allow_pickle=False) as z:
        m=ArrayMesh(*(z[k].copy() for k in ('xyz','faces','classes','rest','anchors')),int(z['generation']))
        roles=z['face_roles'].copy() if 'face_roles' in z else None
    if roles is None and (path/'face_roles.npz').exists():
        with np.load(path/'face_roles.npz',allow_pickle=False) as z:roles=z['face_roles'].copy()
    if roles is None:roles=np.full(len(m.faces),-1,np.int8)
    return SubdivisionState(m,roles)
