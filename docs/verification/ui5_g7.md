# UI5 G7 제출 자료

## 2026-11-03 디자인 채택 후속 기록

- 찬일 결정: 디자인 C(`web-design-c`, `80c53cd`) 채택. 디자인 B는 채택하지 않고 `web-design-b`(`685050c`)를 기록으로 보존한다. B·C 캡처 대조자는 찬일이 전달한 Claude다.
- 원본 C 독립 검토: Codex가 `78ac972..80c53cd`를 먼저 읽기 전용으로 검토. 반드시 수정 0. 저장소 밖 사본의 npm ci·build 뒤 dist 3개 파일 목록·SHA-256 전부 일치, 실제 브라우저 8장면 통과. [상세 기록](design_c_adoption_review.md).
- `web-ui`에 C를 fast-forward로 합친 뒤 notices 청록 강조·중복 그래프 범례 제거만 다듬었다. 이 두 수정의 확인은 Codex 자체 확인이며 독립 검토가 아니다.
- 최종 검증: typecheck·build 성공. 전체 통과 174 / 미도래 0 / 실패 0, test_web_demo 통과 11 / 미도래 0 / 실패 0. 1440×900 장면 1~8 대조·해당 캡처 갱신·S4 해제/필터/선택 상자 추가 확인 통과. 외부 요청 0, 패키지 6개·lock 유지. push·main 합치기 없음.

이하 내용은 최초 UI5 제출 시점의 기록이다.

- 작업일: 2026-11-03. 승인자: 찬일. 작업 브랜치: web-ui.
- LTS Node 재현: 미실행(짝수 LTS 미설치). 실행에는 Node 불필요(dist 포함)
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

UI5에서 운영 코드·dist·기존 테스트·demo_expected·계획서·CLAUDE·README는 변경하지 않았다. UI4c dist를 실제 서버가 제공했다. UI5 제출 커밋은 `78ac972`이다.

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

## 2026-11-03 독립 검토 반영

이 절의 날짜는 찬일의 처리 판정일이다. 실제 수정·실행은 **2026-11-04**, 규리의 로컬 `web-ui-guri`에서 Python 3.15.0으로 진행했다. 시작 기준은 `89e2887`이며, 해당 커밋에 대한 Claude Code 독립 검토를 인계 문서의 결정대로 반영했다. **이번 변경의 실행·고장 주입·대조는 Codex 자체 확인이며 독립 검토 또는 UI5 승인이 아니다.**

### 지적별 조치

| 번호 | 조치 | 확인 근거 |
|---|---|---|
| 1 | `c14b3d2` [SPEC][UI5]에서 기존 테스트 기대값 한 줄만 400→415로 변경. 다음 [UI5 보완] 커밋에서 `_read_json_object`의 응답을 415로 맞추고 docstring에 415 추가 | UI0 설계 3.3. `text/plain`·헤더 누락 × 고객 등록·구매 등록·재고 수정 6개 조합의 상태 코드·문구·전체 상태 불변 확인 |
| 2 | 유효/무효 재고 혼합 PUT 테스트 추가 | P03 아이보리 3·네이비 -1 입력 시 400, `snapshot` 전체 불변. 유효 항목부터 적용하는 고장 M01 검출 |
| 3 | 기존 보호 테스트는 보존하고 실제 호출 대상 `data.initial_records`, `graph.ShopGraph`, `web.create_server`를 감시하는 테스트 3개 추가 | 승인 누락·장면 8 빈칸·잘못된 숫자 형식 모두 생성 전 차단. 승인 검사를 뒤로 미루는 M02와 그래프만 먼저 만드는 M03 검출 |
| 4 | PUT 재고·POST 구매 각각 공개 변경 메서드가 실제 변경한 뒤 예외를 내도록 테스트 추가 | 정확한 불확실성 500 문구, 후속 GET 생존·변경 반영, 무결성 확인. 두 경로의 변경 플래그 제거 M04·M05 각각 검출 |
| 5 | 중첩 중복 키, NaN·Infinity·-Infinity, 65537바이트 본문, 비JSON 형식, 구매된 색상 삭제, 불가능한 날짜, 고객·구매 ID 한도 테스트 추가 | 거절마다 상태 코드·정확한 오류 문구·전체 `snapshot` 비교. C99·T999 직전 상태는 공개 등록 메서드로만 구성. 정상 등록 후 무결성 확인 |
| 6 | 픽스처 P02를 공개 메서드로 품절 처리하고 S4의 전체 순서·점수·구매자·판매 상태·품절 여부 비교 | P02가 목록에 남고 `품절`/true, P01·P03은 `판매 중`/false. 픽스처 손계산 근거를 주석에 기록. 판매 문구 고정 M06 검출 |
| 7 | 넓힘 안내 문구 하드코딩은 동의 판정대로 유지 | 기존 출처 기록·시연 기대값 유지 |
| 8 | web 쪽 bool 이중 방어는 동의 판정대로 유지 | 기존 검증 유지 |

### 405 → 400 → 415 경위와 변경 범위

인계 문서에 기록된 경위는 UI1의 POST 미지원 기대값 405 → UI2(`f80574f`)에서 [SPEC] 없이 400으로 변경 → 찬일 11/03 판정에 따라 설계 3.3의 415로 복원이다. 이번에는 기대값만 고친 [SPEC]과 구현·추가 테스트를 나눠 커밋한다. 첫 커밋 `c14b3d2` 시점의 실패 1개는 아직 구현이 400인 데서 발생한 의도된 중간 상태다.

운영 코드 변경은 `web.py`의 `_read_json_object` 오류 번호와 그 docstring뿐이다. `frontend/src/App.tsx`의 공통 API 함수는 `response.ok`로 성공 여부를 판단하고 `payload.error`를 표시하며 400 상태 코드에 의존하지 않는다. 프런트 수정은 필요하지 않았다. 기존 테스트는 [SPEC]의 기대값 한 줄 외에 삭제·변경·skip·expectedFailure 없이 유지했고, 새 테스트 메서드 15개만 추가했다. 금지 파일과 `frontend/` 전체는 변경하지 않았다.

### 새 테스트 목록 (15개)

아래 이름은 각 파일의 기존 클래스에 추가한 메서드다. 하위 입력 조합(subTest)은 별도 테스트 개수로 부풀리지 않았다.

| 파일 / 클래스 | 새 메서드 |
|---|---|
| `tests/test_web.py` / `TestUI1WebReadAPI` | `test_popular_keeps_sold_out_product_and_status` |
| `tests/test_web_write.py` / `TestUI2WebWriteAPI` | `test_stock_mixed_valid_invalid_is_atomic` |
| 위와 같음 | `test_stock_nested_duplicate_key_is_rejected` |
| 위와 같음 | `test_nonfinite_json_numbers_are_rejected` |
| 위와 같음 | `test_body_over_64kib_is_rejected` |
| 위와 같음 | `test_non_json_content_types_rejected_before_mutation` |
| 위와 같음 | `test_purchased_color_removal_is_rejected` |
| 위와 같음 | `test_impossible_purchase_date_is_rejected` |
| 위와 같음 | `test_customer_id_limit_over_http` |
| 위와 같음 | `test_purchase_id_limit_over_http` |
| 위와 같음 | `test_stock_exception_after_mutation_returns_uncertain_500` |
| 위와 같음 | `test_purchase_exception_after_mutation_returns_uncertain_500` |
| `tests/test_web_demo.py` / `TestUI5DemoGuard` | `test_missing_approval_blocks_real_data_and_graph` |
| 위와 같음 | `test_last_scene_blank_blocks_real_data_and_graph` |
| 위와 같음 | `test_invalid_format_blocks_real_data_and_graph` |

### 신규 테스트 고장 주입 자체 확인

`git archive HEAD`로 당시 HEAD `c14b3d2599c1f8319220c0384b97d3a742492291`을 `/tmp`에 풀고, 아직 커밋 전인 `web.py`와 테스트 3개 파일을 덮어써 수정본을 구성했다. 정상 사본에서 대상 테스트가 통과함을 먼저 확인한 뒤, 고장마다 별도 사본을 만들어 아래 테스트를 실행했다. 고장이 없는 실제 저장소에는 주입하지 않았다. 종료 코드 1과 해당 `FAIL`을 확인했고, 테스트 실행 자체의 `ERROR`는 없었다. 실행 전후 원본 4개 파일의 SHA-256이 같고, 임시 사본 삭제도 확인했다.

표의 보호 테스트 3개는 위 목록의 `test_missing_approval_blocks_real_data_and_graph`, `test_last_scene_blank_blocks_real_data_and_graph`, `test_invalid_format_blocks_real_data_and_graph`를 가리킨다.

| 번호 | 임시 사본에 넣은 고장 | 실제 실패한 새 테스트 | 결과 |
|---|---|---|---|
| M01 | 재고 전체 검증 전에 유효한 색부터 공개 변경 메서드로 반영 | `test_stock_mixed_valid_invalid_is_atomic` | 검출: 전체 상태 불변 위반 |
| M02 | 승인 검사를 데이터·그래프 생성 뒤, 서버 생성 앞으로 이동 | 보호 테스트 3개 모두 | 검출: 실제 데이터 생성 호출 |
| M03 | 승인 검사 전에 빈 `ShopGraph` 생성 | 보호 테스트 3개 모두 | 검출: 실제 그래프 생성 호출 |
| M04 | PUT 재고 경로만 `mutation=False` | `test_stock_exception_after_mutation_returns_uncertain_500` | 검출: 500 문구 불일치 |
| M05 | POST 구매 경로만 `mutation=False` | `test_purchase_exception_after_mutation_returns_uncertain_500` | 검출: 500 문구 불일치 |
| M06 | S4 `status_label`을 항상 `판매 중`으로 고정 | `test_popular_keeps_sold_out_product_and_status` | 검출: 품절 표시 불일치 |
| M07 | JSON의 NaN·Infinity 상수 거절 제거 | `test_nonfinite_json_numbers_are_rejected` | 검출: 3개 상수의 오류 문구 불일치 |
| M08 | 본문 상한을 64KiB에서 128KiB로 잘못 늘림 | `test_body_over_64kib_is_rejected` | 검출: 65537바이트 요청 수락·상태 변경 |
| M09 | JSON 중복 키 검사 제거 | `test_stock_nested_duplicate_key_is_rejected` | 검출: 중복 색상 요청 수락·상태 변경 |
| M10 | 비JSON 오류 번호를 다시 400으로 변경 | `test_non_json_content_types_rejected_before_mutation` | 검출: 6개 조합의 상태 코드 불일치 |

10개 고장 모두 검출했다. 이 실패들은 임시 사본의 의도된 고장 결과이며, 아래 실제 수정본의 전체 테스트 실패 수와 합산하지 않는다. 실행 도구는 저장소 밖 `../check_ui5_mutations.py`, 원문과 구조화 결과는 `../ui5-mutations/`에 보관했다.

### 실제 실행 결과

아래는 모두 이번 세션의 실행이다. 최초 샌드박스 환경에서는 로컬 HTTP 서버 소켓 생성이 거부되어 테스트를 완료하지 못했다. 로컬 통신 권한을 받은 뒤 기준본 174개 통과를 확인하고 작업을 진행했다.

```text
# 시작 기준 89e2887
$ python3 -B -m unittest
Ran 174 tests in 7.293s
OK

# [SPEC] 기대값만 변경한 상태
$ python3 -B -m unittest
Ran 174 tests in 7.546s
FAILED (failures=1)

# 구현 및 새 테스트 추가 후 관련 웹 테스트
$ python3 -B -m unittest tests.test_web tests.test_web_write tests.test_web_demo -v
Ran 40 tests in 12.792s
OK

# 구현 및 새 테스트 추가 후 전체
$ python3 -B -m unittest
Ran 189 tests in 13.270s
OK
```

분류: 기준본 **통과 174 / 미도래 0 / 실패 0**, [SPEC] 중간 상태 **통과 173 / 미도래 0 / 실패 1**, 수정본 **통과 189 / 미도래 0 / 실패 0**. 기존 UI2 테스트가 의도적으로 출력하는 `RuntimeError: after C07`은 500 처리 검사 로그이며 실패가 아니다. 원문은 저장소 밖 `../ui5-baseline.log`, `../ui5-spec.log`, `../ui5-targeted.log`, `../ui5-full.log`에 보관했다. 고장 주입 실행 명령은 작업 공간에서 `python3 -B work/check_ui5_mutations.py`다.

### 미실행 범위·미답 질문

- 이번 인계 작업 1의 요청 항목은 모두 수행했다. ID 한도도 내부 속성을 고치지 않고 고객 C99·구매 T999까지 공개 메서드와 HTTP로 확인했다. 상품 등록 HTTP 경로는 이번 웹 계약에 없으므로 상품 ID 한도 HTTP 검사는 해당하지 않는다.
- 프런트 수정·패키지 설치·브라우저 시연 재실행·LTS Node 재현 빌드는 이번 범위에 포함하지 않았다. 위쪽의 기존 브라우저 캡처 결과를 이번에 재실행한 것처럼 보고하지 않는다. 기존 LTS 재현 미확인 항목도 해소한 것으로 표시하지 않는다.
- UI6, 원격 push, main 합치기는 수행하지 않는다. 찬일 측 Claude Code 재확인과 찬일의 UI5 승인이 다음 단계다. 이번 자체 확인으로 그 승인을 대신하지 않는다.
- 구현 선택에 관해 새로 필요한 판정 질문은 없다. UI5 승인 가능 여부와 기존 LTS 재현 항목의 처리 판단은 찬일의 후속 검토에 남긴다.
