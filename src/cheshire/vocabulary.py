"""Task-21 isolated directional/roof vocabulary; official HDMola owns geometry."""
from collections import Counter,defaultdict
from copy import deepcopy
from dataclasses import dataclass,asdict
from functools import lru_cache
from math import dist,fsum,hypot,isfinite
from pathlib import Path

from compas.datastructures import Mesh
from .branching import BranchRouter,BranchSignatures,content_hash,ROLES,EXTRA_KEYS
from .ornament import (OrnamentStage,OrnamentRecipe,SELECTOR_KEYS,local_polygon,select_event_faces,
    topology_event,propagate_history,run_ornament)
from .mola import _load_backend,_check_mesh,_cross,_dot,_subtract
from .execution import check_execution_budget
from .lineage import LineageMap,ParentRef
from .validation import validate_lineage_coverage

NEW_OPERATORS={'DirectionalExtrusion','Roof'}
NEW_ROLES={'DIRECTIONAL_EXTRUSION_SIDE','DIRECTIONAL_EXTRUSION_CAP','RIDGE_SIDE','RIDGE_END'}
AXES={'horizontal':[1.,0.,0.],'vertical':[0.,0.,1.],'depth':[0.,1.,0.]}

def unit(v):
    length=hypot(*v)
    if not isfinite(length) or length<1e-10: raise ValueError('Degenerate directional basis.')
    return [x/length for x in v]

def local_frame(mesh,face,mode='horizontal',centerline=0.,basis=None):
    """Oriented first-triangle N, projected world tangent, ordered-edge fallback."""
    keys,center,scale,points,n,area=local_polygon(mesh,face)
    if mode not in {*AXES,'outward','normal'}: raise ValueError('Undeclared direction mode.')
    axis=list(basis if basis is not None else AXES.get(mode,AXES['horizontal']))
    sign=1
    if mode=='outward' and basis is None:
        # Exact centerline ties use the fixed positive world axis, never randomness.
        sign=-1 if center[0]<centerline else 1
        axis=[float(sign),0.,0.]
    elif mode=='outward': sign=-1 if axis[0]<0 else 1
    tangent=[axis[a]-_dot(axis,n)*n[a] for a in range(3)]; fallback=False
    if hypot(*tangent)<1e-7:
        # First nondegenerate projected ordered input edge; axis-aligned sign if possible.
        fallback=True
        for i,p in enumerate(points):
            edge=_subtract(points[(i+1)%len(points)],p)
            tangent=[edge[a]-_dot(edge,n)*n[a] for a in range(3)]
            if hypot(*tangent)>=1e-7: break
        for component in tangent:
            if abs(component)>1e-10:
                if component<0: tangent=[-v for v in tangent]
                break
    t1=unit(tangent); t2=unit(_cross(n,t1))
    return dict(N=n,T1=t1,T2=t2,preferred_axis=axis,mode=mode,center=center,scale=scale,
        ordered_corner_ids=list(keys),edge_fallback=fallback,outward_sign=sign,
        normal_contract='Oriented first-triangle normal; compatible with the verified Mola construction. No face flattening.')

@lru_cache(maxsize=1)
def new_backend(dll):
    _,metadata=_load_backend(dll)
    import clr
    from System import Array,Object,Single,Boolean
    assembly=clr.AddReference(dll); vec=assembly.GetType('Mola.Vec3',True)
    ctor=next(c for c in vec.GetConstructors() if [str(p.ParameterType.FullName) for p in c.GetParameters()]==['System.Single']*3)
    methods=[m for m in assembly.GetType('FaceSubdivision',True).GetMethods() if m.IsPublic and m.IsStatic]
    types={'DirectionalExtrusion':['Mola.Vec3[]','Mola.Vec3','System.Single','System.Boolean'],
        'Roof':['Mola.Vec3[]','System.Single','System.Single']}
    found={name:next(m for m in methods if str(m.Name)==('Extrude' if name=='DirectionalExtrusion' else name)
        and [str(p.ParameterType.FullName) for p in m.GetParameters()]==signature) for name,signature in types.items()}
    def vector(p): return ctor.Invoke(Array[Object]([Single(v) for v in p]))
    def execute(name,points,height,other):
        vectors=Array.CreateInstance(vec,len(points))
        for i,p in enumerate(points): vectors.SetValue(vector(p),i)
        args=[vectors,vector(other),Single(height),Boolean(True)] if name=='DirectionalExtrusion' else [vectors,Single(height),Single(other)]
        raw=found[name].Invoke(None,Array[Object](args))
        return [[[float(vec.GetField(a).GetValue(p)) for a in ('x','y','z')] for p in face] for face in raw]
    return execute,{**metadata,'vocabulary_signatures':{k:str(v) for k,v in found.items()}}

@dataclass(frozen=True)
class VocabularyStage:
    id:str
    operator:str
    parameters:dict
    selector:dict|None=None
    def __post_init__(self):
        if self.operator not in NEW_OPERATORS: OrnamentStage(self.id,self.operator,self.parameters,self.selector); return
        allowed={'height_ratio','direction_mode','normal_ratio','tangent_sign'} if self.operator=='DirectionalExtrusion' else {'height_ratio','gable_inset','direction_mode'}
        if not self.id or self.selector is None or set(self.selector)-SELECTOR_KEYS or set(self.parameters)-allowed: raise ValueError('Undeclared vocabulary stage.')
        p=self.parameters
        if not 0<float(p['height_ratio'])<=1.2 or not isfinite(float(p['height_ratio'])): raise ValueError('Task-local height_ratio must be in (0,1.2].')
        if p.get('direction_mode','horizontal') not in {*AXES,'outward','normal'}: raise ValueError('Undeclared direction mode.')
        if self.operator=='DirectionalExtrusion' and (not .15<=p.get('normal_ratio',.45)<=1 or p.get('tangent_sign',1) not in (-1,1)): raise ValueError('Positive normal component and deterministic tangent sign required.')
        if self.operator=='Roof' and not 0<=p.get('gable_inset',.2)<.45: raise ValueError('Noncollapsed gable inset required.')
    def to_data(self): return asdict(self)

@dataclass(frozen=True)
class VocabularyRule:
    id:str
    when:dict
    action:str
    parameters:dict
    def __post_init__(self):
        if not self.id or self.when.get('role') not in ROLES|NEW_ROLES or not self.when.get('event_stage'): raise ValueError('Constructive child role/stage required.')
        if set(self.when)-(SELECTOR_KEYS|EXTRA_KEYS|{'patch_mode','patch_min_faces','side_class','patch_basis'}): raise ValueError('Undeclared routing condition; manual IDs forbidden.')
        if self.when.get('patch_mode','face') not in ('face','connected'): raise ValueError('Only face-local or connected routing coordination is supported.')
        if self.when.get('patch_basis','world_axis') not in ('world_axis','mean_plane'): raise ValueError('Undeclared patch basis.')
        if self.when.get('normal_min',-1)>self.when.get('normal_max',1): raise ValueError('Reversed orientation interval.')
        if self.when.get('side_class') not in (None,'left','right','center'): raise ValueError('Undeclared centerline class.')
        if self.action=='quiet':
            if self.parameters: raise ValueError('Quiet has no geometry parameters.')
        else: VocabularyStage(self.id,self.action,self.parameters,{})

@dataclass(frozen=True)
class VocabularyTable:
    id:str
    rules:tuple[VocabularyRule,...]
    fallback:str='quiet'
    def __post_init__(self):
        if not self.id or not self.rules or len({r.id for r in self.rules})!=len(self.rules) or self.fallback!='quiet': raise ValueError('Ordered unique routes and quiet fallback required.')
    def to_data(self): return asdict(self)

@dataclass(frozen=True)
class VocabularyRecipe:
    id:str
    family:str
    mechanism:str
    backbone:dict
    backbone_stages:int
    steps:tuple
    reference_id:str='C07'
    finish_mode:str='FINISH_NONE'
    def __post_init__(self):
        base=OrnamentRecipe.from_data(self.backbone)
        if not self.id or not self.mechanism or not 1<=self.backbone_stages<=len(base.stages) or self.finish_mode!='FINISH_NONE': raise ValueError('Frozen prefix and explicit no terminal finish required.')
        if len({s.id for s in self.compile().stages})!=len(self.compile().stages): raise ValueError('Duplicate stage ID.')
    def compile(self):
        stages=list(OrnamentRecipe.from_data(self.backbone).stages[:self.backbone_stages])
        for s in self.steps:
            if isinstance(s,VocabularyTable):
                active=[r for r in s.rules if r.action!='quiet']
                if not active: raise ValueError('A table requires an event route; unmatched faces remain quiet.')
                stages.extend(VocabularyStage(s.id+'__'+r.id,r.action,r.parameters,{}) for r in active)
            else: stages.append(s)
        return OrnamentRecipe(self.id,self.family,self.mechanism,tuple(stages))
    def to_data(self):
        return dict(id=self.id,family=self.family,mechanism=self.mechanism,backbone=deepcopy(self.backbone),backbone_sha256=content_hash(self.backbone),
            backbone_stages=self.backbone_stages,reference_id=self.reference_id,finish_mode=self.finish_mode,
            steps=[dict(kind='branch_table',**s.to_data()) if isinstance(s,VocabularyTable) else dict(kind='subdivision',**asdict(s)) for s in self.steps])
    @classmethod
    def from_data(cls,data):
        if content_hash(data['backbone'])!=data['backbone_sha256']: raise ValueError('Backbone hash mismatch.')
        steps=[]
        for s in data['steps']:
            if s['kind']=='branch_table': steps.append(VocabularyTable(s['id'],tuple(VocabularyRule(**r) for r in s['rules']),s['fallback']))
            elif s['kind']=='subdivision': steps.append(OrnamentStage(**{k:v for k,v in s.items() if k!='kind'}))
            else: raise ValueError('Undeclared grammar step.')
        return cls(data['id'],data['family'],data['mechanism'],data['backbone'],data['backbone_stages'],tuple(steps),data.get('reference_id','C07'),data.get('finish_mode','FINISH_NONE'))

def routing_patches(mesh,faces,history,rule,centerline,events=()):
    """Connected role/history/orientation cohorts; never a multi-face operator."""
    mode=rule.parameters.get('direction_mode','horizontal'); groups=defaultdict(set)
    event_map={e['id']:e for e in events}
    for f in faces:
        n=mesh.face_normal(f); axis=max(range(3),key=lambda a:abs(n[a])); sign=1 if n[axis]>=0 else -1
        row=history[f]; side=-1 if mesh.face_centroid(f)[0]<centerline else 1
        signature=(tuple(sorted(row['source'])),tuple(row['roles']),axis,sign,side if mode=='outward' else 0)
        groups[signature].add(f)
    patches=[]
    for signature,remaining in sorted(groups.items()):
        while remaining:
            seed=min(remaining); component={seed}; remaining.remove(seed); queue=[seed]
            if rule.when.get('patch_mode','face')=='connected':
                while queue:
                    current=queue.pop()
                    for f in sorted(mesh.face_neighbors(current)):
                        if f in remaining: remaining.remove(f); component.add(f); queue.append(f)
            ordered=sorted(component)
            preferred=list(AXES.get(mode,AXES['horizontal']))
            if mode=='outward': preferred=[float(signature[-1]),0.,0.]
            mean_n=unit([fsum(mesh.face_normal(f)[a]*mesh.face_area(f) for f in ordered) for a in range(3)])
            if rule.when.get('patch_basis','world_axis')=='mean_plane':
                tangent=[preferred[a]-_dot(preferred,mean_n)*mean_n[a] for a in range(3)]
                preferred=(unit(tangent) if hypot(*tangent)>1e-7 else local_frame(mesh,ordered[0],mode,centerline)['T1'])
            ancestor_ids=sorted({e for f in ordered for e in history[f]['events']})
            matching_ids=[e for e in ancestor_ids if event_map.get(e,{}).get('stage')==rule.when['event_stage']]
            root_ids=[e for e in ancestor_ids if e in event_map and not event_map[e]['parent_event_ids']]
            patches.append(dict(id=f'{rule.id}:patch:{len(patches):04d}',face_ids=ordered,face_count=len(ordered),
                source_C0_ancestry={k:fsum(history[f]['source'].get(k,0) for f in ordered)/len(ordered) for k in signature[0]},
                common_roles=[list(r) for r in signature[1]],orientation_class=[signature[2],signature[3]],
                common_route=rule.id,common_directional_basis=preferred,mean_face_normal=mean_n,basis_policy=rule.when.get('patch_basis','world_axis'),mode=rule.when.get('patch_mode','face'),
                matching_stage_event_ids=matching_ids,matching_parent_cell_count=len(matching_ids),root_event_ids=root_ids,root_event_count=len(root_ids),
                span_scope='Graph/positive ancestry support; multiple parent/root IDs alone do not prove a visible assembly.'))
    return patches

class VocabularyRouter(BranchRouter):
    def __init__(self,recipe):
        self.tables={s.id:s for s in recipe.steps if isinstance(s,VocabularyTable)}
        self.stages={s.id+'__'+r.id:(s.id,r.id) for s in self.tables.values() for r in s.rules if r.action!='quiet'}
        self.allocations={}; self.reports={}; self.face_routes={}
    def _allocate(self,table,mesh,history,source,families,events):
        available=set(mesh.faces()); assignments={}; report=[]
        operator={e['stage']:e['operator'] for e in events}; mean=fsum(mesh.face_area(f) for f in mesh.faces())/mesh.number_of_faces()
        xx=[source.vertex_coordinates(v)[0] for v in source.vertices()]; centerline=(min(xx)+max(xx))/2
        for rule in table.rules:
            selector={k:v for k,v in rule.when.items() if k in SELECTOR_KEYS}
            selection=select_event_faces(mesh,history,selector,source,families); matches=[]; extra=Counter()
            for f in selection['selected_ids']:
                if f not in available: continue
                w=rule.when; row=history[f]; reason=None
                if 'depth' in w and row['depth']!=w['depth']: reason='exact depth'
                elif 'parent_operator' in w and operator.get(w['event_stage'])!=w['parent_operator']: reason='parent operator'
                elif 'area_ratio_max' in w and mesh.face_area(f)>mean*w['area_ratio_max']: reason='area maximum'
                elif rule.action=='Roof' and len(mesh.face_vertices(f))!=4: reason='Roof requires quad'
                elif 'normal_axis' in w:
                    value=mesh.face_normal(f)['xyz'.index(w['normal_axis'])]; value=abs(value) if w.get('normal_absolute') else value
                    if not w.get('normal_min',-1)<=value<=w.get('normal_max',1): reason='orientation interval'
                if w.get('side_class') and reason is None:
                    x=mesh.face_centroid(f)[0]-centerline; side='left' if x< -1e-8 else 'right' if x>1e-8 else 'center'
                    if side!=w['side_class']: reason='centerline class'
                if reason: extra[reason]+=1
                else: matches.append(f)
            patches=routing_patches(mesh,matches,history,rule,centerline,events)
            for patch in patches: patch['id']=table.id+'__'+patch['id']
            accepted=[p for p in patches if p['face_count']>=rule.when.get('patch_min_faces',1)]
            # Coordinate cohorts without changing the existing constructor order.
            # Exact Task-20 fragments retain their original vertex/face keys.
            allowed={f for p in accepted for f in p['face_ids']}
            matches=[f for f in matches if f in allowed]
            available.difference_update(matches); assignments[rule.id]=matches
            for p in accepted:
                for f in p['face_ids']: self.face_routes[(table.id+'__'+rule.id,f)]={**p,'centerline':centerline}
            report.append(dict(rule=asdict(rule),matched_ids=matches,eligibility_excluded=selection['excluded_counts'],additional_excluded=dict(extra),patches=patches,
                rejected_small_patch_count=len(patches)-len(accepted)))
        report.append(dict(fallback=table.fallback,matched_ids=sorted(available)))
        self.allocations[table.id]=assignments; self.reports[table.id]=dict(table=table.to_data(),table_sha256=content_hash(table.to_data()),rules=report,
            semantics='First-match pre-round snapshot; connected cohorts coordinate only direction/route, never stitched.')

def vocabulary_event(mesh,history,stage,*,selected_faces,dll_path,budget,families=None,stage_index=1,routes=None):
    if stage.operator not in NEW_OPERATORS:
        return topology_event(mesh,history,stage,selected_faces=selected_faces,dll_path=dll_path,budget=budget,families=families,stage_index=stage_index)
    _check_mesh(mesh); selected=list(selected_faces)
    if len(set(selected))!=len(selected) or not set(selected)<=set(mesh.faces()): raise ValueError('Invalid event selection.')
    growth_f=sum(len(mesh.face_vertices(f)) if stage.operator=='DirectionalExtrusion' else 3 for f in selected)
    growth_v=sum(len(mesh.face_vertices(f)) if stage.operator=='DirectionalExtrusion' else 2 for f in selected)
    assessment=check_execution_budget(budget,input_faces=mesh.number_of_faces(),input_vertices=mesh.number_of_vertices(),estimated_output_faces=mesh.number_of_faces()+growth_f,
        estimated_output_vertices=mesh.number_of_vertices()+growth_v,current_generation=stage_index-1)
    if assessment['status']!='SAFE': raise ValueError('Event budget: '+' '.join(assessment['reasons']))
    output=Mesh(); vp={}; fp={}; cp={}; roles={}; events=[]
    for v in mesh.vertices():
        p=mesh.vertex_coordinates(v); output.add_vertex(key=v,x=p[0],y=p[1],z=p[2]); vp[v]=[ParentRef(v,1.)]; cp[v]=v
    chosen=set(selected)
    for f in mesh.faces():
        if f not in chosen: output.add_face(mesh.face_vertices(f),fkey=f); fp[f]=[ParentRef(f,1.)]
    nv=max(mesh.vertices(),default=-1)+1; nf=max(mesh.faces(),default=-1)+1; backend=None
    for f in selected:
        keys,center,scale,points,n,area=local_polygon(mesh,f); count=len(keys); p=stage.parameters
        route=(routes or {}).get((stage.id,f),{}); mode=p.get('direction_mode','horizontal')
        frame=local_frame(mesh,f,mode,route.get('centerline',0),route.get('common_directional_basis'))
        rotation=0
        if stage.operator=='Roof':
            if count!=4: raise ValueError('Roof is verified only on quads.')
            # Cyclic order changes only constructor axis; winding and source XYZ stay exact.
            candidates=[]
            for r in (0,1):
                q=points[r:]+points[:r]; a=[(q[0][i]+q[1][i])/2 for i in range(3)]; b=[(q[2][i]+q[3][i])/2 for i in range(3)]
                candidates.append(abs(_dot(unit(_subtract(b,a)),frame['T1'])))
            rotation=0 if candidates[0]>=candidates[1] else 1
            keys=keys[rotation:]+keys[:rotation]; points=points[rotation:]+points[:rotation]
            n=unit(_cross(_subtract(points[1],points[0]),_subtract(points[2],points[0])))
        height=p['height_ratio']*area; execute,backend=new_backend(str(Path(dll_path).resolve()))
        if stage.operator=='DirectionalExtrusion':
            ratio=1 if mode=='normal' else p.get('normal_ratio',.45); tangent=p.get('tangent_sign',1)*(max(0,1-ratio*ratio)**.5)
            direction=unit([ratio*n[a]+tangent*frame['T1'][a] for a in range(3)])
            raw=execute(stage.operator,points,height,direction)
            expected=[[q[a]+height*direction[a] for a in range(3)] for q in points]
            if list(map(len,raw))!=[4]*count+[count] or any(dist(q,t)>3e-6 for q,t in zip(raw[-1],expected)): raise ValueError('Directional cap order/offset contract failed.')
            upper=raw[-1]; newkeys=list(range(nv,nv+count)); nv+=count
            cycles=[[keys[i],keys[(i+1)%count],newkeys[(i+1)%count],newkeys[i]] for i in range(count)]+[newkeys]
            expected_faces=[[points[i],points[(i+1)%count],upper[(i+1)%count],upper[i]] for i in range(count)]+[upper]
            child_roles=['DIRECTIONAL_EXTRUSION_SIDE']*count+['DIRECTIONAL_EXTRUSION_CAP']
            parent_rows=[[ParentRef(k,1.)] for k in keys]; corner_rows=keys
            details=dict(unit_direction=direction,normal_ratio=ratio,tangent_component=tangent,normal_tangent_offset=[height*v*scale for v in direction])
        else:
            g=p.get('gable_inset',.2); raw=execute('Roof',points,height,g)
            if list(map(len,raw))!=[3,4,3,4]: raise ValueError('Roof constructor order contract failed.')
            upper=[raw[0][2],raw[2][2]]
            m0=[(points[0][a]+points[1][a])/2 for a in range(3)]; m1=[(points[2][a]+points[3][a])/2 for a in range(3)]
            oracle=[[(1-g)*m0[a]+g*m1[a]+height*n[a] for a in range(3)],[g*m0[a]+(1-g)*m1[a]+height*n[a] for a in range(3)]]
            if any(dist(q,t)>3e-6 for q,t in zip(upper,oracle)): raise ValueError('Roof ridge interpolation/normal oracle failed.')
            newkeys=[nv,nv+1]; nv+=2; a,b=newkeys
            cycles=[[keys[0],keys[1],a],[keys[1],keys[2],b,a],[keys[2],keys[3],b],[keys[3],keys[0],a,b]]
            expected_faces=[[points[0],points[1],upper[0]],[points[1],points[2],upper[1],upper[0]],[points[2],points[3],upper[1]],[points[3],points[0],upper[0],upper[1]]]
            child_roles=['RIDGE_END','RIDGE_SIDE','RIDGE_END','RIDGE_SIDE']
            parent_rows=[[ParentRef(k,w) for k,w in zip(keys,weights) if w>0] for weights in [[(1-g)/2,(1-g)/2,g/2,g/2],[g/2,g/2,(1-g)/2,(1-g)/2]]]
            ridge_axis=unit(_subtract(upper[1],upper[0]))
            corner_rows=[None,None]; details=dict(gable_inset=g,cyclic_rotation=rotation,constructor_normal=n,normal_offset=[height*v*scale for v in n],
                actual_ridge_axis=ridge_axis,ridge_alignment_abs_dot_T1=abs(_dot(ridge_axis,frame['T1'])),
                axis_contract='Choose the closer of two constructor quad directions by a winding-preserving cyclic rotation; no arbitrary ridge-axis rotation.')
        if any(not isfinite(v) for face in raw for q in face for v in q): raise ValueError('Nonfinite vocabulary output.')
        if any(dist(q,t)>3e-6 for face,expected in zip(raw,expected_faces) for q,t in zip(face,expected)): raise ValueError('Returned boundary/shared constructor corner contract failed.')
        for k,q,parents,corner in zip(newkeys,upper,parent_rows,corner_rows):
            xyz=[center[a]+scale*q[a] for a in range(3)]
            output.add_vertex(key=k,x=xyz[0],y=xyz[1],z=xyz[2]); vp[k]=parents; cp[k]=corner
        children=[]
        for cycle,role in zip(cycles,child_roles):
            output.add_face(cycle,fkey=nf); fp[nf]=[ParentRef(f,1.)]; roles[nf]=(stage.id,role); children.append(dict(id=nf,role=role)); nf+=1
        parent=history[f]
        events.append(dict(id=f'{stage.id}:parent:{f}',stage=stage.id,stage_index=stage_index,operator=stage.operator,parent_face=f,
            parameters=deepcopy(p),source_C0_ancestry=parent['source'],parent_family=(families or {}).get(f),parent_event_ids=parent['events'],
            ornament_depth=parent['depth']+1,children=children,local_frame=frame,direction_details=details,
            routing_patch={k:v for k,v in route.items() if k!='face_ids'},height_world=height*scale,
            lineage_contract='Positive constructive pre-offset vertex parents; separately recorded directional/normal offset is not a semantic coefficient.'))
    lineage=LineageMap(vp,fp)
    if validate_lineage_coverage(mesh,output,lineage): raise ValueError('Incomplete event lineage.')
    _check_mesh(output)
    if output.is_closed()!=mesh.is_closed() or len(output.connected_vertices())!=len(mesh.connected_vertices()): raise ValueError('Vocabulary event changed boundary/components.')
    if output.number_of_faces()!=mesh.number_of_faces()+growth_f or output.number_of_vertices()!=mesh.number_of_vertices()+growth_v: raise ValueError('Actual counts differ from budget estimate.')
    next_history=propagate_history(history,fp)
    for e in events:
        for child in e['children']:
            k=child['id']; row=next_history[k]
            next_history[k]={**row,'events':tuple(sorted((*row['events'],e['id']))),'roles':tuple(sorted((*row['roles'],roles[k]))),'depth':e['ornament_depth']}
    return dict(mesh=output,history=next_history,lineage=lineage,events=events,corner_parents=cp,backend=backend,assessment=assessment)

def run_vocabulary(source,recipe,*,dll_path,budget,publish=None):
    tracker=BranchSignatures(source); router=VocabularyRouter(recipe)
    def retain(mesh,history,events,anchors,parents,vertex_parents,stage):
        tracker.advance(parents,stage); stage['branches']=tracker.diagnostics(history,events)
        if publish: publish(mesh,history,events,anchors,parents,vertex_parents,stage,tracker)
    def execute(mesh,history,stage,**kwargs): return vocabulary_event(mesh,history,stage,routes=router.face_routes,**kwargs)
    result=run_ornament(source,recipe.compile(),dll_path=dll_path,budget=budget,publish=retain,routing=router,event_executor=execute)
    result.update(signatures=tracker,branch_tables=router.reports)
    return result

def validate_morphology_library(data):
    """Validate small reusable serialized fragments, not a new geometry engine."""
    if data.get('version')!=1 or not isinstance(data.get('entries'),list): raise ValueError('Morphology library version/entries required.')
    ids=set()
    for entry in data['entries']:
        required={'id','source_recipe','source_stage_ids','required_input','operator_sequence','known_failure_boundaries','visual_intent','lineage_contract','successful_geometry_sha256'}
        if not required<=set(entry) or entry['id'] in ids: raise ValueError('Incomplete or duplicate morphology fragment.')
        ids.add(entry['id'])
        if not entry['source_stage_ids'] or not entry['operator_sequence'] or len(entry['successful_geometry_sha256'])!=64: raise ValueError('Actual successful construction evidence required.')
        for s in entry['operator_sequence']:
            if s.get('kind')=='branch_table':
                VocabularyTable(s['id'],tuple(VocabularyRule(**r) for r in s['rules']),s['fallback'])
            else: VocabularyStage(**{k:v for k,v in s.items() if k!='kind'})
    return content_hash(data)
