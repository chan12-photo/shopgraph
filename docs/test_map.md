# 6장 ↔ 테스트 대응표 (계획서 부록 B.5 양식)

W0에서 이 양식을 `docs/test_map.md`로 복사하고, W2에서 테스트 이름 칸을 채운다 (계획서 본문은 AI가 고치지 않기 위해 분리). 한 테스트가 여러 항목을 맡아도 되고, 한 항목을 여러 테스트로 나눠도 된다. **각 항목은 여기 배정된 단계에서 통과해야 한다** (6.5). 배정 원칙: 그 항목이 부르는 함수 중 가장 늦게 구현되는 함수의 단계.

**W2 게이트에서 확인하는 것** (새 절차가 아니라 W2 기대값 승인의 내용): ① W2 대상 행(화면·흐름 행 제외)의 테스트 이름 칸이 모두 채워짐 ② 승인 담당자가 각 행 테스트의 **확인문(assert)이 그 규칙을 실제로 검사하는지** 읽음. 테스트 이름에 "검증"이 들어 있는 것과 그 검증을 수행하는 것은 다르다 ③ 이 표는 6장 중심이다. B.3·B.4의 규칙 중 표에 행이 없는 것은 G2·G5의 경계 상황 점검에서 테스트를 추가하고, 추가한 테스트 이름을 아래 "기타" 행에 적는다

| 6장 항목 | 단계 | 테스트 파일 · 클래스 | 테스트 이름 |
|---|---|---|---|
| 6.2 노드·간선·기록 개수 | W3 | test_graph · TestW3Build | test_initial_counts, test_initial_groups |
| 6.2 간선 집계 9개, edge() 형식 | W3 | test_graph · TestW3Build | test_edge_aggregates |
| 6.2 이름 조회(공백 제거, 완전 일치) | W3 | test_graph · TestW3Build | test_find_by_name |
| 6.4 초기 레코드 ID·구매일 형식 오류 (생성자) | W3 | test_graph · TestW3Build | test_ctor_bad_id_and_date_format |
| B.2 없는 ID의 edge()·weight() 오류 vs 간선 없음 None·0 | W3 | test_graph · TestW3Build | test_edge_weight_missing_vs_none |
| 6.4 나가는 쪽 복사본 3종 (직접 재조회) | W3 | test_graph · TestW3Build | test_copies_out |
| 6.4 들어오는 쪽: 생성자 입력 복사 | W3 | test_graph · TestW3Build | test_ctor_input_copied |
| 6.4 생성자 검증 (중복 ID, 없는 참조) | W3 | test_graph · TestW3Build | test_ctor_duplicate_and_missing_ref |
| 6.4 ID 발급 C07, 삭제·rebuild 후 C08, 실패한 고객 등록 뒤 C07 | W4 | test_graph · TestW4CustomerProduct | test_issue_ids_no_reuse, test_failed_add_keeps_counter |
| 6.4 C04 나이 수정 → 그룹 이동 (`g.members`로 확인) | W4 | test_graph · TestW4CustomerProduct | test_age_move |
| 6.4 성별 변경 → 그룹 이동 (C01 → G-M-20) | W4 | test_graph · TestW4CustomerProduct | test_gender_move |
| 6.4 동명이인 (고객1 → [C01, C07]) | W4 | test_graph · TestW4CustomerProduct | test_same_name |
| 6.4 ID 한도 (C99 다음 등록 거부, snapshot 동일) | W4 | test_graph · TestW4CustomerProduct | test_id_limit |
| 6.4 C02 삭제 연쇄 (`g.members`로 확인) | W4 | test_graph · TestW4CustomerProduct | test_delete_customer_cascade |
| 6.4 P01 삭제 연쇄 | W4 | test_graph · TestW4CustomerProduct | test_delete_product_cascade |
| 6.4 P04 재고 교체(색상 추가) / P01 색상 삭제 거절 / 겹치는 색상명 거절 | W4 | test_graph · TestW4CustomerProduct | test_stock_replace_add_color, test_stock_reject_delete_and_dup |
| 6.4 들어오는 쪽: add_product·update_product의 stock 복사 | W4 | test_graph · TestW4CustomerProduct | test_stock_input_copied |
| 6.4 bool 나이, 바꿀 항목 없는 수정, 섞은 수정(고객·상품) — 원본 전체 비교 | W4 | test_graph · TestW4CustomerProduct | test_failed_add_keeps_counter, test_invalid_customer_mixed, test_invalid_product_mixed |
| 6.4 T004 삭제 / T005 삭제 / T014 추가 / T014 추가 후 T006 삭제 / T005 수량 수정 / T002 색상 수정 | W5 | test_graph · TestW5Purchase | test_delete_t004, test_delete_t005_last_record, test_add_t014_same_color, test_add_t014_then_delete_t006, test_update_t005_qty, test_update_t002_color |
| 6.4 잘못된 구매 입력 7종 — 원본 전체 비교, 실패 뒤 T014 발급 | W5 | test_graph · TestW5Purchase | test_invalid_purchases_then_t014 |
| 6.4 고장 주입 4종 (위반 보고, 재호출, 상태 불변) | W5 | test_graph · TestW5Integrity | test_fault_reverse_adj, test_fault_edge_color, test_fault_wrong_group, test_fault_orphan_edge |
| 6.4 W3·W4·W5 변경 테스트의 무결성 확인 추가 | W5 | test_graph · 전 클래스 | W5 단계에서 TestW3Build·TestW4CustomerProduct의 변경 테스트에 추가 예정 (W2 테스트는 W3·W4 테스트에서 check_integrity를 부르지 않음). TestW5Purchase는 W2부터 포함 |
| 6.2 조건 조회(색상·종류·가격), 6.4 가격 범위 거꾸로 | W6 | test_search · TestW6Query | test_find_products_conditions, test_find_products_reversed_range |
| 6.2 S1(C01), S2(P05), S3(G-F-20·G-F-30·G-F-10), S3 이동 후 G-M-20 | W6 | test_search · TestW6Query | test_s1_products_of_c01, test_s2_customers_of_p05, test_s3_members_of, test_s3_after_age_move |
| 6.2 S4(G-F-20), k=2 / 6.4 S4의 잘못된 k (0, 11, True) | W7 | test_search · TestW7Popular | test_s4_g_f_20, test_s4_k2, test_s4_invalid_k |
| 6.3-1 C07, K=3 (범위·점수·구매자 수·지지자·구매 가능 색상) | W8 | test_recommend · TestW8Recommend | test_c07_k3 |
| 6.3-2 C07, K=4 | W8 | test_recommend · TestW8Recommend | test_c07_k4 |
| 6.3-3 C02, K=3 (2개만) | W8 | test_recommend · TestW8Recommend | test_c02_k3 |
| 6.3-4 C06, K=3 (buyers = len(supporters) 포함) | W8 | test_recommend · TestW8Recommend | test_c06_k3 |
| 6.3-5 K 검증 | W8 | test_recommend · TestW8Recommend | test_invalid_k |
| 6.3-6 같은 성별 여러 연령대 합산 (C05–P04) | W8 | test_recommend · TestW8Recommend | test_gender_union |
| 6.3-7 추천 결과 0개 | W8 | test_recommend · TestW8Recommend | test_zero_results |
| 6.4 P02 품절 후 C07 추천 | W8 | test_recommend · TestW8Recommend | test_p02_sold_out |
| 6.3-7 빈 결과 화면 안내 / 6.3-1 화면 출력 (고정 데이터 사용, W8b에서 작성) | W8b | test_flow | |
| 7장 시연 장면 1~8 (docs/demo_expected.md 기대값, 실행용 data.py 사용) | W12 | test_demo | |
| 기타: B.3·B.4 중 위에 행이 없는 규칙의 추가 테스트 | 해당 단계 | 해당 파일 | W3 TestW3Build: test_neighbors_sorted, test_ctor_bad_shape, test_ctor_strips_spaces, test_missing_ids, test_rebuild_idempotent, test_ctor_none_empty, test_ctor_date_not_real / W4 TestW4CustomerProduct: test_invalid_customer_values, test_invalid_product_values, test_strip_on_register, test_sold_out_available_colors, test_boundary_values_accepted, test_delete_unpurchased_color, test_failed_add_product_keeps_counter / W5 TestW5Purchase: test_invalid_purchase_other, test_purchase_color_strip, test_purchase_zero_stock_color_allowed, test_qty_99_accepted / W5 TestW5Integrity: test_clean_state / W6 TestW6Query: test_find_products_invalid_values, test_missing_ids_search / W7 TestW7Popular: test_s4_empty_group / W8 TestW8Recommend: test_k_max_accepted, test_k_min_accepted |
