"""Write the current comparison recommendation and a native-image contact sheet."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont


def main():
    root=Path('E:/CHESHIRE_DATA/experiments/inherited_rule_variations_20261017')
    selection=dict(default_compare='I05',preferred_candidates=['I05','I03'],user_adopted=False,
        meaning='Visual comparison defaults and recommendations only; not adopted geometry.',
        notes_ko=['I05: 가지 출발 위치를 낮춰 긴 상부 흐름과 접합부 배치가 가장 분명하게 달라진다.',
            'I03: 불균일한 네 접힘 구간이 큰 접힘과 작은 접힘의 길이를 나누며 기존 계열을 유지한다.',
            'I04: 실제 지역 분할 형상은 바뀌지만 전체 실루엣 차이는 작다.',
            'I02: 넓은 컵 형태가 덩어리로 읽힐 가능성이 있다.',
            'I06: 상부 단과 띠가 강조돼 후속 장식과 함께 복잡해질 수 있다.'],
        stage='G04_NEUTRAL',reviewed_native_views=14,late_detail_applied_in_this_comparison=False)
    (root/'SELECTION.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf8')
    source=root/'COMPARISON_RENDER'
    output=Path('C:/Users/USER/CHESHIRE/scratch/INHERITED_SEVEN_G4_QUICKVIEW_20261017.png')
    labels=['I00 · 기존 기준','I01 · 두 접힘 위치 이동','I02 · 길이가 다른 세 구간',
        'I03 · 불균등한 네 구간','I04 · 지역 분할점 배분','I05 · 가지 출발 위치 이동','I06 · 방향·폭·분할 배분']
    font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',24)
    small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',19)
    board=Image.new('RGB',(1568,1432),(21,25,29));draw=ImageDraw.Draw(board)
    draw.text((32,20),'같은 초기 형상 · 같은 생성 연산 | 지점 / 불균등 구간 / 방향 / 분할점 배분',font=font,fill=(242,240,232))
    draw.text((32,62),'G4 초기 단계 실제 메시 비교 · 같은 카메라와 배율 · 세부 장식 전',font=small,fill=(175,185,194))
    for i,label in enumerate(labels):
        x=16+(i%4)*388;y=112+(i//4)*648
        picture=Image.open(source/('I%02d_whole.png'%i)).convert('RGB').crop((300,65,900,1145))
        picture.thumbnail((360,600),Image.Resampling.LANCZOS)
        board.paste(picture,(x+(372-picture.width)//2,y+38))
        draw.text((x+6,y),label,font=small,fill=(242,240,232))
    draw.text((1190,890),'비교 추천',font=font,fill=(242,240,232))
    draw.text((1190,940),'I05 · 가지 위치와 긴 흐름',font=small,fill=(205,215,222))
    draw.text((1190,978),'I03 · 접힘 구간의 리듬',font=small,fill=(205,215,222))
    draw.text((1190,1050),'I04의 전체 차이는 작음',font=small,fill=(175,185,194))
    board.save(output)
    print(output)


if __name__=='__main__':main()
