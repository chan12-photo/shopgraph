# UI5 G7 제출 자료

- 작업일: 2026-11-03. 승인자: 찬일. 작업 브랜치: web-ui.
- **판정: HTTP 8장면·보호 3종·실제 Chrome 시연 대조 통과. 짝수 LTS 재현은 설치된 실행 파일이 없어 미실행, 판단 필요. 필수 게이트에서 멈춤.**
- G1: UI4c 표시 변경을 먼저 분리한 뒤 HTTP 시연 테스트, 보호 실험, 실제 화면 시연·캡처, LTS 환경 확인을 수행한다.
- G2/G3: 기존 test_demo의 파서·승인 보호를 테스트 전용 어댑터에서 재사용했다. 첫 HTTP 테스트 실행 8개는 이미 구현된 UI1·UI2 API가 처리해 처음부터 통과했다. 이후 보호 회귀 테스트 3개를 추가했다.
- G4: 아래 원문. G5/G6: Codex 자기 재검토이며 독립 검토가 아니다. 사람 실행이나 Claude의 이번 구현 독립 확인으로 기록하지 않는다.
- G7: 찬일 검토·판정 대기. UI6 미착수. G8: 이 기록을 포함하는 `[UI5]` 제출 커밋, push·main 합치기 없음.

## 커밋과 범위

| 커밋 | 범위 | 해당 시점 전체 테스트 |
|---|---|---|
| `88e823d` `[UI4c] 그래프 좌표와 선택 정보 표시 다듬기` | 그룹 평균 좌표·빈 그룹 배치, 기본 글자/확대, 이름+관계+weight, 근거 앞 공백 제거, 서버 그룹 인원 표시, dist | 통과 163 / 미도래 0 / 실패 0 |
| 이 문서를 포함하는 `[UI5]` 제출 커밋 | tests/demo_expected_adapter.py, tests/test_web_demo.py, 브라우저 검사·결과·캡처·검증 기록 | 통과 174 / 미도래 0 / 실패 0 |

UI5에서 운영 코드·dist·기존 테스트·demo_expected·계획서·CLAUDE·README는 변경하지 않았다. UI4c dist를 실제 서버가 제공했다. 이후 커밋 해시는 `git log -1 --format='%h %s' -- docs/verification/ui5_g7.md`로 확인한다.

## 기대값과 보호

- 값의 출처: docs/demo_expected.md 한 곳. 이 값은 프로그램 코드를 실행하지 않은 AI 독립 계산 2건 대조와 찬일의 대표 항목 손 확인·승인으로 확정했다. 사람이 전체를 손계산했다고 표현하지 않는다.
- tests/demo_expected_adapter.py는 기존 tests.test_demo의 `_require_approval`, `_load_expected`, `_require_through`, `_rows`, `_value`만 기대값 읽기/보호에 사용한다. 기존 실행 함수·기대 화면 생성 함수는 사용하지 않는다.
- 실행 순서: **승인 줄 확인 → 파일 파싱 → 확정값 및 8장면 전체 양식/칸/일관성 확인 → ShopGraph와 HTTPServer 생성**. 정상 문서에서 원자료 색상 확인을 위해 기존 보호 함수가 initial_records를 읽지만 추천·S1·S4 계산을 하지 않는다.
- 실제 HTTP는 같은 프로세스의 HTTPServer(port=0)를 백그라운드 스레드에서 실행한다. 서버 자체는 단일 요청 처리다. 한 서버에서 장면 1~8 상태를 이어 가고, 개별 테스트만 골라도 그 앞 장면부터 한 번씩 진행한다. 종료 시 shutdown·join·server_close를 보장한다.
- 추천·점수·범위·지지자·색상·S1·S4·통계 기대값을 API 응답이나 recommend/view 실행으로 만들지 않았다. 응답의 배열 전체를 문서에서 읽은 배열과 직접 비교하므로 순서·개수·중복도 함께 검사한다. 성공 변경 직후에는 실제 integrity 응답이 빈 위반 목록인지 확인한다.
- 안내의 **유무는 demo_expected 표**, 글자·띄어쓰기 고정 틀은 계획서 5.3.3 및 W8b 승인 형식을 사용했다. demo_expected에는 안내 문장 전체가 아니라 있음/없음만 있어 이 출처 차이를 명시한다. 이번 8장면에서 존재하는 안내는 장면 7의 다음 한 줄뿐이며 프로그램 출력에서 기대 문구를 가져오지 않았다.

```text
 ※ 같은 그룹(남성·10대)에 다른 고객이 없어 '남성 전체'로 넓혀 찾음
```

## test_web_demo 결과 원문

```text
$ python3 -B -m unittest tests.test_web_demo -v
test_invalid_cell_format (tests.test_web_demo.TestUI5DemoGuard.test_invalid_cell_format)
장면 8 통계 칸의 숫자를 문자로 바꾸면 실행을 막는다. ... ok
test_last_scene_blank (tests.test_web_demo.TestUI5DemoGuard.test_last_scene_blank)
장면 8의 빈칸도 장면 1 실행 전에 검사한다. ... ok
test_missing_approval (tests.test_web_demo.TestUI5DemoGuard.test_missing_approval)
승인 상태 줄 자체를 지우면 서버 생성 전에 멈춘다. ... ok
test_01_groups (tests.test_web_demo.TestUI5WebDemo.test_01_groups)
장면 1: 8개 그룹 전부의 인원을 승인 표와 비교한다. ... ok
test_02_register_recommend (tests.test_web_demo.TestUI5WebDemo.test_02_register_recommend)
장면 2: 새 ID·소속 그룹·별도 GET 추천을 비교한다. ... ok
test_03_purchase_s1 (tests.test_web_demo.TestUI5WebDemo.test_03_purchase_s1)
장면 3: 두 구매의 가중치와 S1 집계 전체를 비교한다. ... ok
test_04_recommend_again (tests.test_web_demo.TestUI5WebDemo.test_04_recommend_again)
장면 4: 구매한 상품이 빠진 추천 표 전체와 비교한다. ... ok
test_05_popular_before_after (tests.test_web_demo.TestUI5WebDemo.test_05_popular_before_after)
장면 5: S4 전/후와 세 구매의 가중치를 비교한다. ... ok
test_06_stock_before_after (tests.test_web_demo.TestUI5WebDemo.test_06_stock_before_after)
장면 6: 품절 전 추천·1위·품절 응답·품절 후 추천을 비교한다. ... ok
test_07_widen (tests.test_web_demo.TestUI5WebDemo.test_07_widen)
장면 7: 새 ID·남성10대 그룹·넓힘 안내까지 비교한다. ... ok
test_08_stats_integrity (tests.test_web_demo.TestUI5WebDemo.test_08_stats_integrity)
장면 8: 통계 6항목과 무결성 위반 수를 직접 비교한다. ... ok

----------------------------------------------------------------------
Ran 11 tests in 0.526s

OK
```

분류: **통과 11 / 미도래 0 / 실패 0**(시연 8개+보호 3개).

전체 회귀 원문 요약:

```text
$ python3 -B -m unittest -v
Ran 174 tests in 6.709s

OK
```

분류: **통과 174 / 미도래 0 / 실패 0**. 커밋 직전 전체 -v 원문은 실행 시 `/tmp/shopgraph-ui5-final-full.log`, UI5 전용 원문은 `/tmp/shopgraph-ui5-demo.log`에 보관했다. UI2의 의도된 `RuntimeError: after C07` 로깅은 테스트 실패가 아니다.

## /tmp 보호 실험

`git archive 88e823d`와 새 테스트 파일을 `/tmp/shopgraph-ui5-protect.7svjAo`에 복사했다. 그 사본의 data.py는 initial_records를 호출하면 즉시 AssertionError를 내도록 바꾸고, web.create_server도 호출 즉시 실패하는 mock으로 바꿨다. 저장소의 시연 문서·데이터는 변경하지 않았다.

```text
승인 줄 삭제:
PASS 승인 줄 삭제: 11.3.8 승인 전: 상태 줄이 승인 형식이 아님: ''
PASS data.py 미호출 / create_server 미호출

장면 8 '구매 기록' 빈칸:
PASS 장면 8 빈칸: W11 기대값 승인 전: 장면 8 / 통계 표 빈칸
PASS data.py 미호출 / create_server 미호출

장면 8 숫자 칸을 invalid로 변경:
PASS 장면 8 형식 훼손: W11 기대값 승인 전: 장면 8 / 통계 표 / 개수 형식 확인 필요: 'invalid'
PASS data.py 미호출 / create_server 미호출
```

동일한 보호를 `TestUI5DemoGuard`의 회귀 3개로 저장했다. 이 테스트도 문서 사본은 `/tmp`에서만 만든다.

## 실제 브라우저 시연·오프라인 범위

- 실행: `node docs/verification/ui5_browser_check.mjs`.
- 실제 제품 진입점: `python3 -u -B main.py --web --port 0`. 새 서버 하나로 1~8을 차례로 진행했다. GUI 중복 창을 피하려고 BROWSER=/usr/bin/true로 자동 열기만 억제하고 실제 Chrome은 별도 임시 프로필로 띄웠다. main.py를 mock하지 않았다.
- 브라우저: Chrome/156.0.8078.74, headless Chromium, viewport 1440×900. 긴 카드·차트는 이 너비의 전체 페이지로 캡처했다.
- 입력: w11_scenes.md의 이름·성별·나이·고객/상품·색상·수량·날짜 그대로. 추천 K 생략, S4 전체. 추가 읽기 요청은 화면 갱신용이며 변경 순서/상태는 그대로다.
- 브라우저 전용 기대값도 서버 실행 전에 Python의 동일 어댑터가 승인 문서에서 읽어 JSON으로 넘긴다. DOM에서 읽은 추천·S4·통계를 그 값과 비교한 뒤 캡처한다. Codex가 캡처 12장을 모두 직접 확인했다.
- Chrome Fetch interception으로 127.0.0.1 외 HTTP(S)를 차단하는 상태에서 실행했고, 실제 페이지 Network 이벤트의 외부 요청은 0건, JS 예외는 0건이었다. 운영체제 전체의 인터넷 연결은 끄지 않았다.
- 제품 결함 새 발견 0건. 최초 브라우저 검사기의 정규식 문자열 이스케이프 오류는 T03으로 구분 기록했고 수정 뒤 전체 시연을 새 서버로 재실행했다.

실행 원문:

```text
PASS 장면 1: 01_groups.png / 그룹 8개 인원 전체
PASS 장면 2: 02_registered_recommendation.png / C_new ID·추천 3항목 전체·안내 없음
PASS 장면 3: 03a_purchase_s1.png / 구매 가중치 1→2·S1 색상/가중치
PASS 장면 3: 03b_graph_weight2.png / 선택 정보 이웃 이름·관계·가중치 2
PASS 장면 4: 04_recommend_again.png / 기구매 P_top 제외·추천 전체
PASS 장면 5: 05a_popular_before.png / S4 구매 전 9항목·점수·구매자·상태
PASS 장면 5: 05b_popular_after.png / S4 전 고정·구매 후 9항목·순위 변화
PASS 장면 6: 06a_before_stock.png / 품절 전 P_top6 1위·색상 수 안내 포함 추천 전체
PASS 장면 6: 06b_zero_stock.png / 모든 기존 색상 재고 0·품절·C_new 추천 복귀 버튼
PASS 장면 6: 06c_after_stock.png / 품절 후 P_top6 제외·다음 후보 포함 추천 전체
PASS 장면 7: 07_widen_gender.png / 남성 전체 3항목·점수/지지자/색상·넓힘 안내 원문
PASS 장면 8: 08_integrity.png / 통계 6항목·위반 수
PASS 장면 1~8 전체 대조 / 외부 네트워크 0 / 브라우저 예외 0
```

## 캡처와 기대값 대조표

모든 파일은 `docs/verification/ui5_screens/` 아래에 있다. 아래는 검사 결과 설명이며 새 기대값 출처가 아니다.

| 장면 | 파일 | 캡처 대조 결과 |
|---|---|---|
| 1 | 01_groups.png | 8그룹 인원 3·8·5·2·0·6·4·2, 일치 |
| 2 | 02_registered_recommendation.png | C31 하람/여성20대; P03→P01→P05, 점수 9·7·6, 구매자 7·3·5. 지지자·색상·색상 수 안내 전부 일치. 세 안내 없음 |
| 3 | 03a_purchase_s1.png | 등록 가중치 1→2, S1 P03 베이지·블랙/가중치2 일치. 기록수2·총수량2·최근10/31은 화면에 표시하지 않아 HTTP 테스트에서 별도 일치 확인 |
| 3 | 03b_graph_weight2.png | C31 선택 정보에 여성20대(소속 그룹), 와이드 슬랙스(구매·가중치2). 일치 |
| 4 | 04_recommend_again.png | P01→P05→P07, 점수7·6·5, 구매자3·5·4. 기구매 P03 제외 및 지지자·색상·색상 수 안내 일치, 안내 없음 |
| 5 전 | 05a_popular_before.png | S4 9행 전부 일치. P03 11점/8명, P07 4위 5점/4명. 고정 직후 좌우 동일 |
| 5 후 | 05b_popular_after.png | S4 전 고정 보존, 후 9행 전부 일치. P07 2위 8점/5명, 구매 가중치1→2→3 일치 |
| 6 전 | 06a_before_stock.png | P07→P01→P05, 점수8·7·6, 구매자5·3·5. P07의 `C07은 2가지, C09는 3가지` 및 나머지 근거·색상 일치 |
| 6 재고 | 06b_zero_stock.png | P07 기존 4색 모두 0·품절·구매 가능 색상 없음, C31 추천 복귀 버튼 확인 |
| 6 후 | 06c_after_stock.png | P01→P05→P06, 점수7·6·3, 구매자3·5·3. 지지자·색상·색상 수 안내 일치, 안내 없음 |
| 7 | 07_widen_gender.png | C32 새싹/남성10대; P09→P08→P11, 점수6·5·5, 구매자4·4·4, 남성 전체 범위. 지지자·색상·색상 수 안내 일치. 넓힘 문구 일치, 개수 부족·점수 비교 안내 없음 |
| 8 | 08_integrity.png | 통계8·32·22·32·101·127, 위반0. 일치 |

## 짝수 LTS 재현 결과 / 판단 필요

```text
$ node -v
v25.8.1
$ npm -v
11.11.0
$ which -a node
/opt/homebrew/bin/node
/opt/homebrew/bin/node
```

Homebrew Cellar/opt, /usr/local Cellar/opt, nvm·fnm·volta·mise의 기본 설치 위치 및 Codex.app 안에서 Node 실행 파일을 확인했다. 확인된 실행 파일은 `/opt/homebrew/Cellar/node/25.8.1_1/bin/node`뿐이다. fnm·mise·asdf·volta 실행 명령도 PATH에서 찾지 못했다.

- **짝수 LTS의 npm ci → typecheck → build: 미실행**. 직접 설치해야 하므로 사용자 지시대로 설치하지 않았다.
- **짝수 LTS 산출물과 커밋 dist 비교: 미실행/비교 불가**. '동일' 판정을 하지 않는다. 이번 UI5는 UI4c 커밋의 dist를 그대로 사용했고 diff는 없다.
- 판단 필요: 사용할 짝수 LTS Node의 설치 또는 기존 실행 파일 경로 제공. 제공된 뒤 재현 빌드와 dist 차이 파일 목록 확인이 남는다. 이 환경 항목을 통과한 것처럼 UI5 전체 완료/승인을 기록하지 않는다.

## 이해 질문(기록만)

1. S4에서 P03이 1위인데 C31 추천 1위는 P07인 이유를 장면 3의 구매와 연결해 설명할 수 있는가?
2. P07 재고 0으로 바꿔도 구매 기록·가중치가 남고 추천에서만 제외되는 이유는 무엇인가?
3. 기대값 승인 보호·HTTP 일치·실제 DOM 대조·무결성 검사가 각각 확인하는 범위와 확인하지 못하는 범위는 무엇인가?
