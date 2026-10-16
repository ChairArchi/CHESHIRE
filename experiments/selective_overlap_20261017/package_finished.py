"""Package reviewed native renders, final QA and reusable selective-overlap sources."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import shutil
import zipfile
from collect_replay_bundle import collect_replay_bundle, reproduction_instructions

HERE = Path(__file__).resolve().parent
EXP = Path('E:/CHESHIRE_DATA/experiments/selective_overlap_20261017')
OUT = Path('E:/CHESHIRE_DATA/exports/20261017/COLUMN_SELECTIVE_OVERLAP_FINISHED')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(b)
    return h.hexdigest()


def record(p):
    return dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)


def main(finish, qa, render):
    q = json.loads(qa.read_text(encoding='utf8'))
    if q.get('status') != 'PASS':
        raise ValueError('Final independent QA required.')
    models = sorted((OUT / 'models').glob('*.ply'))
    if len(models) != 1:
        raise ValueError('Exactly one selected final prototype required.')
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'DELIVERY.json').exists():
        raise FileExistsError('Preserve completed delivery.')
    review = OUT / 'review'
    review.mkdir(exist_ok=False)
    copied = []
    for src in [EXP / 'review_selected/G0_COMPARISON.png',
                EXP / 'review_selected/G0_SELECTED_COLOR.png'] + sorted(render.glob('*.png')):
        dst = review / src.name
        shutil.copyfile(src, dst)
        if sha(src) != sha(dst):
            raise ValueError('Review copy changed.')
        copied.append(record(dst))
    evidence = OUT / 'provenance'
    evidence.mkdir(exist_ok=False)
    sources = [EXP / 'source_candidates_v2/RECEIPT.json',
               EXP / 'source_candidates_v2/L08_PRIMARY_193/generation.json',
               EXP / 'actual_source_colors_v2/COLOR_PROOF.json',
               EXP / 'review_selected/BOARD_RECEIPT.json',
               EXP / 'G0_REVIEW_RENDER_v2/RENDER_RECEIPT.json',
               EXP / 'full_pipeline/L08_PRIMARY_193/RECEIPT.json',
               EXP / 'full_pipeline/L08_PRIMARY_193/G5_ONLY_RECIPE.json',
               EXP / 'full_pipeline/L08_PRIMARY_193/states/G05_DIRECTIONAL/G5_EXECUTION_RECEIPT.json',
               finish / 'RECEIPT.json', qa, render / 'RENDER_RECEIPT.json',
               Path('C:/Users/USER/CHESHIRE/scratch/SELECTIVE_193_G0_QA_FINAL_20261017.json')]
    for i, src in enumerate(sources):
        shutil.copyfile(src, evidence / ('%02d_' % i + src.name))
    readme = '''CHESHIRE · 선택적 겹침 완성 프로토타입

넓은 마디의 측면과 끝부분에 접힘을 집중하고, 원형의 잘록한 구간을 남깁니다.
초기 형상은 원형 / 이전 전면 겹침 / 선택한 국소 겹침을 동일한 193링으로 비교했습니다.
원래 큰 접힘 2개와 보조 접힘 3개를 유지하고, 넓은 구간 세 곳에 큰 접힘 6개를 추가했습니다.
원형의 단면에서 목 중심을 측정하고, 추가 접힘의 전체 적용 범위가 그 중심을 피하도록 배치합니다.
초기 형상의 목 중심 좌표 보존과 최종 마감의 G5 부모 보호는 별도 검증 항목입니다.

실제 진행: G0 → G1 → G2 → G3 주름/연결부 → G4 → 원 DIRECTIONAL G5 → 표면 마감.
시작 형상을 촘촘하게 샘플링하여 실제 G5에서 완성했습니다. 예전 G6/G7 회로 전체를 재생한 결과는 아닙니다.
만델벌브 유한 경계 프로파일과 실제 Paper/Tissue 높이 자산을 새 표면에 다시 평가했습니다.
기존 G7의 정점 번호나 장식 변위를 가져오지 않았으며, 표면 전체의 XYZ 스무딩은 하지 않았습니다.
티슈는 닫힌 표면의 얕은 요철로 전달됩니다. 원 논문 자산의 구멍·오버행 위상 전체를 이식한 것은 아닙니다.
메쉬 연결·면 방향·원본 좌표 대응·내보낸 파일의 전체 읽기 검사를 거쳤습니다. 제작 인증은 아닙니다.

review: 전체/확대 렌더, 초기 형상 비교, 색상 분류.
models: 실제 최종 네이티브 전체 PLY. 축소 메쉬가 아닙니다.
provenance: 실행 기록, 독립 검증, 렌더 원본 대응.
SELECTIVE_OVERLAP_ALGORITHM.zip: 재사용 컨트롤러, 생성/마감/검증 코드와 고정된 원 연산 스냅샷.
선정된 유한 필드 캐시와 작은 마감 자산은 포함합니다. 큰 중간 메쉬는 원 경로 및 SHA256으로 연결됩니다.
압축 파일은 현재 작업 환경의 복원용이며, 다른 PC에서의 독립 실행 검증은 하지 않았습니다.
'''
    (OUT / 'README.txt').write_text(readme, encoding='utf8')
    captions = {
        'L08_FINISHED_whole.png': '완성안 · 전체',
        'L08_FINISHED_oblique.png': '완성안 · 사선',
        'L08_FINISHED_crown.png': '완성안 · 상부',
        'L08_FINISHED_detail.png': '완성안 · 표면 확대',
        'L08_FINISHED_effects.png': '마감 분류 · 주황 원형 / 파랑 만델벌브 / 초록 티슈 / 회색 보호 구간',
        'G0_COMPARISON.png': '초기 형상 · 원형 / 이전 겹침안 / 선택한 겹침안',
        'G0_SELECTED_COLOR.png': '초기 겹침 분류 · 주황 원형 / 파랑 추가 접힘 / 회색 목 중심',
    }
    cards = ''.join('<figure><img src="review/'+html.escape(Path(row['path']).name, quote=True)+
                    '"><figcaption>'+html.escape(captions.get(Path(row['path']).name, Path(row['path']).stem))+
                    '</figcaption></figure>' for row in sorted(copied, key=lambda r:
                    (0 if Path(r['path']).name == 'L08_FINISHED_whole.png' else 1, Path(r['path']).name)))
    page = ('<!doctype html><html lang="ko"><meta charset="utf-8"><title>CHESHIRE · 선택적 겹침 완성안</title>'
            '<style>body{margin:0;background:#171d21;color:#edf1f4;font:17px/1.7 system-ui,sans-serif}'
            'main{max-width:1500px;margin:auto;padding:30px}h1{font-size:30px}a{color:#7bc5ff}'
            'figure{margin:28px 0}img{display:block;max-width:100%;max-height:1200px;margin:auto}'
            'figcaption{text-align:center;color:#c0cbd0;padding:10px}nav{display:flex;gap:24px;flex-wrap:wrap}</style>'
            '<main><h1>CHESHIRE · 선택적 겹침 완성안</h1><p>넓은 마디의 옆면과 끝을 겹치고, 잘록한 구간을 남겼습니다. '
            '선택한 초기 형상에 방향성 주름과 만델벌브·티슈 마감을 적용한 G5 기반 프로토타입입니다.</p><nav>'
            '<a href="models/'+html.escape(models[0].name, quote=True)+'">전체 모델 · PLY</a>'
            '<a href="SELECTIVE_OVERLAP_ALGORITHM.zip">알고리즘과 실행 기록</a><a href="README.txt">작업 설명</a></nav>'+cards+'</main></html>')
    (OUT / 'review.html').write_text(page, encoding='utf8')
    archive = OUT / 'SELECTIVE_OVERLAP_ALGORITHM.zip'
    used = set()
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        def add(path, name):
            if name in used:
                raise ValueError('Duplicate archive path: ' + name)
            used.add(name)
            z.write(path, name)
        bundle = collect_replay_bundle(add, finish=finish)
        z.writestr('REPLAY_BUNDLE_MANIFEST.json', json.dumps(bundle, ensure_ascii=False, indent=2))
        z.writestr('REPRODUCE.txt', reproduction_instructions(bundle))
        for path in sorted(evidence.glob('*')):
            add(path, 'provenance/' + path.name)
        add(OUT / 'README.txt', 'README.txt')
    delivery = dict(kind='CHESHIRE_SELECTIVE_OVERLAP_COMPLETED_G5_PROTOTYPE',
        status='COMPLETED', actual_final_subdivision_generation=5, selected='L08_PRIMARY_193',
        models=[record(p) for p in models], images=copied,
        review=record(OUT / 'review.html'),
        algorithm=record(archive), final_QA=record(qa), final_finish=record(finish / 'RECEIPT.json'),
        actual_geometry_rendered=True, main_model_replaced=False, user_adopted=False,
        fabrication_certified=False)
    (OUT / 'DELIVERY.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf8')
    print(OUT)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--finish', type=Path, required=True)
    p.add_argument('--qa', type=Path, required=True)
    p.add_argument('--render', type=Path, required=True)
    a = p.parse_args()
    main(a.finish, a.qa, a.render)
