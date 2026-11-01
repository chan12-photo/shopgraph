# ShopGraph 코드 읽기 안내서

- 대상: 이 코드를 처음 읽는 학부생
- 기준: w12-prep 브랜치 491ad40의 코드와 docs/project_plan.md(계획서)
- 줄 번호는 위 커밋 기준이에요. 코드가 바뀌면 줄 번호도 달라질 수 있어요.
- 예시는 계획서 6장 고정 데이터(tests/fixtures.py와 같은 데이터)와 6장 기대값만 써요. 시연 데이터(data.py)로 계산한 결과는 없어요.

## 1. 파일 5개와 부르는 방향

```text
main.py  (메뉴, 입력 변환, 오류 메시지)
   │  부름
   ├──> graph.py   ShopGraph: 원본 데이터 + 그래프 + 모든 변경 메서드
   ├──> search.py  읽기 전용 조회·검색·추천 (첫 인자 g: ShopGraph)
   └──> view.py    화면 출력 (print만)
data.py  초기 데이터 → main.run()이 ShopGraph를 만들 때 한 번 씀

search.py ──> graph.py (공개 메서드와 대문자 상수만)
view.py   ──> graph.py (공개 메서드와 대문자 상수만)
```

| 파일 | 하는 일 | 근거 |
|---|---|---|
| main.py | 유일한 진입점이에요. 메뉴를 보여 주고, 입력 문자열을 값으로 바꾸고, ValueError를 "[오류] …"로 보여 줘요 | main.py:1-7 (모듈 설명), main.py:55 run, main.py:78 _menu_loop |
| graph.py | 데이터를 바꾸는 유일한 통로예요. ShopGraph 클래스 하나에 원본·그래프·ID 카운터가 있어요 | graph.py:510 class ShopGraph, 계획서 5.5 (402줄부터) |
| search.py | 데이터를 바꾸지 않는 함수들이에요. 조회, S1~S4, 추천 | search.py 모듈 설명 1~11줄, search.py:372 recommend |
| view.py | 화면 출력만 해요. 모든 함수가 None을 돌려줘요 | view.py 모듈 설명 1~7줄 |
| data.py | 실행용 초기 데이터예요. 부를 때마다 새 리스트를 만들어 돌려줘요 | data.py:16 initial_records |

- main.py가 import하는 것: data의 initial_records, graph의 상수와 ShopGraph, search 함수 6개, view 함수 4개 (main.py:14-17)
- search.py가 graph에서 가져오는 것은 상수와 ShopGraph 이름뿐이에요 (search.py:13). graph.py의 `_`로 시작하는 내부 함수는 쓰지 않아요 (CLAUDE.md "구조" 절)
- view.py도 graph의 상수와 ShopGraph만 가져와요 (view.py:11)

## 2. 자료구조 (ShopGraph 안의 7가지)

계획서 부록 B.1(1323~1333줄)에 모양이 정해져 있어요. 생성자가 만드는 곳은 graph.py:532-551이에요.

| 속성 | 담는 것 | 6장 데이터로 본 모양 | 근거 |
|---|---|---|---|
| `_customers` | 고객 ID → 고객 딕셔너리 | `"C01" → {"id": "C01", "name": "고객1", "gender": "여", "age": 23}` | graph.py:532, 계획서 507줄 |
| `_products` | 상품 ID → 상품 딕셔너리 (재고는 색상 → 수량 딕셔너리) | `"P05" → {…, "stock": {"그레이": 0, "블랙": 0}}` (전부 품절) | graph.py:533, 계획서 522줄 |
| `_purchases` | 구매 ID → 구매 기록 딕셔너리 | `"T001" → {"id": "T001", "customer_id": "C01", "product_id": "P01", "color": "블랙", "qty": 1, "date": "2026-09-01"}` | graph.py:534, 계획서 528줄 |
| `_groups` | 그룹 ID → 그룹 정보 (8개, 시작할 때 전부 만듦) | `"G-F-20" → {"id": "G-F-20", "gender": "여", "band": "20대"}` | graph.py:535-539, 계획서 1329줄 |
| `_adj` | 노드 ID → 이웃 ID 집합 (그룹·고객·상품 모두) | C01의 이웃은 G-F-20, P01, P02 | graph.py:540, graph.py:1225 _build_graph, tests/test_view.py TestW9Neighbors.test_customer_node |
| `_edges` | (고객 ID, 상품 ID) → 간선 집계 {색상 집합, 기록 수, 총수량, 최근 구매일} | (C01, P01) → 색상 4가지, 기록 4건, 총수량 4, 최근 2026-10-01 | graph.py:541, graph.py:445 _aggregate_edges, 계획서 545줄 |
| `_next_ids` | 다음에 발급할 번호 | `{"C": 7, "P": 6, "T": 14}` | graph.py:546-550, graph.py:410 _next_number, 계획서 1333줄 |

알아 두면 좋은 점

- 그래프(`_adj`·`_edges`)는 원본 세 개에서 매번 다시 만들어요. `rebuild()`가 `_build_graph()` 결과를 그대로 넣어요 (graph.py:1098).
- `_build_graph()`는 고객마다 성별·나이로 그룹을 찾아 연결하고(graph.py:1243-1245), 구매 기록을 쌍별로 묶어 간선 집계를 만든 뒤 양쪽 인접 리스트에 서로를 넣어요(graph.py:1246-1249).
- 간선 집계는 `_edges` 한 곳에만 있어요. 고객 쪽과 상품 쪽에 따로 두지 않아요 (계획서 5.2 "저장 방식", 235줄 부근).
- 가중치는 색상 집합의 크기예요. `weight()`는 `len(agg["colors"])`를 돌려줘요 (graph.py:1014). 그래서 같은 색을 또 사면 기록 수는 늘어도 가중치는 그대로예요 (graph.py:465-466).
- 조회 메서드는 복사본을 돌려줘요. 예: `get_product`는 딕셔너리와 재고 딕셔너리를 둘 다 복사해요 (graph.py:884-885).
- `rebuild()`는 `_next_ids`를 건드리지 않아요. 그래서 지운 ID를 다시 쓰지 않아요 (graph.py:1098, 계획서 B.1 ID 발급).

## 3. 따라가기

### 3.1 구매 1건 등록 ([1] CREATE → [3] 구매 등록)

| 순서 | 일어나는 일 | 근거 |
|---|---|---|
| 1 | 메뉴에서 "1"을 고르면 `_choose_action`이 CREATE 하위 메뉴를 보여 주고, "3"을 고르면 `_create_purchase`를 돌려줘요 | main.py:93, 97, 106; 하위 메뉴 표 main.py:830 _SUBMENUS |
| 2 | 고객 ID·상품 ID·구매일은 앞뒤 공백을 지우고, 색상은 그대로, 수량은 `_to_int`로 정수로 바꿔요 | main.py:442-446, main.py:141 _to_int |
| 3 | `g.add_purchase(...)`를 불러요 | main.py:447 |
| 4 | graph.py에서 고객·상품이 있는지, 색상이 그 상품 색상 목록에 있는지, 수량(1~99)·날짜 형식을 먼저 모두 검사해요 | graph.py:791-798 (_lookup, _clean_purchase_color, _check_int, _check_date) |
| 5 | 검사를 다 통과한 뒤에야 ID를 정하고(`_next_id("T")`), 원본에 넣고, 카운터를 1 올리고, 그래프를 다시 만들어요 | graph.py:799-803 |
| 6 | main.py가 방금 넣은 기록을 표 행으로 읽고, 그 쌍의 가중치(`g.weight`)와 함께 "[등록] …" 한 줄을 출력해요 | main.py:448-450 |
| 7 | 검사에서 하나라도 틀리면 ValueError가 나고, `_menu_loop`가 "[오류] 메시지"를 출력해요. 이때 원본·그래프·카운터는 그대로예요 | main.py:101-103, graph.py:791-799 순서 |

### 3.2 구매 1건 삭제 ([4] DELETE → [3] 구매 삭제)

| 순서 | 일어나는 일 | 근거 |
|---|---|---|
| 1 | 구매 ID를 받아 앞뒤 공백을 지워요 | main.py:742 |
| 2 | 지우기 전에 그 기록을 표 행으로 읽어 둬요 (고객·상품·색상을 나중에 출력하려고). 없는 ID면 여기서 ValueError | main.py:743, main.py:343 _purchase_row |
| 3 | `g.delete_purchase(purchase_id)`: 원본에서 지우고 그래프를 다시 만들어요 | main.py:744, graph.py:854-856 |
| 4 | 재구축 때 그 쌍의 남은 기록으로 간선 집계를 새로 만들어요. 남은 기록이 없으면 그 쌍의 간선 자체가 생기지 않아요 | graph.py:1246-1249, graph.py:445 _aggregate_edges |
| 5 | "[삭제] …" 줄에 남은 가중치를 보여 줘요 | main.py:745 |

- 구매 삭제는 확인을 묻지 않아요. 고객·상품 삭제만 확인을 물어요 (계획서 5.3.1, 263~265줄; main.py:283 _confirm_delete).
- 6장 예: T004 삭제 뒤 (C01, P01) 간선은 남고 최근 구매일이 바뀌어요 (계획서 6.4, tests/test_graph.py TestW5Purchase.test_delete_t004).

### 3.3 고객 성별·나이 수정 ([3] UPDATE → [1] 고객 수정)

| 순서 | 일어나는 일 | 근거 |
|---|---|---|
| 1 | 고객 ID를 받고, 지금 값을 표로 보여 줘요 (없는 ID면 여기서 ValueError) | main.py:626-627 |
| 2 | 이름·성별·나이를 차례로 받아요. 빈 입력은 None(= 그대로)이 돼요 | main.py:628-630, main.py:232 _optional |
| 3 | `g.update_customer(customer_id, name=…, gender=…, age=…)` | main.py:631 |
| 4 | graph.py는 원본의 복사본(`updated`)에 바꿀 값을 하나씩 검사하며 넣어요. 바꿀 항목이 하나도 없으면 "바꿀 항목이 없습니다" | graph.py:628-637 |
| 5 | 모든 검사를 통과한 뒤에만 원본을 `updated`로 바꾸고 재구축해요 | graph.py:638-639 |
| 6 | 재구축이 성별·나이로 그룹을 다시 찾아 연결해요. 그래서 그룹 이동 코드를 따로 두지 않아요 | graph.py:1243-1245, graph.py:425 _group_id_for |
| 7 | main.py가 수정 뒤 그룹을 "[수정] 이름(ID) → 그룹 표시 이름 그룹"으로 보여 줘요 | main.py:632-633 |

- 6장 예: C04 나이를 31로 바꾸면 G-M-20에서 G-M-30으로 옮겨요 (계획서 6.4, tests/test_flow.py TestW10Menu.test_update_customer_moves_group).

### 3.4 추천 1번 ([6] RECOMMEND)

| 순서 | 일어나는 일 | 근거 |
|---|---|---|
| 1 | 고객 ID와 K를 받아요. K가 빈 입력이면 K_DEFAULT(3) | main.py:823-825, graph.py:65 |
| 2 | `recommend(g, customer_id, k)`를 부르고, 그 결과와 k를 `print_recommendation`에 넘겨요 | main.py:826 |
| 3 | search.py `recommend`: 고객이 있는지, K가 1~10 정수인지 검사해요 | search.py:401-402 |
| 4 | 이미 산 상품 = 고객의 이웃 중 그룹이 아닌 것. 이것을 `chosen`에 넣고 시작해요 | search.py:403-405 |
| 5 | 범위 3개를 좁은 것부터 돌아요: 같은 그룹 → 같은 성별 그룹 4개 → 그룹 8개 | search.py:406, search.py:295 _scopes |
| 6 | 범위마다 그 그룹들의 소속 고객을 모으고(대상 고객은 뺌) | search.py:407, search.py:316 _peers |
| 7 | 동료 → 동료의 이웃 상품을 따라가며 점수(min(가중치, 3))와 지지자를 모아요 | search.py:81-89 _collect_scores |
| 8 | 이미 고른 상품·이미 산 상품·전부 품절인 상품을 빼고, 점수↓ → 구매자 수↓ → 상품 ID↑로 정렬해요 | search.py:357-368, search.py:92 _rank_key |
| 9 | K개가 찰 때까지 앞에서부터 담고, 찼으면 더 넓히지 않아요 | search.py:408-414 |
| 10 | view.py `print_recommendation`: 머리 줄 → 항목마다 3줄(상품·근거·구매 가능 색상) → 안내 줄 | view.py:147-165, view.py:184 _print_item |
| 11 | 넓힘 안내는 k로 판정해요: 결과 수 < k면 전체 고객까지, 결과 수 == k면 마지막 항목의 범위까지 넓힌 것으로 봐요 | view.py:158-160, view.py:220 _widen_note |
| 12 | 결과 수 < k면 개수 부족 안내, 범위가 2개 이상 섞였으면 점수 비교 안내를 덧붙여요 | view.py:161-165 |

- 추천은 구매 기록 전체를 훑지 않고 그룹 → 소속 고객 → 이웃 상품으로 따라가요 (계획서 5.3.2 "그래프 활용 원칙", search.py:82-83).

## 4. 추천 규칙을 6장 C07 사례로 한 단계씩

6장 6.3-1번(계획서 560~562줄): 신규 고객 C07(여, 22) 등록 → 추천(K=3).

| 단계 | 내용 | 근거 |
|---|---|---|
| 1 | C07은 여·22세라 G-F-20에 연결돼요 | 계획서 560줄, graph.py:425 _group_id_for |
| 2 | 이미 산 상품: 없음 (신규 고객) | search.py:403 |
| 3 | 같은 그룹 범위의 동료: G-F-20 소속 C01, C02, C03 (C07 자신은 뺌) | 계획서 507~509줄(6.1 고객표), search.py:316 _peers |
| 4 | 동료의 구매 가중치(6.2 간선 집계): (C01,P01) 4, (C01,P02) 1, (C02,P02) 2, (C02,P03) 1, (C03,P03) 1, (C03,P05) 1 | 계획서 545줄 |
| 5 | 점수 = 상품마다 min(가중치, 3)의 합. P02 = 1 + 2 = 3 (지지자 C01·C02), P01 = min(4, 3) = 3 (지지자 C01), P03 = 1 + 1 = 2 (지지자 C02·C03), P05 = 1 (지지자 C03) | 계획서 550줄 S4(G-F-20)와 같은 계산, search.py:87 |
| 6 | P05는 전부 품절이라 빠져요 | 계획서 562줄, search.py:358 |
| 7 | 정렬: P02(3점, 2명) → P01(3점, 1명) → P03(2점). P02와 P01은 점수가 같아 구매자 수로 갈려요 | 계획서 550~552줄, search.py:92 _rank_key |
| 8 | 같은 그룹에서 3개가 차서 넓히지 않아요. 결과: P02, P01, P03 모두 [같은 그룹] | 계획서 561줄, search.py:409-414 |
| 9 | 구매 가능 색상: P03은 네이비 재고가 0이라 아이보리만 보여요 | 계획서 562줄, graph.py:1081 available_colors |

- P01은 가중치가 4지만 상한 3 때문에 3점이에요. 상한이 없으면 P01이 1위가 돼요 (계획서 551줄).
- 같은 C07에 K=4를 주면 같은 그룹 후보가 3개뿐이라 범위를 넓혀요. 6.3-2번(계획서 563~565줄)에 결과가 있어요.

## 5. 무결성 검사가 잡는 것과 못 잡는 것

`check_integrity()`(graph.py:1100)는 세 부분으로 나뉘어요 (graph.py:1123-1129).

| 부분 | 보는 것 | 근거 |
|---|---|---|
| `_integrity_refs` | 구매 기록이 없는 고객·상품을 가리키는지, 구매 색상이 상품 색상 목록에 있는지 | graph.py:1252, 1270·1274·1277줄의 위반 문구 |
| `_integrity_structure` | 노드 집합이 그룹+고객+상품과 같은지, 인접 리스트가 양쪽에 다 있는지, 구매 간선이 양쪽에 있는지, 고객마다 맞는 그룹 하나에 소속돼 있는지 | graph.py:1280, 1297·1301·1304·1310줄 |
| `_integrity_against_rebuild` | 원본에서 임시로 다시 만든 그래프와 지금 그래프가 같은지 (간선 집계·인접 리스트) | graph.py:1313, 1328~1342줄 |

- 검사는 상태를 바꾸지 않아요. 재구축 비교는 임시 결과로 하고 `rebuild()`를 부르지 않아요 (graph.py:1103-1104, 계획서 5.3.5 "검사는 상태를 바꾸지 않는다").
- 검사기가 정말 일하는지는 일부러 망가뜨려서 확인해요: 고장 주입 4종 + 없는 고객을 가리키는 구매 기록 (tests/test_graph.py TestW5Integrity, 계획서 376~379줄).

못 잡는 것 (계획서 385줄 "이 검사가 보장하지 않는 것")

- 재구축과 검사가 같은 구축 코드(`_build_graph`)를 써요. 그래서 그 코드에 버그가 있으면 양쪽에 똑같이 들어가 "일치"로 나와요 (graph.py:1110-1111 docstring). 집계가 맞는지는 6장 손계산 기대값 테스트가 봐요.
- 원본과 그래프가 맞아도 추천 정렬·범위 순서는 틀릴 수 있어요. 그건 6.3 기대값 테스트가 봐요.
- 발표 표현은 "원본과 그래프가 일치함을 확인"이에요. "정확성 증명"이라고 하지 않아요 (계획서 7장 8번, 5.3.5).

## 6. 테스트 파일 구성

| 파일 | 클래스 | 지키는 단계·내용 | 근거 |
|---|---|---|---|
| tests/test_graph.py | TestW3Build | W3 생성자 계약·rebuild·조회 | tests/test_graph.py:37 |
| | TestW4CustomerProduct | W4 고객·상품 등록·수정·삭제, 그룹 이동 | tests/test_graph.py:232 |
| | TestW5Purchase | W5 구매 등록·수정·삭제 | tests/test_graph.py:486 |
| | TestW5Integrity | W5 무결성 검사와 고장 주입 | tests/test_graph.py:626 |
| tests/test_search.py | TestW6Query | W6 조건 조회, S1~S3 | tests/test_search.py:14 |
| | TestW7Popular | W7 S4 그룹 인기 상품 | tests/test_search.py:122 |
| tests/test_recommend.py | TestW8Recommend | W8 추천 (6.3 전체) | tests/test_recommend.py:89 |
| tests/test_flow.py | TestW8bFlow | W8b 추천 화면 | tests/test_flow.py:149 |
| | TestW10Menu | W10 전체 메뉴, 잘못된 입력, EOF·Ctrl+C | tests/test_flow.py:435 |
| | TestW10aMessages | W10a 오류 메시지 형식 | tests/test_flow.py:679 |
| tests/test_view.py | TestW9Table, TestW9GroupTree, TestW9Neighbors | W9 표·그룹 트리·인접 리스트 | tests/test_view.py:59, 120, 190 |
| tests/test_demo.py | TestW12Demo | W12 시연 장면 1~8 (기대값 승인 전이라 지금은 NotImplementedError) | tests/test_demo.py:206 |

- 고정 데이터는 tests/fixtures.py가 테스트마다 새로 만들어요. 실행용 data.py를 읽는 테스트는 test_demo뿐이에요 (CLAUDE.md "테스트" 절, tests/test_demo.py 모듈 설명).
- 실패 입력 테스트는 `snapshot(g)`로 내부 상태 전체를 전후 비교해요 (tests/helpers.py, CLAUDE.md "테스트" 절).
- 6장 항목과 테스트 이름의 대응표는 docs/test_map.md에 있어요.
