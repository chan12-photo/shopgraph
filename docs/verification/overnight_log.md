# 야간 작업 기록 (2026-11-01 밤 ~ 11-02 새벽)

- 지시: 찬일 11/01 밤 "작업 1~7을 순서대로, 사람 판단이 필요한 작업만 멈추고 기록, 전체를 멈추지 말 것. 승인 여부는 묻지 말고 진행"
- 브랜치: w12-prep (w11-demo dd2164f에서 시작). main 합치기·push 없음. 저장소 밖 변경은 작업 5의 PR 본문 수정뿐
- 작업 시간: 01:12 시작 ~ 01:25 무렵 마지막 커밋
- 모든 작업에서 시연 장면의 기대 결과(추천 순위·점수·가중치·S4 순위·통계 값)를 계산·기록하지 않았고, 장면 확인용으로 프로그램을 돌리지 않았다
- graph.py·search.py·view.py·main.py·data.py와 기존 테스트, 계획서 본문은 바꾸지 않았다 (`git diff --stat dd2164f -- graph.py search.py view.py main.py data.py docs/project_plan.md tests/test_graph.py tests/test_search.py tests/test_recommend.py tests/test_view.py tests/test_flow.py` 결과 없음)
- 커밋마다 커밋 직전 작업 트리에서 `python -m unittest`를 돌리고, 커밋 뒤 그 커밋을 따로 체크아웃(detached worktree)해 다시 돌렸다. 두 번의 결과는 매번 같았다

## 작업별 상태

| 작업 | 상태 | 커밋 | 비고 |
|---|---|---|---|
| 1 demo_expected.md 양식 | 완료 | 973ed28 | 값 칸은 모두 빈칸. 장면 1 "그룹별 인원" 칸은 지시(장면 2~8)에 더해 넣음 (W12 장면 1 테스트가 볼 값) |
| 2 손계산 원자료표 | 완료 | 7277014 | data.py만 읽는 보조 스크립트 docs/verification/make_raw_by_group.py로 생성. 구매 행 122 = 원본 122 (행 수만 확인) |
| 3 tests/test_demo.py 틀 | 완료 | 4cc93a6 | 통과 131 / 미도래 8(전부 NotImplementedError). 장면 실행 경로는 실행하지 않음 (아래 "확인 못 한 것") |
| 4 plan_pending.md | 완료 (판단 필요 2건 포함) | 14df318 | 판단 필요: W11 19장 행의 날짜·결정자는 기대값 승인 때 확정 / 5.4 아래 입력 규칙 문단을 넣을지 |
| 5 PR #1·#2 본문 | 완료 | (저장소 커밋 없음) | "🤖 Generated with [Claude Code](…)" 줄만 지움. 두 PR 모두 OPEN, draft 그대로 |
| 6 report_materials.md | 완료 (판단 필요 1건 포함) | 112e4f0 | 판단 필요: "3판 확장 문서 9장"을 저장소 전 브랜치에서 찾지 못함 |
| 7 README 실행 방법 | 판정 받음: W14에서 반영(찬일 허락 후), README 안 고침 | 8a220c6 | 아래 "판정" 참고 |

## 판단 필요 (찬일)

1. **작업 7 README "실행 방법"**: 계획서 11.3.2와 CLAUDE.md가 "README.md의 다른 섹션은 W0 이후 고치지 않는다"(현재 상태 섹션만 예외)로 정해 README의 "## 실행"·"## 테스트" 절을 고치지 않았다. 붙여 넣을 문안은 docs/verification/readme_run_draft.md에 있다. 선택지: (가) 찬일이 직접 붙여 넣기 (나) 규칙 예외를 정한 뒤 [DOC] 커밋 (다) W14 문서화 단계로 미루기
2. **작업 6 "3판 확장 문서 9장"**: `git grep "3판\|확장 문서"`를 모든 로컬 브랜치에서 돌렸으나 없음. 저장소 밖 문서라면 위치를 알려 주면 보충한다. Downloads·Desktop의 shopgraph_starter 사본은 찬일 지시로 열지 않았다
3. **작업 4 plan_pending.md 끝의 2건**: W11 19장 행 확정 시점, 5.4 입력 규칙 문단 추가 여부
4. **작업 1 장면 1 칸**: 지시에 없던 장면 1 "그룹별 인원" 칸을 넣었다. 빼려면 test_demo의 test_scene1_group_tree도 같이 정해야 한다

## 판정 (찬일 11/02 아침)

| 번호 | 판정 | 반영한 곳 |
|---|---|---|
| 1 README 실행 방법 | README는 고치지 않는다. readme_run_draft.md는 그대로 두고 "W14에서 반영(찬일 허락 후)" | readme_run_draft.md 맨 위 상태 줄 |
| 2 3판 확장 문서 | report_materials의 해당 절은 "확장 단계 실제 수행 후 보충". 지금은 찾지 않음 | report_materials.md 3절 |
| 3 plan_pending | W11 19장 행의 날짜·결정자는 "demo_expected.md 승인일, 찬일". 5.4 입력 규칙 문단은 넣는 것으로 확정 | plan_pending.md 8절 표·끝의 판정 절 |
| 4 장면 1 칸 | demo_expected.md 장면 1 "그룹별 인원" 칸 유지 | 바꾼 파일 없음 (이 기록만) |

## 멈춤 (11.3.4)

- 없음. 수정 시도 횟수 상한·같은 가설 반복에 걸린 작업 없음

## 확인 못 한 것

- tests/test_demo.py의 장면 실행 경로(_run_scenes, _check_recommend, _check_weights, _check_s4)는 실행하지 않았다. 기대값이 없는 상태에서 돌리면 실패 메시지에 실제 결과가 드러나기 때문이다. 합성 값("가짜")을 채운 사본으로 표 파서(_load_expected·_rows·_value)와 장면별 입력 만들기(_scene_inputs)만 확인했다. 첫 실제 실행은 기대값 승인 뒤 W12에서
- 작업 5 "Generated with" 줄 외 본문이 그대로인지는 빈 줄이 아닌 줄을 앞뒤로 비교해 확인했다 (지운 줄 1개, 남은 "Generated with" 0개). 본문 끝의 빈 줄 1~2개도 함께 정리됐다

## 커밋마다 테스트 분류 (커밋 뒤 체크아웃에서 실행한 출력)

973ed28 [W11] 시연 기대값 손계산 양식 (빈칸)
```
Ran 131 tests in 0.048s

OK
```

7277014 [W11] 손계산용 원자료표
```
Ran 131 tests in 0.039s

OK
```

4cc93a6 [W12 준비] 시연 테스트 틀
```
Ran 139 tests in 0.043s

FAILED (errors=8)
   1 NotImplementedError: W11 기대값 승인 전: 장면 1 / 그룹별 인원 빈칸
   1 NotImplementedError: W11 기대값 승인 전: 장면 5 / S4 구매 후 (G-F-20, 전체) 빈칸
   1 NotImplementedError: W11 기대값 승인 전: 장면 8 / 통계 표 빈칸
   4 NotImplementedError: W11 기대값 승인 전: 확정값 / C_new 빈칸
   1 NotImplementedError: W11 기대값 승인 전: 확정값 / C_new7 빈칸
```

14df318 [DOC] 계획서 반영 대기 문안 모음 / 112e4f0 [DOC] 결과보고서 재료: 4cc93a6과 같은 출력 (Ran 139, FAILED (errors=8), 8개 모두 위 NotImplementedError)

## 작업 5: PR 본문 끝 5줄 (수정 뒤 gh pr view로 다시 읽은 것)

PR #1 (chan12-photo/shopgraph, [검토용] W5~W8, OPEN, draft)
```
- W0~W4 (이미 승인되어 main에 있음)
- `docs/verification/` (기대값 검증 기록)

계획서 문구 정정은 별도 draft PR(`doc-pending`)에 있습니다.
```

PR #2 (chan12-photo/shopgraph, [검토용][DOC] 계획서 반영 대기 목록, OPEN, draft)
```

확인한 것: 부록 A 본문(63줄)과 저장소의 `CLAUDE.md` 1~63줄이 같음 (CLAUDE.md는 바꾸지 않음).

코드 쪽 변경은 별도 draft PR(`w8-recommend`)에 있습니다.
```

PR #1은 처음 시도에서 내가 넣은 안전 확인(지운 줄 수 상한)이 본문 끝 빈 줄 때문에 걸려 수정 없이 멈췄고, 확인 조건을 "빈 줄이 아닌 줄은 그 한 줄만 빠짐"으로 바꿔 다시 했다.

---

# 2회차 야간 작업 (2026-11-02)

- 지시: 찬일 11/02 "판단 4건과 추가 야간 작업" (작업 0~5). 공통 규칙은 1회차와 같고, 이번에는 저장소 밖에 파일을 쓰지 않는다 (임시 worktree·커밋 메시지·검토 자료 모두 저장소 안 또는 표준 입력)
- 시작 전 명령 종류를 한 번씩 미리 실행해 승인이 필요한지 확인 (찬일 깨어 있을 때): python -m unittest, git worktree add/remove(저장소 안 .wt_check), 임시 worktree 사본 수정·실행, git commit(이 커밋), 서브에이전트 실행

## 작업 0. 판단 4건 반영

- 4건 모두 이미 b40de17 "[DOC] 야간 작업 판단 4건 판정 기록 (찬일 11/02)"에 반영돼 있음을 확인했다 (readme_run_draft.md 상태 줄, report_materials.md 3절, plan_pending.md 판정 절·W11 행, demo_expected.md 장면 1 칸 유지). 추가로 바꾼 파일 없음

## 2회차 작업별 상태

| 작업 | 상태 | 커밋 | 비고 |
|---|---|---|---|
| 시작 전 명령 미리 실행 | 완료 | 2ccefa7 | python -m unittest, git worktree add/remove(저장소 안), 임시 사본 수정·실행, git commit, 서브에이전트 실행 모두 승인 요청 없이 실행됨 |
| 0 판단 4건 반영 | 완료 | 2ccefa7 | b40de17에 이미 반영돼 있음을 확인, 추가 변경 없음 |
| 1 통합 독립 검토 | 완료 | 4b0d93e | 서브에이전트(맥락 없음, 읽기 전용). 반드시 수정 0, 권장 4, 질문 5. 지시대로 고치지 않음 |
| 2 확장 고장 검사 | 완료 | 491ad40 | 52종 중 49종 잡힘. 못 잡음 3종: S06(동작이 같은 변형), M04·M05(테스트 공백 → mutation_proposals.md 초안) |
| 3 코드 읽기 안내서 | 완료 | a536d70 | docs/study/code_guide.md |
| 4 안내서 검증 | 완료 | 02254b1 | 다른 서브에이전트, 18건 발견·전부 수정. 안내서 밖 발견 1건 → defects A06 |
| 5 발표 뼈대·예상 질문 | 완료 | f0d666d | 예상 질문 22개, 답 문장 없음 |

- 저장소 밖에 쓴 파일 없음: 임시 worktree는 저장소 안 `.wt_mut`·`.wt_run`에 만들고 지움, 커밋 메시지와 실행 스크립트는 표준 입력으로 넘김. 서브에이전트의 대화 기록은 도구가 자체 위치에 남김 (내가 쓴 파일 아님)
- 시연 장면 실행·기대 결과 계산 없음. 서브에이전트 두 개에도 금지함 (검토자는 tools/check_data.py 출력도 보지 않았다고 보고)
- 코드·tests/·계획서 본문·README 변경 없음 (`git diff --stat b40de17 -- graph.py search.py view.py main.py data.py tests docs/project_plan.md README.md` 결과 없음)

## 2회차 판단 필요 (찬일)

1. **통합 검토 Q3 (손계산 전에 판정 권장)**: demo_expected.md 장면 1 "그룹별 인원"은 tools/check_data.py 출력과 w11_g7.md에 이미 같은 숫자가 있다. 실행 결과를 옮겨 적지 않으려면 data.py·w11_raw_by_group.md에서 사람이 직접 셀지 정해야 한다
2. **통합 검토 Q5**: docs/report_materials.md, docs/study/는 찬일 지시 경로지만 CLAUDE.md·11.3.2의 공통 수정 허용 경로 밖이다. 위치를 그대로 둘지
3. **통합 검토 권장 R1~R4, 질문 Q1·Q2·Q4**: main.py K 라벨(R1), main.py 재고 겹침 문구의 콜론 두 번(R2, W10 승인 형식이라 11.3.8 필요), check_data.py check_dates 정리(R3), 오류 문구까지 보는 테스트(R4), graph.py:1199 문구(Q1), main.py 변환 오류 형식(Q2), make_raw_by_group.py의 data.py import(Q4)
4. **고장 검사 테스트 초안 P1·P2**: mutation_proposals.md의 두 테스트를 tests/test_flow.py에 추가할지 ([제안 기대값] 승인 필요)
5. **defects A06**: tests/test_flow.py:607 docstring "(6.4)" 표기 정정 (tests/ 수정이라 승인 필요, 기대값 변경 없음)

## 2회차 커밋마다 테스트 분류

모든 커밋에서 커밋 직전 작업 트리와 커밋 뒤 체크아웃(저장소 안 `.wt_run`) 두 번 실행했고 결과가 같았다:

```
Ran 139 tests
FAILED (errors=8)
```

통과 131 / 미도래 8 (tests/test_demo.py 8개, 전부 `NotImplementedError: W11 기대값 승인 전 …`) / 실패 0. 해당 커밋: 2ccefa7, 491ad40, a536d70, f0d666d, 4b0d93e, 02254b1, 그리고 이 기록 커밋

---

# 3회차 (2026-11-02): 판단 필요 5건과 통합 검토 권장 판정 반영

## 기록만 한 판정 (찬일 11/02)

| 항목 | 판정 | 반영한 곳 |
|---|---|---|
| Q3 장면 1 그룹별 인원 | 찬일이 data.py에서 직접 센다. 칸 옆에 "check_data 출력은 찬일이 이미 본 상태에서 직접 셈" 메모 | docs/demo_expected.md 장면 1 표 메모 칸 |
| Q4 보조 스크립트 import | "프로그램 코드" = graph·search·view·main의 계산 로직. data.py import 허용 | 이 기록, docs/verification/plan_pending.md 해석 기록 |
| Q1 색상 삭제 거절 문구 | 유지 (뒤의 색상은 입력 값이 아니라 결과, 찬일 11/01 판정) | docs/verification/w10a_g7.md 판정 추가 |
| Q2 main.py 변환 오류 형식 | "(입력: 값)"을 붙이지 않는 것이 의도 (콜론 한 번, 안내문) | docs/verification/w10a_g7.md 판정 추가 |
| Q5 파일 위치 | docs/report_materials.md → docs/verification/report_materials.md, docs/study/ → docs/verification/study/ (git mv) | 옮긴 파일 안의 경로 참조, README 현재 상태, docs/defects.md A06의 경로를 새 위치로 고침. 1·2회차 기록(이 파일 위쪽, integrated_review.md)의 옛 경로는 당시 기록이라 그대로 둠 |

## 3회차 커밋

| 커밋 | 내용 | 테스트 (커밋 뒤 체크아웃에서 실행) |
|---|---|---|
| e64d137 [DOC] | Q1~Q4 판정 기록, Q5 파일 위치 이동 | Ran 139, FAILED (errors=8): 통과 131 / 미도래 8 |
| ecf8021 [SPEC][W10b] | R2 재고 겹침 문구, 기존 기대값 1줄 [SPEC] 변경, P1·P2 테스트 3개, R4 assertIn 2개·docstring, A06 | Ran 142, FAILED (errors=8): 통과 134 / 미도래 8 |
| 32f7fc5 [W10b] | R1 추천 K 라벨, R3 check_dates docstring·주석, defects A06 수정·A07 추가 | Ran 143, FAILED (errors=8): 통과 135 / 미도래 8 |
| (이 기록) [DOC] | 3회차 절 마무리 | 아래 커밋 본문 |

- 미도래는 모든 커밋에서 tests/test_demo.py 8개뿐이고 전부 `NotImplementedError: W11 기대값 승인 전 …`
- ecf8021 뒤 저장소 안 임시 worktree에서 고장 검사 M04·M05를 다시 넣어 봄: 각각 test_digit_limit_boundary, test_delete_id_spaces가 잡음 (2회차에 못 잡던 테스트 공백 2건 해소)
- test_recommend_k_not_number는 구현 전(ecf8021 상태)에 AssertionError로 실패하는 것을 확인한 뒤 R1을 고침

## 3회차 판정과 다르게 한 것 (찬일 확인 필요)

- **A06**: 지시는 "test_flow.py:607 docstring의 나이 31을 34로(기대값 변경 없음)"였다. docstring만 34로 바꾸면 바로 아래 메뉴 입력 "31"과 docstring이 어긋나 새 오류가 생겨서, 메뉴 입력도 31 → 34로 함께 바꿨다. 기대 문구 "[수정] 고객4(C04) → 남성·30대 그룹"과 G-M-30 확인은 그대로이고 34로도 통과한다 (ecf8021 본문에 기록). 입력을 31로 되돌리고 docstring만 고치길 원하면 알려 줘
- **R3**: "지우거나 이유를 주석으로" 중 주석을 골랐다. 형식·실제 날짜 분기를 지우면 계획서 11.3.2 W11의 "날짜 형식 점검"이 check_data.py에서 사라지기 때문이다

## 바뀐 오류 화면 (python main.py, data.py, 파이프 입력)

```
[오류] 색상별 재고: 같은 색상이 두 번 나옵니다 (입력: 블랙)
[오류] 추천 개수 K: 숫자로 입력해 주세요
[오류] 추천 개수 K: 1~10이어야 합니다 (입력: 0)
```

- 입력: 상품 등록에서 재고 "블랙=1, 블랙=2" / 추천에서 고객 C01, K "abc" / 추천에서 고객 C01, K "0". 세 경우 모두 오류에서 멈춰 추천 결과는 출력되지 않음
- graph.py·search.py·view.py·data.py는 dd2164f 이후 바뀌지 않음 (`git diff --stat dd2164f -- graph.py search.py view.py data.py` 결과 없음)

---

# 4회차 (2026-11-02): Codex 독립 검토(9784473) 반영

- 근거: docs/verification/codex_review_9784473.md (찬일이 넣은 원문, dc3f402로 먼저 커밋). "Codex 4종" = 이 파일 6번의 계약 위반 4가지 (찬일 확인)
- 규칙: 시연 장면 실행·data.py로 추천·S1·S4·통계 결과 출력·check_data.py 출력 보기 없음. ~/projects/shopgraph_review 폴더 건드리지 않음. 임시 worktree는 저장소 안(.wt_run, .wt_mut, .wt_gen, .wt_mutation)에 만들고 지움

## 커밋과 테스트 분류 (커밋 뒤 체크아웃에서 실행)

| 커밋 | 작업 | 테스트 |
|---|---|---|
| dc3f402 [DOC] | Codex 검토 원문 | Ran 143: 통과 135 / 미도래 8 |
| 6fe24b4 [W12 준비] | 작업 1: test_demo 보호 순서·화면 검증 | Ran 143: 통과 135 / 미도래 8 |
| dc6af7e [SPEC][W3·W4·W6·W9] | 작업 2: snapshot·무결성 보강, Codex 4종 테스트 3개 | Ran 146: 통과 138 / 미도래 8 |
| 2a7777a [W3 보완] | 작업 3: group_of 비용 (A08) | Ran 146: 통과 138 / 미도래 8 |
| 37dc305 [DOC] | 작업 4: 기록 정정 | Ran 146: 통과 138 / 미도래 8 |
| 5538a39 [W12 준비] | 작업 1 정적 독립 검토 반영 | Ran 146: 통과 138 / 미도래 8 |
| dc613a0 [DOC] | 작업 5: 고장 검사 재현 (패치·스크립트·결과) | Ran 146: 통과 138 / 미도래 8 |
| (이 기록) [DOC] | 4회차 절 | 아래 커밋 본문 |

미도래 8은 모든 커밋에서 tests/test_demo.py 8개, 전부 NotImplementedError (6fe24b4부터는 실행 전 보호 때문에 모두 "장면 1 / 그룹별 인원 빈칸"에서 멈춤). 실패 0.

## 작업별 결과

| 작업 | 상태 | 요점 |
|---|---|---|
| 1 test_demo 보호 순서·화면 검증 | 완료 | 실행 전에 장면 1~N의 필수 표·행·칸·형식·확정값 확인. 화면 비교(장면 1 그룹 줄, 3 S1 표, 5 S4 표 2개, 2·4·6·7 추천 항목·근거·색상, 8 통계 표·판정 줄). 시연 데이터 실행 없이 가짜 값 사본으로만 확인. 정적 독립 검토(서브에이전트): 반드시 수정 1·권장 4 반영, 질문 1은 아래 판단 필요 → docs/verification/w12_prep_review.md |
| 2 [SPEC] 테스트 보강 | 완료 | snapshot 전후 비교 3곳, 무결성 확인 1곳, 새 테스트 3개. Codex 4종은 추가 전 테스트로 4종 모두 놓쳤고 추가 뒤 모두 잡힘 (임시 사본 확인) |
| 3 group_of 비용 | 완료 | 그룹 ID 8개만 확인, 반환 규칙 그대로, S2 = O(d log d). defects A08 |
| 4 기록 정정 | 완료 | mutation_sweep 주체 정정, w10_g7 입력 수 67로 정정, defects T 분류·T01, report_materials 건수, view.py 모듈 설명, code_guide 빈 결과 분기·줄 번호, code_guide_check 19번, 발표 질문 23~29 |
| 5 고장 검사 재현 | 완료 | 56종 중 55종 잡힘, S06만 못 잡음(동작이 같은 변형). 기준 5538a39, 명령·실패 테스트 이름까지 mutations/result_5538a39.md |

## 4회차 판단 필요 (찬일)

1. **test_demo 실행 조건에 승인 기록을 넣을지** (작업 1 정적 검토 질문 4) → 처리: ca1171e (찬일 11/02 판정, 상태 줄이 정확한 승인 형식일 때만 실행): 지금은 칸이 다 채워지고 형식이 맞으면 시연을 실행한다. 찬일이 손계산으로 칸을 다 채운 순간, AI 대조·11.3.8 승인 전이라도 `python -m unittest`가 시연을 실행해 결과(실패 메시지 포함)를 보게 될 수 있다. 선택지: (가) demo_expected.md "검산·승인 기록"의 "11.3.8 승인" 행이 채워져야 실행 (나) 지금처럼 빈칸만 보고, 승인 전에는 test_demo를 돌리지 않는 것을 절차로만 지킴
2. **defects A02를 T 분류로 옮길지** → 처리: bd93f79 (찬일 11/02 판정, A02 → T02 재분류): 이번에 "테스트 작성 실수는 T"로 기준을 정했는데, 기준 전에 A로 기록한 A02(테스트 기대값 표의 가변 객체 공유)를 그대로 둘지
3. 참고(판단 아님): integrated_review.md의 "약 60가지"는 검토자가 main.py에 직접 넣어 본 실험 수라 테스트 수 정정(67) 대상이 아니라고 보고 그대로 뒀다
