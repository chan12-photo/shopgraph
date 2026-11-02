# UI0 웹 화면 설계

- 작성: Codex, 2026-11-02. 승인자: 찬일. 상태: **UI0 보완 설계 / [승인] 대기**.
- 기준: `w12-prep` / `w12-complete`의 `61732037dc5b67413c9639859e6d53d28519d224`. 작업 브랜치: `web-ui`. `main`은 `bfd900c` 그대로 둔다.
- 찬일의 11/02 결정으로 웹을 추가한다. 콘솔은 교수님 확정 기본 화면이다. 이 문서의 API·화면 세부안은 아직 승인 전이며, UI1은 시작하지 않는다.
- 지정 순서대로 CLAUDE.md → 계획서 지정 절 → plan_pending → 기대값·장면 절차 → 결함·W12 G7·9784473 검토 원문 → 운영 코드 5개·tests/ 전체를 읽었다.
- 기대값 출처: 프로그램 계산 코드를 쓰지 않은 AI 독립 계산 2건 대조 + 찬일의 대표 항목 손 확인·승인이다. 이번 작업에서 새 기대값을 계산하거나 사람이 전체를 손계산했다고 기록하지 않는다.

## 1. G1 계획과 환경

1. 목표: Python 계산을 그대로 사용하는 웹의 API·문구·화면·검증 계약을 설계한다.
2. 수정 허용: 이 파일과 `docs/verification/plan_pending.md`만.
3. 코드·테스트·data.py·.gitignore·README·CLAUDE.md·계획서 본문은 변경하지 않는다.
4. G2는 기존 테스트 확인과 후속 테스트 계획으로 수행한다. UI0에서는 테스트 코드도 작성하지 않는다.
5. G3 산출물은 문서 두 개, G4는 기존 전체 테스트 실제 실행이다.
6. G5·G6의 문서 대조와 미정 사항을 기록하고, G7 필수 게이트에서 멈춘다.
7. 요청에 따라 승인 대기 자료를 `[UI0]` 문서 커밋 하나로 보관한다. 승인 완료를 뜻하지 않는다.
8. 위험: 콘솔 출력 회귀, 계산의 TypeScript 중복, HTTP 실패의 상태 보존 범위, 의존성 범위.

환경 확인 원문(브랜치 생성 전, 저장소 `/Users/chan12/projects/shopgraph`):

```text
$ python3 --version
Python 3.13.12
$ node -v
v25.8.1
$ npm -v
11.11.0
$ git status
On branch w12-prep
nothing to commit, working tree clean
$ git branch --show-current
w12-prep
$ git rev-parse HEAD w12-prep w12-complete main
61732037dc5b67413c9639859e6d53d28519d224
61732037dc5b67413c9639859e6d53d28519d224
7543bbb9d36c0cfe63c75128d1927a92e1da45d1
bfd900c8028b2e8bce36b8ac2d9177a683d612a0
$ git rev-parse 'w12-complete^{commit}'
61732037dc5b67413c9639859e6d53d28519d224
$ git switch -c web-ui 6173203
Switched to a new branch 'web-ui'
```

## 2. 실행 구조와 책임

`main.py`가 유일한 실행 진입점이다. 인자 없는 실행은 기존 `run()` 그대로다. `--web`일 때만 지연 import한 `web.create_server()`를 사용한다. 서버 시작마다 `ShopGraph(*initial_records())` 한 개를 새로 만들고, 그 객체를 서버 인스턴스가 참조한다. 요청마다 초기화하지 않는다. 저장·초기화 API는 만들지 않으며 처음 상태로 돌아가려면 서버를 재시작한다.

새 공개 계약은 `web.create_server(g: ShopGraph, port: int = 8000) -> HTTPServer`다. `127.0.0.1`로 고정 바인드하고 `HTTPServer`로 순차 처리한다. `ThreadingHTTPServer`·요청별 작업 스레드는 쓰지 않는다. 운영 경로의 출력·브라우저 열기·종료 처리는 main.py가 맡고, web.py는 HTTP 응답을 쓴다. `Ctrl+C` 뒤 소켓을 닫는다.

web.py는 graph·search의 공개 함수·ShopGraph 공개 메서드·읽기 전용 공개 상수와 승인받을 view 순수 함수만 호출한다. `_adj`, `_edges`, `_next_ids`나 main.py의 내부 함수를 읽지 않는다. 점수·가중치·품절·추천 범위는 기존 Python 결과를 받는다. TypeScript는 입력값·선택 상태·받은 응답·화면 배치만 관리한다. 서버가 준 순위를 다시 정렬하거나 구매 기록으로 점수를 계산하지 않는다.

## 3. API 계약안

### 3.1 공통 형식

- 같은 출처의 `/api/` JSON API. 응답은 UTF-8 `application/json`, `Cache-Control: no-store`. GET 요청에는 본문이 없다. 배열 순서는 계약의 일부이며 중복 제거·재정렬을 클라이언트에 맡기지 않는다.
- POST·PUT 본문은 JSON 객체다. 필수 키 누락, 알 수 없는 키, 중복 JSON 키(중첩 stock 포함), 잘못된 UTF-8·JSON, NaN·Infinity는 변경 전에 400으로 거절한다. JSON bool·실수·null을 정수로 바꾸지 않는다.
- `k` 쿼리는 한 번만 허용한다. 생략하면 추천은 `K_DEFAULT`, S4는 `None`(전체)이다. 빈 값·`null` 글자·중복·알 수 없는 쿼리는 400. 숫자 문자열을 Python 정수로 변환한 뒤 범위 검사는 search 함수에 맡긴다. URL의 `+`는 경로에서는 보존하고, ID는 URL 인코딩한다.
- ID·구매일의 앞뒤 공백 제거는 Python HTTP 입력 변환에서 한다(콘솔과 같은 정책). 이름·색상의 정규화와 업무 값 검증은 ShopGraph가 한다. 성별은 메뉴 번호가 아닌 `"남"` 또는 `"여"`를 보낸다.
- 정수 표기 `int`는 JSON 정수이며 bool·실수·null·문자열이 아니다. 금액·재고도 JSON 정수로 송수신하고, 콘솔과 같은 9자리 초과 제한을 적용한다. 서버는 형식을 확인해 graph의 검증에 넘기며, 음수도 기존 범위 오류로 처리한다. JavaScript의 안전 정수 한계를 피하려고 decimal 문자열을 도입하지 않는다. 프런트는 금액·재고를 계산하지 않는다.

공통 자료형(아래 필드는 생략하지 않는다):

| 이름 | JSON 필드·형식 |
|---|---|
| Customer | `id: str, name: str, gender: "남" 또는 "여", age: int` |
| Product | `id, name, kind, style: str; price: int; stock: {색상명: int}`. 금액·재고는 9자리 이내 JSON 정수이며 stock 키는 Python에서 색상 이름순으로 구성 |
| Group | `id: str, label: str` (`GROUP_LABELS` 사용, 그룹 ID 문자열을 재해석하지 않음) |
| EdgeData | `colors: str[], count: int, total_qty: int, last_date: str(YYYY-MM-DD)`; 색상 이름순 |
| S1Item | `product_id, name: str; colors: str[]; weight, count, total_qty: int; last_date: str` (products_of 결과 그대로) |
| S2Item | `customer_id, name, group_id: str; colors: str[]` (customers_of 결과 그대로) |
| PopularItem | `product_id: str, score: int, buyers: int, sold_out: bool, product_name: str, status_label: str` (`판매 중` 또는 `품절`) |
| RecommendationItem | `product_id: str, score: int, buyers: int, scope: "group" 또는 "gender" 또는 "all", supporters: str[], available_colors: str[], product_name: str, scope_label: str, display_lines: str[3]` |
| Recommendation | `customer_id: str, k: int, items: RecommendationItem[], header_line: str, notice_lines: str[], lines: str[]` |
| Stats | `groups, customers, products, membership_edges, purchase_edges, purchases: int` (stats 결과의 6개 키) |

`str[3]`은 문자열 3개를 담은 JSON 배열이라는 뜻이다. Recommendation의 `display_lines`는 항목·근거·구매 가능 색상 순서이며, 근거 줄에는 조사·지지자 그룹·색상 수 안내까지 포함한다. `lines`는 원래 콘솔 추천 블록의 줄 전체, `notice_lines`는 실제로 존재하는 안내 줄만 기존 순서로 담는다. 빈 추천이면 items·notice_lines는 빈 배열이고 lines에는 기존 빈 결과 문장 한 줄만 있다.

### 3.2 경로별 계약

| 메서드·경로 | 요청 JSON / 쿼리 | 성공 응답 JSON | 호출하는 Python 공개 함수·메서드 |
|---|---|---|---|
| GET `/api/meta` | 없음 | 200 `{genders: [{value: str, label: str}], k_default: int, k_max: int}` | `GENDERS`, `GENDER_LABELS`, `K_DEFAULT`, `K_MAX` |
| GET `/api/graph` | 없음 | 200 `{nodes: [{id: str, kind: "group" 또는 "customer" 또는 "product", label: str, neighbor_ids: str[]}], edges: [MembershipEdge 또는 PurchaseEdge]}` | `GROUP_IDS`, `GROUP_LABELS`, `customer_ids`, `product_ids`, `get_customer`, `get_product`, `members`, `neighbors`, `edge`, `weight` |
| GET `/api/groups` | 없음 | 200 `{total_customers: int, branches: [{gender: str, label: str, count: int, groups: [{id: str, label: str, band_label: str, count: int, members: Customer[]}]}]}` | `GENDERS`, `GENDER_LABELS`, `AGE_BANDS`, `GROUP_IDS_BY_GENDER`, `GROUP_LABELS`, `customer_ids`, `members`, `get_customer` |
| GET `/api/stats` | 없음 | 200 `{stats: Stats}` | `stats()` |
| GET `/api/integrity` | 없음 | 200 `{violations: str[], violation_count: int, lines: str[]}` | `check_integrity()`; 건수·정상/위반 문구는 Python에서 구성 |
| GET `/api/customers/{id}` | 없음 | 200 `{customer: Customer, group: Group, purchases: S1Item[]}` | `get_customer`, `group_of`, `GROUP_LABELS`, `products_of` |
| GET `/api/products/{id}` | 없음 | 200 `{product: Product, buyers: S2Item[], sold_out: bool, available_colors: str[], status_label: str}` | `get_product`, `customers_of`, `is_sold_out`, `available_colors` |
| GET `/api/groups/{id}/popular` | `?k=정수` 선택 | 200 `{group: Group, k: int 또는 null, items: PopularItem[]}` | `group_popular`, `get_product`, `GROUP_LABELS` (그룹 검증은 group_popular 먼저) |
| GET `/api/customers/{id}/recommendations` | `?k=정수` 선택 | 200 `Recommendation` | `recommend`, `get_product`, `recommendation_view`, `recommendation_scope_label` |
| POST `/api/customers` | `{name: str, gender: str, age: int}` | 201 `{customer: Customer, group: Group}`; 새 ID는 customer.id. 추천은 별도 GET으로 조회 | `add_customer`, `get_customer`, `group_of` |
| POST `/api/purchases` | `{customer_id: str, product_id: str, color: str, qty: int, date: str}` | 201 `{purchase_id: str, customer_id: str, product_id: str, edge: EdgeData, weight: int}`; 변경 직후 edge·weight만 조회 | `add_purchase`, `edge`, `weight` |
| PUT `/api/products/{id}/stock` | `{stock: {색상명: int}}` 전체 | 200 `{product: Product, sold_out: bool, available_colors: str[], status_label: str}`; 변경 직후 get_product 결과 | `update_product(id, stock=검증한_재고)`, `get_product`, `is_sold_out`, `available_colors` |

MembershipEdge는 `{kind: "membership", source: 그룹ID, target: 고객ID, weight: null}`이다. PurchaseEdge는 `{kind: "purchase", source: 고객ID, target: 상품ID, weight: int, ...EdgeData}`이다. 두 종류 모두 무방향이며 같은 간선을 양쪽 방향으로 두 번 보내지 않는다. 노드는 그룹 → 고객 → 상품, 종류 안에서는 ID 순이다. 소속 간선은 그룹·고객 ID 순, 구매 간선은 고객·상품 ID 순이다. 고립 상품과 빈 그룹도 노드에 포함한다. 이웃 강조는 Python이 돌려준 neighbor_ids를 사용한다.

그룹 트리는 성별·연령대 공개 상수 순서, 고객은 ID 순이다. S1·S2는 기존 ID 순, S4·추천은 search 반환 순서 그대로다. 그룹별 인원·통계·위반 수는 Python에서만 계산한다. 무결성 정상 문장은 `[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인`이며, 정확성을 증명한다고 표시하지 않는다.

### 3.3 오류와 상태

| 상황 | 응답·처리 |
|---|---|
| 업무 입력의 ValueError | 400 `{"error": str(error)}`. 예: `{"error":"나이: 10~99이어야 합니다 (입력: 5)"}`. 기존 한국어 메시지를 재작성하지 않는다. 화면의 `[오류]` 표시는 공통 오류 컴포넌트가 붙인다 |
| 없는 고객·상품·그룹 ID | 공개 함수가 내는 ValueError 그대로 400. 없는 URL 경로와 구별 |
| 잘못된 HTTP 입력 | 변경 전에 400 `{"error":"요청 JSON: ..."}` 등 HTTP 전용 한국어 문구. 기존 콘솔에 없는 전송 오류만 새 문구를 정함 |
| 없는 경로·정적 파일 | 404 `{"error":"없는 경로입니다"}`. API 오타에 index.html을 대신 주지 않음 |
| 알려진 경로의 지원하지 않는 메서드 | 405 JSON 오류 + Allow. 내용 형식이 JSON이 아니면 415, 본문이 64 KiB를 넘으면 413 |
| 허용하지 않는 Host·Origin | 403 JSON 오류. Host는 실제 `127.0.0.1:포트`, Origin이 있으면 같은 출처만 허용. CORS를 열지 않음 |
| 그 밖의 요청 처리 예외 | 500 `{"error":"서버 처리 중 오류가 발생했습니다"}`. 예외를 숨기고 성공 처리하지 않으며 서버 측 진단 기록을 남김. 다음 요청은 계속 처리 |

ValueError·전송 검증 실패는 원본·그래프·ID 카운터 전체가 불변이어야 한다. 본문을 모두 읽고 형식 변환을 끝낸 뒤 변경 메서드 한 번을 호출한다. 고객 등록의 추천 K는 고정 기본값이라 등록 뒤 잘못된 K를 검증하는 경로를 만들지 않는다. 구매는 재고를 차감하지 않으며 재고 0인 기존 색상도 기록 가능하다. 재고 수정은 전체 교체이고, 구매된 색상을 빼면 전체 요청이 거절된다.

**판단 D1 — 승인 범위:** 입력·전송 검증 실패는 변경 전에 400으로 거절하고 상태(원본·그래프·ID 카운터)를 불변으로 한다. 예상 밖 예외는 500 JSON으로 응답하고 서버는 다음 요청을 계속 처리한다. 변경 뒤 응답 생성에서 500이 나면 본문에 `변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요`를 포함한다. graph.py 공개 메서드에 임의 예외까지 되돌리는 트랜잭션 계약은 없으므로, 변경 API는 추천을 함께 계산하지 않는다. 고객 등록은 `{customer, group}`만, 구매·재고 수정은 변경 결과와 그 직후 단순 공개 조회만 반환하고 추천은 별도 GET으로 조회한다. 연결이 끊긴 경우도 자동 재시도하지 않고 조회로 상태부터 확인한다.

## 4. view.py 순수 함수 추출안 — UI1의 [SPEC] 대상

| 함수 | 반환·전제 |
|---|---|
| `recommendation_view(g: ShopGraph, customer_id: str, result: list[dict], k: int) -> dict` | `{"header": str, "items": [[항목줄, 근거줄, 색상줄], ...], "notices": [str, ...]}` 구조의 새 객체. 빈 결과는 header만 있고 items·notices가 빈 리스트. stdout 출력·상태 변경 없음. result는 같은 g·고객·k의 recommend 반환값이고 호출 사이 상태가 바뀌지 않음 |
| `recommendation_scope_label(g: ShopGraph, customer_id: str, scope: str) -> str` | `같은 그룹` / 해당 성별 `전체` / `전체 고객`. scope는 recommend의 3개 값 중 하나. 카드 배지와 추천 문장 모두 이 함수를 사용 |

현재 print_recommendation의 머리·빈 결과 분기·항목·안내 조건을 recommendation_view로 옮긴다. `_print_item`은 출력 없는 내부 줄 생성 함수로 바꾸고 기존 `_id_particle`·`_widen_note` 규칙을 그대로 사용한다. print_recommendation의 이름·인자·None 반환은 유지하고, 구조의 header → items의 세 줄 → notices 순서로 한 줄씩 출력한다. 마지막 개행·들여쓰기·조사·빈 결과 한 줄 종료도 그대로다. 기존 유효 입력의 콘솔 출력은 한 글자도 바꾸지 않는다.

web.py는 recommendation_view가 반환한 구조를 그대로 JSON으로 전달한다. 표시 구조의 분할·재조립 없이 넓힘·부족·비교 조건을 다시 판정하지 않는다. 근거의 색상 수는 view가 `g.weight()`로 읽으며 상한 3을 적용하지 않는다. 화면은 근거 문장을 파싱하거나 조사를 만들지 않는다. scope_label도 view 순수 함수가 준다.

UI1에서는 `[SPEC][UI1]`로 이 공개 계약을 먼저 기록하고 구현 커밋과 분리한다. 관련 문안은 plan_pending 13번이다. 계산·기대값은 변경하지 않으므로 6장·demo_expected 값 재계산은 없다.

검증: 기존 test_flow의 추천 전체 문자열 비교, test_view, test_demo를 그대로 실행한다. 추가 테스트는 순수 함수가 stdout을 쓰지 않는지, snapshot과 입력 result가 불변인지, 없는 고객에서 ValueError인지, 줄을 개행으로 이은 값이 기존 승인 문자열과 같은지 검사한다. 기존 print 함수와 새 함수를 서로 비교하는 검사만으로 형식의 정확성을 주장하지 않는다. 빈 결과·범위 하나/여럿·후보 없는 확장·K 부족·조사·2색 이상 지지자·가중치 4를 모두 포함한다.

## 5. 화면 6개와 시연 연결

공통: 상단에 콘솔이 기본이고 웹은 추가 화면임을 표시하고, `서버 재시작 시 처음 상태`를 안내한다. 왼쪽 탐색 6개, 본문, 선택한 고객·상품의 연결 패널로 구성한다. 외부 글꼴 없이 시스템 글꼴·직접 작성 CSS를 쓴다. 로딩·빈 결과·오류를 구별하고 오류 뒤에도 입력값은 보존한다.

| 화면 | 구성·동작 | 시연 장면 |
|---|---|---|
| ① 그래프 | SVG의 그룹 / 고객 / 상품 3열. 서버 배열 순서로 배치, 빈 그룹·고립 상품 포함. 구매 간선 굵기는 `weight` px(상한 적용 전), 소속 간선은 일정한 점선. 범례·숫자도 제공. 노드 선택 시 전달받은 이웃과 연결 간선 강조, 나머지는 흐리게. 키보드 선택과 상세 이동 제공. 옆에 그룹 트리·인원 | 1 소개, 2·7 소속 추가, 3·5 구매 간선 변화 |
| ② 고객 상세 | 고객·소속 그룹, S1 표, K 입력, 추천 카드. 카드에 Python 점수·범위 배지·근거·구매 가능 색상·안내 줄. 응답 순서를 유지하며 점수가 다른 범위를 가로질러 순위를 다시 매기지 않음 | 2·3·4·6·7 |
| ③ 등록·구매 패널 | 고객 등록과 과거 구매 기록 입력. 등록 성공 응답의 ID·그룹·즉시 추천을 표시. 구매 뒤 반환 weight 표시, 그래프·선택 고객 S1/추천·그룹 인기를 순서대로 재조회. 모든 색상을 구매 기록 입력에 허용하되 최종 판단은 Python. 요청 중 제출을 막아 이중 클릭 방지 | 2·3·5·7 |
| ④ 그룹 인기 S4 | 그룹·개수(전체/1~10), 순위 표와 직접 그린 SVG 막대. 막대 길이만 서버 score를 좌표로 변환. 전·후 패널은 같은 그룹·k에서 받은 두 응답을 그대로 보관·표시. 비교 시작 시 서버 응답을 전으로 고정하고 후만 갱신; 그룹·k를 바꾸면 비교 해제. 품절도 포함 | 5의 구매 전·후, 6 뒤 품절 표시 설명 |
| ⑤ 상품 상세 | S2 구매 고객·그룹·색상, 색상별 재고, Python 품절·구매 가능 색상. 재고 편집은 기존 색상 전체를 채운 폼에서 전체 교체 PUT. 모두 0 설정은 요청값 편집이며 품절 여부는 응답만 사용. 성공 뒤 해당 상품·추천·S4 갱신 | 3의 상품 선택, 6의 재고 변경 |
| ⑥ 무결성 검사 | 통계 6항목과 검사 실행 버튼, Python이 준 결과 줄·위반 목록. 검사 중 상태를 고치거나 rebuild하지 않음. “원본과 그래프의 일관성 확인”이라고 설명 | 8 |

갱신 완료 전 화면에 갱신 중임을 표시한다. 변경 요청은 순차 처리하고 완료 전 다시 제출하지 않는다. 오래 걸린 이전 GET이 최근 선택을 덮지 않도록 요청 순번 또는 AbortController로 이전 응답을 버린다. UI에서 성공을 미리 가정해 간선·추천을 고치지 않는다. 다른 탭도 같은 서버 상태를 공유하며, 발표는 한 탭에서 진행한다.

장면 1~8은 서버 한 번 실행 안에서 w11_scenes 순서를 그대로 따른다. 장면 3 날짜는 10/30·10/31, 장면 5는 10/30·10/30·10/31이다. 장면 6은 승인된 P_top6의 모든 색상을 유지한 채 0으로 보낸다. 장면 7의 점수 비교 안내는 승인 기대값대로 없으며, 섞인 범위의 설명은 별도 고정 데이터 사례로 한다. 화면 이동·새로고침으로 서버 데이터를 초기화하지 않는다.

## 6. 테스트 계획

| 단계 | 검사·통과 기준 |
|---|---|
| UI1 HTTP·읽기 | unittest + urllib.request로 실제 HTTP. 같은 프로세스에서 `create_server(fixtures.make_graph(), port=0)`를 백그라운드 스레드에 두고 `serve_forever()`를 실행한다. 서버 자체는 HTTPServer 단일 요청 처리이며, 응답을 받은 뒤 같은 graph 객체로 snapshot을 직접 비교한다. 테스트 끝에 `shutdown()`·`server_close()`를 finally에서 보장. 모든 읽기 응답의 필드·형식·순서·중복·빈 결과·스냅샷 불변 검사 |
| UI1 경계·정적 파일 | 없는 경로/ID, 잘못된 k·중복 쿼리, 메서드, Host/Origin, JSON 오류 응답, 경로 이탈·디렉터리 목록 노출 방지, dist 없음(503), MIME, 정적 파일 바이트. main 무인자·--web 분기, 포트 충돌, Ctrl+C 종료 검사. 실제 브라우저 실행은 테스트에서 대체 |
| UI2 변경 | 고객 등록·구매·재고 전체 교체의 실제 HTTP, 실패 요청마다 서버 프로세스에서 `tests.helpers.snapshot(g)` 전후 비교(제어 파이프로만 확인, 운영 API로 노출 안 함). 실패 뒤 다음 ID, 혼합 유효/무효 재고, 구매된 색상 삭제 거절, bool·실수·null·숫자 문자열(나이/수량)·중복 키·정밀도 큰 재고·잘못된 날짜·ID 한도 검사. 성공 변경마다 check_integrity == [] |
| UI2 예외 | 조회 중 RuntimeError를 고장 주입해 500 뒤 정상 GET 가능 확인. 변경 후 응답 생성 실패도 별도 주입해 D1 한계를 숨기지 않음. 프로세스 종료·연결 끊김을 성공으로 보고하지 않음 |
| UI3·UI4 프런트 | `tsc --noEmit`와 `vite build` 모두 성공. 설치된 로컬 실행 파일만 사용. Python 전체 테스트도 통과. TypeScript에 추천·상한·품절·안내 조건 로직이 없는지 코드 대조. 자체 SVG, 외부 URL·CDN·글꼴·추가 직접 의존성 없음 확인 |
| UI5 웹 시연 | 새 서버 하나에서 장면 1~8을 HTTP 순서로 수행. 기대값은 docs/demo_expected.md만 읽음. API 응답의 ID·순서·개수·중복·점수·구매자·범위·지지자·색상·색상 수 문구·안내 존재·S1·S4 전후·통계·위반 수를 직접 비교. API와 같은 recommend/view 함수로 기대값을 만들지 않음 |

새 시연 테스트는 기존 test_demo의 파서·승인 보호를 재사용하는 테스트 전용 읽기 어댑터에서 시작한다(운영 코드에서 tests를 import하지 않음). 기존 파일·기대값은 고치지 않는다. 먼저 승인 줄을 확인하고 8장면 전체 양식·빈칸을 검사한 다음에만 서버를 만든다. 보호 실험은 /tmp 사본에서 data.py 또는 실행 함수를 즉시 실패하도록 대체하고 기대값의 빈칸·형식·승인 줄을 훼손해 실행 차단을 확인한다. UI5까지 기대값을 코드에 복사하거나 실행값으로 채우지 않는다.

실제 브라우저 확인은 API 테스트와 별도다. UI3 이후 dist를 Python 서버로 제공해 시연 PC의 Chrome 또는 Edge, 개발 Mac의 Safari에서 버전·창 크기·행동·결과를 기록한다. 장면 1~8, 화면 새로고침, 긴 근거 줄, 키보드 선택·포커스, 좁은 창의 스크롤, 이중 제출·오류 복귀, 네트워크 차단 상태를 확인한다. DOM의 카드·행·안내 줄이 API와 같은 순서·개수인지 대조하고 화면 캡처를 남긴다. 새 브라우저 자동화 패키지는 설치하지 않는다. **브라우저 검증·HTTP 서버·프런트 빌드는 UI0에서 미실행**이다.

## 7. 파일 구조·의존성·명령

| 단계 | 추가·수정할 위치 |
|---|---|
| UI0 | docs/verification/ui0_design.md, plan_pending.md (문서만) |
| UI1 | web.py, main.py의 웹 분기, view.py의 순수 함수, tests/test_web.py·test_web_view.py 추가, 검증 기록. [SPEC][UI1] 계약 기록은 구현과 별도 |
| UI2 | web.py 변경 API, tests/test_web.py 추가 검사, 검증 기록 |
| UI3 | frontend/package.json·package-lock.json·tsconfig.json·vite.config.mjs·index.html·src/main.tsx·App.tsx·api.ts·types.ts·styles.css, frontend/dist/, .gitignore |
| UI4 | frontend/src/components/·screens/의 6화면, dist 재빌드, 검증 기록 |
| UI5 | tests/test_web_demo.py·demo 읽기 어댑터 추가, docs/verification/ui5_* 검증 기록 |
| UI6 | docs/verification/의 실행·빌드·검증 안내, 계획서 반영 대기 문안. 금지된 문서 본문은 계속 직접 수정하지 않음 |

`.gitignore`는 UI3에서 `/frontend/node_modules/`, `/frontend/*.tsbuildinfo`, `/frontend/.vite/`만 추가한다. `/frontend/dist/`는 제외하지 않고 index.html과 해시가 붙은 JS·CSS를 모두 추적한다. 저장소 루트나 개발 서버가 아닌 `Path(__file__)` 기준 dist만 제공한다. 디렉터리 목록·저장소 소스·상위 경로를 제공하지 않는다.

정확한 버전(11/02 npm 공식 registry의 메타데이터 조회, **설치·빌드 미실행**):

| 패키지 | 고정 버전 | 구분 |
|---|---|---|
| react | 19.3.1 | 실행 번들, 게시 2026-10-14 |
| react-dom | 19.3.1 | 실행 번들, 게시 2026-10-14 |
| typescript | 7.0.2 | 개발, 게시 2026-07-08 |
| vite | 8.3.4 | 개발, 게시 2026-10-08. 최신 8.3.5(2026-10-21)는 2주 미만이어서 바로 이전 안정 버전 선택 |
| @types/react | 19.3.0 | 개발, 게시 2026-09-09 |
| @types/react-dom | 19.3.0 | 개발, 게시 2026-09-09 |

UI3에서 위 정확한 버전과 package-lock.json을 함께 고정하며 `^`·`~`·latest를 package.json에 쓰지 않는다. 각 버전의 게시일을 기록하고, 게시 2주 미만이면 위와 같이 바로 이전 안정 버전을 선택한다. typecheck·build가 실패해도 버전을 바꿔가며 시도하지 않고 멈춰 보고한다. Vite의 확인된 Node 조건은 `^20.19.0 || >=22.12.0`, 현재 Node는 이에 맞는다. 현재 Node v25는 홀수 단기 지원이므로 UI3 전에 짝수 LTS 사용을 권장하지만 막는 조건은 아니다. 조합의 실제 호환성은 아직 미실행이다. Vite 기본 TSX 변환과 TypeScript `jsx: react-jsx`를 쓰며 React 플러그인은 추가하지 않는다. Vite 설정은 .mjs로 두고 앱 타입 검사 범위는 src로 한정해 @types/node를 직접 추가하지 않는다. React Fast Refresh는 요구하지 않는다.

**판단 D2 — 간접 의존성:** “4+2개”는 직접 선언하는 패키지 여섯 개로 해석하는 안이다. react-dom·Vite 등이 요구하는 간접 패키지는 필수이므로 UI3에서 lock 파일로 고정·검토한다. 간접 패키지까지 여섯 개 밖을 금지한다는 뜻이면 이 구조로 설치할 수 없으므로 UI3 전에 멈춰 판정을 받는다. UI0에서는 아무 패키지도 설치하지 않았다. 추가 직접 패키지가 필요하면 설치 전에 멈춘다.

예정 명령(현재 구현된 전체 테스트 외에는 **미실행**):

```text
# 저장소 루트: 시연 때 Node 불필요
python3 main.py
python3 main.py --web
python3 main.py --web --port 8001
python3 main.py --web --port 0

# frontend/: UI3에서 lock 파일 생성 뒤 개발·재현 빌드
npm ci
npm run typecheck     # tsc --noEmit
npm run build         # tsc --noEmit && vite build

# 저장소 루트: 매 커밋 직전 전체 회귀
python3 -B -m unittest -v
```

포트 기본값은 8000, `--port 0`은 OS가 빈 포트를 정한다. main이 실제 URL을 출력하고 표준 webbrowser로 열기를 시도한다. 자동 열기에 실패해도 URL로 접속할 수 있다. 개발도 빌드한 dist를 Python으로 제공해 단일 출처를 유지하며, Vite 개발 서버·프록시는 필수 기능에 넣지 않는다.

## 8. 위험과 대응

| 위험 | 대응·확인 시점 |
|---|---|
| 시연 당일 오프라인·Node 없음 | dist 추적, 외부 요청 0, 시스템 글꼴. UI5에서 Node 없는 PATH·네트워크 차단 후 Python 서버 실행 |
| Node 홀수 단기 지원(v25) | UI3 전에 짝수 LTS 사용을 권장한다. UI0을 막지는 않으며, typecheck·build는 지정 버전에서 실패 시 버전 변경 없이 중단·보고 |
| 포트 충돌·브라우저의 선연결이 단일 서버를 점유 | 충돌 시 새 서버를 시작하지 않고 명확한 오류와 --port 안내. HTTP/1.0 연결 종료·읽기 시간 제한으로 대기 연결 해제. UI1 실제 HTTP 검사 |
| 브라우저 호환·SVG 밀집 | UI5에서 실제 버전 명시. SVG viewBox·스크롤·텍스트 범례·키보드 조작. 간선 가중치 수치와 표를 함께 제공 |
| 콘솔 회귀 | main.run 유지, 추천 문구 공유, 기존 기대값 수정 금지, 매 커밋 전체 146개 이상 회귀. 실패 시 기대값을 바꾸지 않고 중단 |
| 의존 패키지 공급망 | 직접 의존 6개와 lock 무결성 값·간접 목록 확인, 추가 패키지/설치 스크립트 검토, npm ci로 재현, 자동 업데이트·CDN 없음. 보안 점검 실패를 --force로 넘기지 않음 |
| 정적 파일·브라우저에서 잘못된 요청 | dist 내부 경로만 허용, MIME 지정, HTML 주입 없이 React 텍스트 렌더링, Host·Origin 확인, 본문 제한. API 오류는 JSON으로 통일 |
| 서로 다른 시점의 그래프·추천 표시 | 한 탭 시연, 요청 순차 처리, 완료된 변경 뒤 재조회, 오래된 응답 폐기. S4 전 상태는 받은 응답을 보존 |
| 500 뒤 중복 등록·입력 정밀도 | D1 판정, 자동 재시도 금지·조회 확인. 금액·재고는 JSON 정수, 콘솔과 같은 9자리 제한 |

## 9. G4~G8 기록과 승인 판단

- G4: Codex가 `python3 -B -m unittest -v`를 실행해 **통과 146 / 미도래 0 / 실패 0**을 확인했다(test_demo 8개 포함). 커밋 직전 재실행의 원문은 임시 로그로 보관하고 종료 코드·개수·OK를 확인한 뒤에만 커밋한다. 사람의 실행 결과가 아니다.
- G5: 아래 항목별로 대조했다. HTTP·브라우저·빌드는 미실행이다.
- G6: **Claude 채팅 검토, 설계 문서 대조, 코드 실행 없음, 반드시 수정 0 / 설계 변경 5건(D1 구조, D3, 아래 1~3)**. 원칙과 설계의 대조로 갈음하며 실행 결과로 기록하지 않는다.
- 기존 구현의 새 결함 판정은 하지 않았다. D1·D2와 아래 세부안은 UI0에서 결정할 항목이며 구현 결함 수로 집계하지 않는다.
- G7: 찬일 [승인] 기록 뒤 UI1 착수 전까지 멈춘다. 이해 질문은 요청대로 기록만 하고 나중에 모아 확인한다.
- G8: `[UI0]` 보완 커밋 뒤 `[승인] UI0` 기록 커밋. 각 커밋 직전 실제 테스트 분류·미답 질문·측정 구간을 본문에 기록한다. [AI]·Co-Authored-By·생성 도구 문구는 넣지 않는다. push·PR·main 합치기 없음.

| G5 항목 | 판정·근거 |
|---|---|
| 표준 라이브러리 import | 해당 없음: 코드 변경·설치 없음, Python 표준 라이브러리만 쓰는 설계 |
| eval·exec·global·예외 무시 | 해당 없음: 코드 변경 없음, 500을 기록하고 다음 요청을 처리하는 계획 |
| ShopGraph에서만 변경 | 확인함: 변경 API 3개를 공개 메서드에 대응 |
| 내부 속성 접근 금지 | 확인함: 공개 호출 표 작성, snapshot은 테스트 프로세스에서만 사용 계획 |
| 조회·입력 복사 | 해당 없음: graph 계약·구현 변경 없음 |
| 무결성 검사 불변 | 확인함: check_integrity 조회만 계획, rebuild 호출 없음 |
| 공개 함수 계약 | 확인함: 새 web·view 계약을 승인 전 제안으로 구분 |
| 경계 테스트 | 확인함: 6절 계획 작성, 새 테스트 작성·실행은 미실행 |
| 실패 snapshot·혼합 입력 | 확인함: UI2 계획에 ID 카운터 포함, D1의 보장 범위 명시 |
| 고정 데이터 분리 | 확인함: 일반 API는 fixtures, UI5만 승인된 demo_expected와 시연 데이터 |
| 다음 단계 함수 호출 금지 | 확인함: UI0 코드 없음, 기존 테스트만 실행 |
| 중복 로직 | 확인함: 계산은 graph/search, 추천 표시 조건은 view 한곳으로 계획 |
| print 위치 | 확인함: 출력은 main/view, web은 HTTP 응답 작성으로 계획 |
| 결정적 순서 | 확인함: API 배열별 순서 명시, TypeScript 재정렬 금지 |
| docstring | 해당 없음: Python 파일 변경 없음 |
| 수정 범위 | 확인함: git status·diff로 문서 두 개만 확인 |
| 테스트 삭제·skip·기대값 변경 | 확인함: tests/·demo_expected 변경 없음, 전체 146개 통과 |
| 특정 ID 하드코딩 | 확인함: API·화면은 선택값 사용, 시연의 지정 ID는 입력 절차에만 존재 |

찬일 판단 항목 반영: **D1** 입력·전송 검증 실패만 상태 불변, 예상 밖 500은 서버 생존과 `변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요` 문구, 변경 API는 변경 결과·직후 단순 조회만 반환하고 추천은 별도 GET. **D2** 6개 직접 의존성과 lock에 포함되는 필수 간접 의존성 구분. **D3** 금액·재고는 JSON 정수와 9자리 제한(decimal 문자열 반려), 기본 포트·HTTP 계약·화면·테스트 세부안 채택. **D4** G6는 Claude 채팅의 설계 문서 대조로 갈음. 승인된 아키텍처 자체를 다시 결정해 달라는 뜻은 아니다.

UI0 이해 질문(찬일 미답, 답은 나중에 모아서 확인):

1. 예측: 같은 색을 수량만 늘려 다시 구매하면 그래프 간선 굵기와 S1의 기록 수·총수량은 각각 어떻게 되고, 웹은 무엇을 다시 받아야 하나?
2. 원인: 콘솔에는 없던 점수 비교 안내가 웹에만 나온다면 계산·문구·화면 중 어느 경계를 먼저 확인해야 하나?
3. 설명: Node 없이 웹을 실행할 수 있는 이유와, HTTPServer를 단일 요청 처리로 쓰는 이유는 무엇인가?

## 10. 외부 문서 확인

Context7으로 공식 자료를 확인했다. Vite는 TSX 변환과 타입 검사를 구별하고, TypeScript noEmit은 파일 출력 없이 타입을 검사하며, React는 createRoot로 브라우저 루트를 만든다. 위 최소 구성의 가능성을 판단한 근거이며 실제 빌드 성공 근거는 아니다.

- [Vite 기능 문서](https://github.com/vitejs/vite/blob/main/docs/guide/features.md)
- [TypeScript noEmit](https://www.typescriptlang.org/tsconfig/noEmit.html), [JSX 설정](https://www.typescriptlang.org/tsconfig/jsx.html)
- [React createRoot](https://react.dev/reference/react-dom/client/createRoot)
- 버전·engines·peerDependencies: `https://registry.npmjs.org/{패키지}/latest`를 11/02에 읽기만 수행. UI3 실제 설치 시 정확한 버전으로 고정한다.
