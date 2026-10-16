"""Show the actual pre-growth input and the separate two-Mandel source fields."""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image, ImageDraw, ImageFont


def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source=Path('C:/Users/USER/CHESHIRE/scratch/OVERLAP_G0_INITIAL_RENDER_20261017')
    fields=Path('C:/Users/USER/CHESHIRE/scratch/TWO_MANDEL_INITIAL_COLORED_20261017')
    root=Path('E:/CHESHIRE_DATA/exports/20261017/COLUMN_OVERLAPPING_FOLD_LAYOUT/INITIAL_REVIEW')
    root.mkdir(parents=True,exist_ok=False)
    records=[]
    for folder in [source,fields/'RENDER']:
        receipt=read(folder/'RENDER_RECEIPT.json')
        for row in receipt['items']:
            if sha(Path(row['geometry']))!=row['source_sha256']:raise ValueError('Rendered source changed.')
            for im in row['images']:
                path=Path(im['path'])
                if sha(path)!=im['sha256']:raise ValueError('Actual PNG changed.')
                dest=root/path.name;shutil.copyfile(path,dest)
                if sha(dest)!=im['sha256']:raise ValueError('Actual PNG copy differs.')
                records.append(dict(id=row['id'],view=im['view'],path=str(dest),sha256=sha(dest),source= row['geometry'],source_sha256=row['source_sha256']))
    # Same crop and scale for each actual G0 image; no geometry alteration.
    board=Image.new('RGB',(1560,1030),'#15191d');d=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',30)
    small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',23)
    d.text((24,20),'후속 성장 전 G0 · 같은 생성식의 초기 접힘 입력',font=font,fill='#eeeae2')
    d.text((24,66),'같은 49링 샘플 · 같은 카메라와 배율 · 하단 판 형태가 남아 있는 수정 전 입력',font=small,fill='#b8c5ce')
    for i,(ident,label) in enumerate([('K00','원래 두 주접힘'),('K06','여섯 중첩 주접힘'),('K08','여덟 중첩 주접힘')]):
        x=10+520*i
        picture=Image.open(root/(ident+'_whole.png')).convert('RGB').crop((300,65,900,1145))
        picture.thumbnail((490,800),Image.Resampling.LANCZOS)
        board.paste(picture,(x+(500-picture.width)//2,118))
        d.text((x+24,940),ident+' · '+label,font=small,fill='#eeeae2')
    board.save(root/'G0_INITIAL_COMPARISON.png')
    shutil.copyfile(fields/'SOURCE_FIELDS_RECEIPT.json',root/'SOURCE_FIELDS_RECEIPT.json')
    description=dict(kind='ACTUAL_INITIAL_INPUT_AND_SEPARATE_MANDEL_SOURCE_FIELDS',
        raw_column_stage='G00_INPUT',native_input_control_vertices=786,native_input_triangles=3136,
        column_G0_K08_M2_equals_K08=True,
        blue_orange_meaning='Separate original finite Mandel source fields, not two overlapping column G0 meshes.',
        field_stage_iterations=8,field_surface='Sampled original finite classifier isosurface at recorded level .501.',
        original_bottom_plate_not_removed=True,main_model_replaced=False,actual_image_bindings=records)
    (root/'INITIAL_PREVIEW_RECEIPT.json').write_text(json.dumps(description,ensure_ascii=False,indent=2),encoding='utf8')
    print(root)


if __name__=='__main__':main()
