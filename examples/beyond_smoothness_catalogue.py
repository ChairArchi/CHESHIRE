"""Gate transfers freeze the original prefix and reuse declared old fragments."""
from copy import deepcopy
from pathlib import Path
from beyond_smoothness_verify import read,write
from beyond_smoothness_recipes import recipe

def gate_basic(root):
    source=read(root.resolve('inputs/C0.json')); xyz={v['id']:v['xyz'] for v in source['vertices']}
    floor=min(p[2] for p in xyz.values()); height=max(p[2] for p in xyz.values())-floor
    lintel=[f['id'] for f in source['faces'] if sum(xyz[v][2] for v in f['vertices'])/len(f['vertices'])>=floor+.74*height]
    map_a={'(3,3)':1.,'(4,4)':-.2}; map_b={'(3,3)':.5,'(4,4)':0.,'(6,6)':-.4,'(8,8)':.3}
    definitions=[
        ('Matched extra standard-CC control',{}, {},1,'ALL'),
        ('Matched old interpolation control, no attraction',dict(w1=-.7,w2=-1.4),{},1,'ALL'),
        ('Face motif term alone on frozen mixed topology',dict(w6=.15),map_a,1,'ALL'),
        ('Edge motif term alone on frozen mixed topology',dict(w7=.3),map_a,1,'ALL'),
        ('Sparse valence3 edge compression',dict(w7=.4),{'(3,3)':1.},1,'ALL'),
        ('Face/edge attraction with restrained original interpolation',dict(w1=-.4,w2=-.8,w6=.12,w7=.25),map_a,1,'ALL'),
        ('Opposite motif values reverse the mixed-junction movement',dict(w1=-.4,w2=-.8,w6=.12,w7=.25),{'(3,3)':-1.,'(4,4)':.2},1,'ALL'),
        ('High-valence junctions deflect separately from cap corners',dict(w1=-.4,w2=-.8,w6=.15,w7=.3),map_b,1,'ALL'),
        ('Lintel-source support isolates motif action above the opening',dict(w1=-.4,w2=-.8,w6=.15,w7=.3),map_b,1,dict(source_face_ids=lintel)),
        ('Inherited inner-cap roles isolate folding before more ornament',dict(w1=-.4,w2=-.8,w6=.15,w7=.3),map_a,1,dict(event_stage='event_2',role='INNER_CAP')),
        ('Existing frame-side ancestry organizes the motif action',dict(w1=-.4,w2=-.8,w6=.12,w7=.25),map_a,1,dict(event_stage='event_2',role='FRAME_SIDE')),
        ('A second motif generation tests persistence without any Mola finish',dict(w1=-.4,w2=-.8,w6=.12,w7=.25),map_a,2,'ALL'),
        ('Eq7 attenuation separates a stronger first fold from weaker later placement',dict(w1=-.4,w2=-.8,w6=dict(mode='EQ7_TREND',a=.16,b=-.06,q=1),w7=dict(mode='EQ7_TREND',a=.35,b=-.15,q=1)),map_a,2,'ALL'),
        ('Eq7 growing edge contrast with weaker face term tests boundary retention',dict(w1=-.4,w2=-1.4,w6=.06,w7=dict(mode='EQ7_TREND',a=.15,b=.15,q=2)),map_b,2,'ALL'),
        ('Later verified V/F/E stencil plus motif explores large angular panel junctions',dict(w1=-.6,w2=-1.8,w3=-.6,w4=.3,w6=.08,w7=.2),map_a,2,'ALL'),
        ('Transfer the sharpest valid C26 control neighborhood literally',dict(w1=-.7,w2=-2.8,w6=.25,w7=.65),map_a,1,'ALL'),
        ('Less corner rounding with limited mixed-junction displacement',dict(w1=-.7,w2=-2.2,w6=.1,w7=.3),map_b,1,'ALL'),
        ('Tiny normal depth on a repositioned substrate',dict(w1=-.4,w2=-1.4,w6=.12,w7=.3,wf=.005,we=-.002,wp=.002),map_a,1,'ALL'),
        ('Source-supported valence6/8 alternation tests connected seam structure',dict(w1=-.6,w2=-1.8,w6=.18,w7=.3),{'(3,3)':.3,'(6,6)':.5,'(7,7)':-.4,'(8,8)':-.35},1,dict(source_face_ids=lintel)),
        ('Explicit strong boundary case retains failure evidence',dict(w1=-.7,w2=-2.8,w6=.5,w7=.85),{'(3,3)':1.,'(4,4)':-.4,'(6,6)':.5},1,'ALL')]
    out=[recipe(f'G1_{i:02d}','G1','C07',h,w,u,generations=g,scope=s) for i,(h,w,u,g,s) in enumerate(definitions,1)]
    for i,(base,duration,mode) in enumerate([(6,1,'SOURCE_EDGE_ENDPOINT_CORNERS'),(6,3,'SOURCE_EDGE_ENDPOINT_CORNERS'),
            (9,1,'INPUT_MOTIF_CORNERS'),(9,3,'INPUT_MOTIF_CORNERS'),(17,1,'INPUT_MOTIF_CORNERS'),(17,3,'INPUT_MOTIF_CORNERS'),
            (15,1,'SOURCE_EDGE_ENDPOINT_CORNERS'),(15,3,'INPUT_MOTIF_CORNERS')],1):
        r=deepcopy(out[base-1]); r.update(id=f'G2_{i:02d}',family='G2',hypothesis=f'{r["hypothesis"]}; first {duration} sharp iterations lock the declared {mode} input group.')
        # Repeat the single-row schedule for two added generations; preserve explicit trends where already present.
        if r['schedule']['generations']==1:
            weights={k:[v,v] for k,v in r['schedule']['rows'][0].items()}
            fresh=recipe(r['id'],'G2','C07',r['hypothesis'],weights,r['u_map'],duration,generations=2,scope=r['scope']); r=fresh
        r['locks']=dict(mode=mode,iterations=duration)
        if mode=='INPUT_MOTIF_CORNERS': r['locks']['motifs']=['(3,3)']
        out.append(r)
    for r in out: write(root.resolve('study/recipes/'+r['id']+'.json'),r)
    return out

def gate_compositions(root,selected):
    """Only call after actual pure-transfer review. Six Roof, eight nested, eight ordered cases."""
    hero=read(root.resolve('inputs/ORDERED_recipe.json')); bases=[read(root.resolve('study/recipes/'+n+'.json')) for n in selected]
    if not bases: raise ValueError('Actual useful pure gate transfers required.')
    out=[]
    for i in range(6):
        r=deepcopy(bases[i%len(bases)]); r.update(id=f'G3_{i+1:02d}',family='G3',hypothesis='Verified Task21 Roof on a reviewed angular substrate; cap versus frame versus original side targets.')
        role,stage=[('INNER_CAP','event_2'),('FRAME_SIDE','event_2'),('EXTRUSION_SIDE','event_1')][i//2]
        r['finish']=[dict(id='sharp_roof',operator='Roof',parameters=dict(height_ratio=.12 if i%2==0 else .18,gable_inset=.2,direction_mode='vertical' if role!='FRAME_SIDE' else 'horizontal'),
            selector=dict(z_min=.74,z_max=1.3,role=role,event_stage=stage,normal_y_min=.25,area_ratio_min=.5))]; out.append(r)
    for i in range(8):
        r=deepcopy(bases[i%len(bases)]); r.update(id=f'G4_{i+1:02d}',family='G4',hypothesis='Existing Task20 nested constructive fragment on the reviewed sharp substrate, no smoothing finish.')
        fragment=[hero['steps'][1]] if i<4 else [hero['steps'][1],hero['steps'][2]]
        if i%2: fragment=[hero['steps'][0],*fragment]
        r['finish']=deepcopy(fragment); out.append(r)
    for i in range(8):
        r=deepcopy(bases[i%len(bases)]); r.update(id=f'G5_{i+1:02d}',family='G5',input='ORDERED_CORE',hypothesis='Exact Task21 pre-ridge core; insert reviewed motif placement before reusing the original two Roof routing tables.')
        # Ordinary-resolution transfer is one global added generation (74176 faces before Roof).
        r['schedule']=recipe('unused','G5','ORDERED_CORE','finite',r['schedule']['rows'][0],r['u_map'],generations=1)['schedule']
        if i==6:
            r['u_map']={'(3,3)':-.4,'(4,4)':.15,'(6,6)':.3,'(8,8)':-.2}
            r['hypothesis']+=' Reverse the exceptional/regular motif relation as a matched alternative.'
        elif i==7:
            r['scope']=dict(event_stage='event_2',role='INNER_CAP')
            weights={**r['schedule']['rows'][0],'w6':.2,'w7':.22}
            r['schedule']=recipe('finite','G5','ORDERED_CORE','finite',weights,generations=1)['schedule']
            r['hypothesis']+=' Restrict motif movement to inherited inner-cap support with a different face/edge balance.'
        r['finish']=deepcopy(hero['steps'][-2:]); out.append(r)
    for r in out: write(root.resolve('study/recipes/'+r['id']+'.json'),r)
    return out

def gate_junction_followups(root):
    """Four hypotheses after weak initial transfers, not a new operator search."""
    definitions=[
        ('Uniform edge pull tests whether the present quad seams retain connected creases',
            dict(w1=-.7,w2=-2.8,w7=.7),{'(3,3)':1.,'(4,4)':1.,'(6,6)':1.,'(8,8)':1.}),
        ('Reverse exceptional corners against the regular valence4 field',
            dict(w1=-.7,w2=-2.8,w6=.2,w7=.6),{'(3,3)':-.5,'(4,4)':1.,'(6,6)':.3,'(8,8)':-.3}),
        ('Existing later-generation stencil emphasizes eligible junctions rather than new cap relief',
            dict(w1=-.7,w2=-2.8,w3=-1.2,w4=.6,w6=.15,w7=.4),{'(3,3)':.5,'(4,4)':.1,'(6,6)':-.25,'(8,8)':.25}),
        ('Literal high-valence input-corner locking targets seams without tagging all cap corners',
            dict(w1=-.7,w2=-2.2,w6=.1,w7=.3),{'(3,3)':.5,'(4,4)':0.,'(6,6)':-.4,'(8,8)':.3})]
    out=[]
    for i,(h,w,u) in enumerate(definitions,21):
        r=recipe(f'G1_{i:02d}','G1','C07',h,w,u,generations=1)
        if i==24: r['locks']=dict(mode='INPUT_MOTIF_CORNERS',iterations=1,motifs=['(6,6)','(8,8)'])
        write(root.resolve('study/recipes/'+r['id']+'.json'),r); out.append(r)
    return out

def refine(root,selected):
    """Three bounded variants for six observed finalists, each fully serialized."""
    if len(selected)!=6: raise ValueError('Six reviewed finalists required.')
    out=[]
    for j,name in enumerate(selected,1):
        base=read(root.resolve('study/recipes/'+name+'.json'))
        for k in range(1,4):
            r=deepcopy(base); rows=r['schedule']['rows']; n=len(rows)
            values={weight:[row[weight] for row in rows] for weight in rows[0]}
            r.update(id=f'R{j}_{k}',family='REFINEMENT',refines=name)
            if k==1:
                r['u_map']={motif:value*.8 if motif!='(4,4)' else value*.5 for motif,value in r['u_map'].items()}
                change='attenuate exceptional motif values; reduce regular-class deflection'
            elif k==2:
                values['w6']=dict(mode='EQ7_TREND',a=values['w6'][0]*.7,b=-.01 if n>1 else 0.,q=2)
                values['w7']=dict(mode='EQ7_TREND',a=values['w7'][0]*.85,b=-.012 if n>1 else 0.,q=2)
                values['w2']=[value*.9 for value in values['w2']]
                change='finite quadratic attenuation of face/edge displacement and reduced old corner extrapolation'
            else:
                values['w6']=[value*.8 for value in values['w6']]
                values['w7']=[value*1.1 for value in values['w7']]
                for finish in r['finish']:
                    if finish.get('operator')=='Roof': finish['parameters']['height_ratio']*=.75
                change='shift face/edge balance toward a crease; restrain explicit Roof height'
            r['schedule']=recipe('finite','R',r['input'],'finite',values,generations=n)['schedule']
            r['hypothesis']=base['hypothesis']+'; refinement: '+change
            write(root.resolve('study/recipes/'+r['id']+'.json'),r); out.append(r)
    return out
