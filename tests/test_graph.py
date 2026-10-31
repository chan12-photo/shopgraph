"""graph.py(ShopGraph) 테스트. 클래스 이름의 W번호가 통과해야 하는 단계다 (계획서 11.3.2, 부록 B.5).

기대값 출처는 계획서 6장과 부록 B뿐이다. 6장에 글자로 적혀 있지 않은 값은
"# [제안 기대값]" 주석과 계산 과정을 달았다 (W2 G7에서 사람 승인).
각 테스트는 자기 단계까지 구현되는 함수만 부른다 (W4는 g.members로 확인, check_integrity는 W5부터).
"""

import unittest
from collections.abc import Callable

from graph import ShopGraph
from tests.fixtures import customers, make_graph, products, purchases
from tests.helpers import snapshot


def _assert_rejected(tc: unittest.TestCase, g: ShopGraph, call: Callable[[], object], msg: str) -> None:
    """call()이 ValueError를 내고 g의 내부 상태 전체가 그대로인지 확인한다 (계획서 6.4 잘못된 입력).

    인자:
        tc: 확인을 수행할 TestCase.
        g: 상태를 비교할 ShopGraph.
        call: 실패해야 하는 호출을 감싼 함수.
        msg: 실패 시 보여 줄 입력 설명.

    반환:
        없음.

    예외:
        AssertionError: ValueError가 나지 않거나 상태가 바뀌었을 때.
    """
    before = snapshot(g)
    with tc.assertRaises(ValueError, msg=msg):
        call()
    tc.assertEqual(snapshot(g), before, msg=f"실패 후 상태가 바뀜: {msg}")


class TestW3Build(unittest.TestCase):
    """W3: 생성자·조회·rebuild (graph 읽기 쪽)."""

    def test_initial_counts(self) -> None:
        """6.2 노드 19개(그룹 8·고객 6·상품 5), 소속 간선 6, 구매 간선 9, 구매 기록 13."""
        g = make_graph()
        st = g.stats()
        self.assertEqual(st, {"groups": 8, "customers": 6, "products": 5,
                              "membership_edges": 6, "purchase_edges": 9, "purchases": 13})
        self.assertEqual(st["groups"] + st["customers"] + st["products"], 19)
        # [제안 기대값] ID 목록은 6.2에 글자로 없음. 6.1 고객 C01~C06, 상품 P01~P05를 ID 오름차순으로 나열.
        self.assertEqual(g.customer_ids(), ["C01", "C02", "C03", "C04", "C05", "C06"])
        self.assertEqual(g.product_ids(), ["P01", "P02", "P03", "P04", "P05"])

    def test_initial_groups(self) -> None:
        """6.1 그룹 칸과 6.2 S3 값: 고객별 그룹, g.members 결과 (빈 그룹 포함)."""
        g = make_graph()
        expected = {"C01": "G-F-20", "C02": "G-F-20", "C03": "G-F-20",
                    "C04": "G-M-20", "C05": "G-F-30", "C06": "G-M-10"}
        for cid, gid in expected.items():
            self.assertEqual(g.group_of(cid), gid, msg=cid)
        self.assertEqual(g.members("G-F-20"), ["C01", "C02", "C03"])
        self.assertEqual(g.members("G-F-30"), ["C05"])
        self.assertEqual(g.members("G-F-10"), [])

    def test_edge_aggregates(self) -> None:
        """6.2 간선 집계 9개의 가중치, edge("C01","P01") 형식, (C02,P02) 집계."""
        g = make_graph()
        weights = {("C01", "P01"): 4, ("C01", "P02"): 1, ("C02", "P02"): 2, ("C02", "P03"): 1,
                   ("C03", "P03"): 1, ("C03", "P05"): 1, ("C04", "P04"): 1, ("C04", "P05"): 1,
                   ("C04", "P01"): 1}
        for (cid, pid), w in weights.items():
            self.assertEqual(g.weight(cid, pid), w, msg=(cid, pid))
        self.assertEqual(g.edge("C01", "P01"), {"colors": ["그레이", "네이비", "블랙", "화이트"],
                                                "count": 4, "total_qty": 4, "last_date": "2026-10-01"})
        e = g.edge("C02", "P02")
        self.assertEqual((len(e["colors"]), e["count"], e["total_qty"], e["last_date"]),
                         (2, 2, 2, "2026-09-20"))

    def test_find_by_name(self) -> None:
        """6.2 이름 조회: 앞뒤 공백 제거 후 완전 일치, 부분 일치 아님, 공백뿐인 이름은 ValueError (B.2)."""
        g = make_graph()
        self.assertEqual(g.find_customers_by_name(" 고객1 "), ["C01"])
        self.assertEqual(g.find_customers_by_name("고객"), [])
        with self.assertRaises(ValueError):
            g.find_customers_by_name("   ")
        # [제안 기대값] 상품명 조회: B.2 규칙을 6.1 상품명에 적용.
        # " 카고 팬츠 " → 공백 제거 "카고 팬츠" = P04 상품명과 완전 일치 → ["P04"],
        # "카고" → 완전 일치하는 상품명 없음 → []
        self.assertEqual(g.find_products_by_name(" 카고 팬츠 "), ["P04"])
        self.assertEqual(g.find_products_by_name("카고"), [])
        with self.assertRaises(ValueError):
            g.find_products_by_name("   ")

    def test_neighbors_sorted(self) -> None:
        """B.2 neighbors: 이웃 ID를 ID 오름차순으로 돌려준다."""
        g = make_graph()
        # [제안 기대값] 6.1 데이터에서 이웃을 모아 문자열 오름차순 정렬.
        # C01: 소속 그룹 G-F-20 + 구매 상품 P01(T001~T004), P02(T005) → ["G-F-20", "P01", "P02"] ("G" < "P")
        # P05: 구매 고객 C03(T010), C04(T012) → ["C03", "C04"]
        # G-F-20: 소속 고객 C01, C02, C03 / G-F-10: 소속 없음 → []
        self.assertEqual(g.neighbors("C01"), ["G-F-20", "P01", "P02"])
        self.assertEqual(g.neighbors("P05"), ["C03", "C04"])
        self.assertEqual(g.neighbors("G-F-20"), ["C01", "C02", "C03"])
        self.assertEqual(g.neighbors("G-F-10"), [])

    def test_ctor_bad_id_and_date_format(self) -> None:
        """6.4 생성자 검증: 초기 고객 ID 형식 C1 / 초기 구매일 형식 20260901 → ValueError."""
        cs = customers()
        cs[0]["id"] = "C1"
        with self.assertRaises(ValueError):
            ShopGraph(cs, products(), [])
        ts = purchases()
        ts[0]["date"] = "20260901"
        with self.assertRaises(ValueError):
            ShopGraph(customers(), products(), ts)

    def test_ctor_date_not_real(self) -> None:
        """B.1 생성자 계약 3·B.3 구매일 ②: 형식은 맞지만 없는 날짜(초기 구매일 2026-02-30) → ValueError."""
        ts = purchases()
        ts[0]["date"] = "2026-02-30"
        with self.assertRaises(ValueError):
            ShopGraph(customers(), products(), ts)

    def test_ctor_bad_shape(self) -> None:
        """B.1 생성자 계약 1·5: 리스트도 None도 아닌 인자, 딕셔너리가 아닌 레코드, 키가 빠진 레코드 → ValueError."""
        as_dict = {c["id"]: c for c in customers()}
        with self.assertRaises(ValueError):
            ShopGraph(as_dict, products(), purchases())
        with self.assertRaises(ValueError):
            ShopGraph(customers() + ["C07"], products(), purchases())
        cs = customers()
        del cs[0]["age"]
        with self.assertRaises(ValueError):
            ShopGraph(cs, products(), purchases())

    def test_ctor_duplicate_and_missing_ref(self) -> None:
        """6.4 생성자 검증: 같은 고객 ID 두 번 / 없는 고객 C99를 참조하는 구매 → ValueError."""
        cs = customers()
        cs.append({"id": "C01", "name": "고객1", "gender": "여", "age": 23})
        with self.assertRaises(ValueError):
            ShopGraph(cs, products(), purchases())
        ts = purchases()
        ts[0]["customer_id"] = "C99"
        with self.assertRaises(ValueError):
            ShopGraph(customers(), products(), ts)

    def test_ctor_input_copied(self) -> None:
        """6.4 들어오는 쪽: 생성자에 넘긴 C01 나이·P01 블랙 재고를 나중에 고쳐도 내부는 23·5."""
        cs, ps, ts = customers(), products(), purchases()
        g = ShopGraph(cs, ps, ts)
        cs[0]["age"] = 50
        ps[0]["stock"]["블랙"] = 0
        self.assertEqual(g.get_customer("C01")["age"], 23)
        self.assertEqual(g.group_of("C01"), "G-F-20")
        self.assertEqual(g.get_product("P01")["stock"]["블랙"], 5)

    def test_ctor_strips_spaces(self) -> None:
        """B.3 공백 제거 값 저장(생성자 초기 레코드 포함): 이름·상품명·재고 색상명·구매 색상을 지운 값으로 저장."""
        cs, ps, ts = customers(), products(), purchases()
        cs[0]["name"] = " 고객1 "
        ps[0]["name"] = " 오버핏 티셔츠 "
        ps[0]["stock"] = {" 블랙 ": 5, "화이트": 5, "그레이": 5, "네이비": 5}
        ts[0]["color"] = " 블랙 "
        g = ShopGraph(cs, ps, ts)
        # [제안 기대값] B.3 "공백 제거 값 저장" 행을 위 입력에 적용: 앞뒤 공백을 지운 값이 저장된다.
        # 이름 " 고객1 " → "고객1", 상품명 " 오버핏 티셔츠 " → "오버핏 티셔츠", 색상 " 블랙 " → "블랙".
        # 그 결과 데이터가 6.1과 같아지므로 (C01,P01) 색상은 6.2 값 그대로다.
        self.assertEqual(g.get_customer("C01")["name"], "고객1")
        self.assertEqual(g.get_product("P01")["name"], "오버핏 티셔츠")
        self.assertEqual(g.get_product("P01")["stock"], {"블랙": 5, "화이트": 5, "그레이": 5, "네이비": 5})
        self.assertEqual(g.get_purchase("T001")["color"], "블랙")
        self.assertEqual(g.edge("C01", "P01")["colors"], ["그레이", "네이비", "블랙", "화이트"])

    def test_edge_weight_missing_vs_none(self) -> None:
        """B.2: 없는 고객·상품 ID의 edge()·weight()는 ValueError, 둘 다 있는데 간선이 없으면 None·0."""
        g = make_graph()
        for cid, pid in (("C99", "P01"), ("C01", "P99")):
            _assert_rejected(self, g, lambda cid=cid, pid=pid: g.edge(cid, pid), f"edge {cid} {pid}")
            _assert_rejected(self, g, lambda cid=cid, pid=pid: g.weight(cid, pid), f"weight {cid} {pid}")
        self.assertIsNone(g.edge("C05", "P01"))
        self.assertEqual(g.weight("C05", "P01"), 0)

    def test_missing_ids(self) -> None:
        """B.2·B.3 ID: 없는 ID와 형식이 틀린 ID의 조회는 ValueError."""
        g = make_graph()
        calls = [
            ("get_customer C99", lambda: g.get_customer("C99")),
            ("get_customer C1", lambda: g.get_customer("C1")),
            ("get_product P99", lambda: g.get_product("P99")),
            ("get_purchase T999", lambda: g.get_purchase("T999")),
            ("neighbors X01", lambda: g.neighbors("X01")),
            ("group_of C99", lambda: g.group_of("C99")),
            ("members G-X-10", lambda: g.members("G-X-10")),
        ]
        for label, call in calls:
            _assert_rejected(self, g, call, label)

    def test_copies_out(self) -> None:
        """6.4 나가는 쪽: get_customer·edge·get_product 반환값을 고쳐도 직접 다시 조회하면 그대로."""
        g = make_graph()
        c = g.get_customer("C01")
        c["age"] = 50
        self.assertEqual(g.get_customer("C01")["age"], 23)
        self.assertEqual(g.group_of("C01"), "G-F-20")
        e = g.edge("C01", "P01")
        e["colors"].append("레드")
        self.assertEqual(g.edge("C01", "P01")["colors"], ["그레이", "네이비", "블랙", "화이트"])
        p = g.get_product("P01")
        p["stock"]["블랙"] = 0
        self.assertEqual(g.get_product("P01")["stock"]["블랙"], 5)

    def test_rebuild_idempotent(self) -> None:
        """B.1·5.5 rebuild: 원본에서 다시 지어도 상태 전체(ID 카운터 포함)가 같다."""
        g = make_graph()
        # [제안 기대값] rebuild()는 원본 데이터에서 그래프를 다시 만들고 ID 카운터는 바꾸지 않는다(B.1).
        # 처음 상태의 그래프는 원본에서 만든 것이므로 rebuild 전후 snapshot이 같아야 한다.
        before = snapshot(g)
        g.rebuild()
        self.assertEqual(snapshot(g), before)

    def test_ctor_none_empty(self) -> None:
        """B.1 생성자 계약 1·6: 인자 None = 빈 리스트, 레코드가 없으면 ID 카운터는 종류별로 1."""
        g = ShopGraph(None, None, None)
        # [제안 기대값] 계약 1 "None = 빈 리스트"와 5.5 "8개 그룹 노드 생성"을 적용:
        # 그룹 8개만 있고 고객·상품·구매·간선은 0. 계약 6 "없으면 1" → 카운터 C·P·T 모두 1.
        self.assertEqual(g.stats(), {"groups": 8, "customers": 0, "products": 0,
                                     "membership_edges": 0, "purchase_edges": 0, "purchases": 0})
        self.assertEqual(g.customer_ids(), [])
        self.assertEqual(g.product_ids(), [])
        self.assertEqual(snapshot(g)["next_ids"], {"C": 1, "P": 1, "T": 1})
        self.assertEqual(snapshot(ShopGraph()), snapshot(g))


class TestW4CustomerProduct(unittest.TestCase):
    """W4: 고객·상품 변경, 그룹 이동, 연쇄 삭제, 입력 검증, 재고."""

    def test_issue_ids_no_reuse(self) -> None:
        """6.4 ID 발급: 처음 등록은 C07, C07 삭제 → rebuild → 다음 등록은 C08."""
        g = make_graph()
        self.assertEqual(g.add_customer("고객7", "여", 22), "C07")
        self.assertEqual(g.delete_customer("C07"), 0)  # [제안 기대값] 구매 기록이 없는 고객 → 함께 삭제된 기록 0건
        g.rebuild()
        self.assertEqual(g.add_customer("고객8", "여", 22), "C08")

    def test_failed_add_keeps_counter(self) -> None:
        """6.4 실패한 등록은 ID를 쓰지 않는다: 나이 True 등록 실패(상태 불변) → 다음 정상 등록은 C07."""
        g = make_graph()
        _assert_rejected(self, g, lambda: g.add_customer("고객7", "여", True), "나이 True")
        self.assertEqual(g.add_customer("고객7", "여", 22), "C07")

    def test_age_move(self) -> None:
        """6.4 C04 나이 24 → 34: group_of = G-M-30, g.members("G-M-20") = []."""
        g = make_graph()
        g.update_customer("C04", age=34)
        self.assertEqual(g.group_of("C04"), "G-M-30")
        self.assertEqual(g.members("G-M-20"), [])

    def test_gender_move(self) -> None:
        """6.4 C01 성별 → 남: G-M-20 이동, G-F-20 = [C02, C03], G-M-20 = [C01, C04]."""
        g = make_graph()
        g.update_customer("C01", gender="남")
        self.assertEqual(g.group_of("C01"), "G-M-20")
        self.assertEqual(g.members("G-F-20"), ["C02", "C03"])
        self.assertEqual(g.members("G-M-20"), ["C01", "C04"])

    def test_same_name(self) -> None:
        """6.4 동명이인: add_customer("고객1", "남", 30) → C07, 이름 조회 = [C01, C07]."""
        g = make_graph()
        self.assertEqual(g.add_customer("고객1", "남", 30), "C07")
        self.assertEqual(g.find_customers_by_name("고객1"), ["C01", "C07"])

    def test_id_limit(self) -> None:
        """6.4 ID 한도: 초기 고객에 C99가 있으면 add_customer → ValueError("ID 한도 초과"), 상태 불변."""
        cs = customers()
        cs.append({"id": "C99", "name": "고객99", "gender": "남", "age": 30})
        g = ShopGraph(cs, products(), purchases())
        before = snapshot(g)
        with self.assertRaisesRegex(ValueError, "ID 한도 초과"):
            g.add_customer("고객100", "여", 22)
        self.assertEqual(snapshot(g), before)

    def test_delete_customer_cascade(self) -> None:
        """6.4 C02 삭제: 반환 3, 구매 기록 10, 구매 간선 7, 노드 18, G-F-20 = [C01, C03]."""
        g = make_graph()
        self.assertEqual(g.delete_customer("C02"), 3)
        st = g.stats()
        self.assertEqual((st["purchases"], st["purchase_edges"]), (10, 7))
        self.assertEqual(st["groups"] + st["customers"] + st["products"], 18)
        self.assertEqual(g.members("G-F-20"), ["C01", "C03"])

    def test_delete_product_cascade(self) -> None:
        """6.4 P01 삭제: 반환 5(T001~T004, T013), 구매 기록 8, 구매 간선 7."""
        g = make_graph()
        self.assertEqual(g.delete_product("P01"), 5)
        st = g.stats()
        self.assertEqual((st["purchases"], st["purchase_edges"]), (8, 7))

    def test_stock_replace_add_color(self) -> None:
        """6.4 P04 재고를 {카키 4, 블랙 4, 그레이 1}로 교체: 색상 추가 성공, 구매 가능 색상에 그레이."""
        g = make_graph()
        g.update_product("P04", stock={"카키": 4, "블랙": 4, "그레이": 1})
        self.assertIn("그레이", g.available_colors("P04"))
        self.assertEqual(g.get_product("P04")["stock"], {"카키": 4, "블랙": 4, "그레이": 1})

    def test_stock_reject_delete_and_dup(self) -> None:
        """6.4: 구매 기록이 있는 색상 삭제(P01 → {블랙 5}) 거절, 공백 제거 후 겹치는 색상명 거절. 상태 불변."""
        g = make_graph()
        _assert_rejected(self, g, lambda: g.update_product("P01", stock={"블랙": 5}), "P01 색상 삭제")
        # [제안 기대값] 6.1에서 P02 베이지는 두 번째 이웃 C02(T007)만 샀으므로 베이지 삭제도 거절.
        _assert_rejected(self, g, lambda: g.update_product("P02", stock={"블랙": 3}), "P02 베이지 삭제")
        _assert_rejected(self, g, lambda: g.update_product("P04", stock={"카키": 1, " 카키 ": 2}),
                         "update_product 겹치는 색상명")
        _assert_rejected(self, g, lambda: g.add_product("새 상품", "상의", "캐주얼", 10000,
                                                        {"카키": 1, " 카키 ": 2}),
                         "add_product 겹치는 색상명")

    def test_stock_input_copied(self) -> None:
        """6.4 들어오는 쪽: add_product·update_product에 넘긴 stock을 나중에 고쳐도 내부 재고 그대로."""
        g = make_graph()
        st = {"블랙": 3, "화이트": 2}
        pid = g.add_product("린넨 셔츠", "상의", "캐주얼", 30000, st)
        st["블랙"] = 0
        self.assertEqual(g.get_product(pid)["stock"]["블랙"], 3)
        st2 = {"카키": 4, "블랙": 4}
        g.update_product("P04", stock=st2)
        st2["카키"] = 0
        self.assertEqual(g.get_product("P04")["stock"]["카키"], 4)

    def test_invalid_customer_mixed(self) -> None:
        """6.4 고객 잘못된 입력: 나이 True 등록, 바꿀 항목 없는 수정, 섞은 수정(이름도 안 바뀜). 상태 불변."""
        g = make_graph()
        _assert_rejected(self, g, lambda: g.add_customer("고객7", "여", True), "나이 True")
        _assert_rejected(self, g, lambda: g.update_customer("C01"), "바꿀 항목 없음")
        _assert_rejected(self, g, lambda: g.update_customer("C01", name="변경됨", age=True), "섞은 수정")
        self.assertEqual(g.get_customer("C01")["name"], "고객1")

    def test_invalid_product_mixed(self) -> None:
        """6.4 상품 섞은 수정 update_product("P01", name="변경됨", price=-1) → 이름도 안 바뀜, 바꿀 항목 없음도 거절."""
        g = make_graph()
        _assert_rejected(self, g, lambda: g.update_product("P01", name="변경됨", price=-1), "섞은 수정")
        self.assertEqual(g.get_product("P01")["name"], "오버핏 티셔츠")
        _assert_rejected(self, g, lambda: g.update_product("P01"), "바꿀 항목 없음")

    def test_invalid_customer_values(self) -> None:
        """B.3·B.4 고객 값 규칙: 빈 이름, 21자, 성별 M, 나이 9·100·"30", 없는 ID 수정·삭제 → ValueError, 상태 불변."""
        g = make_graph()
        cases = [
            ("공백뿐인 이름", lambda: g.add_customer("   ", "여", 22)),
            ("이름 21자", lambda: g.add_customer("가" * 21, "여", 22)),
            ("성별 M", lambda: g.add_customer("고객7", "M", 22)),
            ("나이 9", lambda: g.add_customer("고객7", "여", 9)),
            ("나이 100", lambda: g.add_customer("고객7", "여", 100)),
            ("나이 문자열", lambda: g.add_customer("고객7", "여", "30")),
            ("없는 고객 수정", lambda: g.update_customer("C99", age=30)),
            ("형식이 틀린 고객 ID 수정", lambda: g.update_customer("C1", age=30)),
            ("없는 고객 삭제", lambda: g.delete_customer("C99")),
        ]
        for label, call in cases:
            _assert_rejected(self, g, call, label)

    def test_invalid_product_values(self) -> None:
        """B.3·B.4 상품 값 규칙: 종류·스타일 밖, 가격 -1·"1000"·True, 빈 재고, 재고 -1·True, 색상명 11자, 빈 상품명, 없는 ID."""
        g = make_graph()
        stock = {"블랙": 1}
        cases = [
            ("종류 밖", lambda: g.add_product("새 상품", "신발", "캐주얼", 10000, stock)),
            ("스타일 밖", lambda: g.add_product("새 상품", "상의", "힙합", 10000, stock)),
            ("가격 -1", lambda: g.add_product("새 상품", "상의", "캐주얼", -1, stock)),
            ("가격 문자열", lambda: g.add_product("새 상품", "상의", "캐주얼", "1000", stock)),
            ("가격 True", lambda: g.add_product("새 상품", "상의", "캐주얼", True, stock)),
            ("빈 재고", lambda: g.add_product("새 상품", "상의", "캐주얼", 10000, {})),
            ("재고 -1", lambda: g.add_product("새 상품", "상의", "캐주얼", 10000, {"블랙": -1})),
            ("재고 True", lambda: g.add_product("새 상품", "상의", "캐주얼", 10000, {"블랙": True})),
            ("색상명 11자", lambda: g.add_product("새 상품", "상의", "캐주얼", 10000, {"가" * 11: 1})),
            ("공백뿐인 상품명", lambda: g.add_product("   ", "상의", "캐주얼", 10000, stock)),
            ("없는 상품 수정", lambda: g.update_product("P99", price=1)),
            ("없는 상품 삭제", lambda: g.delete_product("P99")),
        ]
        for label, call in cases:
            _assert_rejected(self, g, call, label)

    def test_strip_on_register(self) -> None:
        """B.3 공백 제거 값 저장: 등록·수정한 이름·상품명·색상명을 앞뒤 공백을 지운 값으로 저장."""
        g = make_graph()
        cid = g.add_customer(" 고객7 ", "여", 22)
        self.assertEqual(g.get_customer(cid)["name"], "고객7")  # B.3 예시 그대로
        # [제안 기대값] 아래는 B.3 "공백 제거 값 저장" 행을 새 입력에 적용한 값.
        # 상품명 " 린넨 셔츠 " → "린넨 셔츠", 재고 색상 " 화이트 " → "화이트".
        pid = g.add_product(" 린넨 셔츠 ", "상의", "캐주얼", 30000, {" 화이트 ": 3})
        self.assertEqual(g.get_product(pid)["name"], "린넨 셔츠")
        self.assertEqual(g.get_product(pid)["stock"], {"화이트": 3})
        # 고객 이름 수정 " 새이름 " → "새이름".
        g.update_customer("C01", name=" 새이름 ")
        self.assertEqual(g.get_customer("C01")["name"], "새이름")
        # P04 재고 {" 카키 ": 4, "블랙": 4}: 공백을 지우면 "카키"라서 기존 색상(T011 구매 기록 있음)을
        # 지우는 수정이 아니므로 성공하고, 저장된 재고는 {"카키": 4, "블랙": 4}.
        g.update_product("P04", name=" 카고 팬츠2 ", stock={" 카키 ": 4, "블랙": 4})
        self.assertEqual(g.get_product("P04")["name"], "카고 팬츠2")
        self.assertEqual(g.get_product("P04")["stock"], {"카키": 4, "블랙": 4})

    def test_sold_out_available_colors(self) -> None:
        """B.2·B.4 품절: P05 전부 품절, P03 일부 품절(아이보리만 구매 가능), 구매 가능 색상은 정렬 리스트."""
        g = make_graph()
        self.assertTrue(g.is_sold_out("P05"))
        self.assertFalse(g.is_sold_out("P03"))
        self.assertEqual(g.available_colors("P03"), ["아이보리"])  # 6.3-1
        self.assertEqual(g.available_colors("P01"), ["그레이", "네이비", "블랙", "화이트"])  # 6.3-4
        self.assertEqual(g.available_colors("P04"), ["블랙", "카키"])  # 6.3-4
        self.assertEqual(g.available_colors("P02"), ["베이지", "블랙"])  # 6.3-4
        # [제안 기대값] P05는 그레이 0·블랙 0(6.1)이라 재고 > 0인 색상이 없음 → []
        self.assertEqual(g.available_colors("P05"), [])

    def test_boundary_values_accepted(self) -> None:
        """B.3 경계값 허용: 나이 10·99, 이름 20자, 가격 0은 등록된다."""
        g = make_graph()
        # [제안 기대값] B.3 범위(나이 10~99, 이름 1~20자, 가격 0 이상)의 양 끝은 허용.
        # 발급 ID는 처음 상태 카운터(B.1 {"C": 7, "P": 6})부터 차례로 C07, C08, P06.
        # 그룹은 5.3 연령대 계산: 10 → 10대, 99 → 40대 이상.
        self.assertEqual(g.add_customer("고객7", "여", 10), "C07")
        self.assertEqual(g.group_of("C07"), "G-F-10")
        self.assertEqual(g.members("G-F-10"), ["C07"])
        self.assertEqual(g.add_customer("가" * 20, "남", 99), "C08")
        self.assertEqual(g.get_customer("C08"), {"id": "C08", "name": "가" * 20, "gender": "남", "age": 99})
        self.assertEqual(g.group_of("C08"), "G-M-40+")
        self.assertEqual(g.add_product("무료 상품", "상의", "캐주얼", 0, {"블랙": 1}), "P06")
        self.assertEqual(g.get_product("P06")["price"], 0)

    def test_delete_unpurchased_color(self) -> None:
        """B.3 색상 삭제: 구매 기록이 없는 색상(P03 네이비)은 재고 교체로 삭제된다."""
        g = make_graph()
        # [제안 기대값] P03 구매 기록은 T008·T009 아이보리뿐(6.1)이라 네이비 삭제는 허용.
        # 교체 후 재고 {"아이보리": 2}, 구매 가능 색상 ["아이보리"].
        g.update_product("P03", stock={"아이보리": 2})
        self.assertEqual(g.get_product("P03")["stock"], {"아이보리": 2})
        self.assertEqual(g.available_colors("P03"), ["아이보리"])

    def test_failed_add_product_keeps_counter(self) -> None:
        """6.4·B.3 실패한 등록은 ID를 쓰지 않는다: 가격 -1 상품 등록 실패(상태 불변) → 다음 정상 등록은 P06."""
        g = make_graph()
        _assert_rejected(self, g, lambda: g.add_product("새 상품", "상의", "캐주얼", -1, {"블랙": 1}), "가격 -1")
        # [제안 기대값] 처음 상태 상품 카운터는 6(B.1 {"P": 6}), 실패한 등록은 번호를 쓰지 않음 → P06.
        self.assertEqual(g.add_product("새 상품", "상의", "캐주얼", 10000, {"블랙": 1}), "P06")

    def test_update_product_fields(self) -> None:
        """5.3.1 상품 수정: 종류·스타일·가격만 수정하면 그 값만 바뀌고 재고·구매 관계는 그대로."""
        g = make_graph()
        g.update_product("P01", kind="아우터", style="포멀", price=31000)
        # [제안 기대값] 6.1 P01에서 종류·스타일·가격만 바꾼 값. 이름·재고는 6.1 그대로.
        # 구매 관계는 바뀌지 않으므로 P01 이웃은 6.1 T001~T004(C01)·T013(C04) → [C01, C04], (C01,P01) 가중치 4(6.2).
        self.assertEqual(g.get_product("P01"), {
            "id": "P01", "name": "오버핏 티셔츠", "kind": "아우터", "style": "포멀", "price": 31000,
            "stock": {"블랙": 5, "화이트": 5, "그레이": 5, "네이비": 5},
        })
        self.assertEqual(g.neighbors("P01"), ["C01", "C04"])
        self.assertEqual(g.weight("C01", "P01"), 4)

    def test_delete_cascade_neighbors(self) -> None:
        """6.4 C02 삭제 연쇄: 개수뿐 아니라 이웃 목록에서도 C02가 빠지고, C02와 그 구매 기록은 조회되지 않는다."""
        g = make_graph()
        g.delete_customer("C02")
        # [제안 기대값] 6.1에서 P02 구매자는 C01(T005)·C02(T006·T007), P03 구매자는 C02(T008)·C03(T009).
        # C02를 지우면 P02 → [C01], P03 → [C03], G-F-20 → [C01, C03](6.4 members 값과 같음).
        self.assertEqual(g.neighbors("P02"), ["C01"])
        self.assertEqual(g.neighbors("P03"), ["C03"])
        self.assertEqual(g.neighbors("G-F-20"), ["C01", "C03"])
        for label, call in (("neighbors C02", lambda: g.neighbors("C02")),
                            ("get_customer C02", lambda: g.get_customer("C02")),
                            ("get_purchase T006", lambda: g.get_purchase("T006")),
                            ("get_purchase T008", lambda: g.get_purchase("T008"))):
            _assert_rejected(self, g, call, label)


class TestW5Purchase(unittest.TestCase):
    """W5: 구매 등록·수정·삭제와 간선 집계. 변경 뒤 check_integrity() = [] (5.3.5)."""

    def test_delete_t004(self) -> None:
        """6.4 T004 삭제: (C01,P01) 간선 유지, 색상 3·가중치 3·기록 3건·최근 2026-09-15."""
        g = make_graph()
        g.delete_purchase("T004")
        e = g.edge("C01", "P01")
        self.assertEqual((len(e["colors"]), g.weight("C01", "P01"), e["count"], e["last_date"]),
                         (3, 3, 3, "2026-09-15"))
        # [제안 기대값] 남는 기록 T001 블랙·T002 화이트·T003 그레이 → 정렬 리스트 ["그레이", "블랙", "화이트"].
        self.assertEqual(e["colors"], ["그레이", "블랙", "화이트"])
        self.assertEqual(g.check_integrity(), [])

    def test_delete_t005_last_record(self) -> None:
        """6.4 T005 삭제(마지막 기록): edge("C01","P02") = None, 구매 기록 12, 구매 간선 8."""
        g = make_graph()
        g.delete_purchase("T005")
        self.assertIsNone(g.edge("C01", "P02"))
        st = g.stats()
        self.assertEqual((st["purchases"], st["purchase_edges"]), (12, 8))
        self.assertEqual(g.check_integrity(), [])

    def test_add_t014_same_color(self) -> None:
        """6.4 T014 추가(C02-P02-블랙, 같은 색 재구매): 발급 T014, 가중치 2 그대로, 기록 3, 총수량 3, 최근 2026-10-05."""
        g = make_graph()
        self.assertEqual(g.add_purchase("C02", "P02", "블랙", 1, "2026-10-05"), "T014")
        e = g.edge("C02", "P02")
        self.assertEqual((g.weight("C02", "P02"), e["count"], e["total_qty"], e["last_date"]),
                         (2, 3, 3, "2026-10-05"))
        self.assertEqual(g.check_integrity(), [])

    def test_add_t014_then_delete_t006(self) -> None:
        """6.4 T014 추가 후 T006 삭제: 색상 2개(베이지·블랙)·가중치 2, 기록 2, 총수량 2, 최근 2026-10-05."""
        g = make_graph()
        g.add_purchase("C02", "P02", "블랙", 1, "2026-10-05")
        g.delete_purchase("T006")
        e = g.edge("C02", "P02")
        self.assertEqual(e, {"colors": ["베이지", "블랙"], "count": 2, "total_qty": 2, "last_date": "2026-10-05"})
        self.assertEqual(g.weight("C02", "P02"), 2)
        self.assertEqual(g.check_integrity(), [])

    def test_update_t005_qty(self) -> None:
        """6.4 T005 수량 1 → 3: (C01,P02) 총수량 3, 기록 1건, 가중치 1 그대로."""
        g = make_graph()
        g.update_purchase("T005", qty=3)
        e = g.edge("C01", "P02")
        self.assertEqual((e["total_qty"], e["count"], g.weight("C01", "P02")), (3, 1, 1))
        self.assertEqual(g.check_integrity(), [])

    def test_update_t002_color(self) -> None:
        """6.4 T002 색상 화이트 → 블랙: (C01,P01) 색상 그레이·네이비·블랙, 가중치 3, 기록 4, 총수량 4, 최근 2026-10-01."""
        g = make_graph()
        g.update_purchase("T002", color="블랙")
        self.assertEqual(g.edge("C01", "P01"), {"colors": ["그레이", "네이비", "블랙"], "count": 4,
                                                "total_qty": 4, "last_date": "2026-10-01"})
        self.assertEqual(g.weight("C01", "P01"), 3)
        self.assertEqual(g.check_integrity(), [])

    def test_invalid_purchases_then_t014(self) -> None:
        """6.4 잘못된 구매 등록 7종(상태 불변) 뒤 다음 정상 등록은 T014."""
        g = make_graph()
        cases = [
            ("없는 고객 C99", ("C99", "P03", "아이보리", 1, "2026-10-05")),
            ("P03에 없는 색상 레드", ("C01", "P03", "레드", 1, "2026-10-05")),
            ("수량 0", ("C01", "P03", "아이보리", 0, "2026-10-05")),
            ("구매일 20261023", ("C01", "P03", "아이보리", 1, "20261023")),
            ("구매일 2026-W43-5", ("C01", "P03", "아이보리", 1, "2026-W43-5")),
            ("구매일 2026-02-30", ("C01", "P03", "아이보리", 1, "2026-02-30")),
            ("구매일 2026-1-5", ("C01", "P03", "아이보리", 1, "2026-1-5")),
        ]
        for label, args in cases:
            _assert_rejected(self, g, lambda args=args: g.add_purchase(*args), label)
        self.assertEqual(g.add_purchase("C02", "P02", "블랙", 1, "2026-10-05"), "T014")
        self.assertEqual(g.check_integrity(), [])

    def test_invalid_purchase_other(self) -> None:
        """B.3·B.4 구매 값 규칙: 수량 100·True·"1", 없는 상품, 바꿀 항목 없는 수정, 없는 구매 ID, 잘못된 수정 값."""
        g = make_graph()
        cases = [
            ("수량 100", lambda: g.add_purchase("C01", "P03", "아이보리", 100, "2026-10-05")),
            ("수량 True", lambda: g.add_purchase("C01", "P03", "아이보리", True, "2026-10-05")),
            ("수량 문자열", lambda: g.add_purchase("C01", "P03", "아이보리", "1", "2026-10-05")),
            ("없는 상품 P99", lambda: g.add_purchase("C01", "P99", "블랙", 1, "2026-10-05")),
            ("바꿀 항목 없는 수정", lambda: g.update_purchase("T001")),
            ("없는 구매 수정", lambda: g.update_purchase("T999", qty=2)),
            ("수정 색상 레드", lambda: g.update_purchase("T001", color="레드")),
            ("수정 수량 0", lambda: g.update_purchase("T001", qty=0)),
            ("없는 구매 삭제", lambda: g.delete_purchase("T999")),
        ]
        for label, call in cases:
            _assert_rejected(self, g, call, label)

    def test_purchase_color_strip(self) -> None:
        """B.3 구매 색상 포함: add_purchase·update_purchase의 " 블랙 "은 공백을 지운 "블랙"으로 비교·저장."""
        g = make_graph()
        self.assertEqual(g.add_purchase("C02", "P02", " 블랙 ", 1, "2026-10-05"), "T014")
        # [제안 기대값] B.3에 따라 " 블랙 " → "블랙"으로 비교(P02 색상 목록에 있음)·저장.
        # 그러면 6.4 "T014 추가"와 같은 입력이 되어 (C02,P02) 값은 6.4 그대로이고,
        # 색상 집합은 기존 {블랙(T006), 베이지(T007)}에 블랙이 더해져도 ["베이지", "블랙"].
        self.assertEqual(g.get_purchase("T014")["color"], "블랙")
        self.assertEqual(g.edge("C02", "P02"), {"colors": ["베이지", "블랙"], "count": 3,
                                                "total_qty": 3, "last_date": "2026-10-05"})
        self.assertEqual(g.check_integrity(), [])
        g2 = make_graph()
        g2.update_purchase("T002", color=" 블랙 ")
        # [제안 기대값] " 블랙 " → "블랙" 저장. 결과 집계는 6.4 "T002 색상 화이트 → 블랙" 값 그대로.
        self.assertEqual(g2.get_purchase("T002")["color"], "블랙")
        self.assertEqual(g2.edge("C01", "P01"), {"colors": ["그레이", "네이비", "블랙"], "count": 4,
                                                 "total_qty": 4, "last_date": "2026-10-01"})
        self.assertEqual(g2.check_integrity(), [])

    def test_purchase_zero_stock_color_allowed(self) -> None:
        """B.3 구매 색상: 재고 비연동이라 재고 0인 색상(P03 네이비)도 구매 기록 가능, 재고는 바뀌지 않음."""
        g = make_graph()
        # [제안 기대값] 처음 상태의 다음 구매 ID는 T014(6.4). C01은 P03을 산 적이 없으므로
        # 새 간선 (C01,P03)이 생기고 색상 ["네이비"]·가중치 1. 재고 비연동이라 P03 네이비 재고는 0 그대로.
        self.assertEqual(g.add_purchase("C01", "P03", "네이비", 1, "2026-10-05"), "T014")
        self.assertEqual(g.edge("C01", "P03")["colors"], ["네이비"])
        self.assertEqual(g.weight("C01", "P03"), 1)
        self.assertEqual(g.get_product("P03")["stock"]["네이비"], 0)
        self.assertEqual(g.check_integrity(), [])

    def test_qty_99_accepted(self) -> None:
        """B.3 경계값 허용: 구매 수량 99는 등록·수정된다."""
        g = make_graph()
        # [제안 기대값] B.3 수량 1~99의 끝값 허용. 다음 구매 ID T014(6.4), C01은 P03을 산 적 없음(6.1)
        # → 새 간선 (C01,P03) 아이보리, 기록 1, 총수량 99.
        self.assertEqual(g.add_purchase("C01", "P03", "아이보리", 99, "2026-10-05"), "T014")
        self.assertEqual(g.edge("C01", "P03"), {"colors": ["아이보리"], "count": 1,
                                                "total_qty": 99, "last_date": "2026-10-05"})
        self.assertEqual(g.check_integrity(), [])
        # T005(C01-P02, 수량 1)을 99로 수정 → (C01,P02) 총수량 99, 기록 1.
        g.update_purchase("T005", qty=99)
        self.assertEqual(g.edge("C01", "P02")["total_qty"], 99)
        self.assertEqual(g.check_integrity(), [])


class TestW5Integrity(unittest.TestCase):
    """W5: 무결성 검사기 자체 (5.3.5 고장 주입). 내부 상태 직접 수정은 이 클래스에만 허용된다."""

    def _assert_fault_reported(self, g: ShopGraph) -> None:
        """고장 난 g에서 검사기가 두 번 모두 위반을 보고하고, 검사 전후 상태가 같은지 확인한다.

        위반 보고는 B.2 형식(위반 설명 문자열의 리스트)이고 1건 이상이어야 한다 (6.4).

        인자:
            g: 고장을 주입한 ShopGraph.

        반환:
            없음.

        예외:
            AssertionError: 위반을 보고하지 않거나, 보고 형식이 문자열 리스트가 아니거나, 검사가 상태를 바꿨을 때.
        """
        before = snapshot(g)
        for _ in range(2):
            report = g.check_integrity()
            self.assertIsInstance(report, list)
            self.assertTrue(report)
            for item in report:
                self.assertIsInstance(item, str)
        self.assertEqual(snapshot(g), before)

    def test_clean_state(self) -> None:
        """5.3.5·B.2: 처음 상태에서 check_integrity() = [], 검사 전후 상태 동일."""
        g = make_graph()
        before = snapshot(g)
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(snapshot(g), before)

    def test_fault_reverse_adj(self) -> None:
        """6.4 고장 주입 1: P01 쪽 인접 리스트에서 C01 제거."""
        g = make_graph()
        g._adj["P01"].discard("C01")
        self._assert_fault_reported(g)

    def test_fault_edge_color(self) -> None:
        """6.4 고장 주입 2: (C01,P01) 색상 집합에서 블랙 제거."""
        g = make_graph()
        g._edges[("C01", "P01")]["colors"].discard("블랙")
        self._assert_fault_reported(g)

    def test_fault_wrong_group(self) -> None:
        """6.4 고장 주입 3: C01을 G-F-30에 잘못 연결 (① G-F-20에 더해 연결 ② G-F-20에서 G-F-30으로 옮김)."""
        g = make_graph()
        g._adj["C01"].add("G-F-30")
        g._adj["G-F-30"].add("C01")
        self._assert_fault_reported(g)
        # ② 소속 그룹은 하나지만 나이(23)와 맞지 않는 경우 (5.3.5 "그 그룹이 성별·나이와 맞다")
        g2 = make_graph()
        g2._adj["C01"].discard("G-F-20")
        g2._adj["G-F-20"].discard("C01")
        g2._adj["C01"].add("G-F-30")
        g2._adj["G-F-30"].add("C01")
        self._assert_fault_reported(g2)

    def test_fault_orphan_edge(self) -> None:
        """6.4 고장 주입 4: 구매 기록 없는 (C05,P01) 간선 추가."""
        g = make_graph()
        g._edges[("C05", "P01")] = {"colors": {"블랙"}, "count": 1, "total_qty": 1, "last_date": "2026-10-01"}
        g._adj["C05"].add("P01")
        g._adj["P01"].add("C05")
        self._assert_fault_reported(g)


if __name__ == "__main__":
    unittest.main()
