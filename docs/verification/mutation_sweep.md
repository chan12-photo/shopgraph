# 확장 고장 검사 (2026-11-02, 2회차 야간 작업 2)

- 대상: w12-prep 2ccefa7의 graph.py·search.py·view.py·main.py
- 방법: 저장소 안 임시 worktree(.wt_mut, detached)에서 변형마다 파일 하나의 한 곳만 바꾸고 `python3 -m unittest` 전체를 돌린 뒤 원래대로 되돌렸다. 끝나고 worktree를 지웠다 (`git worktree list`에 원래 체크아웃만 남음). 실행 스크립트는 파일로 쓰지 않고 표준 입력으로 넘겼다
- 판정: 미도래 8개(tests/test_demo.py, NotImplementedError — 기대값을 먼저 읽고 멈추므로 코드 변형과 무관)를 뺀 실패·오류가 1개 이상이면 "잡힘"
- tests/는 바꾸지 않았다. 못 잡은 변형 중 테스트 공백은 mutation_proposals.md에 초안만 적었다

## 요약

| 항목 | 수 |
|---|---|
| 변형 | 52 (graph 22, search 15, view 6, main 9) |
| 잡힘 | 49 |
| 못 잡음 | 3 |
| └ 동작이 같은 변형 | 1 (S06) |
| └ 테스트 공백 | 2 (M04, M05) |

## 못 잡은 변형과 원인

| 번호 | 변형 | 원인 | 근거 |
|---|---|---|---|
| S06 | search.py `_peers`에서 `peer_ids.discard(customer_id)`를 빼 대상 고객을 동료에 넣음 | **동작이 같은 변형.** 대상 고객이 동료에 들어가도 그 고객이 점수를 주는 상품은 대상이 이미 산 상품뿐이고, 이미 산 상품은 `chosen = set(bought)`(search.py:405)로 후보에서 빠진다(search.py:358). 다른 상품의 점수·지지자는 바뀌지 않는다 | W8 커밋 6cb44e0 본문 "대상을 동료에서 빼지 않음 → 출력 동치(무작위 83,180건 차이 0, 독립 검토자 논증 확인)" |
| M04 | main.py `_to_int`의 자릿수 제한을 9 → 10자리로 (`len(digits) > _MAX_DIGITS + 1`) | **테스트 공백.** 10자리 입력 "1234567890"은 test_invalid_create_inputs(tests/test_flow.py:526)에 있지만 그 테스트는 오류 줄 수만 센다. 변형에서는 graph.py 범위 검사가 대신 거절해 오류 줄 수가 같다. 문구("숫자가 너무 깁니다")를 보는 test_input_error_messages(tests/test_flow.py:504)는 4301자리만 넣는다 | 초안 P1 |
| M05 | main.py `_delete_customer`에서 고객 ID 입력의 `.strip()`을 뺌 (main.py:700 부근) | **테스트 공백.** 메뉴 테스트 중 앞뒤 공백 ID를 넣는 것은 구매 등록(test_purchase_register_weight)과 추천(test_recommend_menu)뿐이고, 삭제 메뉴에는 없다. W10 승인 형식 12번 "ID 입력은 앞뒤 공백을 main.py가 지움" | 초안 P2 |

## 전체 결과

| 번호 | 파일 | 변형 | 결과 | 잡은 테스트 (일부) |
|---|---|---|---|---|
| G01 | graph.py | 날짜 형식(①) 검사 빼기 | 잡힘 (3) | test_ctor_bad_id_and_date_format, test_invalid_create_inputs, test_invalid_purchases_then_t014 |
| G02 | graph.py | 정수 검사에서 bool 허용 | 잡힘 (2) | test_invalid_product_values, test_invalid_purchase_other |
| G03 | graph.py | 정수 상한 경계 하나 차이 (> → >=) | 잡힘 (2) | test_boundary_values_accepted, test_qty_99_accepted |
| G04 | graph.py | 정수 하한 경계 하나 차이 (< → <=) | 잡힘 (119) | test_age_move 외 |
| G05 | graph.py | 이름 길이 상한 경계 (<= → <) | 잡힘 (1) | test_boundary_values_accepted |
| G06 | graph.py | 총수량에 수량 대신 1 더하기 | 잡힘 (2) | test_qty_99_accepted, test_update_t005_qty |
| G07 | graph.py | 최근 구매일을 max 대신 min | 잡힘 (9) | test_delete_t004, test_add_t014_then_delete_t006 외 |
| G08 | graph.py | 고객 등록 뒤 ID 카운터를 늘리지 않음 | 잡힘 (3) | test_issue_ids_no_reuse 외 |
| G09 | graph.py | 고객 등록 뒤 재구축 빼기 | 잡힘 (23) | test_c07_k3 외 |
| G10 | graph.py | 구매 수정 뒤 재구축 빼기 | 잡힘 (4) | test_update_t002_color, test_update_t005_qty 외 |
| G11 | graph.py | get_customer가 복사본 대신 원본 반환 | 잡힘 (1) | test_copies_out |
| G12 | graph.py | get_product가 재고 딕셔너리를 공유 | 잡힘 (1) | test_copies_out |
| G13 | graph.py | is_sold_out을 all 대신 any | 잡힘 (17) | test_c07_k3 외 |
| G14 | graph.py | 구매 가능 색상에 재고 0 포함 | 잡힘 (14) | test_c07_k3 외 |
| G15 | graph.py | ID 한도 경계 하나 차이 (>= → >) | 잡힘 (1) | test_id_limit |
| G16 | graph.py | 구매 기록이 있는 색상 삭제 거절 빼기 | 잡힘 (2) | test_stock_reject_delete_and_dup, test_invalid_update_delete_inputs |
| G17 | graph.py | 검사기가 검사 중 rebuild로 상태를 고침 | 잡힘 (4) | 고장 주입 4종 |
| G18 | graph.py | 검사기가 간선 집계 비교를 건너뜀 | 잡힘 (1) | test_fault_edge_color |
| G19 | graph.py | 가중치를 색상 수 대신 기록 수로 | 잡힘 (2) | test_add_t014_same_color, test_update_t002_color |
| G20 | graph.py | 오류 형식을 콜론 두 번으로 | 잡힘 (2) | test_age_error_screen, test_graph_and_search_same_format |
| G21 | graph.py | 생성자 ID 카운터를 최대 + 2로 | 잡힘 (32) | test_issue_ids_no_reuse 외 |
| G22 | graph.py | 이름 조회를 부분 일치로 | 잡힘 (2) | test_find_by_name, test_read_screens |
| S01 | search.py | 점수 상한 3 빼기 | 잡힘 (18) | test_c07_k3, test_s4_g_f_20 외 |
| S02 | search.py | 정렬 키에서 구매자 수 빼기 | 잡힘 (13) | test_c07_k3 외 |
| S03 | search.py | 정렬 키 구매자 수 오름차순 | 잡힘 (13) | test_c07_k3 외 |
| S04 | search.py | 범위 넓히기 순서 바꾸기 (gender 먼저) | 잡힘 (15) | test_c02_k3 외 |
| S05 | search.py | 같은 성별 범위 건너뛰기 | 잡힘 (5) | test_c06_k3, test_gender_scope_screen 외 |
| S06 | search.py | 대상 고객을 동료에서 빼지 않음 | **못 잡음** (동작이 같음) | - |
| S07 | search.py | 추천에서 품절 제외 빼기 | 잡힘 (16) | test_c02_k3 외 |
| S08 | search.py | 추천에서 이미 산 상품 제외 빼기 | 잡힘 (3) | test_c02_k3, test_c02_screen, test_recommend_menu |
| S09 | search.py | 한 범위 안에서 K+1개까지 담기 | 잡힘 (4) | test_c06_k3, test_k_min_accepted 외 |
| S10 | search.py | S4 품절 표시 뒤집기 | 잡힘 (5) | test_s4_g_f_20 외 |
| S11 | search.py | 조건 조회 최저 가격 경계 (>= → >) | 잡힘 (1) | test_find_products_more_conditions |
| S12 | search.py | 가격 범위 거꾸로 허용 | 잡힘 (2) | test_find_products_reversed_range, test_invalid_read_inputs |
| S13 | search.py | 색상 조건을 재고 있는 색으로 | 잡힘 (3) | test_find_products_conditions 외 |
| S14 | search.py | 오류 형식을 콜론 두 번으로 | 잡힘 (3) | test_graph_and_search_same_format 외 |
| S15 | search.py | S4 개수 항목 이름을 k로 | 잡힘 (1) | test_s4_count_error_screen |
| V01 | view.py | 넓힘 판정에서 결과 수 < k 무시 | 잡힘 (1) | test_widened_without_new_items_screen |
| V02 | view.py | 점수 비교 안내를 범위 1개여도 출력 | 잡힘 (5) | test_c07_screen 외 |
| V03 | view.py | 조사 규칙에서 0을 받침 없음으로 | 잡힘 (1) | test_particle_boundaries |
| V04 | view.py | 표 폭에서 한글을 1칸으로 | 잡힘 (5) | test_korean_width_alignment 외 |
| V05 | view.py | 넓힘 이유를 항상 "K개가 안 돼"로 | 잡힘 (3) | test_c06_screen_example 외 |
| V06 | view.py | 개수 부족 안내 빼기 | 잡힘 (4) | test_c02_screen 외 |
| M01 | main.py | 삭제 확인 무시 | 잡힘 (1) | test_delete_cancel |
| M02 | main.py | ValueError를 메시지로 바꾸지 않음 | 잡힘 (7) | test_invalid_create_inputs 외 |
| M03 | main.py | 추천 K 기본값을 K_MAX로 | 잡힘 (1) | test_recommend_menu |
| M04 | main.py | 숫자 자릿수 제한 경계 (9 → 10) | **못 잡음** (테스트 공백) | - |
| M05 | main.py | 고객 삭제 ID 공백을 안 지움 | **못 잡음** (테스트 공백) | - |
| M06 | main.py | 삭제 확인 0건 문구 빼기 | 잡힘 (1) | test_delete_cancel |
| M07 | main.py | EOF를 받지 않음 | 잡힘 (1) | test_eof_and_ctrl_c |
| M08 | main.py | 전체 인접 리스트에서 상품 빠짐 | 잡힘 (1) | test_print_screens |
| M09 | main.py | 번호 고르기에서 0 허용 | 잡힘 (2) | test_input_error_messages, test_invalid_read_inputs |

괄호 안 숫자 = 미도래 8개를 뺀 실패·오류 수.

## 한계

- 변형은 사람이 고른 52곳이다. 모든 줄을 바꾼 것이 아니므로 "52종 중 49종"은 테스트가 완전하다는 뜻이 아니다 (계획서 11.3.3 G2 "임의의 코드 한 줄을 바꿨는데 통과했다는 사실만으로 테스트가 무의미하다고 단정하지 않는다"의 반대 방향도 같다)
- tests/test_demo.py는 기대값 승인 전이라 어떤 변형도 잡지 못하는 상태다 (모든 변형에서 8개가 같은 NotImplementedError)
