"""Copy a compact review set; all actual geometry stays on E:. No hash audit."""
from pathlib import Path
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = Path('E:/CHESHIRE_DATA/column_detail_20261012')
BASE = Path('E:/CHESHIRE_DATA/directional_growth_20261012/OVERLAP/G03')
DOC = HERE.parents[1]/'docs/column_detail_20261012'

def main():
    images, technical = DOC/'images', DOC/'technical'
    images.mkdir(parents=True,exist_ok=True)
    technical.mkdir(parents=True,exist_ok=True)
    for file in (ROOT/'review').glob('*.png'):
        shutil.copy2(file,images/file.name)
    for file in (ROOT/'review').glob('*.json'):
        shutil.copy2(file,technical/file.name)
    for name in ('SOURCE_NOTES.md','PAPER_NOTES.md','topology_asset_notes.md'):
        file = HERE/name
        if file.exists():
            shutil.copy2(file,DOC/name)
    for file in (ROOT/'visual_review').glob('*.md'):
        shutil.copy2(file,technical/file.name)
    candidates = {}
    for family in ('CONTINUED','NESTED','NESTED_STRONG','RETURN_DETAIL','RETURN_HYBRID'):
        records = {}
        for folder in sorted((ROOT/family).glob('G[0-9][0-9]')):
            if not (folder/'generation.json').exists():
                continue
            key = family+'_'+folder.name
            shutil.copy2(folder/'generation.json',technical/(key+'.json'))
            entry = {kind:str(folder/file) for kind,file in (
                ('authoritative_triangle_mesh','geometry.npz'),('exchange_mesh','gate.ply'),
                ('checkpoint','checkpoint.npz'),('next_control','control_quad.npz'),
                ('operation_fields','operation_fields.npz'),('blender','column.blend'))}
            for kind in ('preview','detail'):
                entry[kind] = {file.stem:str(file) for file in (folder/kind).glob('*.png')}
            core = folder/'core_validation.json'
            if core.exists():
                shutil.copy2(core,technical/(key+'_core.json'))
                entry['core_validation'] = str(core)
            if (folder/'column.obj').exists():
                entry['obj'] = str(folder/'column.obj')
            records[folder.name] = entry
        candidates[family] = records
        for name in ('DESIGN_REVIEW.md','DESIGN_REVIEW.json','ACTUAL_REVIEW.md','ACTUAL_REVIEW.json'):
            file = ROOT/family/name
            if file.exists():
                shutil.copy2(file,technical/(family+'_'+name))
    index = dict(scope='Actual column-only detail comparisons; no gate or topology/Tissue experiment.',
        branch='experiment/column-detail-20261012', preserved_source=str(BASE),
        output_root=str(ROOT), code=str(HERE), candidates=candidates,
        format='geometry.npz float64 explicit triangles drive the actual renders. The legacy exchange filename gate.ply contains a column. Next control is separate from render fan centres.',
        checks='Light intermediate checks; core checks only on explicit selected geometry. No fabrication or exact-IAAC reproduction claim.',
        record_precedence='generation.json preserves generation-time status. Later core_validation.json and REPORT.md supersede its pending render or intersection status; geometry and thresholds were not changed.',
        paper_policy='Four user PDFs reviewed as optional references, not instructions. Originals and copyrighted figures are not included.',
        topology_assets='Audited only; no WINDOW_PATCH mesh/code execution or Tissue dependency work.',
        recommendation='Read REPORT.md; archived experiments are not automatic aesthetic successes.')
    (DOC/'INDEX.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf8')
    print('PACKAGED',DOC,flush=True)

if __name__ == '__main__':
    main()
