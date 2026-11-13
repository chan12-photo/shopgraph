"""X1: 인계 2판·v3 5.2의 ID 발급·정렬. 기대값은 작은 픽스처에서 직접 정한다."""

import copy
import unittest

import graph
from graph import ShopGraph
from search import group_popular, recommend
from tests.fixtures import make_graph, x1_boundary_records, x1_sort_records
from tests.helpers import snapshot


class TestX1Ids(unittest.TestCase):
    """고정 자릿수 경계와 숫자 정렬, 기존 상태 보호 규칙을 함께 확인한다."""

    def test_customer_boundary_and_no_reuse(self) -> None:
        """C99 다음 C100, 삭제·재구축 후 C101. 성공 변경마다 무결성을 확인한다."""
        g = ShopGraph(*x1_boundary_records())
        self.assertEqual(g.add_customer("새 고객", "여", 25), "C100")
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.delete_customer("C100"), 0)
        self.assertEqual(g.check_integrity(), [])
        g.rebuild()
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_customer("다음 고객", "여", 25), "C101")
        self.assertEqual(g.check_integrity(), [])

    def test_product_boundary_and_no_reuse(self) -> None:
        """P99 다음 P100, 삭제·재구축 후 P101. 데이터는 한 상품에서 시작한다."""
        g = ShopGraph(*x1_boundary_records())
        self.assertEqual(g.add_product("새 상품", "상의", "캐주얼", 1000, {"블랙": 1}), "P100")
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.delete_product("P100"), 0)
        self.assertEqual(g.check_integrity(), [])
        g.rebuild()
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_product("다음 상품", "상의", "캐주얼", 1000, {"블랙": 1}), "P101")
        self.assertEqual(g.check_integrity(), [])

    def test_purchase_boundary_and_no_reuse(self) -> None:
        """T999 다음 T1000, 삭제·재구축 후 T1001. 데이터는 한 구매에서 시작한다."""
        g = ShopGraph(*x1_boundary_records())
        self.assertEqual(g.add_purchase("C99", "P99", "블랙", 1, "2026-11-02"), "T1000")
        self.assertEqual(g.check_integrity(), [])
        g.delete_purchase("T1000")
        self.assertEqual(g.check_integrity(), [])
        g.rebuild()
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_purchase("C99", "P99", "블랙", 1, "2026-11-02"), "T1001")
        self.assertEqual(g.check_integrity(), [])

    def test_six_digit_numbers_with_small_records(self) -> None:
        """각 한 건만으로 100000 다음 번호를 확인한다. 대량 성능 검사는 아니다."""
        g = ShopGraph(*x1_boundary_records("C100000", "P100000", "T100000"))
        self.assertEqual(g.add_customer("다음 고객", "여", 25), "C100001")
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_product("다음 상품", "상의", "캐주얼", 1000, {"블랙": 1}), "P100001")
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_purchase("C100000", "P100000", "블랙", 1, "2026-11-02"), "T100001")
        self.assertEqual(g.check_integrity(), [])

    def test_allowed_record_ids(self) -> None:
        """v3 허용 형식을 생성자·조회로 확인한다. 입력 원본도 바뀌지 않아야 한다."""
        cases = {"customer_id": ["C01", "C09", "C10", "C99", "C100"],
                 "product_id": ["P01", "P09", "P10", "P99", "P100"],
                 "purchase_id": ["T001", "T009", "T099", "T100", "T999", "T1000"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    records = x1_boundary_records(**{field: value})
                    before = copy.deepcopy(records)
                    g = ShopGraph(*records)
                    getter = {"customer_id": g.get_customer, "product_id": g.get_product,
                              "purchase_id": g.get_purchase}[field]
                    self.assertEqual(getter(value)["id"], value)
                    self.assertEqual(g.check_integrity(), [])
                    self.assertEqual(records, before)

    def test_rejected_record_ids(self) -> None:
        """0·부족한 자릿수·과도한 앞자리 0·비ASCII·공백을 거부하고 생성자 입력을 보존한다."""
        cases = {"customer_id": ["C00", "C1", "C9", "C007", "C0100", "C０１", "C01\n"],
                 "product_id": ["P00", "P1", "P9", "P007", "P0100", "P０１", " P01"],
                 "purchase_id": ["T000", "T01", "T0001", "T01000", "T００１", "T001\n"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    records = x1_boundary_records(**{field: value})
                    before = copy.deepcopy(records)
                    with self.assertRaisesRegex(ValueError, "ID: 형식이 올바르지 않습니다"):
                        ShopGraph(*records)
                    self.assertEqual(records, before)

    def test_failed_boundary_additions_keep_all_state(self) -> None:
        """경계에서 잘못된 등록은 상태·카운터를 보존하고 다음 정상 번호를 소비하지 않는다."""
        g = ShopGraph(*x1_boundary_records())
        calls = [lambda: g.add_customer("실패", "여", True),
                 lambda: g.add_product("실패", "상의", "캐주얼", True, {"블랙": 1}),
                 lambda: g.add_purchase("C99", "P99", "블랙", True, "2026-11-02")]
        for call in calls:
            before = snapshot(g)
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(snapshot(g), before)
        self.assertEqual(g.add_customer("고객", "여", 25), "C100")
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_product("상품", "상의", "캐주얼", 1000, {"블랙": 1}), "P100")
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.add_purchase("C99", "P99", "블랙", 1, "2026-11-02"), "T1000")
        self.assertEqual(g.check_integrity(), [])

    def test_bad_lookup_ids_keep_all_state(self) -> None:
        """조회에서는 형식이 틀리거나 없는 ID를 기존처럼 거절하고 상태를 보존한다."""
        g = ShopGraph(*x1_boundary_records())
        for getter, value in [(g.get_customer, "C1"), (g.get_customer, "C0100"),
                              (g.get_customer, "C100"), (g.get_product, "P0100"),
                              (g.get_purchase, "T01"), (g.get_purchase, "T0001")]:
            with self.subTest(value=value):
                before = snapshot(g)
                with self.assertRaisesRegex(ValueError, "존재하지 않는"):
                    getter(value)
                self.assertEqual(snapshot(g), before)

    def test_customer_ids_and_name_results_numeric(self) -> None:
        """C09·C10·C99·C100을 포함해 숫자 순이다. 문자열 순이면 C100이 C99보다 앞선다."""
        g = ShopGraph(*x1_sort_records())
        before = snapshot(g)
        self.assertEqual(g.customer_ids(), ["C01", "C09", "C10", "C99", "C100"])
        self.assertEqual(g.find_customers_by_name(" 동명 고객 "), ["C01", "C09", "C10", "C99", "C100"])
        self.assertEqual(snapshot(g), before)

    def test_product_ids_and_name_results_numeric(self) -> None:
        """상품 목록과 동명 검색 모두 P09·P10·P99·P100 순이다."""
        g = ShopGraph(*x1_sort_records())
        before = snapshot(g)
        self.assertEqual(g.product_ids(), ["P09", "P10", "P99", "P100"])
        self.assertEqual(g.find_products_by_name(" 동명 상품 "), ["P09", "P10", "P99", "P100"])
        self.assertEqual(snapshot(g), before)

    def test_neighbors_numeric_with_group(self) -> None:
        """고객 이웃의 그룹 우선·상품 숫자 순과 상품 이웃의 고객 숫자 순을 확인한다."""
        g = ShopGraph(*x1_sort_records())
        before = snapshot(g)
        self.assertEqual(g.neighbors("C09"), ["G-F-20", "P99", "P100"])
        self.assertEqual(g.neighbors("P99"), ["C09", "C10", "C99", "C100"])
        self.assertEqual(g.neighbors("G-F-20"), ["C01", "C09", "C10", "C99", "C100"])
        self.assertEqual(snapshot(g), before)

    def test_members_numeric(self) -> None:
        """소속 고객 조회도 숫자 순이며 조회가 상태를 바꾸지 않는다."""
        g = ShopGraph(*x1_sort_records())
        before = snapshot(g)
        self.assertEqual(g.members("G-F-20"), ["C01", "C09", "C10", "C99", "C100"])
        self.assertEqual(snapshot(g), before)

    def test_public_sort_key_mixed_kinds(self) -> None:
        """종류 C<G<P<T, 번호는 숫자 순, 그룹은 문자열 순으로 정렬한다."""
        ids = ["T1000", "P100", "G-M-10", "C100", "T009", "P99", "C10",
               "G-F-20", "T999", "C09", "C99", "P09", "T010", "P10"]
        self.assertEqual(sorted(ids, key=graph.id_sort_key),
                         ["C09", "C10", "C99", "C100", "G-F-20", "G-M-10", "P09", "P10",
                          "P99", "P100", "T009", "T010", "T999", "T1000"])

    def test_existing_neighbors_and_color_order_unchanged(self) -> None:
        """기존 C01 이웃·색상 정렬은 X1 전과 같다."""
        g = make_graph()
        before = snapshot(g)
        self.assertEqual(g.neighbors("C01"), ["G-F-20", "P01", "P02"])
        self.assertEqual(g.edge("C01", "P01")["colors"], ["그레이", "네이비", "블랙", "화이트"])
        self.assertEqual(g.available_colors("P01"), ["그레이", "네이비", "블랙", "화이트"])
        self.assertEqual(snapshot(g), before)

    def test_recommendation_ties_and_supporters_numeric(self) -> None:
        """각 4점·4명인 P99가 P100보다 앞이며 지지자도 C09·C10·C99·C100 순이다."""
        g = ShopGraph(*x1_sort_records())
        before = snapshot(g)
        expected = [{"product_id": pid, "score": 4, "buyers": 4, "scope": "group",
                     "supporters": ["C09", "C10", "C99", "C100"], "available_colors": ["블랙", "화이트"]}
                    for pid in ("P99", "P100")]
        self.assertEqual(recommend(g, "C01", 2), expected)
        self.assertEqual(snapshot(g), before)

    def test_expanded_peers_and_supporters_numeric(self) -> None:
        """다른 연령대 세 그룹에서 모인 동료도 번호 순이며 점수는 각 4점이다."""
        cs, ps, ts = x1_sort_records()
        ages = {"C01": 25, "C09": 15, "C10": 35, "C99": 35, "C100": 45}
        for row in cs:
            row["age"] = ages[row["id"]]
        g = ShopGraph(cs, ps, ts)
        before = snapshot(g)
        expected = [{"product_id": pid, "score": 4, "buyers": 4, "scope": "gender",
                     "supporters": ["C09", "C10", "C99", "C100"], "available_colors": ["블랙", "화이트"]}
                    for pid in ("P99", "P100")]
        self.assertEqual(recommend(g, "C01", 2), expected)
        self.assertEqual(snapshot(g), before)

    def test_s4_ties_numeric(self) -> None:
        """S4도 점수 4·구매자 4 동점이면 P99가 P100보다 먼저다."""
        g = ShopGraph(*x1_sort_records())
        before = snapshot(g)
        self.assertEqual(group_popular(g, "G-F-20"),
                         [{"product_id": "P99", "score": 4, "buyers": 4, "sold_out": False},
                          {"product_id": "P100", "score": 4, "buyers": 4, "sold_out": False}])
        self.assertEqual(snapshot(g), before)

    def test_integrity_purchase_messages_numeric(self) -> None:
        """고객 원본 삭제 고장에서 T999·T1000 순으로 진단하고 고장 상태를 보존한다."""
        cs, ps, ts = x1_boundary_records()
        ts.insert(0, {**ts[0], "id": "T1000"})
        g = ShopGraph(cs, ps, ts)
        del g._customers["C99"]  # 고장 주입에서만 내부 상태 직접 변경.
        before = snapshot(g)
        errors = g.check_integrity()
        self.assertEqual([e for e in errors if e.startswith("구매 기록")],
                         ["구매 기록 T999: 존재하지 않는 고객 C99을(를) 참조합니다",
                          "구매 기록 T1000: 존재하지 않는 고객 C99을(를) 참조합니다"])
        self.assertEqual(g.check_integrity(), errors)
        self.assertEqual(snapshot(g), before)

    def test_integrity_edge_messages_numeric(self) -> None:
        """집계 고장 진단의 (고객,상품) 키도 숫자 순으로 보고하며 상태를 보존한다."""
        g = ShopGraph(*x1_sort_records())
        for cid in ("C100", "C99", "C10", "C09"):
            g._edges[(cid, "P99")]["colors"].clear()  # 고장 주입.
        before = snapshot(g)
        errors = g.check_integrity()
        self.assertEqual([e for e in errors if e.startswith("간선 (")],
                         ["간선 (C09,P99)의 집계가 구매 기록과 다릅니다",
                          "간선 (C10,P99)의 집계가 구매 기록과 다릅니다",
                          "간선 (C99,P99)의 집계가 구매 기록과 다릅니다",
                          "간선 (C100,P99)의 집계가 구매 기록과 다릅니다"])
        self.assertEqual(g.check_integrity(), errors)
        self.assertEqual(snapshot(g), before)

    def test_integrity_asymmetry_and_missing_links_numeric(self) -> None:
        """단방향 고장에서 이웃·구매 간선·재구축 진단이 모두 숫자 순이다."""
        g = ShopGraph(*x1_sort_records())
        for cid in ("C100", "C99", "C10", "C09"):
            g._adj[cid].discard("P99")  # 고장 주입: P99 쪽 역방향은 남긴다.
        before = snapshot(g)
        errors = g.check_integrity()
        self.assertEqual([e for e in errors if e.startswith("인접 리스트가")],
                         ["인접 리스트가 한쪽만 있습니다: P99 → C09",
                          "인접 리스트가 한쪽만 있습니다: P99 → C10",
                          "인접 리스트가 한쪽만 있습니다: P99 → C99",
                          "인접 리스트가 한쪽만 있습니다: P99 → C100"])
        self.assertEqual([e for e in errors if e.startswith("구매 간선 (")],
                         ["구매 간선 (C09,P99)이 양쪽 인접 리스트에 다 있지 않습니다",
                          "구매 간선 (C10,P99)이 양쪽 인접 리스트에 다 있지 않습니다",
                          "구매 간선 (C99,P99)이 양쪽 인접 리스트에 다 있지 않습니다",
                          "구매 간선 (C100,P99)이 양쪽 인접 리스트에 다 있지 않습니다"])
        self.assertEqual([e for e in errors if "원본에서 다시 만든 결과" in e],
                         ["C09의 인접 리스트가 원본에서 다시 만든 결과와 다릅니다",
                          "C10의 인접 리스트가 원본에서 다시 만든 결과와 다릅니다",
                          "C99의 인접 리스트가 원본에서 다시 만든 결과와 다릅니다",
                          "C100의 인접 리스트가 원본에서 다시 만든 결과와 다릅니다"])
        self.assertEqual(g.check_integrity(), errors)
        self.assertEqual(snapshot(g), before)

    def test_integrity_missing_nodes_numeric(self) -> None:
        """노드 누락 고장의 빠진 노드 목록도 C09·C10·C99·C100 순이다."""
        g = ShopGraph(*x1_sort_records())
        for cid in ("C100", "C99", "C10", "C09"):
            del g._adj[cid]  # 고장 주입.
        before = snapshot(g)
        errors = g.check_integrity()
        self.assertEqual(errors[0],
                         "노드 집합이 맞지 않습니다: 남는 노드 [], 빠진 노드 ['C09', 'C10', 'C99', 'C100']")
        self.assertEqual(g.check_integrity(), errors)
        self.assertEqual(snapshot(g), before)

    def test_integrity_group_messages_numeric(self) -> None:
        """그룹 연결을 양쪽에서 끊으면 소속 그룹 오류도 고객 번호 순으로 나온다."""
        g = ShopGraph(*x1_sort_records())
        for cid in ("C100", "C99", "C10", "C09"):
            g._adj[cid].discard("G-F-20")  # 고장 주입.
            g._adj["G-F-20"].discard(cid)
        before = snapshot(g)
        errors = g.check_integrity()
        self.assertEqual([e for e in errors if "의 소속 그룹" in e],
                         ["C09의 소속 그룹이 []입니다 (성별·나이 기준 G-F-20 하나여야 함)",
                          "C10의 소속 그룹이 []입니다 (성별·나이 기준 G-F-20 하나여야 함)",
                          "C99의 소속 그룹이 []입니다 (성별·나이 기준 G-F-20 하나여야 함)",
                          "C100의 소속 그룹이 []입니다 (성별·나이 기준 G-F-20 하나여야 함)"])
        self.assertEqual(g.check_integrity(), errors)
        self.assertEqual(snapshot(g), before)


if __name__ == "__main__":
    unittest.main()
