"""search.py 조회·검색(S1~S4) 테스트. 클래스 이름의 W번호가 통과해야 하는 단계다 (부록 B.5).

기대값 출처는 계획서 6장과 부록 B뿐이다. 6장에 글자로 적혀 있지 않은 값은
"# [제안 기대값]" 주석과 계산 과정을 달았다.
"""

import unittest

from search import customers_of, find_products, group_popular, members_of, products_of
from tests.fixtures import make_graph
from tests.helpers import snapshot


class TestW6Query(unittest.TestCase):
    """W6: 조건 조회, S1~S3."""

    def test_find_products_conditions(self) -> None:
        """6.2 조건 조회: 색상 네이비 → [P01, P03](재고 0도 포함), 종류 상의 → [P01, P03], 가격 3만~5만 → [P02, P03, P04]."""
        g = make_graph()
        self.assertEqual(find_products(g, color="네이비"), ["P01", "P03"])
        self.assertEqual(find_products(g, kind="상의"), ["P01", "P03"])
        self.assertEqual(find_products(g, price_min=30000, price_max=50000), ["P02", "P03", "P04"])

    def test_find_products_reversed_range(self) -> None:
        """6.4 가격 범위 거꾸로(price_min 50000 > price_max 30000) → ValueError, 상태 불변."""
        g = make_graph()
        before = snapshot(g)
        with self.assertRaises(ValueError):
            find_products(g, price_min=50000, price_max=30000)
        self.assertEqual(snapshot(g), before)

    def test_find_products_invalid_values(self) -> None:
        """B.3 조건 조회: 종류·스타일은 상수 목록 안, 가격은 정수 0 이상(bool·문자열 거부) → 아니면 ValueError."""
        g = make_graph()
        cases = [
            ("종류 신발", {"kind": "신발"}),
            ("스타일 힙합", {"style": "힙합"}),
            ("최저 가격 -1", {"price_min": -1}),
            ("최고 가격 True", {"price_max": True}),
            ("최저 가격 문자열", {"price_min": "1000"}),
        ]
        before = snapshot(g)
        for label, kwargs in cases:
            with self.assertRaises(ValueError, msg=label):
                find_products(g, **kwargs)
            self.assertEqual(snapshot(g), before, msg=f"실패 후 상태가 바뀜: {label}")

    def test_s1_products_of_c01(self) -> None:
        """6.2 S1(C01): P01(색상 4·가중치 4·기록 4·총수량 4·최근 10-01), P02(블랙·1·1·1·09-03)."""
        g = make_graph()
        # [제안 기대값] "name" 칸만 6.2 S1에 글자로 없어서 6.1 상품명을 옮김 (P01 오버핏 티셔츠, P02 와이드 슬랙스).
        # 나머지 칸은 6.2 S1 값 그대로.
        self.assertEqual(products_of(g, "C01"), [
            {"product_id": "P01", "name": "오버핏 티셔츠", "colors": ["그레이", "네이비", "블랙", "화이트"],
             "weight": 4, "count": 4, "total_qty": 4, "last_date": "2026-10-01"},
            {"product_id": "P02", "name": "와이드 슬랙스", "colors": ["블랙"],
             "weight": 1, "count": 1, "total_qty": 1, "last_date": "2026-09-03"},
        ])

    def test_s2_customers_of_p05(self) -> None:
        """6.2 S2(P05) = C03, C04 (고객 ID 순)."""
        g = make_graph()
        result = customers_of(g, "P05")
        self.assertEqual([r["customer_id"] for r in result], ["C03", "C04"])
        # [제안 기대값] 6.2에는 고객 ID만 있음. 나머지 칸은 6.1에서 옮김:
        # C03 = 고객3, G-F-20, T010 그레이 / C04 = 고객4, G-M-20, T012 블랙
        self.assertEqual(result, [
            {"customer_id": "C03", "name": "고객3", "group_id": "G-F-20", "colors": ["그레이"]},
            {"customer_id": "C04", "name": "고객4", "group_id": "G-M-20", "colors": ["블랙"]},
        ])

    def test_s3_members_of(self) -> None:
        """6.2 S3: G-F-20 = [C01, C02, C03], G-F-30 = [C05], G-F-10 = []."""
        g = make_graph()
        self.assertEqual(members_of(g, "G-F-20"), ["C01", "C02", "C03"])
        self.assertEqual(members_of(g, "G-F-30"), ["C05"])
        self.assertEqual(members_of(g, "G-F-10"), [])

    def test_s3_after_age_move(self) -> None:
        """B.5 S3 이동 후: C04 나이 24 → 34 수정 뒤 members_of(G-M-20) = [] (6.4 C04 나이 수정)."""
        g = make_graph()
        g.update_customer("C04", age=34)
        self.assertEqual(g.check_integrity(), [])  # 5.3.5 W5 이후 변경 뒤 확인
        self.assertEqual(members_of(g, "G-M-20"), [])

    def test_missing_ids_search(self) -> None:
        """B.2·B.3: 없는 고객·상품·그룹 ID로 S1·S2·S3 → ValueError."""
        g = make_graph()
        with self.assertRaises(ValueError):
            products_of(g, "C99")
        with self.assertRaises(ValueError):
            customers_of(g, "P99")
        with self.assertRaises(ValueError):
            members_of(g, "G-X-10")


class TestW7Popular(unittest.TestCase):
    """W7: S4 그룹 인기 상품."""

    @staticmethod
    def _s4_g_f_20() -> list[dict]:
        """6.2 S4(G-F-20) 기대값을 새로 만든다.

        6.2: P02(3, 구매자 2), P01(3, 구매자 1), P03(2, 구매자 2), P05(1, 품절 표시)
        [제안 기대값] 6.2에 글자로 없는 칸: P05 구매자 수 1(G-F-20에서 P05를 산 사람은 C03뿐, T010),
        sold_out 값(6.1 재고: P01·P02·P03은 재고 1 이상 색상이 있어 False, P05는 전부 0이라 True).

        인자:
            없음.

        반환:
            항목 4개의 새 리스트.

        예외:
            없음.
        """
        return [
            {"product_id": "P02", "score": 3, "buyers": 2, "sold_out": False},
            {"product_id": "P01", "score": 3, "buyers": 1, "sold_out": False},
            {"product_id": "P03", "score": 2, "buyers": 2, "sold_out": False},
            {"product_id": "P05", "score": 1, "buyers": 1, "sold_out": True},
        ]

    def test_s4_g_f_20(self) -> None:
        """6.2 S4(G-F-20): 상한 3 적용(P01 가중치 4 → 3), 동점은 구매자 수, 품절 P05도 표시."""
        g = make_graph()
        self.assertEqual(group_popular(g, "G-F-20"), self._s4_g_f_20())

    def test_s4_k2(self) -> None:
        """6.2 S4(G-F-20, k=2) = P02, P01."""
        g = make_graph()
        self.assertEqual(group_popular(g, "G-F-20", k=2), self._s4_g_f_20()[:2])

    def test_s4_invalid_k(self) -> None:
        """6.4 S4의 잘못된 k(0, 11, True), B.3 숫자 문자열 "3", B.2 없는 그룹 → ValueError."""
        g = make_graph()
        before = snapshot(g)
        for k in (0, 11, True, "3"):
            with self.assertRaises(ValueError, msg=repr(k)):
                group_popular(g, "G-F-20", k=k)
            self.assertEqual(snapshot(g), before, msg=f"실패 후 상태가 바뀜: k={k!r}")
        with self.assertRaises(ValueError):
            group_popular(g, "G-X-10")
        self.assertEqual(snapshot(g), before, msg="실패 후 상태가 바뀜: G-X-10")

    def test_s4_empty_group(self) -> None:
        """B.4 소속 고객이 없는 그룹, 소속 고객의 구매가 없는 그룹 → 빈 리스트."""
        g = make_graph()
        # [제안 기대값] G-F-10은 소속 고객 없음(6.2 S3), G-F-30은 C05뿐인데 C05 구매 없음(6.1)
        # → 점수가 생긴 상품이 없어 둘 다 []
        self.assertEqual(group_popular(g, "G-F-10"), [])
        self.assertEqual(group_popular(g, "G-F-30"), [])


if __name__ == "__main__":
    unittest.main()
