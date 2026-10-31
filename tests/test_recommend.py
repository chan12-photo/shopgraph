"""search.recommend 추천 테스트 (계획서 6.3, 6.4 P02 품절). 클래스 이름의 W번호가 통과 단계다 (부록 B.5).

항목마다 상품 ID·범위·점수·구매자 수·지지자·구매 가능 색상을 모두 비교한다 (6.3 비교 기준).
6장에 글자로 적혀 있지 않은 값은 "# [제안 기대값]" 주석과 계산 과정을 달았다.
"""

import unittest

from graph import ShopGraph
from search import recommend
from tests.fixtures import make_graph
from tests.helpers import snapshot


def _item(pid: str, score: int, scope: str, supporters: list[str], colors: list[str]) -> dict:
    """추천 결과 한 항목의 기대값을 만든다. buyers는 len(supporters)로 채운다 (부록 B.2).

    인자:
        pid: 상품 ID.
        score: 그 범위 안에서 계산한 점수.
        scope: "group" | "gender" | "all".
        supporters: 지지 고객 ID 리스트, ID 오름차순.
        colors: 구매 가능 색상 리스트, 정렬 순서.

    반환:
        {"product_id", "score", "buyers", "scope", "supporters", "available_colors"} 딕셔너리.

    예외:
        없음.
    """
    return {"product_id": pid, "score": score, "buyers": len(supporters), "scope": scope,
            "supporters": supporters, "available_colors": colors}


def _colors(pid: str) -> list[str]:
    """처음 상태의 구매 가능 색상 기대값을 새 리스트로 돌려준다 (6.3-4: P01·P04·P02, 6.3-1: P03 아이보리만).

    인자:
        pid: P01~P04 중 하나.

    반환:
        구매 가능 색상의 새 리스트, 정렬 순서.

    예외:
        KeyError: 표에 없는 상품 ID.
    """
    return list({
        "P01": ("그레이", "네이비", "블랙", "화이트"),
        "P02": ("베이지", "블랙"),
        "P03": ("아이보리",),
        "P04": ("블랙", "카키"),
    }[pid])


def _c07_k3() -> list[dict]:
    """6.3-1 C07(여, 22), K=3 결과 기대값을 새로 만든다.

    인자:
        없음.

    반환:
        항목 3개의 새 리스트.

    예외:
        없음.
    """
    return [
        _item("P02", 3, "group", ["C01", "C02"], _colors("P02")),
        _item("P01", 3, "group", ["C01"], _colors("P01")),
        _item("P03", 2, "group", ["C02", "C03"], _colors("P03")),
    ]


def _c07_k4() -> list[dict]:
    """6.3-2 C07, K=4 결과 기대값을 새로 만든다: 1번 결과 + P04(점수 1, 1명, 전체, 지지자 C04).

    인자:
        없음.

    반환:
        항목 4개의 새 리스트.

    예외:
        없음.
    """
    return _c07_k3() + [_item("P04", 1, "all", ["C04"], _colors("P04"))]


class TestW8Recommend(unittest.TestCase):
    """W8: 추천 (범위 확장, 상한, 정렬, 품절·이미 산 상품 제외)."""

    def _graph_with_c07(self) -> ShopGraph:
        """6.1 처음 상태에 C07(여, 22)을 등록한 그래프를 만든다.

        인자:
            없음.

        반환:
            C07이 등록된 새 ShopGraph.

        예외:
            AssertionError: 발급 ID가 C07이 아니거나, 그룹이 G-F-20이 아니거나, 등록 뒤 무결성 위반이 있을 때.
        """
        g = make_graph()
        self.assertEqual(g.add_customer("고객7", "여", 22), "C07")
        self.assertEqual(g.group_of("C07"), "G-F-20")
        self.assertEqual(g.check_integrity(), [])  # 5.3.5 W5 이후 변경 뒤 확인
        return g

    def _assert_buyers_match(self, result: list[dict]) -> None:
        """모든 항목에서 buyers == len(supporters)인지 확인한다 (부록 B.2).

        인자:
            result: recommend()의 반환값.

        반환:
            없음.

        예외:
            AssertionError: 하나라도 다를 때.
        """
        for item in result:
            self.assertEqual(item["buyers"], len(item["supporters"]), msg=item["product_id"])

    def test_c07_k3(self) -> None:
        """6.3-1 신규 C07, K=3: P02(3, 2명) → P01(3, 1명) → P03(2, 2명), 모두 같은 그룹. P05 품절 제외."""
        g = self._graph_with_c07()
        result = recommend(g, "C07", 3)
        self.assertEqual(result, _c07_k3())
        self._assert_buyers_match(result)

    def test_c07_k4(self) -> None:
        """6.3-2 C07, K=4: 같은 그룹 3개, 여성 전체에서 새 후보 없음, 전체로 넓혀 P04(1, 1명, 전체, C04)."""
        g = self._graph_with_c07()
        result = recommend(g, "C07", 4)
        self.assertEqual(result, _c07_k4())
        self._assert_buyers_match(result)

    def test_c02_k3(self) -> None:
        """6.3-3 기존 C02, K=3: P01(3, 같은 그룹, C01), P04(1, 전체, C04) → 2개만 (이미 산 P02·P03 제외)."""
        g = make_graph()
        result = recommend(g, "C02", 3)
        self.assertEqual(result, [
            _item("P01", 3, "group", ["C01"], _colors("P01")),
            _item("P04", 1, "all", ["C04"], _colors("P04")),
        ])
        self._assert_buyers_match(result)

    def test_c06_k3(self) -> None:
        """6.3-4 C06(남, 15), K=3: P01·P04(1, 남성 전체, C04) → P02(3, 전체, C01·C02). 범위가 다르면 점수 비교 안 함."""
        g = make_graph()
        result = recommend(g, "C06", 3)
        self.assertEqual(result, [
            _item("P01", 1, "gender", ["C04"], _colors("P01")),
            _item("P04", 1, "gender", ["C04"], _colors("P04")),
            _item("P02", 3, "all", ["C01", "C02"], _colors("P02")),
        ])
        self._assert_buyers_match(result)

    def test_invalid_k(self) -> None:
        """6.3-5 K = 0, 11, True, "3" → ValueError. B.2 없는 고객 C99 → ValueError."""
        g = self._graph_with_c07()
        before = snapshot(g)
        for k in (0, 11, True, "3"):
            with self.assertRaises(ValueError, msg=repr(k)):
                recommend(g, "C07", k)
            self.assertEqual(snapshot(g), before, msg=f"실패 후 상태가 바뀜: K={k!r}")
        with self.assertRaises(ValueError):
            recommend(g, "C99", 3)
        self.assertEqual(snapshot(g), before, msg="실패 후 상태가 바뀜: C99")

    def test_gender_union(self) -> None:
        """6.3-6 같은 성별 여러 연령대 합산: C05가 P04 카키 구매 후 C07, K=4 → 4번째 P04(1, 1명, 같은 성별, C05)."""
        g = self._graph_with_c07()
        g.add_purchase("C05", "P04", "카키", 1, "2026-10-03")
        self.assertEqual(g.check_integrity(), [])
        result = recommend(g, "C07", 4)
        self.assertEqual(result, _c07_k3() + [_item("P04", 1, "gender", ["C05"], _colors("P04"))])
        self._assert_buyers_match(result)

    def test_zero_results(self) -> None:
        """6.3-7 C07 등록 후 모든 상품 재고를 0으로 교체 → recommend(C07, 3) = []."""
        g = self._graph_with_c07()
        for pid in g.product_ids():
            g.update_product(pid, stock={color: 0 for color in g.get_product(pid)["stock"]})
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(recommend(g, "C07", 3), [])

    def test_p02_sold_out(self) -> None:
        """6.4 C07 등록 후 P02 재고를 블랙 0·베이지 0으로 → C07 추천(K=3) = P01, P03, P04[전체]."""
        g = self._graph_with_c07()
        g.update_product("P02", stock={"블랙": 0, "베이지": 0})
        self.assertEqual(g.check_integrity(), [])
        result = recommend(g, "C07", 3)
        self.assertEqual([r["product_id"] for r in result], ["P01", "P03", "P04"])  # 6.4 글자 그대로
        self.assertEqual(result[2]["scope"], "all")  # 6.4 "[전체]"
        # [제안 기대값] 점수·구매자 수·지지자·범위는 5.3.3 규칙으로 계산 (6.3-1·6.3-2와 같은 동료):
        # 같은 그룹(G-F-20) 동료 C01·C02·C03 → P01: C01 min(4,3)=3, 1명 / P02: 품절이라 제외 /
        #   P03: C02 1 + C03 1 = 2, 2명 / P05: 품절 제외 → 후보 2개(P01, P03)
        # 여성 전체: C05 추가, 구매 없음 → 새 후보 없음
        # 전체: C04 추가 → P04: C04 1, 1명 (P01은 이미 선택) → 3개 채움
        self.assertEqual(result, [
            _item("P01", 3, "group", ["C01"], _colors("P01")),
            _item("P03", 2, "group", ["C02", "C03"], _colors("P03")),
            _item("P04", 1, "all", ["C04"], _colors("P04")),
        ])
        self._assert_buyers_match(result)

    def test_k_max_accepted(self) -> None:
        """B.3 K 최댓값 10은 허용: 후보가 10개보다 적으면 있는 만큼."""
        g = self._graph_with_c07()
        # [제안 기대값] C07이 받을 수 있는 후보는 6.3-2에서 본 4개(P02, P01, P03, P04)뿐이고
        # P05는 품절이라 제외 → K=10이어도 결과는 6.3-2(K=4)와 같다.
        result = recommend(g, "C07", 10)
        self.assertEqual(result, _c07_k4())
        self._assert_buyers_match(result)

    def test_k_min_accepted(self) -> None:
        """B.3 K 최솟값 1은 허용: 정렬 1위 한 개만."""
        g = self._graph_with_c07()
        # [제안 기대값] 같은 그룹에서 후보 3개(6.3-1)라 범위 확장 없음. 정렬 1위는 6.3-1의 P02(3, 2명).
        result = recommend(g, "C07", 1)
        self.assertEqual(result, _c07_k3()[:1])
        self._assert_buyers_match(result)


if __name__ == "__main__":
    unittest.main()
