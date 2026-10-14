"""Compose only the requested two matched views against actual current FLOW03."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('end_context_actual_renderer', HERE/'render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=render.ROOT)
    parser.add_argument('--phase', choices=('context','detail'), default='context')
    parser.add_argument('--variant', action='append')
    args = parser.parse_args()
    binding = render.source_binding()
    candidates, candidate_binding = render.variants(args.root, binding)
    chosen = args.variant or list(candidates)
    views = ('close_oblique','body_oblique') if args.phase == 'context' else ('front','macro')
    output = args.root/('images_'+args.phase)
    if output.exists():
        raise FileExistsError('Earlier actual comparison preserved.')
    code = render.code_hashes()
    states = [dict(state='CURRENT_FLOW03', images=binding['images'], saved_geometry=binding['saved_geometry'])]
    for name in chosen:
        path = args.root/(name+'_FLAT')/args.phase/'receipt.json'
        r = render.read_json(path)
        expected = candidates[name]
        if (r['state'] != name or r['phase'] != args.phase or r['source_binding'] != binding or
                r['candidate_binding'] != candidate_binding or r['saved_geometry'] != expected or
                r['code_sha256'] != code or r['geometry_unchanged_by_renderer'] is not True or
                r['all_flat'] is not True or r['geometry_processing'] is not False or
                r['normal_maps'] is not False or r['modifiers'] != []):
            raise ValueError('Actual focused renderer provenance differs.')
        render.frozen.previous.display_proof(r, expected)
        render.require_close(r['conditions'], binding['conditions'])
        if set(r['actual_views']) != set(views) or {i['view'] for i in r['images']} != set(views):
            raise ValueError('Only the chosen two frozen views required.')
        snap = r['source_snapshot']
        if any(render.digest(snap[k]) != snap['sha256'] for k in ('source','snapshot')):
            raise ValueError('Executed renderer snapshot changed.')
        images = []
        for item in r['images']:
            view = item['view']
            png = path.parent/item['filename']
            if png.name != view+'.png' or render.digest(png) != item['sha256']:
                raise ValueError('Actual focused PNG differs.')
            render.scaffold.verify_native_png(png)
            render.require_close(r['actual_views'][view], binding['actual_views'][view], 'matched-camera.'+view)
            images.append(dict(view=view, path=str(png), sha256=item['sha256'], receipt=str(path),
                receipt_sha256=render.digest(path), reused_reference=False))
        states.append(dict(state=name, images=images, saved_geometry=expected, display_readback=r['display_readback']))
    output.mkdir(parents=True)
    source = Path(__file__).resolve()
    snap = args.root/'source_snapshot_boards'/source.name
    snap.parent.mkdir(parents=True, exist_ok=True)
    if snap.exists() and render.digest(snap) != render.digest(source):
        raise ValueError('Earlier actual boards snapshot changed.')
    if not snap.exists():
        shutil.copyfile(source,snap)
    title = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27)
    label = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    boards = []
    for view in views:
        canvas=Image.new('RGB',(900*len(states),1020),'white')
        draw=ImageDraw.Draw(canvas)
        draw.text((24,12),'SPAN | '+view+' | current FLOW03 / saved source replay',font=title,fill='black')
        sources=[]
        for i,state in enumerate(states):
            draw.text((900*i+24,61),state['state']+' | all-flat',font=label,fill='black')
            item=next(x for x in state['images'] if x['view']==view)
            if render.digest(item['path']) != item['sha256']:
                raise ValueError('Actual source PNG changed while composing.')
            with Image.open(item['path']) as image:
                if image.size != (900,900):
                    raise ValueError('Actual 900-square native image required.')
                canvas.paste(image.convert('RGB'),(900*i,105))
            sources.append(dict(state=state['state'],**item))
        path=output/('SPAN_'+view+'.png')
        canvas.save(path)
        boards.append(dict(view=view,path=str(path),sha256=render.digest(path),sources=sources))
    proof=dict(passed=True,phase=args.phase,source_binding=binding,candidate_binding=candidate_binding,
        states=states,boards=boards,requested_views=list(views),reused_current_images=len(views),
        actual_new_images=len(views)*len(chosen),new_model_generation=False,geometry_processing=False,
        all_flat=True,normal_maps=False,modifiers=[],render_code=code,
        boards_code_sha256=render.digest(source),boards_snapshot=str(snap),
        comparison_scope='Actual current FLOW03 versus stored unmasked G7 source replay before FLOW. This changes overall carrier and later finish together; it is not an isolated end-only comparison.')
    for path in (output/'SOURCE_LIST.json',args.root/('RENDER_'+args.phase.upper()+'_VERIFICATION.json')):
        render.write(path,proof)
    print('END_CONTINUITY_MATCHED_PHASE_PASS',args.phase,len(boards),'boards',flush=True)


if __name__ == '__main__':
    main()
