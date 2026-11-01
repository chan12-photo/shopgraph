# 고장 검사 실행 결과 (기준 커밋 5538a39, 2026-11-02)

명령 (저장소 루트):

    python3 docs/verification/mutations/run_mutations.py HEAD

아래는 실행 출력 그대로다 (종료 코드 0).

기준 커밋 5538a39, 명령: python3 -B -m unittest tests.test_graph tests.test_search tests.test_recommend tests.test_view tests.test_flow
기준 상태: OK []
| 번호 | 파일 | 변형 | 결과 | 요약 | 실패·오류 테스트 |
|---|---|---|---|---|---|
| C01 | graph.py | get_purchase가 복사본 대신 원본 반환 (Codex) | 잡힘 | FAILED (failures=1) | test_get_purchase_copy |
| C02 | graph.py | customer_ids가 정렬 대신 입력 순서 (Codex) | 잡힘 | FAILED (failures=1) | test_ids_sorted_regardless_of_input_order |
| C03 | graph.py | product_ids가 정렬 대신 입력 순서 (Codex) | 잡힘 | FAILED (failures=1) | test_ids_sorted_regardless_of_input_order |
| C04 | graph.py | 10대 그룹 상한 19 → 20 (Codex) | 잡힘 | FAILED (failures=1) | test_age_band_boundaries |
| G01 | graph.py | 날짜 형식(①) 검사 빼기 | 잡힘 | FAILED (failures=3) | test_ctor_bad_id_and_date_format, test_invalid_create_inputs, test_invalid_purchases_then_t014 |
| G02 | graph.py | 정수 검사에서 bool 허용 | 잡힘 | FAILED (failures=2) | test_invalid_product_values, test_invalid_purchase_other |
| G03 | graph.py | 정수 상한 경계 하나 차이 (> → >=) | 잡힘 | FAILED (errors=2) | test_boundary_values_accepted, test_qty_99_accepted |
| G04 | graph.py | 정수 하한 경계 하나 차이 (< → <=) | 잡힘 | FAILED (errors=126) | test_add_t014_same_color, test_add_t014_then_delete_t006, test_age_band_boundaries, test_age_error_screen, test_age_move, test_all_scope_only_screen, test_boundary_values_accepted, test_c02_k3, test_c02_screen, test_c06_k2_screen, test_c06_k3, test_c06_screen_example, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_clean_state, test_copies_out, test_ctor_input_copied, test_ctor_strips_spaces, test_customer_node, test_customer_without_purchase, test_delete_cancel, test_delete_cascade_neighbors, test_delete_customer_cascade, test_delete_customer_confirm, test_delete_id_spaces, test_delete_product_cascade, test_delete_product_confirm, test_delete_purchase, test_delete_purchase_id_spaces, test_delete_t004, test_delete_t005_last_record, test_delete_unpurchased_color, test_digit_limit_boundary, test_edge_aggregates, test_edge_weight_missing_vs_none, test_eof_and_ctrl_c, test_failed_add_keeps_counter, test_failed_add_product_keeps_counter, test_fault_dangling_purchase, test_fault_edge_color, test_fault_orphan_edge, test_fault_reverse_adj, test_fault_wrong_group, test_find_by_name, test_find_products_conditions, test_find_products_invalid_values, test_find_products_more_conditions, test_find_products_reversed_range, test_fixture_tree, test_full_menu_and_exit, test_gender_move, test_gender_scope_screen, test_gender_union, test_get_purchase_copy, test_graph_and_search_same_format, test_group_node, test_id_limit, test_ids_sorted_regardless_of_input_order, test_initial_counts, test_initial_groups, test_input_error_messages, test_invalid_create_inputs, test_invalid_customer_mixed, test_invalid_customer_values, test_invalid_k, test_invalid_menu_numbers, test_invalid_product_mixed, test_invalid_product_values, test_invalid_purchase_other, test_invalid_purchases_then_t014, test_invalid_read_inputs, test_invalid_update_delete_inputs, test_issue_ids_no_reuse, test_k_max_accepted, test_k_min_accepted, test_missing_ids, test_missing_ids_search, test_neighbors_sorted, test_p02_sold_out, test_p02_sold_out_screen, test_particle_boundaries, test_print_keeps_state, test_print_screens, test_product_node, test_purchase_color_strip, test_purchase_register_weight, test_purchase_zero_stock_color_allowed, test_qty_99_accepted, test_read_screens, test_rebuild_idempotent, test_recommend_k_error_screen, test_recommend_k_not_number, test_recommend_menu, test_register_then_recommend, test_s1_no_purchases, test_s1_products_of_c01, test_s2_customers_of_p05, test_s3_after_age_move, test_s3_members_of, test_s4_cap_per_customer, test_s4_count_error_screen, test_s4_empty_group, test_s4_g_f_20, test_s4_id_tiebreak, test_s4_invalid_k, test_s4_k2, test_same_name, test_sold_out_available_colors, test_stock_input_copied, test_stock_reject_delete_and_dup, test_stock_replace_add_color, test_strip_on_register, test_submenu_screen_and_back, test_tree_follows_changes, test_unknown_customer, test_unknown_node, test_update_customer_moves_group, test_update_product_fields, test_update_product_stock, test_update_t002_color, test_update_t005_qty, test_widened_without_new_items_screen, test_zero_results, test_zero_screen |
| G05 | graph.py | 이름 길이 상한 경계 (<= → <) | 잡힘 | FAILED (errors=1) | test_boundary_values_accepted |
| G06 | graph.py | 총수량에 수량 대신 1 더하기 | 잡힘 | FAILED (failures=2) | test_qty_99_accepted, test_update_t005_qty |
| G07 | graph.py | 최근 구매일을 max 대신 min | 잡힘 | FAILED (failures=10) | test_add_t014_same_color, test_add_t014_then_delete_t006, test_delete_purchase, test_delete_purchase_id_spaces, test_delete_t004, test_edge_aggregates, test_purchase_color_strip, test_read_screens, test_s1_products_of_c01, test_update_t002_color |
| G08 | graph.py | 고객 등록 뒤 ID 카운터를 늘리지 않음 | 잡힘 | FAILED (failures=3) | test_boundary_values_accepted, test_issue_ids_no_reuse, test_particle_boundaries |
| G09 | graph.py | 고객 등록 뒤 재구축 빼기 | 잡힘 | FAILED (failures=12, errors=12) | test_age_band_boundaries, test_all_scope_only_screen, test_boundary_values_accepted, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_customer_without_purchase, test_failed_add_keeps_counter, test_gender_scope_screen, test_gender_union, test_invalid_k, test_issue_ids_no_reuse, test_k_max_accepted, test_k_min_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_print_keeps_state, test_purchase_register_weight, test_register_then_recommend, test_same_name, test_widened_without_new_items_screen, test_zero_results, test_zero_screen |
| G10 | graph.py | 구매 수정 뒤 재구축 빼기 | 잡힘 | FAILED (failures=4) | test_purchase_color_strip, test_qty_99_accepted, test_update_t002_color, test_update_t005_qty |
| G11 | graph.py | get_customer가 복사본 대신 원본 반환 | 잡힘 | FAILED (failures=1) | test_copies_out |
| G12 | graph.py | get_product가 재고 딕셔너리를 공유 | 잡힘 | FAILED (failures=1) | test_copies_out |
| G13 | graph.py | is_sold_out을 all 대신 any | 잡힘 | FAILED (failures=17) | test_all_scope_only_screen, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_particle_boundaries, test_read_screens, test_register_then_recommend, test_s4_cap_per_customer, test_s4_g_f_20, test_sold_out_available_colors, test_widened_without_new_items_screen |
| G14 | graph.py | 구매 가능 색상에 재고 0 포함 (> → >=) | 잡힘 | FAILED (failures=14) | test_all_scope_only_screen, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_particle_boundaries, test_register_then_recommend, test_sold_out_available_colors, test_widened_without_new_items_screen |
| G15 | graph.py | ID 한도 경계 하나 차이 (>= → >) | 잡힘 | FAILED (failures=1) | test_id_limit |
| G16 | graph.py | 구매 기록이 있는 색상 삭제 거절 빼기 | 잡힘 | FAILED (failures=2) | test_invalid_update_delete_inputs, test_stock_reject_delete_and_dup |
| G17 | graph.py | 검사기가 검사 중 rebuild로 상태를 고침 | 잡힘 | FAILED (failures=4) | test_fault_edge_color, test_fault_orphan_edge, test_fault_reverse_adj, test_fault_wrong_group |
| G18 | graph.py | 검사기가 간선 집계 비교를 건너뜀 | 잡힘 | FAILED (failures=1) | test_fault_edge_color |
| G19 | graph.py | 가중치를 색상 수 대신 기록 수로 | 잡힘 | FAILED (failures=2) | test_add_t014_same_color, test_update_t002_color |
| G20 | graph.py | 오류 형식을 콜론 두 번으로 (graph) | 잡힘 | FAILED (failures=3) | test_age_error_screen, test_digit_limit_boundary, test_graph_and_search_same_format |
| G21 | graph.py | 생성자 ID 카운터를 최대 + 2로 | 잡힘 | FAILED (failures=31, errors=1) | test_add_t014_same_color, test_all_scope_only_screen, test_boundary_values_accepted, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_ctor_none_empty, test_customer_without_purchase, test_failed_add_keeps_counter, test_failed_add_product_keeps_counter, test_gender_scope_screen, test_gender_union, test_invalid_k, test_invalid_purchases_then_t014, test_issue_ids_no_reuse, test_k_max_accepted, test_k_min_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_particle_boundaries, test_print_keeps_state, test_purchase_color_strip, test_purchase_register_weight, test_purchase_zero_stock_color_allowed, test_qty_99_accepted, test_register_then_recommend, test_same_name, test_tree_follows_changes, test_widened_without_new_items_screen, test_zero_results, test_zero_screen |
| G22 | graph.py | 이름 조회를 부분 일치로 | 잡힘 | FAILED (failures=2) | test_find_by_name, test_read_screens |
| M01 | main.py | 삭제 확인 무시 (항상 삭제) | 잡힘 | FAILED (failures=2) | test_delete_cancel, test_delete_id_spaces |
| M02 | main.py | ValueError를 메시지로 바꾸지 않음 | 잡힘 | FAILED (errors=9) | test_age_error_screen, test_digit_limit_boundary, test_input_error_messages, test_invalid_create_inputs, test_invalid_read_inputs, test_invalid_update_delete_inputs, test_recommend_k_error_screen, test_recommend_k_not_number, test_s4_count_error_screen |
| M03 | main.py | 추천 K 기본값을 K_MAX로 | 잡힘 | FAILED (failures=1) | test_recommend_menu |
| M04 | main.py | 숫자 자릿수 제한 경계 (9 → 10) | 잡힘 | FAILED (failures=1) | test_digit_limit_boundary |
| M05 | main.py | 고객 삭제 ID 앞뒤 공백을 안 지움 | 잡힘 | FAILED (failures=1) | test_delete_id_spaces |
| M06 | main.py | 삭제 확인 0건 문구 빼기 | 잡힘 | FAILED (failures=1) | test_delete_cancel |
| M07 | main.py | EOF를 받지 않음 | 잡힘 | FAILED (errors=1) | test_eof_and_ctrl_c |
| M08 | main.py | 전체 인접 리스트에서 상품 빠짐 | 잡힘 | FAILED (failures=1) | test_print_screens |
| M09 | main.py | 번호 고르기에서 0 허용 | 잡힘 | FAILED (failures=2) | test_input_error_messages, test_invalid_read_inputs |
| S01 | search.py | 점수 상한 3 빼기 | 잡힘 | FAILED (failures=18) | test_c02_k3, test_c02_screen, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_k_min_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_read_screens, test_register_then_recommend, test_s4_cap_per_customer, test_s4_g_f_20, test_s4_k2, test_widened_without_new_items_screen |
| S02 | search.py | 정렬 키에서 구매자 수 빼기 | 잡힘 | FAILED (failures=13) | test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_k_min_accepted, test_read_screens, test_register_then_recommend, test_s4_g_f_20, test_s4_k2, test_widened_without_new_items_screen |
| S03 | search.py | 정렬 키 구매자 수 오름차순 | 잡힘 | FAILED (failures=13) | test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_k_min_accepted, test_read_screens, test_register_then_recommend, test_s4_g_f_20, test_s4_k2, test_widened_without_new_items_screen |
| S04 | search.py | 범위 넓히기 순서 바꾸기 (gender 먼저) | 잡힘 | FAILED (failures=15) | test_c02_k3, test_c02_screen, test_c07_k3, test_c07_k4, test_c07_k4_screen, test_c07_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_k_min_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_particle_boundaries, test_register_then_recommend, test_widened_without_new_items_screen |
| S05 | search.py | 같은 성별 범위 건너뛰기 | 잡힘 | FAILED (failures=5) | test_c06_k2_screen, test_c06_k3, test_c06_screen_example, test_gender_scope_screen, test_gender_union |
| S06 | search.py | 대상 고객을 동료에서 빼지 않음 | 못 잡음 | OK |  |
| S07 | search.py | 추천에서 품절 제외 빼기 | 잡힘 | FAILED (failures=16) | test_all_scope_only_screen, test_c02_k3, test_c02_screen, test_c06_k3, test_c06_screen_example, test_c07_k4, test_c07_k4_screen, test_gender_scope_screen, test_gender_union, test_k_max_accepted, test_p02_sold_out, test_p02_sold_out_screen, test_recommend_menu, test_widened_without_new_items_screen, test_zero_results, test_zero_screen |
| S08 | search.py | 추천에서 이미 산 상품 제외 빼기 | 잡힘 | FAILED (failures=3) | test_c02_k3, test_c02_screen, test_recommend_menu |
| S09 | search.py | 한 범위 안에서 K+1개까지 담기 | 잡힘 | FAILED (failures=4) | test_c06_k3, test_c06_screen_example, test_k_min_accepted, test_recommend_menu |
| S10 | search.py | S4 품절 표시 뒤집기 | 잡힘 | FAILED (failures=5) | test_read_screens, test_s4_cap_per_customer, test_s4_g_f_20, test_s4_id_tiebreak, test_s4_k2 |
| S11 | search.py | 조건 조회 최저 가격 경계 (>= → >) | 잡힘 | FAILED (failures=1) | test_find_products_more_conditions |
| S12 | search.py | 가격 범위 거꾸로 허용 | 잡힘 | FAILED (failures=2) | test_find_products_reversed_range, test_invalid_read_inputs |
| S13 | search.py | 색상 조건을 재고 있는 색으로 | 잡힘 | FAILED (failures=3) | test_find_products_conditions, test_find_products_more_conditions, test_read_screens |
| S14 | search.py | 오류 형식을 콜론 두 번으로 (search) | 잡힘 | FAILED (failures=3) | test_graph_and_search_same_format, test_recommend_k_error_screen, test_s4_count_error_screen |
| S15 | search.py | S4 개수 항목 이름을 k로 | 잡힘 | FAILED (failures=1) | test_s4_count_error_screen |
| V01 | view.py | 넓힘 판정에서 결과 수 < k 무시 | 잡힘 | FAILED (failures=1) | test_widened_without_new_items_screen |
| V02 | view.py | 점수 비교 안내를 범위 1개여도 출력 | 잡힘 | FAILED (failures=5) | test_all_scope_only_screen, test_c06_k2_screen, test_c07_screen, test_particle_boundaries, test_widened_without_new_items_screen |
| V03 | view.py | 조사 규칙에서 0을 받침 없음으로 | 잡힘 | FAILED (failures=1) | test_particle_boundaries |
| V04 | view.py | 표 폭에서 한글을 1칸으로 | 잡힘 | FAILED (failures=5) | test_bool_column_left_aligned, test_empty_rows, test_korean_width_alignment, test_mixed_column_left_aligned, test_narrow_and_ambiguous_width |
| V05 | view.py | 넓힘 이유를 항상 'K개가 안 돼'로 | 잡힘 | FAILED (failures=3) | test_all_scope_only_screen, test_c06_k2_screen, test_c06_screen_example |
| V06 | view.py | 개수 부족 안내 빼기 | 잡힘 | FAILED (failures=4) | test_all_scope_only_screen, test_c02_screen, test_recommend_menu, test_widened_without_new_items_screen |

총 56종 중 55종 잡힘, 1종 못 잡음
