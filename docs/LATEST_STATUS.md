# Latest CHESHIRE status — 2026-10-10

Task36은 종료·검증·로컬 보존을 완료했다. 연구 종료 커밋은
`0b89c297647905023e49d029f611b26d7fecc6c4`, branch `experiment/task36-neutral-recursive`다.
이 문서는 그 이후 만든 별도 `pre-astra-baseline` handoff branch의 상태다.

**전체 조형: PARTIAL.** U01은 중립 사각 carrier에서 재귀 세부 접힘을 확보했고 W03는
body/cap coupling 분리로 큰 몸통·결속을 더 분명히 만들었다. U01의 G8 새 child basin은
13개 material 높이 중 3개, W03는 G7/G8 0/13이다. 초기 네 방향 판/외곽 상속은 남는다.

두 최종 후보는 각각 1310722 native 정점/2621440 삼각형, 전체 shared-pair interval 교차0,
실제 16개 단면 경고0, topology/symmetry/caps 검사를 통과했다. 공면·접선·boundary-only는
제외하며 fabrication/solid 인증은 아니다. T02의 이전 안전성 판정은 철회됐고 원본은 보존했다.

- 원본 전체 테스트: **979 passed, 59.58s**.
- 별도 Worktree 전체 테스트: **979 passed, 44.64s**. 초기 환경 경로 실패2건은 코드/기준 변경 없이 해결.
- U01/W03 각각 별도 bundle clone + producer overlay 재생성: G0–G8 **50 NPZ byte-exact**.
- 원본 preservation: Task36 시작 tracked869개 중 README/CURRENT_PATHS 두 안내만 변경,
  보호 Task35 자료7개 동일. Task36 source646/checkpoint2544/render296 identity 검증.
- 후속 handoff에서 기존 아카이브 source1515/image133의 기존 SHA도 모두 재확인했다.

[Astra 인수인계](ASTRA_HANDOFF.md), [연구 계보](astra/TASK_LINEAGE.md),
[대표 이미지](astra/IMAGES.md), [원본 경로](astra/LOCAL_FILES.csv), [최종 연구 결과](TASK36_RESULTS.md).
전체 로컬 데이터는 `E:/CHESHIRE_DATA/`, 원본 작업 폴더는 `C:/Users/USER/CHESHIRE`에 있다.
독립 Worktree는 `C:/Users/USER/CHESHIRE_ASTRA`, 새 실험은 `E:/CHESHIRE_DATA/astra/`를 사용한다.
Worktree 의존성 일부는 원래 venv/DLL을 읽으므로 완전한 offline 환경은 아니다.

GitHub `https://github.com/ChairArchi/CHESHIRE`는 공식 API에서 **public**으로 확인했다.
요청 조건에 따라 handoff branch/tag를 Push하지 않았다. main과 기존 연구 아카이브를 변경하지 않았다.
최종 handoff hash/bundle/검증은 `E:/CHESHIRE_DATA/astra_handoff/pre-astra-baseline/HANDOFF_FINAL_STATE.json`이다.
