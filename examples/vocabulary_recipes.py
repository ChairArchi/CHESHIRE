"""Task-21 structured grammar families; exact saved Task-20 values, no grids."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples'))
from subdivision_capability_study import read
from cheshire.vocabulary import VocabularyRule as Rule,VocabularyTable as Table,VocabularyRecipe as Recipe

def references():
    recipes=read(ROOT/'studies/task20/recipes.json')
    return dict(C07=read(ROOT/'studies/task20/backbone.json')['recipe'],A03=recipes['F_A03_CONTRAST'],D02=recipes['F_D02_CONTRAST'],HERO=recipes['HERO_ROLE_ASSEMBLY'])

def base_steps(reference):
    if reference=='C07': return []
    return deepcopy(references()[reference]['steps'])

def direction(height=.22,axis='horizontal',normal=.5,sign=1):
    return dict(height_ratio=height,direction_mode=axis,normal_ratio=normal,tangent_sign=sign)

def roof(height=.20,axis='horizontal',gable=.20):
    return dict(height_ratio=height,direction_mode=axis,gable_inset=gable)

def rule(name,role,action,parent='event_2',depth=2,parameters=None,patch='connected',**gates):
    when=dict(role=role,event_stage=parent,depth=depth,z_min=.08,z_max=1.3,patch_mode=patch)
    when.update(gates)
    return Rule(name,when,action,
        parameters if parameters is not None else direction() if action=='DirectionalExtrusion' else roof() if action=='Roof' else dict(width_ratio=.08) if action=='InsetFrame' else dict(height_ratio=.16,fraction=.30) if action=='TaperedExtrusion' else {})

def table(name,*rules): return Table(name,tuple(rules),'quiet')

def make(id,family,text,steps,reference='C07'):
    data=dict(id=id,family=family,mechanism=text,reference_id=reference,backbone=references()['C07'],
        backbone_sha256=read(ROOT/'studies/task20/backbone.json')['recipe_sha256'] if 'recipe_sha256' in read(ROOT/'studies/task20/backbone.json') else None,
        backbone_stages=5,finish_mode='FINISH_NONE',steps=base_steps(reference)+[dict(kind='branch_table',**s.to_data()) if isinstance(s,Table) else s for s in steps])
    from cheshire.branching import content_hash
    data['backbone_sha256']=content_hash(data['backbone'])
    return Recipe.from_data(data)

def pure_recipes():
    recipes=[]
    specs=[('FRAME_SIDE','event_2',2,'C07',direction(.24,'horizontal',.55),{}),
        ('FRAME_SIDE','event_2',2,'C07',direction(.24,'vertical',.45),{}),
        ('EXTRUSION_SIDE','event_1',1,'C07',direction(.20,'outward',.45),{}),
        ('INNER_CAP','event_2',2,'C07',direction(.18,'horizontal',.55),{}),
        ('FRAME_SIDE','event_2',2,'C07',direction(.22,'horizontal',.50,-1),{}),
        ('EXTRUSION_SIDE','event_1',1,'HERO',direction(.18,'outward',.55),{}),
        ('FRAME_SIDE','descend__side_child',4,'HERO',direction(.16,'horizontal',.55),{}),
        ('EXTRUSION_CAP','descend__cap_child',4,'HERO',direction(.18,'vertical',.55),{}),
        ('INNER_CAP','event_2',2,'C07',direction(.18,'normal',1),{}),
        ('FRAME_SIDE','event_2',2,'C07',direction(.18,'outward',.55),dict(normal_axis='z',normal_min=0))]
    for i,(role,parent,depth,ref,p,gates) in enumerate(specs,1):
        recipes.append(make(f'A_D{i:02d}','PURE_DIRECTION',f'Isolated {p["direction_mode"]} straight fin on {role} of exact {ref}; remaining branches quiet.',
            [table('new',rule('fin',role,'DirectionalExtrusion',parent,depth,p,**gates))],ref))
    specs=[('INNER_CAP','event_2',2,'C07',roof(.22,'horizontal'),{}),('INNER_CAP','event_2',2,'C07',roof(.22,'vertical'),{}),
        ('FRAME_SIDE','event_2',2,'C07',roof(.14,'horizontal'),{}),('EXTRUSION_SIDE','event_1',1,'C07',roof(.20,'vertical'),{}),
        ('INNER_CAP','event_2',2,'C07',roof(.22,'outward'),{}),('EXTRUSION_CAP','descend__cap_child',4,'HERO',roof(.18,'horizontal'),{}),
        ('INNER_CAP','descend__side_child',4,'HERO',roof(.16,'vertical'),{}),('FRAME_SIDE','event_2',2,'C07',roof(.16,'vertical'),dict(normal_axis='z',normal_min=.2)),
        ('EXTRUSION_SIDE','event_1',1,'HERO',roof(.16,'horizontal'),{}),('FRAME_SIDE','event_2',2,'C07',roof(.14,'outward'),dict(normal_axis='z',normal_absolute=True,normal_max=.35))]
    for i,(role,parent,depth,ref,p,gates) in enumerate(specs,1):
        recipes.append(make(f'A_R{i:02d}','PURE_RIDGE',f'Isolated aligned {p["direction_mode"]} ridge on {role} of exact {ref}; no finish.',
            [table('new',rule('crest',role,'Roof',parent,depth,p,**gates))],ref))
    assert len(recipes)==20
    return recipes

def composition_recipes():
    """Fifty discrete order/role/region combinations after pure operator review."""
    result=[]
    def add(family,i,text,steps,reference='C07'):
        result.append(make(f'B{family}_{i:02d}',f'B{family}',text,steps,reference))
    cap_words=['InsetFrame','TaperedExtrusion','Roof','quiet','InsetFrame','TaperedExtrusion','Roof','InsetFrame','DirectionalExtrusion','Roof']
    axes=['horizontal','vertical','outward','horizontal','vertical','outward','horizontal','vertical','outward','depth']
    # B1: cap language and selected lateral sibling/older-side growth.
    for i,(cap,axis) in enumerate(zip(cap_words,axes),1):
        side_role='EXTRUSION_SIDE' if i in (3,5,7,10) else 'FRAME_SIDE'
        side_parent='event_1' if side_role=='EXTRUSION_SIDE' else 'event_2'; depth=1 if side_parent=='event_1' else 2
        gates=dict(normal_axis='z',normal_min=.25) if i in (2,4,6,8) else dict(normal_axis='y',normal_min=.55) if i in (3,5,7,10) else dict(normal_axis='x',normal_min=.2)
        cap_params=roof(.18,axis) if cap=='Roof' else direction(.12,axis,.75) if cap=='DirectionalExtrusion' else None
        steps=[table('compose',rule('cap','INNER_CAP',cap,parameters=cap_params),rule('lateral',side_role,'DirectionalExtrusion',side_parent,depth,direction(.12,axis,.75),**gates))]
        if i in (2,5,8):
            role='INNER_CAP' if cap=='InsetFrame' else 'EXTRUSION_CAP'
            steps.append(table('micro',rule('cap_child',role,'Roof','compose__cap',3,roof(.14,'horizontal'))))
        if i in (6,9): steps.append(table('micro',rule('fin_cap','DIRECTIONAL_EXTRUSION_CAP','InsetFrame','compose__lateral',depth+1)))
        add(1,i,f'{cap} cap language plus selected {axis} lateral {side_role}; explicit quiet remainder.',steps)
    # B2: ridge on a parent panel, followed by differentiated slope/end words.
    combinations=[('RIDGE_SIDE','InsetFrame','horizontal'),('RIDGE_SIDE','TaperedExtrusion','vertical'),
        ('RIDGE_END','DirectionalExtrusion','horizontal'),('RIDGE_END','DirectionalExtrusion','vertical'),
        ('RIDGE_SIDE','DirectionalExtrusion','outward'),('RIDGE_END','InsetFrame','outward'),
        ('RIDGE_SIDE','Roof','horizontal'),('RIDGE_SIDE','Roof','vertical'),
        ('RIDGE_SIDE','InsetFrame','outward'),('RIDGE_END','TaperedExtrusion','depth')]
    for i,(role,word,axis) in enumerate(combinations,1):
        parent_role='FRAME_SIDE' if i in (7,8) else 'INNER_CAP'
        steps=[table('crest',rule('panel',parent_role,'Roof',parameters=roof(.20,axis)))]
        params=direction(.16,axis,.70) if word=='DirectionalExtrusion' else roof(.13,'horizontal') if word=='Roof' else None
        gates=dict(normal_axis='z',normal_min=0) if i in (4,5,6,9) else {}
        steps.append(table('micro',rule('active',role,word,'crest__panel',3,params,**gates)))
        if i in (1,2,9): steps[-1]=table('micro',rule('active',role,word,'crest__panel',3,params,**gates),rule('end','RIDGE_END','DirectionalExtrusion','crest__panel',3,direction(.12,'vertical',.75),normal_axis='z',normal_min=.15))
        add(2,i,f'{axis} panel ridge gives {role} {word}; end/slope branches receive different morphology or quiet.',steps)
    # B3: directional cap prepares ridge/frame; strip is not faked after its rejection.
    specs=[('INNER_CAP','event_2',2,'horizontal','Roof'),('INNER_CAP','event_2',2,'vertical','Roof'),
        ('INNER_CAP','event_2',2,'outward','InsetFrame'),('FRAME_SIDE','event_2',2,'horizontal','Roof'),
        ('FRAME_SIDE','event_2',2,'vertical','InsetFrame'),('EXTRUSION_SIDE','event_1',1,'outward','Roof'),
        ('INNER_CAP','event_2',2,'depth','Roof'),('FRAME_SIDE','event_2',2,'outward','TaperedExtrusion'),
        ('INNER_CAP','event_2',2,'horizontal','InsetFrame'),('EXTRUSION_SIDE','event_1',1,'vertical','InsetFrame')]
    for i,(role,parent,depth,axis,word) in enumerate(specs,1):
        gates=dict(normal_axis='z',normal_min=.20) if role!='INNER_CAP' else {}
        steps=[table('fin',rule('primary',role,'DirectionalExtrusion',parent,depth,direction(.14,axis,.75),**gates)),
            table('micro',rule('cap','DIRECTIONAL_EXTRUSION_CAP',word,'fin__primary',depth+1,roof(.15,axis) if word=='Roof' else None))]
        if i in (2,7): steps.append(table('crown',rule('ends','RIDGE_END','DirectionalExtrusion','micro__cap',depth+2,direction(.16,'outward',.7),normal_axis='z',normal_min=0)))
        if i==9: steps.append(table('crown',rule('inner','INNER_CAP','Roof','micro__cap',depth+2,roof(.14,'vertical'))))
        add(3,i,f'{axis} straight cap on {role} prepares {word}; no unsupported strip boundary stitching.',steps)
    # B4: exact A03/D02 fragments plus new events, or DS preparation before micro.
    refs=['A03','D02','A03','D02','A03','D02','A03','D02','A03','D02']
    for i,reference in enumerate(refs,1):
        if reference=='A03': role,parent,depth=('EXTRUSION_CAP','descend__cap_child',4) if i in (1,5,9) else ('INNER_CAP','descend__side_child',4)
        else: role,parent,depth='INNER_CAP','micro__cap',4
        word='Roof' if i in (1,2,3,6,9) else 'DirectionalExtrusion'; axis=axes[i-1]
        params=roof(.18,axis) if word=='Roof' else direction(.14,axis,.75)
        steps=[table('new',rule('detail',role,word,parent,depth,params,**(dict(normal_axis='z',normal_min=0) if i in (3,4,7,8) else {})))]
        if i in (5,10):
            # Exact saved standard DS as a structural handoff, followed by real cap event.
            ds=deepcopy(references()['D02']['steps'][0]); ds['id']='prep_DS'
            steps.append(ds); steps.append(table('nested',rule('cap','DIRECTIONAL_EXTRUSION_CAP','InsetFrame','new__detail',5,family='FACE_DERIVED')))
        add(4,i,f'Exact {reference} language adds {axis} {word}; existing macro unchanged.',steps,reference)
    # B5: exact Hero core, augment a current role rather than rewriting macro.
    specs=[('EXTRUSION_SIDE','event_1',1,'Roof','vertical'),('EXTRUSION_SIDE','event_1',1,'DirectionalExtrusion','outward'),
        ('EXTRUSION_CAP','older__flank',2,'Roof','horizontal'),('EXTRUSION_CAP','older__flank',2,'DirectionalExtrusion','vertical'),
        ('FRAME_SIDE','descend__side_child',4,'Roof','horizontal'),('INNER_CAP','descend__side_child',4,'Roof','vertical'),
        ('EXTRUSION_CAP','descend__cap_child',4,'Roof','outward'),('EXTRUSION_SIDE','descend__cap_child',4,'DirectionalExtrusion','vertical'),
        ('EXTRUSION_SIDE','split__side',3,'DirectionalExtrusion','outward'),('EXTRUSION_CAP','older__flank',2,'Roof','outward')]
    for i,(role,parent,depth,word,axis) in enumerate(specs,1):
        params=roof(.18,axis) if word=='Roof' else direction(.14,axis,.75)
        gates=dict(normal_axis='z',normal_min=0) if i in (2,4,5,8) else {}
        steps=[table('new',rule('branch',role,word,parent,depth,params,**gates))]
        if i in (3,7,10): steps.append(table('micro',rule('ends','RIDGE_END','DirectionalExtrusion','new__branch',depth+1,direction(.14,'vertical',.75),normal_axis='z',normal_min=0)))
        add(5,i,f'Exact Hero adds {word} on {role} at event depth {depth}; {axis} alignment and quiet neighboring branches.',steps,'HERO')
    assert len(result)==50
    return result

def assembly_recipes():
    """Fourteen connected-patch direction/crest compositions, including controls."""
    recipes=[]
    specs=[('FRAME_SIDE','Roof','horizontal','mean_plane',2),('FRAME_SIDE','Roof','vertical','mean_plane',2),
        ('FRAME_SIDE','Roof','outward','mean_plane',4),('FRAME_SIDE','DirectionalExtrusion','horizontal','mean_plane',4),
        ('FRAME_SIDE','DirectionalExtrusion','vertical','mean_plane',4),('INNER_CAP','Roof','horizontal','world_axis',1),
        ('EXTRUSION_SIDE','Roof','vertical','mean_plane',2),('EXTRUSION_SIDE','DirectionalExtrusion','outward','mean_plane',2),
        ('FRAME_SIDE','Roof','horizontal','world_axis',1),('FRAME_SIDE','Roof','depth','mean_plane',2),
        ('FRAME_SIDE','Roof','outward','mean_plane',8),('FRAME_SIDE','DirectionalExtrusion','outward','mean_plane',8),
        ('FRAME_SIDE','Roof','vertical','mean_plane',4),('EXTRUSION_SIDE','Roof','outward','mean_plane',2)]
    for i,(role,word,axis,basis,minfaces) in enumerate(specs,1):
        parent='event_1' if role=='EXTRUSION_SIDE' else 'event_2'; depth=1 if parent=='event_1' else 2
        params=roof(.24,axis,.12) if word=='Roof' else direction(.15,axis,.75)
        gates=dict(patch_basis=basis,patch_min_faces=minfaces)
        if i in (3,5,7,8,10,11,12,14): gates.update(normal_axis='z',normal_min=0)
        # Left and right get different words, connected only by actual mesh adjacency.
        routes=[rule('assembly',role,word,parent,depth,params,**gates)]
        if i==13:
            routes=[rule('left',role,'Roof',parent,depth,roof(.24,'horizontal'),side_class='left',**gates),
                rule('right',role,'DirectionalExtrusion',parent,depth,direction(.15,'vertical',.75),side_class='right',**gates)]
        steps=[table('patch',*routes)]
        if word=='Roof' and i in (1,2,7,10,11,14):
            steps.append(table('micro',rule('end','RIDGE_END','DirectionalExtrusion','patch__assembly',depth+1,direction(.14,'vertical',.75),normal_axis='z',normal_min=.15),
                rule('slope','RIDGE_SIDE','InsetFrame','patch__assembly',depth+1,normal_axis='y',normal_min=.3)))
        if word=='DirectionalExtrusion' and i in (4,8,12): steps.append(table('micro',rule('cap','DIRECTIONAL_EXTRUSION_CAP','Roof','patch__assembly',depth+1,roof(.16,axis))))
        recipes.append(make(f'C{i:02d}','C_ASSEMBLY',f'Connected {role} cohort of >= {minfaces} faces uses {basis} {axis} {word}; graph/ancestry grouping, no fusion.',steps))
    assert len(recipes)==14
    return recipes
