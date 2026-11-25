# ShopGraph

의류 쇼핑몰의 고객·상품·구매 관계를 그래프 라이브러리 없이 직접 구현한 그래프로 관리하고, 신규 고객이 가입하면 같은 성별·연령대 그룹의 구매를 바탕으로 상품을 추천하는 콘솔 프로그램이다. (데이터사이언스와컴퓨팅2 DSC2013-01 팀프로젝트)

- 기준 문서: `docs/project_plan.md` (구현 기준 확정판)
- AI 작업 규칙: `CLAUDE.md` (계획서 부록 A + 2026-10-28 보완)
- 환경: Python 3.11 이상, 표준 라이브러리만 사용

## 실행

```bash
python3 main.py          # 콘솔 메뉴
python3 main.py --web    # 웹 화면 (http://127.0.0.1:8000, 포함된 frontend/dist 사용, Node 불필요)
python3 main.py --web --port 8080   # 8000번이 쓰이고 있을 때
```

데이터는 메모리에만 있다. 서버나 프로그램을 다시 켜면 data.py의 시연 데이터로 돌아간다.

## 테스트

```bash
python3 -B -m unittest            # 전체 (웹 테스트는 127.0.0.1 소켓을 연다)
python3 -B tools/check_data.py    # 시연 데이터 점검 (개발용)
python3 -B tools/bench.py time    # 측정 (개발용, 기본 고객 1만·상품 1천·구매 30만)
```

프런트 소스(frontend/src)를 고칠 때만 `frontend/`에서 `npm ci`, `npm run typecheck`, `npm run build`로 dist를 다시 만든다. 화면을 바꾼 뒤에는 `node docs/verification/ui5_browser_check.mjs`와 `node docs/verification/ui9b_browser_check.mjs`를 함께 실행한다.

## 폴더 구조 (계획서 5.5)

```text
main.py                  유일한 진입점. 메뉴, 입력 변환, 오류 메시지 표시 (W1에서 생성)
view.py                  화면 출력 전용 (W1에서 생성)
search.py                읽기 전용: 조회, 검색 S1~S4, 추천 (W1에서 생성)
graph.py                 ShopGraph: 원본 데이터 + 그래프 + 변경 메서드, 공개 정렬 함수 id_sort_key (W1에서 생성, X1에서 가변 ID)
validation.py            입력 검증 함수·검증용 상수. graph.py만 가져옴 (X2에서 graph.py에서 분리)
web.py                   --web 로컬 HTTP 서버: 공개 API 호출·JSON 변환·정적 파일 제공 (UI1에서 생성)
data.py                  초기 더미 데이터 (W8b에서 생성, W11에서 시연 데이터로 교체)
frontend/
  src/                   React·TypeScript 화면 소스 (계산은 Python이 하고 결과만 표시)
  dist/                  저장소에 포함한 빌드 결과 (실행에 Node 불필요)
tests/
  __init__.py            python -m unittest가 tests/를 찾게 함
  fixtures.py            6.1 PoC 고정 데이터를 테스트마다 새로 만드는 함수 (W2에서 생성)
  helpers.py             테스트 전용 snapshot(g) (W2에서 생성)
  test_graph.py          graph 테스트 (W2에서 생성)
  test_search.py         조회·S1~S4 테스트 (W2에서 생성)
  test_recommend.py      추천 테스트 (W2에서 생성)
  test_flow.py           최소 흐름 테스트 (W8b에서 생성)
  test_view.py           화면 테스트 (W9에서 생성)
  test_demo.py           시연 시나리오 테스트 (W12에서 생성)
  demo_expected_adapter.py  docs/demo_expected.md를 읽어 시연 테스트 기대값으로 쓰는 도구
  test_web*.py           웹 API·화면 문구·시연 HTTP·안정성·헤더 검사 테스트 (UI1~UI9c)
  test_x1.py             가변 ID 발급과 ID 순 정렬 테스트 (X1)
  test_bench.py          X0 측정 진단 스크립트 테스트 (X0)
  test_bench_tools.py    측정 도구 tools/bench.py 테스트 (X2)
tools/                   개발용 스크립트, 실행 경로 밖: check_data.py(시연 데이터 점검, W11), bench.py(측정, X2)
docs/
  project_plan.md        계획서 (기준 문서)
  defects.md             결함 기록 (계획서 11.3.9)
  test_map.md            6장 항목 ↔ 테스트 대응표 (양식은 부록 B.5, W2에서 채움)
  verification/          6장 기대값 검증 자료 (프로그램에 포함하지 않음)
  demo_expected.md       시연 시나리오 손계산 기대값 (W11에서 생성)
CLAUDE.md                AI 작업 규칙
```

## 개발 절차

계획서 11.3의 단계(W0~W14)를 한 번에 하나씩 진행한다. 단계마다 G1 계획 → G2 테스트 먼저 → G3 구현 → G4 실행 → G5 자가 점검 → G6 검토 → G7 사람 승인 → G8 기록 순서를 따른다. 단계별 기록은 git log와 `docs/test_map.md`, 결함은 `docs/defects.md`에 남긴다.

## 현재 상태

이 섹션만 모든 단계에서 갱신한다.

- 완료: W0~W12(태그 `w12-complete`), 웹 UI0~UI9c(UI5 승인 11/06, UI6·UI9a·UI9b 승인 11/07, UI9c 승인 11/12), X0(승인 11/07). UI8 구현·Codex 자체 확인은 완료했으며 최종 판정은 찬일이 한다.
- 실행: `python3 main.py`(콘솔), `python3 main.py --web`(웹).
- 테스트: 찬일 터미널 확인(11/12), `python3 -B -m unittest` → `Ran 268 tests`, `OK` (통과 268 / 미도래 0 / 실패 0, Python 3.11.15·3.13.12·3.15.2). Codex 실행 환경에서는 소켓·sysctl 제한으로 웹·측정 도구 테스트가 돌지 않으므로 전체 테스트는 터미널에서 실행한다. 상세: [UI9c 기록](docs/verification/ui9c_g7.md).
- 다음 단계: X0~X2(확장, 11/27까지), W13·W14, 12/7~ 발표. X3a 이후는 이번 제출에서 제외한다.
- 이해 확인 질문: 기존 질문과 UI8 질문은 미답 상태다. X 단계 승인 전에 확인한다. 1차(묶음 1~3과 외부 검토 핵심 6문항)는 X1 승인 전, 2차(나머지)는 X2 승인 전에 끝낸다. 하나라도 답하지 못하면 해당 X 단계를 승인하지 않는다. 앞선 11/29 일괄 답변 일정은 대체됐다.
