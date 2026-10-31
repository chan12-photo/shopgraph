# ShopGraph

의류 쇼핑몰의 고객·상품·구매 관계를 그래프 라이브러리 없이 직접 구현한 그래프로 관리하고, 신규 고객이 가입하면 같은 성별·연령대 그룹의 구매를 바탕으로 상품을 추천하는 콘솔 프로그램이다. (데이터사이언스와컴퓨팅2 DSC2013-01 팀프로젝트)

- 기준 문서: `docs/project_plan.md` (구현 기준 확정판)
- AI 작업 규칙: `CLAUDE.md` (계획서 부록 A + 2026-10-28 보완)
- 환경: Python 3.11 이상, 표준 라이브러리만 사용

## 실행

```bash
python main.py
```

## 테스트

```bash
python -m unittest -v
```

## 폴더 구조 (계획서 5.5)

```text
main.py                  유일한 진입점. 메뉴, 입력 변환, 오류 메시지 표시 (W1에서 생성)
view.py                  화면 출력 전용 (W1에서 생성)
search.py                읽기 전용: 조회, 검색 S1~S4, 추천 (W1에서 생성)
graph.py                 ShopGraph: 원본 데이터 + 그래프 + 변경 메서드 (W1에서 생성)
data.py                  초기 더미 데이터 (W8b에서 생성, W11에서 시연 데이터로 교체)
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
tools/                   개발용 데이터 점검 스크립트, 실행 경로 밖 (W11에서 생성)
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

- 완료: W0 저장소 준비, W1 graph 계약 고정, W2 테스트 먼저, W3 graph 읽기 쪽, W4 고객·상품 변경
- 다음: W5 구매 변경·무결성 검사 (아직 시작 전)
- graph.py는 생성자·rebuild·조회 메서드, 고객·상품 등록·수정·삭제까지 구현됐다. 나머지(graph.py 구매 변경·무결성 검사, search.py·view.py·main.py)는 골격만 있다 (NotImplementedError). `python main.py`의 실제 동작은 W8b(최소 흐름)부터다
- 테스트 76개(test_graph·test_search·test_recommend)가 있다. 지금은 `python -m unittest -v`에서 `Ran 76 tests`, `FAILED (errors=38)`이 정상이다 (W3·W4 테스트 38개 통과, 나머지 38개는 NotImplementedError)
- 계획서 반영 대기 (W5 뒤 사람이 한 번에 반영):
    - B.3 구매일 행 ①: 정규식 표기를 `[0-9]{4}-[0-9]{2}-[0-9]{2}` 전체 일치(fullmatch)로 정정 (결함 B07)
    - 19장 행: `| 10/31 | B.3 구매일 규칙 ①의 정규식 표기를 [0-9]{4}-[0-9]{2}-[0-9]{2} 전체 일치로 정정 | \d·$ 표기가 다른 숫자 체계·끝 줄바꿈을 형식 단계에서 통과시킴(B07) | 찬일 |`
